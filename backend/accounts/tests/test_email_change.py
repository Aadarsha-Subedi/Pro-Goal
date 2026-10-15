import re
from datetime import timedelta
from unittest import mock

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import PendingEmailChange, User
from accounts.services import google_service
from accounts.tasks import purge_stale_email_changes
from accounts.tests.base import PASSWORD, ApiTestCase
from accounts.tests.test_account import FakeVerifier, profile
from security.models import SecurityEvent

NEW = "ada.new@example.com"


class EmailChangeTests(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = self.make_user()
        self.login()
        mail.outbox.clear()

    def request_change(self, **extra):
        body = {"new_email": NEW, "password": PASSWORD, **extra}
        return self.post("/api/me/email/", body)

    def token_from_mail(self) -> str:
        message = next(m for m in mail.outbox if m.to == [NEW])
        return re.search(r"token=([\w.:\-]+)", message.body).group(1)

    def confirm(self, token: str, client: APIClient | None = None):
        client = client or APIClient(enforce_csrf_checks=True)
        client.get("/api/csrf/")
        with self.captureOnCommitCallbacks(execute=True):
            return client.post(
                "/api/auth/email-change/confirm/",
                {"token": token},
                format="json",
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            )

    def test_request_sends_a_link_to_the_new_address_and_warns_the_old_one(self):
        response = self.request_change()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(PendingEmailChange.objects.get().new_email, NEW)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, sorted(["ada@example.com", NEW]))
        warning = next(m for m in mail.outbox if m.to == ["ada@example.com"])
        self.assertIn("a***@example.com", warning.body)
        self.assertNotIn(
            NEW, warning.body
        )  # only a masked form reaches the old address
        # Nothing about the account changed yet.
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ada@example.com")

    def test_the_link_alone_changes_the_address_from_another_browser(self):
        self.request_change()
        token = self.token_from_mail()
        mail.outbox.clear()
        response = self.confirm(token)  # a fresh client: no session at all
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, NEW)
        addresses = list(
            EmailAddress.objects.filter(user=self.user).values_list(
                "email", "primary", "verified"
            )
        )
        self.assertEqual(addresses, [(NEW, True, True)])
        self.assertFalse(PendingEmailChange.objects.exists())
        self.assertEqual([m.to for m in mail.outbox], [["ada@example.com"]])
        self.assertIn("was changed", mail.outbox[0].body)
        self.assertTrue(
            SecurityEvent.objects.filter(
                user=self.user, event_type="email_changed"
            ).exists()
        )

    def test_sessions_end_and_only_the_new_address_logs_in(self):
        self.request_change()
        self.confirm(self.token_from_mail())
        self.assertEqual(self.client.get("/api/me/").status_code, 401)
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/csrf/")
        self.assertEqual(self.login(email="ada@example.com").status_code, 401)
        self.assertEqual(self.login(email=NEW).status_code, 200)

    def test_wrong_or_missing_confirmation_changes_nothing(self):
        wrong = self.request_change(password="Wrong-Password-1")
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(wrong.json()["code"], "reauth_failed")
        missing = self.post("/api/me/email/", {"new_email": NEW})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["code"], "reauth_required")
        self.assertFalse(PendingEmailChange.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_same_address_is_refused(self):
        response = self.request_change(new_email="ADA@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "same_email")

    def test_a_taken_address_gets_the_same_neutral_answer_and_no_mail(self):
        self.make_user(NEW)
        response = self.request_change()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json()["message"],
            self.request_change(new_email="free@example.com").json()["message"],
        )
        self.assertFalse(PendingEmailChange.objects.filter(new_email=NEW).exists())
        self.assertEqual([m for m in mail.outbox if m.to == [NEW]], [])

    def test_a_new_request_replaces_the_pending_one(self):
        self.request_change(new_email="first@example.com")
        first = next(m for m in mail.outbox if m.to == ["first@example.com"])
        first_token = re.search(r"token=([\w.:\-]+)", first.body).group(1)
        self.request_change()
        self.assertEqual(PendingEmailChange.objects.get().new_email, NEW)
        self.assertEqual(self.confirm(first_token).status_code, 401)
        self.assertEqual(self.confirm(self.token_from_mail()).status_code, 200)

    def test_bad_links(self):
        self.request_change()
        token = self.token_from_mail()
        self.assertEqual(
            self.confirm("garbage").json()["code"], "email_change_token_invalid"
        )
        self.assertEqual(
            self.confirm(token[:-2] + "xx").json()["code"], "email_change_token_invalid"
        )
        from accounts.services.tokens import make_verification_token

        other_purpose = make_verification_token(1)
        self.assertEqual(
            self.confirm(other_purpose).json()["code"], "email_change_token_invalid"
        )
        with override_settings(EMAIL_VERIFICATION_TIMEOUT=-1):
            expired = self.confirm(token)
        self.assertEqual(expired.json()["code"], "email_change_token_expired")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ada@example.com")

    def test_a_link_works_once(self):
        self.request_change()
        token = self.token_from_mail()
        self.assertEqual(self.confirm(token).status_code, 200)
        self.assertEqual(
            self.confirm(token).json()["code"], "email_change_token_invalid"
        )

    def test_if_the_address_was_taken_meanwhile_the_link_fails(self):
        self.request_change()
        token = self.token_from_mail()
        self.make_user(NEW, first_name="Other")
        response = self.confirm(token)
        self.assertEqual(response.json()["code"], "email_change_token_invalid")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ada@example.com")

    def test_requires_login_and_is_rate_limited(self):
        self.assertEqual(
            APIClient().post("/api/me/email/", {}, format="json").status_code, 401
        )
        with mock.patch.dict(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"email_change": "2/min"},
        ):
            codes = [
                self.request_change(new_email=f"n{i}@example.com").status_code
                for i in range(3)
            ]
        self.assertEqual(codes, [202, 202, 429])

    def test_stale_requests_are_purged(self):
        self.request_change()
        PendingEmailChange.objects.update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        self.assertEqual(purge_stale_email_changes.delay().get(), 1)
        self.assertFalse(PendingEmailChange.objects.exists())


class GoogleAccountEmailChangeTests(ApiTestCase):
    def test_a_google_only_account_confirms_with_a_fresh_google_token_and_still_signs_in_with_google(
        self,
    ):
        user = self.make_user()
        SocialAccount.objects.create(user=user, provider="google", uid="g-1")
        user.set_unusable_password()
        user.save()
        fake = FakeVerifier(profile(sub="g-1"))
        with mock.patch.object(
            google_service, "GoogleIdTokenVerifier", return_value=fake
        ):
            self.post("/api/auth/google/", {"id_token": "t"})
        mail.outbox.clear()
        with mock.patch(
            "accounts.services.reauth_service.GoogleIdTokenVerifier", return_value=fake
        ):
            response = self.post("/api/me/email/", {"new_email": NEW, "id_token": "t"})
        self.assertEqual(response.status_code, 202)
        token = re.search(
            r"token=([\w.:\-]+)", next(m for m in mail.outbox if m.to == [NEW]).body
        ).group(1)
        client = APIClient(enforce_csrf_checks=True)
        client.get("/api/csrf/")
        client.post(
            "/api/auth/email-change/confirm/",
            {"token": token},
            format="json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertEqual(User.objects.get(pk=user.pk).email, NEW)
        # Google still finds the account by its Google id, even though the profile email differs.
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/csrf/")
        with mock.patch.object(
            google_service, "GoogleIdTokenVerifier", return_value=fake
        ):
            again = self.post("/api/auth/google/", {"id_token": "t"})
        self.assertEqual(again.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
