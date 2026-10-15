import { useState } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ArrowBendUpLeft, PaperPlaneTilt } from "@/icons"

export interface Comment { id: string; author: string; time: string; body: string }

const initials = (n: string) => n.split(" ").map((p) => p[0]).join("")

export function CommentThread({ comments: initial }: { comments: Comment[] }) {
  const [comments, setComments] = useState(initial)
  const [draft, setDraft] = useState("")
  const post = () => {
    if (!draft.trim()) return
    setComments([...comments, { id: String(Date.now()), author: "You", time: "just now", body: draft.trim() }])
    setDraft("")
  }
  return (
    <div>
      <ul className="divide-y">
        {comments.map((c) => (
          <li key={c.id} className="group flex gap-3 py-3 first:pt-0">
            <Avatar size="sm"><AvatarFallback>{initials(c.author)}</AvatarFallback></Avatar>
            <div className="min-w-0 flex-1 text-sm">
              <p className="flex items-baseline gap-2"><span className="font-medium">{c.author}</span><span className="text-xs text-muted-foreground">{c.time}</span></p>
              <p className="mt-0.5 whitespace-pre-wrap">{c.body}</p>
            </div>
            <Button variant="ghost" size="icon-xs" label="Reply" className="opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"><ArrowBendUpLeft /></Button>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex items-end gap-2 border-t pt-3">
        <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Write a comment…" className="min-h-9 resize-none" rows={1} onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) post() }} />
        <Button icon={<PaperPlaneTilt />} onClick={post} disabled={!draft.trim()}>Send</Button>
      </div>
    </div>
  )
}
