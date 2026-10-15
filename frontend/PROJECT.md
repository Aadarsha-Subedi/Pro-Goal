# PROJECT.md: Frontend Plan

2026-10-10

Pro-Goal frontend. Sits beside the Django REST backend (`../backend/project.md` is its source of truth). This file is the frontend's build plan, feature by feature, with the quality scores recorded after each feature.

Product truth lives in `PRODUCT.md`, the visual system in `DESIGN.md` and `.impeccable/design.json`. Surface briefs are in `.impeccable/surfaces/`, critique snapshots in `.impeccable/critique/`.

## Stack and rules

- React 19, TypeScript, Vite, Tailwind v4, shadcn `base-nova` (Base UI), TanStack Router, Query, Table, Phosphor icons, GSAP (`src/motion`). Dev server on port 3000 (backend CSRF origin), `/api` proxied to :8000.
- One SPA, two route groups: public (`/`, `/login`, `/signup`, auth flows, legal) and private (`/app/*`).
- Everything is built with Impeccable and the shared design system (`src/components/ui`, `src/components/patterns`). No one-off styling that bypasses tokens.
- Binding design rules: Button + Icon wherever feasible, no cards over cards, flat surfaces, permissions visible in the UI, light and dark following system.
- Backend errors are handled by their stable `code`, never by message text. Session-cookie auth plus CSRF through the single client in `src/lib/api.ts`.
- Security hardening (CSP, Sentry, dependency policy) is deferred to its own pass near the end.

## Route access

| Route | Rule |
| --- | --- |
| `/`, `/login`, `/signup`, `/forgot-password` | Guest only. A signed-in user is redirected to `/app` (or `/complete-profile` when the profile is unfinished). |
| `/app/*` | Needs a session. Anonymous goes to `/login`, unfinished profile goes to `/complete-profile`. |
| `/complete-profile` | Needs a session with an unfinished profile. Anonymous goes to `/login`, complete goes to `/app`. |
| `/verify-email`, `/reset-password`, `/terms`, `/privacy` | Open to everyone (links arrive from email or the footer). |
| `/design-preview` | Dev reference page. |

Guards live in `src/lib/session.ts` (`guestOnly`, `requireSession`, `requireIncompleteProfile`) and run in each route's `beforeLoad`. They are UX only; the backend enforces access.

## Feature workflow

Every feature follows the same loop, in order. A feature is not done until the last step is recorded.

1. **Scope.** Read the backend feature section, list screens and states, write or update the surface brief (`impeccable shape`, then the direction contract). Unresolved scope is asked of the owner and written here before coding.
2. **UI.** Build with the design system. New patterns go into `src/components/patterns` and `/design-preview`, not into the feature.
3. **API.** Typed calls in `src/features/<feature>/api.ts` over `src/lib/api.ts`, errors mapped by `code`, tests for the mapping.
4. **Audit and critique.** Run `impeccable audit` and `impeccable critique` (dual agent) on the feature's target. Store the critique with `critique-storage write`.
5. **Fix.** Resolve P0 and P1 findings and the agreed P2s.
6. **Re-run** audit and critique. Repeat 5 and 6 until no P0 or P1 remains or the owner accepts the rest.
7. **Record.** Update the score table below, update `DESIGN.md` if the system changed, update `README.md` if setup changed, keep `tsc`, `oxlint`, `vitest` and the build green.

Scoring: critique is out of 40 (ten Nielsen heuristics, 0 to 4), audit is out of 20 (accessibility, performance, theming, responsive, implementation integrity). Bands: audit 18 to 20 excellent, 14 to 17 good; critique 28 to 31 acceptable plus, 32 and above good.

## Feature map

Mirrors the backend feature map. Order is the build order.

