import { beforeEach, describe, expect, it } from "vitest"
import { normalizeInviteCode, peekInviteCode, saveInviteCode, takeInviteCode } from "./invite"

const store = new Map<string, string>()
beforeEach(() => {
  store.clear()
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v), removeItem: (k: string) => void store.delete(k) },
  })
})

describe("invite code", () => {
  it("normalizes", () => {
    expect(normalizeInviteCode(" ab-c12 3 ")).toBe("ABC123")
  })
  it("is kept until taken, then forgotten", () => {
    saveInviteCode("abc123")
    expect(peekInviteCode()).toBe("ABC123")
    expect(takeInviteCode()).toBe("ABC123")
    expect(peekInviteCode()).toBeNull()
  })
  it("expires after a week", () => {
    saveInviteCode("abc123")
    expect(peekInviteCode(Date.now() + 8 * 86_400_000)).toBeNull()
  })
  it("ignores empty input", () => {
    saveInviteCode("  ")
    expect(peekInviteCode()).toBeNull()
  })
})
