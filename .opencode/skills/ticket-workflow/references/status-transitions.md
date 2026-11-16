# Status Transition Matrix

## States

| Status | Meaning |
| --- | --- |
| OPEN | Created, not yet being worked on. |
| IN_PROGRESS | An agent owns it and is actively working. |
| WAITING_ON_USER | The agent needs information or action from the requester. |
| RESOLVED | A fix or answer was provided, awaiting confirmation. |
| CLOSED | Finished. Terminal for requesters. |

## Transitions

| From | To | Allowed roles | Required | Side effects |
| --- | --- | --- | --- | --- |
| OPEN | IN_PROGRESS | agent, admin | assignee_id | audit, email requester and assignee |
| OPEN | CLOSED | agent, admin | resolution_note | audit, email requester |
| IN_PROGRESS | WAITING_ON_USER | assignee, agent, admin | comment | audit, email requester |
| IN_PROGRESS | RESOLVED | assignee, agent, admin | resolution_note | set `resolved_at`, audit, email requester |
| IN_PROGRESS | OPEN | admin | reason | clear assignee, audit |
| WAITING_ON_USER | IN_PROGRESS | assignee, agent, admin | none | audit, optional email assignee |
| WAITING_ON_USER | RESOLVED | assignee, agent, admin | resolution_note | set `resolved_at`, audit, email requester |
| WAITING_ON_USER | CLOSED | admin | reason | audit, email requester |
| RESOLVED | CLOSED | owner, agent, admin | none | set `closed_at`, audit |
| RESOLVED | OPEN | owner, agent, admin | reason | clear `resolved_at`, increment `reopen_count`, audit, email assignee |
| CLOSED | OPEN | admin | reason | clear `closed_at` and `resolved_at`, increment `reopen_count`, audit, email requester and assignee |

Reject every transition not listed with `409` or `422` and a stable error code such as `INVALID_STATUS_TRANSITION`.

## Optional Automation

- A user comment on a `WAITING_ON_USER` ticket may move it to `IN_PROGRESS`. Record the actor as the system and note the trigger in the audit event.
- A scheduled job may close `RESOLVED` tickets after a documented grace period. Use a system actor.

## Priority and Target Times

| Priority | First response | Target resolution |
| --- | --- | --- |
| LOW | 24h | 72h |
| MEDIUM | 8h | 24h |
| HIGH | 4h | 8h |
| URGENT | 1h | 4h |

Store `first_responded_at`, `due_at`, and `resolved_at` only if you will use them. Compute overdue status from timestamps rather than storing a separate boolean.

## Concurrency

- Include `currentStatus` in the transition request or use a `version` column.
- Update with `WHERE id = :id AND status = :expectedStatus`.
- If zero rows are affected, return `409` and tell the caller the ticket changed.

## Test Matrix

- Every allowed transition succeeds for each permitted role.
- Every disallowed transition is rejected.
- A requester cannot move a ticket to `IN_PROGRESS`.
- `IN_PROGRESS` without an assignee is rejected.
- Reopening restores the correct timestamps.
- Two concurrent transitions: one succeeds, one gets `409`.
- A no-op transition produces no audit event and no email.
