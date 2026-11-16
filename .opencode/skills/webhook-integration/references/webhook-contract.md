# Inbound Webhook Contract

## Endpoint

`POST /api/webhooks/tickets`

## Headers

| Header | Required | Example |
| --- | --- | --- |
| `Content-Type` | yes | `application/json` |
| `X-Webhook-Id` | yes | `01J8Z3K4T9` |
| `X-Webhook-Timestamp` | yes | `1763115300` |
| `X-Webhook-Signature` | yes | `sha256=hex...` |
| `X-Webhook-Schema-Version` | yes | `1` |

## Signature

```text
signedPayload = timestamp + "." + rawBody
expected = HMAC-SHA256(secret, signedPayload)
signature = "sha256=" + hex(expected)
```

Verification steps:

1. Read the raw body as bytes before parsing JSON.
2. Read the timestamp and signature headers.
3. Reject when `abs(now - timestamp) > 300` seconds.
4. Compute the expected HMAC with the shared secret.
5. Compare with a constant-time function on equal-length buffers.
6. Reject with `401` on any failure. Do not reveal which check failed.

```python
import hmac
import time
from hashlib import sha256

def verify(secret: bytes, timestamp: str, signature: str, raw_body: bytes) -> bool:
    if abs(time.time() - int(timestamp)) > 300:
        return False
    expected = "sha256=" + hmac.new(
        secret, f"{timestamp}.".encode() + raw_body, sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

`X-Webhook-Id` identifies the delivery. The payload `externalId` identifies the originating email
or form submission.

## Payload

```json
{
  "schemaVersion": 1,
  "source": "email-triage",
  "externalId": "<message-id-or-form-id>",
  "title": "Laptop will not boot",
  "description": "Pressed power, fan spins, no display.",
  "requester": { "email": "jane@example.com", "name": "Jane Doe" },
  "priority": "HIGH",
  "category": "hardware",
  "metadata": {
    "summary": "Possible hardware failure",
    "confidence": 0.82,
    "workflowId": "triage-run-123"
  }
}
```

`metadata` is optional, stored for diagnostics, and never trusted for authorization.

## Validation

- `schemaVersion` must be supported.
- `source` and `externalId` are required and stable.
- `title` length 5 to 200, `description` length 1 to 10,000.
- `requester.email` must parse as an email address.
- `priority` is `LOW`, `MEDIUM`, `HIGH`, or `URGENT`; default `MEDIUM`.
- `category` comes from an allowlist or maps to `other`.
- Unknown fields are ignored or rejected explicitly. Never let them reach the database.

## Responses

All errors use the shared envelope: `{ "error": { "code", "message", "details", "requestId" } }`.

| Status | When | Body |
| --- | --- | --- |
| 201 | Ticket created | `{ "ticketId": "...", "status": "OPEN", "duplicate": false }` |
| 200 | Duplicate delivery | `{ "ticketId": "...", "status": "OPEN", "duplicate": true }` |
| 400 | Malformed JSON | `{ "error": { "code": "INVALID_JSON", ... } }` |
| 401 | Missing or invalid signature | `{ "error": { "code": "UNAUTHORIZED", ... } }` |
| 409 | External ID belongs to a conflicting source | `{ "error": { "code": "CONFLICT", ... } }` |
| 422 | Unsupported schema or validation failure | `{ "error": { "code": "VALIDATION_ERROR", ... } }` |
| 429 | Rate limited | `{ "error": { "code": "RATE_LIMITED", ... } }` plus `Retry-After` |
| 500 | Transient failure | `{ "error": { "code": "INTERNAL_ERROR", "requestId": "..." } }` |

## Idempotency

- Add a unique constraint on `(source, external_id)`.
- Insert the ticket, audit event, and outbox row in one transaction.
- On a unique violation, load and return the existing ticket with `200`.
- Do not return `409` for a genuine retry.

## Security Checklist

- Secret loaded from `WEBHOOK_SECRET`; missing secret fails startup in production.
- Signature verification precedes JSON validation.
- Body size limit, for example 256 KB.
- Rate limit per source and IP.
- Generic error responses with a request ID.
- No secrets or full payloads in logs.
- Audit accepted and rejected calls with a `SYSTEM` actor.

## Test Cases

- Valid signature creates one ticket.
- Replayed timestamp is rejected.
- Tampered body is rejected.
- Same `(source, externalId)` returns `200` with the original ticket.
- Unsupported `schemaVersion` returns `422`.
- Missing secret fails startup in production.
