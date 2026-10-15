import { ArrowDown, ArrowUp, CheckCircle, Circle, CircleHalf, Equals, Flame } from "@/icons"
import { cn } from "@/lib/utils"

export type StatusCategory = "todo" | "in_progress" | "done"

const CATEGORY = {
  todo: { Icon: Circle, tone: "text-muted-foreground", weight: "regular" },
  in_progress: { Icon: CircleHalf, tone: "text-warning", weight: "fill" },
  done: { Icon: CheckCircle, tone: "text-success", weight: "fill" },
} as const

/** A project's own status: icon from its category, text from its name. Icon plus text, never a filled chip. */
export function StatusTag({ name, category, className }: { name: string; category: StatusCategory; className?: string }) {
  const { Icon, tone, weight } = CATEGORY[category]
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm", className)}>
      <Icon weight={weight} className={cn("size-4 shrink-0", tone)} aria-hidden />
      <span className="truncate">{name}</span>
    </span>
  )
}

/** Where a rank sits among the project's priorities (rank 1 is the lowest). */
export function priorityLevel(rank: number, max: number): "top" | "high" | "mid" | "low" {
  if (max <= 1) return "mid"
  const share = (rank - 1) / (max - 1)
  if (share >= 1) return "top"
  if (share >= 0.6) return "high"
  if (share > 0) return "mid"
  return "low"
}

const LEVEL = {
  top: { Icon: Flame, tone: "text-destructive" },
  high: { Icon: ArrowUp, tone: "text-warning" },
  mid: { Icon: Equals, tone: "text-foreground" },
  low: { Icon: ArrowDown, tone: "text-muted-foreground" },
} as const

export function PriorityTag({ name, rank, max, className }: { name: string; rank: number; max: number; className?: string }) {
  const { Icon, tone } = LEVEL[priorityLevel(rank, max)]
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm", className)}>
      <Icon weight="bold" className={cn("size-4 shrink-0", tone)} aria-hidden />
      <span className="truncate">{name}</span>
    </span>
  )
}
