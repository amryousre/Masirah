"""Score composition and component weighting (T047, FR-013, FR-014).

The model rates a candidate 0 to 100 on each of the six components; the domain, not the model,
weighs them into the total, so the arithmetic is exact, testable and the same for every provider.
Weights are whole-number percentages totalling 100, the rule the job table enforces (T013), so
every score stays comparable with every other.
"""

from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from masirah_pipeline.domain.scoring import (
    COMPONENTS,
    DEFAULT_WEIGHTS,
    InvalidComponentsError,
    InvalidWeightsError,
    components_from,
    total_score,
    weights_from,
    weights_hash,
)
from tests.database import WEIGHTS, Cursor, seed_tenant

EVEN = dict.fromkeys(COMPONENTS, 50)

# Weights as a job could hold them, and whether the job table accepts them.
WEIGHT_CASES: list[tuple[str, Any, bool]] = [
    ("valid", WEIGHTS, True),
    ("whole-floats", WEIGHTS | {"skills_match": 30.0}, True),
    ("all-on-one", dict.fromkeys(COMPONENTS, 0) | {"skills_match": 100}, True),
    ("wrong-total", WEIGHTS | {"location": 11}, False),
    (
        "missing-key",
        {k: v for k, v in WEIGHTS.items() if k != "location"} | {"skills_match": 40},
        False,
    ),
    ("extra-key", WEIGHTS | {"salary": 0}, False),
    ("fractional", WEIGHTS | {"skills_match": 29.5, "location": 10.5}, False),
    ("negative", WEIGHTS | {"skills_match": 50, "location": -10}, False),
    ("string", WEIGHTS | {"location": "10"}, False),
    ("boolean", WEIGHTS | {"location": True, "skills_match": 39}, False),
    ("array", [30, 25, 15, 10, 10, 10], False),
]


class TestWeights:
    @pytest.mark.parametrize(
        ("weights", "valid"),
        [(weights, valid) for _, weights, valid in WEIGHT_CASES],
        ids=[name for name, _, _ in WEIGHT_CASES],
    )
    def test_weights_are_accepted_exactly_when_a_job_could_hold_them(
        self, weights: Any, valid: bool
    ) -> None:
        if valid:
            assert weights_from(weights).values["skills_match"] == weights["skills_match"]
        else:
            with pytest.raises(InvalidWeightsError):
                weights_from(weights)

    def test_the_default_weights_are_valid(self) -> None:
        assert weights_from(dict(DEFAULT_WEIGHTS.values)) == DEFAULT_WEIGHTS

    def test_the_hash_names_the_weights_not_their_order(self) -> None:
        reordered = dict(reversed(list(WEIGHTS.items())))
        assert weights_hash(weights_from(WEIGHTS)) == weights_hash(weights_from(reordered))
        changed = WEIGHTS | {"skills_match": 25, "location": 15}
        assert weights_hash(weights_from(WEIGHTS)) != weights_hash(weights_from(changed))

    def test_the_hash_is_a_sha256_hex_digest(self) -> None:
        """The form the cv_rescoring message's weights_hash takes (contracts/queue-message.md)."""
        digest = weights_hash(DEFAULT_WEIGHTS)
        assert len(digest) == 64
        assert digest == digest.lower()
        int(digest, 16)


class TestComponents:
    def test_each_component_is_a_whole_number_from_0_to_100(self) -> None:
        assert components_from(EVEN).values == EVEN

    @pytest.mark.parametrize(
        "change",
        [
            {"skills_match": 101},
            {"skills_match": -1},
            {"skills_match": 50.5},
            {"skills_match": "50"},
            {"skills_match": None},
            {"salary": 50},
        ],
        ids=["above", "below", "fractional", "string", "null", "extra"],
    )
    def test_a_component_out_of_range_or_unknown_is_refused(self, change: dict[str, Any]) -> None:
        with pytest.raises(InvalidComponentsError):
            components_from(EVEN | change)

    def test_a_missing_component_is_refused(self) -> None:
        with pytest.raises(InvalidComponentsError, match="location"):
            components_from({k: v for k, v in EVEN.items() if k != "location"})


class TestTotal:
    def test_full_marks_and_none(self) -> None:
        weights = weights_from(WEIGHTS)
        assert total_score(components_from(dict.fromkeys(COMPONENTS, 100)), weights) == 100
        assert total_score(components_from(dict.fromkeys(COMPONENTS, 0)), weights) == 0

    def test_the_total_is_the_weighted_mean(self) -> None:
        # 90x30 + 80x25 + 70x15 + 60x10 + 50x10 + 40x10 = 7250, so 72.5, rounded half up: 73.
        components = components_from(
            {
                "skills_match": 90,
                "experience_relevance": 80,
                "education": 70,
                "tenure_stability": 60,
                "language": 50,
                "location": 40,
            }
        )
        assert total_score(components, weights_from(WEIGHTS)) == 73

    def test_a_component_weighted_zero_does_not_count(self) -> None:
        weights = weights_from(dict.fromkeys(COMPONENTS, 0) | {"skills_match": 100})
        components = components_from(dict.fromkeys(COMPONENTS, 0) | {"skills_match": 64})
        assert total_score(components, weights) == 64

    def test_the_weights_change_the_order_of_two_candidates(self) -> None:
        """What a recruiter weighs decides who ranks first, which is the point of weights."""
        skilled = components_from(EVEN | {"skills_match": 90, "experience_relevance": 40})
        seasoned = components_from(EVEN | {"skills_match": 40, "experience_relevance": 90})
        by_skills = weights_from(WEIGHTS | {"skills_match": 50, "experience_relevance": 5})
        by_experience = weights_from(WEIGHTS | {"skills_match": 5, "experience_relevance": 50})
        assert total_score(skilled, by_skills) > total_score(seasoned, by_skills)
        assert total_score(seasoned, by_experience) > total_score(skilled, by_experience)


@pytest.mark.database
@pytest.mark.parametrize(
    ("weights", "valid"),
    [(weights, valid) for _, weights, valid in WEIGHT_CASES],
    ids=[name for name, _, _ in WEIGHT_CASES],
)
def test_the_job_table_agrees(cur: Cursor, weights: Any, valid: bool) -> None:
    """The domain and the job table's check accept exactly the same weights."""
    tenant = seed_tenant(cur, "scoring")
    cur.execute("savepoint attempt")
    try:
        cur.execute(
            "insert into public.job (organisation_id, title, weights) values (%s, %s, %s)",
            (tenant.organisation_id, "Engineer", Jsonb(weights)),
        )
        accepted = True
    except psycopg.errors.CheckViolation:
        cur.execute("rollback to savepoint attempt")
        accepted = False
    assert accepted is valid


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf")], ids=["nan", "inf", "-inf"]
)
def test_a_value_that_is_not_finite_is_refused_as_invalid(value: float) -> None:
    """JSON from outside can carry them; they must fail as invalid input, not as a crash."""
    with pytest.raises(InvalidWeightsError):
        weights_from(WEIGHTS | {"location": value})
    with pytest.raises(InvalidComponentsError):
        components_from(EVEN | {"location": value})
