import { api, type Page } from "@/lib/api"
import type { PublicUser } from "@/features/projects/api"

export type StatusCategory = "todo" | "in_progress" | "done"

export interface Status {
  id: string
  name: string
  category: StatusCategory
  position: number
  is_default: boolean
}

export interface Priority {
  id: string
  name: string
  /** 1 is the lowest. */
  rank: number
  position: number
  is_default: boolean
}

export interface Task {
  id: string
  number: number
  key: string
  project: { id: string; name: string; task_key: string }
  title: string
  status: { id: string; name: string; category: StatusCategory }
  priority: { id: string; name: string; rank: number }
  start_date: string | null
  due_date: string | null
  is_overdue: boolean
  parent_number: number | null
  subtasks: { total: number; done: number }
  assignees: PublicUser[]
  tags: string[]
  created_by: PublicUser
  created_at: string
  updated_at: string
  deleted_at: string | null
  deletion_scheduled_for: string | null
  /** Only on a single task, not in lists. */
  description?: string
}

export interface TaskFilters {
  status?: string
  priority?: string
  assignee?: string
  tag?: string
  q?: string
  due_date_after?: string
  due_date_before?: string
  overdue?: boolean
  top_level?: boolean
  ordering?: string
}

export interface TaskCreate {
  title: string
  status?: string
  priority?: string
  description?: string
  start_date?: string | null
  due_date?: string | null
  assignees?: string[]
  tags?: string[]
}

export type TaskPatch = Partial<Omit<TaskCreate, "status" | "priority">> & {
  status?: string
  priority?: string
  /** Task number of the new parent, or null to promote to a top-level task. */
  parent?: number | null
}

export interface Note {
  id: string
  title: string
  version: number
  tags: string[]
  author: PublicUser
  created_at: string
  updated_at: string
  /** Only on a single note, not in lists. */
  body?: string
}

export interface NoteRevision {
  id: string
  version: number
  title: string
  body: string
  edited_by: PublicUser
  created_at: string
}

export interface Comment {
  id: string
  author: PublicUser
  /** Null once deleted. */
  body: string | null
  is_deleted: boolean
  edited_at: string | null
  deleted_at: string | null
  created_at: string
}

export type BoardGroup = "status" | "priority" | "assignee" | "tag"
export type BoardSort = "due_date" | "priority" | "created_at" | "updated_at" | "number" | "title"

export interface BoardPreference {
  group_by: BoardGroup
  sort_by: BoardSort
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const out = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") out.set(k, String(v))
  const s = out.toString()
  return s ? `?${s}` : ""
}

export const BOARD_CAP = 500

const P = (id: string) => `/api/projects/${id}`

