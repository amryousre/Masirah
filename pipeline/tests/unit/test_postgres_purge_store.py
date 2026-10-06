"""The purge sweep's database side, as the worker role runs it (T100, T101)."""

import uuid

import pytest

from masirah_pipeline.adapters.postgres_purge_store import PostgresPurgeStore
from masirah_pipeline.ports.purge_store import DueFile, DuePurge, OriginalFile
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
    original = OriginalFile(tenant.row_ids["cv_file"], tenant.storage_path)
    assert store.originals(tenant.row_ids["candidate"]) == [original]

    store.purge(tenant.row_ids["candidate"], "request", [original.cv_file_id])
    assert due not in store.due(100)
    assert store.originals(tenant.row_ids["candidate"]) == []


def test_an_old_file_without_a_candidate_is_found_and_cleared(cur: Cursor, tenant: Tenant) -> None:
    orphan = uuid.uuid4()
    path = tenant.storage_path.replace(str(tenant.row_ids["cv_file"]), str(orphan))
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash, status, failure_reason, created_at, updated_at)"
        " values (%s, %s, %s, 'cv.pdf', 'application/pdf', 10, %s, 'failed', 'encrypted',"
        " now() - interval '3 years', now() - interval '3 years')",
        (orphan, tenant.organisation_id, path, "e" * 64),
    )
    cur.execute("set local role masirah_worker")
    store = PostgresPurgeStore(cur.connection)
    assert DueFile(tenant.organisation_id, orphan, path) in store.due_files(100)
    store.purge_file(orphan)
    assert all(due.cv_file_id != orphan for due in store.due_files(100))
