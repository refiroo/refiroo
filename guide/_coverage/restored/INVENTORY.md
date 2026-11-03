# Coverage inventory (restored)

Regenerated 2026-11-02 from today's repository with the restored `inventory.py`. One row per item; `owner` DOC9A marks items 0.16 introduced (wave G).

Totals: capability 30, journey 57, setting 63, error 339, command 9, role 10, permission 16, event 10, field 319; total 853.

## capability (30)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| capability | `F01` | Model-defined applications |  |
| capability | `F02` | Workspace discovery and administration |  |
| capability | `F03` | Find, filter, sort and page through records |  |
| capability | `F04` | Inspect a record and its context |  |
| capability | `F05` | Maintain live records |  |
| capability | `F06` | Maintain typed field values |  |
| capability | `F07` | Maintain containment and hierarchy |  |
| capability | `F08` | Maintain relationships and mappings |  |
| capability | `F09` | Maintain translations and coverage |  |
| capability | `F10` | Preview and confirm dependent deletion |  |
| capability | `F11` | Inspect record history |  |
| capability | `F12` | Prepare a change set |  |
| capability | `F13` | Review, validate and publish a change set |  |
| capability | `F14` | Browse publications and withdraw one |  |
| capability | `F15` | Inspect and release application models |  |
| capability | `F16` | Use stable, bounded APIs |  |
| capability | `F17` | Recover from concurrent changes |  |
| capability | `F18` | Accessible and responsive interface |  |
| capability | `F19` | Operate and recover the service |  |
| capability | `F20` | Query and look up across the data |  |
| capability | `F21` | Read by business date (`asOf`) |  |
| capability | `F22` | Load data in bulk as jobs |  |
| capability | `F23` | Declare consumer APIs and read through them |  |
| capability | `F24` | Read the API reference |  |
| capability | `F25` | Follow changes in order |  |
| capability | `F26` | Sign in and manage one's sessions |  |
| capability | `F27` | Control who can do what |  |
| capability | `F28` | Send mail |  |
| capability | `F29` | Use AI proposals | DOC9A |
| capability | `F30` | Reach refiroo from an assistant | DOC9A |

## journey (57)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| journey | `J01` | Find and inspect a record |  |
| journey | `J02` | Correct a record |  |
| journey | `J03` | Add a record where it belongs |  |
| journey | `J04` | Delete a record and what depends on it |  |
| journey | `J05` | Prepare and publish a coordinated design |  |
| journey | `J06` | Continue live work while a change set is open |  |
| journey | `J07` | Withdraw a publication and start reviewed changes from history |  |
| journey | `J08` | Create and activate an application-model release |  |
| journey | `J09` | Retired |  |
| journey | `J10` | Review and replace a record's related records |  |
| journey | `J11` | Submit a bounded bulk change |  |
| journey | `J12` | Run the service, and recover from an expected refusal |  |
| journey | `J13` | Relate records and maintain their relationships |  |
| journey | `J14` | Build and change a hierarchy |  |
| journey | `J15` | Reshape a hierarchy across types, and change a record back |  |
| journey | `J16` | See and fill relationship coverage across ancestors |  |
| journey | `J17` | Review what a change set changes |  |
| journey | `J18` | Prepare under the next model version while live keeps the current one |  |
| journey | `J19` | Administer workspaces |  |
| journey | `J20` | Discover the model and the API |  |
| journey | `J21` | Read a collection completely and resume |  |
| journey | `J22` | Request the precise dataset an integration needs |  |
| journey | `J23` | Answer a business-date question |  |
| journey | `J24` | Run a large background job and recover |  |
| journey | `J25` | Define a consumer API in the model |  |
| journey | `J26` | Follow changes reliably |  |
| journey | `J27` | Exchange a supplier file |  |
| journey | `J28` | Read a business object through a consumer API |  |
| journey | `J29` | Resolve a business object through a consumer API |  |
| journey | `J30` | Follow a consumer API's changes |  |
| journey | `J31` | Check what a deployment runs and how it is configured |  |
| journey | `J32` | Change many records of a collection at once |  |
| journey | `J33` | Design a model in the editor |  |
| journey | `J34` | Onboard a workbook |  |
| journey | `J35` | Load the next version of a workbook |  |
| journey | `J36` | Run a workspace on a model of its own |  |
| journey | `J37` | Move a workspace to another release |  |
| journey | `J38` | Move data between workspaces whose models differ |  |
| journey | `J39` | Sign in and work |  |
| journey | `J40` | Manage who can do what |  |
| journey | `J41` | A system calls with a client |  |
| journey | `J42` | Propose and approve a change |  |
| journey | `J43` | Rotate a key |  |
| journey | `J44` | See who changed what |  |
| journey | `J45` | Start from home |  |
| journey | `J46` | Send mail |  |
| journey | `J47` | Check the security model |  |
| journey | `J48` | Use AI proposals | DOC9A |
| journey | `J49` | Targets for unmapped values | DOC9A |
| journey | `J50` | Load a workbook, or change records, with the assistant | DOC9A |
| journey | `J51` | Reach the engine from an assistant | DOC9A |
| journey | `J52` | An assistant reads | DOC9A |
| journey | `J53` | An assistant prepares a change | DOC9A |
| journey | `J54` | Ask in words | DOC9A |
| journey | `J55` | An account of a model change | DOC9A |
| journey | `J56` | What changed in a period | DOC9A |
| journey | `J57` | Notification digests and following a workspace | DOC9A |

