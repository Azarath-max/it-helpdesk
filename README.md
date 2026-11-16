# IT Helpdesk

A single-tenant IT helpdesk ticketing system built as a portfolio project.

**Status:** Phase 0 foundations complete. Auth, tickets, and integrations are not implemented yet.

## What works today

- `GET /health` liveness and `GET /ready` database readiness.
- Request-ID and security-header middleware plus a stable JSON error envelope.
- An Alembic baseline migration that enables `citext`.
- A React overview page that polls both health endpoints through the Vite proxy.
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

- API docs: <http://localhost:8000/docs>
- API health: <http://localhost:8000/health>
- Web app: <http://localhost:5173>
- Mailpit: <http://localhost:8025>

Configuration is read from the repository root `.env` (see `.env.example`) or `backend/.env`.

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

Phase 1 adds users, sessions, registration/login/logout, Argon2id password hashing, cookie sessions, role and ownership guards, and the authorization test matrix. See the [MVP plan](docs/mvp-plan.md).
