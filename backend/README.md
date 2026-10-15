# Project Management Backend

Django REST API for a project management tool where each **project is its own tenant**: people join projects and per-field permissions control what each member may change. Slack is the only planned integration.

`project.md` is the design document (features, models, endpoints, permission codes, open questions). Features are built one at a time in its "Feature map" order.

## Status

| # | Feature | State |
|---|---------|-------|
| 1 | Accounts and sessions | Implemented (this README documents it) |
| 2-9 | Projects, tasks, attachments, permissions, ... | Not started |

## Stack

Python 3.14, Django 6.1, Django REST Framework, `django-allauth` (email-address and social-account tables only), Celery, Redis, Postgres, Argon2, Pillow, boto3 (Cloudflare R2). Managed with `uv`.

## Setup

```bash
uv sync
cp .env.example .env            # fill in the values
docker compose up -d            # Postgres + Redis
uv run python manage.py migrate
uv run python manage.py createsuperuser   # optional, for /admin/
uv run python manage.py runserver
```

The compose project is `pro-goal-backend` and its containers join the external network `pro-goal-network` (shared with the frontend); create it once with `docker network create pro-goal-network`.

To run the whole backend in containers instead (Postgres, Redis, the API on port 8000 and a Celery worker with beat, all built from `Dockerfile.dev`; the `api` container runs `migrate` and `seed_demo_projects` before starting, both safe to repeat):

```bash
docker compose up --build       # migrates on start; Ctrl+C to stop
```

The `api` and `celery` services reach Postgres and Redis by service name (`PROJECT_MANAGEMENT_DB_HOST` and `PROJECT_MANAGEMENT_REDIS_URL` are overridden in `docker-compose.yml`) and mount the source, so code changes reload. `Dockerfile.prod` is the production image (it does not migrate or seed on start: run `python manage.py migrate && python manage.py seed_demo_projects` once per deploy as a one-off command against the production database) (gunicorn on port 8080, no dev dependencies, no `.env`: variables are injected at runtime); build it with `docker build -f Dockerfile.prod -t pm-api:prod .`.

Background jobs (email, avatar import, purge jobs) need a worker and the beat scheduler:

```bash
uv run celery -A config worker -Q default,integrations -l info
uv run celery -A config beat -l info
```

Beat state files (`celerybeat-schedule*`) are written to `.celery/` (git-ignored, created automatically).

Set `PROJECT_MANAGEMENT_EMAIL_BACKEND` to Django's console backend locally (or the SMTP backend plus the `PROJECT_MANAGEMENT_EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS` variables), so verification and reset links are printed to the worker (or server) log. Avatars go to `media/` unless the `PROJECT_MANAGEMENT_R2_*` variables are set.

### Environment variables

All are required and read in `config/settings.py` (no fallbacks: a missing variable raises `ImproperlyConfigured` at startup; empty is fine for optional ones like R2 or `COOKIE_DOMAIN`). `.env.example` lists every one with comments. Key ones: `PROJECT_MANAGEMENT_DB_*`, `PROJECT_MANAGEMENT_REDIS_URL` (one full URL, database 0; `rediss://` enables TLS), `PROJECT_MANAGEMENT_DB_SSLMODE`, `PROJECT_MANAGEMENT_SECRET_KEY`, `PROJECT_MANAGEMENT_DEBUG`, `PROJECT_MANAGEMENT_FRONTEND_URL` (used in email links and CORS), `PROJECT_MANAGEMENT_NUM_PROXIES`, `PROJECT_MANAGEMENT_GOOGLE_CLIENT_ID`, `PROJECT_MANAGEMENT_R2_*`, `PROJECT_MANAGEMENT_SENTRY_DSN` (empty disables Sentry; with `DEBUG=true`, `GET /sentry-debug/` raises an error to verify it), `PROJECT_MANAGEMENT_ENVIRONMENT` (`local` or `prod`; the name shown in Sentry, and in `prod` signups and email changes with disposable addresses such as yopmail or mailinator are refused with `disposable_email`, using the `disposable-email-domains` list), `PROJECT_MANAGEMENT_RELAX_THROTTLES` (local development only, see Security).

## Tests and lint

```bash
uv run python manage.py test                       # all tests
uv run python manage.py test accounts.tests.test_auth_flow.LoginTests
PROJECT_MANAGEMENT_USE_SQLITE=1 uv run python manage.py test   # no Docker available
uv run ruff check . && uv run ruff format .
```

