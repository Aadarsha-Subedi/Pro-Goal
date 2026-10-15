from uuid import uuid7

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from common.models.delete import SoftDeleteManager, SoftDeleteModel
from common.models.timestamp import TimeStampModel


class UserManager(BaseUserManager):
    """Sees every row, including accounts pending deletion: login inside the
    7-day grace window must find the user in order to cancel the deletion.
    Use `User.visible` for the soft-delete-aware view."""

    use_in_migrations = True

    def _create(self, email: str, password: str | None, **extra) -> User:
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email: str, password: str, **extra) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, TimeStampModel, SoftDeleteModel):
    """Email-login account. Social-only users have an unusable password.
    `is_deleted`/`deleted_at` mark an account in its deletion grace period."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    display_name = models.CharField(max_length=150)

    avatar = models.CharField(max_length=512, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # Owns the shared demo projects. Never logs in, never emailed, never deleted.
    is_system = models.BooleanField(default=False)
    # Set when the user finishes or skips the onboarding walkthrough.
    tour_completed_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "display_name"]

    # `objects` sees every row (including accounts pending deletion) and its
    # queryset hard-deletes; `visible` hides soft-deleted accounts.
    objects = UserManager()
    visible = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        default_manager_name = "objects"

    @property
    def is_profile_complete(self) -> bool:
        return bool(self.first_name and self.last_name and self.display_name)

    def __str__(self) -> str:
        return self.email
