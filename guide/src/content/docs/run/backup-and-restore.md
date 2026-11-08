---
title: Back up and restore
description: Protect the database and source files, rehearse recovery, and restore a consistent installation.
reader: operator
---

Back up PostgreSQL, the job-file volume and the configuration needed to read them. The database holds
all workspaces, records, history, change sets, publications, installed models, jobs, subscriptions and
feeds. Model-authoring source files live in `JOB_FILE_DIR`, outside PostgreSQL. Protect backups as
sensitive data, with encryption keys stored securely outside the database.

Keep the application version, `DATABASE_URL`, `RDM_MODEL_PATH`, capability settings, worker count,
`RDM_CURSOR_SIGNING_KEY` and `SECRETS_ENCRYPTION_KEY` with each recovery record. Losing the sealing
key makes stored secrets unreadable. Backups made before a key change need the old key.

The Compose installation also has an `assistant` volume for task working folders and an
`assistant-claude` volume for Claude Code configuration and session logs. They mount at
`/opt/refiroo/rdm-engine/data/assistant` and `/opt/refiroo/rdm-engine/data/assistant-claude`.
A backup need not include these two volumes: losing them loses open tasks’ folders and session
logs, not records. The database and job-file backup below does not copy them; after restoring
without them, open tasks may lack the files they need to continue.

## Take a database backup

From the repository root of the reference installation:

```bash
docker compose exec -T database pg_dump -U rdm -d rdm -Fc \
  --exclude-table-data=engine_processes > refiroo-backup.dump
```

Check the command's exit status and retain only a successful dump as a backup. Use unique names
for successive backups. Omitting process heartbeat rows avoids showing old processes as silent
after a restore; dumps containing them still restore.
Arrange a consistent copy or snapshot of `job-files` alongside it, quiescing file-changing work
while taking that pair. Do not treat a database dump alone as a backup of source workbooks.

## Rehearse in a separate database

Use PostgreSQL client tools and an administrative account allowed to create and drop a scratch
database. The engine's runtime role should not need that privilege. The following is for a configured
backend environment with network access to the same database server; substitute its connection
options and your dump name. These host commands do not read Compose's `.env` automatically.
Set the live instance's `DATABASE_URL` and original key securely before running the check.

```bash
createdb -T template0 --locale-provider=icu --icu-locale=und --locale=C rdm_restore_check
pg_restore --no-owner -d rdm_restore_check refiroo-backup.dump
cd backend
.venv/bin/python -m app.cli.restore_check \
  --restored postgresql+psycopg://rdm@db/rdm_restore_check \
  --backup refiroo-backup.dump
```

Use a restored URL that actually reaches that scratch database. Supply passwords securely, never
as literal secrets in shell history. Stop if restoration fails. The check must target the copy,
while `DATABASE_URL` continues naming the live instance where its result is recorded.
It refuses the live database as the restored target.

The check prepares and may migrate the copy, clears old process rows, and tries each active
workspace's model. It compares workspace counts with the live instance. It does not validate every
record again or require counts to match a live instance that has changed since the backup.

| Exit | Meaning and action |
| --- | --- |
| `0` | Copy prepared and every active workspace served. Record the result and remove the scratch database. |
| `1` | Check failed. Follow its collation, extension, revision, migration, connectivity or workspace reason; preserve needed diagnostics before removing the copy. |
| `2` | Nothing checked: wrong target, non-PostgreSQL URL or unreachable live instance. Correct the configuration and repeat. |

After inspection, remove only the scratch database, using the same server connection options:

```bash
dropdb rdm_restore_check
```

Open **Settings › Administration › Operations › Last backup rehearsal**. Before the first check,
**No backup has been rehearsed** means no result has been recorded. After a check it shows **Passed**
or **Failed**, the backup name when supplied, the copy's revision and the workspace results.
**Records**, **Relationships**, **Open change sets** and **Publications** count the restored copy;
**Live now** compares the current instance. Different counts alone do not fail the check.

Use **Show earlier rehearsals (N)** to expand older results, **Load more rehearsals** when offered,
and **Hide earlier rehearsals** to collapse them. **How to rehearse a restore** gives the command
sequence; it does not execute it. Nothing on Operations runs a restore.

