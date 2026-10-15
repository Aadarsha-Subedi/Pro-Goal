from collections.abc import Callable

from accounts.models import User

# Features register a callable run when an account first becomes usable (email
# verified, or created through Google). Projects joins the user to the demo
# projects this way.
UserActivatedHook = Callable[[User], None]
user_activated: list[UserActivatedHook] = []


def run_user_activated(user: User) -> None:
    for hook in user_activated:
        hook(user)
