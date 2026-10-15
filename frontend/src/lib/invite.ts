/**
 * A join code that has to survive signup, email verification and sign-in (possibly in another tab), so it lives in
 * localStorage for up to a week. It is not a secret: the owner still approves every request.
 */
const KEY = "pg.invite"
const TTL_MS = 7 * 86_400_000

export function normalizeInviteCode(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 16)
}

export function saveInviteCode(raw: string): void {
  const code = normalizeInviteCode(raw)
  if (!code) return
  try {
    localStorage.setItem(KEY, JSON.stringify({ code, at: Date.now() }))
  } catch {
    // Storage blocked: the code still travels in the URL for this visit.
  }
}

export function peekInviteCode(now: number = Date.now()): string | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const { code, at } = JSON.parse(raw) as { code?: string; at?: number }
    if (!code || typeof at !== "number" || now - at > TTL_MS) {
      localStorage.removeItem(KEY)
      return null
    }
    return code
  } catch {
    return null
  }
}

/** Reads the pending code and forgets it, so the redirect to /join happens once. */
export function takeInviteCode(now: number = Date.now()): string | null {
  const code = peekInviteCode(now)
  try {
    localStorage.removeItem(KEY)
  } catch {
    // ignore
  }
  return code
}
