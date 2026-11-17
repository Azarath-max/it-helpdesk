import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi import status as http_status

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.comments.schemas import CommentCreate, CommentRead
from app.modules.comments.service import (
    add_comment,
    delete_comment,
    list_comments,
)
from app.schemas import Page

router = APIRouter(tags=["comments"])


@router.get(
    "/api/tickets/{ticket_id}/comments",
    response_model=Page[CommentRead],
    summary="List comments for a ticket",
)
def list_ticket_comments(
    ticket_id: uuid.UUID,
    db: DbSession,
    actor: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> Page[CommentRead]:
    comments = list_comments(db, actor, ticket_id)
    # Simple in-memory pagination keeps comment ordering stable and avoids a
    # second count query for a low-volume resource.
    total = len(comments)
    start = (page - 1) * page_size
    page_items = comments[start : start + page_size]
    return Page[CommentRead](
        items=[CommentRead.model_validate(comment) for comment in page_items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/api/tickets/{ticket_id}/comments",
    response_model=CommentRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Add a comment or internal note",
)
def create_ticket_comment(
    ticket_id: uuid.UUID,
    payload: CommentCreate,
    request: Request,
    db: DbSession,
    actor: CurrentUser,
) -> CommentRead:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client is not None else None
    comment = add_comment(
        db,
        actor,
        ticket_id,
        payload,
        request_id=str(request_id) if request_id else None,
        ip=ip,
    )
    return CommentRead.model_validate(comment)


@router.delete(
    "/api/comments/{comment_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a comment",
)
def remove_comment(
    comment_id: uuid.UUID,
    request: Request,
    db: DbSession,
    actor: CurrentUser,
) -> None:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client is not None else None
    delete_comment(
        db,
        actor,
        comment_id,
        request_id=str(request_id) if request_id else None,
        ip=ip,
    )
