import { useNavigate } from "@tanstack/react-router"
import { useState, type ReactNode } from "react"
import { toast } from "sonner"
import { DatePicker } from "@/components/patterns/date-picker"
import { PageHeader } from "@/components/patterns/page-header"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { StorageSettings } from "@/features/attachments/storage-settings"
import { WorkflowSettings, workflowAccess } from "@/features/tracker/workflow/workflow-settings"
import { Archive, ArrowsClockwise, Crown, Lock, Trash, X } from "@/icons"
import { daysUntil, plural } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { Project } from "./api"
import { can, useCurrentProject } from "./current"
import { useLockText } from "@/features/permissions/use-lock-text"
import { projectError, projectFieldError } from "./errors"
import { ReauthDialog } from "./reauth-dialog"
import { useMembers, useProjectMutations } from "./queries"

function Section({ title, description, children, danger }: { title: string; description?: ReactNode; children: ReactNode; danger?: boolean }) {
  return (
    <section className="grid gap-4 py-6 md:grid-cols-[14rem_1fr] md:gap-8" aria-labelledby={`s-${title.replace(/\s/g, "-")}`}>
      <div className="space-y-1">
        <h2 id={`s-${title.replace(/\s/g, "-")}`} className={cn("text-sm font-semibold", danger && "text-destructive")}>{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="min-w-0 space-y-4">{children}</div>
    </section>
  )
}

function LockedNote({ code }: { code: string }) {
  const lockText = useLockText()
  return <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Lock className="size-3.5" aria-hidden />{lockText(code)}</span>
}

function DetailsForm({ project }: { project: Project }) {
  const { update } = useProjectMutations(project.id)
  const [name, setName] = useState(project.name)
  const [key, setKey] = useState(project.task_key)
  const [description, setDescription] = useState(project.description)
  const [start, setStart] = useState(project.start_date)
  const [end, setEnd] = useState(project.end_date)
  const [tags, setTags] = useState(project.tags.join(", "))
  const [error, setError] = useState<unknown>(null)
  const frozen = project.is_archived

  const ok = {
    name: can(project, "project.name.change") && !frozen,
    key: can(project, "project.task_key.change") && !frozen,
    description: can(project, "project.description.change") && !frozen,
    start: can(project, "project.start_date.change") && !frozen,
    end: can(project, "project.end_date.change") && !frozen,
    tags: can(project, "project.tags.change") && !frozen,
  }
  const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean)
  const patch: Record<string, unknown> = {}
  if (ok.name && name.trim() !== project.name) patch.name = name.trim()
  if (ok.key && key.toUpperCase() !== project.task_key) patch.task_key = key.toUpperCase()
  if (ok.description && description !== project.description) patch.description = description
  if (ok.start && start !== project.start_date) patch.start_date = start
  if (ok.end && end !== project.end_date) patch.end_date = end
  if (ok.tags && tagList.join(",") !== project.tags.join(",")) patch.tags = tagList
  const dirty = Object.keys(patch).length > 0
  const anyEditable = Object.values(ok).some(Boolean)

  const save = () => {
    setError(null)
    update.mutate(patch, { onSuccess: () => toast.success("Project saved."), onError: setError })
  }
  const err = (f: string) => projectFieldError(error, f)
  const generic = error && !["name", "task_key", "description", "start_date", "end_date", "tags"].some(err) ? projectError(error) : null

  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (dirty) save() }}>
      <Field data-invalid={!!err("name") || undefined}>
        <FieldLabel htmlFor="s-name">Name</FieldLabel>
        <Input id="s-name" value={name} maxLength={120} disabled={!ok.name} aria-invalid={!!err("name")} onChange={(e) => setName(e.target.value)} />
        {err("name") ? <FieldError>{err("name")}</FieldError> : !ok.name && !frozen && <LockedNote code="project.name.change" />}
      </Field>
      <Field data-invalid={!!err("task_key") || undefined}>
        <FieldLabel htmlFor="s-key">Task key</FieldLabel>
        <Input id="s-key" value={key} maxLength={5} disabled={!ok.key} className="w-28! font-mono uppercase" aria-invalid={!!err("task_key")} onChange={(e) => setKey(e.target.value.replace(/[^a-zA-Z]/g, ""))} />
        {err("task_key") ? <FieldError>{err("task_key")}</FieldError> : !ok.key && !frozen ? <LockedNote code="project.task_key.change" /> : <FieldDescription>Shown in front of task numbers. Existing links keep working.</FieldDescription>}
      </Field>
      <Field>
        <FieldLabel htmlFor="s-description">Description</FieldLabel>
        <Textarea id="s-description" value={description} rows={4} maxLength={5000} disabled={!ok.description} onChange={(e) => setDescription(e.target.value)} />
        {!ok.description && !frozen && <LockedNote code="project.description.change" />}
      </Field>
      <div className="flex flex-wrap gap-4">
        <Field className="w-auto">
          <FieldLabel htmlFor="s-start">Start date</FieldLabel>
          <DatePicker id="s-start" placeholder="No start date" value={start} onChange={setStart} disabled={!ok.start} />
          {err("start_date") ? <FieldError>{err("start_date")}</FieldError> : !ok.start && !frozen && <LockedNote code="project.start_date.change" />}
        </Field>
        <Field className="w-auto">
          <FieldLabel htmlFor="s-end">End date</FieldLabel>
          <DatePicker id="s-end" placeholder="No end date" value={end} onChange={setEnd} disabled={!ok.end} />
          {err("end_date") ? <FieldError>{err("end_date")}</FieldError> : !ok.end && !frozen && <LockedNote code="project.end_date.change" />}
        </Field>
      </div>
      <Field data-invalid={!!err("tags") || undefined}>
        <FieldLabel htmlFor="s-tags">Tags</FieldLabel>
        <Input id="s-tags" value={tags} disabled={!ok.tags} aria-invalid={!!err("tags")} onChange={(e) => setTags(e.target.value)} />
        {err("tags") ? <FieldError>{err("tags")}</FieldError> : !ok.tags && !frozen ? <LockedNote code="project.tags.change" /> : <FieldDescription>Separate with commas. Up to 10, lowercase.</FieldDescription>}
      </Field>
      {generic && <p role="alert" className="text-sm text-destructive">{generic}</p>}
      {anyEditable && <Button type="submit" loading={update.isPending} disabled={!dirty}>Save changes</Button>}
      {frozen && <p className="text-sm text-muted-foreground">Archived projects are read-only.</p>}
    </form>
  )
}

