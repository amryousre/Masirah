"""The purge sweep (T100, T101): personal data removed on request and once retention passes.

For each candidate the database says is due, the worker removes the stored originals first and
only then clears the rows, so no route can leave a CV behind in storage. When storage cannot be
reached, that candidate's rows are left untouched for the next sweep and the others go ahead.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from masirah_pipeline.jobs.purge import purge_due
from masirah_pipeline.ports.cv_store import CvStoreUnavailableError
from masirah_pipeline.ports.purge_store import DueFile, DuePurge

ORG = uuid4()


@dataclass
class FakeStore:
    due_now: list[DuePurge]
    paths: dict[UUID, list[str]]
    purged: list[tuple[UUID, str]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    files_due: list[DueFile] = field(default_factory=list)
    files_purged: list[UUID] = field(default_factory=list)

    def due_files(self, at_most: int) -> list[DueFile]:
        return self.files_due[:at_most]

    def purge_file(self, cv_file_id: UUID) -> None:
        self.events.append(f"purge file {cv_file_id}")
        self.files_purged.append(cv_file_id)

    def due(self, at_most: int) -> list[DuePurge]:
        return self.due_now[:at_most]

    def original_paths(self, candidate_id: UUID) -> list[str]:
        return self.paths.get(candidate_id, [])

    def purge(self, candidate_id: UUID, reason: str) -> None:
        self.events.append(f"purge {candidate_id}")
        self.purged.append((candidate_id, reason))


@dataclass
class FakeFiles:
    events: list[str]
    failing: set[str] = field(default_factory=set)
    removed: list[str] = field(default_factory=list)

    def remove(self, storage_paths: Sequence[str]) -> None:
        if self.failing & set(storage_paths):
            raise CvStoreUnavailableError("storage answered 503")
        self.events.append(f"remove {storage_paths}")
        self.removed.extend(storage_paths)


def test_each_due_candidate_loses_its_originals_then_its_rows() -> None:
    first, second = uuid4(), uuid4()
    store = FakeStore(
        [DuePurge(ORG, first, "request"), DuePurge(ORG, second, "retention")],
        {first: ["a.pdf", "b.pdf"], second: ["c.pdf"]},
    )
    files = FakeFiles(store.events)
    assert purge_due(store, files) == 2
    assert store.purged == [(first, "request"), (second, "retention")]
    assert store.events == [
        "remove ['a.pdf', 'b.pdf']",
        f"purge {first}",
        "remove ['c.pdf']",
        f"purge {second}",
    ]


def test_a_candidate_without_stored_files_is_still_purged() -> None:
    candidate = uuid4()
    store = FakeStore([DuePurge(ORG, candidate, "retention")], {})
    files = FakeFiles(store.events)
    assert purge_due(store, files) == 1
    assert files.removed == []
    assert store.purged == [(candidate, "retention")]


def test_when_storage_fails_the_rows_wait_and_the_rest_go_ahead() -> None:
    stuck, fine = uuid4(), uuid4()
    store = FakeStore(
        [DuePurge(ORG, stuck, "request"), DuePurge(ORG, fine, "request")],
        {stuck: ["stuck.pdf"], fine: ["fine.pdf"]},
    )
    files = FakeFiles(store.events, failing={"stuck.pdf"})
    assert purge_due(store, files) == 1
    assert store.purged == [(fine, "request")]


def test_a_sweep_takes_at_most_its_batch() -> None:
    store = FakeStore([DuePurge(ORG, uuid4(), "retention") for _ in range(5)], {})
    assert purge_due(store, FakeFiles(store.events), at_most=2) == 2


def test_a_file_that_never_became_a_candidate_loses_its_original_then_its_row() -> None:
    orphan = uuid4()
    store = FakeStore([], {}, files_due=[DueFile(ORG, orphan, "orphan.pdf")])
    files = FakeFiles(store.events)
    assert purge_due(store, files) == 1
    assert store.events == ["remove ['orphan.pdf']", f"purge file {orphan}"]


def test_files_share_what_the_candidates_leave_of_the_batch() -> None:
    store = FakeStore(
        [DuePurge(ORG, uuid4(), "retention")],
        {},
        files_due=[DueFile(ORG, uuid4(), f"{n}.pdf") for n in range(3)],
    )
    assert purge_due(store, FakeFiles(store.events), at_most=2) == 2
    assert len(store.files_purged) == 1


def test_a_file_whose_original_cannot_be_removed_waits() -> None:
    stuck = uuid4()
    store = FakeStore([], {}, files_due=[DueFile(ORG, stuck, "stuck.pdf")])
    assert purge_due(store, FakeFiles(store.events, failing={"stuck.pdf"})) == 0
    assert store.files_purged == []
