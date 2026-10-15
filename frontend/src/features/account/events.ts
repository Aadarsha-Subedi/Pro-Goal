import type { PhosphorIcon } from "@/icons"
import { Key, LockKey, Prohibit, SignIn, SignOut, Trash, ArrowCounterClockwise, Envelope, LinkSimple, WarningCircle } from "@/icons"
import type { SecurityEvent, SecurityEventType } from "./api"

export interface EventInfo {
  label: string
  icon: PhosphorIcon
  /** Needs a second look: shown with a warning mark and the word "Check", never colour alone. */
  attention?: boolean
}

export const EVENTS: Record<SecurityEventType, EventInfo> = {
  login_success: { label: "Signed in", icon: SignIn },
  login_failure: { label: "Wrong password", icon: WarningCircle, attention: true },
  login_locked: { label: "Account locked after wrong passwords", icon: Prohibit, attention: true },
  email_changed: { label: "Email changed", icon: Envelope },
  password_changed: { label: "Password changed", icon: Key },
  password_reset: { label: "Password reset", icon: LockKey },
  session_revoked: { label: "Session ended", icon: SignOut },
  social_account_linked: { label: "Google account linked", icon: LinkSimple },
  account_deletion_requested: { label: "Account deletion requested", icon: Trash, attention: true },
  account_deletion_cancelled: { label: "Account deletion cancelled", icon: ArrowCounterClockwise },
}

export const EVENT_OPTIONS = (Object.keys(EVENTS) as SecurityEventType[]).map((value) => ({ value, label: EVENTS[value].label }))

export function eventInfo(e: Pick<SecurityEvent, "event_type">): EventInfo {
  return EVENTS[e.event_type] ?? { label: e.event_type.replace(/_/g, " "), icon: WarningCircle }
}