## setting (63)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| setting | `setting:DATABASE_URL` | The PostgreSQL database the engine runs on [group: runtime] (app/config.py) |  |
| setting | `setting:RDM_MODEL_PATH` | The model file installed on a database's first start; not the active model [group: runtime] (app/config.py) |  |
| setting | `setting:RDM_CURSOR_SIGNING_KEY` | Signs pagination cursors; unset, each process makes its own, so cursors stop working after a restart and differ between instances [group: runtime] (app/config.py) |  |
| setting | `setting:CORS_ORIGINS` | Browser origins allowed to call the API [group: runtime] (app/config.py) |  |
| setting | `setting:PUBLIC_URL` | The engine's address as callers reach it; the issuer of its tokens [group: runtime] (app/config.py) |  |
| setting | `setting:SOURCE_CODE_URL` | Where the source of the running version is offered to its users; the project's tag of this version unless set (AGPL section 13) [group: runtime] (app/config.py) |  |
| setting | `setting:SECRETS_ENCRYPTION_KEY` | Seals the stored token and webhook signing keys; required [group: runtime] (app/config.py) |  |
| setting | `setting:JOB_FILE_DIR` | Where export files wait for download; created at start, kept as long as their job [group: runtime] (app/config.py) |  |
| setting | `setting:RDM_API_REFERENCE_SCRIPT` | Where the API reference page at /docs/api loads its script from: bundled or cdn [group: runtime] (app/config.py) |  |
| setting | `setting:WEB_CONCURRENCY` | Server worker processes on this instance [group: runtime] (app/config.py) |  |
| setting | `setting:DATABASE_POOL_SIZE` | Database connections each process keeps open [group: runtime] (app/config.py) |  |
| setting | `setting:DATABASE_POOL_MAX_OVERFLOW` | Database connections each process opens beyond the pool size when busy [group: runtime] (app/config.py) |  |
| setting | `setting:DATABASE_POOL_TIMEOUT` | Seconds a request waits for a database connection before it answers 503 [group: runtime] (app/config.py) |  |
| setting | `setting:DATABASE_IDLE_TRANSACTION_TIMEOUT` | Seconds a connection may sit idle inside a transaction before the database ends it, releasing a stalled process's locks; 0 turns it off [group: runtime] (app/config.py) |  |
| setting | `setting:LOG_FORMAT` | How the log is written: text lines, or one JSON object a line [group: runtime] (app/config.py) |  |
| setting | `setting:LOG_LEVEL` | The lowest level the log writes [group: runtime] (app/config.py) |  |
| setting | `setting:PROCESS_HEARTBEAT_SECONDS` | Seconds between each process's reports of its state to the others [group: runtime] (app/config.py) |  |
| setting | `setting:MODEL_ADMIN_MUTATIONS_ENABLED` | Model drafts, compiling, installing and activating releases [group: capabilities] (app/config.py) |  |
| setting | `setting:WORKSPACE_ADMIN_MUTATIONS_ENABLED` | Creating, renaming, retiring, deleting workspaces and choosing the default [group: capabilities] (app/config.py) |  |
| setting | `setting:INTEGRATION_JOBS_ENABLED` | Creating and cancelling jobs (POST /batches); job reads stay available [group: capabilities] (app/config.py) |  |
| setting | `setting:CONSUMER_SUBSCRIPTIONS_ENABLED` | Webhook subscriptions and their delivery [group: capabilities] (app/config.py) |  |
| setting | `setting:BATCH_MAX_ITEMS` | Items in an inline batch [group: limits] (app/config.py) |  |
| setting | `setting:BATCH_MAX_BYTES` | Bytes in an inline batch's body [group: limits] (app/config.py) |  |
| setting | `setting:ATOMIC_JOB_MAX_ITEMS` | Items in an atomic batch, inline or background [group: limits] (app/config.py) |  |
| setting | `setting:BACKGROUND_JOB_MAX_ITEMS` | Items in a background batch [group: limits] (app/config.py) |  |
| setting | `setting:BATCH_BACKGROUND_MAX_BYTES` | Bytes in a background batch's body [group: limits] (app/config.py) |  |
| setting | `setting:JOB_CHUNK_ITEMS` | Items one background chunk commits [group: limits] (app/config.py) |  |
| setting | `setting:IMPORT_MAX_BYTES` | Bytes in an import's file [group: limits] (app/config.py) |  |
| setting | `setting:JOB_PREVIEW_MAX_ITEMS` | Items a preview of an import or a batch runs before it is a sample [group: limits] (app/config.py) |  |
| setting | `setting:MODEL_OPERATION_MAX_ITEMS` | Operations in one request to a model draft [group: limits] (app/config.py) |  |
| setting | `setting:JOB_LEASE_SECONDS` | Seconds a worker holds a job, renewed with each chunk [group: limits] (app/config.py) |  |
| setting | `setting:ACCESS_TOKEN_MINUTES` | Minutes an access token lasts, for people and clients [group: runtime] (app/config.py) |  |
| setting | `setting:TOKEN_SIGNING_KEY_DAYS` | Days a token signing key signs before the next token brings a new one [group: runtime] (app/config.py) |  |
| setting | `setting:SESSION_IDLE_HOURS` | Hours a browser session lasts without being used [group: runtime] (app/config.py) |  |
| setting | `setting:SESSION_DAYS` | Days a browser session lasts in all before the person signs in again [group: runtime] (app/config.py) |  |
| setting | `setting:PASSWORD_RESET_HOURS` | Hours a password-reset link stays valid [group: runtime] (app/config.py) |  |
| setting | `setting:PASSWORD_MIN_LENGTH` | Characters a local password needs at least; lower only for development [group: runtime] (app/config.py) |  |
| setting | `setting:JOB_RETENTION_DAYS` | Days a finished job keeps its outcomes and idempotency key [group: limits] (app/config.py) |  |
| setting | `setting:FEED_RETENTION_DAYS` | Days the change feed and consumer events answer a position [group: limits] (app/config.py) |  |
| setting | `setting:CONSUMER_RESOLVE_MAX_ITEMS` | Items in one consumer batch resolve [group: limits] (app/config.py) |  |
| setting | `setting:CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` | Days the webhook delivery log keeps a request, its body and its attempts [group: webhooks] (app/config.py) |  |
| setting | `setting:AI_PROVIDER` | The proposal provider: claude, openai-compatible or a factory module:function; empty, the default, sends nothing anywhere [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_MODEL` | The provider's model; empty for claude means claude-opus-5-5 [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_API_KEY` | The provider's key; never shown [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_BASE_URL` | The provider's address: required for openai-compatible, empty for Claude's own [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_SEND_LEVEL` | The most that may leave the instance: structure (no values), samples (a few) or values (as many as a feature needs) [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_SAMPLE_VALUES` | At send level samples, the most values per column, or rows per sheet, that are sent [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_MIN_CONFIDENCE` | The confidence, 0 to 1, below which a proposal is not offered [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_LOG_CONTENT` | Keep each call's request and answer for an operator debugging a prompt [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_LOG_CONTENT_DAYS` | Days a call's kept request and answer stay, when AI_LOG_CONTENT is on [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_TIMEOUT_SECONDS` | Seconds one call to the provider may take before it fails [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_REASONING_EFFORT` | openai-compatible only: how much the model reasons first, none, low, medium or high; empty sends nothing. none keeps a local thinking model fast [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_CONTEXT_TOKENS` | The model's context window in tokens, for a small local model; each call is sized to half of it. Empty: no limit [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_TASK_RETENTION_DAYS` | Days an assistant task is kept after it finished (loaded, failed or cancelled) or was last changed; then it and its file are deleted [group: ai] (app/config.py) | DOC9A |
| setting | `setting:AI_AGENT_COMMAND` | The command that starts the assistant's Claude Code session, for example: claude --model sonnet; empty, the assistant runs no session [group: runtime] (app/config.py) | DOC9A |
| setting | `setting:AI_AGENT_SANDBOX` | container when the engine runs in a container, where Claude Code's own sandbox cannot run; empty, the operating system's sandbox [group: runtime] (app/config.py) | DOC9A |
| setting | `setting:AI_AGENT_API_URL` | The API address the assistant's session uses; empty, this instance's own [group: runtime] (app/config.py) | DOC9A |
| setting | `setting:MCP_ENABLED` | Whether assistants can reach the instance at /mcp; off, the endpoint does not exist [group: ai] (app/config.py) | DOC9A |
| setting | `setting:MCP_RATE_PER_MINUTE` | Tool calls one person or client may make through /mcp in a minute [group: ai] (app/config.py) | DOC9A |
| setting | `setting:MCP_OPEN_REGISTRATION` | Whether an assistant may register itself; off, only those an administrator registers can sign people in [group: ai] (app/config.py) | DOC9A |
| setting | `setting:MCP_REDIRECT_HOSTS` | HTTPS hosts a self-registered assistant may return to, besides this computer [group: ai] (app/config.py) | DOC9A |
| setting | `setting:MCP_CALLS_DAYS` | Days a record of a tool call through /mcp is kept [group: ai] (app/config.py) | DOC9A |
| setting | `setting:MCP_ANSWER_BYTES` | The longest answer of a tool through /mcp; past it a page comes back smaller, with a cursor [group: ai] (app/config.py) | DOC9A |

## error (339)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| error | `error:ACTION_GROUP_UNKNOWN` | backend/app/engine/authorization/administration.py |  |
| error | `error:ACTIVATION_CONFLICT` | backend/app/engine/model/migrations.py |  |
| error | `error:AGENT_APPLICATION_INVALID` | backend/app/engine/agent_access/applications.py | DOC9A |
| error | `error:AGENT_APPLICATION_NOT_FOUND` | backend/app/engine/agent_access/applications.py | DOC9A |
| error | `error:AI_ASSISTANT_ROLE_CHANGED` | backend/app/engine/tasks/agent.py | DOC9A |
| error | `error:AI_NOT_CONFIGURED` | backend/app/engine/jobs/worker.py | DOC9A |
| error | `error:AI_SEND_LEVEL_TOO_LOW` | backend/app/management/ai.py | DOC9A |
| error | `error:AI_TASK_CHECK_STALE` | backend/app/engine/tasks/design_job.py | DOC9A |
| error | `error:AI_TASK_DRAFT_HELD` | backend/app/engine/tasks/store.py | DOC9A |
| error | `error:AI_TASK_NEEDS_WORDS` | backend/app/management/routers/ai_tasks.py | DOC9A |
| error | `error:AI_TASK_NOTHING_TO_LOAD` | backend/app/engine/tasks/design_job.py | DOC9A |
| error | `error:AI_TASK_NOT_FOUND` | backend/app/engine/tasks/store.py | DOC9A |
| error | `error:AI_TASK_STATE` | backend/app/engine/tasks/changes.py | DOC9A |
| error | `error:AI_TASK_TABLE_UNKNOWN` | backend/app/engine/tasks/changes.py | DOC9A |
| error | `error:AI_TASK_VERSION_CONFLICT` | backend/app/engine/tasks/store.py | DOC9A |
| error | `error:AMBIGUOUS_MATCH` | backend/app/engine/reads/consumer_xref.py |  |
| error | `error:AMBIGUOUS_TARGET` | backend/app/engine/reads/consumer_objects.py |  |
| error | `error:APPROVAL_POLICY_INVALID` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:APPROVAL_REQUIRED` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:AS_OF_NOT_SUPPORTED` | backend/app/engine/jobs/exports.py |  |
| error | `error:ATTRIBUTE_ABOVE_MAXIMUM` | backend/app/engine/jobs/batches.py |  |
| error | `error:ATTRIBUTE_ALREADY_EXISTS` | backend/app/engine/records/attributes.py |  |
| error | `error:ATTRIBUTE_BELOW_MINIMUM` | backend/app/engine/jobs/batches.py |  |
| error | `error:ATTRIBUTE_NOT_FOUND` | backend/app/engine/records/attributes.py |  |
| error | `error:AUTHENTICATION_REQUIRED` | backend/app/engine/identity/authentication.py |  |
| error | `error:BATCH_TOO_LARGE` | backend/app/consumer/router.py |  |
| error | `error:CANNOT_DELETE_REQUIRED_ATTRIBUTE` | backend/app/engine/records/attributes.py |  |
| error | `error:CARDINALITY_VIOLATION` | backend/app/engine/records/rules.py |  |
| error | `error:CHANGE_SET_BASE_INVALID` | backend/app/engine/change_sets/access.py |  |
| error | `error:CHANGE_SET_CONTENT_INCOMPATIBLE` | backend/app/engine/change_sets/pinning.py |  |
| error | `error:CHANGE_SET_INVALID` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:CHANGE_SET_MODEL_RELEASE_CONFLICT` | backend/app/engine/change_sets/publish.py |  |
| error | `error:CHANGE_SET_NOT_FOUND` | backend/app/engine/change_sets/access.py |  |
| error | `error:CHANGE_SET_REQUIRED` | backend/app/engine/jobs/batches.py |  |
| error | `error:CHANGE_SET_SNAPSHOT_RETRY` | backend/app/engine/change_sets/lifecycle.py |  |
| error | `error:CHANGE_SET_SOURCE_INVALID` | backend/app/engine/change_sets/lifecycle.py |  |
| error | `error:CHANGE_SET_SUBMITTED` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:CHANGE_SET_VERSION_CONFLICT` | backend/app/engine/change_sets/pinning.py |  |
| error | `error:CHILD_TYPE_NOT_ALLOWED` | backend/app/engine/operations/restructuring.py |  |
| error | `error:CLIENT_HAS_NO_SECRETS` | backend/app/engine/identity/clients.py | DOC9A |
| error | `error:CLIENT_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:CLIENT_SECRET_NOT_FOUND` | backend/app/engine/identity/clients.py |  |
| error | `error:CODE_INCORRECT` | backend/app/engine/identity/second_factor.py |  |
| error | `error:COMMENT_REQUIRED` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:CONFLICTING_COLUMN_PARAMETERS` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:CONFLICTING_PAGE_PARAMETERS` | backend/app/common/pagination.py |  |
| error | `error:CONSUMER_API_CLIENTS_ONLY` | backend/app/engine/authorization/administration.py |  |
| error | `error:CONSUMER_API_NOT_FOUND` | backend/app/engine/events/subscription_rules.py |  |
| error | `error:CONSUMER_API_REMOVED` | backend/app/engine/model/consumer_contract.py |  |
| error | `error:CONSUMER_CONTRACT_VERSION_DECREASED` | backend/app/engine/model/consumer_contract.py |  |
| error | `error:CONSUMER_CONTRACT_VERSION_REQUIRED` | backend/app/engine/model/consumer_contract.py |  |
| error | `error:CONTRACT_VERSION_NOT_FOUND` | backend/app/engine/reads/consumer_objects.py |  |
| error | `error:COUNTERPARTS_ACROSS_MODELS` | backend/app/engine/jobs/store.py |  |
| error | `error:DEFAULT_WORKSPACE_CANNOT_BE_RETIRED` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:DELETION_PREVIEW_CHANGED` | backend/app/engine/change_sets/records.py |  |
| error | `error:DELETION_PREVIEW_REQUIRED` | backend/app/engine/jobs/batches.py |  |
| error | `error:DELIVERY_NOT_FOUND` | backend/app/engine/events/delivery_log.py |  |
| error | `error:DELIVERY_NOT_SENT` | backend/app/engine/events/resend.py |  |
| error | `error:DIGEST_NOT_SET` | backend/app/engine/notifications/mailing.py | DOC9A |
| error | `error:DRY_RUN_NOT_FOUND` | backend/app/management/routers/source_files.py |  |
| error | `error:DUPLICATE_ATTRIBUTE` | backend/app/engine/jobs/batches.py |  |
| error | `error:DUPLICATE_ATTRIBUTE_VALUE` | backend/app/engine/change_sets/validation.py |  |
| error | `error:DUPLICATE_COLUMN_IDS` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:DUPLICATE_INITIAL_RELATION` | backend/app/engine/jobs/batches.py |  |
| error | `error:DUPLICATE_RELATION` | backend/app/engine/records/objects.py |  |
| error | `error:DUPLICATE_RELATION_SCOPE` | backend/app/engine/change_sets/validation.py |  |
| error | `error:EVENTS_EXPIRED` | backend/app/engine/events/subscription_rules.py |  |
| error | `error:EVENTS_NOT_DECLARED` | backend/app/consumer/router.py |  |
| error | `error:EVENT_NOT_IN_DELIVERY` | backend/app/engine/events/resend.py |  |
| error | `error:EVENT_POSITION_AHEAD` | backend/app/engine/events/subscriptions.py |  |
| error | `error:FEED_POSITION_AHEAD` | backend/app/engine/reads/feed.py |  |
| error | `error:FEED_POSITION_EXPIRED` | backend/app/engine/reads/feed.py |  |
| error | `error:FILTER_MATCHES_NOTHING` | backend/app/engine/events/subscription_rules.py |  |
| error | `error:FORBIDDEN` | backend/app/consumer/router.py |  |
| error | `error:GRANT_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:GRANT_SCOPE_INVALID` | backend/app/engine/authorization/administration.py |  |
| error | `error:GRANT_SCOPE_UNKNOWN` | backend/app/engine/authorization/administration.py |  |
| error | `error:GROUP_CLAIM_TAKEN` | backend/app/engine/authorization/administration.py |  |
| error | `error:GROUP_FROM_PROVIDER` | backend/app/engine/authorization/administration.py |  |
| error | `error:GROUP_MEMBER_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:GROUP_NAME_TAKEN` | backend/app/engine/authorization/administration.py |  |
| error | `error:GROUP_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:HISTORY_PERIOD_INVALID` | backend/app/management/history_account.py | DOC9A |
| error | `error:IDEMPOTENCY_IN_PROGRESS` | backend/app/engine/jobs/store.py |  |
| error | `error:IDEMPOTENCY_KEY_REUSED` | backend/app/engine/jobs/store.py |  |
| error | `error:IDENTITY_NOT_FOUND` | backend/app/engine/identity/links.py |  |
| error | `error:IDENTITY_PROVIDER_TAKEN` | backend/app/engine/identity/links.py |  |
| error | `error:IMMUTABLE_RELATION` | backend/app/engine/records/refusals.py |  |
| error | `error:IMPACT_SUMMARY_DRAFT_INVALID` | backend/app/management/impact_summary.py | DOC9A |
| error | `error:IMPORT_FILE_MISMATCH` | backend/app/engine/imports/binding.py |  |
| error | `error:IMPORT_FILE_MISSING` | backend/app/engine/imports/binding.py |  |
| error | `error:IMPORT_FILE_UNREADABLE` | backend/app/engine/imports/readers.py |  |
| error | `error:IMPORT_PROFILE_EXISTS` | backend/app/engine/imports/profiles.py |  |
| error | `error:IMPORT_PROFILE_NOT_FOUND` | backend/app/engine/imports/profiles.py |  |
| error | `error:IMPORT_PROFILE_VERSION_CONFLICT` | backend/app/engine/imports/profiles.py |  |
| error | `error:IMPORT_TOO_LARGE` | backend/app/engine/imports/submit.py |  |
| error | `error:IMPORT_TOO_MANY_ITEMS` | backend/app/engine/imports/binding.py |  |
| error | `error:INCOMPLETE_VIEW_IDENTITY` | backend/app/management/projections/mapping.py |  |
| error | `error:INFERENCE_NOT_FOUND` | backend/app/engine/moves/mapping_inference.py |  |
| error | `error:INFERENCE_NOT_READY` | backend/app/engine/moves/mapping_inference.py |  |
| error | `error:INFERENCE_STALE` | backend/app/engine/moves/mapping_inference.py |  |
| error | `error:INTERNAL_ERROR` | backend/app/engine/records/attributes.py |  |
| error | `error:INVALID_AS_OF` | backend/app/engine/reads/consumer_request.py |  |
| error | `error:INVALID_ATTRIBUTE_VALUE` | backend/app/engine/imports/cells.py |  |
| error | `error:INVALID_BATCH_CONTEXT` | backend/app/engine/jobs/batches.py |  |
| error | `error:INVALID_CLEAR_ATTRIBUTES` | backend/app/engine/operations/mapping_replacement.py |  |
| error | `error:INVALID_CURSOR` | backend/app/common/cursors.py |  |
| error | `error:INVALID_DATE` | backend/app/management/mcp_tools.py | DOC9A |
| error | `error:INVALID_EFFECTIVE_PERIOD` | backend/app/engine/jobs/batches.py |  |
| error | `error:INVALID_EXPAND` | backend/app/engine/reads/model_query.py |  |
| error | `error:INVALID_EXPECT` | backend/app/consumer/router.py |  |
| error | `error:INVALID_EXPORT_LAYOUT` | backend/app/engine/jobs/people.py |  |
| error | `error:INVALID_FILTER` | backend/app/engine/reads/model_query.py |  |
| error | `error:INVALID_IMPORT_PROFILE` | backend/app/engine/imports/profiles.py |  |
| error | `error:INVALID_INFERENCE_REQUEST` | backend/app/engine/sources/inference/one_list.py |  |
| error | `error:INVALID_INSTALLED_MODEL` | backend/app/management/impact_summary.py |  |
| error | `error:INVALID_MIGRATION_MAPPING` | backend/app/engine/model/migrations.py |  |
| error | `error:INVALID_MODEL` | backend/app/engine/model/authoring/consumer_documents.py |  |
| error | `error:INVALID_MODEL_MAPPING` | backend/app/engine/moves/mappings.py |  |
| error | `error:INVALID_OBJECT_TYPE_FOR_APPLICATION` | backend/app/engine/records/refusals.py |  |
| error | `error:INVALID_OPERATION` | backend/app/engine/model/authoring/history.py |  |
| error | `error:INVALID_PAGE_PARAMETER` | backend/app/engine/reads/consumer_request.py |  |
| error | `error:INVALID_PAGE_SIZE` | backend/app/consumer/router.py |  |
| error | `error:INVALID_PARENT_TYPE` | backend/app/engine/change_sets/records.py |  |
| error | `error:INVALID_PAYLOAD` | backend/app/consumer/router.py |  |
| error | `error:INVALID_POSITION` | backend/app/common/pagination.py |  |
| error | `error:INVALID_QUERY` | backend/app/engine/jobs/exports.py |  |
| error | `error:INVALID_RANGE` | backend/app/engine/sources/inference/one_list.py |  |
| error | `error:INVALID_RECORD_KEY` | backend/app/engine/jobs/batches.py |  |
| error | `error:INVALID_RELATION_PAIR` | backend/app/engine/change_sets/validation.py |  |
| error | `error:INVALID_SEEK` | backend/app/common/pagination.py |  |
| error | `error:INVALID_SORT` | backend/app/engine/reads/model_query.py |  |
| error | `error:INVALID_TYPE_MAPPING` | backend/app/engine/operations/restructuring.py |  |
| error | `error:INVALID_WEBHOOK_URL` | backend/app/engine/events/webhook_urls.py |  |
| error | `error:JOB_EXPIRED` | backend/app/engine/jobs/store.py |  |
| error | `error:JOB_FINISHED` | backend/app/engine/jobs/background.py |  |
| error | `error:JOB_HAS_NO_OUTPUT` | backend/app/management/routers/jobs.py |  |
| error | `error:JOB_HAS_NO_ROWS` | backend/app/management/projections/job_rows.py |  |
| error | `error:JOB_NOT_AWAITING_CONFIRMATION` | backend/app/engine/jobs/store.py |  |
| error | `error:JOB_NOT_COMPLETED` | backend/app/management/routers/jobs.py |  |
| error | `error:JOB_NOT_FOUND` | backend/app/engine/jobs/store.py |  |
| error | `error:JOB_OUTPUT_MISSING` | backend/app/management/routers/jobs.py |  |
| error | `error:LAST_LOCAL_ADMINISTRATOR` | backend/app/engine/identity/providers.py |  |
| error | `error:LAST_SECURITY_ADMINISTRATOR` | backend/app/engine/authorization/administration.py |  |
| error | `error:LINK_SAME_PERSON` | backend/app/engine/identity/links.py |  |
| error | `error:LINK_TARGET_DEACTIVATED` | backend/app/engine/identity/links.py |  |
| error | `error:LIST_NOT_FOUND` | backend/app/engine/reads/consumer_lists.py |  |
| error | `error:LIST_REQUIRED` | backend/app/engine/agent_access/lookup.py | DOC9A |
| error | `error:LOCAL_SIGN_IN_OFF` | backend/app/engine/identity/providers.py |  |
| error | `error:MAIL_INSECURE_LOGIN` | backend/app/engine/mail/settings.py |  |
| error | `error:MAIL_NOT_SET_UP` | backend/app/engine/mail/settings.py |  |
| error | `error:MAIL_PASSWORD_REQUIRED` | backend/app/engine/mail/settings.py |  |
| error | `error:MAIL_SEND_FAILED` | backend/app/management/routers/mail.py |  |
| error | `error:MAPPING_BINDING_NOT_FOUND` | backend/app/management/projections/mapping.py |  |
| error | `error:MAPPING_CANDIDATE_TYPE_MISMATCH` | backend/app/management/projections/mapping.py |  |
| error | `error:MAPPING_ENDPOINT_NOT_FOUND` | backend/app/engine/operations/mapping_replacement.py |  |
| error | `error:MAPPING_ENDPOINT_TYPE_MISMATCH` | backend/app/engine/operations/mapping_replacement.py |  |
| error | `error:MAPPING_PARENT_NOT_FOUND` | backend/app/engine/proposals/mapping_job.py |  |
| error | `error:MAPPING_PARENT_SCOPE_MISMATCH` | backend/app/management/projections/mapping.py |  |
| error | `error:MAPPING_PROPOSED_NEEDS_CHANGE_SET` | backend/app/management/projections/mapping.py | DOC9A |
| error | `error:MAPPING_SOURCE_NOT_FOUND` | backend/app/management/projections/mapping.py |  |
| error | `error:MAPPING_VERSION_CONFLICT` | backend/app/engine/operations/mapping_replacement.py |  |
| error | `error:MAPPING_VIEW_BINDING_MISMATCH` | backend/app/management/projections/mapping.py |  |
| error | `error:MAPPING_VIEW_NOT_FOUND` | backend/app/engine/proposals/mapping_job.py |  |
| error | `error:MAPPING_VIEW_REQUIRED` | backend/app/management/routers/mapping.py |  |
| error | `error:MESSAGE_BEING_SENT` | backend/app/engine/mail/outbox.py |  |
| error | `error:MESSAGE_NOT_WAITING` | backend/app/engine/mail/outbox.py |  |
| error | `error:MIGRATION_FAILED` | backend/app/engine/model/change_set_migrations.py |  |
| error | `error:MIGRATION_HAS_REFUSALS` | backend/app/engine/model/migrations.py |  |
| error | `error:MIGRATION_LOSS_NOT_ACCEPTED` | backend/app/engine/model/migrations.py |  |
| error | `error:MIGRATION_REVIEW_STALE` | backend/app/engine/model/change_set_migrations.py |  |
| error | `error:MIGRATION_TARGET_IS_CURRENT` | backend/app/engine/model/change_set_migrations.py |  |
| error | `error:MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE` | backend/app/engine/model/migrations.py |  |
| error | `error:MIGRATION_TARGET_NOT_WORKSPACE_RELEASE` | backend/app/engine/model/change_set_migrations.py |  |
| error | `error:MISSING_DELETE_NEEDS_CHANGE_SET` | backend/app/engine/imports/submit.py |  |
| error | `error:MISSING_RECORD_KEY` | backend/app/engine/imports/binding.py |  |
| error | `error:MISSING_REQUIRED_ATTRIBUTES` | backend/app/engine/jobs/batches.py |  |
| error | `error:MISSING_REQUIRED_RELATIONS` | backend/app/engine/jobs/batches.py |  |
| error | `error:MODEL_DRAFT_NOT_FOUND` | backend/app/engine/model/drafts.py |  |
| error | `error:MODEL_ELEMENT_NOT_IN_EVERY_MODEL` | backend/app/engine/reads/object_lookup.py |  |
| error | `error:MODEL_HASH_CHANGED` | backend/app/engine/model/raising.py |  |
| error | `error:MODEL_MAPPING_EXISTS` | backend/app/engine/moves/mappings.py |  |
| error | `error:MODEL_MAPPING_MODEL_MISMATCH` | backend/app/engine/moves/mappings.py |  |
| error | `error:MODEL_MAPPING_NOT_FOUND` | backend/app/engine/moves/mappings.py |  |
| error | `error:MODEL_MIGRATION_REQUIRED` | backend/app/engine/proposals/impact_summary.py |  |
| error | `error:MODEL_REGISTRY_REFRESH_FAILED` | backend/app/management/routers/model_management.py |  |
| error | `error:MODEL_REGISTRY_UNAVAILABLE` | backend/app/engine/identity/authentication.py |  |
| error | `error:MODEL_RELEASE_CHANGED` | backend/app/engine/jobs/background.py |  |
| error | `error:MODEL_RELEASE_IN_USE` | backend/app/engine/model/release_lifecycle.py |  |
| error | `error:MODEL_RELEASE_IS_DEFAULT` | backend/app/engine/model/release_lifecycle.py |  |
| error | `error:MODEL_RELEASE_NOT_FOUND` | backend/app/engine/model/drafts.py |  |
| error | `error:MODEL_RELEASE_RETIRED` | backend/app/engine/model/release_lifecycle.py |  |
| error | `error:MODEL_RELEASE_VERSION_CONFLICT` | backend/app/engine/model/release_lifecycle.py |  |
| error | `error:MOVE_COPY_NOT_PUBLISHED` | backend/app/engine/change_sets/publish.py |  |
| error | `error:MOVE_MAPPING_CHANGED` | backend/app/engine/moves/move_job.py |  |
| error | `error:MOVE_MAPPING_HAS_PROBLEMS` | backend/app/engine/moves/move_job.py |  |
| error | `error:MOVE_NOTHING_TO_MOVE` | backend/app/engine/moves/move_load.py |  |
| error | `error:MOVE_SAME_WORKSPACE` | backend/app/engine/moves/move_job.py |  |
| error | `error:MULTIPLE_TARGETS` | backend/app/engine/reads/consumer_request.py |  |
| error | `error:MUTUALLY_EXCLUSIVE_CONTEXT` | backend/app/engine/model/registry.py |  |
| error | `error:MUTUALLY_EXCLUSIVE_SCOPE` | backend/app/management/routers/objects.py |  |
| error | `error:NOTHING_TO_APPLY` | backend/app/engine/model/authoring/history.py |  |
| error | `error:NOTHING_TO_REDO` | backend/app/engine/model/authoring/history.py |  |
| error | `error:NOTHING_TO_UNDO` | backend/app/engine/model/authoring/history.py |  |
| error | `error:NOT_A_PERSON` | backend/app/management/routers/identity.py |  |
| error | `error:NOT_FOUND` | backend/app/engine/mail/outbox.py |  |
| error | `error:NOT_SUBMITTED` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:NOT_SUPPORTED_BY_SOURCE` | backend/app/engine/events/subscriptions.py |  |
| error | `error:NO_EMAIL` | backend/app/engine/mail/links.py |  |
| error | `error:NO_IDENTITY_TO_LINK` | backend/app/engine/identity/links.py |  |
| error | `error:NO_MATCH` | backend/app/engine/reads/consumer_xref.py |  |
| error | `error:NO_WORKING_PROVIDER` | backend/app/engine/identity/providers.py |  |
| error | `error:OBJECT_ALREADY_EXISTS` | backend/app/engine/jobs/batches.py |  |
| error | `error:OBJECT_ATTRIBUTE_RULE_VIOLATION` | backend/app/engine/jobs/batches.py |  |
| error | `error:OBJECT_HAS_DEPENDANTS` | backend/app/engine/moves/move_load.py |  |
| error | `error:OBJECT_ID_REQUIRED` | backend/app/engine/agent_access/lookup.py | DOC9A |
| error | `error:OBJECT_NOT_FOUND` | backend/app/engine/change_sets/records.py |  |
| error | `error:OBJECT_TYPE_CHANGED` | backend/app/engine/records/rules.py |  |
| error | `error:OBJECT_TYPE_NOT_IN_APPLICATION` | backend/app/engine/change_sets/validation.py |  |
| error | `error:OBJECT_TYPE_UNCHANGED` | backend/app/engine/operations/restructuring.py |  |
| error | `error:OPERATION_BATCH_TOO_LARGE` | backend/app/engine/model/authoring/history.py |  |
| error | `error:OPERATION_HAS_DEPENDANTS` | backend/app/engine/model/authoring/history.py |  |
| error | `error:OPERATION_NOT_OFFERED` | backend/app/consumer/router.py |  |
| error | `error:OPERATION_REQUIRES_MIGRATION` | backend/app/engine/model/authoring/history.py |  |
| error | `error:PARAMETER_NOT_SUPPORTED` | backend/app/consumer/router.py |  |
| error | `error:PARENT_CYCLE` | backend/app/engine/jobs/batches.py |  |
| error | `error:PARENT_NOT_FOUND` | backend/app/engine/jobs/exports.py |  |
| error | `error:PARENT_REQUIRED` | backend/app/engine/jobs/batches.py |  |
| error | `error:PARENT_WRONG_SCOPE` | backend/app/engine/change_sets/records.py |  |
| error | `error:PASSKEY_NOT_FOUND` | backend/app/engine/identity/passkeys.py |  |
| error | `error:PASSWORD_INCORRECT` | backend/app/engine/identity/resets.py |  |
| error | `error:PASSWORD_REJECTED` | backend/app/engine/identity/passwords.py |  |
| error | `error:PASSWORD_REQUIRED` | backend/app/engine/identity/passkeys.py |  |
| error | `error:PERSON_HAS_ACCESS` | backend/app/engine/identity/links.py |  |
| error | `error:PINNED_MODEL_INVALID` | backend/app/engine/model/registry.py |  |
| error | `error:PINNED_MODEL_UNAVAILABLE` | backend/app/engine/change_sets/pinning.py |  |
| error | `error:PROFILE_CHECK_NOT_FOUND` | backend/app/management/routers/imports.py |  |
| error | `error:PROOF_REQUIRED` | backend/app/engine/identity/second_factor.py |  |
| error | `error:PROPOSAL_ALREADY_APPLIED` | backend/app/engine/moves/mapping_inference.py |  |
| error | `error:PROPOSAL_NOT_FOUND` | backend/app/engine/moves/mapping_inference.py |  |
| error | `error:PROPOSAL_REQUIREMENT_MISSING` | backend/app/engine/moves/mapping_inference.py |  |
| error | `error:PUBLICATION_CONFLICT` | backend/app/engine/change_sets/approvals.py |  |
| error | `error:PUBLICATION_CONTRACT_MISMATCH` | backend/app/consumer/router.py |  |
| error | `error:PUBLICATION_NOT_FOUND` | backend/app/consumer/router.py |  |
| error | `error:QUERY_OR_ID_REQUIRED` | backend/app/consumer/router.py |  |
| error | `error:QUERY_REQUIRED` | backend/app/engine/reads/consumer_xref.py |  |
| error | `error:QUERY_TOO_BROAD` | backend/app/engine/reads/consumer_xref.py |  |
| error | `error:QUERY_TRANSLATION_FAILED` | backend/app/engine/proposals/query_translation.py | DOC9A |
| error | `error:QUERY_TRANSLATION_VIEW_UNSUPPORTED` | backend/app/engine/proposals/query_translation.py | DOC9A |
| error | `error:READ_ONLY_ATTRIBUTES` | backend/app/engine/jobs/batches.py |  |
| error | `error:REFERENCE_NOT_FOUND` | backend/app/engine/imports/binding.py |  |
| error | `error:REFERENCE_TYPE_MISMATCH` | backend/app/engine/jobs/batches.py |  |
| error | `error:RELATION_ALREADY_EXISTS` | backend/app/engine/operations/type_changes.py |  |
| error | `error:RELATION_ANCESTOR_REQUIRED` | backend/app/engine/records/rules.py |  |
| error | `error:RELATION_CANDIDATE_REFUSED` | backend/app/engine/records/rules.py |  |
| error | `error:RELATION_ENDPOINT_MISSING` | backend/app/engine/change_sets/validation.py |  |
| error | `error:RELATION_MATRIX_ACTION_NOT_ALLOWED` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_MATRIX_COLUMN_NOT_FOUND` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_MATRIX_PARENT_NOT_FOUND` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_MATRIX_PARENT_SCOPE_MISMATCH` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_MATRIX_ROW_NOT_FOUND` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_MATRIX_STATE_REQUIRES_COLUMNS` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_MATRIX_VIEW_NOT_FOUND` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:RELATION_NOT_FOUND` | backend/app/engine/change_sets/records.py |  |
| error | `error:RELATION_SET_CLAIM_INCOMPLETE` | backend/app/engine/jobs/batches.py |  |
| error | `error:RELATION_SET_VERSION_CONFLICT` | backend/app/engine/jobs/batches.py |  |
| error | `error:RELATION_WRONG_SCOPE` | backend/app/engine/records/objects.py |  |
| error | `error:RELEASE_IDENTITY_CONFLICT` | backend/app/management/routers/model_management.py |  |
| error | `error:RELEASE_NOT_RAISABLE` | backend/app/engine/model/raising.py |  |
| error | `error:RELEASE_RAISE_REFUSED` | backend/app/engine/model/raising.py |  |
| error | `error:REQUEST_VALIDATION_ERROR` | backend/app/consumer/router.py |  |
| error | `error:REQUIRED_OWNERSHIP_BINDING` | backend/app/engine/records/relation_sets.py |  |
| error | `error:REQUIRED_RELATION` | backend/app/engine/records/refusals.py |  |
| error | `error:REQUIRED_RELATION_WITHOUT_PLACE` | backend/app/engine/operations/restructuring.py |  |
| error | `error:RESOURCE_NOT_FOUND` | backend/app/management/mcp_tools.py | DOC9A |
| error | `error:RESTRUCTURING_NOT_READY` | backend/app/engine/operations/restructuring.py |  |
| error | `error:RESTRUCTURING_PLAN_CHANGED` | backend/app/engine/operations/restructuring.py |  |
| error | `error:RESTRUCTURING_TOO_LARGE` | backend/app/engine/operations/restructuring.py |  |
| error | `error:ROLE_IN_USE` | backend/app/engine/authorization/administration.py |  |
| error | `error:ROLE_NAME_TAKEN` | backend/app/engine/authorization/administration.py |  |
| error | `error:ROLE_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:ROLE_PREDEFINED` | backend/app/engine/authorization/administration.py |  |
| error | `error:ROUTE_NOT_DECLARED` | backend/app/management/access.py |  |
| error | `error:SECOND_FACTOR_EXISTS` | backend/app/engine/identity/second_factor.py |  |
| error | `error:SECOND_FACTOR_NOT_FOUND` | backend/app/engine/identity/second_factor.py |  |
| error | `error:SECOND_FACTOR_REQUIRED` | backend/app/engine/identity/passkeys.py |  |
| error | `error:SESSION_NOT_FOUND` | backend/app/engine/identity/sessions.py |  |
| error | `error:SIGN_IN_PROVIDER_IN_USE` | backend/app/engine/identity/providers.py |  |
| error | `error:SIGN_IN_PROVIDER_KEY_TAKEN` | backend/app/engine/identity/providers.py |  |
| error | `error:SIGN_IN_PROVIDER_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:SIGN_IN_PROVIDER_SECRET_REQUIRED` | backend/app/engine/identity/providers.py |  |
| error | `error:SIGN_IN_PROVIDER_UNREACHABLE` | backend/app/engine/identity/providers.py |  |
| error | `error:SIGN_IN_SLOWED` | backend/app/engine/identity/resets.py |  |
| error | `error:SOURCE_FILE_MISSING` | backend/app/engine/sources/profiling.py |  |
| error | `error:SOURCE_FILE_NOT_FOUND` | backend/app/engine/sources/dry_run.py |  |
| error | `error:SOURCE_FILE_PROFILE_NOT_READY` | backend/app/engine/sources/profile_check.py |  |
| error | `error:SOURCE_SHEET_NOT_FOUND` | backend/app/engine/sources/inference/one_list.py |  |
| error | `error:SUBSCRIPTION_ALREADY_SUSPENDED` | backend/app/engine/events/subscriptions.py |  |
| error | `error:SUBSCRIPTION_NEEDS_EDIT` | backend/app/engine/events/subscriptions.py |  |
| error | `error:SUBSCRIPTION_NOT_FOUND` | backend/app/engine/events/subscriptions.py |  |
| error | `error:SUBSCRIPTION_NOT_SUSPENDED` | backend/app/engine/events/subscriptions.py |  |
| error | `error:TARGET_NOT_FOUND` | backend/app/engine/reads/consumer_objects.py |  |
| error | `error:TOKEN_INVALID` | backend/app/engine/identity/authentication.py |  |
| error | `error:TOO_MANY_COLUMNS` | backend/app/management/projections/relation_matrix.py |  |
| error | `error:TOO_MANY_PASSKEYS` | backend/app/engine/identity/passkeys.py |  |
| error | `error:TOO_MANY_RECORDS` | backend/app/engine/reads/relation_queries.py |  |
| error | `error:TOO_MANY_TERMS` | backend/app/engine/reads/consumer_xref.py |  |
| error | `error:TYPE_CHANGES_NEED_CHANGE_SET` | backend/app/management/projections/parent_candidates.py |  |
| error | `error:UNKNOWN_APPLICATION` | backend/app/engine/imports/profiles.py |  |
| error | `error:UNKNOWN_ATTRIBUTES` | backend/app/engine/change_sets/records.py |  |
| error | `error:UNKNOWN_ATTRIBUTE_TYPE` | backend/app/engine/model/validation/object_type_rules.py |  |
| error | `error:UNKNOWN_EVENT` | backend/app/consumer/router.py |  |
| error | `error:UNKNOWN_NOTICE_KIND` | backend/app/engine/notifications/mailing.py |  |
| error | `error:UNKNOWN_OBJECT_TYPE` | backend/app/engine/change_sets/validation.py |  |
| error | `error:UNKNOWN_PARAMETER` | backend/app/consumer/router.py |  |
| error | `error:UNKNOWN_RELATION_ATTRIBUTES` | backend/app/engine/jobs/batches.py |  |
| error | `error:UNKNOWN_RELATION_TYPE` | backend/app/engine/imports/profiles.py |  |
| error | `error:UNKNOWN_TIME_ZONE` | backend/app/engine/notifications/mailing.py | DOC9A |
| error | `error:UNSUPPORTED_FILE_FORMAT` | backend/app/engine/imports/submit.py |  |
| error | `error:UNSUPPORTED_PINNED_MODEL_SCHEMA` | backend/app/engine/model/registry.py |  |
| error | `error:UNSUPPORTED_SCHEMA_VERSION` | backend/app/engine/model/compiler.py |  |
| error | `error:USERNAME_TAKEN` | backend/app/engine/identity/users.py |  |
| error | `error:USER_NOT_FOUND` | backend/app/engine/authorization/administration.py |  |
| error | `error:VERSION_CONFLICT` | backend/app/engine/authorization/administration.py |  |
| error | `error:VERSION_REQUIRED` | backend/app/engine/jobs/batches.py |  |
| error | `error:VIEW_NOT_FOUND` | backend/app/engine/proposals/query_translation.py | DOC9A |
| error | `error:WORKSPACE_ACTIVE_PUBLICATION_CONFLICT` | backend/app/engine/change_sets/publish.py |  |
| error | `error:WORKSPACE_ALREADY_EXISTS` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:WORKSPACE_CONTEXT_MISMATCH` | backend/app/engine/model/registry.py |  |
| error | `error:WORKSPACE_GRAPH_INVALID` | backend/app/engine/change_sets/publish.py |  |
| error | `error:WORKSPACE_HAS_PUBLICATIONS` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:WORKSPACE_HAS_SUBSCRIPTIONS` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:WORKSPACE_IS_DEFAULT` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:WORKSPACE_KEY_REQUIRED` | backend/app/management/routers/objects.py |  |
| error | `error:WORKSPACE_NOT_EMPTY` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:WORKSPACE_NOT_FOUND` | backend/app/consumer/router.py |  |
| error | `error:WORKSPACE_RETIRED` | backend/app/engine/change_sets/access.py |  |
| error | `error:WORKSPACE_RUNTIME_STATE_MISSING` | backend/app/engine/workspaces/catalogue.py |  |
| error | `error:WRITER_UNKNOWN` | backend/app/engine/authorization/writes.py |  |

## command (9)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| command | `command:create_admin` | Create the first administrator on the server (Product 0.12 I1, D235). (app/cli/create_admin.py) |  |
| command | `command:create_client` | Create an OAuth client on the server and print its credentials once (Product 0.12 I1, D262). (app/cli/create_client.py) |  |
| command | `command:database_upgrade` | Upgrade the configured database with operator-facing errors and no traceback. (app/cli/database_upgrade.py) |  |
| command | `command:generate_key` | Print a new key for ``SECRETS_ENCRYPTION_KEY``: 32 random bytes in URL-safe base64. (app/cli/generate_key.py) |  |
| command | `command:model_release_prune` | Delete the stored model releases nothing refers to. (app/cli/model_release_prune.py) |  |
| command | `command:model_release_raise` | Raise stored model releases of a schema older than the window to the window's schema, in place. (app/cli/model_release_raise.py) |  |
| command | `command:reseal_secrets` | Re-seal every sealed secret under a new ``SECRETS_ENCRYPTION_KEY`` (Product 0.12 K1, D414). (app/cli/reseal_secrets.py) |  |
| command | `command:restore_check` | Check a restored copy of this instance's database and record the result (Product 0.11 O2). (app/cli/restore_check.py) |  |
| command | `command:settings_template` | Print every engine setting as a commented template, from the settings catalogue (``config.py``). (app/cli/settings_template.py) | DOC9A |

## role (10)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| role | `role:reader` | groups: browse (app/engine/authorization/catalogue.py) |  |
| role | `role:contributor` | groups: browse, change-sets (app/engine/authorization/catalogue.py) |  |
| role | `role:steward` | groups: browse, edit-live, change-sets, publish, bulk, ai-proposals (app/engine/authorization/catalogue.py) |  |
| role | `role:owner` | groups: browse, edit-live, change-sets, publish, approve, bulk, feed, copy-move, ai-proposals (app/engine/authorization/catalogue.py) |  |
| role | `role:model-admin` | groups: model-authoring, model-install, model-release, ai-proposals (app/engine/authorization/catalogue.py) |  |
| role | `role:workspace-admin` | groups: workspace-admin, ai-proposals (app/engine/authorization/catalogue.py) |  |
| role | `role:integration-admin` | groups: integration-admin, feed, ai-proposals (app/engine/authorization/catalogue.py) |  |
| role | `role:operator` | groups: operations (app/engine/authorization/catalogue.py) |  |
| role | `role:security-admin` | groups: security-admin (app/engine/authorization/catalogue.py) |  |
| role | `role:agent` | groups: browse, change-sets (app/engine/authorization/catalogue.py) | DOC9A |

## permission (16)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| permission | `permission:browse` | Browse |  |
| permission | `permission:edit-live` | Edit live |  |
| permission | `permission:change-sets` | Work in change sets |  |
| permission | `permission:publish` | Publish |  |
| permission | `permission:approve` | Approve publications |  |
| permission | `permission:bulk` | Bulk and import |  |
| permission | `permission:copy-move` | Copy and move |  |
| permission | `permission:model-authoring` | Model authoring |  |
| permission | `permission:model-install` | Install a model | DOC9A |
| permission | `permission:model-release` | Model release |  |
| permission | `permission:workspace-admin` | Workspace administration |  |
| permission | `permission:integration-admin` | Integration administration |  |
| permission | `permission:feed` | Feed |  |
| permission | `permission:operations` | Operations |  |
| permission | `permission:security-admin` | Security administration |  |
| permission | `permission:ai-proposals` | Use AI proposals | DOC9A |

## event (10)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| event | `event:change-set.submitted` | workspace event; inbox notice |  |
| event | `event:change-set.approved` | workspace event; inbox notice |  |
| event | `event:change-set.sent-back` | workspace event; inbox notice |  |
| event | `event:consumer.created` | consumer record change |  |
| event | `event:consumer.updated` | consumer record change |  |
| event | `event:consumer.deleted` | consumer record change |  |
| event | `event:job.completed` | inbox notice: A job you started has finished |  |
| event | `event:job.failed` | inbox notice: A job you started has failed |  |
| event | `event:job.awaiting-confirmation` | inbox notice: A job you started is waiting for your confirmation |  |
| event | `event:change-set.published` | inbox notice: A change set was published in a workspace you follow | DOC9A |

## field (319)

| Kind | Key | Description / source | Owner |
|---|---|---|---|
| field | `field:AlsoMatchThrough.related` | backend/app/models/schema.py |  |
| field | `field:AlsoMatchThrough.firstOf` | backend/app/models/schema.py |  |
| field | `field:AlsoMatchThrough.preferTypes` | backend/app/models/schema.py |  |
| field | `field:AncestorParameter.kind` | backend/app/models/schema.py |  |
| field | `field:AncestorParameter.objectTypes` | backend/app/models/schema.py |  |
| field | `field:AncestorParameter.matchFields` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.key` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.name` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.description` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.icon` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.color` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.state` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.objectTypeKeys` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.defaultView` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.views` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.details` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.settings` | backend/app/models/schema.py |  |
| field | `field:ApplicationDefinition.navigation` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.key` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.name` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.description` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.valueType` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.default` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.features` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.validation` | backend/app/models/schema.py |  |
| field | `field:AttributeTypeDefinition.ui` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelConfig.fields` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.key` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.title` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.region` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.order` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.visible` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.type` | backend/app/models/schema.py |  |
| field | `field:AttributesPanelDefinition.config` | backend/app/models/schema.py |  |
| field | `field:BindingCandidates.from` | backend/app/models/schema.py |  |
| field | `field:BindingCandidates.to` | backend/app/models/schema.py |  |
| field | `field:BreadcrumbDefinition.showApplication` | backend/app/models/schema.py |  |
| field | `field:BreadcrumbDefinition.showObjectType` | backend/app/models/schema.py |  |
| field | `field:BreadcrumbDefinition.showAncestors` | backend/app/models/schema.py |  |
| field | `field:CandidateCriterion.field` | backend/app/models/schema.py |  |
| field | `field:CandidateCriterion.op` | backend/app/models/schema.py |  |
| field | `field:CandidateCriterion.value` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelConfig.objectTypeKeys` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelConfig.columns` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelConfig.pageSize` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.key` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.title` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.region` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.order` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.visible` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.type` | backend/app/models/schema.py |  |
| field | `field:ChildrenPanelDefinition.config` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.key` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.name` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.description` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.contractVersion` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.objectTypes` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.object` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.projections` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.match` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.parameters` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.lists` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDefinition.events` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.key` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.name` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.description` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.contractVersion` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.exposes` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.publicNames` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.object` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.operations` | backend/app/models/schema.py |  |
| field | `field:ConsumerApiDocument.filters` | backend/app/models/schema.py |  |
| field | `field:ConsumerAttributeField.source` | backend/app/models/schema.py |  |
| field | `field:ConsumerAttributeField.default` | backend/app/models/schema.py |  |
| field | `field:ConsumerEvent.key` | backend/app/models/schema.py |  |
| field | `field:ConsumerEvent.objectTypes` | backend/app/models/schema.py |  |
| field | `field:ConsumerEvent.changes` | backend/app/models/schema.py |  |
| field | `field:ConsumerEvent.watch` | backend/app/models/schema.py |  |
| field | `field:ConsumerEventWatch.fields` | backend/app/models/schema.py |  |
| field | `field:ConsumerEventWatch.projections` | backend/app/models/schema.py |  |
| field | `field:ConsumerExposedType.publicName` | backend/app/models/schema.py |  |
| field | `field:ConsumerField.output` | backend/app/models/schema.py |  |
| field | `field:ConsumerField.source` | backend/app/models/schema.py |  |
| field | `field:ConsumerField.default` | backend/app/models/schema.py |  |
| field | `field:ConsumerList.key` | backend/app/models/schema.py |  |
| field | `field:ConsumerList.objectType` | backend/app/models/schema.py |  |
| field | `field:ConsumerList.parentParameter` | backend/app/models/schema.py |  |
| field | `field:ConsumerList.sortBy` | backend/app/models/schema.py |  |
| field | `field:ConsumerListParent.name` | backend/app/models/schema.py |  |
| field | `field:ConsumerListParent.objectTypes` | backend/app/models/schema.py |  |
| field | `field:ConsumerMatch.own` | backend/app/models/schema.py |  |
| field | `field:ConsumerMatch.promoted` | backend/app/models/schema.py |  |
| field | `field:ConsumerMatchRule.field` | backend/app/models/schema.py |  |
| field | `field:ConsumerMatchRule.exact` | backend/app/models/schema.py |  |
| field | `field:ConsumerMatchRule.contains` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.id` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.code` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.name` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.active` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.validFrom` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.validTo` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.attributes` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.parent` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.path` | backend/app/models/schema.py |  |
| field | `field:ConsumerObjectDefinition.hierarchy` | backend/app/models/schema.py |  |
| field | `field:ConsumerParentField.output` | backend/app/models/schema.py |  |
| field | `field:ConsumerParentField.fields` | backend/app/models/schema.py |  |
| field | `field:ConsumerProjection.from` | backend/app/models/schema.py |  |
| field | `field:ConsumerProjection.fields` | backend/app/models/schema.py |  |
| field | `field:ConsumerPromotedMatch.projection` | backend/app/models/schema.py |  |
| field | `field:ConsumerPromotedMatch.firstMatch` | backend/app/models/schema.py |  |
| field | `field:ConsumerPromotedMatch.preferTargetTypes` | backend/app/models/schema.py |  |
| field | `field:ConsumerRelationRoute.relation` | backend/app/models/schema.py |  |
| field | `field:ConsumerRelationRoute.direction` | backend/app/models/schema.py |  |
| field | `field:DetailHeaderDefinition.titleField` | backend/app/models/schema.py |  |
| field | `field:DetailHeaderDefinition.subtitleField` | backend/app/models/schema.py |  |
| field | `field:DetailHeaderDefinition.showObjectType` | backend/app/models/schema.py |  |
| field | `field:DetailViewDefinition.objectTypeKey` | backend/app/models/schema.py |  |
| field | `field:DetailViewDefinition.breadcrumbs` | backend/app/models/schema.py |  |
| field | `field:DetailViewDefinition.header` | backend/app/models/schema.py |  |
| field | `field:DetailViewDefinition.panels` | backend/app/models/schema.py |  |
| field | `field:EffectivePeriodDefinition.startAttributeTypeKey` | backend/app/models/schema.py |  |
| field | `field:EffectivePeriodDefinition.endAttributeTypeKey` | backend/app/models/schema.py |  |
| field | `field:EngineModel.schemaVersion` | backend/app/models/schema.py |  |
| field | `field:EngineModel.release` | backend/app/models/schema.py |  |
| field | `field:EngineModel.product` | backend/app/models/schema.py |  |
| field | `field:EngineModel.attributeTypes` | backend/app/models/schema.py |  |
| field | `field:EngineModel.objectTypes` | backend/app/models/schema.py |  |
| field | `field:EngineModel.relationTypes` | backend/app/models/schema.py |  |
| field | `field:EngineModel.objectTypeRelations` | backend/app/models/schema.py |  |
| field | `field:EngineModel.applications` | backend/app/models/schema.py |  |
| field | `field:EngineModel.consumerApis` | backend/app/models/schema.py |  |
| field | `field:EventSpec.key` | backend/app/models/schema.py |  |
| field | `field:EventSpec.objectTypes` | backend/app/models/schema.py |  |
| field | `field:EventSpec.changes` | backend/app/models/schema.py |  |
| field | `field:EventSpec.watch` | backend/app/models/schema.py |  |
| field | `field:EventWatch.fields` | backend/app/models/schema.py |  |
| field | `field:EventWatch.related` | backend/app/models/schema.py |  |
| field | `field:EventsOperation.description` | backend/app/models/schema.py |  |
| field | `field:EventsOperation.perType` | backend/app/models/schema.py |  |
| field | `field:EventsOperation.custom` | backend/app/models/schema.py |  |
| field | `field:FieldSpec.description` | backend/app/models/schema.py |  |
| field | `field:FieldSpec.from` | backend/app/models/schema.py |  |
| field | `field:FieldSpec.default` | backend/app/models/schema.py |  |
| field | `field:FieldSpec.role` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.description` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.byType` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.under` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.linkedTo` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.through` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.onRelated` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.matchOn` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.keepOnlyMatching` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.scoreOnlyMatching` | backend/app/models/schema.py |  |
| field | `field:FilterSpec.crosswalk` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelConfig.showParent` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelConfig.showAncestors` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.key` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.title` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.region` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.order` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.visible` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.type` | backend/app/models/schema.py |  |
| field | `field:HierarchyPanelDefinition.config` | backend/app/models/schema.py |  |
| field | `field:ListSpec.description` | backend/app/models/schema.py |  |
| field | `field:ListSpec.of` | backend/app/models/schema.py |  |
| field | `field:ListSpec.within` | backend/app/models/schema.py |  |
| field | `field:ListSpec.sortBy` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.relationTypeKey` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.fromObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.toObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.direction` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.sourceColumns` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.targetDisplayColumns` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.candidateSearchFields` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewConfig.pageSize` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewDefinition.key` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewDefinition.name` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewDefinition.type` | backend/app/models/schema.py |  |
| field | `field:MappingGridViewDefinition.config` | backend/app/models/schema.py |  |
| field | `field:ModelReleaseDefinition.key` | backend/app/models/schema.py |  |
| field | `field:ModelReleaseDefinition.name` | backend/app/models/schema.py |  |
| field | `field:ModelReleaseDefinition.version` | backend/app/models/schema.py |  |
| field | `field:NavigationDefinition.groups` | backend/app/models/schema.py |  |
| field | `field:NavigationGroupDefinition.key` | backend/app/models/schema.py |  |
| field | `field:NavigationGroupDefinition.label` | backend/app/models/schema.py |  |
| field | `field:NavigationGroupDefinition.collections` | backend/app/models/schema.py |  |
| field | `field:NavigationGroupDefinition.collapsed` | backend/app/models/schema.py |  |
| field | `field:ObjectSpec.fields` | backend/app/models/schema.py |  |
| field | `field:ObjectSpec.parent` | backend/app/models/schema.py |  |
| field | `field:ObjectSpec.path` | backend/app/models/schema.py |  |
| field | `field:ObjectSpec.hierarchy` | backend/app/models/schema.py |  |
| field | `field:ObjectSpec.related` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeAttributeDefinition.attributeTypeKey` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeAttributeDefinition.required` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeAttributeDefinition.readOnly` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeAttributeDefinition.order` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeAttributeDefinition.ui` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.key` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.name` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.pluralName` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.description` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.icon` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.displayAttributeTypeKey` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.attributes` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.features` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.behavior` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.validation` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeDefinition.effectivePeriod` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeParameter.kind` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.relationTypeKey` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.fromObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.toObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.cardinality` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.required` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.attributeTypeKeys` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.features` | backend/app/models/schema.py |  |
| field | `field:ObjectTypeRelationDefinition.candidates` | backend/app/models/schema.py |  |
| field | `field:Operation.description` | backend/app/models/schema.py |  |
| field | `field:Operations.objects` | backend/app/models/schema.py |  |
| field | `field:Operations.xref` | backend/app/models/schema.py |  |
| field | `field:Operations.resolve` | backend/app/models/schema.py |  |
| field | `field:Operations.lists` | backend/app/models/schema.py |  |
| field | `field:Operations.events` | backend/app/models/schema.py |  |
| field | `field:PanelDefinitionBase.key` | backend/app/models/schema.py |  |
| field | `field:PanelDefinitionBase.title` | backend/app/models/schema.py |  |
| field | `field:PanelDefinitionBase.region` | backend/app/models/schema.py |  |
| field | `field:PanelDefinitionBase.order` | backend/app/models/schema.py |  |
| field | `field:PanelDefinitionBase.visible` | backend/app/models/schema.py |  |
| field | `field:ParentSpec.output` | backend/app/models/schema.py |  |
| field | `field:ParentSpec.fields` | backend/app/models/schema.py |  |
| field | `field:ProductDefinition.name` | backend/app/models/schema.py |  |
| field | `field:ProductDefinition.description` | backend/app/models/schema.py |  |
| field | `field:ProjectionParameter.kind` | backend/app/models/schema.py |  |
| field | `field:ProjectionParameter.projection` | backend/app/models/schema.py |  |
| field | `field:ProjectionParameter.matchFields` | backend/app/models/schema.py |  |
| field | `field:ProjectionParameter.scoresFrom` | backend/app/models/schema.py |  |
| field | `field:ProjectionParameter.requireMatch` | backend/app/models/schema.py |  |
| field | `field:ProjectionParameter.targetable` | backend/app/models/schema.py |  |
| field | `field:RelatedParameter.kind` | backend/app/models/schema.py |  |
| field | `field:RelatedParameter.objectTypes` | backend/app/models/schema.py |  |
| field | `field:RelatedParameter.matchFields` | backend/app/models/schema.py |  |
| field | `field:RelatedParameter.via` | backend/app/models/schema.py |  |
| field | `field:RelatedSpec.description` | backend/app/models/schema.py |  |
| field | `field:RelatedSpec.via` | backend/app/models/schema.py |  |
| field | `field:RelatedSpec.fields` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.relationTypeKey` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.direction` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.rowObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.columnObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.cellObjectTypeKey` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.rowColumns` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.columnLabelField` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.cellFields` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.searchFields` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.cellActions` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewConfig.pageSize` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewDefinition.key` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewDefinition.name` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewDefinition.type` | backend/app/models/schema.py |  |
| field | `field:RelationMatrixViewDefinition.config` | backend/app/models/schema.py |  |
| field | `field:RelationTypeDefinition.key` | backend/app/models/schema.py |  |
| field | `field:RelationTypeDefinition.reverseKey` | backend/app/models/schema.py |  |
| field | `field:RelationTypeDefinition.name` | backend/app/models/schema.py |  |
| field | `field:RelationTypeDefinition.reverseName` | backend/app/models/schema.py |  |
| field | `field:RelationTypeDefinition.isOriented` | backend/app/models/schema.py |  |
| field | `field:RelationTypeDefinition.features` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelConfig.relationTypeKeys` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelConfig.direction` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelConfig.columns` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelConfig.showRelationshipColumn` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelConfig.sortFields` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelConfig.defaultSort` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.key` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.title` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.region` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.order` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.visible` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.type` | backend/app/models/schema.py |  |
| field | `field:RelationsPanelDefinition.config` | backend/app/models/schema.py |  |
| field | `field:TablePanelConfig.objectTypeKey` | backend/app/models/schema.py |  |
| field | `field:TablePanelConfig.columns` | backend/app/models/schema.py |  |
| field | `field:TablePanelConfig.filterByParent` | backend/app/models/schema.py |  |
| field | `field:TablePanelConfig.pageSize` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.key` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.title` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.region` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.order` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.visible` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.type` | backend/app/models/schema.py |  |
| field | `field:TablePanelDefinition.config` | backend/app/models/schema.py |  |
| field | `field:TableViewConfig.columns` | backend/app/models/schema.py |  |
| field | `field:TableViewConfig.filterFields` | backend/app/models/schema.py |  |
| field | `field:TableViewConfig.sortFields` | backend/app/models/schema.py |  |
| field | `field:TableViewConfig.defaultSort` | backend/app/models/schema.py |  |
| field | `field:TableViewConfig.pageSize` | backend/app/models/schema.py |  |
| field | `field:TableViewDefinition.key` | backend/app/models/schema.py |  |
| field | `field:TableViewDefinition.name` | backend/app/models/schema.py |  |
| field | `field:TableViewDefinition.type` | backend/app/models/schema.py |  |
| field | `field:TableViewDefinition.objectTypeKey` | backend/app/models/schema.py |  |
| field | `field:TableViewDefinition.config` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.rootObjectTypeKeys` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.objectTypeKeys` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.labelField` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.secondaryField` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.childSort` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.pageSize` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.actions` | backend/app/models/schema.py |  |
| field | `field:TreeViewConfig.availabilityField` | backend/app/models/schema.py |  |
| field | `field:TreeViewDefinition.key` | backend/app/models/schema.py |  |
| field | `field:TreeViewDefinition.name` | backend/app/models/schema.py |  |
| field | `field:TreeViewDefinition.type` | backend/app/models/schema.py |  |
| field | `field:TreeViewDefinition.config` | backend/app/models/schema.py |  |
| field | `field:Within.filter` | backend/app/models/schema.py |  |
| field | `field:Within.types` | backend/app/models/schema.py |  |
| field | `field:XrefOperation.description` | backend/app/models/schema.py |  |
| field | `field:XrefOperation.matchOn` | backend/app/models/schema.py |  |
| field | `field:XrefOperation.alsoMatchThrough` | backend/app/models/schema.py |  |
| field | `field:_Described.description` | backend/app/models/schema.py |  |
