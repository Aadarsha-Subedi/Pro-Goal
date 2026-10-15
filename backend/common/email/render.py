"""Turns a plain-text transactional email into a multipart message: the text
stays as the fallback, and an HTML version adds the Pro-Goal header, a button
for the main link, and a footer. Callers keep passing plain text."""

import re
from email.message import MIMEPart
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

LOGO_PATH = Path(__file__).parent / "static" / "logo.png"
LOGO_CID = "pro-goal-logo"
DEFAULT_ACTION_LABEL = "Open Pro-Goal"

_URL = re.compile(r"https?://[^\s<>\"']+")
# A phrase that introduces a link ("... at <url>", "... : <url>") goes with it.
_LEAD_IN = re.compile(r"\s*(?:\bat|\bto|:)?\s*$")

# Button text by what the link points at, so callers need not name one.
_ACTION_LABELS = (
    ("/verify-email", "Verify email"),
    ("/reset-password", "Reset password"),
    ("/forgot-password", "Reset password"),
    ("/confirm-email-change", "Confirm new address"),
    ("/join-requests", "Review request"),
    ("/transfer", "View offer"),
    ("/integrations", "Open integrations"),
    ("/tasks/", "Open task"),
    ("/login", "Sign in"),
)


def action_label_for(url: str) -> str:
    for fragment, label in _ACTION_LABELS:
        if fragment in url:
            return label
    return DEFAULT_ACTION_LABEL


def _split(body: str) -> tuple[list[str], str | None]:
    """Paragraphs of the body without the first link, and that link. Further
    links stay in the text so nothing is lost."""
    match = _URL.search(body)
    url = match.group(0).rstrip(".,);") if match else None
    if match and url:
        end = match.start() + len(url)
        before = _LEAD_IN.sub("", body[: match.start()])
        body = (
            before
            + ("." if before and not before.endswith((".", "!", "?")) else "")
            + body[end:].lstrip(".")
        )
    paragraphs = [" ".join(chunk.split()) for chunk in re.split(r"\n\s*\n|\n", body)]
    return [p for p in paragraphs if p], url


def _logo() -> MIMEPart:
    """The mark as an inline image the HTML refers to by `cid:`, so it shows
    without the reader loading remote images."""
    image = MIMEPart()
    image.set_content(
        LOGO_PATH.read_bytes(),
        maintype="image",
        subtype="png",
        disposition="inline",
        filename="logo.png",
        cid=f"<{LOGO_CID}>",
    )
    return image


def build_message(
    subject: str, body: str, to: str, action_label: str | None = None
) -> EmailMultiAlternatives:
    paragraphs, url = _split(body)
    html = render_to_string(
        "email/base.html",
        {
            "subject": subject,
            "preheader": paragraphs[0] if paragraphs else subject,
            "paragraphs": paragraphs,
            "action_url": url,
            "action_label": action_label or (action_label_for(url) if url else ""),
            "home_url": settings.FRONTEND_URL,
            "logo_cid": LOGO_CID,
        },
    )
    message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [to])
    message.attach_alternative(html, "text/html")
    message.attach(_logo())
    return message
