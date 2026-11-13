# imports

An import profile says how a workbook's or a CSV file's sheets and columns become records and relationships. Save one, send a file through it, and the import runs as a job (see `jobs`). A preview shows the outcome without writing and waits for you. Profiles belong to the whole instance and to one model; a workspace running another model cannot use them. A profile's next file can be checked against the data before it is loaded.

1. `POST /api/v1/import-profiles`, then store a workbook with `POST /api/v1/source-files`.
2. `POST /api/v1/imports` with `stage: preview`, read the rejected rows, then `POST /api/v1/jobs/{job_id}/confirm`.

## GET /api/v1/import-profiles

Title: List import profiles

Lists the instance's import profiles in key order, each read under the release of `workspaceKey` (the default workspace when omitted) and with its last load.

### Parameters

- workspaceKey: The workspace whose model release each profile is checked against; the default workspace when omitted.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import in some workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## POST /api/v1/import-profiles

Title: Save an import profile

Saves a profile. It is checked against the model release that `workspaceKey` runs (the default workspace's when omitted), and a profile with problems is refused with every one at its JSON pointer. The profile then belongs to that release's model.

### Errors

- 403 FORBIDDEN: needs Bulk and import in some workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 409 IMPORT_PROFILE_EXISTS: the key is in use
- 422 INVALID_IMPORT_PROFILE: the profile does not fit the model
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid

## GET /api/v1/import-profiles/{profile_key}

Title: Get an import profile

Reads a profile with `valid` and `problems` as it reads under the release of `workspaceKey`, so a profile that a later release broke shows what to fix. It also carries its last load: the latest import that named it, and what became of what it loaded.

### Parameters

- profile_key: The profile's key.
- workspaceKey: The workspace whose model release the profile is checked against; the default workspace when omitted.

### Errors

- 403 FORBIDDEN: needs Bulk and import in some workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace

## PUT /api/v1/import-profiles/{profile_key}

Title: Replace an import profile

Replaces the whole profile at `expectedVersion` and raises its `version`. The new profile is checked as a new one is. A workspace running another model than the profile's cannot replace it.

### Parameters

- profile_key: The profile's key.

### Errors

- 403 FORBIDDEN: needs Bulk and import in some workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 409 IMPORT_PROFILE_VERSION_CONFLICT: `expectedVersion` is not current
- 422 INVALID_IMPORT_PROFILE: the profile does not fit the model
- 422 IMPORT_PROFILE_MODEL_MISMATCH: the workspace runs another model
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid

## DELETE /api/v1/import-profiles/{profile_key}

Title: Delete an import profile

Deletes a profile at `expectedVersion`. Its stored files go with it; an import that already ran keeps its outcomes.

### Parameters

- profile_key: The profile's key.
- expectedVersion: The profile's `version`.

### Errors

- 403 FORBIDDEN: needs Bulk and import in some workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 409 IMPORT_PROFILE_VERSION_CONFLICT: `expectedVersion` is not current
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing

## POST /api/v1/imports

Title: Import a file

Loads a file into `workspaceKey`'s live data, or into a change set, as a background job. Send `multipart/form-data`: the `request` part as JSON, and the `file` part or a stored file's `sourceFileId`. A profile reads XLSX and CSV; JSON Lines and an export's own tables need none. A file that does not fit fails the job, not the request. With `stage: preview` nothing is written until you confirm.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace, or in the stored file's
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 IMPORT_PROFILE_NOT_FOUND: `profileKey` names no profile
- 404 SOURCE_FILE_NOT_FOUND: `sourceFileId` names no file, or an assistant task's workbook
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 MODEL_RELEASE_CHANGED: the context runs another release than the header names
- 409 IDEMPOTENCY_IN_PROGRESS: the key's job is still running
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged
- 410 SOURCE_FILE_MISSING: the stored file is gone from the job file directory
- 413 IMPORT_TOO_LARGE: the file is over the import limit
- 422 INVALID_BATCH_CONTEXT: both or neither of `workspaceKey` and `changeSetId`
- 422 IDEMPOTENCY_KEY_REUSED: the key belongs to another request or file
- 422 REQUEST_VALIDATION_ERROR: a part is missing; the file and `sourceFileId` both or neither
- 422 UNSUPPORTED_FILE_FORMAT: the file is not XLSX, CSV or JSON Lines
- 422 IMPORT_FILE_UNREADABLE: a workbook sent without a profile cannot be read
- 422 INVALID_IMPORT_PROFILE: the profile does not fit the model
- 422 IMPORT_PROFILE_MODEL_MISMATCH: the workspace runs another model
- 422 MISSING_DELETE_NEEDS_CHANGE_SET: a live load of a profile that deletes

## POST /api/v1/import-profiles/{profile_key}/check

Title: Check a profile's file

Starts a job that reads the profile's current file in `workspaceKey` against the profile and the workspace's data, and writes nothing. Run it after storing a new workbook for the profile or after changing the profile; a check still running is cancelled. `GET .../check` reads the result.

### Parameters

- profile_key: The profile's key.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 SOURCE_FILE_NOT_FOUND: the profile holds no file in the workspace
- 409 SOURCE_FILE_PROFILE_NOT_READY: the file is not profiled yet
- 422 REQUEST_VALIDATION_ERROR: `workspaceKey` is missing

## GET /api/v1/import-profiles/{profile_key}/check

Title: Read a profile's check

Reads the latest check of the profile's file in `workspaceKey`. While it is `checking` only its identifiers are known; then it reports the columns new, missing and renamed against the earlier file, the profile against the active release, what a load would do, and the counts behind the three finding lists.

### Parameters

- profile_key: The profile's key.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 PROFILE_CHECK_NOT_FOUND: no file of the profile was checked there yet
- 422 REQUEST_VALIDATION_ERROR: `workspaceKey` is missing

## GET /api/v1/import-profiles/{profile_key}/check/new-values

Title: List a check's new values

Lists the values of match columns that name no record, in source, column and value order: the load creates each (`created`) or refuses it.

### Parameters

- profile_key: The profile's key.
- source: Only this source, by its place in the load order.
- pageSize: 1 to 1,000; 100 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 PROFILE_CHECK_NOT_FOUND: no file of the profile was checked there yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/import-profiles/{profile_key}/check/drift

Title: List a check's renamed records

Lists the rows whose key finds a record that is named otherwise, in source and row order. A load that overwrites renames the record to the row's name.

### Parameters

- profile_key: The profile's key.
- source: Only this source, by its place in the load order.
- pageSize: 1 to 1,000; 100 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 PROFILE_CHECK_NOT_FOUND: no file of the profile was checked there yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/import-profiles/{profile_key}/check/missing-records

Title: List the records a file leaves out

Lists the records of a source's type that no row of the file names, in source and name order. A load keeps them, or deletes them into a change set when the source says `missing: delete`.

### Parameters

- profile_key: The profile's key.
- source: Only this source, by its place in the load order.
- pageSize: 1 to 1,000; 100 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 PROFILE_CHECK_NOT_FOUND: no file of the profile was checked there yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/import-profiles/{profile_key}/check/rows

Title: List a check's rows

Lists the rows behind the check's figures, in source then row order, as `GET /api/v1/jobs/{job_id}/rows` lists an import's. Nothing was written: `applied` means the row would load.

### Parameters

- profile_key: The profile's key.
- source: Only this source, by its place in the load order.
- status: Only rows whose worst outcome is this.
- pageSize: 1 to 1,000; 500 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import in the workspace
- 404 IMPORT_PROFILE_NOT_FOUND: no profile has this key
- 404 PROFILE_CHECK_NOT_FOUND: no file of the profile was checked there yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## Schemas

### ImportProfileCreate

A new profile, checked against the release of `workspaceKey` (the default workspace without it), whose model it then belongs to.

- key: The profile's key: 1 to 160 letters, digits, `_`, `.` or `-`, starting with a letter or digit.
- name: The profile's name, 1 to 200 characters.
- workspaceKey: The workspace whose release the profile is checked against; the default workspace when omitted. The profile belongs to that release's model.
- csv: How a CSV file is read.
- sources: The object types the file loads, each from a sheet (a CSV file is one sheet). At least one.
- valueMaps: Named maps from a cell's text to another value, applied before the cell is converted or matched; `null` means no value. A column names one in `valueMap`.

### ImportProfileUpdate

- name: The profile's name, 1 to 200 characters.
- expectedVersion: The profile's `version` you read.
- workspaceKey: The workspace whose release the profile is checked against; the default workspace when omitted. It must run the profile's model.
- csv: How a CSV file is read.
- sources: The object types the file loads. At least one.
- valueMaps: Named maps from a cell's text to another value; `null` means no value.

### ImportProfileResponse

A stored profile. `checkedAgainst` is the release it was saved against and `modelKey` that release's key, the model the profile belongs to. `valid` and `problems` say how it reads under the release of the workspace asked for, so a profile that a later release broke shows what to fix before an import is refused for it. In a workspace running another model it reads as not valid, with the one problem `IMPORT_PROFILE_MODEL_MISMATCH`.

- key: The profile's key.
- name: The profile's name.
- version: Rises by one with every replacement; send it as `expectedVersion`.
- checkedAgainst: The ID of the model release the profile was last saved against.
- modelKey: That release's model key. The profile can be used only in workspaces running this model.
- lastLoad: The latest import that named the profile; `null` before the first, and once that job passed retention.
- valid: Whether the profile fits the release of the workspace asked for. In a workspace running another model it is `false`.
- problems: What does not fit, each at its pointer into the profile.
- createdAt: When the profile was first saved.
- updatedAt: When it was last replaced.
- csv: How a CSV file is read; left out when the profile sets nothing.
- sources: The object types the file loads, in the order they were written; they run in order of their references.
- valueMaps: The named value maps.

### ImportProfileProblem

- path: The JSON pointer of the offending part of the profile; empty for the profile as a whole.
- code: What is wrong, such as `UNKNOWN_OBJECT_TYPE`, `UNKNOWN_ATTRIBUTE`, `KEY_NOT_BOUND`, `RELATION_NOT_ALLOWED` or `IMPORT_PROFILE_MODEL_MISMATCH`.
- message: In words, what is wrong.

### ImportProfileLastLoad

The latest import naming the profile and what became of what it loaded: `live` (loaded into live data), `inChangeSet` (its change set still holds it), `published` (`publicationId`) or `discarded` (its change set is gone and no publication of it is on record); null until the job completes. A job past its retention is not found.

- jobId: The import's job.
- state: The job's state.
- fileName: The file's name; `null` for a stored file read in place of one sent.
- workspaceKey: The workspace loaded into.
- changeSetId: The change set it loaded into; `null` for live data.
- createdAt: When the import was sent.
- finishedAt: When it ended; `null` while it runs.
- counts: What it did, in records.
- outcome: Once completed: `live`, `inChangeSet` (its change set still holds it), `published` or `discarded`. `null` until then.
- publicationId: The publication that published it, with `published`.

### ImportLoadCounts

- created: Records created.
- updated: Records updated.
- deleted: Records deleted.
- rejected: Rows refused.

### ImportRequest

The `request` part of `POST /api/v1/imports`. A stored profile by `profileKey`, one given inline, or neither for a JSON Lines file or an export's table layout. `stage: execute` runs the import as soon as its file is bound; `stage: preview` runs it without writing and waits for `POST /api/v1/jobs/{job_id}/confirm`.

- workspaceKey: The workspace whose live data the import changes. Exactly one of `workspaceKey` and `changeSetId`.
- changeSetId: The change set the import writes into.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.
- profileKey: A stored profile. Not with `profile`.
- profile: A profile given in the request. Not with `profileKey`. Without either, the file is JSON Lines, an export's tables, or a workbook that carries its own profile.
- format: `xlsx`, `csv` or `jsonl`; otherwise from the file name's suffix.
- policy: `independent` loads the rows that bind; `atomic` loads all or none, and a refused row stops the import before anything is written.
- onExisting: `reject` (the default) refuses a found record whose row carries no version; `overwrite` updates it. A row equal to its record is `unchanged` either way.
- otherWorkspaceIds: As on a batch: `refuse` (the default) or `counterparts`.
- stage: `execute` runs the import once its file is bound. `preview` runs it without writing and waits for confirmation.
- sourceFileId: A stored source file to import in place of the file part.

### ProfileCheckResponse

The check of an import profile's latest file: `checking` while its job runs, then `completed` with the report, `failed` with the error, or `cancelled` when a newer check started. `valid` and `problems` are the profile against `releaseId`, the active release the check ran under; `dryRun` is what the load would do, null when the profile has problems or nothing of the file could be read through it.

- jobId: The check's job.
- state: `checking` while it runs, then `completed`, `failed`, `cancelled` (a newer check started) or `expired`.
- profileKey: The profile checked.
- profileVersion: The version of the profile read; `null` when it was gone.
- sourceFileId: The stored file checked.
- previousSourceFileId: The file the profile read before, which the columns are compared with; `null` when there is none.
- workspaceKey: The workspace the file belongs to and is checked in.
- releaseId: The active release the check ran under.
- valid: Whether the profile fits that release.
- problems: What does not fit, each at its pointer. A profile with problems is not read.
- sources: Per source of the profile, what the check found.
- dryRun: What a load would do: the file bound through the profile into live data with `onExisting: "overwrite"`, every item previewed and nothing written. `null` when the profile has problems or nothing could be read.
- bindingReport: What binding made of each column's cells.
- error: Why the check failed.

### CheckSource

- profileSource: The source's place in the profile.
- source: Its place in this check's load order, as the finding routes take it; `null` when the check did not read it.
- sheet: The sheet it reads.
- objectTypeKey: The object type it loads.
- missing: What a load does with the records of the type no row names: `report` or `delete`.
- sheetFound: Whether the file has the sheet.
- columns: How the file's columns differ from the profile and from the earlier file.
- newValues: Values of its match columns that name no record.
- drift: Rows whose key finds a record named otherwise.
- missingRecords: Records of its type no row names.

### CheckColumns

- renamed: Columns the profile names that the file holds under another header at the same position.

### CheckNewColumn

- column: The header.
- letter: The column's sheet letter.

### CheckMissingColumn

- column: The header the profile names that the file lacks.

### CheckRenamedColumn

A column the profile names that the file holds under another header at the same position, sharing `shared` of the larger distinct value count (at least half).

- from: The header the profile names.
- to: The header the file has in the same position.
- letter: The column's sheet letter.
- shared: The share of the larger distinct value count the two columns hold in common; at least a half.

### CheckNewValue

- source: The source, by its place in the load order.
- column: The match column's header.
- value: The value that names no record.
- created: `true` when the load creates a record named by it (`missing: create`); `false` when the load refuses the rows.
- cells: How many cells hold it.

### CheckDrift

- source: The source, by its place in the load order.
- row: The row of the file.
- recordId: The record the row's key finds.
- key: The key's value.
- name: The name the row gives.
- recordName: The record's name now.

### CheckMissingRecord

A record of the source's type with the key filled that no row names.

- source: The source, by its place in the load order.
- recordId: The record no row names.
- name: Its name.
- key: Its key value.

### Block

- firstColumn: The block's first column letter.
- lastColumn: The block's last column letter.
- lastRow: The block's last row; omitted, as far as the sheet goes.

### CsvOptions

- delimiter: The character a CSV file separates cells with; a comma by default.

### Source

One object type loaded from a sheet (the first sheet when omitted, the file for a CSV). `record: existing` finds each row's record by its key and writes only its relationships and related records. A source with a `parent` binds no column as a parent, and a source keyed by name whose rows have a parent finds a row's record among that parent's children.

- sheet: The sheet; the first when omitted, and the file for a CSV.
- headerRow: The row that holds the headers, from 1. A repeated header name keeps its first column, and later ones read `Name #2`.
- block: A rectangle of the sheet; its first row is the header row.
- applicationKey: The application the type belongs to.
- objectTypeKey: The type each row loads.
- record: `upsert` (the default) finds a row's record by `key` and creates it otherwise. `existing` finds it by `key` and writes only its relationships and related records.
- key: What finds a row's existing record. Without it every row creates a record, so sending the file twice creates twice.
- columns: What each column fills; columns not named are ignored. At least one.
- missing: What a load does with records of the type the context holds with the key filled that no row names: `report` (the default) or `delete`, which a load into a change set only may do.
- rowsWithoutKey: What a load does with a row whose key is empty after value maps: `refuse` (the default, `MISSING_RECORD_KEY`) or `skip`, counted as skipped.
- parent: One parent for every row. A source with it binds no `parent` column.
- under: Marks the source as a value sheet: the records one column record of a matrix offers.
- headings: Rows holding only a heading, in the heading column, are read as the parent of the rows beneath them: the heading's text fills a new column that a `parent` binding can name. Applied before `fillDown` and `unpivot`.
- fillDown: Columns repeated by blanks: an empty cell takes the nearest filled cell above it in its column, within its heading group: a heading row starts a new group, so a value never carries across headings. Applied after `headings` and before `unpivot`.
- unpivot: A wide table read as rows: each filled cell of the listed columns becomes a row, with the column's header in one new column and the cell in another, which bindings name like any column. Applied last.

### Unpivot

A wide table read as rows. The listed columns keep their cells but are not read as such. A row whose listed cells are all empty gives no row.

- columns: The headers of the wide columns, at least two, each once.
- nameColumn: The new column holding the header of the column each row came from.
- valueColumn: The new column holding the cell.

### HeadingRows

Rows grouped under a heading. A row whose only filled cell is in `column` is a heading and no record; a data row therefore holds a value in some other column.

- column: The header of the column holding the heading.
- into: The new column holding the heading on every row beneath it, until the next heading; empty above the first.

### SourceKey

What finds a row's existing record: one unique attribute (its value from the column that binds it), several attributes whose values together find it (`attributeTypeKeys`), a column holding the record's ID, or its name (`field: name`, from the column that binds the name, for a list of names without codes). `versionColumn` holds the version the row claims for the record it finds, so a record changed since the file was written is refused. `nameColumn`, with an ID column and `record: existing`, finds a row's record by its name when the ID cell is empty.

- attributeTypeKey: A unique attribute whose value the row's column supplies.
- attributeTypeKeys: Two or more attributes whose values together find one record; none needs to be unique.
- column: A column holding the record's ID.
- field: `name`: the record of the type with the name the row's `name` column gives.
- nameColumn: With `column` and `record: existing`: finds a row's record by its name when its ID cell is empty.
- versionColumn: The column holding the version the row claims; a record changed since the file was written is `VERSION_CONFLICT`.
- storedUnique: With `attributeTypeKey`: the attribute is not declared unique but its stored values identify one record each.

### FixedParent

One parent for every row of a source: the record `matchBy` finds for `value`, as a related record's fixed parent.

- objectTypeKey: The parent's type.
- matchBy: How the record is found.
- value: The value `matchBy` compares, the same for every row.
- missing: `create` creates a missing parent named by `value` (`matchBy` name only); `refuse`, the default, refuses every row.

### SourceUnder

A sheet that lists the records one column record of a matrix offers (a value sheet): records of the source's type under the column record `value` (of `objectTypeKey`), for the matrix of `relationTypeKey` (read in `direction` from `rowObjectTypeKey` records). A row with a key finds its record and updates it; a row without one is a new record in the place the relationship's candidate rules give under the column record, when `creates`, and is refused otherwise. A value another sheet of the file names (a link column of the same column record) finds the record of the row that holds it.

- relationTypeKey: The matrix's relation type.
- direction: The direction the matrix reads the relation, from the row records.
- rowObjectTypeKey: The type of the matrix's row records.
- objectTypeKey: The type of the column record.
- value: The column record, by the value that finds it.
- creates: `true` makes a row without a key a new record in the place the relationship's candidate rules give under the column record; otherwise such a row is refused.

### ColumnBinding

One column (or, for `relationFlags`, several) and what it fills. `valueMap` names a map applied to the cell's text before it is converted or matched. A repeated header name keeps its first column, and later ones read `Currency #2`. A column is named by its header (`column`) or by its sheet letter (`letter`), which reaches a column whose header cell is empty; give exactly one.

- column: The column, by its header. Exactly one of `column` and `letter`.
- letter: The column, by its sheet letter, which reaches a column whose header is empty or repeated.
- columns: For `relationFlags` only: the flag columns, by header.
- field: `name`: the column fills the record's name.
- attributeTypeKey: The column fills this writable attribute.
- parent: The column names the record's parent.
- relation: The column names records the row's record is related to.
- relationFlags: Each of the columns stands for one record.
- relatedRecord: The column is one value of a related record.
- ignore: `true` leaves the column out.
- valueMap: The value map applied to the cell's text first.

### ParentBinding

- objectTypeKey: The parent's type.
- matchBy: How the cell finds the parent.
- missing: `create`: a cell naming no record creates one with that name (`matchBy` name only). `refuse`, the default, refuses the row.

### MatchBy

- field: `name` or `id`: compare the cell with the record's name or ID.
- attributeTypeKey: Compare the cell with this attribute's value. Exactly one of `field` and `attributeTypeKey`.

### RelationBinding

A relationship from the row's record (`outgoing`) or to it (`incoming`) to each record a cell matches. `split` cuts the cell into several values; `replace` makes the matched records the whole set instead of adding to it. For a row that is one relationship, `idColumn` holds the related record's ID, which finds it when filled and otherwise the cell's match does, `attributes` are the relationship's values, and `versionColumn` claims a version: the set's with `replace`, the relationship's without.

- relationTypeKey: The relation type.
- direction: `outgoing` from the row's record (the default) or `incoming` to it.
- objectTypeKey: The type of the records the cell names.
- matchBy: How the cell finds them.
- split: A delimiter that cuts the cell into several values.
- replace: `true` makes the matched records the whole set, as a set replacement, instead of adding to it.
- idColumn: One relationship per row: the column holding the related record's ID, which finds it when filled.
- versionColumn: The column holding the version the row claims: the set's with `replace`, otherwise the relationship's.
- attributes: One relationship per row: columns holding the relationship's own values.
- missing: `create`: a cell naming no record creates one with that name (`matchBy` name only). `refuse`, the default, refuses the row.
- within: For a link matrix: this column is one column record's part of the row's set.

### RelationValue

- column: The column holding the value.
- attributeTypeKey: The relationship's attribute it fills.

### RelationWithin

A relationship column that is one column record's part of the row's set, as in a link matrix. Its cell lists the records of the binding's type that stand under the column record `value` (of `objectTypeKey`), each as the record's name with its `labelAttributeTypeKey` value in parentheses or as its name alone; the records are found among those only. With `replace` the cell makes the row's links to the records under the column record exactly those listed, and changes no other link of the set; an empty cell changes nothing. `container` is where a name that finds no record is created (`missing: create`); without one such a name refuses the row.

- objectTypeKey: The type of the column record.
- value: The column record, by the value that finds it.
- labelAttributeTypeKey: With no `field`: an attribute shown in parentheses after the name.
- field: The field of the cell record each listed value is: `name` or an attribute that identifies its records. Left out, the import guesses it and shows the guess in the preview.
- container: Where a value that finds no record creates one.

### ContainerRecord

- objectTypeKey: The container's type.
- value: The container, by its ID.

### FlagsBinding

- relationTypeKey: The relation type.
- direction: `outgoing` from the row's record (the default) or `incoming` to it.
- objectTypeKey: The type of the records the flags stand for.
- matchBy: How a target is found.
- targets: Each flag column's header and the name of the record it stands for.
- trueValues: Cell texts counted as set, ignoring case; a boolean TRUE cell is set. `x`, `yes`, `y`, `true` and `1` by default.
- missing: `create`: a set flag whose record does not exist creates it, named by the target. `refuse`, the default, refuses the row.

### RelatedRecordBinding

A record of `objectTypeKey` under `parent`, related to the row's record by `relationTypeKey`; this column is one of its values. Columns naming the same relationship, type and parent fill one related record.

- relationTypeKey: The relation type that joins the row's record to the related record.
- direction: `outgoing` from the row's record (the default) or `incoming` to it.
- applicationKey: The related record's application.
- objectTypeKey: The related record's type.
- parent: Where a new related record stands.
- under: In place of `parent`: a column record under which a new record goes in the place the relationship's candidate rules give.
- idColumn: The column holding the related record's ID.
- field: `name`: this column fills the related record's name. Exactly one of `field` and `attributeTypeKey`.
- attributeTypeKey: This column fills this attribute of the related record.
- matchBy: Narrows which related record the row means, by one of its own values.
- versionColumn: The column holding the version the row claims for the related record; the text `not loaded` leaves it out of the row.

### RelatedParent

Where a related record stands: the record `matchBy` finds for a fixed `value`, or for the row's cell in `column`, through `valueMap` when one is named (a language word mapped to the language record's ID).

