# Operations

How to configure, run, upgrade and recover RDM Engine. The design reasons behind these rules are in
[ARCHITECTURE.md](ARCHITECTURE.md); the API contracts are in [API.md](API.md).

The engine is pre-production until 0.11 (production hardening) and 0.12 (authentication). Every API
is unauthenticated today: run it only in a trusted environment or behind an access-control layer.

## Settings

The backend reads its settings from the environment at startup (`backend/app/config.py`).
`GET /api/v1/capabilities` reports the effective capability groups and job limits.

### Runtime

| Setting | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | required | PostgreSQL URL, `postgresql+psycopg://…`. See [Database](#database) |
| `RDM_MODEL_PATH` | `model/rdm-starter.json` | Bootstrap model file. Not the active-model setting; see [Model releases](#model-releases-and-rollback) |
| `RDM_CURSOR_SIGNING_KEY` | ephemeral | Secret that signs pagination cursors. Without it each process generates its own key, so cursors stop working after a restart and between instances |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins allowed to call the API |
| `RDM_API_REFERENCE_SCRIPT` | `bundled` | `bundled` serves the pinned Scalar script from the engine, so `/docs` works offline; `cdn` loads the same version from jsDelivr under its integrity hash. Any other value stops startup |
| `WEB_CONCURRENCY` | `1` | Uvicorn worker count. Must be `1` while model administration is enabled |
| `VITE_API_URL` (frontend) | `http://localhost:8000` | API address the browser application calls |

### Capability groups

A capability group's routes are registered only when it is enabled. These are deployment limits,
not authorization ([ADR-031](DECISIONS.md#adr-031--workspace-terminology-and-deployment-capability-boundaries)).

| Setting | Default | What it registers |
| --- | --- | --- |
| `MODEL_ADMIN_MUTATIONS_ENABLED` | off | Model draft create/edit, compile, release install and activation. Requires one process (`WEB_CONCURRENCY=1`); startup refuses it with more workers |
| `WORKSPACE_ADMIN_MUTATIONS_ENABLED` | on | Workspace create, rename, retire, reactivate, delete and default switching. Turn it off on an API exposed outside a trusted environment unless an access-control layer protects it |
| `INTEGRATION_JOBS_ENABLED` | on | Job creation (`POST /api/v1/batches`) and cancellation. Job reads stay registered |

Always available: installed-release reads, diff and inline validation; workspace discovery; the
change-set workflow (create, edit, validate, publish, discard) and publication withdrawal. Retired
workspaces stay readable and refuse every runtime write. In the browser, the **Models** and
**Workspaces** screens show a disabled group read only and name its setting.

### Batch and job limits

Reported under `integrationJobs` by `GET /api/v1/capabilities`; a request over a limit is
`413 batch_too_large` naming the setting.

| Setting | Default | Limit |
| --- | --- | --- |
| `BATCH_MAX_ITEMS` | 1,000 | Items in an inline batch |
| `BATCH_MAX_BYTES` | 5 MB | Body of an inline batch |
| `ATOMIC_JOB_MAX_ITEMS` | 10,000 | Items in an `atomic` batch, inline or background |
| `BACKGROUND_JOB_MAX_ITEMS` | 1,000,000 | Items in a background batch |
| `BATCH_BACKGROUND_MAX_BYTES` | 50 MB | Body of a background batch |
| `JOB_CHUNK_ITEMS` | 500 | Items one background chunk commits |
| `JOB_LEASE_SECONDS` | 120 | A worker's lease on a job, renewed each chunk |
| `JOB_RETENTION_DAYS` | 7 | How long a finished job keeps its outcomes and idempotency key |

## Database

PostgreSQL 17 is the only supported database (since 0.9.0-alpha.1). The database's default collation
must be the ICU root collation `und` (a language-independent Unicode order), and the role needs the
`pg_trgm` extension, which startup creates when it may. For a server other than the development one:

```sql
CREATE DATABASE rdm TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'und' LOCALE 'C';
```

For local development, `scripts/postgres.sh` runs a private server from Homebrew's binaries
(`brew install postgresql@17`; never start it with `brew services`):

| Command | Effect |
| --- | --- |
| `scripts/postgres.sh start` | Creates `backend/.postgres/` on first use, starts the server and prints `DATABASE_URL` |
| `scripts/postgres.sh stop` | Stops it |
| `scripts/postgres.sh status` | Reports whether it runs |
| `scripts/postgres.sh backup` | Writes a `pg_dump` file to `backend/.postgres/backups/` |

Nothing starts at login. Docker Compose runs `postgres:17-alpine` with the same collation.

SQLite was only ever a development database. The engine runs on PostgreSQL only and offers no
migration from SQLite.

## Startup checks and health

Startup refuses to serve, logs what to do and answers `GET /health` with `503` when:

- `DATABASE_URL` is missing, not PostgreSQL, uses another driver, or the server is unreachable;
- the database has another collation, or `pg_trgm` is missing and cannot be created;
- the database schema revision is unknown, or a migration fails (see [Upgrades](#upgrades));
- the database selects a model release whose schema the engine no longer reads; the log names the
  selected and supported schemas and prints the offline transition command
  (`python -m app.cli.model_schema_upgrade`).

The application does not start at all when model administration is enabled with more than one
worker. `/health` also returns `503` when an activation committed but this process could not load the newly
selected release. Restart the process; it then loads the database selection.

While the service runs, `/health` asks the database each time: while the database is unreachable it
answers `503`, and requests answer `500 internal_error` with a correlation ID (logged in one line, no
traceback). Nothing needs restarting: once the database is back, `/health` answers `200`, requests
are served and the job worker resumes (it retries every 2 s and logs the outage once, then a line a
minute).

## Background jobs

Batches sent with `run: background` are run by a worker thread inside the API process. It runs only
while `INTEGRATION_JOBS_ENABLED` is on and the model is healthy, and expires finished jobs past their
retention every hour.

- **Graceful stop:** the running chunk finishes and the worker releases its lease, so the next start
  resumes the job at once.
- **Crash or kill:** the chunk in progress rolls back. Once the lease expires (`JOB_LEASE_SECONDS`), the
  next worker resumes the job at its first item without an outcome. No item is applied twice or
  skipped.
- **Database outage:** the worker retries every 2 s, logs the traceback once per outage and then one
  line a minute, and logs when the database is reachable again.
- **Cancel:** `POST /api/v1/jobs/{jobId}/cancel` stops a job at its next chunk; an `atomic` job rolls
  back completely.

A background job holds its workspace's write lock for one chunk at a time (0.25–0.5 s for 500 items),
so other writes in that workspace wait at most that long.

## Deployment topologies

The supported topology is one API process (the Docker image starts one Uvicorn process). Several
instances may share one database with different capability groups, for example an internal instance
with model administration on and a public one with both administration groups off, but this topology
has no composed test yet; multi-node operation is 0.11 work. Its known caveats are in
[ARCHITECTURE.md](ARCHITECTURE.md#deployment-topology). Instances behind one load balancer must share
`RDM_CURSOR_SIGNING_KEY`.

## Model releases and rollback

`RDM_MODEL_PATH` is bootstrap input, not the active-model setting. Startup validates the file and
installs its content when that release is missing; an existing database keeps the release it selects
in `model_runtime_state`, even when the file holds a newer one. Changing the file never activates it.

The model lifecycle is staged: save a draft, validate and compile it (no side effects), install it as
an immutable inactive release, then activate it with the current runtime version and active-release
ID. Activation is refused when stored data is incompatible with the candidate. All four steps are in
the browser's **Models** workbench and the [model API](API.md#model-endpoints), with
`MODEL_ADMIN_MUTATIONS_ENABLED` on.

To roll back model content, activate a previously installed compatible release. The same
compatibility check applies in both directions, so a rollback is refused when current data would be
invalid under the older release. Never edit installed release JSON or point `RDM_MODEL_PATH` at an
older file.

## Upgrades

Before upgrading the application:

1. Stop or quiesce writers.
2. Take a consistent backup (`pg_dump` or the platform's snapshot) and verify that a restore includes
   schema and data.
3. Keep the backup with the application version and its configuration, especially `DATABASE_URL`,
   `RDM_MODEL_PATH`, `RDM_CURSOR_SIGNING_KEY`, the capability settings and the worker count.
4. Run the migrations with the new application before accepting traffic:

   ```bash
   cd backend
   .venv/bin/python -m app.cli.database_upgrade
   ```

   It uses the configured `DATABASE_URL`. Startup also upgrades to the latest revision, but the
   explicit step shows a failure before cutover.

A failed migration prints an operator message instead of a traceback: the database without
credentials, the current and target revisions, the reason, backup and retry steps and what to include
in an escalation. Startup in the same condition enters maintenance mode with `/health` `503`. Each
migration runs in one PostgreSQL transaction, so a failed or interrupted migration leaves the
database at its previous revision.

To roll back the application or database schema, stop the new deployment and restore the
pre-upgrade backup together with the matching older application version. Alembic downgrades and
manual edits to release rows are not a supported rollback path.
