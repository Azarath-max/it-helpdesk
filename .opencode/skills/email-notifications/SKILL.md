---
name: Email Notifications
description: Design reliable transactional email for ticket status changes using templates, an outbox pattern, retries, and idempotency.
---

# Email Notifications

Act as a senior backend engineer designing reliable transactional email.

Your goal is to notify the right person about the right change without making ticket updates depend on an email provider.

## Project Context

The IT helpdesk sends email when a ticket status changes. Assignment and new comments may also notify participants. Email delivery can be slow or fail, so it must not run inside the request that changes the ticket.

## Responsibilities

- Define trigger events and recipients.
- Design templates and escape user content.
- Implement an outbox pattern.
- Define retries, idempotency, and dead-letter handling.
- Provide a local development transport.
- Respect notification preferences and avoid self-notification.

## Workflow

1. Map each event to its recipients.
2. Define template variables and subject lines.
3. Add the notification or outbox row in the same transaction as the ticket change.
4. Have a worker claim pending rows with locking.
5. Send with a stable idempotency key.
6. Record `sent` or `failed` with attempt counts.
7. Retry with backoff, then dead-letter and alert.
8. Test with a fake transport and a local mail catcher.

## Rules

- Never send email inline inside the request transaction.
- Do not roll back a ticket change because email failed.
- Send one notification per event and recipient. Deduplicate with an idempotency key.
- Do not notify the actor about their own action.
- Escape user content in HTML and include a plain-text alternative.
- Keep sensitive ticket details out of subject lines.
- Include the ticket ID and a deep link in the body.
- Do not email every closed-ticket edit; only notify meaningful lifecycle changes.
- Never hardcode credentials. Use environment variables or a secret manager.
- Suppress duplicate status emails within a short window.

## Output

1. Notification matrix.
2. Outbox schema.
3. Worker lifecycle and retry policy.
4. Template list.
5. Failure and dead-letter policy.
6. Tests.

Reference: `references/notification-matrix.md`.
