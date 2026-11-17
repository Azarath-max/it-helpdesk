import hashlib
import hmac
import json
import time
import uuid

from fastapi import APIRouter, Request, Response
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.audit.service import record_audit
from app.modules.auth.dependencies import DbSession
from app.modules.auth.security import hash_password
from app.modules.auth.service import find_user_by_email
from app.modules.tickets.models import Ticket
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets.service import create_ticket as create_ticket_record
from app.modules.users.models import User, UserRole
from app.modules.webhooks.schemas import WebhookTicketPayload, WebhookTicketResponse

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

MAX_BODY_BYTES = 256 * 1024
TIMESTAMP_TOLERANCE_SECONDS = 300


def _audit_context(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client is not None else None
    return (str(request_id) if request_id else None, ip)


def _verify_signature(secret: str, timestamp: str, signature: str, raw_body: bytes) -> bool:
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - timestamp_int) > TIMESTAMP_TOLERANCE_SECONDS:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            f"{timestamp}.".encode() + raw_body,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def _get_or_create_requester(db: DbSession, email: str, name: str) -> User:
    existing = find_user_by_email(db, email)
    if existing is not None:
        return existing
    import secrets

    user = User(
        email=email,
        name=name,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role=UserRole.USER,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@router.post(
    "/tickets",
    response_model=WebhookTicketResponse,
    summary="Create a ticket from an external system",
)
async def create_webhook_ticket(
    request: Request, response: Response, db: DbSession
) -> WebhookTicketResponse:
    request_id, ip = _audit_context(request)
    raw_body = await request.body()

    if len(raw_body) > MAX_BODY_BYTES:
        raise AppError("PAYLOAD_TOO_LARGE", "Request body is too large", status_code=413)

    webhook_id = request.headers.get("X-Webhook-Id")
    timestamp = request.headers.get("X-Webhook-Timestamp")
    signature = request.headers.get("X-Webhook-Signature")
    schema_version_header = request.headers.get("X-Webhook-Schema-Version")

    settings = get_settings()
    if not (webhook_id and timestamp and signature and schema_version_header):
        raise AppError("UNAUTHORIZED", "Missing webhook authentication headers", status_code=401)

    if not _verify_signature(settings.webhook_secret, timestamp, signature, raw_body):
        record_audit(
            db,
            action="webhook.rejected",
            entity_type="webhook",
            entity_id=uuid.uuid4(),
            actor=None,
            metadata={
                "outcome": "invalid_signature",
                "webhook_id": webhook_id,
            },
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise AppError("UNAUTHORIZED", "Invalid webhook signature", status_code=401)

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        record_audit(
            db,
            action="webhook.rejected",
            entity_type="webhook",
            entity_id=uuid.uuid4(),
            actor=None,
            metadata={"outcome": "invalid_json", "webhook_id": webhook_id},
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise AppError("INVALID_JSON", "Malformed JSON", status_code=400) from exc

    if schema_version_header != "1":
        record_audit(
            db,
            action="webhook.rejected",
            entity_type="webhook",
            entity_id=uuid.uuid4(),
            actor=None,
            metadata={
                "outcome": "unsupported_schema_version",
                "webhook_id": webhook_id,
                "schema_version": schema_version_header,
            },
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise AppError("VALIDATION_ERROR", "Unsupported schema version", status_code=422)

    try:
        payload = WebhookTicketPayload.model_validate(data)
    except ValidationError as exc:
        record_audit(
            db,
            action="webhook.rejected",
            entity_type="webhook",
            entity_id=uuid.uuid4(),
            actor=None,
            metadata={
                "outcome": "validation_error",
                "webhook_id": webhook_id,
                "errors": exc.errors(),
            },
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise AppError("VALIDATION_ERROR", "Request validation failed", status_code=422) from exc

    if payload.schema_version != 1:
        record_audit(
            db,
            action="webhook.rejected",
            entity_type="webhook",
            entity_id=uuid.uuid4(),
            actor=None,
            metadata={
                "outcome": "unsupported_payload_schema_version",
                "webhook_id": webhook_id,
                "schema_version": payload.schema_version,
            },
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise AppError("VALIDATION_ERROR", "Unsupported schema version", status_code=422)

    # Idempotency: return the original ticket for a genuine retry.
    existing = db.scalar(
        select(Ticket).where(
            Ticket.source == payload.source,
            Ticket.external_id == payload.external_id,
        )
    )
    if existing is not None:
        record_audit(
            db,
            action="webhook.duplicate",
            entity_type="ticket",
            entity_id=existing.id,
            actor=None,
            metadata={
                "source": payload.source,
                "external_id": payload.external_id,
                "webhook_id": webhook_id,
                "metadata": payload.metadata,
            },
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        return WebhookTicketResponse(
            ticket_id=existing.id,
            status=existing.status,
            duplicate=True,
        )

    requester = _get_or_create_requester(db, str(payload.requester.email), payload.requester.name)

    ticket_create = TicketCreate(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        category=payload.category,
    )

    from sqlalchemy.exc import IntegrityError

    try:
        ticket = create_ticket_record(
            db,
            requester,
            ticket_create,
            request_id=request_id,
            ip=ip,
            source=payload.source,
            external_id=payload.external_id,
        )
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Ticket).where(
                Ticket.source == payload.source,
                Ticket.external_id == payload.external_id,
            )
        )
        if existing is not None:
            record_audit(
                db,
                action="webhook.duplicate",
                entity_type="ticket",
                entity_id=existing.id,
                actor=None,
                metadata={
                    "source": payload.source,
                    "external_id": payload.external_id,
                    "webhook_id": webhook_id,
                },
                request_id=request_id,
                ip=ip,
            )
            db.commit()
            return WebhookTicketResponse(
                ticket_id=existing.id,
                status=existing.status,
                duplicate=True,
            )
        raise

    record_audit(
        db,
        action="webhook.accepted",
        entity_type="ticket",
        entity_id=ticket.id,
        actor=None,
        metadata={
            "source": payload.source,
            "external_id": payload.external_id,
            "webhook_id": webhook_id,
            "metadata": payload.metadata,
        },
        request_id=request_id,
        ip=ip,
    )
    response.status_code = 201
    db.commit()

    return WebhookTicketResponse(
        ticket_id=ticket.id,
        status=ticket.status,
        duplicate=False,
    )
