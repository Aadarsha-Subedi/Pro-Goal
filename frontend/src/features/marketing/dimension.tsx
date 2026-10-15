import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

const Head = ({ flip }: { flip?: boolean }) => (
  <svg width="10" height="14" viewBox="0 0 10 14" aria-hidden style={flip ? { transform: "scaleX(-1)" } : undefined}>
    <path d="M10 2L1 7l9 5M1 0v14" fill="none" stroke="currentColor" strokeWidth="1.5" />
  </svg>
)

/** Dimension line: arrowheads at both ends with a label, measuring the span it sits under. */
export function Dimension({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn("bp-dim bp-mono w-full", className)}>
      <span className="hidden sm:contents"><Head /><span className="bp-dim-rule" /></span>
      <span className="mx-auto whitespace-nowrap px-1 sm:mx-0">{children}</span>
      <span className="hidden sm:contents"><span className="bp-dim-rule" /><Head flip /></span>
    </span>
  )
}
