# Backup and recovery

Masirah's hosted project is on Supabase's Free plan, which takes no backups. Our own job does instead (T110, NFR-15: a recovery point of 24 hours or better).

## What a backup holds

Each backup is one file, `masirah-backup-<UTC time>.tar.age`, encrypted to an age public key. It holds:

- **`database/data.sql`.** The data of our own schemas:
  - `public`: organisations, jobs, candidates, CV files, profiles, scores, decisions, activity, spend.
  - `private`: the waitlist and the worker's own tables.
  - `auth`: the user accounts and their sign-in identities.
- **`originals/`.** Every CV original in the `cv-originals` Storage bucket, at its original path.
- **`manifest.json`.** It records:
  - the SHA-256 digest of every file;
  - **the migrations the database was at**, read from the database itself;
  - any original deleted while the backup ran.

The **schema** is not in the backup. A restore rebuilds it from those migrations, then loads the data.

Supabase's own internals are left out on purpose, because a restore could not write them into a new project. Its documented full dump copies its Storage, Realtime and Auth bookkeeping, and the drill below showed that fails in three different places. The `pgmq` queues are left out as well: a file stranded in "queued" is queued again by the worker within ten minutes (migration 0018).

## The keys

- **The public key** (`MASIRAH_BACKUP_RECIPIENT`, starting `age1`) is on the PC that makes backups. It can only encrypt.
- **The private key** (`AGE-SECRET-KEY-1…`) opens backups. It is never kept on that PC.
  - Store it offline: a password manager entry, or a printed copy in a safe place.
  - **Without it, no backup can be opened.** Keep two copies.

Anyone who copies the backup folder without the private key learns nothing. Anyone with the *public* key could plant a backup-shaped file in the folder, so only restore files you know this job made.

A backup holds real candidate data, so where the folder lives is also a data-transfer question (ADR 0003).

## Backups and deletion requests

A candidate's data must be gone within 30 days of a deletion request (FR-076). The purge removes it from the live database within the hour. Backups keep the newest **28** days, so the last backup holding that candidate is deleted by day 29.

If you restore an older backup, **reapply every deletion made since it was taken**:
1. Read the "candidate.deletion_requested" activity in the live project, if it is still reachable, or your own records.
2. Request those deletions again in the restored project.

## Setting it up (once)

All commands are for **PowerShell**.

1. **Make a checkout that stays on `main`.** The job runs code and reads settings from it, so it must not follow your work across branches. From your normal checkout:
   ```
   git worktree add C:\Masirah-backup main
   cd C:\Masirah-backup\pipeline
   uv sync
   ```
   After each merge, update it with `git -C C:\Masirah-backup pull`.
2. **Make the key pair**, from `C:\Masirah-backup\pipeline`:
   ```
   uv run python -m tools.backup keygen C:\path\outside\the\repo\masirah-backup.key
   ```
   It prints `MASIRAH_BACKUP_RECIPIENT=age1…`. Copy the private key file's contents into your password manager, then delete the file from this PC.
3. **Create `C:\Masirah-backup\pipeline\.env`.** `.env.example` describes each value.
   - `MASIRAH_BACKUP_DB_URL`: Supabase dashboard → **Connect** → **Session pooler** URL, with the database password. The password must not contain `& | ^ < > % ! "`, because the Windows command line changes them. The tool refuses such a URL.
   - `MASIRAH_BACKUP_SUPABASE_URL` and `MASIRAH_BACKUP_SUPABASE_SECRET_KEY`: the hosted project's URL and secret key (**Settings → API keys**).
   - `MASIRAH_BACKUP_RECIPIENT`: from step 2.
   - `MASIRAH_BACKUP_DIR`: the folder for backups. A synced folder (Google Drive, OneDrive) keeps a copy off this PC.
   - `MASIRAH_SLACK_WEBHOOK_URL`, if set, receives a message when a backup fails, or when the last one is more than a day old.
4. **Set Docker Desktop to start when you sign in.** The dump runs the pinned Supabase CLI, which needs Docker. A run waits up to ten minutes for Docker to come up.
5. **Run one backup by hand and check it:**
   ```
   $env:PYTHONUTF8 = "1"
   uv run --env-file .env python -m tools.backup run
   ```
6. **Schedule it, then run the scheduled task once and read its log:**
   ```
   powershell -ExecutionPolicy Bypass -File tools\schedule_backup.ps1
   Start-ScheduledTask -TaskName "Masirah backup"
   Get-Content $env:LOCALAPPDATA\Masirah\backup.log -Tail 5
   ```
   The log must end with `backup written: …`.
   - The task runs daily at 02:00, or at the next sign-in after a missed run, on battery as well.
   - It keeps the newest 28 backups.

The recovery point is 24 hours **while this PC is used daily**. A week away from the PC means up to a week without a backup. The first run after it says how old the last backup was, and posts that to Slack. Run a backup by hand before any planned absence.

## Checking backups

- **Log:** `%LOCALAPPDATA%\Masirah\backup.log` gains a timestamped `backup written: …` line each day. A failure leaves a timestamped reason, followed by the last lines of the failing command's own output, with the database URL and password removed.
- **Folder:** a new `masirah-backup-*.tar.age` appears daily.
- **Slack:** gets a message on any failure, and when the last backup is more than a day old.
- **Task Scheduler:** shows a non-zero result for "Masirah backup" on failure.
- **Monthly:** open the newest backup (restore step 1) to confirm the key still opens it.

