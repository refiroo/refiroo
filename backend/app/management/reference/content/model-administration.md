# model administration

A model draft is an editable copy of a model that no workspace runs yet. You use this area to change the model of a workspace: open its draft, change it in recorded steps, check what the result would do, install it as a release and run that release in the workspace. Steps can be undone and redone.

1. Change a model: `POST /api/v1/workspaces/{workspace_key}/model/draft`, send steps with `POST /api/v1/model-drafts/{draft_id}/operations`, then read `POST /api/v1/model-drafts/{draft_id}/compile`.
2. Run it: `POST /api/v1/model-drafts/{draft_id}/installation`, then `POST /api/v1/workspaces/{workspace_key}/model/activation`, or `POST /api/v1/workspaces/{workspace_key}/model/migrations` when the workspace's data has to change with the model.

## POST /api/v1/workspaces/{workspace_key}/model/activation

Title: Run a release in a workspace

Makes an installed release the model of one workspace, when the workspace's data already fits it; other workspaces keep their releases. If the data does not fit, migrate with `POST /api/v1/workspaces/{workspace_key}/model/migrations`. Open change sets stay on the release they were made under and are named in `changeSetsLeftBehind`. Webhook subscriptions the new release cannot serve are suspended. A release that changes what a consumer API's current version returns is refused unless it raises the `contractVersion` or the request sends `keepContractVersions: true`; the answer then lists the versions it kept in `keptContractVersions`.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Model release in this workspace
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 404 MODEL_RELEASE_NOT_FOUND: `releaseId` names no installed release
- 404 HTTP_ERROR: model administration is switched off
- 409 ACTIVATION_CONFLICT: the workspace's model changed since you read it
- 409 WORKSPACE_RETIRED: a retired workspace's model is not changed
- 409 MODEL_RELEASE_RETIRED: the release is retired
- 409 MODEL_MIGRATION_REQUIRED: the workspace's data does not fit the release
- 409 CONSUMER_CONTRACT_VERSION_REQUIRED: a consumer API changes without a higher `contractVersion` and no `keepContractVersions`
- 422 REQUEST_VALIDATION_ERROR: a field is missing or not a UUID
- 422 UNSUPPORTED_SCHEMA_VERSION: this engine cannot run the release's schema
- 500 INVALID_INSTALLED_MODEL: a stored release no longer compiles
- 503 MODEL_REGISTRY_REFRESH_FAILED: activated, but this process could not load it

## POST /api/v1/workspaces/{workspace_key}/model/draft

Title: Open a workspace's model draft

Gives the draft for the model a workspace runs, so you can change that model. It answers 200 with the draft the workspace already remembers, or with the newest draft of its release that no workspace holds, and 201 with a new draft made from the release's model. Apply the result with the draft's `installation`, then `activation` or `migrations`.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 404 HTTP_ERROR: model administration is switched off
- 409 WORKSPACE_RETIRED: a retired workspace's model is not changed

## POST /api/v1/workspaces/{workspace_key}/model/migrations

Title: Preview a workspace migration

Starts a migration of a workspace's data to another installed release and answers 202 with a queued job. The job previews every conversion, loss and refusal, changing nothing; read it with `GET /api/v1/jobs/{job_id}/rows`, then run it with `POST /api/v1/jobs/{job_id}/confirm`. With `changeSetId` the migration also publishes that change set, and the target is its release. `keepContractVersions: true` is accepted as on activation, and the migration records what it kept when it switches the release.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Model release here; with `changeSetId`, also Publish here
- 403 FORBIDDEN: `draftId` is not the session's draft
- 409 AI_TASK_DRAFT_HELD: `draftId` is a draft another task holds
- 404 WORKSPACE_NOT_FOUND: no workspace has this key
- 404 MODEL_RELEASE_NOT_FOUND: the target names no installed release
- 404 CHANGE_SET_NOT_FOUND: the change set is not one of this workspace
- 404 HTTP_ERROR: model administration or integration jobs are switched off
- 409 WORKSPACE_RETIRED: a retired workspace's model is not changed
- 409 MODEL_RELEASE_RETIRED: the target release is retired
- 409 ACTIVATION_CONFLICT: the workspace's model changed since you read it
- 409 CHANGE_SET_VERSION_CONFLICT: the change set changed since you read it
- 409 APPROVAL_REQUIRED: the workspace's policy requires an approval to publish
- 409 CONSUMER_CONTRACT_VERSION_REQUIRED: a consumer API changes without a higher `contractVersion` and no `keepContractVersions`
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or the target is missing
- 422 MIGRATION_TARGET_IS_CURRENT: the workspace runs the target already
- 422 MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE: the target is not the change set's release
- 422 INVALID_MIGRATION_MAPPING: a mapping names what the models lack; `details.pointer` says where
- 422 UNSUPPORTED_SCHEMA_VERSION: this engine cannot run the target's schema

## GET /api/v1/model-drafts

Title: List model drafts

Lists the drafts of the instance, most recently changed first. Each item holds the draft's whole model, so a page can be large; use `outline` for a draft's structure.

### Parameters

- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 HTTP_ERROR: model administration is switched off
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## POST /api/v1/model-drafts

Title: Create a model draft

Saves a model document as a new draft, to be changed with operations and installed as a release. Name `baseReleaseId` when the draft changes an installed model: its elements are then marked against that release and its migration is derived from it. The document need not be valid yet; `compile` says whether it is.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_RELEASE_NOT_FOUND: `baseReleaseId` names no installed release
- 404 HTTP_ERROR: model administration is switched off
- 422 REQUEST_VALIDATION_ERROR: the name or a field is invalid

## GET /api/v1/model-drafts/{draft_id}

Title: Get a model draft

Reads one draft with its whole model. Read it before changing or deleting it: it gives the `version` to send. Use `outline` for the structure an editor shows, and `model` for the compiled model.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off

## PATCH /api/v1/model-drafts/{draft_id}

Title: Rename a draft or replace its model

Renames a draft, replaces its whole model, or both. A replaced model is one step of the draft's history that can be undone; its import profile is kept. To change a part of the model, send operations instead: they are checked and recorded one by one.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 409 VERSION_CONFLICT: the draft changed since you read it
- 422 REQUEST_VALIDATION_ERROR: neither `name` nor `model` is sent, or a field is invalid

## DELETE /api/v1/model-drafts/{draft_id}

Title: Delete a model draft

Deletes a draft together with its history. A release installed from the draft is not affected, and an installed release is never deleted this way. Send the `version` you read, so a draft somebody just changed is not lost.

