# ADR 0001: FastAPI + React + PostgreSQL

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

Greenfield IT helpdesk portfolio project targeting junior full-stack and backend roles. The project must demonstrate authentication, role-based access control, relational modeling, a REST API, and an inbound automation integration. The developer is comfortable with JavaScript/TypeScript and is building Python backend experience.

## Decision

Use a modular monolith with:

- **Backend:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync), psycopg 3, Alembic.
- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS.
- **Database:** PostgreSQL 18.
- **Contract:** Pydantic models generate OpenAPI; TypeScript types are generated from it.

## Consequences

Positive:

- FastAPI provides typed validation, dependency injection, and interactive API documentation.
- SQLAlchemy + Alembic demonstrate real relational design and migration discipline.
- Python fits IT support and automation work better than a Node-only stack.
- Two deployable units remain simple: API and static frontend.

Negative:

- Two languages means no shared TypeScript package. Mitigation: generated OpenAPI types.
- Python packaging on Windows can be inconsistent. Mitigation: uv with a lockfile and pinned Python 3.13.
- Sync SQLAlchemy is less scalable than async. Mitigation: it is more than adequate for helpdesk traffic and avoids async session bugs.

## Alternatives considered

- **Next.js full-stack:** fewer moving parts, but hides API and RBAC boundaries that this project is meant to demonstrate.
- **Express + React:** one language, but loses the Python/automation angle and FastAPI's schema tooling.
- **Django:** batteries included, but its admin and auth abstractions would obscure the RBAC design being showcased.
