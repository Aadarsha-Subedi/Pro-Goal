"""Subjects and body templates for transactional emails. `{link}` and
`{frontend_url}` are filled in by `email_service`."""

VERIFICATION_SUBJECT = "Verify your email"
VERIFICATION_BODY = (
    "Confirm your email address by opening this link within 24 hours:\n\n{link}\n"
)
VERIFICATION_PATH = "/verify-email?token={token}"

ALREADY_REGISTERED_SUBJECT = "You already have an account"
ALREADY_REGISTERED_BODY = (
    "Someone tried to sign up with this email address, but you already have "
    "an account. Log in or reset your password at {frontend_url}/login\n"
    "If this was not you, you can ignore this message.\n"
)

PASSWORD_RESET_SUBJECT = "Reset your password"
PASSWORD_RESET_BODY = (
    "Reset your password by opening this link within 1 hour:\n\n{link}\n"
    "If you did not ask for this, you can ignore this message.\n"
)
PASSWORD_RESET_PATH = "/reset-password?uid={uid}&token={token}"

PASSWORD_CHANGED_SUBJECT = "Your password was changed"
PASSWORD_CHANGED_BODY = (
    "The password on your account was just changed. If this was not you, "
    "reset your password at {frontend_url}/forgot-password\n"
)

EMAIL_CHANGE_SUBJECT = "Confirm your new email address"
EMAIL_CHANGE_BODY = (
    "Confirm that this is your new login address by opening this link within "
    "24 hours:\n\n{link}\n"
    "If you did not ask for this, you can ignore this message.\n"
)
EMAIL_CHANGE_PATH = "/confirm-email-change?token={token}"

EMAIL_CHANGE_REQUESTED_SUBJECT = "Someone asked to change your email address"
EMAIL_CHANGE_REQUESTED_BODY = (
    "A request was made to change the email on your account to {new_email}.\n"
    "Nothing changes until the new address is confirmed. If this was not you, "
    "reset your password now at {frontend_url}/forgot-password\n"
)

EMAIL_CHANGED_SUBJECT = "Your email address was changed"
EMAIL_CHANGED_BODY = (
    "The email on your account was changed to {new_email}, and you were signed "
    "out everywhere. If this was not you, contact support right away.\n"
)
