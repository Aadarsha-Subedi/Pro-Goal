from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from attachments.constants import messages
from attachments.responses import (
    AttachmentData,
    DownloadData,
    UploadData,
    UsageData,
)
from attachments.serializers.attachment import (
    ListQuerySerializer,
    UploadRequestSerializer,
)
from attachments.services import attachment_service, quota_service
from common.exception.domain import ValidationException
from common.response.domain import (
    BaseResponse,
    ResourceCreatedResponse,
    SuccessResponse,
)
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from projects.services import access as project_access
from projects.views.base import ip_of, paginated


class UploadUrlView(CsrfProtectedView):
    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "attachment_upload"

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = UploadRequestSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        attachment, url, expires_in = attachment_service.request_upload(
            membership, **data
        )
        return ResourceCreatedResponse(
            data=UploadData(attachment, url, expires_in),
            message=messages.UPLOAD_URL_READY,
        )


class AttachmentListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        query = ListQuerySerializer.parse(request.query_params.dict())
        chosen = [name for name in ("task", "note", "comment") if name in query]
        if len(chosen) > 1:
            raise ValidationException(
                errors=[
                    {"field": None, "message": "Choose one of task, note or comment."}
                ]
            )
        membership = project_access.get_membership(request.user, project_id)
        kind = chosen[0] if chosen else None
        queryset = attachment_service.list_for_target(
            membership, target_type=kind, target=query.get(kind) if kind else None
        )
        return paginated(request, queryset, AttachmentData)


class AttachmentConfirmView(CsrfProtectedView):
    def post(
        self, request: Request, project_id: UUID, attachment_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        attachment = attachment_service.confirm(
            membership, attachment_id, ip_of(request)
        )
        return SuccessResponse(
            data=AttachmentData(attachment), message=messages.ATTACHMENT_CONFIRMED
        )


class AttachmentDownloadView(CsrfProtectedView):
    def get(
        self, request: Request, project_id: UUID, attachment_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        url, expires_in = attachment_service.download_url(membership, attachment_id)
        return SuccessResponse(data=DownloadData(url, expires_in))


class AttachmentDetailView(CsrfProtectedView):
    def delete(
        self, request: Request, project_id: UUID, attachment_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        attachment_service.delete(membership, attachment_id, ip_of(request))
        return SuccessResponse(message=messages.ATTACHMENT_DELETED)


class ProjectStorageView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return SuccessResponse(
            data=UsageData(quota_service.project_usage(membership.project))
        )


class MyStorageView(CsrfProtectedView):
    def get(self, request: Request) -> BaseResponse:
        return SuccessResponse(data=UsageData(quota_service.user_usage(request.user)))
