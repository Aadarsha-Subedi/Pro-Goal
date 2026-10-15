import { useState } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Kbd } from "@/components/ui/kbd"
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Bell, CaretDown, CheckSquare, ClockCounterClockwise, Compass, House, MagnifyingGlass, Note, Plus, Users } from "@/icons"
import { cn } from "@/lib/utils"
import { Section, Specimen } from "../section"

const NAV = [
  { label: "Home", icon: House },
  { label: "My tasks", icon: CheckSquare, count: 8 },
  { label: "Notes", icon: Note },
  { label: "Activity", icon: ClockCounterClockwise },
  { label: "Explore", icon: Compass },
  { label: "Members", icon: Users, count: 2 },
]

export function Navigation() {
  const [active, setActive] = useState("My tasks")
  return (
    <Section id="navigation" title="Navigation" intro="App shell, breadcrumbs, tabs and pagination. The shell is one flat frame; hierarchy comes from tone and dividers, not boxes.">
      <Specimen title="App shell" note="Sidebar, topbar, content region. Click items.">
        <div className="grid h-[22rem] overflow-hidden rounded-lg border md:grid-cols-[14rem_1fr]">
          <aside className="hidden flex-col border-r bg-sidebar md:flex">
            <Button variant="ghost" size="lg" className="m-2 justify-start gap-2 px-2" iconEnd={<CaretDown className="ml-auto" />}>
              <span className="grid size-5 place-items-center rounded bg-primary text-caption font-semibold text-primary-foreground">A</span>
              Apollo
            </Button>
            <nav className="flex-1 space-y-0.5 px-2" aria-label="Project">
              {NAV.map(({ label, icon: Icon, count }) => (
                <button
                  key={label}
                  onClick={() => setActive(label)}
                  aria-current={active === label ? "page" : undefined}
                  className={cn(
                    "flex h-8 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground",
                    active === label && "bg-sidebar-accent font-medium text-foreground",
                  )}
                >
                  <Icon weight={active === label ? "fill" : "regular"} className="size-4" />
                  {label}
                  {count && <span className="ml-auto text-xs tabular-nums text-muted-foreground">{count}</span>}
                </button>
              ))}
            </nav>
            <div className="flex items-center gap-2 border-t p-3">
              <Avatar size="sm"><AvatarFallback>MC</AvatarFallback></Avatar>
              <span className="truncate text-sm">Maya Chen</span>
            </div>
          </aside>
          <div className="flex min-w-0 flex-col">
            <header className="flex h-12 items-center gap-2 border-b px-4">
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem><BreadcrumbLink href="#">Apollo</BreadcrumbLink></BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem><BreadcrumbPage>{active}</BreadcrumbPage></BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
              <Button variant="outline" size="sm" className="ml-auto text-muted-foreground" icon={<MagnifyingGlass />}>
                Search <Kbd className="ml-2">⌘K</Kbd>
              </Button>
              <Button variant="ghost" size="icon" label="Notifications"><Bell /></Button>
              <Button size="sm" icon={<Plus weight="bold" />}>New</Button>
            </header>
            <div className="flex-1 p-6">
              <h4 className="text-lg font-semibold">{active}</h4>
              <p className="mt-1 text-muted-foreground">The task list renders here.</p>
            </div>
          </div>
        </div>
      </Specimen>

      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Tabs">
          <Tabs defaultValue="all">
            <TabsList variant="line">
              <TabsTrigger value="all">All <Badge variant="secondary" className="ml-1">24</Badge></TabsTrigger>
              <TabsTrigger value="mine">Assigned to me</TabsTrigger>
              <TabsTrigger value="created">Created</TabsTrigger>
            </TabsList>
          </Tabs>
        </Specimen>
        <Specimen title="Pagination" note="25 per page">
          <Pagination className="mx-0 justify-start">
            <PaginationContent>
              <PaginationItem><PaginationPrevious href="#" /></PaginationItem>
              <PaginationItem><PaginationLink href="#" isActive>1</PaginationLink></PaginationItem>
              <PaginationItem><PaginationLink href="#">2</PaginationLink></PaginationItem>
              <PaginationItem><PaginationLink href="#">3</PaginationLink></PaginationItem>
              <PaginationItem><PaginationNext href="#" /></PaginationItem>
            </PaginationContent>
          </Pagination>
        </Specimen>
      </div>
    </Section>
  )
}
