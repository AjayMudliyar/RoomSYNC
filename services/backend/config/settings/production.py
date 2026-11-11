import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import _parse_csv

DEBUG = False
ENVIRONMENT = "production"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
INTERNAL_SERVICE_TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "").strip()
CORS_ALLOWED_ORIGINS = _parse_csv(os.environ.get("CORS_ALLOWED_ORIGINS", ""))
CSRF_TRUSTED_ORIGINS = _parse_csv(os.environ.get("CSRF_TRUSTED_ORIGINS", ""))

if not SECRET_KEY or SECRET_KEY.startswith("replace-"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set cleanly in production.")

if not INTERNAL_SERVICE_TOKEN or INTERNAL_SERVICE_TOKEN.startswith("replace-"):
    raise ImproperlyConfigured("INTERNAL_SERVICE_TOKEN must be configured in production.")

if (
    not JWT_SIGNING_KEY
    or JWT_SIGNING_KEY.startswith("replace-")
    or len(JWT_SIGNING_KEY.encode("utf-8")) < 32
):
    raise ImproperlyConfigured(
        "JWT_SIGNING_KEY must be set cleanly with at least 32 bytes in production."
    )

if not CORS_ALLOWED_ORIGINS or "*" in CORS_ALLOWED_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS must be explicitly configured in production.")

if not CSRF_TRUSTED_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured("CSRF_TRUSTED_ORIGINS must be explicitly configured in production.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
ENABLE_OPENAPI_SCHEMA_ENDPOINT = False
