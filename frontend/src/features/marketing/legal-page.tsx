import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { Button } from "@/components/ui/button"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowLeft } from "@/icons"
import { Sheet } from "./sheet"
import { TitleBlock } from "./title-block"

export interface LegalSection {
  heading: string
  body: ReactNode[]
}

/** Shared frame for the Terms and Privacy pages: sheet, header strip, one title block of numbered sections. */
export function LegalPage({ sheet, title, updated, sections }: { sheet: string; title: string; updated: string; sections: LegalSection[] }) {
  useDocumentTitle(`${title} · Pro-Goal`)
  return (
    <Sheet sheet={sheet}>
      <header className="flex h-12 items-center justify-between border-b bp-rule-strong px-4">
        <Link to="/" aria-label="Pro-Goal home" className="tap-target"><Logo /></Link>
        <ThemeToggle />
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-2xl flex-1 px-4 py-10 focus:outline-none">
        <TitleBlock as="h1" title={title} subtitle={`Last updated ${updated}`}>
          <p className="rounded border border-dashed px-3 py-2 text-sm font-medium">Pro-Goal is a learning project. It is not a reliable place to run a business or keep anything important.</p>
          {sections.map((s, i) => (
            <section key={s.heading} aria-labelledby={`legal-${i}`} className="space-y-2">
              <h2 id={`legal-${i}`} className="text-sm font-semibold">{i + 1}. {s.heading}</h2>
              {s.body.map((p, j) => <p key={j} className="text-sm bp-muted">{p}</p>)}
            </section>
          ))}
          <Button variant="outline" className="w-full" nativeButton={false} render={<Link to="/" />} icon={<ArrowLeft />}>Back to home</Button>
        </TitleBlock>
      </main>
    </Sheet>
  )
}
