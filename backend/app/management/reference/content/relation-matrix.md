# relation-matrix

A relation matrix sets records of one type, the rows, against records of another, the columns; each cell holds the related records of that row that sit under that column record. Municipalities against the systems that code them is one, each record's name per language another. The view of the model fixes the binding and the cell actions it offers. These operations read the matrix and what a cell write needs; the writes are ordinary calls.

1. Read the matrix with `GET .../relation-matrix`; choose its columns with `columnIds`.
2. To create a cell record, read `GET .../relation-matrix/containers`, then `POST /api/v1/objects`. To link one, read `GET .../relation-matrix/link-candidates`, then `POST /api/v1/relations` claiming the row's `relationSetVersion`.

## GET /api/v1/workspaces/{workspace_key}/relation-matrix

Title: Read a relation matrix

Reads a page of the view's rows with their cells, and the columns the cells are under. Name `columnIds` to choose the columns, or page them with `columnsNextCursor`. Each row's `relationSetVersion` is what a link or unlink from that row claims.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: The application holding the matrix view.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- columnPageSize: Columns per page when `columnIds` is not given, 1 to 20; 20 by default.
- pageSize: Rows per page, 1 to 100; the view's page size when omitted.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 UNKNOWN_APPLICATION: the model has no such application
- 404 RELATION_MATRIX_VIEW_NOT_FOUND: the application has no such matrix view
- 404 RELATION_MATRIX_PARENT_NOT_FOUND: `parentObjectId` is not in the context
- 404 RELATION_MATRIX_COLUMN_NOT_FOUND: a `columnIds` entry is not a column record
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the context's workspace
- 422 RELATION_MATRIX_PARENT_SCOPE_MISMATCH: that parent cannot contain the rows
- 422 CONFLICTING_COLUMN_PARAMETERS: `columnIds` with `columnCursor`
- 422 RELATION_MATRIX_STATE_REQUIRES_COLUMNS: `state` without `columnIds`
- 422 TOO_MANY_COLUMNS: more than 20 `columnIds`
- 422 DUPLICATE_COLUMN_IDS: a column is named twice
- 422 INVALID_SORT: `sort` names no sortable row field
- 422 INVALID_CURSOR: the cursor belongs to other values or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 422 INVALID_SEEK: `seek` does not fit the sort field
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/workspaces/{workspace_key}/relation-matrix/containers

Title: List where a cell record can be created

Lists where a new cell record of a view that offers `create` can go under one column record. `defaultContainerId` is where the column's new records go. `derivedPlace` is a container the binding's criteria fix or the data suggests, which creating the record makes first when it does not exist yet. Create the record with `POST /api/v1/objects`.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: The application holding the matrix view.
- changeSetId: Read this change set's work in progress; there is no publication context.
- pageSize: 1 to 100; 50 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 UNKNOWN_APPLICATION: the model has no such application
- 404 RELATION_MATRIX_VIEW_NOT_FOUND: the application has no such matrix view
- 404 RELATION_MATRIX_COLUMN_NOT_FOUND: `columnId` is not a column record
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the change set's workspace
- 422 RELATION_MATRIX_ACTION_NOT_ALLOWED: the view does not offer `create`
- 422 INVALID_CURSOR: the cursor belongs to other values or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## GET /api/v1/workspaces/{workspace_key}/relation-matrix/link-candidates

Title: List records a row could be linked to

Lists the cell-type records under a column record that a row could be linked to, in name order, for a view that offers `link`. A record the link would be refused for is listed with its `reason`, not hidden. Link with `POST /api/v1/relations`, claiming the answer's `relationSetVersion`.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: The application holding the matrix view.
- changeSetId: Read this change set's work in progress; there is no publication context.
- pageSize: 1 to 100; 50 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 UNKNOWN_APPLICATION: the model has no such application
- 404 RELATION_MATRIX_VIEW_NOT_FOUND: the application has no such matrix view
- 404 RELATION_MATRIX_ROW_NOT_FOUND: `rowId` is not a row record
- 404 RELATION_MATRIX_COLUMN_NOT_FOUND: `columnId` is not a column record
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the change set's workspace
- 422 RELATION_MATRIX_ACTION_NOT_ALLOWED: the view does not offer `link`
- 422 INVALID_CURSOR: the cursor belongs to other values or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## Schemas

### RelationMatrixRow

A row with its cells in column order. `relationSetVersion` is the row's version of the view's relationship set, which a link or unlink from the row claims; 0 until the set is first changed, and in a publication.

- row: The row record.
- relationSetVersion: The row's version of the view's relationship set, which a link or unlink from the row claims; 0 until the set first changes, and in a publication.
- cells: One cell per column, in column order.

### RelationMatrixRecord

