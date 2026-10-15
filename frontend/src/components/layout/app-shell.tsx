import { useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate, useParams } from "@tanstack/react-router"
import type { ReactNode } from "react"
import { toast } from "sonner"
import { Logo } from "@/components/patterns/logo"
import { ThemeToggle } from "@/components/patterns/theme-toggle"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { authApi, type Me } from "@/features/auth/api"
import { startTour } from "@/features/tour/tour"
import { useProject, useProjects, useRequests } from "@/features/projects/queries"
import { ClockCounterClockwise, Compass, Question, GearSix, Kanban, PlugsConnected, ShieldCheck, List, ListChecks, NotePencil, SignOut, SquaresFour, UserPlus, Users } from "@/icons"
import { cn } from "@/lib/utils"

const LINK = "flex h-8 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition-colors outline-none hover:bg-sidebar-accent hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:h-11"
const ACTIVE = "bg-sidebar-accent font-medium text-foreground"

function NavLink({ to, params, icon, children, count, exact, tour }: { to: string; params?: Record<string, string>; icon: ReactNode; children: ReactNode; count?: number; exact?: boolean; tour?: string }) {
  return (
    <Link to={to as never} params={params as never} activeOptions={{ exact }} data-tour={tour} className={LINK} activeProps={{ className: ACTIVE, "aria-current": "page" }}>
      {icon}
      <span className="truncate">{children}</span>
      {count ? <span className="ml-auto text-xs tabular-nums text-muted-foreground">{count}</span> : null}
    </Link>
  )
}

function ProjectNav({ projectId }: { projectId: string }) {
  const { data: project } = useProject(projectId)
  const canApprove = project?.role === "owner" || project?.permissions.includes("member.approve")
  const canIntegrations = project?.role === "owner" || project?.permissions.includes("integration.logs.view") || project?.permissions.includes("integration.slack.manage")
  const { data: waiting } = useRequests(projectId, "pending", !!canApprove)
  const p = { projectId }
  return (
    <nav aria-label="Project" className="space-y-0.5">
      <p className="truncate px-2 pb-1 pt-3 text-xs font-medium text-muted-foreground">{project?.name ?? "Project"}</p>
      <NavLink to="/app/projects/$projectId" params={p} exact icon={<SquaresFour className="size-4" />}>Overview</NavLink>
      <NavLink to="/app/projects/$projectId/tasks" params={p} tour="nav-tasks" icon={<ListChecks className="size-4" />}>Tasks</NavLink>
      <NavLink to="/app/projects/$projectId/board" params={p} tour="nav-board" icon={<Kanban className="size-4" />}>Board</NavLink>
      <NavLink to="/app/projects/$projectId/notes" params={p} tour="nav-notes" icon={<NotePencil className="size-4" />}>Notes</NavLink>
      <NavLink to="/app/projects/$projectId/activity" params={p} tour="nav-activity" icon={<ClockCounterClockwise className="size-4" />}>Activity</NavLink>
      <NavLink to="/app/projects/$projectId/members" params={p} tour="nav-members" icon={<Users className="size-4" />} count={project?.member_count}>Members</NavLink>
      {canApprove && <NavLink to="/app/projects/$projectId/requests" params={p} icon={<UserPlus className="size-4" />} count={waiting?.meta.count}>Join requests</NavLink>}
      {canIntegrations && <NavLink to="/app/projects/$projectId/integrations" params={p} icon={<PlugsConnected className="size-4" />}>Integrations</NavLink>}
      <NavLink to="/app/projects/$projectId/settings" params={p} icon={<GearSix className="size-4" />}>Settings</NavLink>
    </nav>
  )
}

