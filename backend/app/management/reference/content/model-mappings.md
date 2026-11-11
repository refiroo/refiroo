# model mappings

A model mapping is a stored definition of what each element of a source model becomes in a target model. It pairs two model releases of one or two models and holds entries that map object types, attributes (with value maps), relationships and where records stand. Moves and migrations use it. It changes only through operations, each step kept in a history you can undo and redo. An inference can propose the entries from the two workspaces' models and records.

1. Create it with `POST /api/v1/model-mappings`, then shape it with `POST .../operations` at the `version` you read.
2. Or let `POST .../inference` propose it, read `GET .../inference/proposals` and apply the ones you accept.
3. Check `problems` and `coverage` of `GET /api/v1/model-mappings/{key}`, then send a move with `POST /api/v1/moves`.

## GET /api/v1/model-mappings

Title: List model mappings

Lists the stored mappings in key order, optionally those between one source model and one target model. A row carries the mapping's `version`; read the mapping itself for its entries, problems and coverage.

### Parameters

- sourceModelKey: Only mappings whose source is this model.
- targetModelKey: Only mappings whose target is this model.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/model-mappings

Title: Create a model mapping

Creates a mapping with no type mapped. Name each side by a workspace, which takes the release it runs now, or by a release ID, never both. Shape it afterwards with operations; its `version` starts at 1.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 WORKSPACE_NOT_FOUND: a named workspace does not exist
- 404 MODEL_RELEASE_NOT_FOUND: a named release is not installed
- 405 HTTP_ERROR: integration jobs are switched off
- 409 WORKSPACE_RETIRED: a named workspace is retired
- 409 MODEL_MAPPING_EXISTS: the key is taken
- 422 INVALID_MODEL_MAPPING: a side is named twice or not at all
- 422 REQUEST_VALIDATION_ERROR: the key or name is invalid

## GET /api/v1/model-mappings/{key}

Title: Get a model mapping

Reads a mapping with its entries and, against its two releases, the `problems` that stop it from holding and the `coverage` it leaves open. Name a workspace to check a side against the release that workspace runs now, which is what a move uses.

### Parameters

- key: The mapping's key.
- sourceWorkspaceKey: Check the source side against the release this workspace runs.
- targetWorkspaceKey: Check the target side against the release this workspace runs.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 WORKSPACE_NOT_FOUND: a named workspace does not exist
- 422 MODEL_MAPPING_MODEL_MISMATCH: a workspace runs another model than the mapping's side

## DELETE /api/v1/model-mappings/{key}

Title: Delete a model mapping

Deletes a mapping with its history and its inference's proposals. A move already queued keeps the definition it was sent with.

### Parameters

- key: The mapping's key.
- expectedVersion: The mapping's `version`.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 405 HTTP_ERROR: integration jobs are switched off
- 409 VERSION_CONFLICT: the mapping changed since you read it
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or invalid

## GET /api/v1/model-mappings/{key}/operations

Title: Read a mapping's history

Lists every operation applied to the mapping in sequence order, undone ones included, so you see who changed what and how to reverse it. Operations applied together share a `step`; undo and redo work on steps.

### Parameters

- key: The mapping's key.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/model-mappings/{key}/operations

Title: Change a model mapping

Applies a list of operations as one step, all or none. Each item's `kind` selects one of the twelve operation kinds: `mapType`, `unmapType`, `mapAttribute`, `unmapAttribute`, `mapRelation`, `unmapRelation`, `setParent`, `setMatch`, `setValueMap`, `setMissing`, `setDefault` and `setReleases`; the other fields of an item depend on the kind. The answer has the new `version` and the problems against the mapping's releases.

### Parameters

- key: The mapping's key.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 405 HTTP_ERROR: integration jobs are switched off
- 409 VERSION_CONFLICT: the mapping changed since you read it
- 413 OPERATION_BATCH_TOO_LARGE: more operations than one request may hold
- 422 INVALID_OPERATION: an operation does not apply; `details` names it and why
- 422 REQUEST_VALIDATION_ERROR: the list is empty or malformed

