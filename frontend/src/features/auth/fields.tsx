import { useNavigate } from "@tanstack/react-router"
import { useEffect, useId, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Check, Circle, Eye, EyeSlash } from "@/icons"
import { GoogleMark } from "@/components/patterns/google-mark"
import { cn } from "@/lib/utils"
import { AuthError, authApi, toAuthError } from "./api"

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

interface GoogleId {
  accounts: { id: { initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void; renderButton: (el: HTMLElement, o: Record<string, unknown>) => void } }
}
const gis = () => (window as unknown as { google?: GoogleId }).google

// Google Identity Services (popup mode, used only to re-confirm identity) is initialized once per page;
// the active button's handler is swapped in.
let initialized = false
let activeHandler: ((idToken: string) => void) | null = null
const REDIRECT_PATH = "/api/auth/google/redirect/"
/** "<nonce>.<0|1>" (1 = remember me), set before leaving for Google. Google echoes it back as `state`. */
const STATE_COOKIE = "pg_google_state"

/**
 * Sends the whole page to Google's sign-in page. A plain navigation, so no blocker or iframe can get in the way.
 * Google posts the ID token to the backend, which checks the cookie against `state` and redirects back to /app.
 */
function signInWithGoogleRedirect(remember: boolean) {
  const nonce = crypto.randomUUID().replaceAll("-", "")
  const state = `${nonce}.${remember ? 1 : 0}`
  // SameSite=None because Google's reply is a cross-site POST. Secure is accepted on localhost too.
  document.cookie = `${STATE_COOKIE}=${state}; path=/; max-age=600; samesite=none; secure`
  const api = (import.meta.env.VITE_API_BASE || location.origin).replace(/\/$/, "")
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: api + REDIRECT_PATH,
    response_type: "id_token",
    response_mode: "form_post",
    scope: "openid email profile",
    nonce,
    state,
    prompt: "select_account",
  })
  location.assign(`https://accounts.google.com/o/oauth2/v2/auth?${params}`)
}

function loadGis(): Promise<GoogleId> {
  return new Promise((resolve, reject) => {
    const ready = gis()
    if (ready) return resolve(ready)
    const existing = document.querySelector<HTMLScriptElement>("script[data-gis]")
    const script = existing ?? Object.assign(document.createElement("script"), { src: "https://accounts.google.com/gsi/client", async: true })
    script.dataset.gis = "1"
    script.addEventListener("load", () => resolve(gis()!), { once: true })
    script.addEventListener("error", () => reject(new Error("gis")), { once: true })
    if (!existing) document.head.appendChild(script)
  })
}

/**
 * Our own Google button (outline Button, Google mark, our copy and focus ring). Sign-in and sign-up send the whole
 * page to Google and come back through /api/auth/google/redirect/ (see signInWithGoogleRedirect). With onCredential
 * it re-confirms identity in place instead: Google's official button is rendered on top at near-zero opacity, and its
 * popup returns an ID token to the caller. Without VITE_GOOGLE_CLIENT_ID it shows disabled.
 */
export function GoogleButton({ children = "Continue with Google", remember = false, onError, onCredential }: { children?: string; remember?: boolean; onError?: (code: AuthError["code"]) => void; /** Receive the ID token instead of signing in (used to re-confirm identity for sensitive actions). */ onCredential?: (idToken: string) => void | Promise<void> }) {
  const host = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const [failed, setFailed] = useState(false)
  // Several buttons can be on one page (landing hero and close): the one being used owns the callback.
  const handle = useRef<(idToken: string) => void>(() => {})
  handle.current = async (token) => {
    if (onCredential) return void (await onCredential(token))
    try {
      await authApi.google(token, remember)
      navigate({ to: "/app" })
    } catch (e) {
      onError?.(toAuthError(e).code)
    }
  }
  const claim = () => {
    activeHandler = (t) => handle.current(t)
  }

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !onCredential) return
    let live = true
    loadGis()
      .then((g) => {
        if (!live || !host.current) return
        claim()
        if (!initialized) {
          g.accounts.id.initialize({ client_id: GOOGLE_CLIENT_ID, callback: (r) => activeHandler?.(r.credential) })
          initialized = true
        }
        host.current.innerHTML = ""
        g.accounts.id.renderButton(host.current, { type: "standard", theme: "outline", size: "medium", locale: "en", width: host.current.offsetWidth || 320, text: children.startsWith("Sign up") ? "signup_with" : "continue_with" })
        // Google localizes the hidden button's accessible name; give it our English label instead.
        for (const ms of [0, 300, 1200]) {
          setTimeout(() => {
            const frame = host.current?.querySelector("iframe")
            if (frame) {
              frame.title = children
              frame.setAttribute("aria-label", children)
            }
            // The focusable node GIS renders in our DOM takes its name from Google's session language.
            const stop = host.current?.querySelector<HTMLElement>("[role=button]")
            if (stop) {
              stop.setAttribute("aria-label", children)
              stop.removeAttribute("aria-labelledby")
              stop.lang = "en"
              for (const span of stop.querySelectorAll("span")) span.setAttribute("aria-hidden", "true")
            }
          }, ms)
        }
      })
      .catch(() => live && setFailed(true))
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [children])

  if (GOOGLE_CLIENT_ID && !onCredential) {
    return <Button type="button" variant="outline" className="w-full" onClick={() => signInWithGoogleRedirect(remember)} icon={<GoogleMark />}>{children}</Button>
  }
  if (GOOGLE_CLIENT_ID && !failed) {
    return (
      <div className="group focus-within:ring-ring/60 relative h-(--ctl-h) w-full rounded-md focus-within:ring-[3px]" onPointerEnter={claim} onFocusCapture={claim}>
        <Button type="button" variant="outline" tabIndex={-1} aria-hidden className="pointer-events-none w-full group-hover:bg-muted" icon={<GoogleMark />}>{children}</Button>
        <div ref={host} className="absolute inset-0 overflow-hidden rounded-md opacity-0" aria-label={children} />
      </div>
    )
  }
  return (
    <div className="space-y-1.5">
      <Button type="button" variant="outline" className="w-full" disabled aria-describedby="google-off" icon={<GoogleMark />}>{children}</Button>
      <p id="google-off" className="text-sm bp-muted">{failed ? "Couldn't load Google sign-in." : "Google sign-in isn't set up yet."}{onCredential ? " Use your password." : " Use your email below."}</p>
    </div>
  )
}

