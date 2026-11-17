import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent
from app.modules.tickets.models import Ticket, TicketPriority, TicketStatus
from app.modules.users.models import UserRole
from tests.helpers import login


def create_ticket(
    client: TestClient,
    *,
    title: str = "Laptop will not boot",
    description: str = "The laptop shows a black screen after the logo.",
    **overrides: Any,
) -> Any:
    body = {"title": title, "description": description, **overrides}
    return client.post("/api/tickets", json=body)


def test_ticket_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/api/tickets").status_code == 401
    assert client.post("/api/tickets", json={}).status_code == 401


def test_requester_creates_open_ticket_with_audit(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("ticket.owner@example.com", name="Ticket Owner")
    assert login(client, owner.email).status_code == 200

    response = create_ticket(
        client,
        title="Printer is offline",
        description="The office printer is unreachable from my desk.",
        priority="HIGH",
        category=" Hardware ",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["publicRef"].startswith("HD-")
    assert len(body["publicRef"]) == 9
    assert body["title"] == "Printer is offline"
    assert body["status"] == "OPEN"
    assert body["priority"] == "HIGH"
    assert body["category"] == "Hardware"
    assert body["source"] == "web"
    assert body["version"] == 1
    assert body["requester"]["email"] == owner.email
    assert body["assignee"] is None
    assert response.headers["location"] == f"/api/tickets/{body['id']}"

    ticket = db.get(Ticket, uuid.UUID(body["id"]))
    assert ticket is not None
    assert ticket.requester_id == owner.id

    event = db.scalar(select(AuditEvent).where(AuditEvent.entity_id == ticket.id))
    assert event is not None
    assert event.action == "ticket.created"
    assert event.actor_user_id == owner.id
    assert event.after is not None
    assert event.after["title"] == "Printer is offline"
    assert event.before is None


def test_create_rejects_workflow_and_identity_fields(
    client: TestClient,
    make_user,
) -> None:
    make_user("field.tester@example.com")
    assert login(client, "field.tester@example.com").status_code == 200

    response = client.post(
        "/api/tickets",
        json={
            "title": "Injected fields",
            "description": "Trying to set server-owned values.",
            "status": "CLOSED",
            "requesterId": str(uuid.uuid4()),
            "assigneeId": str(uuid.uuid4()),
            "version": 99,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_user_list_is_scoped_and_staff_see_everything(
    client: TestClient,
    make_user,
) -> None:
    first = make_user("scope.one@example.com", name="Scope One")
    second = make_user("scope.two@example.com", name="Scope Two")
    make_user("scope.agent@example.com", role=UserRole.AGENT)
    marker = f"scope-{uuid.uuid4().hex[:8]}"

    assert login(client, first.email).status_code == 200
    first_ticket = create_ticket(client, title=f"{marker} first").json()

    assert login(client, second.email).status_code == 200
    second_ticket = create_ticket(client, title=f"{marker} second").json()

    mine = client.get("/api/tickets", params={"q": marker, "pageSize": 100})
    assert mine.status_code == 200
    items = mine.json()["items"]
    assert [item["publicRef"] for item in items] == [second_ticket["publicRef"]]
    assert mine.json()["total"] == 1

    assert login(client, "scope.agent@example.com").status_code == 200
    everything = client.get("/api/tickets", params={"q": marker, "pageSize": 100})
    assert everything.status_code == 200
    refs = {item["publicRef"] for item in everything.json()["items"]}
    assert refs == {first_ticket["publicRef"], second_ticket["publicRef"]}
    assert everything.json()["total"] == 2


def test_filters_by_priority_status_and_search(
    client: TestClient,
    make_user,
) -> None:
    make_user("filter.agent@example.com", role=UserRole.AGENT)
    marker = f"filter-{uuid.uuid4().hex[:8]}"
    assert login(client, "filter.agent@example.com").status_code == 200
    create_ticket(client, title=f"{marker} urgent", priority="URGENT")
    create_ticket(client, title=f"{marker} low", priority="LOW")

    urgent = client.get(
        "/api/tickets",
        params={"q": marker, "priority": "URGENT"},
    )
    assert urgent.status_code == 200
    assert urgent.json()["total"] == 1
    assert urgent.json()["items"][0]["priority"] == "URGENT"

    open_tickets = client.get(
        "/api/tickets",
        params={"q": marker, "status": "OPEN"},
    )
    assert open_tickets.json()["total"] == 2

    resolved = client.get(
        "/api/tickets",
        params={"q": marker, "status": "RESOLVED"},
    )
    assert resolved.json()["total"] == 0

    invalid = client.get("/api/tickets", params={"status": "DONE"})
    assert invalid.status_code == 422


def test_list_paginates(client: TestClient, make_user) -> None:
    make_user("page.agent@example.com", role=UserRole.AGENT)
    marker = f"page-{uuid.uuid4().hex[:8]}"
    assert login(client, "page.agent@example.com").status_code == 200
    for index in range(5):
        create_ticket(client, title=f"{marker} {index}")

    response = client.get(
        "/api/tickets",
        params={"q": marker, "page": 2, "pageSize": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 2
    assert body["pageSize"] == 2


def test_detail_is_visible_to_owner_and_staff_only(
    client: TestClient,
    make_user,
) -> None:
    owner = make_user("detail.owner@example.com")
    make_user("detail.other@example.com")
    make_user("detail.agent@example.com", role=UserRole.AGENT)

    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client).json()
    path = f"/api/tickets/{ticket['id']}"

    assert client.get(path).status_code == 200

    assert login(client, "detail.other@example.com").status_code == 200
    hidden = client.get(path)
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "TICKET_NOT_FOUND"

    assert login(client, "detail.agent@example.com").status_code == 200
    assert client.get(path).status_code == 200


def test_owner_edits_open_ticket_and_audit_records_the_diff(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("edit.owner@example.com")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client).json()

    response = client.patch(
        f"/api/tickets/{ticket['id']}",
        json={"title": "Laptop boots after a hard reset", "version": 1},
        headers={"X-Request-ID": "test-request-42"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Laptop boots after a hard reset"
    assert updated["version"] == 2

    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_id == uuid.UUID(ticket["id"]))
        .order_by(AuditEvent.created_at)
    ).all()
    assert [event.action for event in events] == ["ticket.created", "ticket.updated"]
    update_event = events[-1]
    assert update_event.actor_user_id == owner.id
    assert update_event.before == {"title": ticket["title"]}
    assert update_event.after == {"title": "Laptop boots after a hard reset"}
    assert update_event.request_id == "test-request-42"

    no_op = client.patch(
        f"/api/tickets/{ticket['id']}",
        json={"title": "Laptop boots after a hard reset", "version": 2},
    )
    assert no_op.status_code == 200
    assert no_op.json()["version"] == 2
    assert (
        db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.entity_id == uuid.UUID(ticket["id"]))
        )
        == 2
    )


def test_stale_version_and_foreign_edit_are_rejected(
    client: TestClient,
    make_user,
) -> None:
    owner = make_user("conflict.owner@example.com")
    make_user("conflict.other@example.com")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client).json()
    path = f"/api/tickets/{ticket['id']}"

    assert client.patch(path, json={"title": "First edit wins", "version": 1}).status_code == 200

    stale = client.patch(path, json={"title": "Stale edit loses", "version": 1})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "TICKET_CHANGED"

    assert login(client, "conflict.other@example.com").status_code == 200
    foreign = client.patch(path, json={"title": "Not my ticket", "version": 2})
    assert foreign.status_code == 404


def test_requester_cannot_edit_after_open_but_staff_can(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("locked.owner@example.com")
    agent = make_user("locked.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client).json()
    path = f"/api/tickets/{ticket['id']}"

    record = db.get(Ticket, uuid.UUID(ticket["id"]))
    assert record is not None
    record.status = TicketStatus.IN_PROGRESS
    record.assignee_id = agent.id
    db.commit()

    locked = client.patch(path, json={"title": "Requester edit", "version": 1})
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "TICKET_NOT_EDITABLE"

    assert login(client, agent.email).status_code == 200
    staff_edit = client.patch(path, json={"title": "Agent edit", "version": 1})
    assert staff_edit.status_code == 200
    assert staff_edit.json()["title"] == "Agent edit"


def test_update_rejects_workflow_fields_and_empty_changes(
    client: TestClient,
    make_user,
) -> None:
    make_user("patch.guard@example.com")
    assert login(client, "patch.guard@example.com").status_code == 200
    ticket = create_ticket(client).json()
    path = f"/api/tickets/{ticket['id']}"

    priority = client.patch(
        path,
        json={"priority": TicketPriority.URGENT.value, "version": 1},
    )
    assert priority.status_code == 422

    status = client.patch(
        path,
        json={"status": TicketStatus.RESOLVED.value, "version": 1},
    )
    assert status.status_code == 422

    empty = client.patch(path, json={"version": 1})
    assert empty.status_code == 422

    null_title = client.patch(path, json={"title": None, "version": 1})
    assert null_title.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   ", "description": "Blank title"},
        {"title": "ab", "description": "Too short"},
        {"title": "Valid title", "description": "x" * 5001},
        {"title": "Valid title", "description": "Valid", "category": "x" * 61},
    ],
)
def test_create_validation(
    client: TestClient,
    make_user,
    payload: dict[str, str],
) -> None:
    make_user("validation.ticket@example.com")
    assert login(client, "validation.ticket@example.com").status_code == 200

    response = client.post("/api/tickets", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_ticket_is_404_for_staff(
    client: TestClient,
    make_user,
) -> None:
    make_user("missing.agent@example.com", role=UserRole.AGENT)
    assert login(client, "missing.agent@example.com").status_code == 200

    response = client.get(f"/api/tickets/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TICKET_NOT_FOUND"
