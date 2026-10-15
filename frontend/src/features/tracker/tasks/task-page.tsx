import { Link, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { DatePicker } from "@/components/patterns/date-picker"
import { MemberPicker } from "@/components/patterns/member-picker"
import { MarkdownEditor, MarkdownView } from "@/components/patterns/markdown-editor"
import { PropertyRow } from "@/components/patterns/property-row"
import { PriorityTag, StatusTag } from "@/components/patterns/work-status"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { can, useCurrentProject } from "@/features/projects/current"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowBendLeftUp, ArrowClockwise, ArrowLeft, PencilSimple, Trash } from "@/icons"
import { plural } from "@/lib/format"
import { isNotFound } from "@/features/projects/errors"
import type { Task, TaskPatch } from "../api"
import { trackerError } from "../errors"
import { useProjectPeople } from "../people"
import { usePriorities, useStatuses, useSubtasks, useTask, useTaskMutations } from "../queries"
import { FilesSection } from "@/features/attachments/files-section"
import { CommentSection } from "../comments/comment-section"
import { TaskNotes } from "../notes/task-notes"
import { DueDate, TaskRow } from "./task-row"
import { QuickAdd } from "./quick-add"
import { useLockText } from "@/features/permissions/use-lock-text"

function EditableTitle({ task, allowed, onSave, saving }: { task: Task; allowed: boolean; onSave: (title: string, done: () => void) => void; saving: boolean }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(task.title)
  const commit = () => {
    const t = value.trim()
    if (t && t !== task.title) onSave(t, () => setEditing(false))
    else { setEditing(false); setValue(task.title) }
  }
  if (editing)
    return (
      <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); commit() }}>
        <Input value={value} autoFocus maxLength={255} aria-label="Task title" className="h-9 text-lg font-semibold" onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Escape") { setValue(task.title); setEditing(false) } }} />
        <Button type="submit" loading={saving} disabled={!value.trim()}>Save</Button>
        <Button variant="outline" onClick={() => { setValue(task.title); setEditing(false) }}>Cancel</Button>
      </form>
    )
  return (
    <div className="flex items-start gap-2">
      <h1 className="min-w-0 flex-1 text-xl font-semibold tracking-tight text-balance">{task.title}</h1>
      {allowed && <Button variant="ghost" size="icon" label="Rename task" onClick={() => { setValue(task.title); setEditing(true) }}><PencilSimple /></Button>}
    </div>
  )
}

function Description({ task, allowed, onSave, saving }: { task: Task; allowed: boolean; onSave: (v: string, done: () => void) => void; saving: boolean }) {
  const lockText = useLockText()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(task.description ?? "")
  if (!editing)
    return (
      <section aria-labelledby="desc" className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 id="desc" className="text-sm font-semibold">Description</h2>
          {allowed && <Button variant="outline" size="sm" icon={<PencilSimple />} onClick={() => { setValue(task.description ?? ""); setEditing(true) }}>Edit</Button>}
        </div>
        <MarkdownView source={task.description ?? ""} empty={allowed ? "No description yet. Add context, links or acceptance criteria." : "No description."} />
        {!allowed && <p className="text-xs text-muted-foreground">{lockText("task.description.change")}</p>}
      </section>
    )
  return (
    <section aria-labelledby="desc" className="space-y-2">
      <h2 id="desc" className="text-sm font-semibold">Description</h2>
      <MarkdownEditor label="Description" value={value} onChange={setValue} autoFocus />
      <div className="flex gap-2">
        <Button loading={saving} onClick={() => onSave(value, () => setEditing(false))}>Save description</Button>
        <Button variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
      </div>
    </section>
  )
}

