import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { integrationsApi, slackApi, type DeliveryStatus, type Preference } from "./api"

export const ik = {
  list: (pid: string) => ["integrations", pid] as const,
  deliveries: (pid: string, id: string, status: DeliveryStatus | undefined, page: number) => ["deliveries", pid, id, status ?? "all", page] as const,
  channels: (pid: string) => ["slack-channels", pid] as const,
  mappings: (pid: string) => ["slack-mappings", pid] as const,
  link: ["slack-link"] as const,
  prefs: ["notification-prefs"] as const,
}

export const useIntegrations = (pid: string) => useQuery({ queryKey: ik.list(pid), queryFn: () => integrationsApi.list(pid), retry: false })
export const useDeliveries = (pid: string, id: string, status: DeliveryStatus | undefined, page: number) =>
  useQuery({ queryKey: ik.deliveries(pid, id, status, page), queryFn: () => integrationsApi.deliveries(pid, id, status, page), placeholderData: keepPreviousData, retry: false })
export const useMappings = (pid: string, enabled: boolean) => useQuery({ queryKey: ik.mappings(pid), queryFn: () => slackApi.mappings(pid), enabled, retry: false })
export const useChannels = (pid: string, enabled: boolean) => useQuery({ queryKey: ik.channels(pid), queryFn: () => slackApi.channels(pid), enabled, retry: false, staleTime: 0 })
export const useSlackLink = () => useQuery({ queryKey: ik.link, queryFn: () => slackApi.link(), retry: false })
export const usePreferences = () => useQuery({ queryKey: ik.prefs, queryFn: () => slackApi.preferences() })

export function useIntegrationMutations(pid: string) {
  const qc = useQueryClient()
  const refresh = () => Promise.all([qc.invalidateQueries({ queryKey: ik.list(pid) }), qc.invalidateQueries({ queryKey: ik.mappings(pid) })])
  return {
    disconnect: useMutation({ mutationFn: (id: string) => integrationsApi.disconnect(pid, id), onSuccess: refresh }),
    replay: useMutation({
      mutationFn: ({ id, deliveryId }: { id: string; deliveryId: string }) => integrationsApi.replay(pid, id, deliveryId),
      onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: ["deliveries", pid] }), qc.invalidateQueries({ queryKey: ik.list(pid) })]),
    }),
    createMapping: useMutation({ mutationFn: ({ channelId, events }: { channelId: string; events: string[] }) => slackApi.createMapping(pid, channelId, events), onSuccess: () => qc.invalidateQueries({ queryKey: ik.mappings(pid) }) }),
    updateMapping: useMutation({ mutationFn: ({ id, events }: { id: string; events: string[] }) => slackApi.updateMapping(pid, id, events), onSuccess: () => qc.invalidateQueries({ queryKey: ik.mappings(pid) }) }),
    deleteMapping: useMutation({ mutationFn: (id: string) => slackApi.deleteMapping(pid, id), onSuccess: () => qc.invalidateQueries({ queryKey: ik.mappings(pid) }) }),
  }
}

export function useUnlinkSlack() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: () => slackApi.unlink(), onSuccess: () => qc.invalidateQueries({ queryKey: ik.link }) })
}

/** Optimistic: the switch moves at once and snaps back if the server refuses. */
export function useSavePreference() {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ["save-pref"],
    mutationFn: ({ event, field, value }: { event: string; field: "slack_dm" | "email"; value: boolean }) => slackApi.savePreferences({ [event]: { [field]: value } }),
    onMutate: async ({ event, field, value }) => {
      await qc.cancelQueries({ queryKey: ik.prefs })
      const before = qc.getQueryData<{ items: Preference[]; meta: unknown }>(ik.prefs)
      if (before) qc.setQueryData(ik.prefs, { ...before, items: before.items.map((p) => (p.event_type === event ? { ...p, [field]: value } : p)) })
      return { was: before?.items.find((p) => p.event_type === event)?.[field] }
    },
    onError: (_e, { event, field }, ctx) => {
      const now = qc.getQueryData<{ items: Preference[]; meta: unknown }>(ik.prefs)
      if (now && ctx?.was !== undefined) qc.setQueryData(ik.prefs, { ...now, items: now.items.map((p) => (p.event_type === event ? { ...p, [field]: ctx.was } : p)) })
    },
    onSettled: () => { if (qc.isMutating({ mutationKey: ["save-pref"] }) === 1) void qc.invalidateQueries({ queryKey: ik.prefs }) },
  })
}
