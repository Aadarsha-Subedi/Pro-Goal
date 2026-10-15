import { describe, expect, it } from "vitest"
import { daysUntil, formatPlainDate, initials, plural, suggestTaskKey, waitText } from "./format"

describe("format", () => {
  it("words a wait time", () => {
    expect(waitText(20)).toBe("under a minute")
    expect(waitText(60)).toBe("1 minute")
    expect(waitText(840)).toBe("about 14 minutes")
    expect(waitText(3600)).toBe("1 hour")
    expect(waitText(7300)).toBe("about 3 hours")
  })
  it("builds initials", () => {
    expect(initials("Maya Chen")).toBe("MC")
    expect(initials("maya")).toBe("M")
    expect(initials("")).toBe("?")
  })
  it("does not shift plain dates across time zones", () => {
    expect(formatPlainDate("2026-10-10")).toContain("10")
    expect(formatPlainDate(null)).toBe("")
  })
  it("counts days up to a deadline", () => {
    const now = Date.parse("2026-10-10T00:00:00Z")
    expect(daysUntil("2026-10-17T00:00:00Z", now)).toBe(7)
    expect(daysUntil("2026-10-01T00:00:00Z", now)).toBe(0)
  })
  it("pluralizes", () => {
    expect(plural(1, "member")).toBe("1 member")
    expect(plural(3, "member")).toBe("3 members")
  })
  it("suggests task keys", () => {
    expect(suggestTaskKey("Project Management System")).toBe("PMS")
    expect(suggestTaskKey("Apollo")).toBe("APOLL")
    expect(suggestTaskKey("123")).toBe("")
  })
})
