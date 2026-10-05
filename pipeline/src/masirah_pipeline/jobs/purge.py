"""The purge sweep (T100, T101, NFR-10, FR-076).

Each candidate the database lists as due, on request or past retention, first loses their stored
originals and only then their personal data in the rows, so no path can leave a CV behind in
storage. If storage fails, that candidate is left as it was for the next sweep; the rest go ahead.
"""

import logging

from masirah_pipeline.ports.cv_store import CvStoreUnavailableError
from masirah_pipeline.ports.original_remover import OriginalRemover
from masirah_pipeline.ports.purge_store import PurgeStore

log = logging.getLogger(__name__)

BATCH = 50


def purge_due(store: PurgeStore, files: OriginalRemover, at_most: int = BATCH) -> int:
    """Purges up to at_most due candidates and returns how many were purged."""
    purged = 0
    for due in store.due(at_most):
        paths = store.original_paths(due.candidate_id)
        try:
            if paths:
                files.remove(paths)
        except CvStoreUnavailableError:
            log.warning(
                "originals of candidate %s could not be removed; it waits for the next sweep",
                due.candidate_id,
            )
            continue
        store.purge(due.candidate_id, due.reason)
        purged += 1
    return purged
