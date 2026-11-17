"""Authentication business rules: users, sessions, and password resets."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.auth.models import PasswordResetToken, UserSession
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.security import (
    hash_password,
    hash_token,
    new_opaque_token,
    verify_dummy_password,
    verify_password,
)
from app.modules.users.models import User, UserRole

LAST_USED_UPDATE_INTERVAL = timedelta(minutes=5)


def find_user_by_email(db: Session, email: str) -> User | None:
    """Look up an account by email using the case-insensitive citext column."""
    return db.scalar(select(User).where(User.email == email))


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a requester account. Self-registration never grants elevated roles."""
    if find_user_by_email(db, str(payload.email)) is not None:
        raise AppError(
            "EMAIL_TAKEN",
            "An account with this email already exists",
            status_code=409,
        )

    user = User(
        email=str(payload.email),
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "EMAIL_TAKEN",
            "An account with this email already exists",
            status_code=409,
        ) from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the account for valid credentials, otherwise None.

    Unknown emails and inactive accounts still run a password verification so
    callers cannot distinguish them by timing.
    """
    user = find_user_by_email(db, email)
    if user is None:
        verify_dummy_password(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def create_session(db: Session, user: User, user_agent: str | None) -> tuple[str, UserSession]:
    """Create a session and return the raw token plus the row.

    The raw token is only ever sent to the client in the HttpOnly cookie.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    raw_token = new_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        user_agent=(user_agent or "")[:255] or None,
        expires_at=now + timedelta(days=settings.session_ttl_days),
        last_used_at=now,
    )
    db.add(session)
    db.commit()
    return raw_token, session


def resolve_session(db: Session, raw_token: str) -> UserSession | None:
    """Resolve a raw session token to an active session, or None."""
    session = db.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(UserSession.token_hash == hash_token(raw_token))
    )
    if session is None:
        return None

    now = datetime.now(UTC)
    if session.expires_at <= now or not session.user.is_active:
        db.delete(session)
        db.commit()
        return None

    if session.last_used_at <= now - LAST_USED_UPDATE_INTERVAL:
        session.last_used_at = now
        db.commit()

    return session


def revoke_session(db: Session, session: UserSession) -> None:
    """Delete one session."""
    db.delete(session)
    db.commit()


def create_password_reset_token(db: Session, user: User) -> str:
    """Issue a single-use reset token and return the raw value."""
    settings = get_settings()
    now = datetime.now(UTC)

    # Only the newest link should work.
    db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    raw_token = new_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
        )
    )
    db.commit()
    return raw_token


def reset_password(db: Session, raw_token: str, new_password: str) -> User:
    """Consume a reset token, change the password, and revoke all sessions."""
    now = datetime.now(UTC)
    record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(raw_token))
        .with_for_update()
    )
    if record is None or record.used_at is not None or record.expires_at <= now:
        raise AppError(
            "INVALID_RESET_TOKEN",
            "This password reset link is invalid or has expired",
            status_code=400,
        )

    user = db.get(User, record.user_id)
    if user is None:
        raise AppError(
            "INVALID_RESET_TOKEN",
            "This password reset link is invalid or has expired",
            status_code=400,
        )

    user.password_hash = hash_password(new_password)
    record.used_at = now
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
    return user


def revoke_all_sessions(db: Session, user_id: object) -> None:
    """Revoke every session for an account."""
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    db.commit()
