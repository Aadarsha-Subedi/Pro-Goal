import { Link } from "@tanstack/react-router"
import { useEffect } from "react"
import { ApiError } from "@/lib/api"
import { PageHeader } from "@/components/patterns/page-header"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { can, useCurrentProject } from "@/features/projects/current"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, ArrowRight, Kanban, X } from "@/icons"
import { toast } from "sonner"
import { trackerError } from "../errors"
import { useLazyProjectPeople } from "../people"
import { usePriorityOptions, useStatusOptions, useTaskMutations, useTasks } from "../queries"
import { activeFilterCount, PAGE_SIZE, toFilters, type TaskSearch } from "../search"
import { FilterBar } from "./filter-bar"
import { QuickAdd } from "./quick-add"
import { TaskRow } from "./task-row"

export function TasksPage({ search, onSearch }: { search: TaskSearch; onSearch: (next: TaskSearch) => void }) {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Tasks · ${project.name} · Pro-Goal`)
  const page = search.page ?? 1
  const { data, isPending, isError, error, isFetching, refetch } = useTasks(id, toFilters(search), page)
  // Dropdown choices load when a dropdown first opens; one already in the URL loads now so its name shows.
  const statuses = useStatusOptions(id, !!search.status)
  const priorities = usePriorityOptions(id, !!search.priority)
  const people = useLazyProjectPeople(id, !!search.assignee)
  const { update } = useTaskMutations(id)
  const inline = {
    statuses,
    priorities,
    canStatus: can(project, "task.status.change") && !project.is_archived,
    canPriority: can(project, "task.priority.change") && !project.is_archived,
    onChange: (t: { number: number; key: string }, patch: { status?: string; priority?: string }) => { update.mutateAsync({ number: t.number, patch }).catch((e) => toast.error(`${t.key}: ${trackerError(e)}`)) },
  }
  // j and k move between rows, like most trackers. Typing in a field or an open menu keeps its own keys.
  const rowKeys = (e: React.KeyboardEvent) => {
    if (e.key !== "j" && e.key !== "k") return
    const el = e.target as HTMLElement
    if (el.closest("input, textarea, select, [role=combobox], [role=listbox], [contenteditable]")) return
    const links = [...e.currentTarget.querySelectorAll<HTMLElement>("[data-row-link]")]
    const at = links.indexOf(el.closest("[data-row-link]") as HTMLElement)
    const next = links[e.key === "j" ? Math.min(links.length - 1, at + 1) : Math.max(0, at - 1)]
    if (next) { e.preventDefault(); next.focus() }
  }
  const items = data?.items ?? []
  // Bar length for priority comes from the tasks on screen, so it needs no extra request.
  const maxRank = Math.max(4, ...items.map((t) => t.priority.rank))
  const count = data?.meta.count ?? 0
  const filtered = activeFilterCount(search) > 0
  const first = (page - 1) * PAGE_SIZE + 1
  const lastPage = Math.max(1, Math.ceil(count / PAGE_SIZE))
  // A stale page number (the last row was deleted or filtered away) goes back to the last real page.
  const overshoot = !!data && items.length === 0 && count > 0 && page > lastPage
  useEffect(() => {
    if (overshoot) onSearch({ ...search, page: lastPage > 1 ? lastPage : undefined })
  }, [overshoot, lastPage, search, onSearch])
  const badFilter = isError && error instanceof ApiError && error.status === 400

  return (
    <div className="space-y-5">
      <PageHeader
        title="Tasks"
        actions={<Button variant="outline" icon={<Kanban />} nativeButton={false} render={<Link to="/app/projects/$projectId/board" params={{ projectId: id }} />}>Board</Button>}
        description="Open a task to change its fields and add subtasks."
      />
      <QuickAdd projectId={id} allowed={can(project, "task.create")} archived={project.is_archived} onAdded={() => onSearch({ ...search, page: undefined })} />
      <FilterBar search={search} onChange={onSearch} statuses={statuses} priorities={priorities} people={people} />

      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading tasks">
          {[0, 1, 2, 3].map((i) => <li key={i} className="flex items-center gap-4 px-1 py-3"><Skeleton className="h-4 w-16" /><Skeleton className="h-4 w-64 max-w-full" /><Skeleton className="ml-auto h-4 w-24" /></li>)}
        </ul>
      ) : badFilter ? (
        <Empty>
          <EmptyHeader><EmptyTitle>That filter no longer applies</EmptyTitle><EmptyDescription>A status, priority or person in this link was removed or never existed.</EmptyDescription></EmptyHeader>
          <Button variant="outline" icon={<X />} onClick={() => onSearch({})}>Clear filters</Button>
        </Empty>
      ) : isError ? (
        <Empty>
          <EmptyHeader><EmptyTitle>Couldn't load tasks</EmptyTitle><EmptyDescription>Check your connection and try again.</EmptyDescription></EmptyHeader>
          <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
        </Empty>
      ) : items.length === 0 && count > 0 ? null : items.length === 0 ? (
        filtered ? (
          <Empty>
            <EmptyHeader><EmptyTitle>No tasks match</EmptyTitle><EmptyDescription>Change or clear the filters to see more.</EmptyDescription></EmptyHeader>
            <Button variant="outline" icon={<X />} onClick={() => onSearch({})}>Clear filters</Button>
          </Empty>
        ) : (
          <Empty>
            <EmptyHeader><EmptyTitle>No tasks yet</EmptyTitle><EmptyDescription>Type a title above and press Add. You set status, people and dates on the task page.</EmptyDescription></EmptyHeader>
          </Empty>
        )
      ) : (
        <>
          <ul onKeyDown={rowKeys} className={`divide-y border-y transition-opacity ${isFetching ? "opacity-70" : ""}`} aria-label="Tasks. Press j or k to move between rows.">
            {items.map((t) => <TaskRow key={t.id} task={t} maxRank={maxRank} inline={inline} to={{ to: "/app/projects/$projectId/tasks/$number", params: { projectId: id, number: String(t.number) } }} />)}
          </ul>
          <nav aria-label="Pages" className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="tabular-nums" aria-live="polite">{first}–{first + items.length - 1} of {count}</span>
            <span className="flex gap-2">
              <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => onSearch({ ...search, page: page > 2 ? page - 1 : undefined })}>Previous</Button>
              <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={first + items.length - 1 >= count} onClick={() => onSearch({ ...search, page: page + 1 })}>Next</Button>
            </span>
          </nav>
        </>
      )}
    </div>
  )
}
