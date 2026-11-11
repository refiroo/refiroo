# objects

A record is one instance of an object type, kept in an application and in the tree of its parents. You use this area to find records, read them, and create, change, move and delete them one at a time; use `POST /api/v1/batches` to change many.

A write to a submitted change set is refused with `CHANGE_SET_SUBMITTED`, unless the request carries `withdrawSubmission=true`, which withdraws the submission first. A role may allow only some applications or object types.

1. Find: `GET /api/v1/objects` when the type is not known, `GET /api/v1/objects/{object_type_key}` for one type, or the query for criteria over fields, ancestors and one relationship.
2. Change: read the record, then `PATCH` it with its `version` as `expectedVersion`; a `parentObjectId` moves it.

## POST /api/v1/objects

Title: Create a record

Creates a record of an object type in an application, live in `workspaceKey` or, with `changeSetId`, in a change set. Give `parentObjectId` unless the type may stand alone. A relationship the model requires into the new record must come with it in `initialRelations`; all of it is saved in one transaction. Attributes left out take their default, and the model's required attributes, unique values and rules apply.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 UNKNOWN_APPLICATION: the model has no such application
- 404 OBJECT_NOT_FOUND: no record is the parent
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 OBJECT_ALREADY_EXISTS: `id` is taken, in any workspace
- 409 DUPLICATE_ATTRIBUTE_VALUE: another record holds a unique value
- 409 CARDINALITY_VIOLATION: an initial relationship breaks its cardinality
- 409 DUPLICATE_RELATION_SCOPE: an initial relationship repeats its ancestor scope
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 WORKSPACE_KEY_REQUIRED: a live create without `workspaceKey`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the change set's
- 422 UNKNOWN_OBJECT_TYPE: in a change set, the model has no such type
- 422 OBJECT_TYPE_NOT_IN_APPLICATION: in a change set, the application lacks the type
- 422 INVALID_OBJECT_TYPE_FOR_APPLICATION: the application does not hold the type
- 422 PARENT_REQUIRED: the type may not stand alone
- 422 PARENT_WRONG_SCOPE: the parent is in another application or workspace
- 422 INVALID_PARENT_TYPE: the type cannot sit under that parent
- 422 DUPLICATE_ATTRIBUTE: an attribute is named twice
- 422 UNKNOWN_ATTRIBUTES: the type does not bind an attribute
- 422 READ_ONLY_ATTRIBUTES: an attribute is read-only
- 422 MISSING_REQUIRED_ATTRIBUTES: a required attribute has no value
- 422 INVALID_ATTRIBUTE_VALUE: a value is not of its attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 422 OBJECT_ATTRIBUTE_RULE_VIOLATION: an at-least-one-of rule is not met
- 422 INVALID_EFFECTIVE_PERIOD: the period does not end after it starts
- 422 MISSING_REQUIRED_RELATIONS: a required relationship is not in `initialRelations`
- 422 DUPLICATE_INITIAL_RELATION: `initialRelations` repeats one
- 422 RELATION_ENDPOINT_MISSING: an initial relationship's record is missing
- 422 RELATION_WRONG_SCOPE: that record is in another workspace
- 422 UNKNOWN_RELATION_TYPE: the model has no such relation type
- 422 INVALID_RELATION_PAIR: the relation type does not join these types
- 422 IMMUTABLE_RELATION: containment is set with `parentObjectId`
- 422 UNKNOWN_RELATION_ATTRIBUTES: the binding has no such relation attribute
- 422 RELATION_ANCESTOR_REQUIRED: the related record lacks the scope's ancestor
- 422 RELATION_CANDIDATE_REFUSED: an end does not meet the binding's candidate criteria
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## GET /api/v1/objects

Title: Find records of any type

Lists records of every object type, or of the types you name, in one list: for finding a record by name, ID, parent or time when its type is not known. It filters and sorts only on built-in fields; use the per-type list for attributes. Several `workspaceKey` read those workspaces' live records together.

### Parameters

