import json
import logging
import sys
import tomllib
from importlib.metadata import distributions
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import CATEGORY_WEIGHTS, get_settings
from app.core.logging import StructuredJsonFormatter, redact_sensitive
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-internal-secret-token")
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()


def test_health_endpoints() -> None:
    app = create_app()
    client = TestClient(app)

    live = client.get("/health/live", headers={"X-Request-ID": "req-live-1"})
    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert live.headers["X-Request-ID"] == "req-live-1"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}
    assert ready.headers["X-Request-ID"]


def test_health_ready_returns_503_when_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "")
    get_settings.cache_clear()
    client = TestClient(create_app())

    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable"}


def test_internal_meta_requires_valid_service_token() -> None:
    client = TestClient(create_app())

    missing = client.get("/internal/v1/meta")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "AUTH_REQUIRED"
    assert "test-internal-secret-token" not in missing.text

    invalid = client.get(
        "/internal/v1/meta",
        headers={"X-Internal-Service-Token": "wrong-token"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "AUTH_REQUIRED"

    valid = client.get(
        "/internal/v1/meta",
        headers={"X-Internal-Service-Token": "test-internal-secret-token"},
    )
    assert valid.status_code == 200
    body = valid.json()
    assert body["algorithm_version"] == "roomsync-rule-v1"
    assert body["weights_version"] == "weights-2026-01"
    assert body["question_schema_version"] == 1
    assert sum(CATEGORY_WEIGHTS.values()) == 100


def test_no_database_drivers_declared_or_imported() -> None:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    pyproject_data = tomllib.loads(pyproject_path.read_text())
    deps = " ".join(pyproject_data["project"]["dependencies"]).lower()
    forbidden = (
        "psycopg",
        "psycopg2",
        "sqlalchemy",
        "asyncpg",
        "databases",
        "django",
        "pymysql",
    )
    for pkg in forbidden:
        assert pkg not in deps
        assert pkg not in sys.modules

    installed_names = {dist.metadata["Name"].lower() for dist in distributions()}
    for pkg in ("psycopg", "psycopg2", "sqlalchemy", "asyncpg"):
        assert pkg not in installed_names


def test_logging_redacts_secrets_and_pii() -> None:
    sanitized = redact_sensitive(
        {
            "email": "user@example.com",
            "password": "secret",
            "internal_service_token": "tok",
            "nested": {"phone_e164": "+919999999999", "safe_key": "ok"},
        }
    )
    assert sanitized["email"] == "[REDACTED]"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["internal_service_token"] == "[REDACTED]"
    assert sanitized["nested"]["phone_e164"] == "[REDACTED]"
    assert sanitized["nested"]["safe_key"] == "ok"

    formatter = StructuredJsonFormatter(environment="test")
    record = logging.LogRecord(
        name="matching.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.structured = {"token": "abc", "route": "/health/live"}
    formatted = json.loads(formatter.format(record))
    assert formatted["service"] == "matching"
    assert formatted["token"] == "[REDACTED]"
    assert formatted["route"] == "/health/live"
