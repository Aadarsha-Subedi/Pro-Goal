import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { activityApi, type ActivityFilters } from "./api"

export const useActivity = (projectId: string, f: ActivityFilters) =>
  useQuery({ queryKey: ["activity", projectId, f.actor ?? "", f.entity ?? "", f.after ?? "", f.before ?? "", f.page ?? 1], queryFn: () => activityApi.list(projectId, f), placeholderData: keepPreviousData, retry: false })
