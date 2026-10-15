import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, Check, Key, X } from "@/icons"
import { daysUntil, formatTimestamp, plural } from "@/lib/format"
import type { JoinRequest } from "./api"
import { can, useCurrentProject } from "./current"
import { projectError } from "./errors"
import { useProjectMutations, useRegistry, useRequests } from "./queries"

const NONE = "none"

function name(r: JoinRequest): string {
  return r.user.display_name || r.user.first_name
}

function ApproveDialog({ request, onClose }: { request: JoinRequest | null; onClose: () => void }) {
  // The last request stays visible while the dialog fades out. The form below unmounts with the popup,
  // so the starting permissions never carry over to the next approval.
  const [last, setLast] = useState(request)
  if (request && request !== last) setLast(request)
  return (
    <Dialog open={!!request} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent>{last && <ApproveForm request={last} onClose={onClose} />}</DialogContent>
    </Dialog>
  )
}

function ApproveForm({ request, onClose }: { request: JoinRequest; onClose: () => void }) {
  const { id } = useCurrentProject()
  const { approve } = useProjectMutations(id)
  const { data: registry } = useRegistry()
  const [preset, setPreset] = useState(NONE)
  const presets = registry?.presets ?? []
  const items = [{ value: NONE, label: "No permissions" }, ...presets.map((p) => ({ value: p.name, label: p.label }))]
  const description = preset === NONE ? "They can read everything and change nothing. You can grant more later." : presets.find((p) => p.name === preset)?.description

  const submit = () =>
    approve.mutate(
      { requestId: request.id, preset: preset === NONE ? undefined : preset },
      {
        onSuccess: () => { toast.success(`${name(request)} joined the project.`); onClose() },
        onError: (e) => { toast.error(projectError(e)); onClose() },
      },
    )
  return (
    <>
      <DialogHeader>
        <DialogTitle>Approve {name(request)}?</DialogTitle>
        <DialogDescription>{request.user.email} becomes a member and can read the whole project. Choose what they may change.</DialogDescription>
      </DialogHeader>
      <Field>
        <FieldLabel htmlFor="preset">Starting permissions</FieldLabel>
        <Select value={preset} onValueChange={(v) => v && setPreset(v)} items={items}>
          <SelectTrigger id="preset" className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}</SelectContent>
        </Select>
        <FieldDescription>{description}</FieldDescription>
      </Field>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button icon={<Check weight="bold" />} loading={approve.isPending} onClick={submit}>Approve</Button>
      </DialogFooter>
    </>
  )
}

export function RequestsPage() {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Join requests · ${project.name} · Pro-Goal`)
  const allowed = can(project, "member.approve")
  const { data, isPending, isError, refetch } = useRequests(id, "pending", allowed)
  const { reject } = useProjectMutations(id)
  const [target, setTarget] = useState<JoinRequest | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  if (!allowed)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Only people who approve members see this</EmptyTitle>
          <EmptyDescription>The owner can give you the permission to approve join requests.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )

  const decline = (r: JoinRequest) => {
    setBusy(r.id)
    reject.mutate(r.id, {
      onSuccess: () => toast.success(`Declined ${name(r)}. They can ask again after 24 hours.`),
      onError: (e) => toast.error(projectError(e)),
      onSettled: () => setBusy(null),
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Join requests" description={`People who entered the join code. Requests expire after 14 days.${project.is_archived ? " Approving is paused while the project is archived." : ""}`} />
      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading requests">
          {[0, 1].map((i) => <li key={i} className="flex items-center gap-3 py-3"><Skeleton className="size-8 rounded-full" /><Skeleton className="h-4 w-48" /></li>)}
        </ul>
      ) : isError ? (
        <Empty><EmptyHeader><EmptyTitle>Couldn't load requests</EmptyTitle><EmptyDescription>Check your connection and try again.</EmptyDescription></EmptyHeader><Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></Empty>
      ) : data.items.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>No one is waiting</EmptyTitle>
            <EmptyDescription>{project.role === "owner" ? "Share the join code. Requests show up here and you get an email." : "New requests show up here."}</EmptyDescription>
          </EmptyHeader>
          {project.role === "owner" && <Button variant="outline" icon={<Key />} nativeButton={false} render={<Link to="/app/projects/$projectId" params={{ projectId: id }} />}>Get the join code</Button>}
        </Empty>
      ) : (
        <ul className="divide-y border-y">
          {data.items.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
              <UserAvatar name={name(r)} src={r.user.avatar_url} />
              <div className="min-w-0 flex-1 basis-48">
                <p className="truncate text-sm font-medium">{name(r)}</p>
                <p className="truncate text-xs text-muted-foreground">{r.user.email} · asked {formatTimestamp(r.created_at)} · expires in {plural(daysUntil(r.expires_at), "day")}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" icon={<X />} loading={busy === r.id} disabled={project.is_archived} onClick={() => decline(r)}>Decline</Button>
                <Button size="sm" icon={<Check weight="bold" />} disabled={project.is_archived} onClick={() => setTarget(r)}>Approve…</Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {data && data.meta.count > data.items.length && <p className="text-xs text-muted-foreground">Showing the first {data.items.length} of {data.meta.count} requests.</p>}
      <ApproveDialog request={target} onClose={() => setTarget(null)} />
    </div>
  )
}
