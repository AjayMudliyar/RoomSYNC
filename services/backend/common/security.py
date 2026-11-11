from __future__ import annotations

import hmac
import ipaddress
import secrets
from hashlib import sha256
from typing import Any

import redis
from django.conf import settings
from django.http import HttpRequest

from common.logging import hash_ip_address


def derive_subkey(purpose: str) -> bytes:
    """Derive a domain-separated key from JWT_SIGNING_KEY / SECRET_KEY."""
    root_secret = (
        getattr(settings, "JWT_SIGNING_KEY", "") or getattr(settings, "SECRET_KEY", "")
    ).encode("utf-8")
    return hmac.new(root_secret, f"roomsync:{purpose}".encode(), sha256).digest()


def hmac_token(purpose: str, raw_value: str) -> str:
    """Compute a constant-length HMAC-SHA256 hex digest for opaque tokens and identifiers."""
    return hmac.new(derive_subkey(purpose), raw_value.encode("utf-8"), sha256).hexdigest()


def generate_opaque_token(prefix: str, nbytes: int = 32) -> str:
    """Mint a cryptographically random URL-safe opaque token with recognizable prefix."""
    return f"{prefix}_{secrets.token_urlsafe(nbytes)}"


def extract_client_ip(request: HttpRequest) -> str:
    """Extract client IP respecting TRUSTED_PROXY_COUNT (0 ignores X-Forwarded-For)."""
    trusted_proxies = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0))
    remote_addr = str(request.META.get("REMOTE_ADDR", "") or "").strip()

    if trusted_proxies > 0:
        xff_raw = str(request.META.get("HTTP_X_FORWARDED_FOR", "") or "")
        parts = [part.strip() for part in xff_raw.split(",") if part.strip()]
        if len(parts) >= trusted_proxies:
            candidate = parts[-trusted_proxies]
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass

    if remote_addr:
        try:
            return str(ipaddress.ip_address(remote_addr))
        except ValueError:
            return remote_addr
    return "0.0.0.0"


def get_client_ip_hash(request: HttpRequest) -> str:
    """Hash extracted client IP for rate-limit keys and non-PII security audit logs."""
    root_secret = getattr(settings, "JWT_SIGNING_KEY", "") or getattr(settings, "SECRET_KEY", "")
    return hash_ip_address(extract_client_ip(request), secret_key=root_secret)


def get_redis_client() -> redis.Redis[Any]:
    """Return a short-timeout Redis client bound to REDIS_URL."""
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1.5,
        socket_timeout=1.5,
    )

