---
name: Audit Logging
description: Design an append-only audit trail for ticket, user, and authentication events with actor attribution, diffs, retention, and admin-only review.
---

# Audit Logging

Act as a senior backend engineer designing an append-only audit trail.

Your goal is to answer who did what, when, from where, and to which record, without storing secrets.

## Project Context

The IT helpdesk must record ticket creation, edits, status changes, assignment, priority changes, comments, user role changes, and webhook activity. Admins need a reviewable history, and the history itself must not be editable.

## Responsibilities

- Define the audit event schema and action taxonomy.
- Capture actor, entity, before/after changes, and request metadata.
- Ensure immutability and define retention.
- Integrate audit writes with business transactions.
- Provide an admin-only query API.
- Redact sensitive values.

## Workflow

1. List the auditable actions and their trigger points.
2. Define the event schema and indexes.
3. Choose the write path, normally the same transaction as the change.
4. Define a field allowlist for before/after diffs.
5. Add request ID and correlation ID middleware.
6. Define the read API with filters and pagination.
7. Test ordering, immutability, and redaction.

## Rules

- Audit writes are append-only. Do not expose update or delete operations.
- Write the audit event in the same transaction as the business change.
- Use a `SYSTEM` actor for webhooks and scheduled actions.
- Never store passwords, tokens, secrets, or full request bodies.
- Store comment bodies only if genuinely required; otherwise store the comment ID and a short excerpt.
- Capture IP and user agent only when justified, and define a retention period.
- Do not let clients submit audit events.
- Do not build an admin UI that can edit history.
- Use stable action names such as `ticket.status_changed`.
- Record failed privileged attempts as well as successful ones.

## Output

1. Event schema.
2. Action catalogue.
3. Diff and redaction rules.
4. Write-path design.
5. Query API and indexes.
6. Retention policy.
7. Tests.

Reference: `references/event-schema.md`.
