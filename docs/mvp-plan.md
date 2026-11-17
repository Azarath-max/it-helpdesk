# IT Helpdesk MVP Plan

- **Status:** Phase 4 (email notifications) complete. Webhook intake is next.
- **Last updated:** 2026-11-17
- **Goal:** A portfolio-grade, single-tenant IT helpdesk that demonstrates auth, RBAC, relational modeling, REST API design, transactional side effects, and a secure inbound integration.

## 1. Scope

In scope:

- Three roles: `user` (requester), `agent` (IT support), `admin`.
- Ticket creation, assignment, priority, comments, and an enforced status lifecycle.
- Append-only audit log.
- Email notifications on status changes through a transactional outbox.
- A generic HMAC-authenticated webhook that lets any automation create tickets.
- A React SPA and a FastAPI REST API.
- Local development with Docker Compose, Mailpit, and CI.

Out of scope for the MVP:

- Attachments, SLA automation, real-time updates, full-text search, multi-tenancy, SSO, i18n, Redis/Celery, microservices, ticket deletion, custom reporting.

## 2. Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.13 + FastAPI + Uvicorn |
| Validation/config | Pydantic v2 + pydantic-settings |
| ORM/migrations | SQLAlchemy 2.0 (sync) + psycopg 3 + Alembic |
| Database | PostgreSQL 18 |
| Auth | Opaque DB-backed sessions, Argon2id, HttpOnly cookie |
| Background work | Postgres outbox + `python -m app.worker` |
| Email | Jinja2 templates + smtplib; Mailpit locally |
| Frontend | React 19 + TypeScript + Vite + React Router |
| Server state | TanStack Query + openapi-fetch |
| API types | `openapi-typescript` from FastAPI's OpenAPI document |
| Styling | Tailwind CSS v4 |
| Backend quality | ruff + mypy + pytest |
| Frontend quality | oxlint + tsc + Vitest (later) |
| Local infra | Docker Compose: PostgreSQL 18 + Mailpit |
| CI | GitHub Actions |

Key decisions are recorded in `docs/adr/`.

## 3. Architecture

```text
frontend/ (React + Vite)
      |  HttpOnly session cookie + CSRF/origin check, JSON
      v
backend/app (FastAPI)
  routers -> Pydantic schemas -> services -> SQLAlchemy -> PostgreSQL
                                   |-- tickets/workflow (domain rules)
                                   |-- audit writer   (same transaction)
                                   |-- notification outbox (same transaction)
                                              |
                                   notification worker -> SMTP / Mailpit

Any automation --HMAC webhook--> /api/webhooks/tickets -> ticket service
```

Architecture rules:

- Modular monolith. One API process, one worker process, one database.
- Routers validate and delegate; services own business rules and transactions.
- Only services touch the database session, except the auth session lookup.
- Ticket creation/transition + audit event + outbox row are written atomically.
- The webhook and the REST API call the same ticket service.
- No event bus, message broker, or repository abstraction over SQLAlchemy.

## 4. Role capability matrix

`owner` is the ticket requester; `assignee` is the assigned agent.

| Capability | user | agent | admin |
| --- | --- | --- | --- |
| Register, login, logout, view own profile | yes | yes | yes |
| Create ticket | own only | on behalf if enabled | yes |
| List tickets | own only | all | all |
| View ticket | owner or participant | all | all |
| Edit title/description | own while `OPEN` | all | all |
| Set priority | at creation only | yes | yes |
| Assign ticket | no | self or another agent | any agent |
| Change status | close/reopen own `RESOLVED` | per workflow | per workflow |
| Reopen `CLOSED` ticket | no | no | yes |
| Comment publicly | own tickets | yes | yes |
| Internal note | no | yes | yes |
| Delete comment | own within 5 minutes | own within 5 minutes | any |
| Manage users and roles | no | no | yes |
| Read audit log | no | no | yes |
| Create ticket via webhook | HMAC service identity only | - | - |

Enforcement:

- Role and `requesterId` come from the session/DB, never the request body.
- Requester queries are scoped in SQL, not filtered after fetching.
- `401` unauthenticated, `403` authenticated but forbidden, `404` when existence is sensitive.
- Every role change and failed privileged attempt writes an audit event.

Full matrix: `.opencode/skills/auth-rbac/references/rbac-matrix.md`.

## 5. Ticket lifecycle

