from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from common.response.domain import BaseResponse, SuccessResponse
from common.throttling.scoped import AuthScopedThrottle
from integrations.constants import messages
from integrations.services import webhook_service


class WebhookView(APIView):
    """POST /api/integrations/<provider>/webhook/: the generic entry point for
    provider calls. No session and no CSRF (the provider cannot have either);
    the provider's own signature check is the authentication."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes: list = []
    throttle_classes = [AuthScopedThrottle]
    throttle_scope = "webhook"

    def post(self, request: Request, provider: str) -> BaseResponse:
        webhook_service.receive(provider, request._request)
        return SuccessResponse(message=messages.WEBHOOK_ACCEPTED, status_code=202)
