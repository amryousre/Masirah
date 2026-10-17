"""Daily encrypted backups of the hosted project, and opening one to restore it (T110, NFR-15).

The project is on Supabase's Free plan, which takes no backups of its own. Run from pipeline/ with
the settings in .env (see .env.example), once a day by Windows Task Scheduler:

    uv run --env-file .env python -m tools.backup run
    uv run python -m tools.backup keygen <private-key-file>
    uv run python -m tools.backup open <backup> --identity <private-key-file> --into <folder>

A backup is the data of our own schemas (public, private, and auth for the accounts), dumped by
the pinned Supabase CLI, which needs Docker, and every CV original in Storage, with a manifest of
SHA-256 digests and of the migrations the schema came from, in one tar archive encrypted to an age
public key. The machine that makes backups holds
only the public key. The private key is kept offline, so a copied backup folder reveals nothing.

The unencrypted work happens in a scratch folder on the local disk, never in the backup folder,
which may sync to the cloud, and is removed whatever happens. The newest KEPT backups are kept. A
failure is posted to the operators' Slack channel when MASIRAH_SLACK_WEBHOOK_URL is set, and the
command exits non-zero, which Task Scheduler records.

The restore procedure, and the drill that tested it, are in Docs/runbooks/backup-recovery.md.
"""

import argparse
import hashlib
import json
import mimetypes
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePath, PurePosixPath
from typing import Protocol
from urllib.parse import quote

import httpx2
import pyrage

from masirah_pipeline.adapters.slack_webhook import SlackWebhook
from masirah_pipeline.adapters.supabase_storage import BUCKET, SupabaseStorage

KEPT = 30
PATTERN = "masirah-backup-*.tar.age"
SUPABASE_CLI = ["npx", "--yes", "supabase@2.117.0"]
TIMEOUT = 60

Runner = Callable[[Sequence[str]], None]
Alert = Callable[[str], None]


class BackupError(Exception):
    """A backup or a restore could not be completed. The message never holds a credential."""


@dataclass(frozen=True)
class BackupSettings:
    db_url: str
    storage_url: str
    secret_key: str
    recipient: str
    destination: Path
    slack_webhook: str | None


REQUIRED = {
    "MASIRAH_BACKUP_DB_URL": "db_url",
    "MASIRAH_BACKUP_SUPABASE_URL": "storage_url",
    "MASIRAH_BACKUP_SUPABASE_SECRET_KEY": "secret_key",
    "MASIRAH_BACKUP_RECIPIENT": "recipient",
    "MASIRAH_BACKUP_DIR": "destination",
}


def settings_from(environment: Mapping[str, str]) -> BackupSettings:
    missing = [name for name in REQUIRED if not environment.get(name, "").strip()]
    if missing:
        raise BackupError(f"the backup needs {', '.join(missing)}")
    read = {field: environment[name].strip() for name, field in REQUIRED.items()}
    return BackupSettings(
        db_url=read["db_url"],
        storage_url=read["storage_url"],
        secret_key=read["secret_key"],
        recipient=read["recipient"],
        destination=Path(read["destination"]),
        slack_webhook=environment.get("MASIRAH_SLACK_WEBHOOK_URL", "").strip() or None,
    )


# Our own data only. A restore rebuilds the schema from the repository's migrations and then loads
# this: copying Supabase's own platform (its Storage and Realtime internals, its Auth bookkeeping)
# fails in a new project, which has its own and lets no customer role write them. Storage's rows
# come back when the originals are uploaded again.
DUMPED_SCHEMAS = "auth,public,private"
NOT_DUMPED = "auth.schema_migrations"
MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def dump_commands(cli: Sequence[str], db_url: str, folder: Path) -> list[list[str]]:
    """The data of our own schemas, as COPY statements."""
    return [
        [
            *cli,
            *["db", "dump", "--db-url", db_url, "-f", str(folder / "data.sql")],
            *["--data-only", "--use-copy", "--schema", DUMPED_SCHEMAS],
            *["--exclude", NOT_DUMPED],
        ]
    ]


def restore_commands(psql: Sequence[str], db_url: str, folder: PurePath) -> list[list[str]]:
    """Loads the data into a database already migrated to the manifest's migrations: one
    transaction, stopping at the first error, with triggers off while the data loads."""
    return [
        [
            *psql,
            *["--single-transaction", "--variable", "ON_ERROR_STOP=1"],
            *["--command", "SET session_replication_role = replica"],
            *["--file", str(folder / "data.sql"), "--dbname", db_url],
        ]
    ]


