"""The model provider port's contract (T034), run against both adapters.

contracts/model-provider-port.md sets five terms every implementation must meet: structured output
only, identity returned rather than assumed, cost returned, the payload sent available for
fingerprinting, and failures typed so the caller can tell a rate limit from a timeout, a refusal
or malformed output. Each adapter talks to a fake transport here, so no request leaves the machine.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import anthropic
import httpx2
import openai
import pytest

from masirah_pipeline.adapters.anthropic_provider import AnthropicModel
from masirah_pipeline.adapters.openai_provider import OpenAIModel
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    Price,
    ProviderUnavailableError,
    RateLimitedError,
    RefusedError,
    StructuredModel,
    StructuredRequest,
    TimedOutError,
)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}
REQUEST = StructuredRequest(
    instructions="Extract the candidate's name.",
    content="Mona Khaled, front-end developer",
    schema_name="candidate",
    schema=SCHEMA,
    prompt_version="test/1",
    max_output_tokens=512,
)
# 1,000 tokens in and 200 out at $2 and $10 a million is $0.004, which is 0.2 EGP at 50 EGP/USD.
PRICE = Price(
    input_usd_per_million=Decimal(2),
    output_usd_per_million=Decimal(10),
    cached_input_usd_per_million=Decimal("0.2"),
    cache_write_usd_per_million=Decimal("2.5"),
)
EGP_PER_USD = Decimal(50)
COST = Decimal("0.2")
# With 600 of the 1,000 input tokens read from the provider's cache at $0.20 a million:
# 400 x $2 + 600 x $0.20 + 200 x $10 = $0.00292, which is 0.146 EGP.
CACHED_COST = Decimal("0.146")
# With 600 of them written to the cache instead, at $2.50 a million:
# 400 x $2 + 600 x $2.50 + 200 x $10 = $0.0043, which is 0.215 EGP.
WRITTEN_COST = Decimal("0.215")


@dataclass
class Fake:
    """A provider's API as seen through a transport: it records requests and gives one answer."""

    answer: Callable[[httpx2.Request], httpx2.Response]
    requests: list[httpx2.Request] = field(default_factory=list)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.answer(request)

    @property
    def body(self) -> dict[str, Any]:
        sent: dict[str, Any] = json.loads(self.requests[-1].content)
        return sent


def anthropic_message(
    text: str, stop_reason: str = "end_turn", *, cached: int = 0, written: int = 0
) -> dict[str, Any]:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        # Anthropic counts tokens read from its cache apart from input_tokens.
        "usage": {
            "input_tokens": 1000 - cached - written,
            "cache_read_input_tokens": cached,
            "cache_creation_input_tokens": written,
            "output_tokens": 200,
        },
    }


def openai_response(
    text: str,
    *,
    refusal: bool = False,
    status: str = "completed",
    cached: int = 0,
    written: int = 0,
) -> dict[str, Any]:
    content = (
        {"type": "refusal", "refusal": "I can't help with that."}
        if refusal
        else {"type": "output_text", "text": text, "annotations": []}
    )
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "status": status,
        "model": "gpt-5.6-luna-2026-07-01",
        "output": [
            {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "status": status,
                "content": [content],
            }
        ],
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 200,
            "total_tokens": 1200,
            # OpenAI counts tokens read from its cache within input_tokens.
            "input_tokens_details": {"cached_tokens": cached, "cache_write_tokens": written},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


@dataclass(frozen=True)
class Provider:
    name: str
    model_id: str
    good: Callable[[str], dict[str, Any]]
    refused: dict[str, Any]
    truncated: dict[str, Any]
    build: Callable[[Fake], StructuredModel]

    def schema_sent(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.name == "anthropic":
            output_format: dict[str, Any] = body["output_config"]["format"]
            assert output_format["type"] == "json_schema"
            schema: dict[str, Any] = output_format["schema"]
            return schema
        text_format: dict[str, Any] = body["text"]["format"]
        assert text_format["type"] == "json_schema"
        assert text_format["strict"] is True
        assert text_format["name"] == REQUEST.schema_name
        sent: dict[str, Any] = text_format["schema"]
        return sent


def build_anthropic(fake: Fake) -> StructuredModel:
    client = anthropic.Anthropic(
        api_key="test",
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(fake.handle)),
    )
    return AnthropicModel(client, "claude-haiku-4-5", PRICE, EGP_PER_USD)


def build_openai(fake: Fake) -> StructuredModel:
    client = openai.OpenAI(
        api_key="test",
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(fake.handle)),
    )
    return OpenAIModel(client, "gpt-5.6-luna", PRICE, EGP_PER_USD)


PROVIDERS = [
    Provider(
        name="anthropic",
        model_id="claude-haiku-4-5-20251001",
        good=anthropic_message,
        refused=anthropic_message("", stop_reason="refusal"),
        truncated=anthropic_message('{"name": "Mo', stop_reason="max_tokens"),
        build=build_anthropic,
    ),
    Provider(
        name="openai",
        model_id="gpt-5.6-luna-2026-07-01",
        good=openai_response,
        refused=openai_response("", refusal=True),
        truncated=openai_response('{"name": "Mo', status="incomplete"),
        build=build_openai,
    ),
]


def answering(
    body: dict[str, Any], status: int = 200
) -> Callable[[httpx2.Request], httpx2.Response]:
    return lambda request: httpx2.Response(status, json=body, request=request)


@pytest.fixture(params=PROVIDERS, ids=lambda provider: provider.name)
def provider(request: pytest.FixtureRequest) -> Provider:
    chosen: Provider = request.param
    return chosen


def complete(provider: Provider, answer: Callable[[httpx2.Request], httpx2.Response]) -> Any:
    fake = Fake(answer)
    return provider.build(fake).complete(REQUEST), fake


