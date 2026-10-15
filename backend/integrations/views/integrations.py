from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import (
    BaseResponse,
    ListResponseData,
    ResourceListResponse,
    SuccessResponse,
)
from integrations.constants import messages
from integrations.responses import DeliveryData, IntegrationData
from integrations.serializers.integration import DeliveryQuerySerializer
from integrations.services import integration_service
from projects.services import access
from projects.views.base import ip_of, paginated


class IntegrationListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        items = integration_service.list_for(membership)
        return ResourceListResponse(
            data=ListResponseData([IntegrationData(i) for i in items])
        )


class IntegrationDetailView(CsrfProtectedView):
    def delete(
        self, request: Request, project_id: UUID, integration_id: UUID
    ) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        integration = integration_service.disconnect(
            membership, integration_id, ip_of(request)
        )
        return SuccessResponse(
            data=IntegrationData(integration), message=messages.INTEGRATION_DISCONNECTED
        )


class DeliveryListView(CsrfProtectedView):
    def get(
        self, request: Request, project_id: UUID, integration_id: UUID
    ) -> BaseResponse:
        query = DeliveryQuerySerializer.parse(request.query_params.dict())
        membership = access.get_membership(request.user, project_id)
        queryset = integration_service.deliveries(
            membership, integration_id, query.get("status")
        )
        return paginated(request, queryset, DeliveryData)


class DeliveryReplayView(CsrfProtectedView):
    def post(
        self,
        request: Request,
        project_id: UUID,
        integration_id: UUID,
        delivery_id: UUID,
    ) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        delivery = integration_service.replay(membership, integration_id, delivery_id)
        return SuccessResponse(
            data=DeliveryData(delivery), message=messages.DELIVERY_REPLAYED
        )
