import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { gsap, reducedMotion } from "@/motion"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { FileDropzone } from "@/components/patterns/file-dropzone"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { useRouteContext } from "@tanstack/react-router"
import { can, useCurrentProject } from "@/features/projects/current"
import { ArrowClockwise, DownloadSimple, File as FileIcon, FileDoc, FilePdf, FileText, FileXls, FilePpt, ImageSquare, MusicNote, Trash, X } from "@/icons"
import type { Attachment, Target } from "./api"
import { attachmentError } from "./errors"
import { formatBytes } from "./limits"
import type { UploadState } from "./pipeline"
import { useAttachmentMutations, useAttachments, useDownloadUrl } from "./queries"
import { useUploader } from "./use-uploader"

function FileGlyph({ a }: { a: Pick<Attachment, "category" | "content_type"> }) {
  const cls = "size-5 shrink-0 text-muted-foreground"
  if (a.category === "image") return <ImageSquare className={cls} aria-hidden />
  if (a.category === "audio") return <MusicNote className={cls} aria-hidden />
  if (a.content_type === "application/pdf") return <FilePdf className={cls} aria-hidden />
  if (a.content_type.includes("wordprocessing")) return <FileDoc className={cls} aria-hidden />
  if (a.content_type.includes("spreadsheet")) return <FileXls className={cls} aria-hidden />
  if (a.content_type.includes("presentation")) return <FilePpt className={cls} aria-hidden />
  if (a.content_type === "text/plain") return <FileText className={cls} aria-hidden />
  return <FileIcon className={cls} aria-hidden />
}

/** Small preview for a ready image, fetched only when the row is on screen. */
function Thumb({ projectId, a }: { projectId: string; a: Attachment }) {
  const [seen, setSeen] = useState(false)
  const { data } = useDownloadUrl(projectId, a.id, seen && a.category === "image" && a.status === "ready")
  if (a.category !== "image") return <FileGlyph a={a} />
  return (
    <span ref={(el) => { if (el && !seen && "IntersectionObserver" in window) { const io = new IntersectionObserver(([e]) => { if (e?.isIntersecting) { setSeen(true); io.disconnect() } }); io.observe(el) } else if (el && !seen) setSeen(true) }} className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-muted">
      {data?.url ? <img src={data.url} alt="" loading="lazy" className="size-full object-cover" /> : <ImageSquare className="size-5 text-muted-foreground" aria-hidden />}
    </span>
  )
}

