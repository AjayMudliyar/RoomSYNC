from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
actor_id_ctx: ContextVar[str] = ContextVar("actor_id", default="anonymous")

REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "token",
        "access",
        "access_token",
        "refresh",
        "refresh_token",
        "id_token",
        "csrf_token",
        "link_challenge_token",
        "secret",
        "client_secret",
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

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}")
_OPAQUE_TOKEN_RE = re.compile(r"\b(?:rsr|rsv|rsp|rsl)_[A-Za-z0-9_-]{8,}\b")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{6,}")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_KV_SECRET_RE = re.compile(
    r"(?i)\b(password|passcode|token|access_token|refresh_token|id_token|secret|otp|authorization|"
    r"cookie|set-cookie|x-csrftoken|csrf_token)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;}\]]+)"
)


def redact_text(text: str) -> str:
    """Scrub JWTs, Bearer values, prefixed tokens, key=value secrets, and emails from text."""
    cleaned = _JWT_RE.sub("[REDACTED_JWT]", text)
    cleaned = _OPAQUE_TOKEN_RE.sub("[REDACTED_TOKEN]", cleaned)
    cleaned = _BEARER_RE.sub("Bearer [REDACTED]", cleaned)
    cleaned = _KV_SECRET_RE.sub(r"\1\2[REDACTED]", cleaned)
    cleaned = _EMAIL_RE.sub("[REDACTED_EMAIL]", cleaned)
    return cleaned


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
    if isinstance(data, tuple):
        return [redact_sensitive(item) for item in data]
    if isinstance(data, str):
        return redact_text(data)
    return data


def hash_ip_address(raw_ip: str | None, *, secret_key: str) -> str:
    """Compute a stable domain-separated HMAC-SHA256 digest of a client IP address."""
    if not raw_ip:
        return ""
    try:
        canonical = str(ipaddress.ip_address(raw_ip.strip()))
    except ValueError:
        canonical = raw_ip.strip()
    key = hmac.new(secret_key.encode("utf-8"), b"roomsync:ip-hash", sha256).digest()
    return hmac.new(key, canonical.encode("utf-8"), sha256).hexdigest()


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
            "message": redact_text(record.getMessage()),
        }
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            payload.update(redact_sensitive(structured))
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)
