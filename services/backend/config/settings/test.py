import os

from .base import *  # noqa: F403

DEBUG = False
ENVIRONMENT = "test"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "") or "test-suite-ephemeral-signing-key"
JWT_SIGNING_KEY = (
    os.environ.get("JWT_SIGNING_KEY", "").strip()
    or "test-suite-ephemeral-jwt-signing-key-32-bytes!"
)

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
GOOGLE_OAUTH_CLIENT_ID_WEB = (
    os.environ.get("GOOGLE_OAUTH_CLIENT_ID_WEB", "").strip()
    or "test-google-web-client-id.apps.googleusercontent.com"
)
GOOGLE_OAUTH_CLIENT_ID_ANDROID = (
    os.environ.get("GOOGLE_OAUTH_CLIENT_ID_ANDROID", "").strip()
    or "test-google-android-client-id.apps.googleusercontent.com"
)
GOOGLE_OAUTH_CLIENT_IDS = [GOOGLE_OAUTH_CLIENT_ID_WEB, GOOGLE_OAUTH_CLIENT_ID_ANDROID]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
ENABLE_OPENAPI_SCHEMA_ENDPOINT = True