export function OrDivider() {
  return (
    <p className="bp-dim" role="separator">
      <span className="bp-dim-rule" />
      <span className="px-1">or</span>
      <span className="bp-dim-rule" />
    </p>
  )
}

export function TextField({ label, hint, error, ...props }: React.ComponentProps<typeof Input> & { label: string; hint?: string; error?: string }) {
  const id = useId()
  return (
    <Field data-invalid={error ? true : undefined}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-e` : hint ? `${id}-h` : undefined} {...props} />
      {error ? <FieldError id={`${id}-e`}>{error}</FieldError> : hint ? <FieldDescription id={`${id}-h`}>{hint}</FieldDescription> : null}
    </Field>
  )
}

export const PASSWORD_RULES = [
  { id: "len", label: "At least 10 characters", test: (v: string) => v.length >= 10 },
  { id: "case", label: "An upper and a lower case letter", test: (v: string) => /[a-z]/.test(v) && /[A-Z]/.test(v) },
  { id: "common", label: "Not a common password or part of your email", test: (v: string) => v.length >= 10 && /[a-z]/.test(v) && /[A-Z]/.test(v) && !/^(password|qwerty|letmein|12345)/i.test(v) },
] as const

/** The first rule still failing, as a sentence to show next to the field. */
export function passwordProblem(v: string): string | undefined {
  if (v.length < 10) return "Use at least 10 characters."
  if (!(/[a-z]/.test(v) && /[A-Z]/.test(v))) return "Add an upper case and a lower case letter."
  if (!PASSWORD_RULES[2].test(v)) return "Choose a less common password."
  return undefined
}

export const passwordOk = (v: string) => PASSWORD_RULES.every((r) => r.test(v))

export function PasswordField({ label = "Password", value, onChange, showRules = false, error, autoComplete = "new-password" }: { label?: string; value: string; onChange: (v: string) => void; showRules?: boolean; error?: string; autoComplete?: string }) {
  const id = useId()
  const [show, setShow] = useState(false)
  const [active, setActive] = useState(false)
  const expanded = showRules && (active || value.length > 0)
  const describedBy = [error ? `${id}-e` : null, showRules ? `${id}-rules` : null].filter(Boolean).join(" ") || undefined
  return (
    <Field data-invalid={error ? true : undefined}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <div className="relative">
        <Input id={id} type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)} onFocus={() => setActive(true)} autoComplete={autoComplete} className="pr-10" aria-invalid={!!error} aria-describedby={describedBy} />
        <Button type="button" variant="ghost" size="icon-xs" label={show ? "Hide password" : "Show password"} className="absolute inset-y-0 right-1.5 my-auto" onClick={() => setShow(!show)}>
          {show ? <EyeSlash /> : <Eye />}
        </Button>
      </div>
      {error && <FieldError id={`${id}-e`}>{error}</FieldError>}
      {showRules && !expanded && <p id={`${id}-rules`} className="text-sm bp-muted">10 or more characters, with upper and lower case letters.</p>}
      {showRules && expanded && (
        <ul id={`${id}-rules`} className="space-y-1 text-sm" aria-live="polite">
          {PASSWORD_RULES.map((r) => {
            const ok = r.test(value)
            return (
              <li key={r.id} className={cn("flex items-center gap-1.5", ok ? "text-success-text" : "bp-muted")}>
                {ok ? <Check weight="bold" className="size-3.5 text-success" aria-label="Met" /> : <Circle className="size-3.5" aria-label="Not met" />}
                {r.label}
              </li>
            )
          })}
        </ul>
      )}
    </Field>
  )
}

/** After a failed submit, move focus to the first invalid control so keyboard and screen reader users land on the error. */
export function focusFirstError(form: Element | null) {
  requestAnimationFrame(() => form?.querySelector<HTMLElement>("[aria-invalid=true]")?.focus())
}

export const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
