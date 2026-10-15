import type { ReactNode } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

export interface ActivityItem {
  id: string
  actor: string
  action: ReactNode
  time: string
}

const initials = (n: string) => n.split(" ").map((p) => p[0]).join("")

/** Vertical timeline: one rail line, avatar per entry, no boxes. */
export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <ol className="relative">
      {items.map((it, i) => (
        <li key={it.id} className="relative flex gap-3 pb-5 last:pb-0">
          {i < items.length - 1 && <span aria-hidden className="absolute top-7 bottom-0 left-3 w-px bg-border" />}
          <Avatar size="sm"><AvatarFallback>{initials(it.actor)}</AvatarFallback></Avatar>
          <div className="min-w-0 pt-0.5 text-sm">
            <p><span className="font-medium">{it.actor}</span> <span className="text-muted-foreground">{it.action}</span></p>
            <p className="text-xs text-muted-foreground">{it.time}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
