"""Slack OAuth: installing the app into a project ("Add to Slack") and linking
a person's own account ("Sign in with Slack"). The browser always returns to a
fixed callback URL, so project and user travel in a signed `state`."""

from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.db import transaction
from slack_sdk.errors import SlackApiError

from accounts.models import User
from common.exception.domain import ServiceUnavailableException, ValidationException
from integrations.constants import actions
from integrations.constants.statuses import IntegrationStatus
from integrations.models import Integration, LinkedAccount
from integrations.services import integration_service, linking
from integrations.slack import client, constants
from projects.models import Membership
from projects.services import access, activity


def ensure_configured() -> None:
    needed = (
        settings.SLACK_CLIENT_ID,
        settings.SLACK_CLIENT_SECRET,
        settings.SLACK_SIGNING_SECRET,
        settings.PUBLIC_API_URL,
        settings.INTEGRATION_ENCRYPTION_KEYS,
    )
    if not all(needed):
        raise ServiceUnavailableException(
            constants.NOT_CONFIGURED, error_code=constants.NOT_CONFIGURED_CODE
        )


def _redirect_uri(path: str) -> str:
    return f"{settings.PUBLIC_API_URL}{path}"


def make_state(purpose: str, user_id: UUID, project_id: UUID | None = None) -> str:
    return signing.dumps(
        {
            "purpose": purpose,
            "user": str(user_id),
            "project": str(project_id) if project_id else None,
        },
        salt=constants.STATE_SALT,
    )


def read_state(state: str, purpose: str, user: User) -> dict:
    """The data in a state, if it is genuine, fresh, meant for this purpose and
    was issued to the person now signed in."""
    try:
        data = signing.loads(
            state, salt=constants.STATE_SALT, max_age=constants.STATE_MAX_AGE_SECONDS
        )
    except signing.BadSignature:
        raise _invalid_state() from None
    if data.get("purpose") != purpose or data.get("user") != str(user.pk):
        raise _invalid_state()
    return data


def _invalid_state() -> ValidationException:
    return ValidationException(
        constants.INVALID_STATE, error_code=constants.INVALID_STATE_CODE
    )


def install_url(membership: Membership) -> str:
    ensure_configured()
    from integrations.slack.services import mapping_service

    mapping_service.require_manage(membership)
    access.ensure_writable(membership.project)
    query = urlencode(
        {
            "client_id": settings.SLACK_CLIENT_ID,
            "scope": ",".join(settings.SLACK_SCOPES),
            "redirect_uri": _redirect_uri(constants.INSTALL_CALLBACK_PATH),
            "state": make_state("install", membership.user_id, membership.project_id),
        }
    )
    return f"{constants.AUTHORIZE_URL}?{query}"


@transaction.atomic
def complete_install(code: str, state: str, user: User) -> Integration:
    ensure_configured()
    from integrations.slack.services import mapping_service

    data = read_state(state, "install", user)
    membership = access.get_membership(user, UUID(data["project"]))
    mapping_service.require_manage(membership)
    access.ensure_writable(membership.project)
    try:
        response = client.web_client().oauth_v2_access(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=_redirect_uri(constants.INSTALL_CALLBACK_PATH),
        )
    except SlackApiError as exc:
        raise client.to_api_error(exc) from exc

    team_id = response["team"]["id"]
    details = {
        "team_name": response["team"].get("name", ""),
        "bot_user_id": response.get("bot_user_id", ""),
    }
    integration = (
        Integration.objects.select_for_update()
        .filter(project=membership.project, provider=constants.PROVIDER)
        .exclude(status=IntegrationStatus.DISCONNECTED)
        .first()
    )
    if integration is None:
        integration = Integration(
            project=membership.project, provider=constants.PROVIDER
        )
    elif integration.external_workspace_id != team_id:
        # Channel ids belong to the old workspace.
        integration.slack_mappings.all().delete()
    integration.installed_by = user
    integration.external_workspace_id = team_id
    integration.settings = details
    integration.set_token(response["access_token"])
    integration.save()
    integration_service.reactivate(integration)
    activity.log(
        membership.project,
        user,
        actions.INTEGRATION_CONNECTED,
        actions.ENTITY_INTEGRATION,
        integration.pk,
        {"provider": constants.PROVIDER, "workspace": details["team_name"]},
    )
    return integration


def link_url(user: User) -> str:
    ensure_configured()
    query = urlencode(
        {
            "response_type": "code",
            "scope": "openid",
            "client_id": settings.SLACK_CLIENT_ID,
            "redirect_uri": _redirect_uri(constants.LINK_CALLBACK_PATH),
            "state": make_state("link", user.pk),
        }
    )
    return f"{constants.OPENID_AUTHORIZE_URL}?{query}"


@transaction.atomic
def complete_link(code: str, state: str, user: User) -> LinkedAccount:
    ensure_configured()
    read_state(state, "link", user)
    try:
        token = client.web_client().openid_connect_token(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=_redirect_uri(constants.LINK_CALLBACK_PATH),
        )
        identity = client.web_client(token["access_token"]).openid_connect_userInfo()
    except SlackApiError as exc:
        raise client.to_api_error(exc) from exc
    # Only Slack's own identity counts: people are never matched by email.
    return linking.link(
        user,
        constants.PROVIDER,
        identity["sub"],
        identity["https://slack.com/team_id"],
    )
