from allauth.account.models import EmailAddress
from django.core import mail
from django.test import override_settings

from accounts.models import User, UserSession
from accounts.tests.base import PASSWORD, ApiTestCase

SIGNUP = {
    "email": "Grace@Example.com",
    "password": PASSWORD,
    "first_name": "Grace",
    "last_name": "Hopper",
    "display_name": "Grace",
}


class SignupTests(ApiTestCase):
    def test_signup_creates_unverified_user_and_sends_link(self):
        response = self.post("/api/auth/signup/", SIGNUP)
        self.assertEqual(response.status_code, 202)
        user = User.objects.get(email="grace@example.com")
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify-email?token=", mail.outbox[0].body)

    def test_existing_email_gets_same_reply_and_notice_mail(self):
        self.make_user("grace@example.com")
        response = self.post("/api/auth/signup/", SIGNUP)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json()["message"],
            self.post(
                "/api/auth/signup/", {**SIGNUP, "email": "new@example.com"}
            ).json()["message"],
        )
        self.assertEqual(User.objects.filter(email="grace@example.com").count(), 1)
        self.assertIn("already have an account", mail.outbox[0].body)

    def test_weak_password_rejected(self):
        response = self.post("/api/auth/signup/", {**SIGNUP, "password": "short"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")

    def test_password_similar_to_email_rejected(self):
        response = self.post(
            "/api/auth/signup/", {**SIGNUP, "password": "Grace-Example-1"}
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_field_rejected(self):
        response = self.post("/api/auth/signup/", {**SIGNUP, "is_staff": True})
        self.assertEqual(response.status_code, 400)

    def test_csrf_token_from_body_is_accepted_as_header(self):
        client = type(self.client)(enforce_csrf_checks=True)
        token = client.get("/api/csrf/").json()["data"]["csrf_token"]
        response = client.post(
            "/api/auth/signup/",
            SIGNUP,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 202)

    def test_missing_csrf_rejected(self):
        response = self.client.post("/api/auth/signup/", SIGNUP, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "csrf_failed")


class VerificationTests(ApiTestCase):
    def test_verify_then_token_is_single_use(self):
        user = self.make_user(verified=False)
        token = self.verification_token(user)
        self.assertEqual(
            self.post("/api/auth/verify-email/", {"token": token}).status_code, 200
        )
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        again = self.post("/api/auth/verify-email/", {"token": token})
        self.assertEqual(again.status_code, 401)

    def test_expired_token(self):
        user = self.make_user(verified=False)
        token = self.verification_token(user)
        with override_settings(EMAIL_VERIFICATION_TIMEOUT=-1):
            response = self.post("/api/auth/verify-email/", {"token": token})
        self.assertEqual(response.json()["code"], "verification_token_expired")

    def test_garbage_token(self):
        self.assertEqual(
            self.post("/api/auth/verify-email/", {"token": "nope"}).status_code, 401
        )

    def test_resend_cooldown_and_neutral_reply(self):
        self.make_user(verified=False)
        first = self.post(
            "/api/auth/verify-email/resend/", {"email": "ada@example.com"}
        )
        second = self.post(
            "/api/auth/verify-email/resend/", {"email": "ada@example.com"}
        )
        unknown = self.post(
            "/api/auth/verify-email/resend/", {"email": "who@example.com"}
        )
        self.assertEqual(
            {first.status_code, second.status_code, unknown.status_code}, {202}
        )
        self.assertEqual(len(mail.outbox), 1)


class LoginTests(ApiTestCase):
    def test_login_success_creates_session_and_me_works(self):
        self.make_user()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserSession.objects.count(), 1)
        me = self.client.get("/api/me/")
        self.assertEqual(me.json()["data"]["email"], "ada@example.com")

    def test_wrong_password_and_unknown_user_look_identical(self):
        self.make_user()
        wrong = self.login(password="Wrong-Password-1")
        unknown = self.login(email="nobody@example.com")
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.json()["message"], unknown.json()["message"])
        self.assertEqual(wrong.json()["code"], "invalid_credentials")

    def test_unverified_user_cannot_login(self):
        self.make_user(verified=False)
        response = self.login()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "email_not_verified")

    def test_remember_me_extends_lifetime(self):
        self.make_user()
        self.login(remember_me=True)
        self.assertEqual(self.client.session.get_expiry_age(), 30 * 24 * 3600)

    def test_default_lifetime_is_two_weeks(self):
        self.make_user()
        self.login()
        self.assertEqual(self.client.session.get_expiry_age(), 14 * 24 * 3600)

    def test_login_throttled_after_five_attempts(self):
        self.make_user()
        codes = [self.login(password="Wrong-Password-1").status_code for _ in range(6)]
        self.assertEqual(codes[-1], 429)

    def test_me_requires_login(self):
        self.assertEqual(self.client.get("/api/me/").status_code, 401)

    def test_logout_current_only(self):
        self.make_user()
        other = type(self.client)(enforce_csrf_checks=True)
        other.get("/api/csrf/")
        other.post(
            "/api/auth/login/",
            {"email": "ada@example.com", "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=other.cookies["csrftoken"].value,
        )
        self.login()
        self.assertEqual(UserSession.objects.count(), 2)
        self.assertEqual(self.post("/api/auth/logout/").status_code, 200)
        self.assertEqual(UserSession.objects.count(), 1)
        self.assertEqual(other.get("/api/me/").status_code, 200)

    def test_logout_all_other_sessions(self):
        self.make_user()
        other = type(self.client)(enforce_csrf_checks=True)
        other.get("/api/csrf/")
        other.post(
            "/api/auth/login/",
            {"email": "ada@example.com", "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=other.cookies["csrftoken"].value,
        )
        self.login()
        self.post("/api/auth/logout/", {"all_other_sessions": True})
        self.assertEqual(UserSession.objects.count(), 0)
        self.assertEqual(other.get("/api/me/").status_code, 401)


class PasswordTests(ApiTestCase):
    def _reset_link(self) -> tuple[str, str]:
        body = mail.outbox[-1].body
        query = body.split("reset-password?")[1].split()[0]
        parts = dict(pair.split("=") for pair in query.split("&"))
        return parts["uid"], parts["token"]

    def test_reset_flow_logs_out_all_sessions(self):
        self.make_user()
        self.login()
        self.assertEqual(
            self.post(
                "/api/auth/password/reset/", {"email": "ada@example.com"}
            ).status_code,
            202,
        )
        uid, token = self._reset_link()
        response = self.post(
            "/api/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "new_password": "Brand-New-Pass-7"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserSession.objects.count(), 0)
        self.assertEqual(self.login(password="Brand-New-Pass-7").status_code, 200)
        reuse = self.post(
            "/api/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "new_password": "Another-Pass-77"},
        )
        self.assertEqual(reuse.status_code, 401)

    def test_reset_for_unknown_email_is_neutral(self):
        response = self.post("/api/auth/password/reset/", {"email": "none@example.com"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 0)

    def test_change_password_keeps_current_session_only(self):
        self.make_user()
        other = type(self.client)(enforce_csrf_checks=True)
        other.get("/api/csrf/")
        other.post(
            "/api/auth/login/",
            {"email": "ada@example.com", "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=other.cookies["csrftoken"].value,
        )
        self.login()
        response = self.post(
            "/api/auth/password/change/",
            {"current_password": PASSWORD, "new_password": "Brand-New-Pass-7"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assertEqual(other.get("/api/me/").status_code, 401)
        self.assertIn("password on your account was just changed", mail.outbox[-1].body)

    def test_change_password_keeps_the_current_session_listed(self):
        self.make_user()
        self.login()
        self.post(
            "/api/auth/password/change/",
            {"current_password": PASSWORD, "new_password": "Brand-New-Pass-7"},
        )
        sessions = self.client.get("/api/me/sessions/").json()["data"]["items"]
        self.assertEqual([s["is_current"] for s in sessions], [True])

    def test_change_password_wrong_current(self):
        self.make_user()
        self.login()
        response = self.post(
            "/api/auth/password/change/",
            {
                "current_password": "Wrong-Password-1",
                "new_password": "Brand-New-Pass-7",
            },
        )
        self.assertEqual(response.json()["code"], "invalid_current_password")
