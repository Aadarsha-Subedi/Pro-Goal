"""User-facing response messages for the accounts endpoints."""

CSRF_COOKIE_SET = "CSRF cookie set."
LOGGED_IN = "Logged in."
LOGGED_OUT = "Logged out."
EMAIL_VERIFIED = "Email verified. You can log in now."
PASSWORD_UPDATED = "Password updated. Log in with your new password."
PASSWORD_CHANGED = "Password changed. Other sessions were logged out."
SESSION_REVOKED = "Session revoked."
AVATAR_UPDATED = "Avatar updated."
AVATAR_REMOVED = "Avatar removed."
ACCOUNT_DELETION_SCHEDULED = (
    "Account scheduled for deletion. Log in again within 7 days to cancel."
)
ACCOUNT_DELETION_CANCELLED = "Account deletion cancelled."

# Error messages
INVALID_CREDENTIALS = "Invalid email or password."
EMAIL_NOT_VERIFIED = "Verify your email address before logging in."
GOOGLE_SIGN_IN_FAILED = "Google sign-in failed."
GOOGLE_EMAIL_NOT_VERIFIED = "Your Google email address is not verified."
VERIFICATION_LINK_EXPIRED = "This verification link has expired."
VERIFICATION_LINK_INVALID = "This verification link is invalid."
RESET_LINK_INVALID = "This reset link is invalid or has expired."
CURRENT_PASSWORD_INCORRECT = "Current password is incorrect."
OWNS_PROJECTS = "Transfer or delete the projects you own before deleting your account."
SESSION_NOT_FOUND = "Session not found."
CSRF_FAILED = "CSRF verification failed."
ACCOUNT_PENDING_DELETION = "This account is scheduled for deletion."
PROFILE_INCOMPLETE = "Complete your profile before continuing."
AVATAR_TOO_LARGE = "Avatar must be 2 MB or smaller."
AVATAR_BAD_FORMAT = "Avatar must be a JPEG, PNG or WebP image."
REAUTH_FAILED = "Confirmation failed. Check your password or Google sign-in."
REAUTH_REQUIRED = "Confirm with your password or a fresh Google sign-in."
EMAIL_CHANGE_REQUESTED = (
    "If that address can be used, we sent a confirmation link to it."
)
EMAIL_CHANGED = "Email changed. Log in with your new address."
EMAIL_CHANGE_LINK_INVALID = "This confirmation link is invalid or has expired."
SAME_EMAIL = "That is already your email address."
DISPOSABLE_EMAIL = (
    "Temporary email addresses are not accepted. Use your own email address."
)
