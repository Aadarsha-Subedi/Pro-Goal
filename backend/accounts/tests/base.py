from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services.tokens import make_verification_token

PASSWORD = "Correct-Horse-9"


class ApiTestCase(TestCase):
    """Client that enforces CSRF like a browser: fetches the cookie first and
    sends it back as X-CSRFToken on every call."""

    def setUp(self) -> None:
        cache.clear()
        mail.outbox.clear()
        self.client = APIClient(
            enforce_csrf_checks=True,
            HTTP_USER_AGENT="Mozilla/5.0 (X11; Linux) Firefox/130",
        )
        self.client.get("/api/csrf/")

    def _headers(self) -> dict:
        return {"HTTP_X_CSRFTOKEN": self.client.cookies["csrftoken"].value}

    # TestCase wraps tests in a transaction, so on_commit hooks (queued emails)
    # only run when captured explicitly.
    def post(self, path: str, data: dict | None = None, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                path, data or {}, format="json", **self._headers(), **extra
            )

    def patch(self, path: str, data: dict):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.patch(path, data, format="json", **self._headers())

    def delete(self, path: str):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.delete(path, **self._headers())

    def make_user(
        self, email: str = "ada@example.com", verified: bool = True, **extra
    ) -> User:
        user = User.objects.create_user(
            email=email,
            password=extra.pop("password", PASSWORD),
            first_name=extra.pop("first_name", "Ada"),
            last_name=extra.pop("last_name", "Lovelace"),
            display_name=extra.pop("display_name", "Ada"),
            **extra,
        )
        EmailAddress.objects.create(
            user=user, email=email, primary=True, verified=verified
        )
        return user

    def verification_token(self, user: User) -> str:
        return make_verification_token(EmailAddress.objects.get(user=user).pk)

    def login(self, email: str = "ada@example.com", password: str = PASSWORD, **extra):
        return self.post(
            "/api/auth/login/", {"email": email, "password": password, **extra}
        )
