import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ArrowRight, EnvelopeSimple } from "@/icons"
import { AuthError, authApi, toAuthError } from "./api"
import { AuthSheet } from "./auth-sheet"
import { GoogleButton, OrDivider, PasswordField, TextField, focusFirstError, isEmail, passwordOk, passwordProblem } from "./fields"
import { peekInviteCode } from "@/lib/invite"
import { Notice } from "./notice"

export function SignupPage({ email: initialEmail = "", join = false }: { email?: string; join?: boolean }) {
  const [first, setFirst] = useState("")
  const [last, setLast] = useState("")
  const [email, setEmail] = useState(initialEmail)
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [touched, setTouched] = useState(false)
  const [sent, setSent] = useState(false)
  const [serverError, setServerError] = useState<AuthError | null>(null)
  const invite = peekInviteCode()

  // The backend requires a display name; it starts as the first name and can be changed in settings.
  const shownDisplay = first
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const form = e.currentTarget
    setTouched(true)
    if (!first || !last || !isEmail(email) || !passwordOk(password)) return focusFirstError(form)
    setBusy(true)
    setServerError(null)
    try {
      await authApi.signup({ first, last, display: shownDisplay, email, password })
      setSent(true)
    } catch (err) {
      setServerError(toAuthError(err))
    } finally {
      setBusy(false)
    }
  }

  if (sent) {
    return (
      <AuthSheet sheet="AUTH-02" title="Check your inbox" subtitle="One more step.">
        <Notice tone="info" title="If this email can be used, we sent a message">Open the link in it to verify your email. The link works for 24 hours. If you already have an account, the message says so.</Notice>
        <p className="text-sm bp-muted">Sent to <span className="bp-mono">{email}</span></p>
        <Button variant="outline" className="w-full" nativeButton={false} render={<Link to="/verify-email" search={{ email }} />} icon={<EnvelopeSimple />}>I didn't get it</Button>
      </AuthSheet>
    )
  }

  return (
    <AuthSheet
      sheet="AUTH-02"
      title="Create your account"
      subtitle="Free to start. No credit card."
      footer={<p className="bp-muted">Already have an account? <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">Sign in</Link></p>}
    >
      <GoogleButton onError={(code) => setServerError(new AuthError(code))}>Sign up with Google</GoogleButton>
      <OrDivider />
      <form onSubmit={submit} noValidate className="space-y-3">
        {(join || invite) && (
          <Notice tone="info" title={invite ? `Joining with code ${invite}` : "Joining a project?"}>
            {invite ? "Create your account and verify your email. After you sign in, the code is ready to send to the owner." : "Create your account and verify your email first. You enter the join code after you sign in."}
          </Notice>
        )}
        {serverError?.code === "rate_limited" && <Notice tone="danger" title="Too many attempts">Wait a few minutes before you try again.</Notice>}
        {serverError?.code === "network" && <Notice tone="danger" title="Can't reach the server">Check your connection and try again.</Notice>}
        {serverError?.code === "google_failed" && <Notice tone="danger" title="Google sign-in failed">Try again, or sign up with your email.</Notice>}
        <div className="grid grid-cols-2 gap-3">
          <TextField label="First name" autoComplete="given-name" value={first} onChange={(e) => setFirst(e.target.value)} error={(touched && !first ? "Required." : undefined) ?? serverError?.fieldError("first_name")} />
          <TextField label="Last name" autoComplete="family-name" value={last} onChange={(e) => setLast(e.target.value)} error={(touched && !last ? "Required." : undefined) ?? serverError?.fieldError("last_name")} />
        </div>
        <TextField label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={(touched && !isEmail(email) ? "Enter a valid email address." : undefined) ?? serverError?.fieldError("email")} />
        <PasswordField value={password} onChange={setPassword} showRules error={(touched && !passwordOk(password) ? passwordProblem(password) : undefined) ?? serverError?.fieldError("password")} />
        <Button type="submit" className="w-full" loading={busy} iconEnd={<ArrowRight weight="bold" />}>Create account</Button>
        <p className="text-xs bp-muted">Our <Link to="/terms" className="underline underline-offset-2">Terms</Link> and <Link to="/privacy" className="underline underline-offset-2">Privacy policy</Link> apply to your account. Pro-Goal is a learning project, so please do not store anything important in it.</p>
      </form>
    </AuthSheet>
  )
}
