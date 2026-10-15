import hmac
import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from rest_framework import exceptions as drf_exceptions
from rest_framework.parsers import FormParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.constants import messages
from accounts.responses import CsrfData, UserData
from accounts.serializers.auth import (
    EmailChangeConfirmSerializer,
    EmailOnlySerializer,
    GoogleLoginSerializer,
    GoogleRedirectSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    SignupSerializer,
    VerifyEmailSerializer,
)
from accounts.services import (
    auth_service,
    email_change_service,
    google_service,
    password_service,
    signup_service,
    verification_service,
)
from accounts.views.base import AccountView, CsrfProtectedView, PublicAuthView
from common.email.constants import NEUTRAL_MESSAGE
from common.exception.domain import AppException
from common.response.domain import (
    BaseResponse,
    SuccessResponse,
)
from common.throttling.scoped import AnonThrottle, AuthScopedThrottle

logger = logging.getLogger(__name__)

# The login page sets this cookie to "<nonce>.<0|1>" (1 = remember me) before it sends the browser
# to Google, and Google echoes the same value back as `state`. It must be SameSite=None because
# Google's callback is a cross-site POST.
GOOGLE_STATE_COOKIE = "pg_google_state"
GOOGLE_SUCCESS_PATH = "/app"
GOOGLE_FAILURE_PATH = "/login?google_error="


class CsrfView(CsrfProtectedView):
    """GET /api/csrf/ sets the CSRF cookie."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonThrottle]

    def get(self, request: Request) -> BaseResponse:
        token = get_token(request)
        return SuccessResponse(data=CsrfData(token), message=messages.CSRF_COOKIE_SET)


class SignupView(PublicAuthView):
    throttle_scope = "signup"

    def post(self, request: Request) -> BaseResponse:
        data = SignupSerializer.parse(request.data)
        signup_service.sign_up(**data)
        return SuccessResponse(message=NEUTRAL_MESSAGE, status_code=202)


class VerifyEmailView(PublicAuthView):
    throttle_scope = "email_verify"

    def post(self, request: Request) -> BaseResponse:
        data = VerifyEmailSerializer.parse(request.data)
        verification_service.verify_email(data["token"])
        return SuccessResponse(message=messages.EMAIL_VERIFIED)


class ResendVerificationView(PublicAuthView):
    throttle_scope = "email_resend"

    def post(self, request: Request) -> BaseResponse:
        data = EmailOnlySerializer.parse(request.data)
        verification_service.resend_verification(data["email"])
        return SuccessResponse(message=NEUTRAL_MESSAGE, status_code=202)


class LoginView(PublicAuthView):
    throttle_scope = "login"

    def post(self, request: Request) -> BaseResponse:
        data = LoginSerializer.parse(request.data)
        user = auth_service.log_in(request._request, **data)
        return SuccessResponse(data=UserData(user), message=messages.LOGGED_IN)


class GoogleLoginView(PublicAuthView):
    throttle_scope = "google"

    def post(self, request: Request) -> BaseResponse:
        data = GoogleLoginSerializer.parse(request.data)
        user = google_service.google_login(
            request._request,
            token=data["id_token"],
            remember_me=data["remember_me"],
        )
        return SuccessResponse(data=UserData(user), message=messages.LOGGED_IN)


class GoogleRedirectView(APIView):
    """Landing point after the browser was sent to Google's sign-in page.
    Google POSTs the ID token as a form (`response_mode=form_post`), so this
    answers with a redirect back into the app instead of the API envelope. It
    cannot carry our CSRF header: the `state` value, which must match the
    `pg_google_state` cookie, binds the reply to the browser that started the
    sign-in, and the token's nonce must match too. The reply is always a 302
    to `/app` or `/login`."""

    request_serializers = {"post": GoogleRedirectSerializer}
    authentication_classes: list = []
    permission_classes = [AllowAny]
    parser_classes = [FormParser]
    throttle_classes = [AnonThrottle, AuthScopedThrottle]
    throttle_scope = "google"

    def post(self, request: Request) -> HttpResponse:
        cookie = request.COOKIES.get(GOOGLE_STATE_COOKIE, "")
        posted = str(request.data.get("state", ""))
        if not cookie or not hmac.compare_digest(cookie.encode(), posted.encode()):
            logger.warning(
                "Google redirect rejected: state cookie %s, state field %s",
                "present but different" if cookie else "missing",
                "present" if posted else "missing",
            )
            return self._failed("google_failed")
        # Google adds fields of its own (authuser, prompt, ...); keep only the two we need.
        data = GoogleRedirectSerializer.parse(
            {"id_token": request.data.get("id_token", ""), "state": posted}
        )
        nonce, _, remember = data["state"].partition(".")
        google_service.google_login(
            request._request,
            token=data["id_token"],
            remember_me=remember == "1",
            nonce=nonce,
        )
        return self._done(HttpResponseRedirect(GOOGLE_SUCCESS_PATH))

    def handle_exception(self, exc: Exception) -> HttpResponse:
        if isinstance(exc, drf_exceptions.Throttled):
            return self._failed("rate_limited")
        if isinstance(exc, (AppException, drf_exceptions.APIException)):
            logger.warning(
                "Google redirect rejected: %s",
                getattr(exc, "error_code", None) or type(exc).__name__,
            )
            return self._failed("google_failed")
        logger.exception("Google redirect sign-in failed")
        return self._failed("google_failed")

    def _failed(self, code: str) -> HttpResponse:
        return self._done(HttpResponseRedirect(GOOGLE_FAILURE_PATH + code))

    @staticmethod
    def _done(response: HttpResponse) -> HttpResponse:
        response.delete_cookie(GOOGLE_STATE_COOKIE, samesite="None")
        return response


class LogoutView(AccountView):
    def post(self, request: Request) -> BaseResponse:
        data = LogoutSerializer.parse(request.data)
        auth_service.log_out(request._request, **data)
        return SuccessResponse(message=messages.LOGGED_OUT)


class PasswordResetRequestView(PublicAuthView):
    throttle_scope = "password_reset"

    def post(self, request: Request) -> BaseResponse:
        data = EmailOnlySerializer.parse(request.data)
        password_service.request_reset(data["email"])
        return SuccessResponse(message=NEUTRAL_MESSAGE, status_code=202)


class PasswordResetConfirmView(PublicAuthView):
    throttle_scope = "password_reset"

    def post(self, request: Request) -> BaseResponse:
        data = PasswordResetConfirmSerializer.parse(request.data)
        password_service.confirm_reset(request._request, **data)
        return SuccessResponse(message=messages.PASSWORD_UPDATED)


class PasswordChangeView(AccountView):
    def post(self, request: Request) -> BaseResponse:
        data = PasswordChangeSerializer.parse(request.data)
        password_service.change_password(
            request._request,
            request.user,
            current_password=data.get("current_password"),
            new_password=data["new_password"],
        )
        return SuccessResponse(message=messages.PASSWORD_CHANGED)


class EmailChangeConfirmView(PublicAuthView):
    """POST /api/auth/email-change/confirm/: the link from the new address."""

    throttle_scope = "email_verify"

    def post(self, request: Request) -> BaseResponse:
        data = EmailChangeConfirmSerializer.parse(request.data)
        email_change_service.confirm_change(request._request, data["token"])
        return SuccessResponse(message=messages.EMAIL_CHANGED)
