---
name: Pro-Goal
description: A calm, dense, keyboard-first project management interface in tinted neutrals with one Iris accent.
colors:
  iris: "oklch(0.52 0.2 295)"
  iris-dark: "oklch(0.72 0.15 295)"
  iris-wash: "oklch(0.955 0.03 295)"
  iris-wash-dark: "oklch(0.28 0.05 295)"
  paper: "oklch(0.99 0.003 295)"
  paper-surface: "oklch(0.975 0.004 295)"
  paper-muted: "oklch(0.96 0.005 295)"
  ink: "oklch(0.2 0.02 295)"
  ink-soft: "oklch(0.5 0.02 295)"
  hairline: "oklch(0.91 0.008 295)"
  night: "oklch(0.16 0.012 295)"
  night-surface: "oklch(0.19 0.014 295)"
  night-popover: "oklch(0.22 0.016 295)"
  night-ink: "oklch(0.96 0.005 295)"
  night-ink-soft: "oklch(0.7 0.02 295)"
  success: "oklch(0.55 0.14 155)"
  warning: "oklch(0.62 0.15 70)"
  info: "oklch(0.55 0.14 235)"
  danger: "oklch(0.52 0.21 27)"
typography:
  display:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  heading:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  meta:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.4
  caption:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 500
    lineHeight: 1.3
  mono:
    fontFamily: "Geist Mono Variable, ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  sm: "4.8px"
  md: "6.4px"
  lg: "8px"
  xl: "11.2px"
spacing:
  control-height: "32px"
  row-height: "36px"
  gap-sm: "8px"
  gap-md: "16px"
  section: "48px"
components:
  button-primary:
    backgroundColor: "{colors.iris}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 10px"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 10px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 10px"
  button-ghost:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 10px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 10px"
  table-row:
    height: "36px"
    textColor: "{colors.ink}"
---

# Design System: Pro-Goal

## Overview

**Creative North Star: "The Quiet Instrument"**

Pro-Goal is a tool people use all day, so the interface recedes and the work leads. Surfaces are flat and tinted a hair toward Iris; structure comes from hairline dividers, tone and whitespace, never from stacked boxes. Density is deliberate: 36px rows, 32px controls, 14px body text. Every action is reachable by keyboard and carries an icon.

The one accent, Iris, is spent only where attention should go: the primary action, selection, focus and links. Status colors (green, yellow, blue, red) are reserved for meaning and always paired with an icon. Motion is a supporting actor: short, exponential ease-out, and fully off under reduced motion.

**Key Characteristics:**
- Flat, tinted-neutral surfaces separated by hairlines, one container level at most.
- One accent (Iris, hue 295), light and dark themes derived from the same hue.
- Button plus icon for every action; icon-only buttons always have a label and tooltip.
- Status and priority are icon plus text, never filled chips.
- Tabular numerals in all data; Geist for text, Geist Mono for ids and code.

## Colors

A tinted-neutral palette with a single blue-violet accent. Neutrals carry a trace of Iris hue so the accent never looks pasted on.

### Primary
- **Iris** (oklch(0.52 0.2 295), dark theme oklch(0.72 0.15 295)): Primary buttons, selected state, links, focus ring, logo mark.
- **Iris Wash** (oklch(0.955 0.03 295), dark oklch(0.28 0.05 295)): Subtle selected or hover backgrounds, drop-target highlight.

### Neutral
- **Paper** (oklch(0.99 0.003 295)): Page background in light theme.
- **Paper Surface** (oklch(0.975 0.004 295)): Sidebar, table toolbar, specimen headers.
- **Paper Muted** (oklch(0.96 0.005 295)): Hover rows, secondary buttons, code chips.
- **Ink** (oklch(0.2 0.02 295)): Body text. **Ink Soft** (oklch(0.5 0.02 295)): metadata and placeholders.
- **Hairline** (oklch(0.91 0.008 295)): All borders and dividers.
- **Night** (oklch(0.16 0.012 295)) and **Night Surface** (oklch(0.19 0.014 295)): dark theme page and sidebar; **Night Popover** (oklch(0.22 0.016 295)) for floating layers.

### Status
- **Success** (oklch(0.55 0.14 155)), **Warning** (oklch(0.62 0.15 70)), **Info** (oklch(0.55 0.14 235)), **Danger** (oklch(0.52 0.21 27)); brighter variants in dark theme. Used only for state, always with an icon. For text in light theme use **Success Text** (oklch(0.45 0.13 155)) and **Warning Text** (oklch(0.48 0.12 70)); the base colors are for icons and fills.

