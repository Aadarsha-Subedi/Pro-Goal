import { Link } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ShieldCheck } from "@/icons"
import { authApi, toAuthError } from "./api"
import { AuthSheet } from "./auth-sheet"
import { PasswordField, focusFirstError, passwordOk, passwordProblem } from "./fields"
import { Notice } from "./notice"

export function ResetPasswordPage({ expired: forcedExpired = false, uid = "", token = "" }: { expired?: boolean; uid?: string; token?: string }) {
  const incomplete = !uid || !token
  const [expired, setExpired] = useState(forcedExpired)
  const [serverError, setServerError] = useState<string | null>(null)
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [busy, setBusy] = useState(false)
  const [touched, setTouched] = useState(false)
  const [done, setDone] = useState(false)

  if (incomplete && !forcedExpired) {
    return (
      <AuthSheet sheet="AUTH-05" title="This reset link is incomplete">
        <Notice tone="warning" title="Open the full link from your email">If you pasted it, check that nothing was cut off. Or ask for a new one.</Notice>
        <Button className="w-full" nativeButton={false} render={<Link to="/forgot-password" />}>Send a new link</Button>
      </AuthSheet>
    )
  }
  if (expired) {
    return (
      <AuthSheet sheet="AUTH-05" title="This reset link has expired">
        <Notice tone="warning" title="Reset links work for 1 hour">Ask for a new one to continue.</Notice>
        <Button className="w-full" nativeButton={false} render={<Link to="/forgot-password" />}>Send a new link</Button>
      </AuthSheet>
    )
  }
  if (done) {
    return (
      <AuthSheet sheet="AUTH-05" title="Password changed">
        <Notice tone="success" title="You were signed out everywhere">Sign in with your new password.</Notice>
        <Button className="w-full" nativeButton={false} render={<Link to="/login" search={{ notice: "reset" }} />}>Sign in</Button>
      </AuthSheet>
    )
  }
  const mismatch = confirm.length > 0 && confirm !== password
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const form = e.currentTarget
    setTouched(true)
    if (!passwordOk(password) || password !== confirm) return focusFirstError(form)
    setBusy(true)
    setServerError(null)
    try {
      await authApi.confirmReset(uid, token, password)
      setDone(true)
    } catch (err) {
      const e = toAuthError(err)
      if (e.code === "link_invalid") setExpired(true)
      else setServerError(e.code === "validation" ? (e.fieldError("new_password") ?? "Choose a stronger password.") : "network")
    } finally {
      setBusy(false)
    }
  }
  return (
    <AuthSheet sheet="AUTH-05" title="Choose a new password" subtitle="You will be signed out on every device.">
      <form onSubmit={submit} noValidate className="space-y-3">
        {serverError === "network" && <Notice tone="danger" title="Can't reach the server">Check your connection and try again.</Notice>}
        <PasswordField label="New password" value={password} onChange={setPassword} showRules error={(touched && !passwordOk(password) ? passwordProblem(password) : undefined) ?? (serverError && serverError !== "network" ? serverError : undefined)} />
        <PasswordField label="Confirm new password" value={confirm} onChange={setConfirm} error={mismatch || (touched && !confirm) ? "Passwords don't match." : undefined} />
        <Button type="submit" className="w-full" loading={busy} icon={<ShieldCheck />}>Change password</Button>
      </form>
    </AuthSheet>
  )
}
