"""The worker process, `python -m masirah_pipeline` (T057).

This is the composition root: the one place that picks the adapters behind every port. It reads
its settings from the environment and refuses to start with one missing:

- MASIRAH_DATABASE_URL: Postgres as the masirah_worker role, whose login an operator grants where
  the worker is deployed (migration 0013). Never the service role.
- SUPABASE_URL and SUPABASE_SECRET_KEY: for reading original files from Storage, and only that.
- MASIRAH_CHEAP_MODEL, MASIRAH_STRONG_MODEL, MASIRAH_EGP_PER_USD and a provider key per tier, as
  adapters/provider_registry.py reads them.

Scans and photographs are read by the OCR engine MASIRAH_OCR names (T078): "tesseract", with
MASIRAH_TESSERACT_CMD and MASIRAH_TESSDATA_DIR where they are not the defaults. Without it they go
to the review queue unread.

Each worker records a heartbeat under MASIRAH_WORKER_NAME, or the host's name, which /api/health
reads (T030).

Logs are JSON lines, and errors go to Sentry when SENTRY_DSN is set (T031). Every hour the worker
checks the parse failure rate (NFR-14) and posts to Slack when MASIRAH_SLACK_WEBHOOK_URL is set.

The loop polls again at once while messages arrive and waits IDLE_SECONDS when the queue is
empty. SIGTERM, which a host sends before stopping a process, ends it between batches.
"""

import contextlib
import logging
import os
import signal
import socket
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import psycopg

from masirah_pipeline.adapters.heartbeat import PostgresHeartbeat
from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.adapters.postgres_parse_outcomes import PostgresParseOutcomes
from masirah_pipeline.adapters.postgres_purge_store import PostgresPurgeStore
from masirah_pipeline.adapters.postgres_spend_ledger import PostgresSpendLedger
from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.adapters.provider_registry import ConfigurationError, model_for
from masirah_pipeline.adapters.score_repository import PostgresScoreRepository
from masirah_pipeline.adapters.slack_webhook import SlackWebhook
from masirah_pipeline.adapters.supabase_queue import SupabaseQueue
from masirah_pipeline.adapters.supabase_storage import SupabaseStorage
from masirah_pipeline.adapters.telemetry import configure as configure_telemetry
from masirah_pipeline.adapters.tesseract_ocr import LANGUAGE_DATA, Runner, TesseractOcr
from masirah_pipeline.adapters.tesseract_ocr import run as run_process
from masirah_pipeline.jobs.parse_failures import check_parse_failures
from masirah_pipeline.jobs.purge import purge_due
from masirah_pipeline.metering import MeteredModel, MeteredOcr
from masirah_pipeline.ports.document_text import UnreadableDocumentError
from masirah_pipeline.ports.model_provider import ModelProviderError
from masirah_pipeline.scoring_step import ApplicationScorer
from masirah_pipeline.worker import Worker

log = logging.getLogger("masirah.worker")

REQUIRED = ("MASIRAH_DATABASE_URL", "SUPABASE_URL", "SUPABASE_SECRET_KEY")
IDLE_SECONDS = 5.0
# How often stranded files are queued again, and how old a queued file must be to count as one.
RECONCILE_SECONDS = 5 * 60.0
PURGE_SECONDS = 60 * 60.0
PARSE_CHECK_SECONDS = 60 * 60.0
STRANDED_AFTER_SECONDS = 10 * 60


@dataclass(frozen=True)
class Settings:
    database_url: str
    supabase_url: str
    supabase_secret_key: str


def settings_from(environment: Mapping[str, str]) -> Settings:
    missing = [name for name in REQUIRED if not environment.get(name, "").strip()]
    if missing:
        raise ConfigurationError(f"the worker needs {', '.join(missing)}")
    return Settings(*(environment[name] for name in REQUIRED))


def worker_name(environment: Mapping[str, str]) -> str:
    """The name the heartbeat is recorded under: MASIRAH_WORKER_NAME, or the host's name."""
    return environment.get("MASIRAH_WORKER_NAME", "").strip() or socket.gethostname()


