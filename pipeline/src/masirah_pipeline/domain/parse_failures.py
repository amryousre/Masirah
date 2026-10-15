"""When the parse failure rate is worth an alert (NFR-14, T031).

A CV file settles when the worker is done with it: extracted, sent to the review queue or failed.
The rate is the failed share of those, and above five percent an operator is told. A file sent
for review is not a failure: reading a scan with no text, or one the model was unsure of, and
asking a person is the pipeline working as designed.

Below MINIMUM_SETTLED files a rate says nothing (one failure in three is not a trend), so a quiet
hour stays quiet.
"""

from dataclasses import dataclass
from fractions import Fraction

THRESHOLD = Fraction(5, 100)
MINIMUM_SETTLED = 10


@dataclass(frozen=True)
class ParseOutcomes:
    """The CV files that settled within a window, across every organisation."""

    settled: int
    failed: int
    # How many organisations had a failure, so a fault in one tenant's files reads differently
    # from one in the pipeline.
    organisations: int


def alert_for(outcomes: ParseOutcomes) -> str | None:
    """The alert's text when the failure rate is above the threshold, otherwise None."""
    if outcomes.settled < MINIMUM_SETTLED:
        return None
    rate = Fraction(outcomes.failed, outcomes.settled)
    if rate <= THRESHOLD:
        return None
    noun = "organisation" if outcomes.organisations == 1 else "organisations"
    return (
        f"Masirah parse failure rate is {float(rate) * 100:.1f}%, above 5%:"
        f" {outcomes.failed} of {outcomes.settled} CV files failed in the past hour"
        f" ({outcomes.organisations} {noun})."
    )
