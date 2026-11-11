from __future__ import annotations

import hmac
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from typing import Any, cast

import redis
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import exceptions as drf_exceptions

from apps.accounts.models import (
    EmailVerificationToken,
    OAuthIdentity,
    OAuthLinkChallenge,
    User,
    normalize_email_address,
)
from apps.accounts.services.rate_limit import enforce_ip_rate_limit
from apps.accounts.services.sessions import (
    IssuedSessionPair,
    PendingRedisRevocation,
    issue_session_pair,
    revoke_user_sessions_in_tx,
)
from apps.audit.models import SecurityAuditEvent
from apps.audit.services import record_security_event
from common.exceptions import (
    AccountDeletionRequestedError,
    AccountSuspendedError,
    AuthInvalidCredentialsError,
    OAuthLinkConfirmationRequiredError,
    RoomSyncAPIException,
    SessionRevocationUnavailableError,
    StateConflictError,
)
from common.security import generate_opaque_token, get_redis_client, hmac_token

logger = logging.getLogger("backend.security")

_VALID_GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
_OAUTH_RACE_UNIQUE_CONSTRAINTS = frozenset(
    {
        "accounts_user_email_key",
        "acc_user_email_lower_uniq",
        "acc_oauth_provider_sub_uniq",
        "acc_oauth_user_provider_uniq",
    }
)


def _is_expected_oauth_uniqueness_error(exc: IntegrityError) -> bool:
    """Return True only for PostgreSQL unique violations (23505) on User email or OAuthIdentity."""
    cause = exc.__cause__
    if cause is None or getattr(cause, "sqlstate", None) != "23505":
        return False
    diag = getattr(cause, "diag", None)
    constraint_name = str(getattr(diag, "constraint_name", "") or "").lower()
    if constraint_name in _OAUTH_RACE_UNIQUE_CONSTRAINTS:
        return True
    return constraint_name.startswith("accounts_user_email") or constraint_name.startswith(
        "acc_oauth_"
    )


@dataclass(frozen=True, slots=True)
class VerifiedGoogleClaims:
    sub: str
    email: str
    aud: str
    exp: int


def _get_allowed_google_client_ids() -> list[str]:
    configured = list(getattr(settings, "GOOGLE_OAUTH_CLIENT_IDS", []) or [])
    if configured:
        return [str(cid).strip() for cid in configured if str(cid).strip()]
    web_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID_WEB", "") or "").strip()
    android_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID_ANDROID", "") or "").strip()
    return [cid for cid in (web_id, android_id) if cid]


def _nonce_matches(claim_nonce: str, supplied_nonce: str) -> bool:
    if not claim_nonce or not supplied_nonce:
        return False
    if hmac.compare_digest(claim_nonce, supplied_nonce):
        return True
    hashed_supplied = sha256(supplied_nonce.encode("utf-8")).hexdigest()
    return hmac.compare_digest(claim_nonce, hashed_supplied)


def _consume_google_token_replay_slot(*, raw_id_token: str, exp_epoch: int) -> None:
    digest = sha256(raw_id_token.encode("utf-8")).hexdigest()
    key = f"roomsync:oauth:google_replay:{digest}"
    ttl = min(max(exp_epoch - int(timezone.now().timestamp()) + 30, 60), 3600)
    client: redis.Redis[Any] | None = None
    try:
        client = get_redis_client()
        created = client.set(key, "1", ex=ttl, nx=True)
    except (redis.RedisError, OSError, TimeoutError) as exc:
        logger.warning("Redis unavailable checking Google ID token replay cache")
        raise SessionRevocationUnavailableError() from exc
    finally:
        if client is not None:
            client.close()

    if not created:
        raise AuthInvalidCredentialsError("Google ID token has already been used.")


