"""How the worker reaches an operator, and reads the figures an alert is made from (T031)."""

from typing import Protocol

from masirah_pipeline.domain.parse_failures import ParseOutcomes


class Alerts(Protocol):
    """Posts a short text to the operators' channel."""

    def send(self, text: str) -> None: ...


class ParseOutcomeSource(Protocol):
    """The CV files settled within the past `window_seconds`, across every organisation."""

    def __call__(self, window_seconds: int) -> ParseOutcomes: ...
