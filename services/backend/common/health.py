from __future__ import annotations

import logging
from typing import Any

import redis
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger("backend.health")


def health_live(_request: HttpRequest) -> JsonResponse:
    """Liveness probe checking only that the Django process is responsive."""
    return JsonResponse({"status": "ok"}, status=200)


def health_ready(_request: HttpRequest) -> JsonResponse:
    """Readiness probe verifying PostgreSQL and Redis connectivity without exposing secrets."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.warning("Readiness check failed: database unreachable")
        return JsonResponse({"status": "unavailable"}, status=503)

    client: redis.Redis[Any] | None = None
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
        )
        if not bool(client.ping()):
            logger.warning("Readiness check failed: redis ping returned falsy")
            return JsonResponse({"status": "unavailable"}, status=503)
    except Exception:
        logger.warning("Readiness check failed: redis unreachable")
        return JsonResponse({"status": "unavailable"}, status=503)
    finally:
        if client is not None:
            client.close()

    return JsonResponse({"status": "ok"}, status=200)
