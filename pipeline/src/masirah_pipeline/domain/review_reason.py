"""Why a CV waits in the review queue (T080, FR-011).

The reasons call for different actions, so the queue shows them apart:

- no_text: nothing could be read from the file, such as a scan or photograph before OCR or a
  PDF without a text layer. A clearer copy, or OCR, is what helps.
- unsupported_language: the CV is written in a language version 1.0 does not read (ADR 0005). A
  person reads it, or asks the candidate for an Arabic or English CV. The language found is
  kept, so the queue can name it.
- low_confidence: a profile was extracted, but too little of it is in the text to trust. A
  person checks the fields against the original.
"""

from dataclasses import dataclass
from typing import Literal

from masirah_pipeline.domain.confidence import needs_review
from masirah_pipeline.domain.language import detect_language

ReviewReason = Literal["no_text", "unsupported_language", "low_confidence"]


@dataclass(frozen=True)
class Review:
    reason: ReviewReason
    language: str | None = None

    def __post_init__(self) -> None:
        if (self.language is not None) != (self.reason == "unsupported_language"):
            raise ValueError("only an unsupported language carries the language found")


def before_extraction(text: str | None) -> Review | None:
    """Why the CV waits instead of being extracted, or None when it can be extracted."""
    if text is None or not text.strip():
        return Review("no_text")
    verdict = detect_language(text)
    if not verdict.supported:
        return Review("unsupported_language", verdict.language)
    return None


def after_extraction(score: float) -> Review | None:
    """Why an extracted profile waits instead of being scored, or None when it is trusted."""
    return Review("low_confidence") if needs_review(score) else None
