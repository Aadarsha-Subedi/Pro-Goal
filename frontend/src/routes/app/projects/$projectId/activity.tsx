import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { ActivityPage, validateActivitySearch, type ActivitySearch } from '@/features/activity/activity-page'

export const Route = createFileRoute('/app/projects/$projectId/activity')({
  validateSearch: validateActivitySearch,
  component: ActivityRoute,
})

function ActivityRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const onSearch = useCallback((next: ActivitySearch) => navigate({ search: next, replace: true }), [navigate])
  return <ActivityPage search={search} onSearch={onSearch} />
}
