from django.urls import path

from integrations.slack.views import api, public

P = "projects/<uuid:project_id>/integrations/slack"

urlpatterns = [
    path(f"{P}/install/", api.InstallView.as_view()),
    path(f"{P}/channels/", api.ChannelListView.as_view()),
    path(f"{P}/mappings/", api.MappingListView.as_view()),
    path(f"{P}/mappings/<uuid:mapping_id>/", api.MappingDetailView.as_view()),
    path("me/integrations/slack/link/", api.LinkView.as_view()),
    path("me/notification-preferences/", api.NotificationPreferenceView.as_view()),
    path("integrations/slack/install/callback/", public.install_callback),
    path("integrations/slack/link/callback/", public.link_callback),
    path("integrations/slack/commands/", public.CommandsView.as_view()),
    path("integrations/slack/events/", public.EventsView.as_view()),
]
