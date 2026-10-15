from datetime import timedelta
from uuid import UUID

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import User
from common.exception.domain import (
    ConflictException,
    NotFoundException,
    ThrottledException,
)
from projects import permissions
from projects.constants import actions, error_codes, limits, messages
from projects.constants.cache import (
    WRONG_CODE_IP_KEY,
    WRONG_CODE_USER_KEY,
    WRONG_CODE_WINDOW_SECONDS,
)
from projects.constants.permissions import MEMBER_APPROVE
from projects.constants.statuses import JoinRequestStatus
from projects.models import JoinRequest, Membership, Project
from projects.services import (
    access,
    activity,
    email_service,
    grant_service,
    join_code,
)


def _wrong_code_keys(user: User, ip: str | None) -> list[str]:
    keys = [WRONG_CODE_USER_KEY.format(user_id=user.pk)]
    if ip:
        keys.append(WRONG_CODE_IP_KEY.format(ip=ip))
    return keys


def _ensure_not_throttled(keys: list[str]) -> None:
    if any((cache.get(key) or 0) >= limits.WRONG_CODES_PER_HOUR for key in keys):
        raise ThrottledException(
            messages.JOIN_CODE_THROTTLED, error_code=error_codes.JOIN_CODE_THROTTLED
        )


def _record_wrong_code(keys: list[str]) -> None:
    for key in keys:
        cache.add(key, 0, WRONG_CODE_WINDOW_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, WRONG_CODE_WINDOW_SECONDS)


def submit(user: User, raw_code: str, ip: str | None = None) -> JoinRequest:
    keys = _wrong_code_keys(user, ip)
    _ensure_not_throttled(keys)
    project = (
        Project.objects.filter(
            join_code=join_code.normalize(raw_code), demo_key__isnull=True
        )
        .select_related("owner")
        .first()
    )
    if project is None:
        _record_wrong_code(keys)
        raise NotFoundException(
            messages.INVALID_JOIN_CODE, error_code=error_codes.INVALID_JOIN_CODE
        )
    return _create_request(user, project, ip)


def request_to_join_listed(
    user: User, project_id: UUID, ip: str | None = None
) -> JoinRequest | Membership:
    """Ask to join a project from the explore page (no code). Only listed,
    live, unarchived projects can be found this way; anything else is a 404 so
    unlisted projects are not revealed. The usual limits apply. Demo projects
    need no approval: the caller becomes a viewer straight away."""
    project = (
        Project.objects.filter(pk=project_id, is_listed=True, archived_at__isnull=True)
        .select_related("owner")
        .first()
    )
    if project is None:
        raise NotFoundException(
            messages.PROJECT_NOT_FOUND, error_code=error_codes.PROJECT_NOT_FOUND
        )
    if project.is_demo:
        return join_demo(user, project, ip)
    return _create_request(user, project, ip)


@transaction.atomic
def join_demo(user: User, project: Project, ip: str | None = None) -> Membership:
    """Make `user` a viewer of a demo project. Idempotent for existing members."""
    membership, created = Membership.objects.get_or_create(user=user, project=project)
    if created:
        activity.log(
            project,
            user,
            actions.MEMBER_JOINED,
            actions.ENTITY_MEMBER,
            user.pk,
            ip=ip,
        )
    return membership


@transaction.atomic
def _create_request(user: User, project: Project, ip: str | None) -> JoinRequest:
    access.ensure_writable(project)
    if Membership.objects.filter(user=user, project=project).exists():
        raise ConflictException(
            messages.ALREADY_MEMBER, error_code=error_codes.ALREADY_MEMBER
        )
    _expire_stale(user=user)
    own = JoinRequest.objects.filter(user=user, project=project)
    if own.filter(status=JoinRequestStatus.PENDING).exists():
        raise ConflictException(
            messages.JOIN_REQUEST_PENDING, error_code=error_codes.JOIN_REQUEST_PENDING
        )
    retry_after = timezone.now() - timedelta(hours=limits.JOIN_REQUEST_RETRY_HOURS)
    if own.filter(
        status=JoinRequestStatus.REJECTED, decided_at__gt=retry_after
    ).exists():
        raise ConflictException(
            messages.JOIN_REQUEST_COOLDOWN,
            error_code=error_codes.JOIN_REQUEST_COOLDOWN,
        )
    open_count = JoinRequest.objects.filter(
        user=user, status=JoinRequestStatus.PENDING
    ).count()
    if open_count >= limits.MAX_OPEN_JOIN_REQUESTS:
        raise ConflictException(
            messages.TOO_MANY_OPEN_REQUESTS,
            error_code=error_codes.TOO_MANY_OPEN_REQUESTS,
        )
    try:
        with transaction.atomic():
            request = JoinRequest.objects.create(
                user=user,
                project=project,
                expires_at=timezone.now()
                + timedelta(days=limits.JOIN_REQUEST_EXPIRY_DAYS),
            )
    except IntegrityError:
        raise ConflictException(
            messages.JOIN_REQUEST_PENDING, error_code=error_codes.JOIN_REQUEST_PENDING
        ) from None
    activity.log(
        project,
        user,
        actions.JOIN_REQUESTED,
        actions.ENTITY_JOIN_REQUEST,
        request.pk,
        ip=ip,
    )
    email_service.send_join_request_email(project, user)
    return request


