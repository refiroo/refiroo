# jobs

A job is the engine's record of bulk work: a batch of writes, an import, an export, or a check that reads a file. Send the work, follow the job to its end and read what happened to each item. `independent` applies each item on its own, `atomic` all or none. A background job answers `202` and a worker runs it in chunks. Outcomes are kept for the operator's retention days; then the job is `expired`, keeps its summary and loses its outcomes, and what needed them answers `410`. Retry safely with an `Idempotency-Key`.

1. Send: `POST /api/v1/batches`, `POST /api/v1/imports` or `POST /api/v1/exports`.
2. Follow `GET /api/v1/jobs/{job_id}` (or `.../events`), then read `.../items`, `.../rows` or `.../output`.

## POST /api/v1/batches

Title: Run a batch of writes

Writes many records and relationships as one job, live in `workspaceKey` or into the change set `changeSetId`. Items apply in order, each seeing what the earlier ones left; `op` is `create`, `update`, `upsert`, `delete`, `createRelation`, `ensureRelation`, `ensureNoRelation`, `updateRelation`, `deleteRelation` or `replaceRelationSet`. `run: inline` answers `200` with the outcomes, `background` answers `202` with the queued job. A refused item does not fail the request: read `job.result`.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: an inline batch into a submitted change set
- 409 MODEL_RELEASE_CHANGED: the context runs another release than the header names
- 409 IDEMPOTENCY_IN_PROGRESS: the key's job is still running
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged
- 413 BATCH_TOO_LARGE: over the item or byte limit of the run
- 422 INVALID_BATCH_CONTEXT: both or neither of `workspaceKey` and `changeSetId`
- 422 IDEMPOTENCY_KEY_REUSED: the key belongs to another request
- 422 REQUEST_VALIDATION_ERROR: a field is invalid, or `preview` runs inline

## POST /api/v1/exports

Title: Export records to a file

Starts a job that writes the records of a `scope`, or of a `view`'s current state, to JSON Lines, CSV or XLSX; read everything at one instant. JSON Lines holds batch items that `POST /api/v1/batches` takes back unchanged. When the job is `completed`, `GET /api/v1/jobs/{job_id}/output` serves the file. `context` names a change set or a publication instead of live data. A repeated request makes a second job.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 404 CHANGE_SET_NOT_FOUND: `context.changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `context.publicationId` names no publication
- 404 PARENT_NOT_FOUND: `parentObjectId` is not in the exported context
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged
- 422 REQUEST_VALIDATION_ERROR: the body is malformed or names both `scope` and `view`
- 422 WORKSPACE_CONTEXT_MISMATCH: the context is another workspace's
- 422 INVALID_QUERY: a type, field or operator does not fit the model
- 422 AS_OF_NOT_SUPPORTED: no exported type has an effective period
- 422 INVALID_EXPORT_LAYOUT: the layout, `people` or `view` cannot be built

## GET /api/v1/jobs

Title: List jobs

Lists jobs, newest first: those the caller started and those of a kind whose group the caller holds in the job's workspace. `grouped=true` answers one row per assistant task or model draft, and one per job that has neither; the filters apply before the grouping.

### Parameters

- workspaceKey: Only jobs of this workspace.
- kind: Only jobs of this kind.
- state: Only jobs in this state.
- pageSize: 1 to 500; 50 by default.

### Errors

- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_ORIGIN: `origin` is not `aiTask:<id>` or `modelDraft:<id>`
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/jobs/{job_id}

Title: Get a job

Reads one job: its `state`, `progress` and `counts`, and what its kind adds, such as an export's `output`, a preview's `preview` or an import's `bindingReport`. Poll it until `state` is `completed`, `failed`, `cancelled` or `expired`; `awaiting_confirmation` waits for you. `result` says whether every item applied. The person or client that started the job can always read it.

### Parameters

- job_id: The job's ID.

### Errors

