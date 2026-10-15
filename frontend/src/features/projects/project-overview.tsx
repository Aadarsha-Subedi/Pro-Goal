import { Link } from "@tanstack/react-router"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TaskSummary } from "@/features/tracker/tasks/task-summary"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { Copy, Crown, GearSix, Users } from "@/icons"
import { formatPlainDate, plural } from "@/lib/format"
import { can, useCurrentProject } from "./current"

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[9rem_1fr] sm:gap-4">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm">{children}</dd>
    </div>
  )
}

export function ProjectOverview() {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`${project.name} · Pro-Goal`)
  const owner = project.role === "owner"
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(project.join_code ?? "")
      toast.success("Join code copied.")
    } catch {
      toast.error("Couldn't copy. Select the code and copy it by hand.")
    }
  }
  const dates = [project.start_date && formatPlainDate(project.start_date), project.end_date && formatPlainDate(project.end_date)].filter(Boolean)

  return (
    <div className="space-y-8">
      <PageHeader
        title={<span className="flex flex-wrap items-baseline gap-x-3"><span>{project.name}</span><span aria-hidden className="font-mono text-sm font-normal text-muted-foreground">{project.task_key}</span></span>}
        description={project.description || undefined}
        actions={<Button variant="outline" icon={<GearSix />} nativeButton={false} render={<Link to="/app/projects/$projectId/settings" params={{ projectId: id }} />}>{can(project, "project.name.change") ? "Settings" : "Details"}</Button>}
      />
      <dl className="divide-y border-y">
        {owner && project.join_code && (
          <Row label="Join code">
            <span className="flex flex-wrap items-center gap-3">
              <code className="rounded-md bg-muted px-2 py-1 font-mono text-sm tracking-widest">{project.join_code}</code>
              <Button size="sm" variant="outline" icon={<Copy />} onClick={copy} disabled={project.is_archived}>Copy code</Button>
              <span className="text-xs text-muted-foreground">People who use it still need your approval.</span>
            </span>
          </Row>
        )}
        <Row label="Your role">
          {owner ? <span className="inline-flex items-center gap-1.5"><Crown weight="fill" className="size-4 text-warning" aria-hidden />Owner. You hold every permission.</span> : <span>Member. {project.permissions.length === 0 ? "You can read everything and change nothing yet." : `You hold ${plural(project.permissions.length, "permission")}.`}</span>}
        </Row>
        <Row label="Owner"><span className="inline-flex items-center gap-2"><UserAvatar name={project.owner.first_name} src={project.owner.avatar_url} size="sm" />{project.owner.first_name}</span></Row>
        <Row label="Members"><Link to="/app/projects/$projectId/members" params={{ projectId: id }} className="inline-flex items-center gap-1.5 text-primary underline-offset-4 hover:underline"><Users className="size-4" aria-hidden />{plural(project.member_count, "member")}</Link></Row>
        {dates.length > 0 && <Row label="Dates">{dates.join(" to ")}</Row>}
        {project.tags.length > 0 && <Row label="Tags"><span className="flex flex-wrap gap-1.5">{project.tags.map((t) => <Badge key={t} variant="secondary">{t}</Badge>)}</span></Row>}
      </dl>
      <TaskSummary projectId={id} />
    </div>
  )
}
