# ai

A question, a model change or a workbook becomes words and proposals a person decides on; none writes live data. The operator sets the provider and a send level, the ceiling on what leaves the instance; a request may lower it with `sendLevel`. A provider is sent:

- `structure`: model labels and types, a list's fields, counts, the question. No record name or value.
- `samples`: also the record names a question may choose among, when the list holds at most 50.
- `values`: also names of records, people and files in an account of changes, and what a mapping proposal chooses among. The assistant needs it: it is sent the workbook.

1. Check: `GET /api/v1/ai/status`, `POST /api/v1/ai/test`.
2. Give work: `POST /api/v1/ai/tasks`, follow it to `checked`, then `POST .../accept`.

## GET /api/v1/ai/calls

Title: List the calls to the provider

Lists every call made to the provider and every turn of an assistant session, newest first: who asked, for what, how much went each way and how it ended. Use it to audit what left the instance. `content` holds the request and the answer only while the operator keeps them.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/ai/status

Title: Read how the provider is set up

Reads the provider as the environment set it at start, which features it offers at the send level, the last call and the totals of the last 30 days. Check it before a client offers an AI action. The key is never answered, only whether one is set. With the assistant in a container, `assistantNetwork` says whether its session's network is `restricted`, `unrestricted` or `failed` (assistant turns do not start), with the reason in `assistantNetworkNote`.

### Errors

- 403 FORBIDDEN: needs Operations at the instance

## POST /api/v1/ai/test

Title: Test the provider

Sends the provider a fixed request that holds no data and answers the call it made. Use it after the provider's settings change. A provider that cannot be reached or refuses the key is not an error: the answer is `200` with `outcome` `failed` and the reason in `failureKind` and `failure`. It is recorded like any call.

### Errors

- 403 FORBIDDEN: needs Operations at the instance
- 409 AI_NOT_CONFIGURED: no provider is set

## POST /api/v1/workspaces/{workspace_key}/query-translations

Title: Turn a question into filters

Turns a question in words into the filters of a table view. It only answers: apply `filters` and `search` yourself, and only when `applied` is true. A record named in words is found by the engine in the database, in the context asked about, and comes back as its ID. A provider that fails or answers unusably is `502`, with nothing to apply.

### Parameters

- workspace_key: The workspace of the list.

### Errors

- 403 FORBIDDEN: needs Browse and Use AI proposals in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 404 VIEW_NOT_FOUND: the application has no such view
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 AI_NOT_CONFIGURED: no provider is set
- 409 AI_SEND_LEVEL_TOO_LOW: `sendLevel` is above the ceiling or the feature needs more
- 422 REQUEST_VALIDATION_ERROR: a field is invalid, or both contexts are named
- 422 QUERY_TRANSLATION_VIEW_UNSUPPORTED: the view is not a table view
- 422 WORKSPACE_CONTEXT_MISMATCH: the change set or publication is another workspace's
- 502 QUERY_TRANSLATION_FAILED: the provider failed or its answer does not fit the list; `details.callId`

## POST /api/v1/model-releases/{release_id}/impact-summary

Title: Describe what activating a release does

Words for what activating a release in `workspaceKey` would do, compared with the release it runs. The engine writes the facts and the provider is sent only them, no record; it words them. A provider that fails is not an error: `200` with `failure` and every fact. The same request within an hour is answered from the cache, with no call.

### Parameters

- release_id: The release to describe.

### Errors

- 403 FORBIDDEN: needs Activate model releases and Use AI proposals in `workspaceKey`
- 404 MODEL_RELEASE_NOT_FOUND: no release has this ID
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 409 AI_NOT_CONFIGURED: no provider is set
- 409 AI_SEND_LEVEL_TOO_LOW: `sendLevel` is above the ceiling or the feature needs more
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/model-drafts/{draft_id}/impact-summary

Title: Describe what activating a draft does

The same for a model draft, compared with the release it is based on, before the draft is installed. `expectedVersion` claims the draft's version, so the account is of what you read. An invalid draft has no change to describe.

### Parameters

- draft_id: The draft to describe.

### Errors

- 403 FORBIDDEN: needs Activate model releases and Use AI proposals in `workspaceKey`
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 409 VERSION_CONFLICT: `expectedVersion` is not the draft's version
- 409 AI_NOT_CONFIGURED: no provider is set
- 409 AI_SEND_LEVEL_TOO_LOW: `sendLevel` is above the ceiling or the feature needs more
- 422 REQUEST_VALIDATION_ERROR: a field is invalid
- 422 IMPACT_SUMMARY_DRAFT_INVALID: the draft does not compile