- 403 FORBIDDEN: needs the group that starts this kind of job in its workspace
- 404 JOB_NOT_FOUND: no job has this ID

## GET /api/v1/jobs/{job_id}/events

Title: Follow a job

Streams a job as server-sent events instead of polling. `event: job` carries the job as `GET /api/v1/jobs/{job_id}` answers it, at once and after each change of its state, progress, cancel request or output. The stream ends after a final state; a finished job is sent once. A comment line every 15 seconds keeps an idle stream open.

### Parameters

- job_id: The job's ID.

### Errors

- 403 FORBIDDEN: needs the group that starts this kind of job in its workspace
- 404 JOB_NOT_FOUND: no job has this ID

## GET /api/v1/jobs/{job_id}/items

Title: Read a job's outcomes

Lists the outcome of each item of a batch or an import, in item order. In a preview, `applied` means the item would apply. An expired job answers an empty page, not an error. For an import, `/rows` gathers the outcomes by row of the file.

### Parameters

- job_id: The job's ID.
- status: Only items with this outcome.
- pageSize: 1 to 1,000; 1,000 by default.

### Errors

- 403 FORBIDDEN: needs the group that starts this kind of job in its workspace
- 404 JOB_NOT_FOUND: no job has this ID
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/jobs/{job_id}/rows

Title: Read an import's outcomes by row

Lists an import's rows of the file in source then row order, each with its worst status, its applied items by action and its refused or unprocessed outcomes. A migration's job lists its items and a move's job its rows, narrowed by `status`, `outcome`, `reason` or `sourceType`. A batch or an export has none.

### Parameters

- job_id: The job's ID.
- pageSize: 1 to 1,000; 500 by default.

### Errors

- 403 FORBIDDEN: needs the group that starts this kind of job in its workspace
- 404 JOB_NOT_FOUND: no job has this ID
- 404 JOB_HAS_NO_ROWS: the job is a batch or an export
- 422 INVALID_PAGE_PARAMETER: `status` is of another kind of job
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/jobs/{job_id}/output

Title: Download an export's file

Serves the file of a completed export, with its SHA-256 in `ETag` and `Repr-Digest`. A cancelled or failed export has no file, and retention removes it.

### Parameters

- job_id: The job's ID.

### Errors

- 403 FORBIDDEN: needs Browse in the job's workspace
- 404 JOB_NOT_FOUND: no job has this ID
- 404 JOB_HAS_NO_OUTPUT: the job is not an export
- 409 JOB_NOT_COMPLETED: the export has not completed
- 410 JOB_EXPIRED: retention removed the file
- 410 JOB_OUTPUT_MISSING: the file is gone from the job file directory

## POST /api/v1/jobs/{job_id}/cancel

Title: Cancel a job

Asks a job to stop. `cancelRequestedAt` is set at once and the worker acts at the job's next chunk: items not reached are `unprocessed` with `JOB_CANCELLED`, chunks already committed stay applied, and an `atomic` job rolls back. A preview waiting for confirmation is cancelled immediately and its file removed. Cancelling twice changes nothing.

### Parameters

- job_id: The job's ID.

### Errors

- 403 FORBIDDEN: needs the group that starts this kind of job in its workspace
- 404 JOB_NOT_FOUND: no job has this ID
- 409 JOB_FINISHED: the job is already completed, failed, cancelled or expired

## POST /api/v1/jobs/{job_id}/confirm

Title: Confirm a preview

Runs a previewed import or batch for real: the stored file or items run as `stage: execute` would, and their outcomes replace the preview's, so what changed since the preview counts. Confirming twice answers with the job unchanged. A migration or a move waiting for confirmation is confirmed here too; a migration takes a body.

### Parameters

- job_id: The job's ID.

### Errors

