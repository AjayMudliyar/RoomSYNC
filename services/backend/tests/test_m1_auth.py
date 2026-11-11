
from __future__ import annotations

import importlib
import json
import logging
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import jwt
import pytest
import redis as redis_lib
from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, OperationalError, connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, override_settings
from django.utils import timezone
from google.auth import exceptions as google_auth_exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.accounts.models import (
    EmailVerificationToken,
    OAuthIdentity,
    OAuthLinkChallenge,
    PasswordResetToken,
    RefreshSession,
    User,
    normalize_email_address,
)
from apps.accounts.permissions import IsEmailVerified
from apps.accounts.services.google_oauth import (
    _is_expected_oauth_uniqueness_error,
    authenticate_with_google,
)
from apps.accounts.services.jwt_tokens import mint_access_token
from apps.accounts.services.passwords import change_user_password
from apps.accounts.services.revocation import mark_sessions_revoked as orig_mark_sessions_revoked
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import RoomSyncAPIException
from common.logging import StructuredJsonFormatter
from common.security import generate_opaque_token, get_redis_client, hmac_token
from config.settings import base as base_settings


@pytest.fixture(autouse=True)
def _clean_redis_roomsync_keys() -> Any:
    client = get_redis_client()
    try:
        keys = list(client.scan_iter("roomsync:*"))
        if keys:
            client.delete(*keys)
    finally:
        client.close()

    yield

    client = get_redis_client()
    try:
        keys = list(client.scan_iter("roomsync:*"))
        if keys:
            client.delete(*keys)
    finally:
        client.close()


def _android_client(access_token: str | None = None) -> APIClient:
    client = APIClient()
    headers: dict[str, str] = {"HTTP_X_CLIENT_PLATFORM": "android"}
    if access_token is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    client.credentials(**headers)
    return client


def _web_csrf_client() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    resp = client.get("/api/v1/auth/csrf")
    assert resp.status_code == 200
    csrf_token = str(resp.json()["data"]["csrf_token"])
    return client, csrf_token


def _register_android(
    *,
    email: str = "asha@example.com",
    password: str = "RoomSyncPass#2026!",
    device_label: str = "Pixel 9",
) -> tuple[dict[str, Any], APIClient]:
    anon = _android_client()
    resp = anon.post(
        "/api/v1/auth/register",
        {
            "email": email,
            "password": password,
            "accept_terms": True,
            "confirm_adult": True,
            "device_label": device_label,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()["data"]
    authed = _android_client(data["tokens"]["access_token"])
    return data, authed


def _extract_last_mail_token(prefix: str) -> str:
    assert mail.outbox, "Expected verification/reset email in locmem outbox"
    body = mail.outbox[-1].body
    for word in body.replace("=", " ").replace("&", " ").replace("?", " ").split():
        cleaned = word.strip(".,)\"'")
        if cleaned.startswith(f"{prefix}_"):
            return cleaned
    raise AssertionError(f"Could not find token with prefix {prefix}_ in email body")


def test_email_nfkc_normalization_and_canonicalization() -> None:
    assert normalize_email_address("  \uFF35ser＠Example.COM  ") == "user@example.com"


@pytest.mark.django_db(transaction=True)
def test_migration_0002_collision_audit_and_case_normalization() -> None:
    executor = MigrationExecutor(connection)
    executor.migrate([("accounts", "0001_initial")])
    try:
        old_apps = executor.loader.project_state([("accounts", "0001_initial")]).apps
        OldUser = old_apps.get_model("accounts", "User")
        OldUser.objects.create(email="Mixed.Case@Example.com", password="!")

        executor.loader.build_graph()
        executor.migrate([("accounts", "0002_m1_auth_lifecycle")])
        migrated_apps = executor.loader.project_state(
            [("accounts", "0002_m1_auth_lifecycle")]
        ).apps
        user_model = migrated_apps.get_model("accounts", "User")
        assert user_model.objects.filter(email="mixed.case@example.com").exists()

        executor.loader.build_graph()
        executor.migrate([("accounts", "0001_initial")])
        old_apps_2 = executor.loader.project_state([("accounts", "0001_initial")]).apps
        OldUser2 = old_apps_2.get_model("accounts", "User")
        OldUser2.objects.create(email="Alice@Example.com", password="!")
        OldUser2.objects.create(email="alice@example.com", password="!")

        executor.loader.build_graph()
        with pytest.raises(RuntimeError, match="conflicting normalized email addresses"):
            executor.migrate([("accounts", "0002_m1_auth_lifecycle")])
    finally:
        # Leave database cleanly restored to latest migrations for remaining suite tests.
        executor.loader.build_graph()
        executor.migrate([("accounts", "0001_initial")])
        old_apps_cleanup = executor.loader.project_state([("accounts", "0001_initial")]).apps
        OldUserCleanup = old_apps_cleanup.get_model("accounts", "User")
        OldUserCleanup.objects.all().delete()
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db
def test_django_admin_custom_user_forms() -> None:
    admin_user = User.objects.create_superuser(
        email="superadmin@roomsync.in",
        password="AdminStrongPass#2026!",
    )
    client = Client()
    assert client.login(username="superadmin@roomsync.in", password="AdminStrongPass#2026!")

    admin_prefix = f"/{settings.DJANGO_ADMIN_PATH.lstrip('/')}"
    add_get = client.get(f"{admin_prefix}accounts/user/add/")
    assert add_get.status_code == 200

    add_post = client.post(
        f"{admin_prefix}accounts/user/add/",
        {
            "email": "CreatedByAdmin@Example.com",
            "password1": "AdminCreatedPass#2026!",
            "password2": "AdminCreatedPass#2026!",
            "can_seek_room": "on",
        },
        follow=True,
    )
    assert add_post.status_code == 200
    created = User.objects.get(email="createdbyadmin@example.com")
    assert created.id != admin_user.id

    change_get = client.get(f"{admin_prefix}accounts/user/{created.id}/change/")
    assert change_get.status_code == 200

    dup_post = client.post(
        f"{admin_prefix}accounts/user/add/",
        {
            "email": "CREATEDBYADMIN@example.com",
            "password1": "AdminCreatedPass#2026!",
            "password2": "AdminCreatedPass#2026!",
        },
    )
    assert dup_post.status_code == 200
    assert b"already exists" in dup_post.content


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=base_settings.PASSWORD_HASHERS)
def test_argon2id_primary_hashing_pbkdf2_fallback_and_password_rules() -> None:
    anon = _android_client()
    weak_resp = anon.post(
        "/api/v1/auth/register",
        {
            "email": "weak@example.com",
            "password": "short",
            "accept_terms": True,
            "confirm_adult": True,
        },
        format="json",
    )
    assert weak_resp.status_code == 400
    assert weak_resp.json()["error"]["code"] == "VALIDATION_ERROR"

    reg_data, _ = _register_android(email="argon@example.com", password="StrongArgonPass#2026")
    user = User.objects.get(id=reg_data["user"]["id"])
    assert user.password.startswith("argon2$argon2id$")

    # Verify PBKDF2 legacy hash logs in cleanly and seamlessly re-hashes to Argon2id.
    legacy = User.objects.create_user(
        email="legacy@example.com",
        password="LegacyStrongPass#2026",
        status=User.Status.ACTIVE,
        terms_accepted_at=timezone.now(),
    )
    from django.contrib.auth.hashers import PBKDF2PasswordHasher

    legacy.password = PBKDF2PasswordHasher().encode(
        "LegacyStrongPass#2026", PBKDF2PasswordHasher().salt()
    )
    legacy.save(update_fields=["password"])
    assert legacy.password.startswith("pbkdf2_sha256$")

    login_resp = _android_client().post(
        "/api/v1/auth/login",
        {"email": "legacy@example.com", "password": "LegacyStrongPass#2026"},
        format="json",
    )
    assert login_resp.status_code == 200
    legacy.refresh_from_db()
    assert legacy.password.startswith("argon2$argon2id$")


@pytest.mark.django_db
def test_web_cookie_csrf_rotation_path_isolation_and_logout() -> None:
    client, csrf_token = _web_csrf_client()
    preauth_no_csrf = client.post(
        "/api/v1/auth/login",
        {"email": "webuser@example.com", "password": "WebStrongPass#2026!"},
        format="json",
    )
    assert preauth_no_csrf.status_code == 403
    assert preauth_no_csrf.json()["error"]["code"] == "CSRF_FAILED"

    reg = client.post(
        "/api/v1/auth/register",
        {
            "email": "webuser@example.com",
            "password": "WebStrongPass#2026!",
            "accept_terms": True,
            "confirm_adult": True,
        },
        format="json",
        headers={"X-CSRFToken": csrf_token},
    )
    assert reg.status_code == 201
    reg_body = reg.json()["data"]
    assert reg_body["platform"] == "web"
    assert "tokens" not in reg_body

    access_cookie = reg.cookies[settings.AUTH_ACCESS_COOKIE_NAME]
    refresh_cookie = reg.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert access_cookie["httponly"] is True
    assert refresh_cookie["httponly"] is True
    assert access_cookie["samesite"] == "Lax"
    assert refresh_cookie["samesite"] == "Lax"
    assert access_cookie["path"] == "/"
    assert refresh_cookie["path"] == "/api/v1/auth/"
    # rotate_token rotates csrftoken cookie on session issuance.
    new_csrf = reg.cookies["csrftoken"].value

    # Missing X-CSRFToken must fail with canonical 403 CSRF_FAILED JSON envelope.
    no_csrf = client.patch("/api/v1/me", {"can_offer_room": True}, format="json")
    assert no_csrf.status_code == 403
    assert no_csrf.json()["error"]["code"] == "CSRF_FAILED"

    ok_patch = client.patch(
        "/api/v1/me",
        {"can_offer_room": True},
        format="json",
        headers={"X-CSRFToken": new_csrf},
    )
    assert ok_patch.status_code == 200
    assert ok_patch.json()["data"]["capabilities"]["can_offer_room"] is True

    # Refresh rotates both rs_refresh and CSRF token; body refresh_token is rejected for Web.
    bad_web_refresh = client.post(
        "/api/v1/auth/refresh",
        {"refresh_token": refresh_cookie.value},
        format="json",
        headers={"X-CSRFToken": new_csrf},
    )
    assert bad_web_refresh.status_code == 400

    good_refresh = client.post(
        "/api/v1/auth/refresh",
        {},
        format="json",
        headers={"X-CSRFToken": new_csrf},
    )
    assert good_refresh.status_code == 200
    rotated_csrf = good_refresh.cookies["csrftoken"].value
    assert good_refresh.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value != refresh_cookie.value

    # Even if rs_access cookie is removed (e.g. expired access JWT), logout via rs_refresh works.
    client.cookies.pop(settings.AUTH_ACCESS_COOKIE_NAME, None)
    logout_resp = client.post(
        "/api/v1/auth/logout",
        {},
        format="json",
        headers={"X-CSRFToken": rotated_csrf},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["data"]["logged_out"] is True
    assert logout_resp.cookies[settings.AUTH_ACCESS_COOKIE_NAME].value == ""


@pytest.mark.django_db
def test_android_jwt_claims_mixed_transport_and_refresh_reuse_revocation() -> None:
    reg, authed = _register_android(email="mobile@example.com")
    access_token = str(reg["tokens"]["access_token"])
    refresh_token = str(reg["tokens"]["refresh_token"])

    decoded = jwt.decode(
        access_token,
        settings.JWT_SIGNING_KEY,
        algorithms=["HS256"],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )
    assert set(["sid", "sub", "jti", "iat", "exp", "iss", "aud"]).issubset(decoded.keys())
    assert decoded["exp"] - decoded["iat"] == 900

    # Mixed transport / platform mismatch rejections.
    mixed = APIClient()
    mixed.cookies[settings.AUTH_ACCESS_COOKIE_NAME] = access_token
    mixed.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_CLIENT_PLATFORM="android",
    )
    assert mixed.get("/api/v1/me").status_code == 401

    web_hdr_bearer = APIClient()
    web_hdr_bearer.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_CLIENT_PLATFORM="web",
    )
    assert web_hdr_bearer.get("/api/v1/me").status_code == 401

    cookie_hdr_android = APIClient()
    cookie_hdr_android.cookies[settings.AUTH_ACCESS_COOKIE_NAME] = access_token
    cookie_hdr_android.credentials(HTTP_X_CLIENT_PLATFORM="android")
    assert cookie_hdr_android.get("/api/v1/me").status_code == 401

    # Rotate cleanly once.
    rot1 = _android_client().post(
        "/api/v1/auth/refresh",
        {"refresh_token": refresh_token},
        format="json",
    )
    assert rot1.status_code == 200
    child_access = str(rot1.json()["data"]["tokens"]["access_token"])
    child_refresh = str(rot1.json()["data"]["tokens"]["refresh_token"])
    assert child_refresh != refresh_token
    assert _android_client(child_access).get("/api/v1/me").status_code == 200

    # Replay parent refresh token -> entire family revoked immediately + child access rejected.
    replay = _android_client().post(
        "/api/v1/auth/refresh",
        {"refresh_token": refresh_token},
        format="json",
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "AUTH_REFRESH_REUSE_DETECTED"
    assert _android_client(child_access).get("/api/v1/me").status_code == 401
    assert SecurityAuditEvent.objects.filter(event_type="auth.refresh.reuse_detected").exists()
    # Prevent unused fixture warning.
    assert authed is not None


@pytest.mark.django_db(transaction=True)
def test_concurrent_refresh_race_allows_one_winner_and_revokes_family() -> None:
    reg, _ = _register_android(email="race@example.com")
    refresh_token = str(reg["tokens"]["refresh_token"])
    barrier = threading.Barrier(2)

    def _call_refresh() -> tuple[int, dict[str, Any]]:
        try:
            client = _android_client()
            barrier.wait(timeout=5)
            resp = client.post(
                "/api/v1/auth/refresh",
                {"refresh_token": refresh_token},
                format="json",
            )
            return resp.status_code, resp.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_call_refresh)
        f2 = pool.submit(_call_refresh)
        res1 = f1.result(timeout=10)
        res2 = f2.result(timeout=10)

    statuses = sorted([res1[0], res2[0]])
    assert statuses == [200, 401]
    winner_body = res1[1] if res1[0] == 200 else res2[1]
    loser_body = res1[1] if res1[0] == 401 else res2[1]
    assert loser_body["error"]["code"] == "AUTH_REFRESH_REUSE_DETECTED"

    # Family revocation triggered by the racing loser also invalidates the winner's new tokens.
    winner_access = str(winner_body["data"]["tokens"]["access_token"])
    assert _android_client(winner_access).get("/api/v1/me").status_code == 401


