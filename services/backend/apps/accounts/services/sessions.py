from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import RefreshSession, User
from apps.accounts.services.jwt_tokens import mint_access_token
from apps.accounts.services.revocation import (
    datetime_to_epoch_us,
    epoch_us_to_datetime,
    get_user_revocation_cutoff_us_fail_closed,
    mark_sessions_revoked,
)
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import (
    AccountDeletionRequestedError,
    AccountSuspendedError,
    AuthInvalidCredentialsError,
    RefreshReuseDetectedError,
)
from common.security import generate_opaque_token, get_client_ip_hash, hmac_token


@dataclass(frozen=True, slots=True)
class IssuedSessionPair:
    session: RefreshSession
    access_token: str
    refresh_token: str
    expires_in_seconds: int


@dataclass(frozen=True, slots=True)
class PendingRedisRevocation:
    """PostgreSQL-revoked session set awaiting fail-closed Redis marker publication."""

    sids: list[uuid.UUID]
    watermark_user_id: uuid.UUID | None
    watermark_cutoff: datetime

    def publish(self) -> None:
        if self.sids or self.watermark_user_id is not None:
            mark_sessions_revoked(
                self.sids,
                user_id_watermark=self.watermark_user_id,
                watermark_cutoff=self.watermark_cutoff,
            )


@dataclass(slots=True)
class _RotationTxResult:
    issued: IssuedSessionPair | None = None
    error: Exception | None = None
    revoke_sids: list[uuid.UUID] = field(default_factory=list)


def _derive_device_label(request: HttpRequest | None, explicit_label: str = "") -> str:
    cleaned = " ".join(explicit_label.strip().split())
    if cleaned:
        return cleaned[:120]
    if request is not None:
        ua = str(request.headers.get("User-Agent", "") or "").strip()
        if ua:
            return " ".join(ua.split())[:120]
    return ""


def issue_session_pair(
    *,
    user: User,
    client_platform: str,
    request: HttpRequest | None = None,
    device_label: str = "",
    auth_time: datetime | None = None,
) -> IssuedSessionPair:
    """Create a new RefreshSession family root row and mint a signed access JWT."""
    ttl_days = int(getattr(settings, "REFRESH_TOKEN_TTL_DAYS", 14))
    max_days = int(getattr(settings, "REFRESH_FAMILY_MAX_DAYS", 30))

    raw_refresh = generate_opaque_token("rsr")
    token_hash = hmac_token("refresh-token", raw_refresh)
    ip_hash = get_client_ip_hash(request) if request is not None else ""
    resolved_device = _derive_device_label(request, device_label)

    with transaction.atomic():
        # Serialize session creation per user against user-wide revocation & rotation.
        User.objects.select_for_update().only("id").get(id=user.id)
        now = timezone.now()
        expires_at = now + timedelta(days=ttl_days)
        family_expires_at = now + timedelta(days=max_days)

        min_after_us = get_user_revocation_cutoff_us_fail_closed(user.id)
        revoked_bounds = RefreshSession.objects.filter(
            user=user,
            revoked_at__isnull=False,
        ).aggregate(max_rev=Max("revoked_at"), max_created=Max("created_at"))
        for dt_bound in (revoked_bounds["max_rev"], revoked_bounds["max_created"]):
            if dt_bound is not None:
                bound_us = datetime_to_epoch_us(dt_bound)
                min_after_us = bound_us if min_after_us is None else max(min_after_us, bound_us)

        session = RefreshSession.objects.create(
            user=user,
            token_hash=token_hash,
            client_platform=client_platform,
            device_label=resolved_device,
            ip_hash=ip_hash,
            auth_time=auth_time or now,
            last_used_at=now,
            expires_at=expires_at,
            family_expires_at=family_expires_at,
        )
        # Ensure sub-microsecond / frozen-clock issuances sort strictly after prior cutoffs.
        if min_after_us is not None and datetime_to_epoch_us(session.created_at) <= min_after_us:
            bumped_created_at = epoch_us_to_datetime(min_after_us + 1)
            RefreshSession.objects.filter(id=session.id).update(created_at=bumped_created_at)
            session.created_at = bumped_created_at

    access_jwt, expires_in_seconds = mint_access_token(user_id=user.id, session_id=session.id)
    return IssuedSessionPair(
        session=session,
        access_token=access_jwt,
        refresh_token=raw_refresh,
        expires_in_seconds=expires_in_seconds,
    )


def _revoke_family_rows_in_tx(
    *,
    family_id: uuid.UUID,
    reason: str,
    now: datetime,
) -> list[uuid.UUID]:
    RefreshSession.objects.filter(family_id=family_id, revoked_at__isnull=True).update(
        revoked_at=now,
        revoke_reason=reason[:64],
    )
    return list(RefreshSession.objects.filter(family_id=family_id).values_list("id", flat=True))


