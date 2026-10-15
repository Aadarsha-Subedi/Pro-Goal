import { createFileRoute, Outlet } from '@tanstack/react-router'
import { AppShell } from '@/components/layout/app-shell'
import { requireSession } from '@/lib/session'

/** Signed-in area: the guard runs once here, every child route inherits the session. */
export const Route = createFileRoute('/app')({
  beforeLoad: requireSession,
  component: AppLayout,
})

function AppLayout() {
  const { me } = Route.useRouteContext()
  return (
    <AppShell me={me}>
      <Outlet />
    </AppShell>
  )
}
