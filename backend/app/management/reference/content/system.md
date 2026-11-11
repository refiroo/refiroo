# system

The system area tells you what an instance runs, how it is configured and whether it is healthy. Every process reports through the database, so any process answers for all; the others' figures are as of their last report.

You use it to show the product and version, to check that every workspace is served before and after an upgrade, to watch the instance from a monitoring system, and to confirm that a backup can be restored. Apart from `GET /api/v1/system`, which any signed-in caller may read, the operations need the Operations action group at the instance.

1. Identify the instance: `GET /api/v1/system`.
2. Watch it: scrape `GET /metrics`, or read `GET /api/v1/system/summary`; find the cause with `GET /api/v1/system/processes` and `GET /api/v1/system/readiness`.

## GET /api/v1/system

Title: Get the system

Tells what the deployment runs: the engine version and licence, the model release that is active, the instance's name, and whether AI and assistant access are available. Any signed-in caller may read it. Use `GET /api/v1/system/configuration` for how the instance is configured.

## GET /api/v1/system/configuration

Title: Get the configuration

Lists every setting the engine reads with its value, its default and where the value came from, and the database's migration revision. Settings are read when the process starts and change only with a restart. Secrets show no value.

### Errors

- 403 FORBIDDEN: needs Operations at the instance

## GET /api/v1/system/processes

Title: List the engine processes

Lists every engine process on this database as it last reported itself, in ID order. Use it to see which processes are live, which background threads fail and which releases a process cannot serve. A stopped process leaves the list.

### Parameters

- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/system/readiness

Title: List workspace readiness

Lists the active workspaces in key order, each with its release and whether every live process can serve it. Use it after installing or activating a release: a workspace is `served` only when no live process is missing it. Retired workspaces are not listed.

### Parameters

- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/system/summary

Title: Get the instance summary

Counts the instance's figures now: processes, workspaces served, queued and running jobs, and webhook subscriptions by state. These are the figures `GET /metrics` reports as instance gauges, as JSON, for a client that does not read Prometheus text.

### Errors

- 403 FORBIDDEN: needs Operations at the instance

## GET /api/v1/system/backup-rehearsals

Title: List backup rehearsals

Lists the backups that were restored into a separate database and checked there, newest first, with the result and every workspace of the copy. The list is written by the restore check run outside the API; the API never starts a rehearsal.

### Parameters

- pageSize: 1 to 200; 20 by default.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /metrics

Title: Scrape the metrics

Returns the instance's metrics for a Prometheus scraper. The response is plain text in the Prometheus text format (version 0.0.4), not JSON. One scrape covers every live process of the instance: their series carry a `process` label, and the jobs, webhook subscriptions, processes and unavailable workspaces are counted when you scrape. The path has no `/api/v1` prefix and needs a token like the other operations; a scraper uses a client that holds Operations.

### Errors

- 403 FORBIDDEN: needs Operations at the instance

## Schemas

### SystemResponse

What the deployment runs, for anyone signed in. How it is configured is `GET /api/v1/system/configuration`.

- engine: The running engine.
- schemaLanguages: The model schema versions this engine can run.
- activeModelRelease: The model release that is active.
- product: The instance's name and description, taken from the default workspace's model; `null` when this engine cannot serve that model.
- ai: Whether an AI provider is set. A client offers an AI action only when it is.
- mcp: Whether assistants can reach the instance.

### EngineInfo

- version: The product version, the same as the API document's `info.version`.
- managementApi: The management API version, `v1`.
- license: The licence the engine is offered under, an SPDX identifier.
- sourceCode: Where the source of the running version is.
- build: The commit and tag the code was built from.

### BuildInfo

- commit: The short commit hash; `null` when unknown.
- tag: The release tag on that commit; `null` when it has none or it is unknown.

### ActiveModelRelease

- id: The release's ID.
- key: Shared by all releases of one model.
- name: The model's name.
- version: The release's version.
- schemaVersion: The model schema the release is written in.
- activatedAt: When the release was activated or its schema upgraded.

### InstanceProduct

- name: The product name shown as the instance's name.
- description: A short description; `null` when the model gives none.

### AiSystemInfo

- configured: Whether an AI provider is set.
- provider: The provider's name; `null` when none is set.
- model: The model asked, `null` when none is named.
- sendLevel: The most that may leave the instance: `structure` (no values), `samples` (a few values) or `values`.
- assistant: Whether the assistant's session can run. It does not depend on a provider.

### McpSystemInfo

- enabled: Whether assistants can reach the instance.

### SystemConfiguration

How the deployment is configured, for operators. Settings are read at startup and change only with a restart.

- database: The database's state.
- settings: Every setting the engine reads, once.

### DatabaseInfo

- revision: The database's migration revision; `null` when it has none.

### SystemSetting

- name: The environment variable that sets it.
- group: `runtime`, `capabilities`, `limits`, `webhooks` or `ai`.
- description: What the setting controls.
- value: The value in effect, typed (number, boolean, text, list). `null` for a secret; the database URL is shown without its password.
- default: The value used when the variable is not set; `null` for a secret.
- source: `environment` when the variable is set to a non-empty value, otherwise `default`.

### ProcessPage, WorkspaceReadinessPage, BackupRehearsalPage

