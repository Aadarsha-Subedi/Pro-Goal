import { createFileRoute } from '@tanstack/react-router'
import { ProjectOverview } from '@/features/projects/project-overview'

export const Route = createFileRoute('/app/projects/$projectId/')({ component: ProjectOverview })
