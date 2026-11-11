from __future__ import annotations

import uuid
from typing import Any

from django.http import HttpRequest

from apps.audit.models import SecurityAuditEvent
from common.logging import redact_sensitive, request_id_ctx
from common.security import get_client_ip_hash


def record_security_event(
    *,
    event_type: str,
    outcome: str = SecurityAuditEvent.Outcome.SUCCESS,
    actor_user_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    client_platform: str = "",
    request: HttpRequest | None = None,
    ip_hash: str = "",
    request_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> SecurityAuditEvent:
    """Create an append-only security audit event with redacted metadata and hashed IP."""
    resolved_ip_hash = ip_hash
    resolved_platform = client_platform
    resolved_request_id = request_id or request_id_ctx.get()

    if request is not None:
        if not resolved_ip_hash:
            resolved_ip_hash = get_client_ip_hash(request)
        if not resolved_platform:
            resolved_platform = request.headers.get("X-Client-Platform", "").strip().lower()[:20]
        raw_req_id = request.META.get("HTTP_X_REQUEST_ID")
        if raw_req_id:
            resolved_request_id = str(raw_req_id)[:64]

    cleaned_metadata = redact_sensitive(dict(metadata or {}))
    return SecurityAuditEvent.objects.create(
        event_type=event_type[:80],
        outcome=outcome,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        client_platform=resolved_platform[:20],
        ip_hash=resolved_ip_hash[:64],
        request_id=resolved_request_id[:64],
        metadata=cleaned_metadata,
    )

