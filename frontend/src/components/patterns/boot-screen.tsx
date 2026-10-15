import { Button } from "@/components/ui/button"
import { ArrowClockwise, Target, WarningCircle } from "@/icons"
import { cn } from "@/lib/utils"

/**
 * Page-wide loading screen for the moments nothing can be shown yet: a refresh, a reload, the first sign-in.
 * It appears after a short delay so a fast load never flashes it. In-app navigation keeps using skeletons.
 * When the wait runs long it says so and offers Retry instead of spinning for ever.
 */
export function BootScreen({ message = "Checking your session", slow = false, onRetry, contained = false, className }: { message?: string; slow?: boolean; onRetry?: () => void; /** Fill the nearest positioned parent instead of the viewport (design preview). */ contained?: boolean; className?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy={!slow}
      className={cn("boot-in z-[100] grid place-items-center bg-background px-6", contained ? "absolute inset-0" : "fixed inset-0", className)}
    >
      <div className="flex w-full max-w-xs flex-col items-center gap-5 text-center">
        <span className="grid size-12 place-items-center rounded-xl bg-primary text-primary-foreground" aria-hidden>
          <Target weight="bold" className="size-7" />
        </span>
        <div className="space-y-1">
          <p className="text-lg font-semibold tracking-tight">Pro-Goal</p>
          {slow ? (
            <p className="flex items-start justify-center gap-1.5 text-sm text-muted-foreground"><WarningCircle weight="fill" className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />This is taking longer than usual. Check your connection.</p>
          ) : (
            <p className="text-sm text-muted-foreground">{message}</p>
          )}
        </div>
        {slow ? (
          onRetry && <Button variant="outline" icon={<ArrowClockwise />} onClick={onRetry}>Try again</Button>
        ) : (
          <div className="h-0.5 w-40 overflow-hidden rounded-full bg-muted" aria-hidden>
            <div className="boot-bar h-full w-1/3 rounded-full bg-primary" />
          </div>
        )}
      </div>
    </div>
  )
}
