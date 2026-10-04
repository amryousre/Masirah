"""Reading an original CV from Supabase Storage (T054).

The worker fetches the file the message names from the private bucket. A missing file can never
be processed, while an outage, a rate limit or a rejected key is not the file's fault and must
not fail it: the message waits for the next attempt.
"""

from collections.abc import Callable

import httpx2
import pytest

from masirah_pipeline.adapters.supabase_storage import SupabaseStorage
from masirah_pipeline.ports.cv_store import CvStoreUnavailableError, MissingCvError

BASE = "https://project.supabase.co"
KEY = "sb_secret_example"
PATH = "organisations/0f0e/cv/1a1b/my cv.pdf"


def storage(answer: Callable[[httpx2.Request], httpx2.Response]) -> SupabaseStorage:
    client = httpx2.Client(transport=httpx2.MockTransport(answer))
    return SupabaseStorage(BASE, KEY, client=client)


def test_it_fetches_the_original_with_the_secret_key() -> None:
    seen: list[httpx2.Request] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, content=b"%PDF-1.7")

    assert storage(answer).fetch(PATH) == b"%PDF-1.7"
    [request] = seen
    assert request.method == "GET"
    assert request.headers["apikey"] == KEY
    assert request.url.path == (
        "/storage/v1/object/authenticated/cv-originals/organisations/0f0e/cv/1a1b/my cv.pdf"
    )
    assert "%20" in str(request.url.raw_path, "ascii")


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(404),
        # Storage reports a missing object as a 400 whose body carries the 404.
        httpx2.Response(400, json={"statusCode": "404", "error": "not_found"}),
        # A key Storage cannot hold, such as one with Arabic letters, can never be fetched.
        httpx2.Response(400, json={"statusCode": "400", "error": "InvalidKey"}),
    ],
    ids=["404", "400-not-found", "400-invalid-key"],
)
def test_a_missing_file_says_so(response: httpx2.Response) -> None:
    with pytest.raises(MissingCvError):
        storage(lambda request: response).fetch(PATH)


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_other_failures_are_worth_retrying(status: int) -> None:
    with pytest.raises(CvStoreUnavailableError):
        storage(lambda request: httpx2.Response(status)).fetch(PATH)


def test_a_network_failure_is_worth_retrying() -> None:
    def answer(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(CvStoreUnavailableError):
        storage(answer).fetch(PATH)


def test_the_key_never_appears_in_an_error() -> None:
    with pytest.raises(CvStoreUnavailableError) as raised:
        storage(lambda request: httpx2.Response(500, text=KEY)).fetch(PATH)
    assert KEY not in str(raised.value)
