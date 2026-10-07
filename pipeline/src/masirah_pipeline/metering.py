"""Every model call recorded with what it cost, as it is made (T093, AI-02, AI-06).

The worker's models are wrapped in MeteredModel, so no call can be left out of an organisation's
spend: neither a usable answer nor a refusal or a cut-short answer that was still paid for. The
worker names the organisation and the CV the calls are for with spending_for, around each CV's
work; a call outside one has no one to charge and is refused rather than spent unrecorded.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from masirah_pipeline.ports.model_provider import (
    ModelProviderError,
    StructuredModel,
    StructuredRequest,
    StructuredResponse,
)
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


@dataclass
class MeteredModel:
    inner: StructuredModel
    kind: SpendKind
    ledger: SpendRecorder

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        charged = _charged_to.get()
        if charged is None:
            raise RuntimeError("a model call with no organisation to charge it to")
        organisation, cv_file = charged
        try:
            response = self.inner.complete(request)
        except ModelProviderError as error:
            if error.cost_egp > 0:
                self.ledger.record(
                    Spend(organisation, cv_file, self.kind, None, None, error.cost_egp)
                )
            raise
        self.ledger.record(
            Spend(
                organisation,
                cv_file,
                self.kind,
                response.identity.provider,
                response.identity.model_id,
                response.cost_egp,
            )
        )
        return response
