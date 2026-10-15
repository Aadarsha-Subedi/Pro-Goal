from accounts.models import User
from integrations.models import LinkedAccount


def link(
    user: User,
    provider: str,
    external_user_id: str,
    external_workspace_id: str = "",
    token: str = "",
) -> LinkedAccount:
    """Tie a provider account to `user`. Linking the same provider account again
    to another user moves it (the latest sign-in wins)."""
    LinkedAccount.objects.filter(
        provider=provider,
        external_workspace_id=external_workspace_id,
        external_user_id=external_user_id,
    ).exclude(user=user).delete()
    account, _ = LinkedAccount.objects.update_or_create(
        user=user,
        provider=provider,
        external_workspace_id=external_workspace_id,
        defaults={"external_user_id": external_user_id},
    )
    account.set_token(token)
    account.save(update_fields=["encrypted_token", "updated_at"])
    return account


def unlink(user: User, provider: str) -> int:
    deleted, _ = LinkedAccount.objects.filter(user=user, provider=provider).delete()
    return deleted


def find_user(
    provider: str, external_workspace_id: str, external_user_id: str
) -> User | None:
    account = (
        LinkedAccount.objects.select_related("user")
        .filter(
            provider=provider,
            external_workspace_id=external_workspace_id,
            external_user_id=external_user_id,
        )
        .first()
    )
    return account.user if account else None
