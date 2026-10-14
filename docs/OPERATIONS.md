# Operations

How to configure, run, upgrade and recover RDM Engine. The design reasons behind these rules are in
[ARCHITECTURE.md](ARCHITECTURE.md); the API contracts are in [API.md](API.md).

The engine is pre-production until 0.11 (production hardening) and 0.12 (authentication). Every API
is unauthenticated today: run it only in a trusted environment or behind an access-control layer.

## Settings

The backend reads its settings from the environment at startup (`backend/app/config.py`).
`GET /api/v1/capabilities` reports the effective capability groups and job limits, and
`GET /api/v1/system` every setting with its value, default and source (secrets only as set or not,
`DATABASE_URL` without its password). In the browser, **Settings › Deployment** shows both, read only:
a change needs a restart.

A new setting is added to the `Settings` model, to the settings catalogue in `config.py` (its group
and the one line the API and the Deployment page show) and to the table of its group below.
`tests/unit/test_config.py` fails until all three agree.

### Runtime

| Setting | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | required | PostgreSQL URL, `postgresql+psycopg://…`. See [Database](#database) |
| `RDM_MODEL_PATH` | `model/rdm-starter.json` | Bootstrap model file. Not the active-model setting; see [Model releases](#model-releases-and-rollback) |
| `RDM_CURSOR_SIGNING_KEY` | ephemeral | Secret that signs pagination cursors. Without it each process generates its own key, so cursors stop working after a restart and between instances |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins allowed to call the API |
| `JOB_FILE_DIR` | `var/job-files` | Where export files wait for download and import files wait to be read, named after their job, and where model authoring's source files are kept (0.10 A3); created at start. With job creation on, a directory that cannot be written stops startup. An export's file is kept while its job is completed and removed when the job expires (`JOB_RETENTION_DAYS`), fails or is cancelled; an import's file until its job finishes. Several instances need it on shared storage. See [Exports](#exports), [Imports](#imports) and [Source files and dry runs](#source-files-and-dry-runs) |
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
| `CONSUMER_SUBSCRIPTIONS_ENABLED` | off | The webhook subscriptions API (`/api/v1/consumer-subscriptions`), reads included, and from 0.9 C12 their delivery. Requires `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`; startup refuses without it. Turned off, stored subscriptions are kept and continue when it is turned on again |
| `INFERENCE_ASSISTANT` | empty | The optional assistant of a model draft's inference (0.10 A6, D95), as `package.module:function`, a factory returning an object with `suggest(request)`. Empty, nothing is sent anywhere. Configured, each inference sends it every sheet's headers and at most `INFERENCE_ASSISTANT_ROWS` rows, and the types its proposals add; its label suggestions become proposals, never applied unasked. No provider is bundled; a failing assistant is a warning on the inference |

Always available: installed-release reads, diff and inline validation; workspace discovery; the
change-set workflow (create, edit, validate, publish, discard) and publication withdrawal. Retired
workspaces stay readable and refuse every runtime write. In the browser, Settings › **Model** and
**Workspaces** show a disabled group read only and name its setting, and **Deployment** lists every
group on or off with the setting that switches it.

### Batch and job limits

Reported under `integrationJobs` by `GET /api/v1/capabilities`; a request over a limit is
`413 BATCH_TOO_LARGE` naming the setting.

| Setting | Default | Limit |
| --- | --- | --- |
| `BATCH_MAX_ITEMS` | 1,000 | Items in an inline batch |
| `BATCH_MAX_BYTES` | 5 MB | Body of an inline batch |
| `ATOMIC_JOB_MAX_ITEMS` | 10,000 | Items in an `atomic` batch, inline or background |
| `BACKGROUND_JOB_MAX_ITEMS` | 1,000,000 | Items in a background batch |
| `BATCH_BACKGROUND_MAX_BYTES` | 50 MB | Body of a background batch |
| `IMPORT_MAX_BYTES` | 200 MB | An import's file (`POST /api/v1/imports`); a larger one is `413 IMPORT_TOO_LARGE`, and the request's body is held on disk while it is read. An import's items count against `BACKGROUND_JOB_MAX_ITEMS` and, `atomic`, `ATOMIC_JOB_MAX_ITEMS` (`IMPORT_TOO_MANY_ITEMS`) |
| `JOB_PREVIEW_MAX_ITEMS` | 10,000 | The items a preview runs, an import's (`stage: preview`, 0.9 J3) or a batch's (0.9 K2); beyond them the preview is a `sample`. Named `IMPORT_PREVIEW_MAX_ITEMS` before 0.9 K2, which renamed it without an alias. The preview holds its workspace's write lock (or its change set's claim) while it runs, so a larger value makes other writes in that workspace wait longer once per preview |
| `MODEL_OPERATION_MAX_ITEMS` | 500 | Operations in one request to a model draft (`POST /model-drafts/{id}/operations`, 0.10 A2); more is `413 OPERATION_BATCH_TOO_LARGE`. A request is one step of the draft's history and is applied and validated as a whole, so a larger value makes one step slower to apply and to undo |
| `INFERENCE_ASSISTANT_ROWS` | 20 | Rows of each sheet an inference sends the assistant, when `INFERENCE_ASSISTANT` names one |
| `JOB_CHUNK_ITEMS` | 500 | Items one background chunk commits |
| `JOB_LEASE_SECONDS` | 120 | A worker's lease on a job, renewed each chunk |
| `JOB_RETENTION_DAYS` | 7 | How long a finished job keeps its outcomes and idempotency key |
| `FEED_RETENTION_DAYS` | 30 | How long the change feed answers a position; older positions are `410 FEED_POSITION_EXPIRED`, naming the publication to re-read. Entries after the active publication, and every entry of a workspace without one, are always answered. Consumer events expire with the entries (`410 EVENTS_EXPIRED`) and are deleted hourly. The audit log is not pruned |
| `CONSUMER_RESOLVE_MAX_ITEMS` | 1,000 | Items in one consumer batch resolve (`POST /api/consumer/…/resolve`); more are refused as `413 BATCH_TOO_LARGE`. Reported by `GET /capabilities` |

## Database

PostgreSQL 17 is the only supported database (since 0.9.0-alpha.1). The database's default collation
must be the ICU root collation `und` (a language-independent Unicode order), and the role needs the
`pg_trgm` and `btree_gin` extensions (both in PostgreSQL's contrib modules; `btree_gin` since 0.9
C14), which startup creates when it may. For a server other than the development one:

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
- the database has another collation, or `pg_trgm` or `btree_gin` is missing and cannot be created;
- the database schema revision is unknown, or a migration fails (see [Upgrades](#upgrades));
- the database selects a model release whose schema the engine no longer reads; the log names the
  selected and supported schemas and prints the offline transition command
  (`python -m app.cli.model_schema_upgrade`).

The application does not start at all when model administration is enabled with more than one
worker. `/health` also returns `503` when an activation committed but this process could not load the newly
selected release. Restart the process; it then loads the database selection.

While the service runs, `/health` asks the database each time: while the database is unreachable it
answers `503`, and requests answer `500 INTERNAL_ERROR` with a correlation ID (logged in one line, no
traceback). Nothing needs restarting: once the database is back, `/health` answers `200`, requests
are served and the job worker, the event deriver and the webhook dispatcher resume. Each retries
every 2 s and logs the outage in one ERROR line saying it cannot reach the database, then a WARNING
a minute, then an INFO line when the database answers again, with no traceback: an unreachable
database is an expected failure. The traceback is logged at DEBUG, for escalation. Any other
failure of these threads is logged at ERROR with its traceback, since it points at a defect.

## Background jobs

Batches sent with `run: background` are run by a worker thread inside the API process. It runs only
while `INTEGRATION_JOBS_ENABLED` is on and the model is healthy, and expires finished jobs past their
retention every hour.

- **Graceful stop:** the running chunk finishes and the worker releases its lease, so the next start
  resumes the job at once.
- **Crash or kill:** the chunk in progress rolls back. Once the lease expires (`JOB_LEASE_SECONDS`), the
  next worker resumes the job at its first item without an outcome. No item is applied twice or
  skipped.
- **Database outage:** the worker retries every 2 s, logs the outage in one line (the traceback at
  DEBUG) and then one line a minute, and logs when the database is reachable again.
- **Cancel:** `POST /api/v1/jobs/{jobId}/cancel` stops a job at its next chunk; an `atomic` job rolls
  back completely.

A background job holds its workspace's write lock for one chunk at a time (0.25–0.5 s for 500 items),
so other writes in that workspace wait at most that long.

### Exports

Exports (`POST /api/v1/exports`) run on a second worker thread of their own, so an export never
waits behind a batch and a batch never waits behind an export; two exports run one after the other.

- **Files:** each export writes `{jobId}.partial` in `JOB_FILE_DIR` and renames it to
  `{jobId}.jsonl`, `.csv` or `.xlsx` when the job completes. A file stays while its job is
  completed and goes when the job expires, fails or is cancelled; at start and with the hourly
  sweep the worker removes any file no completed job serves (a partial file a crash left, a file
  of an expired job). A file removed by hand answers `410 JOB_OUTPUT_MISSING`; run the export again.
  Disk use is one file per completed export for `JOB_RETENTION_DAYS`.
- **One snapshot:** an export reads everything in one `REPEATABLE READ` transaction, held for as
  long as it runs. PostgreSQL cannot clean up rows changed meanwhile until it ends; for exports of
  a few minutes this is not noticeable. Writes are never blocked by an export.
- **Crash or kill:** the export starts again from the beginning once its lease expires
  (`JOB_LEASE_SECONDS`); nothing resumes half way.
- **Cancel:** takes effect at the export's next check, every 10,000 rows (a CSV export between its
  records and its relationships).
- **Following jobs (0.9 J1u):** `GET /api/v1/jobs/{id}/events` is a server-sent event stream; the
  browser opens one per running job a tab started, and the job page one while it is shown. A
  proxy in front of the engine must not buffer it (nginx reads the `X-Accel-Buffering: no` header the
  engine sends) and must allow responses that stay open (a keep-alive comment comes every 15 s).
  Under HTTP/1.1 a browser opens at most six connections per site, so a tab following more than
  about five running jobs at once waits for one to end; HTTP/2 lifts it. Each process holds one
  extra database connection that `LISTEN`s for job changes (revision `20261007_05`'s trigger); it
  reconnects after an outage, logging it like the other background threads.
- **CSV and spreadsheets:** values are written exactly as stored. A text value beginning with `=`,
  `+`, `-` or `@` is not altered; a spreadsheet that opens a CSV may read it as a formula. The XLSX
  format writes every text as text, never as a formula.

### Imports

Imports (`POST /api/v1/imports`, 0.9 J2) run on the batch worker: an import first binds its file,
then applies its items in chunks as a background batch does, so a long import makes a batch wait
as a long batch does.

- **Files:** the uploaded file is written to `JOB_FILE_DIR` as `{jobId}.source` before the job is
  queued, read by the worker, and removed when the job finishes; the hourly sweep removes any whose
  job no longer reads it. Disk use is the files of the imports waiting or running. A file removed
  by hand fails its job with `IMPORT_FILE_MISSING`; send it again.
- **Binding:** reading the file and resolving its keys and matches is one transaction. A crash or a
  stop before it commits binds the file again from the start once the lease expires; after it, the
  import resumes at its first item without an outcome, like a batch. A cancel request takes effect
  every 10,000 rows read, and at the next chunk once bound.
- **Readers:** XLSX through openpyxl (read-only mode; a formula's cached value is read, never the
  formula), CSV and JSON Lines through the standard library. A legacy `.xls` file is refused;
  convert it to XLSX.
- **Previews** (0.9 J3, batches since 0.9 K2): a preview runs its first `JOB_PREVIEW_MAX_ITEMS` items in one
  transaction that is rolled back, holding its workspace's write lock (or its change set's claim)
  for that time, as an atomic job of its size does: about 8 s live for 10,000 items on the volume
  fixture (J3's budget run; longer in a change set), so writes in that workspace wait that long
  once per preview. A crash during it runs
  the preview again from the bound items. A preview waiting for confirmation holds no lock and no
  lease; its file stays in `JOB_FILE_DIR` until it is confirmed and finishes, is cancelled, or
  expires `JOB_RETENTION_DAYS` after the preview ended. Confirming binds the file again.

### Source files and dry runs

Model authoring (0.10 A3) keeps workbooks as **source files** (`POST /api/v1/source-files`), each
owned by a model draft or an import profile.

- **Files:** stored in `JOB_FILE_DIR` as `{sourceFileId}.upload` under `IMPORT_MAX_BYTES`, kept as
  long as the draft or profile that owns it. An upload supersedes the owner's earlier file, which the
  hourly sweep deletes `JOB_RETENTION_DAYS` later; deleting a draft or profile deletes its files'
  rows, and the sweep removes a file without a row once it is older than ten minutes. Disk use is one
  current file per draft and profile, plus superseded ones within the retention period. A file
  removed by hand fails the jobs that read it with `SOURCE_FILE_MISSING`; upload it again.
- **Staged cells:** profiling copies every filled cell into `source_file_cells`, about 330,000 rows
  for a 10,000-row workbook of two sheets; they go with their file.
- **Jobs:** profiling (`profile`) and dry runs (`dryRun`) run on the batch worker beside imports and
  batches. A dry run previews every row of its file in one rolled-back transaction, holding its
  workspace's write lock that long, as an import's preview does: 5.75 s of the about 7 s a
  10,000-row workbook (19,453 items) takes on the reference machine, so live writes in that workspace wait that long once per
  dry run. A newer dry run of the same draft cancels a running one.

## Consumer events

A second thread in the API process derives consumer events from each workspace's change feed for
every consumer API that declares `events` (0.9 C10). It runs while the model is healthy, needs no
setting and takes no workspace lock: writes never wait for it.

- **Lag:** it looks once a second. A consumer reading `GET …/events` sees `headPosition`, how far
  events are derived; the workspace's feed head (`GET /api/v1/workspaces/{key}/feed`) shows how far
  writes are. A large fan-out (renaming a container with 20,000 objects below it) derives in under a
  second.
- **Several processes** share the work: each workspace is derived by one at a time through its row in
  `consumer_event_checkpoints`.
- **Crash or kill:** the page in progress rolls back and is derived again; no event is lost or made
  twice.
- **Database outage:** as the job worker: retries every 2 s, one plain line per outage (the
  traceback at DEBUG), then a line a minute.
- **Retention:** events are deleted hourly with the change feed's floor (`FEED_RETENTION_DAYS`).
- **Upgrade to 0.9 C10:** each workspace's events start at its active publication's position (all of
  its feed without one); earlier changes have no events.

## Webhook subscriptions

Subscriptions say where a consumer API's events are delivered (0.9 C11), and a dispatcher thread in
the API process delivers them (0.9 C12). They are deployment data: they are not part of a model
release and are not copied by one.

| Setting | Default | Meaning |
| --- | --- | --- |
| `CONSUMER_SUBSCRIPTIONS_ENABLED` | off | Serves the subscriptions API (see capability groups) and runs the dispatcher that delivers them |
| `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` | none | 32 bytes in URL-safe base64; signing keys are stored sealed with it (AES-256-GCM). Required with the capability on |
| `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` | 7 | Days the delivery log keeps each request, with the body it sent (up to 1 MiB), its events and its attempts (0.9 U5a); a batch still being retried or awaiting a resume is kept longer. Reported by `GET /api/v1/capabilities` |

**The delivery log** (0.9 U5a) records every request the dispatcher sends: its body, the events
it carries and each attempt's start, duration and answer (up to 4 KiB). It is read on Settings ›
Integration › Webhooks, Deliveries, and through `GET /api/v1/consumer-subscriptions/{id}/deliveries`.
A busy subscription writes up to 1 MiB per request: size the database for the retention. The
dispatcher deletes expired entries at most hourly.

A webhook URL may name any host and port. It must use HTTPS; plain HTTP is accepted only to
`localhost`, `127.0.0.1` or `::1` (development). There is no host allowlist (C-D101 revised).

- **Generating the key:** `python -m app.cli.generate_key` prints one. Keep it with the deployment's
  other secrets, never in the database or its backups. Every process of a deployment uses the same
  key. Changing it makes every stored signing key unreadable: subscriptions would have to be
  recreated (rotation arrives in 0.12).
- **A model activation** that drops what a subscription names suspends it (`MODEL_CHANGED`); one
  that raises its consumer API's contract version suspends it until resumed
  (`CONTRACT_VERSION_CHANGED`). **Retiring a workspace** suspends its subscriptions
  (`WORKSPACE_RETIRED`), and a workspace with subscriptions cannot be deleted.
- **Long suspensions:** events expire with `FEED_RETENTION_DAYS`. A resume after unacknowledged
  events expired is refused; the refusal names the publication to re-sync from. The owner resumes
  with `reset`, which starts after the feed's head, and then re-syncs the receiver (a publication's
  lists): reset first, so nothing falls between.

### Delivery

- **What a receiver must do.** Accept `POST` requests of up to 1 MiB of JSON body, more for an
  unusually large single object (nginx's default `client_max_body_size` is exactly 1 MiB); answer
  `2xx` within 10 seconds once the request is stored; verify `RDM-Signature` (HMAC-SHA256 of
  `"{RDM-Timestamp}.{body}"` with the subscription's `signingSecret`) and reject stale timestamps;
  deduplicate by `eventId`, since delivery is at least once. A redirect is not followed: give the
  final URL. The limits are reported in `GET /api/v1/capabilities` (`consumerSubscriptions.delivery`)
  and explained in [CONSUMER_API "Delivery"](CONSUMER_API.md#delivery).
- **A failing receiver.** A batch that fails is retried with the same events and delivery ID after
  10 s, 30 s, 1, 2, 5, 10 and 30 minutes, then hourly (each ±20 %), for 24 hours from its first
  failure; nothing later is sent past it. The subscription's `delivery.pending` shows the attempts,
  the last error and the next attempt; each failed attempt is one INFO line in the log. After 24
  hours it is suspended `DELIVERY_FAILED`. Fix the receiver, then resume: delivery continues from
  the first unacknowledged event. Editing the URL retries at once.
- **Suspensions the dispatcher sets, and what to do:**

  | Reason | Cause | Fix |
  | --- | --- | --- |
  | `DELIVERY_FAILED` | The receiver failed for 24 hours | Fix the receiver (or the URL), then resume |
  | `FILTER_MATCHES_NOTHING` | A filter value no longer matches any record (it was deleted or renamed) | Edit the filter, then resume; the events since, deletions included, are delivered |
  | `EVENTS_EXPIRED` | Events expired before they were delivered: the dispatcher did not run for `FEED_RETENTION_DAYS` (the capability was off, or no process ran) | Resume with `reset`, then re-sync the receiver from the publication the details name |

  Each suspension is one WARNING line in the log.
- **Filtered subscriptions and records leaving their scope.** Filters are applied to each record as
  it is when its events are sent. A record moved out of a filtered scope, or edited so a filter no
  longer matches it, is therefore not sent to that subscription, and its receiver keeps its copy;
  deletions are always sent. A receiver that must drop such records subscribes with the type filter
  only and narrows on its side, or reconciles now and then from the consumer list with the same
  parameters ([CONSUMER_API "Subscriptions"](CONSUMER_API.md#subscriptions-runtime-not-model),
  C-D114).
- **Addresses.** The host is resolved at each attempt; a link-local address (`169.254.0.0/16`,
  `fe80::/10`, where cloud metadata services listen) is always refused, and a loopback address
  unless the URL names a loopback host. Private addresses are allowed. A refused address is a failed attempt and is retried.
- **TLS** is verified against the system's trust store. For receivers with certificates from an
  internal CA, point `SSL_CERT_FILE` at a bundle that includes it. **No outbound proxy** is used in
  0.9: the API process needs direct HTTPS access to the receivers.
- **Throughput.** Requests to one subscription go one at a time, to keep the order, so its speed is
  set by how many events a request carries and how fast the receiver answers. A subscription sends
  one event per request by default (0.9 C17): 10,000 changes are then 10,000 requests in a row,
  about 8 minutes at 50 ms an answer. For bulk changes, batch: measured at full volume with batches
  of 100, one subscription receives about 3,500 events a second with the full payload (about 5,000
  with `identity`) from a receiver that answers at once: 20,001 events from one rename arrive in
  about 6 seconds, in 201 requests. A receiver's own answer time adds to every request, and a
  process delivers four subscriptions at a time. Figures in
  [POSTGRESQL_BUDGETS §7](POSTGRESQL_BUDGETS.md#webhook-delivery-09-c13).
- **Several processes** share delivery through a lease per subscription (60 s): each subscription is
  delivered by one process at a time, in order. Turning the capability off stops delivery; stored
  subscriptions continue when it is turned on again, and those whose events expired meanwhile are
  suspended `EVENTS_EXPIRED`.

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
A schema 0.8 file that declares `consumerApis` refuses to start, naming the file: rewrite its
consumer API definitions in schema 0.9 or point `RDM_MODEL_PATH` at a 0.9 model such as
`model/rdm-starter.json` (0.9 C18). Releases already installed are not affected.

The model lifecycle is staged: save a draft, validate and compile it (no side effects), install it as
an immutable inactive release, then activate it with the current runtime version and active-release
ID. Activation is refused when stored data is incompatible with the candidate. All four steps are in
the browser's Settings › **Model** pages and the [model API](API.md#model-endpoints), with
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
