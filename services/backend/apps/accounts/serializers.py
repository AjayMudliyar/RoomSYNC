from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.accounts.models import RefreshSession
from common.views import ResponseMetaSerializer


class StrictInputSerializer(serializers.Serializer[dict[str, Any]]):
    """Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR."""

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, Mapping):
            unknown = sorted({str(k) for k in data} - set(self.fields.keys()))
            if unknown:
                raise serializers.ValidationError({field: ["Unknown field."] for field in unknown})
        return super().to_internal_value(data)


def build_envelope_serializer(name: str, data_serializer: serializers.Serializer[Any]) -> Any:
    return inline_serializer(
        name=name,
        fields={
            "data": data_serializer,
            "meta": ResponseMetaSerializer(),
        },
    )


class UserCapabilitiesSerializer(serializers.Serializer[dict[str, Any]]):
    can_seek_room = serializers.BooleanField()
    can_offer_room = serializers.BooleanField()
    can_list_property = serializers.BooleanField()


class AuthUserSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    phone_e164 = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    email_verified = serializers.BooleanField()
    email_verified_at = serializers.DateTimeField(allow_null=True)
    phone_verified_at = serializers.DateTimeField(allow_null=True)
    terms_accepted_at = serializers.DateTimeField(allow_null=True)
    deletion_requested_at = serializers.DateTimeField(allow_null=True)
    has_usable_password = serializers.BooleanField()
    linked_providers = serializers.ListField(child=serializers.CharField())
    capabilities = UserCapabilitiesSerializer()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AuthTokensSerializer(serializers.Serializer[dict[str, Any]]):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in_seconds = serializers.IntegerField()


class AuthSessionDataSerializer(serializers.Serializer[dict[str, Any]]):
    user = AuthUserSerializer()
    platform = serializers.ChoiceField(choices=RefreshSession.ClientPlatform.choices)
    session_id = serializers.UUIDField()
    expires_in_seconds = serializers.IntegerField()
    tokens = AuthTokensSerializer(required=False, allow_null=True)


class CsrfTokenDataSerializer(serializers.Serializer[dict[str, Any]]):
    csrf_token = serializers.CharField()


class RegisterRequestSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=10, max_length=256, trim_whitespace=False)
    accept_terms = serializers.BooleanField()
    confirm_adult = serializers.BooleanField()
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class LoginRequestSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=256, trim_whitespace=False)
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class GoogleAuthRequestSerializer(StrictInputSerializer):
    id_token = serializers.CharField(min_length=16, max_length=4096)
    nonce = serializers.CharField(min_length=16, max_length=256)
    accept_terms = serializers.BooleanField(required=False)
    confirm_adult = serializers.BooleanField(required=False)
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class GoogleLinkRequestSerializer(StrictInputSerializer):
    link_challenge_token = serializers.CharField(min_length=16, max_length=512)
    confirm_link = serializers.BooleanField()
    password = serializers.CharField(
        required=False, allow_blank=False, max_length=256, trim_whitespace=False
    )
    email_verification_token = serializers.CharField(
        required=False, allow_blank=False, max_length=512
    )
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class RefreshRequestSerializer(StrictInputSerializer):
    refresh_token = serializers.CharField(
        required=False, allow_blank=False, min_length=16, max_length=512
    )
    device_label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class LogoutRequestSerializer(StrictInputSerializer):
    refresh_token = serializers.CharField(
        required=False, allow_blank=False, min_length=16, max_length=512
    )


class LogoutResponseDataSerializer(serializers.Serializer[dict[str, Any]]):
    logged_out = serializers.BooleanField()


class EmailVerifyRequestSerializer(StrictInputSerializer):
    token = serializers.CharField(min_length=16, max_length=512)


class EmailVerifyResponseDataSerializer(serializers.Serializer[dict[str, Any]]):
    verified = serializers.BooleanField()
    email_verified_at = serializers.DateTimeField()


class EmailResendRequestSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254, required=False)


class GenericAcceptedDataSerializer(serializers.Serializer[dict[str, Any]]):
    accepted = serializers.BooleanField()
    message = serializers.CharField()


class PasswordForgotRequestSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetRequestSerializer(StrictInputSerializer):
    token = serializers.CharField(min_length=16, max_length=512)
    new_password = serializers.CharField(min_length=10, max_length=256, trim_whitespace=False)


class PasswordResetResponseDataSerializer(serializers.Serializer[dict[str, Any]]):
    password_reset = serializers.BooleanField()


