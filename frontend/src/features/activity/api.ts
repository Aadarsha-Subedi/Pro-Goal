import { api } from "@/lib/api"

export interface ActivityEntry {
  id: string
  actor: { id: string | null; first_name: string; avatar_url: string | null }
  action: string
  entity_type: string
  entity_id: string | null
  changes: Record<string, unknown>
  created_at: string
}

export interface ActivityFilters {
  actor?: string
  entity?: string
  after?: string
  before?: string
  page?: number
}

export const ACTIVITY_PAGE = 25

/** Plain dates from the filter inputs become the start and end of that day, in the viewer's own time. */
const startOf = (d: string) => new Date(`${d}T00:00:00`).toISOString()
const endOf = (d: string) => new Date(`${d}T23:59:59.999`).toISOString()

export function activityQuery(f: ActivityFilters): string {
  const p = new URLSearchParams({ limit: String(ACTIVITY_PAGE), offset: String(((f.page ?? 1) - 1) * ACTIVITY_PAGE) })
  if (f.actor) p.set("actor", f.actor)
  if (f.entity) p.set("entity_type", f.entity)
  if (f.after) p.set("created_after", startOf(f.after))
  if (f.before) p.set("created_before", endOf(f.before))
  return p.toString()
}

export const activityApi = {
  list: (projectId: string, f: ActivityFilters) => api.page<ActivityEntry>(`/api/projects/${projectId}/activity/?${activityQuery(f)}`),
}