@pytest.mark.django_db
def test_fail_closed_redis_outage_rejects_authenticated_requests() -> None:
    _, authed = _register_android(email="redisdown@example.com")
    with patch(
        "apps.accounts.services.revocation.get_redis_client",
        side_effect=redis_lib.ConnectionError("redis down"),
    ):
        resp = authed.get("/api/v1/me")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.django_db(transaction=True)
def test_google_oauth_validation_signup_verified_collision_and_unverified_prehijack_link() -> None:
    # 1. Invalid token/claims rejected.
    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        side_effect=google_auth_exceptions.GoogleAuthError("bad sig"),  # type: ignore[no-untyped-call]
    ):
        bad = _android_client().post(
            "/api/v1/auth/google",
            {
                "id_token": "x" * 32,
                "nonce": "n" * 24,
                "accept_terms": True,
                "confirm_adult": True,
            },
            format="json",
        )
        assert bad.status_code == 401

    aud = settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID
    bad_claims = [
        {
            "iss": "https://evil.example",
            "aud": aud,
            "email_verified": True,
            "sub": "g1",
            "email": "g@example.com",
            "nonce": "n" * 24,
            "exp": 9999999999,
        },
        {
            "iss": "https://accounts.google.com",
            "aud": "wrong-client-id",
            "email_verified": True,
            "sub": "g1",
            "email": "g@example.com",
            "nonce": "n" * 24,
            "exp": 9999999999,
        },
        {
            "iss": "https://accounts.google.com",
            "aud": aud,
            "email_verified": False,
            "sub": "g1",
            "email": "g@example.com",
            "nonce": "n" * 24,
            "exp": 9999999999,
        },
        {
            "iss": "https://accounts.google.com",
            "aud": aud,
            "email_verified": True,
            "sub": "g1",
            "email": "g@example.com",
            "nonce": "wrong-nonce",
            "exp": 9999999999,
        },
    ]
    for payload in bad_claims:
        with patch(
            "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
            return_value=payload,
        ):
            r = _android_client().post(
                "/api/v1/auth/google",
                {
                    "id_token": "tok_" + uuid.uuid4().hex,
                    "nonce": "n" * 24,
                    "accept_terms": True,
                    "confirm_adult": True,
                },
                format="json",
            )
            assert r.status_code == 401

    # 2. Valid new signup + replay check.
    future_exp = int((timezone.now() + timedelta(minutes=10)).timestamp())
    valid_token = "google_id_token_unique_12345"
    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID,
            "email_verified": True,
            "sub": "google-sub-1",
            "email": "NewGoogle@Example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        },
    ):
        missing_consent = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_consent_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
        assert missing_consent.status_code == 400

        created = _android_client().post(
            "/api/v1/auth/google",
            {
                "id_token": valid_token,
                "nonce": "n" * 24,
                "accept_terms": True,
                "confirm_adult": True,
            },
            format="json",
        )
        assert created.status_code == 201
        assert created.json()["data"]["user"]["email_verified"] is True
        assert created.json()["data"]["user"]["has_usable_password"] is False

        # Replaying same raw id_token is blocked by Redis replay slot.
        replay = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": valid_token, "nonce": "n" * 24},
            format="json",
        )
        assert replay.status_code == 401

    # 3. Verified password collision -> 409 OAUTH_LINK_CONFIRMATION_REQUIRED (never auto-merged).
    _register_android(email="verified-collision@example.com", password="OwnerPassword#2026")
    ev_token = _extract_last_mail_token("rsv")
    ev_resp = _android_client().post(
        "/api/v1/auth/email/verify", {"token": ev_token}, format="json"
    )
    assert ev_resp.status_code == 200

    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID,
            "email_verified": True,
            "sub": "google-sub-2",
            "email": "verified-collision@example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        },
    ):
        collision = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_verified_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "OAUTH_LINK_CONFIRMATION_REQUIRED"
    challenge_token = str(collision.json()["error"]["details"]["link_challenge_token"])
    assert not OAuthIdentity.objects.filter(provider_sub="google-sub-2").exists()

    # Wrong password rejected (403); valid password links Google identity cleanly.
    bad_link = _android_client().post(
        "/api/v1/auth/google/link",
        {
            "link_challenge_token": challenge_token,
            "confirm_link": True,
            "password": "WrongPassword123!",
        },
        format="json",
    )
    assert bad_link.status_code == 403

    good_link = _android_client().post(
        "/api/v1/auth/google/link",
        {
            "link_challenge_token": challenge_token,
            "confirm_link": True,
            "password": "OwnerPassword#2026",
        },
        format="json",
    )
    assert good_link.status_code == 200
    assert OAuthIdentity.objects.filter(provider_sub="google-sub-2").exists()

    # 4. Unverified pre-hijack collision -> email proof scrubs attacker's password & sessions.
    attacker_reg, attacker_client = _register_android(
        email="victim@example.com",
        password="AttackerPreHijack#2026",
    )
    victim_verify_token = _extract_last_mail_token("rsv")
    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID,
            "email_verified": True,
            "sub": "google-sub-victim",
            "email": "victim@example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        },
    ):
        victim_collision = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_victim_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
    assert victim_collision.status_code == 409
    victim_challenge = str(victim_collision.json()["error"]["details"]["link_challenge_token"])

    # Attacker's unverified Bearer session alone cannot prove mailbox ownership.
    unauth_link = attacker_client.post(
        "/api/v1/auth/google/link",
        {"link_challenge_token": victim_challenge, "confirm_link": True},
        format="json",
    )
    assert unauth_link.status_code == 403

    # Victim links using mailbox verification token -> attacker password scrubbed & session revoked!
    victim_link = _android_client().post(
        "/api/v1/auth/google/link",
        {
            "link_challenge_token": victim_challenge,
            "confirm_link": True,
            "email_verification_token": victim_verify_token,
        },
        format="json",
    )
    assert victim_link.status_code == 200
    victim_access = str(victim_link.json()["data"]["tokens"]["access_token"])
    victim_refresh = str(victim_link.json()["data"]["tokens"]["refresh_token"])
    victim_user = User.objects.get(id=attacker_reg["user"]["id"])
    assert not victim_user.has_usable_password()
    assert attacker_client.get("/api/v1/me").status_code == 401
    assert (
        _android_client()
        .post(
            "/api/v1/auth/refresh",
            {"refresh_token": str(attacker_reg["tokens"]["refresh_token"])},
            format="json",
        )
        .status_code
        == 401
    )
    assert _android_client(victim_access).get("/api/v1/me").status_code == 200
    assert (
        _android_client()
        .post("/api/v1/auth/refresh", {"refresh_token": victim_refresh}, format="json")
        .status_code
        == 200
    )


