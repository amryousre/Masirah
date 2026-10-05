"""A stored score is enough to reproduce it (T086, AI-02).

Every score keeps the model's identity, the prompt version and the fingerprint of the request as
sent. Given the same job and CV, scoring again builds the same request, so the fingerprint shows
whether a rerun saw exactly what the first run saw; and the total follows from the stored ratings
and weights alone, so it can be recomputed without asking any model. The fingerprint covers only
what was sent, which is the redacted profile: a different name gives the same fingerprint, a
different skill does not.
"""

from dataclasses import replace

from masirah_pipeline.assessment import (
    SCORE_PROMPT_VERSION,
    SUMMARY_PROMPT_VERSION,
    Assessment,
    score_application,
)
from masirah_pipeline.domain.profile import Profile
from masirah_pipeline.domain.scoring import DEFAULT_WEIGHTS, total_score, weights_hash
from tests.unit.test_assessment import JOB, PROFILE, FakeModel, cheap, strong


def assess(profile: Profile = PROFILE) -> tuple[Assessment, FakeModel]:
    scorer, summariser = strong(), cheap()
    return score_application(scorer, summariser, JOB, profile, "en"), scorer


def test_the_same_job_and_cv_build_the_same_request_and_fingerprint() -> None:
    first, first_scorer = assess()
    again, again_scorer = assess()
    assert again_scorer.requests[0].content == first_scorer.requests[0].content
    assert again_scorer.requests[0].instructions == first_scorer.requests[0].instructions
    assert again.input_hash == first.input_hash
    assert again.weights_hash == first.weights_hash == weights_hash(DEFAULT_WEIGHTS)


def test_each_call_names_the_model_and_the_prompt_version_it_ran() -> None:
    assessment, _ = assess()
    assert assessment.scoring.identity.provider == "anthropic"
    assert assessment.scoring.identity.model_id == "model-x"
    assert assessment.scoring.identity.prompt_version == SCORE_PROMPT_VERSION
    assert assessment.summarising.identity.prompt_version == SUMMARY_PROMPT_VERSION


def test_the_total_follows_from_the_stored_ratings_and_weights_alone() -> None:
    assessment, _ = assess()
    assert total_score(assessment.components, JOB.weights) == assessment.total


def test_the_fingerprint_ignores_what_was_never_sent() -> None:
    renamed = replace(PROFILE, name="Another Person", emails=("other@mail.test",))
    assert assess(renamed)[0].input_hash == assess()[0].input_hash


def test_the_fingerprint_changes_with_what_was_sent() -> None:
    reskilled = replace(PROFILE, skills=("SAP", "Excel", "IFRS"))
    assert assess(reskilled)[0].input_hash != assess()[0].input_hash
