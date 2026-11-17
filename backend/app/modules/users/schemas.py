import uuid
from datetime import datetime

from app.modules.users.models import UserRole
from app.schemas import APIModel


class UserRead(APIModel):
    """Safe public representation of an account."""

    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime
