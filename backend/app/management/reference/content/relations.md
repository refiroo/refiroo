# relations

A relationship joins two records through a relation type, such as a stop served by a mode or a code that maps to a stop. The model's binding for the two object types sets its cardinality (how many relationships each end may hold), which records may be chosen at an end, whether one related record is allowed per ancestor, and the attributes it carries. Containment is a relationship too, but the engine owns it: it changes with a record's `parentObjectId` and is refused here.

1. Read a record's relationships with `GET /api/v1/relations`, a whole workspace's with `GET /api/v1/workspaces/{workspace_key}/relations`, or a relationships table as a grid with `.../relation-grid`.
2. Add one with `POST`, change its values with `PATCH` (many with `POST /api/v1/relations/batch`), remove it with `DELETE`.

## POST /api/v1/relations

Title: Add a relationship

Joins two records through a relation type, live or, with `changeSetId`, in a change set. The relation type must bind their two object types, and the binding's cardinality, ancestor scope and candidate criteria apply. Name `expectedRelationSetVersion` with `relationSetDirection` to write only while the set you read is unchanged; the answer then carries the set's new version. Containment is refused: set the parent on the record.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 DUPLICATE_RELATION: the two records are already joined by this type
- 409 CARDINALITY_VIOLATION: an end already holds its one relationship
- 409 DUPLICATE_RELATION_SCOPE: live only; the record repeats an ancestor scope
- 409 RELATION_SET_VERSION_CONFLICT: the claimed set has changed
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 RELATION_SET_CLAIM_INCOMPLETE: only one of the two claim fields
- 422 RELATION_ENDPOINT_MISSING: a record is not in the context
- 422 RELATION_WRONG_SCOPE: live only; the records are in different workspaces
- 422 UNKNOWN_RELATION_TYPE: the model has no such relation type
- 422 INVALID_RELATION_PAIR: the relation type does not join these types
- 422 IMMUTABLE_RELATION: containment is set with the parent
- 422 RELATION_ANCESTOR_REQUIRED: the `to` record lacks the scope's ancestor
- 422 RELATION_CANDIDATE_REFUSED: an end does not meet the binding's criteria
- 422 UNKNOWN_RELATION_ATTRIBUTES: the binding has no such attribute
- 422 INVALID_ATTRIBUTE_VALUE: a value is not of its attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## GET /api/v1/relations

Title: List a record's relationships

Lists the relationships of one record, each with the record at the other end, and the relationship sets the record anchors with their versions. `sort` and `search` apply to the related records. Use `GET /api/v1/workspaces/{workspace_key}/relations` for a workspace's relationships.

### Parameters

- objectId: The record whose relationships are listed.
- direction: `outgoing` lists the relationships that start at the record, `incoming` those that end at it, `both` all of them.
- workspaceKey: The workspace read, the default workspace when omitted.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 OBJECT_NOT_FOUND: the record is not in the context
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `objectId` is missing or a parameter is invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 422 INVALID_SORT: `sort` names no sortable field here
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 422 INVALID_SEEK: `seek` does not fit the sort field
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/relations/held

Title: List what records hold through a relationship

Lists the records at the other end of one relation type from the records you name, each with how many of the named records hold it. Use it to offer what a selection's Remove would remove. Name the records' type, the relation type and the direction read from the records; at most 500 records.

### Parameters

- relationTypeKey: The relation type's key.
- workspaceKey: The workspace read, the default workspace when omitted.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a required parameter is missing or invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 422 UNKNOWN_RELATION_TYPE: the model has no such relation type
- 422 INVALID_RELATION_PAIR: the type has no binding in that direction
- 422 TOO_MANY_RECORDS: more than 500 `objectId`
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/relations/{relation_id}

Title: Get a relationship

Reads one relationship with its values and its `version`, which a change or removal names as `expectedVersion`. Live, it is found only in the workspace read, so name `workspaceKey` for one outside the default workspace. In a change set or publication it carries no times.

### Parameters

- relation_id: The relationship's ID.
- workspaceKey: The workspace read, the default workspace when omitted.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 RELATION_NOT_FOUND: the context holds no such relationship
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## PATCH /api/v1/relations/{relation_id}

Title: Change a relationship's values

Replaces the values of a relationship: the values you send are the whole set, so one left out is removed. The ends and the relation type never change; to change an end, remove the relationship and add another. A stale `expectedVersion` is answered before anything else. `POST /api/v1/relations/batch` sets values on many relationships and keeps those it does not name.

### Parameters

