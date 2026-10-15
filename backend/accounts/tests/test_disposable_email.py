from django.core import mail
from django.test import SimpleTestCase, override_settings

from accounts.models import User
from accounts.tests.base import PASSWORD, ApiTestCase
from common.validators.disposable import is_disposable

SIGNUP = {
    "email": "ada@yopmail.com",
    "password": PASSWORD,
    "first_name": "Ada",
    "last_name": "Lovelace",
    "display_name": "Ada",
}


class IsDisposableTests(SimpleTestCase):
    def test_known_throwaway_domains(self):
        for address in ("a@yopmail.com", "a@Mailinator.com", "a@mx.yopmail.com"):
            self.assertTrue(is_disposable(address), address)

    def test_real_providers_pass(self):
        for address in (
            "a@gmail.com",
            "a@example.com",
            "a@mail.company.io",
            "nodomain",
        ):
            self.assertFalse(is_disposable(address), address)


class SignupBlockTests(ApiTestCase):
    @override_settings(BLOCK_DISPOSABLE_EMAILS=True)
    def test_prod_refuses_a_throwaway_address(self):
        response = self.post("/api/auth/signup/", SIGNUP)
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], "disposable_email")
        self.assertEqual(body["errors"][0]["field"], "email")
        self.assertFalse(User.objects.filter(email="ada@yopmail.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(BLOCK_DISPOSABLE_EMAILS=True)
    def test_prod_still_accepts_a_real_address(self):
        response = self.post(
            "/api/auth/signup/", {**SIGNUP, "email": "ada@example.com"}
        )
        self.assertEqual(response.status_code, 202, response.content)

    @override_settings(BLOCK_DISPOSABLE_EMAILS=False)
    def test_local_accepts_a_throwaway_address(self):
        response = self.post("/api/auth/signup/", SIGNUP)
        self.assertEqual(response.status_code, 202, response.content)

    @override_settings(BLOCK_DISPOSABLE_EMAILS=True)
    def test_existing_accounts_can_still_sign_in(self):
        self.make_user("old@yopmail.com")
        response = self.login("old@yopmail.com", PASSWORD)
        self.assertEqual(response.status_code, 200, response.content)

    @override_settings(BLOCK_DISPOSABLE_EMAILS=True)
    def test_email_change_to_a_throwaway_address_is_refused(self):
        self.make_user("ada@example.com")
        self.login("ada@example.com", PASSWORD)
        response = self.post(
            "/api/me/email/", {"new_email": "x@yopmail.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "disposable_email")
