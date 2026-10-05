"""The purge sweep's database side, as the worker role runs it (T100, T101)."""

import pytest

from masirah_pipeline.adapters.postgres_purge_store import PostgresPurgeStore
from masirah_pipeline.ports.purge_store import DuePurge
from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenant(cur: Cursor) -> Tenant:
    return seed_tenant(cur, "delta")


def test_a_requested_candidate_is_found_cleared_and_no_longer_due(
    cur: Cursor, tenant: Tenant
) -> None:
    act_as(cur, tenant.user_id)
    cur.execute("select public.request_candidate_deletion(%s)", (tenant.row_ids["candidate"],))
    cur.execute("reset role")
    cur.execute("set local role masirah_worker")
    store = PostgresPurgeStore(cur.connection)

    due = DuePurge(tenant.organisation_id, tenant.row_ids["candidate"], "request")
    assert due in store.due(100)
    assert store.original_paths(tenant.row_ids["candidate"]) == [tenant.storage_path]

    store.purge(tenant.row_ids["candidate"], "request")
    assert due not in store.due(100)
    assert store.original_paths(tenant.row_ids["candidate"]) == []
