import { api, type Page } from "@/lib/api"

export interface PublicUser {
  id: string
  first_name: string
  avatar_url: string | null
}

/** Owners see the full name and email of members and requesters. */
export interface PrivateUser extends PublicUser {
  last_name?: string
  display_name?: string
  email?: string
}

export interface Transfer {
  id: string
  project: { id: string; name?: string }
  from_user: PublicUser
  to_user: PublicUser
  status: string
  expires_at: string
}

export interface Project {
  id: string
  name: string
  description: string
  task_key: string
  start_date: string | null
  end_date: string | null
  tags: string[]
  is_listed: boolean
  /** A shared, read-only demo project owned by the system. */
  is_demo: boolean
  is_archived: boolean
  archived_at: string | null
  deletion_scheduled_for: string | null
  owner: PublicUser
  member_count: number
  role: "owner" | "member"
  permissions: string[]
  created_at: string
  updated_at: string
  /** Owner only. */
  join_code?: string
  pending_transfer?: Transfer | null
}

export interface Member extends PrivateUser {
  is_owner: boolean
  joined_at: string
}

export type JoinStatus = "pending" | "approved" | "rejected" | "expired"

export interface JoinRequest {
  id: string
  status: JoinStatus
  user: PrivateUser
  created_at: string
  expires_at: string
  decided_at: string | null
}

export interface JoinSubmitted {
  id: string
  status: JoinStatus
  expires_at: string
  project: { name: string; description: string }
}

export interface Preset {
  name: string
  label: string
  description: string
  permissions: string[]
}

export interface Registry {
  groups: string[]
  permissions: { code: string; label: string; description: string; group: string }[]
  presets: Preset[]
  owner_only: string[]
}

/** Proof of identity for sensitive actions: a password, or a fresh Google ID token. */
export type Reauth = { password: string } | { id_token: string }

export interface ProjectInput {
  name: string
  description?: string
  task_key: string
  start_date?: string | null
  end_date?: string | null
  tags?: string[]
}

const P = (id: string) => `/api/projects/${id}`

export const projectsApi = {
  list: (offset = 0, limit = 25) => api.page<Project>(`/api/projects/?limit=${limit}&offset=${offset}`),
  get: (id: string) => api.get<Project>(`${P(id)}/`),
  create: (input: ProjectInput) => api.post<Project>("/api/projects/", input),
  update: (id: string, input: Partial<ProjectInput> & { is_listed?: boolean }) => api.patch<Project>(`${P(id)}/`, input),
  archive: (id: string) => api.post<Project>(`${P(id)}/archive/`, {}),
  unarchive: (id: string) => api.post<Project>(`${P(id)}/unarchive/`, {}),
  remove: (id: string, reauth: Reauth) => api.delete<Project>(`${P(id)}/`, reauth),
  restore: (id: string) => api.post<Project>(`${P(id)}/restore/`, {}),
  copy: (id: string, name?: string) => api.post<Project>(`${P(id)}/copy/`, name ? { name } : {}),
  regenerateCode: (id: string, reauth: Reauth) => api.post<Project>(`${P(id)}/join-code/regenerate/`, reauth),

  members: (id: string, offset = 0) => api.page<Member>(`${P(id)}/members/?limit=100&offset=${offset}`),
  removeMember: (id: string, userId: string) => api.delete<unknown>(`${P(id)}/members/${userId}/`, { reassign: {} }),
  leave: (id: string) => api.post<unknown>(`${P(id)}/leave/`, {}),

  join: (code: string) => api.post<JoinSubmitted>("/api/projects/join/", { code }),
  requests: (id: string, status: JoinStatus = "pending") => api.page<JoinRequest>(`${P(id)}/join-requests/?status=${status}&limit=100`),
  approve: (id: string, requestId: string, preset?: string) => api.post<JoinRequest>(`${P(id)}/join-requests/${requestId}/approve/`, preset ? { preset } : {}),
  reject: (id: string, requestId: string) => api.post<JoinRequest>(`${P(id)}/join-requests/${requestId}/reject/`, {}),

  startTransfer: (id: string, toUser: string, reauth: Reauth) => api.post<Transfer>(`${P(id)}/transfer/`, { to_user: toUser, ...reauth }),
  cancelTransfer: (id: string) => api.post<unknown>(`${P(id)}/transfer/cancel/`, {}),
  incomingTransfers: () => api.page<Transfer>("/api/transfers/"),
  acceptTransfer: (transferId: string) => api.post<unknown>(`/api/transfers/${transferId}/accept/`, {}),

  registry: () => api.get<Registry>("/api/permissions/"),
}

export type { Page }
