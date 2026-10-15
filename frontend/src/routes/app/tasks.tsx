import { createFileRoute } from '@tanstack/react-router'
import { MyTasksPage } from '@/features/tracker/tasks/my-tasks-page'

export const Route = createFileRoute('/app/tasks')({ component: MyTasksPage })
