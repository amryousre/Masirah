"""Daily encrypted backups of the hosted project, and opening one to restore it (T110, NFR-15).

The project is on Supabase's Free plan, which takes no backups of its own. Run from pipeline/ with
the settings in .env (see .env.example), once a day by Windows Task Scheduler
(tools/schedule_backup.ps1):

    uv run --env-file .env python -m tools.backup run
    uv run python -m tools.backup keygen <private-key-file>
    uv run python -m tools.backup open <backup> --identity <private-key-file> --into <folder>

A backup is the data of our own schemas (public, private, and auth for the accounts), dumped by
the pinned Supabase CLI, which needs Docker, and every CV original in Storage, with a manifest of
SHA-256 digests and of the migrations the database was at, in one tar archive encrypted to an age
public key. The machine that makes backups holds only the public key. The private key is kept
offline, so a copied backup folder reveals nothing.

The unencrypted work happens in a scratch folder on the local disk, never in the backup folder,
which may sync to the cloud. It is removed when the run ends, and a run cut short is cleared by
the next. The newest KEPT backups are kept. A failure, and a last backup more than a day old, are
posted to the operators' Slack channel when MASIRAH_SLACK_WEBHOOK_URL is set; a failure also exits
non-zero, which Task Scheduler records. No message carries a credential: the database URL holds
the password, so a failed command's own output goes to the log only, with the URL and password
removed.

The restore procedure, and the drill that tested it, are in Docs/runbooks/backup-recovery.md.
"""

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import quote, unquote, urlsplit

import httpx2
import psycopg
import pyrage

from masirah_pipeline.adapters.slack_webhook import SlackWebhook
from masirah_pipeline.adapters.supabase_storage import BUCKET, SupabaseStorage
from masirah_pipeline.ports.cv_store import MissingCvError

# FR-076: a candidate's data goes within 30 days of the request. The purge runs within the hour, so
# the last backup holding a deleted candidate is pruned KEPT days later, inside the 30.
KEPT = 28
PATTERN = "masirah-backup-*.tar.age"
SCRATCH_PREFIX = "masirah-backup-"
SUPABASE_CLI = ["npx", "--yes", "supabase@2.117.0"]
TIMEOUT = 60
STALE_HOURS = 26
# npx is a batch file, so cmd reads its arguments again, and these would cut or change the URL.
CMD_SPECIAL = set('&|^<>%!"')
STDERR_LINES = 20

Runner = Callable[[Sequence[str]], None]
Alert = Callable[[str], None]


class BackupError(Exception):
    """A backup or a restore could not be completed. The message never holds a credential and
    may go to Slack; `detail` is for the log only, with credentials already removed."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail


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
    """The backup's settings, each checked before any work starts. A message names the setting,
    never its value."""
    missing = [name for name in REQUIRED if not environment.get(name, "").strip()]
    if missing:
        raise BackupError(f"the backup needs {', '.join(missing)}")
    read = {field: environment[name].strip() for name, field in REQUIRED.items()}
    if CMD_SPECIAL & set(read["db_url"]):
        raise BackupError(
            'MASIRAH_BACKUP_DB_URL holds one of & | ^ < > % ! ", which the Windows command line '
            "changes: choose a database password without them"
        )
    try:
        pyrage.x25519.Recipient.from_str(read["recipient"])
    except pyrage.RecipientError:
        raise BackupError("MASIRAH_BACKUP_RECIPIENT is not an age public key (age1...)") from None
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


def restore_command(psql: Sequence[str], db_url: str) -> list[str]:
    """Loads data.sql, given on stdin, into a database already migrated to the manifest's
    migrations: one transaction, stopping at the first error, with triggers off while it loads."""
    return [
        *psql,
        *["--single-transaction", "--variable", "ON_ERROR_STOP=1"],
        *["--command", "SET session_replication_role = replica"],
        *["--file", "-", "--dbname", db_url],
    ]


def applied_migrations(db_url: str) -> list[str]:
    """The migrations the database itself records as applied, not those of whatever branch this
    checkout is on: a restore rebuilds the schema at exactly these."""
    with psycopg.connect(db_url) as connection:
        rows = connection.execute(
            "select version, coalesce(name, '') from supabase_migrations.schema_migrations"
            " order by version"
        ).fetchall()
    return [f"{version}_{name}" if name else str(version) for version, name in rows]


def list_originals(
    base_url: str, secret_key: str, *, client: httpx2.Client | None = None, page: int = 1000
) -> list[str]:
    """Every object in the originals bucket. Storage lists one folder at a time, and an entry
    without an id is a folder."""
    with client or httpx2.Client(timeout=TIMEOUT) as http:
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


def _redacted(text: str, secrets: Sequence[str]) -> str:
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    return text


def secrets_of(db_url: str) -> list[str]:
    """The URL and its password, in the forms a tool's output may repeat them."""
    password = urlsplit(db_url).password or ""
    return [db_url, password, unquote(password)]


