# Audit Event Schema

## Suggested Model

```prisma
enum ActorType {
  USER
  SYSTEM
}

model AuditEvent {
  id          String    @id @default(uuid())
  actorType   ActorType
  actorUserId String?
  action      String
  entityType  String
  entityId    String
  before      Json?
  after       Json?
  metadata    Json?
  requestId   String?
  ipAddress   String?
  createdAt   DateTime  @default(now())

  @@index([entityType, entityId, createdAt])
  @@index([actorUserId, createdAt])
  @@index([action, createdAt])
}
```

## Example Event

```json
{
  "id": "evt_01",
  "actorType": "USER",
  "actorUserId": "usr_42",
  "action": "ticket.status_changed",
  "entityType": "ticket",
  "entityId": "tkt_1007",
  "before": { "status": "OPEN" },
  "after": { "status": "IN_PROGRESS", "assigneeId": "usr_9" },
  "metadata": { "source": "REST", "requestId": "req_abc" },
  "requestId": "req_abc",
  "ipAddress": "203.0.113.10",
  "createdAt": "2026-11-14T10:15:00Z"
}
```

## Action Catalogue

- `auth.login_succeeded`
- `auth.login_failed`
- `auth.logout`
- `user.registered`
- `user.role_changed`
- `user.deactivated`
- `ticket.created`
- `ticket.updated`
- `ticket.status_changed`
- `ticket.assigned`
- `ticket.priority_changed`
- `comment.created`
- `comment.deleted`
- `webhook.received`
- `webhook.rejected`
- `notification.sent`
- `notification.failed`

Keep action names stable. They are part of the API and admin UI filter contract.

## Diff Rules

- Store only fields that changed.
- Use a per-entity allowlist. Never diff the whole row blindly.
- Redact `passwordHash`, tokens, secrets, and full request bodies.
- Truncate long text and record the original length.
- Represent deletions as `null`, not by omitting the key.
- Do not store file contents.

## Write Path

```text
BEGIN
  update ticket
  insert audit_event
  insert notification_outbox rows
COMMIT
```

If any step fails, the whole change rolls back. External delivery happens after commit.

## Read API

- `GET /api/audit-events?entityType=ticket&entityId=...&action=...&from=...&to=...`
- Admin only.
- Cursor pagination by `(createdAt, id)`, newest first.
- Return actor display name, not the full user record.

## Retention

- Define retention up front, for example 12 months.
- Archive to cold storage before deleting.
- Deletion is an administrative process, not an application endpoint.
- Document the policy in the README.
