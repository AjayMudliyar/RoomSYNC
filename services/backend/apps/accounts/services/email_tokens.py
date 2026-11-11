from __future__ import annotations

import functools
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import EmailVerificationToken, User, normalize_email_address
from apps.accounts.tasks import send_verification_email_task
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import (
    AccountDeletionRequestedError,
    AccountSuspendedError,
    AuthInvalidCredentialsError,
)
from common.security import generate_opaque_token, hmac_token

logger = logging.getLogger("backend.security")


def issue_verification_token_in_tx(
    *,
    user: User,
    request: HttpRequest | None = None,
    _user_locked: bool = False,
) -> str:
    """Create a single-use verification token under User -> EmailVerificationToken lock order."""
    if not _user_locked:
        User.objects.select_for_update().only("id").get(id=user.id)

    now = timezone.now()
    ttl_hours = int(getattr(settings, "EMAIL_VERIFICATION_TTL_HOURS", 24))
    active_token_ids = list(
        EmailVerificationToken.objects.select_for_update()
        .filter(user=user, consumed_at__isnull=True)
        .order_by("id")
        .values_list("id", flat=True)
    )
    if active_token_ids:
        EmailVerificationToken.objects.filter(id__in=active_token_ids).update(consumed_at=now)

    raw_token = generate_opaque_token("rsv")
    token_hash = hmac_token("email-verify", raw_token)
    EmailVerificationToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=ttl_hours),
    )

    record_security_event(
        event_type="auth.email.verification_sent",
        outcome=SecurityAuditEvent.Outcome.SUCCESS,
        actor_user_id=user.id,
        target_user_id=user.id,
        request=request,
    )

    user_id_str = str(user.id)
    transaction.on_commit(
        functools.partial(send_verification_email_task.delay, user_id_str, raw_token)
    )
    return raw_token


def verify_email_token(*, raw_token: str, request: HttpRequest) -> User:
    """Verify an email verification token atomically using User -> Token lock order."""
    token_hash = hmac_token("email-verify", raw_token)
    peek_user_id = (
        EmailVerificationToken.objects.filter(token_hash=token_hash)
        .values_list("user_id", flat=True)
        .first()
    )
    if peek_user_id is None:
        record_security_event(
            event_type="auth.email.verify_failed",
            outcome=SecurityAuditEvent.Outcome.FAILURE,
            actor_user_id=None,
            target_user_id=None,
            request=request,
            metadata={"reason": "invalid_or_expired_token"},
        )
        raise AuthInvalidCredentialsError("Email verification token is invalid or expired.")

    error_exc: Exception | None = None
    verified_user: User | None = None

    with transaction.atomic():
        # Global lock order: User -> EmailVerificationToken.
        user = User.objects.select_for_update().filter(id=peek_user_id).first()
        record = (
            EmailVerificationToken.objects.select_for_update()
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
            record_security_event(
                event_type="auth.email.verify_failed",
                outcome=SecurityAuditEvent.Outcome.FAILURE,
                actor_user_id=user.id if user is not None else None,
                target_user_id=user.id if user is not None else peek_user_id,
                request=request,
                metadata={"reason": "invalid_or_expired_token"},
            )
            error_exc = AuthInvalidCredentialsError(
                "Email verification token is invalid or expired."
            )
        elif user.deletion_requested_at is not None:
            error_exc = AccountDeletionRequestedError()
        elif user.status == User.Status.SUSPENDED or not user.is_active:
            error_exc = AccountSuspendedError()
        elif user.status == User.Status.DELETED:
            error_exc = AuthInvalidCredentialsError("Account is inactive.")
        else:
            record.consumed_at = now
            record.save(update_fields=["consumed_at"])
            if user.email_verified_at is None:
                user.email_verified_at = now
                user.save(update_fields=["email_verified_at", "updated_at"])
            record_security_event(
                event_type="auth.email.verified",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=user.id,
                target_user_id=user.id,
                request=request,
            )
            verified_user = user

    if error_exc is not None:
        raise error_exc
    assert verified_user is not None
    return verified_user


def resend_verification_email(
    *,
    request: HttpRequest,
    authenticated_user: User | None = None,
    email: str | None = None,
) -> None:
    """Resend verification email atomically under User -> Token lock order without enumeration."""
    target_id: uuid.UUID | None = None
    if authenticated_user is not None and authenticated_user.is_authenticated:
        target_id = authenticated_user.id
    elif email:
        normalized = normalize_email_address(email)
        peek_user = (
            User.objects.filter(email=normalized)
            .values("id", "email_verified_at", "deletion_requested_at", "is_active", "status")
            .first()
        )
        if (
            peek_user is None
            or peek_user["email_verified_at"] is not None
            or peek_user["deletion_requested_at"] is not None
            or not peek_user["is_active"]
            or peek_user["status"] != User.Status.ACTIVE
        ):
            return
        target_id = peek_user["id"]

    if target_id is None:
        return

    with transaction.atomic():
        # Global lock order: User -> EmailVerificationToken.
        locked_user = User.objects.select_for_update().filter(id=target_id).first()
        if (
            locked_user is None
            or locked_user.email_verified_at is not None
            or locked_user.deletion_requested_at is not None
            or not locked_user.is_active
            or locked_user.status != User.Status.ACTIVE
        ):
            return
        issue_verification_token_in_tx(user=locked_user, request=request, _user_locked=True)
