import { describe, expect, it } from "vitest"
import { checkFile, declaredType, formatBytes } from "./limits"

describe("attachment limits", () => {
  it("accepts allowed types within their limit", () => {
    expect(checkFile({ name: "a.png", type: "image/png", size: 1000 })).toMatchObject({ ok: true, category: "image" })
  })
  it("infers the type from the extension when the browser gives none", () => {
    expect(declaredType({ name: "notes.TXT", type: "" })).toBe("text/plain")
    expect(declaredType({ name: "x.bin", type: "" })).toBe("")
  })
  it("refuses svg, html and unknown types", () => {
    expect(checkFile({ name: "a.svg", type: "image/svg+xml", size: 10 }).ok).toBe(false)
    expect(checkFile({ name: "a.html", type: "text/html", size: 10 }).ok).toBe(false)
  })
  it("enforces per-category sizes and empty files", () => {
    const MB = 1024 * 1024
    expect(checkFile({ name: "a.png", type: "image/png", size: 5 * MB + 1 }).ok).toBe(false)
    expect(checkFile({ name: "a.pdf", type: "application/pdf", size: 10 * MB }).ok).toBe(true)
    expect(checkFile({ name: "a.mp3", type: "audio/mpeg", size: 20 * MB + 1 }).ok).toBe(false)
    expect(checkFile({ name: "a.txt", type: "text/plain", size: 0 }).ok).toBe(false)
  })
  it("formats sizes", () => {
    expect(formatBytes(512)).toBe("512 B")
    expect(formatBytes(1536)).toBe("1.5 KB")
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB")
    expect(formatBytes(1024 * 1024 * 1024)).toBe("1 GB")
  })
})
