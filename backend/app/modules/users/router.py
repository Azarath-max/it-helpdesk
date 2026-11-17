from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.errors import AppError
from app.modules.audit.service import record_audit
from app.modules.auth.dependencies import DbSession, require_roles
from app.modules.auth.service import revoke_all_sessions
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import (
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    UserRead,
)
from app.schemas import Page

router = APIRouter(prefix="/api/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get(
    "",
    response_model=Page[UserRead],
    summary="List accounts (admin only)",
)
def list_users(
    db: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> Page[UserRead]:
    from sqlalchemy import func, select

    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = db.scalars(
        select(User)
        .order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[UserRead](
        items=[UserRead.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    summary="Change a user's role (admin only)",
)
def update_user_role(
    user_id: UUID,
    payload: UpdateUserRoleRequest,
    db: DbSession,
    actor: AdminUser,
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise AppError("USER_NOT_FOUND", "User not found", status_code=404)

    if user.id == actor.id:
        raise AppError("FORBIDDEN", "You cannot change your own role", status_code=400)

    before = {"role": user.role.value}
    if user.role != payload.role:
        user.role = payload.role
        revoke_all_sessions(db, user.id)
    after = {"role": user.role.value}

    record_audit(
        db,
        action="user.role_changed",
        entity_type="user",
        entity_id=user.id,
        actor=actor,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}/status",
    response_model=UserRead,
    summary="Activate or deactivate a user (admin only)",
)
def update_user_status(
    user_id: UUID,
    payload: UpdateUserStatusRequest,
    db: DbSession,
    actor: AdminUser,
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise AppError("USER_NOT_FOUND", "User not found", status_code=404)

    if user.id == actor.id and not payload.is_active:
        raise AppError("FORBIDDEN", "You cannot deactivate your own account", status_code=400)

    before = {"is_active": user.is_active}
    if user.is_active != payload.is_active:
        user.is_active = payload.is_active
        if not payload.is_active:
            revoke_all_sessions(db, user.id)
    after = {"is_active": user.is_active}

    record_audit(
        db,
        action="user.status_changed",
        entity_type="user",
        entity_id=user.id,
        actor=actor,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
