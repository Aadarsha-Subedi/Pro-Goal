from attachments.constants import error_codes, messages
from common.exception.domain import ServiceUnavailableException
from common.storage import get_storage
from common.storage.base import DirectUploadUnsupported, FileStorage


def storage() -> FileStorage:
    """The R2 storage; attachments cannot work on local disk."""
    return get_storage()


def not_configured() -> ServiceUnavailableException:
    return ServiceUnavailableException(
        messages.NOT_CONFIGURED, error_code=error_codes.NOT_CONFIGURED
    )


__all__ = ["DirectUploadUnsupported", "not_configured", "storage"]
