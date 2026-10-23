# Operations

How to configure, run, upgrade and recover RDM Engine. The design reasons behind these rules are in
[ARCHITECTURE.md](ARCHITECTURE.md); the API contracts are in [API.md](API.md).

The engine is pre-production until 0.11 (production hardening) and 0.12 (authentication). Every API
is unauthenticated today: run it only in a trusted environment or behind an access-control layer.

## Settings

The backend reads its settings from the environment at startup (`backend/app/config.py`).
`GET /api/v1/capabilities` reports the effective capability groups and job limits, and
`GET /api/v1/system/configuration` every setting with its value, default and source (secrets only as
set or not, `DATABASE_URL` without its password). In the browser, **Settings › Deployment** shows both, read only:
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
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins allowed to call the API. They are also where a person's sign-in may return: `<origin>/signed-in` for each (0.12 D267), so the browser application is served at the root of one of them |
| `PUBLIC_URL` | `http://localhost:8000` | The engine's address as callers reach it, behind any proxy: the issuer (`iss`) of its tokens and the base of the addresses in `/.well-known/oauth-authorization-server` (0.12 D259). An absolute `http` or `https` URL; anything else stops startup. Set it on every production installation, the same on every process. See [Authentication](#authentication) |
| `SECRETS_ENCRYPTION_KEY` | required | 32 bytes in URL-safe base64 (`python -m app.cli.generate_key`); seals the stored token signing keys and webhook signing keys (AES-256-GCM, D253). Startup refuses without it, and refuses the setting it replaced, `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, by name. Keep it outside the database and its backups; the same on every process |
| `ACCESS_TOKEN_MINUTES` | `60` | Minutes an access token lasts, for people and clients (D251). A deactivation or a retired key applies on the next request whatever the lifetime |
| `TOKEN_SIGNING_KEY_DAYS` | `30` | Days a token signing key signs; the first token issued after that brings a new key, and the old one keeps accepting its tokens until they expire (D254, D264) |
| `SESSION_IDLE_HOURS` | `12` | Hours a person's browser session lasts without being renewed; the browser renews it while the person works (D251). See [Signing in from the browser](#signing-in-from-the-browser) |
| `SESSION_DAYS` | `14` | Days a browser session lasts in all; then the person signs in again (D251) |
| `PASSWORD_RESET_HOURS` | `24` | Hours a password-reset link stays valid; it works once (0.12 D272) |
| `PASSWORD_MIN_LENGTH` | `15` | Characters a local password needs at least (D252). **For a development machine only** it may be lowered, down to `1`, for a short password (D276); the most common passwords stay refused. Leave it at 15 in production |
| `JOB_FILE_DIR` | `var/job-files` | Where export files wait for download and import files wait to be read, named after their job, and where model authoring's source files are kept (0.10 A3); created at start. With job creation on, a directory that cannot be written stops startup. An export's file is kept while its job is completed and removed when the job expires (`JOB_RETENTION_DAYS`), fails or is cancelled; an import's file until its job finishes. Several instances need it on shared storage. See [Exports](#exports), [Imports](#imports) and [Source files and dry runs](#source-files-and-dry-runs) |
| `RDM_API_REFERENCE_SCRIPT` | `bundled` | `bundled` serves the pinned Scalar script from the engine, so `/docs` works offline; `cdn` loads the same version from jsDelivr under its integrity hash. Any other value stops startup |
| `WEB_CONCURRENCY` | `1` | Uvicorn worker count. Any count, with or without model administration (0.11 N1); see [Several processes](#several-processes) |
| `DATABASE_POOL_SIZE` | `5` | Database connections each process keeps open (0.11 Q1). See [Database connections](#database-connections) |
| `DATABASE_POOL_MAX_OVERFLOW` | `10` | Connections each process opens beyond `DATABASE_POOL_SIZE` when busy, closed again when returned; `0` for none |
| `DATABASE_POOL_TIMEOUT` | `30` | Seconds a caller waits for a free connection; a request that waits it out answers `503 DATABASE_UNAVAILABLE` |
| `DATABASE_IDLE_TRANSACTION_TIMEOUT` | `300` | Seconds a connection may sit idle inside a transaction before the database ends it, releasing a stalled process's locks (0.11 N3); `0` turns it off. See [Several processes](#several-processes) |
| `LOG_FORMAT` | `text` | `text` writes one plain line per record; `json` one JSON object per line, for a log collector (0.11 O1). Any other value stops startup. See [Logs](#logs) |
| `LOG_LEVEL` | `INFO` | The lowest level the engine logs: `DEBUG`, `INFO`, `WARNING` or `ERROR`. `DEBUG` adds the tracebacks of expected failures and the access lines of probes and scrapes |
| `PROCESS_HEARTBEAT_SECONDS` | `15` | Seconds between each process's reports of its state to the others through the database; a process silent for three is listed `silent`. See [Monitoring](#monitoring) |
| `VITE_API_URL` (frontend) | `http://localhost:8000` | API address the browser application calls |

