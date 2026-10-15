from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from integrations.constants.events import Source

event_source_var: ContextVar[str] = ContextVar("event_source", default=Source.WEB)


def current_source() -> str:
    return event_source_var.get()


@contextmanager
def use_source(source: str) -> Iterator[None]:
    """Mark every change made inside the block as coming from `source`
    (for example a Slack command), so it is not posted back there."""
    token = event_source_var.set(source)
    try:
        yield
    finally:
        event_source_var.reset(token)
