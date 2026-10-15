import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { AccountPage, validateAccountSearch, type AccountSearch } from '@/features/account/account-page'

export const Route = createFileRoute('/app/account')({
  validateSearch: validateAccountSearch,
  component: AccountRoute,
})

function AccountRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  return <AccountPage search={search} onSearch={(next: AccountSearch) => navigate({ search: next, replace: true })} />
}
