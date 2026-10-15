import logging

from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from common.response.domain import (
    BaseResponse,
    BaseResponseData,
    ErrorResponse,
    SuccessResponse,
)
from common.throttling.scoped import AnonThrottle

PROBE_KEY = "health-probe"
logger = logging.getLogger(__name__)


class _Ok(BaseResponseData):
    def to_dict(self) -> dict:
        return {"status": "ok"}


class HealthView(APIView):
    """GET /api/health/: 200 only if the database and the cache answer. For
    uptime monitors; exposes nothing else."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonThrottle]

    def get(self, request: Request) -> BaseResponse:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            cache.set(PROBE_KEY, 1, 10)
            if cache.get(PROBE_KEY) != 1:
                raise RuntimeError("cache round-trip failed")
        except Exception:
            logger.exception("Health check failed")
            return ErrorResponse(
                message="Service unavailable.",
                error_code="service_unavailable",
                status_code=503,
            )
        return SuccessResponse(data=_Ok())
