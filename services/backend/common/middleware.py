from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from common.logging import actor_id_ctx, request_id_ctx

logger = logging.getLogger("backend.http")


class RequestContextMiddleware:
    """Propagate X-Request-ID and emit PII-redacted structured access logs."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw_id = request.headers.get("X-Request-ID", "").strip()
        request_id = raw_id if raw_id else str(uuid.uuid4())
        request.META["HTTP_X_REQUEST_ID"] = request_id

        req_token = request_id_ctx.set(request_id)
        actor_token = actor_id_ctx.set("anonymous")
        started = time.perf_counter()

        try:
            response = self.get_response(request)
        finally:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                actor_id_ctx.set(str(getattr(user, "pk", "authenticated")))

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response["X-Request-ID"] = request_id
        logger.info(
            "Request completed",
            extra={
                "structured": {
                    "route": request.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                }
            },
        )
        request_id_ctx.reset(req_token)
        actor_id_ctx.reset(actor_token)
        return response
