"""Per-organisation processing limits and a hard monthly spend ceiling (T093, AI-06, FR-026).

Each organisation may have so many CVs read and spend so much on models in a calendar month,
counted in Cairo time. Once either is reached, its processing halts until the next month starts,
rather than continuing to accrue cost.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from masirah_pipeline.domain.budget import Limits, Usage, halt_reason, month_start, next_month_start

LIMITS = Limits(cvs_per_month=300, spend_ceiling_egp=Decimal("750"))


def test_an_organisation_under_both_limits_goes_on() -> None:
    assert halt_reason(Usage(cvs=299, spend_egp=Decimal("749.99")), LIMITS) is None


def test_the_spend_ceiling_halts_processing() -> None:
    assert halt_reason(Usage(cvs=10, spend_egp=Decimal("750")), LIMITS) == "spend_ceiling"


def test_the_monthly_cv_limit_halts_processing() -> None:
    assert halt_reason(Usage(cvs=300, spend_egp=Decimal("1")), LIMITS) == "cv_limit"


def test_the_ceiling_is_named_first_when_both_are_reached() -> None:
    assert halt_reason(Usage(cvs=300, spend_egp=Decimal("800")), LIMITS) == "spend_ceiling"


def test_a_limit_of_nothing_halts_everything() -> None:
    assert halt_reason(Usage(cvs=0, spend_egp=Decimal(0)), Limits(0, Decimal("750"))) == "cv_limit"


@pytest.mark.parametrize(
    ("now", "start"),
    [
        # 23:30 on 30 September in UTC is already 1 October in Cairo (UTC+3 in summer time).
        (datetime(2026, 9, 30, 21, 30, tzinfo=UTC), datetime(2026, 9, 30, 21, 0, tzinfo=UTC)),
        (datetime(2026, 10, 15, 9, 0, tzinfo=UTC), datetime(2026, 9, 30, 21, 0, tzinfo=UTC)),
        # In winter Cairo is UTC+2.
        (datetime(2026, 12, 31, 23, 0, tzinfo=UTC), datetime(2026, 12, 31, 22, 0, tzinfo=UTC)),
    ],
    ids=["after-midnight-in-cairo", "mid-month", "new-year-in-cairo"],
)
def test_a_month_starts_at_midnight_in_cairo(now: datetime, start: datetime) -> None:
    assert month_start(now) == start


def test_the_next_month_starts_at_midnight_in_cairo() -> None:
    assert next_month_start(datetime(2026, 10, 6, 12, 0, tzinfo=UTC)) == datetime(
        2026, 10, 31, 22, 0, tzinfo=UTC
    )
    assert next_month_start(datetime(2026, 12, 15, 12, 0, tzinfo=UTC)) == datetime(
        2026, 12, 31, 22, 0, tzinfo=UTC
    )


def test_a_time_without_a_zone_is_refused() -> None:
    with pytest.raises(ValueError, match="zone"):
        month_start(datetime(2026, 10, 6, 12, 0))
