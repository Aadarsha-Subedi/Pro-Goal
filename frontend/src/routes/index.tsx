import { createFileRoute } from '@tanstack/react-router'
import { LandingPage } from '@/features/marketing/landing-page'
import { guestOnly } from '@/lib/session'

export const Route = createFileRoute('/')({
  validateSearch: (s: Record<string, unknown>): { code?: string } => ({ code: typeof s.code === 'string' ? s.code : undefined }),
  beforeLoad: guestOnly,
  component: LandingPage,
})
