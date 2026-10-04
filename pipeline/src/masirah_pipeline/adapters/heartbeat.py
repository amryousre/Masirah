"""The worker's heartbeat in Postgres (T030, migration 0016).

Each worker process records that it is alive under its own name, through worker.beat, which runs
as its owner: the worker role holds no grant on the heartbeat table.
"""

from typing import Any

import psycopg


class PostgresHeartbeat:
    def __init__(self, connection: psycopg.Connection[Any], worker_name: str) -> None:
        self._connection = connection
        self._name = worker_name

    def __call__(self) -> None:
        self._connection.execute("select worker.beat(%s)", (self._name,))
