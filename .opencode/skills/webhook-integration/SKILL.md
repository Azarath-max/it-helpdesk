---
name: Webhook Integration
description: Design and review secure inbound webhook endpoints with HMAC authentication, replay protection, idempotency, and safe retry semantics.
---

# Webhook Integration

Act as a senior backend engineer designing secure inbound webhooks.

Your goal is to let an external system create tickets safely, even when it retries, duplicates, or sends malformed requests.

## Project Context

Any external automation — a script, n8n, Zapier, or an email poller — can call `POST /api/webhooks/tickets` to create tickets. The endpoint is unauthenticated by user session, so it needs its own service authentication, replay protection, and idempotency. The same size limits and validation apply regardless of caller.

## Responsibilities

- Define the endpoint contract and schema version.
- Authenticate callers with HMAC signatures.
- Prevent replay attacks and duplicate tickets.
- Validate and map payloads strictly.
- Define status codes and retry semantics.
- Rate limit requests and bound body size.
- Audit accepted and rejected webhook calls.

## Workflow

1. Agree the schema version and required fields.
2. Use HMAC-SHA256 over the timestamp and raw request body.
3. Store the shared secret in the environment or a secret manager. Fail closed in production when it is missing.
4. Read the raw body before JSON parsing and verify the signature in constant time.
5. Validate with a strict schema and reject privileged fields.
6. Enforce idempotency with a unique `(source, external_id)` constraint.
7. Create the ticket through the same service used by the REST API.
8. Return `201` for created, `200` for duplicate, `4xx` for bad input, and `5xx` for transient failures.
9. Write an audit event for every accepted or rejected call.

## Rules

- Never trust `role`, `status`, `assigneeId`, or `requesterId` from a webhook unless the contract explicitly allows it.
- Verify the signature against the raw request body, not a re-serialized object.
- Reject timestamps older than five minutes.
- Compare signatures in constant time.
- Never return stack traces or internal identifiers.
- Do not ask the caller to retry `4xx` responses. Do retry `5xx`.
- Return the original ticket for duplicates so retries are safe.
- Limit body size and request rate per source.
- An IP allowlist is optional defense in depth, never the only control.
- Log request ID, source, outcome, and ticket ID, but not full payloads containing personal data.

## Output

1. Endpoint contract.
2. Signature verification steps.
3. Idempotency design.
4. Status code table.
5. Security checklist.
6. Test cases.

Reference: `references/webhook-contract.md`.
