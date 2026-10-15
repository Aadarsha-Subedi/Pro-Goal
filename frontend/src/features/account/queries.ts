import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { accountApi, type SecurityEventType } from "./api"

export const accountKeys = {
  sessions: ["sessions"] as const,
  events: (type: SecurityEventType | undefined, page: number) => ["security-events", type ?? "all", page] as const,
}

export const useSessions = () => useQuery({ queryKey: accountKeys.sessions, queryFn: () => accountApi.sessions() })
export const useSecurityEvents = (type: SecurityEventType | undefined, page: number) =>
  useQuery({ queryKey: accountKeys.events(type, page), queryFn: () => accountApi.events(type, page), placeholderData: keepPreviousData })

export function useRevokeSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => accountApi.revokeSession(id),
    onSuccess: async () => {
      await Promise.all([qc.invalidateQueries({ queryKey: accountKeys.sessions }), qc.invalidateQueries({ queryKey: ["security-events"] })])
    },
  })
}
