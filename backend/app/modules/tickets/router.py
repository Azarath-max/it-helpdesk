import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi import status as http_status

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.tickets.models import TicketPriority, TicketStatus
from app.modules.tickets.schemas import TicketCreate, TicketRead, TicketUpdate
from app.modules.tickets.service import (
    create_ticket as create_ticket_record,
)
from app.modules.tickets.service import (
    get_ticket_for_actor,
)
from app.modules.tickets.service import (
    list_tickets as list_ticket_records,
)
from app.modules.tickets.service import (
    update_ticket as update_ticket_record,
)
from app.schemas import Page

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _audit_context(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client is not None else None
    return (str(request_id) if request_id else None, ip)


@router.get(
    "",
    response_model=Page[TicketRead],
    summary="List visible tickets",
)
def list_tickets(
    db: DbSession,
    actor: CurrentUser,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> Page[TicketRead]:
    tickets, total = list_ticket_records(
        db,
        actor,
        status=status,
        priority=priority,
        query=q,
        page=page,
        page_size=page_size,
    )
    return Page[TicketRead](
        items=[TicketRead.model_validate(ticket) for ticket in tickets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=TicketRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a ticket for the current requester",
)
def create_ticket(
    payload: TicketCreate,
    request: Request,
    response: Response,
    db: DbSession,
    actor: CurrentUser,
) -> TicketRead:
    request_id, ip = _audit_context(request)
    ticket = create_ticket_record(db, actor, payload, request_id=request_id, ip=ip)
    response.headers["Location"] = f"/api/tickets/{ticket.id}"
    return TicketRead.model_validate(ticket)


@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Read one visible ticket",
)
def get_ticket(
    ticket_id: uuid.UUID,
    db: DbSession,
    actor: CurrentUser,
) -> TicketRead:
    return TicketRead.model_validate(get_ticket_for_actor(db, actor, ticket_id))


@router.patch(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Edit ticket text fields",
)
def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    request: Request,
    db: DbSession,
    actor: CurrentUser,
) -> TicketRead:
    request_id, ip = _audit_context(request)
    ticket = update_ticket_record(
        db,
        actor,
        ticket_id,
        payload,
        request_id=request_id,
        ip=ip,
    )
    return TicketRead.model_validate(ticket)
