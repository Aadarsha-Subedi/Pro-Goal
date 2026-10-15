from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from slack_sdk.errors import SlackApiError

from common.exception.domain import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from integrations.constants import actions
from integrations.constants.events import EventType
from integrations.constants.statuses import IntegrationStatus
from integrations.models import Integration, SlackChannelMapping
from integrations.services import integration_service
from integrations.slack import client, constants
from projects import permissions
from projects.models import Membership
from projects.services import access, activity


def require_manage(membership: Membership) -> None:
    permissions.require_permission(membership, constants.MANAGE_PERMISSION)


def get_integration(membership: Membership) -> Integration:
    """The project's live Slack integration, or 404."""
    integration = (
        Integration.objects.filter(
            project=membership.project, provider=constants.PROVIDER
        )
        .exclude(status=IntegrationStatus.DISCONNECTED)
        .first()
    )
    if integration is None:
        raise NotFoundException(
            constants.NOT_CONNECTED, error_code=constants.NOT_CONNECTED_CODE
        )
    return integration


def validate_events(names: list[str]) -> list[str]:
    valid = {e.value for e in EventType}
    unknown = [n for n in names if n not in valid]
    if unknown:
        raise ValidationException(
            errors=[
                {
                    "field": "enabled_events",
                    "message": constants.UNKNOWN_EVENT.format(name=name),
                }
                for name in unknown
            ],
            error_code=constants.UNKNOWN_EVENT_CODE,
        )
    return list(dict.fromkeys(names))


def list_channels(membership: Membership) -> list[dict]:
    require_manage(membership)
    integration = get_integration(membership)
    slack = client.web_client(integration.get_token())
    channels: list[dict] = []
    cursor = None
    try:
        for _ in range(constants.CHANNEL_MAX_PAGES):
            page = slack.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=constants.CHANNEL_PAGE_SIZE,
                cursor=cursor,
            )
            for channel in page["channels"]:
                channels.append(
                    {
                        "id": channel["id"],
                        "name": channel["name"],
                        "is_private": bool(channel.get("is_private")),
                        "is_member": bool(channel.get("is_member")),
                    }
                )
            cursor = (page.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
    except SlackApiError as exc:
        _handle_slack_error(integration, exc)
    return sorted(channels, key=lambda c: c["name"])


def _handle_slack_error(integration: Integration, exc: SlackApiError) -> None:
    code = client.error_code(exc)
    if code in constants.DEAD_TOKEN_ERRORS:
        integration_service.mark_uninstalled(integration)
    raise client.to_api_error(exc) from exc


def list_mappings(membership: Membership) -> QuerySet[SlackChannelMapping]:
    require_manage(membership)
    integration = get_integration(membership)
    return SlackChannelMapping.objects.filter(integration=integration)


def _get(membership: Membership, mapping_id: UUID) -> SlackChannelMapping:
    integration = get_integration(membership)
    mapping = SlackChannelMapping.objects.filter(
        integration=integration, pk=mapping_id
    ).first()
    if mapping is None:
        raise NotFoundException(
            constants.MAPPING_NOT_FOUND, error_code=constants.MAPPING_NOT_FOUND_CODE
        )
    return mapping


@transaction.atomic
def create(
    membership: Membership,
    channel_id: str,
    enabled_events: list[str],
    ip: str | None = None,
) -> SlackChannelMapping:
    require_manage(membership)
    access.ensure_writable(membership.project)
    integration = get_integration(membership)
    events = validate_events(enabled_events)
    try:
        info = client.web_client(integration.get_token()).conversations_info(
            channel=channel_id
        )
    except SlackApiError as exc:
        _handle_slack_error(integration, exc)
    channel = info["channel"]
    # The bot posts only where it has been invited, so refuse early with a
    # clear reason instead of failing every delivery later.
    if not channel.get("is_member"):
        raise ConflictException(
            constants.BOT_NOT_IN_CHANNEL, error_code=constants.BOT_NOT_IN_CHANNEL_CODE
        )
    try:
        with transaction.atomic():
            mapping = SlackChannelMapping.objects.create(
                integration=integration,
                channel_id=channel["id"],
                channel_name=channel["name"],
                is_public=not channel.get("is_private", False),
                enabled_events=events,
            )
    except IntegrityError:
        raise ConflictException(
            constants.DUPLICATE_MAPPING, error_code=constants.DUPLICATE_MAPPING_CODE
        ) from None
    activity.log(
        membership.project,
        membership.user,
        actions.MAPPING_SAVED,
        actions.ENTITY_INTEGRATION,
        integration.pk,
        {"channel": mapping.channel_name, "events": events},
        ip,
    )
    return mapping


@transaction.atomic
def update(
    membership: Membership,
    mapping_id: UUID,
    enabled_events: list[str],
    ip: str | None = None,
) -> SlackChannelMapping:
    require_manage(membership)
    access.ensure_writable(membership.project)
    mapping = _get(membership, mapping_id)
    mapping.enabled_events = validate_events(enabled_events)
    mapping.save(update_fields=["enabled_events", "updated_at"])
    activity.log(
        membership.project,
        membership.user,
        actions.MAPPING_SAVED,
        actions.ENTITY_INTEGRATION,
        mapping.integration_id,
        {"channel": mapping.channel_name, "events": mapping.enabled_events},
        ip,
    )
    return mapping


@transaction.atomic
def delete(membership: Membership, mapping_id: UUID, ip: str | None = None) -> None:
    require_manage(membership)
    access.ensure_writable(membership.project)
    mapping = _get(membership, mapping_id)
    activity.log(
        membership.project,
        membership.user,
        actions.MAPPING_REMOVED,
        actions.ENTITY_INTEGRATION,
        mapping.integration_id,
        {"channel": mapping.channel_name},
        ip,
    )
    mapping.delete()
