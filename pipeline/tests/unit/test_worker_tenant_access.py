"""What the worker may do with tenant data (T054, contracts/queue-message.md obligation 3).

The worker declares the organisation of the message it is handling, and row level security
admits only that organisation's rows. None of the queries below filter by organisation: when they
return only the declared tenant's rows, the database did the filtering.
"""

import uuid

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

from tests.database import Cursor, Tenant, seed_tenant

pytestmark = pytest.mark.database

WORKER_TABLES = ["job", "candidate", "cv_file", "parsed_profile", "application", "score"]


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def as_worker(cur: Cursor, organisation_id: uuid.UUID | None) -> None:
    if organisation_id is not None:
        cur.execute(
            "select set_config('masirah.organisation_id', %s, true)", (str(organisation_id),)
        )
    cur.execute("set local role masirah_worker")


def organisations_seen(cur: Cursor, table: str) -> set[uuid.UUID]:
    cur.execute(sql.SQL("select organisation_id from public.{}").format(sql.Identifier(table)))
    return {row[0] for row in cur.fetchall()}


@pytest.mark.parametrize("table", WORKER_TABLES)
def test_the_worker_sees_only_the_declared_organisation(
    cur: Cursor, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    alpha, _ = tenants
    as_worker(cur, alpha.organisation_id)
    assert organisations_seen(cur, table) == {alpha.organisation_id}


@pytest.mark.parametrize("table", WORKER_TABLES)
def test_a_worker_that_declares_nothing_sees_nothing(
    cur: Cursor, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    as_worker(cur, None)
    assert organisations_seen(cur, table) == set()


def test_the_worker_cannot_reach_another_tenants_file_by_identifier(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    as_worker(cur, alpha.organisation_id)
    cur.execute(
        "update public.cv_file set status = 'failed', failure_reason = 'x' where id = %s",
        (beta.row_ids["cv_file"],),
    )
    assert cur.rowcount == 0


def test_the_worker_cannot_create_a_candidate_in_another_tenant(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    as_worker(cur, alpha.organisation_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.candidate (organisation_id, full_name) values (%s, 'Planted')",
            (beta.organisation_id,),
        )


def test_the_worker_records_an_extraction(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    """Everything one extraction writes: a candidate, a new current profile, the file's status."""
    alpha, _ = tenants
    as_worker(cur, alpha.organisation_id)
    cur.execute(
        "insert into public.candidate (organisation_id, full_name, name_normalised)"
        " values (%s, 'Mona', 'منى') returning id",
        (alpha.organisation_id,),
    )
    row = cur.fetchone()
    assert row is not None
    candidate_id = row[0]
    cur.execute(
        "update public.parsed_profile set is_current = false where cv_file_id = %s",
        (alpha.row_ids["cv_file"],),
    )
    cur.execute(
        "insert into public.parsed_profile (organisation_id, cv_file_id, version, is_current,"
        " extraction_source, confidence, profile) values (%s, %s, 2, true, 'native_text', 0.9, %s)",
        (alpha.organisation_id, alpha.row_ids["cv_file"], Jsonb({"name": "Mona"})),
    )
    cur.execute(
        "update public.cv_file set status = 'extracted', candidate_id = %s where id = %s",
        (candidate_id, alpha.row_ids["cv_file"]),
    )
    assert cur.rowcount == 1


@pytest.mark.parametrize(
    "statement",
    [
        "update public.application set decision = 'rejected'",
        "insert into public.application (organisation_id, candidate_id, job_id, decision)"
        " values ({org}, {candidate}, {job}, 'shortlisted')",
        "update public.parsed_profile set profile = '{{}}'::jsonb",
        "update public.parsed_profile set field_overrides = '{{}}'::jsonb",
        "update public.score set total = 100",
        "delete from public.score",
        "delete from public.cv_file",
        "delete from public.candidate",
        "update public.cv_file set storage_path = 'elsewhere'",
        "update public.job set title = 'Changed'",
        "select * from public.organisation",
        "select * from public.app_user",
        "select * from public.activity",
    ],
    ids=[
        "decide",
        "insert-decided",
        "rewrite-profile",
        "overwrite-corrections",
        "rewrite-score",
        "delete-score",
        "delete-file",
        "delete-candidate",
        "move-file",
        "edit-job",
        "read-organisation",
        "read-users",
        "read-activity",
    ],
)
def test_what_the_worker_may_not_do(
    cur: Cursor, tenants: tuple[Tenant, Tenant], statement: str
) -> None:
    alpha, _ = tenants
    as_worker(cur, alpha.organisation_id)
    query = sql.SQL(statement).format(
        org=sql.Literal(alpha.organisation_id),
        candidate=sql.Literal(alpha.row_ids["candidate"]),
        job=sql.Literal(alpha.row_ids["job"]),
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(query)
