"""No submitted file is ever lost (T073, SC-006, FR-011).

Every kind of file that defeats extraction is uploaded beside a good CV and run through the real
worker, queue, text extraction and adapters, as the masirah_worker role. Each one must end in a
settled state the recruiter can see: extracted, waiting for review with its reason, or failed
with its reason. None may stay queued or half-processed, and no message may be left behind.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.adapters.postgres_spend_ledger import PostgresSpendLedger
from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.adapters.score_repository import PostgresScoreRepository
from masirah_pipeline.adapters.supabase_queue import SupabaseQueue
from masirah_pipeline.extraction import PROMPT_VERSION as EXTRACT_PROMPT_VERSION
from masirah_pipeline.metering import MeteredModel
from masirah_pipeline.ports.model_provider import (
    ModelIdentity,
    StructuredRequest,
    StructuredResponse,
    Usage,
)
from masirah_pipeline.scoring_step import ApplicationScorer
from masirah_pipeline.worker import Worker
from tests.database import Cursor, Tenant, seed_tenant

pytestmark = pytest.mark.database

CORPUS = Path(__file__).parents[1] / "fixtures" / "cvs"
GOOD = "en-native-02.pdf"
# Its text is a real CV, but the model answers with another CV's profile, as a model that misread
# it would: too little of the answer is in the text to trust.
MISREAD = "en-native-05.pdf"


def _profile(name: str) -> dict[str, Any]:
    label = json.loads((CORPUS / name).with_suffix(".json").read_text(encoding="utf-8"))
    profile: dict[str, Any] = label["profile"]
    return profile


def _encrypted() -> bytes:
    doc = pymupdf.open(CORPUS / GOOD)
    locked: bytes = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret"
    )
    return locked


# Each file: its name, content, MIME type, and where it must end.
FILES: dict[str, tuple[bytes, str, tuple[str, str | None, str | None, bool]]] = {
    "good.pdf": ((CORPUS / GOOD).read_bytes(), "application/pdf", ("extracted", None, None, False)),
    "misread.pdf": (
        (CORPUS / MISREAD).read_bytes(),
        "application/pdf",
        ("needs_review", "low_confidence", None, False),
    ),
    "french.pdf": (
        (CORPUS / "syn-fr-native-01.pdf").read_bytes(),
        "application/pdf",
        ("needs_review", "unsupported_language", "fr", False),
    ),
    "scan.pdf": (
        (CORPUS / "en-scanned-01.pdf").read_bytes(),
        "application/pdf",
        ("needs_review", "no_text", None, False),
    ),
    "photo.jpg": (
        (CORPUS / "syn-ar-photographed-01.jpg").read_bytes(),
        "image/jpeg",
        ("needs_review", "no_text", None, False),
    ),
    "locked.pdf": (_encrypted(), "application/pdf", ("failed", None, None, True)),
    "corrupt.pdf": (
        b"%PDF-1.7\n" + b"\x00garbage" * 50,
        "application/pdf",
        ("failed", None, None, True),
    ),
    "empty.pdf": (b"", "application/pdf", ("failed", None, None, True)),
}


@dataclass
class MisreadingModel:
    """Answers extraction with the good CV's own profile, and the misread one with another's."""

    requests: list[StructuredRequest] = field(default_factory=list)

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        assert request.prompt_version == EXTRACT_PROMPT_VERSION, "nothing here is scored"
        self.requests.append(request)
        own = request.content == read_native_text((CORPUS / GOOD).read_bytes())
        return StructuredResponse(
            output=_profile(GOOD) if own else _profile("en-native-07.pdf"),
            identity=ModelIdentity("anthropic", "corpus-model", request.prompt_version),
            usage=Usage(1000, 100),
            cost_egp=Decimal(1),
            payload=request.content.encode(),
        )


@dataclass
class Uploads:
    content: dict[str, bytes] = field(default_factory=dict)

    def fetch(self, storage_path: str) -> bytes:
        return self.content[storage_path]


def upload(cur: Cursor, tenant: Tenant, uploads: Uploads, name: str) -> uuid.UUID:
    """What the web application does on upload, without a job, so nothing is scored."""
    content, mime_type, _ = FILES[name]
    content_hash = hashlib.sha256(content).hexdigest()
    file_id = uuid.uuid4()
    path = f"organisations/{tenant.organisation_id}/cv/{file_id}/{name}"
    uploads.content[path] = content
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash) values (%s, %s, %s, %s, %s, %s, %s)",
        (file_id, tenant.organisation_id, path, name, mime_type, len(content), content_hash),
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
    return file_id


@pytest.fixture
def run(cur: Cursor) -> dict[str, uuid.UUID]:
    cur.execute("delete from pgmq.q_cv_processing")
    tenant = seed_tenant(cur, "alpha")
    uploads, model = Uploads(), MisreadingModel()
    uploaded = {name: upload(cur, tenant, uploads, name) for name in FILES}
    cur.execute("set local role masirah_worker")
    connection = cur.connection
    ledger = PostgresSpendLedger(connection)
    worker = Worker(
        queue=SupabaseQueue(connection),
        store=PostgresWorkerStore(connection),
        files=uploads,
        read_text=read_native_text,
        model=MeteredModel(model, "extraction", ledger),
        score=ApplicationScorer(
            PostgresScoreRepository(connection),
            MeteredModel(model, "scoring", ledger),
            MeteredModel(model, "summary", ledger),
        ),
        budget=ledger,
    )
    handled = 0
    while batch := worker.run_once():
        handled += batch
    assert handled == len(FILES)
    cur.execute("reset role")
    return uploaded


@pytest.mark.parametrize("name", FILES)
def test_every_file_ends_where_the_recruiter_can_see_it(
    cur: Cursor, run: dict[str, uuid.UUID], name: str
) -> None:
    status, reason, language, failed = FILES[name][2]
    cur.execute(
        "select status::text, review_reason::text, review_language, failure_reason is not null"
        " from public.cv_file where id = %s",
        (run[name],),
    )
    assert cur.fetchone() == (status, reason, language, failed)


def test_no_message_is_left_in_the_queue(cur: Cursor, run: dict[str, uuid.UUID]) -> None:
    cur.execute("select count(*) from pgmq.q_cv_processing")
    assert cur.fetchone() == (0,)