### Parameters

- draft_id: The draft's ID.
- expectedVersion: The draft's `version`.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 409 VERSION_CONFLICT: the draft changed since you read it
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or invalid

## POST /api/v1/model-drafts/{draft_id}/operations

Title: Change a draft with a step

Applies operations to the draft in the order sent, all or none, as one step of its history, when the draft is at `expectedVersion`. Each item's `kind` selects one of the operation schemas listed under the request body. The server writes `replaceModel` and `restoreElements` itself (a PATCH of the model; undo and redo), so they cannot be sent. An invalid draft is saved all the same: read `valid` and `diagnostics`. `dryRun` names the import check a step queued.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 403 FORBIDDEN: an assistant's session on a draft neither it nor its task holds
- 409 AI_TASK_DRAFT_HELD: an assistant's session using a draft another task holds
- 409 VERSION_CONFLICT: the draft changed; `details.operations` lists the entries since
- 413 OPERATION_BATCH_TOO_LARGE: more operations than one request may hold
- 422 INVALID_OPERATION: an item is refused; nothing is applied
- 422 REQUEST_VALIDATION_ERROR: `operations` is empty or not a list of objects

## GET /api/v1/model-drafts/{draft_id}/operations

Title: Read a draft's history

Lists the operations applied to the draft, oldest first. The entries of one step share `step`; an undone entry stays listed with `undone: true`. Use it to find the `step` to undo, or to see who changed what.

### Parameters

- draft_id: The draft's ID.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/model-drafts/{draft_id}/migration

Title: Read the migration a draft states

Derives from the steps that stand now what the draft changes in the data of its base release: which types, attributes and relation types became which, what splits and list conversions create, and which key changes consumer APIs still name. `typeMappings`, `relationTypeMappings`, `splits` and `listConversions` are what `POST /api/v1/workspaces/{workspace_key}/model/migrations` takes. With `workspaceKey` the answer also checks every record of that workspace (`landing`) and writes nothing.

### Parameters

- draft_id: The draft's ID.
- workspaceKey: A workspace to check the migration against; the caller needs Browse there.
- againstReleaseId: The release the migration starts from. Needed after the draft was installed, which bases it on the release it installed.
- toReleaseId: The release the migration goes to, usually the one installed from the draft.

### Errors

- 403 FORBIDDEN: needs Model authoring; with `workspaceKey`, also Browse there
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 MODEL_RELEASE_NOT_FOUND: a release ID names no installed release
- 404 HTTP_ERROR: model administration is switched off
- 422 UNSUPPORTED_SCHEMA_VERSION: this engine cannot read a release's schema

## GET /api/v1/model-drafts/{draft_id}/outline

Title: Read a draft's outline

Answers the draft's structure as an editor shows it: applications with their types, attributes, relation types, relations and consumer APIs, each marked `new`, `changed` or `released` against the base release, with the compiler's diagnostics. A draft that does not compile is outlined with what can be read.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off

## GET /api/v1/model-drafts/{draft_id}/model

Title: Preview a draft's compiled model

Compiles the draft as `GET /api/v1/model` serves a running model, with its placements, so a client can render it before it is installed. Nothing is written. While the draft does not compile, `model` and `placements` are left out; read `diagnostics`.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off

## GET /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}

Title: Read a draft's consumer API

Reads one consumer API definition as written in the draft and, when the draft compiles, with every default written out and its `contract` against the base release. Use it to see whether `contractVersion` must be raised before the draft is installed.

### Parameters

- draft_id: The draft's ID.
- consumer_api: The consumer API's key.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 CONSUMER_API_NOT_FOUND: the draft declares no consumer API with this key
- 404 HTTP_ERROR: model administration is switched off

## GET /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/schema.json

Title: Get a draft consumer API's message schema

Answers the JSON Schema (2020-12) of the object message that consumers of this definition will receive, written from the draft: the union of its types, told apart by `objectType`, or one type's schema with `objectType`. Each type's schema holds only the fields and related blocks that type holds. Use it to generate types or validate messages before the model is installed.

### Parameters

- draft_id: The draft's ID.
- consumer_api: The consumer API's key.
- objectType: The public name of one type the definition exposes. Without it the answer covers every type.

### Errors

- 400 UNKNOWN_OBJECT_TYPE: objectType names no type the definition exposes
- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 CONSUMER_API_NOT_FOUND: the draft declares no consumer API with this key
- 404 HTTP_ERROR: model administration is switched off
- 422 INVALID_MODEL: the draft does not compile

## GET /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/example.json

Title: Get a draft consumer API's example message

Answers one object message of one type, valid against the draft consumer API's schema and written from the schema alone: the values are placeholders and no record is read. Use it as a sample for people building a client.

### Parameters

- draft_id: The draft's ID.
- consumer_api: The consumer API's key.
- objectType: The public name of the type to show. Without it the first type the definition exposes.

### Errors

- 400 UNKNOWN_OBJECT_TYPE: objectType names no type the definition exposes
- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 CONSUMER_API_NOT_FOUND: the draft declares no consumer API with this key
- 404 HTTP_ERROR: model administration is switched off
- 422 INVALID_MODEL: the draft does not compile

## GET /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/openapi.json

Title: Get a draft consumer API's OpenAPI document

Answers the OpenAPI document of the consumer API as the consumer tier will serve it once the model runs, with this instance's addresses. Use it to build a client before the model is installed.

### Parameters

- draft_id: The draft's ID.
- consumer_api: The consumer API's key.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 CONSUMER_API_NOT_FOUND: the draft declares no consumer API with this key
- 404 HTTP_ERROR: model administration is switched off
- 422 INVALID_MODEL: the draft does not compile

## POST /api/v1/model-drafts/{draft_id}/undo

Title: Undo a step

Undoes the latest step that stands, the step named in `step`, or the `steps` together, as a new step of the history. A step that later steps depend on is refused unless those are undone with it. An undo can be redone while nothing else was applied after it.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 409 VERSION_CONFLICT: the draft changed since you read it
- 409 NOTHING_TO_UNDO: no step can be undone, or a named step cannot
- 409 OPERATION_HAS_DEPENDANTS: later steps depend on a named step
- 422 REQUEST_VALIDATION_ERROR: a field is invalid

## POST /api/v1/model-drafts/{draft_id}/redo

Title: Redo a step

Applies again the latest undo, as a new step of the history. It works only while no other step was applied after that undo; after a new change, make the change again.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 409 VERSION_CONFLICT: the draft changed since you read it
- 409 NOTHING_TO_REDO: no undone step can be redone

