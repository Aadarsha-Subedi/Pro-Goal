from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import BaseResponse, SuccessResponse
from projects.constants import messages
from projects.responses import JoinRequestData, JoinSubmittedData, MemberData
from projects.serializers.member import (
    JoinRequestQuerySerializer,
    JoinSerializer,
    RemoveMemberSerializer,
)
from projects.serializers.permission import ApproveSerializer
from projects.services import access, grant_service, join_service, membership_service
from projects.views.base import ip_of, paginated


class MemberListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        queryset = membership_service.list_members(membership)
        return paginated(
            request, queryset, lambda m: MemberData(m, membership.is_owner)
        )


class MemberDetailView(CsrfProtectedView):
    def delete(self, request: Request, project_id: UUID, user_id: UUID) -> BaseResponse:
        data = RemoveMemberSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        membership_service.remove(membership, user_id, data["reassign"], ip_of(request))
        return SuccessResponse(message=messages.MEMBER_REMOVED)


class LeaveProjectView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        membership_service.leave(membership, ip_of(request))
        return SuccessResponse(message=messages.LEFT_PROJECT)


class JoinView(CsrfProtectedView):
    def post(self, request: Request) -> BaseResponse:
        data = JoinSerializer.parse(request.data)
        join_request = join_service.submit(request.user, data["code"], ip_of(request))
        return SuccessResponse(
            data=JoinSubmittedData(join_request),
            message=messages.JOIN_REQUEST_SENT,
            status_code=201,
        )


class JoinRequestListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        query = JoinRequestQuerySerializer.parse(request.query_params.dict())
        membership = access.get_membership(request.user, project_id)
        queryset = join_service.list_requests(membership, query["status"])
        return paginated(request, queryset, JoinRequestData)


class JoinRequestApproveView(CsrfProtectedView):
    def post(
        self, request: Request, project_id: UUID, request_id: UUID
    ) -> BaseResponse:
        data = ApproveSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        grants = grant_service.resolve(data.get("permissions"), data.get("preset"))
        join_request = join_service.approve(
            membership, request_id, grants, ip_of(request)
        )
        return SuccessResponse(
            data=JoinRequestData(join_request), message=messages.JOIN_REQUEST_APPROVED
        )


class JoinRequestRejectView(CsrfProtectedView):
    def post(
        self, request: Request, project_id: UUID, request_id: UUID
    ) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        join_request = join_service.reject(membership, request_id, ip_of(request))
        return SuccessResponse(
            data=JoinRequestData(join_request), message=messages.JOIN_REQUEST_REJECTED
        )
