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
class DueFile:
    """A CV that never became a candidate, kept past its organisation's retention."""

    organisation_id: UUID
    cv_file_id: UUID
    storage_path: str


class PurgeStore(Protocol):
    def due(self, at_most: int) -> list[DuePurge]:
        """Open deletion requests first, then candidates past their organisation's retention."""
        ...

    def original_paths(self, candidate_id: UUID) -> list[str]:
        """Where the candidate's stored originals are, until they are purged."""
        ...

    def purge(self, candidate_id: UUID, reason: str) -> None:
        """Clears the candidate's personal data and records it. Safe to repeat."""
        ...

    def due_files(self, at_most: int) -> list[DueFile]:
        """CVs without a candidate kept past their organisation's retention."""
        ...

    def purge_file(self, cv_file_id: UUID) -> None:
        """Empties what was read from the file and names it nothing personal."""
        ...
