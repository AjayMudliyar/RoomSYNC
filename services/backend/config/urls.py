from django.conf import settings
from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from common.health import health_live, health_ready
from common.views import SystemStatusView

urlpatterns = [
    path(settings.DJANGO_ADMIN_PATH, admin.site.urls),
    path("health/live", health_live, name="health-live"),
    path("health/ready", health_ready, name="health-ready"),
    path("api/v1/system/status/", SystemStatusView.as_view(), name="system-status"),
]

if settings.ENABLE_OPENAPI_SCHEMA_ENDPOINT:
    urlpatterns.append(path("api/v1/schema/", SpectacularAPIView.as_view(), name="openapi-schema"))

