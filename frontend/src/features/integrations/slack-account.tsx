import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { ArrowClockwise, CheckCircle, Prohibit, SlackLogo } from "@/icons"
import { useState } from "react"
import { integrationError } from "./errors"
import { eventInfo } from "./events"
import { useSavePreference, usePreferences, useSlackLink, useUnlinkSlack } from "./queries"

function Retry({ label, onRetry }: { label: string; onRetry: () => void }) {
  return <div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground">{label}</span><Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={onRetry}>Try again</Button></div>
}

/** Link your own Slack account. People are never matched by email, so DMs and /task commands need this once. */
export function SlackLinkSection() {
  const { data, isPending, isError, error, refetch } = useSlackLink()
  const unlink = useUnlinkSlack()
  const [leaving, setLeaving] = useState(false)
  if (isPending) return <Skeleton className="h-10 w-full" aria-label="Loading Slack link" />
  if (isError) return <Retry label={integrationError(error)} onRetry={() => refetch()} />
  const linked = data.linked_workspaces
  const go = () => { setLeaving(true); window.location.assign(data.url) }
  return (
    <div className="space-y-3">
      <p className="flex items-center gap-2 text-sm">
        {linked.length > 0
          ? <><CheckCircle weight="fill" className="size-4 text-success" aria-hidden /><span>Linked{linked.length > 1 ? ` in ${linked.length} workspaces` : ""}: <span className="font-mono text-xs">{linked.join(", ")}</span></span></>
          : <><Prohibit className="size-4 text-muted-foreground" aria-hidden /><span className="text-muted-foreground">Not linked</span></>}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant={linked.length > 0 ? "outline" : "default"} icon={<SlackLogo />} loading={leaving} onClick={go}>{linked.length > 0 ? "Link another workspace" : "Link Slack"}</Button>
        {linked.length > 0 && <Button variant="outline" loading={unlink.isPending} onClick={() => unlink.mutate(undefined, { onSuccess: () => toast.success("Slack unlinked."), onError: (e) => toast.error(integrationError(e)) })}>{linked.length > 1 ? "Unlink all" : "Unlink"}</Button>}
      </div>
      <p className="text-xs text-muted-foreground">In Slack: <code className="font-mono">/task create KEY title</code> adds a task, <code className="font-mono">/task done KEY-42</code> finishes one. Both run with your own permissions, and replies are private.</p>
    </div>
  )
}

/** The five events that are about you, with a switch per way of hearing about them. */
export function NotificationsSection() {
  const prefs = usePreferences()
  const link = useSlackLink()
  const save = useSavePreference()
  if (prefs.isPending) return <Skeleton className="h-40 w-full" aria-label="Loading notifications" />
  if (prefs.isError) return <Retry label={integrationError(prefs.error)} onRetry={() => prefs.refetch()} />
  const linked = (link.data?.linked_workspaces.length ?? 0) > 0
  const change = (event: string, field: "slack_dm" | "email", value: boolean) =>
    save.mutate({ event, field, value }, { onError: (e) => toast.error(integrationError(e)) })
  return (
    <div className="space-y-2">
      <table className="w-full text-sm">
        <caption className="sr-only">How you hear about events that involve you</caption>
        <thead><tr className="border-b text-left text-xs text-muted-foreground"><th scope="col" className="py-2 pr-3 font-medium">Event</th><th scope="col" className="px-3 font-medium">Email</th><th scope="col" className="pl-3 font-medium">Slack message</th></tr></thead>
        <tbody className="divide-y">
          {prefs.data.items.map((p) => {
            const info = eventInfo(p.event_type)
            const Icon = info.icon
            return (
              <tr key={p.event_type}>
                <th scope="row" className="py-2.5 pr-3 text-left font-normal"><span className="inline-flex items-center gap-2"><Icon className="size-4 text-muted-foreground" aria-hidden />{info.label}</span></th>
                <td className="px-3"><Switch checked={p.email} onCheckedChange={(v) => change(p.event_type, "email", !!v)} aria-label={`Email me: ${info.label}`} /></td>
                <td className="pl-3"><Switch checked={p.slack_dm && linked} disabled={!linked} onCheckedChange={(v) => change(p.event_type, "slack_dm", !!v)} aria-label={`Slack message: ${info.label}`} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-xs text-muted-foreground">{linked ? "Slack messages are on and email is off until you change them." : "Slack messages are off until you link your account above. Email is off until you turn it on."}</p>
    </div>
  )
}
