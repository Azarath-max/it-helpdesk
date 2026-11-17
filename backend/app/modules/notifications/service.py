"""Transactional email outbox: queueing, rendering, and delivery."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.notifications.templates import render_template
from app.modules.notifications.transport import (
    EmailTransport,
    PermanentEmailError,
    TransientEmailError,
)
from app.modules.tickets.models import Ticket
from app.modules.users.models import User

MAX_ATTEMPTS = 5
BACKOFF = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
)


def queue_notification(
    db: Session,
    *,
    ticket_id: uuid.UUID | None,
    event_type: str,
    recipient_email: str,
    template: str,
    payload: dict[str, Any],
    idempotency_key: str,
) -> Notification:
    """Stage one notification in the current transaction, deduplicating by key."""
    existing = db.scalar(
        select(Notification).where(Notification.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    notification = Notification(
        ticket_id=ticket_id,
        event_type=event_type,
        recipient_email=recipient_email,
        template=template,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    db.add(notification)
    db.flush()
    return notification


def _subject(event_type: str, payload: dict[str, Any]) -> str:
    ref = payload["ticket_public_ref"]
    if event_type == "ticket.created":
        return f"[{ref}] Your ticket has been created"
    if event_type == "ticket.assigned":
        return f"[{ref}] A ticket was assigned to you"
    if event_type == "ticket.status_changed":
        status = str(payload["ticket_status"]).replace("_", " ").title()
        return f"[{ref}] Ticket status: {status}"
    if event_type == "ticket.commented":
        return f"[{ref}] New comment on your ticket"
    return f"[{ref}] Ticket update"


def _send_one(db: Session, transport: EmailTransport, notification: Notification) -> None:
    notification.status = NotificationStatus.SENDING
    db.commit()

    try:
        context = notification.payload
        subject = _subject(notification.event_type, context)
        text_body = render_template(f"{notification.template}.txt.j2", context)
        html_body = render_template(f"{notification.template}.html.j2", context)

        from email.message import EmailMessage

        message = EmailMessage()
        message["From"] = get_settings().smtp_from
        message["To"] = notification.recipient_email
        message["Subject"] = subject
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        transport.send(message)

        notification.attempts += 1
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
        notification.last_error = None
    except PermanentEmailError as exc:
        notification.attempts += 1
        notification.status = NotificationStatus.DEAD
        notification.last_error = str(exc)[:500]
    except (TransientEmailError, Exception) as exc:
        notification.attempts += 1
        if notification.attempts >= MAX_ATTEMPTS:
            notification.status = NotificationStatus.DEAD
        else:
            notification.status = NotificationStatus.FAILED
            delay = BACKOFF[min(notification.attempts - 1, len(BACKOFF) - 1)]
            notification.next_attempt_at = datetime.now(UTC) + delay
        notification.last_error = str(exc)[:500]

    db.commit()


def process_pending(
    db: Session,
    transport: EmailTransport,
    *,
    limit: int = 10,
    now: datetime | None = None,
) -> int:
    """Claim and process a batch of due notifications. Returns the count processed."""
    current = now or datetime.now(UTC)
    notifications = db.scalars(
        select(Notification)
        .where(
            Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.FAILED]),
            Notification.next_attempt_at <= current,
        )
        .order_by(Notification.created_at.asc(), Notification.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()

    processed = 0
    for notification in notifications:
        _send_one(db, transport, notification)
        processed += 1
    return processed


def _deep_link(ticket_id: object) -> str:
    return f"{get_settings().app_base_url}/tickets/{ticket_id}"


def queue_ticket_created(db: Session, ticket: Ticket, requester: User) -> None:
    queue_notification(
        db,
        ticket_id=ticket.id,
        event_type="ticket.created",
        recipient_email=requester.email,
        template="ticket_created",
        payload={
            "recipient_name": requester.name,
            "ticket_public_ref": ticket.public_ref,
            "ticket_title": ticket.title,
            "ticket_status": ticket.status.value,
            "deep_link": _deep_link(ticket.id),
        },
        idempotency_key=f"ticket.created:{ticket.id}:{requester.id}",
    )


def queue_ticket_assigned(db: Session, ticket: Ticket, assignee: User, actor: User) -> None:
    if assignee.id == actor.id:
        return
    queue_notification(
        db,
        ticket_id=ticket.id,
        event_type="ticket.assigned",
        recipient_email=assignee.email,
        template="ticket_assigned",
        payload={
            "recipient_name": assignee.name,
            "ticket_public_ref": ticket.public_ref,
            "ticket_title": ticket.title,
            "ticket_status": ticket.status.value,
            "actor_name": actor.name,
            "deep_link": _deep_link(ticket.id),
        },
        idempotency_key=f"ticket.assigned:{ticket.id}:{assignee.id}",
    )


def queue_ticket_status_changed(
    db: Session,
    ticket: Ticket,
    recipients: list[User],
    actor: User,
) -> None:
    for recipient in recipients:
        if recipient.id == actor.id:
            continue
        queue_notification(
            db,
            ticket_id=ticket.id,
            event_type="ticket.status_changed",
            recipient_email=recipient.email,
            template="ticket_status_changed",
            payload={
                "recipient_name": recipient.name,
                "ticket_public_ref": ticket.public_ref,
                "ticket_title": ticket.title,
                "ticket_status": ticket.status.value,
                "actor_name": actor.name,
                "deep_link": _deep_link(ticket.id),
            },
            idempotency_key=(f"ticket.status_changed:{ticket.id}:{ticket.version}:{recipient.id}"),
        )


def queue_ticket_commented(
    db: Session,
    ticket: Ticket,
    comment_body: str,
    recipients: list[User],
    actor: User,
    *,
    internal: bool,
) -> None:
    event_type = "ticket.commented"
    template = "ticket_commented"
    for recipient in recipients:
        if recipient.id == actor.id:
            continue
        queue_notification(
            db,
            ticket_id=ticket.id,
            event_type=event_type,
            recipient_email=recipient.email,
            template=template,
            payload={
                "recipient_name": recipient.name,
                "ticket_public_ref": ticket.public_ref,
                "ticket_title": ticket.title,
                "ticket_status": ticket.status.value,
                "actor_name": actor.name,
                "comment_body": comment_body,
                "deep_link": _deep_link(ticket.id),
                "internal": internal,
            },
            idempotency_key=f"comment.created:{ticket.id}:{recipient.id}:{actor.id}",
        )
