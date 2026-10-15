import { useEffect, useRef, useState } from "react"
import { Logo } from "@/components/patterns/logo"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { useReveal } from "@/motion"
import { Access } from "./sections/access"
import { Actions } from "./sections/actions"
import { DataTableSection } from "./sections/data-table"
import { Feedback } from "./sections/feedback"
import { Content } from "./sections/content"
import { Forms } from "./sections/forms"
import { Foundations } from "./sections/foundations"
import { Kanban } from "./sections/kanban"
import { Menus } from "./sections/menus"
import { MotionSection } from "./sections/motion"
import { Navigation } from "./sections/navigation"
import { ProjectSurfaces } from "./sections/projects"

const TOC = [
  ["foundations", "Foundations"],
  ["access", "Permissions and access"],
  ["data", "Data table"],
  ["kanban", "Board"],
  ["actions", "Buttons"],
  ["navigation", "Navigation"],
  ["projects", "Project surfaces"],
  ["menus", "Menus and overlays"],
  ["forms", "Forms"],
  ["content", "Content and collaboration"],
  ["feedback", "Feedback and states"],
  ["motion", "Motion"],
]

function useActiveSection() {
  const [active, setActive] = useState(TOC[0][0])
  useEffect(() => {
    const on = () => {
      let cur = TOC[0][0]
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        setActive(TOC[TOC.length - 1][0])
        return
      }
      for (const [id] of TOC) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top <= 140) cur = id
      }
      setActive(cur)
    }
    on()
    const t = window.setTimeout(on, 400)
    window.addEventListener("scroll", on, { passive: true })
    window.addEventListener("hashchange", on)
    return () => {
      window.clearTimeout(t)
      window.removeEventListener("scroll", on)
      window.removeEventListener("hashchange", on)
    }
  }, [])
  return [active, setActive] as const
}

export function DesignPreview() {
  const main = useRef<HTMLElement>(null)
  const [active, setActive] = useActiveSection()
  useReveal(main)
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only z-50 rounded bg-background px-3 py-2 text-sm focus:not-sr-only focus:fixed focus:top-2 focus:left-2">Skip to content</a>
      <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b bg-background px-4">
        <Logo />
        <span aria-hidden className="hidden h-4 w-px bg-border sm:block" />
        <h1 className="hidden text-sm text-muted-foreground sm:block">Design preview</h1>
        <div className="ml-auto flex items-center gap-3">
          <ThemeToggle />
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-10 lg:grid-cols-[12rem_1fr]">
        <nav aria-label="Sections" className="sticky top-24 hidden h-fit lg:block">
          <ul className="space-y-0.5">
            {TOC.map(([id, label]) => (
              <li key={id}><Button variant="ghost" size="sm" className={`w-full justify-start ${active === id ? "bg-muted text-foreground" : "text-muted-foreground"}`} nativeButton={false} render={<a href={`#${id}`} aria-current={active === id ? "location" : undefined} />}>{label}</Button></li>
            ))}
          </ul>
        </nav>
        <main id="main" ref={main} className="min-w-0">
          <label className="mb-8 block lg:hidden">
            <span className="sr-only">Jump to section</span>
            <select
              value={active}
              onChange={(e) => { setActive(e.target.value); document.getElementById(e.target.value)?.scrollIntoView() }}
              className="h-(--ctl-h) w-full rounded-md border border-input bg-background px-2.5 text-sm"
            >
              {TOC.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </label>
          <Foundations />
          <Access />
          <DataTableSection />
          <Kanban />
          <Actions />
          <Navigation />
          <ProjectSurfaces />
          <Menus />
          <Forms />
          <Content />
          <Feedback />
          <MotionSection />
        </main>
      </div>
    </div>
  )
}
