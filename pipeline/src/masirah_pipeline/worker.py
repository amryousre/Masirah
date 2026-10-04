"""The worker's consume loop (T054, contracts/queue-message.md).

The worker reads a batch of messages and handles each one to one of three outcomes:

- DONE: the work is committed, so the message is deleted (obligation 2).
- LEFT: the message stays in the queue and returns after its visibility timeout. This covers a
  failure the next attempt may not repeat, such as a rate limit or an outage, and a message this
  worker must not process, which also raises an alert.
- ARCHIVED: the file can never be processed. Its failure is recorded on the file, where the user
  sees it (obligation 4), and the message is archived rather than deleted.

A CV is never dropped (SC-006). It ends extracted, in the review queue, or failed with a reason.
A retry is safe (obligation 1): a file that already has its profile is not extracted again, and
a file already in review is left there. Every database operation is scoped to the message's
organisation (obligation 3). Scoring, with the redaction that keeps protected attributes from
the model (obligation 6) and the score's cost (obligation 5), sits behind the Scorer (T056, T057).
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol
from uuid import UUID

from masirah_pipeline.domain.arabic import name_normalised
from masirah_pipeline.domain.confidence import confidence, needs_review
from masirah_pipeline.domain.language import detect_language
from masirah_pipeline.domain.profile import Profile, profile_from_output
from masirah_pipeline.extraction import extract_profile
from masirah_pipeline.ports.cv_store import CvStore, MissingCvError
from masirah_pipeline.ports.document_text import DocumentReader, UnreadableDocumentError
from masirah_pipeline.ports.job_queue import JobQueue, ReceivedMessage
from masirah_pipeline.ports.model_provider import RefusedError, StructuredModel
from masirah_pipeline.ports.queue_message import (
    CV_PROCESSING,
    CvProcessingMessage,
    CvRescoringMessage,
    Locale,
    RejectedMessageError,
    parse_queue_message,
)
from masirah_pipeline.ports.worker_store import (
    CandidateDetails,
    CvFile,
    Extraction,
    WorkerStore,
)

log = logging.getLogger("masirah.worker")

# A message is attempted this many times; the read after the last attempt fails the file.
MAX_ATTEMPTS = 5
# How long a read message stays hidden: room for the slowest CV's model calls, after which a
# message whose worker crashed comes back.
VISIBILITY_SECONDS = 600
BATCH_SIZE = 5
# Statuses a file reaches once extraction is settled. A retry does not extract it again.
SETTLED = frozenset({"extracted", "needs_review"})


class Outcome(Enum):
    DONE = "done"
    LEFT = "left"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ScoringRequest:
    organisation_id: UUID
    application_id: UUID
    job_id: UUID
    profile: Profile
    locale: Locale
    # What extracting this CV cost in this run, which the score's cost includes (NFR-13); zero
    # when the profile came from an earlier run.
    extraction_cost_egp: Decimal


class Scorer(Protocol):
    def __call__(self, request: ScoringRequest) -> None: ...


class _TerminalError(Exception):
    """The file cannot be processed, however often it is tried."""


@dataclass
class Worker:
    queue: JobQueue
    store: WorkerStore
    files: CvStore
    read_text: DocumentReader
    model: StructuredModel
    score: Scorer

    def run_once(self) -> int:
        batch = self.queue.read(
            CV_PROCESSING, visibility_seconds=VISIBILITY_SECONDS, quantity=BATCH_SIZE
        )
        for received in batch:
            self.handle(CV_PROCESSING, received)
        return len(batch)

    def handle(self, queue: str, received: ReceivedMessage) -> Outcome:
        try:
            message = parse_queue_message(received.body)
        except RejectedMessageError as error:
            log.error("message %s refused, left in %s: %s", received.message_id, queue, error)
            return Outcome.LEFT
        if isinstance(message, CvRescoringMessage):
            log.error("message %s is a rescoring request, which has no handler yet", queue)
            return Outcome.LEFT
        try:
            if received.read_count > MAX_ATTEMPTS:
                raise _TerminalError(f"processing failed after {MAX_ATTEMPTS} attempts")
            self._process(message)
        except _TerminalError as error:
            self._fail(queue, received, message, str(error))
            return Outcome.ARCHIVED
        except Exception:
            log.exception(
                "message %s for CV file %s failed on attempt %s; it will be retried",
                received.message_id,
                message.cv_file_id,
                received.read_count,
            )
            return Outcome.LEFT
        self.queue.delete(queue, received.message_id)
        return Outcome.DONE

    def _process(self, message: CvProcessingMessage) -> None:
        organisation, file_id = message.organisation_id, message.cv_file_id
        cv_file = self.store.cv_file(organisation, file_id)
        if cv_file is None:
            raise _TerminalError("the CV file does not exist")
        if cv_file.content_hash != message.content_hash:
            raise _TerminalError("the file's content does not match the content the message names")
        if cv_file.status in SETTLED:
            stored = self.store.current_profile(organisation, file_id)
            if cv_file.status == "extracted" and stored is not None:
                if cv_file.candidate_id is None:
                    raise RuntimeError("an extracted CV file has no candidate")
                profile = profile_from_output(stored.profile)
                self._score(message, cv_file.candidate_id, profile, Decimal(0))
            return
        self.store.mark_extracting(organisation, file_id)
        text = self._text(message, cv_file)
        if text is None or not detect_language(text).supported:
            self.store.mark_needs_review(organisation, file_id)
            return
        try:
            extracted = extract_profile(self.model, text)
        except RefusedError as error:
            raise _TerminalError(f"the model declined to read the CV: {error}") from error
        score = Decimal(str(round(confidence(extracted.profile, text), 3)))
        doubtful = needs_review(float(score))
        candidate_id = self.store.record_extraction(
            organisation,
            file_id,
            Extraction(
                source="native_text",
                confidence=score,
                profile=extracted.profile.as_dict(),
                candidate=_candidate(extracted.profile),
                status="needs_review" if doubtful else "extracted",
            ),
        )
        if not doubtful:
            self._score(message, candidate_id, extracted.profile, extracted.response.cost_egp)

    def _text(self, message: CvProcessingMessage, cv_file: CvFile) -> str | None:
        """The CV's text, or None when it has none to read until OCR arrives (T076)."""
        if cv_file.mime_type.startswith("image/"):
            return None
        try:
            content = self.files.fetch(message.storage_path)
        except MissingCvError as error:
            raise _TerminalError("the original file is missing from storage") from error
        try:
            text = self.read_text(content)
        except UnreadableDocumentError as error:
            raise _TerminalError(f"the file cannot be read: {error}") from error
        return text if text.strip() else None

    def _score(
        self, message: CvProcessingMessage, candidate_id: UUID, profile: Profile, cost: Decimal
    ) -> None:
        if message.job_id is None:
            return
        application_id = self.store.ensure_application(
            message.organisation_id, candidate_id, message.job_id
        )
        self.score(
            ScoringRequest(
                organisation_id=message.organisation_id,
                application_id=application_id,
                job_id=message.job_id,
                profile=profile,
                locale=message.locale,
                extraction_cost_egp=cost,
            )
        )

    def _fail(
        self, queue: str, received: ReceivedMessage, message: CvProcessingMessage, reason: str
    ) -> None:
        log.error("CV file %s failed: %s", message.cv_file_id, reason)
        cv_file = self.store.cv_file(message.organisation_id, message.cv_file_id)
        # An extracted file keeps its profile when only its scoring kept failing: the alert is
        # what surfaces that, not a failure that would hide a sound extraction.
        if cv_file is not None and cv_file.status not in SETTLED:
            self.store.mark_failed(message.organisation_id, message.cv_file_id, reason)
        self.queue.archive(queue, received.message_id)


def _candidate(profile: Profile) -> CandidateDetails:
    return CandidateDetails(
        full_name=profile.name,
        email=profile.emails[0] if profile.emails else None,
        phone=profile.phones[0] if profile.phones else None,
        location=profile.location,
        name_normalised=name_normalised(profile.name) if profile.name else None,
    )