## POST /api/v1/workspaces/{workspace_key}/history/account

Title: Describe what changed in a workspace

Words for what changed in a workspace over `[since, until)`. The engine counts the live changes in the database and the provider only words the counts; names reach it at send level `values` alone. Work in an open change set shows only as that set's events. A period with no change makes no call. The same request within an hour is answered from the cache.

### Parameters

- workspace_key: The workspace to describe.

### Errors

- 403 FORBIDDEN: needs Browse and Use AI proposals in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 409 AI_NOT_CONFIGURED: no provider is set
- 409 AI_SEND_LEVEL_TOO_LOW: `sendLevel` is above the ceiling or the feature needs more
- 422 REQUEST_VALIDATION_ERROR: a field is invalid
- 422 HISTORY_PERIOD_INVALID: the period is empty or reversed, or the time zone is unknown

## POST /api/v1/objects/{object_type_key}/{object_id}/history/account

Title: Describe what changed in a record

The same for one record's live changes: its values, relationships, moves and where they came from, and no other record's. It needs Browse and Use AI proposals in the record's workspace.

### Parameters

- object_type_key: The record's type.
- object_id: The record's ID.

### Errors

- 403 FORBIDDEN: needs Browse and Use AI proposals in the record's workspace
- 404 OBJECT_NOT_FOUND: no such record
- 409 AI_NOT_CONFIGURED: no provider is set
- 409 AI_SEND_LEVEL_TOO_LOW: `sendLevel` is above the ceiling or the feature needs more
- 422 REQUEST_VALIDATION_ERROR: a field is invalid
- 422 HISTORY_PERIOD_INVALID: the period is empty or reversed, or the time zone is unknown

## GET /api/v1/ai/tasks

Title: List assistant tasks

Lists the caller's assistant tasks and those of the workspaces they administer, newest first. Read a task to follow it.

### Parameters

- pageSize: 1 to 500; 50 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/ai/tasks

Title: Give the assistant work

Gives the assistant a workbook or an instruction in words, and the workspace it applies to. Send a `multipart/form-data` body: the `request` part as JSON and, optionally, `file` (XLSX or CSV). Answers `202` with the task, `reading`; nothing in the workspace changes. Without a file the words are the instruction. It needs send level `values`.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 AI_NOT_CONFIGURED: no assistant command is set
- 409 AI_SEND_LEVEL_TOO_LOW: the level is below `values` or above the ceiling
- 413 IMPORT_TOO_LARGE: the file is over the import limit
- 422 UNSUPPORTED_FILE_FORMAT: the file is not XLSX or CSV
- 422 AI_TASK_NEEDS_WORDS: neither a file nor words
- 422 REQUEST_VALIDATION_ERROR: the `request` part is invalid

## GET /api/v1/ai/tasks/{task_id}

Title: Get an assistant task

Reads a task: its `state`, what the engine read of the workbook, the assistant's proposal with its questions, the latest check and, once loaded, the change set. Poll it while `state` is `reading`, `checking` or `loading`. A task is visible to its requester and to those who administer its workspace.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it

## GET /api/v1/ai/tasks/{task_id}/changes

Title: List the records a check would change

Lists the records the latest check would change in one sheet, each with the fields that differ, what it holds now and what it would hold. Give `source` as the sheet's `source` in `check.sheets`. A task that has not been checked has none.

### Parameters

- task_id: The task's ID.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 AI_TASK_STATE: the task has no check yet
- 422 AI_TASK_TABLE_UNKNOWN: the check has no figures for `source`
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/ai/tasks/{task_id}/answers

Title: Answer the assistant's questions

Answers the questions of a proposal, by the question's text. The assistant designs again with the answers and the design is checked again. When every answer is the option the proposal assumed, nothing runs: the answers are recorded and the task stays `checked` with a new `version`. Allowed when the task is `checked`.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 VERSION_CONFLICT: `expectedVersion` is not the task's version
- 409 AI_TASK_STATE: the task is not `checked`
- 409 AI_NOT_CONFIGURED: no assistant command is set
- 409 AI_SEND_LEVEL_TOO_LOW: the level in force is below `values`
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/ai/tasks/{task_id}/model

Title: Tell the assistant something

