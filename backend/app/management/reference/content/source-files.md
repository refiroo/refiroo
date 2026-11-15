# source files

A source file is a workbook or CSV file stored on the engine for a model draft or an import profile. Storing it queues a job that reads every cell and profiles it: sheets, blocks, columns and their statistics. Read the profile to choose a profile's `headerRow`, `block` and bindings, then import the stored file by `sourceFileId` or check it against the profile. A file lives as long as its owner; a newer file of the same owner supersedes it.

1. `POST /api/v1/source-files`, then follow the profile job named in its answer.
2. Read `.../profile/sheets`, `.../columns` and `.../cells` once `profile.state` is `completed`.

## POST /api/v1/source-files

Title: Store a source file

Stores a workbook or CSV file for a model draft or an import profile and queues the job that profiles it. Send `multipart/form-data`: the `request` part as JSON and the `file` part. A newer file of the same owner (for a profile, in the same workspace) supersedes the earlier one, which stays readable until retention deletes it. Name `workspaceKey` for a profile's file: a check reads only its workspace's.

### Errors

- 403 FORBIDDEN: needs Bulk and import, for a profile's file in the workspace
- 403 FORBIDDEN: `owner.draftId` is not the session's draft
- 409 AI_TASK_DRAFT_HELD: `owner.draftId` is a draft another task holds
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 MODEL_DRAFT_NOT_FOUND: `owner.draftId` names no draft
- 404 IMPORT_PROFILE_NOT_FOUND: `owner.profileKey` names no profile
- 413 IMPORT_TOO_LARGE: the file is over the import limit
- 422 REQUEST_VALIDATION_ERROR: a part is missing or `owner` names both or neither
- 422 UNSUPPORTED_FILE_FORMAT: the file is neither XLSX nor CSV
- 422 IMPORT_PROFILE_MODEL_MISMATCH: the workspace runs another model than the profile's

## GET /api/v1/source-files

Title: List source files

Lists stored files, newest first: all of them, a draft's, or a profile's. A profile's files are listed to the person or client that stored them and to holders of Bulk and import in their workspace.

### Parameters

- draftId: Only this model draft's files.
- profileKey: Only this profile's files.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: needs Bulk and import in some workspace
- 403 FORBIDDEN: `draftId` is not the session's draft
- 409 AI_TASK_DRAFT_HELD: `draftId` is a draft another task holds
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/source-files/{source_file_id}

Title: Get a source file

Reads a stored file with the state of its profile. Follow `profile.jobId` until `profile.state` is `completed`, or `failed` with its error. A profile's file can be read by whoever stored it and by holders of Bulk and import in its workspace.

### Parameters

- source_file_id: The source file's ID.

### Errors

- 403 FORBIDDEN: a profile's file you may not use, or a foreign draft's
- 409 AI_TASK_DRAFT_HELD: the file belongs to a draft another task holds
- 404 SOURCE_FILE_NOT_FOUND: no source file has this ID

## DELETE /api/v1/source-files/{source_file_id}

Title: Delete a source file

Deletes the file with its staged cells and profile, at `expectedVersion`. Jobs still reading it are asked to stop first. The owner's deletion removes its files too.

### Parameters

- source_file_id: The source file's ID.
- expectedVersion: The file's `version`.

### Errors

- 403 FORBIDDEN: a profile's file you may not use, or a foreign draft's
- 409 AI_TASK_DRAFT_HELD: the file belongs to a draft another task holds
- 404 SOURCE_FILE_NOT_FOUND: no source file has this ID
- 409 VERSION_CONFLICT: `expectedVersion` is not current
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing

## GET /api/v1/source-files/{source_file_id}/profile/sheets

Title: List a file's sheets

Lists the file's sheets in workbook order, each with its blocks: runs of columns between empty columns, or the lists of a sheet laid out for reading. A block's `headerRow` and `range` are the values a profile source takes as `headerRow` and `block`. A CSV file is one sheet.

### Parameters

- source_file_id: The source file's ID.
- pageSize: 1 to 500; 50 by default.

### Errors

- 403 FORBIDDEN: a profile's file you may not use, or a foreign draft's
- 409 AI_TASK_DRAFT_HELD: the file belongs to a draft another task holds
- 404 SOURCE_FILE_NOT_FOUND: no source file has this ID
- 409 SOURCE_FILE_PROFILE_NOT_READY: the profile is not stored yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/columns

Title: List a sheet's columns

Lists a sheet's columns, block by block and in column order, with what helps to choose a binding: how many cells are filled and distinct, which value types they read as, whether the column could be a key, its delimiters and placeholders, its most frequent values, and the columns and records that hold the same values.

### Parameters

- source_file_id: The source file's ID.
- sheet: The sheet's name.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: a profile's file you may not use, or a foreign draft's
- 409 AI_TASK_DRAFT_HELD: the file belongs to a draft another task holds
- 404 SOURCE_FILE_NOT_FOUND: no source file has this ID
- 404 SOURCE_SHEET_NOT_FOUND: the file has no such sheet
- 409 SOURCE_FILE_PROFILE_NOT_READY: the profile is not stored yet
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## GET /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/cells

Title: Read a range of a sheet

Lists the rows of a rectangle that hold a cell, in row order, each cell as an import matches it: its staged text and its value type. A row with no cell in the range is left out.

### Parameters

