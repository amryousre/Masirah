"""The OpenAI adapter for the model provider port (T050).

Structured output through the Responses API's text.format with a strict JSON schema. store is
off, so responses are not kept on OpenAI's side. OpenAI does not train on API data by default
(AI-09); that position is confirmed before the provider is enabled, not at runtime.
"""

from decimal import Decimal
from typing import Any

import openai

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


class OpenAIModel:
    def __init__(
        self, client: openai.OpenAI, model: str, price: Price, egp_per_usd: Decimal
    ) -> None:
        self._client = client
        self._model = model
        self._price = price
        self._egp_per_usd = egp_per_usd

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        body: dict[str, Any] = {
            "model": self._model,
            "instructions": request.instructions,
            "input": request.content,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "schema": dict(request.schema),
                    "strict": True,
                }
            },
        }
        try:
            response = self._client.responses.create(**body)
        except openai.RateLimitError as error:
            # An empty credit balance also answers 429, but waiting will not refill it.
            if error.code == "insufficient_quota":
                raise ProviderUnavailableError(f"the account has no credit: {error}") from error
            raise RateLimitedError(str(error)) from error
        except openai.APITimeoutError as error:
            raise TimedOutError(str(error)) from error
        except openai.APIError as error:
            raise ProviderUnavailableError(str(error)) from error
        tokens = response.usage
        usage = Usage(tokens.input_tokens, tokens.output_tokens) if tokens else Usage(0, 0)
        cost = self._price.cost_egp(usage, self._egp_per_usd)
        contents = [c for item in response.output if item.type == "message" for c in item.content]
        if any(content.type == "refusal" for content in contents):
            raise RefusedError("the model declined the request", cost_egp=cost)
        if response.status != "completed":
            raise MalformedOutputError(f"the response is {response.status}", cost_egp=cost)
        try:
            output = json_object(response.output_text)
        except MalformedOutputError as error:
            raise MalformedOutputError(str(error), cost_egp=cost) from error
        return StructuredResponse(
            output=output,
            identity=ModelIdentity("openai", response.model, request.prompt_version),
            usage=usage,
            cost_egp=cost,
            payload=payload(body),
        )