def run_command(
    command: Sequence[str], *, stdin: Path | None = None, secrets: Sequence[str] = ()
) -> None:
    """Runs a command. A failure is reported by exit code; the last lines it wrote go to the log
    only, with every secret removed. The program is found on PATH as the shell would find it, so
    npx.cmd runs on Windows."""
    program = shutil.which(command[0])
    if program is None:
        raise BackupError(f"{command[0]} was not found on PATH")
    with (stdin if stdin is not None else Path(os.devnull)).open("rb") as given:
        completed = subprocess.run(  # noqa: S603
            [program, *command[1:]], check=False, capture_output=True, stdin=given
        )
    if completed.returncode != 0:
        said = (completed.stderr or completed.stdout).decode("utf-8", errors="replace")
        tail = "\n".join(said.strip().splitlines()[-STDERR_LINES:])
        raise BackupError(
            f"{PurePosixPath(command[0]).name} exited with {completed.returncode}",
            detail=_redacted(tail, secrets),
        )


def docker_running() -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    return subprocess.run([docker, "info"], check=False, capture_output=True).returncode == 0  # noqa: S603


def wait_for_docker(
    check: Callable[[], bool] = docker_running,
    *,
    attempts: int = 40,
    pause: float = 15,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Waits for Docker, which the dump needs: a run missed overnight starts at sign-in, while
    Docker Desktop is still starting. Ten minutes by default."""
    for attempt in range(attempts):
        if check():
            return
        if attempt < attempts - 1:
            sleep(pause)
    raise BackupError("Docker is not running, and the database dump needs it")


def _inside(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise BackupError(f"a stored path leaves the backup: {relative!r}")
    return target


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clear_stale_scratch(scratch_root: Path) -> None:
    """Removes the work of a run cut short by power loss, sleep or a time limit, which `finally`
    never reached: it holds the data and every CV, unencrypted."""
    for left in scratch_root.glob(f"{SCRATCH_PREFIX}*"):
        if left.is_dir():
            shutil.rmtree(left, ignore_errors=True)


def _age_hours(destination: Path, now: datetime) -> int | None:
    newest = max(destination.glob(PATTERN), default=None)
    if newest is None:
        return None
    stamp = newest.name.removeprefix("masirah-backup-").removesuffix(".tar.age")
    try:
        made = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return int((now - made).total_seconds() // 3600)


def _tell(alert: Alert | None, text: str) -> None:
    """Posts to the operators. Slack being down must never hide what it was told."""
    if alert is None:
        return
    try:
        alert(text)
    except Exception as error:  # any failure to post is only logged
        print(f"backup: the alert could not be posted ({type(error).__name__})", file=sys.stderr)


def run_backup(
    settings: BackupSettings,
    *,
    run: Runner | None = None,
    originals: Originals | None = None,
    now: datetime | None = None,
    scratch: Path | None = None,
    alert: Alert | None = None,
    cli: Sequence[str] = SUPABASE_CLI,
    ready: Callable[[], None] = wait_for_docker,
    read_migrations: Callable[[], list[str]] | None = None,
) -> Path:
    """Makes one backup in the destination folder and returns it."""
    moment = now or datetime.now(UTC)
    stamp = moment.strftime("%Y%m%dT%H%M%SZ")
    dump = run or (lambda command: run_command(command, secrets=secrets_of(settings.db_url)))
    migrations = read_migrations or (lambda: applied_migrations(settings.db_url))
    store = originals or StorageOriginals(settings.storage_url, settings.secret_key)
    scratch_root = scratch or Path(tempfile.gettempdir())
    scratch_root.mkdir(parents=True, exist_ok=True)
    _clear_stale_scratch(scratch_root)

    age = _age_hours(settings.destination, moment)
    if age is not None and age > STALE_HOURS:
        _tell(alert, f"Masirah backup: the last backup is {age} hours old; making one now.")

    work = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX, dir=scratch_root))
    try:
        ready()
        content = work / "content"
        database = content / "database"
        database.mkdir(parents=True)
        for command in dump_commands(cli, settings.db_url, database):
            dump(command)
        stored = content / "originals"
        gone: list[str] = []
        for storage_path in store.paths():
            target = _inside(stored, storage_path)
            try:
                data = store.fetch(storage_path)
            except MissingCvError:
                # Deleted between listing and reading, as a purge does: its rows go with it.
                gone.append(storage_path)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        files = sorted(p for p in content.rglob("*") if p.is_file())
        manifest = {
            "made_at": stamp,
            "migrations": migrations(),
            "gone_during_backup": sorted(gone),
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

        # Only the sealed file reaches the destination. It is copied under a name no backup has
        # and then renamed, so a copy cut short never passes for a backup.
        settings.destination.mkdir(parents=True, exist_ok=True)
        made = settings.destination / f"masirah-backup-{stamp}.tar.age"
        partial = settings.destination / f".{made.name}.partial"
        shutil.copyfile(sealed, partial)
        partial.replace(made)
        prune(settings.destination, KEPT)
        return made
    except Exception as error:
        reason = str(error) if isinstance(error, BackupError) else type(error).__name__
        _tell(alert, f"Masirah backup failed: {reason}")
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
    except tarfile.FilterError as error:
        raise BackupError(f"the backup holds an unsafe path ({type(error).__name__})") from None
    except (pyrage.DecryptError, pyrage.IdentityError, tarfile.TarError, OSError) as error:
        raise BackupError(f"the backup could not be opened ({type(error).__name__})") from None
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


# The types the bucket accepts (migration 0009), by suffix: Windows' own table may not know .docx.
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def upload_originals(
    folder: Path, base_url: str, secret_key: str, *, client: httpx2.Client | None = None
) -> int:
    """Puts every original under `folder` back in the bucket at the same path, replacing any
    there; returns how many. The database's own rows for them come back with data.sql."""
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    with client or httpx2.Client(timeout=TIMEOUT) as http:
        for path in files:
            relative = path.relative_to(folder).as_posix()
            url = f"{base_url.rstrip('/')}/storage/v1/object/{BUCKET}/{quote(relative)}"
            media_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
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
                raise BackupError(
                    f"storage could not be reached ({type(error).__name__})"
                ) from None
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


def psql_from(environment: Mapping[str, str]) -> list[str]:
    """MASIRAH_PSQL, read the way Windows quotes a command, so C:\\pg\\bin\\psql.exe survives."""
    parts = shlex.split(environment.get("MASIRAH_PSQL", "psql"), posix=False)
    return [part.strip('"') for part in parts]


def main(argv: Sequence[str] | None = None, environment: Mapping[str, str] | None = None) -> int:
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
    opened.add_argument(
        "--restore-database",
        action="store_true",
        help="also load the data into MASIRAH_RESTORE_DB_URL, already migrated",
    )
    opened.add_argument(
        "--restore-originals",
        action="store_true",
        help="also upload the originals to MASIRAH_RESTORE_SUPABASE_URL",
    )
    args = parser.parse_args(argv)
    webhook = env.get("MASIRAH_SLACK_WEBHOOK_URL", "").strip()
    alert = SlackWebhook(webhook).send if webhook else None

    try:
        if args.command == "keygen":
            public = keygen(args.private_key_file)
            print(f"MASIRAH_BACKUP_RECIPIENT={public}")
            print(f"Move {args.private_key_file} somewhere offline. Without it, no backup opens.")
            return 0
        if args.command == "run":
            try:
                settings = settings_from(env)
            except BackupError as error:
                _tell(alert, f"Masirah backup failed: {error}")
                raise
            made = run_backup(settings, alert=alert)
            print(f"{datetime.now(UTC).isoformat()} backup written: {made}")
            return 0
        try:
            identity = args.identity.read_text(encoding="utf-8").strip()
        except OSError:
            raise BackupError(f"the private key file could not be read: {args.identity}") from None
        folder = open_backup(args.backup, identity, args.into)
        problems = verify(folder)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"opened and verified: {folder}")
        if args.restore_database:
            target_db = env.get("MASIRAH_RESTORE_DB_URL", "").strip()
            if not target_db:
                raise BackupError("restoring the database needs MASIRAH_RESTORE_DB_URL")
            run_command(
                restore_command(psql_from(env), target_db),
                stdin=folder / "database" / "data.sql",
                secrets=secrets_of(target_db),
            )
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
        print(f"{datetime.now(UTC).isoformat()} backup: {error}", file=sys.stderr)
        if error.detail:
            print(error.detail, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
