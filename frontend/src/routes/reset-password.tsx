import { createFileRoute } from '@tanstack/react-router'
import { ResetPasswordPage } from '@/features/auth/reset-password-page'

export const Route = createFileRoute('/reset-password')({
  validateSearch: (s: Record<string, unknown>): { uid?: string; token?: string; expired?: boolean } => ({
    uid: typeof s.uid === 'string' ? s.uid : undefined,
    token: typeof s.token === 'string' ? s.token : undefined,
    expired: s.expired === true || s.expired === 'true' ? true : undefined,
  }),
  component: ResetRoute,
})

function ResetRoute() {
  const { uid, token, expired } = Route.useSearch()
  return <ResetPasswordPage uid={uid} token={token} expired={expired} />
}
