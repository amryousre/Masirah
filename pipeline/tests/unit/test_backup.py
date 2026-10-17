"""Daily backups of the hosted project (T110, NFR-15).

The project is on Supabase's Free plan, which takes no backups of its own, so this tool does: the
data of our own schemas (public, private, and auth for the accounts) and every CV original in
Storage, packed into one archive with a manifest of SHA-256 digests and of the migrations the
schema came from, and encrypted to an age public key. A restore rebuilds the schema from those
migrations, so nothing of Supabase's own platform is copied, which a restore could not write.
The machine that makes backups holds only that public key; the private key that opens them is
kept offline, so a copied backup folder reveals nothing. No plaintext is left on disk afterwards,
the newest KEPT backups are kept, and a failure is posted to the operators' Slack channel.
"""

import io
import json
import tarfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx2
import pyrage
import pytest

from tools.backup import (
    KEPT,
    BackupError,
    BackupSettings,
    Runner,
    dump_commands,
    list_originals,
    open_backup,
    prune,
    restore_commands,
    run_backup,
    settings_from,
    verify,
)

DB_URL = "postgresql://postgres.ref:pw@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
STORAGE_URL = "https://ref.supabase.co"
CLI = ["npx", "--yes", "supabase@2.117.0"]
STORAGE_KEY = "sb_secret_x"


@pytest.fixture
def identity() -> pyrage.x25519.Identity:
    return pyrage.x25519.Identity.generate()


def settings(tmp_path: Path, identity: pyrage.x25519.Identity) -> BackupSettings:
    return BackupSettings(
        db_url=DB_URL,
        storage_url=STORAGE_URL,
        secret_key=STORAGE_KEY,
        recipient=str(identity.to_public()),
        destination=tmp_path / "backups",
        slack_webhook=None,
    )


COMPLETE = {
    "MASIRAH_BACKUP_DB_URL": DB_URL,
    "MASIRAH_BACKUP_SUPABASE_URL": STORAGE_URL,
    "MASIRAH_BACKUP_SUPABASE_SECRET_KEY": "sb_secret_x",
    "MASIRAH_BACKUP_RECIPIENT": "age1example",
    "MASIRAH_BACKUP_DIR": "D:/backups",
}


class TestSettings:
    def test_complete_settings_are_read(self) -> None:
        read = settings_from(COMPLETE)
        assert read.destination == Path("D:/backups")
        assert read.slack_webhook is None

    @pytest.mark.parametrize("missing", sorted(COMPLETE))
    def test_a_missing_setting_is_named_and_no_value_is_shown(self, missing: str) -> None:
        environment = {name: value for name, value in COMPLETE.items() if name != missing}
        with pytest.raises(BackupError) as raised:
            settings_from(environment)
        assert missing in str(raised.value)
        assert "pw@" not in str(raised.value)
        assert "sb_secret_x" not in str(raised.value)

    def test_the_slack_webhook_is_optional_and_shared_with_the_worker(self) -> None:
        url = "https://hooks.slack.com/services/T/B/x"
        read = settings_from(COMPLETE | {"MASIRAH_SLACK_WEBHOOK_URL": url})
        assert read.slack_webhook == url


def test_only_our_own_data_is_dumped(tmp_path: Path) -> None:
    """The data of public, private and auth, as COPY; Auth's record of its own migrations is the
    platform's, and a new project has its own."""
    assert dump_commands(CLI, DB_URL, tmp_path) == [
        [
            *CLI,
            *["db", "dump", "--db-url", DB_URL, "-f", str(tmp_path / "data.sql")],
            *["--data-only", "--use-copy", "--schema", "auth,public,private"],
            *["--exclude", "auth.schema_migrations"],
        ]
    ]


def test_a_restore_loads_the_data_into_the_migrated_schema(tmp_path: Path) -> None:
    """One transaction, stopping at the first error, with triggers off while the data loads."""
    assert restore_commands(["psql"], "postgresql://local", tmp_path) == [
        [
            "psql",
            *["--single-transaction", "--variable", "ON_ERROR_STOP=1"],
            *["--command", "SET session_replication_role = replica"],
            *["--file", str(tmp_path / "data.sql"), "--dbname", "postgresql://local"],
        ]
    ]


