import { createFileRoute } from '@tanstack/react-router'
import { TaskPage } from '@/features/tracker/tasks/task-page'

export const Route = createFileRoute('/app/projects/$projectId/tasks/$number')({
  component: TaskRoute,
})

function TaskRoute() {
  const { number } = Route.useParams()
  return <TaskPage number={Number(number)} />
}
