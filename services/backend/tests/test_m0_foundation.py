from __future__ import annotations

import json
import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from common.exceptions import custom_exception_handler
from common.logging import StructuredJsonFormatter, redact_sensitive
from common.tasks import health_ping


@pytest.mark.django_db
def test_custom_uuid_user_creation_and_normalization() -> None:
    User = get_user_model()
    user = User.objects.create_user(
        email="  Asha.Patel@Example.COM ",
        password="StrongPassword123!",
    )

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "asha.patel@example.com"
    assert user.status == "active"
    assert user.check_password("StrongPassword123!")

    admin = User.objects.create_superuser(email="Admin@RoomSync.IN", password="AdminPassword123!")
    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.email == "admin@roomsync.in"


def test_health_live_propagates_request_id(client: Client) -> None:
    response = client.get("/health/live", HTTP_X_REQUEST_ID="m0-live-req-1")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "m0-live-req-1"


@pytest.mark.django_db
def test_health_ready_checks_db_and_redis(client: Client) -> None:
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch("common.health.redis.Redis.from_url", return_value=mock_redis):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_redis.ping.assert_called_once()
    mock_redis.close.assert_called_once()


@pytest.mark.django_db
def test_health_ready_returns_503_without_leaking_secrets_when_redis_fails(client: Client) -> None:
    with patch("common.health.redis.Redis.from_url", side_effect=ConnectionError("redis://secret")):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert b"secret" not in response.content


def test_system_status_envelope_and_request_id(client: Client) -> None:
    response = client.get("/api/v1/system/status/", HTTP_X_REQUEST_ID="m0-status-1")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "data": {"service": "roomsync-backend", "status": "ok", "api_version": "v1"},
        "meta": {"request_id": "m0-status-1"},
    }
    assert response.headers["X-Request-ID"] == "m0-status-1"


def test_custom_exception_handler_canonical_envelope() -> None:
    factory = APIRequestFactory()
    request = factory.get("/api/v1/protected/", HTTP_X_REQUEST_ID="err-req-42")

    auth_resp = custom_exception_handler(exceptions.NotAuthenticated(), {"request": request})
    assert auth_resp.status_code == 401
    assert auth_resp.data == {
        "error": {
            "code": "AUTH_REQUIRED",
            "message": "Authentication credentials were not provided.",
            "field_errors": {},
            "details": {},
            "request_id": "err-req-42",
        }
    }

    val_resp = custom_exception_handler(
        exceptions.ValidationError({"budget_max_paise": ["Must exceed minimum budget."]}),
        {"request": request},
    )
    assert val_resp.status_code == 400
    assert isinstance(val_resp.data, dict)
    assert val_resp.data["error"]["code"] == "VALIDATION_ERROR"
    assert val_resp.data["error"]["field_errors"] == {
        "budget_max_paise": ["Must exceed minimum budget."]
    }


def test_logging_redacts_pii_and_secrets() -> None:
    cleaned = redact_sensitive(
        {
            "email": "private@example.com",
            "phone_e164": "+919876543210",
            "password": "my-secret-password",
            "route": "/api/v1/system/status/",
        }
    )
    assert cleaned["email"] == "[REDACTED]"
    assert cleaned["phone_e164"] == "[REDACTED]"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["route"] == "/api/v1/system/status/"

    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="backend.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="test",
        args=(),
        exc_info=None,
    )
    record.structured = {"token": "jwt-123", "status_code": 200}
    parsed = json.loads(formatter.format(record))
    assert parsed["service"] == "backend"
    assert parsed["token"] == "[REDACTED]"
    assert parsed["status_code"] == 200


def test_celery_health_ping_task() -> None:
    result = health_ping.delay()
    assert result.get(timeout=5) == "pong"
