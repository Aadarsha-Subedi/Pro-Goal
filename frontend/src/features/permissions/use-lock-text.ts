import { useCallback } from "react"
import { useProjectId } from "@/features/projects/current"
import { useProject, useRegistry } from "@/features/projects/queries"

/** Plain-language reason a control is locked: the permission's label from the registry, and who to ask. */
export function useLockText(): (code: string) => string {
  const projectId = useProjectId()
  const { data: project } = useProject(projectId ?? "")
  const { data } = useRegistry()
  const owner = project?.owner.first_name ?? "the owner"
  return useCallback(
    (code: string) => {
      const label = data?.permissions.find((p) => p.code === code)?.label ?? code
      return `Needs “${label}”. Ask ${owner} or a member who manages permissions.`
    },
    [data, owner],
  )
}
