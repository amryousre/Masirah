"""The model provider port (T048, contracts/model-provider-port.md).

A provider adapter does one thing: send a structured request and return the parsed output with
the identity, usage and cost of the call. What to ask for, the instructions and the output schema,
belongs to the operations built on this port (extract_profile, and later summarise_candidate and
score_application), so both providers answer exactly the same request and a schema only one of
them could satisfy is caught in one place (decision Q5).

Every failure is one of the typed errors below, because each warrants a different retry: wait
out a rate limit, retry a timeout, never retry a refusal, and record malformed output.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Protocol

ProviderName = Literal["anthropic", "openai"]
Tier = Literal["cheap", "strong"]

ONE_MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class StructuredRequest:
    instructions: str
    content: str
    schema_name: str
    schema: Mapping[str, Any]
    prompt_version: str
    max_output_tokens: int


@dataclass(frozen=True)
class ModelIdentity:
    """Who answered: the provider, the concrete model it reports, and the prompt version (AI-02)."""

    provider: ProviderName
    model_id: str
    prompt_version: str


@dataclass(frozen=True)
class Usage:
    """Tokens in and out. input_tokens counts every input token, cached_input_tokens those of
    them the provider read from its prompt cache."""

    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


@dataclass(frozen=True)
class Price:
    """A model's list price in US dollars per million tokens.

    Input read from the provider's prompt cache is billed at its own, lower rate. A price with no
    cached rate charges cached input at the full input rate, which overstates rather than hides
    cost.
    """

    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cached_input_usd_per_million: Decimal | None = None

    def cost_egp(self, usage: Usage, egp_per_usd: Decimal) -> Decimal:
        cached_rate = self.cached_input_usd_per_million
        if cached_rate is None:
            cached_rate = self.input_usd_per_million
        uncached = usage.input_tokens - usage.cached_input_tokens
        usd = (
            uncached * self.input_usd_per_million
            + usage.cached_input_tokens * cached_rate
            + usage.output_tokens * self.output_usd_per_million
        ) / ONE_MILLION
        return usd * egp_per_usd


@dataclass(frozen=True)
class StructuredResponse:
    output: dict[str, Any]
    identity: ModelIdentity
    usage: Usage
    cost_egp: Decimal
    # The request body as sent, serialised, so input_hash fingerprints what was really asked.
    payload: bytes


class StructuredModel(Protocol):
    def complete(self, request: StructuredRequest) -> StructuredResponse: ...


class ModelProviderError(Exception):
    """A model call that did not produce usable output.

    A call that fails after the model answered, refused or cut short, has still been paid for,
    and cost_egp says how much, so spend is counted whether or not the output was usable.
    """

    def __init__(self, message: str, *, cost_egp: Decimal = Decimal(0)) -> None:
        super().__init__(message)
        self.cost_egp = cost_egp


class RateLimitedError(ModelProviderError):
    """The provider is limiting requests. Wait, then retry."""


class TimedOutError(ModelProviderError):
    """No answer in time. Retry."""


class RefusedError(ModelProviderError):
    """The model declined the request. Retrying the same request will not help."""


class MalformedOutputError(ModelProviderError):
    """The output is cut short or does not fit the declared schema."""


class ProviderUnavailableError(ModelProviderError):
    """Any other failure: an outage, a network error, or a rejected request or key."""
