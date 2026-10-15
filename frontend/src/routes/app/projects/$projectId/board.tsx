import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { BoardPage } from '@/features/tracker/board/board-page'
import { validateTaskSearch, type TaskSearch } from '@/features/tracker/search'

export const Route = createFileRoute('/app/projects/$projectId/board')({
  validateSearch: validateTaskSearch,
  component: BoardRoute,
})

function BoardRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  return <BoardPage search={search} onSearch={(next: TaskSearch) => navigate({ search: next, replace: true })} />
}