## GET /api/v1/model-drafts/{draft_id}/profile

Title: Read a draft's import profile

Reads the import profile the draft holds, the instance import profile it stands for, its warnings against the draft's model, and the source file it binds. Nothing is written. Change the profile with operations like the rest of the draft; installing the draft saves it as an instance profile.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off

## POST /api/v1/model-drafts/{draft_id}/compile

Title: Compile a draft

Checks whether the draft is a valid model and says what installing and activating it would do: its changes against the base release, whether each workspace's data would fit, and whether a consumer API needs a higher `contractVersion`. Nothing is installed. A draft that does not compile answers 200 with `valid: false`.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 409 VERSION_CONFLICT: the draft changed since you read it
- 422 UNSUPPORTED_SCHEMA_VERSION: the base release's schema cannot be read
- 500 INVALID_INSTALLED_MODEL: the base release no longer compiles

## POST /api/v1/model-drafts/{draft_id}/installation

Title: Install a draft as a release

Turns a valid draft into an installed model release that no workspace runs yet; run it with `model/activation` or `model/migrations`. It checks no workspace's data. Installing a release whose key, version and content are installed already answers 200 with that release, and a retired one becomes active again. The draft is then based on the release, and its import profile is saved as an instance profile.

### Parameters

- draft_id: The draft's ID.

### Errors

- 403 FORBIDDEN: needs Install a model, or Model release, where the draft was opened
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 409 VERSION_CONFLICT: the draft changed since you read it
- 409 RELEASE_IDENTITY_CONFLICT: the key and version are installed with other content
- 409 IMPORT_PROFILE_MODEL_MISMATCH: another model's profile holds the profile's key
- 422 INVALID_MODEL: the draft does not compile
- 422 UNSUPPORTED_SCHEMA_VERSION: the draft's schema version is not supported

## POST /api/v1/model-drafts/{draft_id}/dry-run

Title: Dry-run a draft against a file or items

Checks what loading would do under the draft's model, and writes nothing: a stored source file of the draft (`sourceFileId`) read with its profile, or batch `items` as `POST /api/v1/batches` takes them. Answers `202` with the dry run `checking`; follow it at `GET /api/v1/model-drafts/{draft_id}/dry-run`. A dry run still running for the draft is cancelled. Exactly one of `sourceFileId` and `items`.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring; `items` also need Browse in the workspace
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 SOURCE_FILE_NOT_FOUND: the draft does not own the file
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 SOURCE_FILE_PROFILE_NOT_READY: the file is not profiled yet
- 409 AI_TASK_STATE: an accepted assistant task is loading the draft's checked items
- 413 BATCH_TOO_LARGE: `items` are over the batch limits
- 422 REQUEST_VALIDATION_ERROR: both or neither of `sourceFileId` and `items`, or `profile` with `items`
- 422 INVALID_MODEL: the draft does not compile
- 422 INVALID_IMPORT_PROFILE: the profile does not fit the draft's model

## GET /api/v1/model-drafts/{draft_id}/dry-run

Title: Get a draft's latest dry run

Reads the draft's latest dry run. While it is `checking` poll again; when `completed`, `summary` (a file) or `items` (items) holds its figures for the whole set. A file's `summary.difference` compares it with the draft's previous completed dry run of that file. A step of the draft that can change what a load writes queues a new dry run, so read it after each such step.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 DRY_RUN_NOT_FOUND: the draft has no dry run yet

## GET /api/v1/model-drafts/{draft_id}/dry-run/rows

Title: List a dry run's rows

Lists the rows behind the latest dry run's figures, in source then row order, each with its status and refused outcomes. Filter by `source`, `status` or the refusal `code` to reach the rows a figure counts. Rows are a file's; a dry run of items reports its refused items in `items.refused`.

### Parameters

- draft_id: The model draft's ID.
- pageSize: 1 to 1,000; 500 by default.
- status: Only rows with this status.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 DRY_RUN_NOT_FOUND: the draft has no dry run yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/model-drafts/{draft_id}/inference

Title: Propose a model from the draft's file

Starts the job that reads the draft's current source file and proposes how to model and load it: a new application, or additions to the draft. Answers `202` with the inference `checking`. Nothing is applied: read the proposals at `.../inference/proposals`, then apply them with `.../inference/application`. An inference still running for the draft is cancelled.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 SOURCE_FILE_NOT_FOUND: the draft has no source file
- 409 SOURCE_FILE_PROFILE_NOT_READY: the file is not profiled yet
- 422 REQUEST_VALIDATION_ERROR: the body is malformed
- 422 INVALID_MODEL: the draft does not compile
- 422 INVALID_INFERENCE_REQUEST: `applicationKey` does not fit `mode`

## GET /api/v1/model-drafts/{draft_id}/inference

Title: Get a draft's latest inference

Reads the draft's latest inference: its state, its proposals counted by status, the columns the draft reads otherwise than the file's shape suggests, warnings, and the elements still as proposed. Poll while it is `checking`; the counts are zero until `completed`. A later inference replaces the proposals, keeping the IDs of those already applied.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 INFERENCE_NOT_FOUND: the draft has no inference yet

## GET /api/v1/model-drafts/{draft_id}/inference/proposals

Title: List an inference's proposals

Lists the proposals of the latest completed inference in the order they apply, each with the operations it would apply and its alternatives. Filter by `sheet` or `column` to see what concerns one part of the file. Read the status of each before applying: only `open` proposals apply.

### Parameters

- draft_id: The model draft's ID.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 INFERENCE_NOT_FOUND: the draft has no inference yet
- 409 INFERENCE_NOT_READY: the inference is still running, or failed
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/model-drafts/{draft_id}/inference/application

Title: Apply an inference's proposals

Applies proposals to the draft, each as one step of its history, all or none; every open proposal when `proposals` is left out. The draft must be unchanged since the inference. Answers like an operations step, with the draft's new `version`; the dry run it queued, when the steps change what a load writes, is in `dryRun`.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 INFERENCE_NOT_FOUND: the draft has no inference yet
- 404 PROPOSAL_NOT_FOUND: a listed proposal is not in the latest inference
- 409 INFERENCE_NOT_READY: the inference is still running, or failed
- 409 INFERENCE_STALE: the draft changed after the inference
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 409 NOTHING_TO_APPLY: no proposal is open
- 409 PROPOSAL_ALREADY_APPLIED: a listed proposal is applied already
- 413 OPERATION_BATCH_TOO_LARGE: a proposal holds more operations than a step may
- 422 REQUEST_VALIDATION_ERROR: the body is malformed
- 422 PROPOSAL_REQUIREMENT_MISSING: a proposal's required proposal is neither applied nor listed
- 422 INVALID_OPERATION: a proposal's operations do not apply; `details.step` names it

