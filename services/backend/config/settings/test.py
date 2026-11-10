import os

from .base import *  # noqa: F403

DEBUG = False
ENVIRONMENT = "test"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "") or "test-suite-ephemeral-signing-key"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
ENABLE_OPENAPI_SCHEMA_ENDPOINT = True
