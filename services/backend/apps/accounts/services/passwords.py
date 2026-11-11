from __future__ import annotations

import functools
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions

from apps.accounts.models import PasswordResetToken, User, normalize_email_address
from apps.accounts.services.email_tokens import issue_verification_token_in_tx
from apps.accounts.services.rate_limit import (
    assert_login_rate_limits_allowed,
    clear_login_failures,
    enforce_ip_rate_limit,
    record_login_failure,
)
from apps.accounts.services.sessions import (
    IssuedSessionPair,
    issue_session_pair,
    revoke_user_sessions_in_tx,
)
from apps.accounts.tasks import send_password_reset_email_task
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import (
    AccountDeletionRequestedError,
    AccountSuspendedError,
    AuthInvalidCredentialsError,
    RoomSyncAPIException,
    StateConflictError,
)
from common.security import generate_opaque_token, hmac_token

_DUMMY_HASH: str | None = None


def _get_dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = make_password("RoomSyncTimingSafeDummy!2026")
    return _DUMMY_HASH


def _validate_password_or_raise(password: str, *, user: User, field_name: str = "password") -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise drf_exceptions.ValidationError({field_name: list(exc.messages)}) from exc


def register_with_email_password(
    *,
    email: str,
    password: str,
    accept_terms: bool,
    confirm_adult: bool,
    client_platform: str,
    request: HttpRequest,
    device_label: str = "",
) -> tuple[User, IssuedSessionPair]:
    """Register an active password account with unverified email and issue session credentials."""
    enforce_ip_rate_limit(
        request,
        bucket="register_ip",
        max_attempts=int(getattr(settings, "RATE_LIMIT_REGISTER_IP_MAX", 5)),
        window_seconds=int(getattr(settings, "RATE_LIMIT_REGISTER_IP_WINDOW_SECONDS", 600)),
    )

    if not accept_terms or not confirm_adult:
        errors: dict[str, list[str]] = {}
        if not accept_terms:
            errors["accept_terms"] = ["You must accept the Terms and Privacy Policy."]
        if not confirm_adult:
            errors["confirm_adult"] = ["You must confirm that you are at least 18 years old."]
        raise drf_exceptions.ValidationError(errors)

    normalized_email = normalize_email_address(email)
    if not normalized_email:
        raise drf_exceptions.ValidationError({"email": ["A valid email address is required."]})

    if User.objects.filter(email=normalized_email).exists():
        record_security_event(
            event_type="auth.register.conflict",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            client_platform=client_platform,
            request=request,
        )
        raise StateConflictError("Unable to create account with the provided email.")

    probe_user = User(email=normalized_email)
    _validate_password_or_raise(password, user=probe_user, field_name="password")

    now = timezone.now()
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=normalized_email,
                password=password,
                status=User.Status.ACTIVE,
                terms_accepted_at=now,
                password_changed_at=now,
                email_verified_at=None,
                last_login=now,
                can_seek_room=True,
                can_offer_room=False,
                can_list_property=False,
            )
            issue_verification_token_in_tx(user=user, request=request)
            issued = issue_session_pair(
                user=user,
                client_platform=client_platform,
                request=request,
                device_label=device_label,
                auth_time=now,
            )
            record_security_event(
                event_type="auth.register.success",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=user.id,
                target_user_id=user.id,
                client_platform=client_platform,
                request=request,
                metadata={"session_id": str(issued.session.id)},
            )
    except IntegrityError as exc:
        raise StateConflictError("Unable to create account with the provided email.") from exc

    return user, issued


