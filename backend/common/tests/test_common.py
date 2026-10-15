from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from rest_framework import exceptions as drf_exceptions
from rest_framework import serializers

from accounts.models import User
from common.exception.domain import ConflictException
from common.exception.handler import exception_handler
from common.serializers.base import StrictSerializer
from common.validators.password import PasswordValidator


class PasswordValidatorTests(SimpleTestCase):
    def test_accepts_strong_password(self):
        PasswordValidator()("Correct-Horse-9")

    def test_rejects_short_common_and_case(self):
        for bad in ("Sh0rt-Pw", "password1234", "alllowercase-123", "ALLUPPERCASE-123"):
            with self.subTest(bad), self.assertRaises(ValidationError):
                PasswordValidator()(bad)

    def test_rejects_password_similar_to_email(self):
        candidate = User(
            email="grace.hopper@example.com", first_name="Grace", last_name="Hopper"
        )

        with self.assertRaises(ValidationError):
            PasswordValidator(user=candidate)("Grace.Hopper@Example.com1")


class ExceptionHandlerTests(SimpleTestCase):
    def test_app_exception_envelope(self):
        response = exception_handler(ConflictException(error_code="dup"), {})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "dup")
        self.assertFalse(response.data["success"])

    def test_drf_validation_error_flattened(self):
        exc = drf_exceptions.ValidationError({"email": ["Bad."]})
        response = exception_handler(exc, {})
        self.assertEqual(
            response.data["errors"], [{"field": "email", "message": "Bad."}]
        )

    def test_throttled_sets_retry_after(self):
        response = exception_handler(drf_exceptions.Throttled(wait=30), {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "30")

    def test_unknown_exception_not_swallowed(self):
        self.assertIsNone(exception_handler(RuntimeError("boom"), {}))


class StrictSerializerTests(SimpleTestCase):
    def test_unknown_fields_listed(self):
        class S(StrictSerializer):
            name = serializers.CharField()

        s = S(data={"name": "a", "extra": 1})
        self.assertFalse(s.is_valid())
        self.assertIn("extra", s.errors)