- 403 FORBIDDEN: the requester no longer holds the group the job needs
- 404 JOB_NOT_FOUND: no job has this ID
- 404 WORKSPACE_NOT_FOUND: the job's workspace is gone
- 404 CHANGE_SET_NOT_FOUND: the job's change set is gone
- 409 JOB_NOT_AWAITING_CONFIRMATION: the job is not a waiting preview
- 409 MODEL_RELEASE_CHANGED: another release is in use than the preview's
- 409 CHANGE_SET_VERSION_CONFLICT: the change set changed since the request
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 MIGRATION_REVIEW_STALE: a migration's workspace changed since its preview
- 409 MIGRATION_HAS_REFUSALS: a migration still has refused items
- 409 MOVE_MAPPING_CHANGED: a move's mapping changed since its dry run
- 410 JOB_EXPIRED: the preview waited past retention
- 422 MIGRATION_LOSS_NOT_ACCEPTED: a migration removes data and `acceptLoss` is missing
- 422 MOVE_NOTHING_TO_MOVE: a move has nothing to load

## POST /api/v1/jobs/{job_id}/reread

Title: Read an import preview again

Starts a new preview of a waiting import's file and profile with other matching fields. Each reading names a source and a column of the binding report and the field its cells are matched by, one of the column's `reading.options`. The first preview is cancelled and neither wrote anything; confirm the new job to load the file.

### Parameters

- job_id: The job's ID.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the job's workspace
- 404 JOB_NOT_FOUND: no job has this ID
- 404 WORKSPACE_NOT_FOUND: the job's workspace is gone
- 404 CHANGE_SET_NOT_FOUND: the job's change set is gone
- 409 JOB_NOT_AWAITING_CONFIRMATION: the job is not a waiting import preview
- 409 MODEL_RELEASE_CHANGED: another release is in use than the preview's
- 409 CHANGE_SET_VERSION_CONFLICT: the change set changed since the import
- 410 IMPORT_FILE_MISSING: the preview's file is gone
- 422 IMPORT_HAS_NO_PROFILE: the import was read without a profile
- 422 INVALID_IMPORT_READING: a reading names no such column or field
- 422 INVALID_IMPORT_PROFILE: the profile no longer fits the model
- 422 REQUEST_VALIDATION_ERROR: `readings` is missing or malformed

## Schemas

### BatchRequest

Items, a failure policy and one context for `POST /api/v1/batches`. `stage: preview` runs the items without writing and waits for confirmation; only a background batch is previewed.

- workspaceKey: The workspace whose live data the batch changes. Exactly one of `workspaceKey` and `changeSetId`.
- changeSetId: The change set the batch writes into.
- expectedChangeSetVersion: The change set's `version`. Required with `changeSetId`, and refused without it. The job advances the version once for all its items, and not at all when nothing changed.
- policy: `independent` applies each item on its own and leaves a refused one out; `atomic` applies every item or none, and a refusal leaves the others `unprocessed` with `BATCH_ROLLED_BACK`.
- run: `inline` runs the batch in the request and answers `200`; `background` queues it and answers `202`. The size never switches the run.
- stage: `execute` (the default) writes. `preview` runs the items without writing, independently whatever the policy, and waits for `POST /api/v1/jobs/{job_id}/confirm`; it needs `run: background`.
- onExisting: `reject` (the default) refuses an upsert that finds a record and carries no `expectedVersion`; `overwrite` writes over the version it read and reports it as `previousVersion`.
- otherWorkspaceIds: `refuse` (the default) treats an ID that another workspace's record holds as naming nothing here. `counterparts` stands it for this workspace's own record derived from it, created with that ID the first time and found by it after; that needs both workspaces to run one model.
- items: The items, applied in order. 1 to the run's item limit.

### BatchResponse

- job: The job, finished. Read its `result`: `applied` when every item applied, `partial`, or `rejected` when none did.

### BatchCreateItem

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `create`: a new record, as `POST /api/v1/objects`.
- id: The ID the new record gets; one is assigned when omitted. Give one to make a retry safe.
- applicationKey: The application the record belongs to.
- objectTypeKey: The record's object type.
- name: The record's name, 1 to 500 characters.
- parent: The parent, by ID or by a unique attribute's value; resolved when the item runs, so it may be a record an earlier item created.
- attributes: The attribute values, as on the single create.
- initialRelations: The relationships the type requires into the new record, created with it.

