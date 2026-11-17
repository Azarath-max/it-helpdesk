from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import PasswordResetToken, UserSession
from app.modules.auth.service import create_password_reset_token
from app.modules.users.models import User, UserRole
from tests.helpers import DEFAULT_PASSWORD, STRONG_PASSWORD, login, register


def test_register_creates_requester_and_starts_session(
    client: TestClient,
    db: Session,
) -> None:
    response = register(client, "jane@example.com", name="Jane Doe")

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "jane@example.com"
    assert body["user"]["name"] == "Jane Doe"
    assert body["user"]["role"] == "user"
    assert body["user"]["isActive"] is True

    user = db.scalar(select(User).where(User.email == "jane@example.com"))
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != STRONG_PASSWORD

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["user"]["id"]


def test_register_sets_hardened_session_cookie(client: TestClient) -> None:
    response = register(client)

    cookie = response.headers["set-cookie"]
    assert "helpdesk_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Max-Age=" in cookie


def test_register_rejects_duplicate_email_case_insensitively(client: TestClient) -> None:
    first = register(client, "Case.User@example.com")
    assert first.status_code == 201

    second = register(client, "case.user@example.com")

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_rejects_privileged_fields(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "sneaky@example.com",
            "name": "Sneaky",
            "password": STRONG_PASSWORD,
            "role": "admin",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = register(client, password="too-short")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_and_me(client: TestClient, make_user) -> None:
    make_user("agent@example.com", name="Agent Smith", role=UserRole.AGENT)

    response = login(client, "agent@example.com")

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "agent"
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "agent@example.com"


def test_login_rejects_wrong_password_and_unknown_email_identically(
    client: TestClient,
    make_user,
) -> None:
    make_user("known@example.com")

    wrong = login(client, "known@example.com", "wrong password here")
    unknown = login(client, "unknown@example.com", "wrong password here")

    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_login_rejects_inactive_account(client: TestClient, make_user) -> None:
    make_user("disabled@example.com", is_active=False)

    response = login(client, "disabled@example.com")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_logout_revokes_session(client: TestClient, make_user) -> None:
    make_user("leaver@example.com")
    assert login(client, "leaver@example.com").status_code == 200

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_expired_session_is_rejected(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    make_user("expired@example.com")
    assert login(client, "expired@example.com").status_code == 200

    session = db.scalar(select(UserSession).join(User).where(User.email == "expired@example.com"))
    assert session is not None
    session_id = session.id
    session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert db.get(UserSession, session_id) is None


def test_password_reset_flow(
    client: TestClient,
    db: Session,
    make_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_user("reset@example.com")
    captured: dict[str, str] = {}

    def capture(user: User, token: str) -> None:
        captured["token"] = token

    monkeypatch.setattr("app.modules.auth.router.deliver_password_reset", capture)

    requested = client.post(
        "/api/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert requested.status_code == 202
    assert captured["token"]

    reset = client.post(
        "/api/auth/reset-password",
        json={"token": captured["token"], "newPassword": "a-brand-new-password-2"},
    )
    assert reset.status_code == 204

    assert login(client, "reset@example.com", DEFAULT_PASSWORD).status_code == 401
    assert login(client, "reset@example.com", "a-brand-new-password-2").status_code == 200

    reused = client.post(
        "/api/auth/reset-password",
        json={"token": captured["token"], "newPassword": "yet-another-password-3"},
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_forgot_password_is_neutral_for_unknown_email(
    client: TestClient,
    db: Session,
) -> None:
    before = db.scalar(select(func.count()).select_from(PasswordResetToken))

    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )

    assert response.status_code == 202
    assert db.scalar(select(func.count()).select_from(PasswordResetToken)) == before


def test_reset_revokes_all_sessions(
    client: TestClient,
    db: Session,
    make_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user("kicked@example.com")
    assert login(client, "kicked@example.com").status_code == 200

    token = create_password_reset_token(db, user)
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "newPassword": "fresh-password-1234"},
    )

    assert response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert (
        db.scalar(
            select(func.count()).select_from(UserSession).where(UserSession.user_id == user.id)
        )
        == 0
    )


def test_expired_reset_token_is_rejected(
    client: TestClient,
    db: Session,
    make_user,
) -> None:
    user = make_user("stale@example.com")
    token = create_password_reset_token(db, user)
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "newPassword": "another-password-5678"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RESET_TOKEN"
