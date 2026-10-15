"""
URL configuration for config project.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API (one include per feature app)
    path("api/", include("accounts.urls")),
    path("api/", include("projects.urls")),
    path("api/", include("tracker.urls")),
    path("api/", include("attachments.urls")),
    path("api/", include("security.urls")),
    path("api/", include("integrations.urls")),
]


if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    ]

    def trigger_error(request):
        """Raise on purpose to verify the Sentry integration."""
        return 1 / 0

    urlpatterns += [path("sentry-debug/", trigger_error)]
