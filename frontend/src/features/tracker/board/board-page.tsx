import { DndContext, DragOverlay, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent, type DragStartEvent } from "@dnd-kit/core"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { PriorityTag, StatusTag } from "@/components/patterns/work-status"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { can, useCurrentProject } from "@/features/projects/current"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowsLeftRight, DotsSixVertical, ListChecks, Lock } from "@/icons"
import { readyOptions } from "@/lib/lazy-options"
import { cn } from "@/lib/utils"
import { trackerApi, type BoardGroup, type BoardSort, type Task } from "../api"
import { trackerError } from "../errors"
import { useProjectPeople } from "../people"
import { tk, useBoardTasks, usePreference, usePriorities, useSavePreference, useStatuses } from "../queries"
import { toFilters, type TaskSearch } from "../search"
import { FilterBar } from "../tasks/filter-bar"
import { DueDate } from "../tasks/task-row"
import { applyMove, buildLanes, GROUP_PERMISSION, movePatch, type Lane } from "./lanes"
import { useLockText } from "@/features/permissions/use-lock-text"

const GROUPS: { value: BoardGroup; label: string }[] = [
  { value: "status", label: "Status" },
  { value: "priority", label: "Priority" },
  { value: "assignee", label: "Assignee" },
  { value: "tag", label: "Tag" },
]
const SORTS: { value: BoardSort; label: string }[] = [
  { value: "number", label: "Number" },
  { value: "due_date", label: "Due date" },
  { value: "priority", label: "Priority" },
  { value: "created_at", label: "Newest" },
  { value: "updated_at", label: "Recently updated" },
  { value: "title", label: "Title" },
]

interface DragData {
  task: Task
  laneId: string
}

function CardRow({ task, laneId, lanes, canMove, maxRank, group, onMove }: { task: Task; laneId: string; lanes: Lane[]; canMove: boolean; maxRank: number; group: BoardGroup; onMove: (task: Task, from: string, to: string) => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `${laneId}:${task.id}`, data: { task, laneId } satisfies DragData, disabled: !canMove })
  return (
    <li ref={setNodeRef} data-card={task.id} className={cn("flex items-start gap-1 py-2", isDragging && "opacity-40")}>
      {canMove ? (
        <button type="button" aria-label={`Drag ${task.key}`} className="mt-0.5 grid size-6 shrink-0 cursor-grab touch-none place-items-center rounded text-muted-foreground outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:size-11" {...listeners} {...attributes}>
          <DotsSixVertical className="size-4" aria-hidden />
        </button>
      ) : (
        <span className="mt-0.5 grid size-6 shrink-0 place-items-center text-muted-foreground pointer-coarse:size-11" title="Locked"><Lock className="size-3.5" aria-hidden /></span>
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <Link to="/app/projects/$projectId/tasks/$number" params={{ projectId: task.project.id, number: String(task.number) }} className="block rounded text-sm font-medium outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50">
          <span className="mr-1.5 font-mono text-xs font-normal text-muted-foreground">{task.key}</span>{task.title}
        </Link>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
          {group !== "status" && <StatusTag name={task.status.name} category={task.status.category} className="text-xs" />}
          {group !== "priority" && <PriorityTag name={task.priority.name} rank={task.priority.rank} max={maxRank} className="text-xs" />}
          <DueDate task={task} hideEmpty />
        </div>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" label={`Move ${task.key}`} disabled={!canMove}><ArrowsLeftRight /></Button>} />
        <DropdownMenuContent align="end">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Move to</DropdownMenuLabel>
            {lanes.filter((l) => l.id !== laneId).map((l) => <DropdownMenuItem key={l.id} onClick={() => onMove(task, laneId, l.id)}>{l.name}</DropdownMenuItem>)}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  )
}

/** What follows the pointer while dragging: looks like the card, holds no controls and no ids. */
function CardPreview({ task }: { task: Task }) {
  return (
    <div aria-hidden className="flex items-center gap-2 rounded-md border bg-background px-2 py-2 shadow-pop">
      <DotsSixVertical className="size-4 text-muted-foreground" />
      <span className="truncate text-sm font-medium"><span className="mr-1.5 font-mono text-xs font-normal text-muted-foreground">{task.key}</span>{task.title}</span>
    </div>
  )
}

function LaneColumn({ lane, children }: { lane: Lane; children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: lane.id })
  return (
    <section ref={setNodeRef} aria-labelledby={`lane-${lane.id}`} className={cn("w-72 shrink-0 snap-start rounded-md px-2 pb-2 transition-colors", isOver && "bg-primary/5")}>
      <h2 id={`lane-${lane.id}`} className="flex items-baseline justify-between border-b py-2 text-sm font-semibold">
        <span className="truncate">{lane.name}</span>
        <span className="text-xs font-normal tabular-nums text-muted-foreground">{lane.tasks.length}</span>
      </h2>
      {lane.tasks.length === 0 ? <p className="py-3 text-xs text-muted-foreground">No tasks</p> : <ul className="divide-y" aria-label={`${lane.name} tasks`}>{children}</ul>}
    </section>
  )
}

