"""The worker's consume loop (T054, contracts/queue-message.md worker obligations).

Each test hands the worker one queue message and checks what it recorded and what became of the
message: deleted once the work is committed, left in the queue to retry, or archived when it can
never succeed. A file is never dropped: it ends extracted, in the review queue, or failed with a
reason (SC-006).
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from masirah_pipeline.domain.budget import Limits, next_month_start
from masirah_pipeline.domain.budget import Usage as BudgetUsage
from masirah_pipeline.domain.profile import Profile
from masirah_pipeline.domain.review_reason import Review
from masirah_pipeline.metering import MeteredModel, MeteredOcr
from masirah_pipeline.ports.cv_store import CvStoreUnavailableError, MissingCvError
from masirah_pipeline.ports.document_text import UnreadableDocumentError
from masirah_pipeline.ports.job_queue import ReceivedMessage
from masirah_pipeline.ports.model_provider import (
    ModelIdentity,
    ProviderUnavailableError,
    RateLimitedError,
    RefusedError,
    StructuredRequest,
    StructuredResponse,
    Usage,
)
from masirah_pipeline.ports.ocr_engine import OcrReading
from masirah_pipeline.ports.queue_message import CV_PROCESSING
from masirah_pipeline.ports.spend_ledger import Spend
from masirah_pipeline.ports.worker_store import CachedProfile, CvFile, Extraction, StoredProfile
from masirah_pipeline.work_context import current_work
from masirah_pipeline.worker import MAX_ATTEMPTS, Outcome, ScoringRequest, Worker

ORG = uuid.uuid4()
FILE_ID = uuid.uuid4()
JOB_ID = uuid.uuid4()
APPLICATION_ID = uuid.uuid4()
CANDIDATE_ID = uuid.uuid4()
HASH = "a" * 64
PATH = f"organisations/{ORG}/cv/{FILE_ID}/cv.pdf"
COST = Decimal("0.42")
NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)

TEXT = """\
منى عبد الله
القاهرة | mona@mail.test | 01001234567
محاسبة في شركة النيل للأدوية 2019 - حتى الآن
بكالوريوس تجارة جامعة القاهرة
المهارات: Excel
"""
OUTPUT: dict[str, Any] = {
    "name": "منى عبد الله",
    "emails": ["mona@mail.test"],
    "phones": ["+201001234567"],
    "location": "القاهرة",
    "years_of_experience": None,
    "employment": [
        {"employer": "شركة النيل للأدوية", "title": "محاسبة", "start": "2019", "end": "present"}
    ],
    "education": [
        {"institution": "جامعة القاهرة", "qualification": "بكالوريوس تجارة", "start": None,
         "end": None}
    ],
    "skills": ["Excel"],
    "languages": [],
    "certifications": [],
}  # fmt: skip


def message(**changes: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "job_type": CV_PROCESSING,
        "organisation_id": str(ORG),
        "cv_file_id": str(FILE_ID),
        "job_id": str(JOB_ID),
        "content_hash": HASH,
        "storage_path": PATH,
        "locale": "ar",
        "enqueued_at": "2026-10-04T12:00:00+00:00",
    } | changes


def received(body: Any, read_count: int = 1) -> ReceivedMessage:
    return ReceivedMessage(7, read_count, datetime(2026, 10, 4, tzinfo=UTC), body)


@dataclass
class FakeQueue:
    waiting: list[ReceivedMessage] = field(default_factory=list)
    deleted: list[int] = field(default_factory=list)
    archived: list[int] = field(default_factory=list)
    deferred: list[tuple[int, datetime]] = field(default_factory=list)
    reads: list[tuple[str, int, int]] = field(default_factory=list)

    def read(self, queue: str, *, visibility_seconds: int, quantity: int) -> list[ReceivedMessage]:
        self.reads.append((queue, visibility_seconds, quantity))
        batch, self.waiting = self.waiting[:quantity], self.waiting[quantity:]
        return batch

    def delete(self, queue: str, message_id: int) -> bool:
        self.deleted.append(message_id)
        return True

    def archive(self, queue: str, message_id: int) -> bool:
        self.archived.append(message_id)
        return True

    def defer(self, queue: str, message_id: int, until: datetime) -> None:
        self.deferred.append((message_id, until))


@dataclass
class FakeBudget:
    usage_now: BudgetUsage = field(default_factory=lambda: BudgetUsage(0, Decimal(0)))
    limits_now: Limits = field(default_factory=lambda: Limits(300, Decimal("750")))
    asked: list[tuple[uuid.UUID, datetime]] = field(default_factory=list)
    spent: list[Spend] = field(default_factory=list)

    def record(self, spend: Spend) -> None:
        self.spent.append(spend)

    def usage(self, organisation_id: uuid.UUID, since: datetime) -> BudgetUsage:
        self.asked.append((organisation_id, since))
        return self.usage_now

    def limits(self, organisation_id: uuid.UUID) -> Limits:
        return self.limits_now


@dataclass
class FakeStore:
    file: CvFile | None = field(
        default_factory=lambda: CvFile(FILE_ID, PATH, "application/pdf", HASH, "queued", None)
    )
    profile: StoredProfile | None = None
    status: str = "queued"
    failure: str | None = None
    review: Review | None = None
    extraction: Extraction | None = None
    applications: list[tuple[uuid.UUID, uuid.UUID]] = field(default_factory=list)
    organisations: set[uuid.UUID] = field(default_factory=set)
    cached: CachedProfile | None = None
    looked_up: list[tuple[str, uuid.UUID]] = field(default_factory=list)

    def profile_for_content(
        self, organisation_id: uuid.UUID, content_hash: str, other_than: uuid.UUID
    ) -> CachedProfile | None:
        self.organisations.add(organisation_id)
        self.looked_up.append((content_hash, other_than))
        return self.cached

    def cv_file(self, organisation_id: uuid.UUID, cv_file_id: uuid.UUID) -> CvFile | None:
        self.organisations.add(organisation_id)
        return self.file if cv_file_id == FILE_ID else None

    def current_profile(
        self, organisation_id: uuid.UUID, cv_file_id: uuid.UUID
    ) -> StoredProfile | None:
        self.organisations.add(organisation_id)
        return self.profile

    def mark_extracting(self, organisation_id: uuid.UUID, cv_file_id: uuid.UUID) -> None:
        self.organisations.add(organisation_id)
        self.status = "extracting"

    def record_extraction(
        self, organisation_id: uuid.UUID, cv_file_id: uuid.UUID, extraction: Extraction
    ) -> uuid.UUID:
        self.organisations.add(organisation_id)
        self.extraction, self.status = extraction, extraction.status
        self.review = extraction.review
        return CANDIDATE_ID

    def mark_needs_review(
        self, organisation_id: uuid.UUID, cv_file_id: uuid.UUID, review: Review
    ) -> None:
        self.organisations.add(organisation_id)
        self.status, self.review = "needs_review", review

    def mark_failed(self, organisation_id: uuid.UUID, cv_file_id: uuid.UUID, reason: str) -> None:
        self.organisations.add(organisation_id)
        self.status, self.failure = "failed", reason

    def ensure_application(
        self, organisation_id: uuid.UUID, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> uuid.UUID:
        self.organisations.add(organisation_id)
        self.applications.append((candidate_id, job_id))
        return APPLICATION_ID


@dataclass
class FakeFiles:
    content: bytes = b"%PDF-1.7 a CV"
    error: Exception | None = None

    def fetch(self, storage_path: str) -> bytes:
        if self.error is not None:
            raise self.error
        assert storage_path == PATH
        return self.content


@dataclass
class FakeModel:
    output: dict[str, Any] = field(default_factory=lambda: dict(OUTPUT))
    error: Exception | None = None
    calls: int = 0

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return StructuredResponse(
            output=self.output,
            identity=ModelIdentity("anthropic", "claude-haiku-4-5", request.prompt_version),
            usage=Usage(1000, 200),
            cost_egp=COST,
            payload=b"{}",
        )


OCR_COST = Decimal("0.30")
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass
class FakeOcr:
    text: str = TEXT
    error: Exception | None = None
    reads: list[tuple[bytes, str]] = field(default_factory=list)

    def read(self, content: bytes, media_type: str) -> OcrReading:
        self.reads.append((content, media_type))
        if self.error is not None:
            raise self.error
        return OcrReading(
            self.text,
            "vision_ocr",
            ModelIdentity("anthropic", "claude-haiku-4-5", "ocr/1"),
            OCR_COST,
        )


@dataclass
class FakeScorer:
    requests: list[ScoringRequest] = field(default_factory=list)
    error: Exception | None = None

    def __call__(self, request: ScoringRequest) -> None:
        if self.error is not None:
            raise self.error
        self.requests.append(request)


@dataclass
class Setup:
    queue: FakeQueue = field(default_factory=FakeQueue)
    store: FakeStore = field(default_factory=FakeStore)
    files: FakeFiles = field(default_factory=FakeFiles)
    model: FakeModel = field(default_factory=FakeModel)
    scorer: FakeScorer = field(default_factory=FakeScorer)
    budget: FakeBudget = field(default_factory=FakeBudget)
    ocr: FakeOcr | None = None
    text: str | Exception = TEXT

    def read_text(self, content: bytes) -> str:
        if isinstance(self.text, Exception):
            raise self.text
        return self.text

    @property
    def worker(self) -> Worker:
        return Worker(
            queue=self.queue,
            store=self.store,
            files=self.files,
            read_text=self.read_text,
            model=self.model,
            score=self.scorer,
            budget=self.budget,
            ocr=None if self.ocr is None else MeteredOcr(self.ocr, self.budget),
            clock=lambda: NOW,
        )

    def handle(self, body: Any = None, read_count: int = 1) -> Outcome:
        return self.worker.handle(
            CV_PROCESSING, received(message() if body is None else body, read_count)
        )


@pytest.fixture
def setup() -> Setup:
    return Setup()


class TestExtraction:
    def test_a_cv_is_extracted_recorded_and_its_message_deleted(self, setup: Setup) -> None:
        assert setup.handle() is Outcome.DONE
        extraction = setup.store.extraction
        assert extraction is not None
        assert (extraction.status, extraction.source) == ("extracted", "native_text")
        assert extraction.confidence == 1
        assert extraction.profile["name"] == "منى عبد الله"
        assert setup.queue.deleted == [7]
        assert setup.queue.archived == []

    def test_the_candidate_is_who_the_cv_describes(self, setup: Setup) -> None:
        setup.handle()
        assert setup.store.extraction is not None
        candidate = setup.store.extraction.candidate
        assert (candidate.full_name, candidate.email, candidate.phone, candidate.location) == (
            "منى عبد الله",
            "mona@mail.test",
            "+201001234567",
            "القاهرة",
        )
        assert candidate.name_normalised

    def test_every_operation_is_scoped_to_the_messages_organisation(self, setup: Setup) -> None:
        setup.handle()
        assert setup.store.organisations == {ORG}

    def test_a_profile_the_text_does_not_support_goes_to_review(self, setup: Setup) -> None:
        setup.model.output = OUTPUT | {"skills": ["Oracle", "SAP", "Python", "Java", "Go"]}
        assert setup.handle() is Outcome.DONE
        assert setup.store.status == "needs_review"
        assert setup.store.review == Review("low_confidence")
        assert setup.store.extraction is not None
        assert setup.store.extraction.confidence < Decimal("0.8")
        assert setup.scorer.requests == []


class TestSameContent:
    """AI-03: the same bytes uploaded again are not paid for again."""

    EARLIER = CachedProfile(
        cv_file_id=uuid.uuid4(),
        candidate_id=CANDIDATE_ID,
        source="native_text",
        confidence=Decimal("0.97"),
        profile=OUTPUT,
    )

    def test_a_profile_of_the_same_content_is_reused_without_a_model_call(
        self, setup: Setup
    ) -> None:
        setup.store.cached = self.EARLIER
        assert setup.handle() is Outcome.DONE
        assert setup.model.calls == 0
        assert setup.store.looked_up == [(HASH, FILE_ID)]
        extraction = setup.store.extraction
        assert extraction is not None
        assert (extraction.profile, extraction.confidence, extraction.status) == (
            OUTPUT,
            Decimal("0.97"),
            "extracted",
        )
        assert extraction.candidate_id == CANDIDATE_ID

    def test_the_reused_profile_is_scored_at_no_extraction_cost(self, setup: Setup) -> None:
        setup.store.cached = self.EARLIER
        setup.handle()
        [request] = setup.scorer.requests
        assert request.extraction_cost_egp == 0

    def test_a_doubtful_profile_stays_doubtful_when_reused(self, setup: Setup) -> None:
        setup.store.cached = CachedProfile(
            self.EARLIER.cv_file_id, None, "native_text", Decimal("0.5"), OUTPUT
        )
        setup.handle()
        assert setup.store.status == "needs_review"
        assert setup.store.review == Review("low_confidence")
        assert setup.scorer.requests == []

    def test_the_original_is_not_read_when_its_content_is_known(self, setup: Setup) -> None:
        setup.store.cached = self.EARLIER
        setup.files.error = AssertionError("the file should not be fetched")
        assert setup.handle() is Outcome.DONE


class TestReviewWithoutExtraction:
    def test_an_unsupported_language_is_not_sent_to_the_model(self, setup: Setup) -> None:
        setup.text = (
            "Je suis comptable avec dix ans d'expérience dans la gestion des comptes.\n" * 5
        )
        assert setup.handle() is Outcome.DONE
        assert setup.store.status == "needs_review"
        assert setup.store.review == Review("unsupported_language", "fr")
        assert setup.model.calls == 0
        assert setup.queue.deleted == [7]

    def test_a_document_without_text_waits_for_ocr_in_review(self, setup: Setup) -> None:
        setup.text = "   \n"
        assert setup.handle() is Outcome.DONE
        assert setup.store.status == "needs_review"
        assert setup.store.review == Review("no_text")
        assert setup.model.calls == 0

    def test_a_photograph_waits_for_ocr_in_review(self, setup: Setup) -> None:
        setup.store.file = CvFile(FILE_ID, PATH, "image/jpeg", HASH, "queued", None)
        setup.text = UnreadableDocumentError("not a PDF")
        assert setup.handle() is Outcome.DONE
        assert setup.store.status == "needs_review"
        assert setup.store.review == Review("no_text")
        assert setup.model.calls == 0


class TestOcr:
    """T076: a scan or a photograph is read by OCR when the worker has an engine (US2)."""

    PHOTO = CvFile(FILE_ID, PATH, "image/jpeg", HASH, "queued", None)

    def test_a_photograph_is_read_by_ocr_and_extracted(self, setup: Setup) -> None:
        setup.ocr, setup.store.file = FakeOcr(), self.PHOTO
        setup.files.content = b"\xff\xd8\xff a photo"
        setup.text = AssertionError("a photograph has no text layer to read")
        assert setup.handle() is Outcome.DONE
        assert setup.ocr.reads == [(b"\xff\xd8\xff a photo", "image/jpeg")]
        extraction = setup.store.extraction
        assert extraction is not None
        assert (extraction.status, extraction.source) == ("extracted", "vision_ocr")
        assert extraction.profile["name"] == "منى عبد الله"

    def test_a_pdf_without_a_text_layer_is_read_by_ocr(self, setup: Setup) -> None:
        setup.ocr, setup.text = FakeOcr(), "  \n"
        assert setup.handle() is Outcome.DONE
        assert setup.ocr.reads == [(b"%PDF-1.7 a CV", "application/pdf")]
        assert setup.store.extraction is not None
        assert setup.store.extraction.source == "vision_ocr"

    def test_a_scan_whose_only_text_is_a_watermark_is_read_by_ocr(self, setup: Setup) -> None:
        setup.ocr, setup.text = FakeOcr(), "Scanned by CamScanner"
        assert setup.handle() is Outcome.DONE
        assert setup.ocr.reads == [(b"%PDF-1.7 a CV", "application/pdf")]
        assert setup.store.extraction is not None
        assert setup.store.extraction.source == "vision_ocr"

    def test_a_file_type_ocr_cannot_read_is_not_fetched(self, setup: Setup) -> None:
        setup.ocr = FakeOcr()
        setup.store.file = CvFile(FILE_ID, PATH, "image/webp", HASH, "queued", None)
        setup.files.error = AssertionError("the file should not be fetched")
        assert setup.handle() is Outcome.DONE
        assert setup.store.review == Review("no_text")

    def test_a_pdf_with_a_text_layer_is_not_sent_to_ocr(self, setup: Setup) -> None:
        # A CV's length of text: the shortest native one in the corpus has 487 letters.
        setup.ocr, setup.text = FakeOcr(), TEXT * 3
        setup.handle()
        assert setup.ocr.reads == []
        assert setup.store.extraction is not None
        assert setup.store.extraction.source == "native_text"

    def test_a_word_document_without_text_is_not_sent_to_ocr(self, setup: Setup) -> None:
        setup.ocr, setup.text = FakeOcr(), ""
        setup.store.file = CvFile(FILE_ID, PATH, DOCX, HASH, "queued", None)
        setup.handle()
        assert setup.ocr.reads == []
        assert setup.store.review == Review("no_text")

    def test_ocr_that_finds_nothing_sends_the_file_to_review(self, setup: Setup) -> None:
        setup.ocr, setup.store.file = FakeOcr(text=" \n "), self.PHOTO
        assert setup.handle() is Outcome.DONE
        assert setup.store.review == Review("no_text")
        assert setup.model.calls == 0

    def test_an_unsupported_language_read_by_ocr_goes_to_review(self, setup: Setup) -> None:
        french = "Je suis comptable avec dix ans d'expérience dans la gestion des comptes.\n" * 5
        setup.ocr, setup.store.file = FakeOcr(text=french), self.PHOTO
        setup.handle()
        assert setup.store.review == Review("unsupported_language", "fr")
        assert setup.model.calls == 0

    def test_the_ocr_cost_is_part_of_the_extraction_cost(self, setup: Setup) -> None:
        setup.ocr, setup.store.file = FakeOcr(), self.PHOTO
        setup.handle()
        [request] = setup.scorer.requests
        assert request.extraction_cost_egp == COST + OCR_COST

    def test_the_ocr_reading_is_charged_to_the_organisation(self, setup: Setup) -> None:
        setup.ocr, setup.store.file = FakeOcr(), self.PHOTO
        setup.handle()
        assert (ORG, FILE_ID, "extraction", OCR_COST) in [
            (spend.organisation_id, spend.cv_file_id, spend.kind, spend.cost_egp)
            for spend in setup.budget.spent
        ]

    def test_ocr_that_finds_no_more_than_the_pdf_keeps_its_own_text(self, setup: Setup) -> None:
        setup.ocr, setup.text = FakeOcr(text="Scanned"), TEXT
        setup.handle()
        assert setup.ocr.reads != []
        assert setup.store.extraction is not None
        assert setup.store.extraction.source == "native_text"

    def test_a_transient_ocr_failure_leaves_the_message_to_retry(self, setup: Setup) -> None:
        setup.store.file = self.PHOTO
        setup.ocr = FakeOcr(error=ProviderUnavailableError("outage"))
        assert setup.handle() is Outcome.LEFT
        assert setup.store.failure is None

    def test_a_refused_ocr_read_fails_the_file(self, setup: Setup) -> None:
        setup.store.file = self.PHOTO
        setup.ocr = FakeOcr(error=RefusedError("declined"))
        assert setup.handle() is Outcome.ARCHIVED
        assert setup.store.failure is not None
        assert "declined" in setup.store.failure

    def test_an_image_the_engine_cannot_open_fails_the_file(self, setup: Setup) -> None:
        setup.store.file = self.PHOTO
        setup.ocr = FakeOcr(error=UnreadableDocumentError("not an image"))
        assert setup.handle() is Outcome.ARCHIVED
        assert setup.store.failure is not None
        assert "not an image" in setup.store.failure


class TestScoring:
    def test_a_cv_uploaded_against_a_job_is_scored_with_its_extraction_cost(
        self, setup: Setup
    ) -> None:
        setup.handle()
        assert setup.store.applications == [(CANDIDATE_ID, JOB_ID)]
        [request] = setup.scorer.requests
        assert (request.organisation_id, request.application_id, request.job_id) == (
            ORG,
            APPLICATION_ID,
            JOB_ID,
        )
        assert isinstance(request.profile, Profile)
        assert (request.locale, request.extraction_cost_egp) == ("ar", COST)

    def test_a_cv_uploaded_without_a_job_is_only_extracted(self, setup: Setup) -> None:
        assert setup.handle(message(job_id=None)) is Outcome.DONE
        assert setup.scorer.requests == []
        assert setup.store.applications == []

    def test_a_failed_score_leaves_the_message_to_retry(self, setup: Setup) -> None:
        setup.scorer.error = RateLimitedError("slow down")
        assert setup.handle() is Outcome.LEFT
        assert setup.queue.deleted == []


class TestRetries:
    def test_a_transient_model_failure_leaves_the_message(self, setup: Setup) -> None:
        setup.model.error = RateLimitedError("slow down")
        assert setup.handle() is Outcome.LEFT
        assert setup.store.status == "extracting"
        assert setup.store.failure is None
        assert (setup.queue.deleted, setup.queue.archived) == ([], [])

    def test_an_unreachable_file_store_leaves_the_message(self, setup: Setup) -> None:
        setup.files.error = CvStoreUnavailableError("timeout")
        assert setup.handle() is Outcome.LEFT
        assert setup.store.failure is None

    def test_an_unexpected_error_leaves_the_message_and_is_logged(
        self, setup: Setup, caplog: pytest.LogCaptureFixture
    ) -> None:
        setup.text = RuntimeError("a bug")
        with caplog.at_level(logging.ERROR):
            assert setup.handle() is Outcome.LEFT
        assert "a bug" in caplog.text

    def test_failure_lines_name_the_tenant(self, setup: Setup) -> None:
        """T031: a retry's and a terminal failure's log lines carry the organisation and file, so
        one tenant's failures can be found."""
        seen: list[tuple[uuid.UUID, uuid.UUID] | None] = []

        class Seeing(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                seen.append(current_work())

        handler = Seeing(level=logging.ERROR)
        logging.getLogger("masirah.worker").addHandler(handler)
        try:
            setup.text = RuntimeError("a bug")
            setup.handle()
            setup.handle(read_count=MAX_ATTEMPTS + 1)
        finally:
            logging.getLogger("masirah.worker").removeHandler(handler)
        assert len(seen) == 2
        assert all(work == (ORG, FILE_ID) for work in seen)
        assert current_work() is None

    def test_a_retry_after_the_profile_was_recorded_does_not_extract_again(
        self, setup: Setup
    ) -> None:
        """Obligation 1: a second run of a message must not create a second profile."""
        setup.store.file = CvFile(FILE_ID, PATH, "application/pdf", HASH, "extracted", CANDIDATE_ID)
        setup.store.profile = StoredProfile(1, Decimal("0.95"), OUTPUT)
        assert setup.handle() is Outcome.DONE
        assert setup.model.calls == 0
        assert setup.store.extraction is None
        [request] = setup.scorer.requests
        assert request.extraction_cost_egp == 0

    def test_a_file_already_in_review_is_not_scored_on_retry(self, setup: Setup) -> None:
        setup.store.file = CvFile(FILE_ID, PATH, "application/pdf", HASH, "needs_review", None)
        assert setup.handle() is Outcome.DONE
        assert setup.model.calls == 0
        assert setup.scorer.requests == []


class TestTerminalFailure:
    def test_after_the_last_attempt_the_file_fails_and_the_message_is_archived(
        self, setup: Setup
    ) -> None:
        assert setup.handle(read_count=MAX_ATTEMPTS + 1) is Outcome.ARCHIVED
        assert setup.store.status == "failed"
        assert setup.store.failure is not None
        assert str(MAX_ATTEMPTS) in setup.store.failure
        assert setup.model.calls == 0
        assert setup.queue.archived == [7]

    def test_scoring_that_keeps_failing_does_not_fail_an_extracted_file(
        self, setup: Setup, caplog: pytest.LogCaptureFixture
    ) -> None:
        setup.store.file = CvFile(FILE_ID, PATH, "application/pdf", HASH, "extracted", CANDIDATE_ID)
        setup.store.status = "extracted"
        with caplog.at_level(logging.ERROR):
            assert setup.handle(read_count=MAX_ATTEMPTS + 1) is Outcome.ARCHIVED
        assert (setup.store.status, setup.store.failure) == ("extracted", None)
        assert caplog.records

    def test_the_last_attempt_is_still_made(self, setup: Setup) -> None:
        assert setup.handle(read_count=MAX_ATTEMPTS) is Outcome.DONE

    def test_an_unreadable_file_fails_at_once(self, setup: Setup) -> None:
        setup.text = UnreadableDocumentError("the PDF is encrypted")
        assert setup.handle() is Outcome.ARCHIVED
        assert setup.store.status == "failed"
        assert setup.store.failure is not None
        assert "encrypted" in setup.store.failure
        assert setup.model.calls == 0

    def test_a_missing_original_fails_at_once(self, setup: Setup) -> None:
        setup.files.error = MissingCvError(PATH)
        assert setup.handle() is Outcome.ARCHIVED
        assert setup.store.status == "failed"

    def test_a_refusal_fails_at_once(self, setup: Setup) -> None:
        setup.model.error = RefusedError("declined")
        assert setup.handle() is Outcome.ARCHIVED
        assert setup.store.status == "failed"

    def test_a_file_whose_bytes_changed_fails(self, setup: Setup) -> None:
        setup.store.file = CvFile(FILE_ID, PATH, "application/pdf", "b" * 64, "queued", None)
        assert setup.handle() is Outcome.ARCHIVED
        assert setup.store.status == "failed"
        assert setup.model.calls == 0

    def test_a_message_naming_another_object_than_the_files_fails(self, setup: Setup) -> None:
        """The file read is always the row's own: another object in the folder is never read."""
        other = PATH.replace("cv.pdf", "other.pdf")
        assert setup.handle(message(storage_path=other)) is Outcome.ARCHIVED
        assert setup.store.status == "failed"
        assert setup.model.calls == 0

    def test_a_message_for_a_file_that_does_not_exist_is_archived_and_alerted(
        self, setup: Setup, caplog: pytest.LogCaptureFixture
    ) -> None:
        gone = uuid.uuid4()
        body = message(cv_file_id=str(gone), storage_path=f"organisations/{ORG}/cv/{gone}/cv.pdf")
        with caplog.at_level(logging.ERROR):
            outcome = setup.handle(body)
        assert outcome is Outcome.ARCHIVED
        assert caplog.records


class TestRefusedMessages:
    @pytest.mark.parametrize(
        "body",
        [
            message(schema_version=2),
            message(locale="fr"),
            "not an object",
            {
                "schema_version": 1,
                "job_type": "cv_rescoring",
                "organisation_id": str(ORG),
                "application_id": str(APPLICATION_ID),
                "weights_hash": "b" * 64,
                "locale": "en",
                "enqueued_at": "2026-10-04T12:00:00+00:00",
            },
        ],
        ids=["unknown-version", "malformed", "not-json-object", "rescoring-has-no-producer-yet"],
    )
    def test_a_message_the_worker_cannot_handle_stays_and_raises_an_alert(
        self, setup: Setup, body: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.ERROR):
            assert setup.handle(body) is Outcome.LEFT
        assert caplog.records
        assert "message 7 " in caplog.text
        assert (setup.queue.deleted, setup.queue.archived) == ([], [])
        assert setup.store.organisations == set()


class TestRunOnce:
    def test_it_reads_a_batch_and_handles_every_message(self, setup: Setup) -> None:
        setup.queue.waiting = [received(message()), received("broken")]
        assert setup.worker.run_once() == 2
        [(queue, visibility, quantity)] = setup.queue.reads
        assert queue == CV_PROCESSING
        assert visibility > 0
        assert quantity >= 1
        assert setup.queue.deleted == [7]

    def test_an_empty_queue_handles_nothing(self, setup: Setup) -> None:
        assert setup.worker.run_once() == 0

    def test_a_failing_heartbeat_never_stops_the_work(
        self, setup: Setup, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The heartbeat only reports on the work; losing it must not leave a batch unhandled."""

        def broken() -> None:
            raise RuntimeError("heartbeat table unreachable")

        worker = setup.worker
        worker.beat = broken
        setup.queue.waiting = [received(message())]
        with caplog.at_level(logging.ERROR):
            assert worker.run_once() == 1
        assert setup.queue.deleted == [7]
        assert "heartbeat" in caplog.text

    def test_the_worker_beats_before_a_batch_and_after_every_message(self, setup: Setup) -> None:
        """T030: a long batch still shows the worker alive."""
        beats: list[int] = []
        worker = setup.worker
        worker.beat = lambda: beats.append(1)
        setup.queue.waiting = [received(message()), received("broken")]
        worker.run_once()
        assert len(beats) == 3


class TestBudget:
    """AI-06, FR-026: an organisation at its limit waits for next month, at no further cost."""

    def test_an_organisation_at_its_spend_ceiling_waits_for_next_month(self, setup: Setup) -> None:
        setup.budget.usage_now = BudgetUsage(12, Decimal("750"))
        assert setup.handle() is Outcome.DEFERRED
        assert setup.queue.deferred == [(7, next_month_start(NOW))]
        assert setup.model.calls == 0
        assert setup.store.status == "queued"
        assert (setup.queue.deleted, setup.queue.archived) == ([], [])

    def test_an_organisation_at_its_cv_limit_waits_too(self, setup: Setup) -> None:
        setup.budget.usage_now = BudgetUsage(300, Decimal("10"))
        assert setup.handle() is Outcome.DEFERRED
        assert setup.model.calls == 0

    def test_usage_is_counted_from_the_start_of_the_month(self, setup: Setup) -> None:
        assert setup.handle() is Outcome.DONE
        assert setup.budget.asked == [(ORG, datetime(2026, 9, 30, 21, 0, tzinfo=UTC))]

    def test_model_calls_are_charged_to_the_cv_they_are_for(self, setup: Setup) -> None:
        metered = MeteredModel(setup.model, "extraction", setup.budget)
        worker = setup.worker
        worker.model = metered
        worker.handle(CV_PROCESSING, received(message()))
        assert [
            (spend.organisation_id, spend.cv_file_id, spend.cost_egp)
            for spend in setup.budget.spent
        ] == [(ORG, FILE_ID, COST)]
