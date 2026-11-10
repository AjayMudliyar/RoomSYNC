from __future__ import annotations

from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.logging import request_id_ctx


def _normalize_field_errors(data: Any) -> dict[str, list[str]]:
    if isinstance(data, dict):
        normalized: dict[str, list[str]] = {}
        for key, value in data.items():
            if key == "detail":
                continue
            if isinstance(value, list):
                normalized[str(key)] = [str(item) for item in value]
            elif isinstance(value, dict):
                nested = _normalize_field_errors(value)
                for nested_key, nested_val in nested.items():
                    normalized[f"{key}.{nested_key}"] = nested_val
            else:
                normalized[str(key)] = [str(value)]
        return normalized
    if isinstance(data, list):
        return {"non_field_errors": [str(item) for item in data]}
    return {}


def _map_error_code(exc: Exception, status_code: int) -> str:
    if isinstance(exc, exceptions.ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, exceptions.AuthenticationFailed):
        return "AUTH_INVALID_CREDENTIALS"
    if isinstance(exc, exceptions.NotAuthenticated):
        return "AUTH_REQUIRED"
    if isinstance(exc, exceptions.PermissionDenied):
        return "PERMISSION_DENIED"
    if isinstance(exc, exceptions.Throttled):
        return "RATE_LIMITED"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "NOT_FOUND"
    if status_code == status.HTTP_409_CONFLICT:
        return "STATE_CONFLICT"
    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return "SERVICE_UNAVAILABLE"
    if status_code >= 500:
        return "INTERNAL_ERROR"
    return "HTTP_ERROR"


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Wrap DRF/HTTP errors in the canonical RoomSync error envelope (API_CONVENTIONS.md §4.3)."""
    request = context.get("request")
    meta = getattr(request, "META", {}) if request is not None else {}
    raw_req_id = meta.get("HTTP_X_REQUEST_ID") if isinstance(meta, dict) else None
    request_id = str(raw_req_id) if raw_req_id else request_id_ctx.get()

    response = drf_exception_handler(exc, context)
    if response is None:
        return Response(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected internal error occurred.",
                    "field_errors": {},
                    "details": {},
                    "request_id": request_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={"X-Request-ID": request_id},
        )

    code = _map_error_code(exc, response.status_code)
    field_errors: dict[str, list[str]] = {}
    details: dict[str, Any] = {}
    message = "Request failed."

    if isinstance(exc, exceptions.ValidationError):
        field_errors = _normalize_field_errors(response.data)
        message = "One or more fields are invalid."
    elif isinstance(exc, exceptions.Throttled):
        message = "Too many attempts. Please try again later."
        wait_seconds = getattr(exc, "wait", None)
        if isinstance(wait_seconds, int | float):
            details["retry_after_seconds"] = int(wait_seconds)
    elif isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])
    elif response.status_text:
        message = response.status_text

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors,
            "details": details,
            "request_id": request_id,
        }
    }
    response["X-Request-ID"] = request_id
    return response

