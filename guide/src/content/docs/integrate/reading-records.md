---
title: Reading records
description: Choose precise record, query and relationship reads without walking an entire workspace.
reader: integrator
---

Choose a read by what you already know. The [object operations](/docs/api/?api=management#tag/objects) offer individual records, per-type collections and a cross-type lookup. The [query operation](/docs/api/?api=management#tag/queries) selects one type using the model's fields and relationships. All use the selected [workspace and context](/docs/integrate/workspaces-contexts-and-models/).

## Find records

Use the cross-type lookup when the type is unknown: search names and built-in fields, narrow to types, an application, a parent or the top level. A parent scope and a top-level scope cannot be combined (`MUTUALLY_EXCLUSIVE_SCOPE`). Model-declared attributes belong to per-type reads: asking for one on the cross-type lookup is refused with guidance to that route.

Use a per-type list for searchable or filterable attributes declared on that type. Keep filter values typed. A boolean stays a boolean; dates and date-times follow their declared types. Date-times keep their UTC instant and explicit offset; a missing zone means UTC. Equivalent decimals read in a canonical form without trailing zeros. Do not turn all values into text to make handling easier.

Use the model-aware query to combine typed field criteria, an ancestor at any depth, or one relationship hop or its absence. You can select fields, choose a sort and include related records. Ancestor field output chooses the matching ancestor nearest the root. A related criterion does not mean an unbounded recursive graph traversal.

Expansions return at most 20 related records per item. Follow their continuation through the [relationship collection](/docs/api/?api=management#tag/relations) when you need the rest. A query's main cursor continues that query only. For date-sensitive questions, read [Business dates](/docs/integrate/business-dates/): dating the root records does not date their expansions.

## Read relationships and values

The [workspace edge list](/docs/api/?api=management#tag/relations) reads all or selected relationship types in one workspace, including snapshot contexts. A selected mapping view changes the projected fields; without it the ends expose identity and name. Without a direction restriction the mapping list can show both orientations of an edge. Keep physical relationship identity if deduplicating.

Relationships of one record can be searched and sorted by the related records' fields. Read an individual attribute through the [attribute operations](/docs/api/?api=management#tag/attributes), in the same context as its record. Their add, change and remove operations claim the owning record version. Adding an existing value is `ATTRIBUTE_ALREADY_EXISTS`; changing or removing an absent one is `ATTRIBUTE_NOT_FOUND`; a required value cannot be removed (`CANNOT_DELETE_REQUIRED_ATTRIBUTE`). Fields not bound to the type cannot be written.

## Correct an invalid read

`INVALID_FILTER`, `INVALID_SORT`, `INVALID_QUERY`, `INVALID_EXPAND`, `INVALID_RANGE` or `INVALID_DATE` require correcting the request against the current model and operation. `INVALID_OBJECT_TYPE_FOR_APPLICATION` means the selected type is outside that application. `OBJECT_TYPE_CHANGED` means reread the record before using the old type route. `UNKNOWN_ATTRIBUTE_TYPE` requires checking the definition key, while `VIEW_NOT_FOUND` requires selecting a view in the current context.

For [relation matrix operations](/docs/api/?api=management#tag/relation-matrix), `CONFLICTING_COLUMN_PARAMETERS`, `DUPLICATE_COLUMN_IDS` and `TOO_MANY_COLUMNS` require a valid bounded column selection. `RELATION_MATRIX_STATE_REQUIRES_COLUMNS` needs a column scope before filtering by state. `RELATION_MATRIX_VIEW_NOT_FOUND`, `RELATION_MATRIX_PARENT_NOT_FOUND`, `RELATION_MATRIX_ROW_NOT_FOUND` and `RELATION_MATRIX_COLUMN_NOT_FOUND` require selecting the declared view and records of its expected types in the same context. `RELATION_MATRIX_PARENT_SCOPE_MISMATCH` requires a parent type that can contain its rows. `RELATION_MATRIX_ACTION_NOT_ALLOWED` means the model does not permit the requested cell change. At most 20 columns can be chosen together; without a selection the columns page separately. A cell preview holds at most five records while reporting its full count; open the cell collection to read the rest. Incoming views cannot show inactive or uniqueness-conflict states from rules declared on the binding's target end. Matrix state remains maintained when writers race; the client must still respect version conflicts.

Use [paged traversal](/docs/guide/integrate/read-a-collection-completely-and-resume/) for a complete result, and [bulk writes](/docs/integrate/writing-in-bulk/) for changes, including typed relationship values and initial relationships.

## Read and replace a mapping set

The [mapping operations](/docs/api/?api=management#tag/mapping) expose a declared mapping view's coverage, candidate records and target membership. Keep the application and view together with the workspace and context. Target details give the exact count and at most 20 preview targets; follow their continuation for the rest. That continuation is bound to the set version. If membership changes, reread the set rather than joining pages from different versions.

Read the existing set before replacing it and retain its set version. Submit all intended targets together, including existing targets you want to keep. On a single-target mapping save, omitting relationship attributes retains their values. Sending an explicit attribute object replaces those values; an empty object clears them only where valid. Clearing the target accepts no non-empty relationship values. Replacement preserves suitable existing relationships and refuses a stale set, so a concurrent edit cannot disappear behind your save. See [Versions and conflicts](/docs/integrate/versions-and-conflicts/) and [Bulk relationship sets](/docs/integrate/writing-in-bulk/#relationships-and-sets).

| Refusal | Recovery |
| --- | --- |
| `INCOMPLETE_VIEW_IDENTITY` or `MAPPING_VIEW_REQUIRED` | Supply both parts of the selected view identity. |
| `MAPPING_BINDING_NOT_FOUND` | Discover an allowed relationship binding in the context's model. |
| `MAPPING_VIEW_BINDING_MISMATCH` | Use the binding and direction declared by the selected view. |
| `MAPPING_PARENT_SCOPE_MISMATCH` | Select a parent whose type can contain the view's sources. |
| `MAPPING_CANDIDATE_TYPE_MISMATCH` | Ask for candidates on the view's target side. |
| `MAPPING_SOURCE_NOT_FOUND` or `MAPPING_ENDPOINT_NOT_FOUND` | Reread the source and targets in the selected workspace and context. |
| `MAPPING_ENDPOINT_TYPE_MISMATCH` | Use endpoints of the binding's declared types. |

## Keep query and edge continuations separate

The workspace Relations and Mappings reads expose the same edge-list contract. The anchored relationship read is a different collection; a cursor from one route does not continue another. Use either a change-set or publication context, never both (`MUTUALLY_EXCLUSIVE_CONTEXT`).

Model-aware queries combine criteria with AND, support one relationship hop or its absence, and one sort field with a stable tie breaker. They do not support OR groups or nested relationship hops. Field criteria follow the type’s filterable declarations. A criterion for an ancestor tests containment, rather than following an arbitrary relation. An expansion limit is 1–20; the expansion reports its full count and a continuation through the relationship collection.

Selected query items always retain public ID, type and version; selected values are under `fields`. Omitting selection uses the list’s usual item shape. The main cursor binds the query body, so preserve criteria, selection, expansions, context and business date when continuing. A malformed body uses `REQUEST_VALIDATION_ERROR`; model-dependent mistakes use `INVALID_QUERY` with a pointer. Consult the [query operation](/docs/api/?api=management#tag/queries) for its full grammar.

Attribute values preserve their declared JSON form. Decimal responses use precision-preserving strings, while requests can supply a decimal number. Integers and booleans remain numbers and booleans. Dates use ISO 8601 days, and date-times return their UTC instant with an explicit offset. Treat missing and empty text as no value.

Unique attributes are unique across all records carrying that attribute type within a workspace, including different object types. Scalar types support uniqueness; JSON does not. `DUPLICATE_ATTRIBUTE_VALUE` identifies the attribute and conflicting record. Any number of records can leave a unique text value empty. Do not use a non-unique name as a substitute for a batch key.
