from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions

from apps.accounts.models import OAuthIdentity, RefreshSession, User
from apps.accounts.services.google_oauth import verify_google_id_token
from apps.accounts.services.revocation import mark_sessions_revoked
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import RoomSyncAPIException, StateConflictError

DELETION_CONFIRMATION_PHRASE = "DELETE MY ACCOUNT"


def request_account_deletion(
    *,
    user: User,
    confirmation_text: str,
    password: str | None,
    google_id_token: str | None,
    nonce: str | None,
    confirm_recent_reauth: bool,
    session_auth_time: datetime | None,
    request: HttpRequest,
) -> datetime:
    """Verify explicit confirmation and reauth, record deletion request, and revoke all sessions."""
    if confirmation_text != DELETION_CONFIRMATION_PHRASE:
        raise drf_exceptions.ValidationError(
            {
                "confirmation_text": [
                    f"Must match '{DELETION_CONFIRMATION_PHRASE}' to request account deletion."
                ]
            }
        )

    now = timezone.now()
    if user.has_usable_password():
        if not password or not user.check_password(password):
            record_security_event(
                event_type="account.deletion_reauth_failed",
                outcome=SecurityAuditEvent.Outcome.FAILURE,
                actor_user_id=user.id,
                target_user_id=user.id,
                request=request,
            )
            raise RoomSyncAPIException(
                "Password reauthentication is required before requesting account deletion.",
                error_code="REAUTHENTICATION_FAILED",
                status_code=403,
            )
    else:
        google_identity = OAuthIdentity.objects.filter(
            user=user, provider=OAuthIdentity.Provider.GOOGLE
        ).first()
        if google_id_token:
            claims = verify_google_id_token(
                raw_id_token=google_id_token,
                nonce=nonce or "",
                enforce_replay_check=True,
            )
            if google_identity is None or claims.sub != google_identity.provider_sub:
                raise RoomSyncAPIException(
                    "Google reauthentication does not match this account.",
                    error_code="REAUTHENTICATION_FAILED",
                    status_code=403,
                )
        elif confirm_recent_reauth and session_auth_time is not None:
            max_age = int(getattr(settings, "AUTH_REAUTH_MAX_AGE_SECONDS", 300))
            if (now - session_auth_time) > timedelta(seconds=max_age):
                raise RoomSyncAPIException(
                    "Recent session reauthentication expired; provide fresh Google auth proof.",
                    error_code="REAUTHENTICATION_REQUIRED",
                    status_code=403,
                )
        else:
            raise RoomSyncAPIException(
                "Reauthentication is required before requesting account deletion.",
                error_code="REAUTHENTICATION_REQUIRED",
                status_code=403,
            )

    conflict_exc: Exception | None = None
    revoked_sids: list[uuid.UUID] = []
    watermark_cutoff = now

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(id=user.id)
        if locked_user.deletion_requested_at is not None:
            conflict_exc = StateConflictError("Account deletion has already been requested.")
        else:
            # Q7: preserve current status (do NOT immediately set status="deleted").
            locked_user.deletion_requested_at = now
            locked_user.save(update_fields=["deletion_requested_at", "updated_at"])

            qs = RefreshSession.objects.filter(user=locked_user)
            rows = list(qs.values_list("id", "created_at"))
            revoked_sids = [sid for sid, _ in rows]
            created_times = [created for _, created in rows if created is not None]
            if created_times:
                watermark_cutoff = max([now, *created_times])
            qs.filter(revoked_at__isnull=True).update(
                revoked_at=now,
                revoke_reason="deletion_requested",
            )
            record_security_event(
                event_type="account.deletion_requested",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=locked_user.id,
                target_user_id=locked_user.id,
                request=request,
                metadata={"revoked_session_count": len(revoked_sids)},
            )
            mark_sessions_revoked(
                revoked_sids,
                user_id_watermark=locked_user.id,
                watermark_cutoff=watermark_cutoff,
            )

    if conflict_exc is not None:
        raise conflict_exc

    return now


def build_user_data_export(*, user: User, request: HttpRequest) -> dict[str, Any]:
    """Build synchronous DPDP account export excluding password hashes and raw secret tokens."""
    now = timezone.now()
    oauth_rows = [
        {
            "provider": item.provider,
            "created_at": item.created_at.isoformat(),
            "last_used_at": item.last_used_at.isoformat() if item.last_used_at else None,
        }
        for item in OAuthIdentity.objects.filter(user=user).order_by("created_at")
    ]

    session_rows = [
        {
            "id": str(sess.id),
            "client_platform": sess.client_platform,
            "device_label": sess.device_label,
            "created_at": sess.created_at.isoformat(),
            "last_used_at": sess.last_used_at.isoformat() if sess.last_used_at else None,
            "expires_at": sess.expires_at.isoformat(),
            "revoked_at": sess.revoked_at.isoformat() if sess.revoked_at else None,
        }
        for sess in RefreshSession.objects.filter(user=user).order_by("-created_at")[:100]
    ]

    audit_rows = [
        {
            "id": str(evt.id),
            "event_type": evt.event_type,
            "outcome": evt.outcome,
            "client_platform": evt.client_platform,
            "request_id": evt.request_id,
            "created_at": evt.created_at.isoformat(),
        }
        for evt in SecurityAuditEvent.objects.filter(target_user_id=user.id).order_by(
            "-created_at"
        )[:200]
    ]

    record_security_event(
        event_type="account.data_exported",
        outcome=SecurityAuditEvent.Outcome.SUCCESS,
        actor_user_id=user.id,
        target_user_id=user.id,
        request=request,
    )

    return {
        "schema_version": "1.0",
        "exported_at": now.isoformat(),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "phone_e164": user.phone_e164,
            "status": user.status,
            "email_verified_at": (
                user.email_verified_at.isoformat() if user.email_verified_at else None
            ),
            "phone_verified_at": (
                user.phone_verified_at.isoformat() if user.phone_verified_at else None
            ),
            "terms_accepted_at": (
                user.terms_accepted_at.isoformat() if user.terms_accepted_at else None
            ),
            "password_changed_at": (
                user.password_changed_at.isoformat() if user.password_changed_at else None
            ),
            "deletion_requested_at": (
                user.deletion_requested_at.isoformat() if user.deletion_requested_at else None
            ),
            "capabilities": {
                "can_seek_room": user.can_seek_room,
                "can_offer_room": user.can_offer_room,
                "can_list_property": user.can_list_property,
            },
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        },
        "oauth_identities": oauth_rows,
        "sessions": session_rows,
        "security_events": audit_rows,
    }
