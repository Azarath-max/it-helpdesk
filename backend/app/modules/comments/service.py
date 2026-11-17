"""Comment business rules: visibility, participation, and soft deletion."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.modules.audit.service import record_audit
from app.modules.comments.models import Comment, CommentVisibility
from app.modules.comments.schemas import CommentCreate
from app.modules.notifications.service import queue_ticket_commented
from app.modules.tickets.service import get_ticket_for_actor
from app.modules.users.models import User, UserRole

STAFF_ROLES = frozenset({UserRole.AGENT, UserRole.ADMIN})
COMMENT_EDIT_WINDOW = timedelta(minutes=5)


def list_comments(db: Session, actor: User, ticket_id: uuid.UUID) -> list[Comment]:
    """Return comments the actor may see for a ticket they can view."""
    get_ticket_for_actor(db, actor, ticket_id)  # raises 404 for hidden tickets

    comments = db.scalars(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    ).all()

    if actor.role not in STAFF_ROLES:
        comments = [
            comment for comment in comments if comment.visibility == CommentVisibility.PUBLIC
        ]
    return list(comments)


def add_comment(
    db: Session,
    actor: User,
    ticket_id: uuid.UUID,
    payload: CommentCreate,
    *,
    request_id: str | None,
    ip: str | None,
) -> Comment:
    """Add a public reply or internal note to a ticket."""
    ticket = get_ticket_for_actor(db, actor, ticket_id)

    if payload.visibility == CommentVisibility.INTERNAL and actor.role not in STAFF_ROLES:
        raise AppError(
            "FORBIDDEN",
            "You do not have permission to perform this action",
            status_code=403,
        )

    comment = Comment(
        ticket_id=ticket.id,
        author_id=actor.id,
        body=payload.body,
        visibility=payload.visibility,
    )
    db.add(comment)
    db.flush()

    record_audit(
        db,
        action="comment.created",
        entity_type="comment",
        entity_id=comment.id,
        actor=actor,
        after={
            "ticket_id": str(ticket.id),
            "body": comment.body,
            "visibility": comment.visibility.value,
        },
        request_id=request_id,
        ip=ip,
    )

    if payload.visibility == CommentVisibility.PUBLIC:
        recipients = [ticket.requester]
        if ticket.assignee is not None and ticket.assignee.id != ticket.requester.id:
            recipients.append(ticket.assignee)
    else:
        recipients = []
        if ticket.assignee is not None and ticket.assignee.id != actor.id:
            recipients.append(ticket.assignee)

    if recipients:
        queue_ticket_commented(
            db,
            ticket,
            comment.body,
            recipients,
            actor,
            internal=payload.visibility == CommentVisibility.INTERNAL,
        )

    db.commit()

    return db.scalar(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment.id)
    )  # type: ignore[return-value]


def delete_comment(
    db: Session,
    actor: User,
    comment_id: uuid.UUID,
    *,
    request_id: str | None,
    ip: str | None,
) -> None:
    """Soft-delete a comment within the allowed window."""
    comment = db.scalar(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment_id)
    )
    if comment is None:
        raise AppError("COMMENT_NOT_FOUND", "Comment not found", status_code=404)

    get_ticket_for_actor(db, actor, comment.ticket_id)

    if comment.deleted_at is not None:
        return

    is_author = comment.author_id == actor.id
    within_window = comment.created_at >= datetime.now(UTC) - COMMENT_EDIT_WINDOW
    if not (actor.role == UserRole.ADMIN or (is_author and within_window)):
        raise AppError(
            "FORBIDDEN",
            "You do not have permission to perform this action",
            status_code=403,
        )

    before = {"body": comment.body, "deleted_at": None}
    comment.deleted_at = datetime.now(UTC)
    db.flush()

    record_audit(
        db,
        action="comment.deleted",
        entity_type="comment",
        entity_id=comment.id,
        actor=actor,
        before=before,
        after={"deleted_at": comment.deleted_at.isoformat()},
        request_id=request_id,
        ip=ip,
    )
    db.commit()
