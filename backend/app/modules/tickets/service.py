"""Ticket business rules: creation, scoped reads, edits, and audit events."""

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.modules.audit.service import record_audit
from app.modules.comments.models import Comment, CommentVisibility
from app.modules.tickets.models import (
    Ticket,
    TicketPriority,
    TicketSource,
    TicketStatus,
)
from app.modules.tickets.schemas import (
    AssignTicketRequest,
    TicketCreate,
    TicketUpdate,
    TransitionTicketRequest,
)
from app.modules.users.models import User, UserRole

STAFF_ROLES = frozenset({UserRole.AGENT, UserRole.ADMIN})
AUDITED_TICKET_FIELDS = (
    "public_ref",
    "title",
    "description",
    "status",
    "priority",
    "category",
    "resolution_note",
    "requester_id",
    "assignee_id",
    "version",
)

_TICKET_LOAD_OPTIONS = (
    selectinload(Ticket.requester),
    selectinload(Ticket.assignee),
)


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _snapshot(ticket: Ticket) -> dict[str, Any]:
    return {field: _json_value(getattr(ticket, field)) for field in AUDITED_TICKET_FIELDS}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _can_view(actor: User, ticket: Ticket) -> bool:
    return (
        actor.role in STAFF_ROLES
        or ticket.requester_id == actor.id
        or ticket.assignee_id == actor.id
    )


def _ticket_filters(
    actor: User,
    *,
    status: TicketStatus | None,
    priority: TicketPriority | None,
    query: str | None,
) -> list[Any]:
    filters: list[Any] = []

    if actor.role == UserRole.USER:
        filters.append(Ticket.requester_id == actor.id)
    if status is not None:
        filters.append(Ticket.status == status)
    if priority is not None:
        filters.append(Ticket.priority == priority)
    if query:
        term = f"%{_escape_like(query.strip())}%"
        filters.append(
            or_(
                Ticket.title.ilike(term, escape="\\"),
                Ticket.description.ilike(term, escape="\\"),
                Ticket.public_ref.ilike(term, escape="\\"),
            )
        )
    return filters


