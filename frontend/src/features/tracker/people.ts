import { useMemo } from "react"
import type { Person } from "@/components/patterns/member-picker"
import { useQuery } from "@tanstack/react-query"
import { membersQuery, useMembers } from "@/features/projects/queries"
import { useLazyOptions } from "@/lib/lazy-options"

/** Project members as pickable people. Non-owners see first names only, which is all they get from the API. */
export function useProjectPeople(projectId: string): { people: Person[]; byId: Map<string, Person>; isPending: boolean } {
  const { data, isPending } = useMembers(projectId)
  return useMemo(() => {
    const people = (data?.items ?? []).map((m) => ({ id: m.id, name: m.display_name || m.first_name, avatar_url: m.avatar_url }))
    return { people, byId: new Map(people.map((p) => [p.id, p])), isPending }
  }, [data, isPending])
}

const toPerson = (m: { id: string; display_name?: string; first_name: string; avatar_url?: string | null }): Person => ({ id: m.id, name: m.display_name || m.first_name, avatar_url: m.avatar_url })

/** The same people, requested only once a dropdown that lists them opens (or at once with `force`). */
export function useLazyProjectPeople(projectId: string, force = false) {
  const members = useLazyOptions((enabled) => useQuery({ ...membersQuery(projectId), enabled: enabled && !!projectId }), force)
  return { ...members, items: members.items.map(toPerson) }
}
