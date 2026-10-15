import { Link, useBlocker, useParams } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { StatusBanner } from "@/components/patterns/status-banner"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError } from "@/lib/api"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, Check, Lock, Minus, Plus } from "@/icons"
import { can, useCurrentProject } from "@/features/projects/current"
import { projectError } from "@/features/projects/errors"
import { useRegistry } from "@/features/projects/queries"
import { applyPreset, diffGrants, groupCounts, holds, presetFor, toggle } from "./logic"
import { useGrants, useReplaceGrants } from "./queries"
import { useLockText } from "./use-lock-text"

const CUSTOM = "custom"

/** Keyed by member so a draft never carries over to another member. */
export function PermissionsPage() {
  const { userId } = useParams({ strict: false }) as { userId: string }
  return <Editor key={userId} userId={userId} />
}

function Editor({ userId }: { userId: string }) {
  const { id, project } = useCurrentProject()
  const registry = useRegistry()
  const grants = useGrants(id, userId)
  const replace = useReplaceGrants(id, userId)
  const lockText = useLockText()
  const [draft, setDraft] = useState<string[] | null>(null)
  const leave = useBlocker({ shouldBlockFn: () => draft !== null && !replace.isPending, withResolver: true, enableBeforeUnload: () => draft !== null })
  useDocumentTitle(`Permissions · ${project.name} · Pro-Goal`)

  const back = (
    <Button variant="ghost" icon={<ArrowLeft />} nativeButton={false} render={<Link to="/app/projects/$projectId/members" params={{ projectId: id }} />}>Members</Button>
  )

  if (grants.isPending || registry.isPending) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading permissions">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }
  if (grants.isError || registry.isError || !grants.data || !registry.data) {
    const err = grants.error ?? registry.error
    return (
      <div className="space-y-4">
        {back}
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Couldn't load permissions</EmptyTitle>
            <EmptyDescription>{err ? projectError(err) : "Check your connection and try again."}</EmptyDescription>
          </EmptyHeader>
          {!(err instanceof ApiError && err.status === 403) && <Button variant="outline" icon={<ArrowClockwise />} onClick={() => { grants.refetch(); registry.refetch() }}>Try again</Button>}
        </Empty>
      </div>
    )
  }

  const reg = registry.data
  const member = grants.data
  const name = member.user.first_name
  const current = member.permissions
  const wanted = draft ?? current
  const manager = can(project, "permissions.manage")
  const frozen = project.is_archived
  const editable = manager && !frozen && !member.is_owner
  const canChange = (code: string) => editable && holds(project, reg, code)
  const { added, removed } = diffGrants(current, wanted)
  const dirty = added.length + removed.length > 0
  const matched = presetFor(wanted, reg.presets)
  const labelOf = (code: string) => reg.permissions.find((p) => p.code === code)?.label ?? code
  const counts = groupCounts(wanted, reg)

  const save = () =>
    replace.mutate(wanted, {
      onSuccess: () => { toast.success(`${name}'s permissions saved.`); setDraft(null) },
      onError: (e) => toast.error(projectError(e)),
    })

  let banner: React.ReactNode = null
  if (member.is_owner) banner = <StatusBanner title={`${name} owns this project.`}>The owner holds every permission. To hand the project over, transfer ownership in Settings.</StatusBanner>
  else if (frozen) banner = <StatusBanner tone="warning" title="This project is archived.">Permissions can't change until it is restored.</StatusBanner>
  else if (!manager) banner = <StatusBanner title="You can read these, not change them.">{lockText("permissions.manage")}</StatusBanner>

  return (
    <div className="space-y-6">
      <div>{back}</div>
      <PageHeader
        title={<span className="inline-flex items-center gap-3"><UserAvatar name={name} src={member.user.avatar_url} />Permissions for {name}</span>}
        description="Reading is open to every member. These decide what they can change."
      />
      {banner}

      {!member.is_owner && <div className="flex flex-wrap items-center gap-3">
        <Label htmlFor="preset" className="text-muted-foreground">Preset</Label>
        <Select
          value={matched?.name ?? CUSTOM}
          onValueChange={(v) => {
            const preset = reg.presets.find((p) => p.name === v)
            if (preset) setDraft(applyPreset(wanted, preset, canChange, reg))
          }}
          items={[...reg.presets.map((p) => ({ value: p.name, label: p.label })), { value: CUSTOM, label: "Custom" }]}
          disabled={!editable}
        >
          <SelectTrigger id="preset" className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            {reg.presets.map((p) => <SelectItem key={p.name} value={p.name}>{p.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground">{matched ? matched.description : "A mix of grants that matches no preset."}</p>
      </div>}

      <div className="space-y-8">
        {reg.groups.map((group) => {
          const c = counts.find((x) => x.group === group)!
          const items = reg.permissions.filter((p) => p.group === group)
          return (
            <section key={group} aria-labelledby={`g-${group}`}>
              <div className="flex items-baseline justify-between gap-3 border-b pb-2">
                <h2 id={`g-${group}`} className="text-sm font-semibold">{group}</h2>
                <p className="text-xs text-muted-foreground tabular-nums">{c.held} of {c.total}</p>
              </div>
              <ul className="divide-y">
                {items.map((p) => {
                  const on = wanted.includes(p.code)
                  const change = on !== current.includes(p.code)
                  const locked = !canChange(p.code)
                  const why = locked && editable ? "You don't hold this one." : null
                  return (
                    <li key={p.code} className="flex items-start gap-3 py-2.5">
                      <Checkbox
                        id={`p-${p.code}`}
                        checked={on}
                        disabled={locked}
                        onCheckedChange={(v) => setDraft(toggle(wanted, p.code, !!v))}
                        aria-describedby={`d-${p.code}`}
                        className="mt-0.5"
                      />
                      <div className="min-w-0 flex-1">
                        <Label htmlFor={`p-${p.code}`} className="leading-snug">{p.label}</Label>
                        <p id={`d-${p.code}`} className="text-xs text-muted-foreground">
                          {p.description}
                          {why && <span className="ml-1 inline-flex items-center gap-1"><Lock className="size-3" aria-hidden />{why}</span>}
                        </p>
                      </div>
                      {change && (
                        <span className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                          {on ? <Plus className="size-3" aria-hidden /> : <Minus className="size-3" aria-hidden />}
                          {on ? "Will add" : "Will remove"}
                        </span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </section>
          )
        })}
      </div>

      <AlertDialog open={leave.status === "blocked"} onOpenChange={(o) => !o && leave.reset?.()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Leave without saving?</AlertDialogTitle>
            <AlertDialogDescription>Your changes to {name}'s permissions will be lost.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep editing</AlertDialogCancel>
            <Button variant="solid-destructive" onClick={() => leave.proceed?.()}>Discard changes</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {editable && (
        <div className="sticky bottom-0 -mx-1 flex flex-wrap items-center gap-3 border-t bg-background px-1 py-3" role="region" aria-label="Save changes">
          <p className="min-w-0 flex-1 text-sm" aria-live="polite">
            {dirty ? (
              <>
                <span className="font-medium">{added.length > 0 && `Adds ${added.length}`}{added.length > 0 && removed.length > 0 && ", "}{removed.length > 0 && `${added.length > 0 ? "removes" : "Removes"} ${removed.length}`}.</span>
                <span className="text-muted-foreground"> {[...added.map((c) => `+ ${labelOf(c)}`), ...removed.map((c) => `− ${labelOf(c)}`)].join(", ")}</span>
              </>
            ) : <span className="text-muted-foreground">No changes.</span>}
          </p>
          <Button variant="ghost" disabled={!dirty || replace.isPending} onClick={() => setDraft(null)}>Discard</Button>
          <Button icon={<Check weight="bold" />} loading={replace.isPending} disabled={!dirty} onClick={save}>Save permissions</Button>
        </div>
      )}
    </div>
  )
}