- objectTypeKey: Repeatable; only records of these types. Every type when omitted.
- workspaceKey: Repeatable. One names the workspace read, the default when omitted; several read their live records together, each under its own model.
- applicationKey: Only records of this application.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.
- parentObjectId: Only the children of this record.
- search: Part of the name, ignoring case.
- sort: `name` (the default), `id`, `objectType` (by the type's name, then the record's) or, live only, `createdAt` or `updatedAt`; `-` in front for descending.
- asOf: Not accepted here: an effective period belongs to one type.
- filter.<field>.<operator>: Repeatable; `field` is `id`, `name`, `objectTypeKey`, `parentObjectId` or, live only, `createdAt` or `updatedAt`. Operators as on the per-type list.

### Errors

- 403 FORBIDDEN: needs Browse in every workspace read
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 UNKNOWN_OBJECT_TYPE: no model holds a named type
- 404 UNKNOWN_APPLICATION: no model holds the application
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or another parameter is invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 MUTUALLY_EXCLUSIVE_SCOPE: `topLevel` with `parentObjectId`
- 422 WORKSPACE_CONTEXT_MISMATCH: a context with several workspaces, or another's
- 422 MODEL_ELEMENT_NOT_IN_EVERY_MODEL: some workspace's model lacks a named type or application
- 422 INVALID_OBJECT_TYPE_FOR_APPLICATION: the application does not hold a named type
- 422 AS_OF_NOT_SUPPORTED: `asOf` was sent
- 422 INVALID_FILTER: a filter is malformed or not on a built-in field
- 422 INVALID_SORT: `sort` is not a built-in sort
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 422 INVALID_SEEK: `seek` does not fit the sort field
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/objects/{object_type_key}

Title: List records of a type

Lists the records of one object type, with their attributes, filtered and sorted by the type's attributes. `expand` adds the records at the other end of a relationship to each item, and `candidateFor` lists the records a relationship may choose. Items in a change set or publication carry no times.

### Parameters

