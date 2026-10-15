import { describe as suite, expect, it } from "vitest"
import type { ActivityEntry } from "./api"
import { describe, fieldDetails, KNOWN_ACTIONS } from "./describe"

const files = import.meta.glob("../../../../backend/*/constants/actions.py", { query: "?raw", import: "default", eager: true }) as Record<string, string>

const entry = (action: string, changes: Record<string, unknown> = {}, entity_type = "task", entity_id: string | null = "id1"): ActivityEntry => ({
  id: "1", actor: { id: "u", first_name: "Sam", avatar_url: null }, action, entity_type, entity_id, changes, created_at: "2026-10-10T10:00:00Z",
})

suite("activity describe", () => {
  it("names every action the backend can write", () => {
    const source = Object.values(files).join("\n")
    if (!source) return // backend checkout not beside the frontend
    const actions = [...source.matchAll(/^[A-Z_]+ = "([a-z_]+\.[a-z_]+)"/gm)].map((m) => m[1])
    expect(actions.length).toBeGreaterThan(30)
    expect(actions.filter((a) => !KNOWN_ACTIONS.includes(a))).toEqual([])
  })
  it("writes a task created sentence with its key and a link", () => {
    const d = describe(entry("task.created", { number: 4, title: "Audit probe" }), "PMS")
    expect(d.verb).toBe("created PMS-4 Audit probe")
    expect(d.link).toEqual({ kind: "task", number: 4 })
  })
  it("turns from and to pairs into details", () => {
    const d = describe(entry("task.updated", { status: { from: "In progress", to: "To do" }, tags: { from: [], to: ["a", "b"] } }), "PMS")
    expect(d.details).toEqual([{ field: "Status", from: "In progress", to: "To do" }, { field: "Tags", from: "none", to: "a, b" }])
  })
  it("lists added and removed permissions and mapped events", () => {
    expect(fieldDetails({ added: ["task.create"], removed: ["task.delete", "note.create"] })).toEqual([{ field: "Added", note: "task.create" }, { field: "Removed", note: "task.delete, note.create" }])
    expect(fieldDetails({ channel: "dev", events: ["task_created"] })).toEqual([{ field: "Events", note: "task_created" }])
  })
  it("marks changed bodies without showing text", () => {
    expect(fieldDetails({ body: { changed: true } })).toEqual([{ field: "Body", note: "changed" }])
  })
  it("links a comment to its task and a note to its page, but not a deleted note", () => {
    expect(describe(entry("comment.created", { task: 2 }, "comment"), "PMS").link).toEqual({ kind: "task", number: 2 })
    expect(describe(entry("note.updated", { body: { changed: true } }, "note", "n1"), "PMS").link).toEqual({ kind: "note", id: "n1" })
    expect(describe(entry("note.deleted", { title: "x" }, "note", "n1"), "PMS").link).toBeUndefined()
  })
  it("still reads an unknown action as words", () => {
    expect(describe(entry("widget.exploded"), "PMS").verb).toBe("widget exploded")
  })
})