## POST /api/v1/model-mappings/{key}/undo

Title: Undo a mapping step

Undoes the latest step not yet undone, or the step named by `step`, or the several named by `steps` together. Undoing is itself a new step, so the version rises and the history keeps both.

### Parameters

- key: The mapping's key.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 HTTP_ERROR: integration jobs are switched off, so the address does not exist
- 409 VERSION_CONFLICT: the mapping changed since you read it
- 409 NOTHING_TO_UNDO: no step, or the named step, can be undone
- 409 OPERATION_HAS_DEPENDANTS: later steps rely on what the step made
- 422 REQUEST_VALIDATION_ERROR: the body is invalid

## POST /api/v1/model-mappings/{key}/redo

Title: Redo a mapping step

Redoes the latest undone step. Only the most recent undo can be redone; a new operation after an undo ends that chance.

### Parameters

- key: The mapping's key.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 HTTP_ERROR: integration jobs are switched off, so the address does not exist
- 409 VERSION_CONFLICT: the mapping changed since you read it
- 409 NOTHING_TO_REDO: no undone step to redo
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or invalid

## GET /api/v1/model-mappings/{key}/inference

Title: Read the latest inference

Reads the mapping's most recent inference: its state and, once completed, how many proposals are in each status. Poll it after `POST .../inference` until `state` leaves `checking`.

### Parameters

- key: The mapping's key.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 INFERENCE_NOT_FOUND: the mapping has had no inference

## POST /api/v1/model-mappings/{key}/inference

Title: Propose a mapping

Starts an inference that compares the two releases' elements and the two workspaces' records and proposes mapping entries. It answers `202` with the inference `checking`; an inference still running for this mapping is cancelled and its proposals are replaced when the new one completes. Nothing in the mapping changes until you apply proposals.

### Parameters

- key: The mapping's key.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 WORKSPACE_NOT_FOUND: a named workspace does not exist
- 405 HTTP_ERROR: integration jobs are switched off
- 422 MODEL_MAPPING_MODEL_MISMATCH: a workspace runs another model than the mapping's side
- 422 REQUEST_VALIDATION_ERROR: a workspace key is missing

## GET /api/v1/model-mappings/{key}/inference/proposals

Title: List proposals

Lists the latest inference's proposals in the order they apply: a type first, then its relationships. Each carries the operations that apply it and alternatives you can send afterwards instead.

### Parameters

- key: The mapping's key.
- sourceType: Only the proposals of this source type.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 INFERENCE_NOT_FOUND: the mapping has had no inference
- 409 INFERENCE_NOT_READY: the inference is still running or failed
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/model-mappings/{key}/inference/application

Title: Apply proposals

Applies the named proposals, or every open one when `proposals` is absent, in their order. Each becomes one step of the history, and all steps apply or none. A relationship proposal needs its type proposal applied before or with it.

### Parameters

- key: The mapping's key.

### Errors

- 403 FORBIDDEN: needs Copy and move in some workspace
- 404 MODEL_MAPPING_NOT_FOUND: no mapping has this key
- 404 INFERENCE_NOT_FOUND: the mapping has had no inference
- 404 PROPOSAL_NOT_FOUND: a named proposal is not in the inference
- 404 HTTP_ERROR: integration jobs are switched off, so the address does not exist
- 409 VERSION_CONFLICT: the mapping changed since you read it
- 409 INFERENCE_NOT_READY: the inference is still running or failed
- 409 INFERENCE_STALE: the mapping was re-pointed to other releases since
- 409 NOTHING_TO_APPLY: no proposal is open
- 409 PROPOSAL_ALREADY_APPLIED: a named proposal is applied
- 413 OPERATION_BATCH_TOO_LARGE: a proposal holds more operations than a request may
- 422 PROPOSAL_REQUIREMENT_MISSING: a proposal's required proposal is neither applied nor named
- 422 INVALID_OPERATION: a proposal's operation no longer applies

