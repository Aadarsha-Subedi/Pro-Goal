import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { trackerError } from "./errors"

const files = import.meta.glob("../../../../backend/tracker/constants/error_codes.py", { query: "?raw", import: "default", eager: true }) as Record<string, string>

describe("tracker error codes", () => {
  it("are all mapped", () => {
    const source = Object.values(files)[0]
    if (!source) return
    const codes = [...source.matchAll(/^[A-Z_]+ = "([a-z_]+)"/gm)].map((m) => m[1])
    expect(codes.length).toBeGreaterThan(15)
    const unmapped = codes.filter((c) => trackerError(new ApiError(400, c, "x")) === "Something went wrong. Try again.")
    expect(unmapped).toEqual([])
  })
  it("lists the fields a forbidden patch touched", () => {
    const err = new ApiError(403, "fields_forbidden", "x", [{ field: "title", message: "no" }, { field: "due_date", message: "no" }])
    expect(trackerError(err)).toBe("You can't change: title, due_date. Nothing was saved.")
  })
})
