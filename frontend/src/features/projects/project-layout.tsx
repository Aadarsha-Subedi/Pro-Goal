import { Link, Outlet, useRouteContext } from "@tanstack/react-router"
import { toast } from "sonner"
import { StatusBanner } from "@/components/patterns/status-banner"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowClockwise, ArrowCounterClockwise, ArrowLeft, Archive } from "@/icons"
import { useAutoTour } from "@/features/tour/use-auto-tour"
import { daysUntil, plural } from "@/lib/format"
import { CopyProjectDialog } from "./copy-project-dialog"
import { isNotFound, projectError } from "./errors"
import { useProject, useProjectMutations } from "./queries"
import { useProjectId } from "./current"

/** Loads the project once for every page below it and owns the not-found, archived and scheduled-for-deletion states. */
export function ProjectLayout() {
  const id = useProjectId()
  const { data: project, isPending, error, refetch } = useProject(id)
  const { unarchive, restore } = useProjectMutations(id)
  const { me } = useRouteContext({ from: "/app" })
  useAutoTour(!!project?.is_demo && !me.tour_completed)

  if (isPending) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading project">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }
  if (error) {
    return isNotFound(error) ? (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Project not found</EmptyTitle>
          <EmptyDescription>It doesn't exist, or you aren't a member. Ask the owner to add you, or look for it on Explore.</EmptyDescription>
        </EmptyHeader>
        <Button variant="outline" icon={<ArrowLeft />} nativeButton={false} render={<Link to="/app" />}>Back to projects</Button>
      </Empty>
    ) : (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Couldn't load this project</EmptyTitle>
          <EmptyDescription>{projectError(error)}</EmptyDescription>
        </EmptyHeader>
        <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
      </Empty>
    )
  }

  const owner = project.role === "owner"
  return (
    <div className="space-y-6">
      {project.deletion_scheduled_for && (
        <StatusBanner
          tone="danger"
          title="Scheduled for deletion."
          action={owner && <Button size="sm" icon={<ArrowCounterClockwise />} loading={restore.isPending} onClick={() => restore.mutate(undefined, { onSuccess: () => toast.success("Project restored."), onError: (e) => toast.error(projectError(e)) })}>Restore project</Button>}
        >
          It is deleted for good in {plural(daysUntil(project.deletion_scheduled_for), "day")}. Members can't open it.
        </StatusBanner>
      )}
      {project.is_archived && !project.deletion_scheduled_for && (
        <StatusBanner
          tone="warning"
          title="Archived."
          action={owner && <Button size="sm" variant="outline" icon={<Archive />} loading={unarchive.isPending} onClick={() => unarchive.mutate(undefined, { onSuccess: () => toast.success("Project unarchived."), onError: (e) => toast.error(projectError(e)) })}>Unarchive</Button>}
        >
          This project is read-only for everyone until the owner unarchives it.
        </StatusBanner>
      )}
      {project.is_demo && !project.is_archived && !project.deletion_scheduled_for && (
        <StatusBanner tone="info" title="Shared demo." action={<CopyProjectDialog project={project} size="sm" />}>
          Everyone sees the same data and it is read-only. Make your own copy to edit it.
        </StatusBanner>
      )}
      <Outlet />
    </div>
  )
}
