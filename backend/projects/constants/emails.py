"""Subjects and body templates for project emails."""

JOIN_REQUEST_SUBJECT = "New request to join {project}"
JOIN_REQUEST_BODY = (
    "{requester} ({email}) asked to join {project}.\n"
    "Review the request at {frontend_url}/projects/{project_id}/join-requests\n"
)

JOIN_APPROVED_SUBJECT = "You joined {project}"
JOIN_APPROVED_BODY = "Your request to join {project} was approved.\n{frontend_url}/projects/{project_id}\n"

JOIN_REJECTED_SUBJECT = "Your request to join {project}"
JOIN_REJECTED_BODY = (
    "Your request to join {project} was not approved. "
    "You can ask again after 24 hours.\n"
)

MEMBER_REMOVED_SUBJECT = "You were removed from {project}"
MEMBER_REMOVED_BODY = "You were removed from the project {project}.\n"

TRANSFER_OFFER_SUBJECT = "Ownership of {project} was offered to you"
TRANSFER_OFFER_BODY = (
    "{owner} wants to make you the owner of {project}. "
    "Accept within 7 days at {frontend_url}/projects/{project_id}/transfer\n"
)

TRANSFER_ACCEPTED_SUBJECT = "{project} has a new owner"
TRANSFER_ACCEPTED_BODY = (
    "{new_owner} accepted ownership of {project}. You are now a regular member.\n"
)
