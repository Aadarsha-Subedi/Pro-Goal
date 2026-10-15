from io import BytesIO
from uuid import uuid7

from django.conf import settings
from PIL import Image, UnidentifiedImageError

from accounts.constants import avatar as avatar_constants
from accounts.constants import error_codes, messages
from accounts.models import User
from common.exception.domain import ValidationException
from common.storage import get_storage


class AvatarError(ValidationException):
    error_code = error_codes.INVALID_AVATAR


def _process(data: bytes) -> bytes:
    if len(data) > settings.AVATAR_MAX_BYTES:
        raise AvatarError(messages.AVATAR_TOO_LARGE)
    try:
        with Image.open(BytesIO(data)) as probe:
            image_format = probe.format
            probe.verify()
        # verify() invalidates the image; reopen to actually decode it.
        with Image.open(BytesIO(data)) as image:
            if image_format not in avatar_constants.ALLOWED_FORMATS:
                raise AvatarError(messages.AVATAR_BAD_FORMAT)
            image.load()
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.thumbnail((settings.AVATAR_MAX_PIXELS, settings.AVATAR_MAX_PIXELS))
            # Re-encoding from pixels drops EXIF and location metadata.
            out = BytesIO()
            image.save(
                out,
                format=avatar_constants.OUTPUT_FORMAT,
                quality=avatar_constants.OUTPUT_QUALITY,
            )
            return out.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise AvatarError(messages.AVATAR_BAD_FORMAT) from exc


def set_avatar(user: User, data: bytes) -> User:
    processed = _process(data)
    storage = get_storage()
    key = avatar_constants.STORAGE_KEY.format(user_id=user.pk, file_id=uuid7())
    storage.upload(key, processed, avatar_constants.OUTPUT_CONTENT_TYPE)
    old_key = user.avatar
    user.avatar = key
    user.save(update_fields=["avatar", "updated_at"])
    if old_key:
        storage.delete(old_key)
    return user


def remove_avatar(user: User) -> User:
    if user.avatar:
        get_storage().delete(user.avatar)
        user.avatar = None
        user.save(update_fields=["avatar", "updated_at"])
    return user


def avatar_url(user: User) -> str | None:
    return get_storage().url(user.avatar) if user.avatar else None
