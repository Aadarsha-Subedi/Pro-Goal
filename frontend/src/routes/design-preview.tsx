import { createFileRoute, notFound } from '@tanstack/react-router'
import { lazy, Suspense } from 'react'

// import.meta.env.DEV is replaced at build time, so the preview chunk is not emitted in production.
const Preview = import.meta.env.DEV
  ? lazy(() => import('@/features/design-preview/preview-page').then((m) => ({ default: m.DesignPreview })))
  : null

export const Route = createFileRoute('/design-preview')({
  beforeLoad: () => {
    if (!import.meta.env.DEV) throw notFound()
  },
  component: () => (Preview ? <Suspense fallback={null}><Preview /></Suspense> : null),
})
