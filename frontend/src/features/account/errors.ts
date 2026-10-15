import { ApiError } from "@/lib/api"

const FALLBACK = "Something went wrong. Try again."

const MESSAGES: Record<string, string> = {
  session_not_found: "That session already ended.",
  login_locked: "Too many wrong passwords. Wait a few minutes and try again.",
  throttled: "Too many requests. Wait a moment and try again.",
  network_error: "Can't reach the server. Check your connection and try again.",
  invalid_credentials: "That password isn't right.",
  email_not_verified: "Verify your email first.",
  google_token_invalid: "Google couldn't confirm it's you. Try again.",
  google_email_not_verified: "Google says that email isn't verified.",
  verification_token_expired: "That link expired. Ask for a new one.",
  verification_token_invalid: "That link doesn't work. Ask for a new one.",
  reset_token_invalid: "That link doesn't work. Ask for a new one.",
  invalid_current_password: "Your current password isn't right.",
  owns_projects: "You still own projects. Transfer or delete them first, then delete your account.",
  csrf_failed: "Your session changed. Reload the page and try again.",
  account_pending_deletion: "This account is scheduled for deletion. Cancel the deletion to keep using it.",
  profile_incomplete: "Finish your profile first.",
  invalid_avatar: "That image can't be used. Choose a JPEG, PNG or WebP picture.",
  reauth_failed: "That password isn't right.",
  reauth_required: "Confirm with your password or Google to continue.",
  email_change_token_invalid: "That link doesn't work. It may have been used already.",
  email_change_token_expired: "That link expired. Request the change again.",
  same_email: "That is already your email address.",
  disposable_email: "Temporary email addresses are not accepted. Use your own email address.",
}

export function accountError(err: unknown): string {
  return err instanceof ApiError ? (MESSAGES[err.code] ?? FALLBACK) : FALLBACK
}
