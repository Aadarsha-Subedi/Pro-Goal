from collections.abc import Callable

from django.db.models import QuerySet
from rest_framework.request import Request

from accounts.services.reauth_service import Reauth
from accounts.services.session_service import client_ip
from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    BaseResponseData,
    ListResponseData,
    ResourceListResponse,
)


def ip_of(request: Request) -> str | None:
    return client_ip(request._request)


def reauth_of(data: dict) -> Reauth:
    return Reauth(password=data.get("password"), id_token=data.get("id_token"))


def paginated(
    request: Request,
    queryset: QuerySet,
    make: Callable[[object], BaseResponseData],
    extra_meta: dict | None = None,
) -> ResourceListResponse:
    paginator = OffsetBasedPagination()
    page = paginator.paginate_queryset(queryset, request)
    return ResourceListResponse(
        data=ListResponseData([make(item) for item in page]),
        meta={**paginator.get_meta(), **(extra_meta or {})},
    )
