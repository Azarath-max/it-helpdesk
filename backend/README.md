# IT Helpdesk API

FastAPI backend for the IT helpdesk ticketing system.

## Commands

Run from this directory:

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run ruff check .
uv run mypy app
```

The API reads configuration from `backend/.env` first, then the repository root `.env`.
