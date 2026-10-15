"""The only place that builds Slack SDK clients, so the timeout is set once and
tests have one thing to replace."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.webhook import WebhookClient

from common.exception.domain import ExternalServiceException
from integrations.providers.base import DeliveryResult
from integrations.slack import constants


def web_client(token: str | None = None) -> WebClient:
    return WebClient(token=token, timeout=constants.CLIENT_TIMEOUT_SECONDS)


def webhook_client(url: str) -> WebhookClient:
    return WebhookClient(url, timeout=constants.CLIENT_TIMEOUT_SECONDS)


def error_code(exc: SlackApiError) -> str:
    return str((exc.response or {}).get("error", "unknown_error"))


def retry_after(exc: SlackApiError) -> int:
    headers = getattr(exc.response, "headers", None) or {}
    try:
        return max(
            int(headers.get("Retry-After", constants.DEFAULT_RETRY_AFTER_SECONDS)), 1
        )
    except TypeError, ValueError:
        return constants.DEFAULT_RETRY_AFTER_SECONDS


def is_rate_limited(exc: SlackApiError) -> bool:
    return getattr(exc.response, "status_code", None) == 429


def to_delivery_result(exc: SlackApiError) -> DeliveryResult:
    """Describe a failed post: rate limits ask us to wait, anything else is a
    failure with Slack's error code as the reason."""
    if is_rate_limited(exc):
        return DeliveryResult(
            ok=False,
            status_code=429,
            retry_after=retry_after(exc),
            error="ratelimited",
        )
    return DeliveryResult(
        ok=False,
        status_code=getattr(exc.response, "status_code", None),
        error=error_code(exc),
    )


def to_api_error(exc: SlackApiError) -> ExternalServiceException:
    """For request/response endpoints: a 502 that names Slack's reason."""
    return ExternalServiceException(
        constants.SLACK_ERROR.format(error=error_code(exc)),
        error_code=constants.SLACK_ERROR_CODE,
    )
