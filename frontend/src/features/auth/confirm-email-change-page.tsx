import { useQueryClient } from "@tanstack/react-query"
import { Link, useRouter } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { accountApi } from "@/features/account/api"
import { accountError } from "@/features/account/errors"
import { ArrowRight, Check } from "@/icons"
import { AuthSheet } from "./auth-sheet"
import { Notice } from "./notice"

/**
 * The link in the email sent to the new address. It asks for a click instead of confirming on load,
 * so a mail scanner opening the link cannot change the address by itself.
 */
export function ConfirmEmailChangePage({ token }: { token?: string }) {
  const queryClient = useQueryClient()
  const router = useRouter()
  const [state, setState] = useState<"ready" | "busy" | "done" | "failed">("ready")
  const [message, setMessage] = useState("")

  const confirm = async () => {
    if (!token) return
    setState("busy")
    try {
      await accountApi.confirmEmailChange(token)
      queryClient.clear()
      await router.invalidate()
      setState("done")
    } catch (e) {
      setMessage(accountError(e))
      setState("failed")
    }
  }

  if (!token)
    return (
      <AuthSheet sheet="AUTH-05" title="This link doesn't work">
        <Notice tone="warning" title="The link is incomplete">Open the whole link from the email, or request the change again from your account.</Notice>
        <Button className="w-full" nativeButton={false} render={<Link to="/login" />} iconEnd={<ArrowRight weight="bold" />}>Sign in</Button>
      </AuthSheet>
    )
  if (state === "done")
    return (
      <AuthSheet sheet="AUTH-05" title="Email changed" subtitle="Sign in again with your new address.">
        <Notice tone="success" title="You were signed out everywhere">This keeps your account safe after a change like this.</Notice>
        <Button className="w-full" nativeButton={false} render={<Link to="/login" />} iconEnd={<ArrowRight weight="bold" />}>Sign in</Button>
      </AuthSheet>
    )
  return (
    <AuthSheet sheet="AUTH-05" title="Confirm your new email" subtitle="One click makes this address your sign-in email.">
      <Notice tone="info" title="You will be signed out everywhere">Every device signs out when the change goes through. Sign in again with the new address.</Notice>
      {state === "failed" && <Notice tone="danger" title="Couldn't change the email">{message}</Notice>}
      <Button className="w-full" icon={<Check weight="bold" />} loading={state === "busy"} onClick={confirm}>Use this address</Button>
      <Button variant="ghost" className="w-full" nativeButton={false} render={<Link to="/login" />}>This wasn't me</Button>
    </AuthSheet>
  )
}
