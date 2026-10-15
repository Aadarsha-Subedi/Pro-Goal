import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { NotesPage, validateNoteSearch, type NoteSearch } from '@/features/tracker/notes/notes-page'

export const Route = createFileRoute('/app/projects/$projectId/notes/')({
  validateSearch: validateNoteSearch,
  component: NotesRoute,
})

function NotesRoute() {
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  return <NotesPage search={search} onSearch={(next: NoteSearch) => navigate({ search: next, replace: true })} />
}