- relation_id: The relationship's ID.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 RELATION_NOT_FOUND: no such relationship in the context
- 409 VERSION_CONFLICT: `expectedVersion` is not the relationship's version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `attributes` or `expectedVersion` is missing or invalid
- 422 IMMUTABLE_RELATION: containment is changed with the parent
- 422 UNKNOWN_RELATION_ATTRIBUTES: the binding has no such attribute
- 422 INVALID_ATTRIBUTE_VALUE: a value is not of its attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## DELETE /api/v1/relations/{relation_id}

Title: Remove a relationship

Removes a relationship, live or, with `changeSetId`, in a change set. Containment and relationships the other record requires cannot be removed on their own: move or delete the record instead. `expectedRelationSetVersion` with `relationSetDirection` removes only while that end's set is unchanged.

### Parameters

- relation_id: The relationship's ID.
- expectedVersion: The relationship's `version`.
- changeSetId: The change set to remove it in; live when omitted.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 RELATION_NOT_FOUND: no such relationship in the context
- 409 VERSION_CONFLICT: `expectedVersion` is not the relationship's version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 RELATION_SET_VERSION_CONFLICT: the claimed set has changed
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or invalid
- 422 RELATION_SET_CLAIM_INCOMPLETE: only one of the two claim parameters
- 422 IMMUTABLE_RELATION: containment is removed with the record
- 422 REQUIRED_RELATION: the binding requires the relationship
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## POST /api/v1/relations/batch

Title: Set values on many relationships

Sets attribute values on many relationships in one write, live in `workspaceKey` or, with `changeSetId`, in a change set. Unlike `PATCH`, an item's values are laid over the stored ones, and `null` clears one. The write is all or nothing: a stale version, an unknown relationship or an invalid value refuses it, and `details.items` names each item that failed.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 409 RELATION_BATCH_REFUSED: an item has a stale version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 413 BATCH_TOO_LARGE: more items than `BATCH_MAX_ITEMS`
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 RELATION_BATCH_REFUSED: an item is refused for another reason
- 422 DUPLICATE_BATCH_ITEMS: a relationship is named twice
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## POST /api/v1/relations/grid-change

Title: Set a value across a relationships grid

Sets one attribute value on the relationships a relationships grid shows: the `from` records you pick, or every record the grid's search and filters select, against up to 50 `to` records. With `linkMissing` it also relates the pairs that are not related. Send `dryRun: true` first: it counts and lists what an apply would be refused for, and writes nothing. An apply is all or nothing.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 RELATION_TABLE_NOT_FOUND: the view is not a relationships table
- 409 RELATION_BATCH_REFUSED: an item has a stale version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: an apply in a retired workspace
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 413 BATCH_TOO_LARGE: more writes than `ATOMIC_JOB_MAX_ITEMS`; a dry run too
- 422 REQUEST_VALIDATION_ERROR: a field is invalid, or rows are not chosen once
- 422 RELATION_BATCH_REFUSED: an item is refused for another reason
- 422 INVALID_GRID_CHANGE: the attribute, value or records do not fit the binding
- 422 INVALID_FILTER: a row filter is not one of the view's
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## Schemas

### RelationCreate

A relationship to create. `expectedRelationSetVersion` with `relationSetDirection` claims one end's relationship set: the write succeeds only while that set is still at the version the caller read, such as a relationship matrix row's `relationSetVersion`. `outgoing` names the from end's set.

- relationTypeKey: The relation type's key; the model must bind it between the two records' object types.
- fromObjectId: The `from` record's ID.
- toObjectId: The `to` record's ID.
- attributes: The relationship's values, keyed by attribute type key, for the attributes the binding carries.
- changeSetId: Add in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.
- expectedRelationSetVersion: With `relationSetDirection`: write only while that end's relationship set is at this version, as `relationSets` or a matrix row gave it; 0 for a set never changed.
- relationSetDirection: With `expectedRelationSetVersion`: `outgoing` claims the `from` record's set, `incoming` the `to` record's.

### RelationResponse

- id: The relationship's ID.
- relationTypeKey: The relation type's key.
- fromObjectId: The `from` record's ID.
- toObjectId: The `to` record's ID.
- attributes: The relationship's values, keyed by attribute type key.
- version: The relationship's version, which rises by one with every change. Send it as `expectedVersion`.
- createdAt: When the relationship was created; `null` in a change set or publication.
- updatedAt: When the relationship last changed; `null` in a change set or publication.
- changeSetVersion: The change set's `version` after a write to it; `null` otherwise.
- relationSetVersion: The claimed set's new version after a create that claimed one; `null` otherwise.
- changeSetId: Not used in an answer; `null`.
- expectedChangeSetVersion: Not used in an answer; `null`.
- expectedRelationSetVersion: Not used in an answer; `null`.
- relationSetDirection: Not used in an answer; `null`.

### RelationUpdate

- attributes: The relationship's whole set of values, keyed by attribute type key; a value left out is removed.
- expectedVersion: The relationship's `version`.
- changeSetId: Change it in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### RelationBatchUpdate

