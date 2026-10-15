import { useParams } from "@tanstack/react-router"
import { useProject } from "./queries"

export function useProjectId(): string {
  return (useParams({ strict: false }) as { projectId: string }).projectId
}

/** The project the layout already loaded. Pages under `/app/projects/$projectId` can rely on it being present. */
export function useCurrentProject() {
  const id = useProjectId()
  const query = useProject(id)
  return { id, project: query.data! }
}

export function can(project: { role: string; permissions: string[] }, code: string): boolean {
  return project.role === "owner" || project.permissions.includes(code)
}
