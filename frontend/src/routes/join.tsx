import { createFileRoute } from '@tanstack/react-router'
import { JoinPage } from '@/features/projects/join-page'
import { normalizeInviteCode } from '@/lib/invite'
import { requireSessionForJoin } from '@/lib/session'

export const Route = createFileRoute('/join')({
  validateSearch: (s: Record<string, unknown>): { code?: string } => ({ code: typeof s.code === 'string' ? normalizeInviteCode(s.code) || undefined : undefined }),
  beforeLoad: requireSessionForJoin,
  component: JoinRoute,
})

function JoinRoute() {
  const { code } = Route.useSearch()
  const { me } = Route.useRouteContext()
  return <JoinPage code={code} me={me} />
}
