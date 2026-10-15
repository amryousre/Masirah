"""Tenant isolation (NFR-07, Constitution II).

A signed-in session in organisation A must reach nothing that belongs to organisation B: not by
identifier, not by an unfiltered list, not by storage path, and not by writing. None of the
queries below filter by organisation. When they return only A's rows, the database did the
filtering, which is the point: isolation is enforced by row level security, not by query code.
"""

import uuid
from typing import Any

import psycopg
import pytest
from psycopg import sql

from tests.database import CV_BUCKET, TENANT_TABLES, Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def select_column(cur: Cursor, table: str, column: str) -> set[Any]:
    cur.execute(
        sql.SQL("select {} from public.{}").format(sql.Identifier(column), sql.Identifier(table))
    )
    return {row[0] for row in cur.fetchall()}


def test_every_public_table_carries_organisation_and_rls(cur: Cursor) -> None:
    cur.execute(
        "select c.relname, c.relrowsecurity,"
        " exists (select 1 from information_schema.columns col"
        "   where col.table_schema = 'public' and col.table_name = c.relname"
        "   and col.column_name = 'organisation_id')"
        " from pg_class c join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = 'public' and c.relkind in ('r', 'p')"
    )
    tables = {name: (rls, tenant_column) for name, rls, tenant_column in cur.fetchall()}
    assert set(tables) >= {"organisation", *TENANT_TABLES}
    offenders = [
        name
        for name, (rls, tenant_column) in tables.items()
        if not rls or (name != "organisation" and not tenant_column)
    ]
    assert offenders == []


def test_both_tenants_rows_exist_when_rls_does_not_apply(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """The control: as the table owner both tenants are visible, so the filtering is RLS."""
    alpha, beta = tenants
    for table in TENANT_TABLES:
        assert select_column(cur, table, "organisation_id") >= {
            alpha.organisation_id,
            beta.organisation_id,
        }


def test_unfiltered_organisation_list_returns_only_own(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    assert select_column(cur, "organisation", "id") == {alpha.organisation_id}


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_unfiltered_list_returns_only_own_rows(
    cur: Cursor, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    assert select_column(cur, table, "organisation_id") == {alpha.organisation_id}


@pytest.mark.parametrize("table", ["organisation", *TENANT_TABLES])
def test_other_tenants_rows_are_unreachable_by_identifier(
    cur: Cursor, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    alpha, beta = tenants
    target = beta.organisation_id if table == "organisation" else beta.row_ids[table]
    act_as(cur, alpha.user_id)
    cur.execute(
        sql.SQL("select count(*) from public.{} where id = %s").format(sql.Identifier(table)),
        (target,),
    )
    assert cur.fetchone() == (0,)


def test_cannot_insert_a_row_into_another_organisation(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.candidate (organisation_id, full_name) values (%s, 'Planted')",
            (beta.organisation_id,),
        )


def test_cannot_move_own_row_into_another_organisation(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "update public.candidate set organisation_id = %s where id = %s",
            (beta.organisation_id, alpha.row_ids["candidate"]),
        )


def test_cannot_change_or_delete_another_organisations_rows(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    cur.execute(
        "update public.candidate set full_name = 'Changed' where id = %s",
        (beta.row_ids["candidate"],),
    )
    assert cur.rowcount == 0
    cur.execute("delete from public.job where id = %s", (beta.row_ids["job"],))
    assert cur.rowcount == 0


@pytest.mark.parametrize("table", ["organisation", *TENANT_TABLES])
def test_anonymous_sessions_have_no_access(
    cur: Cursor, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(sql.SQL("select 1 from public.{}").format(sql.Identifier(table)))


def test_other_tenants_stored_files_are_unreachable_by_path(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    cur.execute("select name from storage.objects where bucket_id = %s", (CV_BUCKET,))
    visible = {row[0] for row in cur.fetchall()}
    assert alpha.storage_path in visible
    assert beta.storage_path not in visible


def test_cannot_store_a_file_under_another_organisations_path(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into storage.objects (bucket_id, name) values (%s, %s)",
            (CV_BUCKET, f"organisations/{beta.organisation_id}/cv/{uuid.uuid4()}/planted.pdf"),
        )


# T095: what has been added since T020 reads tenant data through views and functions as well as
# tables. The tests below hold every one of them to the same rule, and fail on a new one until it
# is accounted for.

TENANT_VIEWS = ["job_overview", "job_candidates"]


def test_every_public_view_runs_with_the_callers_row_security(cur: Cursor) -> None:
    cur.execute(
        "select c.relname, coalesce(c.reloptions, '{}')"
        " from pg_class c join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = 'public' and c.relkind = 'v' order by c.relname"
    )
    views = cur.fetchall()
    assert sorted(name for name, _ in views) == sorted(TENANT_VIEWS)
    for name, options in views:
        assert "security_invoker=true" in options, f"{name} would bypass row level security"


@pytest.mark.parametrize("view", TENANT_VIEWS)
def test_unfiltered_view_returns_only_own_rows(
    cur: Cursor, tenants: tuple[Tenant, Tenant], view: str
) -> None:
    alpha, beta = tenants
    act_as(cur, beta.user_id)
    assert select_column(cur, view, "organisation_id") <= {beta.organisation_id}
    cur.execute("reset role")
    act_as(cur, alpha.user_id)
    assert select_column(cur, view, "organisation_id") == {alpha.organisation_id}


# Each runs as its owner and so must check the caller's organisation itself; each has tests of
# exactly that in its own file. A function added here needs the same before it joins the list.
DEFINER_FUNCTIONS_MEMBERS_CAN_CALL = {
    "enqueue_cv_processing": "test_enqueue_cv.py",
    "join_waitlist": "test_waitlist.py (insert only, into a list no API role can read)",
    "correct_profile": "test_field_overrides.py",
    "record_decision": "test_decisions.py",
    "request_candidate_deletion": "test_deletion.py",
    "set_retention": "test_retention.py",
    "service_health": "test_service_health.py (no tenant data: counts and ages only)",
}


def test_every_definer_function_a_member_can_call_is_accounted_for(cur: Cursor) -> None:
    cur.execute(
        "select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
        " where n.nspname = 'public' and p.prosecdef"
        " and has_function_privilege('authenticated', p.oid, 'execute')"
        " order by p.proname"
    )
    assert {row[0] for row in cur.fetchall()} == set(DEFINER_FUNCTIONS_MEMBERS_CAN_CALL)


# The same for visitors who are not signed in: each function they can call runs as its owner and
# so is held to tests of what it lets a stranger do, in its own file.
DEFINER_FUNCTIONS_VISITORS_CAN_CALL = {
    "join_waitlist": "test_waitlist.py (insert only, into a list no API role can read)",
    "service_health": "test_service_health.py (no tenant data: counts and ages only)",
}


def test_every_definer_function_a_visitor_can_call_is_accounted_for(cur: Cursor) -> None:
    cur.execute(
        "select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
        " where n.nspname = 'public' and p.prosecdef"
        " and has_function_privilege('anon', p.oid, 'execute')"
        " order by p.proname"
    )
    assert {row[0] for row in cur.fetchall()} == set(DEFINER_FUNCTIONS_VISITORS_CAN_CALL)
