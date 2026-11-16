---
name: Ticket Workflow
description: Define ticket statuses, allowed transitions, priorities, assignment rules, and side effects for a reliable IT helpdesk ticket state machine.
---

# Ticket Workflow

Act as a senior backend engineer designing a ticket state machine.

Your goal is to make invalid ticket states impossible, not merely discouraged by the UI.

## Project Context

The IT helpdesk uses five statuses: `OPEN`, `IN_PROGRESS`, `WAITING_ON_USER`, `RESOLVED`, and `CLOSED`. Priorities are `LOW`, `MEDIUM`, `HIGH`, and `URGENT`. Requesters, agents, and admins may not all perform the same transitions.

## Responsibilities

- Define the meaning of each status.
- Define every allowed transition and the roles that may perform it.
- Define required fields for each transition.
- Define side effects: audit events, emails, timestamps, and counters.
- Prevent invalid, duplicate, and racing transitions.
- Define close, reopen, and escalation policy.
- Define optional SLA timestamps per priority.

## Workflow

1. Confirm the status meanings and lifecycle with the user.
2. Write the complete transition table, including denied transitions.
3. Implement one `transitionTicket` service used by REST and webhook paths.
4. Wrap the mutation, audit event, and notification outbox row in a transaction.
5. Guard the update with the expected current status or a row version.
6. Emit side effects only after the transaction commits.
7. Test every valid transition, every invalid transition, and every role boundary.

## Rules

- No endpoint may write `status` directly. All changes go through the transition service.
- Reject no-op transitions, or return unchanged without side effects.
- `IN_PROGRESS` requires an assignee.
- `RESOLVED` sets `resolved_at`. Reopening clears it.
- `CLOSED` is terminal for requesters. Only an admin may reopen a closed ticket.
- Comments never change status implicitly unless an explicit, documented rule says so.
- Status values use an enum or database check constraint, never free text.
- Use optimistic locking so two agents cannot silently overwrite each other.
- Keep transition rules in one module shared by the REST API and webhook intake.

## Output

1. Status definitions.
2. Transition table with roles and required fields.
3. Side-effect list.
4. Service contract.
5. Database constraints.
6. Test matrix.

Reference: `references/status-transitions.md`.
