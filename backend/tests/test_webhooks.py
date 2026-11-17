import hashlib
import hmac
import json
import time
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.audit.models import AuditEvent
from app.modules.tickets.models import Ticket


def signed_headers(
    body: bytes, *, timestamp: str | None = None, signature: str | None = None
) -> dict[str, str]:
    settings = get_settings()
    ts = timestamp if timestamp is not None else str(int(time.time()))
    if signature is None:
        expected = hmac.new(
            settings.webhook_secret.encode("utf-8"),
            f"{ts}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={expected}"
    return {
        "Content-Type": "application/json",
        "X-Webhook-Id": "delivery-1",
        "X-Webhook-Timestamp": ts,
        "X-Webhook-Signature": signature,
        "X-Webhook-Schema-Version": "1",
    }


def make_payload(**overrides) -> dict:
    body = {
        "schemaVersion": 1,
        "source": "email-triage",
        "externalId": f"msg-{uuid.uuid4().hex[:8]}",
        "title": "Laptop will not boot",
        "description": "Pressed power, fan spins, no display.",
        "requester": {"email": "webhook.user@example.com", "name": "Webhook User"},
        "priority": "HIGH",
        "category": "hardware",
        "metadata": {"confidence": 0.82},
    }
    body.update(overrides)
    return body


def post_webhook(client: TestClient, payload: dict, **header_overrides) -> object:
    raw = json.dumps(payload).encode("utf-8")
    headers = signed_headers(raw, **header_overrides)
    return client.post("/api/webhooks/tickets", content=raw, headers=headers)


def test_valid_webhook_creates_ticket(client: TestClient, db: Session) -> None:
    payload = make_payload()
    response = post_webhook(client, payload)

    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    assert body["status"] == "OPEN"

    ticket = db.get(Ticket, uuid.UUID(body["ticketId"]))
    assert ticket is not None
    assert ticket.source == "email-triage"
    assert ticket.external_id == payload["externalId"]
    assert ticket.title == payload["title"]
    assert ticket.requester.email == payload["requester"]["email"]

    audit = db.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == ticket.id, AuditEvent.action == "webhook.accepted"
        )
    )
    assert audit is not None
    assert audit.actor_user_id is None


def test_replayed_timestamp_is_rejected(client: TestClient) -> None:
    payload = make_payload()
    raw = json.dumps(payload).encode("utf-8")
    old_timestamp = str(int(time.time()) - 1000)
    headers = signed_headers(raw, timestamp=old_timestamp)
    response = client.post("/api/webhooks/tickets", content=raw, headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_tampered_body_is_rejected(client: TestClient) -> None:
    payload = make_payload()
    raw = json.dumps(payload).encode("utf-8")
    headers = signed_headers(raw)
    tampered = raw.replace(b"Laptop", b"Desktop")
    response = client.post("/api/webhooks/tickets", content=tampered, headers=headers)

    assert response.status_code == 401


def test_missing_signature_is_rejected(client: TestClient) -> None:
    payload = make_payload()
    raw = json.dumps(payload).encode("utf-8")
    headers = signed_headers(raw)
    del headers["X-Webhook-Signature"]
    response = client.post("/api/webhooks/tickets", content=raw, headers=headers)

    assert response.status_code == 401


def test_duplicate_delivery_returns_original_ticket(client: TestClient) -> None:
    payload = make_payload(externalId="duplicate-message-1")
    first = post_webhook(client, payload)
    assert first.status_code == 201

    second = post_webhook(client, payload)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["ticketId"] == first.json()["ticketId"]

    pass


def test_unsupported_schema_version_is_rejected(client: TestClient) -> None:
    payload = make_payload(schemaVersion=2)
    raw = json.dumps(payload).encode("utf-8")
    headers = signed_headers(raw)
    headers["X-Webhook-Schema-Version"] = "2"
    response = client.post("/api/webhooks/tickets", content=raw, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_malformed_json_is_rejected(client: TestClient) -> None:
    raw = b"{not json"
    headers = signed_headers(raw)
    response = client.post("/api/webhooks/tickets", content=raw, headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"


def test_validation_failure_is_rejected(client: TestClient) -> None:
    payload = make_payload(title="Hi")
    response = post_webhook(client, payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_webhook_queues_notification_to_requester(client: TestClient, db: Session) -> None:
    from app.modules.notifications.models import Notification

    payload = make_payload(
        requester={"email": "webhook.notify@example.com", "name": "Webhook Notify"}
    )
    response = post_webhook(client, payload)
    assert response.status_code == 201

    notification = db.scalar(
        select(Notification).where(
            Notification.event_type == "ticket.created",
            Notification.recipient_email == "webhook.notify@example.com",
        )
    )
    assert notification is not None
