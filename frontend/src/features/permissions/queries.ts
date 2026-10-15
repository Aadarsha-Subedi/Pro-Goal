import { queryOptions, useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query"
import { keys as projectKeys } from "@/features/projects/queries"
import { permissionsApi } from "./api"

export const grantKeys = {
  all: (projectId: string) => ["grants", projectId] as const,
  one: (projectId: string, userId: string) => ["grants", projectId, userId] as const,
}

export const grantsQuery = (projectId: string, userId: string, enabled = true) =>
  queryOptions({ queryKey: grantKeys.one(projectId, userId), queryFn: () => permissionsApi.get(projectId, userId), enabled, retry: false, staleTime: 30_000 })

export const useGrants = (projectId: string, userId: string, enabled = true) => useQuery(grantsQuery(projectId, userId, enabled))

/** One request per member, in parallel, for the matrix. */
export const useAllGrants = (projectId: string, userIds: string[], enabled: boolean) =>
  useQueries({ queries: userIds.map((id) => grantsQuery(projectId, id, enabled)) })

export function useReplaceGrants(projectId: string, userId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (permissions: string[]) => permissionsApi.replace(projectId, userId, permissions),
    onSuccess: async (data) => {
      qc.setQueryData(grantKeys.one(projectId, userId), data)
      await Promise.all([qc.invalidateQueries({ queryKey: projectKeys.project(projectId) }), qc.invalidateQueries({ queryKey: projectKeys.members(projectId) })])
    },
  })
}
