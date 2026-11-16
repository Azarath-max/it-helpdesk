# Notification Matrix

## Events

| Event | Recipients | Template | Notes |
| --- | --- | --- | --- |
| ticket.created | requester, admins (optional) | `ticket-created` | Confirmation with ticket ID |
| ticket.assigned | assignee | `ticket-assigned` | Skip when the actor is the assignee |
| ticket.status_changed | requester, assignee | `ticket-status-changed` | Skip the actor |
| ticket.priority_changed | assignee | `ticket-priority-changed` | High and urgent only, optional |
| comment.created | other participants | `ticket-new-comment` | No comment body in the subject |
| ticket.reopened | assignee, admins | `ticket-reopened` | Include the reopen count |
| ticket.closed | requester | `ticket-closed` | Optional satisfaction link |

## Subject Examples

- `[HD-1007] Your ticket is now in progress`
- `[HD-1007] New comment from the IT team`
- `[HD-1007] Ticket resolved`
- `[HD-1007] Ticket reopened`

Keep subjects free of personal data and ticket descriptions.

## Outbox Schema

```prisma
enum NotificationStatus {
  PENDING
  SENDING
  SENT
  FAILED
  DEAD
}

model Notification {
  id             String             @id @default(uuid())
  ticketId       String?
  eventType      String
  recipientEmail String
  template       String
  payload        Json
  idempotencyKey String             @unique
  status         NotificationStatus @default(PENDING)
  attempts       Int                @default(0)
  lastError      String?
  nextAttemptAt  DateTime           @default(now())
  sentAt         DateTime?
  createdAt      DateTime           @default(now())

  @@index([status, nextAttemptAt])
}
```

Example `idempotencyKey`: `ticket.status_changed:tkt_1007:RESOLVED:usr_42`.

## Worker Lifecycle

1. Select due `PENDING` or retryable `FAILED` rows with `FOR UPDATE SKIP LOCKED`.
2. Mark `SENDING`.
3. Render the template and send with the provider idempotency key.
4. Mark `SENT` with `sentAt`, or `FAILED` with `attempts + 1` and `nextAttemptAt`.
5. After the maximum attempts, mark `DEAD` and alert.

## Retry Policy

- Attempts: 5.
- Backoff: 1m, 5m, 15m, 1h, 6h.
- Retry only transient failures: timeouts, `429`, `5xx`.
- Do not retry invalid addresses or template errors. Mark `DEAD` and surface the reason.

## Development

- Use Mailpit or MailHog in Compose.
- Point `SMTP_HOST` and `SMTP_PORT` at the local catcher.
- Never send real email from tests. Inject a fake transport that records messages.
- Assert on recipient, template, and idempotency key, not HTML whitespace.
