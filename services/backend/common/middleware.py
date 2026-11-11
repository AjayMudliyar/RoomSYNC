from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware

from common.logging import actor_id_ctx, request_id_ctx

logger = logging.getLogger("backend.http")

_API_AUTH_COOKIES = ("rs_access", "rs_refresh", "sessionid", "csrftoken")


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
            content_type = str(response.get("Content-Type", "") or "")
            if (
                request.path.startswith("/api/")
                and response.status_code == 404
                and "application/json" not in content_type.lower()
            ):
                from common.exceptions import json_not_found_view

                response = json_not_found_view(request)
            user = getattr(request, "user", None)
            if (
                actor_id_ctx.get() == "anonymous"
                and user is not None
                and getattr(user, "is_authenticated", False)
            ):
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
            return response
        finally:
            request_id_ctx.reset(req_token)
            actor_id_ctx.reset(actor_token)


def _csrf_enforced_marker(*_args: Any, **_kwargs: Any) -> HttpResponse:
    """Non-csrf-exempt callback marker so DRF's @csrf_exempt wrapper cannot bypass Web CSRF."""
    return HttpResponse()


class RoomSyncCsrfMiddleware(CsrfViewMiddleware):
    """Enforce Django CSRF on Admin/Web cookie flows while allowing stateless mobile calls."""

    def process_view(
        self,
        request: HttpRequest,
        callback: Callable[..., Any],
        callback_args: tuple[Any, ...],
        callback_kwargs: dict[str, Any],
    ) -> HttpResponseForbidden | None:
        if request.path.startswith("/api/"):
            has_browser_cookie = any(name in request.COOKIES for name in _API_AUTH_COOKIES)
            if not has_browser_cookie:
                platform = request.headers.get("X-Client-Platform", "web").strip().lower()
                auth_header = request.headers.get("Authorization", "").strip()
                if platform == "android" or auth_header.startswith("Bearer "):
                    return None
            # DRF APIView.as_view() marks callbacks csrf_exempt=True; pass a non-exempt marker
            # so Web SPA and cookie-bearing API requests always validate Django CSRF tokens.
            return super().process_view(
                request,
                _csrf_enforced_marker,
                callback_args,
                callback_kwargs,
            )
        return super().process_view(request, callback, callback_args, callback_kwargs)
