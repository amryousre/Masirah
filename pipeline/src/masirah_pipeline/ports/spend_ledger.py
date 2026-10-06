"""What every model call cost, and each organisation's limits (T093, AI-02, AI-06, migration 0025).

Each call is recorded as it is made, whether its output was usable or not, so an organisation's
spend this month is the sum of what it really cost and can halt its processing at the ceiling.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

from masirah_pipeline.domain.budget import Limits, Usage

SpendKind = Literal["extraction", "scoring", "summary"]


@dataclass(frozen=True)
class Spend:
    organisation_id: UUID
    cv_file_id: UUID
    kind: SpendKind
    # Who answered, when the call returned at all; a failed call is still paid for.
    provider: str | None
    model: str | None
    cost_egp: Decimal


class SpendLedger(Protocol):
    def record(self, spend: Spend) -> None:
        """Keep one call's cost, committed at once so a later failure cannot lose it."""
        ...

    def usage(self, organisation_id: UUID, since: datetime) -> Usage:
        """CVs read by a model, and the cost of every call, since the given time."""
        ...

    def limits(self, organisation_id: UUID) -> Limits:
        """The organisation's monthly CV limit and spend ceiling."""
        ...
