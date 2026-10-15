from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel


class MemberPermission(TimeStampModel):
    """One permission code granted to one member. The owner never has rows:
    they hold every code implicitly."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    membership = models.ForeignKey(
        "projects.Membership", on_delete=models.CASCADE, related_name="grants"
    )
    code = models.CharField(max_length=64)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "code"], name="unique_member_permission"
            )
        ]

    @property
    def granted_at(self):
        return self.created_at

    def __str__(self) -> str:
        return f"{self.membership_id}: {self.code}"
