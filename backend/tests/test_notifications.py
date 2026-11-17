from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.notifications.service import process_pending
from app.modules.notifications.transport import (
    PermanentEmailError,
    TransientEmailError,
)
from app.modules.users.models import UserRole
from tests.helpers import login


class FakeTransport:
    def __init__(self, fail_times: int = 0, permanent: bool = False) -> None:
        self.sent: list[object] = []
        self.fail_times = fail_times
        self.permanent = permanent
        self.calls = 0

    def send(self, message: object) -> None:
        self.calls += 1
        if self.calls <= self.fail_times:
            if self.permanent:
                raise PermanentEmailError("bad address")
            raise TransientEmailError("timeout")
        self.sent.append(message)


def create_ticket(client: TestClient, **overrides) -> dict:
    body = {"title": "Notify ticket", "description": "Needs notification coverage."}
    body.update(overrides)
    response = client.post("/api/tickets", json=body)
    assert response.status_code == 201
    return response.json()


def test_ticket_created_queues_and_sends_notification(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("notify.owner@example.com", name="Notify Owner")
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)

    notification = db.scalar(
        select(Notification).where(Notification.event_type == "ticket.created")
    )
    assert notification is not None
    assert notification.recipient_email == owner.email
    assert notification.status == NotificationStatus.PENDING
    assert notification.idempotency_key == f"ticket.created:{ticket['id']}:{owner.id}"

    transport = FakeTransport()
    processed = process_pending(db, transport)
    assert processed == 1

    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert len(transport.sent) == 1
    message = transport.sent[0]
    assert owner.email in str(message["To"])
    assert ticket["publicRef"] in str(message["Subject"])


def test_queue_deduplicates_idempotency_key(db: Session, make_user) -> None:
    from app.modules.notifications.service import queue_notification

    ticket_id = None
    first = queue_notification(
        db,
        ticket_id=ticket_id,
        event_type="ticket.created",
        recipient_email="dedup@example.com",
        template="ticket_created",
        payload={"recipient_name": "Dedup"},
        idempotency_key="dedup-key",
    )
    second = queue_notification(
        db,
        ticket_id=ticket_id,
        event_type="ticket.created",
        recipient_email="dedup@example.com",
        template="ticket_created",
        payload={"recipient_name": "Dedup"},
        idempotency_key="dedup-key",
    )
    assert first.id == second.id
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.idempotency_key == "dedup-key")
    )
    assert count == 1


def test_transient_failure_retries_then_dead(
    db: Session,
) -> None:
    from app.modules.notifications.service import queue_notification

    notification = queue_notification(
        db,
        ticket_id=None,
        event_type="ticket.created",
        recipient_email="retry@example.com",
        template="ticket_created",
        payload={
            "recipient_name": "Retry",
            "ticket_public_ref": "HD-000001",
            "ticket_title": "Retry me",
            "ticket_status": "OPEN",
            "deep_link": "http://127.0.0.1:5173/tickets/x",
        },
        idempotency_key="retry-key",
    )
    db.commit()

    transport = FakeTransport(fail_times=5, permanent=False)
    now = datetime.now(UTC)
    for attempt in range(5):
        process_pending(db, transport, now=now + timedelta(hours=attempt))
        db.refresh(notification)
        if notification.status == NotificationStatus.DEAD:
            break

    db.refresh(notification)
    assert notification.status == NotificationStatus.DEAD
    assert notification.attempts == 5
    assert notification.last_error == "timeout"


def test_permanent_failure_marks_dead_immediately(db: Session) -> None:
    from app.modules.notifications.service import queue_notification

    notification = queue_notification(
        db,
        ticket_id=None,
        event_type="ticket.created",
        recipient_email="permanent@example.com",
        template="ticket_created",
        payload={
            "recipient_name": "Permanent",
            "ticket_public_ref": "HD-000002",
            "ticket_title": "Bad address",
            "ticket_status": "OPEN",
            "deep_link": "http://127.0.0.1:5173/tickets/y",
        },
        idempotency_key="permanent-key",
    )
    db.commit()

    transport = FakeTransport(fail_times=1, permanent=True)
    process_pending(db, transport)

    db.refresh(notification)
    assert notification.status == NotificationStatus.DEAD
    assert notification.attempts == 1
    assert notification.last_error == "bad address"


def test_status_change_queues_recipients_and_skips_actor(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("status.owner@example.com", name="Status Owner")
    agent = make_user("status.agent@example.com", role=UserRole.AGENT, name="Status Agent")
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

    keys = db.scalars(select(Notification.idempotency_key)).all()
    assert any("status_changed" in key for key in keys)
    recipients = db.scalars(
        select(Notification.recipient_email).where(
            Notification.event_type == "ticket.status_changed"
        )
    ).all()
    assert owner.email in recipients
    assert agent.email not in recipients


def test_assignment_queues_assignee_notification(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("assign.notify.owner@example.com")
    agent = make_user("assign.notify.agent@example.com", role=UserRole.AGENT)
    admin = make_user("assign.notify.admin@example.com", role=UserRole.ADMIN)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, admin.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )

    notification = db.scalar(
        select(Notification).where(Notification.event_type == "ticket.assigned")
    )
    assert notification is not None
    assert notification.recipient_email == agent.email


def test_comment_queues_participants_not_author(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    owner = make_user("comment.notify.owner@example.com")
    agent = make_user("comment.notify.agent@example.com", role=UserRole.AGENT)
    assert login(client, owner.email).status_code == 200
    ticket = create_ticket(client)
    assert login(client, agent.email).status_code == 200
    client.patch(
        f"/api/tickets/{ticket['id']}/assign",
        json={"assigneeId": str(agent.id), "version": 1},
    )
    assert login(client, owner.email).status_code == 200
    client.post(
        f"/api/tickets/{ticket['id']}/comments",
        json={"body": "Owner says hello.", "visibility": "PUBLIC"},
    )

    recipients = db.scalars(
        select(Notification.recipient_email).where(Notification.event_type == "ticket.commented")
    ).all()
    assert agent.email in recipients
    assert owner.email not in recipients
