"""Rules the schema enforces in data rather than in application code.

Each one would otherwise live only in an interface or a worker, where a single missed code path
breaks it silently: comparable weights (T013), honest file states (T015), one current profile
(T016), a human behind every decision (T017, AI-07), immutable scores (T018, AI-02) and an
insert-only audit trail (T019).
"""

import uuid
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

from tests.database import WEIGHTS, Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenant(cur: Cursor) -> Tenant:
    return seed_tenant(cur, "gamma")


def act_as_member(cur: Cursor, tenant: Tenant) -> None:
    act_as(cur, tenant.user_id)


def insert_job(cur: Cursor, tenant: Tenant, weights: Any, title: str = "Engineer") -> None:
    cur.execute(
        "insert into public.job (organisation_id, title, weights) values (%s, %s, %s)",
        (tenant.organisation_id, title, Jsonb(weights)),
    )


def test_valid_weights_are_accepted(cur: Cursor, tenant: Tenant) -> None:
    insert_job(cur, tenant, WEIGHTS)


@pytest.mark.parametrize(
    "weights",
    [
        WEIGHTS | {"location": 11},
        {k: v for k, v in WEIGHTS.items() if k != "location"} | {"skills_match": 40},
        WEIGHTS | {"salary": 0},
        WEIGHTS | {"skills_match": 29.5, "location": 10.5},
        WEIGHTS | {"skills_match": 50, "location": -10},
        WEIGHTS | {"location": "10"},
        [30, 25, 15, 10, 10, 10],
    ],
    ids=["wrong-total", "missing-key", "extra-key", "fractional", "negative", "string", "array"],
)
def test_malformed_weights_cannot_be_saved(cur: Cursor, tenant: Tenant, weights: Any) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_job(cur, tenant, weights)


def test_a_job_needs_a_title(cur: Cursor, tenant: Tenant) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_job(cur, tenant, WEIGHTS, title="   ")


def test_failure_reason_accompanies_failed_status_only(cur: Cursor, tenant: Tenant) -> None:
    cv_file = tenant.row_ids["cv_file"]
    with pytest.raises(psycopg.errors.CheckViolation):
        cur.execute("update public.cv_file set status = 'failed' where id = %s", (cv_file,))


def test_failed_file_records_its_reason(cur: Cursor, tenant: Tenant) -> None:
    cur.execute(
        "update public.cv_file set status = 'failed', failure_reason = 'encrypted' where id = %s",
        (tenant.row_ids["cv_file"],),
    )
    assert cur.rowcount == 1


def test_a_file_is_stored_only_inside_its_own_tenant_folder(cur: Cursor, tenant: Tenant) -> None:
    elsewhere = f"organisations/{uuid.uuid4()}/cv/{tenant.row_ids['cv_file']}/cv.pdf"
    with pytest.raises(psycopg.errors.CheckViolation):
        cur.execute(
            "update public.cv_file set storage_path = %s where id = %s",
            (elsewhere, tenant.row_ids["cv_file"]),
        )


def test_only_one_profile_version_is_current(cur: Cursor, tenant: Tenant) -> None:
    with pytest.raises(psycopg.errors.UniqueViolation):
        cur.execute(
            "insert into public.parsed_profile (organisation_id, cv_file_id, version, is_current,"
            " extraction_source, confidence, profile)"
            " values (%s, %s, 2, true, 'vision_ocr', 0.9, '{}')",
            (tenant.organisation_id, tenant.row_ids["cv_file"]),
        )


def test_a_decision_without_a_human_cannot_be_stored(cur: Cursor, tenant: Tenant) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        cur.execute(
            "update public.application set decision = 'rejected', decided_at = now() where id = %s",
            (tenant.row_ids["application"],),
        )


def test_a_member_records_their_own_decision(cur: Cursor, tenant: Tenant) -> None:
    act_as_member(cur, tenant)
    cur.execute(
        "update public.application set decision = 'rejected', decided_by = %s, decided_at = now()"
        " where id = %s",
        (tenant.user_id, tenant.row_ids["application"]),
    )
    assert cur.rowcount == 1