function ListedSwitch({ project }: { project: Project }) {
  const { update } = useProjectMutations(project.id)
  return (
    <Field orientation="horizontal">
      <Switch id="s-listed" checked={project.is_listed} disabled={project.is_archived || update.isPending} onCheckedChange={(v) => update.mutate({ is_listed: v }, { onSuccess: () => toast.success(v ? "Project is listed on Explore." : "Project is no longer listed."), onError: (e) => toast.error(projectError(e)) })} />
      <div className="space-y-0.5">
        <FieldLabel htmlFor="s-listed">{project.is_listed ? "Listed on Explore" : "Not listed on Explore"}</FieldLabel>
        <FieldDescription>{project.is_listed ? "Anyone signed in can see the name, description, tags and dates and ask to join without a code." : "Only people with the join code can ask to join."} You approve every request either way.</FieldDescription>
      </div>
    </Field>
  )
}

function JoinCodeSection({ project }: { project: Project }) {
  const { regenerateCode } = useProjectMutations(project.id)
  const [open, setOpen] = useState(false)
  return (
    <Section title="Join code" description="People enter it to ask for access.">
      <div className="flex flex-wrap items-center gap-3">
        <code className="rounded-md bg-muted px-2 py-1 font-mono text-sm tracking-widest">{project.join_code}</code>
        <Button variant="outline" icon={<ArrowsClockwise />} disabled={project.is_archived} onClick={() => setOpen(true)}>Regenerate…</Button>
      </div>
      <p className="text-sm text-muted-foreground">A new code replaces this one. Requests already waiting stay valid.</p>
      <ReauthDialog open={open} onOpenChange={setOpen} title="Regenerate join code?" description="The old code stops working right away. Share the new one with the people you want to invite." confirmLabel="Regenerate code" icon={<ArrowsClockwise />} onConfirm={(r) => regenerateCode.mutateAsync(r).then(() => toast.success("New join code created."))} />
    </Section>
  )
}

