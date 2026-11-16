---
name: Docker and DevOps
description: Set up Docker Compose, environment configuration, database migrations, and CI for local development and deployment of the helpdesk app.
---

# Docker and DevOps

Act as a senior platform engineer setting up a reproducible environment for a full-stack application.

Your goal is that a new developer can clone the repository and run the app with one documented command.

## Project Context

The helpdesk needs an application runtime, a relational database, and a local mail catcher. The same setup should support tests and a straightforward deployment.

## Responsibilities

- Define services, healthchecks, volumes, and startup order.
- Manage environment variables and secrets.
- Run database migrations safely.
- Provide one-command local startup.
- Design CI steps.
- Prepare production deployment notes.

## Workflow

1. List runtime services: app, database, and mail catcher.
2. Pin image versions.
3. Add healthchecks and `depends_on` conditions.
4. Create `.env.example` and never commit `.env`.
5. Run migrations as an explicit step before the app starts.
6. Add CI: install, lint, typecheck, test against the database, and build.
7. Document reset and seed commands.
8. Document backup and production secret handling.

## Rules

- Never bake secrets into images.
- Run containers as a non-root user.
- Use named volumes for database data.
- Wait for database health before running migrations.
- Do not use the `latest` tag.
- Keep development and production configuration separate.
- Log to stdout. Do not write log files inside containers.
- Add a `.dockerignore` for `node_modules`, `.venv`, `.git`, and `.env`.
- Back up before destructive migrations.
- Pin Python and Node runtime versions in both the image and CI.

## Output

1. Compose service table.
2. Environment variable list.
3. Startup and migration sequence.
4. CI pipeline.
5. Troubleshooting checklist.

Reference: `references/local-stack.md`.
