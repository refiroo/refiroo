# Operations

How to configure, run, upgrade and recover refiroo (the application; the engine inside it is the RDM engine, see [BRANDING.md](BRANDING.md)). The design reasons behind these rules are in
[ARCHITECTURE.md](ARCHITECTURE.md); the API contracts are in [API.md](API.md). The setting names and the documented commands are committed from 0.12.0
([COMPATIBILITY.md](COMPATIBILITY.md)).

Every API needs a signed-in person or an access token ([Authentication](#authentication)); only
the health checks and the paths people sign in through are open. Keep the engine behind HTTPS ([Deploying](#deploying)).

## A developer instance

`scripts/dev.sh` runs one for development, each server in the foreground of its own terminal
(0.12 Track DP, D411); `scripts/dev.sh` alone lists its commands. `scripts/dev.sh settings` writes
`.dev/settings.env` (git-ignored): `DATABASE_URL` for `scripts/postgres.sh`'s database, a new
`SECRETS_ENCRYPTION_KEY` (or the one already in your environment, which an existing database needs),
and every other setting commented out at its default with its one-line description. Run again on an
existing file, it keeps every line, adds the settings a newer version brings and comments out a
retired one the engine would refuse. A setting in your environment wins over the file; restart the
engine after a change. `scripts/dev.sh admin <e-mail> "<name>"` makes
the first administrator.

### From a phone on the same network

A browser signs in (PKCE) and uses passkeys
only on a secure page, `https` or `localhost`, so another device needs https:

| Step | What it does |
| --- | --- |
| `scripts/dev.sh cert` | Finds this computer's address on the network (the one its default route leaves from; `RDM_DEV_ADDRESS` overrides it), trusts mkcert's authority on this computer and makes a certificate for the address, `localhost` and `127.0.0.1` in `.dev/certs/`; again when the address changes |
| On the phone, once | Trust mkcert's authority (`mkcert -CAROOT`/`rootCA.pem`): on an iPhone install the profile, then switch it on under Settings › General › About › Certificate Trust Settings; on Android install it as a CA certificate |
| `scripts/dev.sh engine --network` | The engine on `https://<address>:8000` with `PUBLIC_URL=https://<address>:5173` (the address people open) and `CORS_ORIGINS` listing the frontend's names and the engine's own `https://<address>:8000`, `https://localhost:8000` and `https://127.0.0.1:8000`, so the API reference at `/docs/api` works under any of those names; it trusts the forwarded caller address from this computer (`--proxy-headers`) |
| `scripts/dev.sh frontend --network` | The frontend on `https://<address>:5173` (`DEV_HTTPS_CERT` and `DEV_HTTPS_KEY` switch Vite to https), forwarding the engine's paths to `https://localhost:8000` |

**One address (0.12 DP1, D404).** The application calls the engine on the address the page was opened
at, unless `VITE_API_URL` names an engine on another address when the frontend is built. The Vite dev
server forwards the engine's paths to the engine at `ENGINE_URL` (default `http://localhost:8000`):
`/api`, `/oauth`, `/.well-known`, `/docs`, `/openapi.json` and `/health`; `/metrics` is not forwarded,
and `/brand` is the application's own. `/docs` is the documentation (0.13 DOC1; its step-by-step guides are
under `/docs/guide/`) and `/docs/api` the API reference. The documentation is built from `guide/` with
`npm ci && npm run build` there; the engine serves the built files, and without a build `/docs` answers a page
that says so while everything else works. The public site (no engine behind it) is built with `npm run build:public` in `guide/`, which also writes a static, read-only API reference (the management API and the guide's example consumer API) into the build at `api/`; an instance build does not use it. Open `http://localhost:5173` (or `https://<address>:5173` on
every device, this computer included), never the engine's port: `PUBLIC_URL` is that address, the
sign-in cookie is on it (one site, below) and passkeys are bound to its host. `scripts/dev.sh engine`
sets `PUBLIC_URL=http://localhost:5173` unless it is already set. Changing between the network and
`localhost` changes `PUBLIC_URL`, so everyone signs in again. This is for development; an
installation is served as [Deployment topologies](#deployment-topologies) says.

## Settings

The backend reads its settings from the environment at startup (`backend/app/config.py`).
`GET /api/v1/capabilities` reports the effective capability groups and job limits, and
`GET /api/v1/system/configuration` every setting with its value, default and source (secrets only as
set or not, `DATABASE_URL` without its password). In the browser, **Settings › Deployment** shows both, read only:
a change needs a restart.

A new setting is added to the `Settings` model, to the settings catalogue in `config.py` (its group
and the one line the API and the Deployment page show) and to the table of its group below.
`tests/unit/test_config.py` fails until all three agree. The two settings files are written from the
same catalogue by `python -m app.cli.settings_template` (run from `backend/`): the developer's
`.dev/settings.env` (`--for dev`, through `scripts/dev.sh settings`) and the generated part of
`.env.example` (`--for compose`), which `tests/unit/cli/test_settings_template.py` holds equal to it, so
both list every setting. In the reference installation `compose.yml` passes everything set in `.env`
to the engine.

### Runtime

| Setting | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | required | PostgreSQL URL, `postgresql+psycopg://…`. See [Database](#database) |
| `RDM_MODEL_PATH` | `model/rdm-starter.json` | Bootstrap model file. Not the active-model setting; see [Model releases](#model-releases-and-rollback) |
| `RDM_CURSOR_SIGNING_KEY` | ephemeral | Secret that signs pagination cursors. Without it each process generates its own key, so cursors stop working after a restart and between instances |
| `AI_AGENT_COMMAND` | none | The command of the AI assistant's session, such as `claude --model sonnet --permission-mode bypassPermissions`; the provider's key and base URL come from the environment. It runs as a process of the worker. The engine adds its guards to every session: its own folder, its tools, this engine on the network, a client that cannot publish or activate, and none of the server's secrets in its environment. **This setting alone turns the assistant on**: it needs no `AI_PROVIDER`, and Settings › AI and `POST /ai/tasks` treat an empty value as "no assistant" (`409 AI_NOT_CONFIGURED`). Empty: no assistant action is offered. |
| `AI_AGENT_SANDBOX` | operating system sandbox | `container` when the engine runs in a container, where Claude Code's own sandbox cannot run. The engine image sets it (`ENV` in `backend/Dockerfile`) and `compose.yml` sets it again, where a `.env` cannot turn it off (0.17 RF4); it is empty only for an engine that runs without a container. In a container the session runs as a user of its own, never as the engine's, started through `sudo`, whose rule lets the engine's user run two commands as one of the image's session users and nothing else: the Claude Code binary and `/usr/local/bin/refiroo-session-reset`. The session cannot read the engine's environment (the database address, the encryption key) or the job files. **What separates one session from another (0.17 RF5): permissions, not names.** The image holds a pool of session users, `assistant-1` to `assistant-N`, each with a home and a group of its own (the engine's user is a member of every one) and all in the group `assistant`. A turn takes a free one for its length (a lock file in `data/assistant-slots`, which only the engine enters), so two sessions running at once are two different users. The pool's size is the image's build argument `ASSISTANT_USERS` (default 8): set it to at least the number of engine processes (`WEB_CONCURRENCY`), one session running per process, and build the image again (`docker build --build-arg ASSISTANT_USERS=16 …`). A turn that finds every user taken does not start: the task fails with a note naming `ASSISTANT_USERS`, and the log has one ERROR line. Each task has a folder, its gate, in `AI_AGENT_FOLDERS` (default `/opt/refiroo/rdm-engine/data/assistant`) under a random name of at least 100 bits, in a folder the session users may enter but not list (mode 2710). The gate belongs to the engine alone (0700) and, for the length of a turn, to the group of the one session user that runs it (0710): no other session user can enter it, whatever names it knows, and no session can between turns. Inside it, `work` is the session's working folder (and `$TMPDIR`), `claude` the task's own Claude Code folder (`CLAUDE_CONFIG_DIR`, set per session; the image sets none) with its transcripts, and the engine's stream log of each turn (mode 0600). The engine makes them once, before a session has run in them, where a session has no write right; afterwards it neither changes a mode nor writes there by following a path a session controls. **The reset:** around each turn the engine runs `refiroo-session-reset` as the session user, never as root. It first ends every process the user runs, again and again until none is left (so a process that forks meanwhile cannot slip past), and only then empties the user's home and its files in `/tmp`, `/var/tmp` and `/dev/shm`; after a turn it also makes the user's files in the task's two folders readable and writable by the group (Claude Code writes its transcript for its own user alone, and the next turn may run as another), and ends processes once more. Order, so that no process of a session is alive when anything is cleaned or the gate changes: before a turn, reset (gate closed), then open the gate, then start the session; after a turn, reset (gate still open for the user's files), then close the gate. A reset that fails before a turn fails the turn and opens no gate; one that fails after a turn is logged, and the next turn under that user starts with a reset of its own. The task's folders reach the script on standard input, not on its command line. `compose.yml` sets `init: true` on the engine service: a process reaper as PID 1 collects what the reset ends (the engine does not); a deployment of its own should run the engine image with an init (`docker run --init`). Nothing secret is on a session's command line, which every process of the container can read: the person's words reach the session on its standard input, and no folder's path is an argument. The command line holds the session's ID, which the engine needs to find a session a stopped worker left running; the ID alone opens nothing. The session is passed only named variables, the same list in the engine (`PASSED_NAMES` in `backend/app/engine/tasks/agent.py`) and in the sudoers rule: `REFIROO_TOKEN`, `LANG`, `LC_*`, `TMPDIR`, `CLAUDE_CONFIG_DIR`, the provider's credential (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or `CLAUDE_CODE_OAUTH_TOKEN`), `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL` and `ANTHROPIC_DEFAULT_OPUS_MODEL`, `_SONNET_MODEL` and `_HAIKU_MODEL`, `NODE_EXTRA_CA_CERTS`, and, only when `CLAUDE_CODE_USE_BEDROCK` is on, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` and `AWS_PROFILE`. Any other variable (a proxy's `HTTPS_PROXY`, say) is not passed. In a container the session runs with Claude Code's permission prompts off (`bypassPermissions`), because without the sandbox Claude Code refuses compound shell commands otherwise; the separate session user is the boundary. **Three limits remain.** (1) **The provider's credential reaches the session:** Claude Code calls the provider itself, so the key or subscription token is in its environment, and a session steered by text in its workbook could use or send it. Give the engine a key meant for this (a project key with a spending limit), not one that does more. (2) **The container does not limit where a session connects:** give the container only the network it needs. (3) **Isolation between tasks inside one container rests on Unix permissions and the reset around each turn.** It has been reviewed twice, with defects found and fixed each time, and is not a proof; a container per session is the stronger form and is not built. The records the session can reach are only those its grants allow. The engine's own secrets stay out of reach. **After the third review (0.17 RF5)** the reset also removes the user's System V shared memory, semaphores and message queues and its files in `/run/lock`, `/dev/mqueue` and `/var/mail`, and a turn closes every gate still open for its user's group (left by an engine killed mid-turn) before it opens its own. **After the second review (0.17 RF5)** the reset ends processes first and repeatedly, takes its folders on standard input, also empties `/dev/shm`, and runs before the gate opens and before it closes, as above. **At the upgrade to 0.17,** the first sweep after the engine starts moves each existing task's folder (named by the task's ID before) into the new layout under a random name, closes the tasks' folder to listing and closes every gate no turn holds; a task's files are kept. The transcripts the earlier version kept in the shared `assistant-claude` folder are not moved: a task that began before the upgrade starts a new session, with its workbook and files, the next time the person tells it something. `compose.yml` no longer mounts the `assistant-claude` volume; remove it when no longer needed (`docker volume rm refiroo_assistant-claude`). Outside a container nothing of this applies: the operating system's sandbox is the boundary and the folders keep their names |
| `AI_AGENT_API_URL` | `PUBLIC_URL` | The address the session reaches this engine's API at. Compose sets it to `http://127.0.0.1:8000`: the session runs inside the engine's container, where `PUBLIC_URL` may not be reachable (`http://localhost:…` names the container itself). |
| `AI_AGENT_TIMEOUT_SECONDS` | `1800` | The longest one turn of the assistant's session may take, in seconds (0.13 AQ). A turn over it is stopped as a person's Stop is: the session ends, the jobs it started are cancelled and a partly loaded change set is discarded, and the task goes back to where it was, its draft kept. The task's note says the session took longer than the limit; the person can tell the assistant to go on or try again. The log has one WARNING line and no traceback, and the job ends `cancelled`, never `JOB_FAILED`. Raise it for a very large workbook |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated browser origins allowed to call the API. They are also where a person's sign-in may return: `<origin>/signed-in` for each (0.12 D267), so the browser application is served at the root of one of them. **The API reference at `/docs` is a browser page too:** when it calls the engine from an origin not listed here (for example `Try it` on `/oauth/token`), the browser's preflight answers `400 Disallowed CORS origin` before the request is sent. List the origin the reference is opened at; `scripts/dev.sh engine` lists the engine's own addresses |
| `PUBLIC_URL` | `http://localhost:8000` | The engine's address as callers reach it, behind any proxy: the issuer (`iss`) of its tokens and the base of the addresses in `/.well-known/oauth-authorization-server` (0.12 D259). An absolute `http` or `https` URL; anything else stops startup. Set it on every production installation, the same on every process. See [Authentication](#authentication) |
| `SOURCE_CODE_URL` | `https://github.com/refiroo/refiroo/tree/v<version>` | Where the source of the running version is offered to its users: `GET /system` (`engine.sourceCode`), Settings › About and the account menu show it (0.12 L1, D219; AGPL section 13). **An operator who runs a modified version sets it to the address of their own corresponding source**, including the modifications and the scripts and configuration that are part of the work; an absolute `http` or `https` address, anything else stops startup |
| `SECRETS_ENCRYPTION_KEY` | required | 32 bytes in URL-safe base64 (`python -m app.cli.generate_key`); seals the stored token signing keys and webhook signing keys (AES-256-GCM, D253). Startup refuses without it, and refuses the setting it replaced, `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, by name. Keep it outside the database and its backups; the same on every process |
| `ACCESS_TOKEN_MINUTES` | `60` | Minutes an access token lasts, for people and clients (D251). A deactivation or a retired key applies on the next request whatever the lifetime |
| `TOKEN_SIGNING_KEY_DAYS` | `30` | Days a token signing key signs; the first token issued after that brings a new key, and the old one keeps accepting its tokens until they expire (D254, D264) |
| `SESSION_IDLE_HOURS` | `12` | Hours a person's browser session lasts without being renewed; the browser renews it while the person works (D251). See [Signing in from the browser](#signing-in-from-the-browser) |
| `SESSION_DAYS` | `14` | Days a browser session lasts in all; then the person signs in again (D251) |
| `PASSWORD_RESET_HOURS` | `24` | Hours a password-reset link stays valid; it works once (0.12 D272) |
| `PASSWORD_MIN_LENGTH` | `15` | Characters a local password needs at least (D252). **For a development machine only** it may be lowered, down to `1`, for a short password (D276); the most common passwords stay refused. Leave it at 15 in production |
| `JOB_FILE_DIR` | `var/job-files` | Where export files wait for download and import files wait to be read, named after their job, and where model authoring's source files are kept (0.10 A3); created at start. With job creation on, a directory that cannot be written stops startup. An export's file is kept while its job is completed and removed when the job expires (`JOB_RETENTION_DAYS`), fails or is cancelled; an import's file until its job finishes. Several instances need it on shared storage. See [Exports](#exports), [Imports](#imports) and [Source files and dry runs](#source-files-and-dry-runs) |
| `RDM_API_REFERENCE_SCRIPT` | `bundled` | `bundled` serves the pinned Scalar script from the engine, so `/docs/api` works offline; `cdn` loads the same version from jsDelivr under its integrity hash. Any other value stops startup |
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
holding a connection while it is served; the job, export and assistant workers, each holding one
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
| `WORKSPACE_ADMIN_MUTATIONS_ENABLED` | on | Workspace create, rename, retire, reactivate, delete and default switching. Each route also needs the `workspaces.manage` permission (the Workspace administration action group). Turn it off on an instance that should never create or retire workspaces |
| `INTEGRATION_JOBS_ENABLED` | on | Everything that creates or runs a job: batches (`POST /api/v1/batches`), imports, source files, model mappings and AI tasks, job cancellation, the job workers, and the dry run after a draft change. Job reads stay registered |
| `CONSUMER_SUBSCRIPTIONS_ENABLED` | off | The webhook subscriptions API (`/api/v1/consumer-subscriptions`), reads included, and from 0.9 C12 their delivery. Their signing keys are sealed with `SECRETS_ENCRYPTION_KEY`. Turned off, stored subscriptions are kept and continue when it is turned on again |

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
| `BATCH_MAX_BYTES` | 5 MiB | Body of an inline batch |
| `ATOMIC_JOB_MAX_ITEMS` | 10,000 | Items in an `atomic` batch, inline or background |
| `BACKGROUND_JOB_MAX_ITEMS` | 1,000,000 | Items in a background batch |
| `BATCH_BACKGROUND_MAX_BYTES` | 50 MiB | Body of a background batch |
| `IMPORT_MAX_BYTES` | 200 MiB | An import's file (`POST /api/v1/imports`); a larger one is `413 IMPORT_TOO_LARGE`, and the request's body is held on disk while it is read. An import's items count against `BACKGROUND_JOB_MAX_ITEMS` and, `atomic`, `ATOMIC_JOB_MAX_ITEMS` (`IMPORT_TOO_MANY_ITEMS`) |
| `JOB_PREVIEW_MAX_ITEMS` | 10,000 | The items a preview runs, an import's (`stage: preview`, 0.9 J3) or a batch's (0.9 K2); beyond them the preview is a `sample`. Named `IMPORT_PREVIEW_MAX_ITEMS` before 0.9 K2, which renamed it without an alias. The preview holds its workspace's write lock (or its change set's claim) while it runs, so a larger value makes other writes in that workspace wait longer once per preview |
| `MODEL_OPERATION_MAX_ITEMS` | 500 | Operations in one request to a model draft (`POST /model-drafts/{id}/operations`, 0.10 A2); more is `413 OPERATION_BATCH_TOO_LARGE`. A request is one step of the draft's history and is applied and validated as a whole, so a larger value makes one step slower to apply and to undo |
| `JOB_CHUNK_ITEMS` | 500 | Items one background chunk commits |
| `JOB_LEASE_SECONDS` | 120 | A worker's lease on a job, renewed by its heartbeat every third of it while the job runs; how long a stopped process holds its job before another takes it over |
| `JOB_RETENTION_DAYS` | 7 | How long a finished job keeps its outcomes and idempotency key |
| `FEED_RETENTION_DAYS` | 30 | How long the change feed answers a position; older positions are `410 FEED_POSITION_EXPIRED`, naming the publication to re-read. Entries after the active publication, and every entry of a workspace without one, are always answered. Consumer events expire with the entries (`410 EVENTS_EXPIRED`) and are deleted hourly. The audit log is not pruned |
| `CONSUMER_RESOLVE_MAX_ITEMS` | 1,000 | Items in one consumer batch resolve (`POST /api/consumer/…/resolve`); more are refused as `413 BATCH_TOO_LARGE`. Reported by `GET /capabilities` |

## Authentication

Every route needs an access token issued by the engine (0.12, ADR-043) except `/health`,
`/health/live`, `/openapi.json`, `/docs` (the documentation and, at `/docs/api`, the API reference with its script), and the OAuth endpoints
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
.venv/bin/python -m app.cli.create_admin --email ada@example.org --name "Ada Lovelace"
.venv/bin/python -m app.cli.create_client --name "Deployment automation" --role workspace-admin --role model-admin
```

`create_admin` reads the password from the terminal twice (`--password-stdin` reads one line from
standard input): 15 to 128 characters, not the e-mail address, not one of the most common (D252). The
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
commands above. Local accounts have a password, and optionally an authenticator app as a second
factor (D383, [A second factor for local accounts](#a-second-factor-for-local-accounts)); a
sign-in provider brings the organisation's own multi-factor sign-in (D225, [Signing in with the
organisation's provider](#signing-in-with-the-organisations-provider)).

### Changing `SECRETS_ENCRYPTION_KEY`

The key seals what the engine must read back: token signing keys, webhook signing keys, a sign-in
provider's client secret, authenticator secrets, the provider ID tokens kept with a session, the mail
server's password and the text of mail waiting to be sent. To
move to a new key (a suspected leak, or a policy), with the engine **stopped** (a running process would
seal new values with the old key):

1. Leave the current key in `SECRETS_ENCRYPTION_KEY`, make the new one with
   `python -m app.cli.generate_key` and put it in `NEW_SECRETS_ENCRYPTION_KEY` (never as an argument,
   which a shell keeps in its history).
2. `python -m app.cli.reseal_secrets --check` proves every sealed value opens with the current key and
   changes nothing.
3. `python -m app.cli.reseal_secrets` re-seals every value in one transaction: all or none. If one does
   not open (another key, damaged data) it names each by kind and identity, never by content, and
   changes nothing. It refuses a new key equal to the current one. It prints what it re-sealed.
4. Set `SECRETS_ENCRYPTION_KEY` to the new key everywhere, keep it beside the backups (a backup taken
   before the re-sealing needs the old key), and start the engine.

A re-sealing does not change any key's value, so receivers and tokens are unaffected; to change a
webhook's or a token key itself, rotate it (above).

**Recovery codes do not survive a new key.** They are not sealed: each is stored as an HMAC keyed with
`SECRETS_ENCRYPTION_KEY` itself, so the re-sealing cannot carry them over, and under the new key none
of the existing ones is found. `--check` and the re-sealing both print how many people hold unused
recovery codes ("voids the unused recovery codes of N people"): those people must make new ones on
Account › Second factor (their authenticator app keeps working; it is re-sealed). Tell them before the
change; a person who has lost the app as well must be helped by an administrator (the second factor
removed on their page).

### Roles and grants

A **role** is a set of action groups (Browse, Edit live, Work in change sets, Publish, Approve publications, Bulk and
import, Copy and move, Model authoring, Install a model, Model release, Workspace administration, Integration
administration, Feed, Operations, Security administration, Use AI proposals); `GET /api/v1/action-groups` lists them
with the operations each allows. Ten roles are predefined and read-only (Reader, Contributor, Data
steward, Data owner, Model administrator, Workspace administrator, Integration administrator,
Operator, Security administrator, Agent: the most an agent token holds); custom ones are made from scratch or copied
(`/api/v1/roles`). A **grant** gives a role to a person, a client or a group of people
(`/api/v1/groups`) at the instance, which covers every workspace, or in one workspace, optionally
narrowing what may be changed to applications and record types (`/api/v1/grants`). Reading a
workspace is never narrowed: data some readers must not see belongs in a workspace of its own.
`GET /api/v1/workspaces/{key}/access` lists who can do what there. A change to a grant, role, group
or membership applies on the next request on every process. Settings › Security makes each of
these a page (People, Groups, Roles, Clients, and a workspace's Access).

**Clients and signing keys on a page** (0.12 SP2): Settings › Security › Clients creates a client and
shows its ID and secret once; **Rotate secret** makes a new one and keeps the current one working
for 1 hour, 24 hours (the default) or 7 days, or stops it at once for a leaked secret; the Secrets
table tells them apart by their last four characters, and **End now** stops the previous one before
its overlap ends. Settings › Security › Signing keys lists the token signing keys; **Start a new
key** rotates now (the previous key verifies its tokens until they expire), and **Retire the
current key now** refuses its tokens at once: sessions renew on their own, and each client is
refused once and fetches a new token with its unchanged secret. The deployment flags still decide which
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

**Consumer API grants** (0.12 Z3): a system reading a consumer API needs a grant of that API in
each workspace it reads, made with `POST /api/v1/grants` naming `consumerApi` instead of `role` and
`scope: {"workspaceKey": …}`; no role, not even the Security administrator's, opens the consumer
data routes. **After upgrading to 0.12 Z3, every consumer client reads nothing** (`403 FORBIDDEN`
naming the API and workspace) until it is granted the APIs it reads; the index and the OpenAPI
documents read with the browser's token are unaffected for anyone holding Browse. A grant whose API
a later release drops reads `stale: true` and allows nothing. Subscriptions created before Z3 name no
owner.

**Who changed what** (0.12 Z4): every audit entry names the person or client that made it, or the
engine (work no signed-in person or client started, such as a job submitted before Z2); entries recorded before the
upgrade name nobody and read "Before sign-in", with no backfill. **Security events** record each
change to people, groups, roles, grants, clients and token signing keys, and each sign-in, succeeded
or failed once the password was checked, with the e-mail address and the address (the connection's, or
the proxy's forwarded one when uvicorn trusts it); an attempt refused while an account or address is
slowed stays a log line (`sign_in_failed`). Read them with `GET /api/v1/security-events`
(`principalId=`, `aggregateType=`) as a Security administrator, or with a client holding that role
for a log tool. They never hold a password, secret, link or key, and **nothing expires them yet**:
the table grows with sign-ins, bounded per account and address by the growing delay (TODO, after
0.12). **One person's changes** (0.12 Z6): `GET /api/v1/changes?actorId=` lists everything a
person or client changed across the workspaces the caller may read, newest first; without `actorId`
it is every change the caller may read, for an audit export (`since`, `until`). The upgrade to Z6
places existing entries in their workspaces from their change sets; entries recorded before the
feed (0.9) name no workspace and only a caller with Browse at the instance reads them.

**Locked out:** the engine refuses to remove the last active person holding Security administration
at the instance (`409 LAST_SECURITY_ADMINISTRATOR`). If every such person is lost anyway, run
`python -m app.cli.create_admin` on the server: the new person holds Security administration again.

**Monitoring** with `/metrics` needs a client holding the Operator role
(`create_client --role operator`).

### Signing in from the browser

The browser application signs a person in on a screen of its own (0.12 I5) with the authorization
code flow and PKCE (0.12 I2, D234): opening the application without a session shows it, and signing
in returns to the page asked for. The engine decides every step through `/oauth/sign-in/options`,
`/oauth/sign-in/password` and `/oauth/sign-in/second-factor` (and the passkey ceremonies under
`/oauth/passkeys`); the screen only shows what it answers, and **accepts a post from the origins in
`CORS_ORIGINS`**, which is why the application's address must be listed there. The engine's own page,
`/oauth/authorize`, stays for outside web applications: it shows the default workspace's product name,
cannot be framed and runs no script, except where it offers a passkey: then only the engine's own
`/oauth/passkey.js` (a policy of `script-src 'self'`, nothing inline, D390). Both are the same code
(`engine/identity/browser_sign_in.py`). The access token stays in the page's memory; the
session is held in an `HttpOnly`, `SameSite=Strict` cookie named `oauth_refresh`, scoped to `/oauth`,
which the browser renews unseen while the person works. Each renewal replaces the cookie's token; a
token presented a second time ends the session, since only a copy can do that.

- **Serve over `https`.** The cookie is marked `Secure` when `PUBLIC_URL` is `https` (D268); over
  plain `http` it is not, which is for a development machine only.
- **One site.** By default the application calls the engine on its own address (a proxy or the dev
  server forwards the engine's paths, D404), so there is one origin and nothing to set but
  `PUBLIC_URL`, the address people open. With `VITE_API_URL` naming an engine elsewhere, the two must
  share a site (the same registrable domain, for example `rdm.example.org` and `api.rdm.example.org`),
  or the browser does not send the cookie. The application's origin is in `CORS_ORIGINS`.
- **Sessions** end after `SESSION_IDLE_HOURS` without use or `SESSION_DAYS` in all, when the person
  signs out (the account menu), signs out everywhere (Settings › Account, or
  `DELETE /api/v1/users/{id}/sessions` by an administrator), changes or resets their password, or is
  deactivated. Their access tokens are refused from the next request.
- **A first password** for a person created through the API: `POST /api/v1/users/{id}/password-reset`
  answers a one-time link, valid `PASSWORD_RESET_HOURS`, to pass on to the person. With `{"send": true}`, mail set up
  ([Sending mail](#sending-mail)) and an address on the person, the link is also mailed (SP3, D418); People does
  the dialog that shows the link offers Mail it to the person. It opens the application's `/reset-password` page (the Mail page's application address, else the
  first `CORS_ORIGINS` entry; the engine's `/oauth/password` when neither is known, and for links made
  earlier); a newer link replaces an older one, and using it ends the person's sessions. With mail set up
  a person who forgot their password asks for the same link themselves on the sign-in screen (I6): by
  e-mail address, answered the same whoever is named, slowed per name and per address, sent
  only to an active person with a local password and an address. Without mail they ask an administrator.
- **Failed sign-ins are slowed, never locked** (D271): the first 5 failures for one e-mail address and the
  first 20 from one address cost nothing; after that an attempt waits until 1 second after the last
  failure, then 2, 4 and so on to at most 15 minutes, and the page says how long. This is the design
  against password guessing, and its price is that anyone who knows an e-mail address can keep that person
  slowed by failing against it (the right password is not checked while the wait runs). A success clears the address's count;
  counts lapse after 24 hours. Each failure is logged
  (`sign_in_failed`, with the e-mail address and address). Behind a proxy, the address is the proxy's
  unless uvicorn trusts it to forward the caller's (`--forwarded-allow-ips` with
  `--proxy-headers`); without that, every person shares the proxy's address and its count of 20.
  The same slowing counts a wrong current password at `POST /me/password`, a wrong proof when adding a
  passkey, a failed passkey answer, and a wrong client secret at `/oauth/token` (per client ID and per
  address; an ID that is no client costs the same work). Open provider sign-in starts are capped at 2,000 at
  once per provider (`429` page until they lapse after ten minutes) (0.12 R).

### Signing in with the organisation's provider

People can sign in with an OpenID Connect provider (0.12 I3, D224): Microsoft Entra ID, Google,
Keycloak, Okta and others. There is one generic kind, nothing vendor-specific, and the provider
brings its own multi-factor sign-in (D225). The engine still starts its own session; the provider
only proves who the person is.

1. **Register the engine with the provider** as a web application with a client secret. Add a
   new provider on Settings › Security › Sign-in (or `POST /api/v1/sign-in-providers`) with a key,
   then register its **redirect address**, `<PUBLIC_URL>/oauth/providers/<key>/callback`, which
   the provider's page shows with Copy. The engine asks for `openid profile email`.
2. **Enter the issuer exactly as the provider states it** in its discovery document
   (`<issuer>/.well-known/openid-configuration`). Entra ID: `https://login.microsoftonline.com/
   <tenant ID>/v2.0`; Google: `https://accounts.google.com`; Keycloak: `https://<host>/realms/
   <realm>`. Saving an enabled provider reads that document and the provider's keys, and refuses
   with the reason when it cannot (another issuer, no answer, TLS). The engine must reach the
   provider over `https`; plain `http` only to a loopback host. A link-local address is refused,
   as for webhooks.
   The client secret stays write-only and is not carried to another provider: changing the issuer needs
   the new provider's client secret in the same save, and once anyone has signed in with a provider its
   issuer cannot change, because people are matched by the issuer's subjects (`409
   SIGN_IN_PROVIDER_IN_USE`): add a new provider and link people to it instead.
3. **Groups (optional).** Name the ID token claim holding the person's groups, usually `groups`.
   Each value becomes a provider group on Settings › Security › Groups when a sign-in first names
   it, or make the group ahead with **New group › From a sign-in provider** and grant its roles
   before go-live. Entra ID sends each group's **object ID**, not its name: configure the
   application's token to include groups ("groups assigned to the application" keeps the list
   short) and rename the engine's group to something readable. With more than 200 groups Entra ID
   replaces the claim with a link the engine does not follow (an "overage"); the person then has no
   provider groups, so assign only the groups that matter to the application. Keycloak needs a
   "Group Membership" mapper on the client; Google sends no groups.

**Who a person is.** The engine finds a person by the provider and the token's subject (`sub`),
never by e-mail (D363). The e-mail address is the name a person signs in with (0.17 EM1), so the
token must carry an `email` claim: a first sign-in without one is refused, and the message tells
the person to ask whoever manages the provider to add it. At their first sign-in a person is created
with the token's name and e-mail and no roles; their groups grant what they may do. Name and e-mail
follow the provider at each sign-in, except that an address another person holds is not taken: the
stored one stays and the sign-in goes on. Someone who already had
a local account becomes a second person: open the new person's page and choose **Link to an existing
person…** (0.12 I4a, D377): their identity and provider groups move onto the person who had the
account, with their roles and history, and the new person is deactivated. It is refused when the new
person already has a password, roles of their own or local groups: remove those first. **Unlink** on
the person's page undoes a wrong link; the next sign-in with that provider makes a new person.

**An address that is already taken** (`email_taken`, 0.17 EM1). A first provider sign-in is refused
when another person, active or deactivated, already holds the token's e-mail address, in any
letters; the person sees that a security administrator resolves it, and the `sign-in` `failed` event
says `email_taken`. To resolve it, open Settings › Security › People, find the person who holds the
address (search the address) and do one of these, then ask the person to sign in again:

1. The address belongs to an old account that nobody uses: **Deactivate** it, then **Edit…** and
   clear its E-mail (a deactivated person may have none; this frees the address), then **Save**.
2. The old account is the person's own, with roles and history to keep: **Edit…** it and change its
   E-mail to another address of theirs (or any free one), so the token's address is free. The person
   signs in with the provider and a new person is made; choose **Link to an existing person…** on the
   new person's page to move the sign-in onto the old account. The new person is deactivated and its
   address freed, and the old account takes the provider's address at the next sign-in.

A first sign-in refused with `no_email` needs nothing freed: once the provider's administrator adds
the claim, the person signs in again.

**Turning local sign-in off** (D365): on Settings › Security › Sign-in › Local accounts, once an
enabled provider has signed someone in. Passwords then stop working, except for the people who
**keep local sign-in**: those made on the server with `create_admin`, and those made before 0.12 Z4
(the upgrade marks them; `PATCH /api/v1/users/{id}` with `localKept` changes it). They sign in
through **Sign in with a local administrator account** on the sign-in page; the switch **Keeps local
sign-in** on a person's page gives or takes it away, and while local sign-in is off the last person
who keeps it can neither lose it nor be deactivated (D381). If every provider fails
and nobody who keeps local sign-in is available, run `python -m app.cli.create_admin` on the server:
the new administrator keeps it. Clients are not affected.

**Leavers** (D367). A session started through a provider renews like any other; the engine does not
ask the provider again until the next sign-in. Someone removed in the provider keeps an open session
until it lapses (`SESSION_IDLE_HOURS`, at most `SESSION_DAYS`), so deactivate leavers in the engine
too, or shorten `SESSION_IDLE_HOURS`. Disabling a provider ends every session it started. Signing
out of the engine signs the person out of the provider only when the provider's **Sign people out of
*name* too** is on (below).

**Signing out of the provider too** (0.12 I4a, D379, D380). Off by default: with Entra ID or Google,
signing out of the provider signs the person out of every application of the organisation in that
browser (mail, chat), which suits shared computers and surprises everyone else. Turn it on for a
provider on its page under **Signing out**; the engine needs the provider's `end_session_endpoint`
in its discovery document (Entra ID, Google, Keycloak and Okta publish one) and refuses the setting
without it. Then register the second address the page shows, `<PUBLIC_URL>/oauth/providers/<key>/
signed-out`, as the application's **post-logout redirect address** (Entra ID: *Front-channel logout
URL* / redirect URIs; Keycloak: *Valid post logout redirect URIs*; Okta: *Sign-out redirect URIs*).
From then on, signing out in the app takes the browser to the provider's sign-out with the ID token
the person signed in with, which the engine keeps sealed for as long as the session is open, and
back to the sign-in page. Sessions started before the setting was turned on hold no ID token and
sign out of the engine only. Signing out everywhere, and an administrator signing a person out,
end engine sessions only: another browser cannot be sent to the provider. Changing `PUBLIC_URL`'s
host means registering both addresses again.

### A second factor for local accounts

A person with a password can add an authenticator app (any TOTP app: Microsoft Authenticator,
Google Authenticator, 1Password, Aegis) on Settings › Account › Second factor (0.12 I4b, D383,
D384): the engine draws a QR code, shows the key, and asks for a code to confirm; it then shows ten
**recovery codes**, once. From then on the password alone does not sign them in: the sign-in page asks
for the six-digit code, or a recovery code ("Use a recovery code instead"). Each code, the app's or
a recovery code, works once, and a wrong one is slowed like a wrong password (D271). The secret is
sealed with `SECRETS_ENCRYPTION_KEY` (a lost key loses every app), the recovery codes are stored as
keyed hashes (a lost key voids them too: make new ones). Removing a passkey asks for the password
again (or a code). A person who signs in with a provider has no password, so no app and no passkey. The phone's clock must be right within about a minute.

**Requiring it.** Settings › Security › Sign-in › Local accounts › **Require a second factor with a
password** (D388): a person without an app sets one up on the sign-in page, with their recovery
codes, before their session starts, the administrators made on the server included; nobody can
remove their own factor while it is on. Clients and people signing in with a provider are never
asked: the provider's own factor applies.

**Passkeys** (0.12 I4c, D389–D394). A person adds a passkey on Settings › Account › Passkeys: the
button opens the engine's own page, where the browser asks for their fingerprint, face, device PIN
or security key. A passkey signs them in alone (the sign-in page's **Sign in with a passkey**, no
e-mail address typed) or as the second step after a password, and meets the requirement above. A passkey belongs
to one site name, the host of `PUBLIC_URL` (the relying party): it works on the engine's pages, never
on a look-alike. **Changing `PUBLIC_URL`'s host invalidates every passkey**; people add them again,
and until then the password and the app still work. The engine needs `PUBLIC_URL` at the address
people reach it by, over `https` (a browser allows passkeys on `localhost` over `http` only), and the
application and the engine on one site (OPERATIONS' "one site") so the person's session reaches the
engine's page. With local sign-in off, a passkey alone works only for the people who keep it. A
person with only passkeys has no recovery codes: a lost device is a Security administrator removing
the passkey from their page (or a second passkey, kept elsewhere).

**A lost phone.** The person signs in with a recovery code and sets the app up again from Account
(New recovery codes after any use). Without the codes, a Security administrator opens their page and
chooses **Remove second factor…** (D387, a security event records it); with the requirement on, they
set one up at their next sign-in. If no administrator can sign in, run
`python -m app.cli.create_admin` on the server: the new administrator signs in with their password,
sets an app up on the sign-in page when the requirement is on, and then removes the others' second
factors or turns the requirement off.

**When a sign-in fails**, the person sees "*provider* could not sign you in" with the reason, and the
Security events record it (`sign-in` `failed` with `reason` and `detail`), for example `issuer` or
`nonce` (the token was not for this sign-in), `exchange` (the provider refused the code: check the
secret and the redirect address), `browser` (started in another browser) or `deactivated`.

### Sending mail

The engine sends e-mail through the organisation's own SMTP server (0.12 M1, D418, D419) or through
Microsoft 365 ([below](#sending-through-microsoft-365-graph), 0.13 MS), one method at a time: it is
used for a new person's link, a password reset and, when a person asks, inbox notices; never for a
password or a code (D395). **Settings › Integration › Mail** (or `PUT /api/v1/mail-settings`, needing
Security administration at the instance) takes the server, the port, how the connection is secured
(**STARTTLS**, usually port 587, or **TLS**, usually 465; `none` only for a relay on a trusted
network, and then without a login: the engine never sends a login unencrypted), a user name and
password if the server asks for one, the address mail comes from, and the address the application is
reached at, which the links point to (empty: the first `CORS_ORIGINS` entry, D422). Send a test
message from the same page: it names what failed (the connection, TLS, the login, the address).

- **A new server needs the password again.** The saved password is not carried to another server: a
  change of the host or the port is refused (`MAIL_PASSWORD_REQUIRED`) unless the password is entered
  in the same save (0.12 E1). Other changes keep it.
- **The password is sealed** with `SECRETS_ENCRYPTION_KEY` and never shown; the text of a message
  waiting holds a one-time link, so it is sealed too and erased when the message is sent or fails.
  Both are covered by `reseal_secrets` ([above](#changing-secrets_encryption_key)).
- **The server's certificate is verified** against the system's trusted certificates, hostname
  included. A server with the organisation's own authority needs that authority installed on the
  engine's host (or in `SSL_CERT_FILE` of the process); an untrusted certificate shows as `tls` in
  the test message.
- **Mail is sent in the background**, so a slow server never holds a request. A failed attempt is
  tried again after 30 seconds, then after twice as long, at most an hour apart; an address the server
  refuses for good fails at once; anything else fails after 24 hours with the last reason. The Mail
  page lists the messages waiting, sent and failed, and `mailSender` appears among a process's
  threads on Operations. Finished messages are kept for 30 days.
- **Inbox notices are mailed by the same sender** (0.12 M2, D432), one message per notice, to people who switched
  on "Email me when something arrives in my inbox" on Settings › Notifications (off by default; clients have no mail),
  except for the kinds of notice they switched off there (D434).
  Only notices made after switching on are mailed, and only while they are under 24 hours old, so a long outage
  or mail not set up never sends a pile of old notices. A message names the kind of event and links to the
  application address above; it holds no record, change-set or person content. Messages of this kind show as
  `notice` in the outbox.
- **Digests go at 07:00** (0.16 AO3): a person who put kinds of notice in the digest (Settings › Notifications) is mailed
  one `digest` message every morning, or on Monday, at 07:00 in the time zone their browser reported when they chose it
  (the zone is the person's, not the server's; a daylight-saving change keeps 07:00). The mail sender makes it in its
  round, once the time has passed: the person's row is locked and the next time moved in the same commit, so several
  processes make one digest, and a sender that was down sends one, not one per missed morning. With nothing unread to say
  there is no message; with mail not set up nothing is queued and the time does not move, so the digest goes once mail is
  saved. Messages show as `digest` in the outbox. No setting and no AI provider is involved.
- **Sender reputation is the organisation's:** the from address's domain needs SPF and DKIM for the
  sending server, or mailboxes may file the messages as junk. The engine does neither.
- **Several processes** each run a sender; leases keep them off the same message.
- A message still being retried can be stopped from the Messages list (Stop sending): it fails at once and is
  not tried again. Its link keeps working until it expires.

#### Sending through Microsoft 365 (Graph)

Where SMTP with a user name and password is not possible (Microsoft is retiring basic authentication
for SMTP AUTH in Exchange Online) the engine sends through Microsoft Graph as one mailbox (0.13 MS).
Choose **Microsoft 365** on Settings › Mail, then how to **Sign in with** (client secret, certificate or one of
two managed identities; or `PUT /api/v1/mail-settings` with `"method": "microsoft365"`). It takes the tenant ID, the application (client) ID, a client secret or a
certificate or a managed identity ([below](#managed-identity-refiroo-runs-in-azure)), and the sending
mailbox (the from address). The token address
(`https://login.microsoftonline.com`) and the Graph address (`https://graph.microsoft.com`) are
settings with those defaults; change both for a national cloud. Saving one method replaces the other's
saved fields. Set this up in Microsoft Entra first:

1. **Register an application** (Entra admin center, App registrations); copy the tenant (directory)
   ID and the application (client) ID.
2. **Give it a credential.** Either a client secret (Certificates & secrets; copy the secret's
   *Value*, which is shown once; it expires, 6 to 24 months by default) or a certificate: upload the
   public certificate to the registration and give refiroo the private key and the certificate as one
   PEM text (the key not password-protected, RSA). The page shows the certificate's thumbprint (the
   value the Entra portal shows) and expiry; renew before it passes, since mail then fails with
   `login`.
3. **Add the `Mail.Send` application permission** (Microsoft Graph, Application permissions) and
   **grant admin consent**.
4. **Limit the application to the one mailbox.** With only the permission, the application can send as
   any mailbox in the tenant. Use an application access policy (`New-ApplicationAccessPolicy` in
   Exchange Online PowerShell, restricted to a mail-enabled security group holding the mailbox) or
   RBAC for Applications in Exchange Online. A policy can take some time to apply.
5. The sending mailbox must be a licensed user or a shared mailbox of the tenant.

- **A message is sent with `POST /users/<mailbox>/sendMail`** with the same MIME message the SMTP
  path builds (text, HTML and the inline brand images), so mail looks the same through both. Microsoft
  saves a message sent this way in the mailbox's **Sent Items**; the MIME route has no way to turn that off.
- **The token** comes from the client-credentials grant (`<token address>/<tenant>/oauth2/v2.0/token`,
  scope `<Graph address>/.default`; with a certificate a signed assertion, RS256) and is kept in the
  process until shortly before it expires; a token Graph refuses (`401`) is dropped and asked for again.
  No Microsoft library is used.
- **Failures.** A refused token (wrong or expired secret, an unknown certificate, application or
  tenant), missing consent, or a mailbox the application may not use is `login` and the same for every
  message, so all waiting messages share it; the sentence says what to change. Microsoft not reachable,
  throttled (429, 503, any 5xx) is `connection`: the message is tried again after the usual wait, and at
  least as long as Microsoft's `Retry-After`. A mailbox that does not exist is `sender`: the message waits and is tried
  again, as with SMTP, so the administrator can correct the mailbox before it gives up. Messages fail after 24 hours as with SMTP. The secret, the token and Microsoft's
  answers are never written into a message, the outbox or the log.
- **A bad recipient is not seen at sending.** Microsoft accepts the message (`202`) and reports an
  address that does not exist later, as a bounce to the sending mailbox, as an SMTP relay does. The
  engine does not read bounces (MS-D2): refiroo shows the message as sent, and the administrator
  finds the bounce in the mailbox. Do not use a mailbox people read as the only place to find them
  without telling them what it is for.
- **The client secret and the certificate are sealed** with `SECRETS_ENCRYPTION_KEY` like the SMTP
  password and are covered by `reseal_secrets`; they are never shown or logged. A managed identity stores
  no secret.
- Removing the settings stops sending at once; messages still waiting fail after their 24 hours.
  Each change to the settings is a security event.

##### Managed identity (refiroo runs in Azure)

Where refiroo runs on Azure (App Service, Container Apps or a virtual machine with a managed identity)
no secret or certificate is needed or stored (0.13 MS-D5): the Azure host gives the engine a token. On
Settings › Mail choose **Sign in with** › **Managed identity – this tenant** or **Managed identity – hosted in another tenant**, or send
`identityMode` with `PUT /api/v1/mail-settings`. It works only on an Azure host: elsewhere the test
message and queued mail fail as `login` with "refiroo is not running with a managed identity on an
Azure host". The engine reads the host's token endpoint from `IDENTITY_ENDPOINT` and `IDENTITY_HEADER`
(set by App Service and Container Apps; header `X-IDENTITY-HEADER`, `api-version=2019-08-01`), else the
instance metadata service of a virtual machine (`http://169.254.169.254/metadata/identity/oauth2/token`,
`Metadata: true`, `api-version=2018-02-01`); a client ID of a user-assigned identity is passed as
`client_id`. The host's token goes to the saved authority address, so with a managed identity only
Microsoft's sign-in hosts are accepted there (`login.microsoftonline.com`, `.us`,
`login.partner.microsoftonline.cn`, `login.chinacloudapi.cn`): another address is refused when saved and
again before sending (R13-F3). AKS workload identity (a token file) is not supported. Tokens are kept in the process until
shortly before they expire. Two modes:

**1. The identity is in the organisation's own tenant (`direct`).** The engine asks the host for a token for
Microsoft Graph and sends with it; no tenant token request is made, so refiroo's settings need no tenant ID
or application ID. The identity is the host's system-assigned one, or a user-assigned one named by its
client ID.
1. Give the identity's **service principal** (Enterprise applications › Managed identities, or its
   principal (object) ID) the Microsoft Graph `Mail.Send` app role. Entra has no portal button for it;
   run, with `Application.ReadWrite.All` and `AppRoleAssignment.ReadWrite.All` consented:

   ```powershell
   Connect-MgGraph -Scopes "Application.ReadWrite.All","AppRoleAssignment.ReadWrite.All"
   $identity = "<the identity's principal (object) ID>"
   $graph = Get-MgServicePrincipal -Filter "appId eq '00000003-0000-0000-c000-000000000000'"
   $role = $graph.AppRoles | Where-Object { $_.Value -eq "Mail.Send" }
   New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $identity `
     -PrincipalId $identity -ResourceId $graph.Id -AppRoleId $role.Id
   ```

   The assignment is the consent; there is no admin-consent screen for a managed identity.
2. Limit it to the sending mailbox: `New-ApplicationAccessPolicy -AccessRight RestrictAccess -AppId
   <the identity's client ID> -PolicyScopeGroupId <mail-enabled security group holding the mailbox>
   -Description "refiroo"` in Exchange Online PowerShell (or RBAC for Applications), as for an app. A
   policy can take some time to apply.
3. In refiroo, enter the user-assigned identity's client ID (empty for the system-assigned one) and the
   sending mailbox.

**2. refiroo hosted in another tenant (`federated`).** One instance per organisation runs in the
hosting organisation's Azure, and the Microsoft 365 is the customer's. A **user-assigned** managed
identity (the only kind Microsoft allows here) is a federated credential of a **multitenant app
registration** in the hosting tenant. The engine takes an identity token for the audience
`api://AzureADTokenExchange` (`…USGov` or `…China` by the cloud of the token address) and sends it as the
`client_assertion` of the client-credentials grant at the customer's tenant, as a certificate's signed
assertion would be. Another cloud than the identity's is not supported by Microsoft.
1. In the hosting tenant, register a multitenant app and add a federated credential (App registrations ›
   Certificates & secrets › Federated credentials, or `az ad app federated-credential create --id <the
   app's object ID> --parameters credential.json`):

   ```json
   {
     "name": "refiroo-managed-identity",
     "issuer": "https://login.microsoftonline.com/<hosting tenant ID>/v2.0",
     "subject": "<the user-assigned identity's principal (object) ID>",
     "audiences": ["api://AzureADTokenExchange"]
   }
   ```
2. In the customer's tenant, an administrator **grants admin consent** to the app (for example at
   `https://login.microsoftonline.com/<customer tenant ID>/adminconsent?client_id=<the app's client ID>`).
   The app gets the `Mail.Send` application permission there.
3. In the customer's tenant, limit the app to the sending mailbox with an application access policy
   (`-AppId <the app's client ID>`) or RBAC for Applications.
4. In refiroo, enter the identity's client ID, the app's client ID and the customer's tenant ID, and the
   sending mailbox.

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

Startup does not stop for a bootstrap model whose release key and version are already stored with other
content: it logs one error and serves. If the stored release is of a schema outside the window, the error
gives the `model_release_raise` command; if it is in the window, the model file changed without a new
`release.version`, and the error asks to raise it in `RDM_MODEL_PATH`'s file and restart.

Startup refuses to serve, logs what to do and answers `GET /health` with `503` when:

- `DATABASE_URL` is missing, not PostgreSQL, uses another driver, or the server is unreachable;
- the database has another collation, or `pg_trgm`, `btree_gin` or `pgcrypto` is missing and cannot
  be created;
- the database schema revision is unknown, or a migration fails (see [Upgrades](#upgrades));
- every workspace runs a model release whose schema is outside the engine's window; the log names
  the release's and the supported schemas and the recovery: for a schema older than the window, the exact
  command `python -m app.cli.model_release_raise` (run offline in the backend directory; it raises the stored
  releases to the window's schema in place, `--dry-run` only reports, and a release whose raised model is not
  valid or equals another release is left and reported; 0.12 L2a), for a schema newer than the
  window (a database a later RDM Engine used) to start that version (0.11 V4);
- `RDM_MODEL_PATH` names a model of a schema outside the window: the process does not start, and the
  message names the setting, the file, its schema and the supported ones;
- `SECRETS_ENCRYPTION_KEY` is missing or not 32 bytes in URL-safe base64, or the retired
  `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` is set, or `PUBLIC_URL` is not an absolute `http(s)` URL: the
  process does not start, and the message names the setting (0.12 I1).

`/health` also returns `503` when an activation committed but this process could not load the newly
selected release. Restart the process; it then loads the database selection.

A process that started with no workspace it could serve does not need a restart once the releases are
raised: raising a release through the API (`POST /model-releases/{id}/raising`), here or in another process,
makes it ready at the next `/health` probe or heartbeat, and only then does it start the job worker, the
exporter, the job listener, the event deriver and the webhook dispatcher (0.12 R, R-F9). A process that
starts with at least one servable workspace starts them at once, as before.

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
(`jobWorker`, `exportWorker`, `jobListener`, `eventDeriver`, `webhookDispatcher`, `mailSender`, `heartbeat`,
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

## AI proposals

Two settings switch AI on, each for its own work, and neither needs the other:

- **`AI_AGENT_COMMAND` switches the assistant on.** The assistant reads a workbook, or words about the
  stored records, in one Claude Code session and proposes a model and a load that a person reviews; it
  stops at a change set and never activates or publishes. It calls no provider. It needs `AI_SEND_LEVEL`
  `values` (a session reads the file and the records it needs) and the action group Use AI proposals.
  Without the command, `POST /ai/tasks` is `409 AI_NOT_CONFIGURED` and no screen offers the assistant. The
  command's own settings are in [Runtime](#runtime).
- **`AI_PROVIDER` switches the provider on.** It serves mapping targets for a mapping view's unmapped values,
  and later features (search, summaries) on the same provider. It does not serve the assistant. Without it,
  nothing is sent to a provider and no provider action is offered.

A proposal never writes live data and never publishes; it arrives as a step or a change a person edits,
keeps or removes. With both settings empty, the default, nothing is sent anywhere and no AI action is
offered.

| Setting | Default | Meaning |
| --- | --- | --- |
| `AI_PROVIDER` | empty | `claude` (the Claude API), `claude-code` (one headless Claude Code call per request, in the image: no `AI_API_KEY`, it signs in as Claude Code does, with `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` in the environment or the host's sign-in; `AI_MODEL` is passed to `--model`; the call's `total_cost_usd` fills `ai_calls.cost_usd`, also when the call failed after being charged; the context goes to Claude Code on its standard input, not on the command line, so a large one is not refused by the operating system, and Claude Code gets only `PATH`, `HOME`, `LANG`, `LC_*`, `TMPDIR`, `USER`, `LOGNAME`, `SHELL` and the `ANTHROPIC_*` and `CLAUDE_*` variables, never the engine's database address or encryption key; production normally uses `claude`), `openai-compatible` (any endpoint speaking the chat-completions protocol, including a model the organisation runs itself), or a factory `package.module:function` returning an object with `propose(request)`. Empty: no provider |
| `AI_MODEL` | empty | The model asked. Empty with `claude` means `claude-opus-5-5`; required with `openai-compatible` |
| `AI_API_KEY` | empty | The provider's key; required with `claude`, optional with `openai-compatible`. Read from the environment only, never stored in the database, never shown or answered |
| `AI_BASE_URL` | empty | The provider's address: required with `openai-compatible` (for example `http://models.internal:8080/v1`); with `claude`, empty for Anthropic's own API or a gateway's address |
| `AI_SEND_LEVEL` | `values` | The most that may leave the instance: `structure` (keys, names, headers and types; no value), `samples` (also values, at most `AI_SAMPLE_VALUES` per column or attribute) or `values` (as many values as a feature needs: an agent reads as much of a file as its task needs, 0.16 AP-D14). A feature needing more than the level is not offered; a question in words (0.16 AG4) and the account of a model change (0.16 AO1, the facts of the change and a count of records per touched type, no record) and of what changed in a period (0.16 AO2, counts and the model's labels; names of records, people, change sets and files go only at `values`) need only `structure` and are offered at every level; at `samples` or `values` it also sends the record names of a relationship's types when they hold at most 50 records in the list's context, at `structure` none |
| `AI_SAMPLE_VALUES` | 20 | At send level `samples`, the most values per column or attribute, that are sent; no limit at `values`. Replaces `INFERENCE_ASSISTANT_ROWS`. One exception (AG-D35): a question in words sends the record names of a relationship's types whole when the list holds at most 50 records, at `samples` and `values`, whatever this is set to |
| `AI_MIN_CONFIDENCE` | 0.5 | The provider's confidence, 0 to 1, below which a proposal is not offered |
| `AI_LOG_CONTENT` | off | Keep each call's request and answer with its record, for an operator debugging a prompt. They hold reference data: switch it on only while needed |
| `AI_LOG_CONTENT_DAYS` | 7 | Days a kept request and answer stay; then they are emptied and the record stays |
| `AI_REASONING_EFFORT` | empty | `openai-compatible` only: sends `reasoning_effort` (`none`, `low`, `medium`, `high`), how much the model reasons before it answers. Empty sends nothing. A local thinking model (Qwen through Ollama) can reason for minutes on a short request: `none` makes it answer directly |
| `AI_CONTEXT_TOKENS` | empty | The model's context window in tokens, for a model with a small one (a local model): a feature sizes each call to half of it, sending fewer records per call. Leave it empty for a hosted model. Empty: no limit beyond the feature's own batch. Ollama serves a model with its own window (4,096 by default, `OLLAMA_CONTEXT_LENGTH` when it starts), whatever the model supports: set this to that number |
| `MCP_ENABLED` | off | Whether assistants can reach the instance at `/mcp` ([Agent access](#agent-access)); off, the endpoint, its metadata and registration do not exist and no `agent` token is issued |
| `MCP_RATE_PER_MINUTE` | 120 | Tool calls one person or client may make through `/mcp` in a minute; past it a call is refused with how long to wait |
| `MCP_OPEN_REGISTRATION` | on | Whether an assistant may register itself; off, only those an administrator registers can sign people in |
| `MCP_REDIRECT_HOSTS` | none | HTTPS hosts a self-registered assistant may return to, comma separated, besides this computer |
| `MCP_CALLS_DAYS` | 90 | Days a record of a tool call through `/mcp` is kept |
| `MCP_ANSWER_BYTES` | 40000 | The longest answer of a tool through `/mcp`; past it a page comes back smaller with a cursor, and an answer that is no page is refused. A resource answers whole |
| `AI_TASK_RETENTION_DAYS` | 90 | Days an assistant task is kept after it finished (loaded, failed or cancelled) or was last changed; then the worker's sweep deletes the task, its workbook, its folder, the session's log beside the folder and Claude Code's transcript (under `$CLAUDE_CONFIG_DIR/projects`, else `~/.claude/projects`; a warning is logged if a transcript is not where expected). A task's folder and its session's client live until the work is in the person's hands for good: the change set is published or discarded, the migration confirmed, or the task discarded or expired (0.16 AP13); a failed or stopped task keeps them too, as the person can tell the assistant how to go on, and so does a loaded one, whose words discard its change set and load again. The next read of the task (or the worker's sweep after expiry) notices the end and removes the folder, the transcript and the log and deactivates the client. A session's call record counts cache reads and writes in its tokens; its bytes are the prompt and the final answer only. What was sent to the provider is never kept on a task (`AI_LOG_CONTENT` keeps it on the call record only) |
| `AI_TIMEOUT_SECONDS` | 60 | Seconds one call may take; the Claude adapter tries a passing failure (overloaded, rate-limited, a server error, a timeout) up to three times |

- **Where to set them:** in the reference installation, in `.env` (`.env.example` lists them, commented
  out, and `compose.yml` passes `.env` to the engine); on a developer instance, in `.dev/settings.env`
  (`scripts/dev.sh settings` lists them and names the fake provider). Either way restart the engine.
- **Settings are read at start.** A provider without what it needs (`claude` without a key,
  `openai-compatible` without an address or a model, a factory that does not import or has no
  `propose`) refuses the start and names the setting. `INFERENCE_ASSISTANT` and
  `INFERENCE_ASSISTANT_ROWS`, the 0.10 naming helper's settings, are retired: the start is refused while
  either is set, naming `AI_PROVIDER` or `AI_SAMPLE_VALUES`.
- **Settings › Administration › AI** (Operations) opens when either setting is on. It first says what each
  gives: the assistant (`AI_AGENT_COMMAND`: on or not set) and the provider (`AI_PROVIDER`: mapping targets,
  search and summaries, or not offered). With neither it says nothing is sent and no AI action is offered.
  With the provider on it shows the provider, the model, the address,
  whether a key is set, the send level and which features are offered; **Send a test request** sends
  a fixed request that holds no data and says whether it was answered or what failed (the key
  refused, the provider not reached, the answer out of shape). The page lists every call: who asked,
  for what, the model, the sizes each way, the tokens and the outcome; the totals cover the last 30
  days; an assistant session's turn is one call with its tokens and cost. The same is `GET /api/v1/ai/status`, `GET /api/v1/ai/calls` and `POST /api/v1/ai/test`.
- **Who may ask** is a role's business: the action group **Use AI proposals**, held by the
  predefined Data steward, Data owner, Model administrator, Workspace administrator and Integration
  administrator roles. A person without it is never offered an AI action, and a proposal is still
  written by the person's own request, under their other rights.
- **The assistant's session** runs as a process of the worker with the guards in `AI_AGENT_COMMAND`'s row; a
  turn that takes longer than `AI_AGENT_TIMEOUT_SECONDS` (30 minutes) is stopped as a person's Stop is, and the task returns to where the person can tell the assistant to go on or try again. A saved
  import profile that fits a file loads it without a session. A load by the assistant leaves such a profile
  when its sources have keys; the task says why when it cannot (`result.profileNotSaved`). Unused model
  releases the session installed are retired when its task ends, and a session may not write a model draft
  another task holds.
- **What is sent** is built in one place and held to `AI_SEND_LEVEL`. For a question in words (needs `structure`): the question, today's date and the list's fields, conditions and relationships with their labels and the names of the types they reach; at `samples` and `values` also the record names of a relationship's types when the list holds at most 50 records (0.16 AG4), never a value or ID; the record a question names is found in the database after the answer. For mapping targets (needs `values`): the names and the view's displayed fields of
  the unmapped sources, 25 per call, and of their candidate targets (all eligible targets up to 100,
  otherwise each source's 20 closest by name). Reference data is treated as data: the instructions tell the model not to follow
  text found in it, and nothing it answers is applied unasked.
- **A failing provider never fails the work it helps.** An unreachable provider, a refused key, a
  declined request or an answer out of the shape asked for is a warning on the feature and a
  failed call on the AI page.
- **The Claude adapter** asks for structured output and lets the API retry a declined request on
  another model (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). It calls
  `https://api.anthropic.com/v1/messages` unless `AI_BASE_URL` names another address; open that
  address in the firewall. A local `openai-compatible` model must support JSON-schema answers.
- **A model run locally with Ollama** (`AI_BASE_URL=http://localhost:11434/v1`): for a thinking model
  such as Qwen set `AI_REASONING_EFFORT=none`, or a short request can take minutes; raise
  `AI_TIMEOUT_SECONDS` for a laptop. The `openai-compatible` adapter asks for the answer's JSON schema
  and also shows its shape in the instructions as an example to fill in, so a build that does not
  enforce the schema (Ollama's MLX builds, tags ending `-mlx`) still answers in shape. Tried
  2026-10-28: `qwen3.5:9b-mlx` with thinking off named the types of a real workbook in 67 s.
- **Data protection:** a provider outside the organisation receives what the send level allows, under
  the organisation's own agreement with that provider. For data that may not leave, use
  `openai-compatible` with a model run inside the organisation, or `AI_SEND_LEVEL=structure`.

## Agent access

An assistant that speaks MCP can reach the instance at `/mcp`, with `MCP_ENABLED=true` and a restart; off, nothing of it exists. A reverse proxy in front of the engine must pass `/mcp` and `/.well-known/`; the shipped web image does. Security administrators see the address, the agent clients, the assistants and each call on Settings › Security › **Agent access**.

- **A system's assistant** uses an agent client (made on that page), with a grant like any client, and asks for a token with `scope=agent`. An agent client holds no other token and no other client holds this one.
- **A person's assistant** is added by its address and opens this instance's sign-in page. The page says who asks and where it returns; signing in is the consent. The person needs no new grant. The session appears in their sessions and ending it stops the assistant.
- **What an assistant can do** is what its person or client may do, cut down to Browse and Work in change sets. It can never approve or publish, whatever the roles behind it.
- **Registration:** with `MCP_OPEN_REGISTRATION` on, an assistant registers itself and may return only to this computer or a host in `MCP_REDIRECT_HOSTS`. The name it gives is its own claim, and the sign-in page says so. At most a thousand registrations may stand unused; those unused for 30 days with no open session are removed. Turned off, or for any other HTTPS address, an administrator registers it on the page. Blocking an assistant ends its sessions on their next call.
- **What an assistant reads:** with Browse in a workspace, its model, records, relationships, mapping coverage, history and changes, and a lookup tool for each of its consumer APIs. A client holding only a consumer API's grant has that API's tool alone. The consumer API's own routes still need a `consumer` token and a grant.
- **What an assistant can write** (0.16 AG3, [plan](BASE_0_16_IMPLEMENTATION_PLAN.md#ag3-in-detail-planned-2026-10-31-approved-by-the-user-the-same-day-with-ag-d27-as-written)): with Work in change sets in a workspace, it can create a change set, add and change records and relationships and set a field's value in it, read its validation, and submit it for approval. It works only in change sets its own person or client created, never a colleague's, and a person's own change set counts. It cannot remove anything, clear a value, withdraw a submission, discard a change set, batch, restructure the model, approve or publish. Change reaches live data only when a person approves it, and under `secondPerson` a second person decides. A person who asked an assistant to prepare a change may be refused the decision under `secondPerson`, as for a change they made themselves. The assistant's rows are marked "Prepared by an assistant" with the name the assistant gave itself, and the audit entries of a change made through an assistant carry `channel` `mcp`. No new setting.
- **Records:** each tool call is kept for `MCP_CALLS_DAYS` with its argument names, never their values. Nothing else about reads is written to the audit trail.
- **Prompt injection:** reference data is data. Text in a record can reach an assistant through a tool answer, and an assistant may be misled by it. No tool follows text found in a record, the server tells the assistant so, and an assistant cannot approve, publish or write live, so the worst it can do is propose something a person then reviews. This stance extends to writes (AG-D8): a tool that writes follows no text found in a record either, and only in the caller's own change sets, so text in a record cannot steer an assistant into a colleague's change set. Treat what an assistant says about the data with that in mind.

## Webhook subscriptions

Subscriptions say where a consumer API's events are delivered (0.9 C11), and a dispatcher thread in
the API process delivers them (0.9 C12). They are deployment data: they are not part of a model
release and are not copied by one.

| Setting | Default | Meaning |
| --- | --- | --- |
| `CONSUMER_SUBSCRIPTIONS_ENABLED` | off | Serves the subscriptions API (see capability groups) and runs the dispatcher that delivers them |
| `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED` | off | Whether a webhook may go to a loopback, private (RFC 1918, unique-local, shared 100.64.0.0/10) or otherwise non-public address. Off, a subscription naming such an address, or a host name that resolves to one, is refused (`400 INVALID_WEBHOOK_URL`), and a delivery to one fails with `address` in the delivery log. Link-local addresses (cloud metadata) are refused either way. Turn it on for receivers inside the organisation's network and for development (0.17 RF6) |
| `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` | 7 | Days the delivery log keeps each request, with the body it sent (up to 1 MiB), its events and its attempts (0.9 U5a); a batch still being retried or awaiting a resume is kept longer. Reported by `GET /api/v1/capabilities` |

**The delivery log** (0.9 U5a) records every request the dispatcher sends: its body, the events
it carries and each attempt's start, duration and answer (up to 4 KiB). It is read on Settings ›
Integration › Webhooks, Deliveries, and through `GET /api/v1/consumer-subscriptions/{id}/deliveries`.
A busy subscription writes up to 1 MiB per request: size the database for the retention. The
dispatcher deletes expired entries at most hourly.

A webhook URL may name any public host and port. It must use HTTPS; plain HTTP is accepted only to
`localhost`, `127.0.0.1` or `::1`, which also needs `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED=true`
(development). There is no host allowlist (C-D101 revised). An address that is, or whose host name
resolves to, a loopback, private or otherwise non-public address is refused when the subscription is
saved and again at every delivery, unless `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED` is on; link-local
addresses are refused whatever it says (0.17 RF6). **Upgrading:** subscriptions already on a private
address stop delivering (their batches fail with `address`) until the setting is on; set it before
upgrading if the receivers are inside the network.

- **The key:** signing keys are stored sealed with `SECRETS_ENCRYPTION_KEY` (0.12 D253; before
  0.12, `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup now refuses by name: rename it, keeping
  its value). Changing the key without re-sealing makes every stored secret unreadable; see
  [Changing `SECRETS_ENCRYPTION_KEY`](#changing-secrets_encryption_key). **Rotating a webhook's key**
  (0.12 K1): `POST /api/v1/consumer-subscriptions/{id}/rotate-secret` or **Rotate key…** on the
  webhook's page; the receiver is given the new key from the answer or the dialog, and during the
  overlap (24 hours by default, up to 7 days) it can verify with either. **0** is for a key that
  leaked: the old one stops with the next delivery, and the receiver refuses what the engine sends
  until it has the new one; the engine retries meanwhile.
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
  `"{RDM-Timestamp}.{body}"` with the subscription's `signingSecret`; during a key rotation the header
  lists two signatures separated by a comma, and any one verifying is enough) and reject stale timestamps;
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

## Deploying

`compose.yml` is the installation the project tests and describes (0.12 DP2, DP3): three containers,
of which only `web` is published. Deploying one is these steps, in this order; each setting is
explained in `.env.example`.
`compose.yml` reads its settings from `.env`; `RDM_ENV_FILE` names another file (a test deployment's, as the browser
runner for the deployment gives it).

| Container | Image | What it does |
| --- | --- | --- |
| `database` | `postgres:17-alpine` | PostgreSQL with the ICU root collation, its data in the `database` volume |
| `engine` | built from `backend/Dockerfile` | The engine under Uvicorn as an unprivileged user, one process, `--proxy-headers`, export files in the `job-files` volume and the assistant's task folders in the `assistant` volume; its health check is `/health/live` |
| `web` | built from `frontend/Dockerfile` | nginx (unprivileged, 8080 and 8443, published as 80 and 443) serving the application built once for every installation and forwarding the engine's public paths to the engine |

Both images keep the application under `/opt/refiroo/rdm-engine`, laid out as the repository is, and add nothing at `/`. In the engine image: `backend/` (the working directory), `guide/dist`, `model/rdm-starter.json` and `data/` (`job-files` and `assistant`, the volumes; `assistant-slots`, the session users' lock files). In the web image: `frontend/dist` (the application), `frontend/certs` (where `fullchain.pem` and `privkey.pem` are mounted) and `frontend/nginx`. `compose.yml` mounts the `job-files` and `assistant` volumes and the certificate folder there; a deployment of its own mounts them at `/opt/refiroo/rdm-engine/data/job-files` and `/opt/refiroo/rdm-engine/frontend/certs`.

1. **Choose the address people open** and make its DNS name reach the host. It is `PUBLIC_URL`: the
   issuer of the engine's tokens, the address a sign-in provider returns to and the host passkeys are
   bound to. Changing its host later signs everyone out and ends their passkeys.
2. **Fill `.env`** from `.env.example`: `PUBLIC_URL`, then the three secrets with the commands the file
   gives. **Keep `.env` beside your backups**: `SECRETS_ENCRYPTION_KEY` opens the stored keys, and
   the database password is set once, when the database is created. No secret is in an image or the
   repository. Capabilities and ports are in the same file (defaults commented).
3. **Provide HTTPS**, one of three ways:
   - *Your certificate (`WEB_TLS=files`, the default).* Put `fullchain.pem` and `privkey.pem` in
     `./certs` (or the folder `WEB_CERTS_DIR` names). `web` ends HTTPS, answers plain HTTP with a
     redirect to `PUBLIC_URL`, sends HSTS, and refuses to start, saying which files are missing, when
     they are. Renew by replacing the files and restarting `web`.
   - *A public name, certificates that renew themselves:* [Automatic HTTPS](#automatic-https-for-a-public-installation).
   - *A load balancer that ends HTTPS (`WEB_TLS=proxy`).* `web` serves plain HTTP on 8080 (publish it
     as you like), needs no certificate and believes the balancer's `X-Forwarded-Proto`. It believes
     `X-Forwarded-For` only from the addresses in `WEB_TRUSTED_PROXIES`: **list the balancer's own
     address range there** (comma-separated addresses or ranges, for example `10.0.0.0/8,192.168.1.5`;
     a malformed entry stops `web` at start with a message). The default is empty and trusts nobody, so
     a client-sent `X-Forwarded-For` is ignored and every caller appears as the address `web` is
     connected from, the balancer: the sign-in throttle then counts one address for everyone. Keep `web`
     reachable only from the balancer.
4. **Start it:** `docker compose up -d --build`. The engine creates and migrates the database at
   start; `docker compose ps` shows the three healthy.
5. **Create the first administrator:** `docker compose run --rm engine python -m app.cli.create_admin
   --email <address> --name "<Name>"` asks for the password. Everyone else is added in the application.
6. **Register a sign-in provider** (optional): its redirect address is
   `<PUBLIC_URL>/oauth/providers/<key>/callback`, see
   [Signing in with the organisation's provider](#signing-in-with-the-organisations-provider).
7. **Set up mail** (optional) on Settings › Integration › Mail; see [Sending mail](#sending-mail).

**What is public.** `web` forwards `/api`, `/oauth`, `/.well-known`, `/docs` (the documentation and the API
reference at `/docs/api`, built into the engine image and served offline), `/openapi.json` and
`/health` to the engine and serves everything else as the application. `/metrics` is not public: `web`
answers it 404, and monitoring reaches the engine's own port inside the Docker network
([Monitoring](#monitoring)). Nothing but `web` is published; keep it so, because the engine trusts the
caller address `web` forwards, which only `web` can set while the engine's port is closed. The engine
believes that address only from the compose network's private ranges (`FORWARDED_ALLOW_IPS`, default
`10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`, where `web` lies), never from every address (0.17 RF4); behind
another proxy, or with the engine run on its own, set `FORWARDED_ALLOW_IPS` in `.env` to that proxy's
address or range (comma-separated; Uvicorn's own setting, also `--forwarded-allow-ips`). An address
outside the list is the caller as connected, which is correct when nothing forwards. `web` sends the engine one address, the caller's: the address it is connected from, or,
behind a balancer (`WEB_TLS=proxy`), the one `X-Forwarded-For` names when the connection comes from
`WEB_TRUSTED_PROXIES`; whatever else a caller sent is replaced. The sign-in throttle counts per
address (D271).

**Pinned versions (0.17 RF4).** Nothing the images install floats to whatever is newest on the day of the
build.

- *Base images* are named by tag and digest (`node:22-alpine@sha256:…`, `python:3.14-slim@sha256:…`,
  `nginxinc/nginx-unprivileged:1.28-alpine@sha256:…`, `postgres:17-alpine@sha256:…`, `caddy:2@sha256:…`
  and CI's `postgres:17`): the tag says what it is, the digest what is built. To move one, pull the tag,
  read its digest with `docker buildx imagetools inspect <image:tag>` (the line `Digest:`) and replace the
  digest in `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yml`, `compose.acme.yml` or
  `.github/workflows/ci.yml`; then build.
- *Claude Code* in the engine image is installed at `CLAUDE_CODE_VERSION` (`ARG` in `backend/Dockerfile`,
  default the version the assistant was tried with). To move it, change the default (or build with
  `--build-arg CLAUDE_CODE_VERSION=<version>`; `npm view @anthropic-ai/claude-code version` names the
  newest), build, and check `docker run --rm --entrypoint claude <image> --version`.
- *Python dependencies* are the versions in `backend/constraints.txt`, which the image's `pip install`
  and CI use as constraints (every runtime and development dependency, with the versions that were
  current when it was made). Regenerate it after changing `backend/pyproject.toml` or to take newer
  versions: in `backend/`, `uv pip compile pyproject.toml --extra dev --universal --python-version 3.14
  --no-header --annotation-style line -o constraints.txt`, keep its three-line header, review the diff and
  run the tests. `pyproject.toml` keeps its ranges; the file decides what is installed.
- *The application's packages* are the lock files of `frontend/` and `guide/` (`npm ci`).

**Content security policy (0.17 RF4).** Each surface sends the policy it needs, and none allows scripts
from outside the engine's own origin:

| Surface | Sent by | Policy |
| --- | --- | --- |
| The application (every page and file `web` serves itself) | `web`, `frontend/nginx/snippets/csp-app.inc.template` | `default-src 'self'`, scripts only from the origin (no inline script; the theme is applied by `theme-init.js`), styles from the origin and inline (style attributes, and the component library's own style element), fonts from the origin and inline data, images `self`, `data:` and `blob:`, requests (`connect-src`) only to the origin, no `object`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'` |
| The engine's sign-in pages | the engine (`sign_in_pages.py`) | `default-src 'none'`, own script only where a passkey is offered, inline styles, forms only to the engine and the checked return address |
| The guide, `/docs` | the engine (`guide_site.py`) | own origin, each page's inline scripts by hash, `'wasm-unsafe-eval'` for the search, inline styles |
| The API reference, `/docs/api` | the engine (`reference/`) | own origin, each inline script by hash, inline styles, `data:` and `blob:` images and `data:` fonts |

`web` adds `frame-ancestors 'none'` to what the engine answers and no more, so the policies of the engine's
pages are the ones in force. A page that needs an inline script is not accepted: the
policy is what the application is built to. The policy is a file in the image (not a setting): to change
it, edit `csp-app.inc.template` and rebuild `web`. An organisation's own proxy in front of `web` may add
headers, but must not replace these.

**Uploads.** `web` takes bodies up to `WEB_MAX_BODY` (256 MiB, written `256m`); the engine's own limit is
`IMPORT_MAX_BYTES` (200 MiB). Raise both together.

**Upgrading** is [Upgrades](#upgrades) with `docker compose up -d --build` in step 4: back up first,
and the engine migrates the database at start. **Backups** are [Backup and restore](#backup-and-restore)
of the `database` volume (`pg_dump` from the `database` container) together with `.env`; the
`job-files` volume holds export and import files only for as long as their jobs do, and model authoring's
source files for as long as their draft or import profile exists: back it up with the database. The `assistant` volume holds the assistant tasks' folders, each with its working files and Claude Code's session logs, kept for `AI_TASK_RETENTION_DAYS`; they keep open tasks continuable across upgrades. A backup need not include them: losing them loses open tasks' folders and session logs, not records.

**Checking an installation.** `npm run test:deployment` in `frontend/` builds the images, starts the
installation from empty at this computer's network address with a throwaway certificate, creates the
administrator, signs in from a desktop and a phone-sized browser, restarts everything, tries `WEB_TLS=proxy`
and removes everything it made. It runs Docker builds, so it is run once per package and at a release,
announced.

For development, including a phone on the same network, see [A developer instance](#a-developer-instance),
which does not use these containers.

### Automatic HTTPS for a public installation

For an installation on a public name, `compose.acme.yml` (0.12 DP4) puts Caddy in front of `web`,
which gets and renews a Let's Encrypt (or ZeroSSL) certificate for the host in `PUBLIC_URL` by itself
and redirects HTTP to HTTPS. Point the name's DNS at the host, open port 443 to the internet (port 80 is optional: it only redirects people who type `http://`),
set `PUBLIC_URL`, and start with both files:

```bash
docker compose -f compose.yml -f compose.acme.yml up -d --build
```

**Every later Compose command needs both files too** — upgrades, restores, settings changes,
backups, scheduled jobs — or `COMPOSE_FILE=compose.yml:compose.acme.yml` set in the shell (not in
`.env`, which reaches the engine). A command without the overlay recreates `web` in its
own-certificate mode: it collides with the running Caddy on ports 80/443 or refuses to start without
`./certs`, and the site is down until the command is rerun with both files. Renewal also needs Caddy
running; `caddy-data` is untouched.

No certificate files and no `./certs` folder are needed; the overlay sets `WEB_TLS=proxy` and stops
publishing `web`, so Caddy is the only way in. Caddy's configuration is `caddy/Caddyfile` (add
`{ email you@example.org }` above the site to be told of an expiring certificate). The certificates
and the account with the authority live in the `caddy-data` volume: keep it, because the authority
limits how often a name may be issued. If the first certificate does not arrive, `docker compose
logs caddy` says why (usually DNS not yet pointing here, or port 443 closed). **Not for a name only
your network knows**: the authority cannot reach it, so use your own certificate files above.

## Deployment topologies

The supported topology is one API process (the Docker image starts one Uvicorn process). Several
instances, on one node or several, may share one database with different capability groups, for example
an internal instance with model administration on and a public one with both administration groups off
([Several processes](#several-processes)). Its known caveats are in
[ARCHITECTURE.md](ARCHITECTURE.md#deployment-topology). Instances behind one load balancer must share
`RDM_CURSOR_SIGNING_KEY`.

## Model releases and rollback

`RDM_MODEL_PATH` is bootstrap input, not the active-model setting. Startup validates the file and
installs its content when that release is missing and gives it to a workspace that runs none (a new
database's default workspace); an existing database keeps the release each workspace runs
(`workspace_models`, 0.11 M1), even when the file holds a newer one. Changing the file never activates
it. A release this version cannot serve, such as one of an unsupported schema, makes only the
workspaces running it unavailable (`503 MODEL_REGISTRY_UNAVAILABLE` naming the workspace); startup
logs each, with the recovery for a schema older than the window (a new database) or, for a schema newer
than the window, the later engine to run, and `/health` answers 503 only when no
workspace can be served (or the database is unreachable).
A model file of a schema outside the window refuses to start, naming the file.

The model lifecycle is staged: save a draft, validate and compile it (no side effects), install it as
an immutable inactive release, then activate it with the current runtime version and active-release
ID. Activation is refused when stored data is incompatible with the candidate. All four steps are in
the browser's Settings › **Model** pages and the [model API](API.md#model-endpoints), with
`MODEL_ADMIN_MUTATIONS_ENABLED` on.

To roll back model content, activate a previously installed compatible release. The same
compatibility check applies in both directions, so a rollback is refused when current data would be
invalid under the older release. Never edit installed release JSON or point `RDM_MODEL_PATH` at an
older file.

**Clearing out old releases.** A release that should no longer be chosen is retired (Settings › Model › the
release › Retire, or `PATCH /api/v1/model-releases/{releaseId}`): it disappears from every model picker,
and the workspaces running it keep working. A release nothing refers to (no workspace runs it, and no
record, change set, publication, job, import profile or mapping was made under it) can be deleted there too.
To delete many at once, run in the backend directory:

```bash
.venv/bin/python -m app.cli.model_release_prune --dry-run   # list what would go
.venv/bin/python -m app.cli.model_release_prune             # delete the retired releases nothing refers to
.venv/bin/python -m app.cli.model_release_prune --unused    # also the active ones nothing refers to
```

It works in one transaction under the installation lock and may run while the service runs; exit status 0.
Drafts started from a deleted release stay, without the link.

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

A release of the bundled starter model (`model/rdm-starter.json`) with a new `release.version` is
installed at startup beside the older one, and given only to workspaces that run no model yet.
A workspace already running an older starter release keeps it until a person with model
management rights activates the new release there (Settings › **Model**, or
`POST /api/v1/workspaces/{workspace_key}/model/activation`); activation is refused when stored
data is incompatible with it.

To roll back the application or database schema, stop the new deployment and restore the
pre-upgrade backup together with the matching older application version. Alembic downgrades and
manual edits to release rows are not a supported rollback path.

## Backup and restore

The database is the whole state of an instance: every workspace's records, change sets,
publications and history, the installed model releases and which workspace runs which, jobs,
webhook subscriptions and the feed. The source files of model drafts and import profiles live in
`JOB_FILE_DIR` (the `job-files` volume), not in the database: back that up with it. Keep with
it the application version and its configuration (see [Upgrades](#upgrades)); the cursor signing
key and `SECRETS_ENCRYPTION_KEY` are settings, not data, and a restore needs the same ones.

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