### BatchUpdateItem

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `update`: change a record as `PATCH /api/v1/objects/{object_type_key}/{object_id}` does; only the fields given change.
- target: The record to change.
- expectedVersion: The record's `version` you read. A record that equals the update is `unchanged` whatever the version.
- name: The new name.
- parent: The new parent; `null` moves the record to the top level, and omitting it leaves the record where it is.
- attributes: The attribute values to set.

### BatchUpsertItem

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `upsert`: create the record `key` finds none for, otherwise update it as an `update` item would. It never changes an existing record's type or application.
- applicationKey: The application a new record belongs to.
- objectTypeKey: The type of the record found or created.
- key: What finds the record.
- name: The record's name.
- parent: The parent; omitted, an existing record stays where it is.
- attributes: The attribute values; a key by `attributeTypeKey` takes its value from here.
- initialRelations: Used only when the item creates the record.
- expectedVersion: The version of the record found. Without it an upsert that finds a record is refused `VERSION_REQUIRED` unless the request says `onExisting: "overwrite"`.

### UpsertKey

What an upsert finds its record by: an ID the client assigns, or a unique attribute.

- id: The ID of the record; a record created gets it.
- attributeTypeKey: A unique attribute of the type; the record whose value for it is the item's value in `attributes`.

### BatchDeleteItem

Deletes a record, as `DELETE /api/v1/objects/{object_type_key}/{object_id}` does. Without `cascade` a record with dependants is refused with its impact; with it, the impact confirmed by `deletionPreviewToken` is deleted. A preview needs no token: it gives one, and confirming carries it.

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `delete`: delete a record as `DELETE /api/v1/objects/{object_type_key}/{object_id}` does.
- target: The record to delete.
- expectedVersion: The record's `version` you read.
- cascade: `true` deletes the record with the records and relationships that depend on it, under the impact `deletionPreviewToken` confirms. `false` refuses a record with dependants as `OBJECT_HAS_DEPENDANTS`.
- deletionPreviewToken: The token of the impact you were shown. A preview computes it for each item, and confirming the preview carries it into the item.

### BatchCreateRelationItem

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `createRelation`: a new relationship, as `POST /api/v1/relations`.
- relationTypeKey: The relation type.
- from: The record at the start, by ID or by a unique attribute's value.
- to: The record at the end.
- attributes: The relationship's attribute values.
- expectedRelationSetVersion: The version of the relationship set you read; needs `relationSetDirection`.
- relationSetDirection: Which end's set the claim is about: `outgoing` or `incoming`.

### BatchEnsureRelationItem

Creates the relationship unless one of the type already joins the two ends; then it is `unchanged` when `attributes` are omitted or equal, and otherwise an update under `expectedVersion`.

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `ensureRelation`: create the relationship unless one of the type already joins the two records. Then it is `unchanged` when `attributes` are omitted or equal, otherwise updated.
- relationTypeKey: The relation type.
- from: The record at the start.
- to: The record at the end.
- attributes: The relationship's attribute values.
- expectedVersion: The relationship's version, for an update; without it an update needs `onExisting: "overwrite"`.

### BatchEnsureNoRelationItem

Deletes the relationship of the type that joins the two ends, or is `unchanged` when none joins them. `expectedVersion`, when given, claims the relationship's version.

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `ensureNoRelation`: delete the relationship of the type that joins the two records; `unchanged` when none does. A containment is never removed this way.
- relationTypeKey: The relation type.
- from: The record at the start.
- to: The record at the end.
- expectedVersion: When given, the relationship's version; a stale one is `VERSION_CONFLICT`.

