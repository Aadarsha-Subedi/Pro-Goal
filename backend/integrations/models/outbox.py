from uuid import uuid7

from django.db import models

from integrations.constants.events import EventType, Source


class OutboxEvent(models.Model):
    """A project event, saved in the same transaction as the change that caused
    it. A worker forwards it afterwards (at least once)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="outbox_events"
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    payload = models.JSONField(default=dict)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.WEB)
    # Lets scheduled jobs emit an event only once (for example a due date alert).
    dedupe_key = models.CharField(max_length=200, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatch_attempts = models.PositiveSmallIntegerField(default=0)
    dispatch_error = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["created_at"],
                condition=models.Q(dispatched_at__isnull=True),
                name="outbox_undispatched_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.project_id})"
