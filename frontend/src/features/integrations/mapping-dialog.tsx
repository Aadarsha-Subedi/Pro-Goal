import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowClockwise, Check, Hash, Info, Lock } from "@/icons"
import type { Mapping } from "./api"
import { integrationError } from "./errors"
import { ALL_EVENTS, EVENT_GROUPS, eventInfo, toggleEvent } from "./events"
import { useChannels, useIntegrationMutations } from "./queries"

/** Create a mapping (pick a channel) or edit one (channel fixed). The body mounts with the popup, so nothing carries over between openings. */
/** What a person types in a Slack channel to let the bot post there. */
const INVITE_COMMAND = "/invite @Project Management"

export function MappingDialog({ projectId, mapping, open, onOpenChange }: { projectId: string; mapping?: Mapping | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <Body projectId={projectId} mapping={mapping ?? null} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
}

function Body({ projectId, mapping, onClose }: { projectId: string; mapping: Mapping | null; onClose: () => void }) {
  const editing = !!mapping
  const channels = useChannels(projectId, !editing)
  const { createMapping, updateMapping } = useIntegrationMutations(projectId)
  const [channelId, setChannelId] = useState<string | null>(null)
  const [events, setEvents] = useState<string[]>(mapping?.enabled_events ?? ALL_EVENTS)
  const [error, setError] = useState<string | null>(null)
  const pending = createMapping.isPending || updateMapping.isPending
  const ready = (editing || !!channelId) && events.length > 0

  const save = () => {
    setError(null)
    const done = { onSuccess: () => { toast.success(editing ? "Channel updated." : "Channel added."); onClose() }, onError: (e: unknown) => setError(integrationError(e)) }
    if (mapping) updateMapping.mutate({ id: mapping.id, events }, done)
    else if (channelId) createMapping.mutate({ channelId, events }, done)
  }

  const items = (channels.data?.items ?? []).map((c) => ({ value: c.id, label: `#${c.name}${c.is_member ? "" : ` (run ${INVITE_COMMAND} in it first)`}` }))

  return (
    <>
      <DialogHeader>
        <DialogTitle>{editing ? `Events for #${mapping.channel_name}` : "Add a Slack channel"}</DialogTitle>
        <DialogDescription>Messages carry the task key, title, status, names, due date and a link. Never descriptions or comments.</DialogDescription>
      </DialogHeader>

      {!editing && (
        <div className="space-y-1.5">
          <Label htmlFor="channel">Channel</Label>
          {channels.isPending ? <Skeleton className="h-8 w-full" aria-label="Loading channels" /> : channels.isError ? (
            <div className="flex items-center gap-3 text-sm"><span className="text-destructive">{integrationError(channels.error)}</span><Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => channels.refetch()}>Try again</Button></div>
          ) : items.length === 0 ? (
            <p className="flex items-start gap-1.5 text-sm text-muted-foreground"><Info className="mt-0.5 size-4 shrink-0" aria-hidden />The bot can't see any channels. Invite it in Slack with {INVITE_COMMAND}, then try again.</p>
          ) : (
            <Select value={channelId} onValueChange={(v) => setChannelId(v)} items={items}>
              <SelectTrigger id="channel" className="w-full"><SelectValue placeholder="Choose a channel" /></SelectTrigger>
              <SelectContent>
                {channels.data!.items.map((c) => (
                  <SelectItem key={c.id} value={c.id} disabled={!c.is_member}>
                    <span className="inline-flex items-center gap-1.5">{c.is_private ? <Lock className="size-3.5" aria-hidden /> : <Hash className="size-3.5" aria-hidden />}{c.name}{!c.is_member && <span className="text-muted-foreground"> · in this channel, run <code className="font-mono text-xs">{INVITE_COMMAND}</code></span>}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      )}

      <fieldset className="space-y-3">
        <div className="flex items-center justify-between"><legend className="text-sm font-medium">Post these events</legend><span className="flex gap-1"><Button type="button" variant="ghost" size="xs" onClick={() => setEvents(ALL_EVENTS)}>Select all</Button><Button type="button" variant="ghost" size="xs" onClick={() => setEvents([])}>Clear</Button></span></div>
        {EVENT_GROUPS.map((g) => (
          <div key={g.name}>
            <p className="mb-1 text-xs font-medium text-muted-foreground">{g.name}</p>
            <ul>
              {g.events.map((e) => {
                const Icon = eventInfo(e).icon
                return (
                  <li key={e} className="flex items-center gap-2.5 py-1.5">
                    <Checkbox id={`ev-${e}`} checked={events.includes(e)} onCheckedChange={(v) => setEvents(toggleEvent(events, e, !!v))} />
                    <Label htmlFor={`ev-${e}`} className="font-normal"><Icon className="size-4 text-muted-foreground" aria-hidden />{eventInfo(e).label}</Label>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
        {events.length === 0 && <p className="text-xs text-muted-foreground">Pick at least one event.</p>}
      </fieldset>

      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button icon={<Check weight="bold" />} loading={pending} disabled={!ready} onClick={save}>{editing ? "Save events" : "Add channel"}</Button>
      </DialogFooter>
    </>
  )
}
