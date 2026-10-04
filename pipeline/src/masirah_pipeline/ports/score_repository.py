"""Jobs to score against, and the scores themselves (T057, AI-02).

A score is immutable and unique for its application and weights: rescoring with the same weights
finds the score already there, so a retried message never pays for a second one (obligation 1).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from masirah_pipeline.domain.justification import JobSpec
from masirah_pipeline.ports.model_provider import ModelIdentity


@dataclass(frozen=True)
class ScoreRecord:
    application_id: UUID
    total: int
    # Each component's rating and the evidence for it, as the score breakdown shows them.
    components: dict[str, Any]
    justification: str
    summary: str
    scoring: ModelIdentity
    summarising: ModelIdentity
    input_hash: str
    weights_hash: str
    cost_egp: Decimal


class ScoreRepository(Protocol):
    def job(self, organisation_id: UUID, job_id: UUID) -> JobSpec | None: ...

    def has_score(self, organisation_id: UUID, application_id: UUID, weights_hash: str) -> bool: ...

    def record_score(self, organisation_id: UUID, score: ScoreRecord) -> None:
        """Insert the score, or do nothing when one for the same weights already exists."""
        ...
