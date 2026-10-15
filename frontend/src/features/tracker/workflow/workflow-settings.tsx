import { useState } from "react"
import { toast } from "sonner"
import { PriorityTag, StatusTag } from "@/components/patterns/work-status"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowDown, ArrowUp, Check, PencilSimple, Plus, Trash } from "@/icons"
import { ApiError } from "@/lib/api"
import type { Priority, Status, StatusCategory } from "../api"
import { trackerError } from "../errors"
import { usePriorities, useStatuses, useWorkflowMutations } from "../queries"

const CATEGORIES: { value: StatusCategory; label: string }[] = [
  { value: "todo", label: "To do" },
  { value: "in_progress", label: "In progress" },
  { value: "done", label: "Done" },
]

interface Row {
  id: string
  name: string
  position: number
  is_default: boolean
}

/** A move target: another item, chosen when tasks still use the one being deleted. */
function MoveDialog({ open, onOpenChange, what, name, options, onConfirm, pending }: { open: boolean; onOpenChange: (o: boolean) => void; what: string; name: string; options: { value: string; label: string }[]; onConfirm: (to: string) => void; pending: boolean }) {
  const [to, setTo] = useState<string | null>(null)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {name}?</DialogTitle>
          <DialogDescription>Tasks still use this {what}. Choose where they go. This can't be undone.</DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="move-to">Move those tasks to</FieldLabel>
          <Select value={to} onValueChange={setTo} items={options}>
            <SelectTrigger id="move-to" className="w-full"><SelectValue placeholder={`Choose a ${what}`} /></SelectTrigger>
            <SelectContent>{options.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button variant="solid-destructive" icon={<Trash />} loading={pending} disabled={!to} onClick={() => to && onConfirm(to)}>Move tasks and delete</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ItemRow({ item, index, count, label, onRename, onMove, onDefault, onDelete, busy, canUpdate, canDelete }: { item: Row; index: number; count: number; label: React.ReactNode; onRename: (name: string) => void; onMove: (dir: -1 | 1) => void; onDefault: () => void; onDelete: () => void; busy: boolean; canUpdate: boolean; canDelete: boolean }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(item.name)
  return (
    <li className="flex min-h-12 flex-wrap items-center gap-x-3 gap-y-1 py-1.5">
      {editing ? (
        <form className="flex flex-1 items-center gap-2" onSubmit={(e) => { e.preventDefault(); setEditing(false); if (name.trim() && name.trim() !== item.name) onRename(name.trim()) }}>
          <Input value={name} autoFocus maxLength={50} aria-label="Name" onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Escape" && setEditing(false)} />
          <Button type="submit" size="sm" icon={<Check weight="bold" />}>Save</Button>
          <Button type="button" size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
        </form>
      ) : (
        <span className="min-w-0 flex-1">{label}{item.is_default && <span className="ml-2 text-xs text-muted-foreground">Default</span>}</span>
      )}
      {!editing && (
        <span className="flex items-center">
          <Button variant="ghost" size="icon" label={`Move ${item.name} up`} disabled={!canUpdate || index === 0 || busy} onClick={() => onMove(-1)}><ArrowUp /></Button>
          <Button variant="ghost" size="icon" label={`Move ${item.name} down`} disabled={!canUpdate || index === count - 1 || busy} onClick={() => onMove(1)}><ArrowDown /></Button>
          <Button variant="ghost" size="icon" label={`Rename ${item.name}`} disabled={!canUpdate} onClick={() => { setName(item.name); setEditing(true) }}><PencilSimple /></Button>
          {!item.is_default && <Button variant="ghost" size="sm" disabled={!canUpdate || busy} onClick={onDefault}>Make default</Button>}
          {item.is_default ? <span className="px-2 text-xs text-muted-foreground">Make another the default to delete</span> : <Button variant="ghost" size="icon" label={`Delete ${item.name}`} disabled={!canDelete} onClick={onDelete}><Trash /></Button>}
        </span>
      )}
    </li>
  )
}

function AddForm({ placeholder, onAdd, children, busy }: { placeholder: string; onAdd: (name: string) => void; children?: React.ReactNode; busy: boolean }) {
  const [name, setName] = useState("")
  return (
    <form className="flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) { onAdd(name.trim()); setName("") } }}>
      <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={placeholder} aria-label={placeholder} maxLength={50} className="w-56" />
      {children}
      <Button type="submit" variant="outline" icon={<Plus weight="bold" />} loading={busy} disabled={!name.trim()}>Add</Button>
    </form>
  )
}

/** Owner-only: the statuses and priorities every task in the project draws from. */
export interface WorkflowAccess {
  statusCreate: boolean
  statusUpdate: boolean
  statusDelete: boolean
  priorityCreate: boolean
  priorityUpdate: boolean
  priorityDelete: boolean
}

export function workflowAccess(has: (code: string) => boolean, frozen: boolean): WorkflowAccess {
  const f = (code: string) => has(code) && !frozen
  return { statusCreate: f("status.create"), statusUpdate: f("status.update"), statusDelete: f("status.delete"), priorityCreate: f("priority.create"), priorityUpdate: f("priority.update"), priorityDelete: f("priority.delete") }
}

function Locked({ code, frozen }: { code: string; frozen: boolean }) {
  return <p className="text-xs text-muted-foreground">{frozen ? "This project is archived." : <>Needs the <code className="font-mono">{code}</code> permission to add.</>}</p>
}

export function WorkflowSettings({ projectId, access, frozen }: { projectId: string; access: WorkflowAccess; frozen: boolean }) {
  const statuses = useStatuses(projectId).data?.items ?? []
  const priorities = usePriorities(projectId).data?.items ?? []
  const m = useWorkflowMutations(projectId)
  const maxRank = Math.max(1, ...priorities.map((p) => p.rank))
  const [category, setCategory] = useState<StatusCategory>("todo")
  const [pending, setPending] = useState<{ kind: "status" | "priority"; id: string; name: string } | null>(null)
  const fail = (e: unknown) => toast.error(trackerError(e))

  const swap = <T extends Row>(items: T[], index: number, dir: -1 | 1, run: (id: string, position: number) => void) => {
    const other = items[index + dir]
    if (other) run(items[index].id, other.position)
  }
  const del = (kind: "status" | "priority", item: Row, moveTo?: string) => {
    const mut = kind === "status" ? m.deleteStatus : m.deletePriority
    mut.mutate({ id: item.id, moveTo }, {
      onSuccess: () => { setPending(null); toast.success(`${item.name} deleted.`) },
      onError: (e) => {
        if (e instanceof ApiError && (e.code === "in_use_needs_replacement" || e.code === "invalid_replacement")) setPending({ kind, id: item.id, name: item.name })
        else { setPending(null); fail(e) }
      },
    })
  }
  const options = pending?.kind === "status" ? statuses.filter((s) => s.id !== pending.id).map((s) => ({ value: s.id, label: s.name })) : priorities.filter((p) => p.id !== pending?.id).map((p) => ({ value: p.id, label: p.name }))

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h3 className="text-sm font-medium">Statuses</h3>
        <p className="text-sm text-muted-foreground">Each belongs to a group (To do, In progress, Done). Groups drive overdue and the rule that a task can't be done while subtasks are open.</p>
        {CATEGORIES.map((c) => {
          const rows = statuses.filter((s) => s.category === c.value)
          return (
            <div key={c.value}>
              <p className="pt-2 text-xs font-medium text-muted-foreground">{c.label}</p>
              <ul className="divide-y border-y" aria-label={`${c.label} statuses`}>
                {rows.map((s: Status, i) => (
                  <ItemRow key={s.id} item={s} index={i} count={rows.length} canUpdate={access.statusUpdate} canDelete={access.statusDelete} busy={m.updateStatus.isPending}
                    label={<StatusTag name={s.name} category={s.category} />}
                    onRename={(name) => m.updateStatus.mutate({ id: s.id, patch: { name } }, { onError: fail })}
                    onMove={(dir) => swap(rows, i, dir, (id, position) => m.updateStatus.mutate({ id, patch: { position } }, { onError: fail }))}
                    onDefault={() => m.updateStatus.mutate({ id: s.id, patch: { is_default: true } }, { onSuccess: () => toast.success(`${s.name} is now the default.`), onError: fail })}
                    onDelete={() => del("status", s)} />
                ))}
              </ul>
            </div>
          )
        })}
        {access.statusCreate ? (
          <AddForm placeholder="New status" busy={m.createStatus.isPending} onAdd={(name) => m.createStatus.mutate({ name, category }, { onSuccess: () => toast.success(`${name} added.`), onError: fail })}>
            <Select value={category} onValueChange={(v) => v && setCategory(v as StatusCategory)} items={CATEGORIES}>
              <SelectTrigger aria-label="Group" className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectContent>
            </Select>
          </AddForm>
        ) : (
          <Locked code="status.create" frozen={frozen} />
        )}
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium">Priorities</h3>
        <p className="text-sm text-muted-foreground">Listed from highest to lowest. New tasks start with the default.</p>
        <ul className="divide-y border-y" aria-label="Priorities">
          {priorities.slice().sort((a, b) => b.rank - a.rank).map((p: Priority, i, arr) => (
            <ItemRow key={p.id} item={p} index={i} count={arr.length} canUpdate={access.priorityUpdate} canDelete={access.priorityDelete} busy={m.updatePriority.isPending}
              label={<PriorityTag name={p.name} rank={p.rank} max={maxRank} />}
              onRename={(name) => m.updatePriority.mutate({ id: p.id, patch: { name } }, { onError: fail })}
              onMove={(dir) => swap(arr, i, dir, (id, position) => m.updatePriority.mutate({ id, patch: { position } }, { onError: fail }))}
              onDefault={() => m.updatePriority.mutate({ id: p.id, patch: { is_default: true } }, { onSuccess: () => toast.success(`${p.name} is now the default.`), onError: fail })}
              onDelete={() => del("priority", p)} />
          ))}
        </ul>
        {access.priorityCreate ? <AddForm placeholder="New priority" busy={m.createPriority.isPending} onAdd={(name) => m.createPriority.mutate({ name }, { onSuccess: () => toast.success(`${name} added.`), onError: fail })} /> : <Locked code="priority.create" frozen={frozen} />}
      </div>

      <MoveDialog key={pending?.id ?? "none"} open={!!pending} onOpenChange={(o) => !o && setPending(null)} what={pending?.kind ?? "status"} name={pending?.name ?? ""} options={options} pending={m.deleteStatus.isPending || m.deletePriority.isPending}
        onConfirm={(to) => { const item = (pending?.kind === "status" ? statuses : priorities).find((x) => x.id === pending?.id); if (pending && item) del(pending.kind, item, to) }} />
    </div>
  )
}
