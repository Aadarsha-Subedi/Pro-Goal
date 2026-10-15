from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel
from integrations import crypto
from integrations.constants.statuses import IntegrationStatus


class EncryptedTokenMixin(models.Model):
    """Stores a provider token Fernet-encrypted. Never expose the field."""

    encrypted_token = models.TextField(blank=True)

    class Meta:
        abstract = True

    def set_token(self, plain: str) -> None:
        self.encrypted_token = crypto.encrypt(plain) if plain else ""

    def get_token(self) -> str:
        return crypto.decrypt(self.encrypted_token) if self.encrypted_token else ""


class Integration(EncryptedTokenMixin, TimeStampModel):
    """A project's connection to one provider (for example a Slack workspace)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="integrations"
    )
    provider = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=IntegrationStatus.choices,
        default=IntegrationStatus.ACTIVE,
    )
    installed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    external_workspace_id = models.CharField(max_length=64, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    consecutive_failures = models.PositiveIntegerField(default=0)
    paused_until = models.DateTimeField(null=True, blank=True)
    attention_notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "provider"],
                condition=~models.Q(status="disconnected"),
                name="one_live_integration_per_provider",
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider} ({self.project_id})"


class LinkedAccount(EncryptedTokenMixin, TimeStampModel):
    """A person's own account at a provider, linked to their user. Commands
    from the provider run as this user, with their permissions."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="linked_accounts",
    )
    provider = models.CharField(max_length=32)
    external_user_id = models.CharField(max_length=64)
    external_workspace_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_workspace_id", "external_user_id"],
                name="unique_external_account",
            ),
            models.UniqueConstraint(
                fields=["user", "provider", "external_workspace_id"],
                name="one_link_per_user_and_workspace",
            ),
        ]
