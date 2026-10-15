import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { CheckCircle, Clock, UserPlus, XCircle } from "@/icons"

type Stage = "enter" | "pending"

/** Join flow: 6-character code, inline error, pending state replaces the form. */
export function JoinProjectDialog() {
  const [open, setOpen] = useState(false)
  const [code, setCode] = useState("")
  const [stage, setStage] = useState<Stage>("enter")
  const [error, setError] = useState<string | null>(null)

  const reset = (o: boolean) => {
    setOpen(o)
    if (!o) setTimeout(() => { setStage("enter"); setCode(""); setError(null) }, 200)
  }
  const submit = () => {
    const c = code.toUpperCase()
    if (c.length < 6) return setError("Codes are 6 characters.")
    if (c === "AAAAAA") return setError("No project uses this code. Check it with the owner.")
    if (c === "EXPIRE") return setError("This code has expired. Ask the owner for a new one.")
    if (c === "MEMBER") return setError("You are already a member of this project.")
    setStage("pending")
  }

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogTrigger render={<Button variant="outline" icon={<UserPlus />}>Join project</Button>} />
      <DialogContent>
        {stage === "enter" ? (
          <>
            <DialogHeader>
              <DialogTitle>Join a project</DialogTitle>
              <DialogDescription>Enter the 6-character code from the project owner.</DialogDescription>
            </DialogHeader>
            <form id="join-form" className="space-y-2" onSubmit={(e) => { e.preventDefault(); submit() }}>
              <InputOTP maxLength={6} value={code} onChange={(v) => { setCode(v.toUpperCase()); setError(null) }} aria-label="Join code" aria-invalid={!!error}>
                <InputOTPGroup>
                  {[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} />)}
                </InputOTPGroup>
              </InputOTP>
              {error && (
                <p role="alert" className="flex items-center gap-1.5 text-sm text-destructive">
                  <XCircle weight="fill" className="size-4" />
                  {error}
                </p>
              )}
            </form>
            <DialogFooter>
              <Button type="submit" form="join-form" icon={<UserPlus weight="bold" />} disabled={!code}>Request access</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2"><Clock weight="fill" className="size-5 text-info" />Request sent</DialogTitle>
              <DialogDescription>The owner of this project has been notified. You get an email when they decide. You can close this window.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" icon={<CheckCircle />} onClick={() => reset(false)}>Done</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
