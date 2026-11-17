# IT Helpdesk

A single-tenant IT helpdesk ticketing system built as a portfolio project.

**Status:** Phase 3 complete. Enforced ticket workflow, assignment, public comments, and internal
notes are live. Email notifications are next.

## What works today

- `GET /health` liveness and `GET /ready` database readiness.
- Request-ID and security-header middleware, an origin check on state-changing API calls, and a
  stable JSON error envelope.
- Alembic migrations for `citext`, `users`, `sessions`, and `password_reset_tokens`.
- Registration, login, logout, session-backed `GET /api/auth/me`, and password reset.
- Argon2id password hashing, opaque session tokens stored as SHA-256 hashes, and a 14-day HttpOnly
  `SameSite=Lax` session cookie.
- Role-based access control with an admin-only `GET /api/users` paginated endpoint.
- Scoped ticket CRUD: requesters manage their own tickets, agents and admins see the full queue;
  status, priority, and text search filters; optimistic-concurrency edits.
- Enforced ticket workflow: validated status transitions, assignment and claiming, reopen counters,
  and resolution notes, all with optimistic concurrency.
- Public comments and internal notes with soft deletion and role-based visibility.
- An append-only `audit_events` table recording ticket creation, edits, transitions, assignment,
  and comments with before/after diffs.
- A React app with sign-in, registration, forgot/reset password, a protected dashboard, ticket
  lists, creation, and detail/editing.
- Docker Compose for PostgreSQL 18 (host port 5433) and Mailpit.
- CI for ruff, mypy, pytest, and frontend lint/typecheck/build.

## Stack

- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 18
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS
- **Local infrastructure:** Docker Compose (PostgreSQL + Mailpit)
- **Tooling:** uv, npm, ruff, mypy, pytest, GitHub Actions

## Prerequisites

- Node.js 24+
- uv
- Docker Desktop
- Python 3.13 (uv installs and pins it)

On Windows PowerShell, use `npm.cmd` if script execution is disabled. If `uv` is not found after
installation, open a new terminal or add `%USERPROFILE%\.local\bin` to `PATH`.

## Quick start

```powershell
# 1. Start PostgreSQL (host port 5433) and Mailpit
docker compose up -d

# 2. Backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

URLs:

- API docs: <http://127.0.0.1:8000/docs>
- API health: <http://127.0.0.1:8000/health>
- Web app: <http://127.0.0.1:5173>
- Mailpit: <http://127.0.0.1:8025>

Configuration is read from the repository root `.env` (see `.env.example`) or `backend/.env`.

### Accounts and password resets

Self-registration always creates a `user` account. Promote a demo account to `agent` or `admin`
directly in the database; role management endpoints arrive in Phase 6.

In development, `POST /api/auth/forgot-password` logs the reset link to the API console instead of
sending email. The link is single-use and expires after 30 minutes. Email delivery via the outbox
worker arrives in Phase 4.

## Commands

| Task | Command |
| --- | --- |
| Backend dev server | `cd backend; uv run uvicorn app.main:app --reload --port 8000` |
| Backend tests | `cd backend; uv run pytest` |
| Backend lint | `cd backend; uv run ruff check .` |
| Backend format | `cd backend; uv run ruff format .` |
| Backend types | `cd backend; uv run mypy app` |
| Migrations | `cd backend; uv run alembic upgrade head` |
| Frontend dev server | `cd frontend; npm run dev` |
| Frontend build | `cd frontend; npm run build` |
| Frontend lint | `cd frontend; npm run lint` |
| Regenerate API types | `cd frontend; npm run api:types` |

## Structure

```text
backend/        FastAPI app, SQLAlchemy models, Alembic migrations, tests
frontend/       React + TypeScript SPA
docs/           MVP plan and architecture decision records
.opencode/      Project skills for OpenCode
docker-compose.yml
```

## Documentation

- [MVP plan](docs/mvp-plan.md)
- [ADR 0001: Stack](docs/adr/0001-stack.md)
- [ADR 0002: Auth sessions](docs/adr/0002-auth-sessions.md)
- [ADR 0003: Webhook](docs/adr/0003-webhook.md)

## Next phase

Phase 4 adds email notifications: a transactional outbox, templates, worker, retries, and Mailpit
previews. See the [MVP plan](docs/mvp-plan.md).
