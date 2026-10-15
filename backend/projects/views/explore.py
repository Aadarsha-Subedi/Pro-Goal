from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import (
    BaseResponse,
    ListResponseData,
    ResourceListResponse,
    SuccessResponse,
)
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from projects.constants import messages
from projects.models import Membership
from projects.responses import (
    ExploreProjectData,
    JoinedData,
    JoinSubmittedData,
    TagSuggestionData,
)
from projects.serializers.explore import (
    ExploreQuerySerializer,
    TagSuggestionQuerySerializer,
)
from projects.services import explore_service, join_service
from projects.views.base import ip_of, paginated


class ExploreListView(CsrfProtectedView):
    """GET /api/explore/: projects that chose to be listed."""

    def get(self, request: Request) -> BaseResponse:
        query = ExploreQuerySerializer.parse(request.query_params.dict())
        queryset = explore_service.listed_projects(
            request.user,
            q=query.get("q"),
            # `tag` may repeat (?tag=a&tag=b): any of them.
            tags=request.query_params.getlist("tag"),
            starts_after=query.get("starts_after"),
            ends_before=query.get("ends_before"),
        )
        states = explore_service.my_request_states(request.user)
        return paginated(
            request, queryset, lambda p: ExploreProjectData(p, states.get(p.pk))
        )


class ExploreTagView(CsrfProtectedView):
    def get(self, request: Request) -> BaseResponse:
        query = TagSuggestionQuerySerializer.parse(request.query_params.dict())
        tags = explore_service.suggest_tags(query.get("q"))
        return ResourceListResponse(
            data=ListResponseData([TagSuggestionData(t) for t in tags])
        )


class ExploreJoinView(CsrfProtectedView):
    """POST /api/explore/<project_id>/join-request/: ask to join without a code."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "explore_join"

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        result = join_service.request_to_join_listed(
            request.user, project_id, ip_of(request)
        )
        if isinstance(result, Membership):
            return SuccessResponse(
                data=JoinedData(result),
                message=messages.JOINED_PROJECT,
                status_code=201,
            )
        join_request = result
        return SuccessResponse(
            data=JoinSubmittedData(join_request),
            message=messages.JOIN_REQUEST_SENT,
            status_code=201,
        )