States: `OPEN`, `IN_PROGRESS`, `WAITING_ON_USER`, `RESOLVED`, `CLOSED`.

| From | To | Roles | Required | Side effects |
| --- | --- | --- | --- | --- |
| OPEN | IN_PROGRESS | agent, admin | assignee | audit; email requester + assignee |
| OPEN | CLOSED | agent, admin | reason | audit; email requester |
| IN_PROGRESS | WAITING_ON_USER | agent, admin | comment | audit; email requester |
| IN_PROGRESS | RESOLVED | agent, admin | resolution note | set `resolved_at`; audit; email requester |
| IN_PROGRESS | OPEN | admin | reason | clear assignee; audit |
| WAITING_ON_USER | IN_PROGRESS | agent, admin | - | audit |
| WAITING_ON_USER | RESOLVED | agent, admin | resolution note | set `resolved_at`; audit; email requester |
| WAITING_ON_USER | CLOSED | admin | reason | audit; email requester |
| RESOLVED | CLOSED | owner, agent, admin | - | set `closed_at`; audit |
| RESOLVED | OPEN | owner, agent, admin | reason | clear `resolved_at`; `reopen_count++`; audit; email assignee |
| CLOSED | OPEN | admin | reason | clear timestamps; `reopen_count++`; audit; email requester + assignee |

Everything else returns `409 INVALID_STATUS_TRANSITION`.

Rules:

- `IN_PROGRESS` requires an assignee.
- One transition service used by REST and webhook.
- Optimistic concurrency with expected status or a `version` column.
- No-op transitions produce no audit event and no email.
- Priorities: `LOW`, `MEDIUM`, `HIGH`, `URGENT`.

Full matrix: `.opencode/skills/ticket-workflow/references/status-transitions.md`.

## 6. Module boundaries

| Module | Responsibility | May depend on |
| --- | --- | --- |
| `auth` | Register, login, logout, sessions, password hashing, CSRF, guards | users, sessions |
| `users` | Profile, admin user management, role changes | audit |
| `tickets` | Ticket CRUD, scoped queries, assignment, priority | workflow, audit, outbox |
| `tickets/workflow` | Transition table and `transition_ticket` | ticket data, audit, outbox |
| `comments` | Comment CRUD, visibility, participation checks | workflow, audit, outbox |
| `audit` | `record_audit(session, event)`, admin query | - |
| `notifications` | Outbox writer, templates, worker, mail transport | - |
| `webhooks` | HMAC verification, replay checks, idempotent intake | ticket service, audit |

## 7. Data model

| Entity | Key fields | Constraints |
| --- | --- | --- |
| `users` | id, email, name, password_hash, role, is_active, timestamps | unique citext email; role enum |
| `sessions` | id, user_id, token_hash, expires_at, created_at, last_used_at | unique token hash; index expires_at |
| `tickets` | id, public_ref, title, description, status, priority, requester_id, assignee_id, category, source, external_id, resolution_note, resolved_at, closed_at, reopen_count, version, timestamps | unique `(source, external_id)`; indexes on status, assignee/status, requester/created |
| `comments` | id, ticket_id, author_id, body, visibility, created_at, deleted_at | index ticket/created |
| `audit_events` | id, actor_type, actor_user_id, action, entity_type, entity_id, before, after, metadata, request_id, ip, created_at | append-only; indexes on entity/created, actor/created, action/created |
| `notifications` | id, ticket_id, event_type, recipient, template, payload, idempotency_key, status, attempts, next_attempt_at, sent_at | unique idempotency key; index status/next attempt |
| `password_reset_tokens` | id, user_id, token_hash, expires_at, used_at | hashed, single-use |

No ticket deletion. Comments are soft-deleted. Users are deactivated.

