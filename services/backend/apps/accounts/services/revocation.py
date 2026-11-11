from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import redis
from django.conf import settings
from django.utils import timezone

from common.exceptions import AuthInvalidCredentialsError, SessionRevocationUnavailableError
from common.security import get_redis_client

logger = logging.getLogger("backend.security")

_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=UTC)

_WATERMARK_MAX_LUA = """
local prev_raw = redis.call("GET", KEYS[1])
local next_raw = ARGV[1]
local chosen = next_raw
if prev_raw and ((#prev_raw > #next_raw) or (#prev_raw == #next_raw and prev_raw > next_raw)) then
    chosen = prev_raw
end
redis.call("SETEX", KEYS[1], tonumber(ARGV[2]), chosen)
return chosen
"""


def datetime_to_epoch_us(value: datetime) -> int:
    """Convert a datetime cleanly to integer UTC microseconds without float rounding."""
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    delta = aware.astimezone(UTC) - _EPOCH_UTC
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def epoch_us_to_datetime(epoch_us: int) -> datetime:
    """Convert integer UTC microseconds back to a timezone-aware UTC datetime."""
    return _EPOCH_UTC + timedelta(microseconds=epoch_us)


def _revocation_ttl_seconds() -> int:
    access_ttl = int(getattr(settings, "JWT_ACCESS_TTL_SECONDS", 900))
    return max(access_ttl + 120, 1200)


def _sid_revocation_key(session_id: uuid.UUID) -> str:
    return f"roomsync:revoked:sid:{session_id}"


def _user_revocation_key(user_id: uuid.UUID) -> str:
    return f"roomsync:revoked:user_before_us:{user_id}"


def mark_sessions_revoked(
    session_ids: Iterable[uuid.UUID],
    *,
    user_id_watermark: uuid.UUID | None = None,
    watermark_cutoff: datetime | None = None,
) -> None:
    """Publish session and microsecond user-level revocation markers to Redis."""
    sids = list(session_ids)
    if not sids and user_id_watermark is None:
        return

    ttl = _revocation_ttl_seconds()
    client: redis.Redis[Any] | None = None
    try:
        client = get_redis_client()
        if sids:
            pipe = client.pipeline()
            for sid in sids:
                pipe.setex(_sid_revocation_key(sid), ttl, "1")
            pipe.execute()
        if user_id_watermark is not None:
            cutoff_dt = watermark_cutoff if watermark_cutoff is not None else timezone.now()
            cutoff_us = max(0, datetime_to_epoch_us(cutoff_dt))
            eval_script = cast("Callable[..., Any]", client.eval)
            eval_script(
                _WATERMARK_MAX_LUA,
                1,
                _user_revocation_key(user_id_watermark),
                str(cutoff_us),
                str(ttl),
            )
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.error("Failed writing Redis session revocation markers")
        raise SessionRevocationUnavailableError() from exc
    finally:
        if client is not None:
            client.close()


def get_user_revocation_cutoff_us_fail_closed(user_id: uuid.UUID) -> int | None:
    """Read the user-level revocation cutoff in microseconds, failing closed on Redis error."""
    client: redis.Redis[Any] | None = None
    try:
        client = get_redis_client()
        raw_cutoff = client.get(_user_revocation_key(user_id))
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis unavailable reading user revocation cutoff; failing closed")
        raise SessionRevocationUnavailableError() from exc
    finally:
        if client is not None:
            client.close()

    if raw_cutoff is None:
        return None
    try:
        return int(raw_cutoff)
    except (TypeError, ValueError) as exc:
        raise SessionRevocationUnavailableError() from exc


def assert_session_not_revoked_fail_closed(
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int | None:
    """Verify sid is not revoked in Redis and return user microsecond cutoff fail-closed."""
    client: redis.Redis[Any] | None = None
    try:
        client = get_redis_client()
        sid_revoked, user_before = client.mget(
            [_sid_revocation_key(session_id), _user_revocation_key(user_id)]
        )
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis unavailable during session revocation check; failing closed")
        raise SessionRevocationUnavailableError() from exc
    finally:
        if client is not None:
            client.close()

    if sid_revoked is not None:
        raise AuthInvalidCredentialsError("Session has been revoked.")

    if user_before is None:
        return None
    try:
        return int(user_before)
    except (TypeError, ValueError) as exc:
        raise SessionRevocationUnavailableError() from exc


def assert_session_created_after_user_watermark(
    *,
    session_created_at: datetime,
    user_before_us: int | None,
) -> None:
    """Reject sessions created at or before the microsecond user revocation cutoff."""
    if user_before_us is not None and datetime_to_epoch_us(session_created_at) <= user_before_us:
        raise AuthInvalidCredentialsError("Session has been invalidated.")