def verify_google_id_token(
    *,
    raw_id_token: str,
    nonce: str,
    enforce_replay_check: bool = True,
) -> VerifiedGoogleClaims:
    """Verify Google ID token signature, issuer, aud allowlist, exp, email_verified, nonce."""
    allowed_audiences = _get_allowed_google_client_ids()
    if not allowed_audiences:
        raise RoomSyncAPIException(
            "Google authentication is not configured.",
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
        )

    try:
        verify_fn = cast("Callable[..., dict[str, Any]]", google_id_token.verify_oauth2_token)
        claims = verify_fn(
            raw_id_token,
            google_requests.Request(),
        )
    except google_auth_exceptions.TransportError as exc:
        logger.warning("Google certificate verification transport failed")
        raise RoomSyncAPIException(
            "Unable to contact Google identity verification service.",
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
        ) from exc
    except (google_auth_exceptions.GoogleAuthError, ValueError, TypeError) as exc:
        raise AuthInvalidCredentialsError("Invalid Google ID token.") from exc

    if not isinstance(claims, dict):
        raise AuthInvalidCredentialsError("Invalid Google ID token payload.")

    issuer = str(claims.get("iss", "") or "")
    if issuer not in _VALID_GOOGLE_ISSUERS:
        raise AuthInvalidCredentialsError("Google ID token issuer is invalid.")

    audience = str(claims.get("aud", "") or "")
    if audience not in allowed_audiences:
        raise AuthInvalidCredentialsError("Google ID token audience is not allowlisted.")

    if claims.get("email_verified") is not True:
        raise AuthInvalidCredentialsError("Google account email must be verified.")

    sub = str(claims.get("sub", "") or "").strip()
    email = normalize_email_address(str(claims.get("email", "") or ""))
    if not sub or not email:
        raise AuthInvalidCredentialsError("Google ID token is missing required identity claims.")

    claim_nonce = str(claims.get("nonce", "") or "")
    if not _nonce_matches(claim_nonce, nonce):
        raise AuthInvalidCredentialsError("Google ID token nonce validation failed.")

    try:
        exp_epoch = int(claims["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthInvalidCredentialsError("Google ID token expiry is invalid.") from exc

    if enforce_replay_check:
        _consume_google_token_replay_slot(raw_id_token=raw_id_token, exp_epoch=exp_epoch)

    return VerifiedGoogleClaims(sub=sub, email=email, aud=audience, exp=exp_epoch)


def authenticate_with_google(
    *,
    raw_id_token: str,
    nonce: str,
    accept_terms: bool | None,
    confirm_adult: bool | None,
    client_platform: str,
    request: HttpRequest,
    device_label: str = "",
) -> tuple[User, IssuedSessionPair, bool]:
    """Authenticate or register via Google ID token without silently merging email collisions."""
    enforce_ip_rate_limit(
        request,
        bucket="google_ip",
        max_attempts=int(getattr(settings, "RATE_LIMIT_GOOGLE_IP_MAX", 20)),
        window_seconds=int(getattr(settings, "RATE_LIMIT_GOOGLE_IP_WINDOW_SECONDS", 60)),
    )

    claims = verify_google_id_token(raw_id_token=raw_id_token, nonce=nonce)
    now = timezone.now()

    identity = (
        OAuthIdentity.objects.select_related("user")
        .filter(provider=OAuthIdentity.Provider.GOOGLE, provider_sub=claims.sub)
        .first()
    )
    if identity is not None:
        user = identity.user
        if user.deletion_requested_at is not None:
            raise AccountDeletionRequestedError()
        if user.status == User.Status.SUSPENDED or not user.is_active:
            raise AccountSuspendedError()
        if user.status == User.Status.DELETED:
            raise AuthInvalidCredentialsError("Account is inactive.")

        identity.last_used_at = now
        identity.save(update_fields=["last_used_at"])
        user.last_login = now
        user.save(update_fields=["last_login", "updated_at"])

        issued = issue_session_pair(
            user=user,
            client_platform=client_platform,
            request=request,
            device_label=device_label,
            auth_time=now,
        )
        record_security_event(
            event_type="auth.google.success",
            outcome=SecurityAuditEvent.Outcome.SUCCESS,
            actor_user_id=user.id,
            target_user_id=user.id,
            client_platform=client_platform,
            request=request,
            metadata={"session_id": str(issued.session.id)},
        )
        return user, issued, False

    existing_user = User.objects.filter(email=claims.email).first()
    if existing_user is not None:
        if existing_user.deletion_requested_at is not None:
            raise AccountDeletionRequestedError()
        if existing_user.status == User.Status.SUSPENDED or not existing_user.is_active:
            raise AccountSuspendedError()
        if existing_user.status == User.Status.DELETED:
            raise AuthInvalidCredentialsError("Account is inactive.")

        if OAuthIdentity.objects.filter(
            user=existing_user, provider=OAuthIdentity.Provider.GOOGLE
        ).exists():
            record_security_event(
                event_type="auth.google.sub_conflict",
                outcome=SecurityAuditEvent.Outcome.BLOCKED,
                target_user_id=existing_user.id,
                client_platform=client_platform,
                request=request,
            )
            raise StateConflictError(
                "A different Google account is already linked to this user."
            )

        raw_challenge = generate_opaque_token("rsl")
        ttl_seconds = int(getattr(settings, "OAUTH_LINK_CHALLENGE_TTL_SECONDS", 600))
        existing_verified = existing_user.email_verified_at is not None

        OAuthLinkChallenge.objects.create(
            user=existing_user,
            provider=OAuthIdentity.Provider.GOOGLE,
            provider_sub=claims.sub,
            email_at_link=claims.email,
            token_hash=hmac_token("oauth-link", raw_challenge),
            existing_account_verified=existing_verified,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        record_security_event(
            event_type="auth.google.link_required",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            target_user_id=existing_user.id,
            client_platform=client_platform,
            request=request,
            metadata={"existing_account_verified": existing_verified},
        )
        required_proof = (
            "confirm_with_password_or_session"
            if existing_verified
            else "password_or_email_verification_proof"
        )
        raise OAuthLinkConfirmationRequiredError(
            details={
                "link_challenge_token": raw_challenge,
                "existing_account_verified": existing_verified,
                "required_proof": required_proof,
            }
        )

    if accept_terms is not True or confirm_adult is not True:
        errors: dict[str, list[str]] = {}
        if accept_terms is not True:
            errors["accept_terms"] = ["You must accept the Terms and Privacy Policy."]
        if confirm_adult is not True:
            errors["confirm_adult"] = ["You must confirm that you are at least 18 years old."]
        raise drf_exceptions.ValidationError(errors)

    try:
        with transaction.atomic():
            new_user = User.objects.create_user(
                email=claims.email,
                password=None,
                status=User.Status.ACTIVE,
                email_verified_at=now,
                terms_accepted_at=now,
                last_login=now,
                can_seek_room=True,
                can_offer_room=False,
                can_list_property=False,
            )
            OAuthIdentity.objects.create(
                user=new_user,
                provider=OAuthIdentity.Provider.GOOGLE,
                provider_sub=claims.sub,
                email_at_link=claims.email,
                last_used_at=now,
            )
            issued = issue_session_pair(
                user=new_user,
                client_platform=client_platform,
                request=request,
                device_label=device_label,
                auth_time=now,
            )
            record_security_event(
                event_type="auth.google.registered",
                outcome=SecurityAuditEvent.Outcome.SUCCESS,
                actor_user_id=new_user.id,
                target_user_id=new_user.id,
                client_platform=client_platform,
                request=request,
                metadata={"session_id": str(issued.session.id)},
            )
    except IntegrityError as exc:
        if not _is_expected_oauth_uniqueness_error(exc):
            raise
        record_security_event(
            event_type="auth.google.race_conflict",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            client_platform=client_platform,
            request=request,
            metadata={"stage": "google_signup"},
        )
        raise StateConflictError(
            "An account or Google identity with these details already exists."
        ) from exc

    return new_user, issued, True


def confirm_google_link(
    *,
    link_challenge_token: str,
    confirm_link: bool,
    password: str | None,
    email_verification_token: str | None,
    authenticated_user: User | None,
    client_platform: str,
    request: HttpRequest,
    device_label: str = "",
) -> tuple[User, IssuedSessionPair]:
    """Explicitly link Google OAuth identity only after proving ownership of colliding account."""
    enforce_ip_rate_limit(
        request,
        bucket="google_ip",
        max_attempts=int(getattr(settings, "RATE_LIMIT_GOOGLE_IP_MAX", 20)),
        window_seconds=int(getattr(settings, "RATE_LIMIT_GOOGLE_IP_WINDOW_SECONDS", 60)),
    )

    if not confirm_link:
        raise drf_exceptions.ValidationError(
            {"confirm_link": ["Explicit link confirmation is required."]}
        )

    challenge_hash = hmac_token("oauth-link", link_challenge_token)
    peek_user_id = (
        OAuthLinkChallenge.objects.filter(token_hash=challenge_hash)
        .values_list("user_id", flat=True)
        .first()
    )
    if peek_user_id is None:
        record_security_event(
            event_type="auth.google.link_failed",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            client_platform=client_platform,
            request=request,
        )
        raise AuthInvalidCredentialsError("OAuth link challenge token is invalid or expired.")

    error_exc: Exception | None = None
    linked_user: User | None = None
    issued: IssuedSessionPair | None = None

    try:
        with transaction.atomic():
            # Lock order: User -> OAuthLinkChallenge -> EmailVerificationToken -> RefreshSession.
            target = User.objects.select_for_update().filter(id=peek_user_id).first()
            challenge = (
                OAuthLinkChallenge.objects.select_for_update()
                .filter(token_hash=challenge_hash, user_id=target.id)
                .first()
                if target is not None
                else None
            )
            now = timezone.now()
            if (
                target is None
                or challenge is None
                or challenge.consumed_at is not None
                or challenge.expires_at <= now
            ):
                error_exc = AuthInvalidCredentialsError(
                    "OAuth link challenge token is invalid or expired."
                )
            elif target.deletion_requested_at is not None:
                error_exc = AccountDeletionRequestedError()
            elif target.status == User.Status.SUSPENDED or not target.is_active:
                error_exc = AccountSuspendedError()
            elif target.status == User.Status.DELETED:
                error_exc = AuthInvalidCredentialsError("Account is inactive.")
            else:
                has_password_proof = bool(
                    password
                    and target.has_usable_password()
                    and target.check_password(password)
                )
                has_session_proof = bool(
                    authenticated_user is not None
                    and authenticated_user.is_authenticated
                    and authenticated_user.id == target.id
                )
                ev_row: EmailVerificationToken | None = None
                if email_verification_token:
                    ev_hash = hmac_token("email-verify", email_verification_token)
                    ev_row = (
                        EmailVerificationToken.objects.select_for_update()
                        .filter(
                            user=target,
                            token_hash=ev_hash,
                            consumed_at__isnull=True,
                            expires_at__gt=now,
                        )
                        .first()
                    )
                has_email_token_proof = ev_row is not None
                clear_unverified_password = False

                if challenge.existing_account_verified:
                    if not (has_password_proof or has_session_proof):
                        error_exc = RoomSyncAPIException(
                            "Linking an existing verified account requires password or active "
                            "session confirmation.",
                            error_code="REAUTHENTICATION_FAILED",
                            status_code=403,
                        )
                else:
                    # Unverified email collision defense: require password OR mailbox token
                    # proof. If mailbox token is used without knowing existing password, scrub
                    # any prior unverified password so a pre-hijacker loses password access.
                    if has_email_token_proof and not has_password_proof:
                        clear_unverified_password = True
                    elif has_password_proof or (
                        has_session_proof and target.email_verified_at is not None
                    ):
                        pass
                    else:
                        error_exc = RoomSyncAPIException(
                            "Linking an unverified account collision requires password "
                            "proof or email verification token ownership proof.",
                            error_code="OWNERSHIP_PROOF_REQUIRED",
                            status_code=403,
                        )

                if error_exc is None:
                    if OAuthIdentity.objects.filter(
                        provider=challenge.provider, provider_sub=challenge.provider_sub
                    ).exists() or OAuthIdentity.objects.filter(
                        user=target, provider=challenge.provider
                    ).exists():
                        error_exc = StateConflictError("Google identity is already linked.")
                    else:
                        if ev_row is not None:
                            ev_row.consumed_at = now
                            ev_row.save(update_fields=["consumed_at"])
                        challenge.consumed_at = now
                        challenge.save(update_fields=["consumed_at"])
                        OAuthIdentity.objects.create(
                            user=target,
                            provider=challenge.provider,
                            provider_sub=challenge.provider_sub,
                            email_at_link=challenge.email_at_link,
                            last_used_at=now,
                        )
                        update_fields = ["last_login", "updated_at"]
                        target.last_login = now
                        if target.email_verified_at is None:
                            target.email_verified_at = now
                            update_fields.append("email_verified_at")
                        if clear_unverified_password:
                            target.set_unusable_password()
                            update_fields.append("password")
                        target.save(update_fields=update_fields)

                        pending_revocation: PendingRedisRevocation | None = None
                        if clear_unverified_password:
                            pending_revocation = revoke_user_sessions_in_tx(
                                user=target,
                                reason="oauth_link_takeover_scrub",
                                now=now,
                            )

                        issued = issue_session_pair(
                            user=target,
                            client_platform=client_platform,
                            request=request,
                            device_label=device_label,
                            auth_time=now,
                        )
                        record_security_event(
                            event_type="auth.google.linked",
                            outcome=SecurityAuditEvent.Outcome.SUCCESS,
                            actor_user_id=target.id,
                            target_user_id=target.id,
                            client_platform=client_platform,
                            request=request,
                            metadata={
                                "session_id": str(issued.session.id),
                                "scrubbed_unverified_password": clear_unverified_password,
                            },
                        )
                        if pending_revocation is not None:
                            pending_revocation.publish()
                        linked_user = target
    except IntegrityError as exc:
        if not _is_expected_oauth_uniqueness_error(exc):
            raise
        record_security_event(
            event_type="auth.google.link_race_conflict",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            client_platform=client_platform,
            request=request,
            metadata={"stage": "google_link"},
        )
        raise StateConflictError("Google identity is already linked.") from exc

    if error_exc is not None:
        record_security_event(
            event_type="auth.google.link_failed",
            outcome=SecurityAuditEvent.Outcome.BLOCKED,
            client_platform=client_platform,
            request=request,
        )
        raise error_exc

    assert linked_user is not None and issued is not None
    return linked_user, issued
