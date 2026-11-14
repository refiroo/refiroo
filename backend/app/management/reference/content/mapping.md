# mapping

A mapping relates each record of a source type, such as a system's code, to the records it stands for. A `mappingGrid` view of the model fixes the binding, the types and the direction. Coverage says, for each source, whether it is `mapped`, `unmapped` or `ambiguous`, and by which targets. Ambiguous means several targets where the source may hold one, which only data from before the cardinality can show.

1. Find what needs a target: `GET /api/v1/workspaces/{workspace_key}/mapping-coverage` with `state=unmapped`.
2. Choose with `GET .../mapping-candidates`, then replace the source's targets with `PUT .../mappings`, naming the `mappingVersion` coverage gave. Or ask the AI provider with `POST .../mapping-proposals`.
3. `GET .../mapping-targets` reads the targets a coverage row does not show.

## GET /api/v1/workspaces/{workspace_key}/mapping-coverage

Title: Read mapping coverage

Lists the sources of a mapping view with their state and first targets, so you see what still needs a mapping. Sources are the records of the source type the binding lets be mapped, and those that already are. Each row's `mappingVersion` is what a replacement, or a read of its further targets, names.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: The application holding the mapping view.
- viewKey: A `mappingGrid` view of the application.
- relationTypeKey: The view's relation type, as the view declares it.
- fromObjectTypeKey: The binding's `from` object type, as the view declares it.
- toObjectTypeKey: The binding's `to` object type, as the view declares it.
- direction: The view's direction: `outgoing` when the sources are the binding's `from` end, `incoming` when they are its `to` end.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- search: Part of a source's name or of a value the view shows, ignoring case; at most 500 characters.
- parentObjectId: Only sources directly under this record.
- pageSize: 1 to 100; the view's page size when omitted.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 MAPPING_VIEW_NOT_FOUND: the application has no such mapping view
- 404 MAPPING_BINDING_NOT_FOUND: the model has no such binding
- 404 MAPPING_PARENT_NOT_FOUND: `parentObjectId` is not in the context
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the context's workspace
- 422 MAPPING_VIEW_BINDING_MISMATCH: the binding is not the view's
- 422 MAPPING_PARENT_SCOPE_MISMATCH: that parent cannot contain the sources
- 422 MAPPING_PROPOSED_NEEDS_CHANGE_SET: `proposed` without `changeSetId`
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/workspaces/{workspace_key}/mapping-candidates

Title: Find target candidates

Lists the records of the view's target type that a source could be mapped to, in name order. A record the binding does not let be chosen, such as a target a one-to-one binding already holds, is left out. Cardinality and scope for the chosen source are checked when the mapping is replaced.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: The application holding the mapping view.
- viewKey: A `mappingGrid` view of the application.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- objectTypeKey: The target type; it must be the view's.
- search: Part of a value of the view's `candidateSearchFields`, ignoring case; at most 500 characters.
- pageSize: 1 to 100; the view's page size when omitted.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 MAPPING_VIEW_NOT_FOUND: the application has no such mapping view
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the context's workspace
- 422 MAPPING_CANDIDATE_TYPE_MISMATCH: `objectTypeKey` is not the view's target type
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/workspaces/{workspace_key}/mapping-targets

Title: Read a source's targets

Reads the targets of one source, a page at a time, for a coverage row that shows only its first. Name the `mappingVersion` the row gave: if the source's mapping has changed since, the read is refused and you read coverage again. Leave out `applicationKey` and `viewKey` to read the binding with names only.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: With `viewKey`, the mapping view whose values the targets show. Send both or neither.
- viewKey: The view's key, with `applicationKey`.
- relationTypeKey: The binding's relation type.
- fromObjectTypeKey: The binding's `from` object type.
- toObjectTypeKey: The binding's `to` object type.
- direction: `outgoing` when the source is the binding's `from` end, `incoming` when it is its `to` end.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- sourceObjectId: The source record's ID.
- mappingVersion: The source's `mappingVersion` from coverage; 0 for a source with no targets.
- pageSize: 1 to 100; 20 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 MAPPING_VIEW_NOT_FOUND: the application has no such mapping view
- 404 MAPPING_BINDING_NOT_FOUND: the model has no such binding
- 404 MAPPING_SOURCE_NOT_FOUND: the context holds no such source
- 409 MAPPING_VERSION_CONFLICT: the mapping changed; `details.mappingVersion` is current
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the context's workspace
- 422 MAPPING_VIEW_REQUIRED: only one of `applicationKey` and `viewKey`
- 422 MAPPING_VIEW_BINDING_MISMATCH: the binding is not the view's
- 422 INVALID_CURSOR: the cursor belongs to another source, version or context
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## PUT /api/v1/workspaces/{workspace_key}/mappings