def list_tickets(
    db: Session,
    actor: User,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    """Return a page of visible tickets and the total visible count."""
    filters = _ticket_filters(actor, status=status, priority=priority, query=query)

    total = db.scalar(select(func.count()).select_from(Ticket).where(*filters)) or 0

    tickets = db.scalars(
        select(Ticket)
        .options(*_TICKET_LOAD_OPTIONS)
        .where(*filters)
        .order_by(Ticket.created_at.desc(), Ticket.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(tickets), total


def get_ticket_for_actor(db: Session, actor: User, ticket_id: uuid.UUID) -> Ticket:
    """Load a ticket the actor may see, hiding other requesters' tickets as 404."""
    ticket = db.scalar(select(Ticket).options(*_TICKET_LOAD_OPTIONS).where(Ticket.id == ticket_id))
    if ticket is None or not _can_view(actor, ticket):
        raise AppError("TICKET_NOT_FOUND", "Ticket not found", status_code=404)
    db.refresh(ticket, attribute_names=["requester", "assignee"])
    return ticket


def create_ticket(
    db: Session,
    actor: User,
    payload: TicketCreate,
    *,
    request_id: str | None,
    ip: str | None,
) -> Ticket:
    """Create an OPEN ticket for the authenticated requester."""
    next_ref = int(db.scalar(text("SELECT nextval('ticket_ref_seq')")) or 0)
    ticket = Ticket(
        public_ref=f"HD-{next_ref:06d}",
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        category=payload.category,
        status=TicketStatus.OPEN,
        source=TicketSource.WEB,
        requester_id=actor.id,
    )
    db.add(ticket)
    db.flush()

    record_audit(
        db,
        action="ticket.created",
        entity_type="ticket",
        entity_id=ticket.id,
        actor=actor,
        after=_snapshot(ticket),
        request_id=request_id,
        ip=ip,
    )
    db.commit()

    return get_ticket_for_actor(db, actor, ticket.id)


def update_ticket(
    db: Session,
    actor: User,
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    *,
    request_id: str | None,
    ip: str | None,
) -> Ticket:
    """Edit ticket text fields with ownership, status, and version checks."""
    ticket = db.scalar(
        select(Ticket)
        .options(*_TICKET_LOAD_OPTIONS)
        .where(Ticket.id == ticket_id)
        .with_for_update()
    )
    if ticket is None:
        raise AppError("TICKET_NOT_FOUND", "Ticket not found", status_code=404)

    if actor.role not in STAFF_ROLES and ticket.requester_id != actor.id:
        raise AppError("TICKET_NOT_FOUND", "Ticket not found", status_code=404)

    if actor.role == UserRole.USER and ticket.status != TicketStatus.OPEN:
        raise AppError(
            "TICKET_NOT_EDITABLE",
            "Only OPEN tickets can be edited by the requester",
            status_code=409,
        )

    if ticket.version != payload.version:
        raise AppError(
            "TICKET_CHANGED",
            "This ticket changed since you loaded it. Reload and try again",
            status_code=409,
        )

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for field in payload.model_fields_set - {"version"}:
        new_value = getattr(payload, field)
        old_value = getattr(ticket, field)
        if old_value == new_value:
            continue
        before[field] = _json_value(old_value)
        after[field] = _json_value(new_value)
        setattr(ticket, field, new_value)

    if not after:
        return ticket

    ticket.version += 1
    record_audit(
        db,
        action="ticket.updated",
        entity_type="ticket",
        entity_id=ticket.id,
        actor=actor,
        before=before,
        after=after,
        request_id=request_id,
        ip=ip,
    )
    db.commit()

    return get_ticket_for_actor(db, actor, ticket.id)


_TRANSITION_RULES: dict[tuple[TicketStatus, TicketStatus], set[UserRole]] = {
    (TicketStatus.OPEN, TicketStatus.IN_PROGRESS): {UserRole.AGENT, UserRole.ADMIN},
    (TicketStatus.OPEN, TicketStatus.CLOSED): {UserRole.AGENT, UserRole.ADMIN},
    (TicketStatus.IN_PROGRESS, TicketStatus.WAITING_ON_USER): {
        UserRole.AGENT,
        UserRole.ADMIN,
    },
    (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED): {
        UserRole.AGENT,
        UserRole.ADMIN,
    },
    (TicketStatus.IN_PROGRESS, TicketStatus.OPEN): {UserRole.ADMIN},
    (TicketStatus.WAITING_ON_USER, TicketStatus.IN_PROGRESS): {
        UserRole.AGENT,
        UserRole.ADMIN,
    },
    (TicketStatus.WAITING_ON_USER, TicketStatus.RESOLVED): {
        UserRole.AGENT,
        UserRole.ADMIN,
    },
    (TicketStatus.WAITING_ON_USER, TicketStatus.CLOSED): {UserRole.ADMIN},
    (TicketStatus.RESOLVED, TicketStatus.CLOSED): {
        UserRole.USER,
        UserRole.AGENT,
        UserRole.ADMIN,
    },
    (TicketStatus.RESOLVED, TicketStatus.OPEN): {
        UserRole.USER,
        UserRole.AGENT,
        UserRole.ADMIN,
    },
    (TicketStatus.CLOSED, TicketStatus.OPEN): {UserRole.ADMIN},
}

_REQUIRED_TRANSITION_FIELDS: dict[tuple[TicketStatus, TicketStatus], tuple[str, ...]] = {
    (TicketStatus.OPEN, TicketStatus.CLOSED): ("resolution_note",),
    (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED): ("resolution_note",),
    (TicketStatus.IN_PROGRESS, TicketStatus.WAITING_ON_USER): ("comment",),
    (TicketStatus.IN_PROGRESS, TicketStatus.OPEN): ("reason",),
    (TicketStatus.WAITING_ON_USER, TicketStatus.CLOSED): ("reason",),
    (TicketStatus.RESOLVED, TicketStatus.OPEN): ("reason",),
    (TicketStatus.CLOSED, TicketStatus.OPEN): ("reason",),
}


def _can_transition(actor: User, ticket: Ticket, target: TicketStatus) -> bool:
    allowed_roles = _TRANSITION_RULES.get((ticket.status, target))
    if not allowed_roles:
        return False
    if actor.role == UserRole.ADMIN:
        return True
    if actor.role == UserRole.AGENT:
        return UserRole.AGENT in allowed_roles
    if actor.role == UserRole.USER:
        return UserRole.USER in allowed_roles and ticket.requester_id == actor.id
    return False


def transition_ticket(
    db: Session,
    actor: User,
    ticket_id: uuid.UUID,
    payload: TransitionTicketRequest,
    *,
    request_id: str | None,
    ip: str | None,
) -> Ticket:
    """Apply one allowed status transition with optimistic concurrency."""
    ticket = db.scalar(
        select(Ticket)
        .options(*_TICKET_LOAD_OPTIONS)
        .where(Ticket.id == ticket_id)
        .with_for_update()
    )
    if ticket is None or not _can_view(actor, ticket):
        raise AppError("TICKET_NOT_FOUND", "Ticket not found", status_code=404)

    if payload.status == ticket.status:
        if ticket.version != payload.version:
            raise AppError(
                "TICKET_CHANGED",
                "This ticket changed since you loaded it. Reload and try again",
                status_code=409,
            )
        return ticket

    if not _can_transition(actor, ticket, payload.status):
        raise AppError(
            "INVALID_STATUS_TRANSITION",
            "This status change is not allowed",
            status_code=409,
        )

    if ticket.version != payload.version:
        raise AppError(
            "TICKET_CHANGED",
            "This ticket changed since you loaded it. Reload and try again",
            status_code=409,
        )

    for field_name in _REQUIRED_TRANSITION_FIELDS.get((ticket.status, payload.status), ()):
        if getattr(payload, field_name) is None:
            raise AppError(
                "MISSING_TRANSITION_FIELD",
                f"{field_name} is required for this transition",
                status_code=422,
            )

    if (
        ticket.status == TicketStatus.OPEN
        and payload.status == TicketStatus.IN_PROGRESS
        and ticket.assignee_id is None
    ):
        raise AppError(
            "ASSIGNEE_REQUIRED",
            "Assign the ticket before moving it to in progress",
            status_code=422,
        )

    before = _snapshot(ticket)
    now = datetime.now(UTC)
    old_status = ticket.status

    if payload.status == TicketStatus.IN_PROGRESS:
        ticket.status = TicketStatus.IN_PROGRESS
    elif payload.status == TicketStatus.WAITING_ON_USER:
        ticket.status = TicketStatus.WAITING_ON_USER
        if payload.comment:
            db.add(
                Comment(
                    ticket_id=ticket.id,
                    author_id=actor.id,
                    body=payload.comment,
                    visibility=CommentVisibility.PUBLIC,
                )
            )
    elif payload.status == TicketStatus.RESOLVED:
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = now
        if payload.resolution_note is not None:
            ticket.resolution_note = payload.resolution_note
    elif payload.status == TicketStatus.CLOSED:
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = now
        if payload.resolution_note is not None:
            ticket.resolution_note = payload.resolution_note
    elif payload.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.OPEN
        if old_status == TicketStatus.IN_PROGRESS:
            ticket.assignee_id = None
        if old_status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}:
            ticket.resolved_at = None
            ticket.closed_at = None
            ticket.reopen_count += 1
        if old_status == TicketStatus.RESOLVED:
            ticket.closed_at = None

    ticket.version += 1
    after = _snapshot(ticket)

    record_audit(
        db,
        action="ticket.status_changed",
        entity_type="ticket",
        entity_id=ticket.id,
        actor=actor,
        before=before,
        after=after,
        metadata={
            key: value
            for key, value in {
                "reason": payload.reason,
                "resolution_note": payload.resolution_note,
                "comment": payload.comment,
            }.items()
            if value is not None
        },
        request_id=request_id,
        ip=ip,
    )
    db.commit()

    return get_ticket_for_actor(db, actor, ticket.id)


def assign_ticket(
    db: Session,
    actor: User,
    ticket_id: uuid.UUID,
    payload: AssignTicketRequest,
    *,
    request_id: str | None,
    ip: str | None,
) -> Ticket:
    """Assign or unassign a ticket. Agents and admins only."""
    if actor.role not in {UserRole.AGENT, UserRole.ADMIN}:
        raise AppError(
            "FORBIDDEN",
            "You do not have permission to perform this action",
            status_code=403,
        )

    ticket = db.scalar(
        select(Ticket)
        .options(*_TICKET_LOAD_OPTIONS)
        .where(Ticket.id == ticket_id)
        .with_for_update()
    )
    if ticket is None or not _can_view(actor, ticket):
        raise AppError("TICKET_NOT_FOUND", "Ticket not found", status_code=404)

    if ticket.version != payload.version:
        raise AppError(
            "TICKET_CHANGED",
            "This ticket changed since you loaded it. Reload and try again",
            status_code=409,
        )

    if payload.assignee_id is None and actor.role != UserRole.ADMIN:
        raise AppError(
            "FORBIDDEN",
            "Only admins can unassign a ticket",
            status_code=403,
        )

    if payload.assignee_id is not None:
        candidate = db.get(User, payload.assignee_id)
        if (
            candidate is None
            or not candidate.is_active
            or candidate.role not in {UserRole.AGENT, UserRole.ADMIN}
        ):
            raise AppError(
                "INVALID_ASSIGNEE",
                "Assignee must be an active agent or admin",
                status_code=422,
            )
        pass

    if ticket.assignee_id == payload.assignee_id:
        return ticket

    before = _snapshot(ticket)
    ticket.assignee_id = payload.assignee_id
    ticket.version += 1
    after = _snapshot(ticket)

    record_audit(
        db,
        action="ticket.assigned",
        entity_type="ticket",
        entity_id=ticket.id,
        actor=actor,
        before=before,
        after=after,
        request_id=request_id,
        ip=ip,
    )
    db.commit()

    return get_ticket_for_actor(db, actor, ticket.id)
