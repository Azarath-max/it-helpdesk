"""Reusable FastAPI dependencies for authentication and authorization."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.modules.auth.models import UserSession
from app.modules.auth.security import SESSION_COOKIE_NAME
from app.modules.auth.service import resolve_session
from app.modules.users.models import User, UserRole

DbSession = Annotated[Session, Depends(get_db)]


def get_current_session(request: Request, db: DbSession) -> UserSession:
    """Resolve the session cookie to a live session or raise 401."""
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        raise AppError("UNAUTHENTICATED", "Authentication required", status_code=401)

    session = resolve_session(db, raw_token)
    if session is None:
        raise AppError(
            "UNAUTHENTICATED",
            "Your session is invalid or has expired",
            status_code=401,
        )
    return session


CurrentSession = Annotated[UserSession, Depends(get_current_session)]


def get_current_user(session: CurrentSession) -> User:
    """Return the authenticated account for this request."""
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Build a dependency that allows only the given roles."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError(
                "FORBIDDEN",
                "You do not have permission to perform this action",
                status_code=403,
            )
        return user

    return dependency
