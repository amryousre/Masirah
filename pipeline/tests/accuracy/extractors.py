"""Extractors the accuracy gate can measure, named with MASIRAH_EXTRACTOR.

    MASIRAH_EXTRACTOR=tests.accuracy.extractors:cheap_model \
        uv run --env-file .env pytest tests/accuracy

cheap_model reads a document's native text and extracts with whichever model
MASIRAH_CHEAP_MODEL names, so measuring another provider is a change to that one variable. The
spend of every call is tallied and printed with the report, since accuracy and cost per CV are the
two things decision Q5 compares.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.adapters.provider_registry import model_for
from masirah_pipeline.extraction import extract_profile
from masirah_pipeline.ports.model_provider import ModelProviderError, StructuredModel
from tests.accuracy.field_accuracy import Extraction


@dataclass(frozen=True)
class Spend:
    model: str | None  # None for a call that failed
    input_tokens: int
    output_tokens: int
    cost_egp: Decimal


SPENT: list[Spend] = []


def model_extractor(model: StructuredModel) -> Callable[[Path], Extraction]:
    def extract(path: Path) -> Extraction:
        text = read_native_text(path.read_bytes())
        if not text.strip():
            raise NotImplementedError("no text layer: reading scans and photos is OCR, T076-T078")
        try:
            extracted = extract_profile(model, text)
        except ModelProviderError as error:
            SPENT.append(Spend(None, 0, 0, error.cost_egp))
            raise
        response = extracted.response
        SPENT.append(
            Spend(
                response.identity.model_id,
                response.usage.input_tokens,
                response.usage.output_tokens,
                response.cost_egp,
            )
        )
        return extracted.profile.as_dict()

    return extract


@cache
def _cheap() -> Callable[[Path], Extraction]:
    return model_extractor(model_for("cheap"))


def cheap_model(path: Path) -> Extraction:
    return _cheap()(path)


def spend_summary() -> str:
    if not SPENT:
        return ""
    answered = [spend for spend in SPENT if spend.model is not None]
    models = sorted({spend.model for spend in answered if spend.model is not None})
    cost = sum((spend.cost_egp for spend in SPENT), Decimal(0))
    tokens_in = sum(spend.input_tokens for spend in answered)
    tokens_out = sum(spend.output_tokens for spend in answered)
    failed = len(SPENT) - len(answered)
    return (
        f"Spend: {len(answered)} calls answered by {', '.join(models) or 'no model'} "
        f"and {failed} failed, {tokens_in:,} tokens in and {tokens_out:,} out, "
        f"{cost:.2f} EGP in all, {cost / len(SPENT):.3f} EGP per CV"
    )
