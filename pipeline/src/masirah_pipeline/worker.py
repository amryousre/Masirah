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
a file already in review is left there. A file whose content the organisation has extracted
before reuses that profile and its candidate without reading the file or calling the model
(AI-03). Every database operation is scoped to the message's organisation (obligation 3).
Scoring, with the redaction that keeps protected attributes from the model (obligation 6) and the
score's cost (obligation 5), sits behind the Scorer (T056, T057).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol
from uuid import UUID

from masirah_pipeline.domain.arabic import name_normalised
from masirah_pipeline.domain.budget import halt_reason, month_start, next_month_start
from masirah_pipeline.domain.confidence import confidence
from masirah_pipeline.domain.profile import Profile, profile_from_output
from masirah_pipeline.domain.review_reason import Review, after_extraction, before_extraction
from masirah_pipeline.extraction import extract_profile
from masirah_pipeline.metering import MeteredOcr, spending_for
from masirah_pipeline.ports.cv_store import CvStore, MissingCvError
from masirah_pipeline.ports.document_text import DocumentReader, UnreadableDocumentError
from masirah_pipeline.ports.job_queue import JobQueue, ReceivedMessage
from masirah_pipeline.ports.model_provider import RefusedError, StructuredModel
from masirah_pipeline.ports.ocr_engine import OCR_MEDIA_TYPES
from masirah_pipeline.ports.queue_message import (
    CV_PROCESSING,
    CvProcessingMessage,
    CvRescoringMessage,
    Locale,
    RejectedMessageError,
    parse_queue_message,
)
from masirah_pipeline.ports.spend_ledger import SpendLedger
from masirah_pipeline.ports.worker_store import (
    CachedProfile,
    CandidateDetails,
    CvFile,
    Extraction,
    ExtractionSource,
    WorkerStore,
)
from masirah_pipeline.work_context import working_on

log = logging.getLogger("masirah.worker")

# A message is attempted this many times; the read after the last attempt fails the file.
MAX_ATTEMPTS = 5
# How long a read message stays hidden: room for the slowest CV's model calls, after which a
# message whose worker crashed comes back.
VISIBILITY_SECONDS = 600
BATCH_SIZE = 5
# A PDF with fewer letters than this is taken for a scan: the shortest native CV in the corpus has
# 487, while a scanning app's watermark has a few dozen.
SCANNED_TEXT_LETTERS = 200
# Statuses a file reaches once extraction is settled. A retry does not extract it again.
SETTLED = frozenset({"extracted", "needs_review"})


class Outcome(Enum):
    DONE = "done"
    LEFT = "left"
    ARCHIVED = "archived"
    # Put back until the organisation's monthly limits renew (T093).
    DEFERRED = "deferred"


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


def _silent() -> None:
    """No heartbeat, for a worker nobody monitors."""


@dataclass(frozen=True)
class _Read:
    """A CV's text, how it was read, and what reading it cost."""

    text: str
    source: ExtractionSource
    cost_egp: Decimal