## GET /api/v1/model-drafts/{draft_id}/canvas

Title: Read a draft's canvas

Reads what the draft's board keeps: where each card sits by card key, which cards are folded and the chosen scope. They belong to the draft only: they are not part of its model, its version or its history, and no release holds them.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off

## PATCH /api/v1/model-drafts/{draft_id}/canvas

Title: Arrange a draft's canvas

Merges card positions and folded cards by key into the draft's canvas and replaces its scope; a part left out stays. A position places a card and `null` removes it; a folded key set `true` folds a card, `false` or `null` unfolds it; a scope of `model`, `changed` or `workbook` is chosen, `null` is the default. The draft's version does not change, so this never conflicts with an operations request and is not an undo step. At most 500 placed and 500 folded cards.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 HTTP_ERROR: model administration is switched off
- 422 INVALID_CANVAS: the canvas would hold more than 500 placed or folded cards
- 422 REQUEST_VALIDATION_ERROR: a position, a key, the scope or the body is malformed

## POST /api/v1/model-drafts/{draft_id}/join-candidates

Title: Find where a column joins

Compares one column of the draft's source file with the columns of another table over every row and answers the candidates, best first, with their figures. Nothing is stored. Values compare by their trimmed text, as an import matches names. When two candidates match exactly as much the answer is a `tie` with no `best`: ask which; nothing is guessed.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: no draft has this ID
- 404 SOURCE_FILE_NOT_FOUND: the draft has no source file
- 404 SOURCE_SHEET_NOT_FOUND: a sheet is not in the file
- 404 HTTP_ERROR: model administration is switched off
- 409 SOURCE_FILE_PROFILE_NOT_READY: the file is not profiled yet
- 422 COLUMN_NOT_FOUND: a header or letter is not in the table
- 422 INVALID_RANGE: a block's last column is before its first
- 422 REQUEST_VALIDATION_ERROR: a column is named by both header and letter

## POST /api/v1/model-drafts/{draft_id}/inference/list

Title: Read a rectangle as a list

Proposes how to load a rectangle of the draft's source file as a list, against the draft as it is now. The proposal is answered and not stored: send its `operations` to `POST /api/v1/model-drafts/{draft_id}/operations` as one step to adopt it. It needs no earlier inference.

### Parameters

- draft_id: The model draft's ID.

### Errors

- 403 FORBIDDEN: needs Model authoring
- 404 MODEL_DRAFT_NOT_FOUND: the draft does not exist
- 404 SOURCE_FILE_NOT_FOUND: the draft has no source file
- 404 SOURCE_SHEET_NOT_FOUND: `sheet` is not in the file
- 409 SOURCE_FILE_PROFILE_NOT_READY: the file is not profiled yet
- 422 REQUEST_VALIDATION_ERROR: the body is malformed
- 422 INVALID_RANGE: the rectangle is outside the sheet, or holds no list
- 422 INVALID_INFERENCE_REQUEST: `applicationKey` names an application the draft lacks

## Schemas

### WorkspaceModelActivation

- releaseId: The installed release to run.
- expectedVersion: The workspace's model `version`, from `GET /api/v1/workspaces/{workspace_key}/model`.
- expectedReleaseId: The release the workspace runs now, from the same read.
- keepContractVersions: Send `true` to accept the release although it changes what a consumer API's current contract version returns, keeping the version number. It covers every current version the release breaks and nothing else; a lowered `contractVersion` or a changed earlier version is refused still.

### WorkspaceModelActivationResponse

- workspaceKey: The workspace that now runs the release.
- releaseId: The release's ID.
- releaseKey: Shared by all releases of one model.
- releaseName: The model's name.
- releaseVersion: The release's version.
- schemaVersion: The model schema the release is written in.
- modelHash: Identifies the release's content.
- version: The assignment's own version, raised by this activation. The next activation sends it.
- updatedAt: When the workspace changed release.
- changeSetsLeftBehind: Open change sets of the workspace that stay pinned to the release it ran before.
- keptContractVersions: The consumer API versions kept through a breaking change by `keepContractVersions`; empty otherwise. The release's activations list the same.

### ChangeSetLeftBehind

An open change set of the workspace that is pinned to a release the workspace no longer runs.

- id: The change set's ID.
- name: The change set's name; `null` when it has none.
- version: The change set's `version`.

### WorkspaceMigrationRequest

A migration of the workspace's data to an installed release. Naming a change set of the workspace migrates to that change set's release and publishes the change set in the same transaction; `targetReleaseId` may then be left out, and if sent must be the change set's release.

- targetReleaseId: The installed release to migrate to. May be left out when `changeSetId` is sent, and then must be that change set's release.
- expectedVersion: The workspace's model `version`, from `GET /api/v1/workspaces/{workspace_key}/model`.
- typeMappings: What each type of the workspace's model became in the target, so its records keep their IDs. At most 500.
- relationTypeMappings: What each relation type became in the target. At most 500.
- splits: Types split in the target. At most 100.
- listConversions: Attributes turned into list types in the target. At most 100.
- changeSetId: A change set of the workspace to publish in the same transaction as the migration, which then moves the workspace to that change set's release.
- expectedChangeSetVersion: The change set's `version`; sent with `changeSetId`, and only with it.
- keepContractVersions: Send `true` to accept the target although it changes what a consumer API's current contract version returns, keeping the version number; the migration's switch records what was kept.

### MigrationRelationTypeMapping

- fromRelationTypeKey: A relation type of the workspace's release.
- toRelationTypeKey: The relation type it became in the target; its relationships keep their IDs.

### MigrationSplit

- fromObjectTypeKey: The type that was split.
- toObjectTypeKey: The new type in the target.
- attributes: Attributes of the old type whose values move to the new type's records. At least one, at most 500.
- relationTypeKey: The relation type that relates each record to its new record.
- cardinality: `many-to-one` makes records holding the same values share one new record; otherwise each record gets its own.

### MigrationListConversion

- fromObjectTypeKey: The type whose records hold the attribute.
- attributeTypeKey: The attribute turned into a list type.
- toObjectTypeKey: The list type in the target; each distinct value becomes a record of it.
- relationTypeKey: The relation type that relates each record to its value's record.

### ModelDraftCreate

