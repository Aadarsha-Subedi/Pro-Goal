import { Link, useNavigate } from "@tanstack/react-router"
import { useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { FilesSection } from "@/features/attachments/files-section"
import { uploadImage } from "@/features/attachments/image-upload"
import { InlineImage } from "@/features/attachments/inline-image"
import { MarkdownEditor, MarkdownImages, MarkdownView } from "@/components/patterns/markdown-editor"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { can, useCurrentProject } from "@/features/projects/current"
import { isNotFound } from "@/features/projects/errors"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowCounterClockwise, ArrowLeft, ClockCounterClockwise, Copy, PencilSimple, Trash, Warning } from "@/icons"
import { cn } from "@/lib/utils"
import type { Note } from "../api"
import { isStale, trackerError } from "../errors"
import { renderMentions } from "../mentions"
import { useProjectPeople } from "../people"
import { useNote, useNoteMutations, useRevisions } from "../queries"

const stamp = (iso: string) => new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" })
/** `base` is the note version the draft started from; it is what Save sends, so the lock holds across tabs and days. */
type Draft = { base: number; title: string; body: string; tags: string }
const draftKey = (noteId: string) => `pg.note-draft.${noteId}`
function readDraft(noteId: string): Draft | null {
  try {
    const raw = localStorage.getItem(draftKey(noteId))
    return raw ? (JSON.parse(raw) as Draft) : null
  } catch {
    return null
  }
}
function writeDraft(noteId: string, d: Draft | null) {
  try {
    if (d) localStorage.setItem(draftKey(noteId), JSON.stringify(d))
    else localStorage.removeItem(draftKey(noteId))
  } catch {
    // Storage blocked: the draft lives only in memory.
  }
}
const parseTags = (s: string) => s.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean)

function Revisions({ note, canRestore }: { note: Note; canRestore: boolean }) {
  const { id } = useCurrentProject()
  const [open, setOpen] = useState(false)
  const [viewing, setViewing] = useState<string | null>(null)
  const { data, isPending, isError, refetch } = useRevisions(id, note.id, open)
  const { update } = useNoteMutations(id)
  const qc = useQueryClient()
  const { byId } = useProjectPeople(id)
  const items = data?.items ?? []
  return (
    <section aria-labelledby="revisions" className="space-y-2 border-t pt-6">
      <div className="flex items-center justify-between">
        <h2 id="revisions" className="text-sm font-semibold">Revisions</h2>
        <Button variant="outline" size="sm" icon={<ClockCounterClockwise />} aria-expanded={open} onClick={() => setOpen((o) => !o)}>{open ? "Hide history" : "Show history"}</Button>
      </div>
      {open && (isPending ? <Skeleton className="h-16 w-full" aria-busy="true" /> : isError ? (
        <div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground">Couldn't load history.</span><Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></div>
      ) : (
        <ul className="divide-y border-y" aria-label="Revisions">
          {items.map((r) => (
            <li key={r.id} className="space-y-2 py-2">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-mono text-xs text-muted-foreground">v{r.version}</span>
                <span className="min-w-0 flex-1 truncate text-sm">{r.title}</span>
                <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"><UserAvatar name={r.edited_by.first_name} src={r.edited_by.avatar_url} size="sm" />{r.edited_by.first_name} · {stamp(r.created_at)}</span>
                <Button variant="ghost" size="sm" aria-expanded={viewing === r.id} onClick={() => setViewing(viewing === r.id ? null : r.id)}>{viewing === r.id ? "Hide" : "View"}</Button>
                {r.version !== note.version && (
                  <Button variant="outline" size="sm" icon={<ArrowCounterClockwise />} disabled={!canRestore || update.isPending} onClick={() => update.mutate({ id: note.id, input: { version: note.version, title: r.title, body: r.body } }, { onSuccess: () => toast.success(`Restored v${r.version} as a new version.`), onError: (e) => { toast.error(isStale(e) ? "The note changed. Reloaded the latest, try again." : trackerError(e)); if (isStale(e)) void qc.invalidateQueries({ queryKey: ["note", id] }) } })}>Restore this version</Button>
                )}
              </div>
              {viewing === r.id && <div className="rounded-md bg-muted/40 p-3"><MarkdownView source={renderMentions(r.body, byId)} empty="This version was empty." /></div>}
            </li>
          ))}
        </ul>
      ))}
    </section>
  )
}

