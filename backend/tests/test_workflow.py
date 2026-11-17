import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent
from app.modules.comments.models import Comment
from app.modules.users.models import UserRole
from tests.helpers import login


def create_ticket(client: TestClient, **overrides) -> dict:
    body = {"title": "Workflow ticket", "description": "Needs workflow coverage."}
    body.update(overrides)
    response = client.post("/api/tickets", json=body)
    assert response.status_code == 201
    return response.json()


def test_transition_requires_assignee_for_in_progress(
    client: TestClient,
    make_user,
) -> None:
    owner = make_user("wf.owner@example.com")
    agent = make_user("wf.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    assert login(client, agent.email).status_code == 200
    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 1},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ASSIGNEE_REQUIRED"


def test_agent_can_claim_and_start_work(
    client: TestClient,
    make_user,
) -> None:
    owner = make_user("claim.owner@example.com")
    agent = make_user("claim.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    assert login(client, agent.email).status_code == 200
    assigned = client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )
    assert assigned.status_code == 200
    assert assigned.json()["assignee"]["id"] == str(agent.id)

    started = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 2},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "IN_PROGRESS"


def test_invalid_transition_is_rejected(client: TestClient, make_user) -> None:
    owner = make_user("invalid.owner@example.com")
    agent = make_user("invalid.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, agent.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )

    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "RESOLVED", "version": 2},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_user_cannot_transition_other_than_reopen_own_resolved(
    client: TestClient,
    make_user,
) -> None:
    owner = make_user("perm.owner@example.com")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    forbidden = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "CLOSED", "version": 1, "resolutionNote": "done"},
    )
    assert forbidden.status_code == 409
    assert forbidden.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_admin_close_and_reopen_updates_timestamps_and_counter(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("reopen.owner@example.com")
    admin = make_user("reopen.admin@example.com", role=UserRole.ADMIN)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    assert login(client, admin.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(admin.id), "version": 1},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 2},
    )
    resolved = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={
            "status": "RESOLVED",
            "version": 3,
            "resolutionNote": "Fixed by rebooting the router.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolvedAt"] is not None

    closed = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "CLOSED", "version": 4},
    )
    assert closed.status_code == 200
    assert closed.json()["closedAt"] is not None

    reopened = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "OPEN", "version": 5, "reason": "Issue returned."},
    )
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["status"] == "OPEN"
    assert body["resolvedAt"] is None
    assert body["closedAt"] is None
    assert body["reopenCount"] == 1


def test_waiting_on_user_requires_comment_and_can_resolve(
    client: TestClient,
    make_user,
) -> None:
    owner = make_user("wait.owner@example.com")
    agent = make_user("wait.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, agent.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 2},
    )

    missing = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "WAITING_ON_USER", "version": 3},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "MISSING_TRANSITION_FIELD"

    waiting = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={
            "status": "WAITING_ON_USER",
            "version": 3,
            "comment": "Please confirm the serial number.",
        },
    )
    assert waiting.status_code == 200
    assert waiting.json()["status"] == "WAITING_ON_USER"

    resolved = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={
            "status": "RESOLVED",
            "version": 4,
            "resolutionNote": "Serial number received and fixed.",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"


def test_no_op_transition_does_not_bump_version_or_audit(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("noop.owner@example.com")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    before_count = db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.entity_id == uuid.UUID(ticket["id"]))
    )

    response = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "OPEN", "version": 1},
    )
    assert response.status_code == 200
    assert response.json()["version"] == 1

    after_count = db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.entity_id == uuid.UUID(ticket["id"]))
    )
    assert after_count == before_count


def test_stale_transition_version_is_rejected(client: TestClient, make_user) -> None:
    owner = make_user("stale.owner@example.com")
    admin = make_user("stale.admin@example.com", role=UserRole.ADMIN)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, admin.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(admin.id), "version": 1},
    )

    stale = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "TICKET_CHANGED"


def test_assign_requires_active_staff_assignee(client: TestClient, make_user) -> None:
    owner = make_user("assign.owner@example.com")
    agent = make_user("assign.agent@example.com", role=UserRole.AGENT)
    requester = make_user("assign.requester@example.com")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    assert login(client, agent.email).status_code == 200
    invalid = client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(requester.id), "version": 1},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_ASSIGNEE"

    valid = client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )
    assert valid.status_code == 200
    assert valid.json()["assignee"]["id"] == str(agent.id)


def test_only_admin_can_unassign(client: TestClient, make_user) -> None:
    owner = make_user("unassign.owner@example.com")
    agent = make_user("unassign.agent@example.com", role=UserRole.AGENT)
    admin = make_user("unassign.admin@example.com", role=UserRole.ADMIN)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, admin.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )

    assert login(client, agent.email).status_code == 200
    forbidden = client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": None, "version": 2},
    )
    assert forbidden.status_code == 403

    assert login(client, admin.email).status_code == 200
    allowed = client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": None, "version": 2},
    )
    assert allowed.status_code == 200
    assert allowed.json()["assignee"] is None


