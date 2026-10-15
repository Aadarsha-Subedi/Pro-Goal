import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { PasswordField, passwordProblem } from "@/features/auth/fields"
import { Key } from "@/icons"
import { ApiError } from "@/lib/api"
import { accountApi } from "./api"
import { accountError } from "./errors"

/** Change the password while signed in. Every other device is signed out, so a stolen session ends here. */
export function PasswordSection() {
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [busy, setBusy] = useState(false)
  const [touched, setTouched] = useState(false)
  const [currentError, setCurrentError] = useState<string | undefined>()
  const problem = passwordProblem(next)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    setCurrentError(undefined)
    if (problem) return
    setBusy(true)
    try {
      await accountApi.changePassword(current, next)
      setCurrent("")
      setNext("")
      setTouched(false)
      toast.success("Password changed. Other devices were signed out.")
    } catch (err) {
      if (err instanceof ApiError && err.code === "invalid_current_password") setCurrentError(accountError(err))
      else toast.error((err instanceof ApiError && err.fieldError("new_password")) || accountError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="grid max-w-md gap-3">
      <PasswordField label="Current password" value={current} onChange={setCurrent} autoComplete="current-password" error={currentError} />
      <p className="-mt-1 text-xs text-muted-foreground">Signed up with Google and never set a password? Leave this empty.</p>
      <PasswordField label="New password" value={next} onChange={setNext} showRules error={touched ? problem : undefined} />
      <div><Button type="submit" icon={<Key />} loading={busy} disabled={!next}>Change password</Button></div>
    </form>
  )
}
