import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { PaperPlaneTilt } from "@/icons"
import { authApi, toAuthError } from "./api"
import { AuthSheet } from "./auth-sheet"
import { TextField, focusFirstError, isEmail } from "./fields"
import { Notice } from "./notice"

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [busy, setBusy] = useState(false)
  const [touched, setTouched] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const form = e.currentTarget
    setTouched(true)
    if (!isEmail(email)) return focusFirstError(form)
    setBusy(true)
    setError(null)
    try {
      await authApi.requestReset(email)
      setSent(true)
    } catch (err) {
      setError(toAuthError(err).code)
    } finally {
      setBusy(false)
    }
  }
  return (
    <AuthSheet sheet="AUTH-04" title="Reset your password" subtitle="We'll email you a link." footer={<Link to="/login" className="tap-target font-medium text-primary underline-offset-4 hover:underline">Back to sign in</Link>}>
      {sent ? (
        <Notice tone="info" title="If this email can be used, we sent a message">Open the link in it within 1 hour. It signs you out everywhere once you set a new password.</Notice>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-3">
          {error === "rate_limited" && <Notice tone="danger" title="Too many attempts">Wait a few minutes before you try again.</Notice>}
          {error === "network" && <Notice tone="danger" title="Can't reach the server">Check your connection and try again.</Notice>}
          <TextField label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={touched && !isEmail(email) ? "Enter a valid email address." : undefined} />
          <Button type="submit" className="w-full" loading={busy} icon={<PaperPlaneTilt />}>Send reset link</Button>
        </form>
      )}
    </AuthSheet>
  )
}
