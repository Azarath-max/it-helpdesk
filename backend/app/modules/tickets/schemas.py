import uuid
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.modules.tickets.models import (
    TicketPriority,
    TicketSource,
    TicketStatus,
)
from app.modules.users.models import UserRole
from app.schemas import APIModel

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 160
DESCRIPTION_MAX_LENGTH = 5000


class UserBrief(APIModel):
    """Minimal account fields embedded in ticket responses."""

    id: uuid.UUID
    name: str
    email: str
    role: UserRole


class TicketRead(APIModel):
    id: uuid.UUID
    public_ref: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str | None
    source: TicketSource
    version: int
    requester: UserBrief
    assignee: UserBrief | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    reopen_count: int


class TicketCreate(APIModel):
    title: str = Field(min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    description: str = Field(min_length=1, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str | None = Field(default=None, max_length=60)

    @field_validator("title", "description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be blank")
        return cleaned

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TicketUpdate(APIModel):
    title: str | None = Field(
        default=None, min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH
    )
    description: str | None = Field(default=None, min_length=1, max_length=DESCRIPTION_MAX_LENGTH)
    category: str | None = Field(default=None, max_length=60)
    version: int = Field(ge=1)

    @field_validator("title", "description")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be blank")
        return cleaned

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_an_editable_field(self) -> "TicketUpdate":
        editable = self.model_fields_set - {"version"}
        if not editable:
            raise ValueError("Provide at least one field to update")
        for field_name in ("title", "description"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self