- items: The page's entries.
- nextCursor: Send it as `cursor` for the next page; `null` at the end.
- prevCursor: Send it as `cursor` for the previous page; `null` at the start.
- anchor: Reopens this page.
- totalCount: Rows matching, only with `includeTotal=true`.
- startIndex: Rows before the first one, only with `includeTotal=true`.

### ProcessResponse

One engine process as it last reported itself.

- id: The process's ID, `host:pid:random`; a job's `leaseOwner` begins with it.
- host: The host it runs on.
- pid: Its operating-system process ID.
- engineVersion: The engine version it runs.
- startedAt: When it started.
- heartbeatAt: When it last reported itself.
- state: `live`, or `silent` after no report for three heartbeat intervals. A stopped process leaves the list; one that died is listed `silent` for a day.
- ready: Whether it serves requests, which needs at least one workspace's model.
- threads: Its background threads.
- pool: Its database connection pool.
- unavailableReleases: The releases it cannot serve.
- counters: Its request and failure counts.

### ProcessThread

- name: `jobWorker`, `exportWorker`, `assistantWorker`, `jobListener`, `eventDeriver`, `webhookDispatcher`, `mailSender` or `heartbeat`.
- state: `running`, `failing`, or `off`: not started in this process because its capability is off or no workspace can be served.
- reason: Why its rounds fail: `poolExhausted`, `tooManyConnections`, `transactionEnded`, `unreachable` (database reasons) or `error`; `null` when it does not fail.
- since: When the failure began; `null` when it does not fail.

### ProcessPool

- size: The configured pool size.
- maxOverflow: The configured number of connections allowed beyond the pool size.
- inUse: Connections checked out when the process last reported.

### UnavailableRelease

- releaseId: The release's ID.
- schemaVersion: The model schema the release is written in.
- reason: `unsupportedSchema`: outside the schemas this engine reads. `invalid`: the model does not validate. `notLoaded`: activated but not loaded by this process, which serves it again after a restart.

### ProcessCounters

- requests: Requests answered since the process started.
- serverErrors: Of them, those answered with a 5xx status.
- databaseUnavailable: Times a request or background thread got no database connection since the process started, by reason; the key is the reason.

### WorkspaceReadinessResponse

Whether every live process serves a workspace's model.

- workspaceKey: The workspace's key.
- release: The release it runs; `null` when it runs none.
- state: `served`, or `unavailable` when it runs no release or a live process cannot serve its release.
- unavailableIn: The live processes that cannot serve its release, each with why.

### ReadinessRelease

- id: The release's ID.
- key: Shared by all releases of one model.
- version: The release's version.
- schemaVersion: The model schema the release is written in.

### ReadinessProcess

- processId: The process's ID.
- reason: `unsupportedSchema`, `invalid` or `notLoaded`, as for an unavailable release of a process.
- schemaVersion: The model schema of the release.

### SystemSummary

The instance's figures counted now, as the instance gauges of `/metrics`.

- processes: Engine processes by state.
- workspaces: Active workspaces by whether they are served.
- jobs: Jobs queued, running or awaiting confirmation, by kind and state; a kind and state with none is left out.
- webhookSubscriptions: Webhook subscriptions by state.

### SummaryProcesses

- live: Processes that reported recently.
- silent: Processes that have stopped reporting.

### SummaryWorkspaces

- served: Active workspaces every live process serves.
- unavailable: Active workspaces some live process cannot serve, or that run no release.

### SummaryJobs

- kind: The job's kind.
- state: `queued`, `running` or `awaiting_confirmation`.
- count: Jobs of this kind in this state.

### SummarySubscriptions

- active: Delivering, not failing.
- failing: Active while a batch is retried.
- suspended: Not delivering.

### BackupRehearsalResponse

A backup restored into a separate database and checked there.

- id: The rehearsal's ID.
- checkedAt: When the check ran.
- backup: The backup's name given to the check; `null` when none was given.
- dataAsOf: The copy's newest change in the audit trail; `null` when it has none.
- revisionBefore: The copy's migration revision as restored.
- revisionAfter: Its revision once prepared; `null` when it could not be prepared.
- engineVersion: The engine version that ran the check.
- host: Where the check ran.
- result: `passed` or `failed`.
- failure: Why it failed; `null` when it passed.
- workspaces: Every active workspace of the copy.

### RehearsalFailure

- code: `DATABASE_UNREACHABLE`, `DATABASE_URL_INVALID`, `DATABASE_COLLATION`, `DATABASE_EXTENSIONS`, `DATABASE_REVISION_UNKNOWN`, `DATABASE_MIGRATION_FAILED` or `WORKSPACES_NOT_SERVED`.
- message: What a recovery from the backup would meet, and what to do.

### RehearsalWorkspace

- workspaceKey: The workspace's key.
- release: The release it runs in the copy; `null` when none.
- state: `served`, or `unavailable` when the engine could not serve it from the copy.
- reason: Why it could not be served: `unsupportedSchema`, `invalid` or `noRelease`; `null` when served.
- records: Records in the copy.
- relations: Relationships in the copy whose source record is in the workspace.
- openChangeSets: Open change sets in the copy.
- publications: Publications in the copy.
- liveRecords: The instance's records of the workspace when checked, to compare with `records`.

### RehearsalRelease

- id: The release's ID.
- key: Shared by all releases of one model.
- version: The release's version.
- schemaVersion: The model schema the release is written in.
