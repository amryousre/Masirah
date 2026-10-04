"""The core loop end to end in the pipeline: job, upload, extract, score, rank (T040).

Everything is real except the models and the file store: messages travel through the real queue,
the worker reads real CVs from the corpus with the real text extraction, and records profiles,
candidates, applications and scores through the real adapters, as the masirah_worker role under
row level security. The models answer with each CV's labelled profile, so the run costs nothing
and needs no provider account.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.adapters.score_repository import PostgresScoreRepository
from masirah_pipeline.adapters.supabase_queue import SupabaseQueue
from masirah_pipeline.assessment import SCORE_PROMPT_VERSION, SUMMARY_PROMPT_VERSION
from masirah_pipeline.extraction import PROMPT_VERSION as EXTRACT_PROMPT_VERSION
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
# Two real CVs, and the skills match each model rating gives them, so the ranking is known.
CVS = {"en-native-02.pdf": 90, "en-native-05.pdf": 40}


@dataclass
class CorpusModel:
    """Answers extraction with the CV's labelled profile, scoring with a fixed skills rating per
    CV, and summaries with three lines. Each answer costs one pound."""

    requests: list[StructuredRequest] = field(default_factory=list)

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.requests.append(request)
        output = self._answer(request)
        return StructuredResponse(
            output=output,
            identity=ModelIdentity("anthropic", "corpus-model", request.prompt_version),
            usage=Usage(1000, 100),
            cost_egp=Decimal(1),
            payload=request.content.encode(),
        )

    def _answer(self, request: StructuredRequest) -> dict[str, Any]:
        if request.prompt_version == EXTRACT_PROMPT_VERSION:
            name = next(cv for cv in CVS if _text(cv) == request.content)
            label = json.loads((CORPUS / name).with_suffix(".json").read_text(encoding="utf-8"))
            profile: dict[str, Any] = label["profile"]
            return profile
        if request.prompt_version == SCORE_PROMPT_VERSION:
            employers = request.content
            skills = next(rating for cv, rating in CVS.items() if _first_employer(cv) in employers)
            ratings = {
                "skills_match": skills,
                "experience_relevance": 50,
                "education": 50,
                "tenure_stability": 50,
                "language": 50,
                "location": 50,
            }
            return {
                "components": {k: {"rating": v, "evidence": "seen"} for k, v in ratings.items()},
                "justification": "Cites the CV.",
            }
        assert request.prompt_version == SUMMARY_PROMPT_VERSION
        return {"summary": ["One.", "Two.", "Three."]}


def _text(name: str) -> str:
    return read_native_text((CORPUS / name).read_bytes())


def _first_employer(name: str) -> str:
    label = json.loads((CORPUS / name).with_suffix(".json").read_text(encoding="utf-8"))
    employer: str = label["profile"]["employment"][0]["employer"]
    return employer


@dataclass
class CorpusFiles:
    paths: dict[str, str] = field(default_factory=dict)

    def fetch(self, storage_path: str) -> bytes:
        return (CORPUS / self.paths[storage_path]).read_bytes()


def upload(cur: Cursor, tenant: Tenant, files: CorpusFiles, name: str) -> uuid.UUID:
    """What the web application does on upload: a cv_file row, then a queue message."""
    content = (CORPUS / name).read_bytes()
    content_hash = hashlib.sha256(content).hexdigest()
    file_id = uuid.uuid4()
    path = f"organisations/{tenant.organisation_id}/cv/{file_id}/{name}"
    files.paths[path] = name
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash) values (%s, %s, %s, %s, 'application/pdf', %s, %s)",
        (file_id, tenant.organisation_id, path, name, len(content), content_hash),
    )
    message = {
        "schema_version": 1,
        "job_type": "cv_processing",
        "organisation_id": str(tenant.organisation_id),
        "cv_file_id": str(file_id),
        "job_id": str(tenant.row_ids["job"]),
        "content_hash": content_hash,
        "storage_path": path,
        "locale": "en",
        "enqueued_at": "2026-10-04T12:00:00+00:00",
    }
    cur.execute("set local role service_role")
    cur.execute("select * from pgmq_public.send('cv_processing', %s)", (Jsonb(message),))
    cur.execute("reset role")
    return file_id


@pytest.fixture
def run(cur: Cursor) -> tuple[Tenant, dict[str, uuid.UUID], CorpusModel]:
    cur.execute("delete from pgmq.q_cv_processing")
    tenant = seed_tenant(cur, "alpha")
    files, model = CorpusFiles(), CorpusModel()
    uploaded = {name: upload(cur, tenant, files, name) for name in CVS}
    cur.execute("set local role masirah_worker")
    connection = cur.connection
    worker = Worker(
        queue=SupabaseQueue(connection),
        store=PostgresWorkerStore(connection),
        files=files,
        read_text=read_native_text,
        model=model,
        score=ApplicationScorer(PostgresScoreRepository(connection), model, model),
    )
    assert worker.run_once() == len(CVS)
    cur.execute("reset role")
    return tenant, uploaded, model


def test_every_cv_is_extracted_into_a_candidate_and_profile(
    cur: Cursor, run: tuple[Tenant, dict[str, uuid.UUID], CorpusModel]
) -> None:
    _, uploaded, _ = run
    for name, file_id in uploaded.items():
        cur.execute(
            "select f.status::text, c.full_name, p.version, p.is_current"
            " from public.cv_file f join public.candidate c on c.id = f.candidate_id"
            " join public.parsed_profile p on p.cv_file_id = f.id where f.id = %s",
            (file_id,),
        )
        label = json.loads((CORPUS / name).with_suffix(".json").read_text(encoding="utf-8"))
        assert cur.fetchone() == ("extracted", label["profile"]["name"], 1, True)


def test_the_candidates_are_ranked_by_score_against_the_job(
    cur: Cursor, run: tuple[Tenant, dict[str, uuid.UUID], CorpusModel]
) -> None:
    tenant, uploaded, _ = run
    cur.execute(
        "select f.id, s.total, s.cost_egp from public.score s"
        " join public.application a on a.id = s.application_id"
        " join public.cv_file f on f.candidate_id = a.candidate_id"
        " where a.job_id = %s and f.id = any(%s) order by s.total desc",
        (tenant.row_ids["job"], list(uploaded.values())),
    )
    ranked = cur.fetchall()
    assert [file_id for file_id, _, _ in ranked] == [
        uploaded["en-native-02.pdf"],
        uploaded["en-native-05.pdf"],
    ]
    # Extraction, scoring and summary: one pound each.
    assert {cost for _, _, cost in ranked} == {Decimal(3)}


def test_every_message_is_deleted_once_its_work_is_committed(
    cur: Cursor, run: tuple[Tenant, dict[str, uuid.UUID], CorpusModel]
) -> None:
    cur.execute("select count(*) from pgmq.q_cv_processing")
    assert cur.fetchone() == (0,)


def test_no_scoring_or_summary_request_carries_a_candidates_name(
    run: tuple[Tenant, dict[str, uuid.UUID], CorpusModel],
) -> None:
    _, _, model = run
    names = [
        json.loads((CORPUS / cv).with_suffix(".json").read_text(encoding="utf-8"))["profile"][
            "name"
        ]
        for cv in CVS
    ]
    later = [r for r in model.requests if r.prompt_version != EXTRACT_PROMPT_VERSION]
    assert len(later) == 2 * len(CVS)
    assert not any(name in request.content for name in names for request in later)