Tests use an in-memory cache and run Celery tasks eagerly.

## API

All endpoints are under `/api/`. Responses use one envelope: `success`, `status_code`, `message`, plus `data`/`meta` on success or `errors` and a stable machine-readable `code` on failure. Request bodies with unknown fields are rejected. The API uses server-side sessions with CSRF: call `GET /api/csrf/` first (it sets the `csrftoken` cookie and returns the same value as `data.csrf_token`), then send that value as the `X-CSRFToken` header on every unsafe request (including login and signup).

| Method and path | Purpose |
|---|---|
| `GET /csrf/` | Set the CSRF cookie; returns `data.csrf_token` |
| `POST /auth/signup/` | Email signup. Same neutral 202 whether or not the email exists |
| `POST /auth/verify-email/`, `/auth/verify-email/resend/` | Confirm (single use, 24 h) and resend (60 s cooldown) |
| `POST /auth/login/` | Email, password, optional `remember_me` |
| `POST /auth/google/` | Google ID token sign in or sign up (JSON; used to re-confirm identity) |
| `POST /auth/google/redirect/` | Where Google sends the browser back after its sign-in page (`response_mode=form_post`): form fields `id_token` and `state`. `state` (`<nonce>.<0\|1>`, the 1 meaning remember me) must equal the `pg_google_state` cookie and the token's nonce must match. Always a 302 to `/app` or `/login?google_error=google_failed\|rate_limited` |
| `POST /auth/logout/` | Optional `all_other_sessions` |
| `POST /auth/password/reset/`, `/auth/password/reset/confirm/` | Emailed link, valid 1 h, revokes all sessions |
| `POST /auth/password/change/` | Current plus new password, revokes other sessions |
| `GET/PATCH /me/` | Profile |
| `POST/DELETE /me/tour/` | Mark the onboarding walkthrough done / reset it (`tour_completed` on `/me/`) |
| `POST/DELETE /me/avatar/` | Avatar (JPEG, PNG, WebP, 2 MB; re-encoded to WebP at most 512 px) |
| `GET /me/sessions/`, `DELETE /me/sessions/<id>/` | List and revoke sessions |
| `POST /me/delete/`, `/me/delete/cancel/` | Soft delete with a 7-day grace period |

### Projects (feature 2)

A project is the tenant: every project route returns **404** to non-members. Lists are paginated (`limit`, `offset`; 25 by default, 100 at most). Sensitive owner actions (delete, regenerate join code, start a transfer) need re-authentication in the body: `password`, or `id_token` (a fresh Google sign-in) for social-only accounts.