### Named Rules
**The One Voice Rule.** Iris appears on at most one primary action per view plus selection, focus and links. If everything is accent, nothing is.

**The Icon Beside Color Rule.** Color never carries meaning alone; every status color ships with its icon and text.

## Typography

**Display and Body Font:** Geist Variable (with system sans fallback)
**Mono Font:** Geist Mono Variable, for ids (PM-142), codes and the note editor.

**Character:** Neutral, precise and slightly technical; weight and size do the hierarchy, not decoration.

### Hierarchy
- **Display** (600, 2.25rem, 1.1): Rare; empty-state and marketing headlines.
- **Title** (600, 1.25rem, 1.3): Page and section titles.
- **Heading** (500, 1rem, 1.4): Panel and group headings.
- **Body** (400, 0.875rem, 1.5): Everything else; prose capped near 65ch.
- **Meta** (400, 0.75rem, 1.4, muted): Timestamps, helper text, counts.
- **Caption** (500, 0.6875rem, 1.3): Swatch labels and tiny tags only; never body copy.

### Named Rules
**The Tabular Rule.** Any column or counter of numbers uses tabular numerals so it never jitters.

## Layout

Dense, left-aligned, content-first. App shell is a 14rem sidebar plus a 48px topbar over a scrolling content region. Rows are 36px, controls 32px, gaps on an 8px rhythm, 48px between page sections with more space above a heading than below. Lists paginate at 25. Specimen and content width is capped near 80rem; prose near 65ch. On narrow screens the sidebar becomes a drawer and tables scroll horizontally inside their own container.

## Elevation & Depth

Flat by default. Depth is tone and hairlines, not shadow. Only floating layers (menus, popovers, dialogs, toasts) lift.

### Shadow Vocabulary
- **Pop** (`0 1px 2px oklch(0.2 0.02 295 / 0.06), 0 8px 24px -4px oklch(0.2 0.02 295 / 0.12)`; dark: `0 0 0 1px oklch(1 0 0 / 8%), 0 12px 32px -6px oklch(0 0 0 / 0.6)`): Popovers, dropdowns, dialogs, toasts.

### Named Rules
**The Flat-By-Default Rule.** Nothing at rest has a shadow. If it sits in the page, it is separated by a hairline.

**The One Container Rule.** A bordered container never contains another bordered container. Use dividers inside.

## Shapes

Small, even radii: 6.4px on controls, 8px on grouped containers, 11px on dialogs. Avatars are circles. Borders are 1px hairlines; focus is a 2px Iris outline with 2px offset. No decorative clipping or gradients.

## Components

### Buttons
- **Shape:** gently rounded (6.4px), 32px tall, 10px horizontal padding, icon gap 6px.
- **Primary:** Iris fill, paper text, a faint inset top highlight; hover darkens slightly.
- **Secondary / Outline / Ghost:** tonal or hairline, no accent. Approve-style actions in a list are outline, dismiss actions are ghost.
- **Destructive:** a tinted red wash for triggers (Delete project…), a solid red fill (`solid-destructive`) only for the final confirm inside a dialog.
- **Icon-only:** 32px square (24px `xs` for dense chips), requires `label`, which becomes aria-label and tooltip. On coarse pointers controls grow to 44px.
- **Loading:** spinner replaces the icon, button disabled and aria-busy.

### Inputs / Fields
- **Style:** 32px, hairline border, transparent fill, 6.4px radius.
- **Focus:** Iris ring. **Error:** destructive border and message replaces the hint. Label above, hint below.

### Navigation
Sidebar items are 32px, icon plus label, active item gets a tonal background, bold icon fill and `aria-current`. Breadcrumb in the topbar, Cmd+K search, line-style tabs.

### Data table
36px rows, sortable text-button headers, selection checkbox column, bulk bar replaces the count when rows are selected, row actions in a dropdown. Status and priority are icon plus label.

### Board
Open lanes divided by 1px hairlines, one row per task, no card around a card. Sorted by a field, never dragged by hand.

### Permissions and access
Permissions are visible where the work happens. On a task row, editable cells show a pencil on hover or focus; locked cells show a lock, and tapping, clicking or pressing Enter on one opens a popover with the reason and who to ask (never hover-only, so it works on touch). Members are shown as a who-can-change-what matrix (check or dash per permission) with a screen-reader caption. The permission editor offers Viewer, Member and Manager presets with a one-line description, switches to a Custom badge when edited, shows a live "Can edit N of 9 permissions" count, and disables any permission the actor does not hold, with the reason beside it (the subset rule). Every permission state names who can change it, never just "disabled".

