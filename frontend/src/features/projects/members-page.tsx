import { Link, useNavigate, useRouteContext } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { PermissionMatrix } from "@/features/permissions/permission-matrix"
import { ArrowClockwise, Crown, DotsThree, ShieldCheck, SignOut, UserMinus } from "@/icons"
import { formatTimestamp } from "@/lib/format"
import type { Member } from "./api"
import { can, useCurrentProject } from "./current"
import { projectError } from "./errors"
import { useMembers, useProjectMutations, useRegistry } from "./queries"

function displayName(m: Member): string {
  return m.display_name || m.first_name
}

export function MembersPage() {
  const { id, project } = useCurrentProject()
  useDocumentTitle(`Members · ${project.name} · Pro-Goal`)
  const { me } = useRouteContext({ from: "/app" })
  const navigate = useNavigate()
  const { data, isPending, isError, refetch } = useMembers(id)
  const { removeMember, leave } = useProjectMutations(id)
  const [target, setTarget] = useState<Member | null>(null)
  const [leaving, setLeaving] = useState(false)
  const canRemove = can(project, "member.remove") && !project.is_archived
  const owner = project.role === "owner"
  const manager = can(project, "permissions.manage")
  const registry = useRegistry()

  const confirmRemove = () => {
    if (!target) return
    removeMember.mutate(target.id, {
      onSuccess: () => { toast.success(`${displayName(target)} was removed.`); setTarget(null) },
      onError: (e) => { toast.error(projectError(e)); setTarget(null) },
    })
  }
  const confirmLeave = () =>
    leave.mutate(undefined, {
      onSuccess: () => { toast.success(`You left ${project.name}.`); navigate({ to: "/app", replace: true }) },
      onError: (e) => { toast.error(projectError(e)); setLeaving(false) },
    })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Members"
        description={project.is_demo ? "Demo projects keep other members private. You see the owner and yourself." : owner ? "You see everyone's name and email. Other members see first names." : "Everyone here can read the whole project."}
        actions={!owner && <Button variant="outline" icon={<SignOut />} onClick={() => setLeaving(true)}>Leave project</Button>}
      />
      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading members">
          {[0, 1, 2].map((i) => <li key={i} className="flex items-center gap-3 py-3"><Skeleton className="size-8 rounded-full" /><Skeleton className="h-4 w-40" /></li>)}
        </ul>
      ) : isError ? (
        <Empty><EmptyHeader><EmptyTitle>Couldn't load members</EmptyTitle><EmptyDescription>Check your connection and try again.</EmptyDescription></EmptyHeader><Button variant="outline" icon={<ArrowClockwise />} onClick={() => refetch()}>Try again</Button></Empty>
      ) : (
        <ul className="divide-y border-y">
          {data.items.map((m) => (
            <li key={m.id} className="flex min-h-14 items-center gap-3 py-2">
              <UserAvatar name={displayName(m)} src={m.avatar_url} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{displayName(m)}{m.id === me.id && <span className="font-normal text-muted-foreground"> (you)</span>}</p>
                <p className="truncate text-xs text-muted-foreground">{m.email ? `${m.email} · ` : ""}Joined {formatTimestamp(m.joined_at)}</p>
              </div>
              {m.is_owner ? (
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Crown weight="fill" className="size-3.5 text-warning" aria-hidden />Owner</span>
              ) : (
                <span className="text-xs text-muted-foreground">Member</span>
              )}
              {!m.is_owner && (manager || m.id === me.id) && (
                <Button variant="ghost" size="sm" icon={<ShieldCheck />} nativeButton={false} render={<Link to="/app/projects/$projectId/members/$userId/permissions" params={{ projectId: id, userId: m.id }} />}>
                  Permissions{m.id === me.id && <span className="sr-only"> (you)</span>}
                </Button>
              )}
              {canRemove && !m.is_owner && m.id !== me.id ? (
                <DropdownMenu>
                  <DropdownMenuTrigger render={<Button variant="ghost" size="icon" label={`Actions for ${displayName(m)}`}><DotsThree weight="bold" /></Button>} />
                  <DropdownMenuContent align="end" className="min-w-52">
                    <DropdownMenuItem variant="destructive" onClick={() => setTarget(m)}><UserMinus />Remove from project</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <span className="size-(--ctl-h) shrink-0" aria-hidden />
              )}
            </li>
          ))}
        </ul>
      )}
      {manager && data && registry.data && (
        <section aria-labelledby="matrix" className="space-y-3">
          <div>
            <h2 id="matrix" className="text-sm font-semibold">Who can change what</h2>
            <p className="text-sm text-muted-foreground">Every member can read everything. Open an area to see each permission, or a name to change it.</p>
          </div>
          <PermissionMatrix projectId={id} members={data.items} registry={registry.data} />
        </section>
      )}
      {data && data.meta.count > data.items.length && <p className="text-xs text-muted-foreground">Showing the first {data.items.length} of {data.meta.count} members.</p>}

      <AlertDialog open={!!target} onOpenChange={(o) => !o && setTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {target && displayName(target)}?</AlertDialogTitle>
            <AlertDialogDescription>
              They lose access now and their permissions are not kept. Their comments and history stay under their name. They can ask to join again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<UserMinus />} loading={removeMember.isPending} onClick={confirmRemove}>Remove member</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog open={leaving} onOpenChange={setLeaving}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Leave {project.name}?</AlertDialogTitle>
            <AlertDialogDescription>You lose access now. To come back you ask to join again and the owner approves.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Stay</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<SignOut />} loading={leave.isPending} onClick={confirmLeave}>Leave project</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
