"""An organisation at its spend ceiling stops costing anything (T093, AI-06, FR-026).

The real worker, queue and spend ledger, as the masirah_worker role: once an organisation has
spent its month's ceiling, a CV it uploads is not read by any model. It waits in the queue,
queued and visible as such, until the month renews, with none of its attempts used.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.adapters.postgres_spend_ledger import PostgresSpendLedger
from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.adapters.supabase_queue import SupabaseQueue
from masirah_pipeline.metering import MeteredModel
from masirah_pipeline.ports.model_provider import StructuredRequest, StructuredResponse
from masirah_pipeline.worker import Worker
from tests.database import Cursor, seed_tenant

pytestmark = pytest.mark.database

CV = Path(__file__).parents[1] / "fixtures" / "cvs" / "en-native-02.pdf"


@dataclass
class UnreachableModel:
    calls: list[StructuredRequest] = field(default_factory=list)

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.calls.append(request)
        raise AssertionError("an organisation at its ceiling must not reach a model")


def test_a_cv_from_an_organisation_at_its_ceiling_waits_for_next_month(cur: Cursor) -> None:
    cur.execute("delete from pgmq.q_cv_processing")
    tenant = seed_tenant(cur, "alpha")
    # The seeded tenant has spent 0.40 EGP this month (tests/database.py): its ceiling.
    cur.execute(
        "update public.organisation set monthly_spend_ceiling_egp = 0.40 where id = %s",
        (tenant.organisation_id,),
    )
    content = CV.read_bytes()
    file_id = uuid.uuid4()
    path = f"organisations/{tenant.organisation_id}/cv/{file_id}/cv.pdf"
    content_hash = hashlib.sha256(content).hexdigest()
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash) values (%s, %s, %s, 'cv.pdf', 'application/pdf',"
        " %s, %s)",
        (file_id, tenant.organisation_id, path, len(content), content_hash),
    )
    message = {
        "schema_version": 1,
        "job_type": "cv_processing",
        "organisation_id": str(tenant.organisation_id),
        "cv_file_id": str(file_id),
        "job_id": None,
        "content_hash": content_hash,
        "storage_path": path,
        "locale": "en",
        "enqueued_at": "2026-10-06T12:00:00+00:00",
    }
    cur.execute("set local role service_role")
    cur.execute("select * from pgmq_public.send('cv_processing', %s)", (Jsonb(message),))
    cur.execute("reset role")

    cur.execute("set local role masirah_worker")
    connection = cur.connection
    ledger = PostgresSpendLedger(connection)
    model = UnreachableModel()
    worker = Worker(
        queue=SupabaseQueue(connection),
        store=PostgresWorkerStore(connection),
        files=_Files(content),
        read_text=read_native_text,
        model=MeteredModel(model, "extraction", ledger),
        score=lambda request: None,
        budget=ledger,
    )
    assert worker.run_once() == 1
    cur.execute("reset role")

    assert model.calls == []
    cur.execute("select status::text from public.cv_file where id = %s", (file_id,))
    assert cur.fetchone() == ("queued",)
    cur.execute("select read_ct, vt > now(), message->>'cv_file_id' from pgmq.q_cv_processing")
    assert cur.fetchall() == [(0, True, str(file_id))]
    cur.execute(
        "select coalesce(sum(cost_egp), 0) from public.model_spend where organisation_id = %s",
        (tenant.organisation_id,),
    )
    # The seeded call alone, which reached the ceiling: nothing was added.
    assert cur.fetchone() == (Decimal("0.4000"),)


@dataclass
class _Files:
    content: bytes

    def fetch(self, storage_path: str) -> bytes:
        return self.content
