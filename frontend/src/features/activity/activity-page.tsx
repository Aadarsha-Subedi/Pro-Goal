import { Link } from "@tanstack/react-router"
import { useEffect } from "react"
import { DatePicker } from "@/components/patterns/date-picker"
import { FilterSelect } from "@/components/patterns/filter-select"
import { PageHeader } from "@/components/patterns/page-header"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, ArrowRight, X } from "@/icons"
import { useLockText } from "@/features/permissions/use-lock-text"
import { can, useCurrentProject } from "@/features/projects/current"
import { projectError } from "@/features/projects/errors"
import { membersQuery } from "@/features/projects/queries"
import { useLazyOptions } from "@/lib/lazy-options"
import { useQuery } from "@tanstack/react-query"
import { formatDateTime, plural } from "@/lib/format"
import { ACTIVITY_PAGE, type ActivityEntry } from "./api"
import { describe, ENTITY_OPTIONS } from "./describe"
import { useActivity } from "./queries"

export interface ActivitySearch {
  actor?: string
  entity?: string
  after?: string
  before?: string
  page?: number
}

const DAY = /^\d{4}-\d{2}-\d{2}$/
export function validateActivitySearch(s: Record<string, unknown>): ActivitySearch {
  const page = Number(s.page)
  const day = (v: unknown) => (typeof v === "string" && DAY.test(v) && !Number.isNaN(Date.parse(v)) ? v : undefined)
  return {
    actor: typeof s.actor === "string" && /^[0-9a-f-]{36}$/i.test(s.actor) ? s.actor : undefined,
    entity: ENTITY_OPTIONS.find((o) => o.value === s.entity)?.value,
    after: day(s.after),
    before: day(s.before),
    page: Number.isInteger(page) && page > 1 && page <= 10_000 ? page : undefined,
  }
}

function Row({ entry, projectId, taskKey }: { entry: ActivityEntry; projectId: string; taskKey: string }) {
  const d = describe(entry, taskKey)
  const Icon = d.icon
  const name = entry.actor.first_name
  const sentence = <><span className="font-medium">{name}</span> {d.verb}</>
  return (
    <li className="flex gap-3 py-3">
      <UserAvatar name={name} src={entry.actor.avatar_url} />
      <div className="min-w-0 flex-1">
        <p className="flex items-start gap-1.5 text-sm"><Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden /><span className="min-w-0 break-words">
          {d.link?.kind === "task" ? <Link to="/app/projects/$projectId/tasks/$number" params={{ projectId, number: String(d.link.number) }} className="rounded underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50">{sentence}</Link>
            : d.link?.kind === "note" ? <Link to="/app/projects/$projectId/notes/$noteId" params={{ projectId, noteId: d.link.id }} className="rounded underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50">{sentence}</Link>
            : sentence}
        </span></p>
        {d.details.length > 0 && (
          <ul className="mt-1 space-y-0.5 pl-5.5 text-xs text-muted-foreground">
            {d.details.map((x) => <li key={x.field} className="break-words">{x.field}: {x.note ?? <>{x.from} <ArrowRight className="mx-0.5 inline size-3" aria-hidden /><span className="sr-only">to</span> {x.to}</>}</li>)}
          </ul>
        )}
      </div>
      <time dateTime={entry.created_at} className="shrink-0 text-xs text-muted-foreground">{formatDateTime(entry.created_at)}</time>
    </li>
  )
}

export function ActivityPage({ search, onSearch }: { search: ActivitySearch; onSearch: (next: ActivitySearch) => void }) {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Activity · ${project.name} · Pro-Goal`)
  const lockText = useLockText()
  // The Person dropdown lists members; they load when it opens, or at once if one is already chosen in the URL.
  const members = useLazyOptions((enabled) => useQuery({ ...membersQuery(id), enabled: enabled && !!id }), !!search.actor)
  const page = search.page ?? 1
  const { data, isPending, isError, error, isFetching, refetch } = useActivity(id, search)
  const sees = can(project, "activity.view")
  const count = data?.meta.count ?? 0
  const lastPage = Math.max(1, Math.ceil(count / ACTIVITY_PAGE))
  const overshoot = !!data && data.items.length === 0 && count > 0 && page > lastPage
  useEffect(() => {
    if (overshoot) onSearch({ ...search, page: lastPage > 1 ? lastPage : undefined })
  }, [overshoot, lastPage, search, onSearch])
  const filtered = !!(search.actor || search.entity || search.after || search.before)
  const set = (patch: Partial<ActivitySearch>) => onSearch({ ...search, ...patch, page: undefined })

  return (
    <div className="space-y-6">
      <PageHeader title="Activity" description={sees ? "Everything that changed in this project, newest first. Kept for one year." : "Your own actions in this project, newest first."} />
      {!sees && <p className="text-xs text-muted-foreground">{lockText("activity.view")} to see what everyone did.</p>}
      <div className="flex flex-wrap items-center gap-2">
        {sees && <FilterSelect label="Person" value={search.actor} onChange={(actor) => set({ actor })} source={members} options={members.items.map((m) => ({ value: m.id, label: m.display_name || m.first_name }))} />}
        <FilterSelect label="Type" value={search.entity} onChange={(entity) => set({ entity })} options={ENTITY_OPTIONS} />
        <DatePicker id="a-after" placeholder="From" value={search.after ?? null} onChange={(v) => set({ after: v ?? undefined })} />
        <DatePicker id="a-before" placeholder="To" value={search.before ?? null} onChange={(v) => set({ before: v ?? undefined })} />
        {filtered && <Button variant="ghost" icon={<X />} onClick={() => onSearch({})}>Clear filters</Button>}
      </div>

      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading activity">{[0, 1, 2, 3].map((i) => <li key={i} className="flex gap-3 py-3"><Skeleton className="size-8 rounded-full" /><Skeleton className="h-4 w-72" /></li>)}</ul>
      ) : isError ? (
        <Empty><EmptyHeader><EmptyTitle>Couldn't load activity</EmptyTitle><EmptyDescription>{projectError(error)}</EmptyDescription></EmptyHeader><Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></Empty>
      ) : data.items.length === 0 && !overshoot ? (
        <Empty><EmptyHeader><EmptyTitle>{filtered ? "Nothing matches" : "No activity yet"}</EmptyTitle><EmptyDescription>{filtered ? "Widen the dates or clear a filter." : "Changes to tasks, notes, members and settings show up here."}</EmptyDescription></EmptyHeader>{filtered && <Button variant="outline" icon={<X />} onClick={() => onSearch({})}>Clear filters</Button>}</Empty>
      ) : (
        <ul className="divide-y border-y" aria-label="Activity" aria-busy={isFetching}>
          {data.items.map((e) => <Row key={e.id} entry={e} projectId={id} taskKey={project.task_key} />)}
        </ul>
      )}
      {data && count > ACTIVITY_PAGE && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{(page - 1) * ACTIVITY_PAGE + 1} to {Math.min(page * ACTIVITY_PAGE, count)} of {plural(count, "entry", "entries")}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => onSearch({ ...search, page: page > 2 ? page - 1 : undefined })}>Previous</Button>
            <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={page >= lastPage} onClick={() => onSearch({ ...search, page: page + 1 })}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
