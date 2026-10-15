import { createFileRoute } from '@tanstack/react-router'
import { PrivacyPage } from '@/features/marketing/privacy-page'

export const Route = createFileRoute('/privacy')({ component: PrivacyPage })
