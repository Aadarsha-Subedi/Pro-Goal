from django.db import models


class EventType(models.TextChoices):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGIN_LOCKED = "login_locked"
    EMAIL_CHANGED = "email_changed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    SESSION_REVOKED = "session_revoked"
    SOCIAL_ACCOUNT_LINKED = "social_account_linked"
    ACCOUNT_DELETION_REQUESTED = "account_deletion_requested"
    ACCOUNT_DELETION_CANCELLED = "account_deletion_cancelled"
