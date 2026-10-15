import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Crown } from "@/icons"
import { daysUntil, plural } from "@/lib/format"
import type { Transfer } from "./api"
import { projectError } from "./errors"
import { useProjectMutations, useTransfers } from "./queries"

function TransferRow({ transfer }: { transfer: Transfer }) {
  const [open, setOpen] = useState(false)
  const { acceptTransfer } = useProjectMutations()
  const navigate = useNavigate()
  const name = transfer.project.name ?? "this project"
  const days = daysUntil(transfer.expires_at)
  const accept = () =>
    acceptTransfer.mutate(transfer.id, {
      onSuccess: () => {
        setOpen(false)
        toast.success(`You now own ${name}.`)
        navigate({ to: "/app/projects/$projectId", params: { projectId: transfer.project.id } })
      },
      onError: (e) => {
        setOpen(false)
        toast.error(projectError(e))
      },
    })
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
      <Crown weight="fill" className="size-5 shrink-0 text-warning" aria-hidden />
      <p className="min-w-0 flex-1 text-sm">
        <span className="font-medium">{transfer.from_user.first_name}</span> offers you ownership of <span className="font-medium">{name}</span>.{" "}
        <span className="text-muted-foreground">Ignore it to decline. It expires in {plural(days, "day")}.</span>
      </p>
      <Button size="sm" icon={<Crown />} onClick={() => setOpen(true)}>Review offer</Button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Take ownership of {name}?</AlertDialogTitle>
            <AlertDialogDescription>
              You become the owner and hold every permission. {transfer.from_user.first_name} stays as a member with no permissions until you grant some.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Not now</AlertDialogCancel>
            <Button icon={<Crown />} loading={acceptTransfer.isPending} onClick={accept}>Accept ownership</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </li>
  )
}

/** Incoming ownership offers, pinned above the project list. Renders nothing when there are none. */
export function TransferBanner() {
  const { data } = useTransfers()
  if (!data || data.items.length === 0) return null
  return (
    <section aria-label="Ownership offers" className="border-b">
      <ul className="divide-y">
        {data.items.map((t) => <TransferRow key={t.id} transfer={t} />)}
      </ul>
    </section>
  )
}