def login_with_email_password(
    *,
    email: str,
    password: str,
    client_platform: str,
    request: HttpRequest,
    device_label: str = "",
) -> tuple[User, IssuedSessionPair]:
    """Authenticate an email/password account with timing-safe verification and rate limits."""
    normalized_email = normalize_email_address(email)
    assert_login_rate_limits_allowed(request, normalized_email=normalized_email)

    user = User.objects.filter(email=normalized_email).first()
    if user is None or not user.has_usable_password():
        check_password(password, _get_dummy_hash())
        record_login_failure(request, normalized_email=normalized_email)
        record_security_event(
            event_type="auth.login.failed",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            client_platform=client_platform,
            request=request,
            metadata={"reason": "invalid_credentials"},
        )
        raise AuthInvalidCredentialsError("Invalid email or password.")

    if not user.check_password(password):
        record_login_failure(request, normalized_email=normalized_email)
        record_security_event(
            event_type="auth.login.failed",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            target_user_id=user.id,
            client_platform=client_platform,
            request=request,
            metadata={"reason": "invalid_credentials"},
        )
        raise AuthInvalidCredentialsError("Invalid email or password.")

    if user.deletion_requested_at is not None:
        record_security_event(
            event_type="auth.login.blocked",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            target_user_id=user.id,
            client_platform=client_platform,
            request=request,
            metadata={"reason": "deletion_requested"},
        )
        raise AccountDeletionRequestedError()

    if user.status == User.Status.SUSPENDED or not user.is_active:
        record_security_event(
            event_type="auth.login.blocked",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            target_user_id=user.id,
            client_platform=client_platform,
            request=request,
            metadata={"reason": "suspended"},
        )
        raise AccountSuspendedError()

    if user.status == User.Status.DELETED:
        raise AuthInvalidCredentialsError("Invalid email or password.")

    clear_login_failures(request, normalized_email=normalized_email)
    now = timezone.now()
    user.last_login = now
    user.save(update_fields=["last_login", "updated_at"])

    issued = issue_session_pair(
        user=user,
        client_platform=client_platform,
        request=request,
        device_label=device_label,
        auth_time=now,
    )
    record_security_event(
        event_type="auth.login.success",
        outcome=SecurityAuditEvent.Outcome.SUCCESS,
        actor_user_id=user.id,
        target_user_id=user.id,
        client_platform=client_platform,
        request=request,
        metadata={"session_id": str(issued.session.id)},
    )
    return user, issued


def request_password_reset(*, email: str, request: HttpRequest) -> None:
    """Create a password reset token silently when eligible; anti-enumeration safe."""
    enforce_ip_rate_limit(
        request,
        bucket="forgot_ip",
        max_attempts=int(getattr(settings, "RATE_LIMIT_FORGOT_IP_MAX", 5)),
        window_seconds=int(getattr(settings, "RATE_LIMIT_FORGOT_IP_WINDOW_SECONDS", 600)),
    )

    normalized = normalize_email_address(email)
    peek_user = (
        User.objects.filter(email=normalized)
        .values("id", "is_active", "status", "deletion_requested_at")
        .first()
    )
    if (
        peek_user is None
        or not peek_user["is_active"]
        or peek_user["status"] != User.Status.ACTIVE
        or peek_user["deletion_requested_at"] is not None
    ):
        return

    ttl_minutes = int(getattr(settings, "PASSWORD_RESET_TTL_MINUTES", 30))
    raw_token = generate_opaque_token("rsp")
    token_hash = hmac_token("password-reset", raw_token)

    with transaction.atomic():
        # Global lock order: User -> PasswordResetToken.
        user = User.objects.select_for_update().filter(id=peek_user["id"]).first()
        if (
            user is None
            or not user.is_active
            or user.status != User.Status.ACTIVE
            or user.deletion_requested_at is not None
        ):
            return

        now = timezone.now()
        active_token_ids = list(
            PasswordResetToken.objects.select_for_update()
            .filter(user=user, consumed_at__isnull=True)
            .order_by("id")
            .values_list("id", flat=True)
        )
        if active_token_ids:
            PasswordResetToken.objects.filter(id__in=active_token_ids).update(consumed_at=now)
        PasswordResetToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=ttl_minutes),
        )
        record_security_event(
            event_type="auth.password.forgot_requested",
            outcome=SecurityAuditEvent.Outcome.SUCCESS,
            target_user_id=user.id,
            request=request,
        )
        user_id_str = str(user.id)
        transaction.on_commit(
            functools.partial(send_password_reset_email_task.delay, user_id_str, raw_token)
        )


