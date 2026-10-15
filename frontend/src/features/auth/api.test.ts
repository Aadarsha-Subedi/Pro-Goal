import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { AuthError, toAuthError } from "./api"

describe("toAuthError", () => {
  it.each([
    ["invalid_credentials", 401, "invalid_credentials"],
    ["email_not_verified", 403, "email_not_verified"],
    ["verification_token_expired", 400, "link_expired"],
    ["verification_token_invalid", 400, "link_invalid"],
    ["reset_token_invalid", 400, "link_invalid"],
    ["google_token_invalid", 400, "google_failed"],
    ["throttled", 429, "rate_limited"],
    ["network_error", 0, "network"],
  ])("maps backend code %s to %s", (code, status, expected) => {
    expect(toAuthError(new ApiError(status, code, "m")).code).toBe(expected)
  })

  it("a lockout carries how long to wait", () => {
    const e = toAuthError(new ApiError(429, "login_locked", "m", [], 840))
    expect(e.code).toBe("locked")
    expect(e.retryAfter).toBe(840)
  })

  it("a disposable address is a form problem on the email field, not a lost connection", () => {
    const e = toAuthError(new ApiError(400, "disposable_email", "m", [{ field: "email", message: "Use your own address." }]))
    expect(e.code).toBe("validation")
    expect(e.fieldError("email")).toBe("Use your own address.")
  })

  it("any other 400 that names fields still shows them", () => {
    const e = toAuthError(new ApiError(400, "some_new_code", "m", [{ field: "email", message: "Nope." }]))
    expect(e.code).toBe("validation")
    expect(e.fieldError("email")).toBe("Nope.")
  })

  it("keeps field errors for validation failures", () => {
    const e = toAuthError(new ApiError(400, "validation_error", "m", [{ field: "email", message: "Bad email" }]))
    expect(e.code).toBe("validation")
    expect(e.fieldError("email")).toBe("Bad email")
  })

  it("is idempotent: converting an AuthError returns it unchanged", () => {
    const first = toAuthError(new ApiError(401, "invalid_credentials", "m"))
    expect(toAuthError(first)).toBe(first)
    expect(toAuthError(new AuthError("email_not_verified")).code).toBe("email_not_verified")
  })
})
