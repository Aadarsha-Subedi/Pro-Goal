import { createFileRoute } from '@tanstack/react-router'
import { TermsPage } from '@/features/marketing/terms-page'

export const Route = createFileRoute('/terms')({ component: TermsPage })
