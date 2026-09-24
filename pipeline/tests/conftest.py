from collections.abc import Iterator

import psycopg
import pytest

from tests.database import DATABASE_URL, Cursor


@pytest.fixture
def cur() -> Iterator[Cursor]:
    """A cursor inside one transaction that is always rolled back, leaving the database as found."""
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            yield cursor
        conn.rollback()
