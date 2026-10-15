import { Link, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ArrowRight, ArrowClockwise } from "@/icons"
import { waitText } from "@/lib/format"
import { AuthError, authApi, toAuthError } from "./api"
import { AuthSheet } from "./auth-sheet"
import { GoogleButton, OrDivider, PasswordField, TextField, focusFirstError, isEmail } from "./fields"
import { Notice } from "./notice"

export type LoginNotice = "deleted" | "revoked" | "reset"

export function LoginPage({ notice, googleError }: { notice?: LoginNotice; googleError?: AuthError["code"] }) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [remember, setRemember] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<AuthError["code"] | null>(googleError ?? null)
  const [retryAfter, setRetryAfter] = useState<number | undefined>()
  const navigate = useNavigate()
  const [resent, setResent] = useState(false)
  const [touched, setTouched] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const form = e.currentTarget
    setTouched(true)
    if (!isEmail(email) || !password) return focusFirstError(form)
    setBusy(true)
    setError(null)
    setRetryAfter(undefined)
    try {
      await authApi.login(email, password, remember)
      navigate({ to: "/app" })
    } catch (err) {
      const failure = toAuthError(err)
      setError(failure.code)
      setRetryAfter(failure.retryAfter)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthSheet
      sheet="AUTH-01"
      title="Sign in"
      subtitle="Welcome back."
      footer={<p className="bp-muted">New to Pro-Goal? <Link to="/signup" className="font-medium text-primary underline-offset-4 hover:underline">Create an account</Link></p>}
    >
      {notice === "deleted" && <Notice tone="warning" title="Your account is scheduled for deletion">Signing in now cancels the deletion and restores your account.</Notice>}
      {notice === "revoked" && <Notice tone="info" title="You were signed out on this device">Your session was ended from another device. Sign in again to continue.</Notice>}
      {notice === "reset" && <Notice tone="success" title="Password changed">You were signed out everywhere. Sign in with your new password.</Notice>}
      <GoogleButton remember={remember} onError={setError} />
      <OrDivider />
      <form onSubmit={submit} noValidate className="space-y-3">
        {error === "invalid_credentials" && <Notice tone="danger" title="Invalid email or password">Check both and try again.</Notice>}
        {error === "email_not_verified" && (
          <Notice
            tone="warning"
            title="Verify your email first"
            action={<Button type="button" size="sm" variant="outline" icon={<ArrowClockwise />} onClick={async () => { await authApi.resendVerification(email); setResent(true) }} disabled={resent}>{resent ? "Verification email sent" : "Resend verification email"}</Button>}
          >
            We sent a link to {email}. It stays valid for 24 hours.
          </Notice>
        )}
        {error === "locked" && <Notice tone="danger" title="Account locked for now">Too many wrong passwords. Try again in {retryAfter ? waitText(retryAfter) : "a few minutes"}, or <Link to="/forgot-password" className="font-medium text-primary underline-offset-4 hover:underline">reset your password</Link>.</Notice>}
        {error === "rate_limited" && <Notice tone="danger" title="Too many attempts">Wait a few minutes before you try again.</Notice>}
        {error === "google_failed" && <Notice tone="danger" title="Google sign-in failed">Try again, or sign in with your email.</Notice>}
        {error === "network" && <Notice tone="danger" title="Can't reach the server">Check your connection and try again.</Notice>}
        <TextField label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={touched && !isEmail(email) ? "Enter a valid email address." : undefined} />
        <PasswordField label="Password" value={password} onChange={setPassword} autoComplete="current-password" error={touched && !password ? "Enter your password." : undefined} />
        <div className="flex items-center justify-between text-sm">
          <label className="tap-target gap-2"><Checkbox checked={remember} onCheckedChange={(v) => setRemember(!!v)} /> Keep me signed in for 30 days</label>
        </div>
        <Button type="submit" className="w-full" loading={busy} iconEnd={<ArrowRight weight="bold" />}>Sign in</Button>
        <p className="text-sm"><Link to="/forgot-password" className="tap-target font-medium text-primary underline-offset-4 hover:underline">Forgot your password?</Link></p>
      </form>
    </AuthSheet>
  )
}
