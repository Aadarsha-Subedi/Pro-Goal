from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import BaseResponse
from projects.responses import ActivityData
from projects.serializers.activity import ActivityQuerySerializer
from projects.services import access, activity_feed
from projects.views.base import paginated


class ActivityListView(CsrfProtectedView):
    """GET /api/projects/<id>/activity/: what happened in the project (everyone
    sees their own actions; `activity.view` holders see all)."""

    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        query = ActivityQuerySerializer.parse(request.query_params.dict())
        membership = access.get_membership(request.user, project_id)
        filters = {k: v for k, v in query.items() if k not in ("limit", "offset")}
        queryset = activity_feed.feed(membership, **filters)
        return paginated(
            request,
            queryset,
            ActivityData,
            {"scope": "all" if activity_feed.can_view_all(membership) else "own"},
        )
