# Local Stack

## Services

| Service | Image | Host port | Purpose |
| --- | --- | --- | --- |
| api | local `uv run uvicorn` process | 8000 | FastAPI API |
| web | local `npm run dev` process | 5173 | Vite dev server for the React SPA |
| db | `postgres:18-alpine` | 5433 → 5432 | Primary database |
| mailpit | `axllent/mailpit:v1.20` | 8025, 1025 | Local email catcher |

Pin every image to a specific version. The API and web app run on the host during development;
only infrastructure services belong in Compose.

> **PostgreSQL 18:** the official image changed its `VOLUME` to `/var/lib/postgresql` and
> `PGDATA` to `/var/lib/postgresql/18/docker`. Mount the named volume at
> `/var/lib/postgresql`, not `/var/lib/postgresql/data`.

Host port 5433 avoids clashing with a locally installed PostgreSQL on 5432.

## Compose Notes

- `db` has a `pg_isready` healthcheck.
- `db` uses a named volume `pgdata` mounted at `/var/lib/postgresql`.
- Publish only the ports developers need: `5433`, `1025`, and `8025`.
- The API and worker read the repository root `.env` (or `backend/.env`).

## Environment Variables

```text
ENVIRONMENT=development
APP_BASE_URL=http://localhost:5173

DATABASE_URL=postgresql+psycopg://helpdesk:helpdesk@localhost:5433/helpdesk

SESSION_SECRET=change-me
WEBHOOK_SECRET=change-me-too

SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=helpdesk@example.test
```

Commit `.env.example` with placeholders. Never commit `.env`.

## Startup Sequence

1. `docker compose up -d db mailpit`
2. Wait for the `db` healthcheck.
3. `cd backend; uv sync`
4. `cd backend; uv run alembic upgrade head`
5. `cd backend; uv run uvicorn app.main:app --reload --port 8000`
6. `cd frontend; npm install; npm run dev`
7. Verify `GET http://127.0.0.1:8000/health` and `/ready` return `200`.
8. Open Mailpit at `http://localhost:8025`.
9. Run the notification worker with `cd backend; uv run python -m app.worker` when Phase 4 lands.

## CI Pipeline

Backend job:

1. Checkout.
2. Install Python 3.13 and uv.
3. `uv sync --locked`.
4. `uv run ruff check .` and `uv run ruff format --check .`.
5. `uv run mypy app`.
6. Start Postgres as a service container.
7. `uv run alembic upgrade head`.
8. `uv run pytest`.

Frontend job:

1. Checkout.
2. Install Node 24 and run `npm ci` from the lockfile.
3. `npm run lint`, `npm run typecheck`, `npm run build`.

Optionally scan dependencies for known vulnerabilities.

## Production Notes

- Build a single API image with `uv sync --locked --no-dev`; serve the SPA as static files.
- Use a managed database where possible.
- Inject secrets from the platform, not a committed file.
- Run migrations as a release step, not concurrently on every replica.
- Terminate TLS at a reverse proxy or platform edge.
- Enable database backups and test a restore.
- Set `ENVIRONMENT=production`; startup refuses default secrets.
- Run the outbox worker as a separate process or scheduled job.

## Troubleshooting

- API exits before migrations: check database health and retry logic.
- `OperationalError`/connection refused: the API is using `localhost` from inside a container
  instead of the Compose service name `db`.
- Emails missing: check `SMTP_HOST` and port `1025`, then open Mailpit on `8025`.
- Permission errors on volumes: check the container user and volume ownership.
- Postgres 18 refuses to start after upgrading: the volume is mounted at the old
  `/var/lib/postgresql/data` path; move it to `/var/lib/postgresql`.
- Migration drift: reset only the local database, never production.
