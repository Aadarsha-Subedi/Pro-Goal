import { describe, expect, it } from "vitest"
import { availableSteps, TOUR_STEPS } from "./steps"

// A stand-in page: each named target either has layout boxes or is hidden.
const page = (shown: Record<string, boolean>) => ({
  querySelector: (selector: string) => {
    const name = /data-tour="([^"]+)"/.exec(selector)?.[1] ?? ""
    return name in shown ? { getClientRects: () => (shown[name] ? [{}] : []) as unknown as DOMRectList } : null
  },
})

describe("availableSteps", () => {
  it("keeps only steps whose target is on screen", () => {
    const steps = availableSteps(page({ "nav-board": true, "nav-tasks": false, "nav-explore": true }))
    expect(steps.map((s) => s.target)).toEqual(["nav-board", "nav-explore"])
  })
  it("is empty when nothing is rendered", () => {
    expect(availableSteps(page({}))).toEqual([])
  })
  it("names every target once", () => {
    const names = TOUR_STEPS.map((s) => s.target)
    expect(new Set(names).size).toBe(names.length)
  })
})
