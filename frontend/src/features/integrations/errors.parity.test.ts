import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { integrationError, slackReturn } from "./errors"

const files = import.meta.glob(["../../../../backend/integrations/constants/error_codes.py", "../../../../backend/integrations/slack/constants.py"], { query: "?raw", import: "default", eager: true }) as Record<string, string>

describe("backend error codes", () => {
  it("are all mapped", () => {
    const source = Object.values(files).join("\n")
    if (!source) return // backend checkout not beside the frontend
    const codes = [...source.matchAll(/^[A-Z_]+(?:_CODE)? = "([a-z_]+)"$/gm)].map((m) => m[1]).filter((c) => !c.includes("_") || /^[a-z_]+$/.test(c))
    const errorCodes = [...source.matchAll(/^[A-Z_]+ = "([a-z_]+)"$/gm)].map((m) => m[1]).filter((c) => /^(integrations_|unknown_|integration_|delivery_|invalid_|slack_|bot_|mapping_|duplicate_)/.test(c))
    expect(codes.length).toBeGreaterThan(8)
    const unmapped = errorCodes.filter((c) => integrationError(new ApiError(400, c, "x")) === "Something went wrong. Try again." && c !== "invalid_signature" && c !== "invalid_encryption_key")
    expect(unmapped).toEqual([])
  })
})

describe("slackReturn", () => {
  it("words each outcome", () => {
    expect(slackReturn("connected", undefined)?.kind).toBe("success")
    expect(slackReturn("linked", undefined)?.text).toContain("linked")
    expect(slackReturn("error", "access_denied")?.text).toContain("cancelled")
    expect(slackReturn("error", "weird")?.kind).toBe("error")
    expect(slackReturn(undefined, undefined)).toBeNull()
  })
})
