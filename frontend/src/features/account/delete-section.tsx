import { useRouter } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { StatusBanner } from "@/components/patterns/status-banner"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import type { Me } from "@/features/auth/api"
import { ArrowCounterClockwise, Trash } from "@/icons"
import { daysUntil, formatDateTime, plural } from "@/lib/format"
import { accountApi } from "./api"
import { accountError } from "./errors"

/** Account deletion starts a 7-day grace period. Signing in, or this button, cancels it. */
export function DeleteSection({ me }: { me: Me }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scheduled = me.deletion_scheduled_for

  const run = async (fn: () => Promise<unknown>, done: string) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
      await router.invalidate()
      toast.success(done)
      setOpen(false)
      setTyped("")
    } catch (e) {
      setError(accountError(e))
    } finally {
      setBusy(false)
    }
  }

  if (scheduled)
    return (
      <StatusBanner tone="danger" title="Your account is scheduled for deletion." action={<Button size="sm" icon={<ArrowCounterClockwise />} loading={busy} onClick={() => run(() => accountApi.cancelDeletion(), "Deletion cancelled. Your account stays.")}>Keep my account</Button>}>
        It is removed for good in {plural(daysUntil(scheduled), "day")}, on {formatDateTime(scheduled)}. Until then nothing is lost.
      </StatusBanner>
    )

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Your account is removed after 7 days. Signing in again during that time cancels it. Your tasks and comments stay in the projects, shown as "Deleted user". You can't delete while you own a project: transfer or delete it first.</p>
      <Button variant="destructive" icon={<Trash />} onClick={() => { setError(null); setOpen(true) }}>Delete my account…</Button>
      <AlertDialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setTyped("") }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete your account?</AlertDialogTitle>
            <AlertDialogDescription>The account is deleted in 7 days unless you cancel. Signing in again also cancels it. To confirm, type your email address.</AlertDialogDescription>
          </AlertDialogHeader>
          <Field>
            <FieldLabel htmlFor="del-email">{me.email}</FieldLabel>
            <Input id="del-email" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" aria-invalid={!!error} />
          </Field>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <AlertDialogFooter>
            <AlertDialogCancel>Keep my account</AlertDialogCancel>
            <Button variant="solid-destructive" icon={<Trash />} loading={busy} disabled={typed.trim().toLowerCase() !== me.email.toLowerCase()} onClick={() => run(() => accountApi.deleteAccount(), "Deletion scheduled.")}>Delete account</Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
