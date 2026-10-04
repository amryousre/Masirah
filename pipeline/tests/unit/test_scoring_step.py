"""The worker's Scorer: load the job, assess, record the score (T057, obligations 1 and 5)."""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest

from masirah_pipeline.domain.justification import JobSpec
from masirah_pipeline.domain.profile import Employment, Profile
from masirah_pipeline.domain.scoring import DEFAULT_WEIGHTS, weights_hash
from masirah_pipeline.ports.model_provider import (
    ModelIdentity,
    StructuredRequest,
    StructuredResponse,
    Usage,
)
from masirah_pipeline.ports.score_repository import ScoreRecord
from masirah_pipeline.scoring_step import ApplicationScorer
from masirah_pipeline.worker import ScoringRequest

ORG, APPLICATION, JOB_ID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
JOB = JobSpec("Accountant", None, ("SAP",), (), 3, "Cairo", None, DEFAULT_WEIGHTS)
PROFILE = Profile(
    name="Mona",
    emails=(),
    phones=(),
    location="Cairo",
    years_of_experience=None,
    employment=(Employment("Nile Pharma", "Accountant", "2019", "present"),),
    education=(),
    skills=("SAP",),
    languages=(),
    certifications=(),
)
RATINGS = {
    "skills_match": 90,
    "experience_relevance": 80,
    "education": 50,
    "tenure_stability": 70,
    "language": 100,
    "location": 100,
}


@dataclass
class FakeModel:
    output: dict[str, Any]
    cost: Decimal
    model_id: str
    calls: int = 0

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.calls += 1
        return StructuredResponse(
            output=self.output,
            identity=ModelIdentity("openai", self.model_id, request.prompt_version),
            usage=Usage(10, 10),
            cost_egp=self.cost,
            payload=b"sent",
        )


@dataclass
class FakeScores:
    job_spec: JobSpec | None = JOB
    existing: bool = False
    recorded: list[ScoreRecord] = field(default_factory=list)

    def job(self, organisation_id: uuid.UUID, job_id: uuid.UUID) -> JobSpec | None:
        assert (organisation_id, job_id) == (ORG, JOB_ID)
        return self.job_spec

    def has_score(self, organisation_id: uuid.UUID, application_id: uuid.UUID, wh: str) -> bool:
        return self.existing

    def record_score(self, organisation_id: uuid.UUID, score: ScoreRecord) -> None:
        self.recorded.append(score)


def models() -> tuple[FakeModel, FakeModel]:
    components = {name: {"rating": r, "evidence": f"why {name}"} for name, r in RATINGS.items()}
    strong = FakeModel(
        {"components": components, "justification": "SAP at Nile Pharma."},
        Decimal("1.23456"),
        "gpt-5.6-sol",
    )
    cheap = FakeModel({"summary": ["a", "b", "c"]}, Decimal("0.1"), "gpt-5.6-luna")
    return strong, cheap


def request(cost: str = "0.5") -> ScoringRequest:
    return ScoringRequest(ORG, APPLICATION, JOB_ID, PROFILE, "en", Decimal(cost))


def test_a_score_is_recorded_with_its_identity_and_whole_cost() -> None:
    scores, (strong, cheap) = FakeScores(), models()
    ApplicationScorer(scores, strong, cheap)(request())
    [score] = scores.recorded
    assert score.application_id == APPLICATION
    # 90*30 + 80*25 + 50*15 + 70*10 + 100*10 + 100*10 = 8150, over 100, rounded half up
    assert score.total == 82
    assert score.components["skills_match"] == {"rating": 90, "evidence": "why skills_match"}
    assert (score.justification, score.summary) == ("SAP at Nile Pharma.", "a\nb\nc")
    assert (score.scoring.model_id, score.summarising.model_id) == ("gpt-5.6-sol", "gpt-5.6-luna")
    assert score.weights_hash == weights_hash(DEFAULT_WEIGHTS)
    # Extraction 0.5 + scoring 1.23456 + summary 0.1, kept to the column's four places.
    assert score.cost_egp == Decimal("1.8346")


def test_an_existing_score_for_the_same_weights_is_not_paid_for_again() -> None:
    scores, (strong, cheap) = FakeScores(existing=True), models()
    ApplicationScorer(scores, strong, cheap)(request())
    assert (strong.calls, cheap.calls, scores.recorded) == (0, 0, [])


def test_a_job_that_is_gone_cannot_be_scored() -> None:
    scores, (strong, cheap) = FakeScores(job_spec=None), models()
    with pytest.raises(LookupError):
        ApplicationScorer(scores, strong, cheap)(request())
    assert strong.calls == 0