def _letters(text: str) -> int:
    return sum(character.isalpha() for character in text)


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
    # This month's spend and limits per organisation, which halt its processing (T093).
    budget: SpendLedger
    # Records that the worker is alive (T030): before each batch and after every message, so a
    # long batch still shows it working.
    beat: Callable[[], None] = _silent
    # Reads scans and photographs (T076). Without one they go to the review queue unread. It is
    # metered by type, so a paid engine cannot be given to the worker without its spend counted.
    ocr: MeteredOcr | None = None
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def run_once(self) -> int:
        self._beat()
        batch = self.queue.read(
            CV_PROCESSING, visibility_seconds=VISIBILITY_SECONDS, quantity=BATCH_SIZE
        )
        for received in batch:
            self.handle(CV_PROCESSING, received)
            self._beat()
        return len(batch)

    def _beat(self) -> None:
        """The heartbeat reports on the work, so its failure is logged and the work goes on: a
        stopped worker would leave the rest of its batch hidden until the visibility timeout."""
        try:
            self.beat()
        except Exception:
            log.exception("the heartbeat could not be recorded; processing continues")

    def handle(self, queue: str, received: ReceivedMessage) -> Outcome:
        try:
            message = parse_queue_message(received.body)
        except RejectedMessageError as error:
            log.error("message %s refused, left in %s: %s", received.message_id, queue, error)
            return Outcome.LEFT
        if isinstance(message, CvRescoringMessage):
            log.error(
                "message %s in %s is a rescoring request, which has no handler yet",
                received.message_id,
                queue,
            )
            return Outcome.LEFT
        with working_on(message.organisation_id, message.cv_file_id):
            return self._handle(queue, received, message)

    def _handle(
        self, queue: str, received: ReceivedMessage, message: CvProcessingMessage
    ) -> Outcome:
        try:
            if received.read_count > MAX_ATTEMPTS:
                raise _TerminalError(f"processing failed after {MAX_ATTEMPTS} attempts")
            if self._halted(message.organisation_id):
                until = next_month_start(self.clock())
                self.queue.defer(queue, received.message_id, until)
                log.warning(
                    "organisation %s is at its monthly limit; CV file %s waits until %s",
                    message.organisation_id,
                    message.cv_file_id,
                    until.isoformat(),
                )
                return Outcome.DEFERRED
            with spending_for(message.organisation_id, message.cv_file_id):
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

    def _halted(self, organisation: UUID) -> bool:
        """Whether the organisation has reached its monthly CV limit or spend ceiling (AI-06):
        checked before any of a CV's work, so the most it can be passed by is the cost of the
        CVs already being read when it is reached."""
        usage = self.budget.usage(organisation, month_start(self.clock()))
        return halt_reason(usage, self.budget.limits(organisation)) is not None

    def _process(self, message: CvProcessingMessage) -> None:
        organisation, file_id = message.organisation_id, message.cv_file_id
        cv_file = self.store.cv_file(organisation, file_id)
        if cv_file is None:
            raise _TerminalError("the CV file does not exist")
        if cv_file.content_hash != message.content_hash:
            raise _TerminalError("the file's content does not match the content the message names")
        if cv_file.storage_path != message.storage_path:
            raise _TerminalError("the message names another object than the file's own")
        if cv_file.status in SETTLED:
            stored = self.store.current_profile(organisation, file_id)
            if cv_file.status == "extracted" and stored is not None:
                if cv_file.candidate_id is None:
                    raise RuntimeError("an extracted CV file has no candidate")
                profile = profile_from_output(stored.profile)
                self._score(message, cv_file.candidate_id, profile, Decimal(0))
            return
        self.store.mark_extracting(organisation, file_id)
        cached = self.store.profile_for_content(organisation, message.content_hash, file_id)
        if cached is not None:
            self._reuse(message, cached)
            return
        read = self._text(cv_file)
        text = None if read is None else read.text
        waiting = before_extraction(text)
        if waiting is not None or read is None:
            self.store.mark_needs_review(organisation, file_id, waiting or Review("no_text"))
            return
        try:
            extracted = extract_profile(self.model, read.text)
        except RefusedError as error:
            raise _TerminalError(f"the model declined to read the CV: {error}") from error
        score = Decimal(str(round(confidence(extracted.profile, read.text), 3)))
        review = after_extraction(float(score))
        candidate_id = self.store.record_extraction(
            organisation,
            file_id,
            Extraction(
                source=read.source,
                confidence=score,
                profile=extracted.profile.as_dict(),
                candidate=_candidate(extracted.profile),
                review=review,
            ),
        )
        if review is None:
            cost = extracted.response.cost_egp + read.cost_egp
            self._score(message, candidate_id, extracted.profile, cost)

    def _reuse(self, message: CvProcessingMessage, cached: CachedProfile) -> None:
        """The same bytes were extracted before: take that profile, at no model cost (AI-03)."""
        profile = profile_from_output(cached.profile)
        review = after_extraction(float(cached.confidence))
        candidate_id = self.store.record_extraction(
            message.organisation_id,
            message.cv_file_id,
            Extraction(
                source=cached.source,
                confidence=cached.confidence,
                profile=cached.profile,
                candidate=_candidate(profile),
                review=review,
                candidate_id=cached.candidate_id,
            ),
        )
        if review is None:
            self._score(message, candidate_id, profile, Decimal(0))

    def _text(self, cv_file: CvFile) -> _Read | None:
        """The CV's text and how it was read, or None when it has none: a photograph or a scan
        with no OCR engine to read it, or a document nothing legible could be taken from.

        A PDF is read by OCR when its own text is too thin to be a CV, as when a scanning app
        stamps a watermark on page images, and the OCR text replaces it when it holds more."""
        photograph = cv_file.mime_type.startswith("image/")
        ocr = self.ocr if cv_file.mime_type in OCR_MEDIA_TYPES else None
        if photograph and ocr is None:
            return None
        try:
            content = self.files.fetch(cv_file.storage_path)
        except MissingCvError as error:
            raise _TerminalError("the original file is missing from storage") from error
        try:
            native = "" if photograph else self.read_text(content)
            if ocr is None or _letters(native) >= SCANNED_TEXT_LETTERS:
                return _Read(native, "native_text", Decimal(0)) if native.strip() else None
            reading = ocr.read(content, cv_file.mime_type)
        except UnreadableDocumentError as error:
            raise _TerminalError(f"the file cannot be read: {error}") from error
        except RefusedError as error:
            raise _TerminalError(f"the model declined to read the scan: {error}") from error
        if _letters(reading.text) > _letters(native):
            return _Read(reading.text, reading.source, reading.cost_egp)
        # The paid reading found no more than the PDF's own text, which is used instead.
        return _Read(native, "native_text", reading.cost_egp) if native.strip() else None

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
