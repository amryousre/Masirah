"""Personal data is purged once the organisation's retention period passes (T096, NFR-10).

As the settings design has it: a candidate's data is deleted the chosen number of months after
their last activity, unless they are in an active stage (shortlisted for a job). An organisation
may choose not to delete automatically. Shortening the period deletes nobody at once: candidates
it makes due wait seven days. The purge is the one deletion on request uses.
"""

import uuid

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


class TestFilesWithoutACandidate:
    """A CV that never became a candidate (unreadable, or waiting for review) holds personal data
    too: its file, its name and any profile read from it. Retention reaches it on its own."""

    def orphan(self, cur: Cursor, tenant: Tenant, months: int) -> uuid.UUID:
        file_id = uuid.uuid4()
        path = tenant.storage_path.replace(str(tenant.row_ids["cv_file"]), str(file_id))
        cur.execute(
            "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
            " mime_type, byte_size, content_hash, status, failure_reason, created_at, updated_at)"
            " values (%s, %s, %s, 'Mona Abdallah CV.pdf', 'application/pdf', 10, %s, 'failed',"
            " 'encrypted', now() - make_interval(months => %s),"
            " now() - make_interval(months => %s))",
            (file_id, tenant.organisation_id, path, "e" * 64, months, months),
        )
        return file_id

    def due_files(self, cur: Cursor) -> set[tuple[object, ...]]:
        cur.execute("set local role masirah_worker")
        cur.execute("select organisation_id, cv_file_id from worker.files_due_for_purge(1000)")
        rows = set(cur.fetchall())
        cur.execute("reset role")
        return rows

    def test_an_old_unread_file_is_due_and_a_recent_one_is_not(
        self, cur: Cursor, tenant: Tenant
    ) -> None:
        old, recent = self.orphan(cur, tenant, 25), self.orphan(cur, tenant, 1)
        due = self.due_files(cur)
        assert (tenant.organisation_id, old) in due
        assert (tenant.organisation_id, recent) not in due

    def test_a_file_that_became_a_candidate_is_left_to_the_candidates_purge(
        self, cur: Cursor, tenant: Tenant
    ) -> None:
        age(cur, tenant, 25)
        assert (tenant.organisation_id, tenant.row_ids["cv_file"]) not in self.due_files(cur)

    def test_purging_a_file_names_nothing_and_writes_what_went(
        self, cur: Cursor, tenant: Tenant
    ) -> None:
        old = self.orphan(cur, tenant, 25)
        cur.execute("set local role masirah_worker")
        cur.execute("select worker.purge_file(%s)", (old,))
        cur.execute("reset role")
        cur.execute(
            "select original_filename, purged_at is not null from public.cv_file where id = %s",
            (old,),
        )
        assert cur.fetchone() == ("removed", True)
        assert (tenant.organisation_id, old) not in self.due_files(cur)
        cur.execute(
            "select metadata from public.activity"
            " where subject_id = %s and action = 'cv_file.purged'",
            (old,),
        )
        assert cur.fetchall() == [({"reason": "retention", "removed": ["original", "profile"]},)]
