# PROJECT.md: Backend Design Document

2026-10-08

## Overview

This is a Django REST API for a project management tool where each **project is its own tenant**: people join projects, and per-field permissions control what each member may change. Slack is the only integration. Everything here comes from the Q&A with Aadarsha on 2026-10-08; anything undecided is listed under Open questions rather than guessed.

**How to read it.** Each feature section gives purpose, models, endpoints, rules, permission codes, Celery jobs and decisions. Endpoint paths are proposals. A decision marked _(assumed)_ was a default the owner did not object to; unmarked ones were confirmed.

### Stack

- Django REST Framework, Celery, Redis, Postgres. Postgres and Redis run in Docker Compose and Django connects to them (Celery will be added to Compose later).
- Python managed with `uv`. UUIDv7 primary keys on every model (time-ordered, still unguessable).
- Cloudflare R2 (S3 compatible, used through `boto3`) for files. Sentry plus JSON logs with a request ID.
- Backend only for now. CI comes after a working local build. A hosting and DevOps guide is a separate deliverable near the end.

### Tenancy

- There is **no workspace**. A project is the tenant boundary, joined through a `Membership(user, project)` row.
- Every project-scoped query is filtered to projects the caller belongs to. A non-member gets **404**, never 403, so project IDs cannot be probed.
- A user can create and join any number of projects. Each project has exactly one owner.

### Conventions used everywhere

- Timestamps are stored and returned in UTC. Due dates and project dates are plain dates with no time zone.
- Errors carry a stable machine-readable `code` field, so the frontend never parses message text.
- Lists use page size 25 (maximum 100). Request bodies with unknown fields are rejected.
- Reading is open to every member; permissions only unlock writes.
- Soft delete is used for accounts, projects and tasks, with Celery beat jobs doing the final purge.

### Decisions that changed during the Q&A

| Topic                | Final decision                            | What it replaced                                                                                             |
| -------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Tenancy              | Project is the tenant                     | Workspaces with slugs, then schema-per-tenant (`django-tenants`, already removed from the code, uncommitted) |
| Joining              | 6-character join code plus owner approval | Email invites                                                                                                |
| Social login         | Google only                               | Google and GitHub                                                                                            |
| Integrations         | Slack only                                | GitHub and Slack                                                                                             |
| Project grouping     | Free-form tags                            | A single category                                                                                            |
| Permission scope     | Project-wide grants only                  | `own` / `any` scopes and per-task grants                                                                     |
| Due dates            | Date only, no time zones                  | Date plus time with user time zones                                                                          |
| Rate limiting        | DRF built-in throttling on Redis          | A custom Redis limiter                                                                                       |
| Virus scanning       | None in v1 (ClamAV dropped)               | ClamAV required in v1                                                                                        |
| Kanban ordering      | Sort by a field, no manual drag order     | Manual ordering                                                                                              |
| Project cap per user | No cap                                    | 20 owned projects                                                                                            |

### Feature map

1. Accounts and sessions
2. Projects, membership, join requests, ownership transfer
3. Tasks, subtasks, notes, comments, statuses, priorities, views
4. Attachments and quotas
5. Field-level permissions
6. Security hardening
7. Integration framework
8. Slack
9. Cross-feature pieces (activity log, permission registry, outbox, reassignment registry)
10. Demo projects, copy to workspace, onboarding tour

## 1. Accounts and sessions

### Purpose

Let people sign up with email and password or with Google, verify their email, and stay logged in through server-side sessions they can see and revoke. Built on `django-allauth` for the standard flows, plus custom code for sessions, profile and account deletion.

### Models

| Model               | Key fields                                                                                                                                                             | Notes                                                                                                    |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `User`              | `id` (UUIDv7), `email` (unique, login), `first_name`, `last_name`, `display_name` (all required), `avatar` (R2 key, nullable), `is_active`, `deleted_at`, `created_at` | No username. Social-only users have no usable password.                                                  |
| `EmailAddress`      | allauth's table: `email`, `verified`, `primary`                                                                                                                        | Unverified users cannot log in.                                                                          |
| `SocialAccount`     | allauth's table: `provider` (only `google`), `uid`, `extra_data`                                                                                                       | Linked only when Google reports the email as verified.                                                   |
| `UserSession`       | `id`, `user`, `session_key`, `device_name`, `ip`, `user_agent`, `created_at`, `last_seen_at`, `remember_me`                                                            | Custom model that backs "list my sessions". Django's session store is `cached_db`.                       |
| `EmailVerification` | token, `expires_at`, `used_at`                                                                                                                                         | Single use, 24 hours. Existing code keeps this next to credential and signup services under `accounts/`. |

### Endpoints (proposed)

| Method and path                                                          | Purpose                                                                                 |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `GET /api/csrf/`                                                         | Sets the CSRF cookie                                                                    |
| `POST /api/auth/signup/`                                                 | Email signup. Same neutral reply whether or not the email exists                        |
| `POST /api/auth/verify-email/` and `POST /api/auth/verify-email/resend/` | Confirm, and resend (cooldown applies)                                                  |
| `POST /api/auth/login/`                                                  | Email and password, optional `remember_me`                                              |
| `POST /api/auth/google/`                                                 | Google sign in or sign up                                                               |
| `POST /api/auth/logout/`                                                 | Destroys the current session. Optional `all_other_sessions: true` also revokes the rest |
| `POST /api/auth/password/reset/` and `.../confirm/`                      | Emailed token, 1 hour                                                                   |
| `POST /api/auth/password/change/`                                        | See Open questions: flow not fully specified                                            |
| `GET /api/me/`, `PATCH /api/me/`                                         | Profile: first, last, display name, avatar                                              |
| `GET /api/me/sessions/`, `DELETE /api/me/sessions/<id>/`                 | List and revoke sessions                                                                |
| `POST /api/me/delete/`, `POST /api/me/delete/cancel/`                    | Start and cancel account deletion                                                       |

### Rules and edge cases

- **Signup:** email, password, first, last and display name. Email verification is mandatory before first login.
- **Neutral responses:** signup and reset always answer "if this email can be used, we sent a message". A registered email gets an "you already have an account" email instead. Login failure is always 401 "Invalid email or password".
- **Verification link:** 24 hours, single use. If it expired, the user asks for a new one. Resend has a 60-second cooldown and 5 per hour _(assumed)_, set through allauth.
- **Password rules:** Django validators (minimum 10 characters, not common, not similar to the email). Hashing is Argon2.
- **Password reset:** emailed token valid 1 hour. On success all of the user's sessions are logged out _(assumed)_.
- **Google:** a social email that matches an existing account links to it only if Google marks it verified. Google signups skip our email verification. Social-only users never need a password. Google's profile photo is imported as the avatar.
- **Implementation notes (built 2026-10-08):** allauth supplies only `EmailAddress` and `SocialAccount`; all flows are our own services. The error body field is `code`. Verification tokens are signed (24 h, single use because a verified address rejects the link); reset tokens use Django's token generator (1 h). A correct password on an unverified account answers 403 `email_not_verified` (wrong credentials stay a generic 401). Avatar upload is `POST/DELETE /api/me/avatar/` (multipart), stored as WebP at most 512 px. Password minimum is 10 characters, with at least one upper and one lower case letter, and no similarity to the user's details.
- **Complete profile step:** if the provider does not return first and last name, the account is not usable until the user fills them in.
- **Sessions:** Django `cached_db` (Redis first, database on a miss). Lifetime is 2 weeks, sliding. "Remember me" extends it to 30 days, sliding. A user can have many sessions at once.
- **Logout:** by default only the current session is destroyed. The user can choose to log out all other devices too.
- **CSRF:** DRF `SessionAuthentication` with CSRF enforced. The frontend is same-site (for example `app.example.com` and `api.example.com`).
- **Avatar:** JPEG, PNG or WebP, 2 MB maximum, checked and resized on the server, stored in R2.
- **Account deletion:** soft delete with a 7-day grace period. Per the Q&A, a login during the window cancels it and the final purge keeps tasks and comments, shown as "Deleted user" _(assumed)_. A user who owns a project cannot be deleted until they transfer or delete it _(assumed)_.
- **Email delivery:** console backend locally; a transactional provider (Resend, Brevo or Amazon SES) in production. Needs a domain with DNS records; covered in the hosting guide.

