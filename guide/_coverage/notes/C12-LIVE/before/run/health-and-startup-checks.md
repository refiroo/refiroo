---
title: Health and startup checks
description: Use the right probes and recover safely from a refused start.
reader: operator
---

Check readiness before sending traffic, even when Compose reports healthy containers.
Liveness says a process answers; readiness says it can serve work.

| Probe | Authentication | Meaning |
| --- | --- | --- |
| `GET /health/live` | None | HTTP 200 while the process answers; does not query PostgreSQL. Use for restart decisions. |
| `GET /health` | None | HTTP 200 when the database is reachable and at least one workspace can be served; otherwise 503. Use for traffic routing. |

```bash
curl --fail https://refiroo.example.org/health/live
curl --fail https://refiroo.example.org/health
docker compose logs --tail=100 engine
```

Use your public host. Probes reveal only `ok` or `unhealthy`; authenticated operators get the detail
on **Settings › Administration › Operations**. A ready installation can still have an unavailable
workspace. Inspect that page's workspace rows, not just the probe.

## A process refuses startup or stays unready

| Message or condition | Result and safe action |
| --- | --- |
| Missing or unsupported `DATABASE_URL`, wrong driver, unreachable database | No ready service. Supply a PostgreSQL psycopg URL and check network, credentials and server availability. |
| Wrong database collation | No ready service. Create a database with ICU root `und` and restore there; see [The database](/docs/run/database/). |
| Missing extensions | No ready service. Have the database administrator install `pg_trgm`, `btree_gin` and `pgcrypto` when startup cannot. |
| Unknown migration revision | Maintenance mode. Check the application version paired with this database; a later version may have written it. Do not edit revision rows. |
| Failed migration | Maintenance mode; the transaction leaves the previous revision. Follow the message's backup and retry steps in [Upgrades](/docs/run/upgrades/). |
| Missing or malformed encryption key | The process does not start. Restore its original 32-byte URL-safe-base64 key; do not generate a new one for an existing database. |
| Retired encryption or inference setting named | The process does not start. Follow the message's replacement setting; preserve the encryption key's value. |
| `JOB_FILE_DIR` cannot be created or written | With integration jobs enabled, startup is refused. Mount writable persistent storage for the engine user; see [Background jobs](/docs/run/background-jobs/). |
| Invalid count, timeout or password minimum | Correct the named setting within its documented range; see [Configure refiroo](/docs/run/configure/). |
| Invalid `PUBLIC_URL`, `SOURCE_CODE_URL`, log format/level or API-reference script setting | Correct the named setting and recreate the engine. |
| Bootstrap model file uses an unsupported schema | The process does not start. The message names the file, setting and supported versions. Use a compatible file. |
| Every workspace uses an unsupported release | No ready workspace. Raise older stored releases, or run the later engine required by a newer schema. See [Upgrades](/docs/run/upgrades/). |
| Newly activated release could not load | The affected process can be unready. Restart it to reload the stored selection; inspect the named release if failure persists. |

If a bootstrap key and version already exist with different content, startup logs an error and
keeps serving stored content. For a supported schema, give changed model content a new release
version; for an old stored schema, follow the raising command in the message. Changing a bootstrap
file never activates it in an existing workspace.

## A running database goes away

Readiness becomes 503 and requests return `503 DATABASE_UNAVAILABLE`, reason `unreachable`.
Background workers retry every two seconds. Restore the database connection; no engine restart is
needed. They log the outage once, a reminder each minute and recovery once.
Do not wire readiness failure to automatic restarts during a database outage.

Check the workspace's reason before choosing recovery: `unsupportedSchema` names a language
outside this engine's window, `invalid` means model validation failed, and `notLoaded` means a
process could not load its selection. A workspace with no selected release is also unavailable.
Preserve release identifiers and diagnostics for an invalid stored model; do not repair it by
editing database JSON. Model administrators can inspect supported alternatives and review a
raisable older release through [Model language versions](/docs/model/model-language-versions/).

A process with no servable workspace starts its workers only after readiness recovers. Raising a
release through the API lets its next health probe or heartbeat detect recovery. Use the offline
[raising procedure](/docs/run/upgrades/) with all processes stopped when using the command line.

## Distinguish the service states

| What answers | State | Operator action |
| --- | --- | --- |
| No engine HTTP response | Process failed before serving, stopped, or unreachable through web | Check container state, engine and web logs, settings parsing, file permissions and TLS. |
| Liveness 200, readiness 503 from initial database refusal | Startup maintenance mode | Repair the reported database condition, then restart the engine to repeat startup preparation. |
| Liveness 200, readiness 503 during a running database outage | Temporarily unavailable | Restore database connectivity; a successfully started service recovers without restarting. |
| Readiness 503, database reachable, no servable workspace | Waiting for a usable model release | Resolve model compatibility. API raising can be detected by the next probe/heartbeat; offline CLI raising requires stopping all engines. |
| Readiness 200, one workspace unavailable | Partially available | Keep serving unaffected workspaces; inspect the unavailable workspace's release and process reasons. |
| Readiness 200, background thread failing | Requests may work while background work is impaired | Inspect the named thread, its reason, database and destination connectivity. |

Successful health response bodies are `{"status":"ok"}`. Failed readiness is
`{"status":"unhealthy"}`. They contain no diagnostics and require no sign-in. The engine image's
health check calls `/health/live` every ten seconds, with a three-second timeout, a thirty-second
start period and six retries. The web image checks its own `/web-health`; that also does not prove
engine readiness. PostgreSQL's Compose check uses `pg_isready` every five seconds, with a
three-second timeout and ten retries.

