from django.conf import settings

from accounts.services.email_service import queue_email
from integrations.constants import emails, limits
from integrations.constants.statuses import IntegrationStatus
from integrations.models import Integration
from projects.models import Membership


def record_success(integration: Integration) -> None:
    if integration.consecutive_failures:
        integration.consecutive_failures = 0
        integration.save(update_fields=["consecutive_failures", "updated_at"])


def record_failure(integration: Integration) -> None:
    """Count a failed attempt; after too many in a row the integration needs
    attention, sending stops and the installer is told once."""
    integration.consecutive_failures += 1
    fields = ["consecutive_failures", "updated_at"]
    if (
        integration.consecutive_failures >= limits.FAILURES_BEFORE_ATTENTION
        and integration.status == IntegrationStatus.ACTIVE
    ):
        integration.status = IntegrationStatus.NEEDS_ATTENTION
        fields.append("status")
        if not integration.attention_notified:
            integration.attention_notified = True
            fields.append("attention_notified")
            _notify(integration)
    integration.save(update_fields=fields)


def _recipient(integration: Integration) -> str | None:
    """The installer, or the owner if the installer is gone."""
    if integration.installed_by is not None:
        return integration.installed_by.email
    owner = (
        Membership.objects.filter(project=integration.project, is_owner=True)
        .select_related("user")
        .first()
    )
    return owner.user.email if owner else None


def _notify(integration: Integration) -> None:
    to = _recipient(integration)
    if to is None:
        return
    queue_email(
        emails.NEEDS_ATTENTION_SUBJECT.format(provider=integration.provider.title()),
        emails.NEEDS_ATTENTION_BODY.format(
            provider=integration.provider.title(),
            project=integration.project.name,
            count=integration.consecutive_failures,
            frontend_url=settings.FRONTEND_URL,
            project_id=integration.project_id,
        ),
        to,
    )