| Method and path | Purpose |
|---|---|
| `POST /projects/`, `GET /projects/` | Create (caller becomes owner); list the caller's projects |
| `GET/PATCH/DELETE /projects/<id>/` | Detail (includes the caller's permissions), edit per field, soft delete (7-day undo) |
| `POST /projects/<id>/copy/` | Copy a demo project into a project you own (optional `name`; max 3 copies per user, 5 per hour) |
| `POST /projects/<id>/archive/`, `/unarchive/`, `/restore/` | Archive (read-only), restore from archive, undo a delete |
| `POST /projects/<id>/join-code/regenerate/` | New 6-character code (owner) |
| `POST /projects/join/` | Submit a join code; creates a pending request |
| `GET /projects/<id>/join-requests/`, `POST .../<request>/approve/`, `/reject/` | Owner reviews requests |
| `GET /projects/<id>/members/`, `DELETE .../members/<user>/`, `POST /projects/<id>/leave/` | Members; remove with a `reassign` map; leave |
| `POST /projects/<id>/transfer/`, `/transfer/cancel/` | Offer or cancel an ownership transfer (7 days) |
| `GET /transfers/`, `POST /transfers/<id>/accept/` | The recipient's pending offers; accept |

Until feature 5 (field-level permissions) lands, only the owner holds permissions (`projects/permissions.py`). Join codes use letters and digits without `0 O 1 I L`; 5 wrong codes per hour per user and per IP, at most 10 open requests per user. The explore page is not built yet. Notable codes: `invalid_join_code`, `join_code_throttled` (429), `already_member`, `join_request_cooldown`, `project_archived`, `fields_forbidden`, `reauth_failed`, `owner_only`.

### Tasks and notes (feature 3)

Everything is scoped to a project (`/projects/<id>/...`) and returns 404 to non-members. Tasks are addressed by number (`/tasks/42/`); the key (`APL-42`) is display only, so renaming the project key breaks nothing. New projects are seeded with statuses (To do, In progress, In review, Done, Cancelled) and priorities (Low, Medium, High, Urgent).

| Method and path | Purpose |
|---|---|
| `GET/POST /projects/<id>/tasks/` | List (filters: `status`, `priority`, `assignee`, `tag`, `q`, `due_date_after/before`, `overdue`, `top_level`; `ordering`; `limit`/`offset`) and create |
| `GET/PATCH/DELETE /projects/<id>/tasks/<n>/`, `POST .../restore/` | Detail, field-level update, soft delete and restore (7 days) |
| `GET/POST /projects/<id>/tasks/<n>/subtasks/` | One level only |
| `GET/POST /projects/<id>/tasks/<n>/comments/`, `PATCH/DELETE .../<id>/` | Flat comments; edit or delete your own, the owner moderates |
| `GET/POST /projects/<id>/notes/`, `GET/PATCH/DELETE .../<id>/`, `GET .../<id>/revisions/` | Markdown notes; `PATCH` must send the `version` it edited (stale gives 409) |
| `GET /projects/<id>/tasks/<n>/notes/`, `PUT/DELETE .../<n>/notes/<note>/` | Link and unlink notes |
| `GET/POST /projects/<id>/statuses/`, `/priorities/` and `PATCH/DELETE .../<id>/` | Per-project lists; deleting an item in use needs `move_to` |
| `GET/PUT /projects/<id>/kanban-preference/` | The caller's saved board setup |
| `GET /me/tasks/` | Tasks assigned to the caller across projects |

Mentions use `@[user:<uuid>]` in comments and notes and email current project members once. Overdue is judged on the server's UTC date (`is_overdue`, plus `server_time` in list `meta`). Until feature 5, members can do everyday task, note and comment work and the owner manages statuses, priorities and moderation (`projects/constants/permissions.py`). Notable codes: `open_subtasks`, `subtask_of_subtask`, `assignee_not_member`, `stale_data` (409), `in_use_needs_replacement`, `last_in_category`, `fields_forbidden`.

### Attachments (feature 4)

Files go **straight from the browser to R2** through signed URLs and never pass through Django. Flow: `POST /projects/<id>/attachments/upload-url/` (target, filename, content type, exact size) returns a signed `PUT` URL; the browser uploads exactly those bytes with that `Content-Type`; then `POST .../attachments/<id>/confirm/` checks the size, sniffs the real type from the bytes (never the extension) and marks the file ready. JPEG, PNG and WebP are re-encoded by a Celery task (strips EXIF/GPS) and show as `processing` until then.

| Method and path | Purpose |
|---|---|
| `POST /projects/<id>/attachments/upload-url/`, `.../<id>/confirm/` | Request a signed upload, then confirm it |
| `GET /projects/<id>/attachments/?task=<n>\|note=<id>\|comment=<id>` | Files on a task, note or comment |
| `GET .../attachments/<id>/download/` | Signed link valid 5 minutes (images inline, everything else forced download) |
| `DELETE .../attachments/<id>/` | Uploader or owner; frees quota and removes the file |
| `GET /projects/<id>/storage/`, `GET /me/storage/` | Project usage (by category and uploader) and your personal usage |

Allowed: JPEG, PNG, WebP, GIF (5 MB); PDF, DOCX, XLSX, PPTX, plain text (10 MB); MP3, M4A (20 MB). SVG, HTML, executables, legacy Office files and video are refused. Quotas: **100 MB per user** across all projects and 1 GB per project (`USER_STORAGE_QUOTA_BYTES`, `PROJECT_STORAGE_QUOTA_BYTES`; the per-row `quota_bytes` can be edited in the admin). Max 20 files per task, note or comment; uploads are rate limited to 30/hour per user. Images in notes must be written `![alt](attachment:<id>)`; external and raw HTML images are rejected.

Attachments need R2 (`PROJECT_MANAGEMENT_R2_*`); on local-disk storage `upload-url` answers 503 `attachments_not_configured`. They share the avatar bucket, so **set up the bucket before using them**:
- Avatars must be the only public path. Serve them from a custom domain with a rule that allows only `/avatars/*` and keep the unrestricted `r2.dev` URL disabled; otherwise anyone who learns an attachment key could read it. Attachment links are always signed through the authenticated S3 endpoint.
- Add a CORS rule to the bucket allowing `PUT` and `GET` from your frontend origin (headers `Content-Type`, `Content-Length`).
- The API token needs Object Read & Write on the bucket.

Notable codes: `file_type_not_allowed`, `file_too_large`, `user_quota_exceeded`, `project_quota_exceeded`, `attachment_target_full`, `upload_missing`, `upload_size_mismatch`, `attachment_not_ready`, `invalid_note_image`.

### Permissions (feature 5)

Every write is checked against per-member **permission codes** (for example `task.priority.change`, `member.remove`). Reading is open to all members. The owner holds every code implicitly; owner-only actions (delete project, transfer ownership, regenerate join code, archive, manage the owner) are never delegable. A write that touches a field the caller may not change fails as a whole with 403 `fields_forbidden` listing every field. Grants are read from the database on every request, so a revoke applies on the next call.

| Method and path | Purpose |
|---|---|
| `GET /permissions/` | The registry: codes with label, description and group, the presets, and the owner-only actions |
| `GET/PUT /projects/<id>/members/<user>/permissions/` | Read or replace a member's grants (`{"permissions": [...]}` or `{"preset": "contributor"}`) |
| `POST /projects/<id>/join-requests/<id>/approve/` | Optional starting grants (same body); default none |

Presets (defined in code): `viewer` (nothing), `contributor` (create and edit tasks, notes, comments, uploads), `manager` (everything delegable except `permissions.manage`). **Delegation:** changing grants needs `permissions.manage`, and every code added or removed must be one the actor holds (403 `cannot_grant_permission`). Anyone can edit and delete their own comments and attachments and leave a project without a grant; deleting tasks and notes needs `task.delete` / `note.delete`. The project detail's `permissions` field lists the caller's held codes. Notable codes: `cannot_grant_permission`, `cannot_manage_owner`, `unknown_permission`, `unknown_preset`.

### Security (feature 6)

- **Security log:** `GET /me/security-events/` returns the caller's own account events, newest first (`?event_type=` filter, paginated): `login_success`, `login_failure` (known accounts only), `login_locked`, `password_changed`, `password_reset`, `session_revoked`, `social_account_linked`, `account_deletion_requested`, `account_deletion_cancelled`. Rows hold ip, user agent, device name and small metadata, never passwords, tokens or the attempted email. Kept 180 days (`SECURITY_EVENT_RETENTION_DAYS`). It is separate from the project activity log.
- **Alert emails:** sign-in from a device this account has not used before (never on the first sign-in), the first lockout of a window, and password changes.
- **Login protection:** 5 wrong passwords for one email within 15 minutes lock that email for the rest of the window (429 `login_locked` with `Retry-After`, even for the right password; unknown emails behave the same so existence is not revealed). A correct sign-in resets the count. This is on top of the per-IP `login` limit.
- **Rate limits** (DRF throttling on Redis): anonymous 60/min per IP, signed in 600/min per user, login 5/min, signup 5/hour, verification resend 5/hour, password reset 3/hour, Google 20/min, uploads 30/hour, plus 1200/min per project (all its members together). Set `PROJECT_MANAGEMENT_RELAX_THROTTLES=true` **in local development only** to use high limits for Postman; keep it `false` in staging and production. Behind a proxy set `PROJECT_MANAGEMENT_NUM_PROXIES` (1 with only Cloudflare in front).
- **Request ID:** every response carries `X-Request-ID` (an incoming one is kept if it looks like an id, otherwise a new one is made). The same id is on every log line, in Sentry events and in Celery tasks started by the request, so one id follows a request end to end. Production logs (`DEBUG=false`) are JSON lines including the redacted request data.
- **Health check:** `GET /api/health/` answers 200 only if the database and the cache respond, otherwise 503. Point your uptime monitor at it.
- **Sentry:** error monitoring only (no tracing, profiling or logs). No cookies, headers or IPs are sent; events carry the user id and request id, and secrets are redacted before sending.

**Tools outside the app (free).** The app does not duplicate what these do better; set them up when the API is deployed on a domain:
1. **Cloudflare** (proxied DNS record for the API host): SSL/TLS Full (strict), Always Use HTTPS, HSTS (start at 6 months, no preload), one rate-limit rule for `/api/auth/`, Bot Fight Mode, and a response-header Transform Rule on `/api/` adding `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and `Cache-Control: no-store`. Only let Cloudflare reach the server (Cloudflare Tunnel is the simplest way); otherwise anyone can bypass the limits by sending a fake `X-Forwarded-For`.
2. **Logs:** ship stdout to Better Stack or Grafana Cloud (free tier) and search by `request_id`. How depends on the host.
3. **Uptime:** UptimeRobot or Better Stack checking `/api/health/` every 5 minutes.

`manage.py check --deploy` with production settings reports only the HSTS preload note, which is intentional.

### Slack (feature 8)

The Slack provider plugs into the integration framework. One Slack app (yours, created from `docs/slack/app-manifest.yml`) serves every project; each project connects its own workspace.

**One-time setup**
0. Local tunnel: sign up for ngrok (free), claim your static domain, and run `ngrok http --url=<your-domain> 8000` (that domain is your public API address).
1. Create the Slack app: api.slack.com/apps, Create New App, From a manifest, pick a workspace you administer, and paste `docs/slack/app-manifest.yml` with `YOUR_API_URL` replaced by your public HTTPS address. **The server and the tunnel must be running first**, because Slack checks the Events URL when it is saved. (To change an existing app, edit its manifest in the app settings.)
2. Copy the Client ID, Client Secret and Signing Secret (Basic Information > App Credentials) into `.env` as `PROJECT_MANAGEMENT_SLACK_*`. Never commit them.
3. Generate an encryption key and set `PROJECT_MANAGEMENT_INTEGRATION_ENCRYPTION_KEYS`:
   `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
4. Set `PROJECT_MANAGEMENT_PUBLIC_API_URL` to the public address and add its host to `PROJECT_MANAGEMENT_ALLOWED_HOSTS`. Restart the server and the worker (`-Q default,integrations`).

**Connecting a project** (needs `integration.slack.manage`)
- `GET /projects/<id>/integrations/slack/install/` returns the "Add to Slack" `url`; open it in the browser. Slack returns to `/api/integrations/slack/install/callback/`, the token is stored encrypted, and the browser is sent to `FRONTEND_URL/projects/<id>/integrations?slack=connected` (or `slack=error&reason=...`).
- In Slack, invite the bot to each channel it should post in (`/invite @Project Management`); it cannot post anywhere else.
- `GET .../slack/channels/` lists channels; `POST .../slack/mappings/` maps one (`channel_id`, `enabled_events`), `PATCH`/`DELETE .../slack/mappings/<id>/` change or remove it. Public channels return `warn_public: true`. A project may map several channels, each with its own event toggles.
- Messages contain only the task key, title, status, assignee first names, due date and a link; never descriptions, comment text or emails. Changes that came from Slack are not posted back.

**People**
- `GET /me/integrations/slack/link/` returns the "Sign in with Slack" `url` (and the workspaces you are linked in); `DELETE` unlinks. Nobody is matched by email.
- Linked people get Slack DMs for: a task assigned to them, a task of theirs due soon or overdue, a comment on their task (not their own), and join requests (owner and members who can approve). `GET`/`PUT /me/notification-preferences/` set `slack_dm` per event (default on). The `email` flag turns on email notifications for the same events (see below).
- Slash commands (private replies): `/task create <project key> <title>` and `/task done <KEY-42>`. They run as the linked person with their own permissions; an unlinked person gets a link prompt.

If direct messages fail with a Slack scope error, add the `im:write` bot scope to the manifest. If a project's key is used by two of your projects in the same workspace, the command asks you to rename one.

### Activity, explore, email notifications and email change

- **Activity feed:** `GET /projects/<id>/activity/` (newest first; filters `actor`, `action`, `entity_type`, `created_after`, `created_before`). Holders of `activity.view` (the owner always) see everything; every other member sees only their own actions. IP addresses are never returned and long values are cut to 200 characters. Entries older than a year are purged daily.
- **Explore:** owners can list a project (`is_listed`). `GET /explore/` (filters `q`, repeatable `tag`, `starts_after`, `ends_before`; newest listing first) shows listed projects you are not in: name, description, tags, dates, owner first name, member count and `my_request` (`none`, `pending`, `cooldown`). `GET /explore/tags/?q=` suggests the most used tags. `POST /explore/<project_id>/join-request/` asks to join without a code, with the same limits as code joins (10 open requests, 24 h after a rejection, owner approval). Demo projects need no approval: the reply is `status: joined` and the caller becomes a viewer.
- **Email notifications:** people can opt in per event (`PUT /me/notification-preferences/`, `email: true`; default off) to be emailed about: task assigned to them, due soon, overdue, a comment on their task, and join requests (owner and approvers). Email contains only key, title, status, names, due date and a link. Slack DMs and emails use the same audience rules (`integrations/services/audience.py`).
- **Change email:** `POST /me/email/` (`new_email` plus `password`, or `id_token` for Google accounts) sends a link to the new address and warns the old one. `POST /auth/email-change/confirm/` (`token`, no login needed) completes it: the new address becomes the only login, every session is signed out, the old address is told, and a security event is recorded. A taken address gets the same neutral answer as an available one.

### API schema (OpenAPI)

The schema is generated from the code (`drf-spectacular`): exact request bodies and query parameters, session-cookie auth and the CSRF header, and the shared response envelope (response `data` is a free object). It is exported to `docs/openapi.yml`; regenerate it after changing an endpoint and a test fails if it is stale:

```bash
uv run python manage.py spectacular --file docs/openapi.yml --validate --fail-on-warn
```

With `DEBUG=true`, Swagger UI is at `/api/docs/` and the raw schema at `/api/schema/`. Request serializers are found from the `X.parse(request.data)` calls in each view method; for anything unusual set `request_serializers` / `query_serializers` on the view.

Notable account codes: `invalid_credentials` (401), `email_not_verified` (403), `profile_incomplete` (403), `account_pending_deletion` (403), `csrf_failed` (403), `throttled` (429, with `Retry-After`).

Rate limits (DRF throttling on the Redis cache): anonymous 60/min, signed in 600/min, login 5/min, signup 5/h, resend 5/h, password reset 3/h, uploads 30/h.

## Structure

```
config/         Django project, settings, Celery app, root URLs
common/         shared infrastructure, one package per concern:
                response, exception (+ DRF handler), pagination, filter, order,
                cache, logger, validators, models (mixins), serializers (strict),
                throttling, storage (FileStorage ABC: R2, local, in-memory)
accounts/       feature 1
  models/       User (email login, soft delete), UserSession
  services/     all business logic (signup, auth, verification, password, google,
                avatar, profile, session, deletion, email)
  serializers/  request validation
  views/        thin DRF views
  tasks.py      Celery tasks (send_email, avatar import, purge, session cleanup)
tracker/        feature 3: Status, Priority, Task (+assignees, tags), Note (+revisions),
                Comment, KanbanPreference; services/ (workflow, task, note, comment,
                mention, query, seeding, reassignment); tasks.py (purge deleted tasks)
attachments/    feature 4: Attachment, ProjectStorageUsage, UserStorageUsage; services/
                (attachment, quota, type sniffing, image re-encoding, note-image
                validation); signals.py (frees quota and the R2 object on delete)
projects/       feature 2: Project, Tag, Membership, JoinRequest, OwnershipTransfer,
                ActivityLog; services/ (project, membership, join, transfer, reauth,
                reassignment registry, activity), permissions.py (owner-only hook),
                tasks.py (purge projects, expire join requests and transfers)
```

Conventions: UUIDv7 primary keys, business logic in `services/`, responses via `common/response`, errors via `AppException` subclasses, absolute imports from the project root. Message, error-code, cache-key and email-text literals live in the feature's `constants/` package (shared ones in `common/<concern>/constants.py`); validation reuses `common/validators` and `common/serializers/fields.py`.

## Postman

Import `postman/project-management.postman_collection.json` and `postman/project-management.postman_environment.json`, select the environment, call **Get CSRF cookie**, then **Login**. Keep both files updated whenever the API contract changes.

### Demo projects

`python manage.py seed_demo_projects` creates the system user (`is_system`, `demo@system.invalid`, never logs in) and three shared, read-only demo projects (`demo_key` set, listed on explore, no dates). Safe to re-run; `--refresh` rebuilds their tasks and notes, `--join-existing` joins every existing account. New accounts are joined as viewers once, when the email is verified or the Google account is created, and may leave and rejoin from explore without approval. Demo projects cannot be edited, archived, deleted, transferred or joined by code (`demo_project_locked`), their member list shows only the owner and the caller, and `POST /projects/<id>/copy/` clones one into a project the caller owns.

### Emails

Emails are sent as multipart: the plain text you write in the app's `constants/emails.py` stays as the fallback, and `common/email/render.py` adds an HTML version (`common/templates/email/base.html`) with the Pro-Goal mark, the subject as a heading, the first link in the body as a button (plus the link in a box for clients that block buttons) and a footer saying Pro-Goal is a learning project. The mark is `common/email/static/logo.png`, sent inline. To change the look edit the template; to name a button pass `action_label` to `queue_email`, or add the link's path to `_ACTION_LABELS`.
