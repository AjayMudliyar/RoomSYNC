import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
ENVIRONMENT = "production"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
INTERNAL_SERVICE_TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN", "")

if not SECRET_KEY or SECRET_KEY.startswith("replace-"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set cleanly in production.")

if not INTERNAL_SERVICE_TOKEN or INTERNAL_SERVICE_TOKEN.startswith("replace-"):
    raise ImproperlyConfigured("INTERNAL_SERVICE_TOKEN must be configured in production.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
ENABLE_OPENAPI_SCHEMA_ENDPOINT = False
