from dataclasses import dataclass

from accounts.models import User
from accounts.services import avatar_service
from common.response.domain import BaseResponseData
from projects import permissions
from projects.constants.permissions import GROUPS, OWNER_ONLY_ACTIONS, PRESETS, REGISTRY
from projects.models import (
    ActivityLog,
    JoinRequest,
    Membership,
    OwnershipTransfer,
    Project,
)
from projects.services import activity_feed, project_service


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def public_user(user: User) -> dict:
    """What every member may see about another member."""
    return {
        "id": str(user.pk),
        "first_name": user.first_name,
        "avatar_url": avatar_service.avatar_url(user),
    }


def _private_user(user: User) -> dict:
    """What the owner sees about members and requesters."""
    return {
        **public_user(user),
        "last_name": user.last_name,
        "display_name": user.display_name,
        "email": user.email,
    }


@dataclass(frozen=True)
class ProjectData(BaseResponseData):
    """A project as seen by one member (`membership`)."""

    membership: Membership
    member_count: int
    pending_transfer: OwnershipTransfer | None = None

    def to_dict(self) -> dict:
        membership = self.membership
        project = membership.project
        is_owner = membership.is_owner
        data = {
            "id": str(project.pk),
            "name": project.name,
            "description": project.description,
            "task_key": project.task_key,
            "start_date": _iso(project.start_date),
            "end_date": _iso(project.end_date),
            "tags": sorted(tag.name for tag in project.tags.all()),
            "is_listed": project.is_listed,
            "is_demo": project.is_demo,
            "is_archived": project.is_archived,
            "archived_at": _iso(project.archived_at),
            "deletion_scheduled_for": _iso(
                project_service.deletion_scheduled_for(project)
            ),
            "owner": public_user(project.owner),
            "member_count": self.member_count,
            "role": "owner" if is_owner else "member",
            "permissions": permissions.permissions_for(membership),
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
        if is_owner:
            data["join_code"] = project.join_code
            data["pending_transfer"] = (
                TransferData(self.pending_transfer).to_dict()
                if self.pending_transfer
                else None
            )
        return data


@dataclass(frozen=True)
class MemberData(BaseResponseData):
    member: Membership
    viewer_is_owner: bool

    def to_dict(self) -> dict:
        user = self.member.user
        return {
            **(_private_user(user) if self.viewer_is_owner else public_user(user)),
            "is_owner": self.member.is_owner,
            "joined_at": self.member.joined_at.isoformat(),
        }


@dataclass(frozen=True)
class JoinRequestData(BaseResponseData):
    """Owner's view of a request: includes the requester's name and email."""

    request: JoinRequest

    def to_dict(self) -> dict:
        request = self.request
        return {
            "id": str(request.pk),
            "status": request.status,
            "user": _private_user(request.user),
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat(),
            "decided_at": _iso(request.decided_at),
        }


@dataclass(frozen=True)
class JoinSubmittedData(BaseResponseData):
    """Requester's view: only the project name and description."""

    request: JoinRequest

    def to_dict(self) -> dict:
        request = self.request
        return {
            "id": str(request.pk),
            "status": request.status,
            "expires_at": request.expires_at.isoformat(),
            "project": {
                "name": request.project.name,
                "description": request.project.description,
            },
        }


@dataclass(frozen=True)
class JoinedData(BaseResponseData):
    """Joined a demo project at once (no approval)."""

    membership: Membership

    def to_dict(self) -> dict:
        project = self.membership.project
        return {
            "status": "joined",
            "project": {"id": str(project.pk), "name": project.name},
        }


@dataclass(frozen=True)
class TransferData(BaseResponseData):
    transfer: OwnershipTransfer

    def to_dict(self) -> dict:
        transfer = self.transfer
        return {
            "id": str(transfer.pk),
            "project": {"id": str(transfer.project_id)},
            "from_user": public_user(transfer.from_user),
            "to_user": public_user(transfer.to_user),
            "status": transfer.status,
            "expires_at": transfer.expires_at.isoformat(),
        }


@dataclass(frozen=True)
class IncomingTransferData(BaseResponseData):
    transfer: OwnershipTransfer

    def to_dict(self) -> dict:
        data = TransferData(self.transfer).to_dict()
        data["project"] = {
            "id": str(self.transfer.project_id),
            "name": self.transfer.project.name,
        }
        return data


@dataclass(frozen=True)
class RegistryData(BaseResponseData):
    """Every permission with its description, the presets and the actions that
    always stay with the owner. The frontend keeps no copy of this."""

    def to_dict(self) -> dict:
        return {
            "groups": list(GROUPS),
            "permissions": [
                {
                    "code": info.code,
                    "label": info.label,
                    "description": info.description,
                    "group": info.group,
                }
                for info in REGISTRY
            ],
            "presets": [
                {
                    "name": preset.name,
                    "label": preset.label,
                    "description": preset.description,
                    "permissions": sorted(preset.codes),
                }
                for preset in PRESETS.values()
            ],
            "owner_only": list(OWNER_ONLY_ACTIONS),
        }


@dataclass(frozen=True)
class MemberGrantsData(BaseResponseData):
    member: Membership
    codes: list[str]

    def to_dict(self) -> dict:
        from projects.services import grant_service

        return {
            "user": public_user(self.member.user),
            "is_owner": self.member.is_owner,
            "permissions": self.codes,
            "preset": grant_service.preset_name_for(set(self.codes)),
        }


@dataclass(frozen=True)
class ActivityData(BaseResponseData):
    """One activity entry. The IP address is never included."""

    entry: ActivityLog

    def to_dict(self) -> dict:
        entry = self.entry
        actor = (
            public_user(entry.actor)
            if entry.actor
            else {"id": None, "first_name": "Deleted user", "avatar_url": None}
        )
        return {
            "id": str(entry.pk),
            "actor": actor,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": str(entry.entity_id) if entry.entity_id else None,
            "changes": activity_feed.shorten(entry.changes),
            "created_at": entry.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ExploreProjectData(BaseResponseData):
    """A listed project as a stranger sees it. No join code, no emails, no
    tasks or notes."""

    project: Project
    my_request: dict | None = None

    def to_dict(self) -> dict:
        project = self.project
        return {
            "id": str(project.pk),
            "name": project.name,
            "description": project.description,
            "tags": sorted(pt.tag.name for pt in project.project_tags.all()),
            "start_date": _iso(project.start_date),
            "end_date": _iso(project.end_date),
            "owner": public_user(project.owner),
            "member_count": project.member_count,
            "is_demo": project.is_demo,
            "listed_at": _iso(project.listed_at),
            "my_request": self.my_request or {"state": "none", "cooldown_until": None},
        }


@dataclass(frozen=True)
class TagSuggestionData(BaseResponseData):
    tag: dict

    def to_dict(self) -> dict:
        return self.tag
