import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { can, useCurrentProject } from "@/features/projects/current"
import { LinkSimple, LinkBreak, NotePencil } from "@/icons"
import { trackerError } from "../errors"
import { useNoteMutations, useNotes, useTaskNotes } from "../queries"

function Picker({ projectId, number, linked, disabled }: { projectId: string; number: number; linked: Set<string>; disabled: boolean }) {
  const [q, setQ] = useState("")
  const [open, setOpen] = useState(false)
  const { data, isPending } = useNotes(projectId, q, "", 1)
  const { link } = useNoteMutations(projectId)
  const options = (data?.items ?? []).filter((n) => !linked.has(n.id))
  return (
    <Popover open={open} onOpenChange={(o) => { setOpen(o); if (!o) setQ("") }}>
      <PopoverTrigger render={<Button variant="outline" size="sm" icon={<LinkSimple />} disabled={disabled}>Link a note</Button>} />
      <PopoverContent align="start" className="w-72 gap-2 p-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search notes" aria-label="Search notes to link" autoFocus />
        <ul className="max-h-56 overflow-auto" aria-label="Notes">
          {isPending && <li className="px-2 py-1.5 text-sm text-muted-foreground">Loading…</li>}
          {!isPending && options.length === 0 && <li className="px-2 py-1.5 text-sm text-muted-foreground">{q ? "No notes match." : "No other notes to link."}</li>}
          {options.map((n) => (
            <li key={n.id}>
              <button type="button" className="flex min-h-8 w-full items-center rounded-md px-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:min-h-11" onClick={() => link.mutate({ number, noteId: n.id }, { onSuccess: () => { setOpen(false); toast.success("Note linked.") }, onError: (e) => toast.error(trackerError(e)) })}>
                <span className="truncate">{n.title}</span>
              </button>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  )
}

/** Notes attached to a task: open one, unlink it, or link another from the project's notes. */
export function TaskNotes({ number, archived }: { number: number; archived: boolean }) {
  const { id, project } = useCurrentProject()
  const { data } = useTaskNotes(id, number)
  const { unlink } = useNoteMutations(id)
  const items = data?.items ?? []
  const allowed = can(project, "note.link.change") && !archived
  return (
    <section aria-labelledby="task-notes" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 id="task-notes" className="text-sm font-semibold">Notes</h2>
        <Picker projectId={id} number={number} linked={new Set(items.map((n) => n.id))} disabled={!allowed} />
      </div>
      {items.length > 0 ? (
        <ul className="divide-y border-y" aria-label="Linked notes">
          {items.map((n) => (
            <li key={n.id} className="flex min-h-(--row-h) items-center gap-2 py-1.5">
              <NotePencil className="size-4 shrink-0 text-muted-foreground" aria-hidden />
              <Link to="/app/projects/$projectId/notes/$noteId" params={{ projectId: id, noteId: n.id }} className="min-w-0 flex-1 truncate rounded text-sm font-medium underline-offset-4 hover:underline">{n.title}</Link>
              <Button variant="ghost" size="icon" label={`Unlink ${n.title}`} disabled={!allowed || unlink.isPending} onClick={() => unlink.mutate({ number, noteId: n.id }, { onSuccess: () => toast.success("Note unlinked."), onError: (e) => toast.error(trackerError(e)) })}><LinkBreak /></Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No notes linked.</p>
      )}
      {!allowed && !archived && <p className="text-xs text-muted-foreground">Needs the <code className="font-mono">note.link.change</code> permission to link notes.</p>}
    </section>
  )
}
