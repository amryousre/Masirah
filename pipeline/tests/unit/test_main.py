"""The worker process: configuration and the polling loop (T057).

The worker runs as `python -m masirah_pipeline` on its host. It refuses to start with a setting
missing rather than failing on the first message, polls without pause while there is work, and
waits between polls when the queue is empty. A stop request from the host ends it between
batches, never in the middle of a message.
"""

import socket
import threading

import pytest

from masirah_pipeline.adapters.provider_registry import ConfigurationError
from masirah_pipeline.main import IDLE_SECONDS, REQUIRED, poll, settings_from, worker_name

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
