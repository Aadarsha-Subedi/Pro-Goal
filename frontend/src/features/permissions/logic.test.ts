import { describe, expect, it } from "vitest"
import type { Registry } from "@/features/projects/api"
import { applyPreset, cellState, diffGrants, groupCounts, holds, presetFor, toggle } from "./logic"

const registry: Registry = {
  groups: ["Tasks", "Notes"],
  permissions: [
    { code: "task.create", label: "Create tasks", description: "", group: "Tasks" },
    { code: "task.delete", label: "Delete tasks", description: "", group: "Tasks" },
    { code: "note.create", label: "Create notes", description: "", group: "Notes" },
  ],
  presets: [
    { name: "viewer", label: "Viewer", description: "", permissions: [] },
    { name: "contributor", label: "Contributor", description: "", permissions: ["task.create", "note.create"] },
  ],
  owner_only: [],
}

describe("grants logic", () => {
  it("owner holds every registered code, others only their grants", () => {
    expect(holds({ role: "owner", permissions: [] }, registry, "task.delete")).toBe(true)
    expect(holds({ role: "member", permissions: ["task.create"] }, registry, "task.delete")).toBe(false)
  })
  it("diffs added and removed", () => {
    expect(diffGrants(["a", "b"], ["b", "c"])).toEqual({ added: ["c"], removed: ["a"] })
    expect(diffGrants(["a"], ["a"])).toEqual({ added: [], removed: [] })
  })
  it("names a preset only on an exact match", () => {
    expect(presetFor(["note.create", "task.create"], registry.presets)?.name).toBe("contributor")
    expect(presetFor(["task.create"], registry.presets)).toBeNull()
    expect(presetFor([], registry.presets)?.name).toBe("viewer")
  })
  it("a preset leaves codes the actor cannot change alone", () => {
    const viewer = registry.presets[0]
    const next = applyPreset(["task.create", "task.delete"], viewer, (c) => c !== "task.delete", registry)
    expect(next).toEqual(["task.delete"])
  })
  it("toggles without duplicating", () => {
    expect(toggle(["a"], "a", true)).toEqual(["a"])
    expect(toggle(["a"], "a", false)).toEqual([])
  })
  it("counts per group and derives cell state", () => {
    const counts = groupCounts(["task.create"], registry)
    expect(counts).toEqual([{ group: "Tasks", held: 1, total: 2 }, { group: "Notes", held: 0, total: 1 }])
    expect(counts.map(cellState)).toEqual(["some", "none"])
    expect(cellState({ held: 1, total: 1 })).toBe("all")
  })
})