- name: The draft's name, 1 to 300 characters.
- baseReleaseId: The installed release the draft changes; its elements are marked, and its migration derived, against it. Left out for a new model.
- model: The model document.

### ModelDraftUpdate

- expectedVersion: The draft's `version`.
- name: The new name, 1 to 300 characters.
- model: The whole model, replacing the draft's. At least one of `name` and `model` is sent.

### ModelDraftVersionRequest

- expectedVersion: The draft's `version`.

### ModelDraftResponse

- id: The draft's ID.
- name: The draft's name.
- baseReleaseId: The installed release its elements are compared with; `null` for a new model. Installing the draft sets it to the release installed.
- workspaceKey: The workspace the draft was opened for with `POST /api/v1/workspaces/{workspace_key}/model/draft`; `null` otherwise.
- model: The model document as it stands, valid or not.
- version: Raised by every change. Send it as `expectedVersion`.
- createdAt: When the draft was created.
- updatedAt: When the draft last changed.

### ModelDraftOperationsRequest

One step of a draft's history: operations applied in order, all or none.

- expectedVersion: The draft's `version`.
- operations: One or more operations, applied in order; each item's `kind` selects one of the schemas listed here. At most 500 unless the operator set another limit.

### ModelDraftUndoRequest

Undoes the latest step not yet undone, or the named `step`, or the `steps` together.

- expectedVersion: The draft's `version`.
- step: The step to undo. With neither `step` nor `steps`, the latest step that stands.
- steps: Several steps to undo together; used instead of `step`.

### ModelDraftOperationEntry

One operation in a draft's history.

- sequence: The entry's position in the draft's history, from 1, across all steps.
- step: The step the entry belongs to; the operations of one request share it.
- kind: The operation's kind. The server also writes `replaceModel` (a PATCH replacing the model) and `restoreElements` (the inverse of an undo and of the kinds that remove or restructure) here; a request cannot send them.
- parameters: The parameters the operation was applied with; for `replaceModel` the new `model`, for `restoreElements` what it puts back.
- inverse: The operation that takes it back; an undo applies the inverses. Usually `restoreElements` with the logged reversal, or `replaceModel` with the previous model.
- draftVersion: The draft's `version` the step produced.
- author: The person or client that applied it, as they are named now; `null` when none was recorded.
- at: When it was applied.
- undone: Whether an undo took the entry back.
- origin: What made the step. `type` is `request`, `patch` (a model replaced by PATCH), `undo` (with `steps`), `redo` (with `step`) or `proposal` (applied from an inference); `proposedBy`, `proposedByName` and `taskId` are present when an assistant made it.

### ModelDraftOperationMigration

- element: The released element, named by its keys as operations name it, for example `objectType`.
- keyChange: Whether the operation changed the element's key.

### ModelDraftStepResponse

The draft after a step: its version, the step's entries, the compiler's diagnostics, the draft profile's warnings and the dry run the step queued, or `null`.

- version: The draft's `version` after the step.
- entries: The history entries the step wrote, one per operation.
- valid: Whether the draft compiles now.
- diagnostics: The compiler's diagnostics for the model, then warnings about the draft's import profile.
- dryRun: The dry run the step queued, read with `GET /api/v1/model-drafts/{draft_id}/dry-run`; `null` when none was.

### DraftMigrationStep

- step: The step that needs a migration.
- sequence: The history entry that does.
- kind: That entry's operation kind.
- migration: The released elements the entry changed, with what holds each.

### DraftMigrationRow

- fromObjectTypeKey: The type in the base release.
- toObjectTypeKey: What it is now.
- fromName: Its name in the base release.
- toName: Its name now.
- fromApplicationKeys: The applications that listed it in the base release.
- toApplicationKeys: The applications that list it now.
- toApplicationKey: The application its records go to; `null` when they stay where they are.
- attributes: Where each attribute of the new type takes its values from, as `attributeTypeKey` and `from`.
- records: The records, values and relationships that hold the type: a count, exact up to 10,000, then a text such as `10000+`.

### DraftMigrationKeyChange

- element: The released element, named by its keys as operations name it.
- from: Its key in the base release.
- to: Its key now.
- consumerApis: The consumer APIs of the base release that name the old key, each with `key` and `name`. Integrations that use the old key must change with it.

### DraftMigrationLanding

- workspaceKey: The workspace checked.
- moved: Records the migration would move to another type or application.
- createdRecords: Records it would create, for splits and list conversions.
- createdRelationships: Relationships it would create.
- losses: What it would remove, per type: `objectTypeKey` with `records`, `values` and `relationships` counts.
- refused: What it would refuse, per type: `objectTypeKey`, `code`, `message`, `count` and `examples`.

### ModelDraftMigrationResponse

- baseReleaseId: The release the migration starts from.
- draftVersion: The draft's `version` the answer was derived from.
- required: Whether the draft changes anything a workspace's data needs a migration for.
- steps: The steps of the history that need a migration.
- typeMappings: What each changed type became, as `POST /api/v1/workspaces/{workspace_key}/model/migrations` takes them.
- relationTypeMappings: What each re-keyed relation type became.
- splits: The splits the history made.
- listConversions: The attributes the history turned into list types.
- rows: The type mappings described for reading: names, applications, parent change and record counts.
- keyChanges: The released elements whose key changed.
- notes: Things the derivation could not know, each with `code` and `message`; `MODEL_REPLACED` when a step replaced the whole model.
- landing: What the migration would do to the live records of `workspaceKey`; present only with it, and `null` when the draft does not compile or the workspace's model does not fit the mappings.

### DraftProfileSourceFile

- id: The source file's ID.
- name: The file's name.
- profile: Where the file's reading stands: `completed`, or the state of its job (`queued`, `running`, `failed`, `cancelled`).

### ModelDraftProfileResponse

The import profile the draft holds, which reads the draft's source file.

- version: The draft's `version`.
- profile: The profile as the draft holds it; `null` when it has none.
- definition: The instance import profile it stands for; `null` when it cannot stand for one yet.
- valid: Whether the profile holds against the draft's model, so an import could use it.
- diagnostics: Warnings about the profile. Reminders such as an unmapped column do not make it invalid.
- freeKey: A key no stored profile holds, when another model's profile holds this profile's key; set the profile's key to it.
- sourceFile: The source file the profile binds, which a dry run reads; `null` when none is.

### ModelDraftOutlineResponse

A draft's structure as the editor shows it, each element marked against the base release.

