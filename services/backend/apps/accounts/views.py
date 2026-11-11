from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import AuthenticatedSessionContext, RoomSyncJWTAuthentication
from apps.accounts.models import OAuthIdentity, RefreshSession, User
from apps.accounts.serializers import (
    AuthSessionEnvelopeSchema,
    AuthUserEnvelopeSchema,
    CsrfEnvelopeSchema,
    DataExportEnvelopeSchema,
    DeletionRequestEnvelopeSchema,
    DeletionRequestSerializer,
    EmailResendRequestSerializer,
    EmailVerifyEnvelopeSchema,
    EmailVerifyRequestSerializer,
    GenericAcceptedEnvelopeSchema,
    GoogleAuthRequestSerializer,
    GoogleLinkRequestSerializer,
    LoginRequestSerializer,
    LogoutEnvelopeSchema,
    LogoutRequestSerializer,
    MeUpdateRequestSerializer,
    PasswordChangeEnvelopeSchema,
    PasswordChangeRequestSerializer,
    PasswordForgotRequestSerializer,
    PasswordResetEnvelopeSchema,
    PasswordResetRequestSerializer,
    RefreshRequestSerializer,
    RegisterRequestSerializer,
    UserSessionListEnvelopeSerializer,
)
from apps.accounts.services.email_tokens import resend_verification_email, verify_email_token
from apps.accounts.services.google_oauth import authenticate_with_google, confirm_google_link
from apps.accounts.services.jwt_tokens import AccessTokenClaims, decode_expired_access_token
from apps.accounts.services.lifecycle import build_user_data_export, request_account_deletion
from apps.accounts.services.passwords import (
    change_user_password,
    confirm_password_reset,
    login_with_email_password,
    register_with_email_password,
    request_password_reset,
)
from apps.accounts.services.rate_limit import enforce_ip_rate_limit
from apps.accounts.services.sessions import (
    IssuedSessionPair,
    revoke_session_family,
    rotate_refresh_session,
)
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import AuthInvalidCredentialsError
from common.logging import request_id_ctx
from common.security import hmac_token


def _resolve_request_id(request: Request | HttpRequest) -> str:
    raw = request.META.get("HTTP_X_REQUEST_ID")
    return str(raw) if raw else request_id_ctx.get()


def _resolve_client_platform(request: Request) -> str:
    raw = str(request.headers.get("X-Client-Platform", "") or "").strip().lower()
    if not raw:
        return RefreshSession.ClientPlatform.WEB
    if raw not in {RefreshSession.ClientPlatform.WEB, RefreshSession.ClientPlatform.ANDROID}:
        raise drf_exceptions.ValidationError(
            {"client_platform": ["X-Client-Platform must be 'web' or 'android'."]}
        )
    return raw


