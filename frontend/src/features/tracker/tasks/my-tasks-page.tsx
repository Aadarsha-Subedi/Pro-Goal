import { PageHeader } from "@/components/patterns/page-header"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise } from "@/icons"
import { useMyTasks } from "../queries"
import type { Task } from "../api"
import { TaskRow } from "./task-row"

/** Tasks assigned to you, grouped by project. Open work first; done work stays under its project's list. */
export function MyTasksPage() {
  useDocumentTitle("My tasks · Pro-Goal")
  const { data, isPending, isError, refetch } = useMyTasks({ top_level: undefined, ordering: "due_date" })
  const groups = new Map<string, { name: string; tasks: Task[] }>()
  // Open work first, finished work after, each keeping the due-date order from the server.
  const ordered = [...(data?.items ?? [])].sort((a, b) => Number(a.status.category === "done") - Number(b.status.category === "done"))
  for (const t of ordered) {
    const g = groups.get(t.project.id) ?? { name: t.project.name, tasks: [] }
    g.tasks.push(t)
    groups.set(t.project.id, g)
  }
  return (
    <div className="space-y-6">
      <PageHeader title="My tasks" description="Everything assigned to you, across your projects. Open tasks first, earliest due date first." />
      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading your tasks">
          {[0, 1, 2].map((i) => <li key={i} className="flex items-center gap-4 px-1 py-3"><Skeleton className="h-4 w-16" /><Skeleton className="h-4 w-64 max-w-full" /></li>)}
        </ul>
      ) : isError ? (
        <Empty>
          <EmptyHeader><EmptyTitle>Couldn't load your tasks</EmptyTitle><EmptyDescription>Check your connection and try again.</EmptyDescription></EmptyHeader>
          <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
        </Empty>
      ) : groups.size === 0 ? (
        <Empty>
          <EmptyHeader><EmptyTitle>Nothing assigned to you</EmptyTitle><EmptyDescription>When someone assigns you a task, it shows up here.</EmptyDescription></EmptyHeader>
        </Empty>
      ) : (
        [...groups.entries()].map(([pid, g]) => (
          <section key={pid} aria-labelledby={`g-${pid}`} className="space-y-2">
            <h2 id={`g-${pid}`} className="text-sm font-semibold">{g.name}</h2>
            <ul className="divide-y border-y" aria-label={`Tasks in ${g.name}`}>
              {g.tasks.map((t) => <TaskRow key={t.id} task={t} maxRank={Math.max(4, t.priority.rank)} to={{ to: "/app/projects/$projectId/tasks/$number", params: { projectId: pid, number: String(t.number) } }} />)}
            </ul>
          </section>
        ))
      )}
      {data && data.meta.count > data.items.length && <p className="text-xs text-muted-foreground">Showing the first {data.items.length} of {data.meta.count} tasks.</p>}
    </div>
  )
}
