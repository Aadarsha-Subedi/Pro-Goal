import { createFileRoute } from '@tanstack/react-router'
import { guestOnly } from '@/lib/session'
import { SignupPage } from '@/features/auth/signup-page'

export const Route = createFileRoute('/signup')({
  validateSearch: (s: Record<string, unknown>): { email?: string; join?: boolean; code?: string } => ({ code: typeof s.code === 'string' ? s.code : undefined, email: typeof s.email === 'string' ? s.email : undefined, join: s.join === true || s.join === 'true' ? true : undefined }),
  beforeLoad: guestOnly,
  component: SignupRoute,
})

function SignupRoute() {
  const search = Route.useSearch()
  return <SignupPage email={search.email} join={search.join} />
}
