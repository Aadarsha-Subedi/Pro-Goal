import { ApiError, api, type FieldError } from "@/lib/api"

/** Auth failures the screens react to. Anything else is shown as a generic message. */
export type AuthCode = "invalid_credentials" | "email_not_verified" | "rate_limited" | "locked" | "link_expired" | "link_invalid" | "validation" | "google_failed" | "network"

export class AuthError extends Error {
  code: AuthCode
  fields: FieldError[]
  /** Seconds until the account unlocks, when `code` is "locked". */
  retryAfter?: number
  constructor(code: AuthCode, fields: FieldError[] = [], retryAfter?: number) {
    super(code)
    this.code = code
    this.fields = fields
    this.retryAfter = retryAfter
  }
  fieldError(field: string) {
    return this.fields.find((f) => f.field === field)?.message
  }
}

/** Translate the backend's stable `code` into what the screens know how to show. */
export function toAuthError(err: unknown): AuthError {
  // Idempotent: authApi methods already convert, and pages convert again in their catch.
  if (err instanceof AuthError) return err
  if (!(err instanceof ApiError)) return new AuthError("network")
  switch (err.code) {
    case "invalid_credentials":
      return new AuthError("invalid_credentials")
    case "email_not_verified":
      return new AuthError("email_not_verified")
    case "verification_token_expired":
      return new AuthError("link_expired")
    case "verification_token_invalid":
    case "reset_token_invalid":
      return new AuthError("link_invalid")
    case "google_token_invalid":
    case "google_email_not_verified":
      return new AuthError("google_failed")
    case "validation_error":
    case "disposable_email": // a field problem with its own code; the message sits on the email field
      return new AuthError("validation", err.errors)
    case "network_error":
      return new AuthError("network")
    case "login_locked":
      return new AuthError("locked", [], err.retryAfter)
    default:
      if (err.status === 429 || err.code === "throttled") return new AuthError("rate_limited")
      // Any other 400 that names fields is a form problem, not a connection problem.
      if (err.status === 400 && err.errors.length > 0) return new AuthError("validation", err.errors)
      return new AuthError("network")
  }
}

async function run<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn()
  } catch (e) {
    throw toAuthError(e)
  }
}

export interface Me {
  id: string
  email: string
  first_name: string
  last_name: string
  display_name: string
  avatar_url?: string | null
  needs_profile?: boolean
  /** True once the walkthrough was finished or skipped. */
  tour_completed?: boolean
  /** Set while the account waits out its 7-day deletion grace period. */
  deletion_scheduled_for?: string | null
}

export const authApi = {
  login: (email: string, password: string, remember: boolean) => run(() => api.post("/api/auth/login/", { email, password, remember_me: remember })),
  google: (idToken: string, remember = false) => run(() => api.post("/api/auth/google/", { id_token: idToken, remember_me: remember })),
  signup: (d: { first: string; last: string; display: string; email: string; password: string }) =>
    run(() => api.post("/api/auth/signup/", { email: d.email, password: d.password, first_name: d.first, last_name: d.last, display_name: d.display })),
  verifyEmail: (token: string) => run(() => api.post("/api/auth/verify-email/", { token })),
  resendVerification: (email: string) => run(() => api.post("/api/auth/verify-email/resend/", { email })),
  requestReset: (email: string) => run(() => api.post("/api/auth/password/reset/", { email })),
  confirmReset: (uid: string, token: string, password: string) => run(() => api.post("/api/auth/password/reset/confirm/", { uid, token, new_password: password })),
  finishTour: () => run(() => api.post<Me>("/api/me/tour/", {})),
  completeProfile: (d: { first: string; last: string; display: string }) => run(() => api.patch("/api/me/", { first_name: d.first, last_name: d.last, display_name: d.display })),
  me: () => api.get<Me>("/api/me/"),
  logout: () => api.post("/api/auth/logout/", {}),
}
