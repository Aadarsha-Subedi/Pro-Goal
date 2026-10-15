from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import AccountView, CsrfProtectedView
from common.response.domain import (
    BaseResponse,
    ListResponseData,
    ResourceCreatedResponse,
    ResourceListResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from integrations.models import LinkedAccount
from integrations.services import linking
from integrations.slack import constants, oauth
from integrations.slack.responses import (
    ChannelData,
    MappingData,
    PreferenceData,
    UrlData,
)
from integrations.slack.serializers.slack import (
    MappingCreateSerializer,
    MappingUpdateSerializer,
    PreferenceUpdateSerializer,
)
from integrations.slack.services import mapping_service, preference_service
from projects.services import access
from projects.views.base import ip_of


class InstallView(CsrfProtectedView):
    """GET .../integrations/slack/install/: the "Add to Slack" address."""

    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        return SuccessResponse(data=UrlData(oauth.install_url(membership)))


class ChannelListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        channels = mapping_service.list_channels(membership)
        return ResourceListResponse(
            data=ListResponseData([ChannelData(c) for c in channels])
        )


class MappingListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        items = mapping_service.list_mappings(membership)
        return ResourceListResponse(
            data=ListResponseData([MappingData(m) for m in items])
        )

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = MappingCreateSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        mapping = mapping_service.create(
            membership, data["channel_id"], data["enabled_events"], ip_of(request)
        )
        return ResourceCreatedResponse(
            data=MappingData(mapping), message=constants.MAPPING_SAVED
        )


class MappingDetailView(CsrfProtectedView):
    def patch(
        self, request: Request, project_id: UUID, mapping_id: UUID
    ) -> BaseResponse:
        data = MappingUpdateSerializer.parse(request.data)
        membership = access.get_membership(request.user, project_id)
        mapping = mapping_service.update(
            membership, mapping_id, data["enabled_events"], ip_of(request)
        )
        return ResourceUpdatedResponse(
            data=MappingData(mapping), message=constants.MAPPING_SAVED
        )

    def delete(
        self, request: Request, project_id: UUID, mapping_id: UUID
    ) -> BaseResponse:
        membership = access.get_membership(request.user, project_id)
        mapping_service.delete(membership, mapping_id, ip_of(request))
        return SuccessResponse(message=constants.MAPPING_DELETED)


class LinkView(AccountView):
    """GET /api/me/integrations/slack/link/: the "Sign in with Slack" address
    and where this person is already linked. DELETE unlinks."""

    def get(self, request: Request) -> BaseResponse:
        linked = list(
            LinkedAccount.objects.filter(
                user=request.user, provider=constants.PROVIDER
            ).values_list("external_workspace_id", flat=True)
        )
        return SuccessResponse(
            data=UrlData(oauth.link_url(request.user), {"linked_workspaces": linked})
        )

    def delete(self, request: Request) -> BaseResponse:
        linking.unlink(request.user, constants.PROVIDER)
        return SuccessResponse(message=constants.LINK_REMOVED)


class NotificationPreferenceView(AccountView):
    def get(self, request: Request) -> BaseResponse:
        items = preference_service.list_for(request.user)
        return ResourceListResponse(
            data=ListResponseData([PreferenceData(i) for i in items])
        )

    def put(self, request: Request) -> BaseResponse:
        data = PreferenceUpdateSerializer.parse(request.data)
        unknown = [
            e
            for e in data["preferences"]
            if e not in {x.value for x in constants.PERSONAL_EVENTS}
        ]
        if unknown:
            from common.exception.domain import ValidationException

            raise ValidationException(
                errors=[
                    {
                        "field": f"preferences.{name}",
                        "message": constants.UNKNOWN_EVENT.format(name=name),
                    }
                    for name in unknown
                ],
                error_code=constants.UNKNOWN_EVENT_CODE,
            )
        items = preference_service.update(request.user, dict(data["preferences"]))
        return ResourceListResponse(
            data=ListResponseData([PreferenceData(i) for i in items]),
            message=constants.PREFERENCES_SAVED,
        )
