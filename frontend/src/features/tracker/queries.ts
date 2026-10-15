import { keepPreviousData, queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { trackerApi, type BoardPreference, type StatusCategory, type TaskCreate, type TaskFilters, type TaskPatch } from "./api"
import { useLazyOptions } from "@/lib/lazy-options"
import { PAGE_SIZE } from "./search"

export const tk = {
  tasks: (pid: string) => ["tasks", pid] as const,
  list: (pid: string, f: TaskFilters, page: number) => ["tasks", pid, "list", f, page] as const,
  board: (pid: string, f: TaskFilters) => ["tasks", pid, "board", f] as const,
  task: (pid: string, n: number) => ["task", pid, n] as const,
  subtasks: (pid: string, n: number) => ["subtasks", pid, n] as const,
  mine: (f: TaskFilters) => ["my-tasks", f] as const,
  statuses: (pid: string) => ["statuses", pid] as const,
  priorities: (pid: string) => ["priorities", pid] as const,
  preference: (pid: string) => ["board-preference", pid] as const,
  notes: (pid: string) => ["notes", pid] as const,
  noteList: (pid: string, q: string, tag: string, page: number) => ["notes", pid, "list", q, tag, page] as const,
  note: (pid: string, id: string) => ["note", pid, id] as const,
  revisions: (pid: string, id: string) => ["revisions", pid, id] as const,
  taskNotes: (pid: string, n: number) => ["task-notes", pid, n] as const,
  comments: (pid: string, n: number) => ["comments", pid, n] as const,
}

export const statusesQuery = (pid: string) => queryOptions({ queryKey: tk.statuses(pid), queryFn: () => trackerApi.statuses(pid), staleTime: 60_000, enabled: !!pid })
export const prioritiesQuery = (pid: string) => queryOptions({ queryKey: tk.priorities(pid), queryFn: () => trackerApi.priorities(pid), staleTime: 60_000, enabled: !!pid })

export const useStatuses = (pid: string) => useQuery(statusesQuery(pid))
export const usePriorities = (pid: string) => useQuery(prioritiesQuery(pid))
/** Status and priority choices for a dropdown: requested when it opens (or at once if `force`, because one is already chosen). */
export const useStatusOptions = (pid: string, force = false) => useLazyOptions((enabled) => useQuery({ ...statusesQuery(pid), enabled: enabled && !!pid }), force)
export const usePriorityOptions = (pid: string, force = false) => useLazyOptions((enabled) => useQuery({ ...prioritiesQuery(pid), enabled: enabled && !!pid }), force)
export const useTasks = (pid: string, filters: TaskFilters, page = 1) =>
  useQuery({ queryKey: tk.list(pid, filters, page), queryFn: () => trackerApi.tasks(pid, filters, (page - 1) * PAGE_SIZE, PAGE_SIZE), placeholderData: keepPreviousData })
export const useBoardTasks = (pid: string, filters: TaskFilters) => useQuery({ queryKey: tk.board(pid, filters), queryFn: () => trackerApi.allTasks(pid, filters) })
export const useTask = (pid: string, number: number) => useQuery({ queryKey: tk.task(pid, number), queryFn: () => trackerApi.task(pid, number), retry: false })
export const useSubtasks = (pid: string, number: number, enabled = true) => useQuery({ queryKey: tk.subtasks(pid, number), queryFn: () => trackerApi.subtasks(pid, number), enabled })
export const useMyTasks = (filters: TaskFilters) => useQuery({ queryKey: tk.mine(filters), queryFn: () => trackerApi.myTasks(filters, 0, 100) })
export const usePreference = (pid: string) => useQuery({ queryKey: tk.preference(pid), queryFn: () => trackerApi.preference(pid), staleTime: Infinity })

/** One place that knows what a change to a task makes stale. */
export function useTaskMutations(pid: string) {
  const qc = useQueryClient()
  const stale = () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: tk.tasks(pid) }),
      qc.invalidateQueries({ queryKey: ["task", pid] }),
      qc.invalidateQueries({ queryKey: ["subtasks", pid] }),
      qc.invalidateQueries({ queryKey: ["my-tasks"] }),
    ])
  return {
    create: useMutation({ mutationFn: (input: TaskCreate) => trackerApi.createTask(pid, input), onSuccess: stale }),
    update: useMutation({ mutationFn: ({ number, patch }: { number: number; patch: TaskPatch }) => trackerApi.updateTask(pid, number, patch), onSuccess: stale }),
    remove: useMutation({ mutationFn: (number: number) => trackerApi.deleteTask(pid, number), onSuccess: stale }),
    restore: useMutation({ mutationFn: (number: number) => trackerApi.restoreTask(pid, number), onSuccess: stale }),
    createSubtask: useMutation({ mutationFn: ({ parent, input }: { parent: number; input: TaskCreate }) => trackerApi.createSubtask(pid, parent, input), onSuccess: stale }),
  }
}

