from django.contrib import admin

from integrations.models import (
    DeliveryAttempt,
    InboundWebhook,
    Integration,
    OutboxEvent,
)


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("provider", "project", "status", "consecutive_failures")
    exclude = ("encrypted_token",)


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "project", "source", "created_at", "dispatched_at")
    list_filter = ("event_type", "source")


@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = ("event_type", "integration", "status", "attempt", "created_at")
    list_filter = ("status",)


@admin.register(InboundWebhook)
class InboundWebhookAdmin(admin.ModelAdmin):
    list_display = ("provider", "kind", "delivery_id", "status", "received_at")
    list_filter = ("provider", "status")
