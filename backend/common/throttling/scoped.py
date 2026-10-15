from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class AnonThrottle(AnonRateThrottle):
    """60/min per IP for anonymous callers (rate set in REST_FRAMEWORK)."""

    scope = "anon"


class UserThrottle(UserRateThrottle):
    """600/min per signed-in user (rate set in REST_FRAMEWORK)."""

    scope = "user"


class AuthScopedThrottle(ScopedRateThrottle):
    """Per-view named limits (login, signup, password_reset, ...). A view opts
    in by setting `throttle_scope`. Keyed by IP for anonymous callers."""


class ProjectThrottle(SimpleRateThrottle):
    """Caps all traffic to one project (every member together) so a single busy
    project cannot starve the others. Applies only to routes that carry a
    `project_id` URL kwarg; everything else is ignored."""

    scope = "project"

    def get_cache_key(self, request, view) -> str | None:
        project_id = getattr(view, "kwargs", {}).get("project_id")
        if project_id is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(project_id)}