Title: Replace a source's mapping

Replaces all targets of one source with the one target you name, or with none when `targetObjectId` is `null`, live or, with `changeSetId`, in a change set. Send the source's `mappingVersion` as `expectedMappingVersion`: if another write got there first, nothing changes and `details` carry the current version (`currentVersion`) and the current targets. A replacement that changes nothing writes nothing.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Edit live, or Work in change sets
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set in this workspace
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 MAPPING_ENDPOINT_NOT_FOUND: the source or target is not in the context
- 409 VERSION_CONFLICT: the mapping changed; `details.currentVersion` is current and `details` has its current targets
- 409 CHANGE_SET_REQUIRED: `changeSetId` without `expectedChangeSetVersion`
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 CHANGE_SET_SUBMITTED: the change set is submitted
- 409 WORKSPACE_RETIRED: the workspace is retired
- 409 CARDINALITY_VIOLATION: the target's end already holds its one relationship
- 409 DUPLICATE_RELATION_SCOPE: live only; the target repeats an ancestor scope
- 409 PINNED_MODEL_UNAVAILABLE: the change set's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a field is missing or invalid
- 422 MAPPING_ENDPOINT_TYPE_MISMATCH: the source or target is not of the binding's type
- 422 INVALID_CLEAR_ATTRIBUTES: `attributes` with a `null` target
- 422 UNKNOWN_RELATION_TYPE: the model has no such relation type
- 422 INVALID_RELATION_PAIR: the relation type does not join these types
- 422 IMMUTABLE_RELATION: containment is changed with the parent
- 422 REQUIRED_OWNERSHIP_BINDING: the binding requires its owner
- 422 REQUIRED_RELATION: the replacement leaves a record without a required relationship
- 422 RELATION_ANCESTOR_REQUIRED: the target lacks the scope's ancestor
- 422 RELATION_CANDIDATE_REFUSED: an end does not meet the binding's criteria
- 422 UNKNOWN_RELATION_ATTRIBUTES: the binding has no such attribute
- 422 INVALID_ATTRIBUTE_VALUE: a value is not of its attribute's type
- 422 ATTRIBUTE_BELOW_MINIMUM: a number is under the attribute's minimum
- 422 ATTRIBUTE_ABOVE_MAXIMUM: a number is over the attribute's maximum
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the change set's release is too new
- 409 PINNED_MODEL_INVALID: the change set's release is damaged

## POST /api/v1/workspaces/{workspace_key}/mapping-proposals

Title: Ask the AI for mapping targets

Asks the AI provider to propose targets for the sources a mapping view still lacks, into a change set: the one you name, or a new one you name with `changeSetName`. It answers `202` with a queued job whose `aiProposal` tally reads as it runs. The proposals are edits marked as the AI's, to correct and publish like any others; live data does not change.

### Parameters

- workspace_key: The workspace's key.

### Errors

- 403 FORBIDDEN: needs Work in change sets and Use AI proposals
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set in this workspace
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 MAPPING_VIEW_NOT_FOUND: the application has no such mapping view
- 404 MAPPING_PARENT_NOT_FOUND: `parentObjectId` is not in the change set
- 409 AI_NOT_CONFIGURED: the instance has no AI provider
- 409 AI_SEND_LEVEL_TOO_LOW: `sendLevel` is above the instance's ceiling or too low for this
- 409 CHANGE_SET_VERSION_CONFLICT: `expectedChangeSetVersion` is not current
- 409 WORKSPACE_RETIRED: the workspace is retired
- 422 REQUEST_VALIDATION_ERROR: not exactly one of `changeSetId` and `changeSetName`

## GET /api/v1/workspaces/{workspace_key}/relations

