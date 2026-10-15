import { createFileRoute } from '@tanstack/react-router'
import { VerifyEmailPage, type VerifyState } from '@/features/auth/verify-email-page'

export const Route = createFileRoute('/verify-email')({
  validateSearch: (s: Record<string, unknown>): { token?: string; state?: VerifyState; email?: string } => ({
    token: typeof s.token === 'string' ? s.token : undefined,
    state: s.state === 'success' || s.state === 'expired' || s.state === 'invalid' || s.state === 'inbox' ? s.state : undefined,
    email: typeof s.email === 'string' ? s.email : undefined,
  }),
  component: VerifyRoute,
})

function VerifyRoute() {
  const { token, state, email } = Route.useSearch()
  return <VerifyEmailPage token={token} state={state} email={email} />
}
