import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.modules.comments.models import CommentVisibility
from app.modules.tickets.schemas import UserBrief
from app.schemas import APIModel


class CommentCreate(APIModel):
    body: str = Field(min_length=1, max_length=5000)
    visibility: CommentVisibility = CommentVisibility.PUBLIC

    @field_validator("body")
    @classmethod
    def reject_blank_body(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Comment body must not be blank")
        return cleaned


class CommentRead(APIModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author: UserBrief | None
    body: str
    visibility: CommentVisibility
    created_at: datetime
    deleted_at: datetime | None
