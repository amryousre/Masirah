"""The organisation and CV file the worker is handling now (T031).

The worker sets it around the whole of a message's handling, its failure included, so every log
line and error report made meanwhile can name the tenant. It is not the charge: what a model call
is charged to is metering's spending_for, which covers only the calls themselves.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

_current: ContextVar[tuple[UUID, UUID] | None] = ContextVar("working_on", default=None)


@contextmanager
def working_on(organisation_id: UUID, cv_file_id: UUID) -> Iterator[None]:
    token = _current.set((organisation_id, cv_file_id))
    try:
        yield
    finally:
        _current.reset(token)


def current_work() -> tuple[UUID, UUID] | None:
    return _current.get()