- id: The row record's ID.
- objectTypeKey: The row record's object type.
- name: The row record's name.
- fields: The values of the view's `rowColumns`.

### RelationMatrixColumn

- id: The column record's ID.
- name: The column record's name.
- label: The column record's value of the view's `columnLabelField`.

### RelationMatrixPage

A page of rows, and the columns their cells are in. Columns page with their own cursors when the request does not name them.

- columns: The columns the rows' cells are under.
- columnsNextCursor: Send it as `columnCursor` to read the next columns; `null` at the end, and when `columnIds` named the columns.
- columnsPrevCursor: Send it as `columnCursor` to read the previous columns; `null` at the start, and when `columnIds` named the columns.

### RelationMatrixCell

One row's related records under one column record. `recordCount` and `matchingCount` count every record the cell holds and those meeting the condition; `records` lists at most five of them, those meeting it first. A `historyOnly` cell lists and counts the records of the latest earlier publication that held any, named by `publication`.

- columnId: The column record the cell is under.
- state: `one`: exactly one related record meets the binding's condition (every record does when the binding has none); `several`: more than one does; `inactive`: records exist and none does; `historyOnly`: none now, but an earlier publication held one; `none`: no related record.
- conflict: `true` for a `several` cell the binding's uniqueness scope forbids. Live writes refuse that; a change set can hold it until validation.
- recordCount: How many related records the cell holds.
- matchingCount: How many of them meet the binding's condition.
- records: At most five of the related records, those meeting the condition first, then by name.
- publication: For a `historyOnly` cell, the earlier publication its records are from; `null` otherwise.

### RelationMatrixCellRecord

- id: The related record's ID.
- name: The related record's name.
- version: The record's version, which an edit names as `expectedVersion`.
- relationId: The relationship that joins the record to the row.
- relationVersion: The relationship's version, which an unlink names as `expectedVersion`.
- relationAttributes: The relationship's values, as `GET /api/v1/relations/{relation_id}` gives them.
- meetsCondition: Whether the record meets the binding's condition; always `true` without one.
- fields: The values of the view's `cellFields`.

### RelationMatrixPublicationReference

- id: The publication's ID.
- number: The publication's number in its workspace.

### RelationMatrixContainerPage

Containers in path order: only those a new cell record meets the binding's candidate criteria under, those holding cells of the view first. `defaultContainerId` names where the column's new cells go: the one container the criteria fix, else the container already holding cells of the view (the one holding most; none on a tie), whatever the search; a container holding no cells is never the default, even as the only one. `derivedPlace` is the place the criteria fix, null where they fix none: with none offered and no place derived, the cell cannot be created here.

- defaultContainerId: Where the column's new cell records go: the container the criteria fix, else the one holding most cells of the view. `null` on a tie, and when none holds cells.
- derivedPlace: The container the binding's criteria fix, or one proposed from the data; `null` when there is none, and with no container offered the cell cannot be created in this column.

### RelationMatrixContainer

- id: The container's ID.
- objectTypeKey: The container's object type.
- name: The container's name.
- path: The records from below the column record down to the container; empty for the column record itself.
- cellCount: How many cell records stand directly under it; 0 means the view does not use it yet.

### RelationMatrixPathPart

- id: The record's ID.
- name: The record's name.
- objectTypeKey: The record's object type.

### RelationMatrixDerivedPlace

The record the binding's candidate criteria fix as the place a new cell record goes: equalities on one ancestor type's fields that the model lets sit directly under the column record and directly hold the cell type. `willBeCreated` is true when no container of the column meets the criteria yet: creating a cell then creates this record first, in the same change.

- objectTypeKey: The container's object type.
- name: The container's name; the caller may change it.
- attributes: The values the container is created with.
- willBeCreated: `true` when no container of the column meets the criteria yet: creating the cell record creates this one first, in the same change.
- proposed: True when the model's rules fix no place and no container of the column holds cells of the view: the place is then proposed from the data, a new container of the type the view's other columns use, named as most of them are. The caller may change the name; creating the cell creates the container first, in the same change.

### RelationMatrixLinkCandidatePage

- relationSetVersion: The row's version of the view's relationship set, which a link names as `expectedRelationSetVersion`.

### RelationMatrixLinkCandidate

- id: The candidate's ID.
- objectTypeKey: The candidate's object type.
- name: The candidate's name.
- version: The candidate's version.
- path: The records from below the column record down to the candidate.
- fields: The values of the view's `cellFields`.
- eligible: `false` where a link from the row would be refused; see `reason`.
- reason: Why it is not eligible: `alreadyLinked` (the row relates to it), `rowCardinality` or `candidateCardinality` (the binding allows no further relationship at that end), `scopeTaken` (the row already holds a record in the column that meets the condition, and so does this one). `null` when eligible.
