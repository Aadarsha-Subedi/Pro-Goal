import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/lib/api"
import { UploadError, type Attachment } from "./api"
import { runUpload, type Deps, type UploadState } from "./pipeline"

const att = (status: Attachment["status"]): Attachment => ({ id: "a1", filename: "a.png", content_type: "image/png", category: "image", size_bytes: 3, status, target: { type: "task", id: "1" }, uploaded_by: { id: "u", first_name: "U", avatar_url: null }, created_at: "" })
const ticket = { attachment: att("pending"), upload: { method: "PUT" as const, url: "https://s", headers: { "Content-Type": "image/png" }, expires_at: "" } }
const file = new File(["abc"], "a.png", { type: "image/png" })

function deps(over: Partial<Deps> = {}): Deps {
  return { requestUpload: vi.fn().mockResolvedValue(ticket), put: vi.fn(async (_t, _f, p) => p(1)), confirm: vi.fn().mockResolvedValue(att("ready")), get: vi.fn().mockResolvedValue(att("ready")), wait: vi.fn().mockResolvedValue(undefined), ...over }
}
async function run(d: Deps, f: File = file, signal = new AbortController().signal) {
  const seen: UploadState[] = []
  await runUpload("p", { type: "task", id: 1 }, f, "u1", (s) => seen.push(s), signal, d)
  return seen
}

describe("upload pipeline", () => {
  it("goes through uploading and confirming to done", async () => {
    const seen = await run(deps())
    expect(seen.map((s) => s.phase)).toContain("uploading")
    expect(seen.at(-1)?.phase).toBe("done")
  })
  it("polls an image that is still processing", async () => {
    const d = deps({ confirm: vi.fn().mockResolvedValue(att("processing")), get: vi.fn().mockResolvedValueOnce(att("processing")).mockResolvedValue(att("ready")) })
    const seen = await run(d)
    expect(seen.some((s) => s.phase === "processing")).toBe(true)
    expect(seen.at(-1)?.phase).toBe("done")
    expect(d.get).toHaveBeenCalledTimes(2)
    expect(d.get).toHaveBeenCalledWith("p", { type: "task", id: 1 }, "a1")
  })
  it("refuses a bad file before any request", async () => {
    const d = deps()
    const seen = await run(d, new File(["x"], "a.svg", { type: "image/svg+xml" }))
    expect(seen.at(-1)?.phase).toBe("failed")
    expect(d.requestUpload).not.toHaveBeenCalled()
  })
  it("reports a server refusal in plain words", async () => {
    const seen = await run(deps({ requestUpload: vi.fn().mockRejectedValue(new ApiError(409, "project_quota_exceeded", "x")) }))
    expect(seen.at(-1)).toMatchObject({ phase: "failed", error: expect.stringMatching(/out of file storage/) })
  })
  it("explains unreachable storage", async () => {
    const seen = await run(deps({ put: vi.fn().mockRejectedValue(new UploadError("storage_unreachable", 0)) }))
    expect(seen.at(-1)?.error).toMatch(/CORS/)
  })
  it("marks an aborted upload as cancelled, not failed", async () => {
    const ac = new AbortController()
    const d = deps({ put: vi.fn(async () => { ac.abort(); throw new UploadError("cancelled", 0) }) })
    const seen = await run(d, file, ac.signal)
    expect(seen.at(-1)?.phase).toBe("cancelled")
  })
})