### Permission codes

None. A user always controls their own account.

### Celery jobs

- `send_email` for verification, reset and alerts (default queue, so integration outages never delay it).
- Beat: purge accounts 7 days after deletion; clear expired sessions.

### Decisions

Email plus password, no username. Mandatory email verification. `django-allauth`. Google only. `cached_db` sessions with a custom session model. 2 weeks sliding, 30 days with remember me. Per-session management. Soft delete with 7 days. Argon2. Neutral responses with stable error codes.

## 2. Projects, membership, join requests, ownership transfer

### Purpose

A project is the tenant. This feature covers creating and archiving projects, who belongs to them, how people join (code plus owner approval), how ownership moves, and how a member is removed without orphaning their work.

### Models

| Model                  | Key fields                                                                                                                                                                                | Notes                                                                         |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `Project`              | `id`, `name`, `description`, `task_key` (e.g. `PMS`), `start_date`, `end_date`, `join_code`, `is_listed` (explore page), `archived_at`, `deleted_at`, `created_at`, `updated_at`, `owner` | `end_date` on or after `start_date`; both optional. Names need not be unique. |
| `Tag` and `ProjectTag` | `name` (normalized), `usage_count`                                                                                                                                                        | Free-form, lowercase and trimmed. Replaces a single category.                 |
| `Membership`           | `user`, `project`, `joined_at`, `is_owner`                                                                                                                                                | One row per user and project.                                                 |
| `JoinRequest`          | `user`, `project`, `status` (pending, approved, rejected, expired), `created_at`, `decided_by`, `decided_at`, `expires_at`                                                                | Pending expires after 14 days.                                                |
| `OwnershipTransfer`    | `project`, `from_user`, `to_user`, `status`, `expires_at`                                                                                                                                 | One pending per project. Expires after 7 days.                                |

### Endpoints (proposed)

| Method and path                                                                                 | Purpose                                                                                |
| ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `POST /api/projects/`, `GET /api/projects/`                                                     | Create (caller becomes owner); list the caller's projects                              |
| `GET/PATCH /api/projects/<id>/`                                                                 | Detail includes the caller's own permission list; each field edit is checked per field |
| `POST /api/projects/<id>/archive/` and `.../unarchive/`                                         | Archive and restore                                                                    |
| `DELETE /api/projects/<id>/` and `POST .../restore/`                                            | Soft delete; restore inside 7 days                                                     |
| `GET /api/projects/<id>/members/`, `DELETE .../members/<user>/`                                 | Member list; remove with a reassignment map                                            |
| `POST /api/projects/join/`                                                                      | Submit a join code                                                                     |
| `GET /api/projects/<id>/join-requests/`, `POST .../<req>/approve/` and `/reject/`               | Owner or delegate decides                                                              |
| `POST /api/projects/<id>/join-code/regenerate/`                                                 | Owner only                                                                             |
| `POST /api/projects/<id>/transfer/`, `.../transfer/cancel/`, `POST /api/transfers/<id>/accept/` | Ownership transfer                                                                     |
| `GET /api/explore/`                                                                             | Listed projects, filterable by tags and dates (built later)                            |

### Rules and edge cases

- **Roles:** exactly one owner per project, who implicitly holds every permission and cannot be removed. Everyone else is a member whose writes depend on granted permissions.
- **Join code:** 6 characters, uppercase letters and digits, generated randomly and unique across all projects (database unique constraint with retry). About 2.2 billion combinations. Regenerating affects only new requests; pending requests survive.
- **Brute-force defence:** 5 wrong codes per hour per user and per IP, a cap of 10 open requests per user _(assumed)_, and owner approval.
- **Before approval** the requester sees only the project name and description. The owner sees the requester's name and email.
- **Join request flow:** pending, then approved or rejected. A rejected person may ask again after 24 hours. No permanent blocking. Owner is notified by email through Celery, and there is an in-app list endpoint.
- **On approval** the approver chooses starting permissions; the default is none. A new member can still read everything in the project.
- **Explore page (built 2026-10-09):** an owner can mark a project _listed_. People can then request to join without the code; approval is still required. Explore shows name, description, tags, dates, owner first name and member count, never tasks.
- **Ownership transfer:** only to an existing member, who must accept. Pending for 7 days, cancellable, one at a time. After acceptance the old owner becomes a member with no permissions until the new owner grants some. Requires password re-entry (or fresh Google login).
- **Member visibility:** members see first name and picture. Emails are visible to the owner only.
- **Removing a member:** needs `member.remove`. The remover submits a map such as `{tasks: U1, notes: U2}` and everything the removed user owned moves in one transaction (see the reassignment registry in section 9). Models left out of the map become unassigned. Comments and created-by history stay with the person's name. The removed person may request to join again; old permissions are not restored. Members can leave on their own; the owner cannot leave without transferring.
- **Archive:** read-only and restorable, owner only _(assumed)_.
- **Delete:** owner only, soft delete with a 7-day undo window. Hidden from members; the owner sees "scheduled for deletion" with a restore button. Re-entering the password is required.
- **Join code regeneration** also requires password re-entry.
- **Task key:** 2 to 5 letters, editable by the owner _(assumed)_. See Open questions on what editing it does to old references.

### Permission codes

_Built 2026-10-09:_ until feature 5, only the owner holds these; `projects/permissions.py` is the one place to change.

`project.name.change`, `project.description.change`, `project.tags.change`, `project.start_date.change`, `project.end_date.change`, `project.task_key.change` _(assumed)_, `member.approve`, `member.remove`, `permissions.manage` (section 5). Owner only: delete, transfer, regenerate code, archive _(assumed)_.

### Implementation notes (built 2026-10-09)

