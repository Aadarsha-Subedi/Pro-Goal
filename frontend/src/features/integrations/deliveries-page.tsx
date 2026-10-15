import { Link, useParams } from "@tanstack/react-router"
import { useEffect } from "react"
import { toast } from "sonner"
import { FilterSelect } from "@/components/patterns/filter-select"
import { PageHeader } from "@/components/patterns/page-header"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, ArrowRight, ArrowsClockwise, CheckCircle, Clock, X, XCircle } from "@/icons"
import { useLockText } from "@/features/permissions/use-lock-text"
import { can, useCurrentProject } from "@/features/projects/current"
import { formatDateTime, plural } from "@/lib/format"
import { DELIVERY_PAGE, type Delivery, type DeliveryStatus } from "./api"
import { integrationError, isForbidden } from "./errors"
import { eventInfo } from "./events"
import { useDeliveries, useIntegrationMutations } from "./queries"

export interface DeliverySearch {
  status?: DeliveryStatus
  page?: number
}

const STATUSES: { value: DeliveryStatus; label: string }[] = [
  { value: "failed", label: "Failed" },
  { value: "pending", label: "Waiting" },
  { value: "success", label: "Delivered" },
]

export function validateDeliverySearch(s: Record<string, unknown>): DeliverySearch {
  const page = Number(s.page)
  return { status: STATUSES.find((o) => o.value === s.status)?.value, page: Number.isInteger(page) && page > 1 && page <= 10_000 ? page : undefined }
}

const MAX_ATTEMPTS = 6

function DeliveryStatusMark({ d }: { d: Delivery }) {
  if (d.status === "success") return <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><CheckCircle weight="fill" className="size-3.5 text-success" aria-hidden />Delivered</span>
  if (d.status === "failed") return <span className="inline-flex items-center gap-1 text-xs text-destructive"><XCircle weight="fill" className="size-3.5" aria-hidden />Failed</span>
  return <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Clock className="size-3.5" aria-hidden />{d.next_retry_at ? `Retrying ${formatDateTime(d.next_retry_at)}` : "Waiting"}</span>
}

export function DeliveriesPage({ search, onSearch }: { search: DeliverySearch; onSearch: (next: DeliverySearch) => void }) {
  const { id, project } = useCurrentProject()
  const { integrationId } = useParams({ strict: false }) as { integrationId: string }
  useDocumentTitle(`Delivery log · ${project.name} · Pro-Goal`)
  const lockText = useLockText()
  const page = search.page ?? 1
  const { data, isPending, isError, error, isFetching, refetch } = useDeliveries(id, integrationId, search.status, page)
  const { replay } = useIntegrationMutations(id)
  const canReplay = can(project, "integration.slack.manage") && !project.is_archived
  const count = data?.meta.count ?? 0
  const lastPage = Math.max(1, Math.ceil(count / DELIVERY_PAGE))
  const overshoot = !!data && data.items.length === 0 && count > 0 && page > lastPage
  useEffect(() => {
    if (overshoot) onSearch({ ...search, page: lastPage > 1 ? lastPage : undefined })
  }, [overshoot, lastPage, search, onSearch])

  const resend = (d: Delivery) =>
    replay.mutate({ id: integrationId, deliveryId: d.id }, { onSuccess: () => toast.success("Queued to send again."), onError: (e) => toast.error(integrationError(e)) })

  return (
    <div className="space-y-6">
      <div><Button variant="ghost" icon={<ArrowLeft />} nativeButton={false} render={<Link to="/app/projects/$projectId/integrations" params={{ projectId: id }} />}>Integrations</Button></div>
      <PageHeader title="Delivery log" description="Every message sent to Slack, kept for 30 days. Failed ones retry on their own, then wait here to be sent again by hand." />
      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect label="Status" value={search.status} onChange={(status) => onSearch({ status: status as DeliveryStatus | undefined })} options={STATUSES} />
        {search.status && <Button variant="ghost" icon={<X />} onClick={() => onSearch({})}>Clear filter</Button>}
      </div>
      {!canReplay && <p className="text-xs text-muted-foreground">{project.is_archived ? "This project is archived." : lockText("integration.slack.manage")} Sending again is off for you.</p>}

      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading deliveries">{[0, 1, 2, 3].map((i) => <li key={i} className="py-3"><Skeleton className="h-4 w-72" /></li>)}</ul>
      ) : isError ? (
        isForbidden(error) ? (
          <Empty><EmptyHeader><EmptyTitle>You can't read the log</EmptyTitle><EmptyDescription>{lockText("integration.logs.view")}</EmptyDescription></EmptyHeader></Empty>
        ) : (
          <Empty><EmptyHeader><EmptyTitle>Couldn't load the log</EmptyTitle><EmptyDescription>{integrationError(error)}</EmptyDescription></EmptyHeader><Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></Empty>
        )
      ) : data.items.length === 0 && !overshoot ? (
        <Empty><EmptyHeader><EmptyTitle>{search.status ? "Nothing with that status" : "Nothing sent yet"}</EmptyTitle><EmptyDescription>{search.status ? "Pick another status, or clear the filter." : "Messages show up here when something happens in the project."}</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <ul className="divide-y border-y" aria-label="Deliveries" aria-busy={isFetching}>
          {data.items.map((d) => {
            const info = eventInfo(d.event_type)
            const Icon = info.icon
            return (
              <li key={d.id} className="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-1 py-2">
                <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-x-3 text-sm font-medium"><span>{d.direction === "in" ? `Received: ${info.label}` : info.label}</span><DeliveryStatusMark d={d} /></p>
                  <p className="text-xs text-muted-foreground">{formatDateTime(d.created_at)} · {d.attempt < 1 ? "Not tried yet" : d.attempt > 1 || d.status !== "success" ? `Attempt ${Math.min(d.attempt, MAX_ATTEMPTS)} of ${MAX_ATTEMPTS}` : "Sent first try"}{d.response_code ? ` · Answer ${d.response_code}` : ""}</p>
                  {d.error && <p className="break-words text-xs text-destructive">{d.error}</p>}
                </div>
                {d.status === "failed" && <Button variant="outline" size="sm" icon={<ArrowsClockwise />} disabled={!canReplay || replay.isPending} loading={replay.isPending && replay.variables?.deliveryId === d.id} onClick={() => resend(d)}>Send again</Button>}
              </li>
            )
          })}
        </ul>
      )}
      {data && count > DELIVERY_PAGE && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{(page - 1) * DELIVERY_PAGE + 1} to {Math.min(page * DELIVERY_PAGE, count)} of {plural(count, "delivery", "deliveries")}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => onSearch({ ...search, page: page > 2 ? page - 1 : undefined })}>Previous</Button>
            <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={page >= lastPage} onClick={() => onSearch({ ...search, page: page + 1 })}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