| Failure code | Safe next step |
| --- | --- |
| `DATABASE_COLLATION` | Recreate the scratch database with ICU root `und`, restore and check again. |
| `DATABASE_EXTENSIONS` | Install the required extensions in the copy or allow the preparation role to do so. |
| `DATABASE_REVISION_UNKNOWN` | Use the engine version that understands the backup's revision. |
| `DATABASE_MIGRATION_FAILED` | Preserve the diagnostic, resolve the reported migration cause, then repeat on a fresh copy. |
| `DATABASE_UNREACHABLE` | Correct the copy's server address, credentials or network access. |
| `DATABASE_URL_INVALID` | Correct the restored database URL before retrying. |
| `WORKSPACES_NOT_SERVED` | Inspect each failed workspace's release. Use a compatible engine or resolve its model before relying on that backup for recovery. |

Keep the failure result as evidence and repeat the rehearsal after correcting its cause. For local development, `scripts/postgres.sh backup` and
`scripts/postgres.sh rehearse` automate the private server's backup, restore check and scratch cleanup.

![Operations before the first backup rehearsal, showing No backup has been rehearsed](/docs/screens/run-backup-rehearsal.png)

## Recover the installation

1. Stop every engine process and prevent traffic and integrations from writing.
2. Create a replacement database with ICU root `und`, or empty the recovery target deliberately.
   Restore the dump there with `pg_restore --no-owner` using PostgreSQL client tools.
3. Restore the matching source-file volume and configuration, including the backup's encryption key.
   Point `DATABASE_URL` to the recovery database; do not change a database password merely by editing `.env`.
4. Start the application version kept with the backup, or a compatible newer one that migrates it.
5. Check readiness, every active workspace, sign-in and needed files before reopening traffic.

For a host or custom installation, `DATABASE_URL` selects the recovery database. In the reference
Compose file it is constructed from the database service and `POSTGRES_PASSWORD`: a
`DATABASE_URL` line in `.env` does not override it. Recover the service's `rdm` database and its
matching volumes, or explicitly adapt your deployment configuration to the replacement database
before starting engines. Preserve the old volume until the recovery has been checked.

A restore replaces the whole database. Activating an older model, withdrawing a publication or
starting a change set from an earlier publication does not restore data. For partial recovery, read
the desired records from a restored copy and write reviewed changes through the API or a change set.
Recovery time and production backup sizing for your installation are **not measured**; rehearse your
own data and record the result.

## Make a consistent database and file backup with Compose

For the reference installation, you need Docker access, free space outside the named volumes and
a maintenance window. The database image supplies PostgreSQL 17 client tools; the engine image
supplies Python for archiving its mounted job files. The commands below use the standard Compose
file and a new host directory. Choose a unique directory for every backup. Keep traffic and all
external writers closed until the engine is started again.

1. Create a private backup directory and stop all file-changing engine work. The database stays up:

   ```bash
   umask 077
   mkdir -p backups/before-maintenance
   docker compose stop engine
   ```

   In a multi-instance installation, stop every engine using this database and file directory.
   Verify the stop completed. Background work stops too; an interrupted chunk is rolled back or
   recovered under its lease. No browser or integration should write directly to the database.
2. Dump the database, then archive the unchanged file volume:

   ```bash
   docker compose exec -T database pg_dump -U rdm -d rdm -Fc    \
     --exclude-table-data=engine_processes      > backups/before-maintenance/database.dump
   docker compose run --rm --no-deps -T engine python -c    \
     'import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode="w|"); t.add("/opt/refiroo/rdm-engine/data/job-files",arcname="."); t.close()'      > backups/before-maintenance/job-files.tar
   ```

   Both commands are silent on success and must exit 0. Check each status before proceeding.
   Redirection can leave a partial file after failure; do not label that file a successful backup.
   A database dump and file archive made while every engine is stopped represent one unchanged
   application state. No running file cleanup can remove inputs between the two copies.
3. Keep the matching private environment securely, and write the source/application version into
   your recovery record. For the default settings file:

   ```bash
   cp .env backups/before-maintenance/installation.env
   chmod 600 backups/before-maintenance/installation.env
   tar -tf backups/before-maintenance/job-files.tar
   ```

   Expect relative file paths, or only `.` for an empty job directory. Put encryption keys in
   separately controlled storage, outside the database backup, and associate their version with
   this recovery record. Preserve any custom bootstrap files and valid TLS materials too. With
   automatic HTTPS, preserve the `caddy-data` volume using your storage platform's backup process.
4. Resume normal operation with `docker compose up -d engine`, check readiness and sign-in, then
   reopen writers. Copy the backup off the application host into your protected backup storage.
   Rehearse before relying on it. Backup schedule, disk minimums, offsite retention and recovery
   duration are **not measured** for your organisation.

