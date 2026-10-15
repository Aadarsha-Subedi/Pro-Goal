from django.urls import include, path

from integrations.views import integrations, webhook

P = "projects/<uuid:project_id>/integrations"

urlpatterns = [
    path("", include("integrations.slack.urls")),
    path("integrations/<slug:provider>/webhook/", webhook.WebhookView.as_view()),
    path(f"{P}/", integrations.IntegrationListView.as_view()),
    path(f"{P}/<uuid:integration_id>/", integrations.IntegrationDetailView.as_view()),
    path(
        f"{P}/<uuid:integration_id>/deliveries/",
        integrations.DeliveryListView.as_view(),
    ),
    path(
        f"{P}/<uuid:integration_id>/deliveries/<uuid:delivery_id>/replay/",
        integrations.DeliveryReplayView.as_view(),
    ),
]
