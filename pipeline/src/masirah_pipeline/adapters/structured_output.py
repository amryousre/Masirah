"""What both provider adapters do the same way with a structured call."""

import json
from collections.abc import Mapping
from typing import Any

from masirah_pipeline.ports.model_provider import MalformedOutputError


def json_object(text: str) -> dict[str, Any]:
    """The model's output read as the JSON object the schema declares (AI-01).

    Structured output should guarantee it; anything else is refused here, never repaired.
    """
    try:
        output = json.loads(text)
    except json.JSONDecodeError as error:
        raise MalformedOutputError(f"the output is not JSON: {error}") from error
    if not isinstance(output, dict):
        raise MalformedOutputError("the output is not a JSON object")
    return output


def payload(body: Mapping[str, Any]) -> bytes:
    """The request body as the SDK sends it, serialised the same way every time."""
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
