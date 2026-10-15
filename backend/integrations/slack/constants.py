"""Slack-specific constants (messages, error codes, limits)."""

from integrations.services import audience

PROVIDER = "slack"
MANAGE_PERMISSION = "integration.slack.manage"

API_BASE = "https://slack.com"
AUTHORIZE_URL = f"{API_BASE}/oauth/v2/authorize"
OPENID_AUTHORIZE_URL = f"{API_BASE}/openid/connect/authorize"
INSTALL_CALLBACK_PATH = "/api/integrations/slack/install/callback/"
LINK_CALLBACK_PATH = "/api/integrations/slack/link/callback/"
RESPONSE_URL_PREFIX = "https://hooks.slack.com/"

STATE_SALT = "integrations.slack.oauth-state"
STATE_MAX_AGE_SECONDS = 10 * 60
CLIENT_TIMEOUT_SECONDS = 10
CHANNEL_PAGE_SIZE = 200
CHANNEL_MAX_PAGES = 10

# The personal events live in integrations.services.audience.PERSONAL_EVENTS.
PERSONAL_EVENTS = audience.PERSONAL_EVENTS

# Slack errors that mean the bot token is no longer usable.
DEAD_TOKEN_ERRORS = frozenset(
    {"invalid_auth", "token_revoked", "account_inactive", "not_authed", "token_expired"}
)
DEFAULT_RETRY_AFTER_SECONDS = 30

NOT_CONFIGURED_CODE = "slack_not_configured"
SLACK_ERROR_CODE = "slack_error"
BOT_NOT_IN_CHANNEL_CODE = "bot_not_in_channel"
INVALID_STATE_CODE = "invalid_oauth_state"
UNKNOWN_EVENT_CODE = "unknown_event"
MAPPING_NOT_FOUND_CODE = "mapping_not_found"
DUPLICATE_MAPPING_CODE = "duplicate_mapping"
NOT_CONNECTED_CODE = "slack_not_connected"

NOT_CONFIGURED = "Slack is not configured on this server."
SLACK_ERROR = "Slack could not complete the request ({error})."
BOT_NOT_IN_CHANNEL = (
    "Invite the bot to that channel in Slack first (/invite @Project Management)."
)
INVALID_STATE = "This sign-in link is invalid or has expired. Start again."
UNKNOWN_EVENT = "Unknown event type: {name}."
MAPPING_NOT_FOUND = "Channel mapping not found."
DUPLICATE_MAPPING = "That channel is already mapped."
NOT_CONNECTED = "This project is not connected to Slack."
MAPPING_DELETED = "Channel mapping removed."
MAPPING_SAVED = "Channel mapping saved."
PREFERENCES_SAVED = "Notification preferences saved."
LINK_REMOVED = "Slack account unlinked."

# Replies to slash commands (private to the person who typed them).
USAGE = "Usage:\n• `/task create <project key> <title>`\n• `/task done <KEY-42>`"
NOT_LINKED = (
    "Link your Slack account first: open {url} and choose “Sign in with Slack”."
)
NO_PROJECT = "I could not find a project with key *{key}* that you belong to in this Slack workspace."
AMBIGUOUS_PROJECT = (
    "More than one of your projects uses the key *{key}* here: {names}. "
    "Ask an owner to make the keys different."
)
TASK_CREATED = "Created *{key}* {title}\n{url}"
TASK_DONE = "Marked *{key}* {title} as done.\n{url}"
TASK_ALREADY_DONE = "*{key}* is already done."
TASK_NOT_FOUND = "I could not find task *{key}*."
NO_DONE_STATUS = "That project has no “done” status to move the task to."
TITLE_TOO_LONG = "That title is too long (at most {limit} characters)."
COMMAND_FAILED = "Sorry, something went wrong. Try again in a moment."
