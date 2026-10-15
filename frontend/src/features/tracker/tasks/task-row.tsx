import { Link } from "@tanstack/react-router"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PriorityTag, StatusTag } from "@/components/patterns/work-status"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { CalendarBlank, Warning } from "@/icons"
import { formatPlainDate } from "@/lib/format"
import { cn } from "@/lib/utils"
import { OptionsState } from "@/components/patterns/options-state"
import type { LazyOptions } from "@/lib/lazy-options"
import type { Priority, Status, Task } from "../api"

export function DueDate({ task, hideEmpty }: { task: Task; hideEmpty?: boolean }) {
  if (!task.due_date) return hideEmpty ? null : <span className="text-xs text-muted-foreground">No due date</span>
  return task.is_overdue ? (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive"><Warning weight="fill" className="size-3.5" aria-hidden />Overdue · {formatPlainDate(task.due_date)}</span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><CalendarBlank className="size-3.5" aria-hidden />{formatPlainDate(task.due_date)}</span>
  )
}

export interface InlineEdit {
  /** Choices load when a row's dropdown first opens, shared by every row. */
  statuses: LazyOptions<Status>
  priorities: LazyOptions<Priority>
  canStatus: boolean
  canPriority: boolean
  onChange: (task: Task, patch: { status?: string; priority?: string }) => void
}

const QUIET = "h-7 pointer-coarse:h-11 w-full border-transparent bg-transparent px-1.5 shadow-none hover:border-input focus-visible:border-ring data-[popup-open]:border-input"

/** One task as a row: key, title, subtask progress, status, priority, assignees, due date. With `inline`, status and priority change in place. */
export function TaskRow({ task, maxRank, to, showProject, inline }: { task: Task; maxRank: number; to: { to: string; params: Record<string, string> }; showProject?: boolean; inline?: InlineEdit }) {
  const context = (showProject || task.parent_number || task.subtasks.total > 0 || task.tags.length > 0) && (
    <span className="block truncate text-xs text-muted-foreground">
      {[showProject && task.project.name, task.parent_number && `Subtask of ${task.project.task_key}-${task.parent_number}`, task.subtasks.total > 0 && `${task.subtasks.done} of ${task.subtasks.total} subtasks done`, task.tags.length > 0 && task.tags.map((t) => `#${t}`).join(" ")].filter(Boolean).join(" · ")}
    </span>
  )
  const people = (
    <span className="flex shrink-0 -space-x-1.5 sm:w-20" aria-label={task.assignees.length ? `Assigned to ${task.assignees.map((a) => a.first_name).join(", ")}` : "Unassigned"}>
      {task.assignees.slice(0, 3).map((a) => <UserAvatar key={a.id} name={a.first_name} src={a.avatar_url} size="sm" />)}
      {task.assignees.length === 0 && <span className="hidden text-xs text-muted-foreground sm:inline">Unassigned</span>}
      {task.assignees.length > 3 && <span className="pl-2.5 text-xs text-muted-foreground">+{task.assignees.length - 3}</span>}
    </span>
  )
  const linkClass = "outline-none transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50"

  if (!inline)
    return (
      <li>
        <Link data-row-link to={to.to as never} params={to.params as never} className={cn("flex min-h-(--row-h) flex-wrap items-center gap-x-4 gap-y-1 px-1 py-2 pointer-coarse:min-h-12", linkClass, task.deleted_at && "opacity-60")}>
          <span className="shrink-0 font-mono text-xs text-muted-foreground sm:w-20">{task.key}</span>
          <span className="min-w-0 flex-1 basis-40 sm:basis-56"><span className="block truncate text-sm font-medium">{task.title}</span>{context}</span>
          <StatusTag name={task.status.name} category={task.status.category} className="shrink-0 sm:w-32" />
          <PriorityTag name={task.priority.name} rank={task.priority.rank} max={maxRank} className="shrink-0 sm:w-24" />
          {people}
          <span className="shrink-0 sm:w-44"><DueDate task={task} hideEmpty /></span>
        </Link>
      </li>
    )

  return (
    <li className="flex min-h-(--row-h) flex-wrap items-center gap-x-3 gap-y-1 px-1 py-1 pointer-coarse:min-h-12">
      <Link data-row-link to={to.to as never} params={to.params as never} className={cn("flex min-w-0 flex-1 basis-56 items-center gap-4 rounded-md py-1", linkClass)}>
        <span className="shrink-0 font-mono text-xs text-muted-foreground sm:w-20">{task.key}</span>
        <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{task.title}</span>{context}</span>
      </Link>
      <span className="shrink-0 sm:w-36">
        <Select value={task.status.id} disabled={!inline.canStatus} onValueChange={(v) => v && v !== task.status.id && inline.onChange(task, { status: v })} onOpenChange={(open) => open && inline.statuses.load()} items={inline.statuses.items.map((x) => ({ value: x.id, label: x.name }))}>
          <SelectTrigger aria-label={`Status of ${task.key}`} className={QUIET}><SelectValue>{() => <StatusTag name={task.status.name} category={task.status.category} />}</SelectValue></SelectTrigger>
          <SelectContent>{inline.statuses.items.map((x) => <SelectItem key={x.id} value={x.id}><StatusTag name={x.name} category={x.category} /></SelectItem>)}<OptionsState source={inline.statuses} /></SelectContent>
        </Select>
      </span>
      <span className="shrink-0 sm:w-28">
        <Select value={task.priority.id} disabled={!inline.canPriority} onValueChange={(v) => v && v !== task.priority.id && inline.onChange(task, { priority: v })} onOpenChange={(open) => open && inline.priorities.load()} items={inline.priorities.items.map((x) => ({ value: x.id, label: x.name }))}>
          <SelectTrigger aria-label={`Priority of ${task.key}`} className={QUIET}><SelectValue>{() => <PriorityTag name={task.priority.name} rank={task.priority.rank} max={maxRank} />}</SelectValue></SelectTrigger>
          <SelectContent>{inline.priorities.items.slice().sort((a, b) => b.rank - a.rank).map((x) => <SelectItem key={x.id} value={x.id}><PriorityTag name={x.name} rank={x.rank} max={maxRank} /></SelectItem>)}<OptionsState source={inline.priorities} /></SelectContent>
        </Select>
      </span>
      {people}
      <span className="shrink-0 sm:w-40"><DueDate task={task} hideEmpty /></span>
    </li>
  )
}
