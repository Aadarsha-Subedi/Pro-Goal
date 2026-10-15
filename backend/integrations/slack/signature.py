from django.conf import settings
from django.http import HttpRequest
from slack_sdk.signature import SignatureVerifier

from common.exception.domain import AuthenticationDeniedException
from integrations.constants import error_codes, messages


def verify(request: HttpRequest) -> None:
    """Check `X-Slack-Signature` against the raw body with the signing secret.
    The SDK also refuses requests whose timestamp is more than 5 minutes old."""
    secret = settings.SLACK_SIGNING_SECRET
    verifier = SignatureVerifier(secret) if secret else None
    headers = {
        "X-Slack-Signature": request.headers.get("X-Slack-Signature", ""),
        "X-Slack-Request-Timestamp": request.headers.get(
            "X-Slack-Request-Timestamp", ""
        ),
    }
    if verifier is None or not _is_valid(verifier, request.body, headers):
        raise AuthenticationDeniedException(
            messages.INVALID_SIGNATURE, error_code=error_codes.INVALID_SIGNATURE
        )


def _is_valid(
    verifier: SignatureVerifier, body: bytes, headers: dict[str, str]
) -> bool:
    if (
        not headers["X-Slack-Signature"]
        or not headers["X-Slack-Request-Timestamp"].isdigit()
    ):
        return False
    try:
        return verifier.is_valid_request(body, headers)
    except ValueError:
        return False