Gives the assistant the person's words, which win over its own choices; it proposes again. Allowed when the task is `checked`, `failed` or `stopped`, and when it is `loaded` with a change set not yet published: that change set is discarded, which needs Work in change sets, and the session loads again.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Use AI proposals; Work in change sets if loaded
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 VERSION_CONFLICT: `expectedVersion` is not the task's version
- 409 AI_TASK_STATE: the task cannot take words now, or its session has ended
- 409 AI_NOT_CONFIGURED: no assistant command is set
- 409 AI_SEND_LEVEL_TOO_LOW: the level in force is below `values`
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/ai/tasks/{task_id}/accept

Title: Accept the proposal

Accepts the proposal. The assistant maps the sheets onto the proposed model, or makes the change in a new change set, and every row is checked; the task then waits for you again, or is `loaded`. It never activates a model or publishes: you do that from the change set. A proposal that moves whole types loads no change set and needs no Work in change sets.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Use AI proposals and Work in change sets
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 VERSION_CONFLICT: `expectedVersion` is not the task's version
- 409 AI_TASK_STATE: the task has no valid proposal to accept
- 409 AI_NOT_CONFIGURED: no assistant command is set
- 409 AI_SEND_LEVEL_TOO_LOW: the level in force is below `values`
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/ai/tasks/{task_id}/proposal

Title: Go back to the proposal

Goes back from a saved layout's load stage to the proposal it came from, for example to correct it in words. No job runs. It applies only to a task the saved layout read, with no assistant session.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 VERSION_CONFLICT: `expectedVersion` is not the task's version
- 409 AI_TASK_STATE: the task has no load stage to go back from
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/ai/tasks/{task_id}/retry

Title: Go on with a task that stopped

Goes on with a task that failed or stopped, from where its session was and with the person's `words` if there are some. A saved layout that does not fit, or a task whose session never ran, is read with the assistant.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 VERSION_CONFLICT: `expectedVersion` is not the task's version
- 409 AI_TASK_STATE: the task did not fail or stop, or already has a session
- 409 AI_NOT_CONFIGURED: no assistant command is set
- 409 AI_SEND_LEVEL_TOO_LOW: the level in force is below `values`
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/ai/tasks/{task_id}/run

Title: Load a saved layout's plan

Loads the checked plan of a task the saved layout read into a new change set, named after the file unless `changeSetName` says otherwise; live data is unchanged. A draft that changes the model is installed and activated first, which needs Model release rights. `saveProfile` keeps the plan as an import profile. A task the assistant designed is loaded by `accept`.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Work in change sets; model release rights for a model change
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 VERSION_CONFLICT: `expectedVersion` is not the task's version
- 409 AI_TASK_STATE: the task is not `checked`
- 409 AI_TASK_NOTHING_TO_LOAD: the task holds no design to load
- 409 AI_TASK_CHECK_STALE: the draft changed after its check
- 409 IMPORT_PROFILE_EXISTS: `saveProfile.key` is already a profile
- 409 AI_NOT_CONFIGURED: no assistant command is set
- 409 AI_SEND_LEVEL_TOO_LOW: the level in force is below `values`
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/ai/tasks/{task_id}/cancel

Title: Stop what the assistant is doing

Asks the job the task waits for (its reading, check, turn or load) to stop. The turn ends, not the task: it returns to its last proposal, or is `stopped` when it has none, and a load's change set is discarded.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Bulk and import and Use AI proposals in the workspace
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 AI_TASK_STATE: nothing is running for the task

## POST /api/v1/ai/tasks/{task_id}/discard

Title: Discard a task

Ends the task: it becomes `cancelled` and its draft and working folder go. A loaded task's change set is discarded with it, which needs Work in change sets; nothing else is undone. Allowed when the task waits for the person, failed, stopped, or is loaded and not published.

### Parameters

- task_id: The task's ID.

### Errors

- 403 FORBIDDEN: needs Use AI proposals; Work in change sets if loaded
- 404 AI_TASK_NOT_FOUND: no task has this ID, or the caller may not see it
- 409 AI_TASK_STATE: the task cannot be discarded now

## Schemas

### AiStatusResponse

