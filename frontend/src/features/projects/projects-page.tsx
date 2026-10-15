import { Link } from "@tanstack/react-router"
import { PageHeader } from "@/components/patterns/page-header"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { Archive, ArrowClockwise, Compass, Crown, Trash, Users, WarningCircle } from "@/icons"
import { daysUntil, plural } from "@/lib/format"
import type { Project } from "./api"
import { CreateProjectDialog } from "./create-project-dialog"
import { JoinProjectDialog } from "./join-dialog"
import { useProjects } from "./queries"
import { TransferBanner } from "./transfer-banner"

function ProjectState({ project }: { project: Project }) {
  if (project.deletion_scheduled_for)
    return <span className="inline-flex items-center gap-1 text-xs text-destructive"><Trash className="size-3.5" aria-hidden />Deletes in {plural(daysUntil(project.deletion_scheduled_for), "day")}</span>
  if (project.is_archived) return <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Archive className="size-3.5" aria-hidden />Archived</span>
  return null
}

function ProjectRow({ project }: { project: Project }) {
  return (
    <li>
      <Link to="/app/projects/$projectId" params={{ projectId: project.id }} className="flex min-h-(--row-h) flex-wrap items-center gap-x-3 gap-y-1 px-1 py-2.5 outline-none transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:min-h-12">
        <span className="w-12 shrink-0 font-mono text-xs text-muted-foreground">{project.task_key}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{project.name}</span>
          {project.description && <span className="block truncate text-xs text-muted-foreground">{project.description}</span>}
        </span>
        <ProjectState project={project} />
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          {project.role === "owner" && <><Crown weight="fill" className="size-3.5 text-warning" aria-hidden />Owner<span aria-hidden>·</span></>}
          <Users className="size-3.5" aria-hidden /><span className="tabular-nums">{plural(project.member_count, "member")}</span>
        </span>
      </Link>
    </li>
  )
}

function ListSkeleton() {
  return (
    <ul className="divide-y" aria-busy="true" aria-label="Loading projects">
      {[0, 1, 2].map((i) => (
        <li key={i} className="flex items-center gap-3 px-1 py-3"><Skeleton className="h-4 w-10" /><Skeleton className="h-4 w-48" /><Skeleton className="ml-auto h-4 w-20" /></li>
      ))}
    </ul>
  )
}

export function ProjectsPage() {
  useDocumentTitle("Projects · Pro-Goal")
  const { data, isPending, isError, refetch } = useProjects()
  const items = data?.items ?? []
  return (
    <div className="space-y-6">
      <PageHeader title="Projects" description="Every project is its own space with its own members and permissions." actions={items.length > 0 && <><JoinProjectDialog /><CreateProjectDialog /></>} />
      <TransferBanner />
      {isPending ? (
        <ListSkeleton />
      ) : isError ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle className="flex items-center gap-2"><WarningCircle className="size-5 text-destructive" />Couldn't load your projects</EmptyTitle>
            <EmptyDescription>Check your connection and try again.</EmptyDescription>
          </EmptyHeader>
          <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
        </Empty>
      ) : items.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>No projects yet</EmptyTitle>
            <EmptyDescription>Start one, or look around the shared demo projects on Explore.</EmptyDescription>
          </EmptyHeader>
          <div className="flex flex-wrap justify-center gap-2"><Button variant="outline" icon={<Compass />} nativeButton={false} render={<Link to="/app/explore" />}>Explore demos</Button><CreateProjectDialog /><JoinProjectDialog /></div>
        </Empty>
      ) : (
        <>
          <ul className="divide-y border-y">{items.map((p) => <ProjectRow key={p.id} project={p} />)}</ul>
          {data && data.meta.count > items.length && <p className="text-xs text-muted-foreground">Showing the first {items.length} of {data.meta.count} projects.</p>}
        </>
      )}
    </div>
  )
}
