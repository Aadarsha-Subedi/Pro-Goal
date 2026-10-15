import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { ExplorePage, validateExploreSearch, type ExploreSearch } from '@/features/explore/explore-page'

export const Route = createFileRoute('/app/explore')({
  validateSearch: validateExploreSearch,
  component: ExploreRoute,
})

function ExploreRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const onSearch = useCallback((next: ExploreSearch) => navigate({ search: next, replace: true }), [navigate])
  return <ExplorePage search={search} onSearch={onSearch} />
}
