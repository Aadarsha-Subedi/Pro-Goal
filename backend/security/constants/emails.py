"""Alert emails. `{frontend_url}` is filled in by the sender."""

NEW_DEVICE_SUBJECT = "New sign-in to your account"
NEW_DEVICE_BODY = (
    "Your account was just signed in to from a new device: {device}.\n\n"
    "If this was you, no action is needed. If not, reset your password at "
    "{frontend_url}/forgot-password and revoke unknown sessions in your "
    "account settings.\n"
)

LOCKED_SUBJECT = "Repeated failed sign-in attempts"
LOCKED_BODY = (
    "There were several failed attempts to sign in to your account, so sign-in "
    "is paused for a short while.\n\n"
    "If this was not you, reset your password at {frontend_url}/forgot-password\n"
)
