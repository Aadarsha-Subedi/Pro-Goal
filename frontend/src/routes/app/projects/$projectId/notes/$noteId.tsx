import { createFileRoute } from '@tanstack/react-router'
import { NotePage } from '@/features/tracker/notes/note-page'

export const Route = createFileRoute('/app/projects/$projectId/notes/$noteId')({
  validateSearch: (s: Record<string, unknown>): { edit?: boolean } => ({ edit: s.edit === true || s.edit === 'true' ? true : undefined }),
  component: NoteRoute,
})

function NoteRoute() {
  const { noteId } = Route.useParams()
  const { edit } = Route.useSearch()
  return <NotePage noteId={noteId} startEditing={!!edit} />
}