## 8. REST API surface

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | public | Create a requester account |
| POST | `/api/auth/login` | public | Start a session |
| POST | `/api/auth/logout` | authenticated | Revoke the session |
| GET | `/api/auth/me` | authenticated | Current profile and role |
| POST | `/api/auth/forgot-password` | public | Neutral response |
| POST | `/api/auth/reset-password` | public | Single-use token |
| GET | `/api/tickets` | all, scoped | Filter and paginate |
| POST | `/api/tickets` | user, agent, admin | Create |
| GET | `/api/tickets/:id` | owner, agent, admin | Detail |
| PATCH | `/api/tickets/:id` | owner while OPEN, agent, admin | Edit fields |
| PATCH | `/api/tickets/:id/status` | agent, admin, owner for close/reopen | Transition |
| PATCH | `/api/tickets/:id/assign` | agent, admin | Assign or claim |
| PATCH | `/api/tickets/:id/priority` | agent, admin | Priority change |
| GET | `/api/tickets/:id/comments` | participants | Thread |
| POST | `/api/tickets/:id/comments` | participants | Add comment |
| DELETE | `/api/comments/:id` | author, admin | Soft delete |
| GET | `/api/users` | admin | List users |
| PATCH | `/api/users/:id/role` | admin | Role change |
| PATCH | `/api/users/:id/status` | admin | Activate/deactivate |
| GET | `/api/audit-events` | admin | Audit query |
| POST | `/api/webhooks/tickets` | HMAC service | Idempotent intake |
| GET | `/health`, `/ready` | public | Liveness and readiness |

Conventions:

- Error envelope: `{ "error": { "code", "message", "details", "requestId" } }`.
- Pagination: `page`, `pageSize` (max 100), `total`.
- Allowlisted sorting.
- `201` with `Location` on creation; `409` for invalid transitions and concurrency.
- Webhook: `201` created, `200` duplicate, `4xx` no retry, `5xx` retry.

## 9. Cross-cutting rules

- Pydantic validates every boundary; TypeScript types are generated from OpenAPI.
- Business change + audit + outbox are one transaction.
- Request ID on every request; structured logs with redaction.
- Stable error codes; no stack traces in responses.
- Security headers, body size limits, and auth/webhook rate limits added during hardening.
- Settings validated at startup; production refuses default secrets.

## 10. Implementation phases

| Phase | Content | Status |
| --- | --- | --- |
| 0 | Foundations: repo, FastAPI, SQLAlchemy/Alembic, Vite/React, Compose, CI | Complete |
| 1 | Auth + RBAC: users/sessions, Argon2id, cookie sessions, guards, auth tests | Complete |
| 2 | Tickets + audit foundation: CRUD, scoping, filters, audit writer | Complete |
| 3 | Workflow + comments: transition service, comments, internal notes | Complete |
| 4 | Email notifications: outbox, templates, worker, Mailpit, retries | Complete |
| 5 | Webhook + demo script: HMAC, replay protection, idempotency | Next |
| 3 | Workflow + comments: transition service, comments, internal notes | Planned |
| 4 | Email notifications: outbox, templates, worker, Mailpit, retries | Planned |
| 5 | Webhook + demo script: HMAC, replay protection, idempotency | Planned |
| 6 | Admin: user management, audit query, minimal admin UI | Planned |
| 7 | Hardening: security audit, tests, docs, Docker image, demo | Planned |

## 11. Testing strategy

- **Unit:** transition matrix, HMAC verification, priority mapping, permission predicates.
- **Integration:** auth flows, full RBAC/IDOR matrix, ticket CRUD, transitions with side effects, webhook idempotency, worker retries with a fake mailer.
- **E2E (optional):** login, create ticket, agent resolves, requester sees email in Mailpit, admin sees audit entry.
- **Database:** real PostgreSQL, migrations first, truncate between suites. Never mock the ORM.
- **CI:** ruff, mypy, pytest, frontend lint/typecheck/build.

## 12. Risks

| Risk | Mitigation |
| --- | --- |
| Auth/RBAC mistakes | Matrix-driven implementation and IDOR tests from Phase 1 |
| Status rules drifting | Single transition service for REST and webhook |
| Email provider outage | Transactional outbox with retries and dead-letter |
| Webhook replay/duplicates | HMAC, timestamp window, unique `(source, external_id)` |
| Scope creep | Explicit out-of-scope list |
| Windows tooling friction | `npm.cmd`, uv-managed Python, Docker Compose |
| Postgres 18 volume change | Mount `/var/lib/postgresql`, not `/var/lib/postgresql/data` |

## 13. Decisions

- **No n8n dependency.** The webhook remains as a generic integration surface. A signed Python script will demonstrate and test it. n8n can call the same endpoint later if desired.
- **Sync SQLAlchemy + `def` routes.** Simpler transactions and fewer async pitfalls; revisit only if profiling demands it.
- **Database-backed sessions.** Immediate revocation and role freshness; no JWT refresh machinery.
- **OpenAPI-generated TypeScript types.** Server Pydantic models are the contract.
- **Python 3.13.** Pin for broad wheel support; uv manages the toolchain.
