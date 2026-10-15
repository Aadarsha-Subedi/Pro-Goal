import { ApiError } from "@/lib/api"

/** Plain-language message per stable backend code. Never parses the backend's message text. */
const MESSAGES: Record<string, string> = {
  invalid_join_code: "No project uses this code. Check it with the owner.",
  join_code_throttled: "Too many wrong codes. Try again in an hour.",
  already_member: "You are already a member of this project.",
  join_request_pending: "You already asked to join this project. The owner has not decided yet.",
  join_request_cooldown: "The owner declined your last request. You can ask again after 24 hours.",
  too_many_open_requests: "You have 10 open requests. Wait for a decision before asking again.",
  join_request_not_pending: "Someone already decided this request.",
  join_request_expired: "This request expired. Ask the person to request again.",
  project_archived: "This project is archived. The owner can unarchive it to allow changes.",
  project_not_archived: "This project is not archived.",
  project_not_deleted: "This project is not scheduled for deletion.",
  join_request_not_found: "This request no longer exists.",
  transfer_not_found: "This transfer no longer exists.",
  fields_forbidden: "You don't have permission to change those fields.",
  unknown_permission: "That permission doesn't exist. Reload the page and try again.",
  unknown_preset: "That preset doesn't exist. Reload the page and try again.",
  cannot_manage_owner: "The owner's access can't be changed.",
  cannot_grant_permission: "You can only grant permissions you hold yourself.",
  invalid_reassignment: "That reassignment isn't valid. Choose a current member.",
  project_deleted: "This project is scheduled for deletion.",
  project_not_found: "This project doesn't exist, or you don't have access.",
  reauth_failed: "That didn't match. Check your password and try again.",
  reauth_required: "Confirm it is you to continue.",
  owner_only: "Only the project owner can do this.",
  permission_denied: "You don't have permission to do this.",
  cannot_remove_owner: "The owner can't be removed. Transfer ownership first.",
  cannot_remove_self: "Use Leave project to remove yourself.",
  owner_cannot_leave: "Transfer ownership before leaving.",
  member_not_found: "This person is no longer a member.",
  transfer_pending: "A transfer is already waiting for an answer. Cancel it first.",
  transfer_not_pending: "This transfer is no longer open.",
  transfer_expired: "This transfer expired. Ask the owner to send it again.",
  invalid_transfer_target: "Choose a current member to receive ownership.",
  restore_window_over: "The 7-day restore window is over.",
  demo_project_locked: "This is a shared demo project, so it can't be changed. Copy it to your workspace to edit.",
  copy_not_allowed: "Only demo projects can be copied.",
  copy_limit_reached: "You already have 3 copies of demo projects. Delete one to make another.",
  throttled: "Too many attempts. Wait a moment and try again.",
  network_error: "Can't reach the server. Check your connection and try again.",
}

const FALLBACK = "Something went wrong. Try again."

export function projectErrorCode(err: unknown): string {
  return err instanceof ApiError ? err.code : "unknown_error"
}

export function projectError(err: unknown): string {
  if (!(err instanceof ApiError)) return FALLBACK
  if (err.status === 429) return MESSAGES.throttled
  return MESSAGES[err.code] ?? FALLBACK
}

/** Field-level message for form errors (validation_error carries `errors:[{field,message}]`). */
export function projectFieldError(err: unknown, field: string): string | undefined {
  return err instanceof ApiError ? err.fieldError(field) : undefined
}

export function isNotFound(err: unknown): boolean {
  return err instanceof ApiError && err.status === 404
}
