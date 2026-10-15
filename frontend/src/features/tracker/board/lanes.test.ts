import { describe, expect, it } from "vitest"
import type { Priority, Status, Task } from "../api"
import { buildLanes, movePatch, NONE, sortTasks } from "./lanes"

const mk = (n: number, over: Partial<Task> = {}): Task => ({
  id: `t${n}`, number: n, key: `A-${n}`, project: { id: "p", name: "P", task_key: "A" }, title: `Task ${n}`,
  status: { id: "s1", name: "To do", category: "todo" }, priority: { id: "p1", name: "Low", rank: 1 },
  start_date: null, due_date: null, is_overdue: false, parent_number: null, subtasks: { total: 0, done: 0 },
  assignees: [], tags: [], created_by: { id: "u", first_name: "U", avatar_url: null },
  created_at: `2026-10-0${n}T00:00:00Z`, updated_at: `2026-10-0${n}T00:00:00Z`, deleted_at: null, deletion_scheduled_for: null, ...over,
})
const statuses: Status[] = [{ id: "s1", name: "To do", category: "todo", position: 0, is_default: true }, { id: "s2", name: "Done", category: "done", position: 1, is_default: false }]
const priorities: Priority[] = [{ id: "p1", name: "Low", rank: 1, position: 0, is_default: true }, { id: "p2", name: "High", rank: 2, position: 1, is_default: false }]
const people = [{ id: "u1", name: "Maya" }, { id: "u2", name: "Sam" }]
const ctx = (tasks: Task[]) => ({ tasks, statuses, priorities, people })

describe("board lanes", () => {
  it("groups by status in position order, keeping empty lanes", () => {
    const lanes = buildLanes("status", "number", ctx([mk(1), mk(2, { status: { id: "s2", name: "Done", category: "done" } })]))
    expect(lanes.map((l) => [l.name, l.tasks.length])).toEqual([["To do", 1], ["Done", 1]])
  })
  it("lists priorities highest first", () => {
    expect(buildLanes("priority", "number", ctx([])).map((l) => l.name)).toEqual(["High", "Low"])
  })
  it("shows an assigned card in every assignee lane plus Unassigned", () => {
    const two = mk(1, { assignees: [{ id: "u1", first_name: "Maya", avatar_url: null }, { id: "u2", first_name: "Sam", avatar_url: null }] })
    const lanes = buildLanes("assignee", "number", ctx([two, mk(2)]))
    expect(lanes.map((l) => l.tasks.length)).toEqual([1, 1, 1])
    expect(lanes[2].id).toBe(NONE)
  })
  it("builds tag lanes from the tags in use", () => {
    const lanes = buildLanes("tag", "number", ctx([mk(1, { tags: ["bug"] }), mk(2)]))
    expect(lanes.map((l) => l.name)).toEqual(["#bug", "No tag"])
  })
  it("sorts by due date with undated last, and by priority high first", () => {
    const a = mk(1, { due_date: "2026-11-01" }); const b = mk(2); const c = mk(3, { due_date: "2026-10-05", priority: { id: "p2", name: "High", rank: 2 } })
    expect(sortTasks([a, b, c], "due_date").map((t) => t.number)).toEqual([3, 1, 2])
    expect(sortTasks([a, b, c], "priority")[0].number).toBe(3)
  })
})

describe("movePatch", () => {
  it("returns null for a drop on the same lane", () => expect(movePatch("status", mk(1), "s1", "s1")).toBeNull())
  it("moves status and priority by id", () => {
    expect(movePatch("status", mk(1), "s1", "s2")).toEqual({ status: "s2" })
    expect(movePatch("priority", mk(1), "p1", "p2")).toEqual({ priority: "p2" })
  })
  it("swaps one assignee for another and keeps the rest", () => {
    const t = mk(1, { assignees: [{ id: "u1", first_name: "M", avatar_url: null }, { id: "u3", first_name: "Z", avatar_url: null }] })
    expect(movePatch("assignee", t, "u1", "u2")).toEqual({ assignees: ["u3", "u2"] })
    expect(movePatch("assignee", t, "u1", NONE)).toEqual({ assignees: ["u3"] })
    expect(movePatch("assignee", mk(2), NONE, "u1")).toEqual({ assignees: ["u1"] })
  })
  it("swaps tags", () => {
    expect(movePatch("tag", mk(1, { tags: ["bug", "ui"] }), "bug", "ops")).toEqual({ tags: ["ui", "ops"] })
    expect(movePatch("tag", mk(1, { tags: ["bug"] }), "bug", NONE)).toEqual({ tags: [] })
  })
})
