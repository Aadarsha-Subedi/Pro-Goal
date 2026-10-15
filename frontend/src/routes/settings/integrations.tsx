import { createFileRoute, redirect } from '@tanstack/react-router'
import { validateIntegrationsSearch } from '@/features/integrations/integrations-page'

/** Slack sends the browser back to /settings/integrations?slack=... after a person links their account. */
export const Route = createFileRoute('/settings/integrations')({
  validateSearch: validateIntegrationsSearch,
  beforeLoad: ({ search }) => {
    throw redirect({ to: '/app/account', search, hash: 'slack', replace: true })
  },
})
