import { Link, useNavigate } from "@tanstack/react-router"
import { useEffect } from "react"
import { toast } from "sonner"
import { DatePicker } from "@/components/patterns/date-picker"
import { FilterSelect } from "@/components/patterns/filter-select"
import { PageHeader } from "@/components/patterns/page-header"
import { SearchBox } from "@/components/patterns/search-box"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, ArrowRight, Clock, Users, UserPlus, X } from "@/icons"
import { projectError } from "@/features/projects/errors"
import { formatPlainDate, formatDateTime, plural } from "@/lib/format"
import { ApiError } from "@/lib/api"
import { EXPLORE_PAGE, type ExploreFilters, type ExploreProject } from "./api"
import { useExplore, useExploreTags, useRequestJoin } from "./queries"
import { actionFor } from "./state"

export type ExploreSearch = ExploreFilters

const DAY = /^\d{4}-\d{2}-\d{2}$/
export function validateExploreSearch(s: Record<string, unknown>): ExploreSearch {
  const page = Number(s.page)
  const text = (v: unknown, max: number) => (typeof v === "string" && v.trim() ? v.trim().slice(0, max) : undefined)
  const day = (v: unknown) => (typeof v === "string" && DAY.test(v) && !Number.isNaN(Date.parse(v)) ? v : undefined)
  return { q: text(s.q, 100), tag: text(s.tag, 30), after: day(s.after), before: day(s.before), page: Number.isInteger(page) && page > 1 && page <= 10_000 ? page : undefined }
}

function joinError(e: unknown): string {
  return e instanceof ApiError && e.status === 404 ? "That project isn't listed any more." : projectError(e)
}

function Row({ project }: { project: ExploreProject }) {
  const join = useRequestJoin()
  const navigate = useNavigate()
  const action = actionFor(project)
  const dates = [project.start_date && `from ${formatPlainDate(project.start_date)}`, project.end_date && `to ${formatPlainDate(project.end_date)}`].filter(Boolean).join(" ")
  return (
    <li className="flex flex-wrap items-start gap-x-4 gap-y-2 py-4">
      <div className="min-w-0 flex-1 space-y-1">
        <h2 className="flex flex-wrap items-center gap-2 text-sm font-semibold">{project.name}{project.is_demo && <Badge variant="secondary">Demo</Badge>}</h2>
        {project.description && <p className="line-clamp-2 text-sm text-muted-foreground">{project.description}</p>}
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5"><UserAvatar name={project.owner.first_name} src={project.owner.avatar_url} size="sm" />{project.owner.first_name}</span>
          <span className="inline-flex items-center gap-1"><Users className="size-3.5" aria-hidden />{plural(project.member_count, "member")}</span>
          {dates && <span>{dates}</span>}
          {project.tags.length > 0 && <span>{project.tags.map((t) => `#${t}`).join(" ")}</span>}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        {action.kind === "pending" && <span className="inline-flex min-h-(--ctl-h) items-center gap-1.5 text-sm text-muted-foreground"><Clock className="size-4" aria-hidden />Request sent. The owner will review it.</span>}
        {action.kind === "cooldown" && <span className="inline-flex min-h-(--ctl-h) items-center gap-1.5 text-sm text-muted-foreground"><Clock className="size-4" aria-hidden />You can ask again after {formatDateTime(action.until)}</span>}
        {action.kind === "join" && (
          <Button variant="outline" icon={<UserPlus />} loading={join.isPending} onClick={() => join.mutate(project.id, { onSuccess: (r) => { toast.success(`Joined ${project.name}.`); if (r.status === "joined") navigate({ to: "/app/projects/$projectId", params: { projectId: r.project.id } }) }, onError: (e) => toast.error(joinError(e)) })}>Join</Button>
        )}
        {action.kind === "request" && (
          <Button variant="outline" icon={<UserPlus />} loading={join.isPending} onClick={() => join.mutate(project.id, { onSuccess: () => toast.success(`Request sent to ${project.owner.first_name}.`), onError: (e) => toast.error(joinError(e)) })}>Ask to join</Button>
        )}
      </div>
    </li>
  )
}

