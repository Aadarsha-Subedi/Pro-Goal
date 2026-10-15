from django.urls import path

from security.views import events, health

urlpatterns = [
    path("health/", health.HealthView.as_view()),
    path("me/security-events/", events.SecurityEventListView.as_view()),
]
