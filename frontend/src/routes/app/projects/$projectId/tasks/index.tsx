import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { TasksPage } from '@/features/tracker/tasks/tasks-page'
import { validateTaskSearch, type TaskSearch } from '@/features/tracker/search'

export const Route = createFileRoute('/app/projects/$projectId/tasks/')({
  validateSearch: validateTaskSearch,
  component: TasksRoute,
})

function TasksRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  return <TasksPage search={search} onSearch={(next: TaskSearch) => navigate({ search: next, replace: true })} />
}
