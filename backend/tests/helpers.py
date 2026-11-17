"""Test helpers for auth flows."""

from fastapi.testclient import TestClient
from httpx import Response

DEFAULT_PASSWORD = "correct horse battery staple"
STRONG_PASSWORD = "a-very-long-test-password-1"


def register(
    client: TestClient,
    email: str = "new-user@example.com",
    *,
    name: str = "New User",
    password: str = STRONG_PASSWORD,
) -> Response:
    return client.post(
        "/api/auth/register",
        json={"email": email, "name": name, "password": password},
    )


def login(
    client: TestClient,
    email: str,
    password: str = DEFAULT_PASSWORD,
) -> Response:
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
