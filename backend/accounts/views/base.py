from rest_framework import exceptions as drf_exceptions
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.constants import error_codes, messages
from common.exception.domain import PermissionDeniedException
from common.throttling.scoped import AnonThrottle, AuthScopedThrottle, UserThrottle


class CsrfProtectedView(APIView):
    """DRF only enforces CSRF for authenticated requests. Anonymous POSTs
    (login, signup, ...) must carry a valid CSRF token too, so this checks it
    on every unsafe method."""

    authentication_classes = [SessionAuthentication]

    def initial(self, request: Request, *args, **kwargs) -> None:
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            try:
                SessionAuthentication().enforce_csrf(request)
            except drf_exceptions.PermissionDenied as exc:
                raise PermissionDeniedException(
                    messages.CSRF_FAILED, error_code=error_codes.CSRF_FAILED
                ) from exc
        super().initial(request, *args, **kwargs)


class PublicAuthView(CsrfProtectedView):
    """Anonymous endpoint with a named rate limit (`throttle_scope`)."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonThrottle, AuthScopedThrottle]


class AccountView(CsrfProtectedView):
    """Signed-in endpoint that stays reachable with an incomplete profile or a
    pending deletion (profile, logout, sessions, deletion cancel)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserThrottle]
