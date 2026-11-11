from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, cast

import redis
from django.conf import settings
from django.http import HttpRequest

from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import RetryThrottledError, SessionRevocationUnavailableError
from common.security import get_client_ip_hash, get_redis_client, hmac_token

logger = logging.getLogger("backend.security")

_INCR_EXPIRE_LUA = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]))
end
local ttl = redis.call("TTL", KEYS[1])
if ttl < 0 then
    redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]))
    ttl = tonumber(ARGV[1])
end
return {current, ttl}
"""


def _increment_counter(key: str, window_seconds: int) -> tuple[int, int]:
    client: redis.Redis[Any] | None = None
    try:
        client = get_redis_client()
        eval_script = cast("Callable[..., Any]", client.eval)
        result = eval_script(_INCR_EXPIRE_LUA, 1, key, str(window_seconds))
        assert isinstance(result, list) and len(result) == 2
        return int(result[0]), max(1, int(result[1]))
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis unavailable during rate limit update")
        raise SessionRevocationUnavailableError() from exc
    finally:
        if client is not None:
            client.close()


def _audit_rate_limit(request: HttpRequest, bucket: str, wait_seconds: int) -> None:
    record_security_event(
        event_type="security.rate_limited",
        outcome=SecurityAuditEvent.Outcome.BLOCKED,
        request=request,
        metadata={"bucket": bucket, "retry_after_seconds": wait_seconds},
    )


def enforce_ip_rate_limit(
    request: HttpRequest,
    *,
    bucket: str,
    max_attempts: int,
    window_seconds: int,
) -> None:
    """Enforce a fixed-window IP rate limit keyed by hashed client IP."""
    ip_hash = get_client_ip_hash(request)
    key = f"roomsync:rl:{bucket}:{ip_hash}"
    count, ttl = _increment_counter(key, window_seconds)
    if count > max_attempts:
        _audit_rate_limit(request, bucket, ttl)
        raise RetryThrottledError(wait=ttl)


def assert_login_rate_limits_allowed(
    request: HttpRequest,
    *,
    normalized_email: str,
) -> None:
    """Check both per-IP login request limit and (email_hmac, IP) failed login lockout."""
    ip_hash = get_client_ip_hash(request)
    email_hmac = hmac_token("rl-email", normalized_email)

    ip_max = int(getattr(settings, "RATE_LIMIT_LOGIN_IP_MAX", 20))
    ip_window = int(getattr(settings, "RATE_LIMIT_LOGIN_IP_WINDOW_SECONDS", 600))
    acct_max = int(getattr(settings, "RATE_LIMIT_LOGIN_ACCOUNT_MAX", 5))

    client: redis.Redis[Any] | None = None
    fail_key = f"roomsync:rl:login_fail:{email_hmac}:{ip_hash}"
    try:
        client = get_redis_client()
        pipe = client.pipeline()
        pipe.get(fail_key)
        pipe.ttl(fail_key)
        raw_count, raw_ttl = pipe.execute()
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis unavailable checking login lockout")
        raise SessionRevocationUnavailableError() from exc
    finally:
        if client is not None:
            client.close()

    if raw_count is not None and int(raw_count) >= acct_max:
        wait = max(1, int(raw_ttl)) if isinstance(raw_ttl, int) and raw_ttl > 0 else 600
        _audit_rate_limit(request, "login_account", wait)
        raise RetryThrottledError(wait=wait)

    ip_key = f"roomsync:rl:login_ip:{ip_hash}"
    ip_count, ip_ttl = _increment_counter(ip_key, ip_window)
    if ip_count > ip_max:
        _audit_rate_limit(request, "login_ip", ip_ttl)
        raise RetryThrottledError(wait=ip_ttl)


def record_login_failure(request: HttpRequest, *, normalized_email: str) -> None:
    """Increment failed login counter for normalized (email_hmac, IP) pair."""
    ip_hash = get_client_ip_hash(request)
    email_hmac = hmac_token("rl-email", normalized_email)
    window = int(getattr(settings, "RATE_LIMIT_LOGIN_ACCOUNT_WINDOW_SECONDS", 600))
    fail_key = f"roomsync:rl:login_fail:{email_hmac}:{ip_hash}"
    _increment_counter(fail_key, window)


def clear_login_failures(request: HttpRequest, *, normalized_email: str) -> None:
    """Clear failed login counter on valid authentication."""
    ip_hash = get_client_ip_hash(request)
    email_hmac = hmac_token("rl-email", normalized_email)
    fail_key = f"roomsync:rl:login_fail:{email_hmac}:{ip_hash}"
    client: redis.Redis[Any] | None = None
    try:
        client = get_redis_client()
        client.delete(fail_key)
    except (redis.RedisError, OSError, TimeoutError):
        logger.warning("Redis unavailable clearing login failure key")
    finally:
        if client is not None:
            client.close()
