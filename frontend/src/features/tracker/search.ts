import type { TaskFilters } from "./api"

/** Task list state kept in the URL. Not stored anywhere else, so a refresh with a bare URL starts clean. */
export interface TaskSearch {
  status?: string
  priority?: string
  assignee?: string
  tag?: string
  q?: string
  after?: string
  before?: string
  overdue?: boolean
  subtasks?: boolean
  sort?: string
  page?: number
}

export const SORTS = [
  { value: "-number", label: "Newest first" },
  { value: "number", label: "Oldest first" },
  { value: "due_date", label: "Due date" },
  { value: "-priority", label: "Priority" },
  { value: "title", label: "Title" },
  { value: "-updated_at", label: "Recently updated" },
] as const

// The router JSON-parses numeric-looking values (?q=123), so numbers count as text too.
const str = (v: unknown, max = 100) => {
  const t = typeof v === "number" ? String(v) : v
  return typeof t === "string" && t.trim() ? t.trim().slice(0, max) : undefined
}
const date = (v: unknown) => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined)
const flag = (v: unknown) => (v === true || v === "true" ? true : undefined)

export function validateTaskSearch(s: Record<string, unknown>): TaskSearch {
  const sort = str(s.sort)
  const page = Number(s.page)
  return {
    status: str(s.status),
    priority: str(s.priority),
    assignee: str(s.assignee),
    tag: str(s.tag, 30),
    q: str(s.q),
    after: date(s.after),
    before: date(s.before),
    overdue: flag(s.overdue),
    subtasks: flag(s.subtasks),
    sort: SORTS.some((o) => o.value === sort) ? sort : undefined,
    page: Number.isInteger(page) && page > 1 && page <= 10_000 ? page : undefined,
  }
}

export const PAGE_SIZE = 25

export function toFilters(s: TaskSearch): TaskFilters {
  return {
    status: s.status,
    priority: s.priority,
    assignee: s.assignee,
    tag: s.tag,
    q: s.q,
    due_date_after: s.after,
    due_date_before: s.before,
    overdue: s.overdue,
    top_level: s.subtasks ? undefined : true,
    ordering: s.sort ?? "-number",
  }
}

export function activeFilterCount(s: TaskSearch): number {
  return [s.status, s.priority, s.assignee, s.tag, s.after, s.before, s.overdue, s.q].filter(Boolean).length
}

/** Same list with a different filter set; paging always restarts at the first page. */
export function withSearch(s: TaskSearch, patch: Partial<TaskSearch>): TaskSearch {
  return { ...s, ...patch, page: undefined }
}
