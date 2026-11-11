from __future__ import annotations

import uuid
from typing import Any, ClassVar, NoReturn

from django.db import models


class SecurityAuditQuerySet(models.QuerySet["SecurityAuditEvent"]):
    """Append-only queryset prohibiting ordinary ORM bulk updates and deletes."""

    def update(self, **kwargs: Any) -> NoReturn:
        del kwargs
        raise PermissionError("SecurityAuditEvent records are append-only and cannot be updated.")

    def delete(self) -> NoReturn:
        raise PermissionError("SecurityAuditEvent records are append-only and cannot be deleted.")


class SecurityAuditManager(models.Manager["SecurityAuditEvent"]):
    """Custom manager enforcing append-only behavior across queries."""

    def get_queryset(self) -> SecurityAuditQuerySet:
        return SecurityAuditQuerySet(self.model, using=self._db)

    def bulk_update(
        self,
        objs: Any,
        fields: Any,
        batch_size: int | None = None,
    ) -> NoReturn:
        del objs, fields, batch_size
        raise PermissionError("SecurityAuditEvent records are append-only and cannot be updated.")


class SecurityAuditEvent(models.Model):
    """Append-only authentication and account security audit log (Q9)."""

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=80, db_index=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices)

    actor_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    target_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    client_platform = models.CharField(max_length=20, blank=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    request_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects: ClassVar[SecurityAuditManager] = SecurityAuditManager()

    class Meta:
        db_table = "audit_security_event"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["event_type", "-created_at"], name="audit_evt_type_created_idx"),
            models.Index(
                fields=["actor_user_id", "-created_at"], name="audit_evt_actor_created_idx"
            ),
            models.Index(
                fields=["target_user_id", "-created_at"], name="audit_evt_target_created_idx"
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise PermissionError(
                "SecurityAuditEvent records are append-only and cannot be modified."
            )
        super().save(*args, **kwargs)

    def delete(self, using: Any = None, keep_parents: bool = False) -> NoReturn:
        del using, keep_parents
        raise PermissionError("SecurityAuditEvent records are append-only and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.event_type}:{self.outcome}:{self.id}"