### Blueprint sheet (landing and auth)
The public surfaces are a drawing sheet in the same Iris system. Structure is square (no radius): a double border with centering ticks, zone letters A to D across the top and numbers 1 to 4 down the side, a sticky strip at the bottom with the sheet number (`SHEET PG-01`, `AUTH-01`) and revision. Ground is a tinted drawing paper with a 24px hairline grid at 7% (light: pale lavender, dark: deep blue-violet, oklch(0.2 0.05 275)); linework is cyanotype blue (hue 280). The **title block** is a ruled box on a lighter or darker paper tone (`--bp-paper`) that holds the sign-up and auth forms; controls inside keep the app's 6.4px radius. Figures are captioned in Geist Mono (`FIG. 1`, `DETAIL A`) and use real dimension lines (arrowheads, label centered, spanning what they measure). The revision table is the one authored motion moment: approval boxes are signed by default and drawn in when scrolled to. Auth screens carry one `h1` (the title block heading), one filled primary and flat notice rows.

### Dialogs and destructive flows
Centered dialogs only; there are no side sheets. Friction scales with risk: Join project is a code field; Transfer ownership shows the person affected and asks for a password; Delete project needs the typed project name plus a password, states what is lost and the 7-day recovery window, and uses a solid red confirm that stays disabled until both fields are filled. Cancel is always present and focused by default on destructive confirms. The scrim is a plain 30% black with no blur.

### Join and approval
Joining is a 6-character code in six slots, Enter submits, and every failure has its own plain sentence (wrong length, no such project, expired, already a member). The pending state replaces the form. Owners review requests one row at a time (avatar, name, email, time, role select, Decline ghost, Approve outline). Roles above what the approver holds are shown with a lock and cannot be picked. Every approval or decline raises a toast with Undo that lasts 9 seconds.

### App shell and project pages
Flat frame: a 14rem sidebar in the Paper Surface tone, a 48px topbar with breadcrumb, theme toggle and account menu, content to `max-w-5xl`. Page header is one h1, one line of context and the actions; the single primary action is the only filled Iris button. Lists divide with hairlines (`divide-y border-y`), rows are 36px, a row is a link or holds one. Page-level state (archived, scheduled for deletion, ownership offer) is a flat banner: icon, one sentence, one action, a hairline below. Loading is a skeleton of the real rows, never a spinner in the middle of content. A list that loads only the first 100 says "Showing the first N of M".

### Tasks
Status and priority come from the project's own lists: the icon comes from the status group (To do, In progress, Done) or the priority's rank position, the text from its name; never a filled chip. Task keys are Geist Mono. Overdue is icon plus the word Overdue plus the date, from the server's date. A task row shows key, title with context, status, priority, people, due date; absent data is left out, not written. In the list, status and priority change in place through quiet selects, and `j` and `k` move between rows. A task opens as a full page of labelled property rows (`PropertyRow`); a property the viewer may not change is disabled and says which permission it needs, in text beside the value. Subtasks and comments sit under the properties.

### Board lanes
Open lanes, one row per card, a count in each lane header, an Iris wash on the lane under the pointer. Cards sort by a chosen field; there is no manual order. The grip is a real button (drag with pointer or keyboard) and every card has a Move button with the same targets. A move shows at once, rolls back on failure, and reports success with an Undo toast. Locked boards say why in one line above the lanes.

### Notes and comments
Notes are read as sanitized markdown at reading width and edited in a Write / Preview editor with a small toolbar. Saves send the version; a conflict never overwrites: the writer keeps their text and chooses between copying it, discarding it for the latest version, or replacing the other version knowingly. Unsaved drafts persist on the device and survive reloads; Cancel on a dirty note asks first. Comments are a flat thread: author, time, edited marker, a tombstone for deleted ones, edit and delete for your own, moderators for any. Mentions are typed as `@Name` and travel as tokens.

### Permission editor and matrix
A member's permissions are a full page, never a sheet: a preset select, then the registry's groups as flat checkbox lists, each row a label and one line of what it allows, a count per group ("3 of 6"). A row the viewer does not hold is disabled and says so in text; a changed row says "Will add" or "Will remove" with a plus or minus icon. A sticky footer states the diff ("Adds 2, removes 1") with Discard and Save; leaving with edits asks first. The owner and archived projects are read-only and a banner says why. On Members, "Who can change what" is a read-only table: members as columns, groups as rows that open to single permissions, cells are icon plus text (All, n of m, None; Yes, No). It scrolls inside its own labelled region and never relies on colour. Locked controls elsewhere read "Needs “Change due date”. Ask Olive or a member who manages permissions." from one hook.

