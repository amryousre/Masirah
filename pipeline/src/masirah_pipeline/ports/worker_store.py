"""The worker's tenant data (T054, contracts/queue-message.md obligations 1, 3 and 4).

Every operation names the organisation it acts in, and the adapter declares that organisation to
the database for the operation's transaction, so row level security confines it to that tenant.
Each operation is one transaction: an extraction is recorded whole or not at all, which is what
makes a retried message safe.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Protocol
from uuid import UUID

from masirah_pipeline.domain.review_reason import Review

ExtractionSource = Literal["native_text", "vision_ocr", "tesseract_ocr", "manual"]
ExtractedStatus = Literal["extracted", "needs_review"]


@dataclass(frozen=True)
class CvFile:
    id: UUID
    storage_path: str
    mime_type: str
    content_hash: str
    status: str
    candidate_id: UUID | None


@dataclass(frozen=True)
class StoredProfile:
    """The current parsed profile of a CV file."""

    version: int
    confidence: Decimal
    profile: dict[str, Any]


@dataclass(frozen=True)
class CachedProfile:
    """The current profile of another file with the same content in the organisation (AI-03)."""

    cv_file_id: UUID
    candidate_id: UUID | None
    source: ExtractionSource
    confidence: Decimal
    profile: dict[str, Any]


@dataclass(frozen=True)
class CandidateDetails:
    """Who the CV describes, as the candidate record holds it."""

    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    name_normalised: str | None


@dataclass(frozen=True)
class Extraction:
    source: ExtractionSource
    confidence: Decimal
    profile: dict[str, Any]
    candidate: CandidateDetails
    # Why the profile waits in the review queue, or None when it is trusted.
    review: Review | None
    # The candidate to link when the file has none yet, as when the same content was uploaded
    # before; otherwise a new candidate is created.
    candidate_id: UUID | None = None

    @property
    def status(self) -> ExtractedStatus:
        return "extracted" if self.review is None else "needs_review"


class WorkerStore(Protocol):
    def cv_file(self, organisation_id: UUID, cv_file_id: UUID) -> CvFile | None: ...

    def current_profile(self, organisation_id: UUID, cv_file_id: UUID) -> StoredProfile | None: ...

    def profile_for_content(
        self, organisation_id: UUID, content_hash: str, other_than: UUID
    ) -> CachedProfile | None:
        """The current profile of another file in the organisation with the same content."""
        ...

    def mark_extracting(self, organisation_id: UUID, cv_file_id: UUID) -> None: ...

    def record_extraction(
        self, organisation_id: UUID, cv_file_id: UUID, extraction: Extraction
    ) -> UUID:
        """Add the profile as the file's new current version, create or update the candidate it
        describes, and set the file's status, all at once. Returns the candidate's id."""
        ...

    def mark_needs_review(self, organisation_id: UUID, cv_file_id: UUID, review: Review) -> None:
        """A file the worker cannot extract yet but has not failed on: no text, or a language
        version 1.0 does not support. It stays visible in the review queue with its reason
        (FR-011, SC-006, T080)."""
        ...

    def mark_failed(self, organisation_id: UUID, cv_file_id: UUID, reason: str) -> None: ...

    def ensure_application(self, organisation_id: UUID, candidate_id: UUID, job_id: UUID) -> UUID:
        """The application linking the candidate to the job, created if it does not exist."""
        ...
