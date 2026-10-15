import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { exploreApi, type ExploreFilters } from "./api"

export const useExplore = (f: ExploreFilters) =>
  useQuery({ queryKey: ["explore", f.q ?? "", f.tag ?? "", f.after ?? "", f.before ?? "", f.page ?? 1], queryFn: () => exploreApi.list(f), placeholderData: keepPreviousData, retry: false })
export const useExploreTags = () => useQuery({ queryKey: ["explore-tags"], queryFn: () => exploreApi.tags(), staleTime: 60_000 })

export function useRequestJoin() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (projectId: string) => exploreApi.requestJoin(projectId), onSettled: () => Promise.all([qc.invalidateQueries({ queryKey: ["explore"] }), qc.invalidateQueries({ queryKey: ["projects"] })]) })
}
