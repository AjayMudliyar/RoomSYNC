from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
actor_id_ctx: ContextVar[str] = ContextVar("actor_id", default="anonymous")

REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "access",
        "refresh",
        "secret",
        "otp",
        "authorization",
        "cookie",
        "set-cookie",
        "x-csrftoken",
        "x-internal-service-token",
        "email",
        "phone",
        "phone_e164",
        "date_of_birth",
        "body",
        "message_body",
        "evidence_object_key",
    }
)


def redact_sensitive(data: Any) -> Any:
    """Recursively mask sensitive PII and credentials before log emission."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            lowered = str(key).lower()
            if lowered in SENSITIVE_KEYS or any(
                marker in lowered for marker in ("secret", "token", "password", "cookie", "otp")
            ):
                sanitized[str(key)] = REDACTED_VALUE
            else:
                sanitized[str(key)] = redact_sensitive(value)
        return sanitized
    if isinstance(data, list):
        return [redact_sensitive(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Emit structured JSON log events aligned with TDD.md §16.2."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "severity": record.levelname,
            "service": "backend",
            "environment": os.environ.get("ENVIRONMENT", "local"),
            "request_id": request_id_ctx.get(),
            "actor_id": actor_id_ctx.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            payload.update(redact_sensitive(structured))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)

