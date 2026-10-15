import { useState } from "react"
import { Button } from "@/components/ui/button"
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { CheckCircle, Clock, UserPlus, XCircle } from "@/icons"
import type { JoinSubmitted } from "./api"
import { projectError } from "./errors"
import { useProjectMutations } from "./queries"

/**
 * Join by code, as the body of a dialog or of the /join page. After a valid code the form is replaced by the
 * pending state, which names the project (the only thing a requester may see before approval).
 */
export function JoinForm({ initialCode = "", onDone, doneLabel = "Done", asPage = false }: { initialCode?: string; onDone: () => void; doneLabel?: string; asPage?: boolean }) {
  const [code, setCode] = useState(initialCode.toUpperCase().slice(0, 6))
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState<JoinSubmitted | null>(null)
  const { join } = useProjectMutations()

  const submit = () => {
    if (code.length < 6) return setError("Codes are 6 characters.")
    join.mutate(code, { onSuccess: setSent, onError: (e) => setError(projectError(e)) })
  }
  const Title = asPage ? "h1" : DialogTitle
  const Description = asPage ? "p" : DialogDescription

  if (sent) {
    return (
      <>
        <DialogHeader>
          <Title className="flex items-center gap-2 text-lg font-semibold"><Clock weight="fill" className="size-5 text-info" />Request sent to {sent.project.name}</Title>
          <Description className="text-sm text-muted-foreground">The owner has been notified and decides whether to let you in. You get an email when they do. Until then you cannot see anything in this project.</Description>
        </DialogHeader>
        <DialogFooter className="sm:justify-start">
          <Button variant="outline" icon={<CheckCircle />} onClick={onDone}>{doneLabel}</Button>
        </DialogFooter>
      </>
    )
  }
  return (
    <>
      <DialogHeader>
        <Title className="text-lg font-semibold">Join a project</Title>
        <Description className="text-sm text-muted-foreground">Enter the 6-character code from the project owner. They approve every request.</Description>
      </DialogHeader>
      <form id="join-form" className="space-y-2" onSubmit={(e) => { e.preventDefault(); submit() }}>
        <InputOTP maxLength={6} value={code} onChange={(v) => { setCode(v.toUpperCase()); setError(null) }} aria-label="Join code" aria-invalid={!!error} aria-describedby={error ? "join-error" : undefined} autoFocus>
          <InputOTPGroup>
            {[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} />)}
          </InputOTPGroup>
        </InputOTP>
        {error && (
          <p id="join-error" role="alert" className="flex items-center gap-1.5 text-sm text-destructive">
            <XCircle weight="fill" className="size-4 shrink-0" />{error}
          </p>
        )}
      </form>
      <DialogFooter className="sm:justify-start">
        <Button type="submit" form="join-form" icon={<UserPlus weight="bold" />} loading={join.isPending} disabled={code.length < 6}>Request access</Button>
      </DialogFooter>
    </>
  )
}
