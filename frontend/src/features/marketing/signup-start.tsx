import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { GoogleButton, OrDivider, TextField, isEmail } from "@/features/auth/fields"
import { Notice } from "@/features/auth/notice"
import { ArrowRight } from "@/icons"

/** First step of signup, used inside the title block: Google, or an email that carries into /signup. */
export function SignupStart() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [touched, setTouched] = useState(false)
  const [googleError, setGoogleError] = useState<string | null>(null)
  const go = (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!isEmail(email)) return
    navigate({ to: "/signup", search: { email } })
  }
  return (
    <div className="space-y-3">
      <GoogleButton onError={setGoogleError}>Sign up with Google</GoogleButton>
      {googleError && <Notice tone="danger" title="Google sign-in failed">{googleError === "network" ? "Check your connection and try again." : "Try again, or continue with your email."}</Notice>}
      <OrDivider />
      <form onSubmit={go} noValidate className="space-y-3">
        <TextField label="Work email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={touched && !isEmail(email) ? "Enter a valid email address." : undefined} />
        <Button type="submit" className="w-full" iconEnd={<ArrowRight weight="bold" />}>Continue with email</Button>
      </form>
    </div>
  )
}
