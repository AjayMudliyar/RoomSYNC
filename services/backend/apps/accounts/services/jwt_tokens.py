from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

import jwt
from django.conf import settings

from common.exceptions import AuthInvalidCredentialsError

logger = logging.getLogger("backend.security")


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    jti: str
    iat: int
    exp: int
    iss: str
    aud: str


def _get_jwt_signing_key() -> str:
    key = str(getattr(settings, "JWT_SIGNING_KEY", "") or "").strip()
    if not key:
        raise RuntimeError("JWT_SIGNING_KEY is not configured.")
    return key


def mint_access_token(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    expires_in_seconds: int | None = None,
) -> tuple[str, int]:
    """Mint a signed HS256 access JWT carrying standard RoomSync session claims."""
    ttl = int(
        expires_in_seconds
        if expires_in_seconds is not None
        else getattr(settings, "JWT_ACCESS_TTL_SECONDS", 900)
    )
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + ttl,
        "iss": str(getattr(settings, "JWT_ISSUER", "https://api.roomsync.in")),
        "aud": str(getattr(settings, "JWT_AUDIENCE", "roomsync-clients")),
    }
    encoded = jwt.encode(
        payload,
        _get_jwt_signing_key(),
        algorithm=str(getattr(settings, "JWT_ALGORITHM", "HS256")),
    )
    return encoded, ttl


def decode_access_token(raw_token: str) -> AccessTokenClaims:
    """Strictly verify HS256 signature, issuer, audience, expiry, and required claims."""
    if not raw_token:
        raise AuthInvalidCredentialsError("Access token is missing.")
    try:
        payload = jwt.decode(
            raw_token,
            _get_jwt_signing_key(),
            algorithms=[str(getattr(settings, "JWT_ALGORITHM", "HS256"))],
            issuer=str(getattr(settings, "JWT_ISSUER", "https://api.roomsync.in")),
            audience=str(getattr(settings, "JWT_AUDIENCE", "roomsync-clients")),
            options={
                "require": ["sid", "sub", "jti", "iat", "exp", "iss", "aud"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        user_id = uuid.UUID(str(payload["sub"]))
        session_id = uuid.UUID(str(payload["sid"]))
        jti = str(payload["jti"])
        iat = int(payload["iat"])
        exp = int(payload["exp"])
        iss = str(payload["iss"])
        aud = str(payload["aud"])
        if not jti or exp <= iat:
            raise ValueError("Invalid token timestamps or jti.")
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise AuthInvalidCredentialsError("Invalid or expired access token.") from exc

    return AccessTokenClaims(
        user_id=user_id,
        session_id=session_id,
        jti=jti,
        iat=iat,
        exp=exp,
        iss=iss,
        aud=aud,
    )


def decode_expired_access_token(raw_token: str) -> AccessTokenClaims | None:
    """Verify signature and claims of an access JWT that failed strictly due to expiration."""
    if not raw_token:
        return None
    signing_key = _get_jwt_signing_key()
    algorithm = str(getattr(settings, "JWT_ALGORITHM", "HS256"))
    issuer = str(getattr(settings, "JWT_ISSUER", "https://api.roomsync.in"))
    audience = str(getattr(settings, "JWT_AUDIENCE", "roomsync-clients"))
    required = ["sid", "sub", "jti", "iat", "exp", "iss", "aud"]
    try:
        jwt.decode(
            raw_token,
            signing_key,
            algorithms=[algorithm],
            issuer=issuer,
            audience=audience,
            options={
                "require": required,
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        return None
    except jwt.ExpiredSignatureError:
        pass
    except jwt.PyJWTError:
        return None

    try:
        payload = jwt.decode(
            raw_token,
            signing_key,
            algorithms=[algorithm],
            issuer=issuer,
            audience=audience,
            options={
                "require": required,
                "verify_signature": True,
                "verify_exp": False,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        user_id = uuid.UUID(str(payload["sub"]))
        session_id = uuid.UUID(str(payload["sid"]))
        jti = str(payload["jti"])
        iat = int(payload["iat"])
        exp = int(payload["exp"])
        iss = str(payload["iss"])
        aud = str(payload["aud"])
        if not jti or exp <= iat:
            return None
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        return None

    return AccessTokenClaims(
        user_id=user_id,
        session_id=session_id,
        jti=jti,
        iat=iat,
        exp=exp,
        iss=iss,
        aud=aud,
    )