### Several processes

Several processes may serve one database: Uvicorn workers (`WEB_CONCURRENCY` above 1) or instances on
several nodes. Processes started together check, migrate and install the bootstrap model one at a
time under a database lock; the others wait and then find the database ready. A model activated or a
workspace migrated through any process is served by every process from its next request, with no
restart. A read whose workspace switched to another release while it ran answers
`409 MODEL_RELEASE_CHANGED`, and the client reads again. Instances share `RDM_CURSOR_SIGNING_KEY` and
keep `JOB_FILE_DIR` on shared storage.

Every process runs a job worker (0.11 N2). A job queued through any process starts on whichever
worker is idle, at once: each process hears job changes through `LISTEN` and wakes its workers. A
running job keeps its lease by a heartbeat however long a step takes, and moves to another worker
only once its process stops renewing (`JOB_LEASE_SECONDS`, 120 s by default): stopped, crashed,
frozen or cut off from the database.

Writes take turns through database locks (the workspace's, a change set's), so the rules a write
checks (unique values, versions, parent cycles, cardinality, feed positions) hold whichever process
or node each write reaches. A process that stalls inside a transaction, frozen, starved of CPU or cut
off from the database, holds that transaction's locks, and the writes of its workspace wait for
them. The database ends such a transaction once it has been idle for
`DATABASE_IDLE_TRANSACTION_TIMEOUT` (300 s by default), which releases the locks; the other
processes go on, and a job moves to another worker through its lease as above (0.11 N3). When the
stalled process resumes, nothing of that transaction is saved, a job it was running is left to its
lease rather than failed, and it serves again. What it logs, in one line without a traceback,
depends on what it reads first: the database's notice gives a WARNING naming the setting, and a
request it was serving answers `503 DATABASE_UNAVAILABLE` with `details.reason` `transactionEnded`;
when its next statement meets the closed connection first, the notice is lost and it logs that it
cannot reach the database (`unreachable`), then finds it again at once. A working process is never idle inside a transaction for that long: its
longest step between two statements, a publish's validation at full volume, is estimated at about
70 s. Raise the setting if the warning appears while the processes run normally; `0` turns it off,
and a stalled process then holds its locks until it resumes or its connection closes.

A node cut off from the network in the middle of a statement, rather than between two, is not idle
in its transaction; the server notices the lost connection through TCP keep-alives, which are the
server's settings (`tcp_keepalives_idle`, `tcp_keepalives_interval`, `tcp_keepalives_count`,
`tcp_user_timeout`), by default after about two hours on Linux and macOS. Lower them on the
database server for deployments of several nodes.

### Database connections

Each process has one pool of connections (`DATABASE_POOL_SIZE`, plus up to
`DATABASE_POOL_MAX_OVERFLOW` more while busy), shared by everything it runs: requests, each one
holding a connection while it is served; the job worker and the export worker, each holding one
while it runs a step of a job; their heartbeats, briefly every third of `JOB_LEASE_SECONDS`; the
event deriver and the webhook dispatcher, briefly each round. The job listener holds one more
connection of its own, outside the pool, and startup one more while it checks and migrates.

