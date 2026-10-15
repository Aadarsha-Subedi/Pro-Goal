import { useEffect, useState } from "react"
import { toast } from "sonner"
import { ErrorScreen } from "@/components/patterns/error-screen"
import { NotFoundScreen } from "@/components/patterns/not-found-screen"
import { ApiError } from "@/lib/api"
import { BootScreen } from "@/components/patterns/boot-screen"
import { Button } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowsClockwise, ArrowUUpLeft, CheckCircle, Info, Plus, Warning, XCircle, ClipboardText } from "@/icons"
import { Section, Specimen } from "../section"

const BANNERS = [
  { Icon: Info, tone: "text-info", title: "Join request pending", body: "The owner has not approved your request yet." },
  { Icon: Warning, tone: "text-warning", title: "Storage at 90%", body: "Uploads pause at 100%. Remove files or ask the owner to raise the quota." },
  { Icon: XCircle, tone: "text-destructive", title: "Slack disconnected", body: "The token was revoked. Reconnect to resume notifications.", action: "Reconnect" },
]

function BootPreview() {
  const [full, setFull] = useState(false)
  const [run, setRun] = useState(0)
  useEffect(() => {
    if (!full) return
    const t = window.setTimeout(() => setFull(false), 4000)
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setFull(false)
    window.addEventListener("keydown", esc)
    return () => { window.clearTimeout(t); window.removeEventListener("keydown", esc) }
  }, [full])
  return (
    <Specimen title="Page loading screen" note="Shown when nothing can render yet: refresh, reload, first sign-in. It waits 180ms before fading in so fast loads never flash it. In-app navigation keeps using skeletons. After a long wait it says so and offers Try again.">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="relative h-72 overflow-hidden rounded-lg border"><BootScreen key={run} contained message="Checking your session" /></div>
        <div className="relative h-72 overflow-hidden rounded-lg border"><BootScreen contained slow onRetry={() => setRun(run + 1)} /></div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button variant="outline" size="sm" icon={<ArrowsClockwise />} onClick={() => setRun(run + 1)}>Replay</Button>
        <Button variant="outline" size="sm" onClick={() => setFull(true)}>Show full screen for 4 seconds</Button>
      </div>
      {full && <BootScreen message="Signing you in" />}
    </Specimen>
  )
}

function ErrorPreview() {
  return (
    <Specimen title="Page failed to load" note="The router's fallback when a page throws, for example a 500 from the server. Same frame again: one sentence, Try again re-runs the page's loaders, home as the way out. The raw error is never shown.">
      <div className="relative overflow-hidden rounded-lg border"><ErrorScreen error={new ApiError(500, "server_error", "Internal Server Error")} reset={() => {}} /></div>
    </Specimen>
  )
}

function NotFoundPreview() {
  return (
    <Specimen title="Page not found" note="Same frame as the loading screen. Shows the address that was asked for, offers home (which sends a signed-in person to their projects) and back. It renders inside the app shell when the miss happens under /app.">
      <div className="relative overflow-hidden rounded-lg border"><NotFoundScreen path="/app/projects/apollo/roadmap" onBack={() => {}} /></div>
    </Specimen>
  )
}

export function Feedback() {
  return (
    <Section id="feedback" title="Feedback and states" intro="Banners are flat rows with an icon, not boxed alerts. Every list has loading, empty and error states.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Inline banners">
          <div className="divide-y border-y">
            {BANNERS.map(({ Icon, tone, title, body, action }) => (
              <div key={title} className="flex gap-3 px-4 py-3">
                <Icon weight="fill" className={`mt-0.5 size-4 shrink-0 ${tone}`} />
                <div className="text-sm"><p className="font-medium">{title}</p><p className="text-muted-foreground">{body}</p>{action && <Button size="xs" variant="outline" className="mt-2" icon={<ArrowsClockwise />}>{action}</Button>}</div>
              </div>
            ))}
          </div>
        </Specimen>
        <Specimen title="Toasts" note="Click to trigger. Icon and color match the inline banners.">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" icon={<CheckCircle weight="fill" />} onClick={() => toast.success("Task moved to Done")}>Success</Button>
            <Button variant="outline" icon={<Info weight="fill" />} onClick={() => toast.info("Join request sent", { description: "The owner will be notified." })}>Info</Button>
            <Button variant="outline" icon={<Warning weight="fill" />} onClick={() => toast.warning("Storage almost full", { description: "1.8 of 2 GB used." })}>Warning</Button>
            <Button variant="outline" icon={<XCircle weight="fill" />} onClick={() => toast.error("Could not save", { description: "Check your connection.", action: { label: "Retry", onClick: () => {} } })}>Danger</Button>
            <Button variant="outline" icon={<ArrowUUpLeft />} onClick={() => toast.success("Task archived", { action: { label: "Undo", onClick: () => {} } })}>With undo</Button>
          </div>
        </Specimen>
      </div>

      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Loading" note="Skeleton matches the row it replaces">
          <div className="space-y-3 rounded-lg border p-4" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="size-4 rounded-full" />
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        </Specimen>
        <Specimen title="Progress">
          <div className="space-y-4">
            <div><div className="mb-1.5 flex justify-between text-xs text-muted-foreground"><span>Storage</span><span className="tabular-nums">1.8 of 2 GB</span></div><Progress value={90} /></div>
            <div><div className="mb-1.5 flex justify-between text-xs text-muted-foreground"><span>Sprint</span><span className="tabular-nums">12 of 20 done</span></div><Progress value={60} /></div>
          </div>
        </Specimen>
      </div>

      <BootPreview />

      <NotFoundPreview />

      <ErrorPreview />

      <Specimen title="Empty state">
        <div className="rounded-lg border">
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon"><ClipboardText weight="duotone" /></EmptyMedia>
              <EmptyTitle>No tasks match this filter</EmptyTitle>
              <EmptyDescription>Clear a filter or create a task. Empty states always offer the next action.</EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <Button icon={<Plus weight="bold" />}>Create task</Button>
            </EmptyContent>
          </Empty>
        </div>
      </Specimen>
    </Section>
  )
}
