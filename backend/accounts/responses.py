from dataclasses import dataclass

from accounts.models import User, UserSession
from accounts.services import avatar_service, deletion_service
from common.response.domain import BaseResponseData


@dataclass(frozen=True)
class UserData(BaseResponseData):
    user: User

    def to_dict(self) -> dict:
        user = self.user
        purge_at = deletion_service.scheduled_purge_at(user)
        return {
            "id": str(user.pk),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "avatar_url": avatar_service.avatar_url(user),
            "needs_profile": not user.is_profile_complete,
            "tour_completed": user.tour_completed_at is not None,
            "deletion_scheduled_for": purge_at.isoformat() if purge_at else None,
            "created_at": user.created_at.isoformat(),
        }


@dataclass(frozen=True)
class CsrfData(BaseResponseData):
    token: str

    def to_dict(self) -> dict:
        return {"csrf_token": self.token}


@dataclass(frozen=True)
class SessionData(BaseResponseData):
    session: UserSession
    current_key: str | None = None

    def to_dict(self) -> dict:
        session = self.session
        return {
            "id": str(session.pk),
            "device_name": session.device_name,
            "ip": session.ip,
            "user_agent": session.user_agent,
            "created_at": session.created_at.isoformat(),
            "last_seen_at": session.last_seen_at.isoformat(),
            "remember_me": session.remember_me,
            "is_current": session.session_key == self.current_key,
        }
