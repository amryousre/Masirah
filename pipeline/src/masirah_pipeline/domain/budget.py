"""Per-organisation processing limits and a hard monthly spend ceiling (T093, AI-06, FR-026).

An organisation may have so many CVs read and spend so much on model calls in a calendar month,
counted in Cairo time, where the organisations are. Once either is reached its processing halts
until the next month starts, rather than continuing to accrue cost. These are cost controls, not
billing (spec: billing and quotas are Phase 3).

The ceiling is checked before a CV's work starts, so it can be passed by at most the cost of the
CVs already in progress when it is reached: a few pounds, never an open-ended run.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

CAIRO = ZoneInfo("Africa/Cairo")

HaltReason = Literal["spend_ceiling", "cv_limit"]


@dataclass(frozen=True)
class Limits:
    cvs_per_month: int
    spend_ceiling_egp: Decimal


@dataclass(frozen=True)
class Usage:
    """This month's work for one organisation: CVs read by a model, and what all calls cost."""

    cvs: int
    spend_egp: Decimal


def halt_reason(usage: Usage, limits: Limits) -> HaltReason | None:
    """Why the organisation's processing halts, or None while it is under both limits. The
    ceiling is named first: it is the limit that protects against cost."""
    if usage.spend_egp >= limits.spend_ceiling_egp:
        return "spend_ceiling"
    if usage.cvs >= limits.cvs_per_month:
        return "cv_limit"
    return None


def _cairo(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("a time without a zone cannot be placed in a month")
    return now.astimezone(CAIRO)


def month_start(now: datetime) -> datetime:
    """Midnight in Cairo on the first of the month `now` falls in, in UTC."""
    local = _cairo(now)
    return datetime(local.year, local.month, 1, tzinfo=CAIRO).astimezone(UTC)


def next_month_start(now: datetime) -> datetime:
    """Midnight in Cairo on the first of the following month, in UTC: when a halt lifts."""
    local = _cairo(now)
    year, month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
    return datetime(year, month, 1, tzinfo=CAIRO).astimezone(UTC)
