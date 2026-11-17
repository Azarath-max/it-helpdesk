from fastapi.testclient import TestClient

from app.modules.users.models import UserRole
from tests.helpers import login, register


def test_list_users_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/users")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_requester_cannot_list_users(client: TestClient, make_user) -> None:
    make_user("requester@example.com", role=UserRole.USER)
    assert login(client, "requester@example.com").status_code == 200

    response = client.get("/api/users")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_agent_cannot_list_users(client: TestClient, make_user) -> None:
    make_user("agent@example.com", role=UserRole.AGENT)
    assert login(client, "agent@example.com").status_code == 200

    response = client.get("/api/users")

    assert response.status_code == 403


def test_admin_can_list_users(client: TestClient, make_user) -> None:
    make_user("admin@example.com", role=UserRole.ADMIN)
    make_user("second@example.com")
    assert login(client, "admin@example.com").status_code == 200

    response = client.get("/api/users")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    assert body["page"] == 1
    assert body["pageSize"] == 20
    emails = {item["email"] for item in body["items"]}
    assert {"admin@example.com", "second@example.com"} <= emails


def test_admin_list_users_paginates(client: TestClient, make_user) -> None:
    make_user("admin@example.com", role=UserRole.ADMIN)
    for index in range(3):
        make_user(f"member{index}@example.com")
    assert login(client, "admin@example.com").status_code == 200

    response = client.get("/api/users", params={"page": 2, "pageSize": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 4
    assert len(body["items"]) == 2
    assert body["page"] == 2


def test_self_registration_never_grants_a_role(client: TestClient) -> None:
    response = register(client, "newbie@example.com")

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "user"
    assert client.get("/api/users").status_code == 403


def test_role_is_read_from_the_database_on_every_request(
    client: TestClient,
    db,
    make_user,
) -> None:
    user = make_user("promoted@example.com", role=UserRole.USER)
    assert login(client, "promoted@example.com").status_code == 200
    assert client.get("/api/users").status_code == 403

    user.role = UserRole.ADMIN
    db.commit()

    assert client.get("/api/users").status_code == 200