def list_originals(
    base_url: str, secret_key: str, *, client: httpx2.Client | None = None, page: int = 1000
) -> list[str]:
    """Every object in the originals bucket. Storage lists one folder at a time, and an entry
    without an id is a folder."""
    http = client or httpx2.Client(timeout=TIMEOUT)
    url = f"{base_url.rstrip('/')}/storage/v1/object/list/{BUCKET}"
    found: list[str] = []
    folders = [""]
    while folders:
        prefix = folders.pop()
        offset = 0
        while True:
            try:
                response = http.post(
                    url,
                    headers={"apikey": secret_key, "authorization": f"Bearer {secret_key}"},
                    json={"prefix": prefix, "limit": page, "offset": offset},
                )
            except httpx2.HTTPError as error:
                raise BackupError(
                    f"storage could not be reached ({type(error).__name__})"
                ) from None
            if response.status_code != 200:
                raise BackupError(f"storage answered {response.status_code} when listing")
            entries = response.json()
            for entry in entries:
                path = f"{prefix}/{entry['name']}" if prefix else str(entry["name"])
                (folders if entry.get("id") is None else found).append(path)
            if len(entries) < page:
                break
            offset += page
    return found


class Originals(Protocol):
    def paths(self) -> list[str]: ...

    def fetch(self, storage_path: str) -> bytes: ...


class StorageOriginals:
    """The hosted bucket, listed here and read through the worker's own Storage adapter."""

    def __init__(self, base_url: str, secret_key: str) -> None:
        self._base_url, self._secret_key = base_url, secret_key
        self._storage = SupabaseStorage(base_url, secret_key)

    def paths(self) -> list[str]:
        return list_originals(self._base_url, self._secret_key)

    def fetch(self, storage_path: str) -> bytes:
        return self._storage.fetch(storage_path)


def run_command(command: Sequence[str]) -> None:
    """Runs a command, reporting a failure by exit code only: the command holds the database URL.
    The program is found on PATH as the shell would find it, so npx.cmd runs on Windows."""
    program = shutil.which(command[0])
    if program is None:
        raise BackupError(f"{command[0]} was not found on PATH")
    completed = subprocess.run([program, *command[1:]], check=False, capture_output=True)  # noqa: S603
    if completed.returncode != 0:
        raise BackupError(f"{PurePosixPath(command[0]).name} exited with {completed.returncode}")


