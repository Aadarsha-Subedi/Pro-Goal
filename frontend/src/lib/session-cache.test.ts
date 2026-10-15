import { beforeEach, describe, expect, it, vi } from "vitest"
import { cachedSession, clearSessionCache } from "./session-cache"

describe("cachedSession", () => {
  beforeEach(() => clearSessionCache())

  it("asks once while a signed-in answer is fresh", async () => {
    const load = vi.fn().mockResolvedValue({ status: "signed-in" })
    const ok = (s: { status: string }) => s.status === "signed-in"
    await cachedSession(load, ok)
    await cachedSession(load, ok)
    expect(load).toHaveBeenCalledTimes(1)
  })

  it("never keeps an anonymous answer", async () => {
    const load = vi.fn().mockResolvedValue({ status: "anonymous" })
    const ok = (s: { status: string }) => s.status === "signed-in"
    await cachedSession(load, ok)
    await cachedSession(load, ok)
    expect(load).toHaveBeenCalledTimes(2)
  })

  it("asks again after the cache is cleared", async () => {
    const load = vi.fn().mockResolvedValue({ status: "signed-in" })
    const ok = (s: { status: string }) => s.status === "signed-in"
    await cachedSession(load, ok)
    clearSessionCache()
    await cachedSession(load, ok)
    expect(load).toHaveBeenCalledTimes(2)
  })

  it("shares one request between simultaneous callers", async () => {
    const load = vi.fn().mockResolvedValue({ status: "signed-in" })
    const ok = (s: { status: string }) => s.status === "signed-in"
    await Promise.all([cachedSession(load, ok), cachedSession(load, ok)])
    expect(load).toHaveBeenCalledTimes(1)
  })
})