def _serialize_user(user: User) -> dict[str, Any]:
    linked_providers = sorted(
        OAuthIdentity.objects.filter(user=user).values_list("provider", flat=True)
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "phone_e164": user.phone_e164,
        "status": user.status,
        "email_verified": user.email_verified_at is not None,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "phone_verified_at": user.phone_verified_at.isoformat() if user.phone_verified_at else None,
        "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
        "deletion_requested_at": (
            user.deletion_requested_at.isoformat() if user.deletion_requested_at else None
        ),
        "has_usable_password": user.has_usable_password(),
        "linked_providers": linked_providers,
        "capabilities": {
            "can_seek_room": user.can_seek_room,
            "can_offer_room": user.can_offer_room,
            "can_list_property": user.can_list_property,
        },
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _set_auth_cookies(
    *,
    request: HttpRequest,
    response: Response,
    issued: IssuedSessionPair,
) -> None:
    rotate_token(request)
    refresh_ttl_seconds = int(getattr(settings, "REFRESH_TOKEN_TTL_DAYS", 14)) * 86400
    cookie_secure = bool(getattr(settings, "SESSION_COOKIE_SECURE", False))
    samesite = str(getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"))

    response.set_cookie(
        key=settings.AUTH_ACCESS_COOKIE_NAME,
        value=issued.access_token,
        max_age=issued.expires_in_seconds,
        httponly=True,
        secure=cookie_secure,
        samesite=samesite,  # type: ignore[arg-type]
        path=settings.AUTH_ACCESS_COOKIE_PATH,
    )
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=issued.refresh_token,
        max_age=refresh_ttl_seconds,
        httponly=True,
        secure=cookie_secure,
        samesite=samesite,  # type: ignore[arg-type]
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    samesite = str(getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"))
    response.delete_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        path=settings.AUTH_ACCESS_COOKIE_PATH,
        samesite=samesite,  # type: ignore[arg-type]
    )
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=samesite,  # type: ignore[arg-type]
    )


def _build_auth_session_response(
    *,
    request: Request,
    user: User,
    issued: IssuedSessionPair,
    client_platform: str,
    http_status: int = status.HTTP_200_OK,
) -> Response:
    data: dict[str, Any] = {
        "user": _serialize_user(user),
        "platform": client_platform,
        "session_id": str(issued.session.id),
        "expires_in_seconds": issued.expires_in_seconds,
    }
    if client_platform == RefreshSession.ClientPlatform.ANDROID:
        data["tokens"] = {
            "access_token": issued.access_token,
            "refresh_token": issued.refresh_token,
            "token_type": "Bearer",
            "expires_in_seconds": issued.expires_in_seconds,
        }

    response = Response(
        {"data": data, "meta": {"request_id": _resolve_request_id(request)}},
        status=http_status,
    )
    if client_platform == RefreshSession.ClientPlatform.WEB:
        _set_auth_cookies(request=request._request, response=response, issued=issued)
    return response


def _envelope_response(
    request: Request,
    data: Any,
    *,
    http_status: int = status.HTTP_200_OK,
) -> Response:
    return Response(
        {"data": data, "meta": {"request_id": _resolve_request_id(request)}},
        status=http_status,
    )


class PublicAuthAPIView(APIView):
    """Public auth endpoint preserving 401 WWW-Authenticate semantics for auth errors."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get_authenticate_header(self, request: Request) -> str:
        del request
        return 'Bearer realm="roomsync-api"'


class CsrfTokenView(PublicAuthAPIView):
    """Issue a CSRF cookie and token for Web SPA unsafe requests."""

    @method_decorator(ensure_csrf_cookie)
    @extend_schema(
        operation_id="auth_csrf_retrieve",
        responses={200: CsrfEnvelopeSchema},
        tags=["Auth"],
    )
    def get(self, request: Request) -> Response:
        csrf_token = get_token(request._request)
        return _envelope_response(request, {"csrf_token": csrf_token})


class RegisterView(PublicAuthAPIView):
    """Register an email/password account (status='active', email_verified_at=None)."""

    @extend_schema(
        operation_id="auth_register_create",
        request=RegisterRequestSerializer,
        responses={201: AuthSessionEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        client_platform = _resolve_client_platform(request)
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user, issued = register_with_email_password(
            email=validated["email"],
            password=validated["password"],
            accept_terms=validated["accept_terms"],
            confirm_adult=validated["confirm_adult"],
            client_platform=client_platform,
            request=request._request,
            device_label=validated.get("device_label", ""),
        )
        return _build_auth_session_response(
            request=request,
            user=user,
            issued=issued,
            client_platform=client_platform,
            http_status=status.HTTP_201_CREATED,
        )


class LoginView(PublicAuthAPIView):
    """Authenticate an existing email/password account."""

    @extend_schema(
        operation_id="auth_login_create",
        request=LoginRequestSerializer,
        responses={200: AuthSessionEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        client_platform = _resolve_client_platform(request)
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user, issued = login_with_email_password(
            email=validated["email"],
            password=validated["password"],
            client_platform=client_platform,
            request=request._request,
            device_label=validated.get("device_label", ""),
        )
        return _build_auth_session_response(
            request=request,
            user=user,
            issued=issued,
            client_platform=client_platform,
            http_status=status.HTTP_200_OK,
        )


class GoogleAuthView(PublicAuthAPIView):
    """Verify Google ID token and sign in or create unmerged confirmation challenge."""

    @extend_schema(
        operation_id="auth_google_create",
        request=GoogleAuthRequestSerializer,
        responses={200: AuthSessionEnvelopeSchema, 201: AuthSessionEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        client_platform = _resolve_client_platform(request)
        serializer = GoogleAuthRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user, issued, created = authenticate_with_google(
            raw_id_token=validated["id_token"],
            nonce=validated["nonce"],
            accept_terms=validated.get("accept_terms"),
            confirm_adult=validated.get("confirm_adult"),
            client_platform=client_platform,
            request=request._request,
            device_label=validated.get("device_label", ""),
        )
        return _build_auth_session_response(
            request=request,
            user=user,
            issued=issued,
            client_platform=client_platform,
            http_status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class GoogleLinkView(APIView):
    """Explicitly confirm and prove account ownership before linking a Google identity."""

    permission_classes = (AllowAny,)
    authentication_classes = (RoomSyncJWTAuthentication,)

    @extend_schema(
        operation_id="auth_google_link_create",
        request=GoogleLinkRequestSerializer,
        responses={200: AuthSessionEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        client_platform = _resolve_client_platform(request)
        serializer = GoogleLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        auth_user = request.user if isinstance(request.user, User) else None
        user, issued = confirm_google_link(
            link_challenge_token=validated["link_challenge_token"],
            confirm_link=validated["confirm_link"],
            password=validated.get("password"),
            email_verification_token=validated.get("email_verification_token"),
            authenticated_user=auth_user,
            client_platform=client_platform,
            request=request._request,
            device_label=validated.get("device_label", ""),
        )
        return _build_auth_session_response(
            request=request,
            user=user,
            issued=issued,
            client_platform=client_platform,
            http_status=status.HTTP_200_OK,
        )


class RefreshView(PublicAuthAPIView):
    """Rotate refresh token atomically and detect refresh reuse across web cookies or mobile."""

    @extend_schema(
        operation_id="auth_refresh_create",
        request=RefreshRequestSerializer,
        responses={200: AuthSessionEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        raw_req = request._request
        client_platform = _resolve_client_platform(request)
        enforce_ip_rate_limit(
            raw_req,
            bucket="refresh_ip",
            max_attempts=int(getattr(settings, "RATE_LIMIT_REFRESH_IP_MAX", 20)),
            window_seconds=int(getattr(settings, "RATE_LIMIT_REFRESH_IP_WINDOW_SECONDS", 60)),
        )

        auth_header = str(raw_req.META.get("HTTP_AUTHORIZATION", "") or "").strip()
        access_cookie = raw_req.COOKIES.get(settings.AUTH_ACCESS_COOKIE_NAME)
        refresh_cookie = raw_req.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if auth_header and (access_cookie or refresh_cookie):
            raise AuthInvalidCredentialsError(
                "Conflicting cookie and Bearer authentication transports on the same request."
            )

        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        body_token = validated.get("refresh_token")

        if client_platform == RefreshSession.ClientPlatform.WEB:
            if auth_header:
                raise AuthInvalidCredentialsError(
                    "Bearer transport is invalid for web refresh requests."
                )
            if body_token:
                raise drf_exceptions.ValidationError(
                    {"refresh_token": ["Web clients must supply refresh tokens via cookie."]}
                )
            raw_refresh = str(refresh_cookie or "").strip()
            if not raw_refresh:
                raise AuthInvalidCredentialsError("Refresh cookie is missing.")
        else:
            if access_cookie or refresh_cookie:
                raise AuthInvalidCredentialsError(
                    "Cookie transport is invalid for android refresh requests."
                )
            if not body_token:
                raise drf_exceptions.ValidationError(
                    {"refresh_token": ["refresh_token is required for android clients."]}
                )
            raw_refresh = str(body_token).strip()

        issued = rotate_refresh_session(
            raw_refresh_token=raw_refresh,
            client_platform=client_platform,
            request=raw_req,
            device_label=validated.get("device_label", ""),
        )

        return _build_auth_session_response(
            request=request,
            user=issued.session.user,
            issued=issued,
            client_platform=client_platform,
            http_status=status.HTTP_200_OK,
        )


class LogoutView(PublicAuthAPIView):
    """Revoke active session family and clear cookies for Web clients."""

    @extend_schema(
        operation_id="auth_logout_create",
        request=LogoutRequestSerializer,
        responses={200: LogoutEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        raw_req = request._request
        client_platform = _resolve_client_platform(request)

        auth_header = str(raw_req.META.get("HTTP_AUTHORIZATION", "") or "").strip()
        access_cookie = raw_req.COOKIES.get(settings.AUTH_ACCESS_COOKIE_NAME)
        refresh_cookie = raw_req.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)

        has_bearer = bool(auth_header)
        has_auth_cookies = bool(access_cookie or refresh_cookie)

        if has_bearer and has_auth_cookies:
            raise AuthInvalidCredentialsError(
                "Conflicting cookie and Bearer authentication transports on the same request."
            )
        if client_platform == RefreshSession.ClientPlatform.WEB and has_bearer:
            raise AuthInvalidCredentialsError(
                "Bearer transport is invalid for web logout requests."
            )
        if client_platform == RefreshSession.ClientPlatform.ANDROID and has_auth_cookies:
            raise AuthInvalidCredentialsError(
                "Cookie transport is invalid for android logout requests."
            )

        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body_refresh = serializer.validated_data.get("refresh_token")

        if client_platform == RefreshSession.ClientPlatform.WEB and body_refresh:
            raise drf_exceptions.ValidationError(
                {"refresh_token": ["Web clients must supply refresh tokens via cookie."]}
            )

        raw_access: str | None = None
        if client_platform == RefreshSession.ClientPlatform.ANDROID and has_bearer:
            if not auth_header.startswith("Bearer "):
                raise AuthInvalidCredentialsError("Authorization header must use Bearer scheme.")
            raw_access = auth_header[len("Bearer ") :].strip()
            if not raw_access:
                raise AuthInvalidCredentialsError("Bearer token is missing.")
        elif client_platform == RefreshSession.ClientPlatform.WEB and access_cookie:
            raw_access = access_cookie.strip()
            if not raw_access:
                raise AuthInvalidCredentialsError("Access cookie is empty.")

        raw_refresh = (
            str(refresh_cookie).strip()
            if client_platform == RefreshSession.ClientPlatform.WEB and refresh_cookie
            else (str(body_refresh).strip() if body_refresh else "")
        )

        target_family_id: uuid.UUID | None = None
        actor_user_id: uuid.UUID | None = None

        auth_result = None
        expired_claims: AccessTokenClaims | None = None
        if raw_access is not None:
            try:
                auth_result = RoomSyncJWTAuthentication().authenticate(request)
            except AuthInvalidCredentialsError:
                expired_claims = decode_expired_access_token(raw_access)
                if expired_claims is None or not raw_refresh:
                    raise

        if auth_result is not None:
            user, auth_ctx = auth_result
            target_family_id = auth_ctx.family_id
            actor_user_id = user.id
        elif raw_refresh:
            token_hash = hmac_token("refresh-token", raw_refresh)
            session = RefreshSession.objects.filter(
                token_hash=token_hash,
                client_platform=client_platform,
            ).first()
            if session is not None and (
                expired_claims is None or session.user_id == expired_claims.user_id
            ):
                target_family_id = session.family_id
                actor_user_id = session.user_id

        if target_family_id is None:
            if expired_claims is not None or raw_refresh:
                raise AuthInvalidCredentialsError("Invalid authentication credentials.")
            response_unauth = Response(
                {
                    "error": {
                        "code": "AUTH_REQUIRED",
                        "message": "Authentication credentials were not provided.",
                        "field_errors": {},
                        "details": {},
                        "request_id": _resolve_request_id(request),
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
            if client_platform == RefreshSession.ClientPlatform.WEB:
                _clear_auth_cookies(response_unauth)
            return response_unauth

        revoke_session_family(family_id=target_family_id, reason="logout")
        record_security_event(
            event_type="auth.logout.success",
            outcome=SecurityAuditEvent.Outcome.SUCCESS,
            actor_user_id=actor_user_id,
            target_user_id=actor_user_id,
            client_platform=client_platform,
            request=raw_req,
            metadata={"family_id": str(target_family_id)},
        )

        response = _envelope_response(request, {"logged_out": True})
        if client_platform == RefreshSession.ClientPlatform.WEB:
            _clear_auth_cookies(response)
        return response


class EmailVerifyView(PublicAuthAPIView):
    """Consume single-use email verification token and stamp email_verified_at."""

    @extend_schema(
        operation_id="auth_email_verify_create",
        request=EmailVerifyRequestSerializer,
        responses={200: EmailVerifyEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = EmailVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = verify_email_token(
            raw_token=serializer.validated_data["token"],
            request=request._request,
        )
        assert user.email_verified_at is not None
        return _envelope_response(
            request,
            {
                "verified": True,
                "email_verified_at": user.email_verified_at.isoformat(),
            },
        )


class EmailResendView(APIView):
    """Queue verification email resend without disclosing account existence."""

    permission_classes = (AllowAny,)
    authentication_classes = (RoomSyncJWTAuthentication,)

    @extend_schema(
        operation_id="auth_email_resend_create",
        request=EmailResendRequestSerializer,
        responses={202: GenericAcceptedEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        enforce_ip_rate_limit(
            request._request,
            bucket="email_resend_ip",
            max_attempts=int(getattr(settings, "RATE_LIMIT_EMAIL_RESEND_IP_MAX", 5)),
            window_seconds=int(
                getattr(settings, "RATE_LIMIT_EMAIL_RESEND_IP_WINDOW_SECONDS", 600)
            ),
        )
        serializer = EmailResendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_user = request.user if isinstance(request.user, User) else None
        email = serializer.validated_data.get("email")
        if auth_user is None and not email:
            raise drf_exceptions.ValidationError(
                {"email": ["Provide an email address or authenticate first."]}
            )

        resend_verification_email(
            request=request._request,
            authenticated_user=auth_user,
            email=email,
        )
        return _envelope_response(
            request,
            {
                "accepted": True,
                "message": "If the account is eligible for verification, an email has been sent.",
            },
            http_status=status.HTTP_202_ACCEPTED,
        )


class PasswordForgotView(PublicAuthAPIView):
    """Issue password reset token asynchronously without revealing account existence."""

    @extend_schema(
        operation_id="auth_password_forgot_create",
        request=PasswordForgotRequestSerializer,
        responses={202: GenericAcceptedEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordForgotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(
            email=serializer.validated_data["email"],
            request=request._request,
        )
        return _envelope_response(
            request,
            {
                "accepted": True,
                "message": (
                    "If an eligible account exists for this email, password reset instructions "
                    "have been sent."
                ),
            },
            http_status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetView(PublicAuthAPIView):
    """Consume single-use password reset token and invalidate all active sessions."""

    @extend_schema(
        operation_id="auth_password_reset_create",
        request=PasswordResetRequestSerializer,
        responses={200: PasswordResetEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        confirm_password_reset(
            raw_token=validated["token"],
            new_password=validated["new_password"],
            request=request._request,
        )
        return _envelope_response(request, {"password_reset": True})


class PasswordChangeView(APIView):
    """Change authenticated password and revoke all sibling session families."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="auth_password_change_create",
        request=PasswordChangeRequestSerializer,
        responses={200: PasswordChangeEnvelopeSchema},
        tags=["Auth"],
    )
    def post(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        assert isinstance(request.auth, AuthenticatedSessionContext)
        serializer = PasswordChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        change_user_password(
            user=request.user,
            current_password=validated.get("current_password"),
            new_password=validated["new_password"],
            current_family_id=request.auth.family_id,
            request=request._request,
        )
        return _envelope_response(request, {"password_changed": True})


class MeView(APIView):
    """Read or update authenticated user's capability settings (server-enforced)."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="me_retrieve",
        responses={200: AuthUserEnvelopeSchema},
        tags=["Account"],
    )
    def get(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        return _envelope_response(request, _serialize_user(request.user))

    @extend_schema(
        operation_id="me_partial_update",
        request=MeUpdateRequestSerializer,
        responses={200: AuthUserEnvelopeSchema},
        tags=["Account"],
    )
    def patch(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        serializer = MeUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user = request.user
        update_fields: list[str] = []
        changed: dict[str, bool] = {}
        for field in ("can_seek_room", "can_offer_room", "can_list_property"):
            if field in validated:
                new_val = bool(validated[field])
                if getattr(user, field) != new_val:
                    setattr(user, field, new_val)
                    update_fields.append(field)
                    changed[field] = new_val

        if update_fields:
            update_fields.append("updated_at")
            user.save(update_fields=update_fields)
            record_security_event(
                event_type="account.capabilities_updated",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=user.id,
                target_user_id=user.id,
                request=request._request,
                metadata={"changed": changed},
            )

        return _envelope_response(request, _serialize_user(user))


class MeSessionsView(APIView):
    """List current user's active session families."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="me_sessions_list",
        responses={200: UserSessionListEnvelopeSerializer},
        tags=["Account"],
    )
    def get(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        assert isinstance(request.auth, AuthenticatedSessionContext)
        now = timezone.now()
        sessions = (
            RefreshSession.objects.filter(
                user=request.user,
                revoked_at__isnull=True,
                rotated_at__isnull=True,
                expires_at__gt=now,
                family_expires_at__gt=now,
            )
            .order_by("-last_used_at", "-created_at")
        )
        items = [
            {
                "id": str(sess.id),
                "client_platform": sess.client_platform,
                "device_label": sess.device_label,
                "created_at": sess.created_at.isoformat(),
                "last_used_at": sess.last_used_at.isoformat() if sess.last_used_at else None,
                "expires_at": sess.expires_at.isoformat(),
                "is_current": sess.family_id == request.auth.family_id,
            }
            for sess in sessions
        ]
        return _envelope_response(request, items)


class MeSessionDetailView(APIView):
    """Revoke one active session family owned strictly by the authenticated user."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="me_sessions_destroy",
        responses={204: None},
        tags=["Account"],
    )
    def delete(self, request: Request, session_id: uuid.UUID) -> Response:
        assert isinstance(request.user, User)
        assert isinstance(request.auth, AuthenticatedSessionContext)

        target_session = RefreshSession.objects.filter(
            id=session_id,
            user=request.user,
        ).first()
        if target_session is None:
            raise drf_exceptions.NotFound("Session not found.")

        revoke_session_family(family_id=target_session.family_id, reason="user_revoked")
        record_security_event(
            event_type="account.session.revoked",
            outcome=SecurityAuditEvent.Outcome.SUCCESS,
            actor_user_id=request.user.id,
            target_user_id=request.user.id,
            request=request._request,
            metadata={"revoked_family_id": str(target_session.family_id)},
        )

        response = Response(
            status=status.HTTP_204_NO_CONTENT,
            headers={"X-Request-ID": _resolve_request_id(request)},
        )
        if (
            request.auth.client_platform == RefreshSession.ClientPlatform.WEB
            and target_session.family_id == request.auth.family_id
        ):
            _clear_auth_cookies(response)
        return response


class MeDeletionRequestView(APIView):
    """Request DPDP account deletion requiring explicit phrase confirmation and reauth."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="me_deletion_request_create",
        request=DeletionRequestSerializer,
        responses={202: DeletionRequestEnvelopeSchema},
        tags=["Account"],
    )
    def post(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        assert isinstance(request.auth, AuthenticatedSessionContext)
        serializer = DeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        requested_at = request_account_deletion(
            user=request.user,
            confirmation_text=validated["confirmation_text"],
            password=validated.get("password"),
            google_id_token=validated.get("google_id_token"),
            nonce=validated.get("nonce"),
            confirm_recent_reauth=bool(validated.get("confirm_recent_reauth", False)),
            session_auth_time=request.auth.auth_time,
            request=request._request,
        )

        response = _envelope_response(
            request,
            {
                "deletion_requested": True,
                "deletion_requested_at": requested_at.isoformat(),
            },
            http_status=status.HTTP_202_ACCEPTED,
        )
        if request.auth.client_platform == RefreshSession.ClientPlatform.WEB:
            _clear_auth_cookies(response)
        return response


class MeDataExportView(APIView):
    """Export current user's non-secret account, identity, session, and security records."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="me_data_export_retrieve",
        responses={200: DataExportEnvelopeSchema},
        tags=["Account"],
    )
    def get(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        payload = build_user_data_export(user=request.user, request=request._request)
        return _envelope_response(request, payload)
