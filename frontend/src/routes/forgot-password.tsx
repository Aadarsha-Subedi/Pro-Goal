import { createFileRoute } from '@tanstack/react-router'
import { guestOnly } from '@/lib/session'
import { ForgotPasswordPage } from '@/features/auth/forgot-password-page'

export const Route = createFileRoute('/forgot-password')({ beforeLoad: guestOnly, component: ForgotPasswordPage })
