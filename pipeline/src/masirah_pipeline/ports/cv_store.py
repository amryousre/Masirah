"""Where uploaded CV files are kept (T054).

The worker only ever reads an original: originals are retained unchanged (FR-012).
"""

from typing import Protocol


class MissingCvError(LookupError):
    """No file at the path. Retrying cannot help."""


class CvStoreUnavailableError(Exception):
    """The store could not be reached or failed. The next attempt may succeed."""


class CvStore(Protocol):
    def fetch(self, storage_path: str) -> bytes: ...
