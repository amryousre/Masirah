"""The worker's Scorer: score an application and record it (T057).

A score already recorded for the application under the job's current weights is not paid for
again (obligation 1). The score's cost is everything this CV cost in this run: extraction,
scoring and summary together (obligation 5, NFR-13).
"""

from dataclasses import dataclass
from decimal import Decimal

from masirah_pipeline.assessment import score_application
from masirah_pipeline.domain.scoring import COMPONENTS, weights_hash
from masirah_pipeline.ports.model_provider import StructuredModel
from masirah_pipeline.ports.score_repository import ScoreRecord, ScoreRepository
from masirah_pipeline.worker import ScoringRequest

# score.cost_egp is numeric(10, 4).
COST_PLACES = Decimal("0.0001")


@dataclass
class ApplicationScorer:
    scores: ScoreRepository
    strong: StructuredModel
    cheap: StructuredModel

    def __call__(self, request: ScoringRequest) -> None:
        organisation = request.organisation_id
        job = self.scores.job(organisation, request.job_id)
        if job is None:
            raise LookupError(f"job {request.job_id} is not in organisation {organisation}")
        if self.scores.has_score(organisation, request.application_id, weights_hash(job.weights)):
            return
        assessment = score_application(
            self.strong, self.cheap, job, request.profile, request.locale
        )
        cost = request.extraction_cost_egp + assessment.cost_egp
        self.scores.record_score(
            organisation,
            ScoreRecord(
                application_id=request.application_id,
                total=assessment.total,
                components={
                    name: {
                        "rating": assessment.components.values[name],
                        "evidence": assessment.evidence[name],
                    }
                    for name in COMPONENTS
                },
                justification=assessment.justification,
                summary=assessment.summary,
                scoring=assessment.scoring.identity,
                summarising=assessment.summarising.identity,
                input_hash=assessment.input_hash,
                weights_hash=assessment.weights_hash,
                cost_egp=cost.quantize(COST_PLACES),
            ),
        )
