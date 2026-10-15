from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import (
    BaseResponse,
    ResourceCreatedResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from projects.constants import messages
from projects.models import Membership
from projects.responses import ProjectData
from projects.serializers.project import (
    ProjectCopySerializer,
    ProjectCreateSerializer,
    ProjectUpdateSerializer,
    ReauthSerializer,
)
from projects.services import access, copy_service, project_service, transfer_service
from projects.views.base import ip_of, paginated, reauth_of


def _project_data(membership: Membership) -> ProjectData:
    project = membership.project
    return ProjectData(
        membership,
        member_count=Membership.objects.filter(project=project).count(),
        pending_transfer=(
            transfer_service.pending_for_project(project)
            if membership.is_owner
            else None
        ),
    )


def _list_item(membership: Membership) -> ProjectData:
    return ProjectData(membership, member_count=membership.member_count)


class ProjectListView(CsrfProtectedView):
    def get(self, request: Request) -> BaseResponse:
        queryset = project_service.list_memberships(request.user).prefetch_related(
            "project__tags"
        )
        return paginated(request, queryset, _list_item)

    def post(self, request: Request) -> BaseResponse:
        data = ProjectCreateSerializer.parse(request.data)
        membership = project_service.create(request.user, ip=ip_of(request), **data)
        return ResourceCreatedResponse(
            data=_project_data(membership), message=messages.PROJECT_CREATED
        )


class ProjectDetailView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id, allow_deleted=True)
        return SuccessResponse(data=_project_data(membership))

    def patch(self, request: Request, project_id: UUID) -> BaseResponse:
        data = ProjectUpdateSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        project_service.update(membership, data, ip_of(request))
        return ResourceUpdatedResponse(
            data=_project_data(membership), message=messages.PROJECT_UPDATED
        )

    def delete(self, request: Request, project_id: UUID) -> BaseResponse:
        data = ReauthSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        project_service.soft_delete(membership, reauth_of(data), ip_of(request))
        return SuccessResponse(
            data=_project_data(membership), message=messages.PROJECT_DELETION_SCHEDULED
        )


class ProjectArchiveView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        project_service.archive(membership, ip_of(request))
        return SuccessResponse(
            data=_project_data(membership), message=messages.PROJECT_ARCHIVED
        )


class ProjectUnarchiveView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        project_service.unarchive(membership, ip_of(request))
        return SuccessResponse(
            data=_project_data(membership), message=messages.PROJECT_UNARCHIVED
        )


class ProjectRestoreView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id, allow_deleted=True)
        project_service.restore(membership, ip_of(request))
        return SuccessResponse(
            data=_project_data(membership), message=messages.PROJECT_RESTORED
        )


class JoinCodeRegenerateView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = ReauthSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        project_service.regenerate_join_code(
            membership, reauth_of(data), ip_of(request)
        )
        return SuccessResponse(
            data=_project_data(membership), message=messages.JOIN_CODE_REGENERATED
        )


class ProjectCopyView(CsrfProtectedView):
    """POST /api/projects/<id>/copy/: copy a demo project into the caller's own."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "project_copy"

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = ProjectCopySerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        created = copy_service.copy_project(
            membership, data.get("name"), ip_of(request)
        )
        return ResourceCreatedResponse(
            data=_project_data(created), message=messages.PROJECT_COPIED
        )
