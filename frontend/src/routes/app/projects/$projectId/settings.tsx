import { createFileRoute } from '@tanstack/react-router'
import { SettingsPage } from '@/features/projects/settings-page'

export const Route = createFileRoute('/app/projects/$projectId/settings')({ component: SettingsPage })
