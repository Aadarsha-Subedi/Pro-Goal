from common.exception.domain import NotFoundException
from integrations.constants import error_codes, messages
from integrations.providers.base import Provider

_providers: dict[str, Provider] = {}


def register(provider: Provider) -> None:
    _providers[provider.code] = provider


def unregister(code: str) -> None:
    _providers.pop(code, None)


def get(code: str) -> Provider:
    provider = _providers.get(code)
    if provider is None:
        raise NotFoundException(
            messages.UNKNOWN_PROVIDER, error_code=error_codes.UNKNOWN_PROVIDER
        )
    return provider


def find(code: str) -> Provider | None:
    return _providers.get(code)


def codes() -> list[str]:
    return sorted(_providers)
