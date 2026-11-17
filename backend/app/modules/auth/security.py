"""Password hashing and opaque token helpers."""

import secrets
from hashlib import sha256

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

SESSION_COOKIE_NAME = "helpdesk_session"

_password_hash = PasswordHash.recommended()
# A valid hash used to keep login timing similar when the account does not exist.
_DUMMY_HASH = _password_hash.hash("dummy-password-that-is-never-valid")


def hash_password(password: str) -> str:
    """Hash a password with Argon2id using the library's recommended parameters."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        return _password_hash.verify(password, password_hash)
    except UnknownHashError:
        return False


def verify_dummy_password(password: str) -> None:
    """Spend comparable time when an email does not match an account."""
    try:
        _password_hash.verify(password, _DUMMY_HASH)
    except UnknownHashError:  # pragma: no cover - defensive only
        return


def new_opaque_token() -> str:
    """Generate a high-entropy token for a session or password reset."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a bearer token before storing or looking it up."""
    return sha256(token.encode("utf-8")).hexdigest()
