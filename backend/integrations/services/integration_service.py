import logging
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from common.exception.domain import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
)
from integrations.constants import actions, error_codes, messages
from integrations.constants.statuses import DeliveryStatus, IntegrationStatus
from integrations.models import DeliveryAttempt, Integration
from integrations.providers import registry
from integrations.services import delivery as delivery_service
from projects import permissions
from projects.constants import error_codes as project_error_codes
from projects.constants import messages as project_messages
from projects.constants.permissions import INTEGRATION_LOGS_VIEW
from projects.models import Membership, Project
from projects.services import access, activity

logger = logging.getLogger(__name__)


def _manage_code(provider_code: str) -> str | None:
    provider = registry.find(provider_code)
    return provider.manage_permission if provider else None


def can_manage(membership: Membership, provider_code: str) -> bool:
    code = _manage_code(provider_code)
    return bool(code) and permissions.has_permission(membership, code)


def _require_manage(membership: Membership, provider_code: str) -> None:
    if not can_manage(membership, provider_code):
        raise PermissionDeniedException(
            project_messages.PERMISSION_DENIED,
            error_code=project_error_codes.PERMISSION_DENIED,
        )


def can_view_logs(membership: Membership, provider_code: str) -> bool:
    return permissions.has_permission(membership, INTEGRATION_LOGS_VIEW) or can_manage(
        membership, provider_code
    )


def _not_found(message: str, code: str) -> NotFoundException:
    return NotFoundException(message, error_code=code)


def get(membership: Membership, integration_id: UUID) -> Integration:
    integration = (
        Integration.objects.select_related("installed_by", "project")
        .filter(project=membership.project, pk=integration_id)
        .first()
    )
    if integration is None:
        raise _not_found(
            messages.INTEGRATION_NOT_FOUND, error_codes.INTEGRATION_NOT_FOUND
        )
    return integration


def list_for(membership: Membership) -> list[Integration]:
    """Integrations the caller may see (health only, never secrets)."""
    items = Integration.objects.select_related("installed_by").filter(
        project=membership.project
    )
    return [i for i in items if can_view_logs(membership, i.provider)]


def _wipe(integration: Integration) -> None:
    integration.encrypted_token = ""
    integration.settings = {}
    integration.status = IntegrationStatus.DISCONNECTED
    integration.paused_until = None
    integration.save(
        update_fields=[
            "encrypted_token",
            "settings",
            "status",
            "paused_until",
            "updated_at",
        ]
    )


def _revoke_quietly(integration: Integration) -> None:
    provider = registry.find(integration.provider)
    if provider is None:
        return
    try:
        provider.revoke(integration)
    except Exception:
        # Disconnecting must always succeed locally, even if the provider is down.
        logger.exception(
            "Could not revoke integration token",
            extra={"integration_id": str(integration.pk)},
        )


@transaction.atomic
def disconnect(
    membership: Membership, integration_id: UUID, ip: str | None = None
) -> Integration:
    integration = get(membership, integration_id)
    _require_manage(membership, integration.provider)
    access.ensure_writable(membership.project)
    if integration.status != IntegrationStatus.DISCONNECTED:
        _revoke_quietly(integration)
        _wipe(integration)
        activity.log(
            membership.project,
            membership.user,
            actions.INTEGRATION_DISCONNECTED,
            actions.ENTITY_INTEGRATION,
            integration.pk,
            {"provider": integration.provider},
            ip,
        )
    return integration


def mark_uninstalled(integration: Integration) -> None:
    """The provider told us (or an API error proved) the token is gone: wipe it
    and stop sending, without trying to revoke it again."""
    if integration.status != IntegrationStatus.DISCONNECTED:
        _wipe(integration)


def disconnect_all(project: Project) -> int:
    """Revoke and wipe every live integration of a project (before it is purged)."""
    live = Integration.objects.filter(project=project).exclude(
        status=IntegrationStatus.DISCONNECTED
    )
    count = 0
    for integration in live:
        _revoke_quietly(integration)
        _wipe(integration)
        count += 1
    return count


def reactivate(integration: Integration) -> Integration:
    """Called by a provider's install flow after a successful reconnect."""
    integration.status = IntegrationStatus.ACTIVE
    integration.consecutive_failures = 0
    integration.paused_until = None
    integration.attention_notified = False
    integration.save(
        update_fields=[
            "status",
            "consecutive_failures",
            "paused_until",
            "attention_notified",
            "updated_at",
        ]
    )
    delivery_service.requeue_pending(integration.pk)
    return integration


def deliveries(
    membership: Membership, integration_id: UUID, status: str | None = None
) -> QuerySet[DeliveryAttempt]:
    integration = get(membership, integration_id)
    if not can_view_logs(membership, integration.provider):
        raise PermissionDeniedException(
            project_messages.PERMISSION_DENIED,
            error_code=project_error_codes.PERMISSION_DENIED,
        )
    queryset = DeliveryAttempt.objects.filter(integration=integration)
    if status:
        queryset = queryset.filter(status=status)
    return queryset


@transaction.atomic
def replay(
    membership: Membership, integration_id: UUID, delivery_id: UUID
) -> DeliveryAttempt:
    integration = get(membership, integration_id)
    _require_manage(membership, integration.provider)
    access.ensure_writable(membership.project)
    delivery = (
        DeliveryAttempt.objects.select_for_update(of=("self",))
        .filter(integration=integration, pk=delivery_id)
        .first()
    )
    if delivery is None:
        raise _not_found(messages.DELIVERY_NOT_FOUND, error_codes.DELIVERY_NOT_FOUND)
    if delivery.status != DeliveryStatus.FAILED:
        raise ConflictException(
            messages.NOT_REPLAYABLE, error_code=error_codes.NOT_REPLAYABLE
        )
    if integration.status != IntegrationStatus.ACTIVE:
        raise ConflictException(
            messages.INTEGRATION_INACTIVE, error_code=error_codes.INTEGRATION_INACTIVE
        )
    return delivery_service.replay(delivery)
