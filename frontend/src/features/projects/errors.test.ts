import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { isNotFound, projectError, projectErrorCode } from "./errors"

describe("projectError", () => {
  it("maps stable codes to plain messages", () => {
    expect(projectError(new ApiError(404, "invalid_join_code", "x"))).toMatch(/No project uses this code/)
    expect(projectError(new ApiError(403, "reauth_failed", "x"))).toMatch(/password/)
  })
  it("treats 429 as throttled whatever the code", () => {
    expect(projectError(new ApiError(429, "unknown", "x"))).toMatch(/Too many/)
  })
  it("falls back for unknown codes and non-API errors", () => {
    expect(projectError(new ApiError(500, "weird", "x"))).toBe("Something went wrong. Try again.")
    expect(projectError(new Error("boom"))).toBe("Something went wrong. Try again.")
    expect(projectErrorCode(new Error("boom"))).toBe("unknown_error")
  })
  it("detects 404", () => {
    expect(isNotFound(new ApiError(404, "project_not_found", "x"))).toBe(true)
    expect(isNotFound(new ApiError(403, "owner_only", "x"))).toBe(false)
  })
})