export function BoardPage({ search, onSearch }: { search: TaskSearch; onSearch: (next: TaskSearch) => void }) {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Board · ${project.name} · Pro-Goal`)
  const filters = { ...toFilters(search), ordering: undefined }
  const tasksQ = useBoardTasks(id, filters)
  const { data, isError, refetch } = tasksQ
  const statuses = useStatuses(id).data?.items ?? []
  const priorities = usePriorities(id).data?.items ?? []
  const { people } = useProjectPeople(id)
  const prefQ = usePreference(id)
  const pref = prefQ.data
  const isPending = tasksQ.isPending || prefQ.isPending
  const savePref = useSavePreference(id)
  const group: BoardGroup = pref?.group_by ?? "status"
  const sortBy: BoardSort = pref?.sort_by ?? "number"
  const qc = useQueryClient()
  const [active, setActive] = useState<DragData | null>(null)
  const maxRank = Math.max(1, ...priorities.map((p) => p.rank))
  const tasks = data?.items ?? []
  const lanes = buildLanes(group, sortBy, { tasks, statuses, priorities, people })
  const permission = GROUP_PERMISSION[group]
  const lockText = useLockText()
  const canMove = can(project, permission) && !project.is_archived
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor))

  const move = useMutation({
    mutationKey: ["board-move", id],
    mutationFn: ({ task, patch }: { task: Task; patch: Record<string, unknown> }) => trackerApi.updateTask(id, task.number, patch),
    onMutate: async ({ task, patch }) => {
      const key = tk.board(id, filters)
      await qc.cancelQueries({ queryKey: key })
      const before = qc.getQueryData(key)
      qc.setQueryData(key, (old: typeof data) => old && { ...old, items: old.items.map((t) => (t.id === task.id ? applyMove(t, group, patch, { statuses, priorities, people }) : t)) })
      return { before, key }
    },
    onError: (e, _v, ctx) => {
      if (ctx) qc.setQueryData(ctx.key, ctx.before)
      toast.error(trackerError(e))
    },
    // Several quick moves share one refetch, so a slow answer can't overwrite a newer move.
    onSettled: () => { if (qc.isMutating({ mutationKey: ["board-move", id] }) === 1) void qc.invalidateQueries({ queryKey: tk.tasks(id) }) },
  })
  const laneName = (lid: string) => lanes.find((l) => l.id === lid)?.name ?? lid
  const doMove = (task: Task, from: string, to: string) => {
    const patch = movePatch(group, task, from, to)
    if (!patch) return
    move.mutate({ task, patch }, {
      onSuccess: () => {
        // The card remounts in its new lane; hand keyboard focus to it so the user keeps their place.
        requestAnimationFrame(() => requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-card="${task.id}"] [aria-label^="Drag"]`)?.focus()))
        const moved = applyMove(task, group, patch, { statuses, priorities, people })
        const back = movePatch(group, moved, to, from)
        toast.success(`${task.key} moved to ${laneName(to)}.`, { duration: 8000, action: back ? { label: "Undo", onClick: () => move.mutate({ task: moved, patch: back }, {}) } : undefined })
      },
    })
  }
  const announce = {
    onDragStart: ({ active: a }: { active: { data: { current?: unknown } } }) => `Picked up ${(a.data.current as DragData).task.key}.`,
    onDragOver: ({ active: a, over }: { active: { data: { current?: unknown } }; over: { id: string | number } | null }) => (over ? `${(a.data.current as DragData).task.key} is over ${laneName(String(over.id))}.` : undefined),
    onDragEnd: ({ active: a, over }: { active: { data: { current?: unknown } }; over: { id: string | number } | null }) => (over ? `${(a.data.current as DragData).task.key} dropped in ${laneName(String(over.id))}.` : `${(a.data.current as DragData).task.key} was not moved.`),
    onDragCancel: ({ active: a }: { active: { data: { current?: unknown } } }) => `Move of ${(a.data.current as DragData).task.key} cancelled.`,
  }
  const end = (e: DragEndEvent) => {
    setActive(null)
    const d = e.active.data.current as DragData | undefined
    if (d && e.over) doMove(d.task, d.laneId, String(e.over.id))
  }
  const setPref = (next: Partial<{ group_by: BoardGroup; sort_by: BoardSort }>) => savePref.mutate({ group_by: group, sort_by: sortBy, ...next }, { onError: (e) => toast.error(trackerError(e)) })

  return (
    <div className="space-y-5">
      <PageHeader title="Board" description="Cards sit in lanes by the field you group by. Moving a card changes that field. Subtasks open from their parent." actions={<Button variant="outline" icon={<ListChecks />} nativeButton={false} render={<Link to="/app/projects/$projectId/tasks" params={{ projectId: id }} />}>List</Button>} />
      <div className="flex flex-wrap items-center gap-2">
        <Select value={group} onValueChange={(v) => v && setPref({ group_by: v as BoardGroup })} items={GROUPS.map((g) => ({ value: g.value, label: `Group by: ${g.label}` }))}>
          <SelectTrigger aria-label="Group by" className="w-auto min-w-40"><SelectValue /></SelectTrigger>
          <SelectContent>{GROUPS.map((g) => <SelectItem key={g.value} value={g.value}>Group by: {g.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={sortBy} onValueChange={(v) => v && setPref({ sort_by: v as BoardSort })} items={SORTS.map((s) => ({ value: s.value, label: `Sort: ${s.label}` }))}>
          <SelectTrigger aria-label="Sort cards" className="w-auto min-w-40"><SelectValue /></SelectTrigger>
          <SelectContent>{SORTS.map((s) => <SelectItem key={s.value} value={s.value}>Sort: {s.label}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <FilterBar search={search} onChange={onSearch} statuses={readyOptions(statuses)} priorities={readyOptions(priorities)} people={readyOptions(people)} hideSort />
      {!canMove && <p className="flex items-center gap-1.5 text-sm text-muted-foreground"><Lock className="size-4" aria-hidden />{project.is_archived ? "This project is archived, so cards can't move." : `${lockText(permission)} Moving cards grouped by ${group} needs it.`}</p>}

      {data && data.meta.count > data.items.length && <p className="text-sm text-muted-foreground">Showing {data.items.length} of {data.meta.count} tasks. Narrow the board with filters to see the rest.</p>}

      {isPending ? (
        <div className="flex gap-4" aria-busy="true" aria-label="Loading board">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-48 w-72" />)}</div>
      ) : isError ? (
        <Empty>
          <EmptyHeader><EmptyTitle>Couldn't load the board</EmptyTitle><EmptyDescription>Check your connection and try again.</EmptyDescription></EmptyHeader>
          <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
        </Empty>
      ) : (
        <DndContext sensors={sensors} accessibility={{ screenReaderInstructions: { draggable: "Press space to lift the card, arrow keys to move it, space to drop, escape to cancel. The Move button on each card is an easier way." }, announcements: announce }} onDragStart={(e: DragStartEvent) => setActive(e.active.data.current as DragData)} onDragEnd={end} onDragCancel={() => setActive(null)}>
          <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-4 md:-mx-6 md:px-6" role="group" aria-label="Board lanes">
            {lanes.map((l) => (
              <LaneColumn key={l.id} lane={l}>
                {l.tasks.map((t) => <CardRow key={t.id} task={t} laneId={l.id} lanes={lanes} canMove={canMove} maxRank={maxRank} group={group} onMove={doMove} />)}
              </LaneColumn>
            ))}
          </div>
          <DragOverlay>{active && <div className="w-72"><CardPreview task={active.task} /></div>}</DragOverlay>
        </DndContext>
      )}
    </div>
  )
}
