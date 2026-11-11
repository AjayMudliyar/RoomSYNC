from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.http import HttpRequest

from .forms import RoomSyncUserChangeForm, RoomSyncUserCreationForm
from .models import (
    EmailVerificationToken,
    OAuthIdentity,
    OAuthLinkChallenge,
    PasswordResetToken,
    RefreshSession,
    User,
)

if TYPE_CHECKING:
    BaseUserAdmin = DjangoUserAdmin[Any]
    BaseOAuthAdmin = admin.ModelAdmin[OAuthIdentity]
    BaseRefreshAdmin = admin.ModelAdmin[RefreshSession]
    BaseEmailVerifyAdmin = admin.ModelAdmin[EmailVerificationToken]
    BasePwResetAdmin = admin.ModelAdmin[PasswordResetToken]
    BaseOAuthChallengeAdmin = admin.ModelAdmin[OAuthLinkChallenge]
else:
    BaseUserAdmin = DjangoUserAdmin
    BaseOAuthAdmin = admin.ModelAdmin
    BaseRefreshAdmin = admin.ModelAdmin
    BaseEmailVerifyAdmin = admin.ModelAdmin
    BasePwResetAdmin = admin.ModelAdmin
    BaseOAuthChallengeAdmin = admin.ModelAdmin


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    form = RoomSyncUserChangeForm
    add_form = RoomSyncUserCreationForm

    list_display = (
        "id",
        "email",
        "status",
        "email_verified_at",
        "can_seek_room",
        "can_offer_room",
        "can_list_property",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("status", "is_staff", "is_active", "can_offer_room", "can_list_property")
    search_fields = ("id", "email")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "password_changed_at")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Capabilities",
            {"fields": ("can_seek_room", "can_offer_room", "can_list_property")},
        ),
        (
            "Lifecycle & Verification",
            {
                "fields": (
                    "status",
                    "phone_e164",
                    "email_verified_at",
                    "phone_verified_at",
                    "terms_accepted_at",
                    "password_changed_at",
                    "deletion_requested_at",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "can_seek_room",
                    "can_offer_room",
                    "can_list_property",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(OAuthIdentity)
class OAuthIdentityAdmin(BaseOAuthAdmin):
    list_display = ("id", "user", "provider", "created_at", "last_used_at")
    list_filter = ("provider",)
    search_fields = ("user__email", "provider_sub")
    readonly_fields = ("id", "user", "provider", "provider_sub", "email_at_link", "created_at")


@admin.register(RefreshSession)
class RefreshSessionAdmin(BaseRefreshAdmin):
    list_display = (
        "id",
        "family_id",
        "user",
        "client_platform",
        "device_label",
        "created_at",
        "expires_at",
        "rotated_at",
        "revoked_at",
    )
    list_filter = ("client_platform",)
    search_fields = ("id", "family_id", "user__email")
    readonly_fields = (
        "id",
        "family_id",
        "user",
        "parent_session",
        "client_platform",
        "device_label",
        "ip_hash",
        "auth_time",
        "created_at",
        "last_used_at",
        "expires_at",
        "family_expires_at",
        "rotated_at",
        "revoked_at",
        "revoke_reason",
    )
    exclude = ("token_hash",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(BaseEmailVerifyAdmin):
    list_display = ("id", "user", "expires_at", "consumed_at", "created_at")
    readonly_fields = ("id", "user", "expires_at", "consumed_at", "created_at")
    exclude = ("token_hash",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(BasePwResetAdmin):
    list_display = ("id", "user", "expires_at", "consumed_at", "created_at")
    readonly_fields = ("id", "user", "expires_at", "consumed_at", "created_at")
    exclude = ("token_hash",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False


@admin.register(OAuthLinkChallenge)
class OAuthLinkChallengeAdmin(BaseOAuthChallengeAdmin):
    list_display = (
        "id",
        "user",
        "provider",
        "existing_account_verified",
        "expires_at",
        "consumed_at",
        "created_at",
    )
    readonly_fields = (
        "id",
        "user",
        "provider",
        "provider_sub",
        "email_at_link",
        "existing_account_verified",
        "expires_at",
        "consumed_at",
        "created_at",
    )
    exclude = ("token_hash",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False
