"""The shared, read-only demo projects: the system user that owns them, the
project shells, and joining new accounts to them as viewers."""

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from projects.models import Membership, Project
from projects.services import join_service, project_service

SYSTEM_USER_EMAIL = "demo@system.invalid"
SYSTEM_USER_NAME = "Pro-Goal Demo"


def get_system_user() -> User:
    user = User.objects.filter(is_system=True).first()
    if user is not None:
        return user
    return User.objects.create_user(
        SYSTEM_USER_EMAIL,
        password=None,
        first_name="Pro-Goal",
        last_name="Demo",
        display_name=SYSTEM_USER_NAME,
        is_system=True,
    )


@transaction.atomic
def get_or_create_demo_project(spec: dict) -> tuple[Project, bool]:
    """The demo project for `spec["key"]`, creating its shell if missing. Task
    content is added by the caller (see tracker's demo seeding)."""
    project = Project.all_objects.filter(demo_key=spec["key"]).first()
    if project is not None:
        return project, False
    owner = get_system_user()
    membership = project_service.create(
        owner,
        name=spec["name"],
        task_key=spec["task_key"],
        description=spec["description"],
        tags=spec["tags"],
    )
    project = membership.project
    project.demo_key = spec["key"]
    project.is_listed = True
    project.listed_at = timezone.now()
    project.save(update_fields=["demo_key", "is_listed", "listed_at", "updated_at"])
    return project, True


def demo_projects():
    return Project.objects.filter(demo_key__isnull=False, archived_at__isnull=True)


def join_all_demo_projects(user: User) -> list[Membership]:
    """Make `user` a viewer of every demo project. Safe to repeat."""
    if user.is_system:
        return []
    return [join_service.join_demo(user, project) for project in demo_projects()]
