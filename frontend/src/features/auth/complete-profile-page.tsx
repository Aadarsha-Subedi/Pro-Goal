import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "@/icons"
import { authApi, toAuthError } from "./api"
import { AuthSheet } from "./auth-sheet"
import { TextField, focusFirstError } from "./fields"
import { Notice } from "./notice"

export function CompleteProfilePage() {
  const [first, setFirst] = useState("")
  const [last, setLast] = useState("")
  const [display, setDisplay] = useState("")
  const [displayTouched, setDisplayTouched] = useState(false)
  const [busy, setBusy] = useState(false)
  const [touched, setTouched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const shown = displayTouched ? display : first
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const form = e.currentTarget
    setTouched(true)
    if (!first || !last || !shown) return focusFirstError(form)
    setBusy(true)
    setError(null)
    try {
      await authApi.completeProfile({ first, last, display: shown })
      navigate({ to: "/app" })
    } catch (err) {
      const e = toAuthError(err)
      setError(e.code === "validation" ? "Check your names and try again." : "We couldn't save that. Check your connection and try again.")
    } finally {
      setBusy(false)
    }
  }
  return (
    <AuthSheet sheet="AUTH-06" title="Finish your profile" subtitle="Google didn't share your name. Teammates see this.">
      <form onSubmit={submit} noValidate className="space-y-3">
        {error && <Notice tone="danger" title="Not saved">{error}</Notice>}
        <div className="grid grid-cols-2 gap-3">
          <TextField label="First name" autoComplete="given-name" value={first} onChange={(e) => setFirst(e.target.value)} error={touched && !first ? "Required." : undefined} />
          <TextField label="Last name" autoComplete="family-name" value={last} onChange={(e) => setLast(e.target.value)} error={touched && !last ? "Required." : undefined} />
        </div>
        <TextField label="Display name" autoComplete="nickname" hint="You can change it later." value={shown} onChange={(e) => { setDisplayTouched(true); setDisplay(e.target.value) }} error={touched && !shown ? "Required." : undefined} />
        <Button type="submit" className="w-full" loading={busy} iconEnd={<ArrowRight weight="bold" />}>Continue</Button>
      </form>
    </AuthSheet>
  )
}
