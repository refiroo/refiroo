---
title: Upgrade refiroo
description: Back up, migrate, check model compatibility, and cut over safely.
reader: operator
---

Upgrade the application with its matching source and images. Before changing a running installation,
read the target version's compatibility and model-language notes. The database schema and a model's
schema language are separate: a successful database migration does not prove every workspace's
model can be served.

## Upgrade the Compose installation

:::caution[Automatic HTTPS needs both Compose files]
With [automatic HTTPS](/docs/run/install-with-compose/#5-start-with-automatic-https), run every command in these steps with
`compose.acme.yml` too: keep `COMPOSE_FILE=compose.yml:compose.acme.yml` set in the shell, or add
`-f compose.yml -f compose.acme.yml` to each command. Without it, web is recreated without Caddy
in front and the site stops answering until you run the command again with both files.
:::

1. Stop or quiesce writers, including integrations. Preserve the current application version,
   environment file, model input and file volume, and [back up and rehearse a restore](/docs/run/backup-and-restore/).
   Keep the encryption and cursor keys associated with that backup.
2. Stop the old engine and build the target version's images, using the same Compose files and
   environment as your installation:

   ```bash
   docker compose stop engine
   docker compose build
   docker compose run --rm engine python -m app.cli.database_upgrade
   ```

3. Read the migration result before accepting traffic. On failure, the command exits 1 and reports
   the database without credentials, current and target revisions, cause and recovery steps.
   The migration run uses one PostgreSQL transaction; a failed or interrupted run leaves the
   database at the revision it held before that run. Preserve the backup, correct the cause and retry the explicit command.
4. Start the new images:

   ```bash
   docker compose up -d --build
   docker compose logs --tail=100 engine
   ```

5. Check **Settings › Administration › Deployment › Database › Migration revision** against the
   migrated version, then `/health` and **Settings › Administration › Operations**. Check every active workspace,
   not only overall readiness. Verify sign-in and a representative read before reopening writers.

Startup also migrates automatically. The explicit command exposes failure before cutover; a failed
startup migration instead leaves the engine in maintenance mode with readiness 503.

Changing record types or a workspace's selected model is a separate model operation, not an
application upgrade. Its preview can hold locks that delay writes while it checks converted rows.
Arrange a suitable window and let it finish or cancel it before investigating blocked writes.
See [Migrations](/docs/model/migrations/) for the review and confirmation workflow.

## Stored models outside the language window

This engine reads schema language `0.10`. Before 1.0, releases may drop earlier language versions.
A workspace on an unsupported schema is unavailable; others can remain served.

For supported older stored releases, stop **every** engine process and take a backup before raising:

```bash
docker compose run --rm engine python -m app.cli.model_release_raise --dry-run
docker compose run --rm engine python -m app.cli.model_release_raise
```

Review the dry run first. The command preserves release identities and their records, change sets,
publications and history. A release whose raised model is invalid or duplicates another release's
hash is skipped and reported; exit 1 means at least one was skipped. Later-schema releases are
left unchanged and reported: run the later engine that understands them. Inspect the actual report
even when the command exits 0. Start the engine and check workspace readiness afterwards.
A model file is separate: its author must supply a file with a supported `schemaVersion`.

## Roll back and preserve compatibility

An application or database rollback means stopping the new deployment and restoring the pre-upgrade
backup with the matching older application and configuration. Alembic downgrades and hand edits to
stored release rows are unsupported. [Model content rollback](/docs/run/model-releases-and-rollback/)
is a different operation and must pass data compatibility checks.

From the compatibility commitment, management and consumer APIs, events, sign-in contracts,
deployment settings and documented commands evolve additively. A breaking version is offered beside
the old contract, with at least 12 months and two minor releases of notice. Clients must tolerate
added fields, values and error codes. Before 1.0, stored-model raising tools and the model language
have separate maintenance rules. Database tables and browser layout are not stable public contracts.

## Prepare and verify a cutover

You need the target source version, Docker build access, the existing private configuration,
maintenance control over every writer and a successfully rehearsed pre-upgrade backup. Reserve
space for both the old recovery material and the new images. Upgrade duration and production
hardware requirements are **not measured**; rehearse on a copy of your own data first.

Before stopping the installation, record the current source version, the engine version shown on
About, Deployment's database revision, the selected model releases, enabled capabilities and any
custom mounts or proxy settings. Preserve an independently recoverable copy of the old source and
build configuration. Merely stopping an old container does not preserve a usable older deployment
when its image is rebuilt under the same name.

Build the target images from a source directory containing that target's files. When it replaces
the original checkout, preserve the same Compose project identity and volume selection. Running
a copied source directory under another project name can silently create empty volumes. The
checked-in Compose project name is `refiroo`; preserve any explicit project override you use.
Do not improvise a switch to a differently named project during cutover.

With the same project and mounts, upgrading keeps `database`, `job-files` and `assistant`,
plus `caddy-data` when using automatic HTTPS. Each task's working files and session logs now
live together in the `assistant` volume; see [Volumes and open assistant tasks](#volumes-and-open-assistant-tasks).
A backup may omit that volume: losing it loses open tasks’ folders and session logs, not records.
Do not run `docker compose down -v`: it removes the named volumes.

Before reopening webhook integrations, check whether any receiver uses a private or localhost
address. These destinations are now refused by default, including on existing subscriptions.
An operator must set `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED=true` and recreate the engine if those
receivers are intended. Link-local addresses stay refused. Check the delivery log for `address`
attempts and resume subscriptions that became suspended once the cause is resolved. See
[Webhook delivery](/docs/run/webhook-delivery/#network-and-receiver-requirements).

After the explicit migration command, expect:

```text
Database migration completed successfully.
```

Exit 1 means migration/preparation failed. The diagnostic starts `Database migration failed for`
for a migration failure and includes `Current revision:`, `target revision:` and `Reason:`.
Other preparation failures identify connection, collation, extensions or an unknown revision.
Use the [startup diagnostic reference](/docs/run/health-and-startup-checks/#recognise-the-startup-diagnostic)
for their recovery actions. Do not accept traffic just because the one-shot command exited 0.

Once the new engine starts, run:

```bash
curl -i https://refiroo.example.org/health/live
curl -i https://refiroo.example.org/health
docker compose exec -T database psql -U rdm -d rdm -c 'SELECT version_num FROM alembic_version;'
docker compose logs --tail=100 engine
```

Expect both probes 200, readiness `{"status":"ok"}` and the target revision. Then sign in at the
public address, confirm the engine version in About, and inspect every active workspace on
Operations. Open an application and read records in the workspaces your users rely on. If the
installation uses jobs, verify an export can finish and its file downloads. If it uses mail,
providers or webhook receivers, test the relevant connection before reopening those integrations.
A valid model and a running container do not prove those external connections still work.

## Recover a failed cutover

Keep writers closed while diagnosing. If the cause is missing permissions, an unavailable
extension or a transient database connection, correct that cause and repeat the same explicit
migration with the target engine. The migration runner wraps its pending revisions in one
PostgreSQL transaction, so a failed or interrupted run rolls back to its starting revision. Read the reported current revision
before retrying.

For a process interrupted during migration, the next start takes the installation lock and retries
from the revision PostgreSQL retained. Inspect logs and readiness afterwards. This describes the
transactional implementation; rehearse interruption and recovery on an isolated copy of your
production backup to establish its recovery time. Do not run an older engine against an unknown
newer database revision.

If the target cannot be made ready, stop it and follow the
[replacement-host recovery procedure](/docs/run/backup-and-restore/#restore-on-a-replacement-host)
using the **pre-upgrade** database, file archive, settings and application version. Recheck all
workspaces before moving traffic. If writers were reopened after the upgrade, those later writes
are absent from the backup: decide how to preserve or reconcile them before rollback.

Model raising is a separate maintenance write, even though it preserves release identities. Keep
a backup from before raising. Its dry run can prepare/migrate the database before reporting model
changes. Invalid or duplicate raised models are skipped while eligible models may still be raised;
read the per-release report, not only the total. Restoring the pre-maintenance backup with its
matching engine is the recovery path if the raised stored state must be undone.

## Volumes and open assistant tasks

The `assistant` volume mounts at `/opt/refiroo/rdm-engine/data/assistant`. Each task has a randomly
named folder containing its workbooks, files, Claude Code configuration, transcripts and turn logs.
Keep this volume mounted if open tasks need to continue.

When upgrading from the shared-transcript layout, the engine renames existing task folders to
random names and keeps their workbooks and files. An existing task starts a new Claude Code session
on its next turn. Earlier shared transcripts are not moved. The old `assistant-claude` volume is
no longer mounted or needed by the new image. After checking the upgraded tasks and retaining any
old logs required by your policy, remove only that obsolete volume if no longer needed:

```bash
docker volume rm refiroo_assistant-claude
```

That name assumes the default `refiroo` project; use your actual old volume name if you override
the project. This removal deletes the old transcripts, so keep it until you no longer need them.
Do not remove the current `assistant` volume as part of this cleanup.

The image and Compose set `AI_AGENT_SANDBOX=container`. The image builds eight session users by
default. If you run more engine processes in a container, rebuild with `ASSISTANT_USERS` at least
as large as `WEB_CONCURRENCY`. A task that cannot obtain a user fails with a note naming the build
argument. Users are taken per turn. Unix permissions close each task's folder between turns
and open it only to the user running that turn; startup also closes folders left open by stopped
turns. The engine resets the selected user's processes, home and temporary files around each turn.
Keep Compose's `init: true`; when running the image directly, supply `docker run --init`.
See [Set up AI](/docs/run/set-up-ai/#if-startup-or-a-request-fails) for reset and pool failures,
and [the assistant's session](/docs/run/ai/#the-assistants-session) for the remaining limits.

## Maintain build versions

Release source files fix the versions used to build the images. Preserve them with the deployment
record. When maintaining your own build, move each pin deliberately:

- **Base images:** the Dockerfiles and Compose files name a tag and a SHA-256 digest. Pull the
  chosen tag and read its digest with `docker buildx imagetools inspect <image:tag>` (the
  `Digest:` line). Replace the digest in `backend/Dockerfile`, `frontend/Dockerfile`,
  `compose.yml` or `compose.acme.yml`, as applicable, then rebuild. If maintaining CI too,
  update its PostgreSQL digest in `.github/workflows/ci.yml`.
- **Claude Code:** `CLAUDE_CODE_VERSION` in `backend/Dockerfile` names the installed version (default `2.1.295`).
  Change that default, or run `docker compose build --build-arg CLAUDE_CODE_VERSION=<version> engine`.
  `npm view @anthropic-ai/claude-code version` reports the newest published version; it does not
  choose one for your build. Check the built version with
  `docker compose run --rm --no-deps --entrypoint claude engine --version`, then recreate the
  engine and check an assistant turn as described in [Set up AI](/docs/run/set-up-ai/).
- **Python dependencies:** the engine image installs with `backend/constraints.txt`. After changing
  `backend/pyproject.toml`, or to take newer dependencies, regenerate it from `backend/`:

  ```bash
  uv pip compile pyproject.toml --extra dev --universal --python-version 3.14 \
    --no-header --annotation-style line -o constraints.txt
  ```

  Keep the file's comment header, review the version changes and run the relevant tests before
  building. The ranges in `pyproject.toml` describe compatible versions; the constraints select
  the installed versions.
- **Browser application and guide:** `npm ci` installs the versions in each directory's
  `package-lock.json`. Keep the matching lock file with any package change and rebuild the image.

These changes need rebuilt images, not a container restart. Preserve the earlier source, build
configuration and matching backup until the new build has passed your cutover checks.
