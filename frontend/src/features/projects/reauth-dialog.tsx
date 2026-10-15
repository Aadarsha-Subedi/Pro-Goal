import { useState, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { GoogleButton } from "@/features/auth/fields"
import { XCircle } from "@/icons"
import type { Reauth } from "./api"
import { projectError } from "./errors"

interface ReauthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  confirmLabel: string
  icon: ReactNode
  variant?: "default" | "solid-destructive"
  /** Extra fields (typed name, recipient) rendered above the password. */
  children?: ReactNode
  /** False while the extra fields are incomplete. */
  ready?: boolean
  /** Runs the sensitive action. Throw to show the error inline; resolve to close. */
  onConfirm: (reauth: Reauth) => Promise<unknown>
  /** Turns a failure into the sentence shown in the dialog. Defaults to the project messages. */
  errorText?: (e: unknown) => string
}

/** Sensitive owner actions re-confirm identity: password, or a fresh Google sign-in for accounts without one. */
export function ReauthDialog(props: ReauthDialogProps) {
  // The popup unmounts after its exit animation, taking the body with it, so a typed password never outlives the dialog (cancel, Escape or success).
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent><ReauthBody {...props} /></DialogContent>
    </Dialog>
  )
}

function ReauthBody({ onOpenChange, title, description, confirmLabel, icon, variant = "default", children, ready = true, onConfirm, errorText = projectError }: ReauthDialogProps) {
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const run = async (reauth: Reauth) => {
    setPending(true)
    setError(null)
    try {
      await onConfirm(reauth)
      onOpenChange(false)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setPending(false)
    }
  }
  const reset = onOpenChange

  return (
    <>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <form id="reauth-form" className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (ready && password) void run({ password }) }}>
          {children}
          <Field>
            <FieldLabel htmlFor="reauth-password">Your password</FieldLabel>
            <Input id="reauth-password" type="password" autoComplete="current-password" value={password} onChange={(e) => { setPassword(e.target.value); setError(null) }} aria-invalid={!!error} aria-describedby={error ? "reauth-error" : undefined} />
          </Field>
          {error && (
            <p id="reauth-error" role="alert" className="flex items-center gap-1.5 text-sm text-destructive">
              <XCircle weight="fill" className="size-4 shrink-0" />{error}
            </p>
          )}
        </form>
        <div className="space-y-3">
          <p role="separator" className="flex items-center gap-2 text-xs text-muted-foreground before:h-px before:flex-1 before:bg-border after:h-px after:flex-1 after:bg-border">or</p>
          <div className={ready ? undefined : "pointer-events-none opacity-50"} aria-disabled={!ready} inert={!ready}>
            <GoogleButton onCredential={(idToken) => run({ id_token: idToken })}>Confirm with Google</GoogleButton>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => reset(false)}>Cancel</Button>
          <Button type="submit" form="reauth-form" variant={variant} icon={icon} loading={pending} disabled={!ready || !password}>{confirmLabel}</Button>
        </DialogFooter>
    </>
  )
}
