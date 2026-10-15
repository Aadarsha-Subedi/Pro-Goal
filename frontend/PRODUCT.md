# Product

Name: Pro-Goal. Logo: Phosphor Target mark in the accent color with the wordmark.

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Small developer and product teams (roughly 2-30 people) running several projects at once. Daily use: triaging tasks, moving work between statuses, reading notes and comments, checking activity, reacting to Slack notifications. Project owners also approve join requests and manage member permissions.

## Product Purpose

A project management tool where projects, tasks and notes live in one app and reach the team in Slack. Each project is its own tenant. People join with a 6-character join code plus owner approval, a Slack channel per project receives the events the owner picks, and per-field permissions decide what each member may change. Success: a team gets set up in minutes, hears about changes in Slack, and stays in control of who can edit what as it grows.

## Positioning

Lead with the whole loop: collaborate on projects, manage tasks and notes, and get updates in Slack. Lightweight to start (no workspaces, no email invites, join by code), precise as the team grows (field-level permission grants, subset rule, owner re-authentication for sensitive actions). Permissions are the differentiator lower on the landing page, not the headline.

## Operating Context

- Frontend sits beside a Django REST backend (cookie sessions + CSRF, project-scoped routes, non-members get 404).
- Two surfaces: a public landing page (hero: "Projects, tasks and notes, all in one app and Slack", with an animated task-to-Slack figure) with login and signup (email/password or Google), and the authenticated web app.
- Tasks, subtasks, notes, comments, statuses, priorities, tags, kanban sorted by a field (no manual drag order), attachments with quotas, activity feed, explore, Slack integration.
- Reading is open to every member; permissions only unlock writes, so the UI must show clearly what the viewer can and cannot change.
- Light and dark themes following system with a user toggle.

## Capabilities and Constraints

- Stack: React 19, TypeScript, Vite, Tailwind v4, shadcn (base-nova, Base UI), TanStack Router/Query/Table/Form, Phosphor icons, GSAP for orchestrated motion.
- Backend errors carry a stable `code`; the UI never parses message text.
- Lists paginate at 25 per page. Due dates are plain dates.
- Product name: Pro-Goal. Logo: Phosphor `Target` icon plus wordmark.

## Brand Commitments

Name: Pro-Goal. Logo: Phosphor `Target` mark with wordmark. Voice: plain and direct. Short sentences, name the action and its consequence (Approve, Decline, Transfer ownership), no filler or exclamation marks.

## Evidence on Hand

Backend design in `../backend/project.md` and `../backend/docs/openapi.yml`. No testimonials, customers, metrics, or pricing exist; do not fabricate them.

## Product Principles

1. Fast to scan, fast to act: dense by default, keyboard-first, every action reachable in one or two moves.
2. Permissions are visible: the UI shows what a member can and cannot edit instead of failing on submit.
3. Start light, scale up: no setup ceremony; advanced control appears when needed.
4. Flat and calm: structure comes from hierarchy and whitespace, not stacked containers.

## Accessibility & Inclusion

WCAG 2.2 AA target, full keyboard operation, visible focus, reduced-motion respected for every animation.
