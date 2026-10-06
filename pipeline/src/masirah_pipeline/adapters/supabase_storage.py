"""Original CV files in Supabase Storage's private bucket (T054, migration 0009).

Storage authenticates through the API gateway, not Postgres roles, so the worker reads files with
the project's secret key. The key does two things only: read an original for extraction, and
remove a candidate's originals when the purge sweep clears their personal data (FR-076, NFR-10).
Every database operation goes through the masirah_worker role, under row level security.
"""

from collections.abc import Sequence
from urllib.parse import quote

import httpx2

from masirah_pipeline.ports.cv_store import CvStoreUnavailableError, MissingCvError

BUCKET = "cv-originals"
TIMEOUT = 60


class SupabaseStorage:
    def __init__(
        self, base_url: str, secret_key: str, *, client: httpx2.Client | None = None
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = secret_key
        self._client = client or httpx2.Client(timeout=TIMEOUT)

    def fetch(self, storage_path: str) -> bytes:
        url = f"{self._base}/storage/v1/object/authenticated/{BUCKET}/{quote(storage_path)}"
        try:
            response = self._client.get(url, headers={"apikey": self._key})
        except httpx2.HTTPError as error:
            reason = f"storage could not be reached: {type(error).__name__}"
            raise CvStoreUnavailableError(reason) from error
        if response.status_code == 200:
            return response.content
        if _not_found(response):
            raise MissingCvError(storage_path)
        # The body is not quoted: a misconfigured gateway could echo the request back.
        raise CvStoreUnavailableError(f"storage answered {response.status_code}")

    def remove(self, storage_paths: Sequence[str]) -> None:
        # One request per object: the bulk endpoint answers 200 whatever it managed, so a partial
        # failure would read as success and leave a CV behind. Each answer here is about one file.
        for storage_path in storage_paths:
            url = f"{self._base}/storage/v1/object/{BUCKET}/{quote(storage_path)}"
            try:
                response = self._client.request("DELETE", url, headers={"apikey": self._key})
            except httpx2.HTTPError as error:
                reason = f"storage could not be reached: {type(error).__name__}"
                raise CvStoreUnavailableError(reason) from error
            # An object already gone is what removing it was for.
            if response.status_code == 200 or _not_found(response):
                continue
            raise CvStoreUnavailableError(f"storage answered {response.status_code}")


def _not_found(response: httpx2.Response) -> bool:
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    # Storage reports a missing object, and a key it cannot hold, as a 400 with the cause in the
    # body. Neither can ever be fetched.
    return isinstance(body, dict) and (
        str(body.get("statusCode")) == "404" or body.get("error") == "InvalidKey"
    )