export function NotePage({ noteId, startEditing }: { noteId: string; startEditing: boolean }) {
  const { id, project } = useCurrentProject()
  const navigate = useNavigate()
  const { data: note, isPending, error, refetch } = useNote(id, noteId)
  useDocumentTitle(note ? `${note.title} · Pro-Goal` : "Note · Pro-Goal")
  const { update, remove } = useNoteMutations(id)
  const { byId } = useProjectPeople(id)
  const [editing, setEditing] = useState(startEditing)
  const [draft, setDraftState] = useState<Draft | null>(() => (startEditing ? readDraft(noteId) : null))
  const [discard, setDiscard] = useState(false)
  const setDraft = (d: Draft | null) => { setDraftState(d); writeDraft(noteId, d) }
  const [stale, setStale] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const frozen = project.is_archived
  const perms = { title: can(project, "note.title.change") && !frozen, body: can(project, "note.body.change") && !frozen, tags: can(project, "note.tags.change") && !frozen }
  const canEdit = perms.title || perms.body || perms.tags
  const dirty = editing && !!draft && !!note && (draft.title !== note.title || draft.body !== (note.body ?? "") || draft.tags !== note.tags.join(", "))
  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [dirty])

  if (isPending) return <div className="space-y-4" aria-busy="true" aria-label="Loading note"><Skeleton className="h-7 w-80" /><Skeleton className="h-40 w-full" /></div>
  if (error || !note)
    return (
      <Empty>
        <EmptyHeader><EmptyTitle>{isNotFound(error) ? "Note not found" : "Couldn't load this note"}</EmptyTitle><EmptyDescription>{isNotFound(error) ? "It doesn't exist or was deleted." : trackerError(error)}</EmptyDescription></EmptyHeader>
        {isNotFound(error) ? <Button variant="outline" icon={<ArrowLeft />} nativeButton={false} render={<Link to="/app/projects/$projectId/notes" params={{ projectId: id }} />}>Back to notes</Button> : <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>}
      </Empty>
    )

  const d: Draft = draft ?? { base: note.version, title: note.title, body: note.body ?? "", tags: note.tags.join(", ") }
  const behind = editing && d.base !== note.version
  const begin = () => {
    // A draft left from an earlier session comes back; it is never silently dropped.
    const saved = readDraft(note.id)
    setDraftState(saved && typeof saved.base === "number" ? saved : { base: note.version, title: note.title, body: note.body ?? "", tags: note.tags.join(", ") })
    if (saved) toast.info("Restored your unsaved draft.")
    setStale(false)
    setEditing(true)
  }
  const cancel = () => {
    setEditing(false)
    setDraft(null)
    setDiscard(false)
    setStale(false)
    if (startEditing) navigate({ to: "/app/projects/$projectId/notes/$noteId", params: { projectId: id, noteId }, search: {}, replace: true })
  }
  const save = () => {
    const input: { version: number; title?: string; body?: string; tags?: string[] } = { version: d.base }
    if (perms.title && d.title.trim() !== note.title) input.title = d.title.trim()
    if (perms.body && d.body !== (note.body ?? "")) input.body = d.body
    if (perms.tags && parseTags(d.tags).join(",") !== note.tags.join(",")) input.tags = parseTags(d.tags)
    if (Object.keys(input).length === 1) return cancel()
    update.mutate({ id: note.id, input }, {
      onSuccess: () => { toast.success("Note saved."); cancel() },
      onError: (e) => (isStale(e) ? setStale(true) : toast.error(trackerError(e))),
    })
  }
  // The draft only exists while editing; opening `?edit` straight from "New note" seeds it on first render.
  const showEditor = editing

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <nav aria-label="Note path" className="text-sm text-muted-foreground"><Link to="/app/projects/$projectId/notes" params={{ projectId: id }} className="inline-flex min-h-6 items-center gap-1 rounded underline-offset-4 hover:text-foreground hover:underline pointer-coarse:min-h-11"><ArrowLeft className="size-3.5" aria-hidden />Notes</Link></nav>
        {showEditor ? (
          <Field>
            <FieldLabel htmlFor="n-title">Title</FieldLabel>
            <Input id="n-title" value={d.title} disabled={!perms.title} maxLength={255} className="h-9 text-lg font-semibold" onChange={(e) => setDraft({ ...d, title: e.target.value })} />
          </Field>
        ) : (
          <div className="flex items-start gap-2">
            <h1 className="min-w-0 flex-1 text-xl font-semibold tracking-tight text-balance">{note.title}</h1>
            <Button variant="outline" icon={<PencilSimple />} disabled={!canEdit} onClick={begin}>Edit</Button>
          </div>
        )}
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5"><UserAvatar name={note.author.first_name} src={note.author.avatar_url} size="sm" />{note.author.first_name}</span>
          <span>Updated {stamp(note.updated_at)}</span>
          <span className="font-mono">v{note.version}</span>
        </p>
        {!canEdit && !frozen && <p className="text-xs text-muted-foreground">Needs a <code className="font-mono">note.*.change</code> permission to edit.</p>}
        {frozen && <p className="text-xs text-muted-foreground">This project is archived, so notes are read-only.</p>}
      </div>

      {(stale || behind) && (
        <div role="alert" className="space-y-2 border-y py-3">
          <p className="flex items-center gap-2 text-sm font-medium"><Warning weight="fill" className="size-4 text-warning" aria-hidden />Someone else changed this note while you were editing.</p>
          <p className="text-sm text-muted-foreground">Nothing was overwritten, and your text is still here. Read their version, then choose.</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" icon={<Copy />} onClick={() => navigator.clipboard?.writeText(`${d.title}\n\n${d.body}`).then(() => toast.success("Your text is copied."), () => toast.error("Couldn't copy. Select the text and copy it by hand."))}>Copy my text</Button>
            <Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => { void refetch().then((r) => { if (r.data) { setDraft(null); setStale(false); setEditing(true) } }) }}>Discard mine, load latest</Button>
            <Button size="sm" variant="destructive" onClick={() => { void refetch().then((r) => { if (r.data) update.mutate({ id: note.id, input: { version: r.data.version, ...(perms.title ? { title: d.title.trim() } : {}), ...(perms.body ? { body: d.body } : {}), ...(perms.tags ? { tags: parseTags(d.tags) } : {}) } }, { onSuccess: () => { toast.success("Saved over their version. It is in the revision history."); cancel() }, onError: (e) => toast.error(trackerError(e)) }) }) }}>Keep mine, replace theirs</Button>
          </div>
        </div>
      )}

      {showEditor ? (
        <section aria-label="Edit note" className="space-y-4">
          <MarkdownImages.Provider value={(aid, alt) => <InlineImage projectId={id} id={aid} alt={alt} />}>
            <MarkdownEditor label="Note body" value={d.body} onChange={(body) => setDraft({ ...d, body })} disabled={!perms.body} minRows={14} imageUpload={can(project, "attachment.create") && !frozen ? (f) => uploadImage(id, { type: "note", id: note.id }, f) : undefined} />
          </MarkdownImages.Provider>
          <Field>
            <FieldLabel htmlFor="n-tags">Tags</FieldLabel>
            <Input id="n-tags" value={d.tags} disabled={!perms.tags} placeholder="Comma-separated, e.g. spec, decision" className="max-w-sm" onChange={(e) => setDraft({ ...d, tags: e.target.value })} />
            <FieldDescription>Up to 10, lowercase.</FieldDescription>
          </Field>
          <div className="flex gap-2">
            <Button loading={update.isPending} disabled={!d.title.trim() || stale || behind} onClick={save}>Save note</Button>
            <Button variant="outline" onClick={() => (dirty ? setDiscard(true) : cancel())}>Cancel</Button>
            {dirty && <span className="self-center text-xs text-muted-foreground">Unsaved changes. A draft is kept on this device.</span>}
          </div>
        </section>
      ) : (
        <section aria-label="Note body" className={cn("max-w-3xl")}>
          <MarkdownImages.Provider value={(aid, alt) => <InlineImage projectId={id} id={aid} alt={alt} />}>
            <MarkdownView source={renderMentions(note.body ?? "", byId)} empty="This note is empty." />
          </MarkdownImages.Provider>
          {note.tags.length > 0 && <p className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">{note.tags.map((t) => <Link key={t} to="/app/projects/$projectId/notes" params={{ projectId: id }} search={{ tag: t }} className="rounded underline-offset-4 hover:underline">#{t}</Link>)}</p>}
        </section>
      )}

      <FilesSection target={{ type: "note", id: note.id }} />

      <Revisions note={note} canRestore={perms.body && perms.title} />

      {can(project, "note.delete") && !frozen && (
        <section aria-label="Delete" className="border-t pt-6"><Button variant="destructive" icon={<Trash />} onClick={() => setConfirm(true)}>Delete note…</Button></section>
      )}
      <AlertDialog open={discard} onOpenChange={setDiscard}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard your changes?</AlertDialogTitle>
            <AlertDialogDescription>The edits you haven't saved, and the draft kept on this device, are deleted.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep editing</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} onClick={cancel}>Discard changes</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog open={confirm} onOpenChange={setConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{note.title}"?</AlertDialogTitle>
            <AlertDialogDescription>The note and its revisions are deleted for good, and it is unlinked from every task. This can't be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} loading={remove.isPending} onClick={() => remove.mutate(note.id, { onSuccess: () => { toast.success("Note deleted."); navigate({ to: "/app/projects/$projectId/notes", params: { projectId: id }, replace: true }) }, onError: (e) => { setConfirm(false); toast.error(trackerError(e)) } })}>Delete note</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
