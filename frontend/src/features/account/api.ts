import type { Me } from "@/features/auth/api"
import { api } from "@/lib/api"

export interface UserSession {
  id: string
  device_name: string
  ip: string | null
  user_agent: string
  created_at: string
  last_seen_at: string
  remember_me: boolean
  is_current: boolean
}

export type SecurityEventType =
  | "login_success"
  | "login_failure"
  | "login_locked"
  | "email_changed"
  | "password_changed"
  | "password_reset"
  | "session_revoked"
  | "social_account_linked"
  | "account_deletion_requested"
  | "account_deletion_cancelled"

export interface SecurityEvent {
  id: string
  event_type: SecurityEventType
  ip: string | null
  user_agent: string
  device_name: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface ProfileInput {
  first_name: string
  last_name: string
  display_name: string
}

export type Reauth = { password: string } | { id_token: string }

export const PAGE_SIZE = 25

export const accountApi = {
  updateProfile: (input: ProfileInput) => api.patch<Me>("/api/me/", input),
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return api.post<Me>("/api/me/avatar/", form)
  },
  removeAvatar: () => api.delete<Me>("/api/me/avatar/"),
  changePassword: (current: string, next: string) => api.post<unknown>("/api/auth/password/change/", { ...(current ? { current_password: current } : {}), new_password: next }),
  requestEmailChange: (newEmail: string, reauth: Reauth) => api.post<unknown>("/api/me/email/", { new_email: newEmail, ...reauth }),
  confirmEmailChange: (token: string) => api.post<unknown>("/api/auth/email-change/confirm/", { token }),
  deleteAccount: () => api.post<Me>("/api/me/delete/", {}),
  cancelDeletion: () => api.post<Me>("/api/me/delete/cancel/", {}),
  sessions: () => api.page<UserSession>("/api/me/sessions/"),
  revokeSession: (id: string) => api.delete<unknown>(`/api/me/sessions/${id}/`),
  events: (eventType: SecurityEventType | undefined, page: number) =>
    api.page<SecurityEvent>(`/api/me/security-events/?limit=${PAGE_SIZE}&offset=${(page - 1) * PAGE_SIZE}${eventType ? `&event_type=${eventType}` : ""}`),
}