So a process opens at most `DATABASE_POOL_SIZE + DATABASE_POOL_MAX_OVERFLOW + 1` connections (16
with the defaults), and an instance `WEB_CONCURRENCY` times that. Across every instance on one
server, the sum stays under the server's `max_connections` less `superuser_reserved_connections`
and whatever else connects to it (backups, an administrator's session). At startup each process
compares its own instance's figure with the server's and logs a WARNING when it is over; other
instances are not visible to it.

When every connection of a process's pool is in use for `DATABASE_POOL_TIMEOUT`, its next request
answers `503 DATABASE_UNAVAILABLE` with `details.reason` `poolExhausted` and `Retry-After: 5`, and
the log has one WARNING line naming the settings; nothing is saved. When the server refuses a new
connection because it has as many as it takes, the reason is `tooManyConnections`; when it ended a
stalled process's idle transaction, `transactionEnded` (see [Several processes](#several-processes)). Seen now and then
under a peak, it needs nothing; seen under normal load, raise `DATABASE_POOL_SIZE` or
`DATABASE_POOL_MAX_OVERFLOW` within the server's limit, or lower `WEB_CONCURRENCY`. A background
thread without a connection logs one ERROR line saying so, without a traceback, and retries as
for an unreachable database (below).

### Capability groups

A capability group's routes are registered only when it is enabled. These are deployment limits,
not authorization ([ADR-031](DECISIONS.md#adr-031--workspace-terminology-and-deployment-capability-boundaries)).

| Setting | Default | What it registers |
| --- | --- | --- |
| `MODEL_ADMIN_MUTATIONS_ENABLED` | off | Model draft create/edit, compile, release install and activation. Works with any number of processes and instances on one database (0.11 N1) |
| `WORKSPACE_ADMIN_MUTATIONS_ENABLED` | on | Workspace create, rename, retire, reactivate, delete and default switching. Turn it off on an API exposed outside a trusted environment unless an access-control layer protects it |
| `INTEGRATION_JOBS_ENABLED` | on | Job creation (`POST /api/v1/batches`) and cancellation. Job reads stay registered |
| `CONSUMER_SUBSCRIPTIONS_ENABLED` | off | The webhook subscriptions API (`/api/v1/consumer-subscriptions`), reads included, and from 0.9 C12 their delivery. Their signing keys are sealed with `SECRETS_ENCRYPTION_KEY`. Turned off, stored subscriptions are kept and continue when it is turned on again |
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
| `JOB_LEASE_SECONDS` | 120 | A worker's lease on a job, renewed by its heartbeat every third of it while the job runs; how long a stopped process holds its job before another takes it over |
| `JOB_RETENTION_DAYS` | 7 | How long a finished job keeps its outcomes and idempotency key |
| `FEED_RETENTION_DAYS` | 30 | How long the change feed answers a position; older positions are `410 FEED_POSITION_EXPIRED`, naming the publication to re-read. Entries after the active publication, and every entry of a workspace without one, are always answered. Consumer events expire with the entries (`410 EVENTS_EXPIRED`) and are deleted hourly. The audit log is not pruned |
| `CONSUMER_RESOLVE_MAX_ITEMS` | 1,000 | Items in one consumer batch resolve (`POST /api/consumer/…/resolve`); more are refused as `413 BATCH_TOO_LARGE`. Reported by `GET /capabilities` |

## Authentication

Every route needs an access token issued by the engine (0.12, ADR-043) except `/health`,
`/health/live`, `/openapi.json`, `/docs` with its script, and the OAuth endpoints
(`/.well-known/oauth-authorization-server`, `/oauth/jwks`, `/oauth/token`, `/oauth/revoke`, and the
sign-in and password pages `/oauth/authorize` and `/oauth/password`). A request without one
answers `401 AUTHENTICATION_REQUIRED`; a token that does not verify, has expired, is for the other API
or belongs to a deactivated client or person answers `401 TOKEN_INVALID` with the reason. No setting
turns this off (D235). What a caller may do is decided by its roles: a request its roles do not
allow answers `403 FORBIDDEN`, naming the action, the action groups that would allow it and the
workspace (see [Roles and grants](#roles-and-grants)).

**The first administrator and the first client** are created on the server, in the configured
environment:

```bash
cd backend
.venv/bin/python -m app.cli.create_admin --username ada --name "Ada Lovelace"
.venv/bin/python -m app.cli.create_client --name "Deployment automation" --role workspace-admin --role model-admin
```

`create_admin` reads the password from the terminal twice (`--password-stdin` reads one line from
standard input): 15 to 128 characters, not the username, not one of the most common (D252). The
administrator then signs in from the browser. The first administrator holds, at the instance,
Security administrator and every role needed to set the instance up: Data owner, Model
administrator, Workspace administrator, Integration administrator and Operator (D282). Hand out
narrower roles and remove these when others take over. `create_client` prints the client's
`client_id` and `client_secret` once (`--json` for a script); keep the secret in the calling
system's secret store. Each `--role` (a role's key) is granted to the client at the instance;
without one it may do nothing until a Security administrator grants it a role. More clients and
people are managed through `/api/v1/clients` and `/api/v1/users`.

**A client obtains a token** with the client credentials grant and sends it as a bearer token:

```bash
curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
  http://localhost:8000/oauth/token
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/api/v1/workspaces
```

`scope=consumer` asks for a token for the consumer APIs (`/api/consumer`); the default, `management`,
is for `/api/v1` and `/metrics`. A token lasts `ACCESS_TOKEN_MINUTES`; a client asks for a new one
with the same credentials, as OAuth client libraries do on expiry or on a `401`. A client's secret is
rotated with `POST /api/v1/clients/{id}/secrets` (`overlapHours`, 24 by default): both secrets work
during the overlap. A client is deactivated with `PATCH /api/v1/clients/{id}` `{"active": false}`;
its tokens are refused from the next request.

**Signing keys** are made by the engine, stored sealed with `SECRETS_ENCRYPTION_KEY` and published at
`/oauth/jwks`. A new key replaces the current one after `TOKEN_SIGNING_KEY_DAYS`; tokens of the old
one stay valid until they expire, and nobody acts. After a suspected leak,
`POST /api/v1/token-signing-keys/rotation` `{"immediate": true}` refuses the old key's tokens at once;
clients obtain new ones with their unchanged credentials. `GET /api/v1/token-signing-keys` lists the
keys and their state, never a private key.

**Setting up:** set `SECRETS_ENCRYPTION_KEY` (`python -m app.cli.generate_key`) and, outside local
development, `PUBLIC_URL` and `CORS_ORIGINS`; then create the first client and administrator with the
commands above. Local accounts have a password only; a sign-in provider (I3) brings the
organisation's multi-factor sign-in (D225).

### Roles and grants

A **role** is a set of action groups (Browse, Edit live, Work in change sets, Publish, Bulk and
import, Copy and move, Model authoring, Model release, Workspace administration, Integration
administration, Feed, Operations, Security administration); `GET /api/v1/action-groups` lists them
with the operations each allows. Nine roles are predefined and read-only (Reader, Contributor, Data
steward, Data owner, Model administrator, Workspace administrator, Integration administrator,
Operator, Security administrator); custom ones are made from scratch or copied
(`/api/v1/roles`). A **grant** gives a role to a person, a client or a group of people
(`/api/v1/groups`) at the instance, which covers every workspace, or in one workspace, optionally
narrowing what may be changed to applications and record types (`/api/v1/grants`). Reading a
workspace is never narrowed: data some readers must not see belongs in a workspace of its own.
`GET /api/v1/workspaces/{key}/access` lists who can do what there. A change to a grant, role, group
or membership applies on the next request on every process. Until the Security pages (SP1), these
are API calls made with a Security administrator's token. The deployment flags still decide which
operations exist at all; a role decides who may use them.

**Upgrading to 0.12 Z1** grants every person and client that existed before it the first
administrator's roles at the instance, so nothing that worked stops (D282); review them with
`GET /api/v1/grants`.

**A narrowed grant** limits every write its holder makes in the workspace (0.12 Z2): live edits,
change sets, batches and imports, publishing, moves into it and type changes, each refused with
`403 FORBIDDEN` naming the record types outside it. After a model change, look for grants marked
`stale: true` in `GET /api/v1/grants`: the types or applications they name are gone and allow
nothing, so replace them.

**Jobs run with their requester's rights** at every step (0.12 Z2): taking a role away from a person
or client, or deactivating them, also stops their queued and running jobs at the next step, which
then fail naming the requester. Jobs queued before upgrading to 0.12 Z2 name no requester and run
as before; an import profile's files uploaded before it name no uploader and are seen by the
workspace's Bulk and import holders.

**Locked out:** the engine refuses to remove the last active person holding Security administration
at the instance (`409 LAST_SECURITY_ADMINISTRATOR`). If every such person is lost anyway, run
`python -m app.cli.create_admin` on the server: the new person holds Security administration again.

**Monitoring** with `/metrics` needs a client holding the Operator role
(`create_client --role operator`).

### Signing in from the browser

The browser application signs a person in on the engine's own page, `/oauth/authorize`, with the
authorization code flow and PKCE (0.12 I2, D234): opening the application without a session leads
there, and signing in returns to the page asked for. The page shows the default workspace's product
name, needs no script, and cannot be framed. The access token stays in the page's memory; the
session is held in an `HttpOnly`, `SameSite=Strict` cookie named `oauth_refresh`, scoped to `/oauth`,
which the browser renews unseen while the person works. Each renewal replaces the cookie's token; a
token presented a second time ends the session, since only a copy can do that.

- **Serve over `https`.** The cookie is marked `Secure` when `PUBLIC_URL` is `https` (D268); over
  plain `http` it is not, which is for a development machine only.
- **One site.** The application and the engine must share a site (the same registrable domain, for
  example `rdm.example.org` and `api.rdm.example.org`, or one host on two ports in development), or
  the browser does not send the cookie. The application's origin is in `CORS_ORIGINS`.
- **Sessions** end after `SESSION_IDLE_HOURS` without use or `SESSION_DAYS` in all, when the person
  signs out (the account menu), signs out everywhere (Settings › Account, or
  `DELETE /api/v1/users/{id}/sessions` by an administrator), changes or resets their password, or is
  deactivated. Their access tokens are refused from the next request.
- **A first password** for a person created through the API: `POST /api/v1/users/{id}/password-reset`
  answers a one-time link, valid `PASSWORD_RESET_HOURS`, to pass on to the person (no e-mail is sent,
  D233). It opens the engine's page that sets the password; a newer link replaces an older one, and
  using it ends the person's sessions. The same link resets a forgotten password.
- **Failed sign-ins are slowed, never locked** (D271): after 5 failures for one username, or 20 from
  one address, each attempt waits 1 second, doubling to at most 15 minutes, and the page says how
  long. A success clears the username's count; counts lapse after 24 hours. Each failure is logged
  (`sign_in_failed`, with the username and address). Behind a proxy, the address is the proxy's
  unless uvicorn trusts it to forward the caller's (`--forwarded-allow-ips` with
  `--proxy-headers`); without that, every person shares the proxy's address and its count of 20.

## Database

PostgreSQL 17 is the only supported database (since 0.9.0-alpha.1). The database's default collation
must be the ICU root collation `und` (a language-independent Unicode order), and the role needs the
`pg_trgm`, `btree_gin` and `pgcrypto` extensions (all in PostgreSQL's contrib modules; `btree_gin`
since 0.9 C14, `pgcrypto` since 0.11, for the counterpart IDs a move derives), which startup creates
when it may. For a server other than the development one:

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
| `scripts/postgres.sh backup` | Writes a `pg_dump` file to `backend/.postgres/backups/`, without the processes' rows |
| `scripts/postgres.sh rehearse [<dump>]` | Restores the newest (or the named) dump into a scratch database, checks it with `app.cli.restore_check`, records the result in `rdm` and drops the scratch database ([Backup and restore](#backup-and-restore)) |

Nothing starts at login. Docker Compose runs `postgres:17-alpine` with the same collation.

SQLite was only ever a development database. The engine runs on PostgreSQL only and offers no
migration from SQLite.

## Startup checks and health

Startup refuses to serve, logs what to do and answers `GET /health` with `503` when:

- `DATABASE_URL` is missing, not PostgreSQL, uses another driver, or the server is unreachable;
- the database has another collation, or `pg_trgm`, `btree_gin` or `pgcrypto` is missing and cannot
  be created;
- the database schema revision is unknown, or a migration fails (see [Upgrades](#upgrades));
- every workspace runs a model release whose schema is outside the engine's window; the log names
  the release's and the supported schemas and the recovery: for schema 0.4 the offline transition
  command (`python -m app.cli.model_schema_upgrade`), for a schema newer than the window (a database
  a later RDM Engine used) to start that version (0.11 V4);
- `RDM_MODEL_PATH` names a model of a schema outside the window: the process does not start, and the
  message names the setting, the file, its schema and the supported ones;
- `SECRETS_ENCRYPTION_KEY` is missing or not 32 bytes in URL-safe base64, or the retired
  `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` is set, or `PUBLIC_URL` is not an absolute `http(s)` URL: the
  process does not start, and the message names the setting (0.12 I1).

`/health` also returns `503` when an activation committed but this process could not load the newly
selected release. Restart the process; it then loads the database selection.

While the service runs, `/health` asks the database each time: while the database is unreachable it
answers `503`, and requests answer `503 DATABASE_UNAVAILABLE` with `details.reason` `unreachable`
and `Retry-After` (logged in one ERROR line, no traceback; before 0.11 Q1 `500 INTERNAL_ERROR`). Nothing needs restarting: once the database is back, `/health` answers `200`, requests
are served and the job worker, the event deriver and the webhook dispatcher resume. Each retries
every 2 s and logs the outage in one ERROR line saying it cannot reach the database, then a WARNING
a minute, then an INFO line when the database answers again, with no traceback: an unreachable
database is an expected failure. The traceback is logged at DEBUG, for escalation. Any other
failure of these threads is logged at ERROR with its traceback, since it points at a defect.

## Monitoring

Every process reports itself to the others through the database (table `engine_processes`, 0.11
O1): every `PROCESS_HEARTBEAT_SECONDS` it writes whether it is ready, its background threads, its
pool, the releases it cannot serve and its counters. A request reaches one process, so this is how
any process answers for all of them. A process that stops cleanly deletes its row; one that dies
leaves it, listed `silent` after three heartbeats and deleted after a day. Another process's
figures are up to one heartbeat old; the asking process's are current.

**Probes.** Point the orchestrator's liveness probe at `GET /health/live`: it answers `200`
whenever the process answers and asks nothing else, so a database outage restarts nothing. Point
the readiness probe (and a load balancer's health check) at `GET /health`, as before: `503` while
the database is unreachable or no workspace can be served. A workspace one process cannot serve
does not fail `/health`; read it from readiness.

**Readiness.** `GET /api/v1/system/readiness` lists each active workspace, its release, `served` or
`unavailable`, and the live processes that cannot serve it, each with why: `unsupportedSchema` (the
release's schema is outside this version's window; see [Startup checks](#startup-checks-and-health)),
`invalid` (the model does not validate) or `notLoaded` (activated, but this process could not load it;
restart it). A workspace that runs no release is `unavailable` with no process named.
`GET /api/v1/system/processes` lists every process: its ID (`host:pid:random`, as a job's
`leaseOwner` begins), version, start, last heartbeat, `live` or `silent`, `ready`, its threads
(`jobWorker`, `exportWorker`, `jobListener`, `eventDeriver`, `webhookDispatcher`, `heartbeat`,
each `running`, `failing` with the reason and since when, or `off` when not started), its pool and
its counters. Both page like every collection. `GET /api/v1/system/summary` gives the instance
figures that `/metrics` counts when scraped (below) as JSON: processes live and silent, workspaces
served and unavailable, jobs by kind and state, webhook subscriptions by state.

**In the browser.** Settings › Administration › **Operations** shows the four figures, each
workspace and the processes that do not serve it, every process with its threads, connections and
requests, the last [backup rehearsal](#backup-and-restore) and the probe addresses. It reads again
every 15 seconds while it is open and visible.

**Metrics.** `GET /metrics` answers the whole instance in the Prometheus text format (0.0.4): scrape
any one process, or the load balancer, once; scraping every process returns the same series. Per
live process, labelled `process`:

| Series | Kind | What |
| --- | --- | --- |
| `rdm_process_ready` (`version`) | gauge | `1` when the process serves requests |
| `rdm_process_start_time_seconds` | gauge | When it started |
| `rdm_http_requests_total` (`method`, `route`, `status`) | counter | Requests answered; `route` is the route's template, `unmatched` for none |
| `rdm_http_request_duration_seconds` (`route`) | histogram | Time to answer, buckets 5 ms to 10 s |
| `rdm_database_unavailable_total` (`reason`) | counter | Requests answered `503 DATABASE_UNAVAILABLE` and background thread outages begun, by reason: `poolExhausted`, `tooManyConnections`, `transactionEnded`, `unreachable` |
| `rdm_database_pool_size`, `rdm_database_pool_max_overflow` | gauge | The pool settings |
| `rdm_database_pool_connections_in_use` | gauge | Connections checked out at its last heartbeat |
| `rdm_background_thread_failing` (`thread`) | gauge | `1` while a started thread's rounds fail |
| `rdm_releases_unavailable` | gauge | Releases some workspace runs that it cannot serve |

Counted when scraped: `rdm_processes` (`state`: `live`, `silent`), `rdm_jobs` (`kind`, `state`:
`queued`, `running`, `awaiting_confirmation`), `rdm_webhook_subscriptions` (`state`: `active`,
`failing` while a batch is being retried, `suspended`) and `rdm_workspaces_unavailable`. A counter
restarts with its process, under a new `process` label. Nothing is labelled by workspace, record
type or record.

Worth alerting on: `rdm_workspaces_unavailable` above 0; `rdm_process_ready` 0; `rdm_processes`
`silent` above 0; `rdm_database_unavailable_total` rising (the reason names the setting, see
[Database connections](#database-connections)); `rdm_background_thread_failing` 1 for minutes;
`rdm_jobs` `queued` growing; `rdm_webhook_subscriptions` `suspended` above 0.

**Who can read them.** `/health` and `/health/live` need no token, so probes work unchanged; they
say only `ok` or `unhealthy`. `/metrics` and `/api/v1/system/*` need an access token (0.12 I1): a
Prometheus scrape uses a client's token (`authorization` with `credentials_file`, or the
`oauth2` client credentials block with `token_url` `/oauth/token`), and the client needs the
Operator role (0.12 Z1); `GET /api/v1/system` alone (the engine and its release) is open to anyone
signed in.

### Logs

The engine writes to standard error. With `LOG_FORMAT=json` each line is one JSON object: `time`
(UTC), `level`, `logger`, `message`, `process` (the PID), `thread`, and within a request
`requestId`, `method` and `route`; a traceback is in `exception`. The engine writes one access line
per request (logger `app.access`: method, path, status, `durationMs`) in place of uvicorn's, at
`INFO`, and at `DEBUG` for `/health`, `/health/live` and `/metrics`. The text format writes the same
records as `time LEVEL logger: message [request ID]`.

Each request has one ID: the `X-Request-Id` the client or a proxy sent, when it is 1–64 letters,
digits, `.`, `_` or `-`, otherwise a generated one. It comes back in the `X-Request-Id` response
header and is every log line's `requestId`, and `INTERNAL_ERROR`'s `correlationId` is it: search the
log for the reference a user reports. An expected failure (an unreachable database, a refused start)
logs one line without a traceback; its traceback is at `DEBUG`.

## Background jobs

Batches sent with `run: background` are run by a worker thread inside the API process. It runs only
while `INTEGRATION_JOBS_ENABLED` is on and the model is healthy, and expires finished jobs past their
retention every hour.

- **Graceful stop:** the running chunk finishes and the worker releases its lease, so the next start
  resumes the job at once.
- **Crash or kill:** the chunk in progress rolls back. Once the lease expires (`JOB_LEASE_SECONDS`), the
  next worker (in another process, or in this one after a restart) resumes the job at its
  first item without an outcome. No item is applied twice or skipped.
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
| `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` | 7 | Days the delivery log keeps each request, with the body it sent (up to 1 MiB), its events and its attempts (0.9 U5a); a batch still being retried or awaiting a resume is kept longer. Reported by `GET /api/v1/capabilities` |

**The delivery log** (0.9 U5a) records every request the dispatcher sends: its body, the events
it carries and each attempt's start, duration and answer (up to 4 KiB). It is read on Settings ›
Integration › Webhooks, Deliveries, and through `GET /api/v1/consumer-subscriptions/{id}/deliveries`.
A busy subscription writes up to 1 MiB per request: size the database for the retention. The
dispatcher deletes expired entries at most hourly.

A webhook URL may name any host and port. It must use HTTPS; plain HTTP is accepted only to
`localhost`, `127.0.0.1` or `::1` (development). There is no host allowlist (C-D101 revised).

- **The key:** signing keys are stored sealed with `SECRETS_ENCRYPTION_KEY` (0.12 D253; before
  0.12, `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup now refuses by name: rename it, keeping
  its value). Changing the key makes every stored signing key unreadable until re-sealing arrives
  (0.12 K1).
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
installs its content when that release is missing and gives it to a workspace that runs none (a new
database's default workspace); an existing database keeps the release each workspace runs
(`workspace_models`, 0.11 M1), even when the file holds a newer one. Changing the file never activates
it. A release this version cannot serve, such as one of an unsupported schema, makes only the
workspaces running it unavailable (`503 MODEL_REGISTRY_UNAVAILABLE` naming the workspace); startup
logs each, with the schema upgrade command for schema 0.4 or, for a schema newer than the window,
the later engine to run, and `/health` answers 503 only when no
workspace can be served (or the database is unreachable).
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
2. Take a consistent backup (`pg_dump` or the platform's snapshot) and
   [rehearse its restore](#backup-and-restore).
3. Keep the backup with the application version and its configuration, especially `DATABASE_URL`,
   `RDM_MODEL_PATH`, `RDM_CURSOR_SIGNING_KEY`, `SECRETS_ENCRYPTION_KEY` (without it the restored
   signing keys cannot be read), the capability settings and the worker count.
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

## Backup and restore

The database is the whole state of an instance: every workspace's records, change sets,
publications and history, the installed model releases and which workspace runs which, jobs,
webhook subscriptions and the feed. A backup of the database is a backup of the instance. Keep with
it the application version and its configuration (see [Upgrades](#upgrades)); the cursor signing
key and the webhook key encryption key are settings, not data, and a restore needs the same ones.

**Taking a backup.** `pg_dump` in its custom format, or the platform's snapshot. The processes'
heartbeat rows are of no use in a backup; leave them out:

```bash
pg_dump -Fc --exclude-table-data=engine_processes -f rdm-$(date +%Y%m%d-%H%M).dump postgresql://rdm@db/rdm
```

A backup taken without the option restores as well; the old processes are then listed `silent` until
they age out after a day.

**Rehearsing a restore.** A backup is known to work only once it has been restored. Restore it into
a new, separate database with the ICU root collation, then check that copy from the backend
directory with the instance's own `DATABASE_URL`:

```bash
createdb -T template0 --locale-provider=icu --icu-locale=und --locale=C rdm_restore_check
pg_restore --no-owner -d rdm_restore_check rdm-20261022-0200.dump
cd backend
.venv/bin/python -m app.cli.restore_check \
    --restored postgresql+psycopg://rdm@db/rdm_restore_check --backup rdm-20261022-0200.dump
dropdb rdm_restore_check
```

The check meets what a recovery from that backup would meet. It prepares the copy as startup
prepares a database (collation, extensions, migrations to this engine's revision, so the copy is
changed), clears the processes' rows that came with it, loads each active workspace's release on its
own and counts the workspace's records, relationships, open change sets and publications in
PostgreSQL, beside the instance's records of that workspace now. It passes when the copy could be
prepared and every active workspace in it is served. It does not validate every record again: the
backup holds what the engine wrote and validated.

The result, passed or failed, is recorded in the instance (`backup_rehearsals`) and shown on
Settings › Operations and by `GET /api/v1/system/backup-rehearsals`; the copy gets nothing. The
command prints the same and exits `0` when it passed, `1` when it failed and `2` when nothing was
checked (the copy named is the instance's own database, the URL is not PostgreSQL, or the
instance's database cannot be reached). A failure names its reason and what to do:
`DATABASE_COLLATION`, `DATABASE_EXTENSIONS`, `DATABASE_REVISION_UNKNOWN` (the backup was written by
a newer version), `DATABASE_MIGRATION_FAILED`, `DATABASE_UNREACHABLE`, or `WORKSPACES_NOT_SERVED`
(a workspace runs a release this engine cannot read; activate a supported release in it, or keep
the engine version that reads it with the backup). No route runs the check: restoring needs the
PostgreSQL client programs and the right to create databases, which the engine's own role should
not have (0.11 D198).

For development, `scripts/postgres.sh backup` and `scripts/postgres.sh rehearse` do the same on
the development server.

**Recovering.** Stop every process; restore the backup into the database `DATABASE_URL` names (a
new database with the ICU root collation, or the emptied one) with `pg_restore --no-owner`; start
the application version kept with the backup, or a newer one, which migrates it at startup. Each
workspace runs the release it ran when the backup was taken.

**What a restore is.** Restoring a backup replaces the whole database. Nothing inside the engine
restores data: a change set started from an earlier publication applies only what is edited in it
and leaves newer live data as it is, and withdrawing a publication changes no data
([ARCHITECTURE](ARCHITECTURE.md)). To bring back part of an earlier state, read it from a restored
copy and write it through the API as a change set.

**Rehearsed (0.11 O2, 2026-10-22).** On the development server: `scripts/postgres.sh backup` wrote
a 26 MB dump of `rdm` in 2.6 s; `scripts/postgres.sh rehearse` restored, checked and dropped it in
8.6 s. Six workspaces on three different models, all at schema 0.10: every workspace served from
the copy, each under its own release, with 6,665 records, 14,303 relationships, 6 open change sets
and 7 publications, the record counts equal to live. The copy was at revision `20261025_01` and needed no migration. The browser runner
`test:browser:operations` and the journeys J12.16 and J12.17 repeat it on two generated models,
including a copy with the wrong collation and a workspace on a release outside the schema window.

