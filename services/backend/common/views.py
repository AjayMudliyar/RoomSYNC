from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import request_id_ctx


class SystemStatusDataSerializer(serializers.Serializer[dict[str, str]]):
    service = serializers.CharField()
    status = serializers.CharField()
    api_version = serializers.CharField()


class ResponseMetaSerializer(serializers.Serializer[dict[str, str]]):
    request_id = serializers.CharField()


SystemStatusEnvelopeSchema: Any = inline_serializer(
    name="SystemStatusEnvelope",
    fields={
        "data": SystemStatusDataSerializer(),
        "meta": ResponseMetaSerializer(),
    },
)


class SystemStatusView(APIView):
    """Minimal M0 public system status endpoint verifying DRF envelopes and OpenAPI generation."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        operation_id="system_status_retrieve",
        responses={200: SystemStatusEnvelopeSchema},
        tags=["System"],
    )
    def get(self, request: Request) -> Response:
        req_id = str(request.META.get("HTTP_X_REQUEST_ID") or request_id_ctx.get())
        return Response(
            {
                "data": {
                    "service": "roomsync-backend",
                    "status": "ok",
                    "api_version": "v1",
                },
                "meta": {
                    "request_id": req_id,
                },
            }
        )