Values set on many relationships as one write. Each item's `attributes` are set over the relationship's stored values, and `null` clears one. In live data the relationships are those of `workspaceKey` (the default workspace without it); with `changeSetId` they are the change set's and `expectedChangeSetVersion` is required.

- items: The relationships to change, at least one, each once; at most `BATCH_MAX_ITEMS`.
- workspaceKey: The workspace of the live relationships; the default workspace when omitted.
- changeSetId: Change the relationships in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### RelationBatchItem

- id: The relationship's ID.
- expectedVersion: The relationship's `version`, as read.
- attributes: The values to set over the stored ones, keyed by attribute type key; `null` clears one.

### RelationBatchResponse

- items: The relationships, in the order of the request's items, each at its new version.
- changeSetVersion: The change set's `version` after the write; `null` live.

### RelationGridChange

One value set on the relationships between many `from` records and some `to` records of a relationships grid, all or none. The rows are `fromObjectIds` (the ticked ones) or, with `allMatching`, every record the `search` and `filters` of the grid select, less `exceptObjectIds`; the columns are `toObjectIds` (the shown or picked groups, at most 50). `value` is set on `attributeTypeKey` of each relationship between them that holds another value (`null` clears it); with `linkMissing` the pairs not yet related are related too, with that value. `dryRun` answers the counts and every refusal the apply would meet, and writes nothing. In live data the relationships are those of `workspaceKey` (the default workspace without it); with `changeSetId` they are the change set's and `expectedChangeSetVersion` is required.

- applicationKey: The application holding the relationships table.
- viewKey: The `relationTable` view whose binding is changed.
- fromObjectIds: The ticked rows, records of the view's `from` type. Give this or `allMatching`.
- allMatching: `true` selects every record the `search` and `filters` match as rows, instead of `fromObjectIds`.
- exceptObjectIds: With `allMatching`: records left out of the selection.
- search: With `allMatching`: part of the rows' names, ignoring case.
- filters: With `allMatching`: the grid's row filters.
- toObjectIds: The column records, 1 to 50 of the view's `to` type.
- attributeTypeKey: The relationship attribute to set; the binding must carry it and it must hold a single value.
- value: The value to set, in the attribute type's form; `null` clears it.
- linkMissing: `true` also relates the pairs that are not related, with the value.
- dryRun: `true` counts and lists what an apply would be refused for, and writes nothing.
- workspaceKey: The workspace of the live relationships; the default workspace when omitted.
- changeSetId: Change the relationships in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### RelationGridFilter

- field: A filter field of the view: `from:<field>`, `to:<field>` or `relation:<attribute>`.
- operator: The operator; `eq` when omitted.
- value: The value to compare with, as text.

### RelationGridChangeResponse

- dryRun: Whether the request was a dry run, which writes nothing.
- change: How many relationships hold another value than the one sent.
- same: How many relationships already hold the value.
- missing: How many pairs are not related.
- linked: How many pairs were, or on a dry run would be, related; 0 without `linkMissing`.
- refused: On a dry run, what an apply would be refused for; empty when it would go through.
- changeSetVersion: The change set's `version` after an apply; `null` live and on a dry run.

### RelationGridChangeItem

- index: The position among the changes: the relationships to update first, then the pairs to link.
- relationId: The relationship; `null` for a pair to link.
- fromObjectId: The pair's `from` record.
- toObjectId: The pair's `to` record.
- code: The refusal's error code.
- message: The refusal's message.

### RelationPage

A record's relationships, and every relationship set it anchors in the listed direction and types, an empty one included. A publication is read-only and names no sets.

- relationSets: Every relationship set the record anchors in the listed direction and types, with its version, empty sets included; left out for a publication.

### RelationExpansion

- direction: `outgoing` when the listed record is the relationship's `from` end, `incoming` when it is the `to` end.
- relation: The relationship.
- object: The record at the other end.

### RelationSetVersionItem

A relationship set the listed record anchors and its version, which a claimed write names (`expectedRelationSetVersion` with `relationSetDirection`).

- relationTypeKey: The relation type's key.
- fromObjectTypeKey: The binding's `from` object type.
- toObjectTypeKey: The binding's `to` object type.
- direction: The end the set is anchored at: `outgoing` the `from` record, `incoming` the `to` record.
- relationSetVersion: The set's version, which a claimed write names; 0 until a write first changes it.

### HeldRecord

- object: The record at the other end of the relationship.
- count: How many of the named records hold a relationship to it.

### HeldObject

- id: The record's ID.
- name: The record's name.
- objectTypeKey: The record's object type.

### HeldRecordPage

What a set of records holds through one relationship, in name order.
