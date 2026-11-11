from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.http import HttpRequest

from .models import SecurityAuditEvent

if TYPE_CHECKING:
    BaseAuditAdmin = admin.ModelAdmin[SecurityAuditEvent]
else:
    BaseAuditAdmin = admin.ModelAdmin


@admin.register(SecurityAuditEvent)
class SecurityAuditEventAdmin(BaseAuditAdmin):
    list_display = (
        "created_at",
        "event_type",
        "outcome",
        "actor_user_id",
        "target_user_id",
        "client_platform",
        "request_id",
    )
    list_filter = ("outcome", "client_platform", "event_type")
    search_fields = ("event_type", "request_id", "actor_user_id", "target_user_id")
    readonly_fields = (
        "id",
        "event_type",
        "outcome",
        "actor_user_id",
        "target_user_id",
        "client_platform",
        "ip_hash",
        "request_id",
        "metadata",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: SecurityAuditEvent | None = None,
    ) -> bool:
        del request, obj
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: SecurityAuditEvent | None = None,
    ) -> bool:
        del request, obj
        return False

    def get_actions(self, request: HttpRequest) -> dict[str, Any]:
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

