from fastapi.testclient import TestClient

from app.modules.users.models import UserRole
from tests.helpers import login


def test_admin_can_change_user_role_and_status(make_user, client: TestClient) -> None:
    admin = make_user("phase6.admin@example.com", role=UserRole.ADMIN)
    user = make_user("phase6.user@example.com")
    assert login(client, admin.email).status_code == 200

    role_response = client.patch(
        f"/api/users/{user.id}/role",
        json={"role": "agent"},
    )
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "agent"

    status_response = client.patch(
        f"/api/users/{user.id}/status",
        json={"isActive": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["isActive"] is False


def test_non_admin_cannot_manage_users(make_user, client: TestClient) -> None:
    user = make_user("phase6.plain@example.com")
    assert login(client, user.email).status_code == 200

    response = client.get("/api/users")
    assert response.status_code == 403

    audit = client.get("/api/audit-events")
    assert audit.status_code == 403


def test_admin_can_query_audit_events(make_user, client: TestClient) -> None:
    admin = make_user("phase6.audit@example.com", role=UserRole.ADMIN)
    assert login(client, admin.email).status_code == 200

    response = client.get("/api/audit-events", params={"pageSize": 5})
    assert response.status_code == 200
    assert "items" in response.json()
