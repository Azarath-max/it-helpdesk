import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.modules.tickets.schemas import UserBrief
from app.schemas import APIModel


class AuditEventRead(APIModel):
    id: uuid.UUID
    actor_type: str
    actor: UserBrief | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="event_metadata")
    request_id: str | None
    ip: str | None
    created_at: datetime
