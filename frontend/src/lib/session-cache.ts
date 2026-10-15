/**
 * Short-lived memory of who the cookie belongs to. Route guards run on every navigation, so without
 * this each page change asks GET /api/me/ again. Only a successful answer is kept; any sign-in,
 * sign-out or profile change clears it (see `send` in api.ts), and so does a 401 on a data request.
 */
const TTL_MS = 30 * 60_000

let entry: { value: unknown; expires: number } | undefined
let inflight: Promise<unknown> | undefined

export function cachedSession<T>(load: () => Promise<T>, isCacheable: (value: T) => boolean): Promise<T> {
  if (entry && entry.expires > Date.now()) return Promise.resolve(entry.value as T)
  inflight ??= load()
    .then((value) => {
      if (isCacheable(value)) entry = { value, expires: Date.now() + TTL_MS }
      return value
    })
    .finally(() => {
      inflight = undefined
    })
  return inflight as Promise<T>
}

export function clearSessionCache() {
  entry = undefined
  inflight = undefined
}
