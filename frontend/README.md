# IT Helpdesk Web

React 19 + TypeScript + Vite + Tailwind CSS frontend for the IT helpdesk.

## Commands

Run from this directory:

```powershell
npm install
npm run dev         # http://127.0.0.1:5173
npm run typecheck
npm run lint
npm run build
npm run api:types   # regenerate src/types/api.ts, requires the API on :8000
```

The Vite dev server proxies `/health`, `/ready`, and `/api` to `http://127.0.0.1:8000`.

## API contract

`src/types/api.ts` is generated from the FastAPI OpenAPI document. Regenerate it after backend
schema changes:

```powershell
# terminal 1
cd ../backend
uv run uvicorn app.main:app --port 8000

# terminal 2
npm run api:types
```

Commit the regenerated file so CI can typecheck without running the API.

## Structure

```text
src/
  components/   Layout and shared UI
  lib/          API client (openapi-fetch)
  routes/       Route components
  types/        Generated OpenAPI types
```