- objectTypeKey: The parent's type.
- matchBy: How the record is found.
- value: A fixed value for every row. Exactly one of `value` and `column`.
- column: The column whose cell is the value.
- valueMap: A value map applied to the cell first.
- missing: `create`: a parent no record matches is created with the value as its name (`matchBy` name only). `refuse`, the default, refuses the row.

### RelatedMatch

- attributeTypeKey: The related record's attribute the cell is compared with.

### InlineProfile

- name: A name for the profile; it is not stored.
- csv: How a CSV file is read.
- sources: The object types the file loads. At least one.
- valueMaps: Named maps from a cell's text to another value.

### DryRunSummary

- coverage: Always `complete`: every row is counted.
- rows: How many rows the file has and how many ran.
- sources: What each source's rows would do, in load order.
- difference: What changed since the earlier completed dry run of the file; `null` for the first.
- previousJobId: The earlier dry run's job.
- ranAt: When it ran.

### DryRunRows

- total: Rows in the file's sources.
- run: Rows run.

### DryRunSource

- source: The source's place in the load order.
- profileSource: Its place in the profile.
- sheet: The sheet.
- objectTypeKey: The object type.
- rows: Rows read.
- records: What the rows would do to records.
- values: Attribute values that would be written.
- relationships: Relationships that would be written.
- relatedRecords: Related records that would be written.
- rejections: The refusals, counted by code.
- missingRecords: Records of the type that no row names.
- skippedRows: Rows without a key that the source skips (`rowsWithoutKey: skip`).

### DryRunRecords

- created: Records that would be created.
- updated: Records that would be updated.
- unchanged: Records that already equal their row.
- deleted: Records missing from the file that the source deletes.

### DryRunRejection

- code: The refusal's code.
- rows: How many rows it refuses.

### DryRunDifference

- source: The source's place in the load order.
- objectTypeKey: The object type.
- sheet: The sheet.

### DryRunFigure

- now: The figure in this run.
- was: The figure in the earlier run.