def rotate_refresh_session(
    *,
    raw_refresh_token: str,
    client_platform: str,
    request: HttpRequest,
    device_label: str = "",
) -> IssuedSessionPair:
    """Atomically rotate a refresh token with row locking and full-family reuse revocation."""
    token_hash = hmac_token("refresh-token", raw_refresh_token)
    ip_hash = get_client_ip_hash(request)
    now = timezone.now()
    ttl_days = int(getattr(settings, "REFRESH_TOKEN_TTL_DAYS", 14))

    tx_result = _rotate_refresh_session_tx(
        token_hash=token_hash,
        client_platform=client_platform,
        request=request,
        ip_hash=ip_hash,
        device_label=device_label,
        now=now,
        ttl_days=ttl_days,
    )

    if tx_result.revoke_sids:
        mark_sessions_revoked(tx_result.revoke_sids)

    if tx_result.error is not None:
        raise tx_result.error

    assert tx_result.issued is not None
    return tx_result.issued


def _rotate_refresh_session_tx(
    *,
    token_hash: str,
    client_platform: str,
    request: HttpRequest,
    ip_hash: str,
    device_label: str,
    now: datetime,
    ttl_days: int,
) -> _RotationTxResult:
    peek_user_id = (
        RefreshSession.objects.filter(token_hash=token_hash)
        .values_list("user_id", flat=True)
        .first()
    )
    if peek_user_id is None:
        record_security_event(
            event_type="auth.refresh.failed",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            client_platform=client_platform,
            request=request,
            ip_hash=ip_hash,
            metadata={"reason": "unknown_token"},
        )
        return _RotationTxResult(error=AuthInvalidCredentialsError("Invalid refresh token."))

    with transaction.atomic():
        # Global lock order: User -> RefreshSession (prevents deadlocks with revoke/issue).
        User.objects.select_for_update().only("id").get(id=peek_user_id)
        session = (
            RefreshSession.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=token_hash)
            .first()
        )
        if session is None:
            record_security_event(
                event_type="auth.refresh.failed",
                outcome=SecurityAuditEvent.Outcome.FAILURE,
                client_platform=client_platform,
                request=request,
                ip_hash=ip_hash,
                metadata={"reason": "unknown_token"},
            )
            return _RotationTxResult(error=AuthInvalidCredentialsError("Invalid refresh token."))

        if session.client_platform != client_platform:
            record_security_event(
                event_type="auth.refresh.failed",
                outcome=SecurityAuditEvent.Outcome.BLOCKED,
                actor_user_id=session.user_id,
                target_user_id=session.user_id,
                client_platform=client_platform,
                request=request,
                ip_hash=ip_hash,
                metadata={"reason": "platform_mismatch"},
            )
            return _RotationTxResult(
                error=AuthInvalidCredentialsError(
                    "Refresh token is invalid for this client platform."
                )
            )

        if session.rotated_at is not None or (
            session.revoked_at is not None and session.revoke_reason == "reuse_detected"
        ):
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason="reuse_detected",
                now=now,
            )
            record_security_event(
                event_type="auth.refresh.reuse_detected",
                outcome=SecurityAuditEvent.Outcome.BLOCKED,
                actor_user_id=session.user_id,
                target_user_id=session.user_id,
                client_platform=client_platform,
                request=request,
                ip_hash=ip_hash,
                metadata={"family_id": str(session.family_id), "session_id": str(session.id)},
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=RefreshReuseDetectedError(),
            )

        if session.revoked_at is not None:
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason=session.revoke_reason or "revoked",
                now=now,
            )
            record_security_event(
                event_type="auth.refresh.failed",
                outcome=SecurityAuditEvent.Outcome.BLOCKED,
                actor_user_id=session.user_id,
                target_user_id=session.user_id,
                client_platform=client_platform,
                request=request,
                ip_hash=ip_hash,
                metadata={"reason": "session_revoked"},
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=AuthInvalidCredentialsError("Session has been revoked."),
            )

        if session.expires_at <= now or session.family_expires_at <= now:
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason="expired",
                now=now,
            )
            record_security_event(
                event_type="auth.refresh.failed",
                outcome=SecurityAuditEvent.Outcome.FAILURE,
                actor_user_id=session.user_id,
                target_user_id=session.user_id,
                client_platform=client_platform,
                request=request,
                ip_hash=ip_hash,
                metadata={"reason": "expired"},
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=AuthInvalidCredentialsError("Refresh session expired."),
            )

        user = session.user
        if user.deletion_requested_at is not None:
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason="deletion_requested",
                now=now,
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=AccountDeletionRequestedError(),
            )
        if user.status == User.Status.SUSPENDED or not user.is_active:
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason="account_suspended",
                now=now,
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=AccountSuspendedError(),
            )
        if user.status == User.Status.DELETED:
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason="account_deleted",
                now=now,
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=AuthInvalidCredentialsError("Account is inactive."),
            )

        redis_cutoff_us = get_user_revocation_cutoff_us_fail_closed(user.id)
        parent_us = datetime_to_epoch_us(session.created_at)
        if redis_cutoff_us is not None and parent_us <= redis_cutoff_us:
            sids = _revoke_family_rows_in_tx(
                family_id=session.family_id,
                reason="user_watermark_revoked",
                now=now,
            )
            return _RotationTxResult(
                revoke_sids=sids,
                error=AuthInvalidCredentialsError("Session has been revoked."),
            )

        # Valid unrotated session: rotate atomically into a child session inside the same family.
        session.rotated_at = now
        session.last_used_at = now
        session.save(update_fields=["rotated_at", "last_used_at"])

        next_raw = generate_opaque_token("rsr")
        next_hash = hmac_token("refresh-token", next_raw)
        next_expires_at = min(now + timedelta(days=ttl_days), session.family_expires_at)
        resolved_device = _derive_device_label(request, device_label) or session.device_label

        child = RefreshSession.objects.create(
            family_id=session.family_id,
            user=user,
            parent_session=session,
            token_hash=next_hash,
            client_platform=client_platform,
            device_label=resolved_device,
            ip_hash=ip_hash,
            auth_time=session.auth_time,
            last_used_at=now,
            expires_at=next_expires_at,
            family_expires_at=session.family_expires_at,
        )
        floor_us = parent_us if redis_cutoff_us is None else max(parent_us, redis_cutoff_us)
        if datetime_to_epoch_us(child.created_at) <= floor_us:
            bumped_created_at = epoch_us_to_datetime(floor_us + 1)
            RefreshSession.objects.filter(id=child.id).update(created_at=bumped_created_at)
            child.created_at = bumped_created_at
        record_security_event(
            event_type="auth.refresh.rotated",
            outcome=SecurityAuditEvent.Outcome.SUCCESS,
            actor_user_id=user.id,
            target_user_id=user.id,
            client_platform=client_platform,
            request=request,
            ip_hash=ip_hash,
            metadata={"family_id": str(session.family_id), "session_id": str(child.id)},
        )
        access_jwt, expires_in_seconds = mint_access_token(user_id=user.id, session_id=child.id)
        return _RotationTxResult(
            issued=IssuedSessionPair(
                session=child,
                access_token=access_jwt,
                refresh_token=next_raw,
                expires_in_seconds=expires_in_seconds,
            )
        )


