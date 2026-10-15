import { api } from "@/lib/api"
import type { PublicUser } from "@/features/projects/api"

export interface MemberGrants {
  user: PublicUser
  is_owner: boolean
  permissions: string[]
  /** Preset name when the grants match one exactly, else null. */
  preset: string | null
}

const url = (projectId: string, userId: string) => `/api/projects/${projectId}/members/${userId}/permissions/`

export const permissionsApi = {
  get: (projectId: string, userId: string) => api.get<MemberGrants>(url(projectId, userId)),
  replace: (projectId: string, userId: string, permissions: string[]) => api.put<MemberGrants>(url(projectId, userId), { permissions }),
}
