import { useRouteContext } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { MarkdownView } from "@/components/patterns/markdown-editor"
import { MentionTextarea, type PickedMention } from "@/components/patterns/mention-textarea"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { can, useCurrentProject } from "@/features/projects/current"
import { FilesSection } from "@/features/attachments/files-section"
import { ArrowClockwise, ChatCircle, Paperclip, PencilSimple, Trash } from "@/icons"
import { trackerError } from "../errors"
import { toDisplay, toWire, renderMentions } from "../mentions"
import { useProjectPeople } from "../people"
import { useCommentMutations, useComments } from "../queries"
import type { Comment } from "../api"

const stamp = (iso: string) => new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" })

function Composer({ projectId, number, allowed, archived }: { projectId: string; number: number; allowed: boolean; archived: boolean }) {
  const { people } = useProjectPeople(projectId)
  const { create } = useCommentMutations(projectId, number)
  const [text, setText] = useState("")
  const [picked, setPicked] = useState<PickedMention[]>([])
  const off = !allowed || archived
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim() || off) return
    create.mutate(toWire(text.trim(), picked), { onSuccess: () => { setText(""); setPicked([]) }, onError: (err) => toast.error(trackerError(err)) })
  }
  return (
    <form onSubmit={submit} className="space-y-2">
      <MentionTextarea label="Add a comment" value={text} onChange={setText} people={people} onPick={(m) => setPicked((p) => [...p, m])} maxLength={10000} placeholder={off ? "Commenting is off for you" : "Write a comment. Markdown works."} disabled={off} />
      <div className="flex items-center gap-3">
        <Button type="submit" icon={<ChatCircle />} loading={create.isPending} disabled={off || !text.trim()}>Comment</Button>
        {off && <p className="text-xs text-muted-foreground">{archived ? "This project is archived." : <>Needs the <code className="font-mono">comment.create</code> permission.</>}</p>}
      </div>
    </form>
  )
}

function CommentItem({ comment, projectId, number, mine, moderate, archived }: { comment: Comment; projectId: string; number: number; mine: boolean; moderate: boolean; archived: boolean }) {
  const { people, byId } = useProjectPeople(projectId)
  const { update, remove } = useCommentMutations(projectId, number)
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [files, setFiles] = useState(false)
  const [text, setText] = useState("")
  const [picked, setPicked] = useState<PickedMention[]>([])
  const canAct = (mine || moderate) && !archived && !comment.is_deleted
  const start = () => {
    const d = toDisplay(comment.body ?? "", byId)
    setText(d.text)
    setPicked(d.mentions)
    setEditing(true)
  }
  const save = (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return
    update.mutate({ id: comment.id, body: toWire(text.trim(), picked) }, { onSuccess: () => setEditing(false), onError: (err) => toast.error(trackerError(err)) })
  }
  return (
    <li className="flex gap-3 py-3">
      <UserAvatar name={comment.author.first_name} src={comment.author.avatar_url} />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-sm font-medium">{comment.author.first_name}</span>
          <time dateTime={comment.created_at} className="text-xs text-muted-foreground">{stamp(comment.created_at)}</time>
          {comment.edited_at && !comment.is_deleted && <span className="text-xs text-muted-foreground">edited</span>}
          {canAct && !editing && (
            <span className="ml-auto flex">
              <Button variant="ghost" size="icon-sm" label={files ? "Hide files" : "Files"} aria-expanded={files} onClick={() => setFiles((f) => !f)}><Paperclip /></Button>
              <Button variant="ghost" size="icon-sm" label="Edit comment" onClick={start}><PencilSimple /></Button>
              <Button variant="ghost" size="icon-sm" label="Delete comment" onClick={() => setConfirm(true)}><Trash /></Button>
            </span>
          )}
        </div>
        {comment.is_deleted ? (
          <p className="text-sm italic text-muted-foreground">This comment was deleted.</p>
        ) : editing ? (
          <form onSubmit={save} className="space-y-2">
            <MentionTextarea label="Edit comment" value={text} onChange={setText} people={people} onPick={(m) => setPicked((p) => [...p, m])} maxLength={10000} autoFocus />
            <div className="flex gap-2">
              <Button type="submit" loading={update.isPending} disabled={!text.trim()}>Save</Button>
              <Button type="button" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            </div>
          </form>
        ) : (
          <MarkdownView source={renderMentions(comment.body ?? "", byId)} />
        )}
        {files && !comment.is_deleted && <div className="pt-2"><FilesSection target={{ type: "comment", id: comment.id }} title="Files on this comment" archived={archived} /></div>}
      </div>
      <AlertDialog open={confirm} onOpenChange={setConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this comment?</AlertDialogTitle>
            <AlertDialogDescription>It is replaced by "This comment was deleted" for everyone. This can't be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} loading={remove.isPending} onClick={() => remove.mutate(comment.id, { onSuccess: () => setConfirm(false), onError: (err) => { setConfirm(false); toast.error(trackerError(err)) } })}>Delete comment</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </li>
  )
}

/** Flat thread under a task: oldest first, newest at the composer. Edit and delete your own; moderators can act on any. */
export function CommentSection({ number }: { number: number }) {
  const { id, project } = useCurrentProject()
  const { me } = useRouteContext({ from: "/app" })
  const { data, isPending, isError, refetch } = useComments(id, number)
  const items = data?.items ?? []
  return (
    <section aria-labelledby="comments" className="space-y-3">
      <h2 id="comments" className="text-sm font-semibold">Comments{items.length > 0 && <span className="ml-2 font-normal tabular-nums text-muted-foreground">{items.length}</span>}</h2>
      {isPending ? (
        <div className="space-y-3" aria-busy="true" aria-label="Loading comments"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
      ) : isError ? (
        <div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground">Couldn't load comments.</span><Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No comments yet.</p>
      ) : (
        <ul className="divide-y border-y" aria-label="Comments">
          {items.map((c) => <CommentItem key={c.id} comment={c} projectId={id} number={number} mine={c.author.id === me.id} moderate={can(project, "comment.moderate")} archived={project.is_archived} />)}
        </ul>
      )}
      <Composer projectId={id} number={number} allowed={can(project, "comment.create")} archived={project.is_archived} />
    </section>
  )
}
