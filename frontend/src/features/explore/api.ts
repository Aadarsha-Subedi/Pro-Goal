import { api } from "@/lib/api"
import type { PublicUser } from "@/features/projects/api"

export type RequestState = "none" | "pending" | "cooldown"

export interface ExploreProject {
  id: string
  name: string
  description: string
  tags: string[]
  start_date: string | null
  end_date: string | null
  owner: PublicUser
  member_count: number
  /** Shared, read-only demo: joining needs no approval. */
  is_demo: boolean
  listed_at: string
  my_request: { state: RequestState; cooldown_until: string | null }
}

/** A demo project is joined at once; any other project waits for the owner. */
export type JoinResult = { status: "joined"; project: { id: string; name: string } } | { status: "pending" | "approved" | "rejected" | "expired" }

export interface ExploreFilters {
  q?: string
  tag?: string
  after?: string
  before?: string
  page?: number
}

export interface TagSuggestion {
  name: string
  projects: number
}

export const EXPLORE_PAGE = 20

export function exploreQuery(f: ExploreFilters): string {
  const p = new URLSearchParams({ limit: String(EXPLORE_PAGE), offset: String(((f.page ?? 1) - 1) * EXPLORE_PAGE) })
  if (f.q) p.set("q", f.q)
  if (f.tag) p.set("tag", f.tag)
  if (f.after) p.set("starts_after", f.after)
  if (f.before) p.set("ends_before", f.before)
  return p.toString()
}

export const exploreApi = {
  list: (f: ExploreFilters) => api.page<ExploreProject>(`/api/explore/?${exploreQuery(f)}`),
  tags: () => api.page<TagSuggestion>("/api/explore/tags/"),
  requestJoin: (projectId: string) => api.post<JoinResult>(`/api/explore/${projectId}/join-request/`, {}),
}
