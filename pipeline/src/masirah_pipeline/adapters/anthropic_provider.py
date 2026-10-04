"""The Anthropic adapter for the model provider port (T049).

Structured output through the Messages API's output_config.format, which constrains the answer to
the declared JSON schema. Anthropic does not train on API inputs or outputs under its commercial
terms (AI-09); that position is confirmed before the provider is enabled, not at runtime.
"""

from decimal import Decimal
from typing import Any

import anthropic

from masirah_pipeline.adapters.structured_output import json_object, payload
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    ModelIdentity,
    Price,
    ProviderUnavailableError,
    RateLimitedError,
    RefusedError,
    StructuredRequest,
    StructuredResponse,
    TimedOutError,
    Usage,
)


class AnthropicModel:
    def __init__(
        self, client: anthropic.Anthropic, model: str, price: Price, egp_per_usd: Decimal
    ) -> None:
        self._client = client
        self._model = model
        self._price = price
        self._egp_per_usd = egp_per_usd

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": request.max_output_tokens,
            "system": request.instructions,
            "messages": [{"role": "user", "content": request.content}],
            "output_config": {"format": {"type": "json_schema", "schema": dict(request.schema)}},
        }
        try:
            message = self._client.messages.create(**body)
        except anthropic.RateLimitError as error:
            raise RateLimitedError(str(error)) from error
        except anthropic.APITimeoutError as error:
            raise TimedOutError(str(error)) from error
        except anthropic.APIError as error:
            raise ProviderUnavailableError(str(error)) from error
        # Anthropic counts input read from or written to its prompt cache apart from input_tokens.
        cached = message.usage.cache_read_input_tokens or 0
        written = message.usage.cache_creation_input_tokens or 0
        usage = Usage(
            message.usage.input_tokens + cached + written,
            message.usage.output_tokens,
            cached,
            written,
        )
        cost = self._price.cost_egp(usage, self._egp_per_usd)
        if message.stop_reason == "refusal":
            raise RefusedError("the model declined the request", cost_egp=cost)
        if message.stop_reason == "max_tokens":
            raise MalformedOutputError("the output was cut short", cost_egp=cost)
        text = "".join(block.text for block in message.content if block.type == "text")
        try:
            output = json_object(text)
        except MalformedOutputError as error:
            raise MalformedOutputError(str(error), cost_egp=cost) from error
        return StructuredResponse(
            output=output,
            identity=ModelIdentity("anthropic", message.model, request.prompt_version),
            usage=usage,
            cost_egp=cost,
            payload=payload(body),
        )
