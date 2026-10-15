import { Link, useRouteContext } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { ArrowRight, ListChecks } from "@/icons"
import { trackerApi, type TaskFilters } from "../api"
import { tk } from "../queries"

function useCount(pid: string, filters: TaskFilters, enabled = true) {
  return useQuery({ queryKey: [...tk.tasks(pid), "count", filters], queryFn: () => trackerApi.tasks(pid, filters, 0, 1), select: (p) => p.meta.count, enabled })
}

/** The project overview's work summary: three counts that each open the matching list. */
export function TaskSummary({ projectId }: { projectId: string }) {
  const { me } = useRouteContext({ from: "/app" })
  const all = useCount(projectId, { top_level: true })
  const overdue = useCount(projectId, { top_level: true, overdue: true })
  const mine = useCount(projectId, { top_level: true, assignee: me.id })
  const row = (label: string, value: number | undefined, search: Record<string, unknown>) => (
    <li key={label}>
      <Link to="/app/projects/$projectId/tasks" params={{ projectId }} search={search as never} className="flex min-h-(--row-h) items-center gap-3 px-1 py-2 text-sm outline-none hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:min-h-12">
        <span className="flex-1">{label}</span>
        <span className="tabular-nums text-muted-foreground">{value === undefined ? "–" : value}</span>
        <ArrowRight className="size-4 text-muted-foreground" aria-hidden />
      </Link>
    </li>
  )
  return (
    <section aria-labelledby="work" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 id="work" className="text-sm font-semibold">Work</h2>
        <Button size="sm" variant="outline" icon={<ListChecks />} nativeButton={false} render={<Link to="/app/projects/$projectId/tasks" params={{ projectId }} />}>All tasks</Button>
      </div>
      <ul className="divide-y border-y">
        {row(all.data === 1 ? "Task" : "Tasks", all.data, {})}
        {row("Overdue", overdue.data, { overdue: true })}
        {row("Assigned to you", mine.data, { assignee: me.id })}
      </ul>
      {all.data === 0 && <p className="text-sm text-muted-foreground">No tasks yet. Add the first one from the Tasks page.</p>}
    </section>
  )
}