## Recognise the startup diagnostic

The following are **verbatim fragments**, not replacement messages. The complete log adds the
installation's database label, revision, file, rejected value or underlying reason. Read the whole
message before acting. Database refusals describe maintenance mode; environment/model-file
refusals can happen before HTTP starts.

| Quoted fragment | Cause and safe next step |
| --- | --- |
| `DATABASE_URL is not set.` | Supply the database URL; Compose normally constructs it from its required password. |
| `DATABASE_URL is not a database URL.` | Correct URL syntax in the process environment; use PostgreSQL with psycopg. |
| `SQLite is no longer supported.` | The URL names an unsupported database. Supply PostgreSQL; no SQLite conversion command exists. |
| `DATABASE_URL uses the driver` | Replace the driver prefix with `postgresql+psycopg://` or `postgresql://`. |
| `the ICU root collation 'und', the language-independent Unicode order it sorts and matches names by` | The database was created with another collation. Restore into a correctly created database; do not relabel the old one. |
| `does not know (its newest is` | An unknown stored migration revision. Use the matching engine version or restore the pre-upgrade backup; never stamp the revision manually. |
| `lacks the` and `could not create` | The message names missing extensions. Install the contrib modules or have the database owner create those extensions. |
| `cannot connect to the` | Check the named PostgreSQL host, database, role, password and network; restart after an initial startup failure. |
| `Database migration failed for` | Preserve the full message and backup, stop every engine, correct the named cause and retry `database_upgrade`. It reports current and target revisions. |
| `SECRETS_ENCRYPTION_KEY is required: it seals the token signing keys and webhook signing keys stored in the database.` | Supply a new key only for a new installation. For existing data recover the original key. |
| `SECRETS_ENCRYPTION_KEY must be 32 bytes written in URL-safe base64; generate one with` | The provided value is malformed. Correct its encoding or restore the correct existing key. |
| `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY is no longer read: SECRETS_ENCRYPTION_KEY replaces it` | Rename the retired setting and preserve its value; remove the retired entry. |
| `INFERENCE_ASSISTANT is no longer read: the proposal provider replaces the inference assistant` | Remove the retired setting; review [AI configuration](/docs/run/ai/) before choosing its replacement. |
| `INFERENCE_ASSISTANT_ROWS is no longer read: the proposal provider replaces the inference assistant` | Remove the retired setting; use the documented replacement in the AI settings. |
| `PUBLIC_URL must be the engine's absolute http or https address, not` | Supply the permanent absolute public origin. |
| `SOURCE_CODE_URL must be an absolute http or https address, not` | Supply a valid corresponding-source address or leave the default for an unmodified version. |
| `WEB_CONCURRENCY must be a positive integer` | Supply an integer of at least 1. |
| `must be a positive integer, not` | A named count/timeout is non-numeric or below 1. Correct it using the settings reference. |
| `must be zero or a positive integer, not` | A named setting accepting zero is negative or non-numeric. Correct it. |
| `must be one of` | The message names the valid choices for log format, log level, API-reference script or an AI option. Use one of those values. |
| `must be a number from 0 to 1, not` | Correct the named AI confidence setting; see the AI pages. |
| `JOB_FILE_DIR` and `cannot be created or written` | Restore a writable mount for the engine user, UID 10001 in the reference image. Check capacity and permissions. |
| `RDM_MODEL_PATH names` and `Point RDM_MODEL_PATH at a model of a supported schema` | Supply a supported bootstrap file, or use the engine version that understands it. Stored releases are separate. |
| `which has left the window; this version supports schema` | Stored workspace model is older than supported. Back up, preview and perform the [raising procedure](/docs/run/upgrades/). |
| `This database was used by a later` | Stored workspace model needs a later engine; run that version. Raising does not lower a later schema. |
| `is invalid` and `diagnostics` | Preserve the named release ID and validation diagnostics; ask its model administrator to review a supported alternative. |
| `was not installed because the database holds another model with that release version.` | Bootstrap content conflicts with a stored immutable release. A supported stored schema needs a new file release version; an older one needs reviewed raising. |

Shape validation can also reject out-of-range settings: `PASSWORD_MIN_LENGTH` must be 1–128 and,
when set, `AI_CONTEXT_TOKENS` must be at least 256. AI provider construction refusals are covered
in [Set up AI](/docs/run/set-up-ai/). Web TLS/proxy refusals belong to [HTTPS](/docs/run/https/).
If a bootstrap file is missing, unreadable, malformed or invalid, keep its filename and validation
reason and supply the correct file; do not change installed release rows as a substitute.

After fixing an initial database refusal, repeat startup explicitly:

```bash
docker compose restart engine
curl -i https://refiroo.example.org/health
```

Use `docker compose up -d engine` instead when the fix changed `.env`. Expect 200, then inspect
workspace readiness in Operations. If it stays 503, collect a fresh bounded log; do not remove
volumes or repeatedly restart without addressing the reported cause. For an unavailable workspace,
record `unsupportedSchema`, `invalid` or `notLoaded` and the process IDs reported alongside it.

Expected database outages log concise errors and keep tracebacks at DEBUG. Other background-thread
failures log ERROR with a traceback because they can indicate a defect; preserve that diagnostic
with the thread name and process identity when escalating.
