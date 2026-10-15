"""Slack Events API: the workspace tells us the app or its tokens are gone."""

import json

from integrations.constants.statuses import IntegrationStatus
from integrations.models import InboundWebhook, Integration, LinkedAccount
from integrations.services import integration_service
from integrations.slack import constants


def _live(team_id: str):
    return Integration.objects.filter(
        provider=constants.PROVIDER, external_workspace_id=team_id
    ).exclude(status=IntegrationStatus.DISCONNECTED)


def handle(webhook: InboundWebhook) -> None:
    payload = json.loads(webhook.raw_payload)
    team_id = payload.get("team_id", "")
    event = payload.get("event") or {}
    kind = event.get("type")

    if kind == "app_uninstalled":
        # Every project connected to that workspace loses its integration.
        for integration in _live(team_id):
            integration_service.mark_uninstalled(integration)
        LinkedAccount.objects.filter(
            provider=constants.PROVIDER, external_workspace_id=team_id
        ).delete()
    elif kind == "tokens_revoked":
        tokens = event.get("tokens") or {}
        bots = set(tokens.get("bot") or [])
        for integration in _live(team_id):
            if integration.settings.get("bot_user_id") in bots:
                integration_service.mark_uninstalled(integration)
        people = tokens.get("oauth") or []
        if people:
            LinkedAccount.objects.filter(
                provider=constants.PROVIDER,
                external_workspace_id=team_id,
                external_user_id__in=people,
            ).delete()