Title: List the relationships of a workspace

Lists every relationship of a workspace, of any relation type, live or in a change set or publication. Each appears in both directions unless `direction` is given. Name the `applicationKey` and `viewKey` of a relationships table to list that view's rows, with its sorts, filters and groups; the view then fixes the binding.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: With `viewKey`, the view whose columns the list follows: a mapping grid or a relationships table. Send both or neither.
- viewKey: The view's key, with `applicationKey`.
- relationTypeKey: Only relationships of this relation type. Not with a relationships table.
- fromObjectTypeKey: Only relationships whose `from` record is of this type. Not with a relationships table.
- toObjectTypeKey: Only relationships whose `to` record is of this type. Not with a relationships table.
- direction: `outgoing` or `incoming`: the end each row's `source` is, so each relationship appears once. Both directions when omitted. Not with a relationships table.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- search: Part of either record's name, ignoring case; at most 500 characters.
- seek: On a relationships table, a value of what the list is ordered by first: the group record's name with `groupBy`, else the sort field. Otherwise the list is in relationship ID order, and a seek compares those IDs.
- pageSize: 1 to 100; the view's page size, else 20, when omitted.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 MAPPING_VIEW_NOT_FOUND: the view is neither a mapping grid nor a relationships table
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the context's workspace
- 422 INCOMPLETE_VIEW_IDENTITY: only one of `applicationKey` and `viewKey`
- 422 RELATION_TABLE_VIEW_REQUIRED: `sort` or a filter without a relationships table
- 422 RELATION_TABLE_BINDING_FIXED: a binding parameter with a relationships table
- 422 INVALID_FILTER: a filter is not one of the view's `filterFields`
- 422 INVALID_SORT: `sort` is not one of the view's `sortFields`
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 422 INVALID_SEEK: `seek` does not fit the sort field
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## GET /api/v1/workspaces/{workspace_key}/relation-grid

Title: Read a relationships grid

Reads a relationships table as a grid: each record of the view's `from` type once, linked or not, with its relationships to the shown `to` records, which `columns` list with how many rows each is linked to. Use it to review or change values across many records; `POST /api/v1/relations/grid-change` writes them.

### Parameters

- workspace_key: The workspace's key.
- applicationKey: The application holding the relationships table.
- viewKey: A `relationTable` view of the application, whatever its layout.
- changeSetId: Read this change set's work in progress. Not with `publicationId`.
- publicationId: Read this published state. Not with `changeSetId`.
- pageSize: Rows per page, 1 to 100; the view's page size when omitted.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 404 WORKSPACE_NOT_FOUND: `workspace_key` names no workspace
- 404 RELATION_TABLE_NOT_FOUND: the view is not a relationships table
- 409 CHANGE_SET_BASE_INVALID: the change set's base is unusable
- 409 PINNED_MODEL_UNAVAILABLE: the context's release is not installed
- 422 REQUEST_VALIDATION_ERROR: a parameter is missing or invalid
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspace_key` is not the context's workspace
- 422 INVALID_ATTRIBUTE: an `attribute` is not one of the view's `attributeColumns`
- 422 INVALID_FILTER: a filter is not one the grid offers
- 422 INVALID_SORT: `sort` is not one of the view's `sortFields`
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 INVALID_POSITION: `position` is below zero
- 422 INVALID_SEEK: `seek` does not fit the sort field
- 409 UNSUPPORTED_PINNED_MODEL_SCHEMA: the context's release is too new
- 409 PINNED_MODEL_INVALID: the context's release is damaged

## Schemas

### MappingObjectSummary

- id: The record's ID.
- objectTypeKey: The record's object type.
- name: The record's name.
- fields: The values the view selects for the record, keyed by field; a missing value is `null`.

### MappingCoverageRow

- source: The source record, with the values of the view's `sourceColumns`.
- state: `mapped`: the source has a target, or several where it may hold many; `unmapped`: it has none; `ambiguous`: it has several where it may hold one.
- mappingVersion: The version of the source's mapping, which rises with every change to its targets. A replacement and a read of its targets name it.
- targetCount: How many targets the source has.
- targets: The first targets, at most 20.
- targetsNextCursor: Send it as `cursor` to `GET .../mapping-targets` with `sourceObjectId` and `mappingVersion` for the other targets; `null` when `targets` holds them all.

### MappingTargetPage

- mappingVersion: The mapping version the page was read at, the request's.
- targetCount: How many targets the source has.

### MappingTargetSummary

- relationId: The relationship to the target.
- attributes: The relationship's values, keyed by attribute type key.
- object: The target record.
- origin: Who proposed the target when the AI did and nobody has changed it since; left out otherwise.

### MappingReplacementRequest

- relationTypeKey: The binding's relation type.
- fromObjectTypeKey: The binding's `from` object type.
- toObjectTypeKey: The binding's `to` object type.
- direction: `outgoing` when the source is the binding's `from` end, `incoming` when it is its `to` end.
- sourceObjectId: The record whose targets are replaced.
- targetObjectId: The one target, or `null` to leave the source without targets.
- expectedMappingVersion: The source's `mappingVersion` as read; 0 for a source with no targets.
- attributes: The relationship's values, keyed by attribute type key, replacing its stored ones; `{}` clears them. Omit it to keep a kept relationship's values. Not with a `null` target.
- changeSetId: Replace in this change set instead of live data.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`.