class PasswordChangeRequestSerializer(StrictInputSerializer):
    current_password = serializers.CharField(
        required=False, allow_blank=False, max_length=256, trim_whitespace=False
    )
    new_password = serializers.CharField(min_length=10, max_length=256, trim_whitespace=False)


class PasswordChangeResponseDataSerializer(serializers.Serializer[dict[str, Any]]):
    password_changed = serializers.BooleanField()


class MeUpdateRequestSerializer(StrictInputSerializer):
    can_seek_room = serializers.BooleanField(required=False)
    can_offer_room = serializers.BooleanField(required=False)
    can_list_property = serializers.BooleanField(required=False)


class UserSessionItemSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    client_platform = serializers.ChoiceField(choices=RefreshSession.ClientPlatform.choices)
    device_label = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField(allow_null=True)
    expires_at = serializers.DateTimeField()
    is_current = serializers.BooleanField()


UserSessionListEnvelopeSerializer: Any = build_envelope_serializer(
    "UserSessionListEnvelope", UserSessionItemSerializer(many=True)
)


class DeletionRequestSerializer(StrictInputSerializer):
    confirmation_text = serializers.CharField(min_length=1, max_length=64)
    password = serializers.CharField(
        required=False, allow_blank=False, max_length=256, trim_whitespace=False
    )
    google_id_token = serializers.CharField(required=False, allow_blank=False, max_length=4096)
    nonce = serializers.CharField(required=False, allow_blank=False, max_length=256)
    confirm_recent_reauth = serializers.BooleanField(required=False, default=False)


class DeletionRequestResponseDataSerializer(serializers.Serializer[dict[str, Any]]):
    deletion_requested = serializers.BooleanField()
    deletion_requested_at = serializers.DateTimeField()


class ExportAccountSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    phone_e164 = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    email_verified_at = serializers.DateTimeField(allow_null=True)
    phone_verified_at = serializers.DateTimeField(allow_null=True)
    terms_accepted_at = serializers.DateTimeField(allow_null=True)
    password_changed_at = serializers.DateTimeField(allow_null=True)
    deletion_requested_at = serializers.DateTimeField(allow_null=True)
    capabilities = UserCapabilitiesSerializer()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ExportOAuthIdentitySerializer(serializers.Serializer[dict[str, Any]]):
    provider = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField(allow_null=True)


class ExportSessionSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    client_platform = serializers.CharField()
    device_label = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField(allow_null=True)
    expires_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField(allow_null=True)


class ExportSecurityEventSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    event_type = serializers.CharField()
    outcome = serializers.CharField()
    client_platform = serializers.CharField()
    request_id = serializers.CharField()
    created_at = serializers.DateTimeField()


class DataExportDataSerializer(serializers.Serializer[dict[str, Any]]):
    schema_version = serializers.CharField()
    exported_at = serializers.DateTimeField()
    account = ExportAccountSerializer()
    oauth_identities = ExportOAuthIdentitySerializer(many=True)
    sessions = ExportSessionSerializer(many=True)
    security_events = ExportSecurityEventSerializer(many=True)


CsrfEnvelopeSchema = build_envelope_serializer("CsrfTokenEnvelope", CsrfTokenDataSerializer())
AuthSessionEnvelopeSchema = build_envelope_serializer(
    "AuthSessionEnvelope", AuthSessionDataSerializer()
)
AuthUserEnvelopeSchema = build_envelope_serializer("AuthUserEnvelope", AuthUserSerializer())
LogoutEnvelopeSchema = build_envelope_serializer("LogoutEnvelope", LogoutResponseDataSerializer())
EmailVerifyEnvelopeSchema = build_envelope_serializer(
    "EmailVerifyEnvelope", EmailVerifyResponseDataSerializer()
)
GenericAcceptedEnvelopeSchema = build_envelope_serializer(
    "GenericAcceptedEnvelope", GenericAcceptedDataSerializer()
)
PasswordResetEnvelopeSchema = build_envelope_serializer(
    "PasswordResetEnvelope", PasswordResetResponseDataSerializer()
)
PasswordChangeEnvelopeSchema = build_envelope_serializer(
    "PasswordChangeEnvelope", PasswordChangeResponseDataSerializer()
)
DeletionRequestEnvelopeSchema = build_envelope_serializer(
    "DeletionRequestEnvelope", DeletionRequestResponseDataSerializer()
)
DataExportEnvelopeSchema = build_envelope_serializer(
    "DataExportEnvelope", DataExportDataSerializer()
)