- configured: True when a provider is set (`AI_PROVIDER`).
- assistant: True when the assistant's session can run (`AI_AGENT_COMMAND`); it needs no provider.
- assistantNetwork: With the assistant in a container: `restricted` (its session reaches only this engine and the provider's hosts), `unrestricted` (no `NET_ADMIN` in the container: it can reach any host) or `failed` (the rule could not be set: assistant turns do not start). Null without the assistant or outside a container.
- assistantNetworkNote: Why the network is `unrestricted` or `failed`, or null.
- provider: The provider's name, or null.
- model: The model asked for, or null.
- endpoint: `AI_BASE_URL`, or null for the provider's own address.
- keySet: Whether a key is set. The key itself is never answered.
- sendLevel: The ceiling on what leaves the instance: `structure`, `samples` or `values`.
- sampleValues: The most values of a column a feature may send at `samples`.
- minConfidence: The lowest confidence, 0 to 1, at which a mapping proposal is kept.
- logContent: Whether a call's request and answer are kept.
- logContentDays: How many days a kept request and answer stay.
- timeoutSeconds: How long a call waits for the provider.
- features: Each feature that asks the provider.
- lastCall: The most recent call, or null.
- totals: The calls of the last `totals.days` days.

### AiFeature

- purpose: What the feature is: `mappingTarget`, `queryTranslation`, `impactSummary` or `historyAccount`.
- name: The feature in words.
- needs: The least send level it works at.
- available: True when a provider is set and the send level reaches `needs`.

### AiTotals

- days: The days counted, 30.
- calls: Calls made.
- failed: Calls that failed.
- tokensIn: Tokens sent, as the provider reported them.
- tokensOut: Tokens answered.
- bytesIn: Bytes sent.
- bytesOut: Bytes answered.
- costUsd: The cost the assistant's sessions reported, in US dollars; a provider call reports none.

### AiCallResponse

One call to the provider: who asked, for what, of which provider and model, how much went each way and how it ended. `content` holds the request and answer only while `AI_LOG_CONTENT` keeps them.

- id: The call's ID.
- purpose: What it was for: `connectionTest`, `mappingTarget`, `queryTranslation`, `impactSummary`, `historyAccount`, `workbookLoad`, `assistantSession`, or `modelNames` on calls recorded before that feature was removed.
- provider: The provider that answered.
- model: The model, as the provider named it.
- sendLevel: The send level in force for this call.
- promptVersion: The version of the instructions sent.
- requestedBy: The person or client who asked.
- jobId: The job the call belongs to, or null.
- startedAt: When the call began.
- durationMs: How long it took, in milliseconds.
- bytesIn: Bytes sent. For a session turn, the prompt only.
- bytesOut: Bytes answered. For a session turn, the final answer only.
- tokensIn: Tokens sent, or null when none were reported.
- tokensOut: Tokens answered, or null.
- outcome: `answered` or `failed`.
- failureKind: Why it failed: `unreachable`, `unauthorized`, `rateLimited`, `declined`, `malformed`, `failed`, `timeout`, `cancelled` or `interrupted`; null when it was answered.
- failure: The reason in a sentence, or null.

### AiTaskRequest

The `request` part of `POST /api/v1/ai/tasks`: the workspace the workbook goes into, the person's words and a send level lower than the instance's ceiling.

- workspaceKey: The workspace the work applies to.
- words: What the assistant should do, in up to 4,000 characters. Required without a file.
- sendLevel: A send level below the instance's ceiling for this task. The assistant needs `values`.

### AiTaskAcceptRequest

The steward accepts the proposed model.

- expectedVersion: The task's `version`.

### AiTaskAnswersRequest

The person's answers to the design's questions, by the question's text.

- expectedVersion: The task's `version`.
- answers: The answers by question: the question's `text` as the key, the chosen option or your own words as the value.

### AiTaskCorrectionRequest

The steward's correction of the proposed model, in words.

- expectedVersion: The task's `version`.
- correction: What to change, in words, up to 2,000 characters.

### AiTaskRetryRequest

Go on with a task, with the person's words when there are some.

- expectedVersion: The task's `version`.
- words: What to tell the assistant as it goes on, up to 2,000 characters; without words it goes on from where it was.

### AiTaskRunRequest

- expectedVersion: The task's `version`.
- changeSetName: The new change set's name, up to 300 characters.
- saveProfile: Keep the plan as an import profile.

### AiTaskSaveProfile

- key: The profile's key: letters, digits, `_`, `.` and `-`, up to 160 characters.
- name: The profile's name, up to 200 characters.

### AiTaskResponse

- id: The task's ID.
- workspaceKey: The workspace the work applies to.
- fileName: The workbook's name; empty for a task given in words.
- sourceFileId: The stored workbook's ID; empty for a task given in words.
- words: What the person asked, as given.
- title: A short title the assistant wrote with its first answer; null until then.
- state: `reading`, `checking`, `checked` (a proposal waits for the person), `loading`, `loaded`, `failed`, `stopped` (stopped before any proposal) or `cancelled` (discarded). `read` is in the schema and no task reaches it.
- version: Moves with every change; a request names the version it read.
- jobId: The job the task waits for, or null.
- phase: While a job runs: `profiling`, `reading`, `designing` or `checking`; else null.
- createdAt: When the task was given.
- updatedAt: When it last changed.
- requestedBy: The person or client who gave it.
- reading: What the engine read of the workbook; null for a task given in words.
- check: The latest check of every row; null before one.
- design: The assistant's proposal; null until it has proposed.
- draftId: The task's draft of the workspace's model, which the model editor opens; null when the model does not change.
- notes: What the session said as it ended, and why a task failed.
- result: What the load made; null before it.
- canTell: Whether the person may tell the assistant something now, with `/model` or `/retry`.
- ahead: While the task's job waits for the assistant's worker, the jobs before it; null otherwise.

### TaskNote

- kind: `note`, `warning` or `refused`.
- text: The note.
- at: When it was made.

### TaskResult

- changeSetId: The change set the load made; absent when the task ended in a migration.
- changeSetName: Its name.
- changeSetReleaseId: The release the change set sits on.
- thenReleaseId: For a part-of-a-type reshaping, the final release the person activates after publishing.
- releaseId: The release a design's draft was installed as and activated in the workspace.
- migration: A task that moved whole types ends here instead of in a change set.
- importJobId: The job that imported the workbook or ran the items.
- profileKey: The import profile the load saved.
- profileNotSaved: Why the load saved no profile, in a sentence.
- counts: What the load wrote: `applied`, `created`, `updated`, `unchanged`, `rejected` and the like.
- published: True once the change set was published.
- publicationId: The publication it made.

### TaskMigration

A task that moved whole types ends here instead of in a change set: the release the session installed and the type mappings, as the migration at `POST /api/v1/workspaces/{workspace_key}/model/migrations` takes them.

- releaseId: The release the session installed.
- typeMappings: The type mappings, as `POST /api/v1/workspaces/{workspace_key}/model/migrations` takes them.
- relationTypeMappings: What the draft's steps imply for relation types.
- splits: The splits the draft's steps imply.
- listConversions: The list conversions the draft's steps imply.

### TaskReading

- tables: The tables of the workbook.
- sheets: The sheets that are no table.
- titles: Title blocks with no rows below them.
- profile: The stored import profile the reading follows, or null.
- summary: The figures of the reading.

### ReadingProfile

- key: The profile's key.
- name: Its name.
- version: Its version.

### ReadingSummary

- tables: Tables read.
- sheets: Sheets that are no table.
- updates: Tables read as updates of stored records.
- notLoaded: Tables that will not be loaded.
- needDecision: Tables that need a decision from the person.
- types: Record types the tables fill.
- applications: Applications those types are in.

### NotDataSheet

- sheet: The sheet's name.
- rows: Its rows.
- as: Always `notData`.
- reason: Why it is no table.

### TitleBlock

- sheet: The sheet it is on.
- range: Its cells.
- text: The title.

### TaskTable

- table: The table's number in the reading, `t1`, `t2`.
- sheet: The sheet it is on.
- range: Its cells, such as `A3:J54`.
- list: The index of the list on the sheet, when the sheet holds several.
- rows: Rows of data.
- as: `update` (rows name stored records), `newData` or `notData`.
- objectTypeKey: The record type it fills.
- applicationKey: The type's application.
- parentTypeKeys: The types its records can sit under.
- typeName: The type's name.
- reason: Why it was read this way.
- evidence: What the reading found, in a sentence.
- owner: Who decided: `rules`, `assistant`, `person` or `profile`.
- origin: Where the assistant's decision came from.
- profile: The stored profile it follows.
- keyColumn: The column that identifies the rows.
- key: What that column matches: an attribute type or the name.
- keyOptions: Other columns that could be the key, with how many values match.
- matched: Rows that match a stored record.
- new: Rows whose key no stored record has.
- missing: Stored records the file does not name.
- namesDiffer: Rows whose name differs from the stored one.
- meaning: Values matched to records by meaning.
- parent: The parent the rows sit under.
- notes: Remarks about the table.
- attention: What still needs the person: `newKeys`, `namesDiffer`, `missing`, `meaning`, `leftOutColumns`, `noParent` or `notLoaded`.
- leftOut: Columns the table does not read, with why.
- columns: Each column and what it fills.
- choices: The decisions about new records, names, missing records and whether to load.

### TableProfile

- key: The profile's key.
- name: Its name.
- version: Its version.
- source: The index of the profile source that reads the table.

### TaskColumn

- column: The column's letter.
- header: Its header.
- binding: What it fills.
- kind: The binding's kind: `field`, `attributeTypeKey`, `parent`, `relation`, `relationFlags`, `relatedRecord`, `ignore`, or `other` for a column read with another's binding.
- label: The binding in words.
- evidence: Why the column was bound so.
- leftOut: Why it is left out; null when it is read.
- known: True when the followed profile left it out of the file it read before too, so it needs no decision.
- owner: Who decided: `rules`, `assistant`, `person` or `profile`.
- origin: Where the assistant's decision came from.

### LeftOutColumn

- column: The column's letter.
- header: Its header.
- reason: Why it is left out.

### KeyOption

- column: The column's letter.
- header: Its header.
- key: What the column would match.
- matched: How many of its distinct values match a stored record.

### MeaningMatch

- value: The file's value.
- record: The record it was matched to.
- to: Its name.
- reason: Why it was matched.
- confidence: How sure, 0 to 1.
- origin: Where the match came from.

### Choice

- value: The decision, such as `create`, `leaveOut` or a boolean.
- owner: Who made it: `rules`, `assistant`, `person` or `profile`.

### TaskChoices

- newRecords: Whether rows with a new key become records.
- names: Whether the file's names or the stored ones are kept.
- missing: What happens to stored records the file does not name.
- load: Whether the table is loaded.

### TaskOrigin

Where an assistant's proposal came from.

- kind: Always `ai`.
- provider: The provider or session that decided.
- model: The model.
- promptVersion: The version of the instructions.
- confidence: How sure, 0 to 1.
- reason: Why, in a sentence.

### DesignCheck

- dryRunJobId: The dry run's job.
- ranAt: When it ran.
- sheets: Per sheet, what the rows would do.
- refused: What was refused, by code, with examples.
- summary: The totals: `created`, `updated`, `unchanged`, `refused`, `skipped` and, for items, `relationships`.
- rounds: How many times the check was made.
- draftChanged: True when the draft changed after this run, which then does not cover the model as it stands.
- mode: `items` for a dry run of items, which has no sheets; its summary is in `design.load`.

### DesignSheet

- source: The sheet's source in the dry run's profile; `GET /api/v1/ai/tasks/{task_id}/changes` takes it.
- sheet: The sheet's name.
- objectTypeKey: The type its rows fill.
- structure: True for a sheet that holds structure rather than records.
- rows: Rows read.
- created: Records it would create.
- updated: Records it would change.
- unchanged: Records already as the file says.
- refused: Rows refused.
- skipped: Rows with no key that wrote nothing.

### TaskDesign

The assistant's design: what the workbook is, the model-draft operations applied to the task's draft, the records the structure needs, the profile of the person's sheets, the questions with the option assumed, the person's answers and the engine's last outcome.

- summary: Two sentences the person reads.
- moves: Whole types the proposal turns into others, with the records and attributes each moves.
- removals: What the person's words explicitly ask to remove, with what each deletes.
- consumerChanges: The consumer APIs whose `contractVersion` the draft raises, from the engine's diff.
- operations: The model-draft operations applied to the task's draft.
- records: Records the structure needs that no row gives.
- profile: The profile of the person's sheets.
- questions: What only the person can decide.
- answers: The person's answers, by question.
- rounds: How many design rounds ran.
- origin: Where the proposal came from.
- outcome: The engine's last outcome: the operations applied and what the check found.
- leftOut: Columns no source loads, each with the assistant's reason.
- stage: `model` while the proposal waits; `load` once accepted.
- outline: The proposed model, one line per type, in words.
- checks: The engine's remarks on the proposal, each `{id, kind, text, open, explanation?}`.
- corrections: The person's corrections in words, the newest last.
- progress: While a session works: where it is and its milestones.
- agentSession: The session working on this task; null for a saved layout.
- modelUnchanged: True for a task whose model does not change: the proposal has no draft.
- load: For a load made from items, what the dry run of those items found.
- itemsLoad: True when accepting loads exactly the items in `load`.

### DesignQuestion

- text: The question.
- options: The options offered.
- assumed: The option the draft assumes.

### DesignRecord

- ref: A name the plan refers to it by.
- objectTypeKey: The record's type.
- applicationKey: The type's application.
- name: The record's name.
- attributes: Its attribute values by key.
- parent: Its parent.

### TaskChange

- recordId: The record's ID.
- name: Its name.
- table: The sheet it comes from.
- fields: The fields that differ.

### FieldChange

- field: The attribute's key, or `name`.
- label: The field in words.
- now: What the record holds now.
- after: What it would hold.

### ItemsDryRunSummary

What a dry run of items found: per type and relationship type what the items would do, the engine's findings, the refused items with their refs, and where in the file the items came from. Nothing was written.

- mode: Always `items`.
- jobId: The dry run's job.
- draftId: The draft it ran against.
- draftVersion: The draft's version it ran against.
- workspaceKey: The workspace.
- items: Items sent.
- figures: The totals.
- types: What the items do to each type's records.
- relationships: What they do to each relation type's relationships.
- sheets: Rows read per sheet.
- parts: Where in the file the items came from, up to 100.
- partsTotal: How many parts there are in all.
- findings: What the engine noticed, up to 100.
- refused: Refused items, up to 100.
- refusedByCode: Refused items counted by code.
- ranAt: When it ran.

### ItemsFigures

- recordsNew: Records the items would create.
- recordsMatched: Existing records they found.
- recordsChanged: Matched records they would change.
- recordsRemoved: Records they would remove.
- relationshipsNew: Relationships they would create, including each new record's link to its parent.
- parentLinksNew: Of those, the links to a parent.
- relationshipsMatched: Relationships already in place.
- refused: Items refused.
- rowsRead: Rows of the file the items came from.

### ItemsType

- objectTypeKey: The type.
- new: Records created.
- matched: Existing records found, then changed or unchanged.
- changed: Of those, records changed.
- removed: Records removed.
- refused: Items refused.
- linkedTo: The types its records are linked to.
- examples: Up to three items, with their values.

### ItemsExample

- index: The item's place in the items.
- ref: The cells it came from, such as `Sheet!Q31:S31`.
- objectTypeKey: The record's type.
- action: `created`, `updated`, `unchanged` or `refused`.
- name: The record's name.
- id: The record's ID, when it has one.
- values: Its values.
- links: Its relationships.
- error: Why it was refused; null otherwise.

### ItemsExampleValue

- attributeTypeKey: The attribute.
- value: The value.

### ItemsExampleLink

- relationTypeKey: The relation type.
- direction: `outgoing` or `incoming`.
- objectTypeKey: The other record's type.
- name: The other record's name.

### ItemsExampleError

- code: The refusal's code.
- message: The refusal in words.

### ItemsRelationship

- relationTypeKey: The relation type.
- new: Relationships created.
- matched: Relationships already in place.
- refused: Relationships refused.

### ItemsSheet

- sheet: The sheet's name.
- rows: Distinct rows the items came from.

### ItemsPart

- sheet: The sheet.
- firstColumn: The first column of the block.
- lastColumn: Its last column.
- firstRow: Its first row.
- lastRow: Its last row.
- objectTypeKey: The type the block's cells became records of; null for relationships.
- relationTypeKey: The relation type they became relationships of; null for records.
- items: Items from the block.

### ItemsFinding

- kind: `nameTwice`: a name that appears more than once in one type once the load is in.
- objectTypeKey: The type.
- name: The name.
- count: How many records carry it.
- parents: The parent of each, or null at the root.

### ItemsParent

- id: The parent's ID.
- name: Its name.
- objectTypeKey: Its type.

### ItemsRefusal

- index: The item's place in the items.
- ref: The cells it came from.
- key: The record's key, when it has one.
- code: Why it was refused.
- message: The refusal in words.

### ItemsRefusedCode

- code: The refusal's code.
- items: How many items it refused.

### DraftImpactSummaryRequest

- expectedVersion: The draft's `version`.
- language: A language tag for the words, such as `de`; English without one.
- sendLevel: A send level below the instance's ceiling for this request.
- workspaceKey: The workspace the draft would be activated in.

### ImpactSummaryRequest

Asks the AI provider for an account of what activating a release, or a draft, in a workspace does: the facts of the change, with the workspace's data checked against it, worded in `language` (a language tag; English without one). `sendLevel` is a level lower than the instance's ceiling.

- language: A language tag for the words, such as `de`; English without one.
- sendLevel: A send level below the instance's ceiling for this request.
- workspaceKey: The workspace the release would be activated in.

### ImpactSummaryResponse

The account of a model change. `facts` are every fact, whatever the provider did; `statements` word them, each citing `factIds` (a fact's ID, or `more-<kind>` for the facts of a kind the provider was not sent). A provider that fails or answers out of shape is not an error: `statements` is empty and `failure` says what failed. `removedStatements` counts those dropped for citing no fact that exists; `cached` is true when the same request was answered within the hour and no call was made; `callId` is the call that made the words.

- facts: Every fact the engine found, whatever the provider did.
- statements: The provider's words, each citing the facts it rests on.
- removedStatements: Statements dropped for citing no fact that exists.
- failure: What failed when the provider did; null otherwise.
- cached: True when the same request was answered within the hour and no call was made.
- callId: The call that made the words.

### ImpactFact

One fact of a model change, written by the engine from the diff, the check of the workspace's data, the consumer API check and a count of its records. `id` is stable: the same fact keeps it.

- id: A stable ID derived from the fact's kind, code and place; the same fact keeps it.
- kind: `change`, `data`, `contract`, `blocked` or `records`.
- text: The fact in words, from the model's labels.
- path: The model element's JSON pointer.
- count: How many, for a fact that counts.

### ImpactStatement

- text: One sentence.
- factIds: The facts it rests on; `more-<kind>` stands for facts the provider was not sent.

### HistoryAccountRequest

Asks the AI provider for an account of what changed over a period. `since` is included and `until` is not, as in `GET /api/v1/changes`. `timeZone` (an IANA name, UTC without one) says where a day begins. `sendLevel` is a level lower than the instance's ceiling; `language` is a language tag (English without one).

- since: Start of the period, included.
- until: End of the period, not included.
- timeZone: An IANA name that says where a day begins; UTC without one.
- sendLevel: A send level below the instance's ceiling for this request.
- language: A language tag for the words; English without one.

### HistoryAccountResponse

The account of what changed in a period. `facts` are every fact, whatever the provider did; `statements` word them, each citing `factIds` (a fact's ID, or `more-<kind>` for the facts of a kind the provider was not sent). Counts are of live data: work in an open change set appears only as that set's events. A provider that fails or answers out of shape is not an error: `statements` is empty and `failure` says what failed. A period with no change has no facts and makes no call. `removedStatements` counts those dropped for citing no fact that exists; `cached` is true when the same request was answered within the hour and no call was made.

- scope: `workspace` or `record`.
- since: Start of the period.
- until: End of the period.
- timeZone: The time zone used.
- facts: Every fact the engine counted, whatever the provider did.
- statements: The provider's words, each citing the facts it rests on.
- removedStatements: Statements dropped for citing no fact that exists.
- failure: What failed when the provider did; null otherwise.
- cached: True when the same request was answered within the hour and no call was made.
- callId: The call that made the words; null when none was made.

### HistoryFact

One fact of an account of history, counted by the engine over every live change of the period. `text` names records, people, change sets and files, as Activity does; `keys` says what the fact counts (its type, attribute, action, cause, people...); `link` is where the reader follows it, none when there is nowhere to follow (a job since removed).

- id: A stable ID derived from the fact's kind and keys.
- kind: `records`, `fields`, `relationships`, `source`, `people`, `changeSet`, `publication` or `model`.
- text: The fact in words, naming records, people, change sets and files.
- count: How many changes it counts.
- keys: What it counts: its type, attribute, action, cause or people.
- link: Where to follow it; null when there is nowhere, such as a job since removed.

### HistoryFactLink

- kind: `changes` (read `GET /api/v1/changes` with `query`), `history` (a record's history), `changeSet`, `job` or `publication`.
- id: The change set, job or publication.
- query: The filters that narrow the list to what the fact counted.

### QueryTranslationRequest

Asks the AI provider what filters a question in words means on a table view. `changeSetId` or `publicationId` reads the list in that context, otherwise it is live; `sendLevel` is a level lower than the instance's ceiling.

- applicationKey: The application of the view.
- viewKey: The table view.
- question: The question, 1 to 500 characters.
- changeSetId: Read the list in this change set; not with `publicationId`.
- publicationId: Read the list in this publication; not with `changeSetId`.
- sendLevel: A send level below the instance's ceiling for this request.

### QueryTranslationResponse

What a question became on a table view. `applied` is true when every part was expressed; otherwise the client applies nothing, and `filters` and `search` are what could be built, for the person to take or change.

- filters: The filters that could be built.
- search: Words for the name search; empty when none.
- notExpressed: The parts of the question the list cannot express.
- applied: True when every part was expressed. Otherwise apply nothing without the person's say.

### QueryTranslationFilter

- field: The list's field: an attribute key, `related:<relation type>`, or on a live list `createdAt` or `updatedAt`.
- operator: The condition, such as `eq`, `contains` or `under`.
- value: The value as text; a record named in words is its ID.

### QueryTranslationUnexpressed

- reason: Why the list cannot express it.

### AiCallPage

Calls to the provider, newest first.
