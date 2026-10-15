import { Target } from "@/icons"
import { cn } from "@/lib/utils"

/** Pro-Goal mark: Phosphor Target in the accent, with wordmark. */
export function Logo({ className, mark = false }: { className?: string; mark?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2 whitespace-nowrap font-semibold tracking-tight", className)}>
      <span className="grid size-6 place-items-center rounded-md bg-primary text-primary-foreground">
        <Target weight="bold" className="size-4" aria-hidden />
      </span>
      {!mark && <span>Pro-Goal</span>}
    </span>
  )
}