### MappingReplacementResponse

- sourceObjectId: The source record's ID.
- mappingVersion: The version of the source's mapping now; unchanged when the request changed nothing.
- state: `mapped` with a target, `unmapped` without.
- relationId: The relationship to the target; `null` when unmapped.
- changeSetVersion: The change set's `version` after the write; `null` live.

### MappingProposalRequest

Asks the AI provider for targets for the unmapped sources of a mapping view, into a change set: `changeSetId` with `expectedChangeSetVersion`, or `changeSetName` for a new change set the request creates; exactly one. `search` and `parentObjectId` narrow the sources as the grid does; `sendLevel` is a level lower than the instance's ceiling.

- applicationKey: The application holding the mapping view.
- viewKey: The `mappingGrid` view whose unmapped sources get proposals.
- search: Only sources whose name or shown values contain this text, ignoring case.
- parentObjectId: Only sources directly under this record.
- changeSetId: Propose into this change set. Give this or `changeSetName`.
- expectedChangeSetVersion: The change set's `version`; required with `changeSetId`, not allowed with `changeSetName`.
- changeSetName: Propose into a new change set of this name.
- sendLevel: What the provider may be sent for this request: `structure`, `samples` or `values`; never above the instance's `AI_SEND_LEVEL`.

### MappingListPage

- groupCounts: On a relationships table with `groupBy`: how many rows each group record on the page holds under the filters, keyed by the record's ID; left out otherwise.

### MappingListRow

- relationId: The relationship's ID.
- relationTypeKey: The relation type's key.
- direction: `outgoing` when `source` is the relationship's `from` end, `incoming` when it is the `to` end.
- source: The record the relationship is read from; on a relationships table the `from` record.
- target: The record at the other end; on a relationships table the `to` record.
- attributes: The relationship's values, keyed by attribute type key.
- relationVersion: The relationship's version, which a change of its values names as `expectedVersion`.
- mappingVersion: The version of the source's relationship set for this binding; 0 in a publication.

### RelationGridPage

- columns: The column records, at most 50, in name order.
- columnTotal: How many records match the column filters and the `toObjectId` pick; more than 50 are not in `columns`.
- rowTotal: How many rows match the row filters.

### RelationGridColumn

- id: The column record's ID.
- objectTypeKey: The column record's object type.
- name: The column record's name.
- label: The value of the view's first `toColumns` field.
- fields: The values of the view's `toColumns`.
- linkedCount: How many rows, under the filters and across every page, are related to it.

### RelationGridRow

- source: The `from` record, with the values of the view's `fromColumns`.
- mappingVersion: The version of the row's relationship set for this binding, which a link claims.
- relations: The row's relationships to the shown columns, keyed by column record ID; a column without an entry is not linked.

### RelationGridRelation

- relationId: The relationship's ID.
- version: The relationship's version, which a change of its values names as `expectedVersion`.
- attributes: The relationship's values: the `attribute`s the request chose, else every stored one.
- proposed: Whether a change set stages the relationship; always `false` live and in a publication.