| # | Frontend feature | Backend | Status |
| --- | --- | --- | --- |
| 0 | Design system and `/design-preview` | none | Done |
| 1 | Landing page, auth layer, route guards | Accounts and sessions (1) | Built. Run 4 scores recorded; re-score after the latest fixes pending |
| 2 | App shell, projects, membership, join requests, ownership transfer | Projects (2) | Built, scored twice, no P0 or P1 open |
| 3 | Tasks, subtasks, notes, comments, statuses, priorities, kanban | Tracker (3) | 3a, 3b, 3c built and re-audited (16, 17, 17 of 20); critique re-run still owed |
| 4 | Attachments and quotas | Attachments (4) | Built, not yet live-tested or scored |
| 5 | Field-level permissions UI | Permissions (5) | Built, not yet audited. Editor, matrix, lock copy done |
| 6 | Account security: sessions, security log, lockout notices | Security (6) | Built, not yet audited. `/app/account`, lockout notice done |
| 7 | Integrations framework screens | Integrations (7) | Built, scored once, live Slack pass pending |
| 8 | Slack integration | Slack (8) | Built, scored once, live Slack pass pending |
| 9 | Activity feed, explore, account basics, email change, loading and 404 screens | Cross-feature (9) | Built, scored once |

## Score history

One row per audit and critique run. Append, never overwrite. Critique heuristics order: visibility, match with real world, user control, consistency, error prevention, recognition, flexibility, aesthetic, error recovery, help.

### Feature 0: Design system (`src/features/design-preview`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 26 | n/a | 0 | 2 | Permission model absent from the system, hollow join dialog |
| 2 | 25 | 16 | 1 | 2 | Cmd+K crash found and fixed |
| 3 | 25 | 17 | 0 | 3 | Contract breaks (voice, boxed banners, toast colors) |
| 4 | 27 | 16 (17 after overflow fix) | 0 | 2 | Delete project lacked typed confirm, accent discipline |

### Feature 1: Landing, auth, route guards (`src/features/marketing`, `src/features/auth`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 27 | 15 | 0 | 2 | Landing did not prove locked-field reason, signup had five fields. Double error conversion fixed |
| 2 | 27 | 16 | 0 | 1 | First viewport cut Figure 1. Google button label and overlay fixed |
| 3 | 28 | 17 | 0 | 3 | Revision table contradictory, dimension lines weak, invited users no fast lane |
| 4 | pending | pending | | | After fixes: revision table, dimension lines, verify dead-ends, skip link, tap targets, mobile roles, route guards |

Detector: one intentional advisory (`codex-grid-background`, the blueprint grid on public surfaces).

Open items for Feature 1:
- Invited-user fast lane: built in Feature 2 (`src/lib/invite.ts`, `/join`).
- Terms and Privacy are placeholders until legal copy exists.
- Real Google sign-in not yet clicked through; `http://localhost:3000` must be an Authorized JavaScript origin in Google Cloud.
- Guards are checked with an anonymous session only; the signed-in redirect needs a manual pass with a real account.
- `.env` is not ignored by `frontend/.gitignore`; add it when the repo is created.
- Expired sessions: handled in Feature 2 (`setUnauthorizedHandler` in `src/lib/api.ts`, wired in `src/main.tsx`).

### Feature 2: App shell, projects, membership (`src/features/projects`, `src/components/layout`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 26 | 15 | 1 (audit) | 2 design, 4 audit | Invite code redirect loop; preset carried between approvals; reauth password retained; cache survived sign out; join loop had no pending count |
| 2 | 29 | 17 | 0 | 0 | All P0 and P1 fixed. Open P2: settings order and danger zone, hollow "Tasks arrive next" block, Save button reason |

Detector: no findings. Backend error-code parity test guards `errors.ts`.

Open items for Feature 2:
- Undo toast for approve and decline (promised in DESIGN.md, not built).
- Members and requests lists load the first 100 and say so; paging comes when a project needs it.
- Transfer offers have no Decline button (ignore to decline); revisit with Feature 6 notifications.
- Reassignment map on member removal waits for Feature 3.
- The signed-in user's join step has not been exercised end to end against a second real account (emails are real); do this with throwaway accounts and the worker off.
- E2E test accounts live in the dev database (`e2e-owner@pro-goal.test`, `e2e-member@pro-goal.test`); credentials are in `frontend/.env.e2e.local` (git-ignored).

