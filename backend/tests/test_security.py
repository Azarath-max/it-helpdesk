from fastapi.testclient import TestClient

from app.core.middleware import allowed_origins
from app.modules.auth.security import (
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)


def test_password_hash_is_argon2id_and_salted() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first.startswith("$argon2id$")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password("anything", "not-a-real-hash")


def test_tokens_are_random_and_hashed() -> None:
    first = new_opaque_token()
    second = new_opaque_token()

    assert first != second
    assert len(first) >= 40
    assert len(hash_token(first)) == 64
    assert hash_token(first) == hash_token(first)
    assert hash_token(first) != hash_token(second)


def test_development_allows_both_loopback_spellings() -> None:
    origins = allowed_origins()

    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:5173" in origins


def test_cross_origin_state_change_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "irrelevant-password"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_ORIGIN"
    assert response.json()["error"]["requestId"]


def test_matching_origin_is_allowed(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "irrelevant-password"},
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.status_code == 401


def test_safe_methods_are_not_origin_checked(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Origin": "https://evil.example"})

    assert response.status_code == 401


def test_webhook_route_is_exempt_from_origin_check(client: TestClient) -> None:
    response = client.post(
        "/api/webhooks/tickets",
        json={},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 404
