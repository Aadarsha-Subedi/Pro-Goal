import { createFileRoute } from '@tanstack/react-router'
import { guestOnly } from '@/lib/session'
import { LoginPage, type LoginNotice } from '@/features/auth/login-page'

export const Route = createFileRoute('/login')({
  validateSearch: (s: Record<string, unknown>): { notice?: LoginNotice; code?: string; google_error?: 'google_failed' | 'rate_limited' } => ({
    google_error: s.google_error === 'google_failed' || s.google_error === 'rate_limited' ? s.google_error : undefined,
    code: typeof s.code === 'string' ? s.code : undefined,
    notice: s.notice === 'deleted' || s.notice === 'revoked' || s.notice === 'reset' ? s.notice : undefined,
  }),
  beforeLoad: guestOnly,
  component: LoginRoute,
})

function LoginRoute() {
  const search = Route.useSearch()
  return <LoginPage notice={search.notice} googleError={search.google_error} />
}
