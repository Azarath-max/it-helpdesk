"""Append-only audit writer and query helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.audit.models import AuditActorType, AuditEvent
from app.modules.users.models import User


def record_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor: User | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    ip: str | None = None,
) -> AuditEvent:
    """Stage an audit event in the current transaction."""
    event = AuditEvent(
        actor_type=AuditActorType.USER if actor is not None else AuditActorType.SYSTEM,
        actor_user_id=actor.id if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        event_metadata=metadata,
        request_id=request_id,
        ip=ip,
    )
    db.add(event)
    db.flush()
    return event


def list_audit_events(
    db: Session,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AuditEvent], int]:
    """Return a filtered, paginated page of audit events."""
    filters = []
    if action is not None:
        filters.append(AuditEvent.action == action)
    if entity_type is not None:
        filters.append(AuditEvent.entity_type == entity_type)
    if actor_user_id is not None:
        filters.append(AuditEvent.actor_user_id == actor_user_id)
    if entity_id is not None:
        filters.append(AuditEvent.entity_id == entity_id)
    if created_after is not None:
        filters.append(AuditEvent.created_at >= created_after)
    if created_before is not None:
        filters.append(AuditEvent.created_at <= created_before)

    from sqlalchemy import func

    total = db.scalar(select(func.count()).select_from(AuditEvent).where(*filters)) or 0

    events = db.scalars(
        select(AuditEvent)
        .options(selectinload(AuditEvent.actor))
        .where(*filters)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(events), total
