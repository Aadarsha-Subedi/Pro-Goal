from rest_framework.request import Request

from accounts.views.base import AccountView
from common.response.domain import BaseResponse
from projects.views.base import paginated
from security.responses import SecurityEventData
from security.serializers.events import EventQuerySerializer
from security.services import query


class SecurityEventListView(AccountView):
    """GET /api/me/security-events/: the caller's own security log."""

    def get(self, request: Request) -> BaseResponse:
        params = EventQuerySerializer.parse(request.query_params.dict())
        queryset = query.events_for(request.user, params.get("event_type"))
        return paginated(request, queryset, SecurityEventData)
