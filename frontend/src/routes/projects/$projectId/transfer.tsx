import { createFileRoute, redirect } from '@tanstack/react-router'

/** Transfer-offer emails link to /projects/<id>/transfer; offers are pinned on the projects page. */
export const Route = createFileRoute('/projects/$projectId/transfer')({
  beforeLoad: () => {
    throw redirect({ to: '/app', replace: true })
  },
})