function TransferSection({ project }: { project: Project }) {
  const { startTransfer, cancelTransfer } = useProjectMutations(project.id)
  const { data } = useMembers(project.id)
  const [open, setOpen] = useState(false)
  const [to, setTo] = useState<string | null>(null)
  const candidates = (data?.items ?? []).filter((m) => !m.is_owner)
  const items = candidates.map((m) => ({ value: m.id, label: m.display_name || m.first_name }))
  const pending = project.pending_transfer
  return (
    <Section title="Ownership" description="One owner per project. A transfer needs the new owner to accept.">
      {pending ? (
        <div className="flex flex-wrap items-center gap-3">
          <p className="flex-1 text-sm"><Crown weight="fill" className="mr-1.5 inline size-4 text-warning" aria-hidden />Offer sent to <span className="font-medium">{pending.to_user.first_name}</span>. It expires in {plural(daysUntil(pending.expires_at), "day")}.</p>
          <Button variant="outline" icon={<X />} loading={cancelTransfer.isPending} onClick={() => cancelTransfer.mutate(undefined, { onSuccess: () => toast.success("Transfer cancelled."), onError: (e) => toast.error(projectError(e)) })}>Cancel offer</Button>
        </div>
      ) : (
        <>
          <Button variant="outline" icon={<Crown />} disabled={project.is_archived || candidates.length === 0} onClick={() => setOpen(true)}>Transfer ownership…</Button>
          {candidates.length === 0 && <p className="text-sm text-muted-foreground">Add another member first. Ownership can only go to an existing member.</p>}
        </>
      )}
      <ReauthDialog
        open={open}
        onOpenChange={(o) => { setOpen(o); if (!o) setTo(null) }}
        title="Transfer ownership"
        description="After they accept, you stay as a member with no permissions until the new owner grants some."
        confirmLabel="Send offer"
        icon={<Crown />}
        ready={!!to}
        onConfirm={(reauth) => startTransfer.mutateAsync({ toUser: to!, reauth }).then(() => toast.success("Offer sent. They have 7 days to accept."))}
      >
        <Field>
          <FieldLabel htmlFor="transfer-to">New owner</FieldLabel>
          <Select value={to} onValueChange={setTo} items={items}>
            <SelectTrigger id="transfer-to" className="w-full"><SelectValue placeholder="Choose a member" /></SelectTrigger>
            <SelectContent>{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </ReauthDialog>
    </Section>
  )
}

function ArchiveSection({ project }: { project: Project }) {
  const { archive, unarchive } = useProjectMutations(project.id)
  const done = (m: string) => ({ onSuccess: () => toast.success(m), onError: (e: unknown) => toast.error(projectError(e)) })
  return (
    <Section title="Archive" description="Read-only for everyone, and you can undo it.">
      {project.is_archived ? (
        <Button variant="outline" icon={<Archive />} loading={unarchive.isPending} onClick={() => unarchive.mutate(undefined, done("Project unarchived."))}>Unarchive project</Button>
      ) : (
        <Button variant="outline" icon={<Archive />} loading={archive.isPending} onClick={() => archive.mutate(undefined, done("Project archived."))}>Archive project</Button>
      )}
    </Section>
  )
}

function DeleteSection({ project }: { project: Project }) {
  const { remove } = useProjectMutations(project.id)
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState("")
  return (
    <Section danger title="Delete project" description="Hidden from everyone now, deleted for good after 7 days.">
      <Button variant="destructive" icon={<Trash />} onClick={() => setOpen(true)}>Delete project…</Button>
      <ReauthDialog
        open={open}
        onOpenChange={(o) => { setOpen(o); if (!o) setTyped("") }}
        title={`Delete ${project.name}?`}
        description={`Everyone loses access now. You can restore the project during the next 7 days. After that its tasks, notes and files are deleted permanently.`}
        confirmLabel="Delete project"
        variant="solid-destructive"
        icon={<Trash />}
        ready={typed === project.name}
        onConfirm={(r) => remove.mutateAsync(r).then(() => { toast.success("Project scheduled for deletion."); navigate({ to: "/app", replace: true }) })}
      >
        <Field>
          <FieldLabel htmlFor="delete-name">Type <span className="font-mono">{project.name}</span> to confirm</FieldLabel>
          <Input id="delete-name" value={typed} autoComplete="off" onChange={(e) => setTyped(e.target.value)} />
        </Field>
      </ReauthDialog>
    </Section>
  )
}

export function SettingsPage() {
  const { project } = useCurrentProject()
  useDocumentTitle(`Settings · ${project.name} · Pro-Goal`)
  const owner = project.role === "owner"
  return (
    <div className="space-y-2">
      <PageHeader title="Settings" description={owner ? "Details, access and the actions only you can take." : "You can change the details you have permission for."} />
      <div className="divide-y border-b">
        <Section title="Details">
          <DetailsForm key={project.id} project={project} />
        </Section>
        {owner && (
          <Section title="Visibility" description="Who can find this project without the join code.">
            <ListedSwitch project={project} />
          </Section>
        )}
        {owner && project.join_code && <JoinCodeSection project={project} />}
        <Section title="Storage" description="Files on tasks, comments and notes. Each person has 100 MB across all projects.">
          <StorageSettings projectId={project.id} />
        </Section>
        <Section title="Workflow" description="The statuses and priorities every task in this project uses.">
          <WorkflowSettings projectId={project.id} frozen={project.is_archived} access={workflowAccess((c) => can(project, c), project.is_archived)} />
        </Section>
        {owner && <TransferSection project={project} />}
        {owner && <ArchiveSection project={project} />}
        {owner && <DeleteSection project={project} />}
      </div>
    </div>
  )
}
