from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import User

logger = logging.getLogger("backend.notifications")


def send_verification_email_sync(*, user_id: str, raw_token: str) -> None:
    """Deliver email verification link using configured Django EMAIL_BACKEND."""
    user = User.objects.filter(id=user_id).first()
    if user is None or user.email_verified_at is not None or user.deletion_requested_at is not None:
        return
    web_origin = str(getattr(settings, "APP_WEB_ORIGIN", "http://localhost:5173")).rstrip("/")
    ttl_hours = int(getattr(settings, "EMAIL_VERIFICATION_TTL_HOURS", 24))
    expires_note = timedelta(hours=ttl_hours)
    del expires_note
    verify_url = f"{web_origin}/auth/verify-email?token={raw_token}"
    send_mail(
        subject="Verify your RoomSync email address",
        message=(
            "Welcome to RoomSync.\n\n"
            f"Use this verification link within {ttl_hours} hours:\n{verify_url}\n\n"
            "If you did not create a RoomSync account, you can ignore this message."
        ),
        from_email=str(getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@roomsync.local")),
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info(
        "Dispatched verification email",
        extra={"structured": {"user_id": str(user.id), "email_kind": "verification"}},
    )


def send_password_reset_email_sync(*, user_id: str, raw_token: str) -> None:
    """Deliver password reset link using configured Django EMAIL_BACKEND."""
    user = User.objects.filter(id=user_id).first()
    if user is None or user.deletion_requested_at is not None or not user.is_active:
        return
    web_origin = str(getattr(settings, "APP_WEB_ORIGIN", "http://localhost:5173")).rstrip("/")
    ttl_minutes = int(getattr(settings, "PASSWORD_RESET_TTL_MINUTES", 30))
    reset_url = f"{web_origin}/auth/reset-password?token={raw_token}"
    send_mail(
        subject="Reset your RoomSync password",
        message=(
            "A password reset was requested for your RoomSync account.\n\n"
            f"Use this reset link within {ttl_minutes} minutes:\n{reset_url}\n\n"
            "If you did not request this, you can safely ignore this email."
        ),
        from_email=str(getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@roomsync.local")),
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info(
        "Dispatched password reset email",
        extra={"structured": {"user_id": str(user.id), "email_kind": "password_reset"}},
    )

