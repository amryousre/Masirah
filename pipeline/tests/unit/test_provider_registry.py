"""Provider selection by configuration (T051, AI-05).

Which provider and model serve each tier is an environment variable, so comparing Anthropic with
OpenAI on the same CVs means changing a variable, not code (decision Q5). Configuration that
could not account for its cost is refused when the worker starts, not on the first CV.
"""

from decimal import Decimal

import pytest

from masirah_pipeline.adapters.anthropic_provider import AnthropicModel
from masirah_pipeline.adapters.openai_provider import OpenAIModel
from masirah_pipeline.adapters.provider_registry import (
    PRICES,
    ConfigurationError,
    model_for,
)

ENVIRONMENT = {
    "MASIRAH_CHEAP_MODEL": "anthropic:claude-haiku-4-5",
    "MASIRAH_STRONG_MODEL": "openai:gpt-5.6-sol",
    "MASIRAH_EGP_PER_USD": "50",
    "ANTHROPIC_API_KEY": "test-anthropic",
    "OPENAI_API_KEY": "test-openai",
}


def with_changes(**changes: str | None) -> dict[str, str]:
    environment = ENVIRONMENT | changes
    return {key: value for key, value in environment.items() if value is not None}


def test_each_tier_gets_its_configured_provider() -> None:
    assert isinstance(model_for("cheap", ENVIRONMENT), AnthropicModel)
    assert isinstance(model_for("strong", ENVIRONMENT), OpenAIModel)


def test_a_comparison_run_is_one_variable() -> None:
    environment = with_changes(MASIRAH_CHEAP_MODEL="openai:gpt-5.6-luna")
    assert isinstance(model_for("cheap", environment), OpenAIModel)


def test_every_priced_model_is_a_known_provider() -> None:
    assert {spec.partition(":")[0] for spec in PRICES} == {"anthropic", "openai"}
    assert all(price.input_usd_per_million > 0 for price in PRICES.values())


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"MASIRAH_CHEAP_MODEL": None}, "MASIRAH_CHEAP_MODEL"),
        ({"MASIRAH_CHEAP_MODEL": "claude-haiku-4-5"}, "provider:model"),
        ({"MASIRAH_CHEAP_MODEL": "gemini:flash"}, "no price"),
        ({"MASIRAH_CHEAP_MODEL": "anthropic:claude-made-up"}, "no price"),
        ({"MASIRAH_EGP_PER_USD": None}, "MASIRAH_EGP_PER_USD"),
        ({"MASIRAH_EGP_PER_USD": "fifty"}, "MASIRAH_EGP_PER_USD"),
        ({"MASIRAH_EGP_PER_USD": "0"}, "MASIRAH_EGP_PER_USD"),
        ({"ANTHROPIC_API_KEY": None}, "ANTHROPIC_API_KEY"),
    ],
    ids=[
        "no-model",
        "no-provider",
        "unknown-provider",
        "unpriced",
        "no-rate",
        "bad-rate",
        "zero-rate",
        "no-key",
    ],
)
def test_configuration_that_cannot_work_is_refused(
    changes: dict[str, str | None], message: str
) -> None:
    with pytest.raises(ConfigurationError, match=message):
        model_for("cheap", with_changes(**changes))


def test_the_rate_is_exact() -> None:
    """Money is decimal, so a rate such as 48.73 is not rounded on the way in."""
    model = model_for("cheap", with_changes(MASIRAH_EGP_PER_USD="48.73"))
    assert model._egp_per_usd == Decimal("48.73")  # type: ignore[attr-defined]
