import { createFileRoute, redirect } from '@tanstack/react-router'

/** Email links point at /projects/<id>; the app lives under /app. */
export const Route = createFileRoute('/projects/$projectId/')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/app/projects/$projectId', params, replace: true })
  },
})
