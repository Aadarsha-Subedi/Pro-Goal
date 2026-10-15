import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { projectsApi, type JoinStatus, type ProjectInput, type Reauth } from "./api"

export const keys = {
  projects: ["projects"] as const,
  project: (id: string) => ["project", id] as const,
  members: (id: string) => ["members", id] as const,
  requests: (id: string, status: JoinStatus) => ["requests", id, status] as const,
  transfers: ["transfers"] as const,
  registry: ["registry"] as const,
}

export const projectsQuery = () => queryOptions({ queryKey: keys.projects, queryFn: () => projectsApi.list(0, 100) })
export const projectQuery = (id: string) => queryOptions({ queryKey: keys.project(id), queryFn: () => projectsApi.get(id), retry: false, enabled: !!id })
export const membersQuery = (id: string) => queryOptions({ queryKey: keys.members(id), queryFn: () => projectsApi.members(id) })
export const requestsQuery = (id: string, status: JoinStatus = "pending", enabled = true) =>
  queryOptions({ queryKey: keys.requests(id, status), queryFn: () => projectsApi.requests(id, status), enabled })
export const transfersQuery = () => queryOptions({ queryKey: keys.transfers, queryFn: () => projectsApi.incomingTransfers() })
export const registryQuery = () => queryOptions({ queryKey: keys.registry, queryFn: () => projectsApi.registry(), staleTime: Infinity })

export const useProjects = () => useQuery(projectsQuery())
export const useProject = (id: string) => useQuery(projectQuery(id))
export const useMembers = (id: string) => useQuery(membersQuery(id))
export const useRequests = (id: string, status: JoinStatus = "pending", enabled = true) => useQuery(requestsQuery(id, status, enabled))
export const useTransfers = () => useQuery(transfersQuery())
export const useRegistry = () => useQuery(registryQuery())

/** One place that knows what each mutation makes stale. */
export function useProjectMutations(id?: string) {
  const qc = useQueryClient()
  const refreshProject = async () => {
    await Promise.all([qc.invalidateQueries({ queryKey: keys.projects }), id ? qc.invalidateQueries({ queryKey: keys.project(id) }) : undefined])
  }
  const need = () => {
    if (!id) throw new Error("project id required")
    return id
  }
  return {
    create: useMutation({ mutationFn: (input: ProjectInput) => projectsApi.create(input), onSuccess: refreshProject }),
    update: useMutation({ mutationFn: (input: Parameters<typeof projectsApi.update>[1]) => projectsApi.update(need(), input), onSuccess: refreshProject }),
    archive: useMutation({ mutationFn: () => projectsApi.archive(need()), onSuccess: refreshProject }),
    unarchive: useMutation({ mutationFn: () => projectsApi.unarchive(need()), onSuccess: refreshProject }),
    remove: useMutation({ mutationFn: (reauth: Reauth) => projectsApi.remove(need(), reauth), onSuccess: refreshProject }),
    restore: useMutation({ mutationFn: () => projectsApi.restore(need()), onSuccess: refreshProject }),
    copy: useMutation({ mutationFn: (name?: string) => projectsApi.copy(need(), name), onSuccess: refreshProject }),
    regenerateCode: useMutation({ mutationFn: (reauth: Reauth) => projectsApi.regenerateCode(need(), reauth), onSuccess: refreshProject }),
    removeMember: useMutation({
      mutationFn: (userId: string) => projectsApi.removeMember(need(), userId),
      onSuccess: async () => {
        await Promise.all([qc.invalidateQueries({ queryKey: keys.members(need()) }), refreshProject()])
      },
    }),
    leave: useMutation({
      mutationFn: () => projectsApi.leave(need()),
      onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: keys.projects }), qc.invalidateQueries({ queryKey: ["explore"] })]),
    }),
    approve: useMutation({
      mutationFn: ({ requestId, preset }: { requestId: string; preset?: string }) => projectsApi.approve(need(), requestId, preset),
      onSuccess: async () => {
        await Promise.all([qc.invalidateQueries({ queryKey: ["requests", need()] }), qc.invalidateQueries({ queryKey: keys.members(need()) }), refreshProject()])
      },
    }),
    reject: useMutation({
      mutationFn: (requestId: string) => projectsApi.reject(need(), requestId),
      onSuccess: () => qc.invalidateQueries({ queryKey: ["requests", need()] }),
    }),
    startTransfer: useMutation({ mutationFn: ({ toUser, reauth }: { toUser: string; reauth: Reauth }) => projectsApi.startTransfer(need(), toUser, reauth), onSuccess: refreshProject }),
    cancelTransfer: useMutation({ mutationFn: () => projectsApi.cancelTransfer(need()), onSuccess: refreshProject }),
    join: useMutation({ mutationFn: (code: string) => projectsApi.join(code) }),
    acceptTransfer: useMutation({
      mutationFn: (transferId: string) => projectsApi.acceptTransfer(transferId),
      onSuccess: async () => {
        await Promise.all([qc.invalidateQueries({ queryKey: keys.transfers }), qc.invalidateQueries({ queryKey: keys.projects }), qc.invalidateQueries({ queryKey: ["project"] })])
      },
    }),
  }
}
