"""The worker process, `python -m masirah_pipeline` (T057).

This is the composition root: the one place that picks the adapters behind every port. It reads
its settings from the environment and refuses to start with one missing:

- MASIRAH_DATABASE_URL: Postgres as the masirah_worker role, whose login an operator grants where
  the worker is deployed (migration 0013). Never the service role.
- SUPABASE_URL and SUPABASE_SECRET_KEY: for reading original files from Storage, and only that.
- MASIRAH_CHEAP_MODEL, MASIRAH_STRONG_MODEL, MASIRAH_EGP_PER_USD and a provider key per tier, as
  adapters/provider_registry.py reads them.

Each worker records a heartbeat under MASIRAH_WORKER_NAME, or the host's name, which /api/health
reads (T030).

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
from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.adapters.provider_registry import ConfigurationError, model_for
from masirah_pipeline.adapters.score_repository import PostgresScoreRepository
from masirah_pipeline.adapters.supabase_queue import SupabaseQueue
from masirah_pipeline.adapters.supabase_storage import SupabaseStorage
from masirah_pipeline.scoring_step import ApplicationScorer
from masirah_pipeline.worker import Worker

log = logging.getLogger("masirah.worker")

REQUIRED = ("MASIRAH_DATABASE_URL", "SUPABASE_URL", "SUPABASE_SECRET_KEY")
IDLE_SECONDS = 5.0
# How often stranded files are queued again, and how old a queued file must be to count as one.
RECONCILE_SECONDS = 5 * 60.0
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


class Reconciling:
    """Runs a batch, and before it, at most once per RECONCILE_SECONDS, queues again any file left
    queued without a message (migration 0018), so no upload waits for ever (SC-006). A failed
    reconciliation is logged; the batch runs regardless."""

    def __init__(
        self,
        run_once: Callable[[], int],
        reconcile: Callable[[], int],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._run_once, self._reconcile, self._clock = run_once, reconcile, clock
        self._last: float | None = None

    def __call__(self) -> int:
        now = self._clock()
        if self._last is None or now - self._last >= RECONCILE_SECONDS:
            self._last = now
            try:
                requeued = self._reconcile()
            except Exception:
                log.exception("stranded files could not be reconciled; processing continues")
            else:
                if requeued:
                    log.warning("queued %s stranded files again", requeued)
        return self._run_once()


def poll(run_once: Callable[[], int], stop: threading.Event, wait: Callable[[float], bool]) -> None:
    """Run batches until stopped, waiting only when a batch found nothing to do."""
    while not stop.is_set():
        if run_once() == 0 and wait(IDLE_SECONDS):
            return


def main(environment: Mapping[str, str] = os.environ) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = settings_from(environment)
    cheap, strong = model_for("cheap", environment), model_for("strong", environment)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    # Autocommit: each store operation opens its own transaction, and a read's visibility
    # timeout takes effect at once rather than when some later statement commits.
    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        worker = Worker(
            queue=SupabaseQueue(connection),
            store=PostgresWorkerStore(connection),
            files=SupabaseStorage(settings.supabase_url, settings.supabase_secret_key),
            read_text=read_native_text,
            model=cheap,
            score=ApplicationScorer(PostgresScoreRepository(connection), strong, cheap),
            beat=PostgresHeartbeat(connection, worker_name(environment)),
        )
        log.info("worker started")

        def requeue_stranded() -> int:
            row = connection.execute(
                "select worker.requeue_stranded(%s)", (STRANDED_AFTER_SECONDS,)
            ).fetchone()
            return int(row[0]) if row else 0

        with contextlib.suppress(KeyboardInterrupt):
            poll(Reconciling(worker.run_once, requeue_stranded), stop, stop.wait)
        log.info("worker stopped")