def test_a_member_cannot_attribute_a_decision_to_someone_else(cur: Cursor, tenant: Tenant) -> None:
    colleague = uuid.uuid4()
    cur.execute("insert into auth.users (id, email) values (%s, 'c@example.test')", (colleague,))
    cur.execute(
        "insert into public.app_user (id, organisation_id, email)"
        " values (%s, %s, 'c@example.test')",
        (colleague, tenant.organisation_id),
    )
    act_as_member(cur, tenant)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "update public.application set decision = 'rejected', decided_by = %s,"
            " decided_at = now() where id = %s",
            (colleague, tenant.row_ids["application"]),
        )


@pytest.mark.parametrize("role", ["authenticated", "service_role"])
def test_scores_are_immutable(cur: Cursor, tenant: Tenant, role: str) -> None:
    if role == "authenticated":
        act_as_member(cur, tenant)
    else:
        cur.execute("set local role service_role")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("update public.score set total = 99 where id = %s", (tenant.row_ids["score"],))


def test_members_cannot_write_scores(cur: Cursor, tenant: Tenant) -> None:
    act_as_member(cur, tenant)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.score (organisation_id, application_id, total, components,"
            " justification, summary, model_id, provider, prompt_version, input_hash,"
            " weights_hash, cost_egp) values (%s, %s, 100, '{}', 'x', 'x', 'm', 'openai', 'v1',"
            " %s, %s, 0)",
            (tenant.organisation_id, tenant.row_ids["application"], "d" * 64, "e" * 64),
        )


@pytest.mark.parametrize("role", ["authenticated", "service_role"])
@pytest.mark.parametrize(
    "statement",
    [
        "update public.activity set action = 'candidate.exported' where id = %s",
        "delete from public.activity where id = %s",
    ],
    ids=["update", "delete"],
)
def test_the_audit_trail_is_insert_only(
    cur: Cursor, tenant: Tenant, role: str, statement: str
) -> None:
    if role == "authenticated":
        act_as_member(cur, tenant)
    else:
        cur.execute("set local role service_role")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(statement, (tenant.row_ids["activity"],))


def test_a_member_cannot_record_an_action_as_someone_else(cur: Cursor, tenant: Tenant) -> None:
    act_as_member(cur, tenant)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.activity (organisation_id, actor_id, action, subject_type,"
            " subject_id) values (%s, %s, 'candidate.viewed', 'candidate', %s)",
            (tenant.organisation_id, uuid.uuid4(), tenant.row_ids["candidate"]),
        )


@pytest.mark.parametrize("table", ["candidate", "cv_file"])
def test_members_cannot_delete_personal_data_directly(
    cur: Cursor, tenant: Tenant, table: str
) -> None:
    """Erasure (FR-076) runs server-side and removes the stored original first (T100, T101).

    A direct delete would leave the original CV behind in storage, so members have none.
    """
    act_as_member(cur, tenant)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            sql.SQL("delete from public.{} where id = %s").format(sql.Identifier(table)),
            (tenant.row_ids[table],),
        )


def test_members_cannot_delete_stored_originals(cur: Cursor, tenant: Tenant) -> None:
    """Originals are retained unchanged (FR-012) until erasure removes them.

    Supabase blocks direct SQL deletes from storage with a trigger, so this takes the path the
    Storage API takes: it lifts that guard for the transaction and deletes as the member,
    leaving row level security as the only thing standing between the member and the file.
    """
    act_as_member(cur, tenant)
    cur.execute("select set_config('storage.allow_delete_query', 'true', true)")
    cur.execute("delete from storage.objects where name = %s", (tenant.storage_path,))
    assert cur.rowcount == 0
    cur.execute("select count(*) from storage.objects where name = %s", (tenant.storage_path,))
    assert cur.fetchone() == (1,)


def test_every_foreign_key_has_a_covering_index(cur: Cursor) -> None:
    """Every policy filters by organisation, and deleting a referenced row scans its referrers.

    An index covers a foreign key when its leading columns are exactly the key's columns.
    """
    cur.execute(
        "select c.conrelid::regclass::text || ' ' || c.conname"
        " from pg_constraint c"
        " where c.contype = 'f' and c.connamespace = 'public'::regnamespace"
        " and not exists ("
        "   select 1 from pg_index i"
        "   where i.indrelid = c.conrelid"
        "   and (i.indkey::int2[])[0:cardinality(c.conkey) - 1] @> c.conkey"
        "   and (i.indkey::int2[])[0:cardinality(c.conkey) - 1] <@ c.conkey"
        " )"
        " order by 1"
    )
    assert [row[0] for row in cur.fetchall()] == []
