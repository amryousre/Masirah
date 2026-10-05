"""Personal data is purged once the organisation's retention period passes (T096, NFR-10).

worker.due_for_purge also lists every candidate first seen longer ago than their organisation's
retention_months and not yet purged. The purge is the one deletion on request uses; what it
leaves is the aggregate record: scores and the audit trail.
"""

import pytest

from tests.database import Cursor, Tenant, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenant(cur: Cursor) -> Tenant:
    return seed_tenant(cur, "gamma")


def age(cur: Cursor, tenant: Tenant, months: int) -> None:
    cur.execute(
        "update public.candidate set created_at = now() - make_interval(months => %s)"
        " where id = %s",
        (months, tenant.row_ids["candidate"]),
    )


def due(cur: Cursor) -> set[tuple[object, ...]]:
    cur.execute("set local role masirah_worker")
    cur.execute("select organisation_id, candidate_id, reason from worker.due_for_purge(1000)")
    rows = set(cur.fetchall())
    cur.execute("reset role")
    return rows


def entry(tenant: Tenant) -> tuple[object, ...]:
    return (tenant.organisation_id, tenant.row_ids["candidate"], "retention")


def test_a_candidate_within_the_period_is_kept(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 23)
    assert entry(tenant) not in due(cur)


def test_a_candidate_past_the_period_is_due(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    assert entry(tenant) in due(cur)


def test_the_period_is_the_organisations_own(cur: Cursor, tenant: Tenant) -> None:
    cur.execute(
        "update public.organisation set retention_months = 6 where id = %s",
        (tenant.organisation_id,),
    )
    age(cur, tenant, 7)
    assert entry(tenant) in due(cur)


def test_a_purged_candidate_is_not_due_again(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    cur.execute("set local role masirah_worker")
    cur.execute("select worker.purge_candidate(%s, 'retention')", (tenant.row_ids["candidate"],))
    cur.execute("reset role")
    assert entry(tenant) not in due(cur)


def test_retention_keeps_the_aggregate_record(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    cur.execute("set local role masirah_worker")
    cur.execute("select worker.purge_candidate(%s, 'retention')", (tenant.row_ids["candidate"],))
    cur.execute("reset role")
    cur.execute(
        "select s.total, a.decision::text from public.score s"
        " join public.application a on a.id = s.application_id where s.id = %s",
        (tenant.row_ids["score"],),
    )
    assert cur.fetchone() == (72, "undecided")
    cur.execute(
        "select metadata ->> 'reason' from public.activity"
        " where subject_id = %s and action = 'candidate.purged'",
        (tenant.row_ids["candidate"],),
    )
    assert cur.fetchone() == ("retention",)
