from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import BaseResponse, SuccessResponse
from projects.constants import messages
from projects.responses import IncomingTransferData, TransferData
from projects.serializers.transfer import TransferStartSerializer
from projects.services import access, transfer_service
from projects.views.base import ip_of, paginated, reauth_of


class ProjectTransferView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = TransferStartSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        transfer = transfer_service.start(
            membership, data["to_user"], reauth_of(data), ip_of(request)
        )
        return SuccessResponse(
            data=TransferData(transfer),
            message=messages.TRANSFER_STARTED,
            status_code=201,
        )


class ProjectTransferCancelView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        transfer = transfer_service.cancel(membership, ip_of(request))
        return SuccessResponse(
            data=TransferData(transfer), message=messages.TRANSFER_CANCELLED
        )


class IncomingTransferListView(CsrfProtectedView):
    def get(self, request: Request) -> BaseResponse:
        queryset = transfer_service.incoming(request.user).order_by("-created_at")
        return paginated(request, queryset, IncomingTransferData)


class TransferAcceptView(CsrfProtectedView):
    def post(self, request: Request, transfer_id: UUID) -> BaseResponse:
        transfer = transfer_service.accept(request.user, transfer_id, ip_of(request))
        return SuccessResponse(
            data=TransferData(transfer), message=messages.TRANSFER_ACCEPTED
        )
