import { describe, expect, it } from "vitest"
import { ALL_EVENTS, summarizeEvents, toggleEvent } from "./events"

describe("events", () => {
  it("summarizes", () => {
    expect(summarizeEvents([])).toBe("No events")
    expect(summarizeEvents(ALL_EVENTS)).toBe(`All ${ALL_EVENTS.length} events`)
    expect(summarizeEvents(["task_created"])).toBe("1 event: Task created")
    expect(summarizeEvents(["task_created", "task_updated", "task_assigned", "comment_added"])).toBe("4 events: Task created, Task changed, Task assigned and 1 more")
  })
  it("toggles in catalog order without duplicates", () => {
    expect(toggleEvent(["comment_added"], "task_created", true)).toEqual(["task_created", "comment_added"])
    expect(toggleEvent(["task_created"], "task_created", true)).toEqual(["task_created"])
    expect(toggleEvent(["task_created", "comment_added"], "task_created", false)).toEqual(["comment_added"])
  })
  it("catalog has no duplicates", () => {
    expect(new Set(ALL_EVENTS).size).toBe(ALL_EVENTS.length)
  })
})
