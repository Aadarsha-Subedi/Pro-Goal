import { useEffect } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Logo } from "@/components/patterns/logo"
import { useDocumentTitle } from "@/hooks/use-document-title"
import type { Me } from "@/features/auth/api"
import { takeInviteCode } from "@/lib/invite"
import { JoinForm } from "./join-form"

/** Landing spot for invite links (/join?code=ABC123). The code is prefilled; the person still confirms it. */
export function JoinPage({ code, me }: { code?: string; me: Me }) {
  useDocumentTitle("Join a project · Pro-Goal")
  const navigate = useNavigate()
  // The code is in the form now; a stored copy would send the user back here from /app.
  useEffect(() => { takeInviteCode() }, [])
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-4 py-10">
      <Logo />
      <p className="text-sm text-muted-foreground">Signed in as {me.email}.</p>
      <JoinForm asPage initialCode={code ?? ""} doneLabel="Go to my projects" onDone={() => navigate({ to: "/app" })} />
    </main>
  )
}