## Schemas

### MappingCoverage

What the mapping leaves out: source types, attributes and relationships not mapped; the target's required attributes and relationships that nothing fills; and the parents a source record may stand under that its target type cannot (`PARENT_NOT_ALLOWED`, `PARENT_TYPE_NOT_MAPPED`, `PARENT_REQUIRED`, with `parentType` null for the top).

- types: Source types with no entry.
- attributes: Attributes of a mapped source type that its entry neither maps nor ignores, as `sourceType` and `attributeTypeKey`.
- relations: Relationships of a mapped source type that its entry does not carry, as `sourceType` and `relationTypeKey`.
- required: Required target attributes that nothing fills, as `targetType` and `attributeTypeKey`.
- requiredRelations: Required target relationships that nothing carries, as `targetType` and `relationTypeKey`.
- parents: Parents a source record may stand under that its target type cannot, as `sourceType`, `parentType` (null for the top) and `reason`.

### MappingInferenceApplication

- expectedVersion: The mapping's `version`.
- proposals: IDs of the proposals to apply; every open proposal when absent.

### MappingInferenceCounts

- open: Proposals not yet in the mapping.
- applied: Proposals whose result the mapping holds.
- held: Proposals whose type or relationship the mapping already decides otherwise.
- rejected: Proposals whose applying step was undone.

### MappingInferenceRequest

The two workspaces whose models the mapping maps and whose records it compares.

- sourceWorkspaceKey: The workspace running the mapping's source model, whose records are compared.
- targetWorkspaceKey: The workspace running the mapping's target model, whose records are compared.

### MappingInferenceResponse

A mapping's latest inference: `checking` while its job runs, then `completed` with its proposals' counts by status and its warnings, or `failed` with the error.

- jobId: The inference's job.
- state: `checking` while it runs, `completed`, `failed`, `cancelled` (a newer inference replaced it) or `expired`. Proposals can be read only when `completed`.
- mappingVersion: The mapping's `version` when the inference started.
- sourceWorkspaceKey: The workspace compared on the source side.
- targetWorkspaceKey: The workspace compared on the target side.
- sourceReleaseId: The source release the inference read.
- targetReleaseId: The target release the inference read.
- counts: Proposals by status; zero until completed.
- warnings: Things the inference could not propose, such as source types no target type is like.
- error: Why it failed; `null` otherwise.

### MappingProblem

An entry naming what a release lacks or no longer allows, at its pointer into the mapping, on the `source` or `target` side.

- code: `ELEMENT_NOT_IN_RELEASE`, `BINDING_NOT_ALLOWED`, `VALUE_TYPES_NOT_CONVERTIBLE` or `ATTRIBUTE_FILLED_TWICE`.
- message: In words, what is wrong.
- pointer: The JSON pointer into the mapping, such as `/types/0/target`.
- side: `source` or `target`: the release the entry is checked against.

### MappingProposalResponse

A proposal: a source type's or one of its relationships' target, its score and evidence, the operations it applies, its alternatives as operations to send after it, the proposals it requires and its status: `open`, `applied`, `held` (the mapping decides it otherwise) or `rejected` (a step that applied it was undone).

