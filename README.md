# Pro-Goal

A project management tool where each **project is its own tenant**: people join projects, and per-field permissions control what each member may change. Slack is the only planned integration.

This is a monorepo with two apps:

| Folder | What it is | Stack |
|---|---|---|
| [`backend/`](backend/README.md) | REST API, background jobs, integrations | Python 3.14, Django 6.1, Django REST Framework, Celery, Redis, Postgres, Cloudflare R2 |
| [`frontend/`](frontend/README.md) | Single-page web app | React 19, TypeScript, Vite, Tailwind v4, shadcn (Base UI), TanStack Router/Query/Table/Form |

## Features

- Accounts: email signup with verification, Google sign in, password reset, session management, security log
- Projects with members, join requests, and a public explore page
- Tasks, board view, notes, comments, and workflow
- Per-member, per-field permissions with a members matrix editor
- File attachments uploaded straight from the browser to Cloudflare R2 through signed URLs
- Project activity feed
- Slack integration: channel mappings, delivery log, account linking

## Quick start

Prerequisites: Docker, [`uv`](https://docs.astral.sh/uv/) (backend), Node.js and npm (frontend).

```bash
# Once: shared Docker network used by both compose projects
docker network create pro-goal-network

# Backend (API on http://localhost:8000)
cd backend
cp .env.example .env              # fill in the values
docker compose up --build         # Postgres, Redis, API and Celery worker

# Frontend (http://localhost:3000, proxies /api to the backend)
cd ../frontend
cp .env.example .env
npm install
npm run dev
```

Start the backend first. See each app's README for running without Docker, the full list of environment variables, and production images.

## Repository layout

```
.
├── backend/    Django API (accounts, projects, tracker, attachments, security, integrations)
│   ├── docs/       OpenAPI schema and Slack app manifest
│   └── postman/    Postman collection and environment
└── frontend/   React app (src/routes, src/features, src/components)
```

## Development

```bash
# Backend
cd backend
uv run python manage.py test
uv run ruff check . && uv run ruff format .

# Frontend
cd frontend
npm run lint
npm test
npm run build
```

## Configuration and secrets

Each app reads its own `.env` (git-ignored). Copy `.env.example` in each folder and fill it in. Never commit `.env` files, virtual environments, `node_modules`, or `db.sqlite3`. Variables are required with no fallbacks: a missing one stops startup with a clear error.

## Documentation

- Backend setup, environment variables, API reference: [`backend/README.md`](backend/README.md)
- Frontend setup, layout, file uploads, Slack: [`frontend/README.md`](frontend/README.md)
- Backend design document: [`backend/project.md`](backend/project.md)
- Frontend build plan: [`frontend/PROJECT.md`](frontend/PROJECT.md)
- OpenAPI schema: [`backend/docs/openapi.yml`](backend/docs/openapi.yml)
