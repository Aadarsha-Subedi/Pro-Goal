import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

const LETTERS = ["A", "B", "C", "D"]
const NUMBERS = ["1", "2", "3", "4"]

/** Drawing sheet: double border, centering ticks, zone letters and numbers, sticky sheet-number strip. */
export function Sheet({ children, sheet = "PG-01", rev = "C", className }: { children: ReactNode; sheet?: string; rev?: string; className?: string }) {
  return (
    <div className={cn("bp min-h-screen p-6 sm:p-8", className)}>
      <a href="#main" onClick={() => requestAnimationFrame(() => document.getElementById("main")?.focus())} className="sr-only z-50 rounded bg-background px-3 py-2 text-sm text-foreground focus:not-sr-only focus:fixed focus:top-2 focus:left-2">Skip to content</a>
      <div className="bp-sheet flex min-h-[calc(100vh-3rem)] flex-col sm:min-h-[calc(100vh-4rem)]">
        <div aria-hidden>
          {LETTERS.map((l, i) => <span key={l} className="bp-zone -top-[22px]" style={{ left: `${12.5 + i * 25}%` }}>{l}</span>)}
          {NUMBERS.map((n, i) => <span key={n} className="bp-zone -left-[22px]" style={{ top: `${12.5 + i * 25}%` }}>{n}</span>)}
          <span className="bp-tick -top-2 left-1/2 h-4 w-px" />
          <span className="bp-tick -bottom-2 left-1/2 h-4 w-px" />
          <span className="bp-tick -left-2 top-1/2 h-px w-4" />
          <span className="bp-tick -right-2 top-1/2 h-px w-4" />
        </div>
        {children}
        <div className="bp-mono sm:sticky sm:bottom-0 mt-auto flex items-center justify-between border-t bp-rule-strong bg-[var(--bp-ground)] px-4 py-1.5 text-xs bp-muted">
          <span>SHEET {sheet}</span>
          <span>REV {rev}</span>
        </div>
      </div>
    </div>
  )
}
