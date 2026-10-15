import { CheckCircle, Circle, CircleDashed, CircleHalf, XCircle, ArrowUp, ArrowDown, Equals, Flame } from "@/icons"
import { cn } from "@/lib/utils"

export type TaskStatus = "backlog" | "todo" | "progress" | "done" | "cancelled"
export type TaskPriority = "urgent" | "high" | "medium" | "low"

const STATUS = {
  backlog: { label: "Backlog", Icon: CircleDashed, tone: "text-muted-foreground", weight: "regular" },
  todo: { label: "Todo", Icon: Circle, tone: "text-foreground", weight: "regular" },
  progress: { label: "In progress", Icon: CircleHalf, tone: "text-warning", weight: "fill" },
  done: { label: "Done", Icon: CheckCircle, tone: "text-success", weight: "fill" },
  cancelled: { label: "Cancelled", Icon: XCircle, tone: "text-muted-foreground", weight: "fill" },
} as const

const PRIORITY = {
  urgent: { label: "Urgent", Icon: Flame, tone: "text-destructive" },
  high: { label: "High", Icon: ArrowUp, tone: "text-warning" },
  medium: { label: "Medium", Icon: Equals, tone: "text-foreground" },
  low: { label: "Low", Icon: ArrowDown, tone: "text-muted-foreground" },
} as const

export function StatusLabel({ status, className }: { status: TaskStatus; className?: string }) {
  const { label, Icon, tone, weight } = STATUS[status]
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm", className)}>
      <Icon weight={weight} className={cn("size-4", tone)} aria-hidden />
      {label}
    </span>
  )
}

export function PriorityLabel({ priority, className }: { priority: TaskPriority; className?: string }) {
  const { label, Icon, tone } = PRIORITY[priority]
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm", className)}>
      <Icon weight="bold" className={cn("size-4", tone)} aria-hidden />
      {label}
    </span>
  )
}

export const STATUSES = Object.keys(STATUS) as TaskStatus[]
