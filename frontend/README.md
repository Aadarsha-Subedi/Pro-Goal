# Pro-Goal frontend

React 19, TypeScript, Vite, Tailwind v4, shadcn (base-nova on Base UI), TanStack Router, Query, Table and Form, Phosphor icons, GSAP.

## Run

```bash
npm install
npm run dev        # http://localhost:3000, proxies /api to http://localhost:8000
npm run build      # type-check and production build
npm run lint
npm test           # vitest (API client)
```

The dev server runs on port **3000** because the backend's `PROJECT_MANAGEMENT_CSRF_TRUSTED_ORIGINS` defaults to `http://localhost:3000`. Start the backend (`uv run python manage.py runserver`) with Postgres and Redis up. Run a Celery worker only if you want emails sent: the backend `.env` may point at a real SMTP server.

## Docker

Both compose projects join the external network `pro-goal-network`; create it once with `docker network create pro-goal-network`, and start the backend first (`cd ../backend && docker compose up -d --build`).

```bash
docker compose up --build                                  # Vite dev server on http://localhost:3000 (Dockerfile.dev, hot reload)
docker compose --profile prod up --build frontend-prod     # production image on http://localhost:8080 (Dockerfile.prod)
```

The dev container proxies `/api` to the backend's `api` service (`DEV_API_PROXY_TARGET` in `docker-compose.yml`; outside Docker it defaults to `http://localhost:8000`). The production image is a Vite build served by nginx: `/api/` is forwarded to `API_UPSTREAM`, unknown paths fall back to `index.html`, and `VITE_API_BASE` and `VITE_GOOGLE_CLIENT_ID` are public build arguments read from `.env`.

## Environment

| Variable | Purpose |
|---|---|
| `VITE_API_BASE` | API origin. Empty means same origin (the dev proxy, nginx or the Worker forward `/api`); set a full origin only if the API is on another domain. |
| `VITE_GOOGLE_CLIENT_ID` | Google Identity Services client id. Empty shows the Google button disabled. |
| `DEV_API_PROXY_TARGET` | Dev server only: where `/api` is forwarded (`http://localhost:8000`). Set by `docker-compose.yml` in Docker. |

Every variable is required: `vite.config.ts` stops dev and build with `Missing environment variable: NAME` when one is unset (empty is allowed). There are no fallbacks.

## File uploads (R2)

Files go from the browser straight to the Cloudflare R2 bucket the backend signs for. The bucket needs a CORS rule allowing `PUT` and `GET` from the frontend origin (`http://localhost:3000` in dev) with headers `Content-Type` and `Content-Length`; without it uploads fail with "Couldn't reach file storage". See the backend README for bucket setup.

## Slack

Slack needs the backend running with the Slack app credentials and a public HTTPS tunnel (`PROJECT_MANAGEMENT_PUBLIC_API_URL`, for example ngrok). After a person approves the app or links their account, the backend sends the browser to `PROJECT_MANAGEMENT_FRONTEND_URL` at `/projects/<id>/integrations` or `/settings/integrations` with `?slack=...`; the SPA redirects those to `/app/projects/<id>/integrations` and `/app/account`.

## Layout

- `src/routes/` file routes: `/` landing, `/login`, `/signup`, `/verify-email`, `/forgot-password`, `/reset-password`, `/complete-profile`, `/terms`, `/privacy`, `/join`, `/app/*` (projects, tasks, board, notes, members and their permissions, settings, My tasks, account, activity, explore); `/confirm-email-change` is the emailed link for a new address, `/design-preview` (dev only).
- `src/lib/api.ts` the one API client: session cookie, CSRF (`X-CSRFToken` from the `csrftoken` cookie, fetched from `/api/csrf/` when missing), backend envelope, `ApiError` with the stable `code`.
- `src/features/auth/` auth screens and `api.ts` (maps backend error codes to what the screens show).
- `src/features/marketing/` landing page and blueprint sheet pieces.
- `src/features/projects/` shell pages, members, join requests, settings. `src/features/tracker/` tasks, board, notes, comments, workflow. `src/features/attachments/` uploads (browser to R2 through signed URLs), file lists, storage usage. `src/features/permissions/` per-member permission editor, the members matrix, `useLockText`. `src/features/activity/` project activity feed (`describe` turns backend entries into sentences; a test reads the backend action list). `src/features/explore/` listed projects and requests to join. `src/features/integrations/` project integrations page, Slack channel mappings, delivery log, Slack link and notification switches on the account page. `src/features/account/` signed-in devices, security log, personal storage (`/app/account`).
- `src/components/ui/` shadcn primitives, `src/components/patterns/` composed components, `src/motion/` GSAP helpers (reduced motion honoured in one place).
- `src/styles/` tokens (`tokens.css`) and the public-surface blueprint world (`blueprint.css`).

## Design system

`PRODUCT.md` (product truth) and `DESIGN.md` (visual system, with `.impeccable/design.json`). Open `/design-preview` in dev to see every component and state.
