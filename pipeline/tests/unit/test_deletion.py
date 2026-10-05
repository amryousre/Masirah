"""Deleting a candidate's personal data on request (T097, FR-076, migration 0022).

A member asks through public.request_candidate_deletion, which records the request and who made
it. The worker finds open requests through worker.due_for_purge, removes the stored originals,
then runs worker.purge_candidate, which clears the candidate's identity, empties the profile
content and names no file, closes the request and writes an activity row. Scores and the audit
trail stay. Members cannot delete candidate rows, files or originals themselves.
"""

import psycopg
import pytest

from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def request(cur: Cursor, tenant: Tenant, candidate: object | None = None) -> object:
    act_as(cur, tenant.user_id)
    cur.execute(
        "select public.request_candidate_deletion(%s)",
        (candidate or tenant.row_ids["candidate"],),
    )
    row = cur.fetchone()
    cur.execute("reset role")
    assert row is not None
    return row[0]


def as_worker(cur: Cursor, statement: str, params: tuple[object, ...]) -> list[tuple[object, ...]]:
    cur.execute("set local role masirah_worker")
    cur.execute(statement, params)
    rows = cur.fetchall() if cur.description else []
    cur.execute("reset role")
    return rows


def due(cur: Cursor) -> list[tuple[object, ...]]:
    return as_worker(
        cur, "select organisation_id, candidate_id, reason from worker.due_for_purge(100)", ()
    )


def purge(cur: Cursor, tenant: Tenant, reason: str = "request") -> None:
    as_worker(
        cur,
        "select worker.purge_candidate(%s, %s)",
        (tenant.row_ids["candidate"], reason),
    )


def test_a_request_records_who_asked_and_when(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    requested_at = request(cur, alpha)
    assert requested_at is not None
    cur.execute(
        "select requested_by, completed_at from public.deletion_request"
        " where candidate_id = %s and completed_at is null",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchall() == [(alpha.user_id, None)]
    cur.execute(
        "select actor_id from public.activity"
        " where subject_id = %s and action = 'candidate.deletion_requested'",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchall() == [(alpha.user_id,)]


def test_asking_twice_keeps_one_open_request(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    first = request(cur, alpha)
    assert request(cur, alpha) == first
    cur.execute(
        "select count(*) from public.deletion_request where candidate_id = %s"
        " and completed_at is null",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchone() == (1,)


def test_another_organisations_candidate_cannot_be_requested(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    with pytest.raises(psycopg.errors.NoDataFound):
        request(cur, alpha, beta.row_ids["candidate"])


def test_a_visitor_who_has_not_signed_in_cannot_ask(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select public.request_candidate_deletion(%s)", (alpha.row_ids["candidate"],))


def test_an_open_request_is_due_for_the_worker(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    assert (alpha.organisation_id, alpha.row_ids["candidate"], "request") not in due(cur)
    request(cur, alpha)
    assert (alpha.organisation_id, alpha.row_ids["candidate"], "request") in due(cur)


def test_the_worker_is_told_which_originals_to_remove(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    paths = as_worker(
        cur, "select storage_path from worker.purge_paths(%s)", (alpha.row_ids["candidate"],)
    )
    assert paths == [(alpha.storage_path,)]


def test_purging_removes_identity_profile_and_file_name(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    request(cur, alpha)
    purge(cur, alpha)
    cur.execute(
        "select full_name, email, phone, location, name_normalised, purged_at is not null"
        " from public.candidate where id = %s",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchone() == (None, None, None, None, None, True)
    cur.execute(
        "select p.profile, f.original_filename, f.purged_at is not null"
        " from public.cv_file f join public.parsed_profile p on p.cv_file_id = f.id"
        " where f.id = %s",
        (alpha.row_ids["cv_file"],),
    )
    assert cur.fetchone() == ({}, "removed", True)


def test_purging_closes_the_request_and_writes_what_was_removed(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    request(cur, alpha)
    purge(cur, alpha)
    assert (alpha.organisation_id, alpha.row_ids["candidate"], "request") not in due(cur)
    cur.execute(
        "select actor_id, metadata from public.activity"
        " where subject_id = %s and action = 'candidate.purged'",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchall() == [
        (None, {"reason": "request", "files": 1, "removed": ["identity", "profile", "original"]})
    ]


def test_scores_and_the_audit_trail_survive(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    request(cur, alpha)
    purge(cur, alpha)
    cur.execute("select total from public.score where id = %s", (alpha.row_ids["score"],))
    assert cur.fetchone() == (72,)
    cur.execute("select count(*) from public.activity where id = %s", (alpha.row_ids["activity"],))
    assert cur.fetchone() == (1,)


def test_purging_leaves_another_organisation_alone(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    request(cur, alpha)
    purge(cur, alpha)
    cur.execute(
        "select full_name from public.candidate where id = %s", (beta.row_ids["candidate"],)
    )
    assert cur.fetchone() == ("beta candidate",)


@pytest.mark.parametrize(
    "statement", ["delete from public.candidate", "delete from public.cv_file"]
)
def test_members_cannot_delete_candidates_or_files_themselves(
    cur: Cursor, tenants: tuple[Tenant, Tenant], statement: str
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(statement)


@pytest.mark.parametrize("role", ["authenticated", "anon"])
def test_only_the_worker_purges(cur: Cursor, tenants: tuple[Tenant, Tenant], role: str) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id if role == "authenticated" else None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select worker.purge_candidate(%s, 'request')", (alpha.row_ids["candidate"],))