@pytest.mark.django_db(transaction=True)
def test_email_verification_resend_anti_enumeration_and_permission_guard() -> None:
    mail.outbox.clear()
    reg, authed = _register_android(email="verifyme@example.com")
    assert reg["user"]["email_verified"] is False
    token_1 = _extract_last_mail_token("rsv")

    class VerifiedOnlyDummyView(APIView):
        permission_classes = (IsAuthenticated, IsEmailVerified)

        def get(self, request: Request) -> Response:
            del request
            return Response({"ok": True})

    # Verify IsEmailVerified permission blocks unverified account with EMAIL_VERIFICATION_REQUIRED.
    raw_req = APIClient().get("/").wsgi_request
    user_obj = User.objects.get(id=reg["user"]["id"])
    perm = IsEmailVerified()
    from rest_framework.request import Request as DrfRequest

    drf_req = DrfRequest(raw_req)
    drf_req.user = user_obj
    with pytest.raises(Exception) as exc_info:
        perm.has_permission(drf_req, VerifiedOnlyDummyView())
    assert getattr(exc_info.value, "error_code", None) == "EMAIL_VERIFICATION_REQUIRED"

    # Anti-enumeration resend returns identical 202 for nonexistent and existing unverified emails.
    anon = _android_client()
    r_missing = anon.post(
        "/api/v1/auth/email/resend", {"email": "nobody@example.com"}, format="json"
    )
    r_existing = anon.post(
        "/api/v1/auth/email/resend", {"email": "verifyme@example.com"}, format="json"
    )
    assert r_missing.status_code == 202
    assert r_existing.status_code == 202
    assert r_missing.json()["data"] == r_existing.json()["data"]
    unconsumed_count = EmailVerificationToken.objects.filter(
        user=user_obj, consumed_at__isnull=True
    ).count()
    assert unconsumed_count == 1
    token_2 = _extract_last_mail_token("rsv")
    assert token_2 != token_1

    # Old invalidated token is rejected; newest token succeeds once.
    old_verify = anon.post("/api/v1/auth/email/verify", {"token": token_1}, format="json")
    assert old_verify.status_code == 401
    v_ok = anon.post("/api/v1/auth/email/verify", {"token": token_2}, format="json")
    assert v_ok.status_code == 200
    assert v_ok.json()["data"]["verified"] is True
    replay_verify = anon.post("/api/v1/auth/email/verify", {"token": token_2}, format="json")
    assert replay_verify.status_code == 401

    user_obj.refresh_from_db()
    drf_req.user = user_obj
    assert perm.has_permission(drf_req, VerifiedOnlyDummyView()) is True
    assert authed.get("/api/v1/me").json()["data"]["email_verified"] is True


@pytest.mark.django_db(transaction=True)
def test_password_forgot_reset_and_change_session_revocation() -> None:
    reg1, authed1 = _register_android(email="pw@example.com", password="InitialStrong#2026")
    login2 = _android_client().post(
        "/api/v1/auth/login",
        {"email": "pw@example.com", "password": "InitialStrong#2026", "device_label": "Tablet"},
        format="json",
    )
    assert login2.status_code == 200
    authed2 = _android_client(login2.json()["data"]["tokens"]["access_token"])

    # Wrong current password returns 403 REAUTHENTICATION_FAILED (not 401 loop).
    bad_pw = authed1.post(
        "/api/v1/auth/password/change",
        {"current_password": "WrongPassword#2026", "new_password": "UpdatedStrong#2026"},
        format="json",
    )
    assert bad_pw.status_code == 403
    assert bad_pw.json()["error"]["code"] == "REAUTHENTICATION_FAILED"

    # Change revokes sibling session 2 while keeping current session 1 alive.
    good_pw = authed1.post(
        "/api/v1/auth/password/change",
        {"current_password": "InitialStrong#2026", "new_password": "UpdatedStrong#2026"},
        format="json",
    )
    assert good_pw.status_code == 200
    assert authed1.get("/api/v1/me").status_code == 200
    assert authed2.get("/api/v1/me").status_code == 401

    # Forgot password returns identical 202 for missing and existing emails; reset clears sessions.
    mail.outbox.clear()
    r_miss = _android_client().post(
        "/api/v1/auth/password/forgot", {"email": "doesnotexist@example.com"}, format="json"
    )
    r_hit = _android_client().post(
        "/api/v1/auth/password/forgot", {"email": "pw@example.com"}, format="json"
    )
    assert r_miss.status_code == 202
    assert r_hit.status_code == 202
    assert r_miss.json()["data"] == r_hit.json()["data"]

    reset_token = _extract_last_mail_token("rsp")
    reset_ok = _android_client().post(
        "/api/v1/auth/password/reset",
        {"token": reset_token, "new_password": "ResetStrong#2026!"},
        format="json",
    )
    assert reset_ok.status_code == 200
    assert PasswordResetToken.objects.filter(
        token_hash=hmac_token("password-reset", reset_token),
        consumed_at__isnull=False,
    ).exists()
    assert authed1.get("/api/v1/me").status_code == 401
    assert (
        _android_client()
        .post(
            "/api/v1/auth/refresh",
            {"refresh_token": str(reg1["tokens"]["refresh_token"])},
            format="json",
        )
        .status_code
        == 401
    )
    post_reset_login = _android_client().post(
        "/api/v1/auth/login",
        {"email": "pw@example.com", "password": "ResetStrong#2026!"},
        format="json",
    )
    assert post_reset_login.status_code == 200
    post_reset_access = str(post_reset_login.json()["data"]["tokens"]["access_token"])
    assert _android_client(post_reset_access).get("/api/v1/me").status_code == 200
    assert reg1 is not None


@pytest.mark.django_db
def test_me_capabilities_sessions_idor_deletion_and_data_export() -> None:
    reg_a, client_a = _register_android(email="ownera@example.com", password="OwnerAStrong#2026")
    _, client_b = _register_android(email="ownerb@example.com", password="OwnerBStrong#2026")

    # Reject unknown / admin privilege fields strictly.
    for forbidden in ({"is_staff": True}, {"is_superuser": True}, {"status": "suspended"}):
        assert client_a.patch("/api/v1/me", forbidden, format="json").status_code == 400

    # Sessions IDOR: owner B cannot revoke owner A's session.
    sess_list = client_a.get("/api/v1/me/sessions")
    assert sess_list.status_code == 200
    session_a_id = sess_list.json()["data"][0]["id"]
    assert client_b.delete(f"/api/v1/me/sessions/{session_a_id}").status_code == 404

    # Data export must contain non-secret profile/session/audit rows and ZERO secret hashes.
    exp = client_a.get("/api/v1/me/data-export")
    assert exp.status_code == 200
    exp_text = json.dumps(exp.json())
    assert "argon2" not in exp_text
    assert "token_hash" not in exp_text
    assert "pbkdf2" not in exp_text

    # Deletion requires exact confirmation phrase and password reauth.
    bad_phrase = client_a.post(
        "/api/v1/me/deletion-request",
        {"confirmation_text": "delete my account", "password": "OwnerAStrong#2026"},
        format="json",
    )
    assert bad_phrase.status_code == 400

    del_ok = client_a.post(
        "/api/v1/me/deletion-request",
        {"confirmation_text": "DELETE MY ACCOUNT", "password": "OwnerAStrong#2026"},
        format="json",
    )
    assert del_ok.status_code == 202
    user_a = User.objects.get(id=reg_a["user"]["id"])
    assert user_a.status == User.Status.ACTIVE
    assert user_a.deletion_requested_at is not None
    assert client_a.get("/api/v1/me").status_code == 401
    assert (
        _android_client()
        .post(
            "/api/v1/auth/login",
            {"email": "ownera@example.com", "password": "OwnerAStrong#2026"},
            format="json",
        )
        .status_code
        == 403
    )

    # Passwordless Google user deletion respects AUTH_REAUTH_MAX_AGE_SECONDS (300s).
    g_user = User.objects.create_user(
        email="gdel@example.com",
        password=None,
        status=User.Status.ACTIVE,
        email_verified_at=timezone.now(),
        terms_accepted_at=timezone.now(),
    )
    OAuthIdentity.objects.create(
        user=g_user,
        provider=OAuthIdentity.Provider.GOOGLE,
        provider_sub="gdel-sub",
        email_at_link="gdel@example.com",
    )
    stale_sess = RefreshSession.objects.create(
        user=g_user,
        token_hash=hmac_token("refresh-token", "rsr_stale_gdel"),
        client_platform=RefreshSession.ClientPlatform.ANDROID,
        auth_time=timezone.now() - timedelta(seconds=600),
        expires_at=timezone.now() + timedelta(days=7),
        family_expires_at=timezone.now() + timedelta(days=30),
    )
    stale_jwt, _ = mint_access_token(user_id=g_user.id, session_id=stale_sess.id)
    stale_res = _android_client(stale_jwt).post(
        "/api/v1/me/deletion-request",
        {"confirmation_text": "DELETE MY ACCOUNT", "confirm_recent_reauth": True},
        format="json",
    )
    assert stale_res.status_code == 403
    assert stale_res.json()["error"]["code"] == "REAUTHENTICATION_REQUIRED"


