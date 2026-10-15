import { useState } from "react"
import { toast } from "sonner"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowClockwise, Globe, Hash, Lock, PencilSimple, Plus, Trash, WarningCircle } from "@/icons"
import { useLockText } from "@/features/permissions/use-lock-text"
import type { Mapping } from "./api"
import { integrationError } from "./errors"
import { summarizeEvents } from "./events"
import { MappingDialog } from "./mapping-dialog"
import { useIntegrationMutations, useMappings } from "./queries"

/** Which Slack channels get which project events. Public channels say who can read the posts. */
export function SlackMappings({ projectId, canManage, frozen }: { projectId: string; canManage: boolean; frozen: boolean }) {
  const { data, isPending, isError, error, refetch } = useMappings(projectId, true)
  const { deleteMapping } = useIntegrationMutations(projectId)
  const lockText = useLockText()
  const [editing, setEditing] = useState<Mapping | null>(null)
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState<Mapping | null>(null)
  const [last, setLast] = useState<Mapping | null>(null)
  const [lastEdit, setLastEdit] = useState<Mapping | null>(null)
  if (removing && removing !== last) setLast(removing)
  if (editing && editing !== lastEdit) setLastEdit(editing)
  const allowed = canManage && !frozen

  const confirmRemove = () => {
    if (!removing) return
    deleteMapping.mutate(removing.id, {
      onSuccess: () => { toast.success(`#${removing.channel_name} won't get posts any more.`); setRemoving(null) },
      onError: (e) => { toast.error(integrationError(e)); setRemoving(null) },
    })
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Channels</h3>
        <Button variant="outline" size="sm" icon={<Plus weight="bold" />} disabled={!allowed} onClick={() => setAdding(true)}>Add channel</Button>
      </div>
      {!allowed && <p className="text-xs text-muted-foreground">{frozen ? "This project is archived." : lockText("integration.slack.manage")}</p>}
      {isPending ? <Skeleton className="h-14 w-full" aria-label="Loading channels" /> : isError ? (
        <div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground">{integrationError(error)}</span><Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></div>
      ) : data.items.length === 0 ? (
        <Empty><EmptyHeader><EmptyTitle>No channels yet</EmptyTitle><EmptyDescription>Add a channel to post task and comment updates there. Invite the bot to the channel in Slack first.</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <ul className="divide-y border-y" aria-label="Mapped channels">
          {data.items.map((m) => (
            <li key={m.id} className="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-1 py-2">
              {m.is_public ? <Hash className="size-4 shrink-0 text-muted-foreground" aria-hidden /> : <Lock className="size-4 shrink-0 text-muted-foreground" aria-hidden />}
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-x-2 text-sm font-medium"><span>{m.channel_name}</span><span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground">{m.is_public ? <><Globe className="size-3.5" aria-hidden />Public channel</> : <><Lock className="size-3.5" aria-hidden />Private channel</>}</span></p>
                <p className="text-xs text-muted-foreground">{summarizeEvents(m.enabled_events)}</p>
                {m.warn_public && <p className="mt-0.5 flex items-start gap-1 text-xs text-warning-text"><WarningCircle weight="fill" className="mt-px size-3.5 shrink-0 text-warning" aria-hidden />Anyone in the workspace can read these posts.</p>}
              </div>
              <Button variant="ghost" size="sm" icon={<PencilSimple />} disabled={!allowed} onClick={() => setEditing(m)}>Events</Button>
              <Button variant="ghost" size="icon" label={`Remove #${m.channel_name}`} disabled={!allowed} onClick={() => setRemoving(m)}><Trash /></Button>
            </li>
          ))}
        </ul>
      )}

      <MappingDialog projectId={projectId} open={adding} onOpenChange={setAdding} />
      <MappingDialog projectId={projectId} mapping={editing ?? lastEdit} open={!!editing} onOpenChange={(o) => !o && setEditing(null)} />
      <AlertDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Stop posting to #{last?.channel_name}?</AlertDialogTitle>
            <AlertDialogDescription>Nothing more is sent there. Messages already posted stay in Slack. You can add the channel again.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} loading={deleteMapping.isPending} onClick={confirmRemove}>Remove channel</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
