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