@pytest.mark.django_db
def test_rate_limits_trusted_proxy_count_audit_immutability_and_log_redaction() -> None:
    _register_android(email="ratelimit@example.com", password="RateLimitPass#2026")
    client = _android_client()

    # TRUSTED_PROXY_COUNT=0 ignores spoofed X-Forwarded-For, so 5 failed logins lock out.
    for attempt in range(5):
        r = client.post(
            "/api/v1/auth/login",
            {"email": "ratelimit@example.com", "password": "WrongPassword#2026"},
            format="json",
            headers={"X-Forwarded-For": f"10.0.0.{attempt + 1}"},
        )
        assert r.status_code == 401

    locked = client.post(
        "/api/v1/auth/login",
        {"email": "ratelimit@example.com", "password": "RateLimitPass#2026"},
        format="json",
        headers={"X-Forwarded-For": "10.0.0.99"},
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(locked.headers["Retry-After"]) >= 1

    # When TRUSTED_PROXY_COUNT=1, the rightmost trusted hop isolates distinct client IPs.
    with override_settings(TRUSTED_PROXY_COUNT=1):
        proxied_ok = client.post(
            "/api/v1/auth/login",
            {"email": "ratelimit@example.com", "password": "RateLimitPass#2026"},
            format="json",
            headers={"X-Forwarded-For": "203.0.113.9, 198.51.100.77"},
        )
        assert proxied_ok.status_code == 200

    # Non-existent email triggers the exact same 401 -> 429 behavior without enumeration.
    for attempt in range(5):
        assert (
            client.post(
                "/api/v1/auth/login",
                {"email": "missing-rl@example.com", "password": "WrongPassword#2026"},
                format="json",
                headers={"X-Forwarded-For": f"10.0.1.{attempt + 1}"},
            ).status_code
            == 401
        )
    missing_locked = client.post(
        "/api/v1/auth/login",
        {"email": "missing-rl@example.com", "password": "WrongPassword#2026"},
        format="json",
    )
    assert missing_locked.status_code == 429
    assert missing_locked.json()["error"]["message"] == locked.json()["error"]["message"]

    # Append-only audit immutability checks.
    evt = record_security_event(
        event_type="test.audit.created",
        outcome=SecurityAuditEvent.Outcome.SUCCESS,
        metadata={"note": "ok"},
    )
    with pytest.raises(PermissionError):
        evt.outcome = SecurityAuditEvent.Outcome.FAILURE
        evt.save()
    with pytest.raises(PermissionError):
        evt.delete()
    with pytest.raises(PermissionError):
        SecurityAuditEvent.objects.filter(id=evt.id).update(event_type="tampered")
    with pytest.raises(PermissionError):
        SecurityAuditEvent.objects.filter(id=evt.id).delete()

    # Log formatter redaction covers both record.getMessage() and structured fields.
    formatter = StructuredJsonFormatter()
    log_rec = logging.LogRecord(
        name="backend.security",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Failed auth for alice@example.com token=rsr_supersecret123 Bearer abc.def.ghi",
        args=(),
        exc_info=None,
    )
    log_rec.structured = {"note": "user alice@example.com sent eyJhbGciOiJIUzI1NiJ9.aaa.bbb"}
    formatted = json.loads(formatter.format(log_rec))
    serialized = json.dumps(formatted)
    assert "alice@example.com" not in serialized
    assert "rsr_supersecret123" not in serialized
    assert "eyJhbGciOiJIUzI1NiJ9" not in serialized


def test_production_settings_validation_rejects_weak_jwt_key_and_missing_origins() -> None:
    base_env = {
        "DJANGO_SECRET_KEY": "real-django-secret-key-for-testing-only-64bytes-long-value!",
        "INTERNAL_SERVICE_TOKEN": "real-internal-token-for-testing-only-32bytes!",
        "JWT_SIGNING_KEY": "short-key",
        "CORS_ALLOWED_ORIGINS": "https://app.roomsync.in",
        "CSRF_TRUSTED_ORIGINS": "https://app.roomsync.in",
    }
    sys.modules.pop("config.settings.production", None)
    with patch.dict("os.environ", base_env, clear=False), pytest.raises(ImproperlyConfigured):
        importlib.import_module("config.settings.production")

    no_cors_env = dict(base_env)
    no_cors_env["JWT_SIGNING_KEY"] = "0123456789abcdef0123456789abcdef0123456789abcdef"
    no_cors_env["CORS_ALLOWED_ORIGINS"] = ""
    sys.modules.pop("config.settings.production", None)
    with patch.dict("os.environ", no_cors_env, clear=False), pytest.raises(ImproperlyConfigured):
        importlib.import_module("config.settings.production")


@pytest.mark.django_db(transaction=True)
def test_same_second_and_frozen_clock_revocation_watermark_does_not_self_lockout() -> None:
    # Part A: Same-second progression (100_000us -> 200_000us within one integer clock second).
    base_dt = datetime.now(tz=UTC).replace(microsecond=100_000)
    clock = {"now": base_dt}

    with (
        patch("django.utils.timezone.now", side_effect=lambda: clock["now"]),
        patch(
            "apps.accounts.services.jwt_tokens.time.time",
            side_effect=lambda: clock["now"].timestamp(),
        ),
    ):
        reg, old_client = _register_android(
            email="same-sec@example.com",
            password="SameSecPassword#2026",
        )
        old_access = str(reg["tokens"]["access_token"])
        old_refresh = str(reg["tokens"]["refresh_token"])
        old_session_id = uuid.UUID(str(reg["session_id"]))
        old_user_id = uuid.UUID(str(reg["user"]["id"]))

        forgot_resp = _android_client().post(
            "/api/v1/auth/password/forgot",
            {"email": "same-sec@example.com"},
            format="json",
        )
        assert forgot_resp.status_code == 202
        reset_token = _extract_last_mail_token("rsp")
        reset_resp = _android_client().post(
            "/api/v1/auth/password/reset",
            {"token": reset_token, "new_password": "SameSecReset#2026!"},
            format="json",
        )
        assert reset_resp.status_code == 200

        # Immediate login still inside the exact same clock second.
        clock["now"] = base_dt.replace(microsecond=200_000)
        new_login = _android_client().post(
            "/api/v1/auth/login",
            {"email": "same-sec@example.com", "password": "SameSecReset#2026!"},
            format="json",
        )
        assert new_login.status_code == 200
        new_access = str(new_login.json()["data"]["tokens"]["access_token"])
        new_refresh = str(new_login.json()["data"]["tokens"]["refresh_token"])

        assert _android_client(new_access).get("/api/v1/me").status_code == 200
        assert old_client.get("/api/v1/me").status_code == 401
        assert (
            _android_client()
            .post("/api/v1/auth/refresh", {"refresh_token": old_refresh}, format="json")
            .status_code
            == 401
        )

        # Rotate immediately inside the exact same second and verify rotated child access JWT works.
        rot_resp = _android_client().post(
            "/api/v1/auth/refresh",
            {"refresh_token": new_refresh},
            format="json",
        )
        assert rot_resp.status_code == 200
        child_access = str(rot_resp.json()["data"]["tokens"]["access_token"])
        assert _android_client(child_access).get("/api/v1/me").status_code == 200

        # Part B: Completely frozen clock (0us delta) across revoke -> login -> refresh -> /me.
        frozen_dt = datetime.now(tz=UTC).replace(microsecond=500_000)
        clock["now"] = frozen_dt
        forgot_frozen = _android_client().post(
            "/api/v1/auth/password/forgot",
            {"email": "same-sec@example.com"},
            format="json",
        )
        assert forgot_frozen.status_code == 202
        frozen_reset_tok = _extract_last_mail_token("rsp")
        assert (
            _android_client()
            .post(
                "/api/v1/auth/password/reset",
                {"token": frozen_reset_tok, "new_password": "FrozenClockPass#2026"},
                format="json",
            )
            .status_code
            == 200
        )

        frozen_login = _android_client().post(
            "/api/v1/auth/login",
            {"email": "same-sec@example.com", "password": "FrozenClockPass#2026"},
            format="json",
        )
        assert frozen_login.status_code == 200
        frozen_access = str(frozen_login.json()["data"]["tokens"]["access_token"])
        frozen_refresh = str(frozen_login.json()["data"]["tokens"]["refresh_token"])
        assert _android_client(frozen_access).get("/api/v1/me").status_code == 200

        frozen_rot = _android_client().post(
            "/api/v1/auth/refresh",
            {"refresh_token": frozen_refresh},
            format="json",
        )
        assert frozen_rot.status_code == 200
        frozen_child_access = str(frozen_rot.json()["data"]["tokens"]["access_token"])
        assert _android_client(frozen_child_access).get("/api/v1/me").status_code == 200

        # Remove per-session sid keys to prove microsecond user watermark rejects prior sessions
        # even if a JWT for old_session_id had a later iat, while preserving new/child sessions.
        rclient = get_redis_client()
        try:
            sid_keys = list(rclient.scan_iter("roomsync:revoked:sid:*"))
            if sid_keys:
                rclient.delete(*sid_keys)
            assert rclient.get(f"roomsync:revoked:user_before_us:{old_user_id}") is not None
        finally:
            rclient.close()

        assert _android_client(old_access).get("/api/v1/me").status_code == 401
        late_minted_old_jwt, _ = mint_access_token(user_id=old_user_id, session_id=old_session_id)
        assert _android_client(late_minted_old_jwt).get("/api/v1/me").status_code == 401
        assert _android_client(frozen_child_access).get("/api/v1/me").status_code == 200

    # Fail-closed Redis check still rejects with 503 after watermark changes.
    with patch(
        "apps.accounts.services.revocation.get_redis_client",
        side_effect=redis_lib.ConnectionError("redis down"),
    ):
        down_resp = _android_client(frozen_child_access).get("/api/v1/me")
        assert down_resp.status_code == 503
        assert down_resp.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.django_db
def test_logout_strict_transport_validation_expired_access_fallback_and_idempotency() -> None:
    # Android setup
    android_reg, android_authed = _register_android(email="logout-mob@example.com")
    android_access = str(android_reg["tokens"]["access_token"])
    android_refresh = str(android_reg["tokens"]["refresh_token"])
    android_uid = uuid.UUID(str(android_reg["user"]["id"]))
    android_sid = uuid.UUID(str(android_reg["session_id"]))

    # Web setup
    web_client, csrf_tok = _web_csrf_client()
    web_reg = web_client.post(
        "/api/v1/auth/register",
        {
            "email": "logout-web@example.com",
            "password": "LogoutWebStrong#2026",
            "accept_terms": True,
            "confirm_adult": True,
        },
        format="json",
        headers={"X-CSRFToken": csrf_tok},
    )
    assert web_reg.status_code == 201
    web_csrf = web_reg.cookies["csrftoken"].value
    web_access = web_client.cookies[settings.AUTH_ACCESS_COOKIE_NAME].value
    web_refresh = web_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

    # 1. Mixed Bearer + cookies -> 401 canonical envelope.
    mixed = _android_client(android_access)
    mixed.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = web_refresh
    mixed_resp = mixed.post("/api/v1/auth/logout", {}, format="json")
    assert mixed_resp.status_code == 401
    assert mixed_resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    # 2. Android + Web cookies (without Bearer) -> 401 canonical envelope.
    android_cookies_only = _android_client()
    android_cookies_only.cookies[settings.AUTH_ACCESS_COOKIE_NAME] = web_access
    android_cookies_only.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = web_refresh
    r_ac = android_cookies_only.post("/api/v1/auth/logout", {}, format="json")
    assert r_ac.status_code == 401
    assert r_ac.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    # 3. Web + Bearer header -> 401 canonical envelope.
    web_bearer = APIClient()
    web_bearer.credentials(
        HTTP_X_CLIENT_PLATFORM="web",
        HTTP_AUTHORIZATION=f"Bearer {android_access}",
    )
    r_wb = web_bearer.post("/api/v1/auth/logout", {}, format="json")
    assert r_wb.status_code == 401
    assert r_wb.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    # 4. Web + JSON refresh_token body -> 400 VALIDATION_ERROR.
    r_wbody = web_client.post(
        "/api/v1/auth/logout",
        {"refresh_token": web_refresh},
        format="json",
        headers={"X-CSRFToken": web_csrf},
    )
    assert r_wbody.status_code == 400
    assert r_wbody.json()["error"]["code"] == "VALIDATION_ERROR"

    # 5. Invalid X-Client-Platform -> 400 VALIDATION_ERROR.
    bad_plat = APIClient()
    bad_plat.credentials(HTTP_X_CLIENT_PLATFORM="ios")
    r_ios = bad_plat.post("/api/v1/auth/logout", {}, format="json")
    assert r_ios.status_code == 400
    assert r_ios.json()["error"]["code"] == "VALIDATION_ERROR"

    # 6. Android non-Bearer / empty Bearer -> 401.
    non_bearer = APIClient()
    non_bearer.credentials(HTTP_X_CLIENT_PLATFORM="android", HTTP_AUTHORIZATION="Basic dXNlcjpw")
    assert non_bearer.post("/api/v1/auth/logout", {}, format="json").status_code == 401
    empty_bearer = APIClient()
    empty_bearer.credentials(HTTP_X_CLIENT_PLATFORM="android", HTTP_AUTHORIZATION="Bearer   ")
    assert empty_bearer.post("/api/v1/auth/logout", {}, format="json").status_code == 401

    # 7. Tampered Bearer JWT + valid Android refresh_token MUST fail 401 and leave session intact!
    tampered_android = _android_client("tampered.jwt.signature")
    r_tampered = tampered_android.post(
        "/api/v1/auth/logout",
        {"refresh_token": android_refresh},
        format="json",
    )
    assert r_tampered.status_code == 401
    assert r_tampered.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert android_authed.get("/api/v1/me").status_code == 200

    # 8. Tampered Web rs_access cookie + valid rs_refresh MUST fail 401.
    tampered_web_client = APIClient(enforce_csrf_checks=True)
    c_resp = tampered_web_client.get("/api/v1/auth/csrf")
    tampered_csrf = c_resp.cookies["csrftoken"].value
    tampered_web_client.cookies[settings.AUTH_ACCESS_COOKIE_NAME] = "tampered.web.cookie"
    tampered_web_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = web_refresh
    r_tw = tampered_web_client.post(
        "/api/v1/auth/logout",
        {},
        format="json",
        headers={"X-CSRFToken": tampered_csrf},
    )
    assert r_tw.status_code == 401
    assert web_client.get("/api/v1/me").status_code == 200

    # 9. Valid expired-only Android JWT + matching refresh_token -> 200!
    past_epoch = int((timezone.now() - timedelta(hours=2)).timestamp())
    expired_android_jwt = jwt.encode(
        {
            "sub": str(android_uid),
            "sid": str(android_sid),
            "jti": str(uuid.uuid4()),
            "iat": past_epoch,
            "exp": past_epoch + 60,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        },
        settings.JWT_SIGNING_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    exp_logout = _android_client(expired_android_jwt).post(
        "/api/v1/auth/logout",
        {"refresh_token": android_refresh},
        format="json",
    )
    assert exp_logout.status_code == 200
    assert exp_logout.json()["data"]["logged_out"] is True
    assert android_authed.get("/api/v1/me").status_code == 401

    # Idempotent Android repeat without Bearer header (refresh_token fallback only) -> 200.
    idem_android = _android_client().post(
        "/api/v1/auth/logout",
        {"refresh_token": android_refresh},
        format="json",
    )
    assert idem_android.status_code == 200
    assert idem_android.json()["data"]["logged_out"] is True

    # 10. Expired Web rs_access cookie + valid rs_refresh -> 200 + cleared cookies; empty -> 401.
    web_uid = uuid.UUID(str(web_reg.json()["data"]["user"]["id"]))
    web_sid = uuid.UUID(str(web_reg.json()["data"]["session_id"]))
    expired_web_jwt = jwt.encode(
        {
            "sub": str(web_uid),
            "sid": str(web_sid),
            "jti": str(uuid.uuid4()),
            "iat": past_epoch,
            "exp": past_epoch + 60,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        },
        settings.JWT_SIGNING_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    web_client.cookies[settings.AUTH_ACCESS_COOKIE_NAME] = expired_web_jwt
    web_logout = web_client.post(
        "/api/v1/auth/logout",
        {},
        format="json",
        headers={"X-CSRFToken": web_csrf},
    )
    assert web_logout.status_code == 200
    assert web_logout.cookies[settings.AUTH_ACCESS_COOKIE_NAME].value == ""
    assert web_logout.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value == ""

    # Idempotent repeat for Web with valid transport + saved rs_refresh cookie -> 200.
    web_client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = web_refresh
    web_idem = web_client.post(
        "/api/v1/auth/logout",
        {},
        format="json",
        headers={"X-CSRFToken": web_csrf},
    )
    assert web_idem.status_code == 200

    # No credentials at all -> 401 AUTH_REQUIRED.
    no_creds_web, nc_csrf = _web_csrf_client()
    r_nc = no_creds_web.post(
        "/api/v1/auth/logout",
        {},
        format="json",
        headers={"X-CSRFToken": nc_csrf},
    )
    assert r_nc.status_code == 401
    assert r_nc.json()["error"]["code"] == "AUTH_REQUIRED"

    # 11. Redis outage during logout with active Bearer token -> 503 SERVICE_UNAVAILABLE.
    _, active_client = _register_android(email="logout-redis-down@example.com")
    with patch(
        "apps.accounts.services.revocation.get_redis_client",
        side_effect=redis_lib.ConnectionError("redis down"),
    ):
        down_logout = active_client.post("/api/v1/auth/logout", {}, format="json")
    assert down_logout.status_code == 503
    assert down_logout.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.django_db(transaction=True)
def test_concurrent_google_oauth_signup_and_link_uniqueness_races() -> None:
    future_exp = int((timezone.now() + timedelta(minutes=10)).timestamp())
    aud = settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID

    def _fake_verify(token: str, _request: Any) -> dict[str, Any]:
        if token.startswith("tok_gs_1"):
            return {
                "iss": "https://accounts.google.com",
                "aud": aud,
                "email_verified": True,
                "sub": "race-google-sub-1",
                "email": "Race-Google@Example.com",
                "nonce": "n" * 24,
                "exp": future_exp,
            }
        if token.startswith("tok_gs_2"):
            return {
                "iss": "https://accounts.google.com",
                "aud": aud,
                "email_verified": True,
                "sub": "race-google-sub-2",
                "email": "race-google@example.com",
                "nonce": "n" * 24,
                "exp": future_exp,
            }
        if token.startswith("tok_mixed_"):
            return {
                "iss": "https://accounts.google.com",
                "aud": aud,
                "email_verified": True,
                "sub": "race-mixed-sub",
                "email": "race-reg-google@example.com",
                "nonce": "n" * 24,
                "exp": future_exp,
            }
        if token.startswith("tok_link_1"):
            return {
                "iss": "https://accounts.google.com",
                "aud": aud,
                "email_verified": True,
                "sub": "link-race-sub-1",
                "email": "link-race@example.com",
                "nonce": "n" * 24,
                "exp": future_exp,
            }
        return {
            "iss": "https://accounts.google.com",
            "aud": aud,
            "email_verified": True,
            "sub": "link-race-sub-2",
            "email": "link-race@example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        }

    # (a) Simultaneous first-time Google signups colliding on email -> [201, 409 STATE_CONFLICT].
    orig_create_user = User.objects.create_user
    signup_barrier = threading.Barrier(2, timeout=5)

    def _barrier_create_user(*args: Any, **kwargs: Any) -> User:
        target_email = normalize_email_address(str(kwargs.get("email", "")))
        if target_email in {"race-google@example.com", "race-reg-google@example.com"}:
            signup_barrier.wait(timeout=5)
        return orig_create_user(*args, **kwargs)

    with (
        patch(
            "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
            side_effect=_fake_verify,
        ),
        patch.object(User.objects, "create_user", side_effect=_barrier_create_user),
    ):

        def _google_signup(tok: str) -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/google",
                    {
                        "id_token": tok,
                        "nonce": "n" * 24,
                        "accept_terms": True,
                        "confirm_adult": True,
                    },
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_google_signup, "tok_gs_1_" + uuid.uuid4().hex)
            f2 = pool.submit(_google_signup, "tok_gs_2_" + uuid.uuid4().hex)
            res_a = f1.result(timeout=10)
            res_b = f2.result(timeout=10)

    assert sorted([res_a[0], res_b[0]]) == [201, 409]
    loser_gs = res_a[1] if res_a[0] == 409 else res_b[1]
    assert loser_gs["error"]["code"] == "STATE_CONFLICT"
    assert User.objects.filter(email="race-google@example.com").count() == 1
    assert OAuthIdentity.objects.filter(user__email="race-google@example.com").count() == 1
    assert RefreshSession.objects.filter(user__email="race-google@example.com").count() == 1
    assert SecurityAuditEvent.objects.filter(event_type="auth.google.race_conflict").count() == 1

    # (b) Simultaneous Google signup racing with register -> [201, 409 STATE_CONFLICT].
    signup_barrier.reset()
    with (
        patch(
            "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
            side_effect=_fake_verify,
        ),
        patch.object(User.objects, "create_user", side_effect=_barrier_create_user),
    ):

        def _google_mixed() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/google",
                    {
                        "id_token": "tok_mixed_" + uuid.uuid4().hex,
                        "nonce": "n" * 24,
                        "accept_terms": True,
                        "confirm_adult": True,
                    },
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        def _register_mixed() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/register",
                    {
                        "email": "race-reg-google@example.com",
                        "password": "MixedRaceStrong#2026",
                        "accept_terms": True,
                        "confirm_adult": True,
                    },
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fg = pool.submit(_google_mixed)
            fr = pool.submit(_register_mixed)
            rg = fg.result(timeout=10)
            rr = fr.result(timeout=10)

    assert sorted([rg[0], rr[0]]) == [201, 409]
    mixed_loser = rg[1] if rg[0] == 409 else rr[1]
    assert mixed_loser["error"]["code"] == "STATE_CONFLICT"
    assert User.objects.filter(email="race-reg-google@example.com").count() == 1
    assert RefreshSession.objects.filter(user__email="race-reg-google@example.com").count() == 1

    # (c1) Simultaneous confirm_google_link using two challenges on the same user -> [200, 409].
    _register_android(email="link-race@example.com", password="LinkRaceStrong#2026")
    verify_tok = _extract_last_mail_token("rsv")
    assert (
        _android_client()
        .post("/api/v1/auth/email/verify", {"token": verify_tok}, format="json")
        .status_code
        == 200
    )

    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        side_effect=_fake_verify,
    ):
        c1_resp = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_link_1_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
        c2_resp = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_link_2_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
    assert c1_resp.status_code == 409
    assert c2_resp.status_code == 409
    chal_1 = str(c1_resp.json()["error"]["details"]["link_challenge_token"])
    chal_2 = str(c2_resp.json()["error"]["details"]["link_challenge_token"])

    same_user_barrier = threading.Barrier(2, timeout=5)

    def _do_same_user_link(challenge_token: str) -> tuple[int, dict[str, Any]]:
        try:
            same_user_barrier.wait(timeout=5)
            resp = _android_client().post(
                "/api/v1/auth/google/link",
                {
                    "link_challenge_token": challenge_token,
                    "confirm_link": True,
                    "password": "LinkRaceStrong#2026",
                },
                format="json",
            )
            return resp.status_code, resp.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        fl1 = pool.submit(_do_same_user_link, chal_1)
        fl2 = pool.submit(_do_same_user_link, chal_2)
        rl1 = fl1.result(timeout=10)
        rl2 = fl2.result(timeout=10)

    assert sorted([rl1[0], rl2[0]]) == [200, 409]
    link_loser = rl1[1] if rl1[0] == 409 else rl2[1]
    assert link_loser["error"]["code"] == "STATE_CONFLICT"
    assert OAuthIdentity.objects.filter(user__email="link-race@example.com").count() == 1
    assert (
        OAuthLinkChallenge.objects.filter(
            user__email="link-race@example.com", consumed_at__isnull=False
        ).count()
        == 1
    )
    assert (
        OAuthLinkChallenge.objects.filter(
            user__email="link-race@example.com", consumed_at__isnull=True
        ).count()
        == 1
    )

    # (c2) Simultaneous confirm_google_link hitting real PostgreSQL 23505 on provider_sub across
    # distinct User locks -> loser rolls back mutations and returns 409 STATE_CONFLICT.
    reg_u1, _ = _register_android(email="link-sub-u1@example.com", password="LinkRaceStrong#2026")
    reg_u2, _ = _register_android(email="link-sub-u2@example.com", password="LinkRaceStrong#2026")
    u1 = User.objects.get(id=reg_u1["user"]["id"])
    u2 = User.objects.get(id=reg_u2["user"]["id"])
    shared_sub = "shared-provider-sub-race"
    raw_chal_u1 = generate_opaque_token("rsl")
    raw_chal_u2 = generate_opaque_token("rsl")
    chal_obj_u1 = OAuthLinkChallenge.objects.create(
        user=u1,
        provider=OAuthIdentity.Provider.GOOGLE,
        provider_sub=shared_sub,
        email_at_link=u1.email,
        token_hash=hmac_token("oauth-link", raw_chal_u1),
        existing_account_verified=False,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    chal_obj_u2 = OAuthLinkChallenge.objects.create(
        user=u2,
        provider=OAuthIdentity.Provider.GOOGLE,
        provider_sub=shared_sub,
        email_at_link=u2.email,
        token_hash=hmac_token("oauth-link", raw_chal_u2),
        existing_account_verified=False,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    orig_oauth_create = OAuthIdentity.objects.create
    link_barrier = threading.Barrier(2, timeout=5)

    def _barrier_oauth_create(*args: Any, **kwargs: Any) -> OAuthIdentity:
        if kwargs.get("provider_sub") == shared_sub:
            link_barrier.wait(timeout=5)
        return orig_oauth_create(*args, **kwargs)

    with patch.object(OAuthIdentity.objects, "create", side_effect=_barrier_oauth_create):

        def _do_sub_link(challenge_token: str) -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/google/link",
                    {
                        "link_challenge_token": challenge_token,
                        "confirm_link": True,
                        "password": "LinkRaceStrong#2026",
                    },
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fs1 = pool.submit(_do_sub_link, raw_chal_u1)
            fs2 = pool.submit(_do_sub_link, raw_chal_u2)
            rs1 = fs1.result(timeout=10)
            rs2 = fs2.result(timeout=10)

    assert sorted([rs1[0], rs2[0]]) == [200, 409]
    sub_loser = rs1[1] if rs1[0] == 409 else rs2[1]
    assert sub_loser["error"]["code"] == "STATE_CONFLICT"
    assert OAuthIdentity.objects.filter(provider_sub=shared_sub).count() == 1
    chal_obj_u1.refresh_from_db()
    chal_obj_u2.refresh_from_db()
    consumed_flags = sorted(
        [chal_obj_u1.consumed_at is not None, chal_obj_u2.consumed_at is not None]
    )
    assert consumed_flags == [False, True]
    assert (
        SecurityAuditEvent.objects.filter(event_type="auth.google.link_race_conflict").count() == 1
    )

    # (d) Unrelated IntegrityError (non-23505 or unrelated constraint) must NEVER become 409.
    class _FakeDiag:
        def __init__(self, constraint_name: str) -> None:
            self.constraint_name = constraint_name

    class _FakeCause(Exception):
        def __init__(self, sqlstate: str, constraint_name: str) -> None:
            self.sqlstate = sqlstate
            self.diag = _FakeDiag(constraint_name)

    non_unique_err = IntegrityError("null value violates not-null constraint")
    non_unique_err.__cause__ = _FakeCause("23502", "")
    assert _is_expected_oauth_uniqueness_error(non_unique_err) is False

    unrelated_unique_err = IntegrityError("unrelated unique violation")
    unrelated_unique_err.__cause__ = _FakeCause("23505", "some_unrelated_table_key")
    assert _is_expected_oauth_uniqueness_error(unrelated_unique_err) is False

    raw_req = _android_client().post("/").wsgi_request
    with (
        patch(
            "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
            return_value={
                "iss": "https://accounts.google.com",
                "aud": aud,
                "email_verified": True,
                "sub": "sub-non-unique-db",
                "email": "non-unique-db@example.com",
                "nonce": "n" * 24,
                "exp": future_exp,
            },
        ),
        patch.object(User.objects, "create_user", side_effect=non_unique_err),
        pytest.raises(IntegrityError),
    ):
        authenticate_with_google(
            raw_id_token="tok_non_unique_" + uuid.uuid4().hex,
            nonce="n" * 24,
            accept_terms=True,
            confirm_adult=True,
            client_platform="android",
            request=raw_req,
        )


@pytest.mark.django_db(transaction=True)
def test_credential_mutation_redis_failure_rolls_back_atomically_across_all_three_flows() -> None:
    def _fail_redis_publish(*args: Any, **kwargs: Any) -> None:
        with patch(
            "apps.accounts.services.revocation.get_redis_client",
            side_effect=redis_lib.ConnectionError("redis down during publish"),
        ):
            orig_mark_sessions_revoked(*args, **kwargs)

    # 1. confirm_google_link (unverified pre-hijack scrub): Redis outage -> 503 + full rollback.
    attacker_reg, attacker_client = _register_android(
        email="atom-link@example.com",
        password="AttackerInitial#2026",
    )
    attacker_uid = uuid.UUID(str(attacker_reg["user"]["id"]))
    attacker_sid = uuid.UUID(str(attacker_reg["session_id"]))
    attacker_refresh = str(attacker_reg["tokens"]["refresh_token"])
    verify_tok = _extract_last_mail_token("rsv")
    future_exp = int((timezone.now() + timedelta(minutes=10)).timestamp())

    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID,
            "email_verified": True,
            "sub": "google-sub-atom-link",
            "email": "atom-link@example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        },
    ):
        coll = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_atom_link_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
    assert coll.status_code == 409
    challenge_tok = str(coll.json()["error"]["details"]["link_challenge_token"])

    with patch(
        "apps.accounts.services.sessions.mark_sessions_revoked",
        side_effect=_fail_redis_publish,
    ):
        link_fail = _android_client().post(
            "/api/v1/auth/google/link",
            {
                "link_challenge_token": challenge_tok,
                "confirm_link": True,
                "email_verification_token": verify_tok,
            },
            format="json",
        )
    assert link_fail.status_code == 503
    assert link_fail.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

    # Verify full PG rollback: password untouched, tokens unconsumed, session alive.
    user_obj = User.objects.get(id=attacker_uid)
    assert user_obj.has_usable_password()
    assert user_obj.check_password("AttackerInitial#2026")
    assert user_obj.email_verified_at is None
    assert not OAuthIdentity.objects.filter(user=user_obj).exists()
    assert OAuthLinkChallenge.objects.filter(user=user_obj, consumed_at__isnull=True).exists()
    assert EmailVerificationToken.objects.filter(user=user_obj, consumed_at__isnull=True).exists()
    attacker_sess = RefreshSession.objects.get(id=attacker_sid)
    assert attacker_sess.revoked_at is None
    assert RefreshSession.objects.filter(user=user_obj).count() == 1
    assert not SecurityAuditEvent.objects.filter(
        target_user_id=user_obj.id, event_type="auth.google.linked"
    ).exists()
    assert attacker_client.get("/api/v1/me").status_code == 200

    # Retry succeeds once Redis is healthy; attacker session & password are scrubbed.
    link_ok = _android_client().post(
        "/api/v1/auth/google/link",
        {
            "link_challenge_token": challenge_tok,
            "confirm_link": True,
            "email_verification_token": verify_tok,
        },
        format="json",
    )
    assert link_ok.status_code == 200
    victim_access = str(link_ok.json()["data"]["tokens"]["access_token"])
    user_obj.refresh_from_db()
    assert not user_obj.has_usable_password()
    assert attacker_client.get("/api/v1/me").status_code == 401
    assert (
        _android_client()
        .post("/api/v1/auth/refresh", {"refresh_token": attacker_refresh}, format="json")
        .status_code
        == 401
    )
    assert _android_client(victim_access).get("/api/v1/me").status_code == 200
    assert (
        SecurityAuditEvent.objects.filter(
            target_user_id=user_obj.id, event_type="auth.google.linked"
        ).count()
        == 1
    )

    # 2. confirm_password_reset: Redis outage -> 503 + full PG rollback, retry succeeds cleanly.
    pw_reg, pw_s1_client = _register_android(
        email="atom-pw@example.com",
        password="OldPassword#2026",
        device_label="Phone",
    )
    pw_uid = uuid.UUID(str(pw_reg["user"]["id"]))
    pw_s1_refresh = str(pw_reg["tokens"]["refresh_token"])

    mail.outbox.clear()
    assert (
        _android_client()
        .post("/api/v1/auth/password/forgot", {"email": "atom-pw@example.com"}, format="json")
        .status_code
        == 202
    )
    reset_tok = _extract_last_mail_token("rsp")

    with patch(
        "apps.accounts.services.revocation.get_redis_client",
        side_effect=redis_lib.ConnectionError("redis down during password reset"),
    ):
        reset_fail = _android_client().post(
            "/api/v1/auth/password/reset",
            {"token": reset_tok, "new_password": "NewResetPassword#2026"},
            format="json",
        )
    assert reset_fail.status_code == 503
    assert reset_fail.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

    pw_user = User.objects.get(id=pw_uid)
    assert pw_user.check_password("OldPassword#2026")
    assert PasswordResetToken.objects.filter(
        token_hash=hmac_token("password-reset", reset_tok), consumed_at__isnull=True
    ).exists()
    assert RefreshSession.objects.get(id=pw_reg["session_id"]).revoked_at is None
    assert not SecurityAuditEvent.objects.filter(
        target_user_id=pw_uid, event_type="auth.password.reset"
    ).exists()
    assert pw_s1_client.get("/api/v1/me").status_code == 200

    reset_ok = _android_client().post(
        "/api/v1/auth/password/reset",
        {"token": reset_tok, "new_password": "NewResetPassword#2026"},
        format="json",
    )
    assert reset_ok.status_code == 200
    assert pw_s1_client.get("/api/v1/me").status_code == 401
    assert (
        _android_client()
        .post("/api/v1/auth/refresh", {"refresh_token": pw_s1_refresh}, format="json")
        .status_code
        == 401
    )
    assert (
        _android_client()
        .post(
            "/api/v1/auth/login",
            {"email": "atom-pw@example.com", "password": "NewResetPassword#2026"},
            format="json",
        )
        .status_code
        == 200
    )

    # 3. change_user_password: Redis outage -> 503 + rollback; retry preserves current session.
    s1_login = _android_client().post(
        "/api/v1/auth/login",
        {"email": "atom-pw@example.com", "password": "NewResetPassword#2026", "device_label": "S1"},
        format="json",
    )
    s2_login = _android_client().post(
        "/api/v1/auth/login",
        {"email": "atom-pw@example.com", "password": "NewResetPassword#2026", "device_label": "S2"},
        format="json",
    )
    assert s1_login.status_code == 200 and s2_login.status_code == 200
    s1_client = _android_client(str(s1_login.json()["data"]["tokens"]["access_token"]))
    s2_client = _android_client(str(s2_login.json()["data"]["tokens"]["access_token"]))
    s2_sid = uuid.UUID(str(s2_login.json()["data"]["session_id"]))

    with patch(
        "apps.accounts.services.sessions.mark_sessions_revoked",
        side_effect=_fail_redis_publish,
    ):
        chg_fail = s1_client.post(
            "/api/v1/auth/password/change",
            {
                "current_password": "NewResetPassword#2026",
                "new_password": "ChangedStrong#2026",
            },
            format="json",
        )
    assert chg_fail.status_code == 503
    assert chg_fail.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

    pw_user.refresh_from_db()
    assert pw_user.check_password("NewResetPassword#2026")
    assert RefreshSession.objects.get(id=s2_sid).revoked_at is None
    assert not SecurityAuditEvent.objects.filter(
        target_user_id=pw_uid, event_type="auth.password.changed"
    ).exists()
    assert s2_client.get("/api/v1/me").status_code == 200

    chg_ok = s1_client.post(
        "/api/v1/auth/password/change",
        {
            "current_password": "NewResetPassword#2026",
            "new_password": "ChangedStrong#2026",
        },
        format="json",
    )
    assert chg_ok.status_code == 200
    assert s1_client.get("/api/v1/me").status_code == 200
    assert s2_client.get("/api/v1/me").status_code == 401
    assert (
        SecurityAuditEvent.objects.filter(
            target_user_id=pw_uid, event_type="auth.password.changed"
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_redis_commit_before_pg_rollback_causes_safe_over_revocation_without_self_lockout() -> None:
    publish_attempts = 0

    def _redis_writes_then_pg_fails(*args: Any, **kwargs: Any) -> None:
        nonlocal publish_attempts
        publish_attempts += 1
        orig_mark_sessions_revoked(*args, **kwargs)
        raise OperationalError("simulated postgres outage before tx commit")

    reg, old_client = _register_android(
        email="overrevoke@example.com",
        password="InitialSafePass#2026",
    )
    uid = uuid.UUID(str(reg["user"]["id"]))
    old_refresh = str(reg["tokens"]["refresh_token"])

    mail.outbox.clear()
    assert (
        _android_client()
        .post("/api/v1/auth/password/forgot", {"email": "overrevoke@example.com"}, format="json")
        .status_code
        == 202
    )
    reset_tok = _extract_last_mail_token("rsp")

    with patch(
        "apps.accounts.services.sessions.mark_sessions_revoked",
        side_effect=_redis_writes_then_pg_fails,
    ):
        crash_resp = _android_client().post(
            "/api/v1/auth/password/reset",
            {"token": reset_tok, "new_password": "AfterDbCrashPass#2026"},
            format="json",
        )
    assert publish_attempts == 1
    assert crash_resp.status_code == 500
    assert crash_resp.json()["error"]["code"] == "INTERNAL_ERROR"

    # PostgreSQL rolled back cleanly.
    user_obj = User.objects.get(id=uid)
    assert user_obj.check_password("InitialSafePass#2026")
    assert PasswordResetToken.objects.filter(
        token_hash=hmac_token("password-reset", reset_tok), consumed_at__isnull=True
    ).exists()
    assert RefreshSession.objects.get(id=reg["session_id"]).revoked_at is None
    assert not SecurityAuditEvent.objects.filter(
        target_user_id=uid, event_type="auth.password.reset"
    ).exists()

    # Redis markers were written -> old session fails closed (safe over-revocation).
    assert old_client.get("/api/v1/me").status_code == 401
    assert (
        _android_client()
        .post("/api/v1/auth/refresh", {"refresh_token": old_refresh}, format="json")
        .status_code
        == 401
    )

    # Retrying reset and logging in works cleanly (issue_session_pair sorts above Redis watermark).
    retry_reset = _android_client().post(
        "/api/v1/auth/password/reset",
        {"token": reset_tok, "new_password": "AfterDbCrashPass#2026"},
        format="json",
    )
    assert retry_reset.status_code == 200
    new_login = _android_client().post(
        "/api/v1/auth/login",
        {"email": "overrevoke@example.com", "password": "AfterDbCrashPass#2026"},
        format="json",
    )
    assert new_login.status_code == 200
    assert (
        _android_client(str(new_login.json()["data"]["tokens"]["access_token"]))
        .get("/api/v1/me")
        .status_code
        == 200
    )


@pytest.mark.django_db(transaction=True)
def test_change_user_password_locks_user_row_and_rejects_stale_or_concurrent_changes() -> None:
    reg, client_1 = _register_android(
        email="lock-pw@example.com",
        password="FirstPassword#2026",
    )
    uid = uuid.UUID(str(reg["user"]["id"]))
    sess = RefreshSession.objects.get(id=reg["session_id"])

    # Direct stale-object check: grab in-memory User instance before another update commits in DB.
    stale_user = User.objects.get(id=uid)
    mail.outbox.clear()
    assert (
        _android_client()
        .post("/api/v1/auth/password/forgot", {"email": "lock-pw@example.com"}, format="json")
        .status_code
        == 202
    )
    reset_tok = _extract_last_mail_token("rsp")
    assert (
        _android_client()
        .post(
            "/api/v1/auth/password/reset",
            {"token": reset_tok, "new_password": "SecondPassword#2026"},
            format="json",
        )
        .status_code
        == 200
    )
    # stale_user in memory still has FirstPassword#2026; select_for_update() re-reads committed DB.
    assert stale_user.check_password("FirstPassword#2026")
    raw_req = client_1.post("/api/v1/auth/password/change", {}, format="json").wsgi_request
    with pytest.raises(RoomSyncAPIException) as exc_info:
        change_user_password(
            user=stale_user,
            current_password="FirstPassword#2026",
            new_password="ThirdPassword#2026",
            current_family_id=sess.family_id,
            request=raw_req,
        )
    assert exc_info.value.error_code == "REAUTHENTICATION_FAILED"
    assert exc_info.value.status_code == 403

    # Concurrent HTTP /api/v1/auth/password/change calls with same current_password -> [200, 403].
    fresh_login = _android_client().post(
        "/api/v1/auth/login",
        {"email": "lock-pw@example.com", "password": "SecondPassword#2026"},
        format="json",
    )
    assert fresh_login.status_code == 200
    bearer = str(fresh_login.json()["data"]["tokens"]["access_token"])
    barrier = threading.Barrier(2, timeout=5)

    def _race_change(next_pw: str) -> tuple[int, dict[str, Any]]:
        try:
            client = _android_client(bearer)
            barrier.wait(timeout=5)
            resp = client.post(
                "/api/v1/auth/password/change",
                {"current_password": "SecondPassword#2026", "new_password": next_pw},
                format="json",
            )
            return resp.status_code, resp.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_race_change, "WinnerPassword#2026")
        f2 = pool.submit(_race_change, "LoserPassword#2026")
        r1 = f1.result(timeout=10)
        r2 = f2.result(timeout=10)

    assert sorted([r1[0], r2[0]]) == [200, 403]
    loser_json = r1[1] if r1[0] == 403 else r2[1]
    assert loser_json["error"]["code"] == "REAUTHENTICATION_FAILED"


@pytest.mark.django_db(transaction=True)
def test_concurrent_lock_order_prevents_deadlocks_across_m1_flows() -> None:
    def _make_user_lock_barrier() -> tuple[Any, dict[str, int]]:
        state = {"entered": 0}
        count_lock = threading.Lock()
        local_state = threading.local()
        barrier = threading.Barrier(2, timeout=5)
        orig_select_for_update = User.objects.select_for_update

        def _wrapped_select_for_update(*args: Any, **kwargs: Any) -> Any:
            if not getattr(local_state, "seen", False):
                local_state.seen = True
                with count_lock:
                    state["entered"] += 1
                barrier.wait(timeout=5)
            return orig_select_for_update(*args, **kwargs)

        return _wrapped_select_for_update, state

    # 1. confirm_password_reset vs request_password_reset (both use User -> ResetToken)
    pw_reg, pw_client = _register_android(
        email="deadlock-pw@example.com",
        password="InitialDeadlock#2026",
    )
    pw_uid = uuid.UUID(str(pw_reg["user"]["id"]))
    pw_refresh = str(pw_reg["tokens"]["refresh_token"])
    mail.outbox.clear()
    assert (
        _android_client()
        .post("/api/v1/auth/password/forgot", {"email": "deadlock-pw@example.com"}, format="json")
        .status_code
        == 202
    )
    first_reset_tok = _extract_last_mail_token("rsp")

    wrapper_pw, state_pw = _make_user_lock_barrier()
    with patch.object(User.objects, "select_for_update", side_effect=wrapper_pw):

        def _run_confirm_reset() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/password/reset",
                    {"token": first_reset_tok, "new_password": "ResetWinnerStrong#2026"},
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        def _run_forgot_reset() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/password/forgot",
                    {"email": "deadlock-pw@example.com"},
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_confirm = pool.submit(_run_confirm_reset)
            fut_forgot = pool.submit(_run_forgot_reset)
            res_confirm = fut_confirm.result(timeout=10)
            res_forgot = fut_forgot.result(timeout=10)

    assert state_pw["entered"] == 2
    assert res_forgot[0] == 202
    assert res_confirm[0] in {200, 401}
    assert (
        PasswordResetToken.objects.filter(user_id=pw_uid, consumed_at__isnull=True).count() == 1
    )
    pw_user = User.objects.get(id=pw_uid)
    if res_confirm[0] == 200:
        assert pw_user.check_password("ResetWinnerStrong#2026")
        assert pw_client.get("/api/v1/me").status_code == 401
        assert (
            _android_client()
            .post("/api/v1/auth/refresh", {"refresh_token": pw_refresh}, format="json")
            .status_code
            == 401
        )
    else:
        assert res_confirm[1]["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
        assert pw_user.check_password("InitialDeadlock#2026")
        second_reset_tok = _extract_last_mail_token("rsp")
        assert second_reset_tok != first_reset_tok
        assert (
            _android_client()
            .post(
                "/api/v1/auth/password/reset",
                {"token": second_reset_tok, "new_password": "ResetFollowupStrong#2026"},
                format="json",
            )
            .status_code
            == 200
        )

    # 2. confirm_google_link vs resend_verification_email on same unverified account
    mail.outbox.clear()
    link_reg, attacker_client = _register_android(
        email="deadlock-link-resend@example.com",
        password="AttackerPreHijack#2026",
    )
    link_uid = uuid.UUID(str(link_reg["user"]["id"]))
    ev_tok_1 = _extract_last_mail_token("rsv")
    future_exp = int((timezone.now() + timedelta(minutes=10)).timestamp())
    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID,
            "email_verified": True,
            "sub": "deadlock-google-resend-sub",
            "email": "deadlock-link-resend@example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        },
    ):
        coll_1 = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_dl_resend_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
    assert coll_1.status_code == 409
    challenge_1 = str(coll_1.json()["error"]["details"]["link_challenge_token"])

    wrapper_lr, state_lr = _make_user_lock_barrier()
    with patch.object(User.objects, "select_for_update", side_effect=wrapper_lr):

        def _run_google_link_1() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/google/link",
                    {
                        "link_challenge_token": challenge_1,
                        "confirm_link": True,
                        "email_verification_token": ev_tok_1,
                    },
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        def _run_resend_1() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/email/resend",
                    {"email": "deadlock-link-resend@example.com"},
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_link_1 = pool.submit(_run_google_link_1)
            fut_resend_1 = pool.submit(_run_resend_1)
            res_link_1 = fut_link_1.result(timeout=10)
            res_resend_1 = fut_resend_1.result(timeout=10)

    assert state_lr["entered"] == 2
    assert res_resend_1[0] == 202
    assert res_link_1[0] in {200, 403}
    link_user_1 = User.objects.get(id=link_uid)
    if res_link_1[0] == 200:
        assert not link_user_1.has_usable_password()
        assert link_user_1.email_verified_at is not None
        assert OAuthIdentity.objects.filter(user=link_user_1).count() == 1
        assert attacker_client.get("/api/v1/me").status_code == 401
        assert (
            EmailVerificationToken.objects.filter(
                user=link_user_1, consumed_at__isnull=True
            ).count()
            == 0
        )
    else:
        assert res_link_1[1]["error"]["code"] == "OWNERSHIP_PROOF_REQUIRED"
        assert link_user_1.email_verified_at is None
        assert not OAuthIdentity.objects.filter(user=link_user_1).exists()
        assert (
            EmailVerificationToken.objects.filter(
                user=link_user_1, consumed_at__isnull=True
            ).count()
            == 1
        )
        ev_tok_2 = _extract_last_mail_token("rsv")
        assert ev_tok_2 != ev_tok_1
        assert (
            _android_client()
            .post(
                "/api/v1/auth/google/link",
                {
                    "link_challenge_token": challenge_1,
                    "confirm_link": True,
                    "email_verification_token": ev_tok_2,
                },
                format="json",
            )
            .status_code
            == 200
        )

    # 3. confirm_google_link vs verify_email_token racing on the same EmailVerificationToken
    mail.outbox.clear()
    lv_reg, _ = _register_android(
        email="deadlock-link-verify@example.com",
        password="AttackerPreHijack2#2026",
    )
    lv_uid = uuid.UUID(str(lv_reg["user"]["id"]))
    lv_ev_tok = _extract_last_mail_token("rsv")
    with patch(
        "apps.accounts.services.google_oauth.google_id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID_ANDROID,
            "email_verified": True,
            "sub": "deadlock-google-verify-sub",
            "email": "deadlock-link-verify@example.com",
            "nonce": "n" * 24,
            "exp": future_exp,
        },
    ):
        coll_2 = _android_client().post(
            "/api/v1/auth/google",
            {"id_token": "tok_dl_verify_" + uuid.uuid4().hex, "nonce": "n" * 24},
            format="json",
        )
    assert coll_2.status_code == 409
    challenge_2 = str(coll_2.json()["error"]["details"]["link_challenge_token"])

    wrapper_lv, state_lv = _make_user_lock_barrier()
    with patch.object(User.objects, "select_for_update", side_effect=wrapper_lv):

        def _run_google_link_2() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/google/link",
                    {
                        "link_challenge_token": challenge_2,
                        "confirm_link": True,
                        "email_verification_token": lv_ev_tok,
                    },
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        def _run_verify_2() -> tuple[int, dict[str, Any]]:
            try:
                resp = _android_client().post(
                    "/api/v1/auth/email/verify",
                    {"token": lv_ev_tok},
                    format="json",
                )
                return resp.status_code, resp.json()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_link_2 = pool.submit(_run_google_link_2)
            fut_verify_2 = pool.submit(_run_verify_2)
            res_link_2 = fut_link_2.result(timeout=10)
            res_verify_2 = fut_verify_2.result(timeout=10)

    assert state_lv["entered"] == 2
    assert (res_link_2[0], res_verify_2[0]) in {(200, 401), (403, 200)}
    lv_user = User.objects.get(id=lv_uid)
    assert lv_user.email_verified_at is not None
    assert (
        EmailVerificationToken.objects.filter(user=lv_user, consumed_at__isnull=True).count() == 0
    )
    if res_link_2[0] == 200:
        assert res_verify_2[1]["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
        assert OAuthIdentity.objects.filter(user=lv_user).count() == 1
        assert not lv_user.has_usable_password()
    else:
        assert res_link_2[1]["error"]["code"] == "OWNERSHIP_PROOF_REQUIRED"
        assert not OAuthIdentity.objects.filter(user=lv_user).exists()
        assert lv_user.has_usable_password()
