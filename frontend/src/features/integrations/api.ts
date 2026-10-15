import { api } from "@/lib/api"
import type { PublicUser } from "@/features/projects/api"

export type IntegrationStatus = "active" | "needs_attention" | "disconnected"
export type DeliveryStatus = "pending" | "success" | "failed"

export interface Integration {
  id: string
  provider: string
  status: IntegrationStatus
  external_workspace_id: string
  installed_by: PublicUser | null
  consecutive_failures: number
  paused_until: string | null
  created_at: string
  updated_at: string
}

export interface Delivery {
  id: string
  direction: "in" | "out"
  event_type: string
  status: DeliveryStatus
  attempt: number
  response_code: number | null
  next_retry_at: string | null
  error: string
  created_at: string
  updated_at: string
}

export interface SlackChannel {
  id: string
  name: string
  is_private: boolean
  is_member: boolean
}

export interface Mapping {
  id: string
  channel_id: string
  channel_name: string
  is_public: boolean
  warn_public: boolean
  enabled_events: string[]
  created_at: string
}

export interface Preference {
  event_type: string
  slack_dm: boolean
  email: boolean
}

export interface SlackLink {
  url: string
  linked_workspaces: string[]
}

export const DELIVERY_PAGE = 25

const P = (id: string) => `/api/projects/${id}/integrations`

export const integrationsApi = {
  list: (projectId: string) => api.page<Integration>(`${P(projectId)}/`),
  disconnect: (projectId: string, id: string) => api.delete<unknown>(`${P(projectId)}/${id}/`),
  deliveries: (projectId: string, id: string, status: DeliveryStatus | undefined, page: number) =>
    api.page<Delivery>(`${P(projectId)}/${id}/deliveries/?limit=${DELIVERY_PAGE}&offset=${(page - 1) * DELIVERY_PAGE}${status ? `&status=${status}` : ""}`),
  replay: (projectId: string, id: string, deliveryId: string) => api.post<Delivery>(`${P(projectId)}/${id}/deliveries/${deliveryId}/replay/`, {}),
}

export const slackApi = {
  installUrl: (projectId: string) => api.get<{ url: string }>(`${P(projectId)}/slack/install/`),
  channels: (projectId: string) => api.page<SlackChannel>(`${P(projectId)}/slack/channels/`),
  mappings: (projectId: string) => api.page<Mapping>(`${P(projectId)}/slack/mappings/`),
  createMapping: (projectId: string, channelId: string, events: string[]) => api.post<Mapping>(`${P(projectId)}/slack/mappings/`, { channel_id: channelId, enabled_events: events }),
  updateMapping: (projectId: string, id: string, events: string[]) => api.patch<Mapping>(`${P(projectId)}/slack/mappings/${id}/`, { enabled_events: events }),
  deleteMapping: (projectId: string, id: string) => api.delete<unknown>(`${P(projectId)}/slack/mappings/${id}/`),

  link: () => api.get<SlackLink>("/api/me/integrations/slack/link/"),
  unlink: () => api.delete<unknown>("/api/me/integrations/slack/link/"),
  preferences: () => api.page<Preference>("/api/me/notification-preferences/"),
  savePreferences: (changes: Record<string, Partial<Pick<Preference, "slack_dm" | "email">>>) => api.put<{ items: Preference[] }>("/api/me/notification-preferences/", { preferences: changes }),
}
