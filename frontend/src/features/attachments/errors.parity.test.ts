import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { attachmentError } from "./errors"

const files = import.meta.glob("../../../../backend/attachments/constants/error_codes.py", { query: "?raw", import: "default", eager: true }) as Record<string, string>

describe("attachment error codes", () => {
  it("are all mapped", () => {
    const source = Object.values(files)[0]
    if (!source) return
    const codes = [...source.matchAll(/^[A-Z_]+ = "([a-z_]+)"/gm)].map((m) => m[1])
    expect(codes.length).toBeGreaterThan(10)
    const unmapped = codes.filter((c) => attachmentError(new ApiError(400, c, "x")) === "Something went wrong. Try again.")
    expect(unmapped).toEqual([])
  })
})