### BatchUpdateRelationItem

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `updateRelation`: replace a relationship's attributes, as `PATCH /api/v1/relations/{relation_id}`.
- id: The relationship's ID.
- expectedVersion: The relationship's version you read.
- attributes: The new attribute values, replacing the old.

### BatchDeleteRelationItem

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `deleteRelation`: delete a relationship, as `DELETE /api/v1/relations/{relation_id}`.
- id: The relationship's ID.
- expectedVersion: The relationship's version you read.
- expectedRelationSetVersion: The version of the relationship set you read; needs `relationSetDirection`.
- relationSetDirection: Which end's set the claim is about: `outgoing` or `incoming`.

### BatchReplaceRelationSetItem

Makes `targets` (possibly none) the anchor's whole set of relationships for one binding and direction, under `expectedRelationSetVersion` or the request's `onExisting: "overwrite"`. A preview needs no claim: the outcome names the version found, and confirming carries it.

- ref: Your own name for the item, 1 to 200 characters. Its outcome carries it back.
- op: `replaceRelationSet`: the anchor's set of one binding in one direction becomes `targets`. A target already related keeps its relationship; the others are removed, and new ones created in the order given.
- relationTypeKey: The relation type.
- fromObjectTypeKey: The type at the start of the binding.
- toObjectTypeKey: The type at the end of the binding.
- direction: Whether the anchor is at the start (`outgoing`) or the end (`incoming`).
- anchor: The record whose set is replaced.
- targets: The records the set is to hold; possibly none.
- expectedRelationSetVersion: The set's version you read. A set equal to `targets` is `unchanged` whatever the claim; otherwise it is needed, or `onExisting: "overwrite"`. A preview needs none.

### BatchInitialRelation

- relationTypeKey: The relation type.
- direction: `outgoing` from the new record, or `incoming` to it.
- object: The record at the other end.
- attributes: The relationship's attribute values.

### RelationSetTarget

- object: The record the set holds.
- attributes: The relationship's values. Omitted, a relationship that is kept keeps its values; given, they replace them.

### RecordReference

An existing record, by its ID or by a unique attribute's value on a type.

- id: The record's ID. Use this or the pair `objectTypeKey` and `key`.
- objectTypeKey: The record's type, with `key`.
- key: A unique attribute of that type and the value that finds the record.

### RecordKeyValue

- attributeTypeKey: The unique attribute, bound to the type.
- value: The attribute's value, in its JSON type.

### JobItemResponse

One item's outcome. `applied` carries `action` and the record's `id`, `objectTypeKey` and `version` (no version after a live delete), and `previousVersion` when it overwrote without a version claim. A delete item carries its `impact`, or is `unchanged` with `deletedWithItem`, the earlier item whose impact held its record. A relationship item carries `relationId` and the relationship's `version` (none after a delete), and `relationSetVersion` when it claimed a set. A set replacement carries the anchor's `relationSetVersion`, the version it found (`previousRelationSetVersion`, which confirming a preview carries into the item) and `relationIds`. An `ensureNoRelation` that found no relationship is `unchanged` without `relationId`. `rejected` carries `error`, with the single write's code and a JSON `pointer` into the request in its `details`; `unprocessed` carries `reason`.

- index: The item's position in the job, from 0.
- ref: The item's `ref`; for an import, the row of the file as `{sheet}!{row}`.
- status: `applied`, `rejected` or `unprocessed`. Only the fields of that status follow.
- action: What an applied item did: `created`, `updated`, `unchanged` or `deleted`.
- id: The ID of the record written; none after a live delete.
- sourceId: The ID the request gave, when the record written is its counterpart in this workspace.
- objectTypeKey: The type of the record written.
- version: The record's, or a relationship's, version after the item; none after a delete.
- previousVersion: The version an overwrite replaced, when the item carried no version claim.
- relationId: The relationship the item wrote or removed; none for an `ensureNoRelation` that found none.
- relationSetVersion: The relationship set's new version, for an item that claimed one and for a set replacement.
- previousRelationSetVersion: The version a set replacement found. Confirming a preview carries it into the item.
- relationIds: What a set replacement did to the set's relationships.
- impact: What a delete item removed, with the token that confirms exactly this impact.
- deletedWithItem: The earlier item whose delete already removed this record, for an `unchanged` delete.
- error: Why a rejected item was refused: the single write's `code`, and in `details` a JSON `pointer` into the request.
- reason: Why an unprocessed item did not run: `BATCH_ROLLED_BACK`, `JOB_CANCELLED`, `MODEL_RELEASE_CHANGED` or `JOB_FAILED`.

