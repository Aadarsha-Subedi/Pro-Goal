from rest_framework import serializers

from accounts.constants import fields
from accounts.serializers.reauth import ReauthSerializer
from common.serializers.base import StrictSerializer
from common.serializers.fields import NormalizedEmailField

NAME_FIELD = {"max_length": fields.NAME_MAX_LENGTH, "trim_whitespace": True}


class PasswordField(serializers.CharField):
    """Write-only password input: never trimmed or echoed back."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("max_length", fields.PASSWORD_MAX_LENGTH)
        kwargs.setdefault("trim_whitespace", False)
        super().__init__(**kwargs)


class SignupSerializer(StrictSerializer):
    email = NormalizedEmailField()
    password = PasswordField(write_only=True)
    first_name = serializers.CharField(**NAME_FIELD)
    last_name = serializers.CharField(**NAME_FIELD)
    display_name = serializers.CharField(**NAME_FIELD)


class VerifyEmailSerializer(StrictSerializer):
    token = serializers.CharField(max_length=fields.TOKEN_MAX_LENGTH)


class EmailOnlySerializer(StrictSerializer):
    email = NormalizedEmailField()


class LoginSerializer(StrictSerializer):
    email = NormalizedEmailField()
    password = PasswordField()
    remember_me = serializers.BooleanField(required=False, default=False)


class GoogleLoginSerializer(StrictSerializer):
    id_token = serializers.CharField(max_length=fields.GOOGLE_ID_TOKEN_MAX_LENGTH)
    remember_me = serializers.BooleanField(required=False, default=False)


class GoogleRedirectSerializer(StrictSerializer):
    """Google's form post after the browser was sent to its sign-in page."""

    id_token = serializers.CharField(max_length=fields.GOOGLE_ID_TOKEN_MAX_LENGTH)
    state = serializers.CharField(max_length=256)


class LogoutSerializer(StrictSerializer):
    all_other_sessions = serializers.BooleanField(required=False, default=False)


class PasswordResetConfirmSerializer(StrictSerializer):
    uid = serializers.CharField(max_length=fields.RESET_UID_MAX_LENGTH)
    token = serializers.CharField(max_length=fields.RESET_TOKEN_MAX_LENGTH)
    new_password = PasswordField(write_only=True)


class PasswordChangeSerializer(StrictSerializer):
    current_password = PasswordField(required=False, allow_blank=True)
    new_password = PasswordField(write_only=True)


class EmailChangeSerializer(ReauthSerializer):
    new_email = NormalizedEmailField()


class EmailChangeConfirmSerializer(StrictSerializer):
    token = serializers.CharField(max_length=fields.TOKEN_MAX_LENGTH)