def storage_answering(tree: dict[str, list[dict[str, object]]]) -> httpx2.Client:
    """Storage's list endpoint over a fixed tree: a folder entry has no id."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/storage/v1/object/list/cv-originals"
        assert request.headers["apikey"] == "sb_secret_x"
        body = json.loads(request.content)
        page = tree.get(body["prefix"], [])[body["offset"] : body["offset"] + body["limit"]]
        return httpx2.Response(200, json=page)

    return httpx2.Client(transport=httpx2.MockTransport(answer), base_url=STORAGE_URL)


def test_every_original_is_found_through_its_folders() -> None:
    tree: dict[str, list[dict[str, object]]] = {
        "": [{"name": "organisations", "id": None}],
        "organisations": [{"name": "org-1", "id": None}, {"name": "org-2", "id": None}],
        "organisations/org-1": [{"name": "cv", "id": None}],
        "organisations/org-1/cv": [{"name": "f1", "id": None}],
        "organisations/org-1/cv/f1": [{"name": "cv.pdf", "id": "a"}],
        "organisations/org-2": [{"name": "cv", "id": None}],
        "organisations/org-2/cv": [{"name": "f2", "id": None}],
        "organisations/org-2/cv/f2": [{"name": "cv.docx", "id": "b"}, {"name": "p.jpg", "id": "c"}],
    }
    found = list_originals(STORAGE_URL, "sb_secret_x", client=storage_answering(tree))
    assert sorted(found) == [
        "organisations/org-1/cv/f1/cv.pdf",
        "organisations/org-2/cv/f2/cv.docx",
        "organisations/org-2/cv/f2/p.jpg",
    ]


def test_a_folder_longer_than_a_page_is_read_to_its_end() -> None:
    files: list[dict[str, object]] = [{"name": f"{n}.pdf", "id": str(n)} for n in range(250)]
    found = list_originals(
        STORAGE_URL, "sb_secret_x", client=storage_answering({"": files}), page=100
    )
    assert len(found) == 250


class Originals:
    """Storage as the backup reads it: listing, then each file's bytes."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def paths(self) -> list[str]:
        return list(self.files)

    def fetch(self, storage_path: str) -> bytes:
        return self.files[storage_path]


def dumping(fail: bool = False) -> tuple[list[list[str]], Runner]:
    ran: list[list[str]] = []

    def run(command: Sequence[str]) -> None:
        ran.append(list(command))
        if fail:
            raise BackupError("supabase db dump exited with 1")
        target = Path(command[command.index("-f") + 1])
        target.write_text(f"-- {target.name}\nselect 1;\n", encoding="utf-8")

    return ran, run


FILES = {"organisations/o/cv/f/cv.pdf": b"%PDF-1.7 a CV", "organisations/o/cv/g/cv.docx": b"PK.."}
NOW = datetime(2026, 10, 16, 2, 0, tzinfo=UTC)


def backups_in(folder: Path) -> list[Path]:
    return sorted(folder.glob("masirah-backup-*.tar.age"))


