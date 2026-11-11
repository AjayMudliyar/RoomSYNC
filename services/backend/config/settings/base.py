from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _database_from_env() -> dict[str, Any]:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError("Unsupported DATABASE_URL scheme; PostgreSQL is required.")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/") or "roomsync",
            "USER": unquote(parsed.username or "roomsync"),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "db",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
        }

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "roomsync"),
        "USER": os.environ.get("POSTGRES_USER", "roomsync"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }


ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = _parse_csv(os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.audit",
    "apps.accounts",
    "common",
]

MIDDLEWARE = [
    "common.middleware.RequestContextMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "common.middleware.RoomSyncCsrfMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
APPEND_SLASH = False
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": _database_from_env()}

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis, Cache & Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60

# Security, Cookies & Origins
CORS_ALLOWED_ORIGINS = _parse_csv(os.environ.get("CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _parse_csv(os.environ.get("CSRF_TRUSTED_ORIGINS", ""))
CSRF_FAILURE_VIEW = "common.exceptions.csrf_failure_view"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "false").lower() == "true"

# Authentication, JWT, OAuth & Email Lifecycle
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.environ.get("JWT_ISSUER", "https://api.roomsync.in")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "roomsync-clients")
JWT_ACCESS_TTL_SECONDS = int(os.environ.get("JWT_ACCESS_TTL_SECONDS", "900"))
REFRESH_TOKEN_TTL_DAYS = int(os.environ.get("REFRESH_TOKEN_TTL_DAYS", "14"))
REFRESH_FAMILY_MAX_DAYS = int(os.environ.get("REFRESH_FAMILY_MAX_DAYS", "30"))

AUTH_ACCESS_COOKIE_NAME = "rs_access"
AUTH_REFRESH_COOKIE_NAME = "rs_refresh"
AUTH_ACCESS_COOKIE_PATH = "/"
AUTH_REFRESH_COOKIE_PATH = "/api/v1/auth/"

GOOGLE_OAUTH_CLIENT_ID_WEB = os.environ.get("GOOGLE_OAUTH_CLIENT_ID_WEB", "").strip()
GOOGLE_OAUTH_CLIENT_ID_ANDROID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID_ANDROID", "").strip()
GOOGLE_OAUTH_CLIENT_IDS = [
    cid
    for cid in (GOOGLE_OAUTH_CLIENT_ID_WEB, GOOGLE_OAUTH_CLIENT_ID_ANDROID)
    if cid
]

TRUSTED_PROXY_COUNT = max(0, int(os.environ.get("TRUSTED_PROXY_COUNT", "0")))
APP_WEB_ORIGIN = os.environ.get("WEB_ORIGIN", "http://localhost:5173").rstrip("/")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "RoomSync <no-reply@roomsync.local>")

EMAIL_VERIFICATION_TTL_HOURS = int(os.environ.get("EMAIL_VERIFICATION_TTL_HOURS", "24"))
PASSWORD_RESET_TTL_MINUTES = int(os.environ.get("PASSWORD_RESET_TTL_MINUTES", "30"))
OAUTH_LINK_CHALLENGE_TTL_SECONDS = int(os.environ.get("OAUTH_LINK_CHALLENGE_TTL_SECONDS", "600"))
AUTH_REAUTH_MAX_AGE_SECONDS = int(os.environ.get("AUTH_REAUTH_MAX_AGE_SECONDS", "300"))

RATE_LIMIT_LOGIN_ACCOUNT_MAX = int(os.environ.get("RATE_LIMIT_LOGIN_ACCOUNT_MAX", "5"))
RATE_LIMIT_LOGIN_ACCOUNT_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_LOGIN_ACCOUNT_WINDOW_SECONDS", "600")
)
RATE_LIMIT_LOGIN_IP_MAX = int(os.environ.get("RATE_LIMIT_LOGIN_IP_MAX", "20"))
RATE_LIMIT_LOGIN_IP_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_LOGIN_IP_WINDOW_SECONDS", "600")
)
RATE_LIMIT_REGISTER_IP_MAX = int(os.environ.get("RATE_LIMIT_REGISTER_IP_MAX", "5"))
RATE_LIMIT_REGISTER_IP_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_REGISTER_IP_WINDOW_SECONDS", "600")
)
RATE_LIMIT_FORGOT_IP_MAX = int(os.environ.get("RATE_LIMIT_FORGOT_IP_MAX", "5"))
RATE_LIMIT_FORGOT_IP_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_FORGOT_IP_WINDOW_SECONDS", "600")
)
RATE_LIMIT_EMAIL_RESEND_IP_MAX = int(os.environ.get("RATE_LIMIT_EMAIL_RESEND_IP_MAX", "5"))
RATE_LIMIT_EMAIL_RESEND_IP_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_EMAIL_RESEND_IP_WINDOW_SECONDS", "600")
)
RATE_LIMIT_GOOGLE_IP_MAX = int(os.environ.get("RATE_LIMIT_GOOGLE_IP_MAX", "20"))
RATE_LIMIT_GOOGLE_IP_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_GOOGLE_IP_WINDOW_SECONDS", "60")
)
RATE_LIMIT_REFRESH_IP_MAX = int(os.environ.get("RATE_LIMIT_REFRESH_IP_MAX", "20"))
RATE_LIMIT_REFRESH_IP_WINDOW_SECONDS = int(
    os.environ.get("RATE_LIMIT_REFRESH_IP_WINDOW_SECONDS", "60")
)

# Internal Matching Service & S3 config
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://matching:8001")
FASTAPI_TIMEOUT_SECONDS = float(os.environ.get("FASTAPI_TIMEOUT_SECONDS", "3.0"))
INTERNAL_SERVICE_TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
S3_BUCKET_PUBLIC = os.environ.get("S3_BUCKET_PUBLIC", "roomsync-public")
S3_BUCKET_PRIVATE = os.environ.get("S3_BUCKET_PRIVATE", "roomsync-private")

# Django REST Framework & OpenAPI
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.accounts.authentication.RoomSyncJWTAuthentication",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "RoomSync Public API",
    "DESCRIPTION": "Authoritative compatibility-first roommate discovery API.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ClientPlatformEnum": (("web", "Web"), ("android", "Android")),
    },
}

ENABLE_OPENAPI_SCHEMA_ENDPOINT = False
DJANGO_ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "admin/")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "common.logging.StructuredJsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO").upper(),
    },
}
