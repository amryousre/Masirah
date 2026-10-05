"""The purge sweep's database side (T100, T101, migration 0022).

Each call is one of the worker functions migration 0022 grants the masirah_worker role: they run
as their owner because retention crosses organisations, and they are all the sweep can do.
"""

from typing import cast
from uuid import UUID

import psycopg

from masirah_pipeline.ports.purge_store import DuePurge, PurgeReason


class PostgresPurgeStore:
    def __init__(self, connection: psycopg.Connection[tuple[object, ...]]) -> None:
        self._connection = connection

    def due(self, at_most: int) -> list[DuePurge]:
        rows = self._connection.execute(
            "select organisation_id, candidate_id, reason from worker.due_for_purge(%s)",
            (at_most,),
        ).fetchall()
        return [
            DuePurge(cast(UUID, org), cast(UUID, candidate), cast(PurgeReason, reason))
            for org, candidate, reason in rows
        ]

    def original_paths(self, candidate_id: UUID) -> list[str]:
        rows = self._connection.execute(
            "select storage_path from worker.purge_paths(%s)", (candidate_id,)
        ).fetchall()
        return [str(path) for (path,) in rows]

    def purge(self, candidate_id: UUID, reason: str) -> None:
        self._connection.execute("select worker.purge_candidate(%s, %s)", (candidate_id, reason))
