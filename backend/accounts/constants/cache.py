"""Cache key templates and limits."""

PASSWORD_RESET_KEY = "password-reset:{email}"
PASSWORD_RESET_WINDOW_SECONDS = 60 * 60
RESET_REQUESTS_PER_HOUR = 3

VERIFY_RESEND_KEY = "verify-resend:{email}"

SESSION_SEEN_FIELD = "last_seen"
SESSION_TOUCH_INTERVAL_SECONDS = 60