export function TaskPage({ number }: { number: number }) {
  const { id, project } = useCurrentProject()
  const navigate = useNavigate()
  const { data: task, isPending, error, refetch } = useTask(id, number)
  useDocumentTitle(task ? `${task.key} ${task.title} · Pro-Goal` : "Task · Pro-Goal")
  const statuses = useStatuses(id).data?.items ?? []
  const priorities = usePriorities(id).data?.items ?? []
  const { people } = useProjectPeople(id)
  const { update, remove, restore } = useTaskMutations(id)
  const busy = update.isPending
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [tags, setTags] = useState<string | null>(null)
  const maxRank = Math.max(1, ...priorities.map((p) => p.rank))
  const frozen = project.is_archived
  const allow = (code: string) => can(project, code) && !frozen && !task?.deleted_at && !busy
  const lockText = useLockText()
  const lock = (code: string) => (frozen || task?.deleted_at || can(project, code) ? undefined : lockText(code))

  const save = (patch: TaskPatch, done?: string, after?: () => void) =>
    update.mutate({ number, patch }, { onSuccess: () => { if (done) toast.success(done); after?.() }, onError: (e) => toast.error(trackerError(e)) })

  if (isPending)
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading task">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-7 w-96 max-w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  if (error || !task)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>{isNotFound(error) ? "Task not found" : "Couldn't load this task"}</EmptyTitle>
          <EmptyDescription>{isNotFound(error) ? "It doesn't exist, or it was deleted more than 7 days ago." : trackerError(error)}</EmptyDescription>
        </EmptyHeader>
        {isNotFound(error) ? (
          <Button variant="outline" icon={<ArrowLeft />} nativeButton={false} render={<Link to="/app/projects/$projectId/tasks" params={{ projectId: id }} />}>Back to tasks</Button>
        ) : (
          <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
        )}
      </Empty>
    )

  const isSub = task.parent_number != null
  const tagText = tags ?? task.tags.join(", ")
  const saveTags = () => {
    const next = tagText.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean)
    setTags(null)
    if (next.join(",") !== task.tags.join(",")) save({ tags: next })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <nav aria-label="Task path" className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Link to="/app/projects/$projectId/tasks" params={{ projectId: id }} className="inline-flex min-h-6 items-center gap-1 rounded underline-offset-4 hover:text-foreground hover:underline pointer-coarse:min-h-11"><ArrowLeft className="size-3.5" aria-hidden />Tasks</Link>
          <span aria-hidden>/</span>
          {isSub && <><Link to="/app/projects/$projectId/tasks/$number" params={{ projectId: id, number: String(task.parent_number) }} className="inline-flex min-h-6 items-center font-mono underline-offset-4 hover:text-foreground hover:underline pointer-coarse:min-h-11">{task.project.task_key}-{task.parent_number}</Link><span aria-hidden>/</span></>}
          <span className="font-mono">{task.key}</span>
        </nav>
        <EditableTitle task={task} allowed={allow("task.title.change")} saving={update.isPending} onSave={(title, done) => save({ title }, "Title saved.", done)} />
        {!allow("task.title.change") && !task.deleted_at && !frozen && <p className="text-xs text-muted-foreground">{lockText("task.title.change")}</p>}
      </div>

      <section aria-label="Properties" className="divide-y border-y">
        <PropertyRow label="Status" htmlFor="p-status" lockedBy={lock("task.status.change")}>
          <Select value={task.status.id} disabled={!allow("task.status.change")} onValueChange={(v) => v && v !== task.status.id && save({ status: v })} items={statuses.map((s) => ({ value: s.id, label: s.name }))}>
            <SelectTrigger id="p-status" className="w-56"><SelectValue>{() => <StatusTag name={task.status.name} category={task.status.category} />}</SelectValue></SelectTrigger>
            <SelectContent>{statuses.map((s) => <SelectItem key={s.id} value={s.id}><StatusTag name={s.name} category={s.category} /></SelectItem>)}</SelectContent>
          </Select>
        </PropertyRow>
        <PropertyRow label="Priority" htmlFor="p-priority" lockedBy={lock("task.priority.change")}>
          <Select value={task.priority.id} disabled={!allow("task.priority.change")} onValueChange={(v) => v && v !== task.priority.id && save({ priority: v })} items={priorities.map((p) => ({ value: p.id, label: p.name }))}>
            <SelectTrigger id="p-priority" className="w-56"><SelectValue>{() => <PriorityTag name={task.priority.name} rank={task.priority.rank} max={maxRank} />}</SelectValue></SelectTrigger>
            <SelectContent>{priorities.slice().sort((a, b) => b.rank - a.rank).map((p) => <SelectItem key={p.id} value={p.id}><PriorityTag name={p.name} rank={p.rank} max={maxRank} /></SelectItem>)}</SelectContent>
          </Select>
        </PropertyRow>
        <PropertyRow label="Assignees" htmlFor="p-assignees" lockedBy={lock("task.assignees.change")}>
          <MemberPicker id="p-assignees" people={people} value={task.assignees.map((a) => a.id)} disabled={!allow("task.assignees.change")} onChange={(ids) => save({ assignees: ids })} />
        </PropertyRow>
        <PropertyRow label="Start date" htmlFor="p-start" lockedBy={lock("task.start_date.change")}>
          <DatePicker id="p-start" placeholder="No start date" value={task.start_date} disabled={!allow("task.start_date.change")} onChange={(v) => save({ start_date: v })} />
        </PropertyRow>
        <PropertyRow label="Due date" htmlFor="p-due" lockedBy={lock("task.due_date.change")}>
          <div className="flex flex-wrap items-center gap-3">
            <DatePicker id="p-due" placeholder="No due date" value={task.due_date} disabled={!allow("task.due_date.change")} onChange={(v) => save({ due_date: v })} />
            {task.due_date && <DueDate task={task} />}
          </div>
        </PropertyRow>
        <PropertyRow label="Tags" htmlFor="p-tags" lockedBy={lock("task.tags.change")}>
          <Input id="p-tags" value={tagText} disabled={!allow("task.tags.change")} placeholder="Comma-separated, e.g. bug, design" maxLength={200} className="max-w-sm" onChange={(e) => setTags(e.target.value)} onBlur={saveTags} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); saveTags() } }} />
        </PropertyRow>
        {isSub && (
          <PropertyRow label="Parent" lockedBy={lock("task.parent.change")}>
            <span className="flex flex-wrap items-center gap-3 text-sm">
              <Link to="/app/projects/$projectId/tasks/$number" params={{ projectId: id, number: String(task.parent_number) }} className="font-mono text-primary underline-offset-4 hover:underline">{task.project.task_key}-{task.parent_number}</Link>
              <Button size="sm" variant="outline" icon={<ArrowBendLeftUp />} disabled={!allow("task.parent.change")} onClick={() => save({ parent: null }, "Now a top-level task.")}>Make top-level</Button>
            </span>
          </PropertyRow>
        )}
      </section>

      <Description task={task} allowed={allow("task.description.change")} saving={update.isPending} onSave={(description, done) => save({ description }, "Description saved.", done)} />

      <TaskNotes number={number} archived={frozen || !!task.deleted_at} />

      <FilesSection target={{ type: "task", id: number }} archived={frozen || !!task.deleted_at} />

      <CommentSection number={number} />

      {!isSub && <SubtaskSection projectId={id} task={task} maxRank={maxRank} allowed={can(project, "task.create")} archived={frozen || !!task.deleted_at} />}

      {can(project, "task.delete") && !task.deleted_at && !frozen && (
        <section aria-label="Delete" className="border-t pt-6">
          <Button variant="destructive" icon={<Trash />} onClick={() => setConfirmDelete(true)}>Delete task…</Button>
        </section>
      )}
      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {task.key}?</AlertDialogTitle>
            <AlertDialogDescription>
              {task.subtasks.total > 0 ? `Its ${plural(task.subtasks.total, "subtask")} are deleted too. ` : ""}It disappears for everyone. Right after deleting you get a few seconds to undo it.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} loading={remove.isPending} onClick={() => remove.mutate(number, {
              onSuccess: () => {
                setConfirmDelete(false)
                toast.success(`${task.key} deleted.`, { action: { label: "Undo", onClick: () => restore.mutate(number, { onSuccess: () => toast.success(`${task.key} restored.`), onError: (e) => toast.error(trackerError(e)) }) }, duration: 9000 })
                navigate({ to: "/app/projects/$projectId/tasks", params: { projectId: id }, replace: true })
              },
              onError: (e) => { setConfirmDelete(false); toast.error(trackerError(e)) },
            })}>Delete task</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function SubtaskSection({ projectId, task, maxRank, allowed, archived }: { projectId: string; task: Task; maxRank: number; allowed: boolean; archived: boolean }) {
  const { data } = useSubtasks(projectId, task.number)
  const items = data?.items ?? []
  return (
    <section aria-labelledby="subtasks" className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 id="subtasks" className="text-sm font-semibold">Subtasks</h2>
        {task.subtasks.total > 0 && <span className="text-xs text-muted-foreground tabular-nums">{task.subtasks.done} of {task.subtasks.total} done</span>}
      </div>
      {items.length > 0 && (
        <ul className="divide-y border-y" aria-label="Subtasks">
          {items.map((t) => <TaskRow key={t.id} task={t} maxRank={maxRank} to={{ to: "/app/projects/$projectId/tasks/$number", params: { projectId, number: String(t.number) } }} />)}
        </ul>
      )}
      <QuickAdd projectId={projectId} parent={task.number} allowed={allowed} archived={archived} placeholder="Add a subtask" />
    </section>
  )
}
