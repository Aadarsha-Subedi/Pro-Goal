import { describe, expect, it } from "vitest"
import type { ExploreProject } from "./api"
import { actionFor } from "./state"

const project = (state: ExploreProject["my_request"]["state"], until: string | null = null) =>
  ({ id: "p1", my_request: { state, cooldown_until: until } }) as ExploreProject

describe("actionFor", () => {
  const now = Date.parse("2026-10-10T12:00:00Z")
  it("pending waits", () => expect(actionFor(project("pending"), now).kind).toBe("pending"))
  it("a live cooldown locks the button", () => expect(actionFor(project("cooldown", "2026-10-11T00:00:00Z"), now)).toEqual({ kind: "cooldown", until: "2026-10-11T00:00:00Z" }))
  it("an expired cooldown allows a new request", () => expect(actionFor(project("cooldown", "2026-10-10T00:00:00Z"), now).kind).toBe("request"))
  it("demo projects are joined without a request", () => expect(actionFor({ ...project("none"), is_demo: true } as ExploreProject, now).kind).toBe("join"))
  it("everything else can request", () => expect(actionFor(project("none"), now).kind).toBe("request"))
})
