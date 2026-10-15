import type { BoardGroup, BoardSort, Priority, Status, Task } from "../api"

export interface Lane {
  /** Status or priority id, user id, or a tag name. `none` is the catch-all lane (Unassigned, No tag). */
  id: string
  name: string
  tasks: Task[]
}

export const NONE = "__none__"

interface Inputs {
  tasks: Task[]
  statuses: Status[]
  priorities: Priority[]
  people: { id: string; name: string }[]
}

export function sortTasks(tasks: Task[], by: BoardSort): Task[] {
  const dueKey = (t: Task) => t.due_date ?? "9999-12-31"
  const cmp: Record<BoardSort, (a: Task, b: Task) => number> = {
    number: (a, b) => a.number - b.number,
    title: (a, b) => a.title.localeCompare(b.title),
    due_date: (a, b) => dueKey(a).localeCompare(dueKey(b)) || a.number - b.number,
    priority: (a, b) => b.priority.rank - a.priority.rank || a.number - b.number,
    created_at: (a, b) => b.created_at.localeCompare(a.created_at),
    updated_at: (a, b) => b.updated_at.localeCompare(a.updated_at),
  }
  return [...tasks].sort(cmp[by])
}

/** Lanes for one grouping. An assignee grouping lists a card in every assignee's lane. */
export function buildLanes(group: BoardGroup, sortBy: BoardSort, { tasks, statuses, priorities, people }: Inputs): Lane[] {
  const sorted = sortTasks(tasks, sortBy)
  if (group === "status") return statuses.slice().sort((a, b) => a.position - b.position).map((s) => ({ id: s.id, name: s.name, tasks: sorted.filter((t) => t.status.id === s.id) }))
  if (group === "priority") return priorities.slice().sort((a, b) => b.rank - a.rank).map((p) => ({ id: p.id, name: p.name, tasks: sorted.filter((t) => t.priority.id === p.id) }))
  if (group === "assignee") {
    const lanes = people.map((p) => ({ id: p.id, name: p.name, tasks: sorted.filter((t) => t.assignees.some((a) => a.id === p.id)) }))
    return [...lanes, { id: NONE, name: "Unassigned", tasks: sorted.filter((t) => t.assignees.length === 0) }]
  }
  const tags = [...new Set(tasks.flatMap((t) => t.tags))].sort()
  return [...tags.map((tag) => ({ id: tag, name: `#${tag}`, tasks: sorted.filter((t) => t.tags.includes(tag)) })), { id: NONE, name: "No tag", tasks: sorted.filter((t) => t.tags.length === 0) }]
}

export const GROUP_PERMISSION: Record<BoardGroup, string> = {
  status: "task.status.change",
  priority: "task.priority.change",
  assignee: "task.assignees.change",
  tag: "task.tags.change",
}

/** The PATCH body that moves a card from one lane to another, or null when nothing changes. */
export function movePatch(group: BoardGroup, task: Task, from: string, to: string): Record<string, unknown> | null {
  if (from === to) return null
  if (group === "status") return { status: to }
  if (group === "priority") return { priority: to }
  if (group === "assignee") {
    const ids = task.assignees.map((a) => a.id).filter((id) => id !== from)
    if (to !== NONE && !ids.includes(to)) ids.push(to)
    return { assignees: ids }
  }
  const tags = task.tags.filter((t) => t !== from)
  if (to !== NONE && !tags.includes(to)) tags.push(to)
  return { tags }
}

/** The same card as the screen should show it before the server answers. */
export function applyMove(task: Task, group: BoardGroup, patch: Record<string, unknown>, ctx: { statuses: Status[]; priorities: Priority[]; people: { id: string; name: string }[] }): Task {
  if (group === "status") {
    const s = ctx.statuses.find((x) => x.id === patch.status)
    return s ? { ...task, status: { id: s.id, name: s.name, category: s.category } } : task
  }
  if (group === "priority") {
    const p = ctx.priorities.find((x) => x.id === patch.priority)
    return p ? { ...task, priority: { id: p.id, name: p.name, rank: p.rank } } : task
  }
  if (group === "assignee") {
    const ids = patch.assignees as string[]
    return { ...task, assignees: ids.map((id) => task.assignees.find((a) => a.id === id) ?? { id, first_name: ctx.people.find((p) => p.id === id)?.name ?? "", avatar_url: null }) }
  }
  return { ...task, tags: patch.tags as string[] }
}
