"""The figures the parse failure alert reads, and its claim (NFR-14, T031, migration 0028).

worker.parse_outcomes counts the CV files that settled within a window, extracted, sent for
review or failed, and how many failed, across every organisation. It returns counts and nothing
else: no identifier, file name or reason, since the alert goes to an operator's channel. A file
settles once, when the worker finishes with it; a later review or purge does not settle it again.

worker.claim_alert lets one worker send an alert of a kind per quiet period, so several workers,
or one restarted, do not repeat it.
"""

import uuid

import psycopg
import pytest
from psycopg import sql

from masirah_pipeline.adapters.postgres_parse_outcomes import (
    PostgresAlertClaim,
    PostgresParseOutcomes,
)
from masirah_pipeline.domain.parse_failures import ParseOutcomes
from tests.database import Cursor, seed_tenant

pytestmark = pytest.mark.database

HOUR = 3600


@pytest.fixture(autouse=True)
def nothing_settled_recently(cur: Cursor) -> None:
    """Files other tests or the e2e suite left behind are moved out of every window, and no alert
    has been claimed."""
    cur.execute("update public.cv_file set settled_at = now() - interval '30 days'")
    cur.execute("delete from private.alert_claim")


def add_file(
    cur: Cursor, organisation: uuid.UUID, status: str, *, minutes_ago: int = 5
) -> uuid.UUID:
    """A file the worker settled `minutes_ago`, or one still in progress."""
    file_id = uuid.uuid4()
    settled = status in ("extracted", "needs_review", "failed")
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash, status, failure_reason, settled_at)"
        " values (%s, %s, %s, 'cv.pdf', 'application/pdf', 10, %s, %s, %s,"
        " case when %s then now() - make_interval(mins => %s) end)",
        (
            file_id,
            organisation,
            f"organisations/{organisation}/cv/{file_id}/cv.pdf",
            "d" * 64,
            status,
            "unreadable" if status == "failed" else None,
            settled,
            minutes_ago,
        ),
    )
    return file_id


def as_worker(cur: Cursor) -> None:
    cur.execute("set local role masirah_worker")


def outcomes(cur: Cursor, window: int = HOUR) -> ParseOutcomes:
    as_worker(cur)
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


def test_a_file_settles_when_the_worker_finishes_with_it(cur: Cursor) -> None:
    alpha = seed_tenant(cur, "alpha")
    file_id = add_file(cur, alpha.organisation_id, "extracting")
    cur.execute(
        "update public.cv_file set status = 'failed', failure_reason = 'unreadable' where id = %s",
        (file_id,),
    )
    assert outcomes(cur) == ParseOutcomes(settled=1, failed=1, organisations=1)


def test_a_later_review_or_purge_does_not_settle_a_file_again(cur: Cursor) -> None:
    """An old failure touched today, by a person or by retention, is not a new failure."""
    alpha = seed_tenant(cur, "alpha")
    reviewed = add_file(cur, alpha.organisation_id, "needs_review", minutes_ago=600)
    failed = add_file(cur, alpha.organisation_id, "failed", minutes_ago=600)
    cur.execute("update public.cv_file set status = 'extracted' where id = %s", (reviewed,))
    cur.execute("update public.cv_file set original_filename = 'x' where id = %s", (failed,))
    assert outcomes(cur) == ParseOutcomes(settled=0, failed=0, organisations=0)


def test_a_purged_file_is_left_out(cur: Cursor) -> None:
    alpha = seed_tenant(cur, "alpha")
    file_id = add_file(cur, alpha.organisation_id, "failed")
    cur.execute("update public.cv_file set purged_at = now() where id = %s", (file_id,))
    assert outcomes(cur) == ParseOutcomes(settled=0, failed=0, organisations=0)


def test_a_window_under_a_minute_is_refused(cur: Cursor) -> None:
    as_worker(cur)
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        cur.execute("select * from worker.parse_outcomes(30)")


def claim(cur: Cursor, kind: str = "parse_failures", quiet: int = HOUR) -> bool:
    as_worker(cur)
    try:
        return PostgresAlertClaim(cur.connection)(kind, quiet)
    finally:
        cur.execute("reset role")


def test_the_first_claim_wins_and_the_next_waits_out_the_quiet_period(cur: Cursor) -> None:
    assert claim(cur) is True
    assert claim(cur) is False
    cur.execute("update private.alert_claim set claimed_at = now() - interval '61 minutes'")
    assert claim(cur) is True


def test_kinds_are_claimed_separately(cur: Cursor) -> None:
    assert claim(cur, "parse_failures") is True
    assert claim(cur, "worker_silent") is True


@pytest.mark.parametrize(
    "call", ["select * from worker.parse_outcomes(3600)", "select worker.claim_alert('x', 3600)"]
)
@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_only_the_worker_may_call_them(cur: Cursor, role: str, call: str) -> None:
    cur.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(call)
