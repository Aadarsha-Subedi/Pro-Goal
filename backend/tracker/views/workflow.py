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
from tracker.responses import PriorityData, StatusData
from tracker.serializers.workflow import (
    MoveToSerializer,
    PriorityCreateSerializer,
    PriorityUpdateSerializer,
    StatusCreateSerializer,
    StatusUpdateSerializer,
)
from tracker.services import access, priority_service, status_service
from tracker.views.base import ip_of, paginated


class StatusListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return paginated(request, status_service.list_statuses(membership), StatusData)

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = StatusCreateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        status = status_service.create(membership, ip=ip_of(request), **data)
        return ResourceCreatedResponse(
            data=StatusData(status), message=messages.STATUS_CREATED
        )


class StatusDetailView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, status_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return SuccessResponse(
            data=StatusData(access.get_status(membership.project, status_id))
        )

    def patch(
        self, request: Request, project_id: UUID, status_id: UUID
    ) -> BaseResponse:
        data = StatusUpdateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        status = status_service.update(membership, status_id, data, ip_of(request))
        return ResourceUpdatedResponse(
            data=StatusData(status), message=messages.STATUS_UPDATED
        )

    def delete(
        self, request: Request, project_id: UUID, status_id: UUID
    ) -> BaseResponse:
        data = MoveToSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        status_service.delete(
            membership, status_id, data.get("move_to"), ip_of(request)
        )
        return SuccessResponse(message=messages.STATUS_DELETED)


class PriorityListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return paginated(
            request, priority_service.list_priorities(membership), PriorityData
        )

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = PriorityCreateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        priority = priority_service.create(membership, ip=ip_of(request), **data)
        return ResourceCreatedResponse(
            data=PriorityData(priority), message=messages.PRIORITY_CREATED
        )


class PriorityDetailView(CsrfProtectedView):
    def get(
        self, request: Request, project_id: UUID, priority_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return SuccessResponse(
            data=PriorityData(access.get_priority(membership.project, priority_id))
        )

    def patch(
        self, request: Request, project_id: UUID, priority_id: UUID
    ) -> BaseResponse:
        data = PriorityUpdateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        priority = priority_service.update(
            membership, priority_id, data, ip_of(request)
        )
        return ResourceUpdatedResponse(
            data=PriorityData(priority), message=messages.PRIORITY_UPDATED
        )

    def delete(
        self, request: Request, project_id: UUID, priority_id: UUID
    ) -> BaseResponse:
        data = MoveToSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        priority_service.delete(
            membership, priority_id, data.get("move_to"), ip_of(request)
        )
        return SuccessResponse(message=messages.PRIORITY_DELETED)
