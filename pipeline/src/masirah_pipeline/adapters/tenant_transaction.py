"""A transaction acting for one organisation, as the worker's row level security expects.

The worker's policies admit only rows of the organisation declared with
set_config('masirah.organisation_id', ..., true) (migration 0014). The declaration is local to
the transaction, so every operation opens one, declares its organisation, and nothing it does can
leak into the next operation's tenant.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg

Cursor = psycopg.Cursor[tuple[Any, ...]]


@contextmanager
def acting_for(connection: psycopg.Connection[Any], organisation_id: UUID) -> Iterator[Cursor]:
    with connection.transaction(), connection.cursor() as cur:
        cur.execute(
            "select set_config('masirah.organisation_id', %s, true)", (str(organisation_id),)
        )
        yield cur