### Feature 3a: Tasks (`src/features/tracker`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 25 | 15 | 0 | 2 design, 4 audit | Audit P1s fixed after the run (search focus, page clamp, honest delete copy, per-permission workflow gating) |
| 2 | n/a | 16 | 0 | 0 | Re-audit only. Open P2: inline select errors and pending state, touch size, page clamp now in an effect |

Open items for 3a:
- List has no inline edit, bulk selection or keyboard row navigation (design P1, not started).
- Mobile task row layout is ragged below 640px (design P1, not started).
- Lock notes show permission codes, not names or who to ask.
- Board (3b) and Notes and comments (3c) not started; board query and preference code already exists in `tracker/api.ts` and `queries.ts`.
- Backend: `project` object added to task responses (needed by My tasks); tests and OpenAPI pass.

### Feature 3b: Board (`src/features/tracker/board`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 25 | 15 | 0 | 2 design, 3 audit | P1s fixed after the run (overlay, undo, announcements, focus, truncation notice) |
| 2 | n/a | 17 | 0 | 0 | Re-audit only. Every fix verified; only P3 items remain |

Open items for 3b:
- Keyboard drag moves 25px per key; the per-card Move menu is the supported keyboard path. A lane-aware keyboard sensor is not built.
- Empty lanes are 288px wide each; consider a collapsed rail.
- Mobile controls block (group, sort, filters) is tall.
- Assignee lanes drop cards whose only assignee is no longer a member.
- Drop animation ignores reduced motion; GSAP Flip re-sort animation not built.

### Feature 3c: Notes and comments (`src/features/tracker/{notes,comments}`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 26 | 15 | 0 | 2 design, 2 audit | Design review was code-only (browser tab cap). P1s fixed after the run |
| 2 | n/a | 17 | 0 | 0 | Re-audit only. Lost-update fix verified live. Open P2: conflict banner offers no way to read their version |

Browser-checked: create note, edit and save, comment on a task.

Open items for 3c:
- Re-run audit and critique after the P1 fixes; the design pass needs a live browser look.
- @mention picker is in comments only; the note editor has none yet.
- The note page does not list linked tasks (the backend has no note-to-tasks endpoint).
- Mentions send real emails; mention flows were not exercised in the browser.
- Locked states for members without permissions were not exercised live.

### Feature 4: Attachments (`src/features/attachments`)

Built, not yet audited or live-tested against R2 (needs the bucket CORS rule for `http://localhost:3000`). Unit tested: client limits, upload pipeline (progress, processing poll, refusals, cancel), error-code parity.

Built: drop zone with browse and paste, upload queue (2 at a time, cancel, retry), file lists with download and delete on tasks, comments and notes, inline note images (`![alt](attachment:id)` resolved to signed links, third-party images never loaded), project and personal storage meters in settings.

Live check done 2026-10-10 on task AL-2: a 1 KB text file uploaded to R2, confirmed, listed, deleted. Found and fixed a StrictMode bug that left uploads at 0% (the unmount flag was never reset on remount). Upload row now eases to 100%, folds away and the file slides into the list (GSAP, with a fallback for hidden tabs). Not yet live-checked: comment and note uploads, inline note images, PNG processing, refusals.

Open items for 4:
- Audit, critique, fix, re-run, record scores.
- Comment files are reached through a Files button per comment (author or moderator), not in the composer.

### Feature 5: Permissions (`src/features/permissions`)

Built, not yet audited. Per-member editor at `/app/projects/$projectId/members/$userId/permissions` (preset select, registry-driven groups, subset-rule rows disabled with the reason, diff footer, one PUT, owner and archived read-only), "Who can change what" matrix on Members for owners and `permissions.manage` holders (one grants request per member, capped at 30), "Permissions" button per row ("Your permissions" for yourself), and `useLockText` replacing raw permission codes in every lock note. Unit tested: grants diff, preset match and apply, subset rule, group counts.


| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 (F5+F6 together) | 29 | 15 | 0 | 2 design (matrix on mobile, unsaved-changes guard) | Fixed after the run: leave guard, scroll region, th scope=row, blank cells, draft keyed by member, no Retry on 403. Critique was desktop and code, mobile and dark not seen |

Open items for 5:
- Editing a second member live is untested: the dev project has only the owner, and joining needs approval emails (worker on). Do it with a seeded second membership.
- Re-run audit and critique; matrix fans out one GET per member (a bulk grants endpoint would remove it); no conflict detection if two managers edit at once; no select-all per group.

### Feature 6: Account security (`src/features/account`)

Built, not yet audited. `/app/account` (user menu, "Account security"): signed-in devices with sign out per device, security log with event filter and paging, personal file storage. Login lockout: `ApiError.retryAfter` from `Retry-After`, `AuthError("locked")`, login notice says how long to wait. Unit tested: lockout mapping, `waitText`, error parity.

Open items for 6:
- Revoking another session live is untested (needs a second sign-in).
- No "sign out everywhere else" (backend has no endpoint). Profile, password change and account deletion are not built.
- Scored together with Feature 5 above. Re-run pending. `Retry-After` is not in CORS exposed headers (fine behind the proxy). "Check this was you" has no next-step link.

### Features 7 and 8: Integrations and Slack (`src/features/integrations`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 (7+8 together) | 28 | 15 | 0 | 1 audit, 3 design | Fixed after the run: logs-only viewers no longer hit a 403 channel panel; disabled Slack switches no longer show on; needs-attention is bold with a "See why" link for everyone; edit dialog no longer flips to create mode on close; per-field rollback of notification switches; defaults stated; select all and clear for events; page renamed Account |

Built: Integrations page (Slack row, status as icon plus text, Disconnect, Reconnect), channel mappings with event dialog and public-channel warning, delivery log with status filter and Send again, Slack link and Notifications table on `/app/account`, redirects for the backend's OAuth return paths. Unit tested: error parity, return-message wording, event summary and toggle.

Open items for 7 and 8:
- Live Slack pass (install, map a test channel, post, link, DM) needs the user to approve the Slack app in the browser; not done.
- Delivery log does not show the target (channel or person); the API does not return it.
- Log has no auto refresh; no event filter.
- Re-run audit and critique after fixes.

### Feature 9: Activity, Explore, Account basics, loading and 404 (`src/features/{activity,explore,account}`)

| Run | Critique /40 | Audit /20 | P0 | P1 | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 33 | 16 | 0 | 2 audit, 2 design | Fixed after the run: false "signed out everywhere" claim on delete, permission and Slack-event lists in the feed, confirm page now warns of sign-out and says "This wasn't me", Explore dead "member" branch and extra request removed, Activity uses the shared DatePicker, stable onSearch, cache cleared after email confirm, shorter account header |

Built: activity feed (describe with a backend action-parity test), Explore with request states, Profile, Password, Email (re-auth dialog and `/confirm-email-change`), Delete account with typed confirmation and 7-day banner, boot screen wired to the router (refresh, reload, first step into the app) and 404 screen.

Open items for 9:
- **Needs a backend change:** `task.updated`, `note.updated`, `status.updated`, `comment.deleted` entries carry no task number or title, so the feed says "updated a task" with no link. Adding it in `projects` would break layering (tracker owns tasks); needs a hook or the tracker writing `number` into a separate field the outbox ignores.
- The confirm-email page cannot name the new address (the backend does not return it).
- Password form cannot hide the current-password field for Google-only accounts (no `has_password` flag).
- Account page is nine sections long with no in-page navigation.
- Email change, password change, deletion, avatar and join-from-Explore were not exercised live (real mail); covered by code review only.
- Re-run audit and critique after fixes.

## Per-feature scope notes

Filled in at step 1 of the workflow, when each feature starts.

### Feature 2 scope (built)
Backend screens covered: project list and create, join by 6-character code, join request approval (owner), member list, ownership transfer with re-authentication, leave and remove member, project settings and delete. Existing patterns to reuse: join dialog, delete-project dialog, permission figure, solid-destructive confirm. Scope questions go to the owner before coding.
