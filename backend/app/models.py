"""ORM model registry.

Import every model module here so Alembic autogenerate can discover the tables.
"""

from app.core.db import Base
from app.modules.auth.models import PasswordResetToken, UserSession
from app.modules.users.models import User, UserRole

__all__ = ["Base", "PasswordResetToken", "User", "UserRole", "UserSession"]