export function ExplorePage({ search, onSearch }: { search: ExploreSearch; onSearch: (next: ExploreSearch) => void }) {
  useDocumentTitle("Explore · Pro-Goal")
  const page = search.page ?? 1
  const { data, isPending, isError, error, isFetching, refetch } = useExplore(search)
  const tags = useExploreTags()
  const count = data?.meta.count ?? 0
  const lastPage = Math.max(1, Math.ceil(count / EXPLORE_PAGE))
  const overshoot = !!data && data.items.length === 0 && count > 0 && page > lastPage
  useEffect(() => {
    if (overshoot) onSearch({ ...search, page: lastPage > 1 ? lastPage : undefined })
  }, [overshoot, lastPage, search, onSearch])
  const filtered = !!(search.q || search.tag || search.after || search.before)
  const set = (patch: Partial<ExploreSearch>) => onSearch({ ...search, ...patch, page: undefined })
  const tagOptions = (tags.data?.items ?? []).map((t) => ({ value: t.name, label: `#${t.name} (${t.projects})` }))
  if (search.tag && !tagOptions.some((o) => o.value === search.tag)) tagOptions.unshift({ value: search.tag, label: `#${search.tag}` })

  return (
    <div className="space-y-6">
      <PageHeader title="Explore" description="Projects whose owners listed them. Demo projects are open to everyone and read-only; for other projects the owner approves each request. Strangers see the name, description, tags, owner, size and dates, never tasks or notes." />
      <div role="search" aria-label="Find projects" className="flex flex-wrap items-center gap-2">
        <SearchBox value={search.q ?? ""} onCommit={(q) => set({ q })} placeholder="Search projects" />
        <FilterSelect label="Tag" value={search.tag} onChange={(tag) => set({ tag })} options={tagOptions} />
        <DatePicker id="x-after" placeholder="Starts after" value={search.after ?? null} onChange={(v) => set({ after: v ?? undefined })} />
        <DatePicker id="x-before" placeholder="Ends before" value={search.before ?? null} onChange={(v) => set({ before: v ?? undefined })} />
        {filtered && <Button variant="ghost" icon={<X />} onClick={() => onSearch({})}>Clear filters</Button>}
      </div>
      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading projects">{[0, 1, 2].map((i) => <li key={i} className="space-y-2 py-4"><Skeleton className="h-4 w-48" /><Skeleton className="h-4 w-80" /></li>)}</ul>
      ) : isError ? (
        <Empty><EmptyHeader><EmptyTitle>Couldn't load projects</EmptyTitle><EmptyDescription>{projectError(error)}</EmptyDescription></EmptyHeader><Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></Empty>
      ) : data.items.length === 0 && !overshoot ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>{filtered ? "No projects match" : "Nothing listed yet"}</EmptyTitle>
            <EmptyDescription>{filtered ? "Try fewer words, another tag, or wider dates." : "Owners choose to list a project from its settings."}</EmptyDescription>
          </EmptyHeader>
          {filtered ? <Button variant="outline" icon={<X />} onClick={() => onSearch({})}>Clear filters</Button> : <Button variant="outline" icon={<UserPlus />} nativeButton={false} render={<Link to="/app" />}>Go to your projects</Button>}
        </Empty>
      ) : (
        <ul className="divide-y border-y" aria-label="Listed projects" aria-busy={isFetching}>{data.items.map((p) => <Row key={p.id} project={p} />)}</ul>
      )}
      {data && count > EXPLORE_PAGE && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{(page - 1) * EXPLORE_PAGE + 1} to {Math.min(page * EXPLORE_PAGE, count)} of {plural(count, "project")}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => onSearch({ ...search, page: page > 2 ? page - 1 : undefined })}>Previous</Button>
            <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={page >= lastPage} onClick={() => onSearch({ ...search, page: page + 1 })}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
