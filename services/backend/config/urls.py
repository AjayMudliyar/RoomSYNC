from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from common.health import health_live, health_ready
from common.views import SystemStatusView

handler404 = "common.exceptions.json_not_found_view"
handler500 = "common.exceptions.json_server_error_view"

urlpatterns = [
    path(settings.DJANGO_ADMIN_PATH, admin.site.urls),
    path("health/live", health_live, name="health-live"),
    path("health/ready", health_ready, name="health-ready"),
    path("api/v1/system/status", SystemStatusView.as_view(), name="system-status"),
    path("api/v1/", include("apps.accounts.urls")),
]

if settings.ENABLE_OPENAPI_SCHEMA_ENDPOINT:
    urlpatterns.append(path("api/v1/schema", SpectacularAPIView.as_view(), name="openapi-schema"))
