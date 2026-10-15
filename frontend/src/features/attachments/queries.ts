import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { attachmentsApi, type Target } from "./api"

const targetKey = (t: Target) => [t.type, String(t.id)] as const

export const ak = {
  all: (pid: string) => ["attachments", pid] as const,
  list: (pid: string, t: Target) => ["attachments", pid, ...targetKey(t)] as const,
  url: (pid: string, id: string) => ["attachment-url", pid, id] as const,
  usage: (pid: string) => ["storage", pid] as const,
  mine: ["my-storage"] as const,
}

export const useAttachments = (pid: string, target: Target, enabled = true) =>
  useQuery({ queryKey: ak.list(pid, target), queryFn: () => attachmentsApi.list(pid, target), enabled })

/** Signed links last five minutes; this keeps one for four so a re-render never asks again. */
export const useDownloadUrl = (pid: string, id: string, enabled: boolean) =>
  useQuery({ queryKey: ak.url(pid, id), queryFn: () => attachmentsApi.download(pid, id), enabled, staleTime: 4 * 60_000, gcTime: 4 * 60_000, retry: false })

export const useProjectUsage = (pid: string) => useQuery({ queryKey: ak.usage(pid), queryFn: () => attachmentsApi.projectUsage(pid) })
export const useMyUsage = () => useQuery({ queryKey: ak.mine, queryFn: () => attachmentsApi.myUsage() })

export function useAttachmentMutations(pid: string) {
  const qc = useQueryClient()
  const stale = () => Promise.all([qc.invalidateQueries({ queryKey: ak.all(pid) }), qc.invalidateQueries({ queryKey: ak.usage(pid) }), qc.invalidateQueries({ queryKey: ak.mine })])
  return { remove: useMutation({ mutationFn: (id: string) => attachmentsApi.remove(pid, id), onSuccess: stale }), refresh: stale }
}
