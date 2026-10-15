import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { IntegrationsPage, validateIntegrationsSearch, type IntegrationsSearch } from '@/features/integrations/integrations-page'

export const Route = createFileRoute('/app/projects/$projectId/integrations')({
  validateSearch: validateIntegrationsSearch,
  component: IntegrationsRoute,
})

function IntegrationsRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  return <IntegrationsPage search={search} onSearch={(next: IntegrationsSearch) => navigate({ search: next, replace: true })} />
}
