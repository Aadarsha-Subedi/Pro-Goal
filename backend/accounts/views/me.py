from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request

from accounts.constants import messages
from accounts.responses import SessionData, UserData
from accounts.serializers.auth import EmailChangeSerializer
from accounts.serializers.profile import AvatarUploadSerializer, ProfileUpdateSerializer
from accounts.services import (
    avatar_service,
    deletion_service,
    email_change_service,
    profile_service,
    session_service,
)
from accounts.services.reauth_service import Reauth
from accounts.views.base import AccountView
from common.response.domain import (
    BaseResponse,
    ListResponseData,
    ResourceListResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from security.constants.events import EventType
from security.services import event_service


class MeView(AccountView):
    def get(self, request: Request) -> BaseResponse:
        return SuccessResponse(data=UserData(request.user))

    def patch(self, request: Request) -> BaseResponse:
        data = ProfileUpdateSerializer.parse(request.data)
        user = profile_service.update_profile(request.user, **data)
        return ResourceUpdatedResponse(data=UserData(user))


class TourView(AccountView):
    """POST /api/me/tour/ marks the walkthrough done; DELETE resets it."""

    def post(self, request: Request) -> BaseResponse:
        user = profile_service.set_tour_completed(request.user, True)
        return ResourceUpdatedResponse(data=UserData(user))

    def delete(self, request: Request) -> BaseResponse:
        user = profile_service.set_tour_completed(request.user, False)
        return ResourceUpdatedResponse(data=UserData(user))


class AvatarView(AccountView):
    parser_classes = [MultiPartParser]
    throttle_scope = "upload"

    def post(self, request: Request) -> BaseResponse:
        data = AvatarUploadSerializer.parse(request.data)
        upload = data["file"]
        user = avatar_service.set_avatar(request.user, upload.read())
        return ResourceUpdatedResponse(
            data=UserData(user), message=messages.AVATAR_UPDATED
        )

    def delete(self, request: Request) -> BaseResponse:
        user = avatar_service.remove_avatar(request.user)
        return ResourceUpdatedResponse(
            data=UserData(user), message=messages.AVATAR_REMOVED
        )


class SessionListView(AccountView):
    def get(self, request: Request) -> BaseResponse:
        current = request.session.session_key
        sessions = session_service.list_sessions(request.user)
        return ResourceListResponse(
            data=ListResponseData([SessionData(s, current) for s in sessions])
        )


class SessionDetailView(AccountView):
    def delete(self, request: Request, session_id) -> BaseResponse:
        session_service.revoke(request.user, str(session_id))
        event_service.record(request._request, request.user, EventType.SESSION_REVOKED)
        return SuccessResponse(message=messages.SESSION_REVOKED)


class DeleteAccountView(AccountView):
    def post(self, request: Request) -> BaseResponse:
        user = deletion_service.start_deletion(request.user, request._request)
        return SuccessResponse(
            data=UserData(user),
            message=messages.ACCOUNT_DELETION_SCHEDULED,
        )


class CancelDeletionView(AccountView):
    def post(self, request: Request) -> BaseResponse:
        user = deletion_service.cancel_deletion(request.user, request._request)
        return SuccessResponse(
            data=UserData(user), message=messages.ACCOUNT_DELETION_CANCELLED
        )


class EmailChangeView(AccountView):
    """POST /api/me/email/: ask to change the login address."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "email_change"

    def post(self, request: Request) -> BaseResponse:
        data = EmailChangeSerializer.parse(request.data)
        email_change_service.request_change(
            request.user,
            data["new_email"],
            Reauth(password=data.get("password"), id_token=data.get("id_token")),
        )
        return SuccessResponse(message=messages.EMAIL_CHANGE_REQUESTED, status_code=202)
