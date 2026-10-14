"""Reading the text of a scan or a photograph (T076, US2, research.md "OCR strategy").

A photographed CV, and a PDF scanned without a text layer, have no text the document reader can
take. The worker hands their bytes to an OcrEngine instead. A vision model is the primary engine
(T077), because Tesseract is weak on Arabic and weaker still on photographs of printed pages;
Tesseract is the fallback (T078).

An engine that pays for its reading says what it cost and who read it, so the reading is charged
to the organisation like any other model call (AI-02, AI-06). Its failures are the model provider's
typed errors, which carry the same retry meaning: wait out a rate limit, retry a timeout or an
outage, never retry a refusal. A file the engine cannot open at all raises UnreadableDocumentError,
as the document reader does.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

from masirah_pipeline.ports.model_provider import ModelIdentity

OcrSource = Literal["vision_ocr", "tesseract_ocr"]

# What an engine is given: a photograph, or a PDF whose pages carry no text.
OCR_MEDIA_TYPES = frozenset({"image/jpeg", "image/png", "application/pdf"})


@dataclass(frozen=True)
class OcrReading:
    # The text in reading order, or "" when nothing legible was found.
    text: str
    # Which engine read it, recorded as the profile's source.
    source: OcrSource
    # Who answered, for an engine that is a model call; None for one that runs here.
    identity: ModelIdentity | None
    cost_egp: Decimal


class OcrEngine(Protocol):
    def read(self, content: bytes, media_type: str) -> OcrReading:
        """The text of the whole document, every page, in reading order."""
        ...
