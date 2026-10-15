import { createFileRoute } from '@tanstack/react-router'
import { RequestsPage } from '@/features/projects/requests-page'

export const Route = createFileRoute('/app/projects/$projectId/requests')({ component: RequestsPage })
