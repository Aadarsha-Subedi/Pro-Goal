import { useRef, useState } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { PriorityLabel, STATUSES, StatusLabel } from "@/components/patterns/status"
import { CalendarBlank, Plus } from "@/icons"
import { useFlip } from "@/motion"
import { TASKS } from "../data"
import { Section, Specimen } from "../section"

const SORTS = {
  due: (a: (typeof TASKS)[number], b: (typeof TASKS)[number]) => a.due.localeCompare(b.due, undefined, { numeric: true }),
  priority: (a: (typeof TASKS)[number], b: (typeof TASKS)[number]) => ["urgent", "high", "medium", "low"].indexOf(a.priority) - ["urgent", "high", "medium", "low"].indexOf(b.priority),
  number: (a: (typeof TASKS)[number], b: (typeof TASKS)[number]) => b.number - a.number,
}

export function Kanban() {
  const [sort, setSort] = useState<keyof typeof SORTS>("priority")
  const ref = useRef<HTMLDivElement>(null)
  const capture = useFlip(ref, sort)
  const cols = STATUSES.filter((s) => s !== "cancelled")
  return (
    <Section id="kanban" title="Board" intro="Columns are sorted by a field, never dragged by hand. Columns are open lanes with one row per task; there is no card around the card.">
      <Specimen title="Sorted by field" note="Change the sort and watch rows flip into place (GSAP Flip)">
        <ToggleGroup variant="outline" size="sm" value={[sort]} onValueChange={(v) => {
          if (!v[0]) return
          capture()
          setSort(v[0] as keyof typeof SORTS)
        }} className="mb-4">
          <ToggleGroupItem value="priority">Priority</ToggleGroupItem>
          <ToggleGroupItem value="due">Due date</ToggleGroupItem>
          <ToggleGroupItem value="number">Newest</ToggleGroupItem>
        </ToggleGroup>
        <div ref={ref} className="grid gap-px overflow-hidden rounded-lg border bg-border md:grid-cols-4">
          {cols.map((s) => {
            const items = TASKS.filter((t) => t.status === s).sort(SORTS[sort])
            return (
              <div key={s} className="min-h-56 bg-background">
                <div className="flex h-10 items-center justify-between border-b px-3">
                  <span className="inline-flex items-center gap-2 text-sm font-medium"><StatusLabel status={s} /><span className="text-xs tabular-nums text-muted-foreground">{items.length}</span></span>
                  <Button variant="ghost" size="icon-xs" label={`Add to ${s}`}><Plus weight="bold" /></Button>
                </div>
                <ul>
                  {items.map((t) => (
                    <li key={t.id} data-flip-id={t.id} className="border-b px-3 py-2.5 transition-colors last:border-b-0 hover:bg-muted/50">
                      <p className="text-sm leading-snug font-medium">{t.title}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs whitespace-nowrap text-muted-foreground">
                        <span className="font-mono">PM-{t.number}</span>
                        <PriorityLabel priority={t.priority} className="text-xs" />
                        <span className="ml-auto inline-flex items-center gap-1"><CalendarBlank className="size-3.5" />{t.due}</span>
                        <Avatar size="sm"><AvatarFallback>{t.assignee.split(" ").map((p) => p[0]).join("")}</AvatarFallback></Avatar>
                      </div>
                      {t.tags.length > 0 && <div className="mt-2 flex gap-1">{t.tags.map((g) => <Badge key={g} variant="secondary">{g}</Badge>)}</div>}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </Specimen>
    </Section>
  )
}
