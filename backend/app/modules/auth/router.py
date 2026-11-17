from fastapi import APIRouter, Request, Response, status

from app.core.errors import AppError
from app.modules.auth.cookies import clear_session_cookie, set_session_cookie
from app.modules.auth.dependencies import CurrentSession, CurrentUser, DbSession
from app.modules.auth.notifications import deliver_password_reset
from app.modules.auth.schemas import (
    AcceptedResponse,
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.modules.auth.service import (
    authenticate_user,
    create_password_reset_token,
    create_session,
    find_user_by_email,
    register_user,
    reset_password,
    revoke_session,
)
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a requester account and start a session",
)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> AuthResponse:
    user = register_user(db, payload)
    raw_token, _ = create_session(db, user, request.headers.get("user-agent"))
    set_session_cookie(response, raw_token)
    return AuthResponse(user=UserRead.model_validate(user))


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Start a session with email and password",
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> AuthResponse:
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise AppError(
            "INVALID_CREDENTIALS",
            "Invalid email or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    raw_token, _ = create_session(db, user, request.headers.get("user-agent"))
    set_session_cookie(response, raw_token)
    return AuthResponse(user=UserRead.model_validate(user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current session",
)
def logout(
    response: Response,
    session: CurrentSession,
    db: DbSession,
) -> None:
    revoke_session(db, session)
    clear_session_cookie(response)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the authenticated account",
)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post(
    "/forgot-password",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset link",
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> AcceptedResponse:
    user = find_user_by_email(db, str(payload.email))
    if user is not None and user.is_active:
        raw_token = create_password_reset_token(db, user)
        deliver_password_reset(user, raw_token)
    return AcceptedResponse()


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password with a single-use token",
)
def reset_password_with_token(payload: ResetPasswordRequest, db: DbSession) -> None:
    reset_password(db, payload.token, payload.new_password)
