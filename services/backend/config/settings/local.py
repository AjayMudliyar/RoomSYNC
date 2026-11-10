import os

from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

# Local development fallback only — overridden by .env when present
SECRET_KEY = (
    os.environ.get("DJANGO_SECRET_KEY", "")
    or "local-dev-only-insecure-fallback-change-in-env"
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ENABLE_OPENAPI_SCHEMA_ENDPOINT = True
