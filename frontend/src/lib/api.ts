/**
 * Single API client. Session-cookie auth: every request sends credentials, every unsafe request
 * carries the CSRF token from the `csrftoken` cookie (fetched from GET /api/csrf/ when missing).
 * Responses use the backend envelope; failures throw ApiError carrying the stable `code`.
 */

import { clearSessionCache } from "@/lib/session-cache"

const BASE = import.meta.env.VITE_API_BASE

export interface FieldError {
  field: string | null
  message: string
}

interface Envelope<T> {
  success: boolean
  status_code: number
  message: string
  data?: T
  code?: string
  errors?: FieldError[]
  meta?: Record<string, unknown>
}

/** Pagination meta the backend adds to list responses. */
export interface PageMeta {
  count: number
  limit: number
  offset: number
  /** Task lists carry the server's UTC date so "overdue" never depends on the browser clock. */
  server_date?: string
  /** Activity feeds say whether the caller sees everything ("all") or only their own actions ("own"). */
  scope?: string
}

export interface Page<T> {
  items: T[]
  meta: PageMeta
}

let unauthorizedHandler: (() => void) | undefined
/** Called once when a data request answers 401 (the session ended). Auth endpoints are exempt. */
export function setUnauthorizedHandler(fn: (() => void) | undefined) {
  unauthorizedHandler = fn
}

export class ApiError extends Error {
  status: number
  code: string
  errors: FieldError[]
  /** Seconds to wait before retrying, from the `Retry-After` header of a 429. */
  retryAfter?: number
  constructor(status: number, code: string, message: string, errors: FieldError[] = [], retryAfter?: number) {
    super(message)
    this.status = status
    this.code = code
    this.errors = errors
    this.retryAfter = retryAfter
  }
  /** First message for a request field, e.g. fieldError("email"). */
  fieldError(field: string): string | undefined {
    return this.errors.find((e) => e.field === field)?.message
  }
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"])

export function readCookie(name: string, cookie: string = document.cookie): string | undefined {
  const match = cookie.split("; ").find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : undefined
}

async function ensureCsrf(fetcher: typeof fetch): Promise<string | undefined> {
  const existing = readCookie("csrftoken")
  if (existing) return existing
  await fetcher(`${BASE}/api/csrf/`, { credentials: "include" })
  return readCookie("csrftoken")
}

async function send<T>(method: string, path: string, body: unknown, fetcher: typeof fetch): Promise<Envelope<T> | undefined> {
  const headers: Record<string, string> = { Accept: "application/json" }
  const isForm = typeof FormData !== "undefined" && body instanceof FormData
  // A FormData body sets its own multipart boundary; JSON bodies are stringified.
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json"
  if (UNSAFE.has(method)) {
    const token = await ensureCsrf(fetcher)
    if (token) headers["X-CSRFToken"] = token
  }
  let res: Response
  try {
    res = await fetcher(`${BASE}${path}`, { method, headers, credentials: "include", body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body) })
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.")
  }
  let payload: Envelope<T> | undefined
  try {
    payload = (await res.json()) as Envelope<T>
  } catch {
    payload = undefined
  }
  if (!res.ok || payload?.success === false) {
    const code = payload?.code ?? (res.status === 429 ? "throttled" : res.status === 403 ? "forbidden" : "unknown_error")
    if (res.status === 401) clearSessionCache()
    if (res.status === 401 && !path.startsWith("/api/auth/") && path !== "/api/me/") unauthorizedHandler?.()
    const wait = Number(res.headers.get("Retry-After"))
    throw new ApiError(res.status, code, payload?.message ?? res.statusText, payload?.errors ?? [], Number.isFinite(wait) && wait > 0 ? wait : undefined)
  }
  // Anything that changes who is signed in or their profile makes the remembered session stale.
  if (UNSAFE.has(method) && (path.startsWith("/api/auth/") || path.startsWith("/api/me/"))) clearSessionCache()
  return payload
}

export async function request<T>(method: string, path: string, body?: unknown, fetcher: typeof fetch = fetch): Promise<T> {
  return (await send<T>(method, path, body, fetcher))?.data as T
}

/** List endpoints answer `{ data: { items }, meta: { count, limit, offset } }`. */
export async function requestPage<T>(path: string, fetcher: typeof fetch = fetch): Promise<Page<T>> {
  const payload = await send<{ items: T[] }>("GET", path, undefined, fetcher)
  const meta = (payload?.meta ?? {}) as Partial<PageMeta>
  const items = payload?.data?.items ?? []
  return { items, meta: { count: meta.count ?? items.length, limit: meta.limit ?? items.length, offset: meta.offset ?? 0, server_date: meta.server_date, scope: meta.scope } }
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  delete: <T>(path: string, body?: unknown) => request<T>("DELETE", path, body),
  page: <T>(path: string) => requestPage<T>(path),
}