class TestRunBackup:
    def test_one_encrypted_backup_is_written_and_opens_with_the_private_key(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        _, run = dumping()
        made = run_backup(
            settings(tmp_path, identity),
            run=run,
            originals=Originals(FILES),
            now=NOW,
            scratch=tmp_path / "scratch",
        )
        assert made == tmp_path / "backups" / "masirah-backup-20261016T020000Z.tar.age"
        assert backups_in(tmp_path / "backups") == [made]

        opened = open_backup(made, str(identity), tmp_path / "opened")
        assert (opened / "database" / "data.sql").read_text(encoding="utf-8").startswith("--")
        assert (
            opened / "originals" / "organisations/o/cv/f/cv.pdf"
        ).read_bytes() == b"%PDF-1.7 a CV"
        assert verify(opened) == []

    def test_the_manifest_names_the_migrations_the_schema_came_from(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        """A restore must rebuild the schema from these exact migrations before the data loads."""
        migrations = tmp_path / "migrations"
        migrations.mkdir()
        for name in ("0002_job.sql", "0001_tenancy.sql"):
            (migrations / name).write_text("-- ddl", encoding="utf-8")
        (migrations / "README.md").write_text("not a migration", encoding="utf-8")
        _, run = dumping()
        made = run_backup(
            settings(tmp_path, identity),
            run=run,
            originals=Originals(FILES),
            now=NOW,
            scratch=tmp_path / "scratch",
            migrations=migrations,
        )
        opened = open_backup(made, str(identity), tmp_path / "opened")
        manifest = json.loads((opened / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["migrations"] == ["0001_tenancy.sql", "0002_job.sql"]

    def test_the_backup_reveals_nothing_without_the_private_key(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        _, run = dumping()
        made = run_backup(
            settings(tmp_path, identity),
            run=run,
            originals=Originals(FILES),
            now=NOW,
            scratch=tmp_path / "scratch",
        )
        sealed = made.read_bytes()
        assert sealed.startswith(b"age-encryption.org/v1")
        assert b"a CV" not in sealed
        assert b"select 1" not in sealed
        with pytest.raises(pyrage.DecryptError):
            pyrage.decrypt(sealed, [pyrage.x25519.Identity.generate()])

    def test_the_unencrypted_work_never_touches_the_backup_folder(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        """The backup folder may be a cloud-synced one: only sealed files may ever appear there."""
        seen: list[str] = []
        _, dump = dumping()

        def run(command: Sequence[str]) -> None:
            dump(command)
            seen.extend(p.name for p in (tmp_path / "backups").glob("*"))

        run_backup(
            settings(tmp_path, identity),
            run=run,
            originals=Originals(FILES),
            now=NOW,
            scratch=tmp_path / "scratch",
        )
        assert seen == []

    def test_no_plaintext_is_left_on_disk(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        _, run = dumping()
        run_backup(
            settings(tmp_path, identity),
            run=run,
            originals=Originals(FILES),
            now=NOW,
            scratch=tmp_path / "scratch",
        )
        left = [p for p in tmp_path.rglob("*") if p.is_file() and not p.name.endswith(".tar.age")]
        assert left == []

    def test_a_failed_dump_writes_no_backup_and_tells_slack(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        _, run = dumping(fail=True)
        posted: list[str] = []
        with pytest.raises(BackupError):
            run_backup(
                settings(tmp_path, identity),
                run=run,
                originals=Originals(FILES),
                now=NOW,
                scratch=tmp_path / "scratch",
                alert=posted.append,
            )
        assert backups_in(tmp_path / "backups") == []
        assert len(posted) == 1
        assert "backup failed" in posted[0]
        assert "pw@" not in posted[0]
        assert [p for p in tmp_path.rglob("*") if p.is_file()] == []

    def test_the_newest_backups_are_kept(
        self, tmp_path: Path, identity: pyrage.x25519.Identity
    ) -> None:
        folder = tmp_path / "backups"
        folder.mkdir()
        for day in range(1, KEPT + 4):
            (folder / f"masirah-backup-202609{day:02d}T020000Z.tar.age").write_bytes(b"old")
        (folder / "notes.txt").write_text("kept", encoding="utf-8")
        _, run = dumping()
        made = run_backup(
            settings(tmp_path, identity),
            run=run,
            originals=Originals(FILES),
            now=NOW,
            scratch=tmp_path / "scratch",
        )
        kept = backups_in(folder)
        assert len(kept) == KEPT
        assert made in kept
        assert (folder / "notes.txt").exists()


def test_prune_keeps_the_newest_by_name(tmp_path: Path) -> None:
    names = [f"masirah-backup-2026100{d}T020000Z.tar.age" for d in range(1, 6)]
    for name in names:
        (tmp_path / name).write_bytes(b"x")
    removed = prune(tmp_path, keep=2)
    assert sorted(p.name for p in removed) == names[:3]
    assert sorted(p.name for p in backups_in(tmp_path)) == names[3:]


def test_verify_names_a_changed_or_missing_file(tmp_path: Path) -> None:
    (tmp_path / "originals").mkdir()
    (tmp_path / "originals" / "a.pdf").write_bytes(b"one")
    (tmp_path / "originals" / "b.pdf").write_bytes(b"two")
    import hashlib

    manifest = {
        "files": {
            "originals/a.pdf": hashlib.sha256(b"one").hexdigest(),
            "originals/b.pdf": hashlib.sha256(b"changed").hexdigest(),
            "originals/c.pdf": hashlib.sha256(b"three").hexdigest(),
        }
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert verify(tmp_path) == ["changed: originals/b.pdf", "missing: originals/c.pdf"]


def test_an_archive_cannot_write_outside_where_it_is_opened(
    tmp_path: Path, identity: pyrage.x25519.Identity
) -> None:
    """A tampered backup with a path like ../x must not write outside the folder it opens into."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo("../escaped.txt")
        member.size = 3
        archive.addfile(member, io.BytesIO(b"bad"))
    sealed = tmp_path / "bad.tar.age"
    sealed.write_bytes(pyrage.encrypt(buffer.getvalue(), [identity.to_public()]))
    with pytest.raises(BackupError):
        open_backup(sealed, str(identity), tmp_path / "opened")
    assert not (tmp_path / "escaped.txt").exists()


def test_keygen_writes_the_private_key_once_and_returns_its_public_key(tmp_path: Path) -> None:
    from tools.backup import keygen

    private = tmp_path / "masirah-backup.key"
    public = keygen(private)
    identity = pyrage.x25519.Identity.from_str(private.read_text(encoding="utf-8").strip())
    assert public == str(identity.to_public())
    sealed = pyrage.encrypt(b"x", [pyrage.x25519.Recipient.from_str(public)])
    assert pyrage.decrypt(sealed, [identity]) == b"x"
    # An existing key is never overwritten: it may be the only one that opens past backups.
    with pytest.raises(FileExistsError):
        keygen(private)


def test_the_command_line_fails_without_settings_and_shows_no_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tools.backup import main

    assert main(["run"], {"MASIRAH_BACKUP_DB_URL": DB_URL}) == 1
    error = capsys.readouterr().err
    assert "MASIRAH_BACKUP_DIR" in error
    assert "pw@" not in error


def test_the_command_line_opens_and_verifies_a_backup(
    tmp_path: Path, identity: pyrage.x25519.Identity, capsys: pytest.CaptureFixture[str]
) -> None:
    from tools.backup import main

    _, run = dumping()
    made = run_backup(
        settings(tmp_path, identity),
        run=run,
        originals=Originals(FILES),
        now=NOW,
        scratch=tmp_path / "scratch",
    )
    key = tmp_path / "key.txt"
    key.write_text(f"{identity}\n", encoding="utf-8")
    assert main(["open", str(made), "--identity", str(key), "--into", str(tmp_path / "o")], {}) == 0
    assert "opened and verified" in capsys.readouterr().out


def test_a_restore_puts_every_original_back_where_it_was(tmp_path: Path) -> None:
    from tools.backup import upload_originals

    originals = tmp_path / "originals"
    for relative, content in FILES.items():
        (originals / relative).parent.mkdir(parents=True, exist_ok=True)
        (originals / relative).write_bytes(content)
    uploaded: dict[str, bytes] = {}

    def answer(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert request.headers["x-upsert"] == "true"
        assert request.headers["apikey"] == STORAGE_KEY
        prefix = "/storage/v1/object/cv-originals/"
        uploaded[request.url.path.removeprefix(prefix)] = request.content
        return httpx2.Response(200, json={"Key": "x"})

    client = httpx2.Client(transport=httpx2.MockTransport(answer))
    assert upload_originals(originals, STORAGE_URL, STORAGE_KEY, client=client) == len(FILES)
    assert uploaded == FILES


def test_a_refused_upload_stops_the_restore(tmp_path: Path) -> None:
    from tools.backup import upload_originals

    (tmp_path / "a.pdf").write_bytes(b"x")
    client = httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(403)))
    with pytest.raises(BackupError, match="403"):
        upload_originals(tmp_path, STORAGE_URL, STORAGE_KEY, client=client)


def test_a_command_is_found_on_the_path_as_the_shell_would_find_it() -> None:
    """On Windows npx is npx.cmd, which a bare subprocess call cannot start."""
    from tools.backup import run_command

    run_command(["npx", "--version"])


def test_a_missing_program_is_named() -> None:
    from tools.backup import run_command

    with pytest.raises(BackupError, match="no-such-program-masirah"):
        run_command(["no-such-program-masirah", "--db-url", DB_URL])
