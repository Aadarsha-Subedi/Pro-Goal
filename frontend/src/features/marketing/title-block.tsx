import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/** Ruled title block. The top cell names the document, the body holds the form. */
export function TitleBlock({ title, subtitle, children, className, footer, as: Heading = "h2" }: { title: string; subtitle?: string; children: ReactNode; className?: string; footer?: ReactNode; as?: "h1" | "h2" }) {
  return (
    <section aria-label={title} className={cn("bp-block", className)}>
      <header className="px-4 py-3">
        <Heading className="text-lg font-semibold">{title}</Heading>
        {subtitle && <p className="mt-0.5 text-sm bp-muted">{subtitle}</p>}
      </header>
      <div className="space-y-3 px-4 py-4">{children}</div>
      {footer && <footer className="px-4 py-3 text-sm">{footer}</footer>}
    </section>
  )
}