- object_type_key: The object type's key.
- workspaceKey: The workspace read, the default workspace when omitted.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.
- applicationKey: Only records of this application, which must hold the type.
- parentObjectId: Only the children of this record.
- search: Part of the name or of a searchable attribute's value, ignoring case. `%`, `_` and quotes match themselves.
- asOf: A date, `YYYY-MM-DD`: only records whose effective period includes it. Refused for a type without a period. In a cursor, it binds the date.
- expand: Repeatable, each key once: a relation type's `key` (its outgoing relationships) or `reverseKey` (its incoming ones) that the type binds, optionally followed by `.` and a field of the related records (`name`, an attribute or `ancestor:<type>.<field>`). Each item then carries `expanded`.
- expandLimit: How many related records each `expand` shows per item, 1 to 20; 3 by default.
- candidateFor: A relation key or reverse key, read from `anchorTypeKey`'s records: only the records such a record may choose through it, by the criteria the model sets there; every record when it sets none.
- anchorTypeKey: The type of the record choosing, with `candidateFor`.
- filter.<field>.<operator>: Repeatable. `field` is `id`, `name`, `parentObjectId`, live `createdAt` or `updatedAt`, or an attribute the model marks filterable. Text takes `eq`, `contains`, `startsWith`; numbers and dates `eq`, `lt`, `lte`, `gt`, `gte`; booleans `eq`; yes/no attributes also `ne`; all `isNull`, attributes `isUnset`, as `true` or `false`. Different filters must all hold; repeated `eq` of one field are alternatives. `filter.related:<key>.eq=<record ID>` keeps records related to it, `.isNull`, `.under` and `.notUnder` also work.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace read
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 UNKNOWN_APPLICATION: the model has no such application
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `pageSize`, `asOf` or another parameter is invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 MUTUALLY_EXCLUSIVE_SCOPE: `topLevel` with `parentObjectId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 422 INVALID_OBJECT_TYPE_FOR_APPLICATION: the application does not hold the type
- 422 AS_OF_NOT_SUPPORTED: the type has no effective period
- 422 INVALID_FILTER: a filter or `candidateFor` is malformed or not allowed
- 422 INVALID_SORT: `sort` names no sortable field
- 422 INVALID_EXPAND: an `expand` key or field does not resolve
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 422 INVALID_SEEK: `seek` does not fit the sort field
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## POST /api/v1/workspaces/{workspace_key}/queries/objects

Title: Query records

Lists the records of one object type that match criteria over their fields, their ancestors and one relationship hop, and returns the fields and related records you select. It is a read that changes nothing, and it takes its page selection in the body. A cursor continues only the same query.

### Parameters

- workspace_key: The workspace queried; a `context` must belong to it.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `context.changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `context.publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: the workspace does not exist
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: the body is malformed or breaks a bound
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: both a change set and a publication
- 422 WORKSPACE_CONTEXT_MISMATCH: the context is another workspace's
- 422 INVALID_QUERY: a name or value does not fit the model
- 422 AS_OF_NOT_SUPPORTED: `asOf` on a type without an effective period
- 422 INVALID_CURSOR: the cursor belongs to another query
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/objects/{object_type_key}/{object_id}

Title: Get a record

Reads one record with its attributes and path. The live read finds the record only in the workspace read, so name `workspaceKey` for a record outside the default workspace.

### Parameters

- object_type_key: The record's type key; another type answers `OBJECT_TYPE_CHANGED`.
- object_id: The record's ID.
- workspaceKey: The workspace read, the default workspace when omitted.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: the context holds no such record
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## PATCH /api/v1/objects/{object_type_key}/{object_id}

Title: Update or move a record

Changes the fields you send and leaves the rest: the name, attribute values, or the parent, which moves the record and its subtree. `parentObjectId: null` makes it a root where its type may be one. An attribute you send replaces its value; use the attribute operations to remove one. A live update checks an at-least-one-of rule over the resulting values; a change set leaves it to its validation.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: no such record, or no such new parent
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 VERSION_CONFLICT: `expectedVersion` is not the record's version
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 DUPLICATE_ATTRIBUTE_VALUE: another record holds a unique value
- 409 DUPLICATE_RELATION_SCOPE: the move or value repeats a relationship's ancestor scope
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a field is invalid or `expectedVersion` is missing
- 422 UNKNOWN_OBJECT_TYPE: in a change set, the model has no such type
- 422 DUPLICATE_ATTRIBUTE: an attribute is named twice
- 422 UNKNOWN_ATTRIBUTES: the type does not bind an attribute
- 422 READ_ONLY_ATTRIBUTES: an attribute is read-only
- 422 MISSING_REQUIRED_ATTRIBUTES: a required attribute is emptied
- 422 INVALID_ATTRIBUTE_VALUE: a value is not of its attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 422 OBJECT_ATTRIBUTE_RULE_VIOLATION: an at-least-one-of rule is not met
- 422 INVALID_EFFECTIVE_PERIOD: the period does not end after it starts
- 422 PARENT_REQUIRED: the type may not become a root
- 422 PARENT_WRONG_SCOPE: the parent is in another application or workspace
- 422 INVALID_PARENT_TYPE: the type cannot sit under that parent
- 422 PARENT_CYCLE: the parent is the record or under it
- 422 RELATION_ANCESTOR_REQUIRED: a relationship's record lacks the scope's ancestor
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## DELETE /api/v1/objects/{object_type_key}/{object_id}

Title: Delete a record

Deletes a record, live or in a change set. A record with children or relationships beyond its place under its parent is not deleted without `cascade=true`; the refusal is a preview that lists them and carries a `deletionPreviewToken`. Repeat the request with `cascade=true` and that token to delete the record, its descendants and its relationships.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- expectedVersion: The record's `version`.
- changeSetId: The change set to delete in; live when omitted.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.
- cascade: `true` to delete what depends on the record; needs `deletionPreviewToken`.
- deletionPreviewToken: The token the preview returned. It holds only while nothing it lists has changed.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 OBJECT_NOT_FOUND: the context holds no such record
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 VERSION_CONFLICT: `expectedVersion` is not the record's version
- 409 OBJECT_HAS_DEPENDANTS: it has children or relationships; read the preview
- 409 DELETION_PREVIEW_REQUIRED: `cascade` without `deletionPreviewToken`
- 409 DELETION_PREVIEW_CHANGED: the token no longer matches; preview again
- 409 WORKSPACE_GRAPH_INVALID: its hierarchy reaches into another workspace
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `expectedVersion` is missing or below 1
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## GET /api/v1/objects/{object_type_key}/{object_id}/parent-candidates

Title: List parent candidates

Lists the records a record could move under, live or in a change set, in name order. A candidate the move would refuse or would not change stays in the list, marked ineligible with its `reason`, so pages and totals stay complete. Publications have no move targets, and the operation takes no `publicationId`.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- workspaceKey: The workspace read, the default workspace when omitted.
- changeSetId: Read the candidates in this change set.
- pageSize: 1 to 100; 50 by default.
- parentObjectTypeKey: Only candidates of this type, one that can contain the record.
- search: Part of the name or of a searchable attribute's value.
- includeTypeChanges: In a change set, also list records of types that can contain another type of the record's application, each with the types the record would become there.
- withinObjectTypeKey: Repeatable; only candidates of these types and, with `includeTypeChanges`, only these as the types the record would become.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: the context holds no such record
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or another parameter is invalid
- 422 UNKNOWN_PARAMETER: a parameter the operation does not take, such as `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the change set's
- 422 INVALID_PARENT_TYPE: `parentObjectTypeKey` cannot contain the record
- 422 UNKNOWN_OBJECT_TYPE: `withinObjectTypeKey` names a type the model lacks
- 422 TYPE_CHANGES_NEED_CHANGE_SET: `includeTypeChanges` without `changeSetId`
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/objects/{object_type_key}/{object_id}/history

