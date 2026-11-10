import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "authorization",
        "cookie",
        "x-internal-service-token",
        "internal_service_token",
        "otp",
        "email",
        "phone",
        "phone_e164",
        "date_of_birth",
        "answers",
        "raw_payload",
    }
)


def redact_sensitive(data: Any) -> Any:
    """Recursively mask PII and secret keys prior to logging."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            lowered = str(key).lower()
            has_secret_marker = any(s in lowered for s in ("secret", "token", "password"))
            if lowered in SENSITIVE_KEYS or has_secret_marker:
                sanitized[str(key)] = REDACTED_VALUE
            else:
                sanitized[str(key)] = redact_sensitive(value)
        return sanitized
    if isinstance(data, list):
        return [redact_sensitive(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Emit structured JSON logs compatible with TDD.md §16.2 without leaking PII."""

    def __init__(self, environment: str) -> None:
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "severity": record.levelname,
            "service": "matching",
            "environment": self.environment,
            "request_id": request_id_ctx.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra_fields = getattr(record, "structured", None)
        if isinstance(extra_fields, dict):
            payload.update(redact_sensitive(extra_fields))
        return json.dumps(payload, default=str)


def configure_logging(environment: str, level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter(environment=environment))
    root_logger.handlers = [handler]
    root_logger.setLevel(level.upper())
