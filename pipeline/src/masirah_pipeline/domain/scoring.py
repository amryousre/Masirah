"""Score composition and component weighting (T047, FR-013, FR-014).

A score has six components, each rated 0 to 100. The job's weights say how much each counts,
as whole-number percentages totalling 100, which is the rule the job table enforces too (T013):
every score is then on the same scale and comparable with every other. The total is the weighted
mean of the components, rounded half up. The model rates the components; this module, not the
model, does the arithmetic, so it is exact and the same whichever provider rated them.

weights_hash fingerprints the weights a score used (AI-02), so the score can be reproduced, and so
a change of weights can be told from a score that is merely stale (AI-04).
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from types import MappingProxyType

COMPONENTS = (
    "skills_match",
    "experience_relevance",
    "education",
    "tenure_stability",
    "language",
    "location",
)
WEIGHT_TOTAL = 100
TOP_MARK = 100


class InvalidWeightsError(ValueError):
    """Weights a job could not hold."""


class InvalidComponentsError(ValueError):
    """Component ratings that are not six whole numbers from 0 to 100."""


@dataclass(frozen=True)
class Weights:
    values: Mapping[str, int]


@dataclass(frozen=True)
class Components:
    values: Mapping[str, int]


def weights_from(raw: object) -> Weights:
    values = _whole_numbers(raw, "weights", InvalidWeightsError)
    if any(value < 0 for value in values.values()):
        raise InvalidWeightsError("a weight is negative")
    if sum(values.values()) != WEIGHT_TOTAL:
        raise InvalidWeightsError(f"the weights total {sum(values.values())}, not {WEIGHT_TOTAL}")
    return Weights(MappingProxyType(values))


def components_from(raw: object) -> Components:
    values = _whole_numbers(raw, "the components", InvalidComponentsError)
    if out := [name for name, value in values.items() if not 0 <= value <= TOP_MARK]:
        raise InvalidComponentsError(f"{out} are not from 0 to {TOP_MARK}")
    return Components(MappingProxyType(values))


def total_score(components: Components, weights: Weights) -> int:
    weighted = sum(
        (Decimal(components.values[name]) * weights.values[name] for name in COMPONENTS),
        Decimal(0),
    )
    return int((weighted / WEIGHT_TOTAL).to_integral_value(rounding=ROUND_HALF_UP))


def weights_hash(weights: Weights) -> str:
    """The SHA-256 of the weights written as sorted JSON, the same whatever their order."""
    canonical = json.dumps(dict(weights.values), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _whole_numbers(raw: object, what: str, error: type[ValueError]) -> dict[str, int]:
    """One whole number per component, and nothing else. Whole floats such as 30.0 count, as
    they do in the job table; booleans, which Python counts as numbers, do not."""
    if not isinstance(raw, Mapping):
        raise error(f"{what} are not an object")
    if missing := [name for name in COMPONENTS if name not in raw]:
        raise error(f"{what} are missing {missing}")
    if extra := sorted(set(raw) - set(COMPONENTS)):
        raise error(f"{what} have unexpected {extra}")
    values: dict[str, int] = {}
    for name in COMPONENTS:
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise error(f"{name} is not a number")
        if value != int(value):
            raise error(f"{name} is not a whole number")
        values[name] = int(value)
    return values


DEFAULT_WEIGHTS = weights_from(
    {
        "skills_match": 30,
        "experience_relevance": 25,
        "education": 15,
        "tenure_stability": 10,
        "language": 10,
        "location": 10,
    }
)
