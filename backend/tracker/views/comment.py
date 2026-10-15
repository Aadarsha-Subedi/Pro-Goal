from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import (
    BaseResponse,
    ResourceCreatedResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from projects.services import access as project_access
from tracker.constants import messages
from tracker.responses import CommentData, PreferenceData
from tracker.serializers.comment import CommentSerializer
from tracker.serializers.preference import PreferenceSerializer
from tracker.services import access, comment_service, preference_service
from tracker.views.base import ip_of, paginated


class CommentListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        return paginated(request, comment_service.list_comments(task), CommentData)

    def post(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        data = CommentSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        comment = comment_service.create(membership, task, data["body"], ip_of(request))
        return ResourceCreatedResponse(
            data=CommentData(comment), message=messages.COMMENT_CREATED
        )


class CommentDetailView(CsrfProtectedView):
    def patch(
        self, request: Request, project_id: UUID, number: int, comment_id: UUID
    ) -> BaseResponse:
        data = CommentSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        comment = comment_service.edit(
            membership, task, comment_id, data["body"], ip_of(request)
        )
        return ResourceUpdatedResponse(
            data=CommentData(comment), message=messages.COMMENT_UPDATED
        )

    def delete(
        self, request: Request, project_id: UUID, number: int, comment_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        comment = comment_service.delete(membership, task, comment_id, ip_of(request))
        return SuccessResponse(
            data=CommentData(comment), message=messages.COMMENT_DELETED
        )


class KanbanPreferenceView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return SuccessResponse(data=PreferenceData(preference_service.get(membership)))

    def put(self, request: Request, project_id: UUID) -> BaseResponse:
        data = PreferenceSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        preference = preference_service.save(membership, **data)
        return ResourceUpdatedResponse(
            data=PreferenceData(preference), message=messages.PREFERENCE_SAVED
        )