## Rehearse the reference dump inside Compose

These commands create only `rdm_restore_check`. Confirm that name is unused before starting;
do not substitute `rdm`, the live database. The reference PostgreSQL account initializes the server
and can create the scratch database; a custom runtime role should not be given that privilege
merely for this task.

```bash
docker compose exec -T database createdb -U rdm -T template0 \
  --locale-provider=icu --icu-locale=und --locale=C rdm_restore_check
docker compose exec -T database pg_restore -U rdm --no-owner --exit-on-error \
  -d rdm_restore_check < backups/before-maintenance/database.dump
```

Stop on either failure. A successful restore finishes with exit 0. Then run the checker in the
engine image, deriving the scratch URL from its configured connection without writing the password
in a command argument:

```bash
docker compose run --rm -T engine python -c \
  'from app.db import configured_url; from app.cli.restore_check import main; raise SystemExit(main(["--restored",configured_url().set(database="rdm_restore_check").render_as_string(hide_password=False),"--backup","before-maintenance/database.dump"]))'
```

Expect `Backup rehearsal passed.`, each workspace's model and counts, and
`Recorded in the instance (Settings › Operations). Delete the copy when done.`
The recorded result belongs to the live instance. The checker changes/prepares only the restored
copy's schema and records the result in live; it does not activate the copy as the live database.
Its database/model check does **not** verify the file archive: inspect the archive and separately
exercise needed source/download files during your isolated recovery trial.

After reading the result, remove the scratch database:

```bash
docker compose exec -T database dropdb -U rdm rdm_restore_check
```

A failed rehearsal is evidence that recovery needs work. Keep its recorded failure and diagnostics,
correct the cause and retry from a fresh scratch restore; do not switch production to a failed copy.

## Restore on a replacement host

The safest whole-instance recovery keeps the old host and volumes untouched, isolated from
writers, while a replacement is checked. On that host, obtain the matching source version,
Compose files, private configuration and backup pair. Use the same project and environment-file
selection as the original; then:

:::caution[Automatic HTTPS needs both Compose files]
If the original used [automatic HTTPS](/docs/run/install-with-compose/#5-start-with-automatic-https),
set `COMPOSE_FILE=compose.yml:compose.acme.yml` in the replacement host's shell before these steps,
and restore the `caddy-data` volume too if you have it. Without `compose.acme.yml`, web starts
without Caddy in front and the site does not answer.
:::

1. Restore the protected configuration to `.env`, restore certificate files if using file mode,
   and make sure DNS/traffic still cannot send production users to the replacement.
2. Start only PostgreSQL: `docker compose up -d database`. Wait for its health check.
   An empty reference volume creates an empty `rdm` database with the required collation.
3. Restore into that **empty replacement** database:

   ```bash
   docker compose exec -T database pg_restore -U rdm --no-owner --exit-on-error    \
     -d rdm < backups/before-maintenance/database.dump
   ```

4. Build the matching engine image with `docker compose build engine` before restoring files.
   On a fresh host this downloads dependencies and prints build progress; wait for success.
   Restore the matching file archive with the engine stopped:

   ```bash
   docker compose run --rm --no-deps -T engine python -c    \
     'import sys,tarfile; t=tarfile.open(fileobj=sys.stdin.buffer,mode="r|*"); t.extractall("/opt/refiroo/rdm-engine/data/job-files",filter="data"); t.close()'      < backups/before-maintenance/job-files.tar
   ```

   Use only your trusted backup archive. The command runs as the engine user and must exit 0.
   The archive is extracted into a new job-file volume; do not overlay it on unrelated newer files.
5. Start the matching images with `docker compose up -d --build` (with automatic HTTPS, with both
   Compose files, as in [Upgrades](/docs/run/upgrades/#upgrade-the-compose-installation)), inspect bounded engine logs,
   readiness, every workspace, sign-in and important files. Review integrations before reconnecting
   them: external receivers can already hold events sent after the backup, so reconcile them rather
   than assuming their state rolled back too.
6. Only after those checks move traffic and reopen writers. Keep the old host isolated and retained
   until recovery is accepted. Switching back after new writes requires another reconciliation or
   recovery decision; it is not a lossless automatic undo.

Restoring into a populated database causes conflicts; stop and prepare a deliberate empty recovery
target instead of ignoring errors. A wrong encryption key may allow database restore yet prevent
sign-in or stored-secret use: supply the key associated with that backup. Never generate a new key
as a recovery shortcut. Whole-instance recovery reverts data written after the backup.