Title: Get a record's history

Lists a record's history, newest first: what each change did, the values it changed with the value before, and the other record of a relationship change. It covers the record's own changes and those of its relationships, live and in change sets.

### Parameters

- object_type_key: The record's type key.
- object_id: The record's ID.
- changeSetId: Requires the record to exist in this change set; the entries read the same.
- pageSize: 1 to 500; 100 by default.
- kind: Only one kind of entry: `values`, `relationships`, or `structure` (a parent or type change).
- actorId: Only the changes of one person or client, by ID, or `engine` for the engine's own.
- live: `true` keeps only entries that changed live data; a change set's edits are left out. Not used with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the record's workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 UNKNOWN_OBJECT_TYPE: the model has no such type
- 404 OBJECT_NOT_FOUND: no such record, or not in the change set
- 409 OBJECT_TYPE_CHANGED: the record is of another type
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `kind` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another record
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## Schemas

### ObjectCreate

- id: The ID the record gets, a UUID; the engine assigns one when omitted. Record IDs are unique across the instance.
- applicationKey: The application the record belongs to.
- objectTypeKey: The record's object type; the application must hold it.
- name: The record's display name, 1 to 500 characters.
- workspaceKey: The workspace to create in. Required without `changeSetId`; a change set's own when given.
- parentObjectId: The parent record, in the same application and workspace. Omit it for a type that may stand alone.
- attributes: The attribute values, each attribute type once. Attributes left out take their default.
- initialRelations: Relationships made with the record, in the same transaction.
- changeSetId: Create in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### ObjectUpdate

- name: The new display name, 1 to 500 characters.
- parentObjectId: The new parent, which moves the record; `null` makes it a root. Omit it to leave the parent.
- attributes: The attribute values to set, each attribute type once. Attributes not named keep their value.
- expectedVersion: The record's `version`.
- changeSetId: Update in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### AttributeInput

- attributeTypeKey: The attribute type's key; the record's type must bind it.
- value: The value, in the attribute type's JSON form: a string, number or boolean, a date as `YYYY-MM-DD`, a date-time as ISO 8601 (a zone-less one is UTC), a decimal as a number or a string.

### InitialRelationInput

- relationTypeKey: The relation type's key. A containment relation is set with the parent, not here.
- direction: `outgoing` makes the new record the relationship's `from` end, `incoming` its `to` end.
- otherObjectId: The record at the other end.
- attributes: The relationship's attribute values, keyed by attribute type key, for the attributes the binding carries.

### ObjectResponse, LookupObject, QueryObject

