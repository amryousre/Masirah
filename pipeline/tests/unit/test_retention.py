"""Personal data is purged once the organisation's retention period passes (T096, NFR-10).

As the settings design has it: a candidate's data is deleted the chosen number of months after
their last activity, unless they are in an active stage (shortlisted for a job). An organisation
may choose not to delete automatically. Shortening the period deletes nobody at once: candidates
it makes due wait seven days. The purge is the one deletion on request uses.
"""

import psycopg
import pytest

from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenant(cur: Cursor) -> Tenant:
    return seed_tenant(cur, "gamma")


def age(cur: Cursor, tenant: Tenant, months: int) -> None:
    """Makes every trace of the candidate's activity the given number of months old."""
    candidate = tenant.row_ids["candidate"]
    cur.execute("alter table public.candidate disable trigger set_updated_at")
    cur.execute("alter table public.application disable trigger set_updated_at")
    cur.execute(
        "update public.candidate set created_at = now() - make_interval(months => %s),"
        " updated_at = now() - make_interval(months => %s) where id = %s",
        (months, months, candidate),
    )
    cur.execute(
        "update public.cv_file set created_at = now() - make_interval(months => %s)"
        " where candidate_id = %s",
        (months, candidate),
    )
    cur.execute(
        "update public.application set created_at = now() - make_interval(months => %s),"
        " updated_at = now() - make_interval(months => %s) where candidate_id = %s",
        (months, months, candidate),
    )
    cur.execute("alter table public.candidate enable trigger set_updated_at")
    cur.execute("alter table public.application enable trigger set_updated_at")


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


def test_activity_since_keeps_a_candidate(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    cur.execute(
        "update public.application set updated_at = now() where id = %s",
        (tenant.row_ids["application"],),
    )
    assert entry(tenant) not in due(cur)


def test_a_shortlisted_candidate_is_kept(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    cur.execute("alter table public.application disable trigger set_updated_at")
    cur.execute(
        "update public.application set decision = 'shortlisted', decided_by = %s,"
        " decided_at = now() - interval '25 months' where id = %s",
        (tenant.user_id, tenant.row_ids["application"]),
    )
    cur.execute("alter table public.application enable trigger set_updated_at")
    assert entry(tenant) not in due(cur)


def test_an_organisation_can_choose_not_to_delete_automatically(
    cur: Cursor, tenant: Tenant
) -> None:
    cur.execute(
        "update public.organisation set retention_months = null where id = %s",
        (tenant.organisation_id,),
    )
    age(cur, tenant, 120)
    assert entry(tenant) not in due(cur)


def test_shortening_the_period_deletes_nobody_for_seven_days(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 7)
    cur.execute(
        "update public.organisation set retention_months = 6, retention_changed_at = now()"
        " where id = %s",
        (tenant.organisation_id,),
    )
    assert entry(tenant) not in due(cur)
    cur.execute(
        "update public.organisation set retention_changed_at = now() - interval '8 days'"
        " where id = %s",
        (tenant.organisation_id,),
    )
    assert entry(tenant) in due(cur)


def test_a_purged_candidate_is_not_due_again(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    cur.execute("set local role masirah_worker")
    cur.execute("select worker.purge_candidate(%s, 'retention')", (tenant.row_ids["candidate"],))
    cur.execute("reset role")
    assert entry(tenant) not in due(cur)


def test_retention_keeps_the_decision_and_the_trail(cur: Cursor, tenant: Tenant) -> None:
    age(cur, tenant, 25)
    cur.execute("set local role masirah_worker")
    cur.execute("select worker.purge_candidate(%s, 'retention')", (tenant.row_ids["candidate"],))
    cur.execute("reset role")
    cur.execute(
        "select decision::text from public.application where id = %s",
        (tenant.row_ids["application"],),
    )
    assert cur.fetchone() == ("undecided",)
    cur.execute(
        "select metadata ->> 'reason' from public.activity"
        " where subject_id = %s and action = 'candidate.purged'",
        (tenant.row_ids["candidate"],),
    )
    assert cur.fetchone() == ("retention",)


class TestSetRetention:
    """A member chooses the period on the settings page (T102); the choice is recorded."""

    def set_to(self, cur: Cursor, tenant: Tenant, months: int | None) -> int:
        act_as(cur, tenant.user_id)
        cur.execute("select public.set_retention(%s)", (months,))
        row = cur.fetchone()
        cur.execute("reset role")
        assert row is not None
        return int(row[0])

    def test_it_sets_the_period_starts_the_grace_and_records_who(
        self, cur: Cursor, tenant: Tenant
    ) -> None:
        self.set_to(cur, tenant, 6)
        cur.execute(
            "select retention_months, retention_changed_at is not null from public.organisation"
            " where id = %s",
            (tenant.organisation_id,),
        )
        assert cur.fetchone() == (6, True)
        cur.execute(
            "select actor_id, metadata from public.activity"
            " where action = 'organisation.retention_changed' and subject_id = %s",
            (tenant.organisation_id,),
        )
        assert cur.fetchall() == [(tenant.user_id, {"from": 24, "to": 6})]

    def test_it_says_how_many_candidates_the_new_period_will_remove(
        self, cur: Cursor, tenant: Tenant
    ) -> None:
        age(cur, tenant, 7)
        assert self.set_to(cur, tenant, 6) == 1
        assert self.set_to(cur, tenant, 12) == 0

    def test_never_deleting_is_a_choice(self, cur: Cursor, tenant: Tenant) -> None:
        assert self.set_to(cur, tenant, None) == 0
        cur.execute(
            "select retention_months from public.organisation where id = %s",
            (tenant.organisation_id,),
        )
        assert cur.fetchone() == (None,)

    def test_only_the_offered_periods_are_accepted(self, cur: Cursor, tenant: Tenant) -> None:
        with pytest.raises(psycopg.errors.InvalidParameterValue):
            self.set_to(cur, tenant, 3)

    def test_a_member_cannot_change_the_period_directly(self, cur: Cursor, tenant: Tenant) -> None:
        act_as(cur, tenant.user_id)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute(
                "update public.organisation set retention_months = 6 where id = %s",
                (tenant.organisation_id,),
            )
