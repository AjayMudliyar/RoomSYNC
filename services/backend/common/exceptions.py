from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.defaults import page_not_found, server_error
from rest_framework import exceptions, status
from rest_framework.response import Response

from common.logging import actor_id_ctx, request_id_ctx

logger = logging.getLogger("backend.security")


class RoomSyncAPIException(exceptions.APIException):
    """Base API exception preserving an explicit RoomSync canonical error code."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code = "HTTP_ERROR"
    default_detail = "Request failed."
    error_code = "HTTP_ERROR"
    extra_details: dict[str, Any]

    def __init__(
        self,
        detail: str | None = None,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.extra_details = dict(details or {})
        super().__init__(detail=detail or self.default_detail, code=self.error_code)


class AuthInvalidCredentialsError(exceptions.AuthenticationFailed):
    default_detail = "Invalid authentication credentials."
    default_code = "AUTH_INVALID_CREDENTIALS"


class RefreshReuseDetectedError(exceptions.AuthenticationFailed):
    default_detail = "Refresh token reuse detected. Session family revoked."
    default_code = "AUTH_REFRESH_REUSE_DETECTED"


class SessionRevocationUnavailableError(RoomSyncAPIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    default_detail = "Authentication session verification is temporarily unavailable."


class AccountSuspendedError(RoomSyncAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "ACCOUNT_SUSPENDED"
    default_detail = "This account is suspended."


class AccountDeletionRequestedError(RoomSyncAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "ACCOUNT_DELETION_REQUESTED"
    default_detail = "Account deletion has been requested for this account."


class EmailVerificationRequiredError(RoomSyncAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "EMAIL_VERIFICATION_REQUIRED"
    default_detail = "Email verification is required before performing this action."


class StateConflictError(RoomSyncAPIException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "STATE_CONFLICT"
    default_detail = "The requested operation conflicts with existing state."


class OAuthLinkConfirmationRequiredError(RoomSyncAPIException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "OAUTH_LINK_CONFIRMATION_REQUIRED"
    default_detail = (
        "An account with this email already exists. "
        "Confirm account ownership to link Google sign-in."
    )


class RetryThrottledError(exceptions.Throttled):
    default_detail = "Too many attempts. Please try again later."
    default_code = "RATE_LIMITED"


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
    if isinstance(exc, RoomSyncAPIException):
        return exc.error_code
    if isinstance(exc, RefreshReuseDetectedError):
        return "AUTH_REFRESH_REUSE_DETECTED"
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


def _resolve_request_id(request: Any) -> str:
    meta = getattr(request, "META", {}) if request is not None else {}
    raw_req_id = meta.get("HTTP_X_REQUEST_ID") if isinstance(meta, dict) else None
    return str(raw_req_id) if raw_req_id else request_id_ctx.get()


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Wrap DRF/HTTP errors in the canonical RoomSync error envelope (API_CONVENTIONS.md §4.3)."""
    from rest_framework.views import exception_handler as drf_exception_handler

    request = context.get("request")
    request_id = _resolve_request_id(request)

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
            retry_after = max(1, int(wait_seconds))
            details["retry_after_seconds"] = retry_after
            response["Retry-After"] = str(retry_after)
    elif isinstance(exc, RoomSyncAPIException):
        details = dict(exc.extra_details)
        message = str(exc.detail)
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


def csrf_failure_view(request: HttpRequest, reason: str = "") -> JsonResponse:
    """Emit canonical JSON CSRF error envelope (403 CSRF_FAILED) without internal leakage."""
    request_id = _resolve_request_id(request)
    logger.warning(
        "CSRF verification failed",
        extra={
            "structured": {
                "route": request.path,
                "method": request.method,
                "actor_id": actor_id_ctx.get(),
                "reason_code": "csrf_rejected",
            }
        },
    )
    del reason  # Never reflect raw CSRF reason strings to clients.
    return JsonResponse(
        {
            "error": {
                "code": "CSRF_FAILED",
                "message": "CSRF verification failed.",
                "field_errors": {},
                "details": {},
                "request_id": request_id,
            }
        },
        status=403,
        headers={"X-Request-ID": request_id},
    )


def json_not_found_view(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Return canonical JSON 404 envelope when APPEND_SLASH is disabled or /api/ URL misses."""
    if not request.path.startswith("/api/"):
        return page_not_found(request, exception or Exception("Not Found"))
    request_id = _resolve_request_id(request)
    return JsonResponse(
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
                "field_errors": {},
                "details": {},
                "request_id": request_id,
            }
        },
        status=404,
        headers={"X-Request-ID": request_id},
    )


def json_server_error_view(request: HttpRequest) -> HttpResponse:
    """Return canonical JSON 500 envelope without exposing server internals."""
    if not request.path.startswith("/api/"):
        return server_error(request)
    request_id = _resolve_request_id(request)
    return JsonResponse(
        {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal error occurred.",
                "field_errors": {},
                "details": {},
                "request_id": request_id,
            }
        },
        status=500,
        headers={"X-Request-ID": request_id},
    )
