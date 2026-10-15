import { Link } from "@tanstack/react-router"
import type { ReactNode } from "react"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { Sheet } from "@/features/marketing/sheet"
import { TitleBlock } from "@/features/marketing/title-block"

/** Shared frame for every auth screen: sheet, header strip, one title block. */
export function AuthSheet({ sheet, title, subtitle, children, footer }: { sheet: string; title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  useDocumentTitle(`${title} · Pro-Goal`)
  return (
    <Sheet sheet={sheet}>
      <header className="flex h-12 items-center justify-between border-b bp-rule-strong px-4">
        <Link to="/" aria-label="Pro-Goal home" className="tap-target"><Logo /></Link>
        <ThemeToggle />
      </header>
      <main id="main" tabIndex={-1} className="mx-auto flex focus:outline-none w-full max-w-md flex-1 items-center px-4 py-10">
        <TitleBlock as="h1" title={title} subtitle={subtitle} className="w-full" footer={footer}>{children}</TitleBlock>
      </main>
    </Sheet>
  )
}
