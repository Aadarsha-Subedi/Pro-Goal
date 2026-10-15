"""Who gets a Slack direct message about a personal event."""

from accounts.models import User
from integrations.constants.statuses import IntegrationStatus
from integrations.models import (
    Integration,
    LinkedAccount,
    NotificationPreference,
    OutboxEvent,
)
from integrations.services import audience
from integrations.slack import constants


def dm_targets(integration: Integration, event: OutboxEvent) -> list[tuple[User, str]]:
    """(user, Slack user id) pairs to DM: current members who linked Slack in
    this workspace and have not switched this event's DMs off."""
    if event.event_type not in audience.PERSONAL_EVENTS:
        return []
    if integration.status != IntegrationStatus.ACTIVE:
        return []
    wanted = audience.candidate_users(event)
    if not wanted:
        return []
    members = audience.current_members(event, wanted)
    muted = {
        str(pk)
        for pk in NotificationPreference.objects.filter(
            user_id__in=members, event_type=event.event_type, slack_dm=False
        ).values_list("user_id", flat=True)
    }
    linked = LinkedAccount.objects.select_related("user").filter(
        provider=constants.PROVIDER,
        external_workspace_id=integration.external_workspace_id,
        user_id__in=members - muted,
    )
    return [(account.user, account.external_user_id) for account in linked]
