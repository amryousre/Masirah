"""The worker process: configuration and the polling loop (T057).

The worker runs as `python -m masirah_pipeline` on its host. It refuses to start with a setting
missing rather than failing on the first message, polls without pause while there is work, and
waits between polls when the queue is empty. A stop request from the host ends it between
batches, never in the middle of a message.
"""

import socket
import subprocess
import threading
from collections.abc import Callable

import pytest

from masirah_pipeline.adapters.provider_registry import ConfigurationError
from masirah_pipeline.adapters.slack_webhook import SlackWebhook
from masirah_pipeline.adapters.tesseract_ocr import Runner
from masirah_pipeline.main import (
    IDLE_SECONDS,
    PARSE_CHECK_SECONDS,
    PURGE_SECONDS,
    RECONCILE_SECONDS,
    REQUIRED,
    Purging,
    Reconciling,
    Watching,
    alerts_for,
    ocr_for,
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


class TestOcrSetting:
    """MASIRAH_OCR picks the engine that reads scans and photographs (T078). The worker checks it
    can run before taking any work, so a missing install fails at start, not on the first scan."""

    @staticmethod
    def tesseract(
        languages: tuple[str, ...] = ("ara", "eng", "osd"), error: Exception | None = None
    ) -> Runner:
        def run(args: list[str], stdin: bytes, timeout: float) -> tuple[int, bytes, bytes]:
            if error is not None:
                raise error
            assert "--list-langs" in args
            listing = "\n".join(['List of available languages in "/tessdata/" (3):', *languages])
            return 0, listing.encode(), b""

        return run

    def test_without_the_setting_there_is_no_ocr(self) -> None:
        assert ocr_for({}, run=self.tesseract()) is None

    def test_tesseract_is_configured_with_its_command_and_data(self) -> None:
        engine = ocr_for(
            {
                "MASIRAH_OCR": "tesseract",
                "MASIRAH_TESSERACT_CMD": "/usr/bin/tesseract",
                "MASIRAH_TESSDATA_DIR": "/usr/share/tessdata",
            },
            run=self.tesseract(),
        )
        assert engine is not None
        assert (engine.command, engine.tessdata) == ("/usr/bin/tesseract", "/usr/share/tessdata")

    @pytest.mark.parametrize(
        "error",
        [
            FileNotFoundError("tesseract"),
            PermissionError("tesseract"),
            subprocess.TimeoutExpired("tesseract", 30),
        ],
        ids=["not-installed", "not-executable", "hangs"],
    )
    def test_a_tesseract_that_cannot_run_stops_the_worker(self, error: Exception) -> None:
        with pytest.raises(ConfigurationError, match="not usable"):
            ocr_for({"MASIRAH_OCR": "tesseract"}, run=self.tesseract(error=error))

    @pytest.mark.parametrize(
        ("languages", "missing"),
        [(("eng", "osd"), "ara"), (("ara", "osd"), "eng"), (("ara", "eng"), "osd")],
    )
    def test_a_tesseract_without_the_data_a_reading_uses_stops_the_worker(
        self, languages: tuple[str, ...], missing: str
    ) -> None:
        """A reading runs with Arabic and English and finds orientation with osd, so all three
        must be there: one missing would fail every scan the worker is given."""
        with pytest.raises(ConfigurationError, match=f"no {missing}"):
            ocr_for({"MASIRAH_OCR": "tesseract"}, run=self.tesseract(languages=languages))

    def test_an_unknown_engine_stops_the_worker(self) -> None:
        with pytest.raises(ConfigurationError, match="MASIRAH_OCR"):
            ocr_for({"MASIRAH_OCR": "magic"}, run=self.tesseract())


class TestWatching:
    """Every hour the worker checks the parse failure rate (NFR-14, T031)."""

    def test_it_checks_at_start_and_then_once_an_hour(self) -> None:
        now = [0.0]
        checks: list[float] = []

        def check() -> int:
            checks.append(now[0])
            return 0

        watching = Watching(lambda: 1, check, clock=lambda: now[0])
        for moment in (0.0, 60.0, PARSE_CHECK_SECONDS - 1, PARSE_CHECK_SECONDS):
            now[0] = moment
            assert watching() == 1
        assert checks == [0.0, PARSE_CHECK_SECONDS]

    def test_a_failed_check_never_stops_the_work(self) -> None:
        def broken() -> int:
            raise RuntimeError("Slack unreachable")

        assert Watching(lambda: 2, broken, clock=lambda: 0.0)() == 2


def test_slack_is_used_when_its_webhook_is_set() -> None:
    url = " https://hooks.slack.com/services/T0/B0/x "
    assert isinstance(alerts_for({"MASIRAH_SLACK_WEBHOOK_URL": url}), SlackWebhook)


@pytest.mark.parametrize("environment", [{}, {"MASIRAH_SLACK_WEBHOOK_URL": "  "}])
def test_without_a_webhook_alerts_are_only_logged(environment: dict[str, str]) -> None:
    assert alerts_for(environment) is None