export const trackerApi = {
  tasks: (projectId: string, filters: TaskFilters, offset = 0, limit = 25) => api.page<Task>(`${P(projectId)}/tasks/${qs({ ...filters, limit, offset })}`),
  /** The board needs every card: it pages through until the whole project is loaded (capped). */
  async allTasks(projectId: string, filters: TaskFilters): Promise<Page<Task>> {
    const first = await api.page<Task>(`${P(projectId)}/tasks/${qs({ ...filters, limit: 100, offset: 0 })}`)
    const offsets: number[] = []
    for (let o = first.items.length; o < Math.min(first.meta.count, BOARD_CAP); o += 100) offsets.push(o)
    const rest = await Promise.all(offsets.map((offset) => api.page<Task>(`${P(projectId)}/tasks/${qs({ ...filters, limit: 100, offset })}`)))
    // `meta.count` stays the project's real total, so the board can say when it shows fewer.
    return { items: first.items.concat(...rest.map((r) => r.items)), meta: first.meta }
  },
  myTasks: (filters: TaskFilters, offset = 0, limit = 50) => api.page<Task>(`/api/me/tasks/${qs({ ...filters, limit, offset })}`),
  task: (projectId: string, number: number) => api.get<Task>(`${P(projectId)}/tasks/${number}/`),
  createTask: (projectId: string, input: TaskCreate) => api.post<Task>(`${P(projectId)}/tasks/`, input),
  updateTask: (projectId: string, number: number, patch: TaskPatch) => api.patch<Task>(`${P(projectId)}/tasks/${number}/`, patch),
  deleteTask: (projectId: string, number: number) => api.delete<Task>(`${P(projectId)}/tasks/${number}/`),
  restoreTask: (projectId: string, number: number) => api.post<Task>(`${P(projectId)}/tasks/${number}/restore/`, {}),
  subtasks: (projectId: string, number: number) => api.page<Task>(`${P(projectId)}/tasks/${number}/subtasks/?limit=100`),
  createSubtask: (projectId: string, number: number, input: TaskCreate) => api.post<Task>(`${P(projectId)}/tasks/${number}/subtasks/`, input),

  statuses: (projectId: string) => api.page<Status>(`${P(projectId)}/statuses/?limit=100`),
  createStatus: (projectId: string, input: { name: string; category: StatusCategory; is_default?: boolean }) => api.post<Status>(`${P(projectId)}/statuses/`, input),
  updateStatus: (projectId: string, id: string, patch: Partial<Pick<Status, "name" | "category" | "position" | "is_default">>) => api.patch<Status>(`${P(projectId)}/statuses/${id}/`, patch),
  deleteStatus: (projectId: string, id: string, moveTo?: string | null) => api.delete<unknown>(`${P(projectId)}/statuses/${id}/`, { move_to: moveTo ?? null }),
  priorities: (projectId: string) => api.page<Priority>(`${P(projectId)}/priorities/?limit=100`),
  createPriority: (projectId: string, input: { name: string; is_default?: boolean }) => api.post<Priority>(`${P(projectId)}/priorities/`, input),
  updatePriority: (projectId: string, id: string, patch: Partial<Pick<Priority, "name" | "position" | "is_default">>) => api.patch<Priority>(`${P(projectId)}/priorities/${id}/`, patch),
  deletePriority: (projectId: string, id: string, moveTo?: string | null) => api.delete<unknown>(`${P(projectId)}/priorities/${id}/`, { move_to: moveTo ?? null }),

  notes: (projectId: string, params: { q?: string; tag?: string }, offset = 0, limit = 25) => api.page<Note>(`${P(projectId)}/notes/${qs({ ...params, limit, offset })}`),
  note: (projectId: string, id: string) => api.get<Note>(`${P(projectId)}/notes/${id}/`),
  createNote: (projectId: string, input: { title: string; body?: string; tags?: string[] }) => api.post<Note>(`${P(projectId)}/notes/`, input),
  updateNote: (projectId: string, id: string, input: { version: number; title?: string; body?: string; tags?: string[] }) => api.patch<Note>(`${P(projectId)}/notes/${id}/`, input),
  deleteNote: (projectId: string, id: string) => api.delete<unknown>(`${P(projectId)}/notes/${id}/`),
  revisions: (projectId: string, id: string) => api.page<NoteRevision>(`${P(projectId)}/notes/${id}/revisions/?limit=100`),
  taskNotes: (projectId: string, number: number) => api.page<Note>(`${P(projectId)}/tasks/${number}/notes/?limit=100`),
  linkNote: (projectId: string, number: number, noteId: string) => api.put<Note>(`${P(projectId)}/tasks/${number}/notes/${noteId}/`, {}),
  unlinkNote: (projectId: string, number: number, noteId: string) => api.delete<unknown>(`${P(projectId)}/tasks/${number}/notes/${noteId}/`),

  comments: (projectId: string, number: number) => api.page<Comment>(`${P(projectId)}/tasks/${number}/comments/?limit=100`),
  createComment: (projectId: string, number: number, body: string) => api.post<Comment>(`${P(projectId)}/tasks/${number}/comments/`, { body }),
  updateComment: (projectId: string, number: number, id: string, body: string) => api.patch<Comment>(`${P(projectId)}/tasks/${number}/comments/${id}/`, { body }),
  deleteComment: (projectId: string, number: number, id: string) => api.delete<Comment>(`${P(projectId)}/tasks/${number}/comments/${id}/`),

  preference: (projectId: string) => api.get<BoardPreference>(`${P(projectId)}/kanban-preference/`),
  savePreference: (projectId: string, pref: BoardPreference) => api.put<BoardPreference>(`${P(projectId)}/kanban-preference/`, pref),
}

export type { Page }
