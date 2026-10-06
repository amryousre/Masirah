"""The purge sweep's database side (T100, T101, migration 0022).

Each call is one of the worker functions migration 0022 grants the masirah_worker role: they run
as their owner because retention crosses organisations, and they are all the sweep can do.
"""

from typing import cast
from uuid import UUID

import psycopg

from masirah_pipeline.ports.purge_store import DueFile, DuePurge, OriginalFile, PurgeReason


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

    def originals(self, candidate_id: UUID) -> list[OriginalFile]:
        rows = self._connection.execute(
            "select cv_file_id, storage_path from worker.purge_paths(%s)", (candidate_id,)
        ).fetchall()
        return [OriginalFile(cast(UUID, file), str(path)) for file, path in rows]

    def purge(self, candidate_id: UUID, reason: str, removed: list[UUID]) -> None:
        self._connection.execute(
            "select worker.purge_candidate(%s, %s, %s)", (candidate_id, reason, removed)
        )

    def due_files(self, at_most: int) -> list[DueFile]:
        rows = self._connection.execute(
            "select organisation_id, cv_file_id, storage_path from worker.files_due_for_purge(%s)",
            (max(at_most, 0),),
        ).fetchall()
        return [DueFile(cast(UUID, org), cast(UUID, file), str(path)) for org, file, path in rows]

    def purge_file(self, cv_file_id: UUID) -> None:
        self._connection.execute("select worker.purge_file(%s)", (cv_file_id,))

    def defer(self, subject_id: UUID) -> None:
        self._connection.execute("select worker.defer_purge(%s)", (subject_id,))
