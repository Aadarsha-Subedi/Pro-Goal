"""Endpoints Slack (or the browser coming back from Slack) calls. None of them
use the API session login except the two browser callbacks."""

import json
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from common.exception.domain import AppException
from common.throttling.scoped import AuthScopedThrottle
from integrations.services import webhook_service
from integrations.slack import constants, oauth, signature


def _frontend(path: str, **query: str) -> HttpResponseRedirect:
    suffix = f"?{urlencode(query)}" if query else ""
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}{path}{suffix}")


def _project_path(state: str) -> str | None:
    try:
        data = signing.loads(
            state, salt=constants.STATE_SALT, max_age=constants.STATE_MAX_AGE_SECONDS
        )
    except signing.BadSignature:
        return None
    project = data.get("project")
    return f"/projects/{project}/integrations" if project else None


@require_GET
def install_callback(request: HttpRequest) -> HttpResponseRedirect:
    state, code = request.GET.get("state", ""), request.GET.get("code", "")
    path = _project_path(state) or "/settings/integrations"
    if request.GET.get("error") or not code:
        return _frontend(
            path, slack="error", reason=request.GET.get("error", "no_code")
        )
    if not request.user.is_authenticated:
        return _frontend(path, slack="error", reason="not_signed_in")
    try:
        oauth.complete_install(code, state, request.user)
    except AppException as exc:
        return _frontend(path, slack="error", reason=exc.error_code)
    return _frontend(path, slack="connected")


@require_GET
def link_callback(request: HttpRequest) -> HttpResponseRedirect:
    state, code = request.GET.get("state", ""), request.GET.get("code", "")
    path = "/settings/integrations"
    if request.GET.get("error") or not code:
        return _frontend(
            path, slack="error", reason=request.GET.get("error", "no_code")
        )
    if not request.user.is_authenticated:
        return _frontend(path, slack="error", reason="not_signed_in")
    try:
        oauth.complete_link(code, state, request.user)
    except AppException as exc:
        return _frontend(path, slack="error", reason=exc.error_code)
    return _frontend(path, slack="linked")


class _SlackInbound(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes: list = []
    throttle_classes = [AuthScopedThrottle]
    throttle_scope = "webhook"
    kind = "webhook"

    def post(self, request: Request) -> HttpResponse:
        webhook_service.receive(constants.PROVIDER, request._request, kind=self.kind)
        # Slack wants an empty 200 within 3 seconds; the work happens in a worker.
        return HttpResponse(status=200)


class CommandsView(_SlackInbound):
    kind = "commands"


class EventsView(_SlackInbound):
    kind = "events"

    def post(self, request: Request) -> HttpResponse:
        signature.verify(request._request)
        try:
            body = json.loads(request._request.body)
        except ValueError:
            body = {}
        # Slack checks the address by sending a challenge to echo back.
        if body.get("type") == "url_verification":
            return JsonResponse({"challenge": body.get("challenge", "")})
        return super().post(request)