### RelationIds

What a relationship-set replacement did to the set's relationships.

- created: IDs of the relationships the replacement created.
- kept: IDs of the relationships it left in place.
- removed: IDs of the relationships it removed.

### DeletionImpact

- objectCount: The records deleted: the target and the records that went with it.
- objectsByType: How many records of each type, by type key.
- relationshipCount: The relationships deleted.
- retainedAssociationCount: How many of those relationships reach records that stay.
- deletionPreviewToken: Confirms exactly this impact; send it as `deletionPreviewToken` on a cascading delete.

### JobRowResponse

One row of an import's file. Its `status` is its worst item's (`rejected`, then `unprocessed`, then `applied`), `actions` counts its applied items, and `outcomes` holds its rejected and unprocessed items' outcomes. Every item of the row reads at `GET /api/v1/jobs/{job_id}/items?ref=`.

- ref: The row as `{sheet}!{row}`; `csv!{row}` for a CSV file.
- sheet: The sheet; `null` for a CSV or JSON Lines file.
- row: The row number in the sheet.
- status: The worst status of the row's items: `rejected`, then `unprocessed`, then `applied`.
- actions: The row's applied items by action.
- outcomes: The row's rejected and unprocessed items. Read every item of the row at `GET /api/v1/jobs/{job_id}/items?ref=`.

### JobActions

- created: Items that created a record or relationship.
- updated: Items that updated one.
- unchanged: Items that found nothing to change.
- deleted: Items that deleted one.

### JobGroup

A group of related jobs: the jobs of one `origin` that the request's filters leave, their count per state and the time of the newest.

- origin: The assistant task or model draft the jobs belong to.
- jobs: How many jobs of this origin the filters leave.
- latestAt: When the newest of them was created.

### JobGroupRow

- job: The newest job of the group, or the job itself when `group` is `null`.
- group: The group, or `null` for a job that belongs to no task or draft.

### ColumnReadingChoice

- column: The column's header in the profile.

### ImportRereadRequest

The preview's file read again with other fields, for `POST /api/v1/jobs/{job_id}/reread`.

- readings: The columns to read differently, one entry each.

### JobConfirmation

Confirms a previewed job. A migration names the assignment version and feed position its preview reported and, when it removes anything, `acceptLoss: true`; an import or a batch takes no body.

- expectedVersion: A migration: the workspace's model assignment `version` its preview reported.
- expectedFeedPosition: A migration: the feed position its preview reported.
- acceptLoss: A migration that removes anything needs `true`. Sending it for an import or a batch is ignored.

### ExportRequest

- workspaceKey: The workspace exported.
- context: Where to read: live data when empty, or one change set or one publication.
- include: Whether relationships go in the file.
- format: `jsonl` (batch items), `csv` or `xlsx`.
- view: A view to export in place of `scope`: the records and the workbook come from the view's definition and the state it was narrowed to.
- people: What a workbook for people holds; only with `layout: "people"`.

### ExportContext

- changeSetId: Export the change set's work in progress.
- publicationId: Export this published state. Not with `changeSetId`.

### ExportScope

- types: The object types exported, each once, each with its own criteria.
- asOf: A date (`YYYY-MM-DD`): the types that declare an effective period export the records effective on it; the others are exported undated.

### ExportType

- objectTypeKey: The object type.
- where: Criteria as the model query takes them; all must hold. Empty exports every record of the type.

