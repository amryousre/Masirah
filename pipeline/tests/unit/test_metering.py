"""Every model call is recorded with what it cost, as it is made (T093, AI-02, AI-06).

The worker's models are wrapped so no call can be left out of an organisation's spend: a usable
answer, and a refusal or a cut-short answer that was still paid for. A call outside a CV's work
has no organisation to charge, so it is refused rather than spent unrecorded.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from masirah_pipeline.metering import MeteredModel, MeteredOcr, spending_for
from masirah_pipeline.ports.model_provider import (
    MalformedOutputError,
    ModelIdentity,
    ProviderUnavailableError,
    RefusedError,
    StructuredRequest,
    StructuredResponse,
    Usage,
)
from masirah_pipeline.ports.ocr_engine import OcrReading
from masirah_pipeline.ports.spend_ledger import Spend

ORG, FILE = uuid.uuid4(), uuid.uuid4()
REQUEST = StructuredRequest(
    instructions="Read the CV.",
    content="CV text",
    schema_name="profile",
    schema={"type": "object"},
    prompt_version="extract-profile/1",
    max_output_tokens=100,
)


@dataclass
class Ledger:
    spent: list[Spend] = field(default_factory=list)

    def record(self, spend: Spend) -> None:
        self.spent.append(spend)


@dataclass
class Model:
    error: Exception | None = None

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        if self.error is not None:
            raise self.error
        return StructuredResponse(
            output={},
            identity=ModelIdentity("anthropic", "model-x", request.prompt_version),
            usage=Usage(1000, 100),
            cost_egp=Decimal("0.42"),
            payload=b"",
        )


def test_a_usable_answer_is_recorded_with_who_answered() -> None:
    ledger = Ledger()
    model = MeteredModel(Model(), "extraction", ledger)
    with spending_for(ORG, FILE):
        model.complete(REQUEST)
    assert ledger.spent == [Spend(ORG, FILE, "extraction", "anthropic", "model-x", Decimal("0.42"))]


@pytest.mark.parametrize(
    "error",
    [
        RefusedError("declined", cost_egp=Decimal("0.10")),
        MalformedOutputError("cut short", cost_egp=Decimal("0.30")),
    ],
    ids=["refused", "cut-short"],
)
def test_a_paid_failure_is_recorded_and_still_raised(error: Exception) -> None:
    ledger = Ledger()
    model = MeteredModel(Model(error), "scoring", ledger)
    with spending_for(ORG, FILE), pytest.raises(type(error)):
        model.complete(REQUEST)
    assert [(spend.kind, spend.provider, spend.cost_egp) for spend in ledger.spent] == [
        ("scoring", None, error.cost_egp)  # type: ignore[attr-defined]
    ]


def test_a_failure_that_cost_nothing_is_not_recorded() -> None:
    ledger = Ledger()
    model = MeteredModel(Model(ProviderUnavailableError("outage")), "summary", ledger)
    with spending_for(ORG, FILE), pytest.raises(ProviderUnavailableError):
        model.complete(REQUEST)
    assert ledger.spent == []


def test_a_call_outside_a_cvs_work_is_refused() -> None:
    ledger = Ledger()
    model = MeteredModel(Model(), "extraction", ledger)
    with pytest.raises(RuntimeError, match="no organisation"):
        model.complete(REQUEST)
    assert ledger.spent == []


def test_the_work_it_is_charged_to_ends_with_its_block() -> None:
    ledger = Ledger()
    model = MeteredModel(Model(), "extraction", ledger)
    with spending_for(ORG, FILE):
        pass
    with pytest.raises(RuntimeError):
        model.complete(REQUEST)


@dataclass
class Ocr:
    reading: OcrReading = field(
        default_factory=lambda: OcrReading(
            "CV text", "vision_ocr", ModelIdentity("openai", "model-v", "ocr/1"), Decimal("0.25")
        )
    )
    error: Exception | None = None

    def read(self, content: bytes, media_type: str) -> OcrReading:
        if self.error is not None:
            raise self.error
        return self.reading


def test_a_paid_ocr_reading_is_recorded_as_extraction() -> None:
    ledger = Ledger()
    with spending_for(ORG, FILE):
        MeteredOcr(Ocr(), ledger).read(b"image", "image/png")
    assert ledger.spent == [Spend(ORG, FILE, "extraction", "openai", "model-v", Decimal("0.25"))]


def test_a_reading_that_cost_nothing_is_not_recorded() -> None:
    ledger = Ledger()
    free = OcrReading("CV text", "tesseract_ocr", None, Decimal(0))
    with spending_for(ORG, FILE):
        MeteredOcr(Ocr(free), ledger).read(b"image", "image/png")
    assert ledger.spent == []


def test_a_paid_ocr_failure_is_recorded_and_still_raised() -> None:
    ledger = Ledger()
    engine = Ocr(error=RefusedError("declined", cost_egp=Decimal("0.05")))
    with spending_for(ORG, FILE), pytest.raises(RefusedError):
        MeteredOcr(engine, ledger).read(b"image", "image/png")
    assert ledger.spent == [Spend(ORG, FILE, "extraction", None, None, Decimal("0.05"))]


def test_an_ocr_reading_outside_a_cvs_work_is_refused() -> None:
    ledger = Ledger()
    with pytest.raises(RuntimeError, match="no organisation"):
        MeteredOcr(Ocr(), ledger).read(b"image", "image/png")
    assert ledger.spent == []
