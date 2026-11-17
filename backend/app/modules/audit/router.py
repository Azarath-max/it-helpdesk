from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.modules.audit.schemas import AuditEventRead
from app.modules.audit.service import list_audit_events
from app.modules.auth.dependencies import DbSession, require_roles
from app.modules.users.models import User, UserRole
from app.schemas import Page

router = APIRouter(prefix="/api/audit-events", tags=["audit"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get(
    "",
    response_model=Page[AuditEventRead],
    summary="Query audit events (admin only)",
)
def list_audit_events_endpoint(
    db: DbSession,
    _: AdminUser,
    action: str | None = None,
    entity_type: Annotated[str | None, Query(alias="entityType")] = None,
    actor_user_id: Annotated[UUID | None, Query(alias="actorUserId")] = None,
    entity_id: Annotated[UUID | None, Query(alias="entityId")] = None,
    created_after: Annotated[datetime | None, Query(alias="from")] = None,
    created_before: Annotated[datetime | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> Page[AuditEventRead]:
    events, total = list_audit_events(
        db,
        action=action,
        entity_type=entity_type,
        actor_user_id=actor_user_id,
        entity_id=entity_id,
        created_after=created_after,
        created_before=created_before,
        page=page,
        page_size=page_size,
    )
    return Page[AuditEventRead](
        items=[AuditEventRead.model_validate(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
    )
