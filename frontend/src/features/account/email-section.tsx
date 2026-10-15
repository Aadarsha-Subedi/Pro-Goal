import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { isEmail } from "@/features/auth/fields"
import { ReauthDialog } from "@/features/projects/reauth-dialog"
import { Envelope } from "@/icons"
import { accountApi } from "./api"
import { accountError } from "./errors"

/** Changing the login address re-confirms identity, then sends a link to the NEW address. Nothing changes until it is opened. */
export function EmailSection({ email }: { email: string }) {
  const [open, setOpen] = useState(false)
  const [next, setNext] = useState("")
  const clean = next.trim()
  return (
    <div className="space-y-3">
      <p className="text-sm">Your sign-in address is <span className="font-medium">{email}</span>.</p>
      <Button variant="outline" icon={<Envelope />} onClick={() => setOpen(true)}>Change email</Button>
      <ReauthDialog
        open={open}
        onOpenChange={(o) => { setOpen(o); if (!o) setNext("") }}
        title="Change your email"
        description="We send a link to the new address. The change happens when you open it, and you are signed out everywhere."
        confirmLabel="Send link"
        icon={<Envelope />}
        errorText={accountError}
        ready={isEmail(clean) && clean.toLowerCase() !== email.toLowerCase()}
        onConfirm={async (reauth) => {
          await accountApi.requestEmailChange(clean, reauth)
          toast.success("If that address is free, a link is on its way. It works for 24 hours.")
        }}
      >
        <Field>
          <FieldLabel htmlFor="new-email">New email address</FieldLabel>
          <Input id="new-email" type="email" autoComplete="email" value={next} onChange={(e) => setNext(e.target.value)} />
          <FieldDescription>We alert your current address too, so nobody can change it unnoticed.</FieldDescription>
        </Field>
      </ReauthDialog>
    </div>
  )
}
