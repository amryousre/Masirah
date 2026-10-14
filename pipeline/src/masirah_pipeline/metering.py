"""Every model call recorded with what it cost, as it is made (T093, AI-02, AI-06).

The worker's models are wrapped in MeteredModel, so no call can be left out of an organisation's
spend: neither a usable answer nor a refusal or a cut-short answer that was still paid for. An OCR
engine is wrapped in MeteredOcr for the same reason, its readings charged as extraction. The
worker names the organisation and the CV the calls are for with spending_for, around each CV's
work; a call outside one has no one to charge and is refused rather than spent unrecorded.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from masirah_pipeline.ports.model_provider import (
    ModelIdentity,
    ModelProviderError,
    StructuredModel,
    StructuredRequest,
    StructuredResponse,
)
from masirah_pipeline.ports.ocr_engine import OcrEngine, OcrReading
from masirah_pipeline.ports.spend_ledger import Spend, SpendKind

_charged_to: ContextVar[tuple[UUID, UUID] | None] = ContextVar("charged_to", default=None)


class SpendRecorder(Protocol):
    def record(self, spend: Spend) -> None: ...


@contextmanager
def spending_for(organisation_id: UUID, cv_file_id: UUID) -> Iterator[None]:
    """Charges the model calls made inside the block to this organisation and CV."""
    token = _charged_to.set((organisation_id, cv_file_id))
    try:
        yield
    finally:
        _charged_to.reset(token)


Record = Callable[[ModelIdentity | None, Decimal], None]


@contextmanager
def _charging(ledger: SpendRecorder, kind: SpendKind) -> Iterator[Record]:
    """Charges the call made inside the block to the CV whose work it is part of: the caller
    records what a usable answer cost, and a failure that was still paid for is recorded here."""
    charged = _charged_to.get()
    if charged is None:
        raise RuntimeError("a paid call with no organisation to charge it to")
    organisation, cv_file = charged

    def record(identity: ModelIdentity | None, cost_egp: Decimal) -> None:
        provider = identity.provider if identity else None
        model = identity.model_id if identity else None
        ledger.record(Spend(organisation, cv_file, kind, provider, model, cost_egp))

    try:
        yield record
    except ModelProviderError as error:
        if error.cost_egp > 0:
            record(None, error.cost_egp)
        raise


@dataclass
class MeteredModel:
    inner: StructuredModel
    kind: SpendKind
    ledger: SpendRecorder

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        with _charging(self.ledger, self.kind) as record:
            response = self.inner.complete(request)
            record(response.identity, response.cost_egp)
        return response


@dataclass
class MeteredOcr:
    """An OCR engine whose paid readings are charged as extraction: reading a scan is part of
    reading the CV. A reading that cost nothing, as Tesseract's do, leaves no row."""

    inner: OcrEngine
    ledger: SpendRecorder

    def read(self, content: bytes, media_type: str) -> OcrReading:
        with _charging(self.ledger, "extraction") as record:
            reading = self.inner.read(content, media_type)
            if reading.cost_egp > 0:
                record(reading.identity, reading.cost_egp)
        return reading
