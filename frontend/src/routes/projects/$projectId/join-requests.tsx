import { createFileRoute, redirect } from '@tanstack/react-router'

/** Join-request emails link to /projects/<id>/join-requests. */
export const Route = createFileRoute('/projects/$projectId/join-requests')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/app/projects/$projectId/requests', params, replace: true })
  },
})
