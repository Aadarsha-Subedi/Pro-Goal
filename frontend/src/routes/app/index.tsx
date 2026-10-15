import { createFileRoute, redirect } from '@tanstack/react-router'
import { ProjectsPage } from '@/features/projects/projects-page'
import { takeInviteCode } from '@/lib/invite'

export const Route = createFileRoute('/app/')({
  // A join code kept through signup and sign-in is used once, here, on the first visit to the app.
  beforeLoad: () => {
    const code = takeInviteCode()
    if (code) throw redirect({ to: '/join', search: { code }, replace: true })
  },
  component: ProjectsPage,
})
