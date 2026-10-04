"""Scoring a candidate against a job, with justification and summary (T056, FR-013 to FR-017).

The strong tier rates the six components and writes the justification; the cheap tier writes
the summary (AI-05). Both see only the redacted profile. The total is this code's arithmetic over
the job's weights, never a number the model chose.
"""

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest

from masirah_pipeline.assessment import (
    SCORE_PROMPT_VERSION,
    SUMMARY_PROMPT_VERSION,
    score_application,
)
from masirah_pipeline.domain.justification import JobSpec
from masirah_pipeline.domain.profile import Education, Employment, Profile
from masirah_pipeline.domain.scoring import DEFAULT_WEIGHTS, weights_hash
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    ModelIdentity,
    StructuredRequest,
    StructuredResponse,
    Usage,
)

NAME = "Zeinab Fathy"
EMAIL = "zeinab@mail.test"

PROFILE = Profile(
    name=NAME,
    emails=(EMAIL,),
    phones=("+201001234567",),
    location="Cairo",
    years_of_experience=6.0,
    employment=(Employment("Nile Pharma", "محاسبة", "2019-03", "present"),),
    education=(Education("Cairo University", "BCom", "2010", "2014"),),
    skills=("SAP", "Excel"),
    languages=(),
    certifications=(),
)
JOB = JobSpec(
    title="Senior Accountant",
    description="Month-end close and IFRS reporting.",
    required_skills=("SAP",),
    preferred_skills=("IFRS",),
    minimum_experience_years=5,
    location="Cairo",
    language_requirement="English",
    weights=DEFAULT_WEIGHTS,
)
RATINGS = {
    "skills_match": 80,
    "experience_relevance": 90,
    "education": 70,
    "tenure_stability": 60,
    "language": 50,
    "location": 100,
}
JUSTIFICATION = "Six years at Nile Pharma on month-end close; SAP listed; no IFRS evidence."
SUMMARY_LINES = ["Accountant with six years in pharma.", "Uses SAP daily.", "Based in Cairo."]


@dataclass
class FakeModel:
    output: dict[str, Any]
    cost: Decimal
    requests: list[StructuredRequest] = field(default_factory=list)

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.requests.append(request)
        return StructuredResponse(
            output=self.output,
            identity=ModelIdentity("anthropic", "model-x", request.prompt_version),
            usage=Usage(100, 50),
            cost_egp=self.cost,
            payload=f"payload:{request.content}".encode(),
        )


def strong(ratings: dict[str, Any] | None = None) -> FakeModel:
    components = {
        name: {"rating": rating, "evidence": f"evidence for {name}"}
        for name, rating in (ratings or RATINGS).items()
    }
    return FakeModel({"components": components, "justification": JUSTIFICATION}, Decimal("1.5"))


def cheap(lines: list[str] | None = None) -> FakeModel:
    return FakeModel({"summary": lines or SUMMARY_LINES}, Decimal("0.1"))


def test_the_total_is_the_weighted_mean_of_the_ratings() -> None:
    assessment = score_application(strong(), cheap(), JOB, PROFILE, "en")
    # 80*30 + 90*25 + 70*15 + 60*10 + 50*10 + 100*10 = 7800, over 100
    assert assessment.total == 78
    assert dict(assessment.components.values) == RATINGS


def test_justification_and_summary_come_back() -> None:
    assessment = score_application(strong(), cheap(), JOB, PROFILE, "en")
    assert assessment.justification == JUSTIFICATION
    assert assessment.summary == "\n".join(SUMMARY_LINES)


def test_scoring_uses_the_strong_tier_and_the_summary_the_cheap_one() -> None:
    scorer, summariser = strong(), cheap()
    score_application(scorer, summariser, JOB, PROFILE, "en")
    assert [request.prompt_version for request in scorer.requests] == [SCORE_PROMPT_VERSION]
    assert [request.prompt_version for request in summariser.requests] == [SUMMARY_PROMPT_VERSION]


@pytest.mark.parametrize("which", ["score", "summary"])
def test_no_model_sees_the_candidates_identity(which: str) -> None:
    """FR-017: what each model receives, instructions included, carries no name or contact."""
    scorer, summariser = strong(), cheap()
    score_application(scorer, summariser, JOB, PROFILE, "en")
    [request] = (scorer if which == "score" else summariser).requests
    sent = request.instructions + request.content
    for identifying in (NAME, "Zeinab", EMAIL, "+201001234567", "2010", "2014"):
        assert identifying not in sent


def test_the_scoring_request_carries_the_job_and_the_redacted_profile() -> None:
    scorer = strong()
    score_application(scorer, cheap(), JOB, PROFILE, "en")
    [request] = scorer.requests
    for expected in ("Senior Accountant", "IFRS", "Nile Pharma", "SAP", "Cairo"):
        assert expected in request.content


def test_the_instructions_set_aside_grammatical_gender() -> None:
    scorer = strong()
    score_application(scorer, cheap(), JOB, PROFILE, "en")
    assert "gender" in scorer.requests[0].instructions.casefold()


@pytest.mark.parametrize(("locale", "language"), [("ar", "Arabic"), ("en", "English")])
def test_the_texts_are_written_in_the_readers_language(locale: str, language: str) -> None:
    """FR-015: the justification and summary follow the interface language, not the CV's."""
    scorer, summariser = strong(), cheap()
    score_application(scorer, summariser, JOB, PROFILE, locale)  # type: ignore[arg-type]
    assert f"in {language}" in scorer.requests[0].instructions
    assert f"in {language}" in summariser.requests[0].instructions


def test_the_input_hash_fingerprints_what_the_scoring_model_was_sent() -> None:
    """AI-02: the hash is over the request as sent, which is the redacted one."""
    scorer = strong()
    assessment = score_application(scorer, cheap(), JOB, PROFILE, "en")
    sent = f"payload:{scorer.requests[0].content}".encode()
    assert assessment.input_hash == hashlib.sha256(sent).hexdigest()
    assert assessment.weights_hash == weights_hash(DEFAULT_WEIGHTS)


def test_the_cost_is_both_calls_together() -> None:
    assessment = score_application(strong(), cheap(), JOB, PROFILE, "en")
    assert assessment.cost_egp == Decimal("1.6")
    assert assessment.scoring.identity.prompt_version == SCORE_PROMPT_VERSION


@pytest.mark.parametrize(
    "ratings",
    [
        RATINGS | {"education": 101},
        RATINGS | {"education": -1},
        RATINGS | {"education": 7.5},
        {name: rating for name, rating in RATINGS.items() if name != "location"},
    ],
    ids=["above-100", "negative", "fractional", "missing-component"],
)
def test_ratings_outside_the_scale_are_malformed_and_still_cost(ratings: dict[str, Any]) -> None:
    with pytest.raises(MalformedOutputError) as raised:
        score_application(strong(ratings), cheap(), JOB, PROFILE, "en")
    assert raised.value.cost_egp == Decimal("1.5")


@pytest.mark.parametrize(
    "lines", [["One line."], ["a", "b"], ["a", "b", "c", "d", "e", "f"], ["a", "", "c"]]
)
def test_a_summary_must_be_three_to_five_lines(lines: list[str]) -> None:
    """FR-016."""
    with pytest.raises(MalformedOutputError):
        score_application(strong(), cheap(lines), JOB, PROFILE, "en")


def test_an_empty_justification_is_malformed() -> None:
    scorer = strong()
    scorer.output["justification"] = "  "
    with pytest.raises(MalformedOutputError):
        score_application(scorer, cheap(), JOB, PROFILE, "en")
