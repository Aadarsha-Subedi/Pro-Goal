import { Link } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { StatusBanner } from "@/components/patterns/status-banner"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, CheckCircle, ListMagnifyingGlass, PlugsConnected, Plugs, Prohibit, SlackLogo, WarningCircle } from "@/icons"
import { useLockText } from "@/features/permissions/use-lock-text"
import { can, useCurrentProject } from "@/features/projects/current"
import { formatTimestamp, plural } from "@/lib/format"
import { slackApi, type Integration } from "./api"
import { integrationError, isForbidden, slackReturn } from "./errors"
import { useIntegrationMutations, useIntegrations } from "./queries"
import { SlackMappings } from "./slack-panel"

export interface IntegrationsSearch {
  slack?: string
  reason?: string
}

export function validateIntegrationsSearch(s: Record<string, unknown>): IntegrationsSearch {
  const t = (v: unknown) => (typeof v === "string" && /^[a-z_]{1,40}$/.test(v) ? v : undefined)
  return { slack: t(s.slack), reason: t(s.reason) }
}

const STATUS = {
  active: { icon: CheckCircle, weight: "fill" as const, cls: "text-success", text: "Active" },
  needs_attention: { icon: WarningCircle, weight: "fill" as const, cls: "text-warning", text: "Needs attention" },
  disconnected: { icon: Prohibit, weight: "regular" as const, cls: "text-muted-foreground", text: "Disconnected" },
}

/** A project keeps old disconnected rows next to a new connection. The current one is the live row, else the newest. */
export function pickCurrent(items: Integration[], provider: string): Integration | undefined {
  const mine = items.filter((i) => i.provider === provider)
  return mine.find((i) => i.status !== "disconnected") ?? [...mine].sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
}

export function IntegrationStatus({ status }: { status: Integration["status"] }) {
  const s = STATUS[status]
  const Icon = s.icon
  return <span className={`inline-flex items-center gap-1 text-xs ${status === "needs_attention" ? "font-medium text-warning-text" : "font-normal text-muted-foreground"}`}><Icon weight={s.weight} className={`size-3.5 ${s.cls}`} aria-hidden />{s.text}</span>
}

export function IntegrationsPage({ search, onSearch }: { search: IntegrationsSearch; onSearch: (next: IntegrationsSearch) => void }) {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Integrations · ${project.name} · Pro-Goal`)
  const { data, isPending, isError, error, refetch } = useIntegrations(id)
  const { disconnect } = useIntegrationMutations(id)
  const lockText = useLockText()
  const [connecting, setConnecting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const canManage = can(project, "integration.slack.manage")
  const canLogs = can(project, "integration.logs.view") || canManage
  const frozen = project.is_archived

  const handled = useRef(false)
  useEffect(() => {
    const result = slackReturn(search.slack, search.reason)
    if (!result || handled.current) return
    handled.current = true
    if (result.kind === "success") toast.success(result.text)
    else toast.error(result.text)
    onSearch({})
  }, [search, onSearch])

  const connect = async () => {
    setConnecting(true)
    try {
      const { url } = await slackApi.installUrl(id)
      window.location.assign(url)
    } catch (e) {
      toast.error(integrationError(e))
      setConnecting(false)
    }
  }

  const slack = pickCurrent(data?.items ?? [], "slack")
  const live = slack && slack.status !== "disconnected"
  const connectLabel = slack ? "Reconnect Slack" : "Add to Slack"

  const body = isPending ? (
    <div aria-busy="true" aria-label="Loading integrations" className="space-y-2"><Skeleton className="h-14 w-full" /><Skeleton className="h-24 w-full" /></div>
  ) : isError ? (
    isForbidden(error) ? (
      <Empty><EmptyHeader><EmptyTitle>You can't see integrations</EmptyTitle><EmptyDescription>{lockText("integration.logs.view")}</EmptyDescription></EmptyHeader></Empty>
    ) : (
      <Empty><EmptyHeader><EmptyTitle>Couldn't load integrations</EmptyTitle><EmptyDescription>{integrationError(error)}</EmptyDescription></EmptyHeader><Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></Empty>
    )
  ) : (
    <div className="space-y-6">
      {slack?.status === "needs_attention" && (
        <StatusBanner tone="warning" title="Slack stopped sending." action={<span className="flex flex-wrap gap-2">{canLogs && <Button size="sm" variant="outline" icon={<ListMagnifyingGlass />} nativeButton={false} render={<Link to="/app/projects/$projectId/integrations/$integrationId/deliveries" params={{ projectId: id, integrationId: slack.id }} search={{ status: "failed" }} />}>See why</Button>}{canManage && !frozen && <Button size="sm" icon={<PlugsConnected />} loading={connecting} onClick={connect}>Reconnect Slack</Button>}</span>}>
          {plural(slack.consecutive_failures, "delivery", "deliveries")} in a row failed. Waiting messages go out once you reconnect.
        </StatusBanner>
      )}
      <section aria-labelledby="slack" className="space-y-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b pb-3">
          <SlackLogo className="size-6 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0 flex-1">
            <h2 id="slack" className="flex flex-wrap items-center gap-x-2 text-sm font-semibold">Slack{slack ? <IntegrationStatus status={slack.status} /> : <span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground"><Plugs className="size-3.5" aria-hidden />Not connected</span>}</h2>
            <p className="text-xs text-muted-foreground">
              {slack && live ? `Workspace ${slack.external_workspace_id}${slack.installed_by ? ` · connected by ${slack.installed_by.first_name}` : ""} · since ${formatTimestamp(slack.created_at)}` : "Post task and comment updates to channels and send direct messages. After connecting, add a channel and invite the bot to it in Slack."}
            </p>
          </div>
          {canLogs && slack && <Button variant="outline" size="sm" icon={<ListMagnifyingGlass />} nativeButton={false} render={<Link to="/app/projects/$projectId/integrations/$integrationId/deliveries" params={{ projectId: id, integrationId: slack.id }} />}>Delivery log</Button>}
          {!live && <Button size="sm" icon={<SlackLogo />} loading={connecting} disabled={!canManage || frozen} onClick={connect}>{connectLabel}</Button>}
          {live && canManage && !frozen && <Button variant="outline" size="sm" icon={<Plugs />} onClick={() => setConfirming(true)}>Disconnect</Button>}
        </div>
        {(!canManage || frozen) && <p className="text-xs text-muted-foreground">{frozen ? "This project is archived, so integrations can't change." : lockText("integration.slack.manage")}</p>}
        {live && canManage && <SlackMappings projectId={id} canManage={canManage} frozen={frozen} />}
      </section>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader title="Integrations" description="Send project events to other tools. Only people with the right permissions can change these." />
      {body}
      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disconnect Slack?</AlertDialogTitle>
            <AlertDialogDescription>The project stops posting to Slack and the stored access is deleted. Channel settings and the delivery log are kept for 30 days. You can connect again later.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Stay connected</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Plugs />} loading={disconnect.isPending} onClick={() => slack && disconnect.mutate(slack.id, { onSuccess: () => { toast.success("Slack was disconnected."); setConfirming(false) }, onError: (e) => { toast.error(integrationError(e)); setConfirming(false) } })}>Disconnect</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
