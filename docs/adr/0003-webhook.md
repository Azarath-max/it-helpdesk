# ADR 0003: Generic signed webhook, no n8n dependency

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

The original scope used n8n to triage inbound email and create tickets. n8n is an external workflow tool, not a runtime dependency of the helpdesk. Coupling the API contract to one automation vendor reduces flexibility and adds a service to operate.

## Decision

Expose a generic inbound webhook at `POST /api/webhooks/tickets`.

- Authenticate callers with HMAC-SHA256 over a timestamp and the raw body.
- Reject stale timestamps and enforce a unique `(source, external_id)` constraint for idempotency.
- Return `201` on creation, `200` for a duplicate delivery, `4xx` for invalid requests, and `5xx` for transient failures.
- Treat the caller as a `SYSTEM` actor in the audit log.
- Demonstrate and test the contract with a signed Python script rather than n8n.

## Consequences

Positive:

- Any automation tool can call the endpoint: a script, n8n, Zapier, or a future email poller.
- The integration can be tested deterministically in CI.
- No extra service to run or document.

Negative:

- No visual workflow demo. Mitigation: the signed script and OpenAPI docs show the contract clearly.
- A future email-to-ticket feature will need its own poller or workflow.

## Alternatives considered

- **Keep n8n:** useful demo, but adds an external dependency and a second configuration surface.
- **Remove the webhook entirely:** loses a strong demonstration of authentication, replay protection, and idempotency.
- **Email ingestion inside the API:** more scope and more operational risk than the MVP needs.
