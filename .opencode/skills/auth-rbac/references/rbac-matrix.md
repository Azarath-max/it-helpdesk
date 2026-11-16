# RBAC Matrix

Legend: yes = allowed, cond = conditional, no = denied. `owner` is the ticket requester. `assignee` is the assigned agent.

## Authentication

| Endpoint | user | agent | admin | Notes |
| --- | --- | --- | --- | --- |
| POST /api/auth/register | yes | yes | yes | Public. Always creates role `user`. |
| POST /api/auth/login | yes | yes | yes | Public and rate limited. |
| POST /api/auth/logout | yes | yes | yes | Revokes the current session. |
| GET /api/auth/me | yes | yes | yes | Safe profile fields only. |
| POST /api/auth/forgot-password | yes | yes | yes | Public. Same response for unknown emails. |
| POST /api/auth/reset-password | yes | yes | yes | Public. Single-use token. |

## Tickets

| Action | user | agent | admin | Condition |
| --- | --- | --- | --- | --- |
| GET /api/tickets | cond | yes | yes | user sees only own tickets |
| GET /api/tickets/:id | cond | yes | yes | owner, assignee, or admin |
| POST /api/tickets | yes | cond | yes | agent on behalf only if explicitly allowed |
| PATCH /api/tickets/:id | cond | yes | yes | user only while `OPEN`, title and description only |
| PATCH /api/tickets/:id/status | no | yes | yes | transition service enforces the target state |
| PATCH /api/tickets/:id/assign | no | cond | yes | agent may self-assign or claim unassigned |
| PATCH /api/tickets/:id/priority | no | yes | yes | audited |
| POST /api/tickets/:id/comments | cond | yes | yes | owner, assignee, agent, admin |
| GET /api/tickets/:id/comments | cond | yes | yes | user must be a participant |
| DELETE /api/comments/:id | cond | yes | yes | author within 5 minutes, admin always |

## Administration

| Action | user | agent | admin |
| --- | --- | --- | --- |
| GET /api/users | no | no | yes |
| PATCH /api/users/:id/role | no | no | yes |
| PATCH /api/users/:id/status | no | no | yes |
| GET /api/audit-events | no | no | yes |
| GET /api/webhook-events | no | no | yes |

## Enforcement Order

1. Authenticate the session or token.
2. Load the current user and role from the database.
3. Authorize by role.
4. Authorize by resource ownership or assignment.
5. Validate input.
6. Execute in a transaction.
7. Write the audit event.

## Failure Semantics

- `401` unauthenticated, invalid, or expired session.
- `403` authenticated but not permitted.
- `404` for resources the caller should not know exist, when existence is sensitive.
- Choose one policy for another user's ticket and apply it consistently. Do not leak existence through mixed responses.

## Query Rules

- Scope requester queries in SQL with `WHERE requester_id = :userId`. Never fetch all rows and filter in application code.
- Never trust `requesterId` from a request body when the caller is a `user`.
- Agents do not automatically become admins. User management is admin-only.
- Every role or permission change writes an audit event.

## Test Cases

| Case | Expected |
| --- | --- |
| user reads own ticket | 200 |
| user reads another user's ticket | 403 or 404 per policy |
| user changes status | 403 |
| agent changes status on any ticket | 200 if the transition is valid |
| agent changes a user's role | 403 |
| admin reads the audit log | 200 |
| unauthenticated request | 401 |
| expired session | 401 |
| agent self-assigns an unassigned ticket | 200 |
| agent assigns another agent without permission | 403 |