export function useWorkflowMutations(pid: string) {
  const qc = useQueryClient()
  const stale = (...keys: (readonly unknown[])[]) => Promise.all([...keys.map((k) => qc.invalidateQueries({ queryKey: k })), qc.invalidateQueries({ queryKey: tk.tasks(pid) }), qc.invalidateQueries({ queryKey: ["task", pid] })])
  return {
    createStatus: useMutation({ mutationFn: (i: { name: string; category: StatusCategory; is_default?: boolean }) => trackerApi.createStatus(pid, i), onSuccess: () => stale(tk.statuses(pid)) }),
    updateStatus: useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Parameters<typeof trackerApi.updateStatus>[2] }) => trackerApi.updateStatus(pid, id, patch), onSuccess: () => stale(tk.statuses(pid)) }),
    deleteStatus: useMutation({ mutationFn: ({ id, moveTo }: { id: string; moveTo?: string | null }) => trackerApi.deleteStatus(pid, id, moveTo), onSuccess: () => stale(tk.statuses(pid)) }),
    createPriority: useMutation({ mutationFn: (i: { name: string; is_default?: boolean }) => trackerApi.createPriority(pid, i), onSuccess: () => stale(tk.priorities(pid)) }),
    updatePriority: useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Parameters<typeof trackerApi.updatePriority>[2] }) => trackerApi.updatePriority(pid, id, patch), onSuccess: () => stale(tk.priorities(pid)) }),
    deletePriority: useMutation({ mutationFn: ({ id, moveTo }: { id: string; moveTo?: string | null }) => trackerApi.deletePriority(pid, id, moveTo), onSuccess: () => stale(tk.priorities(pid)) }),
  }
}

export function useSavePreference(pid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pref: BoardPreference) => trackerApi.savePreference(pid, pref),
    onSuccess: (pref) => qc.setQueryData(tk.preference(pid), pref),
  })
}

export const useNotes = (pid: string, q: string, tag: string, page = 1) =>
  useQuery({ queryKey: tk.noteList(pid, q, tag, page), queryFn: () => trackerApi.notes(pid, { q: q || undefined, tag: tag || undefined }, (page - 1) * PAGE_SIZE, PAGE_SIZE), placeholderData: keepPreviousData })
export const useNote = (pid: string, id: string) => useQuery({ queryKey: tk.note(pid, id), queryFn: () => trackerApi.note(pid, id), retry: false })
export const useRevisions = (pid: string, id: string, enabled = true) => useQuery({ queryKey: tk.revisions(pid, id), queryFn: () => trackerApi.revisions(pid, id), enabled })
export const useTaskNotes = (pid: string, n: number) => useQuery({ queryKey: tk.taskNotes(pid, n), queryFn: () => trackerApi.taskNotes(pid, n) })
export const useComments = (pid: string, n: number) => useQuery({ queryKey: tk.comments(pid, n), queryFn: () => trackerApi.comments(pid, n) })

export function useNoteMutations(pid: string) {
  const qc = useQueryClient()
  const stale = () => Promise.all([qc.invalidateQueries({ queryKey: tk.notes(pid) }), qc.invalidateQueries({ queryKey: ["note", pid] }), qc.invalidateQueries({ queryKey: ["revisions", pid] }), qc.invalidateQueries({ queryKey: ["task-notes", pid] })])
  return {
    create: useMutation({ mutationFn: (input: { title: string; body?: string; tags?: string[] }) => trackerApi.createNote(pid, input), onSuccess: stale }),
    update: useMutation({ mutationFn: ({ id, input }: { id: string; input: { version: number; title?: string; body?: string; tags?: string[] } }) => trackerApi.updateNote(pid, id, input), onSuccess: stale }),
    // The deleted note's own query would 404 and flash "not found" before the page leaves; drop it first.
    remove: useMutation({ mutationFn: (id: string) => trackerApi.deleteNote(pid, id), onSuccess: (_d, id) => { qc.removeQueries({ queryKey: tk.note(pid, id) }); return stale() } }),
    link: useMutation({ mutationFn: ({ number, noteId }: { number: number; noteId: string }) => trackerApi.linkNote(pid, number, noteId), onSuccess: stale }),
    unlink: useMutation({ mutationFn: ({ number, noteId }: { number: number; noteId: string }) => trackerApi.unlinkNote(pid, number, noteId), onSuccess: stale }),
  }
}

export function useCommentMutations(pid: string, number: number) {
  const qc = useQueryClient()
  const stale = () => qc.invalidateQueries({ queryKey: tk.comments(pid, number) })
  return {
    create: useMutation({ mutationFn: (body: string) => trackerApi.createComment(pid, number, body), onSuccess: stale }),
    update: useMutation({ mutationFn: ({ id, body }: { id: string; body: string }) => trackerApi.updateComment(pid, number, id, body), onSuccess: stale }),
    remove: useMutation({ mutationFn: (id: string) => trackerApi.deleteComment(pid, number, id), onSuccess: stale }),
  }
}
