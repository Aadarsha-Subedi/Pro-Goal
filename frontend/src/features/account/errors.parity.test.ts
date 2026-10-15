import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { accountError } from "./errors"

const files = import.meta.glob(["../../../../backend/security/constants/error_codes.py", "../../../../backend/accounts/constants/error_codes.py"], { query: "?raw", import: "default", eager: true }) as Record<string, string>

// Every code the account pages can meet reads as a sentence, never the generic fallback.
describe("backend error codes", () => {
  it("are all mapped", () => {
    const source = Object.values(files).join("\n")
    if (!source) return // backend checkout not beside the frontend
    const codes = [...source.matchAll(/^[A-Z_]+ = "([a-z_]+)"/gm)].map((m) => m[1])
    expect(codes.length).toBeGreaterThan(15)
    expect(codes.filter((c) => accountError(new ApiError(400, c, "x")) === "Something went wrong. Try again.")).toEqual([])
  })
})