### Account security
A full page of flat sections, each a short heading and sentence on the left and the content on the right. Devices list the device, address, last activity and a Sign out button, with "This device" as icon plus text and no button. The security log is a filterable, paged list, one icon and plain label per event; events that need a second look carry a warning icon and words, never colour alone. A locked login says how long to wait and links to password reset.

### Integrations
One flat row per provider: logo, name with status as icon plus text (Active, Needs attention, Disconnected, Not connected), a line of who connected it and when, then the actions (Delivery log, Disconnect, Add to Slack). A provider that stopped sending gets a banner that says why and offers Reconnect. Channels are a divided list: channel, public or private as icon plus text, an event summary; public channels carry a warning that anyone in the workspace can read the posts. Adding or editing a channel is a dialog with the event catalog as grouped checkboxes (Tasks, Comments, Members, Project). The delivery log is a full page: event, outcome (Delivered, Retrying with the time, Failed), attempt n of 6, the server's answer, and Send again on failed rows. Personal choices live on the account page: Slack link state, and a table of the five personal events with an Email and a Slack message switch each, saved on change and rolled back on failure.

### Activity and Explore
Activity is a divided list: avatar, one sentence with the person's name in medium weight ("Sam created PMS-4 Audit probe"), field changes underneath as `Field: old -> new` in muted small text, and the time on the right. A sentence links to the thing it names when the entry carries it. Members without the view permission see only their own actions and the page says so once, in words. Explore rows are not cards: name, two lines of description, owner, size, dates and tags in one muted line, and one state-aware action on the right (Ask to join, a sentence while the request is pending or cooling down, a link when already a member).

### Account forms
Each account setting is a flat section with its own small form: Profile (picture, names), Password (current plus new with live rules), Email (a re-authentication dialog that sends a link to the new address), and Delete account last, as the only destructive-toned button, behind a typed confirmation. A pending deletion becomes a banner at the top of the page with one button to keep the account.

### Loading and not found
Both are the same frame: the mark, "Pro-Goal" or the heading, one sentence, one or two buttons. The loading screen is for a refresh, a reload and the first step into the app; it fades in after a short delay so quick loads never flash it, becomes a "taking longer than usual" message with Try again after eight seconds, and holds still under reduced motion. Moving between pages inside the app uses skeletons, not this screen. Not found shows the address that was asked for, a Take me home button (home sends a signed-in person on to their projects) and Go back.

### Feedback
Inline banners and toasts share one icon language: Info blue, Success green, Warning yellow, Danger red, filled icons on a neutral surface. Empty states always offer the next action.

## Do's and Don'ts

### Do:
- **Do** pair every action with an icon, and every icon-only button with a label.
- **Do** separate with hairlines and whitespace; keep to one container level.
- **Do** use `--ctl-h` (32px) and `--row-h` (36px) for control and row heights.
- **Do** honor reduced motion: GSAP reveals and flips no-op, CSS transitions collapse.
- **Do** keep status as icon plus text; Todo and Backlog use open circles, Done is green, In progress is the half circle.
- **Do** make every undoable action undoable from a toast, and give errors a specific sentence with the next step.
- **Do** give tables a caption and `scope` on headers; give every icon-only button a label.

### Don't:
- **Don't** nest cards, or build pages from same-size icon-heading-text cards.
- **Don't** use a kicker or eyebrow above headings, or numbered section labels.
- **Don't** use gradient text, glass decoration, side-stripe borders or hard offset shadows.
- **Don't** spend Iris on more than the primary action, selection, focus and links.
- **Don't** fill a list row with permanent Unassigned or No due date text; absence is quiet.
- **Don't** use a side sheet for creating a task; creation is a centered dialog, details are a full page.
- **Don't** make a destructive action lighter than a reversible one: Delete project asks for more than Transfer ownership, never less.
- **Don't** explain a lock in a hover-only tooltip; the reason must open on tap and focus.
- **Don't** show a primary Iris button on every row of a list; per-row actions are outline or ghost.
- **Don't** use backdrop blur on scrims, headers or any surface.
- **Don't** use the blueprint grid, sheet border or title block inside the app; they belong to the landing and auth surfaces only.
- **Don't** put an unlabelled decorative figure on the landing: every figure is real product UI with a caption and no invented numbers.
