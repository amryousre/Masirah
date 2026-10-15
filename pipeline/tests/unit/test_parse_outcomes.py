"""The figures the parse failure alert reads (NFR-14, T031, migration 0028).

worker.parse_outcomes counts the CV files that settled within a window, extracted, sent for
review or failed, and how many failed, across every organisation. It returns counts and nothing
else: no identifier, file name or reason, since the alert goes to an operator's channel.
"""

import uuid

import psycopg
import pytest
from psycopg import sql

from masirah_pipeline.adapters.postgres_parse_outcomes import PostgresParseOutcomes
from masirah_pipeline.domain.parse_failures import ParseOutcomes
from tests.database import Cursor, seed_tenant

pytestmark = pytest.mark.database

HOUR = 3600


@pytest.fixture(autouse=True)
def nothing_settled_recently(cur: Cursor) -> None:
    """Files other tests or the e2e suite left behind are moved out of every window. Triggers are
    off for the transaction, so updated_at keeps the value given."""
    cur.execute("set local session_replication_role = replica")
    cur.execute("update public.cv_file set updated_at = now() - interval '30 days'")


def add_file(
    cur: Cursor, organisation: uuid.UUID, status: str, *, minutes_ago: int = 5
) -> uuid.UUID:
    file_id = uuid.uuid4()
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash, status, failure_reason, updated_at)"
        " values (%s, %s, %s, 'cv.pdf', 'application/pdf', 10, %s, %s, %s,"
        " now() - make_interval(mins => %s))",
        (
            file_id,
            organisation,
            f"organisations/{organisation}/cv/{file_id}/cv.pdf",
            "d" * 64,
            status,
            "unreadable" if status == "failed" else None,
            minutes_ago,
        ),
    )
    return file_id


def outcomes(cur: Cursor, window: int = HOUR) -> ParseOutcomes:
    cur.execute("set local role masirah_worker")
    try:
        return PostgresParseOutcomes(cur.connection)(window)
    finally:
        cur.execute("reset role")


def test_nothing_settled_is_all_zero(cur: Cursor) -> None:
    assert outcomes(cur) == ParseOutcomes(settled=0, failed=0, organisations=0)


def test_settled_files_are_counted_across_organisations(cur: Cursor) -> None:
    alpha, beta = seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")
    for status in ("extracted", "extracted", "needs_review", "failed"):
        add_file(cur, alpha.organisation_id, status)
    add_file(cur, beta.organisation_id, "failed")
    assert outcomes(cur) == ParseOutcomes(settled=5, failed=2, organisations=2)


def test_files_still_in_progress_are_not_settled(cur: Cursor) -> None:
    alpha = seed_tenant(cur, "alpha")
    add_file(cur, alpha.organisation_id, "queued")
    add_file(cur, alpha.organisation_id, "extracting")
    add_file(cur, alpha.organisation_id, "extracted")
    assert outcomes(cur) == ParseOutcomes(settled=1, failed=0, organisations=0)


def test_only_the_window_counts(cur: Cursor) -> None:
    alpha = seed_tenant(cur, "alpha")
    add_file(cur, alpha.organisation_id, "failed", minutes_ago=90)
    add_file(cur, alpha.organisation_id, "extracted", minutes_ago=10)
    assert outcomes(cur) == ParseOutcomes(settled=1, failed=0, organisations=0)
    assert outcomes(cur, window=2 * HOUR) == ParseOutcomes(settled=2, failed=1, organisations=1)


def test_a_window_under_a_minute_is_refused(cur: Cursor) -> None:
    cur.execute("set local role masirah_worker")
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        cur.execute("select * from worker.parse_outcomes(30)")


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_only_the_worker_may_read_the_figures(cur: Cursor, role: str) -> None:
    cur.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select * from worker.parse_outcomes(3600)")
