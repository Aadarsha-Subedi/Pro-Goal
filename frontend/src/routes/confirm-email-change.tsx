import { createFileRoute } from '@tanstack/react-router'
import { ConfirmEmailChangePage } from '@/features/auth/confirm-email-change-page'

/** The emailed link from a change-of-address request. Open to everyone: the token is the proof. */
export const Route = createFileRoute('/confirm-email-change')({
  validateSearch: (s: Record<string, unknown>): { token?: string } => ({ token: typeof s.token === 'string' ? s.token : undefined }),
  component: ConfirmRoute,
})

function ConfirmRoute() {
  const { token } = Route.useSearch()
  return <ConfirmEmailChangePage token={token} />
}
