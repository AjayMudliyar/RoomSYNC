from __future__ import annotations

from celery import shared_task

from apps.accounts.services.email_dispatch import (
    send_password_reset_email_sync,
    send_verification_email_sync,
)


@shared_task(name="accounts.send_verification_email")
def send_verification_email_task(user_id: str, raw_token: str) -> None:
    """Async Celery task dispatching verification email without persisting plaintext tokens."""
    send_verification_email_sync(user_id=user_id, raw_token=raw_token)


@shared_task(name="accounts.send_password_reset_email")
def send_password_reset_email_task(user_id: str, raw_token: str) -> None:
    """Async Celery task dispatching password reset email without persisting plaintext tokens."""
    send_password_reset_email_sync(user_id=user_id, raw_token=raw_token)

