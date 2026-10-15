import { Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { ArrowClockwise, ArrowRight } from "@/icons"
import { authApi, toAuthError } from "./api"
import { AuthSheet } from "./auth-sheet"
import { Notice } from "./notice"

// One request per token: verification links are single-use, so a remount (StrictMode, navigation) must reuse the in-flight call.
const inflight = new Map<string, Promise<unknown>>()
function verifyOnce(token: string) {
  let p = inflight.get(token)
  if (!p) {
    p = authApi.verifyEmail(token)
    inflight.set(token, p)
  }
  return p
}

export type VerifyState = "inbox" | "success" | "expired" | "invalid"

/**
 * Email verification. With a `token` (from the emailed link) it verifies on load; without one it is
 * the waiting screen after signup. `state` can force a screen for design review.
 */
export function VerifyEmailPage({ token, state: forced, email = "" }: { token?: string; state?: VerifyState; email?: string }) {
  const [state, setState] = useState<VerifyState | "checking">(forced ?? (token ? "checking" : "inbox"))
  const [cooldown, setCooldown] = useState(0)
  const [busy, setBusy] = useState(false)
  const [limit, setLimit] = useState(false)
  const [sends, setSends] = useState(0)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!token || forced) return
    let live = true
    verifyOnce(token)
      .then(() => live && setState("success"))
      .catch((e) => live && setState(toAuthError(e).code === "link_expired" ? "expired" : "invalid"))
    return () => {
      live = false
    }
  }, [token, forced])

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown(cooldown - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const resend = async () => {
    if (sends >= 5) return setLimit(true)
    setBusy(true)
    setFailed(false)
    try {
      await authApi.resendVerification(email)
      setSends(sends + 1)
      setCooldown(60)
    } catch (e) {
      if (toAuthError(e).code === "rate_limited") setLimit(true)
      else setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  const resendButton = (variant: "default" | "outline" = "default") => (
    <div className="space-y-2">
      {limit && <Notice tone="danger" title="Too many requests">You can request 5 emails per hour. Try again later.</Notice>}
      {failed && <Notice tone="danger" title="We couldn't send it">Check your connection and try again.</Notice>}
      {email ? (
        <Button className="w-full" variant={variant} icon={<ArrowClockwise />} loading={busy} disabled={cooldown > 0 || limit} onClick={resend}>
          {cooldown > 0 ? `Resend in ${cooldown}s` : "Send a new link"}
        </Button>
      ) : (
        <Button className="w-full" nativeButton={false} render={<Link to="/login" />}>Sign in to get a new link</Button>
      )}
    </div>
  )

  if (state === "checking") {
    return (
      <AuthSheet sheet="AUTH-03" title="Verifying your email">
        <p className="flex items-center gap-2 text-sm bp-muted" role="status"><Spinner /> One moment.</p>
      </AuthSheet>
    )
  }
  if (state === "success") {
    return (
      <AuthSheet sheet="AUTH-03" title="Email verified" subtitle="Sign in to create or join your first project.">
        <Button className="w-full" nativeButton={false} render={<Link to="/login" />} iconEnd={<ArrowRight weight="bold" />}>Sign in</Button>
      </AuthSheet>
    )
  }
  if (state === "expired" || state === "invalid") {
    return (
      <AuthSheet sheet="AUTH-03" title={state === "expired" ? "This link has expired" : "This link doesn't work"}>
        <Notice tone="warning" title={state === "expired" ? "Verification links work for 24 hours" : "It may have been used already"}>
          {state === "expired" ? "Ask for a new one and use it within 24 hours." : "If your email is already verified, sign in. If not, ask for a new link."}
        </Notice>
        {state === "invalid" && <Button className="w-full" nativeButton={false} render={<Link to="/login" />} iconEnd={<ArrowRight weight="bold" />}>Sign in</Button>}
        {resendButton(state === "invalid" ? "outline" : "default")}
        {email && <Button variant="ghost" className="w-full" nativeButton={false} render={<Link to="/login" />}>Back to sign in</Button>}
      </AuthSheet>
    )
  }
  return (
    <AuthSheet sheet="AUTH-03" title="Check your inbox" subtitle={email ? `We sent a link to ${email}.` : "We sent a link to the email you signed up with."}>
      <Notice tone="info" title="Open the link to verify your email">It works for 24 hours and once only. Check spam if you don't see it.</Notice>
      {resendButton()}
      <Button variant="ghost" className="w-full" nativeButton={false} render={<Link to="/signup" />}>Use a different email</Button>
    </AuthSheet>
  )
}
