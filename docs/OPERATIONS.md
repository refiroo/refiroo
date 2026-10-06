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
| `CONSUMER_WEBHOOK_ALLOWED_HOSTS` | empty | Comma-separated hosts a webhook URL may name: exact names, or `*.` and a domain for any host below it (not the domain itself); IP addresses as written; any port. Empty allows nothing. URLs must use HTTPS; plain HTTP is accepted only to `localhost`, `127.0.0.1` or `::1` when listed (development). Reported by `GET /api/v1/capabilities` |
| `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` | none | 32 bytes in URL-safe base64; signing keys are stored sealed with it (AES-256-GCM). Required with the capability on |

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
  | `HOST_NOT_ALLOWED` | The URL's host left `CONSUMER_WEBHOOK_ALLOWED_HOSTS` | Edit the URL, or list the host again and restart, then resume |
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
  unless the URL names a loopback host. Private addresses are allowed: the allowlist decides which
  hosts. A refused address is a failed attempt and is retried.
- **TLS** is verified against the system's trust store. For receivers with certificates from an
  internal CA, point `SSL_CERT_FILE` at a bundle that includes it. **No outbound proxy** is used in
  0.9: the API process needs direct HTTPS access to the receivers.
- **Throughput.** Measured at full volume, one subscription receives about 3,500 events a second
  with the full payload (about 5,000 with `identity`) from a receiver that answers at once: 20,001
  events from one rename arrive in about 6 seconds, in 201 requests. A receiver's own answer time
  adds to every request, and a process delivers four subscriptions at a time. Figures in
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