def confirm_password_reset(*, raw_token: str, new_password: str, request: HttpRequest) -> None:
    """Complete password reset atomically and revoke every active session family for the user."""
    token_hash = hmac_token("password-reset", raw_token)
    peek_user_id = (
        PasswordResetToken.objects.filter(token_hash=token_hash)
        .values_list("user_id", flat=True)
        .first()
    )
    if peek_user_id is None:
        record_security_event(
            event_type="auth.password.reset_failed",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            target_user_id=None,
            request=request,
            metadata={"reason": "invalid_or_expired_token"},
        )
        raise AuthInvalidCredentialsError("Password reset token is invalid or expired.")

    error_exc: Exception | None = None
    audit_invalid_token = False

    with transaction.atomic():
        # Global lock order: User -> PasswordResetToken -> RefreshSession.
        user = User.objects.select_for_update().filter(id=peek_user_id).first()
        record = (
            PasswordResetToken.objects.select_for_update()
            .filter(token_hash=token_hash, user_id=user.id)
            .first()
            if user is not None
            else None
        )
        now = timezone.now()
        if (
            user is None
            or record is None
            or record.consumed_at is not None
            or record.expires_at <= now
        ):
            audit_invalid_token = True
            error_exc = AuthInvalidCredentialsError("Password reset token is invalid or expired.")
        elif user.deletion_requested_at is not None:
            error_exc = AccountDeletionRequestedError()
        elif user.status == User.Status.SUSPENDED or not user.is_active:
            error_exc = AccountSuspendedError()
        elif user.status == User.Status.DELETED:
            error_exc = AuthInvalidCredentialsError("Account is inactive.")
        else:
            _validate_password_or_raise(new_password, user=user, field_name="new_password")
            record.consumed_at = now
            record.save(update_fields=["consumed_at"])
            user.set_password(new_password)
            user.password_changed_at = now
            user.save(update_fields=["password", "password_changed_at", "updated_at"])

            pending_revocation = revoke_user_sessions_in_tx(
                user=user,
                reason="password_reset",
                now=now,
            )
            record_security_event(
                event_type="auth.password.reset",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=user.id,
                target_user_id=user.id,
                request=request,
            )
            pending_revocation.publish()

    if error_exc is not None:
        if audit_invalid_token:
            record_security_event(
                event_type="auth.password.reset_failed",
                outcome=SecurityAuditEvent.Outcome.FAILURE,
                target_user_id=peek_user_id,
                request=request,
                metadata={"reason": "invalid_or_expired_token"},
            )
        raise error_exc


def change_user_password(
    *,
    user: User,
    current_password: str | None,
    new_password: str,
    current_family_id: uuid.UUID,
    request: HttpRequest,
) -> None:
    """Change authenticated user's password and invalidate all sibling session families."""
    reauth_failed = False
    status_error: Exception | None = None

    with transaction.atomic():
        # Global lock order: User -> RefreshSession; re-read authoritative row under lock.
        locked_user = User.objects.select_for_update().filter(id=user.id).first()
        if locked_user is None:
            status_error = AuthInvalidCredentialsError("Account is inactive.")
        elif locked_user.deletion_requested_at is not None:
            status_error = AccountDeletionRequestedError()
        elif locked_user.status == User.Status.SUSPENDED or not locked_user.is_active:
            status_error = AccountSuspendedError()
        elif locked_user.status == User.Status.DELETED:
            status_error = AuthInvalidCredentialsError("Account is inactive.")
        elif locked_user.has_usable_password() and (
            not current_password or not locked_user.check_password(current_password)
        ):
            reauth_failed = True
        else:
            _validate_password_or_raise(new_password, user=locked_user, field_name="new_password")
            now = timezone.now()
            locked_user.set_password(new_password)
            locked_user.password_changed_at = now
            locked_user.save(update_fields=["password", "password_changed_at", "updated_at"])

            pending_revocation = revoke_user_sessions_in_tx(
                user=locked_user,
                reason="password_change",
                now=now,
                except_family_id=current_family_id,
            )
            record_security_event(
                event_type="auth.password.changed",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=locked_user.id,
                target_user_id=locked_user.id,
                request=request,
                metadata={"revoked_sibling_sessions": len(pending_revocation.sids)},
            )
            pending_revocation.publish()

            user.password = locked_user.password
            user.password_changed_at = locked_user.password_changed_at
            user.updated_at = locked_user.updated_at

    if status_error is not None:
        raise status_error

    if reauth_failed:
        record_security_event(
            event_type="auth.password.change_failed",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            actor_user_id=user.id,
            target_user_id=user.id,
            request=request,
            metadata={"reason": "incorrect_current_password"},
        )
        raise RoomSyncAPIException(
            "Current password verification failed.",
            error_code="REAUTHENTICATION_FAILED",
            status_code=403,
        )
