import { Link, useNavigate } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { PageHeader } from "@/components/patterns/page-header"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { can, useCurrentProject } from "@/features/projects/current"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, ArrowRight, MagnifyingGlass, Plus, X } from "@/icons"
import { formatTimestamp } from "@/lib/format"
import { trackerError } from "../errors"
import { useNoteMutations, useNotes } from "../queries"
import { PAGE_SIZE } from "../search"

export interface NoteSearch {
  q?: string
  tag?: string
  page?: number
}

export function validateNoteSearch(s: Record<string, unknown>): NoteSearch {
  const t = (v: unknown, max: number) => { const x = typeof v === "number" ? String(v) : v; return typeof x === "string" && x.trim() ? x.trim().slice(0, max) : undefined }
  const page = Number(s.page)
  return { q: t(s.q, 100), tag: t(s.tag, 30), page: Number.isInteger(page) && page > 1 && page <= 10_000 ? page : undefined }
}

function NewNote({ projectId, allowed }: { projectId: string; allowed: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button icon={<Plus weight="bold" />} disabled={!allowed}>New note</Button>} />
      <DialogContent>{open && <NewNoteForm projectId={projectId} onClose={() => setOpen(false)} />}</DialogContent>
    </Dialog>
  )
}

function NewNoteForm({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const [title, setTitle] = useState("")
  const [error, setError] = useState<string | null>(null)
  const { create } = useNoteMutations(projectId)
  const navigate = useNavigate()
  return (
    <>
      <DialogHeader>
        <DialogTitle>New note</DialogTitle>
        <DialogDescription>Give it a title. You write the body on the next screen.</DialogDescription>
      </DialogHeader>
      <form id="new-note" className="space-y-2" onSubmit={(e) => {
        e.preventDefault()
        if (!title.trim()) return
        create.mutate({ title: title.trim() }, { onSuccess: (n) => { onClose(); navigate({ to: "/app/projects/$projectId/notes/$noteId", params: { projectId, noteId: n.id }, search: { edit: true } }) }, onError: (err) => setError(trackerError(err)) })
      }}>
        <Field>
          <FieldLabel htmlFor="note-title">Title</FieldLabel>
          <Input id="note-title" value={title} maxLength={255} autoFocus onChange={(e) => { setTitle(e.target.value); setError(null) }} aria-invalid={!!error} />
        </Field>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      </form>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button type="submit" form="new-note" icon={<Plus weight="bold" />} loading={create.isPending} disabled={!title.trim()}>Create note</Button>
      </DialogFooter>
    </>
  )
}

export function NotesPage({ search, onSearch }: { search: NoteSearch; onSearch: (n: NoteSearch) => void }) {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Notes · ${project.name} · Pro-Goal`)
  const page = search.page ?? 1
  const { data, isPending, isError, isFetching, refetch } = useNotes(id, search.q ?? "", search.tag ?? "", page)
  const [q, setQ] = useState(search.q ?? "")
  const commit = useRef(onSearch)
  useEffect(() => { commit.current = onSearch })
  useEffect(() => {
    if (q.trim() === (search.q ?? "")) return
    const t = setTimeout(() => commit.current({ ...search, q: q.trim() || undefined, page: undefined }), 400)
    return () => clearTimeout(t)
  }, [q, search])
  const items = data?.items ?? []
  const count = data?.meta.count ?? 0
  const first = (page - 1) * PAGE_SIZE + 1
  const lastPage = Math.max(1, Math.ceil(count / PAGE_SIZE))
  const overshoot = !!data && items.length === 0 && count > 0 && page > lastPage
  useEffect(() => {
    if (overshoot) onSearch({ ...search, page: lastPage > 1 ? lastPage : undefined })
  }, [overshoot, lastPage, search, onSearch])
  const filtered = !!(search.q || search.tag)

  return (
    <div className="space-y-5">
      <PageHeader title="Notes" description="Long-form writing for the project. Link a note to a task from the task page." actions={<NewNote projectId={id} allowed={can(project, "note.create") && !project.is_archived} />} />
      {!can(project, "note.create") && <p className="text-xs text-muted-foreground">Needs the <code className="font-mono">note.create</code> permission to add notes.</p>}
      <div role="search" aria-label="Filter notes" className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <MagnifyingGlass className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search notes" aria-label="Search notes" className="w-56 pl-8" />
        </div>
        {search.tag && <Button variant="outline" icon={<X />} onClick={() => onSearch({ ...search, tag: undefined, page: undefined })}>#{search.tag}</Button>}
      </div>

      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading notes">{[0, 1, 2].map((i) => <li key={i} className="px-1 py-3"><Skeleton className="h-4 w-64 max-w-full" /></li>)}</ul>
      ) : isError ? (
        <Empty>
          <EmptyHeader><EmptyTitle>Couldn't load notes</EmptyTitle><EmptyDescription>Check your connection and try again.</EmptyDescription></EmptyHeader>
          <Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button>
        </Empty>
      ) : items.length === 0 && count > 0 ? null : items.length === 0 ? (
        filtered ? (
          <Empty><EmptyHeader><EmptyTitle>No notes match</EmptyTitle><EmptyDescription>Change the search or clear the tag.</EmptyDescription></EmptyHeader><Button variant="outline" icon={<X />} onClick={() => { setQ(""); onSearch({}) }}>Clear filters</Button></Empty>
        ) : (
          <Empty><EmptyHeader><EmptyTitle>No notes yet</EmptyTitle><EmptyDescription>Meeting notes, decisions and specs live here. Every save keeps a revision you can go back to.</EmptyDescription></EmptyHeader></Empty>
        )
      ) : (
        <>
          <ul className={`divide-y border-y ${isFetching ? "opacity-70" : ""}`} aria-label="Notes">
            {items.map((n) => (
              <li key={n.id}>
                <Link to="/app/projects/$projectId/notes/$noteId" params={{ projectId: id, noteId: n.id }} className="flex min-h-(--row-h) flex-wrap items-center gap-x-4 gap-y-1 px-1 py-2.5 outline-none hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:min-h-12">
                  <span className="min-w-0 flex-1 basis-56">
                    <span className="block truncate text-sm font-medium">{n.title}</span>
                    {n.tags.length > 0 && <span className="block truncate text-xs text-muted-foreground">{n.tags.map((t) => `#${t}`).join(" ")}</span>}
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"><UserAvatar name={n.author.first_name} src={n.author.avatar_url} size="sm" />{n.author.first_name}</span>
                  <span className="w-28 text-xs text-muted-foreground">{formatTimestamp(n.updated_at)}</span>
                </Link>
              </li>
            ))}
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