- id: The proposal's ID; the same in every inference of the mapping.
- position: Its place in the order the proposals apply, from 0.
- kind: `type` (a source type's target) or `relation` (one of its relationships).
- sourceType: The source type.
- relation: The source relation type of a `relation` proposal; `null` for a type.
- target: The proposed target type, or target relation type.
- score: How alike the two are by key, name and shared values; higher is likelier. Compare only proposals for one source element.
- summary: The proposal in words.
- evidence: What the score rests on, each item with a `kind`.
- operations: The operations that apply the proposal, as `POST .../operations` takes them.
- alternatives: Other targets, each with `target`, `score`, a `label` and the `operations` to send after this proposal.
- requires: IDs of the proposals that must be applied first or with this one.
- status: `open`, `applied`, `held` or `rejected`, as the counts name them.

### MappingTypeEntry

What one source type becomes: its target type, its attributes (`target` with an optional `valueMap`, or `ignore`), its relationships, where its records stand, how existing target records are matched, and the defaults of target attributes.

- source: The source object type.
- target: The target object type its records become.
- attributes: One item per source attribute: `source`, then `target` (with an optional `valueMap`) or `ignore`.
- relations: One item per source relation type: `source`, `target` (a target relation type), `direction` and optional `attributes`.
- defaults: Values given to target attributes no source attribute fills, by attribute type key.
- parent: Where a target record stands: taken from the source record's parent or fixed. `null` when not set.
- match: The target attribute that finds a record the target already holds, so it is updated rather than created. `null` creates every record.

### ModelMappingCreate

A mapping between two sides, each named by a workspace or by a release, not both.

- key: The mapping's key: 1 to 160 characters, a letter or digit first, then letters, digits, `_`, `.` or `-`. It cannot change.
- name: A name for people; 1 to 200 characters.
- sourceWorkspaceKey: The source side is the release this workspace runs now. Not with `sourceReleaseId`.
- targetWorkspaceKey: The target side is the release this workspace runs now. Not with `targetReleaseId`.
- sourceReleaseId: The source side is this installed release. Not with `sourceWorkspaceKey`.
- targetReleaseId: The target side is this installed release. Not with `targetWorkspaceKey`.

### ModelMappingOperationEntry

One operation in a mapping's history, as in a draft's.

- sequence: The operation's position in the mapping's history.
- step: The step it was applied in; operations of one request share a step.
- kind: The operation kind. The server also writes `restoreElements`, the inverse of every step, here; a request cannot send it.
- parameters: The operation's fields as applied; for `restoreElements` the logged changes it puts back.
- inverse: The operation that reverses it, as undo applies: a `restoreElements` operation holding the logged reversal.
- mappingVersion: The mapping's `version` after the step.
- author: Who applied it; `null` when unknown.
- at: When it was applied.
- undone: `true` once a later undo reversed its step.
- origin: Where the step came from: `type` is `request`, `proposal` (with `proposalId`), `undo` or `redo`.
- removed: Always empty for a mapping; a draft's entry lists the views and panels an operation took away.
- migration: Always empty for a mapping; a draft's entry lists the elements that need a migration.

### ModelMappingOperationsRequest

- expectedVersion: The mapping's `version`.
- operations: The operations, applied in order; at least one. Each has a `kind`.

### ModelMappingResponse

- key: The mapping's key.
- name: The mapping's name.
- sourceModelKey: The model the mapping maps from.
- targetModelKey: The model the mapping maps to.
- sourceReleaseId: The source release the mapping is checked against.
- targetReleaseId: The target release the mapping is checked against.
- version: The mapping's version; it rises with every step.
- updatedAt: When it last changed.
- createdAt: When it was created.
- types: One entry per source type the mapping maps.
- valueMaps: Named value maps that attributes refer to: each maps source values to target values.
- problems: What the releases lack or no longer allow, so a move would be refused.
- coverage: What the mapping leaves out.

### ModelMappingStepResponse

- version: The mapping's `version` after the step.
- entries: The operations the step recorded, with the history's fields.
- problems: The mapping's problems against its releases after the step.

### ModelMappingSummary

- key: The mapping's key.
- name: The mapping's name.
- sourceModelKey: The model the mapping maps from.
- targetModelKey: The model the mapping maps to.
- sourceReleaseId: The source release the mapping is checked against.
- targetReleaseId: The target release the mapping is checked against.
- version: The mapping's version.
- updatedAt: When it last changed.

### ModelMappingUndoRequest

- expectedVersion: The mapping's `version`.
- step: The step to undo. Not with `steps`.
- steps: Steps to undo together. Not with `step`. With neither, the latest step not yet undone.

### ModelMappingVersionRequest

- expectedVersion: The mapping's `version`.
