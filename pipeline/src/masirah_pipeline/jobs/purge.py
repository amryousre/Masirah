"""The purge sweep (T100, T101, NFR-10, FR-076).

Each candidate the database lists as due, on request or past retention, first loses their stored
originals and only then their personal data in the rows, so no path can leave a CV behind in
storage. If storage fails, that candidate is left as it was and put back for a while, so it cannot
hold the head of every batch; the rest go ahead.
CVs that never became a candidate are swept the same way, with what the candidates leave of the
batch.
"""

import logging

from masirah_pipeline.ports.cv_store import CvStoreUnavailableError
from masirah_pipeline.ports.original_remover import OriginalRemover
from masirah_pipeline.ports.purge_store import PurgeStore

log = logging.getLogger(__name__)

BATCH = 50


def purge_due(store: PurgeStore, files: OriginalRemover, at_most: int = BATCH) -> int:
    """Purges up to at_most due candidates, then files, and returns how many were purged."""
    purged = 0
    for due in store.due(at_most):
        originals = store.originals(due.candidate_id)
        try:
            if originals:
                files.remove([original.storage_path for original in originals])
        except CvStoreUnavailableError:
            log.warning(
                "originals of candidate %s could not be removed; it is retried later",
                due.candidate_id,
            )
            store.defer(due.candidate_id)
            continue
        store.purge(due.candidate_id, due.reason, [original.cv_file_id for original in originals])
        purged += 1
    for file in store.due_files(at_most - purged):
        try:
            files.remove([file.storage_path])
        except CvStoreUnavailableError:
            log.warning(
                "original of file %s could not be removed; it is retried later",
                file.cv_file_id,
            )
            store.defer(file.cv_file_id)
            continue
        store.purge_file(file.cv_file_id)
        purged += 1
    return purged