### ExportView

An export of what a view shows: the engine derives the records and the workbook's shape from the view's definition, so an integrator gets the file the page gets.

- applicationKey: The application that holds the view.
- viewKey: The view's key.
- state: What the page showing the view had narrowed it to.
- cellField: For a matrix whose cells link records: the field of the cell record that each cell lists the linked records by, `name` or an attribute the cell type's records are identified by (its display attribute, or a unique one). The file records the choice and an import reads it back. Left out, a cell lists each record as its name with its display field in parentheses.

### PeopleLayout

What a workbook for people holds: the main sheet's columns as a table view names them, the relationships that get a sheet of their own (relationship keys or reverse keys), and the field a `related:<key>` column shows instead of the related records' names.

- sheets: Relationships that get a sheet of their own, by relation key or reverse key.
- columnFields: For a `related:<key>` column, the field shown instead of the related records' names.
- referenceLists: Relationship keys whose pointer cells offer a list of the records they may choose; every relationship the workbook names when omitted.

### OwnedColumns

An owned relationship's sheet as columns per parent: the parents added to those already holding an owned record of an exported one, and the owned records' fields (`name` or an attribute), each parent getting one column per field.

- parents: Parents to add to those already holding an owned record of an exported record. Each parent gets one column per field.

### MigrationRow

One item a migration changes. `outcome` is `conversion` (a value converted, `VALUE_CONVERTED`, or carried to another attribute, `VALUE_CARRIED`), `reclassified` (a record's type, application or parent changes), `loss` (a record, value or relationship removed), `created` (a record, `RECORD_CREATED`, or a relationship, `RELATION_CREATED`, that a split or a list conversion creates) or `refused` (a record the target release refuses, by the rule's `code` and `path`). A record's item names it; a relationship's names its `relationId` and both ends; a value's names its attribute, with `before` and, when converted, `after`.

- index: The item's position, from 0.
- outcome: `conversion` (a value converted or carried), `reclassified` (a record's type, application or parent changes), `loss` (a record, value or relationship removed), `created` (a record or relationship a split or list conversion creates) or `refused` (the target release refuses a record).
- code: Why: `VALUE_CONVERTED`, `VALUE_CARRIED`, `RECORD_CREATED`, `RELATION_CREATED`, or the rule that refused or removed it.
- objectId: The record the item is about.
- objectName: The record's name.
- objectTypeKey: The record's type now.
- targetObjectTypeKey: Its type in the target release.
- applicationKey: The record's application now.
- targetApplicationKey: Its application in the target release.
- attributeTypeKey: The attribute, for a value.
- targetAttributeTypeKey: The attribute it moves to in the target release.
- relationId: The relationship, for a relationship's item.
- relationTypeKey: The relationship's type.
- toObjectId: The record at the relationship's other end.
- before: The value before.
- after: The value after, when converted.
- path: Where the target release's rule refused it.
- message: In words, what the item does or why it is refused.

### MoveRow

One row of a move's dry run: a record (`kind: record`) or a relationship it holds (`kind: relationship`), with its `outcome` in the target: `create`, `update` (found by its counterpart, `foundBy: counterpart`, or by the mapping's match, `matchedBy`), `refused` (the target's rule) or `notMoved` (the mapping's reason). `updateOriginal` is the original a record moved back finds through its origins (`foundBy: origin`), and a `create` found so is the original created again under its ID. A created record names the `origin` it is recorded with; with `mode: move`, a loaded record names what became of it in the source (`source`). A record not selected (`selected: false`) is one the mapping creates: a parent or a relationship's other end (`missing: create`), or the parent the mapping names by type and name (no `sourceId`). `possibleDuplicates` names up to 10 target records of the type and name a created record has; `parentRow` and `endRows` are the rows of its parent and of a relationship's records, and `rides` is the row of the record whose create carries a relationship the target requires.