def _expire_stale(**filters) -> int:
    return JoinRequest.objects.filter(
        status=JoinRequestStatus.PENDING, expires_at__lte=timezone.now(), **filters
    ).update(status=JoinRequestStatus.EXPIRED)


def list_requests(
    membership: Membership, status: str = JoinRequestStatus.PENDING
) -> QuerySet[JoinRequest]:
    permissions.require_permission(membership, MEMBER_APPROVE)
    return JoinRequest.objects.filter(
        project=membership.project, status=status
    ).select_related("user")


def _get_decidable(membership: Membership, request_id: UUID) -> JoinRequest:
    permissions.require_permission(membership, MEMBER_APPROVE)
    access.ensure_writable(membership.project)
    request = (
        JoinRequest.objects.select_for_update(of=("self",))
        .select_related("user", "project__owner")
        .filter(pk=request_id, project=membership.project)
        .first()
    )
    if request is None:
        raise NotFoundException(
            messages.JOIN_REQUEST_NOT_FOUND,
            error_code=error_codes.JOIN_REQUEST_NOT_FOUND,
        )
    if request.status != JoinRequestStatus.PENDING:
        raise ConflictException(
            messages.JOIN_REQUEST_NOT_PENDING,
            error_code=error_codes.JOIN_REQUEST_NOT_PENDING,
        )
    if request.expires_at <= timezone.now():
        request.status = JoinRequestStatus.EXPIRED
        request.save(update_fields=["status", "updated_at"])
        raise ConflictException(
            messages.JOIN_REQUEST_EXPIRED, error_code=error_codes.JOIN_REQUEST_EXPIRED
        )
    return request


def _decide(request: JoinRequest, status: str, decider: User) -> None:
    request.status = status
    request.decided_by = decider
    request.decided_at = timezone.now()
    request.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])


@transaction.atomic
def approve(
    membership: Membership,
    request_id: UUID,
    grants: set[str] | None = None,
    ip: str | None = None,
) -> JoinRequest:
    """Approve and optionally give the newcomer starting permissions (none by
    default)."""
    request = _get_decidable(membership, request_id)
    codes = grant_service.check_starting_grants(membership, grants)
    _decide(request, JoinRequestStatus.APPROVED, membership.user)
    newcomer, _ = Membership.objects.get_or_create(
        user=request.user, project=request.project
    )
    grant_service.give_starting_grants(newcomer, membership, codes)
    activity.log(
        request.project,
        membership.user,
        actions.JOIN_APPROVED,
        actions.ENTITY_JOIN_REQUEST,
        request.pk,
        {"user": str(request.user_id)},
        ip,
    )
    email_service.send_join_decision_email(request.project, request.user, True)
    return request


@transaction.atomic
def reject(
    membership: Membership, request_id: UUID, ip: str | None = None
) -> JoinRequest:
    request = _get_decidable(membership, request_id)
    _decide(request, JoinRequestStatus.REJECTED, membership.user)
    activity.log(
        request.project,
        membership.user,
        actions.JOIN_REJECTED,
        actions.ENTITY_JOIN_REQUEST,
        request.pk,
        {"user": str(request.user_id)},
        ip,
    )
    email_service.send_join_decision_email(request.project, request.user, False)
    return request


def expire_join_requests() -> int:
    return _expire_stale()
