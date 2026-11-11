from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.conf import settings
from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from apps.accounts.models import RefreshSession, User
from apps.accounts.services.jwt_tokens import AccessTokenClaims, decode_access_token
from apps.accounts.services.revocation import (
    assert_session_created_after_user_watermark,
    assert_session_not_revoked_fail_closed,
)
from common.exceptions import (
    AccountDeletionRequestedError,
    AccountSuspendedError,
    AuthInvalidCredentialsError,
)
from common.logging import actor_id_ctx

logger = logging.getLogger("backend.security")


@dataclass(frozen=True, slots=True)
class AuthenticatedSessionContext:
    """Verified runtime authentication context attached to DRF request.auth."""

    session_id: uuid.UUID
    family_id: uuid.UUID
    client_platform: str
    claims: AccessTokenClaims
    auth_time: datetime


def resolve_requested_platform(request: Request | Any, *, default: str = "web") -> str:
    """Extract X-Client-Platform header cleanly or raise validation-style failure."""
    headers = getattr(request, "headers", {})
    raw = str(headers.get("X-Client-Platform", default) or default).strip().lower()
    if raw not in {RefreshSession.ClientPlatform.WEB, RefreshSession.ClientPlatform.ANDROID}:
        raise AuthInvalidCredentialsError("Unsupported X-Client-Platform header.")
    return raw


class RoomSyncJWTAuthentication(BaseAuthentication):
    """Dual Cookie (Web) and Bearer (Android) JWT auth with fail-closed revocation."""

    def authenticate(
        self, request: Request
    ) -> tuple[User, AuthenticatedSessionContext] | None:
        raw_request = getattr(request, "_request", request)
        auth_header = str(raw_request.META.get("HTTP_AUTHORIZATION", "") or "").strip()

        access_cookie = raw_request.COOKIES.get(settings.AUTH_ACCESS_COOKIE_NAME)
        refresh_cookie = raw_request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)

        has_bearer = bool(auth_header)
        has_auth_cookies = bool(access_cookie or refresh_cookie)

        if has_bearer and has_auth_cookies:
            raise AuthInvalidCredentialsError(
                "Conflicting cookie and Bearer authentication transports on the same request."
            )

        if not has_bearer and not access_cookie:
            return None

        raw_platform_hdr = (
            str(raw_request.headers.get("X-Client-Platform", "") or "").strip().lower()
        )

        if has_bearer:
            if not auth_header.startswith("Bearer "):
                raise AuthInvalidCredentialsError("Authorization header must use Bearer scheme.")
            raw_token = auth_header[len("Bearer ") :].strip()
            if not raw_token:
                raise AuthInvalidCredentialsError("Bearer token is missing.")
            if raw_platform_hdr == RefreshSession.ClientPlatform.WEB:
                raise AuthInvalidCredentialsError(
                    "Bearer authentication is not allowed for web client transport."
                )
            transport = RefreshSession.ClientPlatform.ANDROID
        else:
            assert access_cookie is not None
            raw_token = access_cookie.strip()
            if raw_platform_hdr == RefreshSession.ClientPlatform.ANDROID:
                raise AuthInvalidCredentialsError(
                    "Cookie authentication is not allowed for android client transport."
                )
            transport = RefreshSession.ClientPlatform.WEB

        claims = decode_access_token(raw_token)
        user_before_us = assert_session_not_revoked_fail_closed(
            session_id=claims.session_id,
            user_id=claims.user_id,
        )

        session = (
            RefreshSession.objects.select_related("user")
            .filter(id=claims.session_id, user_id=claims.user_id)
            .first()
        )
        if session is None:
            raise AuthInvalidCredentialsError("Authentication session was not found.")

        if session.client_platform != transport:
            raise AuthInvalidCredentialsError("Token transport mismatch.")

        now = timezone.now()
        if session.revoked_at is not None or session.family_expires_at <= now:
            raise AuthInvalidCredentialsError("Authentication session is revoked or expired.")

        if RefreshSession.objects.filter(
            family_id=session.family_id,
            revoked_at__isnull=False,
        ).exists():
            raise AuthInvalidCredentialsError("Authentication session family has been revoked.")

        assert_session_created_after_user_watermark(
            session_created_at=session.created_at,
            user_before_us=user_before_us,
        )

        user = session.user
        if user.deletion_requested_at is not None:
            raise AccountDeletionRequestedError()
        if user.status == User.Status.SUSPENDED or not user.is_active:
            raise AccountSuspendedError()
        if user.status == User.Status.DELETED:
            raise AuthInvalidCredentialsError("Account is inactive.")

        actor_id_ctx.set(str(user.id))
        return (
            user,
            AuthenticatedSessionContext(
                session_id=session.id,
                family_id=session.family_id,
                client_platform=transport,
                claims=claims,
                auth_time=session.auth_time,
            ),
        )

    def authenticate_header(self, request: Request) -> str:
        del request
        return 'Bearer realm="roomsync-api"'


class RoomSyncJWTAuthenticationScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    """Register Dual Cookie/Bearer schemes explicitly in OpenAPI output."""

    target_class = "apps.accounts.authentication.RoomSyncJWTAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        del auto_schema
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Android Bearer JWT or Web HttpOnly cookie session.",
        }
