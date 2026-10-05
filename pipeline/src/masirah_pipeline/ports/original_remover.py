"""Removing stored originals, which only purging does (T100, T101).

Kept apart from CvStore: extraction only ever reads an original, and must not be handed the means
to delete one.
"""

from collections.abc import Sequence
from typing import Protocol


class OriginalRemover(Protocol):
    def remove(self, storage_paths: Sequence[str]) -> None:
        """Removes the objects; one already gone is not an error. Raises CvStoreUnavailableError
        when the store cannot be reached or refuses."""
        ...