function Sidebar({ projectId }: { projectId?: string }) {
  const { data: projects } = useProjects()
  return (
    <div className="flex h-full flex-col gap-1 p-2">
      <Link to="/app" className="mb-2 flex h-10 items-center rounded-md px-2 outline-none focus-visible:ring-3 focus-visible:ring-ring/50" aria-label="Pro-Goal projects">
        <Logo />
      </Link>
      <nav aria-label="Main" className="space-y-0.5">
        <NavLink to="/app" exact tour="nav-projects" icon={<SquaresFour className="size-4" />}>Projects</NavLink>
        <NavLink to="/app/tasks" icon={<ListChecks className="size-4" />}>My tasks</NavLink>
        <NavLink to="/app/explore" tour="nav-explore" icon={<Compass className="size-4" />}>Explore</NavLink>
      </nav>
      {projectId ? <ProjectNav projectId={projectId} /> : projects && projects.items.length > 0 && (
        <nav aria-label="Your projects" className="space-y-0.5">
          <p className="px-2 pb-1 pt-3 text-xs font-medium text-muted-foreground">Your projects</p>
          {projects.items.slice(0, 8).map((p) => (
            <NavLink key={p.id} to="/app/projects/$projectId" params={{ projectId: p.id }} icon={<span className="font-mono text-caption text-muted-foreground">{p.task_key}</span>}>{p.name}</NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}

/** Mobile navigation: one menu button instead of a side drawer. */
function MobileMenu({ projectId }: { projectId?: string }) {
  const { data: projects } = useProjects()
  const { data: current } = useProject(projectId ?? "")
  const canApprove = current?.role === "owner" || current?.permissions.includes("member.approve")
  const canIntegrations = current?.role === "owner" || current?.permissions.includes("integration.logs.view") || current?.permissions.includes("integration.slack.manage")
  const navigate = useNavigate()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="icon" label="Menu"><List /></Button>} />
      <DropdownMenuContent className="w-60">
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={() => navigate({ to: "/app" })}><SquaresFour />Projects</DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate({ to: "/app/tasks" })}><ListChecks />My tasks</DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate({ to: "/app/explore" })}><Compass />Explore</DropdownMenuItem>
        </DropdownMenuGroup>
        {projectId && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuLabel>This project</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId", params: { projectId } })}><SquaresFour />Overview</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/tasks", params: { projectId } })}><ListChecks />Tasks</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/board", params: { projectId } })}><Kanban />Board</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/notes", params: { projectId } })}><NotePencil />Notes</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/activity", params: { projectId } })}><ClockCounterClockwise />Activity</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/members", params: { projectId } })}><Users />Members</DropdownMenuItem>
              {canApprove && <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/requests", params: { projectId } })}><UserPlus />Join requests</DropdownMenuItem>}
              {canIntegrations && <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/integrations", params: { projectId } })}><PlugsConnected />Integrations</DropdownMenuItem>}
              <DropdownMenuItem onClick={() => navigate({ to: "/app/projects/$projectId/settings", params: { projectId } })}><GearSix />Settings</DropdownMenuItem>
            </DropdownMenuGroup>
          </>
        )}
        {projects && projects.items.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuLabel>Your projects</DropdownMenuLabel>
              {projects.items.slice(0, 8).map((p) => (
                <DropdownMenuItem key={p.id} onClick={() => navigate({ to: "/app/projects/$projectId", params: { projectId: p.id } })}>
                  <span className="font-mono text-caption text-muted-foreground">{p.task_key}</span>
                  <span className="truncate">{p.name}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function UserMenu({ me }: { me: Me }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const signOut = async () => {
    try {
      await authApi.logout()
    } catch {
      toast.error("Couldn't sign you out. Check your connection and try again.")
      return
    }
    qc.clear()
    navigate({ to: "/login", replace: true })
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="ghost" size="icon" label="Account"><UserAvatar name={me.display_name} size="sm" /></Button>} />
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="flex flex-col gap-0.5">
            <span className="truncate text-sm font-medium text-foreground">{me.display_name}</span>
            <span className="truncate text-xs font-normal text-muted-foreground">{me.email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate({ to: "/app/account" })}><ShieldCheck />Account</DropdownMenuItem>
        <DropdownMenuItem onClick={() => { if (!startTour()) toast.info("Open a project to take the tour.") }}><Question />Replay tour</DropdownMenuItem>
        <DropdownMenuItem onClick={signOut}><SignOut />Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function Crumbs({ projectId }: { projectId?: string }) {
  const { data: project } = useProject(projectId ?? "")
  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem>
          {projectId ? <BreadcrumbLink render={<Link to="/app">Projects</Link>} /> : <BreadcrumbPage>Projects</BreadcrumbPage>}
        </BreadcrumbItem>
        {projectId && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem><BreadcrumbPage className="truncate">{project?.name ?? "Project"}</BreadcrumbPage></BreadcrumbItem>
          </>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

/** Flat frame: sidebar and topbar are tone and hairlines, never boxes. */
export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const { projectId } = useParams({ strict: false }) as { projectId?: string }
  return (
    <div className="grid min-h-screen md:grid-cols-[14rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:ring-3 focus:ring-ring/50">Skip to content</a>
      <aside className="sticky top-0 hidden h-screen border-r bg-sidebar md:block" aria-label="Sidebar">
        <Sidebar projectId={projectId} />
      </aside>
      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background px-3 md:px-6">
          <div className="md:hidden"><MobileMenu projectId={projectId} /></div>
          <div className="min-w-0 flex-1"><Crumbs projectId={projectId} /></div>
          <ThemeToggle />
          <UserMenu me={me} />
        </header>
        <main id="main" tabIndex={-1} className={cn("mx-auto w-full max-w-5xl flex-1 px-4 py-6 outline-none md:px-6 md:py-8")}>{children}</main>
      </div>
    </div>
  )
}