class TestASuccessfulCall:
    def test_output_is_the_parsed_structured_output(self, provider: Provider) -> None:
        response, _ = complete(provider, answering(provider.good('{"name": "Mona Khaled"}')))
        assert response.output == {"name": "Mona Khaled"}

    def test_the_schema_is_declared_in_the_request(self, provider: Provider) -> None:
        _, fake = complete(provider, answering(provider.good('{"name": "Mona Khaled"}')))
        assert provider.schema_sent(fake.body) == SCHEMA

    def test_identity_is_what_the_provider_reports(self, provider: Provider) -> None:
        response, _ = complete(provider, answering(provider.good('{"name": "Mona Khaled"}')))
        assert response.identity.provider == provider.name
        assert response.identity.model_id == provider.model_id
        assert response.identity.prompt_version == REQUEST.prompt_version

    def test_tokens_and_cost_are_returned(self, provider: Provider) -> None:
        response, _ = complete(provider, answering(provider.good('{"name": "Mona Khaled"}')))
        assert (response.usage.input_tokens, response.usage.output_tokens) == (1000, 200)
        assert response.cost_egp == COST

    def test_the_payload_is_what_was_sent(self, provider: Provider) -> None:
        """So input_hash fingerprints the request that was made, not the one intended."""
        response, fake = complete(provider, answering(provider.good('{"name": "Mona Khaled"}')))
        assert json.loads(response.payload) == fake.body
        assert REQUEST.content in json.dumps(fake.body, ensure_ascii=False)


class TestFailuresAreTyped:
    def test_a_rate_limit(self, provider: Provider) -> None:
        error = {"type": "error", "error": {"type": "rate_limit_error", "message": "slow down"}}
        with pytest.raises(RateLimitedError):
            complete(provider, answering(error, status=429))

    def test_an_anthropic_account_without_credit_is_unavailable(self) -> None:
        """Anthropic answers an empty balance with 400, which no retry can fix."""
        error = {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Your credit balance is too low to access the Anthropic API.",
            },
        }
        (anthropic_provider,) = [p for p in PROVIDERS if p.name == "anthropic"]
        with pytest.raises(ProviderUnavailableError, match="credit"):
            complete(anthropic_provider, answering(error, status=400))

    def test_running_out_of_credit_is_not_a_rate_limit(self) -> None:
        """OpenAI answers an empty balance with 429 too, but waiting will not refill it."""
        quota = {
            "error": {
                "message": "You have no credits remaining.",
                "type": "insufficient_quota",
                "code": "insufficient_quota",
            }
        }
        (openai_provider,) = [p for p in PROVIDERS if p.name == "openai"]
        with pytest.raises(ProviderUnavailableError, match="credit"):
            complete(openai_provider, answering(quota, status=429))

    def test_a_timeout(self, provider: Provider) -> None:
        def time_out(request: httpx2.Request) -> httpx2.Response:
            raise httpx2.ReadTimeout("timed out", request=request)

        with pytest.raises(TimedOutError):
            complete(provider, time_out)

    def test_a_refusal(self, provider: Provider) -> None:
        with pytest.raises(RefusedError):
            complete(provider, answering(provider.refused))

    def test_output_cut_short(self, provider: Provider) -> None:
        with pytest.raises(MalformedOutputError):
            complete(provider, answering(provider.truncated))

    def test_output_that_is_not_json(self, provider: Provider) -> None:
        with pytest.raises(MalformedOutputError):
            complete(provider, answering(provider.good("Mona Khaled")))

    def test_output_that_is_not_an_object(self, provider: Provider) -> None:
        with pytest.raises(MalformedOutputError):
            complete(provider, answering(provider.good('["Mona Khaled"]')))

    def test_a_provider_outage(self, provider: Provider) -> None:
        error = {"type": "error", "error": {"type": "api_error", "message": "down"}}
        with pytest.raises(ProviderUnavailableError):
            complete(provider, answering(error, status=500))

    def test_every_failure_is_one_family(self) -> None:
        """A caller that wants every model failure catches one type, never a provider's own."""
        from masirah_pipeline.ports.model_provider import ModelProviderError

        for error in (RateLimitedError, TimedOutError, RefusedError, MalformedOutputError):
            assert issubclass(error, ModelProviderError)
        assert issubclass(ProviderUnavailableError, ModelProviderError)


class TestCachedInput:
    """Input read from a provider's prompt cache is billed at a fraction of the input rate."""

    def test_cached_input_costs_the_cached_rate(self, provider: Provider) -> None:
        good = (
            anthropic_message('{"name": "Mona"}', cached=600)
            if provider.name == "anthropic"
            else openai_response('{"name": "Mona"}', cached=600)
        )
        response, _ = complete(provider, answering(good))
        assert response.usage.input_tokens == 1000
        assert response.usage.cached_input_tokens == 600
        assert response.cost_egp == CACHED_COST

    def test_a_price_without_a_cached_rate_charges_the_input_rate(self) -> None:
        from masirah_pipeline.ports.model_provider import Usage

        plain = Price(input_usd_per_million=Decimal(2), output_usd_per_million=Decimal(10))
        assert plain.cost_egp(Usage(1000, 200, cached_input_tokens=600), EGP_PER_USD) == COST

    def test_input_written_to_the_cache_costs_the_write_rate(self, provider: Provider) -> None:
        good = (
            anthropic_message('{"name": "Mona"}', written=600)
            if provider.name == "anthropic"
            else openai_response('{"name": "Mona"}', written=600)
        )
        response, _ = complete(provider, answering(good))
        assert response.usage.input_tokens == 1000
        assert response.usage.cache_write_tokens == 600
        assert response.cost_egp == WRITTEN_COST
