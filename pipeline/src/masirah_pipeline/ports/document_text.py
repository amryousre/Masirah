"""Reading a CV file's text (T052, T054).

The worker depends on this port, not on the PDF and Word libraries behind it, so the consume loop
can be tested without documents and the OCR path (T076) can join without changing it.
"""

from typing import Protocol


class UnreadableDocumentError(ValueError):
    """The file is not a document that can be read: corrupt, encrypted or of another kind."""


class DocumentReader(Protocol):
    def __call__(self, content: bytes) -> str:
        """The document's text in reading order, or "" when it has none, as a scan has none."""
        ...
