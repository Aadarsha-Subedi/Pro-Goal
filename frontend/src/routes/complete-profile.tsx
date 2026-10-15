import { createFileRoute } from '@tanstack/react-router'
import { requireIncompleteProfile } from '@/lib/session'
import { CompleteProfilePage } from '@/features/auth/complete-profile-page'

export const Route = createFileRoute('/complete-profile')({ beforeLoad: requireIncompleteProfile, component: CompleteProfilePage })