- id: The record's ID.
- workspaceKey: The workspace that holds the record.
- applicationKey: The application the record belongs to.
- objectTypeKey: The record's object type.
- parentObjectId: The parent record's ID; `null` for a root.
- name: The record's display name.
- path: The records from the root down to this one, itself last.
- attributes: The attribute values the record holds, one entry per attribute type. An attribute without a value is left out.
- version: The record's version, which rises by one with every change. Send it as `expectedVersion`.
- createdAt: When the record was created; `null` in a change set or publication.
- updatedAt: When the record last changed; `null` in a change set or publication.
- changeSetVersion: The change set's `version` after a write to it; `null` otherwise.
- origin: Who prepared the record when the AI or an assistant did; left out otherwise. The mark stays after a person edits it.

### LookupObject

A cross-type lookup's item: a record naming the release its workspace's model, or its change set's or publication's, was read under.

- modelReleaseId: The model release the record was read under: its workspace's, or its change set's or publication's.

### QueryObject, QuerySelectedObject

- expanded: One entry per `expand`, in request order; left out when nothing was expanded.

### ObjectPathPart

- id: The ancestor's ID.
- name: The ancestor's name.
- objectTypeKey: The ancestor's object type.

### ParentCandidate

A record the model allows as the moved record's parent. `path` runs from the root to the candidate itself, so same-named candidates can be told apart. An ineligible candidate is listed, not hidden, so pages and totals stay truthful, with a `reason`: `self` (the record itself, when its type may contain its own), `descendant` (a record under it, which would make a cycle) or `currentParent` (where it already is).

- id: The candidate's ID.
- objectTypeKey: The candidate's object type.
- name: The candidate's name.
- path: The records from the root down to the candidate, itself last.
- eligible: `false` where the move would be refused or would change nothing; see `reason`.
- reason: Why it is not eligible: `self` (the record itself), `descendant` (a record under it, which would make a cycle) or `currentParent`. `null` when eligible.
- objectTypeKeys: With `includeTypeChanges`, the types the record would become under the candidate.

### ModelQuery

A query over one object type's records.

- objectTypeKey: The object type queried.
- context: Where to read; live data when empty.
- where: Criteria combined with AND. A field criterion, or a `related` hop.
- select: The fields each item returns: `name`, `workspaceKey`, `applicationKey`, `parentObjectId`, `path`, `createdAt`, `updatedAt`, an attribute the type binds, or `ancestor:<type>`. Items then carry `fields`; without `select` they are the object list's items. Every item has `id`, `objectTypeKey` and `version`.
- asOf: A date, `YYYY-MM-DD`: only the queried records whose type's effective period includes it. A hop's far end and the expansions are not dated.
- sort: One field as on the per-type list, `-` in front for descending; `name` when omitted.
- expand: Relationships to read for each item; one entry per binding, in request order.
- pageSize: Items per page, 1 to 500; 100 by default.
- cursor: A cursor from a page of this query.
- position: The zero-based row to start at.
- from: `start` (the default) or `end`, the last page.
- includeTotal: `true` adds `totalCount` and `startIndex`.

### QueryContext

- changeSetId: Read the change set's work in progress.
- publicationId: Read this published state. Not with `changeSetId`.

### QueryCriterion

- field: `id`, `name`, `parentObjectId`, live `createdAt` or `updatedAt`, a filterable attribute, `ancestor:<type>` with `eq` on an ancestor's ID, or `ancestor:<type>.<field>`. Not with `related`.
- op: The operator, as on the object list; `isNull` and `isUnset` take a boolean.
- value: The value, in its JSON type: text and dates as strings, integers as integers, decimals as numbers or strings, booleans as booleans.
- related: One relationship hop, true where at least one record at the other end matches. No further hop inside it.
- not: `true` inverts a hop: records with no such related record.

### RelatedCriterion

- relationTypeKey: A relation type the queried type binds in `direction`.
- direction: `outgoing` reads relationships the record starts, `incoming` those that end at it.

### QueryExpansion

- relationTypeKey: A relation type the queried type binds in `direction`.
- direction: `outgoing` reads relationships the record starts, `incoming` those that end at it.
- limit: How many related records to return per item, 1 to 20; 20 by default.

