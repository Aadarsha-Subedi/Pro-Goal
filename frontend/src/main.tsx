import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ApiError, setUnauthorizedHandler } from '@/lib/api'
import { ThemeProvider } from '@/hooks/use-theme'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import './index.css'
import { routeTree } from './routeTree.gen'
import { NotFoundScreen } from '@/components/patterns/not-found-screen'
import { ErrorScreen } from '@/components/patterns/error-screen'
import { RouterPending, setOutsideApp } from '@/components/layout/router-pending'

// Data is fetched on mount and after mutations only: no refetch on tab focus or reconnect (request quota); reload for fresh data.
// 4xx answers are final (not found, no access, validation); only network and 5xx failures are worth a retry.
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: (count, e) => count < 2 && !(e instanceof ApiError && e.status >= 400 && e.status < 500), staleTime: 5 * 60_000, refetchOnWindowFocus: false, refetchOnReconnect: false } },
})
const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPendingComponent: RouterPending,
  defaultNotFoundComponent: () => <NotFoundScreen />,
  defaultErrorComponent: ({ error, reset }) => <ErrorScreen error={error} reset={reset} />,
  defaultPendingMs: 200,
  defaultPendingMinMs: 200,
})
router.subscribe('onResolved', ({ toLocation }) => setOutsideApp(!toLocation.pathname.startsWith('/app')))

// A data request answered 401: the session ended (expired, revoked, signed out elsewhere). Back to sign-in once.
setUnauthorizedHandler(() => {
  queryClient.clear()
  if (!['/login', '/signup'].includes(router.state.location.pathname)) router.navigate({ to: '/login', search: { notice: 'revoked' }, replace: true })
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider delay={300}>
          <RouterProvider router={router} />
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
