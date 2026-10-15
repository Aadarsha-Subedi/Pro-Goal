import { UsageMeter } from "@/components/patterns/usage-meter"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowClockwise } from "@/icons"
import { formatBytes } from "./limits"
import { useMyUsage, useProjectUsage } from "./queries"

const CATEGORY_LABEL = { image: "Images", document: "Documents", audio: "Audio" } as const

/** Project file storage and your own allowance: meters in words, then who and what is using the space. */
export function StorageSettings({ projectId }: { projectId: string }) {
  const project = useProjectUsage(projectId)
  const mine = useMyUsage()
  if (project.isPending || mine.isPending) return <div className="space-y-3" aria-busy="true" aria-label="Loading storage"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
  if (project.isError || mine.isError || !project.data || !mine.data)
    return (
      <div className="flex items-center gap-3 text-sm">
        <span className="text-muted-foreground">Couldn't load storage usage.</span>
        <Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => { void project.refetch(); void mine.refetch() }}>Try again</Button>
      </div>
    )
  const p = project.data
  const m = mine.data
  const categories = Object.entries(p.by_category).filter(([, b]) => (b ?? 0) > 0) as [keyof typeof CATEGORY_LABEL, number][]
  return (
    <div className="space-y-6">
      <UsageMeter label="This project" used={p.bytes_used} limit={p.quota_bytes} format={formatBytes} />
      {(categories.length > 0 || p.by_uploader.length > 0) && (
        <div className="grid gap-6 sm:grid-cols-2">
          {categories.length > 0 && (
            <div>
              <h3 className="mb-1 text-sm font-medium">By type</h3>
              <ul className="divide-y border-y text-sm" aria-label="Storage by type">
                {categories.map(([c, b]) => <li key={c} className="flex justify-between py-1.5"><span>{CATEGORY_LABEL[c]}</span><span className="tabular-nums text-muted-foreground">{formatBytes(b)}</span></li>)}
              </ul>
            </div>
          )}
          {p.by_uploader.length > 0 && (
            <div>
              <h3 className="mb-1 text-sm font-medium">By person</h3>
              <ul className="divide-y border-y text-sm" aria-label="Storage by person">
                {p.by_uploader.map((u) => <li key={u.user_id ?? "deleted"} className="flex justify-between py-1.5"><span>{u.first_name}</span><span className="tabular-nums text-muted-foreground">{formatBytes(u.bytes)}</span></li>)}
              </ul>
            </div>
          )}
        </div>
      )}
      <div className="space-y-2">
        <UsageMeter label="Your files, across all projects" used={m.bytes_used} limit={m.quota_bytes} format={formatBytes} />
        {m.by_project.length > 0 && <p className="text-xs text-muted-foreground">{m.by_project.map((x) => `${x.project_name} ${formatBytes(x.bytes)}`).join(" · ")}</p>}
      </div>
    </div>
  )
}
