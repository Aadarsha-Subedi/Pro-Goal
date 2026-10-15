"""User-facing response messages for the attachments endpoints."""

UPLOAD_URL_READY = "Upload URL ready. Upload the file, then confirm it."
ATTACHMENT_CONFIRMED = "Attachment confirmed."
ATTACHMENT_DELETED = "Attachment deleted."

# Error messages
NOT_CONFIGURED = "File attachments are not configured on this server."
ATTACHMENT_NOT_FOUND = "Attachment not found."
TARGET_NOT_FOUND = "The task, note or comment was not found."
TARGET_REQUIRED = "Choose exactly one of task, note or comment."
TYPE_NOT_ALLOWED = "This file type is not allowed."
FILE_TOO_LARGE = "This file is larger than the {limit} MB limit for its type."
EMPTY_FILE = "The file is empty."
USER_QUOTA_EXCEEDED = "You have used your personal storage allowance."
PROJECT_QUOTA_EXCEEDED = "This project has used its storage allowance."
TARGET_FULL = "This item already has the maximum number of attachments ({limit})."
NOT_PENDING = "This attachment was already confirmed."
UPLOAD_MISSING = "The file has not been uploaded yet."
UPLOAD_SIZE_MISMATCH = "The uploaded file does not match the declared size."
NOT_READY = "This attachment is still being processed."
INVALID_NOTE_IMAGE = (
    "Images in notes must be attachments of this project (attachment:<id>)."
)