### SelectedRecord, QuerySelectedObject

- id: The record's ID.
- objectTypeKey: The record's object type.
- version: The record's version.
- fields: The selected fields: a built-in's or an attribute's value (`null` when the record has none); for `ancestor:<type>`, the `id` and `name` of the nearest ancestor of that type, `null` when there is none.

### ExpandedRelations

- relationTypeKey: The relation type read.
- direction: `outgoing` or `incoming`, as requested.
- field: The field of the related records shown beside `name`, when `expand` named one.
- count: How many related records the item has, in all.
- items: The first related records, in name order.
- nextCursor: Continues on `GET /api/v1/relations` with this record as `objectId`; `null` when `items` holds them all.

### ExpandedRecord

- relationId: The relationship's ID.
- object: The record at the other end.

### AuditEventResponse

- id: The entry's ID.
- aggregateType: What the entry is about: `object` or `change-set-object` for the record, `relation` or `mapping` for a relationship.
- aggregateId: The ID of the record or relationship.
- action: What was done, such as `created`, `updated`, `deleted` or `reclassified`.
- version: The record's or relationship's version after the entry.
- changedFields: The names of the fields the entry changed.
- attributeTypeKeys: The attribute types the entry changed.
- occurredAt: When the change was recorded.
- cause: What made the change when it was not a single write.
- actor: Who made it; `null` for an entry from before the engine recorded actors.
- kind: `values`, `relationships` (a relationship or a mapping change) or `structure` (a parent or type change).
- values: Each field the entry changed, with the value before. Empty for an entry that kept names only.
- related: A relationship entry's other record.
- channel: `mcp` for a change an assistant made; left out otherwise.
- origin: Who proposed the change when the AI did; left out otherwise.

### AuditCause

What made a change other than a single write: a job, or a publication whose publishing applied it to live data.

- kind: `job` when a job made the change, `publication` when a publication applied it to live data.
- id: The job's or the publication's ID.
- origin: For a move's job, where the record came from: the record it was copied from, in its workspace.

### RecordOrigin

The record a move copied a record from, in its workspace.

- workspaceKey: The workspace the record was copied from.
- objectId: The record it was copied from, in that workspace.

### HistoryValue

One value an entry changed, with the value before.

- kind: What `field` is: `name`, `parent`, `attribute` or `relation`.
- to: What the entry stored: a name or attribute value, a parent by its name, or a relationship's records by their names.

### HistoryRelated

The other record of a relationship's entry, read from this record.

- relationTypeKey: The relationship's type.
- direction: `outgoing` when this record is the relationship's `from` end, `incoming` when it is the `to` end.
- objectId: The other record's ID.
- objectTypeKey: The other record's object type.

### ProposalOrigin

Who proposed a change when a person did not: the provider and model that answered, the prompt's version, how confident it was and why, and the person or client whose request asked for it.

- kind: `ai`: the AI proposed the change.
- provider: The AI provider that answered.
- model: The model that answered; `null` when it is not known.
- promptVersion: The version of the instructions sent to it.
- confidence: How confident it said it was; left out when it gave none.
- reason: Why it proposed this; left out when it gave none.
- proposedBy: The ID of the person or client whose request asked for it.
- proposedByName: Their name now; left out when unknown.
- editedBy: The ID of the person or client who edited the proposal afterwards; left out when none did.
- editedByName: Their name now; left out when unknown.
- taskId: The assistant task it came from; left out when none.

### AgentOrigin

A change an assistant prepared through a tool: the name it gave itself, and the person or client it acted for.

- kind: `agent`: an assistant prepared the change through a tool.
- application: The name the assistant gave itself.
- proposedBy: The ID of the person or client it acted for.
- proposedByName: Their name now; left out when unknown.
- editedBy: The ID of the person or client who edited the change afterwards; left out when none did.
- editedByName: Their name now; left out when unknown.

### ObjectQueryPage

One page of the query's records in its sort order.

### TypedObjectPage

One page of a type's records (`GET /api/v1/objects/{object_type_key}`), each with `expanded` when the list's `expand` named relationship columns.
