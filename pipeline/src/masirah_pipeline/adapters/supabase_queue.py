"""Supabase Queues, through the worker schema's functions (T053, contracts/queue-message.md).

The masirah_worker role touches no queue table. It calls worker.read, worker.delete and
worker.archive, which take only the contract's queues and bound the visibility timeout
(supabase/migrations/0013_worker_role.sql).

The connection belongs to the caller, who decides its transactions. The worker opens it in
autocommit mode as the masirah_worker role, so a read's visibility timeout takes effect at once
and no transaction stays open while a CV is processed. Tests pass a connection inside a
transaction they roll back.
"""

import math
from datetime import UTC, datetime
from typing import Any

import psycopg

from masirah_pipeline.ports.job_queue import ReceivedMessage
from masirah_pipeline.ports.queue_message import CV_PROCESSING, CV_RESCORING

QUEUES = frozenset({CV_PROCESSING, CV_RESCORING})


class UnknownQueueError(ValueError):
    """A queue the contract does not name."""


class SupabaseQueue:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def read(self, queue: str, *, visibility_seconds: int, quantity: int) -> list[ReceivedMessage]:
        rows = self._connection.execute(
            "select msg_id, read_ct, enqueued_at, message from worker.read(%s, %s, %s)",
            (_known(queue), visibility_seconds, quantity),
        ).fetchall()
        return [ReceivedMessage(*row) for row in rows]

    def delete(self, queue: str, message_id: int) -> bool:
        return self._called("select worker.delete(%s, %s)", queue, message_id)

    def archive(self, queue: str, message_id: int) -> bool:
        return self._called("select worker.archive(%s, %s)", queue, message_id)

    def defer(self, queue: str, message_id: int, until: datetime) -> None:
        # Whole seconds, rounded up, so the message never comes back before `until`.
        delay = max(0, math.ceil((until - datetime.now(UTC)).total_seconds()))
        self._connection.execute(
            "select worker.defer(%s, %s, %s)", (_known(queue), message_id, delay)
        )

    def _called(self, statement: str, queue: str, message_id: int) -> bool:
        row = self._connection.execute(statement, (_known(queue), message_id)).fetchone()
        return bool(row and row[0])


def _known(queue: str) -> str:
    if queue not in QUEUES:
        raise UnknownQueueError(f"{queue!r} is not a queue in the contract")
    return queue
