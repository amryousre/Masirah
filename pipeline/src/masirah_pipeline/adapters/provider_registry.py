"""Which provider and model serve each tier, from environment configuration (T051, AI-05).

MASIRAH_CHEAP_MODEL serves extraction and summaries, and MASIRAH_STRONG_MODEL serves scoring and
justification, each written provider:model. Comparing providers on the same CVs is a change to
one variable (decision Q5).

Cost is in Egyptian pounds (NFR-13), from each model's list price in US dollars and the rate in
MASIRAH_EGP_PER_USD. A model without a price here cannot report its cost and is refused, so a
new model is added here, with its price, before it can be configured.
"""

import os
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

import anthropic
import openai

from masirah_pipeline.adapters.anthropic_provider import AnthropicModel
from masirah_pipeline.adapters.openai_provider import OpenAIModel
from masirah_pipeline.ports.model_provider import Price, StructuredModel, Tier

TIER_VARIABLES: dict[Tier, str] = {
    "cheap": "MASIRAH_CHEAP_MODEL",
    "strong": "MASIRAH_STRONG_MODEL",
}
RATE_VARIABLE = "MASIRAH_EGP_PER_USD"
KEY_VARIABLES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
# Seconds to wait for one answer. The SDKs retry rate limits and outages twice on their own.
TIMEOUT = 120.0


def _price(input_usd: str, output_usd: str, cached_usd: str, cache_write_usd: str) -> Price:
    return Price(
        Decimal(input_usd), Decimal(output_usd), Decimal(cached_usd), Decimal(cache_write_usd)
    )


# List prices per million tokens: input, output, input read from the provider's prompt cache, and
# input written to it. Checked against each provider's pricing pages on 4 October 2026.
PRICES: dict[str, Price] = {
    "anthropic:claude-haiku-4-5": _price("1", "5", "0.10", "1.25"),
    "anthropic:claude-sonnet-5": _price("2", "10", "0.20", "2.50"),
    "openai:gpt-5.6-luna": _price("0.20", "1.20", "0.02", "0.25"),
    "openai:gpt-5.6-sol": _price("4", "20", "0.40", "5"),
}


class ConfigurationError(ValueError):
    """The worker's model configuration cannot work. Raised at startup, before any CV."""


def model_for(tier: Tier, environment: Mapping[str, str] = os.environ) -> StructuredModel:
    variable = TIER_VARIABLES[tier]
    spec = _required(environment, variable)
    provider, _, model = spec.partition(":")
    if not model:
        raise ConfigurationError(f"{variable} must be written provider:model, not {spec!r}")
    price = PRICES.get(spec)
    if price is None:
        raise ConfigurationError(f"{spec} has no price here, so its cost could not be reported")
    rate = _rate(environment)
    key = _required(environment, KEY_VARIABLES[provider])
    if provider == "anthropic":
        return AnthropicModel(anthropic.Anthropic(api_key=key, timeout=TIMEOUT), model, price, rate)
    return OpenAIModel(openai.OpenAI(api_key=key, timeout=TIMEOUT), model, price, rate)


def _required(environment: Mapping[str, str], variable: str) -> str:
    value = environment.get(variable, "").strip()
    if not value:
        raise ConfigurationError(f"{variable} is not set")
    return value


def _rate(environment: Mapping[str, str]) -> Decimal:
    text = _required(environment, RATE_VARIABLE)
    try:
        rate = Decimal(text)
    except InvalidOperation as error:
        raise ConfigurationError(f"{RATE_VARIABLE} is not a number: {text!r}") from error
    if not rate.is_finite() or rate <= 0:
        raise ConfigurationError(f"{RATE_VARIABLE} must be a positive number: {text!r}")
    return rate
