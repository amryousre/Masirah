"""What the purge sweep needs from the database (T100, T101, migration 0022)."""

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

PurgeReason = Literal["request", "retention"]


@dataclass(frozen=True)
class DuePurge:
    organisation_id: UUID
    candidate_id: UUID
    reason: PurgeReason


@dataclass(frozen=True)
class OriginalFile:
    """One of a candidate's CVs whose stored original the sweep removes."""

    cv_file_id: UUID
    storage_path: str


@dataclass(frozen=True)
class DueFile:
    """A CV that never became a candidate, kept past its organisation's retention."""

    organisation_id: UUID
    cv_file_id: UUID
    storage_path: str


class PurgeStore(Protocol):
    def due(self, at_most: int) -> list[DuePurge]:
        """Open deletion requests first, then candidates past their organisation's retention."""
        ...

    def originals(self, candidate_id: UUID) -> list[OriginalFile]:
        """The candidate's CVs whose stored originals are still there."""
        ...

    def purge(self, candidate_id: UUID, reason: str, removed: list[UUID]) -> None:
        """Clears the candidate's personal data once the originals of `removed` are gone, and
        records it. A CV linked since the originals were listed is left for the next sweep."""
        ...

    def due_files(self, at_most: int) -> list[DueFile]:
        """CVs without a candidate kept past their organisation's retention."""
        ...

    def purge_file(self, cv_file_id: UUID) -> None:
        """Empties what was read from the file and names it nothing personal."""
        ...