- index: The row's position in the move, from 0.
- kind: `record` or `relationship`.
- outcome: In the target: `create`, `update`, `updateOriginal` (the original a record moved back finds), `refused` (the target's rule) or `notMoved` (the mapping's reason).
- reasons: Why the row does not move, or why the target refused it.
- leftBehind: What a moving row leaves behind.
- sourceType: The record's type in the source.
- sourceId: The record's ID in the source; none for a parent the mapping creates by name.
- name: The record's name.
- selected: `false` for a record the mapping creates: a parent or a relationship's other end.
- targetId: The record's ID in the target, when found.
- targetType: Its type in the target.
- targetParentId: The parent in the target.
- parentRow: The row of the record's parent.
- foundBy: How an existing target record was found: `origin`, `counterpart` or `match`.
- origin: The origin a created record is recorded with.
- source: What a `mode: move` did with a loaded record in the source.
- matchedBy: The mapping's match, by attribute.
- possibleDuplicates: Up to 10 target records of the type and name a created record has.
- relationId: The source relationship's ID.
- relationTypeKey: The relation type in the source.
- targetRelationTypeKey: The relation type in the target.
- direction: `outgoing` or `incoming`, as the mapping reads it.
- fromId: The record at the relationship's start, in the source.
- toId: The record at its end, in the source.
- targetFromId: The record at its start, in the target.
- targetToId: The record at its end, in the target.
- endRows: The rows of the relationship's two records.
- rides: The row of the record whose create carries a relationship the target requires.
- fromName: A relationship row's record at its from end, by its name as it is now.
- toName: A relationship row's record at its to end, by its name as it is now.

### MoveReason

- code: `TYPE_NOT_MAPPED`, `PARENT_NOT_FOUND`, `PARENT_TYPE_NOT_MAPPED`, `RECORD_NOT_MOVED`, `RELATION_NOT_MAPPED`, `RELATION_TARGET_LEFT_BEHIND`, `MATCH_AMBIGUOUS`, or the target's refusal.
- message: In words, why.
- action: The mapping step or selection that changes it.
- details: For a refusal, its `details`, with a `pointer` into the batch item.

### MoveLeftBehind

- code: `ATTRIBUTE_NOT_MAPPED`, `VALUE_NOT_CONVERTIBLE`, `ATTRIBUTE_READ_ONLY` (the target holds it read-only) or `EFFECTIVE_PERIOD_DROPPED` (the target type has no period).
- attributeTypeKey: The source attribute.
- pointer: Where it is in the source record.
- targetAttributeTypeKey: The target attribute, when mapped.
- value: The value that could not be converted.

### MoveSourceOutcome

What a `mode: move` did with a loaded record in the source: `deleted` in the source's change set, or `kept` with why (`SOURCE_CHANGED`: it changed since it was read; `OBJECT_HAS_DEPENDANTS`: a record that stays depends on it).

- outcome: `deleted` in the source's change set, or `kept`.
- reasons: Why it was kept: `SOURCE_CHANGED` or `OBJECT_HAS_DEPENDANTS`.

### PrincipalResponse

A person or a client as a read names it now: a renamed or deactivated one reads as it is.

- kind: `user` or `client`.
- id: The person's or client's ID.
- name: The name now; a renamed or deactivated one reads as it is.

### ApiErrorResponse

- error: The refusal.

### ApiErrorBody

- code: The stable code; see the catalogue.
- message: In words, for a person reading a log; it can be reworded.
- details: What the code adds, if anything.

### ExportViewState

What the page showing a view had narrowed it to: the same state the list routes take. Each part applies to the view kinds that read it; a part a kind does not read is refused as `INVALID_EXPORT_LAYOUT`.

### JobGroupPage

Jobs grouped by origin, newest activity first.

### JobItemPage

A job's outcomes in item order.

### JobPage

Jobs, newest first.

### MigrationRowPage

A migration's items in item order.

### MoveRowPage

A move's rows in their order: records as they are created, then relationships.
