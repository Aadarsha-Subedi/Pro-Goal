import { ApiError } from "@/lib/api"

const FALLBACK = "Something went wrong. Try again."

const MESSAGES: Record<string, string> = {
  integrations_not_configured: "Integrations aren't set up on this server yet.",
  unknown_provider: "That integration doesn't exist.",
  integration_not_found: "That integration was already removed. Reload the page.",
  delivery_not_found: "That delivery no longer exists. Reload the page.",
  delivery_not_replayable: "Only failed deliveries can be sent again.",
  integration_inactive: "This integration isn't active, so nothing is sent. Reconnect it first.",
  invalid_signature: FALLBACK,
  invalid_encryption_key: FALLBACK,
  slack_not_configured: "Slack isn't set up on this server yet. Ask whoever runs it to add the Slack app credentials.",
  slack_error: "Slack couldn't complete that. Try again in a moment.",
  bot_not_in_channel: "Invite the bot to that channel in Slack first: /invite @Project Management.",
  invalid_oauth_state: "That Slack sign-in link expired. Start again.",
  unknown_event: "That event type doesn't exist. Reload the page.",
  mapping_not_found: "That channel mapping was already removed. Reload the page.",
  duplicate_mapping: "That channel is already mapped. Edit its events instead.",
  slack_not_connected: "This project isn't connected to Slack yet.",
  permission_denied: "You don't have permission to do this.",
  forbidden: "You don't have permission to do this.",
  project_archived: "This project is archived, so integrations can't change.",
  throttled: "Too many requests. Wait a moment and try again.",
  network_error: "Can't reach the server. Check your connection and try again.",
}

export function integrationError(err: unknown): string {
  return err instanceof ApiError ? (MESSAGES[err.code] ?? FALLBACK) : FALLBACK
}

export const isForbidden = (err: unknown) => err instanceof ApiError && err.status === 403

const REASONS: Record<string, string> = {
  access_denied: "You cancelled in Slack, so nothing changed.",
  invalid_oauth_state: MESSAGES.invalid_oauth_state,
  not_signed_in: "You were signed out while connecting. Sign in and try again.",
  no_code: "Slack didn't send anything back. Try again.",
}

/** Toast copy for the `?slack=` result the backend adds when Slack sends the browser back. */
export function slackReturn(slack: string | undefined, reason: string | undefined): { kind: "success" | "error"; text: string } | null {
  if (slack === "connected") return { kind: "success", text: "Slack is connected. Map a channel to start posting." }
  if (slack === "linked") return { kind: "success", text: "Your Slack account is linked." }
  if (slack === "error") return { kind: "error", text: (reason && (REASONS[reason] ?? MESSAGES[reason])) || "Slack couldn't finish connecting. Try again." }
  return null
}