- version: The draft's `version`.
- baseReleaseId: The installed release the marks compare with; `null` for a new model.
- workspaceKey: The workspace the draft was opened for; `null` otherwise.
- suggestedReleaseVersion: The release version installing proposes: the draft's own when it differs from the base release's and is not installed, else the next free one. `null` without a release key.
- release: The release identity the draft declares.
- baseRelease: The base release's identity; `null` for a new model.
- applications: The applications, each with its types, navigation and views.
- objectTypes: The object types.
- attributeTypes: The attribute types.
- relationTypes: The relation types.
- relations: The relations allowed between object types.
- consumerApis: The consumer API definitions.
- valid: Whether the draft compiles.
- diagnostics: The compiler's diagnostics, each tied to its element.

### OutlineReleaseIdentity

- key: Shared by all releases of one model.
- name: The model's name.
- version: The release's version.
- schemaVersion: The model schema; left out for a base release.

### OutlineTypeNode

- objectType: The object type's key.
- children: The types contained directly under it.

### OutlineNavigationEntry

- collection: The object type key of a collection in the group.
- view: The key of a view of the application in the group. An entry holds one of the two.

### OutlineNavigationGroup

- key: The group's key.
- label: The group's name.
- collapsed: Whether the group starts folded.
- collections: The collections in the group, by object type key.
- entries: The group's collections and views in their one order.
- mark: `new`, `changed` or `released` against the base release.

### OutlineNavigation

- groups: The navigation groups.
- ungrouped: The collections in no group.
- opens: For each collection key, the view its entry opens on.

### OutlineView

- key: The view's key.
- name: The view's name.
- type: The view's kind, for example `table`, `tree` or `relationMatrix`.
- collection: The collection the view belongs to, which is its source type.
- shows: The object types the view shows.
- matrix: A relation matrix's configuration as the model declares it; left out for other kinds.
- config: A tree's, mapping grid's or relation table's configuration as the model declares it; left out for other kinds.
- mark: `new`, `changed` or `released` against the base release.

### OutlineUse

- view: The key of the relation view that uses the type.
- viewName: That view's name.
- viewType: That view's kind.
- role: How the view uses the type: `rows`, `columns`, `cells`, `from`, `to`, or `link` for a type on the containment path between a matrix's column and cell types.
- relationType: The relation type the view is about.
- relationName: Its name.

### OutlineBorrowedType

- objectType: The type's key.
- home: The first application, in model order, that holds the type's records; `null` when none does.
- uses: How the application's relation views use the type.

### OutlineBorrowedIn

- application: An application that lists the type only for a relation view.
- uses: How its relation views use the type.

### OutlineApplication

- key: The application's key.
- name: The application's name.
- icon: Its icon.
- color: Its color.
- defaultView: The view it opens on.
- objectTypeKeys: The object types it lists.
- tree: The listed types in their containment tree.
- ownTypes: The listed types whose records it holds: a table view of the type, or a tree view that includes it.
- ownTree: The own types in their containment tree.
- borrowed: The listed types it lists only because a relation view uses them.
- borrowedTree: The borrowed types in their containment tree.
- unused: The listed types nothing in the application uses.
- navigation: Its navigation.
- views: Its views.
- unlistable: The types it could stop listing: unused here, listed in another application, and not in the base release here.
- mark: `new`, `changed` or `released` against the base release.

### OutlineAttribute

- attributeType: The attribute type's key.
- name: The attribute type's name.
- valueType: The attribute type's value type.
- required: Whether a record of the type must fill it.
- readOnly: Whether people cannot edit it.
- unique: Whether the attribute type requires unique values.
- sharedWith: The other object types that bind the same attribute type.
- hidden: Whether the type hides the attribute in its forms and tables.
- helpText: The type's help text for the attribute; `null` when none.
- mark: `new`, `changed` or `released` against the base release.

### OutlineAttributeType

- key: The attribute type's key.
- name: The attribute type's name.
- valueType: Its value type.
- features: Its declared features.
- minimum: The lowest value a number type accepts; `null` for none.
- maximum: The highest value a number type accepts; `null` for none.
- hidden: Whether it is hidden by default.
- helpText: Its help text; `null` when none.
- boundBy: The object types that bind it.
- mark: `new`, `changed` or `released` against the base release.

### OutlineObjectType

- key: The object type's key.
- name: Its name.
- pluralName: Its plural name.
- icon: Its icon.
- description: Its description.
- rootCreatable: Whether a record can be created without a parent.
- parents: The types it can be placed under.
- displayAttribute: The attribute that names a record; `null` when none.
- effectivePeriod: The start and end date attributes that give a record its validity period; `null` without one.
- atLeastOneOf: The attributes of which a record must fill at least one.
- parentRelationTypeKeys: The relation types that place it under a parent.
- attributes: The attributes bound to it.
- home: The first application, in model order, that holds its records; `null` when none does.
- ownIn: Every application that holds its records.
- borrowedIn: The applications that list it only for a relation view, with the uses.
- mark: `new`, `changed` or `released` against the base release. A type also reads `changed` when a relation allowed from it changed.

### OutlineRelationType

- key: The relation type's key.
- reverseKey: The key of its reverse direction.
- name: Its name.
- reverseName: Its reverse direction's name.
- containment: Whether it places records under parents.
- isOriented: Whether the relation has a direction; otherwise both ends are alike.
- mark: `new`, `changed` or `released` against the base release.

### OutlineRelation

- relationType: The relation type's key.
- from: The object type the relationship starts from.
- to: The object type it points to.
- cardinality: How many targets a source may hold, as the model declares it.
- required: Whether a source must have one.
- attributeTypeKeys: The attributes a relationship carries; left out when none.
- containment: Whether the relation type places records under parents.
- uniquePer: The ancestor type under which a source may hold only one target; left out without the rule.
- candidates: Which records may be chosen at each end, as the model declares it; left out without the rule.
- mark: `new`, `changed` or `released` against the base release.

### OutlineDiagnostic

- severity: `error` makes the draft invalid; `warning` does not.
- code: A stable code for the kind of problem.
- path: A JSON pointer to the place in the model.
- message: What is wrong, for a person.
- count: How many places it covers, when one diagnostic sums up several.
- element: The element the path falls in, named as operations name elements; `null` when it falls in none.

### OutlineConsumerExposedType

- objectType: The exposed object type's key.
- publicName: The name consumers see for it.

### OutlineConsumerCounts

- fields: The fields of the object message.
- related: The related blocks.
- lists: The list operations.
- filters: The filters.
- events: The custom events.

### OutlineConsumerContract

A definition checked against what the active release's consumers read.

