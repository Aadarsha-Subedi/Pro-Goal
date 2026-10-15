from django.apps import AppConfig
from django.conf import settings


class IntegrationsConfig(AppConfig):
    name = "integrations"

    def ready(self) -> None:
        from integrations.notifications.email import notify_by_email
        from integrations.services import events, fanout, integration_service, outbox
        from projects.services import activity, hooks

        if events.on_activity not in activity.listeners:
            activity.listeners.append(events.on_activity)
        if fanout.deliver_to_integrations not in outbox.subscribers:
            outbox.subscribers.append(fanout.deliver_to_integrations)
        if notify_by_email not in outbox.subscribers:
            outbox.subscribers.append(notify_by_email)
        if settings.SLACK_CLIENT_ID:
            from integrations.providers import registry
            from integrations.slack.provider import SlackProvider

            registry.register(SlackProvider())
        if integration_service.disconnect_all not in hooks.project_purging:
            hooks.project_purging.append(integration_service.disconnect_all)