- source_file_id: The source file's ID.
- sheet: The sheet's name.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: a profile's file you may not use, or a foreign draft's
- 409 AI_TASK_DRAFT_HELD: the file belongs to a draft another task holds
- 404 SOURCE_FILE_NOT_FOUND: no source file has this ID
- 404 SOURCE_SHEET_NOT_FOUND: the file has no such sheet
- 409 SOURCE_FILE_PROFILE_NOT_READY: the profile is not stored yet
- 422 INVALID_RANGE: `range` is malformed, empty or outside the sheet
- 422 REQUEST_VALIDATION_ERROR: `range` is missing or a parameter is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero

## Schemas

### SourceFileRequest

The `request` part of `POST /api/v1/source-files`. `workspaceKey` names the workspace whose records the profile compares the columns with; without it, columns are compared with each other only.

- owner: The model draft or the import profile the file belongs to.
- format: `xlsx` or `csv`; otherwise from the file name's suffix.
- csv: How a CSV file is read.
- workspaceKey: The workspace whose records the profile compares the columns with, and whose file of the profile this is. A profile's file is current per workspace.

### SourceFileOwner

- draftId: The model draft the file belongs to. Exactly one of `draftId` and `profileKey`.
- profileKey: The import profile the file belongs to.

### SourceFileOwnerResponse

- draftId: The model draft that owns the file; `null` for a profile's.
- profileKey: The import profile that owns the file; `null` for a draft's.

### SourceFileResponse

A file that a model draft or an import profile owns. `supersededAt` is set once a newer file of the same owner arrived; the file is deleted `JOB_RETENTION_DAYS` later.

- id: The file's ID.
- name: The file's name as it was sent.
- format: `xlsx` or `csv`.
- bytes: The file's size.
- sha256: The file's SHA-256, in hexadecimal.
- owner: Who owns the file.
- csvDelimiter: The delimiter a CSV file is read with; `null` for a workbook.
- uploadedAt: When the file was stored.
- supersededAt: When a newer file of the same owner arrived; the file is deleted after the retention days. `null` while it is the current one.
- version: Send it as `expectedVersion` to delete the file.
- profile: Where the file's profile stands.
- workspaceKey: The workspace whose records the profile compared the columns with.

### SourceFileProfileState

- state: `completed` once the profile is stored, otherwise its job's state: `queued`, `running`, `failed`, `cancelled` or `expired`.
- jobId: The profile job.
- error: Why the job failed.

### SourceSheetResponse

- index: The sheet's position in the workbook, from 0.
- name: The sheet's name.
- blocks: The blocks of the sheet, in the order they are found.
- laidOut: Laid out for reading: lists side by side or stacked, read list by list.

### SourceBlock

A run of columns holding cells, between empty columns; on a sheet laid out for reading, one list of such a run, between empty rows. It can be used as an import profile source's `headerRow` and `block`.

- index: The block's position on the sheet, from 0.
- range: The block as cells, such as `A3:C12`.
- firstColumn: The first column letter.
- lastColumn: The last column letter.
- headerRow: The header row: the first row whose cells are all text and fill every column; `null` when there is none.
- lastRow: The last row with a cell.
- note: A note under a list's header, when there is one.
- titles: The titles above the list, the outermost first.

### SourceBlockNote

A note under a list's header: its row, its text and what it says of the list: `many` answers, `one`, `free` (a free field, no list), or `heading`: a second header row, answering none of the list's yes/no columns.

- row: The note's row.
- text: The note's text.
- meaning: What it says of the list: `many` answers, `one`, `free` (a free field, not a list) or `heading` (a second header row).

### SourceColumnResponse

A column of a block, with its statistics over the rows below the block's header, the block's note left out.

- sheet: The sheet's name.
- letter: The column letter.
- header: The header text; `null` when the cell is empty.
- block: The block's position on the sheet.
- rows: The rows below the block's header.
- filled: How many of them hold a value.
- distinct: How many distinct values they hold.
- delimiters: Characters that cut cells into several values, with how many cells hold each.
- placeholders: Values that stand for no value, such as `n/a`, `-`, `?` or `TBD`, at most 10, with their counts.
- overlaps: The columns, and records of the workspace, that hold most of this column's distinct values.
- limits: How many values were compared and listed.
- values: The most frequent values with their counts.

### SourceColumnLimits

- overlapsListed: At most this many overlaps are listed.
- placeholdersListed: At most this many placeholders are listed.

### SourceDelimiter

- character: The delimiter: `;`, `,`, `|`, `/` or a line break.
- cells: How many cells hold it.
- share: Their share of the column's filled cells.

### SourcePlaceholder

- value: The value, as it appears in the file.
- count: How many cells hold it.

### SourceOverlap

- values: How many of the column's compared distinct values the other holds.
- share: Their share of the compared values.
- sheet: Another column's sheet.
- column: Another column's letter.
- block: Its block, on a sheet laid out for reading.
- header: Its header.
- workspaceKey: The workspace whose records hold the values.
- objectTypeKey: The type whose records hold them.
- field: `name`, when the record names hold them.
- attributeTypeKey: The attribute that holds them.

### SourceCellRow

- row: The row number.

### SourceCell

- text: The cell as text, as an import matches it.

### SourceCellPage

The rows of a range holding a cell, in row order.

### SourceFilePage

Source files, newest first.
