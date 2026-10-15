import { describe, expect, it } from "vitest"
import type { Integration } from "./api"
import { pickCurrent } from "./integrations-page"

const row = (id: string, status: Integration["status"], created_at: string, provider = "slack") => ({ id, provider, status, created_at }) as Integration

describe("pickCurrent", () => {
  it("prefers the live row over an older disconnected one", () => {
    expect(pickCurrent([row("old", "disconnected", "2026-10-09"), row("new", "active", "2026-10-10")], "slack")?.id).toBe("new")
  })
  it("falls back to the newest disconnected row", () => {
    expect(pickCurrent([row("a", "disconnected", "2026-10-08"), row("b", "disconnected", "2026-10-09")], "slack")?.id).toBe("b")
  })
  it("ignores other providers and empty lists", () => {
    expect(pickCurrent([row("x", "active", "2026-10-10", "other")], "slack")).toBeUndefined()
    expect(pickCurrent([], "slack")).toBeUndefined()
  })
})