function Row({ projectId, a, canDelete, onDelete, enter }: { projectId: string; a: Attachment; canDelete: boolean; onDelete: (a: Attachment) => void; /** A file that just finished uploading slides in; the ones already there do not. */ enter?: boolean }) {
  const [opening, setOpening] = useState(false)
  const li = useRef<HTMLLIElement>(null)
  useEffect(() => {
    if (!enter || !li.current || reducedMotion()) return
    gsap.fromTo(li.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out", delay: 0.15 })
  }, [enter])
  const ready = a.status === "ready"
  const { refetch } = useDownloadUrl(projectId, a.id, false)
  const open = async () => {
    setOpening(true)
    try {
      const r = await refetch()
      if (r.data?.url) window.open(r.data.url, "_blank", "noopener,noreferrer")
      else toast.error("Couldn't get the download link. Try again.")
    } finally {
      setOpening(false)
    }
  }
  return (
    <li ref={li} className="flex min-h-12 items-center gap-3 py-1.5">
      <Thumb projectId={projectId} a={a} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{a.filename}</p>
        <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
          <span className="tabular-nums">{formatBytes(a.size_bytes)}</span>
          <span className="inline-flex items-center gap-1"><UserAvatar name={a.uploaded_by.first_name} src={a.uploaded_by.avatar_url} size="sm" className="size-4" />{a.uploaded_by.first_name}</span>
          {!ready && <span>Processing…</span>}
        </p>
      </div>
      <Button variant="ghost" size="icon" label={`Download ${a.filename}`} loading={opening} disabled={!ready} onClick={open}><DownloadSimple /></Button>
      <Button variant="ghost" size="icon" label={`Delete ${a.filename}`} disabled={!canDelete} onClick={() => onDelete(a)}><Trash /></Button>
    </li>
  )
}

/**
 * One upload in flight. The bar eases to the real progress, fills to 100% when the file lands, holds a beat,
 * then the row folds away and the finished file takes its place in the list. Reduced motion skips the movement.
 */
function Pending({ u, onCancel, onRetry, onDismiss }: { u: UploadState; onCancel: () => void; onRetry: () => void; onDismiss: () => void }) {
  const failed = u.phase === "failed"
  const done = u.phase === "done"
  const active = u.phase === "uploading" || u.phase === "confirming" || u.phase === "processing"
  const showBar = active || done
  const pct = done || u.phase !== "uploading" ? 100 : Math.round(u.progress * 100)
  const label = failed ? u.error : u.phase === "cancelled" ? "Cancelled" : u.phase === "uploading" ? `Uploading ${pct}%` : u.phase === "confirming" ? "Checking the file…" : u.phase === "processing" ? "Processing the image…" : "Uploaded"
  const row = useRef<HTMLLIElement>(null)
  const bar = useRef<HTMLDivElement>(null)
  const dismiss = useRef(onDismiss)
  useEffect(() => { dismiss.current = onDismiss })

  useEffect(() => {
    if (!bar.current) return
    if (reducedMotion()) gsap.set(bar.current, { width: `${pct}%` })
    else gsap.to(bar.current, { width: `${pct}%`, duration: 0.4, ease: "power2.out", overwrite: true })
  }, [pct])

  useEffect(() => {
    if (!done || !row.current) return
    const el = row.current
    if (reducedMotion()) {
      const t = window.setTimeout(() => dismiss.current(), 600)
      return () => window.clearTimeout(t)
    }
    const tl = gsap.timeline({ delay: 0.55, onComplete: () => dismiss.current() })
    tl.to(el, { opacity: 0, y: -6, duration: 0.25, ease: "power2.in" }).to(el, { height: 0, paddingTop: 0, paddingBottom: 0, duration: 0.25, ease: "power2.inOut" }, "<0.1")
    // A hidden tab pauses animation frames; the row must still go.
    const fallback = window.setTimeout(() => dismiss.current(), 2000)
    return () => { tl.kill(); window.clearTimeout(fallback) }
  }, [done])

  return (
    <li ref={row} className="flex min-h-12 items-center gap-3 overflow-hidden py-1.5">
      <FileIcon className="size-5 shrink-0 text-muted-foreground" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{u.name}</p>
        <p role={failed ? "alert" : "status"} className={failed ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>{label}</p>
        {showBar && <div role="progressbar" aria-label={`Uploading ${u.name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="mt-1 h-1 overflow-hidden rounded-full bg-muted"><div ref={bar} className="h-full bg-primary" style={{ width: `${pct}%` }} /></div>}
      </div>
      {failed && <Button variant="ghost" size="icon" label={`Retry ${u.name}`} onClick={onRetry}><ArrowClockwise /></Button>}
      {active ? <Button variant="ghost" size="icon" label={`Cancel ${u.name}`} onClick={onCancel}><X /></Button> : !done && <Button variant="ghost" size="icon" label={`Dismiss ${u.name}`} onClick={onDismiss}><X /></Button>}
    </li>
  )
}

/** Files on one task, note or comment: drop zone, in-flight uploads, the list. */
export function FilesSection({ target, title = "Files", archived, compact }: { target: Target; title?: string; archived?: boolean; compact?: boolean }) {
  const { id, project } = useCurrentProject()
  const { me } = useRouteContext({ from: "/app" })
  const { data, isPending, isError, refetch } = useAttachments(id, target)
  const { remove } = useAttachmentMutations(id)
  const up = useUploader(id, target)
  const [del, setDel] = useState<Attachment | null>(null)
  const items = data?.items ?? []
  // Files present when the list first loaded appear at once; anything added after that animates in.
  const [seen, setSeen] = useState<Set<string> | null>(null)
  if (data && seen === null) setSeen(new Set(items.map((x) => x.id)))
  const frozen = archived ?? project.is_archived
  const mayUpload = can(project, "attachment.create")
  const reason = frozen ? "This project is archived, so files can't be added." : undefined
  const owner = project.role === "owner"

  return (
    <section aria-labelledby={`files-${target.type}-${target.id}`} className="space-y-3">
      <h2 id={`files-${target.type}-${target.id}`} className="text-sm font-semibold">{title}{items.length > 0 && <span className="ml-2 font-normal tabular-nums text-muted-foreground">{items.length}</span>}</h2>
      {up.items.length > 0 && <ul className="divide-y border-y" aria-label="Uploads">{up.items.map((u) => <Pending key={u.id} u={u} onCancel={() => up.cancel(u.id)} onRetry={() => up.retry(u.id)} onDismiss={() => up.dismiss(u.id)} />)}</ul>}
      {isPending ? (
        <p className="text-sm text-muted-foreground" aria-busy="true">Loading files…</p>
      ) : isError ? (
        <div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground">Couldn't load files.</span><Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></div>
      ) : items.length > 0 ? (
        <ul className="divide-y border-y" aria-label="Files">
          {items.map((a) => <Row key={a.id} projectId={id} a={a} enter={seen !== null && !seen.has(a.id)} canDelete={!frozen && (a.uploaded_by.id === me.id || owner || can(project, "attachment.delete"))} onDelete={setDel} />)}
        </ul>
      ) : (
        up.items.length === 0 && <p className="text-sm text-muted-foreground">No files yet.</p>
      )}
      <FileDropzone compact={compact ?? true} onFiles={up.add} disabledReason={reason ?? (!mayUpload ? "Needs the attachment.create permission to add files." : undefined)} />
      <AlertDialog open={!!del} onOpenChange={(o) => !o && setDel(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {del?.filename}?</AlertDialogTitle>
            <AlertDialogDescription>The file is removed for everyone and its space is freed. This can't be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} loading={remove.isPending} onClick={() => del && remove.mutate(del.id, { onSuccess: () => { setDel(null); toast.success("File deleted.") }, onError: (e) => { setDel(null); toast.error(attachmentError(e)) } })}>Delete file</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  )
}
