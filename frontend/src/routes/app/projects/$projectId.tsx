import { createFileRoute } from '@tanstack/react-router'
import { ProjectLayout } from '@/features/projects/project-layout'

export const Route = createFileRoute('/app/projects/$projectId')({ component: ProjectLayout })
