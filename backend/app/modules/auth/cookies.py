"""Session cookie helpers."""

from fastapi import Response

from app.core.config import get_settings
from app.modules.auth.security import SESSION_COOKIE_NAME


def set_session_cookie(response: Response, raw_token: str) -> None:
    """Attach the opaque session token as an HttpOnly cookie."""
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
    )


def clear_session_cookie(response: Response) -> None:
    """Expire the session cookie in the browser."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=get_settings().environment == "production",
    )