def revoke_session_family(
    *,
    family_id: uuid.UUID,
    reason: str,
) -> list[uuid.UUID]:
    """Revoke every session row in family_id in PostgreSQL and push Redis revocation markers."""
    peek_user_id = (
        RefreshSession.objects.filter(family_id=family_id)
        .values_list("user_id", flat=True)
        .first()
    )
    if peek_user_id is None:
        return []
    now = timezone.now()
    with transaction.atomic():
        User.objects.select_for_update().only("id").get(id=peek_user_id)
        sids = _revoke_family_rows_in_tx(family_id=family_id, reason=reason, now=now)
        if sids:
            mark_sessions_revoked(sids)
    return sids


def revoke_user_sessions_in_tx(
    *,
    user: User,
    reason: str,
    now: datetime,
    except_family_id: uuid.UUID | None = None,
) -> PendingRedisRevocation:
    """Revoke user RefreshSessions in an active User-locked TX before Redis publish."""
    watermark_user_id = user.id if except_family_id is None else None
    qs = RefreshSession.objects.filter(user=user)
    if except_family_id is not None:
        qs = qs.exclude(family_id=except_family_id)
    rows = list(qs.values_list("id", "created_at"))
    sids = [sid for sid, _ in rows]
    created_times = [created for _, created in rows if created is not None]
    watermark_cutoff = max([now, *created_times]) if created_times else now
    qs.filter(revoked_at__isnull=True).update(revoked_at=now, revoke_reason=reason[:64])
    return PendingRedisRevocation(
        sids=sids,
        watermark_user_id=watermark_user_id,
        watermark_cutoff=watermark_cutoff,
    )


def revoke_all_user_sessions(
    *,
    user: User,
    reason: str,
    except_family_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    """Revoke all (or all non-current) sessions for user cleanly across DB and Redis."""
    with transaction.atomic():
        # Global lock order: User -> RefreshSession (matches issue_session_pair & rotate).
        User.objects.select_for_update().only("id").get(id=user.id)
        now = timezone.now()
        pending = revoke_user_sessions_in_tx(
            user=user,
            reason=reason,
            now=now,
            except_family_id=except_family_id,
        )
        pending.publish()
    return pending.sids

