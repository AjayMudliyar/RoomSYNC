import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import MatchingSettings, get_settings


def verify_internal_service_token(
    settings: Annotated[MatchingSettings, Depends(get_settings)],
    x_internal_service_token: Annotated[str | None, Header()] = None,
) -> None:
    """Authenticate internal callers using constant-time token comparison."""
    expected = settings.internal_service_token.strip()
    provided = (x_internal_service_token or "").strip()
    if not expected or not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal service credentials.",
        )
