import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { DeliveriesPage, validateDeliverySearch, type DeliverySearch } from '@/features/integrations/deliveries-page'

export const Route = createFileRoute('/app/projects/$projectId/integrations_/$integrationId/deliveries')({
  validateSearch: validateDeliverySearch,
  component: DeliveriesRoute,
})

function DeliveriesRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  return <DeliveriesPage search={search} onSearch={(next: DeliverySearch) => navigate({ search: next, replace: true })} />
}
