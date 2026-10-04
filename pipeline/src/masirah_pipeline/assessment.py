"""Scoring an application and summarising the candidate, through the provider port (T056).

score_application is the contract's operation of that name with summarise_candidate folded in:
the strong tier rates and justifies, the cheap tier summarises (AI-05), and both receive only the
redacted profile (FR-017, worker obligation 6). input_hash fingerprints the scoring request as
it was sent, so the audit trail shows exactly what the model saw (AI-02).
"""

import hashlib
from dataclasses import dataclass
from decimal import Decimal

from masirah_pipeline.domain.justification import (
    SCORE_SCHEMA,
    SUMMARY_SCHEMA,
    JobSpec,
    Locale,
    MalformedAssessmentError,
    rating_from_output,
    score_content,
    score_instructions,
    summary_content,
    summary_from_output,
    summary_instructions,
)
from masirah_pipeline.domain.profile import Profile
from masirah_pipeline.domain.redaction import scoring_input
from masirah_pipeline.domain.scoring import Components, total_score, weights_hash
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    StructuredModel,
    StructuredRequest,
    StructuredResponse,
)

SCORE_PROMPT_VERSION = "score-application/1"
SUMMARY_PROMPT_VERSION = "summarise-candidate/1"
SCORE_MAX_OUTPUT_TOKENS = 8_000
SUMMARY_MAX_OUTPUT_TOKENS = 2_000


@dataclass(frozen=True)
class Assessment:
    total: int
    components: Components
    evidence: dict[str, str]
    justification: str
    summary: str
    input_hash: str
    weights_hash: str
    scoring: StructuredResponse
    summarising: StructuredResponse

    @property
    def cost_egp(self) -> Decimal:
        return self.scoring.cost_egp + self.summarising.cost_egp


def score_application(
    strong: StructuredModel, cheap: StructuredModel, job: JobSpec, profile: Profile, locale: Locale
) -> Assessment:
    redacted = scoring_input(profile)
    scoring = strong.complete(
        StructuredRequest(
            instructions=score_instructions(locale),
            content=score_content(job, redacted),
            schema_name="application_score",
            schema=SCORE_SCHEMA,
            prompt_version=SCORE_PROMPT_VERSION,
            max_output_tokens=SCORE_MAX_OUTPUT_TOKENS,
        )
    )
    try:
        rating = rating_from_output(scoring.output)
    except MalformedAssessmentError as error:
        raise MalformedOutputError(str(error), cost_egp=scoring.cost_egp) from error
    summarising = cheap.complete(
        StructuredRequest(
            instructions=summary_instructions(locale),
            content=summary_content(redacted),
            schema_name="candidate_summary",
            schema=SUMMARY_SCHEMA,
            prompt_version=SUMMARY_PROMPT_VERSION,
            max_output_tokens=SUMMARY_MAX_OUTPUT_TOKENS,
        )
    )
    try:
        summary = summary_from_output(summarising.output)
    except MalformedAssessmentError as error:
        spent = scoring.cost_egp + summarising.cost_egp
        raise MalformedOutputError(str(error), cost_egp=spent) from error
    return Assessment(
        total=total_score(rating.components, job.weights),
        components=rating.components,
        evidence=rating.evidence,
        justification=rating.justification,
        summary=summary,
        input_hash=hashlib.sha256(scoring.payload).hexdigest(),
        weights_hash=weights_hash(job.weights),
        scoring=scoring,
        summarising=summarising,
    )
