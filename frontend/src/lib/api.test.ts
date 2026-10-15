import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError, readCookie, request } from "./api"

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })

describe("readCookie", () => {
  it("reads and decodes a named cookie", () => {
    expect(readCookie("csrftoken", "a=1; csrftoken=abc%20d; b=2")).toBe("abc d")
    expect(readCookie("missing", "a=1")).toBeUndefined()
  })
})

describe("request", () => {
  it("returns data from the envelope and sends credentials", async () => {
    const fetcher = vi.fn().mockResolvedValue(json(200, { success: true, status_code: 200, message: "ok", data: { id: 1 } }))
    await expect(request("GET", "/api/me/", undefined, fetcher)).resolves.toEqual({ id: 1 })
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: "GET", credentials: "include" })
  })

  it("throws ApiError with the stable code and field errors", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      json(400, { success: false, status_code: 400, message: "Validation failed.", code: "validation_error", errors: [{ field: "email", message: "Enter a valid email." }] }),
    )
    const err = (await request("GET", "/x", undefined, fetcher).catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe("validation_error")
    expect(err.fieldError("email")).toBe("Enter a valid email.")
  })

  it("maps a throttled response without a body to a stable code", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("", { status: 429 }))
    await expect(request("GET", "/x", undefined, fetcher)).rejects.toMatchObject({ status: 429, code: "throttled" })
  })

  it("reports a network failure as network_error", async () => {
    const fetcher = vi.fn().mockRejectedValue(new TypeError("fail"))
    await expect(request("GET", "/x", undefined, fetcher)).rejects.toMatchObject({ status: 0, code: "network_error" })
  })
})

describe("CSRF", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("sends X-CSRFToken from the cookie on unsafe methods", async () => {
    vi.stubGlobal("document", { cookie: "csrftoken=tok123" })
    const fetcher = vi.fn().mockResolvedValue(json(200, { success: true, status_code: 200, message: "ok", data: null }))
    await request("POST", "/api/auth/login/", { a: 1 }, fetcher)
    expect(fetcher.mock.calls[0][1].headers["X-CSRFToken"]).toBe("tok123")
    expect(fetcher.mock.calls[0][1].body).toBe('{"a":1}')
  })

  it("fetches /api/csrf/ first when the cookie is missing", async () => {
    let cookie = ""
    vi.stubGlobal("document", { get cookie() { return cookie } })
    const fetcher = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("/api/csrf/")) cookie = "csrftoken=fresh"
      return json(200, { success: true, status_code: 200, message: "ok", data: null })
    })
    await request("POST", "/api/auth/logout/", undefined, fetcher)
    expect(fetcher.mock.calls[0][0]).toContain("/api/csrf/")
    expect(fetcher.mock.calls[1][1].headers["X-CSRFToken"]).toBe("fresh")
  })

  it("does not send a CSRF token on GET", async () => {
    const fetcher = vi.fn().mockResolvedValue(json(200, { success: true, status_code: 200, message: "ok", data: null }))
    await request("GET", "/api/me/", undefined, fetcher)
    expect(fetcher.mock.calls[0][1].headers["X-CSRFToken"]).toBeUndefined()
  })
})