- App `projects/`. Owner-only permissions with a single hook; "starting permissions" on approval is accepted later, with feature 5.
- Re-authentication for transfer, delete and code regeneration: `password`, or `id_token` (fresh Google sign-in linked to the account) for social-only users. Failure is 403 `reauth_failed`.
- Reassignment registry and a small append-only `ActivityLog` exist; the registry has no handlers until feature 3. No outbox yet; emails go through the Celery `send_email` task.
- Archived projects are read-only for everyone (409 `project_archived`) except unarchive, delete and leave. Joins to an archived project are refused.
- Extra endpoints beyond the table: `POST /projects/<id>/leave/` and `GET /transfers/` (the recipient's pending offers). The explore page is built (see Backend wrap-up below).
- Join limits: 5 wrong codes per hour per user and per IP (cache counters), at most 10 open requests per user.
- Only the owner sees `join_code` and emails.

### Celery jobs

- Beat: purge projects 7 days after deletion; expire join requests after 14 days; expire ownership transfers after 7 days.
- On demand: join-request and transfer emails; member-removal reassignment (runs inside the request transaction, with notifications afterwards).

### Decisions

Project is the tenant. Single owner, transferable with acceptance. Join by 6-character code with owner approval, retry after 24 hours. No cap on projects per user. Free-form tags. Soft delete with 7 days. Removal with per-model reassignment. Everything logged to the activity log.

## 3. Tasks, subtasks, notes, comments, statuses, priorities, views

### Purpose

The core work-tracking feature. Tasks live in a project, can have one level of subtasks, several assignees, a status and priority taken from per-project lists, linked notes, comments and (see section 4) attachments. Each user also stores a kanban preference.

### Models

| Model              | Key fields                                                                                                                                                                              | Notes                                                              |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `Task`             | `id`, `project`, `number` (per project), `title`, `description` (markdown), `status`, `priority`, `start_date`, `due_date`, `parent` (nullable), `created_by`, `deleted_at`, timestamps | Key shown as `PMS-42` = project `task_key` + `number`. Dates only. |
| `TaskAssignee`     | `task`, `user`                                                                                                                                                                          | Many assignees; each must be a project member.                     |
| `TaskTag`          | `task`, `tag`                                                                                                                                                                           | Free-form tags, same normalization as projects.                    |
| `Status`           | `project`, `name`, `category` (To do, In progress, Done), `position`, `is_default`                                                                                                      | Per project, seeded on creation.                                   |
| `Priority`         | `project`, `name`, `rank`, `position`                                                                                                                                                   | Per project, seeded on creation.                                   |
| `Note`             | `id`, `project`, `title`, `body` (raw markdown, max about 100 KB), `author`, `version`, tags, timestamps                                                                                | Separate entity; may exist with no task.                           |
| `NoteRevision`     | `note`, `version`, `body`, `edited_by`, `created_at`                                                                                                                                    | One row per save.                                                  |
| `TaskNote`         | `task`, `note`                                                                                                                                                                          | Many to many.                                                      |
| `Comment`          | `id`, `task`, `author`, `body`, `edited_at`, `deleted_at`, `deleted_by`                                                                                                                 | Flat, no threads.                                                  |
| `KanbanPreference` | `user`, `project`, `group_by`, `sort_by`                                                                                                                                                | The only stored view setting.                                      |

### Endpoints (proposed)

| Method and path                                                          | Purpose                                                                                         |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `GET/POST /api/projects/<id>/tasks/`                                     | List with filters (status, priority, assignee, due date, tag), title search, pagination; create |
| `GET/PATCH/DELETE /api/projects/<id>/tasks/<key>/`                       | Detail, field-level update, soft delete; `POST .../restore/`                                    |
| `GET/POST /api/projects/<id>/tasks/<key>/subtasks/`                      | One level only                                                                                  |
| `GET/POST /api/projects/<id>/notes/`, `GET/PATCH/DELETE .../notes/<id>/` | PATCH must send the `version` it edited; a stale version returns 409                            |
| `GET .../notes/<id>/revisions/`                                          | Revision history                                                                                |
| `PUT/DELETE /api/projects/<id>/tasks/<key>/notes/<note>/`                | Link or unlink a note                                                                           |
| `GET/POST .../tasks/<key>/comments/`, `PATCH/DELETE .../comments/<id>/`  | Comments                                                                                        |
| `GET/POST/PATCH/DELETE /api/projects/<id>/statuses/` and `/priorities/`  | Manage the per-project lists                                                                    |
| `GET/PUT /api/projects/<id>/kanban-preference/`                          | The caller's saved board setup                                                                  |
| `GET /api/me/tasks/`                                                     | Tasks assigned to the caller across projects                                                    |

### Rules and edge cases

- **Overdue** is judged on the server's UTC date, never by the browser. Responses carry the server time so the UI can show countdowns.
- **Dates:** `start_date` optional; `due_date` must not be before it. No time of day, no time zone.
- **Subtasks:** one level only. A parent cannot move to a Done-category status while any subtask is open. Deleting a parent soft-deletes its subtasks.
- **Assignees:** several allowed. Grouping a board by assignee shows the card in every assignee's column plus an Unassigned column.
- **Statuses and priorities** are per project and editable. Each status has a category (To do, In progress, Done) so automations survive renames. Each category must always keep at least one status. Deleting a status or priority in use asks which one to move its tasks to (same reassignment pattern as member removal).
- **Whole-request permission check:** a PATCH that touches a field the caller cannot change is rejected with 403 listing every forbidden field (section 5).
- **Task deletion:** soft delete; anyone holding the delete permission can restore _(assumed)_.
- **Notes:** the raw markdown is the only source of truth; rendered HTML is never stored and the frontend sanitizes on render. Images in markdown may only point to this project's own attachments, no external URLs. Each save writes a `NoteRevision` and bumps `version`; optimistic locking prevents lost updates.
- **Comments:** edit and delete your own with no grant. Deleting or editing others' comments is a moderation permission. `@member` mentions in comments and notes notify the member (email now, Slack later).
- **Views:** a list view and a kanban view. Kanban can group only by fields with a finite set of values: status, priority, assignee, tag. Date fields are not allowed. Cards inside a column sort by a chosen field; there is no manual drag order. Moving a card changes the grouped field and needs that field's permission. Filters, search and sort are not stored and reset on refresh.
- **Listing:** filters by status, priority, assignee, due date and tag, plus title search, paginated _(assumed)_.

### Implementation notes (built 2026-10-09)

- App `tracker/`. Interim permissions (until feature 5): members hold the everyday task, note-edit, link and `comment.create` codes and may delete what they created; the owner alone manages statuses and priorities, moderates comments and deletes others' items. The single decision point is `projects/permissions.py`.
- Soft-deleted tasks are purged after 7 days; deleting a parent deletes its subtasks, and restoring it brings back only the subtasks deleted with it. Notes are hard-deleted.
- Deleting a status or priority that tasks use needs `move_to`; the default item and the last status of a category cannot be deleted.
- `PATCH` on a note needs `version`; a stale one is 409 `stale_data`. Every content change writes a `NoteRevision`.
- Overdue = due before today's UTC date and not in a Done-category status. Task lists carry `server_time` and `server_date` in `meta`.
- `GET /me/tasks/` and the project task list share filters and ordering. The task list includes subtasks (use `top_level=true` to hide them).
- Images in notes limited to project attachments waits for feature 4.

### Permission codes

`task.create`, `task.delete` (also covers restore), `task.title.change`, `task.description.change`, `task.status.change`, `task.priority.change`, `task.assignees.change`, `task.start_date.change`, `task.due_date.change`, `task.tags.change`, `task.parent.change`, `note.create`, `note.title.change`, `note.body.change`, `note.tags.change`, `note.delete`, `note.link.change` (link notes to tasks), `comment.create`, `comment.moderate`, `status.create`, `status.update`, `status.delete`, `priority.create`, `priority.update`, `priority.delete`. The exact list is final only once the registry is written (section 5).

### Celery jobs

- Beat: scan for tasks due soon and overdue and emit events (for notifications and Slack); purge soft-deleted tasks after the project-level retention _(open)_.
- On demand: mention notification emails.

### Decisions

Multiple assignees. Date-only deadlines. Subtasks in v1, one level. Notes as a separate markdown entity with revisions and optimistic locking. Custom per-project statuses and priorities. Comment moderation. Kanban preference is the only stored view setting.

## 4. Attachments and quotas

### Purpose

Let members attach files to tasks, comments and notes, store them privately in Cloudflare R2, and cap storage per project with a visible usage tab.

### Models

| Model                 | Key fields                                                                                                                                                                                                     | Notes                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `Attachment`          | `id`, `project`, `uploaded_by`, `target_type` and `target_id` (task, comment or note), `object_key`, `filename`, `content_type` (sniffed), `size_bytes`, `status` (pending, ready), `created_at`, `deleted_at` | The file itself is never stored in Postgres.                                  |
| `ProjectStorageUsage` | `project`, `bytes_used`, `quota_bytes` (default 1 GB)                                                                                                                                                          | Updated on confirm and delete; a nightly job recomputes it from `Attachment`. |

### Endpoints (proposed)

| Method and path                                     | Purpose                                                                                      |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `POST /api/projects/<id>/attachments/upload-url/`   | Checks type, size, quota and rate limit, then returns a short-lived signed R2 upload URL     |
| `POST /api/projects/<id>/attachments/<id>/confirm/` | Called after the browser upload; server verifies the object, sniffs the type, marks it ready |
| `GET /api/projects/<id>/attachments/<id>/download/` | Checks membership, then returns a short-lived signed download URL                            |
| `DELETE /api/projects/<id>/attachments/<id>/`       | Remove and free quota                                                                        |
| `GET /api/projects/<id>/storage/`                   | Usage tab: bytes used, quota, breakdown by type                                              |

### Rules and edge cases

- **Direct upload:** the browser uploads straight to a private R2 bucket with a signed URL, so files never pass through Django. Downloads work the same way and the server issues the link only after a membership check.
- **Allowed types**, decided by the actual file content, not the extension: images (JPEG, PNG, WebP, GIF), PDF, Office documents, plain text, audio (MP3, M4A), video (MP4, WebM). SVG, HTML and executables are refused.
- **Size limits:** images 5 MB, documents 10 MB, audio 20 MB, video 50 MB.
- **Quota:** 1 GB per project. An upload that would exceed it is refused before a URL is issued.
- **Images** are re-encoded server-side to strip location metadata _(assumed)_.
- **Hardening without a virus scanner:** content-type checks, forced download headers, and serving from a separate storage domain.
- **Markdown images** in notes may only reference this project's attachments.
- **Abandoned uploads:** a pending attachment that is never confirmed is deleted by a beat job (age threshold open).
- **Permissions on remove:** the uploader can delete their own attachment; deleting others' needs `attachment.delete` _(assumed)_.

### Implementation notes (built 2026-10-09)

- App `attachments/`. **Quotas changed from the original spec:** 100 MB per user across all projects (the main cap, because R2's free tier is 10 GB in total) plus 1 GB per project. Both counters include pending reservations and are checked atomically before a URL is issued. Video is dropped from v1.
- Same R2 bucket as avatars, keys `projects/<project_id>/attachments/<id>`. Public access must be limited to `avatars/*` (README).
- Type allowlist by sniffed content (`filetype` library): JPEG, PNG, WebP, GIF, PDF, DOCX, XLSX, PPTX, plain text, MP3, M4A. Limits 5/10/20 MB. The declared type must equal the sniffed type.
- The signed `PUT` binds `Content-Type` and `Content-Length`; `confirm` re-checks size and bytes and deletes a refused file.
- Images (JPEG, PNG, WebP) are re-encoded by Celery (EXIF stripped, orientation applied); GIF is left as is. Status: pending, processing (images only), ready.
- Pending uploads are cleaned after 24 h; a nightly job recomputes both counters. Deleting a parent (after its 7-day purge) or a whole project releases files through a `post_delete` signal.
- Notes may only embed `![alt](attachment:<id>)` images of the same project; external, raw HTML and reference-style images are rejected.
- Extra endpoints: `GET .../attachments/` (list a target's files) and `GET /me/storage/`. Max 20 files per target.
- Interim permissions: members upload; the uploader or the owner deletes.

### Permission codes

`attachment.create`, `attachment.delete` _(assumed)_. Reading and downloading is open to members.

### Celery jobs

- Post-upload processing: type sniffing and image re-encoding.
- Beat: clean up pending uploads; recompute usage; purge R2 objects for deleted attachments.

### Decisions

Attachments are in v1 on tasks, comments and notes. R2 with signed URLs. Strict type allowlist and size limits. 1 GB per project with a usage tab. No ClamAV in v1 (see Known limitations).

## 5. Field-level permissions

### Purpose

Decide, per member and per project, exactly which fields and actions they may change. Instead of broad roles, each field of each entity has its own permission code, for example `task.priority.change` or `project.end_date.change`.

### Models

| Model               | Key fields                                                    | Notes                                                                                                                                            |
| ------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `MemberPermission`  | `membership`, `code`, `granted_by`, `granted_at`              | One row per member and permission. Unique on (membership, code).                                                                                 |
| Permission registry | In code, not a table: `code`, `label`, `description`, `group` | Single source of truth. Served by an endpoint so the frontend keeps no map of its own.                                                           |
| `PermissionPreset`  | `name`, list of codes                                         | Deferred. Proposed starters: Viewer (nothing), Contributor (create tasks and comments, change status and notes), Manager (everything delegable). |

### Endpoints (proposed)

| Method and path                                      | Purpose                                                  |
| ---------------------------------------------------- | -------------------------------------------------------- |
| `GET /api/permissions/`                              | The registry with descriptions, generated by the backend |
| `GET /api/projects/<id>/members/<user>/permissions/` | A member's grants                                        |
| `PUT /api/projects/<id>/members/<user>/permissions/` | Replace the set of grants                                |
| `GET /api/projects/<id>/`                            | Includes `my_permissions` so the UI knows what to show   |

### Rules and edge cases

- **Project-wide only.** A grant applies to every object in the project. There are no per-task grants and no `own` / `any` scopes in v1.
- **Flat.** One permission never implies another; the editor groups related ones visually.
- **Reading is open** to all members, so there are no view-level permissions.
- **Whole request fails together.** A write that touches a field the caller cannot change is rejected with 403 and a body listing every forbidden field. Nothing is partially applied.
- **Checked on every request** from the database, cached for the duration of that request, so a revoke takes effect on the next call. A Redis cache can be added if this proves slow.
- **Delegation:** the owner always has everything. Anyone granted `permissions.manage` can grant or revoke only permissions they hold themselves, and can never touch the owner.
- **Never delegable (owner only):** delete project, transfer ownership, regenerate the join code, manage the owner.
- **No grant needed:** editing or deleting your own comments, and leaving a project.
- **Operator access:** Django admin can see everything. The API never offers a bypass.
- **Automations** (for example a Slack command) run as the linking user and are checked with that user's permissions.

### Permission codes (current draft)

| Group                   | Codes                                                                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Project                 | `project.name.change`, `project.description.change`, `project.tags.change`, `project.start_date.change`, `project.end_date.change` |
| Members                 | `member.approve`, `member.remove`, `permissions.manage`                                                                            |
| Tasks                   | See section 3                                                                                                                      |
| Notes and comments      | See section 3                                                                                                                      |
| Statuses and priorities | See section 3                                                                                                                      |
| Attachments             | `attachment.create`, `attachment.delete`                                                                                           |
| Activity                | `activity.view` _(name assumed)_                                                                                                   |
| Integrations            | `integration.slack.manage`, `integration.logs.view`                                                                                |

The naming scheme is `entity.field.change` for field edits, plus `entity.create`, `entity.delete`, `member.remove`, `member.approve`. The final list is built when each model is implemented; a model's serializer declares which field maps to which code.

### Implementation notes (built 2026-10-09)

- Lives in the `projects` app: `MemberPermission(membership, code, granted_by)`, the registry and presets in `projects/constants/permissions.py`, `projects/permissions.py` (checks) and `projects/services/grant_service.py` (changes). All earlier features already called the one checking module, so no service logic changed.
- The project detail returns the held codes as `permissions` (not `my_permissions`).
- Presets (code, not a table): Viewer (nothing), Contributor (create and edit tasks, notes, comments, uploads; no deletes), Manager (everything delegable except `permissions.manage`). A data migration gave existing non-owner members Contributor.
- Delegation: changing a member's grants needs `permissions.manage`; every added or removed code must be held by the actor; the owner cannot be targeted. Starting permissions on join approval follow the same rule and default to none.
- No-grant exceptions: own comments, own attachments (uploader), leaving. Deleting tasks and notes needs `task.delete` / `note.delete`, even for the creator.
- Ownership transfer clears both owners' stored grants (the old owner starts with nothing).
- Not built yet: `activity.view` (with the activity endpoint, feature 9) and the Slack codes (features 7 and 8); each is registered when its feature lands.

### Celery jobs

None.

### Decisions

Field-level codes, project-wide grants, flat model, backend-generated descriptions, delegable permission management with a subset rule, whole-request 403 with the forbidden field list, per-request database check, presets decided later.

## 6. Security hardening

### Purpose

Protect the API against abuse and make security-relevant events visible: request limits, safe defaults for cookies and headers, a per-user security log and alerts.

### Models

| Model           | Key fields                                                                                                                                             | Notes                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| `SecurityEvent` | `user`, `event_type` (login success or failure, password change, session revoked, social account linked), `ip`, `user_agent`, `created_at`, `metadata` | Separate from the activity log. Each user can read their own recent events. |

Throttle counters are not models: they live in the Redis cache.

### Endpoints (proposed)

| Method and path                | Purpose                             |
| ------------------------------ | ----------------------------------- |
| `GET /api/me/security-events/` | The caller's recent security events |

### Rules and edge cases

- **Rate limiting** means a hard cap: the server answers 429 with a `Retry-After` header. The progressive-delay idea for logins was dropped; login failures rely on allauth's built-in limits.
- **Implementation:** DRF's built-in throttle classes on the Redis cache. The custom Redis limiter was rejected.
- **Default limits** _(assumed)_: anonymous 60 per minute per IP; signed in 600 per minute per user. Named scopes: login 5 per minute per IP; signup 5 per hour per IP; password reset 3 per hour per email; wrong join codes 5 per hour; uploads 30 per hour per user.
- **Per-project cap** _(assumed)_: an extra limit per project so one busy project cannot starve others.
- **Client IP:** behind a proxy the real address comes from `X-Forwarded-For`. DRF's `NUM_PROXIES` is set per environment (0 locally, 1 or 2 in production) so only the part added by our own servers is trusted.
- **Transport and cookies:** HTTPS only, secure cookies, `SameSite=Lax`, HSTS, and CORS allowing only the frontend origin. A maximum request body size is enforced.
- **API shape:** page size 25 default and 100 maximum; unknown fields rejected rather than ignored.
- **Passwords:** Argon2.
- **Alerts** _(assumed)_: emails for password change, email change and login from a new device.
- **Observability:** Sentry (free tier) and JSON logs with a request ID on every line. Sensitive fields are redacted from logs.

### Implementation notes (built 2026-10-09)

- **Scope split:** the app builds only what needs knowledge of users and projects; edge rate limiting, bot filtering, HSTS and response headers (Cloudflare), log search (Better Stack or Grafana) and uptime checks are external free tools. They are **not set up yet**; see "Not done yet: set up after deployment" below. No header or CSP middleware exists in the app.
- App `security/`: `SecurityEvent` (append-only, 180-day purge), `GET /api/me/security-events/`, `GET /api/health/`. Event types: login success, failure (known accounts only), locked, password changed, password reset, session revoked, social account linked, account deletion requested and cancelled.
- Login: per-account lockout after 5 wrong passwords in 15 minutes (fixed window, hashed cache keys, unknown emails counted too); 429 `login_locked` with `Retry-After`. Alert emails: new device (device name never seen in earlier successful sign-ins, not for the first), first lockout of a window, password change. An email-change alert is not built because there is no email-change feature yet.
- Rates: the spec values are the default (`STRICT_THROTTLE_RATES`); `PROJECT_MANAGEMENT_RELAX_THROTTLES=true` and the test run use relaxed ones. New per-project cap of 1200/min across all members.
- Observability: `X-Request-ID` in and out, a request/user id on every log line and in Celery tasks, JSON logs now include the redacted request data, Sentry for errors only (no PII, user id and request id only, secrets redacted).
- Fixed along the way: changing a password cycled the session key without updating the `UserSession` row, so the current session disappeared from the session list.

### Not done yet: set up after deployment

These parts of section 6 are **missing on purpose** and must be added when we move to deployment (they need a deployed API on a domain). They belong in the hosting and DevOps guide. Nothing in the code needs to change for them except where noted.

| Item | What to do | Needs |
| ---- | ---------- | ----- |
| **Cloudflare in front of the API** | Proxied DNS record for the API host; SSL/TLS Full (strict); Always Use HTTPS; HSTS (6 months, no preload at first); one rate-limit rule for `/api/auth/`; Bot Fight Mode; response-header Transform Rule on `/api/` adding `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and `Cache-Control: no-store`. Lock the origin so only Cloudflare can reach it (Cloudflare Tunnel is the simplest way), otherwise a forged `X-Forwarded-For` bypasses the per-IP limits. Set `PROJECT_MANAGEMENT_NUM_PROXIES=1` (2 if a load balancer is also in front) and re-check the per-IP limits behind the proxy. | A domain on Cloudflare DNS and a deployed API host |
| **Logs** | Ship the JSON stdout logs to Better Stack or Grafana Cloud (free tier) and make them searchable by `request_id`. The shipping method depends on the host (log driver, Vector or Alloy). Optionally add an alert on error-level lines. | The chosen host |
| **Uptime** | UptimeRobot or Better Stack checking `GET /api/health/` every 5 minutes, with email alerts. | A public URL |
| Sentry production project | Create or reuse the project with `PROJECT_MANAGEMENT_ENVIRONMENT=production` and the DSN in the production environment only; add a "new issue" alert. | Production environment variables |

Already in the code and ready for these: the `X-Request-ID` header and request id on every log line, JSON logs with the redacted request data, `GET /api/health/`, `NUM_PROXIES`, and the Sentry hook. The README section "Tools outside the app" has the same checklist.

### Permission codes

None.

### Celery jobs

Alert emails go through the shared `send_email` task. Beat: delete security events older than 180 days.

### Decisions

DRF built-in throttling on Redis. Trusted proxy count per environment. HTTPS, HSTS, strict CORS. Argon2. Unknown fields rejected. Separate security log. Sentry and JSON logs. CI deferred until the local build works.

## 7. Integration framework

### Purpose

Shared plumbing for any third-party provider. Slack is the only provider today, but events, inbound webhooks, retries, token storage and logging are generic so another provider can be added later (Google Calendar is a possible next one).

### Models

| Model             | Key fields                                                                                                                                                              | Notes                                                                           |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `OutboxEvent`     | `id`, `project`, `event_type`, `payload`, `source` (web, slack), `created_at`, `dispatched_at`                                                                          | Written in the same database transaction as the change.                         |
| `Integration`     | `project`, `provider`, `status` (active, needs_attention, disconnected), `installed_by`, `external_workspace_id`, `encrypted_token`, `settings`, `consecutive_failures` | Tokens are Fernet-encrypted with a key from the environment, with key rotation. |
| `LinkedAccount`   | `user`, `provider`, `external_user_id`, `encrypted_token`                                                                                                               | Each person links their own account.                                            |
| `InboundWebhook`  | `provider`, `delivery_id` (unique), `raw_payload`, `provider_timestamp`, `status`, `received_at`                                                                        | The unique delivery ID makes replays harmless.                                  |
| `DeliveryAttempt` | `integration`, `direction` (in or out), `event`, `status`, `response_code`, `attempt`, `next_retry_at`, `error`, `created_at`                                           | Kept 30 days.                                                                   |

### Endpoints (proposed)

| Method and path                                        | Purpose                                |
| ------------------------------------------------------ | -------------------------------------- |
| `POST /api/integrations/<provider>/webhook/`           | Inbound entry point for provider calls |
| `GET /api/projects/<id>/integrations/`                 | List and show health                   |
| `DELETE /api/projects/<id>/integrations/<id>/`         | Disconnect                             |
| `GET /api/projects/<id>/integrations/<id>/deliveries/` | Delivery log                           |
| `POST .../deliveries/<id>/replay/`                     | Manually replay a failed delivery      |

### Rules and edge cases

- **Outbox:** an event is saved with the change that caused it, and a worker forwards it afterwards. A crash can never lose an event or announce a change that was rolled back.
- **Event catalog (v1)** _(assumed)_: task created, task updated (with field-by-field changes), task assigned, due soon, overdue, comment added, member joined, member removed, project archived. Join request created is needed for Slack notifications (section 8).
- **Source tag:** every event records where the change came from (web or Slack), so a change that came from Slack is not posted back to Slack.
- **Inbound flow:** verify the provider signature, store the raw payload with the delivery ID, return 202 quickly, process in Celery.
- **Out-of-order delivery:** keep the provider's timestamp and ignore anything older than what was already applied for that item.
- **Retries:** 5 attempts with waits of 1 minute, 5 minutes, 30 minutes, 2 hours and 12 hours. After that the delivery is marked failed and can be replayed by hand.
- **Provider rate limits:** honor a 429 or `Retry-After` and pause that integration's queue.
- **Health:** after 10 consecutive failures the integration becomes _needs attention_, the installer gets an email and sending stops until it is reconnected.
- **Queues:** a separate Celery queue for integrations so a provider outage never delays emails or verification links.
- **Linking:** actions started from a provider run as the person who linked their account, with that person's permissions. Unlinked users get a "link your account" reply.
- **Disconnect:** revoke the token at the provider, delete stored credentials, keep log history for its normal 30 days.
- **Provider uninstall:** the integration shows _disconnected_ and stops processing.

### Implementation notes (built 2026-10-09)

- App `integrations/`; the fake provider (`integrations/testing.py`) exists for tests only. Slack plugs in through `integrations.providers.base.Provider` in feature 8.
- Events come from the activity log (a listener in `projects.services.activity`), so every change is saved with its outbox event in one transaction. `source` defaults to `web`, scheduled jobs use `system`, and `integrations.context.use_source` marks provider-originated changes. A provider never receives events whose source is its own code.
- Retries: the first attempt plus five retries after 1 min, 5 min, 30 min, 2 h and 12 h (six attempts in total), then `failed`; replay starts over. A rate-limit answer pauses the integration without using an attempt. Ten failures in a row set `needs_attention` (installer emailed once; owner if the installer is gone) and sending stops until `integration_service.reactivate` (called by a provider's reconnect flow) re-queues the waiting deliveries.
- Inbound: `receive` verifies through the provider, stores the raw call keyed by `(provider, delivery_id)`, answers 202 and processes in a worker; older calls for the same `item_key` are `ignored`.
- Management endpoints are as in the table; list and delivery log need `integration.logs.view` or the provider's manage code, disconnect and replay need the manage code. Project purge disconnects its integrations first so tokens are revoked at the provider.
- The activity-view permission `activity.view`, `integration.logs.view` and `integration.slack.manage` are registered; the Manager preset includes them.
- Not built here (feature 8): the Slack provider, install and link flows, channel mappings, notification preferences. `LinkedAccount` exists with `link`/`unlink`/`find_user` services only.

### Permission codes

`integration.<provider>.manage` (for Slack: `integration.slack.manage`) to install, configure and remove; `integration.logs.view` to read delivery logs. The owner always holds both.

### Celery jobs

- Outbox dispatcher (polls for undispatched events); per-provider delivery task with the retry schedule above.
- Inbound webhook processor.
- Beat: delete delivery attempts and processed webhooks older than 30 days.

### Decisions

Transactional outbox. Inbox with dedupe by delivery ID. Five retries with backoff. Separate queue. Fernet-encrypted tokens. Per-provider manage permissions. Users link their own accounts. 30-day delivery log.

## 8. Slack

### Purpose

Post project events into Slack channels, notify people by direct message, and let linked users create and finish tasks with slash commands. One Slack app is registered once by the app developer; users only approve it, never create their own.

### Models

Slack reuses `Integration`, `LinkedAccount`, `InboundWebhook` and `DeliveryAttempt` from section 7, plus:

| Model                    | Key fields                                                                                      | Notes                                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `SlackChannelMapping`    | `integration`, `channel_id`, `channel_name`, `is_public`, `enabled_events` (set of event types) | A project can map several channels, each with its own event toggles. |
| `NotificationPreference` | `user`, `event_type`, `email` (bool), `slack_dm` (bool)                                         | Per-user choice of channel for each event.                           |

### Endpoints (proposed)

| Method and path                                                   | Purpose                                       |
| ----------------------------------------------------------------- | --------------------------------------------- |
| `GET .../integrations/slack/install/` and `.../install/callback/` | "Add to Slack" OAuth for the project          |
| `GET .../integrations/slack/channels/`                            | Channels the bot can see                      |
| `GET/POST/PATCH/DELETE .../integrations/slack/mappings/`          | Channel mappings and event toggles            |
| `GET /api/me/integrations/slack/link/` and `.../link/callback/`   | "Sign in with Slack" to link the caller       |
| `POST /api/integrations/slack/commands/`                          | Slash command endpoint                        |
| `POST /api/integrations/slack/events/`                            | Event callbacks (for example app uninstalled) |
| `GET/PUT /api/me/notification-preferences/`                       | Per-event email and Slack DM choices          |

### Rules and edge cases

- **Installation:** needs `integration.slack.manage`. One Slack workspace can connect to several projects.
- **Bot access:** the bot posts only in channels it has been invited to; the owner invites it manually. This avoids requesting broad Slack scopes.
- **Message content:** key, title, status, assignee, due date and a link. Never the description or comments, because a channel may be public. The settings page warns when a mapped channel is public.
- **Events posted:** the toggles apply to the catalog in section 7: assigned, due soon, overdue, new comment, new join request, and the other catalog events.
- **Each update is a new message**, not a threaded reply.
- **Account linking:** each person uses "Sign in with Slack" once. People are never matched by email automatically.
- **Direct messages:** an assignee receives a DM when assigned if linked; each user can turn email or Slack DM on or off per event.
- **Slash commands (v1):** `/task create <project key> <title>` and `/task done PMS-42`. Replies are visible only to the person who typed the command.
- **Permissions:** commands run as the linked user and are checked against that user's permissions. Unlinked or forbidden users get a private explanation.
- **3-second rule:** Slack needs an answer within 3 seconds, so the endpoint acknowledges immediately and Celery does the work, then replies through Slack's follow-up URL.
- **Request verification:** every Slack request is checked with the signing secret and rejected if older than 5 minutes, to stop replays.
- **Echo prevention:** changes made from Slack carry `source = slack` and are not posted back.
- **Uninstall:** if the workspace removes the app the integration shows _disconnected_ and its tokens are deleted.
- **Local development:** Slack must reach the developer's machine, so a public HTTPS tunnel is needed: ngrok with its free static domain (decided 2026-10-09).
- **Fixed callback URLs (decided 2026-10-09):** Slack only accepts redirect URLs registered in advance, so the OAuth callbacks cannot contain a project id. They are `POST/GET /api/integrations/slack/install/callback/` and `/api/integrations/slack/link/callback/`; the project (install) or the user (link) travels in the signed `state` parameter. The slash command and event endpoints are `/api/integrations/slack/commands/` and `/api/integrations/slack/events/`. These replace the project-scoped callback paths in the endpoint table above.

### Prerequisites (set up 2026-10-09)

Done in the repo: `docs/slack/app-manifest.yml` (the app definition to paste when creating the Slack app), settings and `.env.example` entries, `cryptography` as a direct dependency.

| Variable | Meaning |
| -------- | ------- |
| `PROJECT_MANAGEMENT_PUBLIC_API_URL` | Public HTTPS address Slack uses to reach the API (tunnel URL in development). Its host must also be in `ALLOWED_HOSTS`. |
| `PROJECT_MANAGEMENT_INTEGRATION_ENCRYPTION_KEYS` | Fernet keys (comma separated; the first encrypts, all decrypt, so rotation means adding a new key in front). |
| `PROJECT_MANAGEMENT_SLACK_CLIENT_ID`, `..._CLIENT_SECRET`, `..._SIGNING_SECRET` | From the Slack app, Basic Information > App Credentials. The signing secret verifies every inbound request. |

Slack app settings: bot scopes `chat:write`, `commands`, `channels:read`, `groups:read`; slash command `/task`; the two redirect URLs above (the "Sign in with Slack" flow uses the OpenID scopes `openid`, `profile`, `email` requested at authorize time and the same registered redirect URLs, so it needs no manifest entry). Event Subscriptions (`app_uninstalled`, `tokens_revoked`) are added after the events endpoint exists, because Slack verifies that URL when it is saved. The app stays in the developer's own test workspace until we decide to distribute it; distribution (Slack's review for the Marketplace) is not needed for the v1 goal that each customer workspace simply installs it.

### Implementation notes (built 2026-10-09)

- Code in `integrations/slack/`; official `slack-sdk` (`WebClient` for API calls, `WebhookClient` for private command replies, `SignatureVerifier` for inbound requests). Socket Mode and the async clients are not used.
- Install and link callbacks are fixed URLs (`/api/integrations/slack/install/callback/`, `/link/callback/`) with project and user in a signed, 10-minute `state`; the signed-in session user must match it. The browser is redirected to `FRONTEND_URL` with `?slack=connected|linked|error&reason=...`. "Sign in with Slack" requests only the `openid` scope and uses Slack's own user id and team id; people are never matched by email.
- Channel mappings require the bot to be in the channel (409 `bot_not_in_channel`); public channels carry `warn_public`. Messages are Block Kit with a text fallback and contain only key, title, status, first names, due date and a link.
- `Provider.plan()` lets one event make several deliveries (`DeliveryAttempt.target`, unique with event and integration): a message per mapped channel with the event on, plus a DM per recipient. DMs exist for five events (task assigned, due soon, overdue, comment on my task, join request); linked members only, per-person `slack_dm` preference (default on). `email` is stored in `NotificationPreference` but inactive until the email notifications of feature 9.
- Slash commands acknowledge with an empty 200, run in a worker, and reply privately. `/task create <KEY> <title>` and `/task done <KEY-42>` resolve the project by key among the caller's projects connected to the calling workspace (several matches: asked to rename), run through the normal task services with the caller's permissions, and are tagged `source=slack`.
- The events endpoint answers Slack's URL check, then handles `app_uninstalled` (every project of the workspace is disconnected and tokens wiped) and `tokens_revoked` (matching bot integrations disconnected, revoked people unlinked). A dead token seen while posting disconnects the integration at once.
- Fixed in feature 7's event mapping: people assigned while a task is created now also produce `task_assigned` events.
- Manifest: bot scopes `chat:write`, `commands`, `channels:read`, `groups:read`; add `im:write` if Slack refuses DMs.

### Permission codes

`integration.slack.manage`, `integration.logs.view`. Linked users act with their own project permissions, for example `task.create` for `/task create`.

### Celery jobs

- Slash command executor (integrations queue).
- Outbound message sender consuming outbox events, with the shared retry schedule.
- DM and channel notification fan-out.

### Decisions

Slack is the only integration. Per-project channel mapping with event toggles. Bot invited manually. Minimal message content. Link by Sign in with Slack. DMs with per-user preferences. Two slash commands in v1. Signing secret and 5-minute replay window.

## 9. Cross-feature pieces

Four shared mechanisms are used by several features. Build them once and have each feature plug in.

### Activity log

- **What:** an append-only record of changes. Rows hold actor, action, entity type and ID, field-level old and new values, time and IP. Rows are never updated.
- **Covers:** project events (member joined or removed, ownership transferred, code regenerated), task, note, comment and status changes, and automated actions (shown with their source, for example Slack).
- **Access:** project members holding the activity-view permission. Retention is 1 year, purged by a beat job.
- **Separate from the security log** (section 6), which is per user and about sign-in and account events.
- **Feeds** the outbox: the same change that writes a log row can emit an event.

### Permission registry

- A code-level registry lists every permission with `code`, `label`, `description`, `group`.
- One endpoint serves it, so the frontend never keeps its own copy of descriptions.
- Serializers map each writable field to a code. A shared DRF mixin checks every field in a request against the caller's grants and raises one 403 listing all forbidden fields.
- Presets (Viewer, Contributor, Manager) will be defined as lists of codes later.

### Transactional outbox

- A service function that changes data also writes an `OutboxEvent` inside the same transaction.
- A dispatcher task reads undispatched events and hands them to subscribers: email, Slack, and notifications.
- Events carry a `source` so integrations can avoid echoing their own changes back.
- Consumers must be idempotent, because dispatch is at-least-once.

### Reassignment registry

- Each model that is owned by a user registers a handler: its name, what "owned" means, and how to move or unassign it.
- Member removal sends a map such as `{tasks: U1, notes: U2}`; the registry validates that targets are members and runs every handler in one transaction.
- Models not in the map become unassigned (tasks) or keep their author name (comments, created-by history).
- The same mechanism is reused when a status or priority is deleted: the caller picks the replacement.
- Adding a new owned model means registering one handler; no change to the removal endpoint.

### Celery jobs, all features

| Job                                                                        | Schedule or trigger           | Queue        |
| -------------------------------------------------------------------------- | ----------------------------- | ------------ |
| Send email (verification, reset, alerts, mentions, join requests)          | On demand                     | default      |
| Purge deleted accounts                                                     | Daily, 7 days after deletion  | default      |
| Purge deleted projects                                                     | Daily, 7 days after deletion  | default      |
| Expire join requests (14 days) and ownership transfers (7 days)            | Daily                         | default      |
| Due soon and overdue scan                                                  | Daily or hourly (not decided) | default      |
| Clear expired sessions                                                     | Daily                         | default      |
| Attachment post-processing, cleanup, usage recompute                       | On demand, nightly            | default      |
| Outbox dispatcher                                                          | Every few seconds             | integrations |
| Provider delivery with retries, inbound webhook processing, Slack commands | On demand                     | integrations |
| Purge activity log (1 year), delivery logs (30 days)                       | Daily                         | default      |

## 10. Demo projects, copy to workspace, onboarding tour

### Purpose

New accounts should have live data to explore without per-user duplication. A system user that cannot log in owns a few shared, read-only demo projects. Every newly activated account joins them as a viewer. Users who want to work with the data copy a demo into a project they own.

### Rules

- **System user:** `User.is_system`. Reserved `@system.invalid` email, unusable password, never logs in (rejected at session start, Google login and the default API permission), never deleted, never emailed.
- **Demo project:** a project with a non-null `demo_key` (stable id used by the idempotent `seed_demo_projects` command). Owned by the system user, always listed on explore, never archived, deleted, transferred or edited. Demo data carries no dates, so nothing goes stale and there is no reset or date-shift job.
- **Membership:** members of a demo project are viewers (a Membership with zero grants). A user is joined to every demo project once, when the account becomes usable (email verified, or created through Google). Leaving is allowed and is never undone by a later login. Rejoining is open: from explore, no request and no approval. Demo projects cannot be joined by code.
- **Privacy:** the member list of a demo project shows only the caller and the owner. Seed content is authored by the system user, so no real person appears in it.
- **No cap on members:** read-only demo projects need no member cap.
- **Copy to workspace:** `POST /api/projects/{id}/copy/`. Any member of a demo project may copy it into a new unlisted project they own (statuses, priorities, tasks with parents and tags, notes, comments). Attachments, integrations, activity, requests and preferences are not copied. Each user may hold at most 3 live copies. Throttled at 5 per hour.
- **Disposable emails:** when `PROJECT_MANAGEMENT_ENVIRONMENT=prod`, signup and email change refuse addresses on known throwaway-mail domains (and their subdomains) with `disposable_email` on the email field. Existing accounts, login and Google sign-in are not affected. `local` accepts everything.
- **Tour flag:** `User.tour_completed_at`. Exposed as `tour_completed` on `/api/me/`; `POST /api/me/tour/` marks it done, `DELETE /api/me/tour/` resets it for a replay.

### Decisions

- Read-only demo instead of a shared writable one: no moderation, no graffiti, no reset job.
- Copy is opt-in, so storage grows only for users who ask for it.

## Backend wrap-up (built 2026-10-09)

- **Activity feed:** `GET /api/projects/<id>/activity/`; `activity.view` holders see all, everyone else only their own actions; IP never returned; long values cut to 200 characters; rows older than 1 year purged daily. Completes feature 9.
- **Explore:** `Project.listed_at` (set when listed, cleared when unlisted); `GET /api/explore/`, `GET /api/explore/tags/`, `POST /api/explore/<project_id>/join-request/` (unlisted, archived or deleted projects are 404). Throttle `explore_join` 20/hour.
- **Email change:** `PendingEmailChange` (one per user) instead of an unverified allauth address, so stale requests can be aged out (purged after 24 h). Re-authentication required, neutral reply, link to the new address, alerts to the old address at request and completion, all sessions revoked on confirm, `email_changed` security event. Throttle `email_change` 5/hour.
- **Email notifications:** second outbox subscriber for the five personal events; opt-in (`email` preference, default off); same audience as Slack DMs; idempotent per event and person.
- **OpenAPI:** generated from the code with `drf-spectacular` (requests exact, responses wrapped in the envelope with a free `data`), exported to `docs/openapi.yml`; Swagger UI in DEBUG only.
- **Postgres:** the whole test suite was run against real Postgres with no changes needed.
- CI is part of the DevOps stage, after the frontend.

## Known limitations

These are accepted trade-offs for v1, not bugs.

| Limitation                                                  | Effect                                                                  | Mitigation or later fix                                                                                                               |
| ----------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| No virus scanning (ClamAV dropped)                          | A malicious file could be stored and shared between members             | Content-type sniffing, no SVG, HTML or executables, forced download headers, separate storage domain, private bucket with signed URLs |
| "Overdue" uses the server's UTC date                        | Someone far from UTC sees a task turn overdue a few hours early or late | A project-level time zone could be added later                                                                                        |
| DRF built-in throttling has a race                          | Two simultaneous requests can both pass just under a limit              | Acceptable for v1; a Lua-based atomic limiter was considered and rejected                                                             |
| Permissions are read from the database on each request      | Extra queries per request                                               | Per-request cache now; Redis cache later if slow                                                                                      |
| Project-wide grants only                                    | Cannot give someone rights on one task only                             | Per-task grants could be added later                                                                                                  |
| No manual card ordering on kanban                           | Cards sort by a chosen field only                                       | Revisit after launch                                                                                                                  |
| Filters, sort and search are not saved                      | Reset on every refresh                                                  | By design; only the kanban setup is stored                                                                                            |
| Slack messages may reach large public channels              | Minimal data is exposed there                                           | Content kept to key, title, status, assignee, due date; settings page warns on public channels                                        |
| Single owner and no layer above projects                    | No shared member list, org settings or billing across projects          | Out of scope                                                                                                                          |
| Google is the only social login, Slack the only integration | Narrower than first planned                                             | Framework is generic, providers can be added                                                                                          |
| Correct client IP depends on `NUM_PROXIES`                  | Wrong value breaks per-IP limits or lets them be spoofed                | Set per environment and document in the hosting guide                                                                                 |

## Open questions

Gaps, contradictions and defaults the owner never confirmed. Each needs an answer before the related feature is built.

### Accounts

1. ~~**Remember me**~~ Confirmed 2026-10-08: 30 days sliding.
2. ~~**Change password while logged in**~~ Confirmed 2026-10-08: current password plus new password; other sessions are logged out; an alert email is sent.
3. ~~**Account deletion**~~ Confirmed 2026-10-08 (defaults accepted): login during the 7 days cancels it, tasks and comments are kept as "Deleted user" (to be honored by features 3 and later via `SET_NULL`), and deletion is blocked while the user owns a project (feature 2 registers its check in `deletion_service.ownership_checks`).
4. ~~**Join code alphabet**~~ Confirmed 2026-10-09: uppercase letters and digits without the look-alikes `0 O 1 I L` (31 symbols).

### Projects

5. **Archive:** owner only is assumed. What does read-only mean for members, and is it delegable?
6. ~~**Task key edits**~~ Confirmed 2026-10-09: tasks are addressed by number only (`/tasks/42/`); the key is display only, so no alias table.
7. ~~**Explore page**~~ Resolved 2026-10-09: newest listing first; filters text, tags (any of), dates; no seeded or featured tags (suggestions are the most used among listed projects).
8. ~~**Join limits**~~ Resolved 2026-10-09: listed projects use the same limits as code joins (10 open requests, 24 h after a rejection); the wrong-code counter does not apply because no code is typed.

### Tasks and attachments

9. ~~**Task description**~~ Default applied 2026-10-09: a task keeps its own markdown description.
10. ~~**Seeded defaults**~~ Applied 2026-10-09: statuses To do (todo, default), In progress and In review (in progress), Done and Cancelled (done); priorities Low, Medium (default), High, Urgent.
11. ~~**Pagination style**~~ Offset (`limit`/`offset`), 25 default, 100 max.
12. ~~**Retention of soft-deleted tasks**~~ Confirmed 2026-10-09: 7 days.
13. ~~**Mentions**~~ Default applied 2026-10-09: current project members only, `@[user:<uuid>]` tokens, email only (no in-app list yet).
14. ~~**Local file storage**~~ Resolved 2026-10-09: attachments need R2 (the same bucket as avatars); tests use an in-memory fake; local-disk storage answers 503.

### Permissions, security and logs

15. ~~**Permission list and presets**~~ Resolved 2026-10-09: the registry in code is the list (names as built); presets `viewer`, `contributor`, `manager` are defined in code. New codes are added with their feature.
16. ~~**Activity-view permission name**~~ Resolved 2026-10-09: `activity.view` (registered in feature 7); holders see all project activity, everyone else only entries where they were the actor. The endpoint is built in feature 9.
17. ~~**Security log retention**~~ Resolved 2026-10-09: 180 days.
18. ~~**Due-soon scan**~~ Resolved 2026-10-09: daily at 08:00 UTC; due soon = due today or tomorrow, overdue = past the due date; each fires once per task and due date.

### Slack and integrations

19. ~~**Slack features beyond v1**~~ Left out of v1 (confirmed by building feature 8 without them): buttons on messages, link unfurling, `/task mine` and a daily digest.
20. ~~**Local Slack testing**~~ Resolved 2026-10-09: ngrok free plan with its static domain (`ngrok http --url=<your-domain> 8000`), so the Slack app URLs are set once.
21. **Google Calendar:** later or dropped? The default was later, not v1.

### Contradictions already resolved

- ClamAV was first required in v1, then dropped. Dropped wins.
- A cap of 20 owned projects per user was proposed; the owner replied no cap.
- Social login was first Google and GitHub, then Google only. Invite-by-email was dropped in favor of codes.
- Timezones were requested, then dropped; deadlines are dates only.
- The hosting and DevOps guide the owner asked for is still to be written. It must include the deployment-time items from section 6 (Cloudflare, logs, uptime, production Sentry).
