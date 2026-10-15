from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
)
from django.core.exceptions import ValidationError

from common.exception.domain import ValidationException
from common.validators.base import BaseValidator
from common.validators.constants import NEW_PASSWORD_MUST_DIFFER_MESSAGE

MIN_PASSWORD_LENGTH = 10


class PasswordValidator(BaseValidator):
    """Callable validator. Pass `user` (any object with email/name attributes)
    to also reject passwords too similar to the user's own details."""

    message = "Password does not meet security requirements."

    def __init__(self, user: object | None = None) -> None:
        self.user = user
        self.validators = [
            MinimumLengthValidator(min_length=MIN_PASSWORD_LENGTH),
            CommonPasswordValidator(),
            NumericPasswordValidator(),
        ]
        if user is not None:
            self.validators.append(UserAttributeSimilarityValidator())

    def __call__(self, value: str) -> None:
        errors = []

        for validator in self.validators:
            try:
                validator.validate(value, self.user)
            except ValidationError as e:
                errors.extend(e.messages)

        if not any(c.isupper() for c in value):
            errors.append("Password must contain at least one uppercase letter.")

        if not any(c.islower() for c in value):
            errors.append("Password must contain at least one lowercase letter.")

        if errors:
            raise ValidationError(errors)


def validate_password_strength(
    password: str, user: object | None = None, field: str = "password"
) -> None:
    """Run PasswordValidator and report failures as an API ValidationException
    pointing at `field`."""
    try:
        PasswordValidator(user=user)(password)
    except ValidationError as exc:
        raise ValidationException(
            errors=[{"field": field, "message": message} for message in exc.messages]
        ) from exc


def validate_password_changed(
    user: object, new_password: str, field: str = "new_password"
) -> None:
    """Raise an API ValidationException on `field` when `new_password` equals
    the user's current password. `user` needs `check_password`."""
    if user.check_password(new_password):
        raise ValidationException(
            errors=[{"field": field, "message": NEW_PASSWORD_MUST_DIFFER_MESSAGE}]
        )
