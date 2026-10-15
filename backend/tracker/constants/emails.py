"""Subjects and body templates for tracker emails."""

MENTION_SUBJECT = "{author} mentioned you in {project}"
MENTION_BODY = (
    "{author} mentioned you in {where} ({project}).\n"
    "Open it at {frontend_url}/projects/{project_id}/{path}\n"
)
