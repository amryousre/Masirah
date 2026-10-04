"""Extracting a profile from CV text through the provider port (T048, FR-008).

The operation, not the provider, decides what is asked: the instructions, the output schema and
the prompt version are the same whichever provider answers.
"""

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from masirah_pipeline.domain.profile import PROFILE_SCHEMA
from masirah_pipeline.extraction import PROMPT_VERSION, extract_profile
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    ModelIdentity,
    StructuredRequest,
    StructuredResponse,
    Usage,
)

LABELS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs" / "en-native-03.json"


@dataclass
class FakeModel:
    output: dict[str, Any]
    requests: list[StructuredRequest] = field(default_factory=list)

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.requests.append(request)
        return StructuredResponse(
            output=self.output,
            identity=ModelIdentity(
                "anthropic", "claude-haiku-4-5-20251001", request.prompt_version
            ),
            usage=Usage(1000, 200),
            cost_egp=Decimal("0.3"),
            payload=b"{}",
        )


def labelled_profile() -> dict[str, Any]:
    profile: dict[str, Any] = json.loads(LABELS.read_text(encoding="utf-8"))["profile"]
    return profile


def test_the_profile_comes_back_with_the_calls_identity_and_cost() -> None:
    extracted = extract_profile(FakeModel(labelled_profile()), "YOUSSEF SAMIR NABIL ...")
    assert extracted.profile.as_dict() == labelled_profile()
    assert extracted.response.identity.prompt_version == PROMPT_VERSION
    assert extracted.response.cost_egp == Decimal("0.3")


def test_the_request_is_the_cv_text_under_the_profile_schema() -> None:
    model = FakeModel(labelled_profile())
    extract_profile(model, "YOUSSEF SAMIR NABIL ...")
    (request,) = model.requests
    assert request.content == "YOUSSEF SAMIR NABIL ..."
    assert request.schema == PROFILE_SCHEMA
    assert request.prompt_version == PROMPT_VERSION


@pytest.mark.parametrize(
    "rule",
    ["E.164", "YYYY-MM", "present", "null", "soft skills", "certifications", "translate"],
)
def test_the_instructions_carry_the_labelling_conventions(rule: str) -> None:
    """The model is told the conventions the gate scores against (fixtures/cvs/README.md)."""
    model = FakeModel(labelled_profile())
    extract_profile(model, "CV")
    assert rule in model.requests[0].instructions


def test_output_that_is_not_a_profile_is_malformed_and_still_costs() -> None:
    with pytest.raises(MalformedOutputError) as caught:
        extract_profile(FakeModel({"name": "Youssef"}), "CV")
    assert caught.value.cost_egp == Decimal("0.3")


def test_empty_text_is_not_sent() -> None:
    """A document with no text layer goes to OCR; asking a model to read nothing costs money."""
    model = FakeModel(labelled_profile())
    with pytest.raises(ValueError, match="no text"):
        extract_profile(model, "  \n ")
    assert model.requests == []


class TestTheGatesExtractor:
    """tests/accuracy/extractors.py, which the accuracy gate runs with a real model."""

    CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"

    def test_it_returns_the_profile_in_the_labels_format_and_tallies_spend(self) -> None:
        from tests.accuracy import extractors

        extractors.SPENT.clear()
        extract = extractors.model_extractor(FakeModel(labelled_profile()))
        assert extract(self.CORPUS / "en-native-03.pdf") == labelled_profile()
        assert "0.30 EGP in all" in extractors.spend_summary()

    def test_a_document_without_text_is_not_sent(self) -> None:
        from tests.accuracy import extractors

        model = FakeModel(labelled_profile())
        with pytest.raises(NotImplementedError, match="OCR"):
            extractors.model_extractor(model)(self.CORPUS / "en-scanned-01.pdf")
        assert model.requests == []
