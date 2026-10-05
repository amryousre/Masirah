"""The worker process: configuration and the polling loop (T057).

The worker runs as `python -m masirah_pipeline` on its host. It refuses to start with a setting
missing rather than failing on the first message, polls without pause while there is work, and
waits between polls when the queue is empty. A stop request from the host ends it between
batches, never in the middle of a message.
"""

import socket
import threading
from collections.abc import Callable

import pytest

from masirah_pipeline.adapters.provider_registry import ConfigurationError
from masirah_pipeline.main import (
    IDLE_SECONDS,
    PURGE_SECONDS,
    RECONCILE_SECONDS,
    REQUIRED,
    Purging,
    Reconciling,
    poll,
    settings_from,
    worker_name,
)

COMPLETE = {
    "MASIRAH_DATABASE_URL": "postgresql://masirah_worker:secret@db.example.test:5432/postgres",
    "SUPABASE_URL": "https://project.supabase.co",
    "SUPABASE_SECRET_KEY": "sb_secret_example",
}


def test_complete_settings_are_read() -> None:
    settings = settings_from(COMPLETE)
    assert settings.supabase_url == "https://project.supabase.co"


@pytest.mark.parametrize("missing", REQUIRED)
def test_a_missing_setting_stops_the_worker_from_starting(missing: str) -> None:
    environment = {name: value for name, value in COMPLETE.items() if name != missing}
    with pytest.raises(ConfigurationError, match=missing):
        settings_from(environment)


def test_an_error_names_the_setting_but_never_its_value() -> None:
    with pytest.raises(ConfigurationError) as raised:
        settings_from(COMPLETE | {"SUPABASE_URL": ""})
    assert "sb_secret_example" not in str(raised.value)


def test_it_polls_again_at_once_while_there_is_work_and_waits_when_idle() -> None:
    stop = threading.Event()
    batches = iter([5, 2, 0])
    waits: list[float] = []

    def run_once() -> int:
        handled = next(batches)
        if handled == 0:
            stop.set()
        return handled

    def wait(seconds: float) -> bool:
        waits.append(seconds)
        return stop.is_set()

    poll(run_once, stop, wait)
    assert waits == [IDLE_SECONDS]


def test_a_stop_request_ends_the_loop_before_the_next_batch() -> None:
    stop = threading.Event()
    stop.set()
    calls: list[int] = []

    def run_once() -> int:
        calls.append(1)
        return 1

    poll(run_once, stop, lambda seconds: True)
    assert calls == []


def test_the_heartbeat_name_is_configured_or_the_hosts() -> None:
    assert worker_name({"MASIRAH_WORKER_NAME": "render-1"}) == "render-1"
    assert worker_name({}) == socket.gethostname()


class TestReconciling:
    """Every few minutes the worker queues again any file stranded without a message (SC-006)."""

    def test_it_reconciles_at_start_and_then_once_per_interval(self) -> None:
        now = [0.0]
        calls: list[float] = []

        def reconcile() -> int:
            calls.append(now[0])
            return 0

        reconciling = Reconciling(lambda: 1, reconcile, clock=lambda: now[0])
        for moment in (0.0, 10.0, RECONCILE_SECONDS - 1, RECONCILE_SECONDS, RECONCILE_SECONDS + 5):
            now[0] = moment
            assert reconciling() == 1
        assert calls == [0.0, RECONCILE_SECONDS]

    def test_a_failed_reconciliation_never_stops_the_work(self) -> None:
        def broken() -> int:
            raise RuntimeError("database unreachable")

        reconciling = Reconciling(lambda: 3, broken, clock=lambda: 0.0)
        assert reconciling() == 3


class TestPurging:
    """Every hour the worker sweeps for personal data due to go (T100, T101)."""

    def test_it_sweeps_at_start_and_then_once_an_hour(self) -> None:
        now = [0.0]
        sweeps: list[float] = []

        def sweep() -> int:
            sweeps.append(now[0])
            return 0

        purging = Purging(lambda: 1, sweep, clock=lambda: now[0])
        for moment in (0.0, 60.0, PURGE_SECONDS - 1, PURGE_SECONDS):
            now[0] = moment
            assert purging() == 1
        assert sweeps == [0.0, PURGE_SECONDS]

    def test_a_failed_sweep_never_stops_the_work(self) -> None:
        def broken() -> int:
            raise RuntimeError("database unreachable")

        assert Purging(lambda: 2, broken, clock=lambda: 0.0)() == 2

    def test_it_runs_beside_reconciliation(self) -> None:
        calls: list[str] = []

        def step(name: str, result: int) -> Callable[[], int]:
            def run() -> int:
                calls.append(name)
                return result

            return run

        both = Purging(Reconciling(step("batch", 1), step("requeue", 0)), step("purge", 0))
        assert both() == 1
        assert calls == ["purge", "requeue", "batch"]
