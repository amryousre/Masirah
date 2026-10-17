# Backup and recovery

Masirah's hosted project is on Supabase's Free plan, which takes no backups. Our own job does instead (T110, NFR-15: a recovery point of 24 hours or better).

## What a backup holds

Each backup is one file, `masirah-backup-<UTC time>.tar.age`, encrypted to an age public key. It holds:

- **`database/data.sql`.** The data of our own schemas:
  - `public`: organisations, jobs, candidates, CV files, profiles, scores, decisions, activity, spend.
  - `private`: the waitlist and the worker's own tables.
  - `auth`: the user accounts and their sign-in identities.
- **`originals/`.** Every CV original in the `cv-originals` Storage bucket, at its original path.
- **`manifest.json`.** The SHA-256 digest of every file, and the migrations the schema came from.

The **schema** is not in the backup. A restore rebuilds it from the repository's migrations (`supabase/migrations`), then loads the data.

Supabase's own internals are left out on purpose, because a restore could not write them into a new project. Its documented full dump copies its Storage, Realtime and Auth bookkeeping, and the drill below showed that fails in three different places. The `pgmq` queues are left out as well: a file stranded in "queued" is queued again by the worker within ten minutes (migration 0018).

## The keys

- **The public key** (`MASIRAH_BACKUP_RECIPIENT`, starting `age1`) is on the PC that makes backups. It can only encrypt.
- **The private key** (`AGE-SECRET-KEY-1…`) opens backups. It is never kept on that PC.
  - Store it offline: a password manager entry, or a printed copy in a safe place.
  - **Without it, no backup can be opened.** Keep two copies.

Anyone who copies the backup folder without the private key learns nothing. A backup holds real candidate data, so where the folder lives is also a data-transfer question (ADR 0003).

## Setting it up (once)

On the PC that will make backups, from `pipeline\`:

1. **Make the key pair:**
   ```
   uv run python -m tools.backup keygen C:\path\outside\the\repo\masirah-backup.key
   ```
   It prints `MASIRAH_BACKUP_RECIPIENT=age1…`. Copy the private key file's contents into your password manager, then move the file off this PC.
2. **Fill in `pipeline\.env`.** `.env.example` describes each value.
   - `MASIRAH_BACKUP_DB_URL`: Supabase dashboard → **Connect** → **Session pooler** URL, with the database password.
   - `MASIRAH_BACKUP_SUPABASE_URL` and `MASIRAH_BACKUP_SUPABASE_SECRET_KEY`: the hosted project's URL and secret key (**Settings → API keys**).
   - `MASIRAH_BACKUP_RECIPIENT`: from step 1.
   - `MASIRAH_BACKUP_DIR`: the folder for backups. A synced folder (Google Drive, OneDrive) keeps a copy off this PC.
   - `MASIRAH_SLACK_WEBHOOK_URL`, if set, receives a message when a backup fails.
3. **Set Docker Desktop to start when you sign in.** The dump runs the pinned Supabase CLI, which needs Docker.
4. **Run one backup by hand and check it:**
   ```
   uv run --env-file .env python -m tools.backup run
   ```
5. **Schedule it:**
   ```
   powershell -ExecutionPolicy Bypass -File tools\schedule_backup.ps1
   ```
   The task runs daily at 02:00, or at the next sign-in after a missed run. It keeps the newest 30 backups. Its log is `%LOCALAPPDATA%\Masirah\backup.log`.

The recovery point is 24 hours **while this PC is used daily**. A week away from the PC means up to a week of exposure. Run a backup by hand before any planned absence.

## Checking backups

- **Log:** `%LOCALAPPDATA%\Masirah\backup.log` gains a `backup written: …` line each day.
- **Folder:** a new `masirah-backup-*.tar.age` appears daily.
- **Failures:** posted to Slack, and Task Scheduler shows a non-zero result for "Masirah backup".
- **Monthly:** open the newest backup (step 1 of the restore below) to confirm the key still opens it.

## Restoring

Restore into a **new** Supabase project, or into the existing one only after it has been emptied. Never load the data on top of live data.

1. **Open and verify the backup:**
   ```
   uv run python -m tools.backup open <backup.tar.age> --identity <private-key-file> --into <folder>
   ```
   This decrypts the backup and unpacks it into `<folder>`, refusing any path that would escape it. It then checks every file against the manifest, and stops if anything differs.
2. **Rebuild the schema** at the migrations named in `<folder>\manifest.json`. Check out the commit whose `supabase/migrations` matches that list, then:
   ```
   npx --yes supabase@2.117.0 link --project-ref <new-ref>
   npx --yes supabase@2.117.0 db push
   ```
   This creates every table, row level security policy, function, queue, the `cv-originals` bucket and the `masirah_worker` role.
3. **Load the data:**
   ```
   uv run python -m tools.backup open <backup.tar.age> --identity <key> --into <folder> --restore-to "<new project's session pooler URL>"
   ```
   This needs `psql` on PATH, or `MASIRAH_PSQL` naming one (for example `docker exec -i <container> psql`).
   - It runs one transaction with triggers off, and stops at the first error, so nothing loads half way.
   - Use a project on the **same Supabase Auth version or newer** than the source. A new hosted project is on the current one.
4. **Put the originals back** (this also recreates their Storage rows):
   ```
   set MASIRAH_RESTORE_SUPABASE_URL=https://<new-ref>.supabase.co
   set MASIRAH_RESTORE_SUPABASE_SECRET_KEY=<new project's secret key>
   uv run python -m tools.backup open <backup.tar.age> --identity <key> --into <folder> --restore-originals
   ```
5. **Reconnect the app:**
   - Point Netlify's `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, and the worker's settings, at the new project.
   - Redo Google sign-in's redirect allow list for the new project.
   - Give `masirah_worker` its login password again (migration 0013). Passwords are not in the backup.
6. **Delete the unpacked `<folder>`.** It holds the data unencrypted.

## Restore drill, 17 October 2026

The procedure above was tested end to end on a laptop.

- **Source:** the local stack, holding the e2e suite's data and a seeded "Backup Drill Ltd" organisation with two synthetic CV originals (`syn-ar-native-01.pdf`, `-02.pdf`). That was 17 tables and 2,388 rows.
- **Backup:** `tools.backup run` against the source made a 4 MB encrypted file in 13 s. It was opened and verified with the private key.
- **Target:** a second local Supabase stack, wiped and started on the hosted project's service versions (Auth v2.197.0, Postgres 17.6.1.127). All 28 migrations were applied (step 2).
- **Data:** loaded with `restore_commands` through the target container's `psql`. Exit 0.
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

Repeat the drill after any change to the tool, to the migrations' handling of `auth` or `storage`, or to the Supabase CLI version.
