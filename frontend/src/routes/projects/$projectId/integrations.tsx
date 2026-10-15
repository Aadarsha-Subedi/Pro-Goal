import { createFileRoute, redirect } from '@tanstack/react-router'
import { validateIntegrationsSearch } from '@/features/integrations/integrations-page'

/** Slack sends the browser back to /projects/<id>/integrations?slack=... after installing the app. */
export const Route = createFileRoute('/projects/$projectId/integrations')({
  validateSearch: validateIntegrationsSearch,
  beforeLoad: ({ params, search }) => {
    throw redirect({ to: '/app/projects/$projectId/integrations', params, search, replace: true })
  },
})
