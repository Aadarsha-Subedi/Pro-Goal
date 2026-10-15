import { createFileRoute } from '@tanstack/react-router'
import { PermissionsPage } from '@/features/permissions/permissions-page'

export const Route = createFileRoute('/app/projects/$projectId/members_/$userId/permissions')({ component: PermissionsPage })
