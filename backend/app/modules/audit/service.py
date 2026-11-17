"""Append-only audit writer.

Callers add audit events inside the same transaction as the domain change and
commit once, so a mutation can never be recorded without its audit trail.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

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
