import { createFileRoute } from '@tanstack/react-router'
import { MembersPage } from '@/features/projects/members-page'

export const Route = createFileRoute('/app/projects/$projectId/members')({ component: MembersPage })
