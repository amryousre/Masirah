"""Jobs and scores in Postgres, as the masirah_worker role (T057, AI-02).

Every score carries what AI-02 needs to reproduce it: the scoring and summary models and prompt
versions, the hash of what the model was sent, the weights' hash and the cost. A score for the
same application and weights is recorded once, however often the message is retried.
"""

import uuid
from decimal import Decimal

import psycopg
import pytest

from masirah_pipeline.adapters.score_repository import PostgresScoreRepository
from masirah_pipeline.domain.scoring import weights_from
from masirah_pipeline.ports.model_provider import ModelIdentity
from masirah_pipeline.ports.score_repository import ScoreRecord
from tests.database import WEIGHTS, Cursor, Tenant, seed_tenant

pytestmark = pytest.mark.database

NEW_WEIGHTS = "e" * 64


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


@pytest.fixture
def scores(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> PostgresScoreRepository:
    cur.execute("set local role masirah_worker")
    return PostgresScoreRepository(cur.connection)


def record(application_id: uuid.UUID, weights_hash: str = NEW_WEIGHTS) -> ScoreRecord:
    return ScoreRecord(
        application_id=application_id,
        total=82,
        components={"skills_match": {"rating": 90, "evidence": "SAP"}},
        justification="SAP at Nile Pharma.",
        summary="a\nb\nc",
        scoring=ModelIdentity("openai", "gpt-5.6-sol", "score-application/1"),
        summarising=ModelIdentity("anthropic", "claude-haiku-4-5", "summarise-candidate/1"),
        input_hash="f" * 64,
        weights_hash=weights_hash,
        cost_egp=Decimal("1.8346"),
    )


def test_it_reads_the_job(scores: PostgresScoreRepository, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    job = scores.job(alpha.organisation_id, alpha.row_ids["job"])
    assert job is not None
    assert job.title == "Accountant"
    assert job.weights == weights_from(WEIGHTS)


def test_another_tenants_job_is_not_there(
    scores: PostgresScoreRepository, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    assert scores.job(alpha.organisation_id, beta.row_ids["job"]) is None


def test_it_knows_a_score_exists_for_the_same_weights(
    scores: PostgresScoreRepository, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    application = alpha.row_ids["application"]
    assert scores.has_score(alpha.organisation_id, application, "c" * 64)
    assert not scores.has_score(alpha.organisation_id, application, NEW_WEIGHTS)


def test_a_score_is_recorded_with_everything_ai02_needs(
    scores: PostgresScoreRepository, tenants: tuple[Tenant, Tenant], cur: Cursor
) -> None:
    alpha, _ = tenants
    scores.record_score(alpha.organisation_id, record(alpha.row_ids["application"]))
    cur.execute(
        "select total, components, justification, summary, model_id, provider::text,"
        " prompt_version, summary_model_id, summary_provider::text, summary_prompt_version,"
        " input_hash, cost_egp from public.score where weights_hash = %s",
        (NEW_WEIGHTS,),
    )
    assert cur.fetchone() == (
        82,
        {"skills_match": {"rating": 90, "evidence": "SAP"}},
        "SAP at Nile Pharma.",
        "a\nb\nc",
        "gpt-5.6-sol",
        "openai",
        "score-application/1",
        "claude-haiku-4-5",
        "anthropic",
        "summarise-candidate/1",
        "f" * 64,
        Decimal("1.8346"),
    )


def test_the_same_score_is_recorded_once(
    scores: PostgresScoreRepository, tenants: tuple[Tenant, Tenant], cur: Cursor
) -> None:
    alpha, _ = tenants
    for _ in range(2):
        scores.record_score(alpha.organisation_id, record(alpha.row_ids["application"]))
    cur.execute("select count(*) from public.score where weights_hash = %s", (NEW_WEIGHTS,))
    assert cur.fetchone() == (1,)


def test_a_score_cannot_land_in_another_tenant(
    scores: PostgresScoreRepository, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    with pytest.raises(psycopg.errors.Error):
        scores.record_score(alpha.organisation_id, record(beta.row_ids["application"]))
