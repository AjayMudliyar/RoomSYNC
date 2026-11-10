from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User

if TYPE_CHECKING:
    BaseUserAdmin = DjangoUserAdmin[Any]
else:
    BaseUserAdmin = DjangoUserAdmin


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("id", "email", "status", "is_staff", "is_active", "created_at")
    list_filter = ("status", "is_staff", "is_active")
    search_fields = ("id", "email")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Lifecycle & Verification",
            {
                "fields": (
                    "status",
                    "phone_e164",
                    "email_verified_at",
                    "phone_verified_at",
                    "terms_accepted_at",
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
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
