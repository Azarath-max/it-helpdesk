import uuid
from typing import Any

from pydantic import EmailStr, Field, field_validator

from app.modules.tickets.models import TicketPriority, TicketStatus
from app.schemas import APIModel


class WebhookRequester(APIModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name must not be blank")
        return cleaned


class WebhookTicketPayload(APIModel):
    schema_version: int = Field(alias="schemaVersion")
    source: str = Field(min_length=1, max_length=80)
    external_id: str = Field(alias="externalId", min_length=1, max_length=200)
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    requester: WebhookRequester
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str | None = Field(default=None, max_length=60)
    metadata: dict[str, Any] | None = None

    @field_validator("title", "description", "source", "external_id")
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


class WebhookTicketResponse(APIModel):
    ticket_id: uuid.UUID
    status: TicketStatus
    duplicate: bool
