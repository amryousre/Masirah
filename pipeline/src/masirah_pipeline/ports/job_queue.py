"""The job queue port (T053, contracts/queue-message.md).

The worker reads a message, does the work, and deletes the message only once the results are
committed. A message it does not delete comes back after its visibility timeout, which is the
retry mechanism; read_count says how many times it has been handed out, so the worker can stop at
its retry limit and archive the message rather than retrying forever.

The body is returned as the JSON it was sent as. parse_queue_message decides whether it is a
message this worker understands, so a refused message can be left in the queue and alerted on.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ReceivedMessage:
    message_id: int
    read_count: int
    enqueued_at: datetime
    body: Any


class JobQueue(Protocol):
    def read(self, queue: str, *, visibility_seconds: int, quantity: int) -> list[ReceivedMessage]:
        """Up to quantity waiting messages, hidden from other readers for visibility_seconds."""
        ...

    def delete(self, queue: str, message_id: int) -> bool:
        """Remove a message whose work is done. False when it was already gone."""
        ...

    def archive(self, queue: str, message_id: int) -> bool:
        """Move a message that failed for good out of the queue, keeping it for inspection."""
        ...