class Every:
    """Runs a batch, and before it, at most once per `every` seconds, a housekeeping task. A failed
    task is logged; the batch runs regardless, so housekeeping can never stop the processing."""

    def __init__(
        self,
        run_once: Callable[[], int],
        task: Callable[[], int],
        every: float,
        describe: str,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._run_once, self._task, self._every = run_once, task, every
        self._describe, self._clock = describe, clock
        self._last: float | None = None

    def __call__(self) -> int:
        now = self._clock()
        if self._last is None or now - self._last >= self._every:
            self._last = now
            try:
                done = self._task()
            except Exception:
                log.exception("%s failed; processing continues", self._describe)
            else:
                if done:
                    log.warning("%s: %s", self._describe, done)
        return self._run_once()


def Reconciling(  # noqa: N802 - reads as the wrapper it returns
    run_once: Callable[[], int],
    reconcile: Callable[[], int],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> Every:
    """Queues again any file left queued without a message (migration 0018), at most once per
    RECONCILE_SECONDS, so no upload waits for ever (SC-006)."""
    return Every(run_once, reconcile, RECONCILE_SECONDS, "stranded files queued again", clock=clock)


def Purging(  # noqa: N802 - reads as the wrapper it returns
    run_once: Callable[[], int],
    sweep: Callable[[], int],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> Every:
    """Removes personal data due to go, on request or past retention (migration 0022), at most
    once per PURGE_SECONDS: a request is met within the hour, well inside FR-076's 30 days."""
    return Every(run_once, sweep, PURGE_SECONDS, "candidates purged", clock=clock)


def Watching(  # noqa: N802 - reads as the wrapper it returns
    run_once: Callable[[], int],
    check: Callable[[], int],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> Every:
    """Checks the past hour's parse failure rate once per PARSE_CHECK_SECONDS (NFR-14), so a
    sustained fault alerts once an hour rather than on every batch."""
    return Every(run_once, check, PARSE_CHECK_SECONDS, "parse failure alerts raised", clock=clock)


def alerts_for(environment: Mapping[str, str]) -> SlackWebhook | None:
    """Slack through MASIRAH_SLACK_WEBHOOK_URL, or None: the alert is then only logged, which
    error tracking still picks up."""
    url = environment.get("MASIRAH_SLACK_WEBHOOK_URL", "").strip()
    return SlackWebhook(url) if url else None


def ocr_for(environment: Mapping[str, str], run: Runner = run_process) -> TesseractOcr | None:
    """The OCR engine MASIRAH_OCR names, checked to run with all the language data its readings
    use, or None for none. A worker that cannot read a scan refuses to start rather than failing
    every scan it is given."""
    engine = environment.get("MASIRAH_OCR", "").strip()
    if not engine:
        return None
    if engine != "tesseract":
        raise ConfigurationError(f"MASIRAH_OCR names no engine this worker has: {engine!r}")
    ocr = TesseractOcr(
        command=environment.get("MASIRAH_TESSERACT_CMD", "").strip() or "tesseract",
        tessdata=environment.get("MASIRAH_TESSDATA_DIR", "").strip() or None,
        run=run,
    )
    try:
        available = ocr.available_languages()
    except (ModelProviderError, UnreadableDocumentError) as error:
        raise ConfigurationError(f"Tesseract is not usable: {error}") from error
    missing = [language for language in LANGUAGE_DATA if language not in available]
    if missing:
        raise ConfigurationError(
            f"Tesseract has no {', '.join(missing)} language data (.traineddata); "
            "Arabic, English and orientation data are all needed"
        )
    return ocr


def poll(run_once: Callable[[], int], stop: threading.Event, wait: Callable[[float], bool]) -> None:
    """Run batches until stopped, waiting only when a batch found nothing to do."""
    while not stop.is_set():
        if run_once() == 0 and wait(IDLE_SECONDS):
            return


def main(environment: Mapping[str, str] = os.environ) -> None:
    configure_telemetry(environment)
    settings = settings_from(environment)
    cheap, strong = model_for("cheap", environment), model_for("strong", environment)
    ocr = ocr_for(environment)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    # Autocommit: each store operation opens its own transaction, and a read's visibility
    # timeout takes effect at once rather than when some later statement commits.
    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        storage = SupabaseStorage(settings.supabase_url, settings.supabase_secret_key)
        # Every model call is recorded with its cost as it is made, and the month's spend halts
        # an organisation's processing at its ceiling (T093, AI-06).
        ledger = PostgresSpendLedger(connection)
        worker = Worker(
            queue=SupabaseQueue(connection),
            store=PostgresWorkerStore(connection),
            files=storage,
            read_text=read_native_text,
            model=MeteredModel(cheap, "extraction", ledger),
            score=ApplicationScorer(
                PostgresScoreRepository(connection),
                MeteredModel(strong, "scoring", ledger),
                MeteredModel(cheap, "summary", ledger),
            ),
            budget=ledger,
            beat=PostgresHeartbeat(connection, worker_name(environment)),
            ocr=None if ocr is None else MeteredOcr(ocr, ledger),
        )
        log.info("worker started")

        def requeue_stranded() -> int:
            row = connection.execute(
                "select worker.requeue_stranded(%s)", (STRANDED_AFTER_SECONDS,)
            ).fetchone()
            return int(row[0]) if row else 0

        with contextlib.suppress(KeyboardInterrupt):
            purge_store = PostgresPurgeStore(connection)
            outcomes, alerts = PostgresParseOutcomes(connection), alerts_for(environment)
            batch = Reconciling(worker.run_once, requeue_stranded)
            batch = Watching(batch, lambda: check_parse_failures(outcomes, alerts))
            poll(Purging(batch, lambda: purge_due(purge_store, storage)), stop, stop.wait)
        log.info("worker stopped")
