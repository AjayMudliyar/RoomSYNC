from __future__ import annotations

import unicodedata
import uuid
from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_email_address(email: str) -> str:
    """Normalize emails deterministically using Unicode NFKC and lowercase."""
    return unicodedata.normalize("NFKC", email).strip().lower()


class UserManager(BaseUserManager["User"]):
    """Custom manager enforcing normalized email identifiers."""

    def get_by_natural_key(self, username: str | None) -> User:
        normalized = normalize_email_address(username or "")
        return self.get(**{self.model.USERNAME_FIELD: normalized})

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        normalized_email = normalize_email_address(email)
        if not normalized_email:
            raise ValueError("An email address is required.")

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)

        user = self.model(email=normalized_email, **extra_fields)
        if password is not None:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields.setdefault("email_verified_at", timezone.now())

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if not password:
            raise ValueError("Superuser must have a password.")

        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Authoritative UUID-based user identity per TDD.md §6.3.1 & M1 decisions Q5-Q7."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SUSPENDED = "suspended", "Suspended"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    phone_e164 = models.CharField(max_length=20, null=True, blank=True, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    can_seek_room = models.BooleanField(default=True)
    can_offer_room = models.BooleanField(default=False)
    can_list_property = models.BooleanField(default=False)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["status", "created_at"], name="acc_user_status_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="acc_user_email_lower_uniq"),
        ]

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_deletion_requested(self) -> bool:
        return self.deletion_requested_at is not None

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = normalize_email_address(self.email)
        if self.phone_e164 is not None:
            stripped = self.phone_e164.strip()
            self.phone_e164 = stripped if stripped else None
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.id)


class OAuthIdentity(models.Model):
    """External OAuth identity bound to immutable provider subject (sub)."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth_identities")
    provider = models.CharField(max_length=32, choices=Provider.choices)
    provider_sub = models.CharField(max_length=255)
    email_at_link = models.EmailField(max_length=254, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_oauth_identity"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_sub"], name="acc_oauth_provider_sub_uniq"
            ),
            models.UniqueConstraint(
                fields=["user", "provider"], name="acc_oauth_user_provider_uniq"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.user_id}"


class OAuthLinkChallenge(models.Model):
    """Single-use explicit link confirmation challenge preventing silent email collision merges."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oauth_link_challenges"
    )
    provider = models.CharField(
        max_length=32, choices=OAuthIdentity.Provider.choices, default=OAuthIdentity.Provider.GOOGLE
    )
    provider_sub = models.CharField(max_length=255)
    email_at_link = models.EmailField(max_length=254)
    token_hash = models.CharField(max_length=128, unique=True)
    existing_account_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_oauth_link_challenge"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="acc_oauth_link_user_exp_idx"),
        ]

    def __str__(self) -> str:
        return f"link-challenge:{self.provider}:{self.id}"


class RefreshSession(models.Model):
    """Rotating refresh session family record enabling instant reuse detection & revocation."""

    class ClientPlatform(models.TextChoices):
        WEB = "web", "Web"
        ANDROID = "android", "Android"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_sessions")
    parent_session = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_sessions",
    )
    token_hash = models.CharField(max_length=128, unique=True)
    client_platform = models.CharField(max_length=16, choices=ClientPlatform.choices)
    device_label = models.CharField(max_length=120, blank=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    auth_time = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    family_expires_at = models.DateTimeField()
    rotated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "accounts_refresh_session"
        indexes = [
            models.Index(
                fields=["user", "revoked_at", "rotated_at", "expires_at"],
                name="acc_ref_user_active_idx",
            ),
            models.Index(fields=["family_id", "revoked_at"], name="acc_ref_family_rev_idx"),
        ]

    @property
    def is_active_session(self) -> bool:
        now = timezone.now()
        return (
            self.revoked_at is None
            and self.rotated_at is None
            and self.expires_at > now
            and self.family_expires_at > now
        )

    def __str__(self) -> str:
        return f"session:{self.id}"


class EmailVerificationToken(models.Model):
    """Single-use HMAC-hashed email verification token."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_verification_tokens"
    )
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_email_verification_token"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="acc_everify_user_exp_idx"),
        ]

    def __str__(self) -> str:
        return f"email-verify:{self.id}"


class PasswordResetToken(models.Model):
    """Single-use HMAC-hashed password reset token."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_password_reset_token"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="acc_pwreset_user_exp_idx"),
        ]

    def __str__(self) -> str:
        return f"pw-reset:{self.id}"