def _inside(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise BackupError(f"a stored path leaves the backup: {relative!r}")
    return target


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_backup(
    settings: BackupSettings,
    *,
    run: Runner = run_command,
    originals: Originals | None = None,
    now: datetime | None = None,
    scratch: Path | None = None,
    alert: Alert | None = None,
    cli: Sequence[str] = SUPABASE_CLI,
    migrations: Path = MIGRATIONS,
) -> Path:
    """Makes one backup in the destination folder and returns it."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    store = originals or StorageOriginals(settings.storage_url, settings.secret_key)
    scratch_root = scratch or Path(tempfile.gettempdir())
    scratch_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="masirah-backup-", dir=scratch_root))
    try:
        content = work / "content"
        database = content / "database"
        database.mkdir(parents=True)
        for command in dump_commands(cli, settings.db_url, database):
            run(command)
        stored = content / "originals"
        for storage_path in store.paths():
            target = _inside(stored, storage_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(store.fetch(storage_path))
        files = sorted(p for p in content.rglob("*") if p.is_file())
        manifest = {
            "made_at": stamp,
            "migrations": sorted(m.name for m in migrations.glob("*.sql")),
            "files": {p.relative_to(content).as_posix(): _digest(p) for p in files},
        }
        (content / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        archive = work / "backup.tar"
        with tarfile.open(archive, "w") as tar:
            for child in sorted(content.iterdir()):
                tar.add(child, arcname=child.name)
        sealed = work / "backup.tar.age"
        recipient = pyrage.x25519.Recipient.from_str(settings.recipient)
        pyrage.encrypt_file(str(archive), str(sealed), [recipient])

        # Only the sealed file reaches the destination, moved in whole.
        settings.destination.mkdir(parents=True, exist_ok=True)
        made = settings.destination / f"masirah-backup-{stamp}.tar.age"
        shutil.move(sealed, made)
        prune(settings.destination, KEPT)
        return made
    except Exception as error:
        reason = str(error) if isinstance(error, BackupError) else type(error).__name__
        if alert is not None:
            alert(f"Masirah backup failed: {reason}")
        if isinstance(error, BackupError):
            raise
        raise BackupError(reason) from None
    finally:
        shutil.rmtree(work, ignore_errors=True)


def prune(folder: Path, keep: int) -> list[Path]:
    """Removes all but the newest `keep` backups; names sort by time. Other files are left."""
    backups = sorted(folder.glob(PATTERN))
    removed = backups[: max(0, len(backups) - keep)]
    for old in removed:
        old.unlink()
    return removed


def open_backup(backup: Path, identity: str, into: Path) -> Path:
    """Decrypts a backup with the private key and unpacks it into `into`, refusing any member
    that would land outside it."""
    into.mkdir(parents=True, exist_ok=True)
    archive = into / "backup.tar"
    try:
        pyrage.decrypt_file(str(backup), str(archive), [pyrage.x25519.Identity.from_str(identity)])
        with tarfile.open(archive) as tar:
            tar.extractall(into, filter="data")
    except (pyrage.DecryptError, pyrage.IdentityError) as error:
        raise BackupError(f"the backup could not be opened ({type(error).__name__})") from None
    except tarfile.FilterError as error:
        raise BackupError(f"the backup holds an unsafe path ({type(error).__name__})") from None
    finally:
        archive.unlink(missing_ok=True)
    return into


def verify(folder: Path) -> list[str]:
    """What differs from the manifest: each file changed or missing. Empty when all match."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    for relative, digest in sorted(manifest["files"].items()):
        path = folder / relative
        if not path.is_file():
            problems.append(f"missing: {relative}")
        elif _digest(path) != digest:
            problems.append(f"changed: {relative}")
    return problems


def upload_originals(
    folder: Path, base_url: str, secret_key: str, *, client: httpx2.Client | None = None
) -> int:
    """Puts every original under `folder` back in the bucket at the same path, replacing any
    there; returns how many. The database's own rows for them come back with data.sql."""
    http = client or httpx2.Client(timeout=TIMEOUT)
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    for path in files:
        relative = path.relative_to(folder).as_posix()
        url = f"{base_url.rstrip('/')}/storage/v1/object/{BUCKET}/{quote(relative)}"
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            response = http.post(
                url,
                content=path.read_bytes(),
                headers={
                    "apikey": secret_key,
                    "authorization": f"Bearer {secret_key}",
                    "content-type": media_type,
                    "x-upsert": "true",
                },
            )
        except httpx2.HTTPError as error:
            raise BackupError(f"storage could not be reached ({type(error).__name__})") from None
        if response.status_code != 200:
            raise BackupError(f"storage answered {response.status_code} for {relative}")
    return len(files)


def keygen(private_key_file: Path) -> str:
    """Writes a new private key to the file, which must not exist yet, and returns the public key
    for MASIRAH_BACKUP_RECIPIENT. The private key is shown nowhere else."""
    identity = pyrage.x25519.Identity.generate()
    with private_key_file.open("x", encoding="utf-8") as file:
        file.write(f"{identity}\n")
    return str(identity.to_public())


def main(argv: Sequence[str] | None = None, environment: Mapping[str, str] | None = None) -> int:
    import os

    env = os.environ if environment is None else environment
    parser = argparse.ArgumentParser(prog="python -m tools.backup")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="make today's backup")
    key = commands.add_parser("keygen", help="make the key pair; keep the private key offline")
    key.add_argument("private_key_file", type=Path)
    opened = commands.add_parser("open", help="decrypt, unpack and verify a backup")
    opened.add_argument("backup", type=Path)
    opened.add_argument("--identity", type=Path, required=True)
    opened.add_argument("--into", type=Path, required=True)
    opened.add_argument("--restore-to", help="also replay the dumps into this database URL")
    opened.add_argument(
        "--restore-originals",
        action="store_true",
        help="also upload the originals to MASIRAH_RESTORE_SUPABASE_URL",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "keygen":
            public = keygen(args.private_key_file)
            print(f"MASIRAH_BACKUP_RECIPIENT={public}")
            print(f"Move {args.private_key_file} somewhere offline. Without it, no backup opens.")
            return 0
        if args.command == "run":
            settings = settings_from(env)
            webhook = settings.slack_webhook
            made = run_backup(
                settings, alert=None if webhook is None else SlackWebhook(webhook).send
            )
            print(f"backup written: {made}")
            return 0
        folder = open_backup(
            args.backup, args.identity.read_text(encoding="utf-8").strip(), args.into
        )
        problems = verify(folder)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"opened and verified: {folder}")
        if args.restore_to:
            psql = shlex.split(env.get("MASIRAH_PSQL", "psql"))
            for command in restore_commands(psql, args.restore_to, folder / "database"):
                run_command(command)
            print("database restored")
        if args.restore_originals:
            target = env.get("MASIRAH_RESTORE_SUPABASE_URL", "").strip()
            target_key = env.get("MASIRAH_RESTORE_SUPABASE_SECRET_KEY", "").strip()
            if not target or not target_key:
                raise BackupError(
                    "restoring originals needs MASIRAH_RESTORE_SUPABASE_URL and "
                    "MASIRAH_RESTORE_SUPABASE_SECRET_KEY"
                )
            count = upload_originals(folder / "originals", target, target_key)
            print(f"originals restored: {count}")
        return 0
    except BackupError as error:
        print(f"backup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