def test_user_cannot_assign(client: TestClient, make_user) -> None:
    owner = make_user("userassign.owner@example.com")
    agent = make_user("userassign.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    response = client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )
    assert response.status_code == 403


def test_admin_revert_to_open_clears_assignee(client: TestClient, make_user) -> None:
    owner = make_user("revert.owner@example.com")
    admin = make_user("revert.admin@example.com", role=UserRole.ADMIN)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, admin.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(admin.id), "version": 1},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 2},
    )

    reverted = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "OPEN", "version": 3, "reason": "Need to restart triage."},
    )
    assert reverted.status_code == 200
    assert reverted.json()["status"] == "OPEN"
    assert reverted.json()["assignee"] is None


def test_comments_visibility_and_soft_delete(client: TestClient, make_user) -> None:
    owner = make_user("comment.owner@example.com")
    agent = make_user("comment.agent@example.com", role=UserRole.AGENT)
    other = make_user("comment.other@example.com")

    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    path = f"/api/tickets/{ticket['id']}/comments"

    owner_comment = client.post(
        path,
        json={"body": "Public update from requester.", "visibility": "PUBLIC"},
    )
    assert owner_comment.status_code == 201

    assert login(client, agent.email).status_code == 200
    internal = client.post(
        path,
        json={"body": "Internal triage note.", "visibility": "INTERNAL"},
    )
    assert internal.status_code == 201

    assert login(client, other.email).status_code == 200
    hidden_ticket = client.get(f"/api/tickets/{ticket['id']}")
    assert hidden_ticket.status_code == 404

    assert login(client, owner.email).status_code == 200
    owner_view = client.get(path)
    assert owner_view.status_code == 200
    bodies = [item["body"] for item in owner_view.json()["items"]]
    assert "Public update from requester." in bodies
    assert "Internal triage note." not in bodies

    assert login(client, agent.email).status_code == 200
    agent_view = client.get(path)
    bodies = [item["body"] for item in agent_view.json()["items"]]
    assert "Internal triage note." in bodies

    internal_id = internal.json()["id"]
    deleted = client.delete(f"/api/comments/{internal_id}")
    assert deleted.status_code == 204

    after = client.get(path)
    deleted_item = next(item for item in after.json()["items"] if item["id"] == internal_id)
    assert deleted_item["deletedAt"] is not None


def test_internal_comment_requires_staff(client: TestClient, make_user) -> None:
    owner = make_user("internal.owner@example.com")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    response = client.post(
        f"/api/tickets/{ticket['id']}/comments",
        json={"body": "Trying to add an internal note.", "visibility": "INTERNAL"},
    )
    assert response.status_code == 403


def test_comment_delete_window_is_enforced(client: TestClient, db: Session, make_user) -> None:
    owner = make_user("window.owner@example.com")
    admin = make_user("window.admin@example.com", role=UserRole.ADMIN)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    comment = client.post(
        f"/api/tickets/{ticket['id']}/comments",
        json={"body": "Delete me later."},
    ).json()

    comment_row = db.get(Comment, uuid.UUID(comment["id"]))
    assert comment_row is not None
    comment_row.created_at = datetime.now(UTC) - timedelta(minutes=10)
    db.commit()

    expired_delete = client.delete(f"/api/comments/{comment['id']}")
    assert expired_delete.status_code == 403

    assert login(client, admin.email).status_code == 200
    admin_delete = client.delete(f"/api/comments/{comment['id']}")
    assert admin_delete.status_code == 204


def test_closed_to_open_requires_admin(client: TestClient, make_user) -> None:
    owner = make_user("closed.owner@example.com")
    agent = make_user("closed.agent@example.com", role=UserRole.AGENT)
    admin = make_user("closed.admin@example.com", role=UserRole.ADMIN)

    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, admin.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(admin.id), "version": 1},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS", "version": 2},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "RESOLVED", "version": 3, "resolutionNote": "Done."},
    )
    client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "CLOSED", "version": 4},
    )

    assert login(client, agent.email).status_code == 200
    forbidden = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "OPEN", "version": 5, "reason": "Reopen please."},
    )
    assert forbidden.status_code == 409
    assert forbidden.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    assert login(client, admin.email).status_code == 200
    reopened = client.patch(
        f"/api/tickets/{ticket['id']}/status",
        json={"status": "OPEN", "version": 5, "reason": "Admin reopen."},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "OPEN"
    assert reopened.json()["reopenCount"] == 1