## Restoring

Restore into a **new** Supabase project, or into the existing one only after it has been emptied. Never load the data on top of live data. All commands are for **PowerShell**, run from `pipeline\` of a checkout. Secrets go in variables, not on the command line, so they stay out of your shell's history.

1. **Open and verify the backup:**
   ```
   uv run python -m tools.backup open <backup.tar.age> --identity <private-key-file> --into <folder>
   ```
   This decrypts the backup and unpacks it into `<folder>`, refusing any path that would escape it. It then checks every file against the manifest, and stops if anything differs.
2. **Rebuild the schema** at the migrations listed under `"migrations"` in `<folder>\manifest.json`. Check out the commit whose `supabase\migrations` holds exactly that list (`git log -- supabase/migrations` finds it), then:
   ```
   npx --yes supabase@2.117.0 link --project-ref <new-ref>
   npx --yes supabase@2.117.0 db push
   ```
   This creates every table, row level security policy, function, queue, the `cv-originals` bucket and the `masirah_worker` role.
3. **Load the data.** You need `psql`:
   - either the PostgreSQL 17 client, with `$env:MASIRAH_PSQL = "C:\Program Files\PostgreSQL\17\bin\psql.exe"`;
   - or Docker, with `$env:MASIRAH_PSQL = "docker run --rm -i postgres:17 psql"`.

   The data goes to psql on stdin, so either works. Then:
   ```
   $env:MASIRAH_RESTORE_DB_URL = Read-Host "New project's session pooler URL"
   uv run python -m tools.backup open <backup.tar.age> --identity <key> --into <folder> --restore-database
   ```
   - It runs one transaction with triggers off, and stops at the first error, so nothing loads half way.
   - Use a project on the **same Supabase Auth version or newer** than the source. A new hosted project is on the current one.
4. **Put the originals back** (this also recreates their Storage rows):
   ```
   $env:MASIRAH_RESTORE_SUPABASE_URL = "https://<new-ref>.supabase.co"
   $env:MASIRAH_RESTORE_SUPABASE_SECRET_KEY = Read-Host "New project's secret key"
   uv run python -m tools.backup open <backup.tar.age> --identity <key> --into <folder> --restore-originals
   ```
5. **Reconnect everything to the new project:**
   - **Auth:**
     - Enable the Google provider, with the client ID and secret from the root `.env`.
     - Add `https://<new-ref>.supabase.co/auth/v1/callback` to the OAuth client in Google Cloud (project `masirah`).
     - Set the Site URL to `https://masirah.online`.
     - Set the redirect allow list, the same as in `supabase/config.toml`.
     - **Close sign-ups again.** A new project allows them by default.
   - **Web (Netlify):** `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, then redeploy.
   - **Worker:** `MASIRAH_DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. Give `masirah_worker` its login password again (migration 0013); passwords are not in the backup.
   - **This backup job:** set the `MASIRAH_BACKUP_*` values in `C:\Masirah-backup\pipeline\.env` to the new project. Otherwise the next run backs up the old one, or fails.
   - **Deletions:** reapply any deletion requested since the backup (see "Backups and deletion requests").
6. **Delete the unpacked `<folder>`** and clear the `$env:MASIRAH_RESTORE_*` variables. The folder holds the data unencrypted.

## Restore drill, 17 October 2026

The procedure above was tested end to end on a laptop.

- **Source:** the local stack, holding the e2e suite's data and a seeded "Backup Drill Ltd" organisation with two synthetic CV originals (`syn-ar-native-01.pdf`, `-02.pdf`). That was 17 tables and 2,388 rows.
- **Backup:** `tools.backup run` against the source made a 4 MB encrypted file in 13 s. It was opened and verified with the private key.
- **Target:** a second local Supabase stack, wiped and started on the hosted project's service versions (Auth v2.197.0, Postgres 17.6.1.127). All 28 migrations were applied (step 2).
- **Data:** `data.sql` was loaded with the tool's restore command through the target container's `psql`. Exit 0.
- **Originals:** restored with `--restore-originals`. Both uploaded.
- **Result:**
  - The row counts of all 17 tables in `public`, `private`, `auth.users` and `auth.identities` matched the source exactly.
  - The drill organisation was present.
  - Both originals downloaded from the target were byte-identical to the source (SHA-256).

What the drill changed before it passed:

1. On Windows, `npx` is `npx.cmd`, so commands are now found on PATH the way the shell finds them.
2. The first design dumped Supabase's documented roles, schema and data. Restoring that into a clean project failed three times, in a new place each time:
   - a parameter grant only `supabase_admin` may make;
   - Auth tables of a newer version;
   - Storage's internal `buckets_vectors` table.

   The design changed to our own data on top of the migrated schema, as described above.

The code review that followed found that the scheduled task could not start Python at all: cmd kept a space in `set PYTHONUTF8=1 &&`. The task's exact command line has since been run through `cmd.exe` and starts the tool. Setup step 6 runs the registered task once, so that path is checked on every installation.

Repeat the drill after any change to the tool, to the migrations' handling of `auth` or `storage`, or to the Supabase CLI version. **Before pilot data arrives, repeat it against the hosted project**: back it up, restore it into a fresh project, and compare.