- classification: `compatible`, or `version_required` when the definition changes what its consumers read without a higher `contractVersion`.
- diagnostics: What differs from the base release, each tied to its element.

### OutlineConsumerApi

A consumer API definition of the draft. `contract` is `null` while the draft does not compile.

- key: The consumer API's key.
- name: Its name.
- description: Its description; `null` when none.
- contractVersion: Its declared contract version; `null` when none is set.
- exposes: The object types it exposes, with their public names.
- counts: How much the definition declares.
- mark: `new`, `changed` or `released` against the base release.
- contract: The definition checked against the base release; `null` while the draft does not compile.

### ModelDraftConsumerApiResponse

A draft's consumer API definition as written and, when the draft compiles, with every default written out and its contract checked against the active release.

- version: The draft's `version`.
- valid: Whether the draft compiles.
- definition: The definition as written in the draft.
- expanded: The definition with every default written out; left out while the draft does not compile.
- contract: The definition checked against the base release; left out while the draft does not compile.

### ModelDraftModelResponse

A draft compiled as `GET /api/v1/model` serves the active model, with its placements. `model` and `placements` are absent when the draft does not compile.

- version: The draft's `version`.
- valid: Whether the draft compiles.
- diagnostics: The compiler's diagnostics, each tied to its element.
- model: The compiled model, as `GET /api/v1/model` serves a running one; left out while the draft does not compile.
- placements: Where types can stand under each application; left out while the draft does not compile.

### ModelCompilationResponse

- valid: Whether the draft compiles.
- model: The compiled model in canonical form; left out when invalid.
- modelHash: Identifies the compiled model's content; left out when invalid.
- diagnostics: The compiler's diagnostics, errors and warnings.
- compatibility: What activating the model would do to each workspace's data. `invalid` for a draft that does not compile.
- againstReleaseId: The release `changes` compare with: the draft's base, else the newest release of its model; `null` for a new model, left out when invalid.
- changes: Each added, changed or removed element against that release; empty when invalid.
- consumerContracts: The consumer API definitions checked against that release; `null` for a new model, left out when invalid.

### ModelInstallationResponse

- id: The release's ID.
- key: Shared by all releases of one model.
- name: The model's name.
- version: The release's version.
- schemaVersion: The model schema the release is written in.
- modelHash: Identifies the release's content.
- installedAt: When the release was first installed.
- assigned: Whether a workspace runs it already.
- workspaces: The keys of the workspaces that run it.
- retiredAt: Left out: installing makes a retired release active again.
- model: Left out; read it with the release.
- importProfile: The instance import profile saved from the draft's, as `key` and `version`; left out when the draft's profile does not hold against the release.

### InstalledImportProfile

The instance import profile an installation saved from the draft's profile.

- key: The instance import profile's key.
- version: Its version after this installation.

### DryRunRequest

What to check against the draft's model: either the draft's source file with the workspace the import would write in and the profile that binds the file, or `items`, the batch items of `POST /api/v1/batches` (each with an optional `ref` naming the cells it comes from). Give exactly one of `sourceFileId` and `items`. Without `profile` a source file is read with the profile the draft holds; a profile sent may be the one `GET /api/v1/model-drafts/{draft_id}/profile` answered, whose read-only `key`, `unmapped`, `ignoredSheets` and source `id` are ignored.

- sourceFileId: A source file the draft owns, to check. Exactly one of `sourceFileId` and `items`.
- workspaceKey: The workspace whose records the check compares with; it must not be retired.
- profile: How the file is read. Without it, the draft's own profile. The read-only members of `GET /api/v1/model-drafts/{draft_id}/profile` are ignored. Not with `items`.
- onExisting: `reject` (the default) refuses a found record whose row carries no version; `overwrite` updates it.
- items: Batch items to check, each with an optional `ref` naming the cells it comes from. At least one; held to the limits of a background atomic batch.

### DryRunResponse

A model draft's dry run: `checking` while its job runs, then `completed` with its `summary` of the whole file or its `items` of the whole set, `failed` with the error, or `cancelled` when the draft changed or a newer dry run started.

- jobId: The dry run's job.
- state: `checking` while it runs; then `completed`, `failed` with `error`, `cancelled` when the draft changed or a newer dry run started, or `expired` once retention removed its outcomes.
- draftId: The draft.
- draftVersion: The draft's version the dry run was sent for.
- sourceFileId: The file checked; `null` for items.
- workspaceKey: The workspace compared with.
- summary: What a file's rows would do; `null` for items and until `completed`.
- bindingReport: How each sheet's columns were read; `null` for items and until the file is bound.
- error: Why it `failed`.
- items: What the items would do; `null` for a file and until `completed`.

### InferenceRequest

Asks what the table patterns propose for the draft's current source file: a new application (named `applicationName`, by default after the file, keyed `applicationKey` when given), or additions to the draft's model, whose new types go into `applicationKey` (by default the application most matched types are in).

- mode: `newApplication` proposes a new application for the file; `extend` proposes additions to the draft's model.
- applicationKey: `newApplication`: the new application's key, one the draft lacks. `extend`: the application new types go into, one the draft has; by default the one most matched types are in.
- applicationName: The new application's name; by default after the file. Used by `newApplication`.

### InferenceResponse

A model draft's latest inference: `checking` while its job runs, then `completed` with its proposals' counts by status, what the workbook disagrees with, its warnings and the elements still as proposed, or `failed` with the error.

- jobId: The inference's job.
- state: `checking` while it runs; then `completed`, `failed` with `error`, `cancelled` when a newer inference started, or `expired`.
- mode: The mode it was asked for.
- draftVersion: The draft's version the inference read; applying needs the draft unchanged since.
- sourceFileId: The file it read.
- counts: The proposals by status; zero until `completed`.
- disagreements: Columns the draft reads otherwise than the file's shape suggests.
- warnings: What the inference could not use, in words, such as a sheet it left out.
- proposed: Elements of the draft still as an applied proposal left them.
- error: Why it `failed`.

### InferenceCounts

- open: Proposals that can be applied.
- applied: Proposals a step of the draft applied.
- held: Proposals not applied because the draft binds those columns already.
- rejected: Proposals undone before; they are not proposed again.

### InferenceDisagreement

A column the draft reads otherwise than a pattern does: its sheet, the source, how the draft binds it and how the pattern would, the pattern's finding, and the step that decided it.

