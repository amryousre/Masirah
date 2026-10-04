"""The worker's tenant data in Postgres, as the masirah_worker role (T054, migration 0014).

Each operation runs in its own transaction, which first declares the organisation it acts in.
Row level security then confines the transaction to that tenant, so an operation handed another
tenant's identifier finds nothing and raises LookupError rather than writing.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from masirah_pipeline.ports.worker_store import CvFile, Extraction, StoredProfile

Cursor = psycopg.Cursor[tuple[Any, ...]]


class PostgresWorkerStore:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def cv_file(self, organisation_id: UUID, cv_file_id: UUID) -> CvFile | None:
        with self._acting_for(organisation_id) as cur:
            row = cur.execute(
                "select id, storage_path, mime_type, content_hash, status::text, candidate_id"
                " from public.cv_file where id = %s",
                (cv_file_id,),
            ).fetchone()
        return None if row is None else CvFile(*row)

    def current_profile(self, organisation_id: UUID, cv_file_id: UUID) -> StoredProfile | None:
        with self._acting_for(organisation_id) as cur:
            row = cur.execute(
                "select version, confidence, profile from public.parsed_profile"
                " where cv_file_id = %s and is_current",
                (cv_file_id,),
            ).fetchone()
        return None if row is None else StoredProfile(*row)

    def mark_extracting(self, organisation_id: UUID, cv_file_id: UUID) -> None:
        self._set_status(organisation_id, cv_file_id, "extracting", None)

    def mark_needs_review(self, organisation_id: UUID, cv_file_id: UUID) -> None:
        self._set_status(organisation_id, cv_file_id, "needs_review", None)

    def mark_failed(self, organisation_id: UUID, cv_file_id: UUID, reason: str) -> None:
        self._set_status(organisation_id, cv_file_id, "failed", reason)

    def record_extraction(
        self, organisation_id: UUID, cv_file_id: UUID, extraction: Extraction
    ) -> UUID:
        details = extraction.candidate
        fields = (
            details.full_name,
            details.email,
            details.phone,
            details.location,
            details.name_normalised,
        )
        with self._acting_for(organisation_id) as cur:
            # Locks the file so two workers handling the same message cannot both add a version.
            row = cur.execute(
                "select candidate_id from public.cv_file where id = %s for update", (cv_file_id,)
            ).fetchone()
            if row is None:
                raise LookupError(f"CV file {cv_file_id} is not in organisation {organisation_id}")
            candidate_id = _candidate(cur, organisation_id, row[0], fields)
            cur.execute(
                "update public.parsed_profile set is_current = false"
                " where cv_file_id = %s and is_current",
                (cv_file_id,),
            )
            cur.execute(
                "insert into public.parsed_profile (organisation_id, cv_file_id, version,"
                " is_current, extraction_source, confidence, profile)"
                " select %s, %s, coalesce(max(version), 0) + 1, true, %s, %s, %s"
                " from public.parsed_profile where cv_file_id = %s",
                (
                    organisation_id,
                    cv_file_id,
                    extraction.source,
                    extraction.confidence,
                    Jsonb(extraction.profile),
                    cv_file_id,
                ),
            )
            cur.execute(
                "update public.cv_file set status = %s, failure_reason = null, candidate_id = %s"
                " where id = %s",
                (extraction.status, candidate_id, cv_file_id),
            )
        return candidate_id

    def ensure_application(self, organisation_id: UUID, candidate_id: UUID, job_id: UUID) -> UUID:
        with self._acting_for(organisation_id) as cur:
            cur.execute(
                "insert into public.application (organisation_id, candidate_id, job_id)"
                " values (%s, %s, %s) on conflict (job_id, candidate_id) do nothing",
                (organisation_id, candidate_id, job_id),
            )
            row = cur.execute(
                "select id from public.application where job_id = %s and candidate_id = %s",
                (job_id, candidate_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"no application for candidate {candidate_id} and job {job_id}")
        application_id: UUID = row[0]
        return application_id

    def _set_status(
        self, organisation_id: UUID, cv_file_id: UUID, status: str, reason: str | None
    ) -> None:
        with self._acting_for(organisation_id) as cur:
            cur.execute(
                "update public.cv_file set status = %s, failure_reason = %s where id = %s",
                (status, reason, cv_file_id),
            )
            if cur.rowcount != 1:
                raise LookupError(f"CV file {cv_file_id} is not in organisation {organisation_id}")

    @contextmanager
    def _acting_for(self, organisation_id: UUID) -> Iterator[Cursor]:
        with self._connection.transaction(), self._connection.cursor() as cur:
            cur.execute(
                "select set_config('masirah.organisation_id', %s, true)", (str(organisation_id),)
            )
            yield cur


def _candidate(
    cur: Cursor, organisation_id: UUID, existing: UUID | None, fields: tuple[str | None, ...]
) -> UUID:
    """The file's candidate brought up to date, or a new candidate when the file has none."""
    if existing is not None:
        cur.execute(
            "update public.candidate set full_name = %s, email = %s, phone = %s, location = %s,"
            " name_normalised = %s where id = %s",
            (*fields, existing),
        )
        return existing
    row = cur.execute(
        "insert into public.candidate (organisation_id, full_name, email, phone, location,"
        " name_normalised) values (%s, %s, %s, %s, %s, %s) returning id",
        (organisation_id, *fields),
    ).fetchone()
    if row is None:
        raise LookupError("the new candidate was not returned")
    created: UUID = row[0]
    return created