- proposalId: The proposal that found it.
- pattern: The pattern it found, such as `listBlock`.
- sheet: The sheet; `null` for a CSV file.
- column: The column's header.
- source: The profile source that binds the column.
- binding: How the draft binds the column: `field`, `attributeTypeKey`, `parent`, `relation`, `relationFlags` or `relatedRecord`.
- proposed: How the pattern would bind it, in the same words.
- found: What the pattern found, in a sentence.
- step: The step that decided the binding; `null` when none did.

### ProposedElement

An element still as a proposal step left it: the engine's, until the administrator changes it. Elements are named as the history names them, and `source:<id>`, `column:<source>/<header>` and `valueMap:<name>` for the draft's profile.

- element: The element, as a history entry names it, or `source:<id>`, `column:<source>/<header>` or `valueMap:<name>` in the profile.
- proposalId: The proposal that created it.
- pattern: That proposal's pattern.

### ProposalResponse

A proposal: the pattern found, on which sheet and columns, in one sentence, with the evidence it rests on; the operations it applies (the kinds of `POST /api/v1/model-drafts/{draft_id}/operations`), its alternatives as operations to send after it, the proposals it requires, and its status: `open`, `applied`, `held` (the draft decides those columns already) or `rejected` (an undone proposal, not applied again).

- id: The proposal's ID. A later inference keeps it for the same finding.
- position: Its place in the order proposals apply.
- pattern: The pattern found, such as `listBlock`.
- sheet: The sheet; `null` for a CSV file.
- columns: The headers of the columns it concerns.
- summary: What it found, in a sentence.
- evidence: What the finding rests on: shares, vocabularies and values the file holds that stored records do not. Its shape depends on the pattern.
- operations: The operations it applies, as `POST /api/v1/model-drafts/{draft_id}/operations` takes them.
- alternatives: Other readings of the same columns.
- requires: IDs of the proposals that create what this one names; apply them first or with it.
- status: `open` can be applied; `applied` was; `held` because the draft binds those columns already; `rejected` because it was undone and is not proposed again.

### ProposalAlternative

- label: What the alternative reads differently, in a sentence.
- operations: The operations to send after the proposal's to read it this way.

### InferenceApplicationRequest

Which proposals of the draft's latest inference to apply, each as its own step; every proposal that is still open when omitted.

- expectedVersion: The draft's `version`.
- proposals: IDs of the proposals to apply; by default every open one.

### ListProposalRequest

A rectangle of the draft's file to read as a list, with its header row and `block` as a source takes them. New types go into `applicationKey`, by default the application the sheet's sources load into.

- sheet: The sheet, as `GET /api/v1/source-files/{source_file_id}/profile/sheets` names it.
- headerRow: The row holding the headers, from 1.
- block: The columns and rows the list spans, as a source's `block`.
- applicationKey: The application new types go into, one the draft has; by default the one the sheet's sources load into.

### JoinCandidatesRequest

Two tables of the draft's file to compare: `column`, the one dropped, and `against`, what it is compared with.

- column: The dropped column: its sheet, its header row and block (as a source takes them) and the column by `column` (its header) or `letter`. One of the two is needed.
- against: The table compared with. With a `column` or `letter` only that column is compared; without, every column of the table that holds a value of the dropped column.

### JoinColumnRef

A table of the file and, optionally, one of its columns.

- sheet: The sheet, as `GET /api/v1/source-files/{source_file_id}/profile/sheets` names it.
- headerRow: The row holding the headers; the sheet's own when left out.
- block: The columns and rows the table spans, as a source's `block`.
- column: The column's header text; spaces around it do not count, so the header as the columns read lists it is accepted and saved trimmed, as an import reads it; a repeated header reads `Name #2`. Not with `letter`.
- letter: The column's sheet letter, such as `C`. Not with `column`.

### JoinCandidatesResponse

The columns the dropped column's values point at, compared over every row.

- column: The dropped column as read.
- candidates: The columns that hold values of the dropped column (every column of a named table), by `matchedRows` and then `matchedValues`, then column order.
- best: The letter of the one column that matches most; `null` when two or more tie or none matches.
- tie: Whether two or more columns match exactly as much. The client asks which.
- tied: The letters of the tied columns; empty without a tie.

### JoinColumnResponse

The dropped column.

- sheet: Its sheet.
- letter: Its sheet letter.
- header: Its header text; `null` when the header cell is empty.
- rows: Its filled rows.
- distinct: How many of them differ.

### JoinCandidate

A column of the compared table, with its figures over every row.

- sheet: Its sheet.
- letter: Its sheet letter.
- header: Its header text; `null` when the header cell is empty.
- rows: Its filled rows.
- distinct: How many of them differ.
- matchedValues: How many of the dropped column's different values the column holds.
- matchedRows: How many of the dropped column's rows hold a value the column holds.
- share: `matchedRows` over the dropped column's filled rows, from 0 to 1.
- unique: Whether every filled cell of the column differs, so it reads as a list to link to.

### CanvasResponse

What the draft's board keeps: card positions, folded cards and the chosen scope.

- positions: Each card's position. A card a client does not know is left as it is.
- folded: The keys of the folded cards, in order.
- scope: What the board shows: `model`, `changed` or `workbook`; `null` is the default.

### CanvasPosition

Where a card sits on the board, in the board's own units.

- x: Horizontal position, from -1,000,000 to 1,000,000.
- y: Vertical position, from -1,000,000 to 1,000,000.

### CanvasUpdate

Parts to merge into the canvas; at least one.

- positions: A position for each card to place or move, by key (1 to 200 characters), or `null` to remove the card.
- folded: For each card key (1 to 200 characters), `true` to fold the card, `false` or `null` to unfold it.
- scope: `model`, `changed` or `workbook` to choose it, `null` for the default.

### ListProposalResponse

A rectangle read as a list: a `listBlock` proposal built against the draft as it is and not stored. Its `operations` go to `POST /api/v1/model-drafts/{draft_id}/operations` as one step.

- pattern: The pattern the rectangle was read as.
- sheet: The sheet.
- columns: The headers of its columns.
- summary: What it found, in a sentence.
- evidence: What the finding rests on. Its shape depends on the pattern.
- operations: The operations that load the list, to send to `POST /api/v1/model-drafts/{draft_id}/operations` as one step.
- alternatives: Other readings, each with a `label` and its `operations`.

### StepDryRun

The dry run a step queued; `GET /api/v1/model-drafts/{draft_id}/dry-run` reads it.

- state: Always `checking`.
- jobId: The dry run's job; read it at `GET /api/v1/model-drafts/{draft_id}/dry-run`.

### JobRowPage

An import's rows in source and row order.
