# model

The model is the engine's whole description of a dataset: its applications and views, object types, attribute types, relation types and the consumer APIs. A model is installed as an immutable release, and each workspace runs one release. You use this area to read the model a context runs (to build a client from it), to validate a model document before installing it, and to inspect, compare, retire or delete installed releases. Drafts, installing and activating are in the model authoring areas.

1. Build a client: `GET /api/v1/model` for the whole document, or the per-element reads for one part, in the workspace, change set or publication you work in.
2. Check a candidate: `POST /api/v1/model-validations`, then `GET /api/v1/model-releases/{release_id}/diff` against the release a workspace runs.

## GET /api/v1/capabilities

Title: Read what this instance offers

Tells which optional surfaces are switched on and their limits, so a client can decide what to show before it calls. Each group names the setting that controls it; ask the operator to change a setting, the client cannot. Any signed-in caller may read it.

### Errors

- 401 AUTHENTICATION_REQUIRED: no token

## GET /api/v1/model

Title: Read the model

Reads the complete model document the context runs: the workspace named by `workspaceKey` (the default workspace without it), or the release a `changeSetId` or `publicationId` is pinned to. The answer carries the model's `ETag`, `X-Model-Release-Id` and `RDM-Workspace` headers. Use it to build a client; the per-element reads add IDs.

### Parameters

- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/model/placements

Title: Read where records may stand

Reads, per application, which object types may stand at the top level and, under each type as a parent, which types it contains and which a record can become there. The engine uses the same rule for adding children, moving and restructuring, so a client reads it instead of working it out. It answers with the model's `ETag`.

### Parameters

- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/model/consumer-apis/{consumerApi}

Title: Read a consumer API definition in full

Reads one consumer API definition of the context's model with every default written out: public names, operations, generated events and each `matchOn` and `within.types`. Use it to see what a consumer API actually offers; `GET /api/v1/model` returns the definition as the author wrote it. The answer carries the model's `ETag`.

### Parameters

- consumerApi: The definition's `key`, which is the name in `/api/consumer/{consumerApi}`.
- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 CONSUMER_API_NOT_FOUND: the model declares no such API
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## POST /api/v1/model-validations

Title: Validate a model document

Checks a model document against the schema and every reference rule without storing anything. An invalid document is not an error: the answer is `200` with `valid: false` and each problem as a diagnostic with its JSON pointer. A document of an unsupported `schemaVersion` is reported the same way.

### Errors

- 403 FORBIDDEN: needs Model authoring at the instance
- 422 REQUEST_VALIDATION_ERROR: the body has no `model` object

## GET /api/v1/applications

Title: List applications

Lists the applications of the context's model with their IDs, views, detail pages and the object types each holds, in key order. Use it to build navigation; the whole model document has the same content without IDs.

### Parameters

- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list or release
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/applications/{application_key}

Title: Get an application

Reads one application of the context's model, with its views and detail pages, when a client needs a single application rather than the list. Use the `key` as the address of the application's records and views elsewhere; the `id` is for reference only.

### Parameters

- application_key: The application's `key`.
- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 UNKNOWN_APPLICATION: the model has no such application
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/attribute-types

Title: List attribute types

Lists the attribute types of the context's model, in key order: the typed, reusable definitions that object types bind. Use it to learn what values a field takes and how it is validated.

### Parameters

- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list or release
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/attribute-types/{attribute_type_key}

Title: Get an attribute type

Reads one attribute type of the context's model by its `key`, for example to check a field's value type, default and limits before sending a value. The attribute types an object type binds are listed with the object type.

### Parameters

- attribute_type_key: The attribute type's `key`.
- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 UNKNOWN_ATTRIBUTE_TYPE: the model has no such attribute type
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/object-types

Title: List object types

Lists the object types of the context's model, in key order, each with the attributes it binds. Use it to learn what a record of a type holds, which attributes are required or read-only, and whether the type may stand without a parent.

### Parameters

- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list or release
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/object-types/{object_type_key}

Title: Get an object type

Reads one object type of the context's model by its `key`, with the attributes it binds, in order. Use it before creating a record to see which attributes are required or read-only and whether the type may stand without a parent.

### Parameters

- object_type_key: The object type's `key`.
- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 UNKNOWN_OBJECT_TYPE: the model has no such object type
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/relation-types

Title: List relation types

Lists the relation types of the context's model, in key order, each with the pairs of object types it may join. Use it to learn which relationships a client may create and their cardinality.

### Parameters

- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list or release
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/relation-types/{relation_type_key}

Title: Get a relation type

Reads one relation type of the context's model by its `key`, with every pair of object types it may join. The `reverseKey` names the same relation from the other end but is not an address; read the type by `key`.

### Parameters

- relation_type_key: The relation type's `key`, not its `reverseKey`.
- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 UNKNOWN_RELATION_TYPE: the model has no relation type with this key
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/object-type-relations

Title: List permitted relationships

Lists the bindings of the context's model, each saying that a relation type may join one object type to another, with its cardinality, whether it is required and the attributes the relationship may carry. Ordered by relation type, then source type, then target type. Narrow it with `fromObjectType` and `toObjectType`.

### Parameters

- fromObjectType: Only bindings whose source is this object type's `key`.
- toObjectType: Only bindings whose target is this object type's `key`.
- workspaceKey: The workspace whose model to read; the default workspace without it.
- changeSetId: Read the model the change set was opened on. Not with `publicationId`.
- publicationId: Read the model the publication was made under. Not with `changeSetId`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Browse in the workspace
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 404 CHANGE_SET_NOT_FOUND: `changeSetId` names no change set
- 404 PUBLICATION_NOT_FOUND: `publicationId` names no publication
- 409 MODEL_RELEASE_CHANGED: `X-Expected-Model-Release-Id` is not the release read
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page
- 422 MUTUALLY_EXCLUSIVE_CONTEXT: `changeSetId` with `publicationId`
- 422 WORKSPACE_CONTEXT_MISMATCH: `workspaceKey` is not the context's workspace
- 503 MODEL_REGISTRY_UNAVAILABLE: the release cannot be served by this engine

## GET /api/v1/model-releases

Title: List model releases

Lists the installed releases, oldest first, each with the workspaces that run it and whether it can be deleted. Use it to choose a release for a workspace or to find releases that can be retired.

### Parameters

- releaseKey: Only releases of the model with this key.
- assigned: `true`: releases some workspace runs. `false`: releases none runs.
- status: `active`, `retired` or `all` (the default).
- usable: `true` keeps the releases a caller may choose: active, and of a schema this engine reads.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Model authoring or Model release
- 422 REQUEST_VALIDATION_ERROR: `status`, `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to other filters or another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/model-releases/{release_id}

Title: Get a model release

Reads one installed release, with the workspaces that run it and whether it can be deleted. Add `includeModel=true` to get its complete model document, which can be large; without it the answer has no `model`.

### Parameters

- release_id: The release's `id`.
- includeModel: `true` adds the release's complete model document; `false` by default.

### Errors

- 403 FORBIDDEN: needs Model authoring or Model release
- 404 MODEL_RELEASE_NOT_FOUND: no installed release has this ID

## PATCH /api/v1/model-releases/{release_id}

Title: Retire or restore a model release

Retires a release or brings it back. A retired release is refused wherever a release is chosen (a new workspace, a change set, an activation, a migration), while every workspace and change set already on it keeps working. Its model never changes. Asking for the status it already has changes nothing.

### Parameters

- release_id: The release's `id`.

### Errors

- 403 FORBIDDEN: needs Install a model at the instance
- 404 MODEL_RELEASE_NOT_FOUND: no installed release has this ID
- 409 MODEL_RELEASE_VERSION_CONFLICT: `expectedStatusVersion` is not current
- 409 MODEL_RELEASE_IS_DEFAULT: the default workspace runs it
- 422 REQUEST_VALIDATION_ERROR: `status` or `expectedStatusVersion` is invalid

## DELETE /api/v1/model-releases/{release_id}

Title: Delete a model release

Deletes a release nothing refers to, with its structure. It is refused while a workspace runs it or any record, change set, publication, job, import profile or model mapping was made under it; retire it instead. Drafts that started from it stay, without the link.

### Parameters

- release_id: The release's `id`.
- expectedStatusVersion: The release's `statusVersion` as you read it.

### Errors

- 403 FORBIDDEN: needs Install a model at the instance
- 404 MODEL_RELEASE_NOT_FOUND: no installed release has this ID
- 409 MODEL_RELEASE_VERSION_CONFLICT: `expectedStatusVersion` is not current
- 409 MODEL_RELEASE_IN_USE: something refers to the release
- 422 REQUEST_VALIDATION_ERROR: `expectedStatusVersion` is missing or invalid

## GET /api/v1/model-releases/{release_id}/activations

Title: List a release's activations

Lists the recorded selections of this release as a workspace's model, oldest first, with the release each replaced and who made it. A release first selected when the instance was set up has no item for that selection.

### Parameters

- release_id: The release's `id`.
- pageSize: 1 to 500; 100 by default.

### Errors

- 403 FORBIDDEN: needs Model authoring or Model release
- 404 MODEL_RELEASE_NOT_FOUND: no installed release has this ID
- 422 REQUEST_VALIDATION_ERROR: `pageSize` or `position` is invalid
- 422 INVALID_CURSOR: the cursor belongs to another list
- 422 CONFLICTING_PAGE_PARAMETERS: more than one way to select a page

## GET /api/v1/model-releases/{release_id}/diff

Title: Compare two model releases

Lists what changed from `againstReleaseId` to the release in the address, and what activating it would do: whether stored data fits it, in the workspace named by `workspaceKey` (the default without it) and in each workspace running a release of the same model, and whether consumer contracts changed without a higher `contractVersion`. Use it before activating.

### Parameters

- release_id: The candidate release's `id`, the newer side of the comparison.
- againstReleaseId: The baseline release's `id`, the older side.
- workspaceKey: The workspace whose activation `compatibility` and `consumerContracts` describe, against its own release and data; the default workspace without it.

### Errors

- 403 FORBIDDEN: needs Model authoring or Model release
- 404 MODEL_RELEASE_NOT_FOUND: either release is not installed
- 404 WORKSPACE_NOT_FOUND: `workspaceKey` names no workspace
- 422 REQUEST_VALIDATION_ERROR: `againstReleaseId` is missing
- 422 UNSUPPORTED_SCHEMA_VERSION: a release's schema cannot be compared by this engine
- 500 INVALID_INSTALLED_MODEL: a stored release fails validation
- 503 MODEL_REGISTRY_UNAVAILABLE: the workspace's release cannot be served

## POST /api/v1/model-releases/{release_id}/raising

Title: Raise a release's schema

Rewrites an installed release written in a schema this engine no longer reads into the schema it reads, in place; its ID, key and version stay, so records, change sets and publications follow. Send `confirm: false` to preview, which changes nothing, then `confirm: true` with the previewed `modelHash`.

### Parameters

- release_id: The release's `id`.

### Errors

- 403 FORBIDDEN: needs Install a model at the instance
- 404 MODEL_RELEASE_NOT_FOUND: no installed release has this ID
- 409 MODEL_HASH_CHANGED: the release changed after the preview
- 422 REQUEST_VALIDATION_ERROR: `confirm: true` without `expectedModelHash`
- 422 RELEASE_NOT_RAISABLE: its schema is already read as it is, or is newer
- 422 RELEASE_RAISE_REFUSED: the raised document is invalid or equals another release

## Schemas

### ModelReleaseDefinition

- key: Names the model; shared by every release of it. Install refuses a release whose key and version are installed already.
- name: The model's name, as people read it.
- version: The release's version text. A key and version pair identifies one release.

### ProductDefinition

- name: The product's name, as people read it.
- description: What the product is, in one or two sentences; `null` if none.

### EngineModel

- schemaVersion: The model language the document is written in. This engine reads `0.10`; another value is refused with `UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`.
- release: Which release this document is: the model's key, name and version.
- product: The product the model serves, shown to people.
- attributeTypes: The reusable, typed value definitions that object types bind. Keys are unique.
- objectTypes: The kinds of record. Keys are unique.
- relationTypes: The kinds of relationship. Keys and reverse keys share one namespace, so no two are equal.
- objectTypeRelations: The bindings that say which relation type may join which object type to which. Each relation type, source and target triple appears once.
- applications: The workspaces people use: which types an application holds and its views, detail pages and navigation. Keys are unique.
- consumerApis: The read APIs for other systems. Left out when the model declares none.

### AttributeTypeDefinition, AttributeTypeResponse

- key: Names the attribute type in addresses and bindings; unique among attribute types.
- name: The name people read.
- description: What the attribute holds, for people; `null` if none.
- valueType: What a value is: `text`, `longText`, `integer`, `decimal`, `boolean`, `date` (YYYY-MM-DD), `dateTime` (UTC; a value without a zone is read as UTC) or `json`. `text` and `longText` differ only in how a client shows them.
- default: The value a new record gets when it is created without one, in the shape of `valueType`; `null` for none.
- features: Switches, each true or false: `unique` (no two records in a workspace hold the same value; not for `json`), `searchable` (a text `query` and consumer API matching may read it), `filterable` (a table view may offer it as a filter), `sortable` (a generated view offers it as a sort option).
- validation: Limits a value must meet. `minimum` and `maximum` are finite numbers and only for `integer` and `decimal`; `minimum` may not exceed `maximum`. A value outside answers `ATTRIBUTE_BELOW_MINIMUM` or `ATTRIBUTE_ABOVE_MAXIMUM`.
- ui: Display hints: `hidden` (true or false) and `helpText` (text). Other keys are kept as written and ignored.

### AttributeTypeResponse

- id: The attribute type's ID in this release. Read-only; use `key` in addresses.

### ObjectTypeAttributeDefinition

- attributeTypeKey: The attribute type this binding attaches; each type is bound once per object type.
- required: `true`: a record needs a value (a default fills one in). `false` by default.
- readOnly: `true`: clients may not set or clear it (`READ_ONLY_ATTRIBUTES`). `false` by default.
- order: Position among the type's attributes, lowest first. 0 by default.
- ui: Display hints for this binding that override the attribute type's: `hidden` and `helpText`.

### AttributeBindingResponse

- id: The binding's ID in this release.
- attributeTypeKey: The bound attribute type's `key`.
- name: That attribute type's name.
- valueType: That attribute type's `valueType`.
- required: `true`: a record needs a value.
- readOnly: `true`: clients may not set or clear it.
- order: Position among the type's attributes, lowest first.

### EffectivePeriodDefinition

A type's business validity, read from two `date` attributes: the start is inclusive and the end exclusive, and either may be empty.

- startAttributeTypeKey: A `date` attribute the type binds; the day the record becomes valid, inclusive. May be empty on a record.
- endAttributeTypeKey: A different `date` attribute the type binds; the day validity ends, exclusive. May be empty on a record.

### ObjectTypeDefinition

- key: Names the object type in addresses; unique among object types.
- name: The name of one record's kind, as people read it.
- pluralName: The name for several, shown on lists.
- description: What the type is, for people; `null` if none.
- icon: A presentation hint for the type, kept as written and not checked by the engine; `null` if none.
- displayAttributeTypeKey: The bound attribute that names a record to a person; it must be bound. `null` for none.
- attributes: The attribute types a record of this type may hold, one binding per attribute type.
- features: Switches: `rootCreatable` (true: a record may stand without a parent; the type may be a top-level or tree root).
- behavior: `parentRelationTypeKeys`: the relation types that place a record under its parent. Each must be a binding that ends at this type. A type without them has no parent.
- validation: `atLeastOneOf`: attribute type keys, all bound and without repeats; a record needs a value in at least one (`OBJECT_ATTRIBUTE_RULE_VIOLATION`).
- effectivePeriod: The two `date` attributes that give a record its validity; `asOf` reads use it. Left out when the type has none.

### ObjectTypeResponse

- id: The object type's ID in this release.
- key: Names the object type in addresses.
- name: The name of one record's kind.
- pluralName: The name for several.
- description: What the type is; `null` if none.
- icon: A presentation hint, kept as written; `null` if none.
- displayAttributeTypeKey: The bound attribute that names a record to a person; `null` for none.
- attributes: The attributes a record may hold, in `order`.
- features: Switches such as `rootCreatable`, as in the model document.
- behavior: `parentRelationTypeKeys`, as in the model document.
- validation: `atLeastOneOf`, as in the model document.

### RelationTypeDefinition

- key: Names the relation type read from the source record's side (outgoing); unique together with all reverse keys.
- reverseKey: Names the same relation read from the target's side (incoming).
- name: The relation's name from the source's side, as people read it.
- reverseName: The relation's name from the target's side.
- isOriented: `true` (the default): the ends differ, and a required one-to-one or one-to-many binding makes the source the owner of the target when records are deleted. `false`: the ends are peers and no binding makes an owner.
- features: Switches: `parentOf` (the relation places a record under a parent, containment), `hierarchical` (a type contains records of itself), `searchable` and `creatableOnChildAdd` (hints for clients; the engine acts on neither).

### RelationTypeResponse

- id: The relation type's ID in this release.
- key: Names the relation type from the source's side.
- name: Its name from the source's side.
- reverseKey: Names the relation from the target's side.
- reverseName: Its name from the target's side.
- isOriented: `false` means the ends are peers.
- features: Switches such as `parentOf` and `hierarchical`, as in the model document.
- allowedPairs: The bindings of this relation type: each pair of object types it may join.

### CandidateCriterion

One criterion a record at a binding's end must meet to be chosen: a field criterion over the record's own fields or an ancestor's (`ancestor:<type>.<field>`).

- field: What to compare on a record at that end: `name`, an attribute the type binds (not `json`), or `ancestor:<type>.<field>` for a field of an ancestor of that type.
- op: The comparison. Text: `eq`, `contains`, `startsWith`, `isNull`, `isUnset`. Number, date and date-time: `eq`, `lt`, `lte`, `gt`, `gte`, `isNull`, `isUnset`. Yes/no: `eq`, `isNull`, `isUnset`. `isUnset` is for attributes only.
- value: What to compare with, in the field's own form: text, a number, a date `YYYY-MM-DD`, a date-time, or `true` or `false` (for yes/no fields and for `isNull` and `isUnset`).

### BindingCandidates

Which records may be chosen at each end of a binding: criteria are combined with AND, and several `eq` on one field are alternatives. An end without criteria is unrestricted.

- from: Criteria a source record must meet to be chosen. All must hold; several `eq` on one field are alternatives. Empty: any record.
- to: Criteria a target record must meet to be chosen. Same rules.

### ObjectTypeRelationDefinition

- relationTypeKey: The relation type this binding permits.
- fromObjectTypeKey: The source object type.
- toObjectTypeKey: The target object type. The three keys together identify the binding.
- cardinality: `one-to-one`, `one-to-many`, `many-to-one` or `many-to-many` (the default): how many relationships a record at each end may hold in this binding. `many-to-one` cannot be `required`.
- required: `true`: the target record must be created with the relationship, and it cannot be removed on its own. `false` by default.
- attributeTypeKeys: Attribute types a relationship of this binding carries; empty: none.
- features: Rules on this binding: `uniqueToAncestorTypeKey` (an object type key: a source holds at most one relationship to targets under the same ancestor of that type) and `uniqueWhenToAttributeEquals` (`{attributeTypeKey, value}`: that rule applies only to targets whose attribute equals the value).
- candidates: Limits which records may be chosen at each end. Left out when neither end is limited.

### ObjectTypeRelationResponse

- relationTypeKey: The relation type this binding permits.

### AllowedObjectTypePair, ObjectTypeRelationResponse

- id: The binding's ID in this release.
- fromObjectTypeKey: The source object type.
- toObjectTypeKey: The target object type.
- cardinality: `one-to-one`, `one-to-many`, `many-to-one` or `many-to-many`.
- required: `true`: the target record is created with the relationship and the relationship cannot be removed on its own.
- attributeTypeKeys: The attribute types a relationship of this binding carries.
- features: `uniqueToAncestorTypeKey` and `uniqueWhenToAttributeEquals`, as in the model document.

### TableViewConfig

- columns: What each row shows, in order, at least one: `id`, `name`, `path`, `createdAt`, `updatedAt`, a bound attribute type key, or `related:<relation key>` (the related records' names; `related:<key>.<field>` shows one of their fields).
- filterFields: What the list may be filtered by, at least one, no repeats: `id`, `name`, `createdAt`, `updatedAt`, a `filterable` attribute, or `related:<key>` (the relationship alone).
- sortFields: What the list may be sorted by, at least one: the built-in fields, `objectType`, any non-`json` bound attribute, or a `related:` column that holds at most one record and shows names.
- defaultSort: One of `sortFields`, with `-` in front for descending.
- pageSize: Rows per page, 1 to 100.
- availabilityField: A boolean attribute of the type; a record whose value is `false` is shown as inactive. Left out when unused.

### TableViewDefinition

- key: Names the view within its application.
- name: The name people read.
- objectTypeKey: The object type whose records the view lists.
- type: `table`.
- config: The view's settings.

### MappingGridViewConfig

- relationTypeKey: The relation type whose relationships the grid edits. It is not a containment relation, and the binding is not a required one-to-one or one-to-many one.
- fromObjectTypeKey: The source object type of the binding.
- toObjectTypeKey: The target object type of the binding.
- direction: `outgoing`: the rows are the binding's source records. `incoming`: the rows are its target records.
- sourceColumns: What a row shows of its record, at least one: `name` or a bound attribute.
- targetDisplayColumns: What the mapped records show, at least one.
- candidateSearchFields: Fields searched when choosing a target, at least one: bound, `searchable` attributes of the target type.
- pageSize: Rows per page, 1 to 100.

### MappingGridViewDefinition

- key: Names the view within its application.
- name: The name people read.
- type: `mappingGrid`.
- config: The view's settings.

### RelationMatrixViewConfig

- relationTypeKey: The relation type between the rows' records and the cells' records. It is not a containment relation.
- direction: `outgoing` or `incoming`: which end the row type is.
- rowObjectTypeKey: The type of the rows.
- columnObjectTypeKey: The type of the columns; its records must contain the cell type through `parentRelationTypeKeys`.
- cellObjectTypeKey: The type of the records shown in cells: the related records, placed in the column of the ancestor they sit under.
- rowColumns: What each row shows of its record, at least one.
- columnLabelField: What labels a column: `name` or a scalar attribute of the column type.
- cellFields: What a cell shows of each record, at least one, bound to the cell type.
- searchFields: Fields searched when choosing a record for a cell, at least one: `name` or a `searchable` attribute of the row type.
- cellActions: What a person may do in a cell: `create`, `edit`, `link`, `unlink`. An action that could never succeed on this model is refused. Empty: read only.
- pageSize: Rows per page, 1 to 100.

### RelationMatrixViewDefinition

A relationship matrix: each row's related records, in columns by the ancestor record they sit under.

- key: Names the view within its application.
- name: The name people read.
- type: `relationMatrix`.
- config: The view's settings.

### RelationTableViewConfig

A table of one binding's relationships, one row each. `fromColumns` and `toColumns` are `name` or a scalar attribute of that end's type; `attributeColumns` are attribute types the binding declares (`attributeTypeKeys`). A filter or sort field names its place: `from:<field>`, `to:<field>` (`name` or a scalar attribute of that end's type) or `relation:<attribute>`. `defaultSort` is one of `sortFields`, with `-` for descending. `groupBy` heads the rows by their `from` or `to` record. With `layout` `grid`, each `from` record is shown once with a column group per `to` record and the relationship's `attributeColumns` under it: `from:` sorts order the rows, `groupBy` is ignored and the first `toColumns` field labels a column group.

- relationTypeKey: The relation type whose relationships are the rows. It is not a containment relation.
- fromObjectTypeKey: The source type of the binding.
- toObjectTypeKey: The target type of the binding.
- fromColumns: What a row shows of its source record, at least one: `name` or a scalar attribute.
- toColumns: What a row shows of its target record, at least one.
- attributeColumns: Attribute types of the relationship itself to show; each must be in the binding's `attributeTypeKeys`.
- filterFields: What the list may be filtered by: `from:<field>`, `to:<field>` (`name` or a `filterable` attribute of that end) or `relation:<attribute>`.
- sortFields: What the list may be sorted by, at least one, written like filter fields.
- defaultSort: One of `sortFields`, with `-` in front for descending.
- groupBy: `from` or `to`: rows are headed by that end's record. Ignored with the `grid` layout. Left out for none.
- layout: `rows` (the default): one row per relationship. `grid`: one row per source record with a column group per target.
- pageSize: Rows per page, 1 to 100.

### RelationTableViewDefinition

The relationships of one binding as rows, with the relationship's own attributes as columns.

- key: Names the view within its application.
- name: The name people read.
- type: `relationTable`.
- config: The view's settings.

### TreeViewConfig

- rootObjectTypeKeys: Types that start the tree, at least one; each is in `objectTypeKeys` and `rootCreatable`.
- objectTypeKeys: Every type the tree shows, at least one, in the application; each must be reachable from a root type through the types the tree shows.
- labelField: What names a node: `name` or a scalar attribute bound to every node type.
- secondaryField: A second line on a node: a built-in field or a scalar attribute bound to every node type. `null` for none.
- childSort: A sort per node type, written as for lists: the object type key to a field, `-` in front for descending. A type left out sorts by name.
- pageSize: Children per page, 1 to 100.
- actions: What a person may do in the tree: `createChild`, `rename`, `move`, `setAvailability`. An action that could never succeed on this model is refused.
- availabilityField: A boolean attribute that `setAvailability` toggles; only with that action, and bound to every node type.

### TreeViewDefinition

A containment hierarchy as a tree, from its root types down through its node types.

- key: Names the view within its application.
- name: The name people read.
- type: `tree`.
- config: The view's settings.

### BreadcrumbDefinition

- showApplication: Show the application's name. `true` by default.
- showObjectType: Show the type's name. `true` by default.
- showAncestors: Show the record's parents. `true` by default.

### DetailHeaderDefinition

- titleField: What titles the page: `name` or a field the type has. `name` by default.
- subtitleField: A second line under the title; `null` for none.
- showObjectType: Show the type's name in the header. `true` by default.

### AttributesPanelConfig

- fields: The attributes to show, in order; empty shows all the type's attributes.

### ChildrenPanelConfig

- objectTypeKeys: The child types listed; at least one, each contained by the page's type and in the application.
- columns: What a child row shows. `name` by default.
- pageSize: Children per page, 1 to 100; 20 by default.

### RelationsPanelConfig

- relationTypeKeys: The relation types listed, each declared in the model.
- direction: `outgoing`, `incoming` or `both` (the default).
- columns: What each related record shows. `name` and `objectType` by default.
- showRelationshipColumn: Show which relation type joins each row. `true` by default.
- sortFields: What the list may be sorted by, no repeats. Left out for the default order.
- defaultSort: One of `sortFields`, with `-` in front for descending.

### TablePanelConfig

- objectTypeKey: The type listed.
- columns: What a row shows. `name` by default.
- filterByParent: `true`: only records under the page's record. `false` by default.
- pageSize: Rows per page, 1 to 100; 20 by default.

### HierarchyPanelConfig

- showParent: Show the record's parent. `true` by default.
- showAncestors: Show all its ancestors. `true` by default.

### AttributesPanelDefinition, ChildrenPanelDefinition, RelationsPanelDefinition, TablePanelDefinition, HierarchyPanelDefinition

- key: Names the panel within its page; unique on the page.
- title: The panel's heading.
- type: The panel's kind, fixed by the schema: `attributes`, `children`, `relations`, `table` or `hierarchy`.
- region: `main` (the default) or `side`.
- order: Position within the region, lowest first. 0 by default.
- visible: `false` hides the panel without removing it. `true` by default.
- config: The panel's settings.

### DetailViewDefinition

- objectTypeKey: The type whose record this page shows; one page per type in an application.
- breadcrumbs: The trail above the title.
- header: The title block.
- panels: The panels of the page, at least one.

### NavigationViewEntry

- view: The `key` of a relation matrix view of the application, shown as an entry of its own.

### NavigationGroupDefinition

A labelled, collapsible sidebar section of an application's collections and relationship matrices (`{"view": key}`), in one shared order. It is presentation only and carries no data, validation or permission.

- key: Names the group within the application.
- label: The group's heading.
- collections: The entries in order: an object type key (the collection of that type) or `{"view": key}` for a relation matrix. An entry is in one group at most.
- collapsed: Whether the group starts folded. `false` by default.

### NavigationDefinition

- groups: The sidebar's sections, in order. Collections left out of every group are listed without one.
- opens: A map from a collection to the view of it that its sidebar entry opens, instead of the application's default view.

### ApplicationDefinition, ApplicationResponse

- key: Names the application in addresses; unique among applications.
- name: The name people read.
- description: What it is for; `null` if none.
- icon: A presentation hint, kept as written; `null` if none.
- color: A presentation hint, kept as written; `null` if none.
- state: `draft`, `active` (the default) or `retired`, recorded as written; the engine does not hide or refuse anything by it.
- objectTypeKeys: The object types the application holds; each must exist.
- defaultView: The `key` of the view the application opens on; one of its views.
- views: The ways to see the application's records, each of one of five types: `table`, `mappingGrid`, `relationMatrix`, `relationTable`, `tree`. Keys are unique within the application.
- details: One detail page per type, for a record's page.
- settings: Free-form settings kept as written.

### ApplicationDefinition

- navigation: The sidebar's grouping. Left out when the application has none.

### ApplicationResponse

- id: The application's ID in this release.

### ModelPlacementParent

A type of the application as a parent: the types it contains, and the types a record can become under it (a restructuring's possible types).

- objectTypeKey: The type taken as a parent.
- childObjectTypeKeys: The application's types a record of this type contains, as the add-child action offers.
- possibleObjectTypeKeys: The types a record can become under it: those contained through exactly one relation type, or `rootCreatable` ones at the top.

### ModelApplicationPlacements

- applicationKey: The application these places belong to.
- topLevelObjectTypeKeys: The types that may stand without a parent: those `rootCreatable`.
- parents: One entry for each type the application holds, taken as a parent.

### ModelPlacements

Where the model lets records stand, per application: the engine's one rule, served so clients read it instead of working it out again.

- applications: The places of every application, in the model's order.

### ConsumerMatchRule

- field: The output field or source to compare: a field the definition's object shows, an `ancestor:<type>.<field>`, or a related block's field. It must be `searchable` or `unique`.
- exact: Score when the term equals the field, ignoring case; a whole number of at least 1. Left out for none.
- contains: Score when the field contains the term; at least 1. Counts only when no exact score applied. At least one of `exact` and `contains` is set.

### AlsoMatchThrough

- related: The related block whose items are matched too.
- firstOf: Rules tried in order; the first that matches gives the item's score.
- preferTypes: Public type names that win when the related item belongs to several; left out for none.

### XrefOperation

- description: Text for the definition's OpenAPI document; left out for none.
- matchOn: The scoring rules for the object's own fields. Left out: the operation is offered and finds nothing.
- alsoMatchThrough: Related blocks whose items pass their score on to the objects they relate to.

### Operation

- description: Text for the operation in the definition's OpenAPI document; left out for none.

### Operations

- objects: Get one object by ID. Listed means offered.
- xref: Find objects by a term, with scores.
- resolve: Resolve many terms in one request; needs `objects` and `xref`.
- lists: The named lists, by key, each a list of one type.
- events: The change events the API announces.

### Within

- filter: The name of the filter whose value selects the list's parent. It must be one of the definition's filters.
- types: The parent's public types; needed unless the filter is an `under` filter, where its types are taken.

### ListSpec

- description: Text for the list in the OpenAPI document; left out for none.
- of: The public name of the type listed.
- within: What the list sits under. Left out: every object of the type.
- sortBy: A scalar attribute the type binds; records without it come last, then name. Left out: by name.

### EventWatch

What makes an object `updated` for an event: output names and related blocks.

- fields: Output names whose change makes the object `updated`, no repeats.
- related: Related blocks whose change makes the object `updated`, no repeats. At least one of the two.

### EventSpec

- key: Names the event; unique in the definition. Lower case letters, digits and single hyphens.
- objectTypes: The exposed public types the event concerns; at least one, no repeats.
- changes: Which changes are announced: `created`, `updated`, `deleted`; at least one, no repeats.
- watch: Limits `updated` to changes of the named outputs or blocks; needs `updated` in `changes`. Left out: any change to the object's output counts.

### EventsOperation

- description: Text for the operation in the OpenAPI document; left out for none.
- perType: `true`: one event `<type>-changed` for each exposed type, announcing every change. Left out: false.
- custom: The definition's own events.

### FieldSpec

- description: Text for the field in the OpenAPI document; left out for none.
- from: The source: one attribute, `ancestor:<type>.<field>` or built-in name, or a list read as the first non-empty. Sources share one value type.
- default: The value served when every source is empty, in the field's type; left out for none.
- role: The place the field has in the shared object: `id`, `code`, `name`, `active`, `validFrom` or `validTo`. One field per role; role fields come first, in that order.

### RelatedSpec

Related records under one output name, reached by a relationship type's `key` (outgoing) or `reverseKey` (incoming). `served`: in every answer (the default), or only when a read names it in `include`.

- description: Text for the block in the OpenAPI document; left out for none.
- via: The relation type's `key` (outgoing) or `reverseKey` (incoming) that leads to the related records.
- fields: Output name to a field of the related record: `id`, `name`, `objectType`, an attribute, `ancestor:<type>.<field>` or `relation:<attribute>` (a value on the relationship).
- served: `always` (the default): in every answer. `onRequest`: only when a read names the block in `include`.

### ParentSpec

The parent as a record shows it: `fields` are `objectType`, `id`, `code` and `name` or any source an object field takes, and `related` blocks are written as the object's. The parent has no parent of its own.

- output: The output name the parent has.
- fields: What the parent shows: the built-in names `objectType`, `id`, `code`, `name` as a list, or output names to sources as for the object's fields.
- related: Related blocks of the parent, one level only.

### ObjectSpec

- fields: The output fields, by output name; each is one source, a list of sources, or a field written out. At least one, and one has role `id`.
- parent: How the parent is shown: a list of fields, or written out. Left out: no parent.
- path: `true` outputs the record's ancestors as `path`; a text names the output instead. Left out: not shown.
- hierarchy: `true` outputs the ancestors as `hierarchy`; a text names the output. Left out: not shown.
- related: Related blocks by output name.

### FilterSpec

- description: Text for the filter in the OpenAPI document; left out for none.
- byType: `true`: keeps objects of the named public types.
- under: Types of an ancestor an object must have, matched with `matchOn`.
- linkedTo: Types of an object it must be linked to, through the routes in `through` and matched with `matchOn`.
- through: With `linkedTo`: related block names, `itself`, or `sharedWith:<block>`.
- onRelated: A related block the filter limits to items that match on `matchOn`.
- matchOn: Fields compared with the filter's value; the defaults are `id`, the code sources and `name`.
- keepOnlyMatching: With `onRelated`: also drops objects left with no matching item.
- scoreOnlyMatching: With `onRelated`: only matching items pass scores on.
- crosswalk: With `onRelated`: allows `to.<filter>` to translate to a target system. Only `onRelated` filters.

### ConsumerApiEarlierVersion

An earlier contract version of a consumer API that is still served: a frozen copy of the definition as it was at `contractVersion` (everything but its key and name, which the API keeps). `deprecated` is the day it was superseded (the `Deprecation` header), and `sunset` the day its administrator announces it stops (the `Sunset` header); the engine serves it until the administrator removes it, whatever the date.

- description: Text for this version; left out for none.
- contractVersion: The version this copy is frozen at, at least 1; lower than the current one.
- deprecated: The day it was superseded, `YYYY-MM-DD`; sent as the `Deprecation` header. Left out: when the release declaring it was activated.
- sunset: The day it is announced to stop, `YYYY-MM-DD`; sent as the `Sunset` header. The engine serves it until it is removed from the model.
- exposes: The public types served in this version.
- publicNames: Public names that differ from the key in PascalCase, by type key.
- object: The object's shape in this version.
- operations: The operations offered in this version.
- filters: The filters of this version, by name.

### ConsumerApiDocument

One consumer API definition.

- key: The consumer API's name in `/api/consumer/{consumerApi}` and in subscriptions. Lower case letters, digits and single hyphens; unique in the model.
- name: The name people read.
- description: What the API is for; left out for none.
- contractVersion: The current version, at least 1; raise it for any change consumers would notice.
- exposes: The object types served, at least one, by key.
- publicNames: Public type names that differ from the type key in PascalCase, by type key.
- object: What an object looks like: fields, parent, path, hierarchy and related blocks.
- operations: Which operations exist; one not listed does not.
- filters: The filters reads accept, by name. A name may not be a reserved parameter name or start with `to.`.
- earlierVersions: Earlier contract versions still served beside this one, newest first. Left out for none.

### CandidateCompatibilityResponse

What activating the candidate into the default workspace would do (`activeReleaseId` is the default workspace's release), and `workspaces`: the same for each workspace running a release of the candidate's model, in workspace key order. A new model's list is empty.

- classification: `compatible`: the stored data fits. `migration_required`: some data would not, and each diagnostic says what. `invalid`: only in the answer of `compile` for a draft that does not compile, with no diagnostics.
- activeReleaseId: The release the default workspace runs, which activation would replace.
- diagnostics: What would not fit, with the number of records or relationships each affects in `count`.

### WorkspaceCompatibilityResponse

What activating the candidate into one workspace that runs its model would do: that workspace's data against its own release.

- workspaceKey: The workspace a release of the candidate's model runs in.
- releaseId: The release that workspace runs.
- classification: `compatible` or `migration_required`, as above, for this workspace's data alone.
- diagnostics: What would not fit in this workspace.

### CandidateCompatibilityResponse

- workspaces: The same check for each active workspace running a release of the candidate's model, in key order. Empty for a model not installed before.

### ModelConsumerContractsResponse

The candidate's consumer API definitions against the active release's. `version_required` when a definition changes what its consumers read without a higher `contractVersion`: its diagnostics are errors, and activation is refused until it is raised. A removed definition is a warning and does not change the classification.

- classification: `compatible`, or `version_required`: a definition changed what its consumers read without a higher `contractVersion`, and activation is refused until it is raised.
- activeReleaseId: The release the contracts were compared with.
- diagnostics: Each breaking change as an error; a removed API is a warning.

### ModelDiagnosticResponse

- severity: `error` makes the model invalid or the change refused; `warning` does not.
- code: A stable code naming the rule that failed.
- path: A JSON pointer to the part of the document, for example `/objectTypes/<key>/behavior`.
- message: What is wrong, for a person.
- count: The records or relationships a compatibility problem affects. Left out otherwise.

### ModelValidationResponse

- valid: `true` when the document is valid.
- diagnostics: Every problem found. Empty when valid.

### ModelDocumentRequest

- model: The model document, as `GET /api/v1/model` returns it.

### ModelChangeResponse

- kind: `added`, `changed` or `removed`.
- path: A JSON pointer to what changed. Items of a list that has keys are addressed by their key.
- before: The value in the baseline; left out when added.
- after: The value in the candidate; left out when removed.

### ModelReleaseDiffResponse

- againstReleaseId: The baseline release.
- releaseId: The candidate release.
- changes: What changed from the baseline to the candidate, in path order.
- compatibility: Whether stored data fits the candidate.
- consumerContracts: Whether the consumer APIs changed without a higher version, compared with the workspace's release.

### ModelReleaseSummary, ModelReleaseResponse

- id: The release's ID. Use it in addresses and requests.
- key: Names the model; shared by every release of it.
- name: The model's name.
- version: The release's version.
- schemaVersion: The model language the release is written in.
- modelHash: Identifies the release's content; two releases never share one.
- installedAt: When the release was installed.
- assigned: `true` when some workspace runs it.
- workspaces: The keys of the workspaces running it.
- retiredAt: When it was retired; `null` while active.

### ModelReleaseResponse

- model: The complete model document. Present only with `includeModel=true`.

### ModelReleaseStatusRequest

Retires a release or brings it back.

- status: `retired` or `active`.
- expectedStatusVersion: The release's `statusVersion` as you read it.

### ModelReleaseRaisingRequest

Previews (`confirm: false`) or applies (`confirm: true`, with the hash the preview named) raising a release to the schema version this engine reads.

- confirm: `false` previews and changes nothing. `true` applies.

### ModelReleaseRaisingResponse

- releaseId: The release's ID, unchanged by raising.
- releaseKey: The release's key.
- releaseVersion: The release's version.
- schemaFrom: The schema the release is written in.
- schemaTo: The schema it is raised to; the one this engine reads.

### ModelReleaseRaisingWorkspace

- key: The workspace's key.
- label: The workspace's label.

### ModelReleaseActivationResponse

One recorded selection of a release as a workspace's model, read from the audit trail. `workspaceKey` is absent for an old selection made for the whole instance, and `runtimeVersion` is the assignment's version it gave the workspace.

- eventId: The audit event's ID.
- kind: `activated`: the release became a workspace's model. `schemaUpgraded`: the release was brought to a newer schema by the engine.
- previousReleaseId: The release it replaced.
- workspaceKey: The workspace. Left out for a selection made for the whole instance before workspaces had models of their own.
- runtimeVersion: The workspace's assignment version after the change.
- occurredAt: When it happened.
- actor: Who made it; `null` when the engine did, or it was recorded before actors were kept.

### CapabilitiesResponse

- modelAdmin: Whether models can be installed and edited.
- workspaceAdmin: Whether workspaces can be created, changed and deleted.
- integrationJobs: Whether batches, imports and exports run, and their limits.
- changeFeed: The change feed's retention.
- consumerApi: The consumer API's limits.
- consumerSubscriptions: Whether webhook subscriptions can be managed, and how they are delivered.

### ModelAdminCapabilities

- readReleases: Releases can be read. Always `true`.
- manageDrafts: Model drafts can be created and changed.
- install: A draft can be installed as a release.
- activate: A release can be activated in a workspace.
- setting: The operator setting that controls these.

### WorkspaceAdminCapabilities

- manageWorkspaces: Workspaces can be created, changed and deleted.
- setting: The operator setting that controls it.

### IntegrationJobCapabilities

Bulk writes, imports and exports as jobs. Job reads are always available.

- createJobs: Whether a batch, import or export can be started. Reading jobs is always possible.
- runModes: Where a job may run: `inline` (in the request) and `background`. Empty when jobs are off.
- limits: What a request or job may hold.
- setting: The operator setting that controls jobs.

### JobLimits

Batch and job limits and the retention of finished jobs. A refusal names the setting it enforces: `BATCH_MAX_ITEMS`, `BATCH_MAX_BYTES`, `ATOMIC_JOB_MAX_ITEMS`, `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES` or `IMPORT_MAX_BYTES`. A background job commits `chunkItems` items at a time (`JOB_CHUNK_ITEMS`); a preview, of an import or a batch, runs at most `previewMaxItems` items (`JOB_PREVIEW_MAX_ITEMS`) and is a sample beyond them.

- batchMaxItems: Most items in a batch that runs in the request; a larger one is `BATCH_TOO_LARGE`.
- batchMaxBytes: Most bytes in the body of a batch that runs in the request.
- atomicJobMaxItems: Most items in a job that must succeed or fail as a whole.
- backgroundJobMaxItems: Most items in a job that runs in the background.
- backgroundBatchMaxBytes: Most bytes in the body of a batch that runs in the background.
- chunkItems: Items a background job commits at a time.
- importMaxBytes: Most bytes in an uploaded import file.
- previewMaxItems: Most items a preview checks; beyond them it is a sample.
- retentionDays: Days a finished job and its output are kept.

### ChangeFeedCapabilities

The change feed's retention. A position older than `retentionDays` (`FEED_RETENTION_DAYS`) is refused as expired, and the refusal names a baseline to read again.

- retentionDays: Days of events the feed keeps. A position older than that is refused as expired.

### ConsumerApiCapabilities

The consumer read API's limit. A batch resolve holds at most `resolveMaxItems` items (`CONSUMER_RESOLVE_MAX_ITEMS`); more are refused as `BATCH_TOO_LARGE`.

- resolveMaxItems: Most items in one batch resolve; more are `BATCH_TOO_LARGE`.
- setting: The operator setting that controls it.

### ConsumerSubscriptionCapabilities

Webhook subscriptions: managed through `/api/v1/consumer-subscriptions` and delivered when `manageSubscriptions` is true (`CONSUMER_SUBSCRIPTIONS_ENABLED`).

- delivery: How webhooks are delivered. These are fixed by the engine, not settings.
- logRetentionDays: Days the delivery log keeps a request.
- manageSubscriptions: Whether subscriptions can be created and delivered.
- setting: The operator setting that controls subscriptions.

### WebhookDeliveryLimits

How webhooks are delivered. A subscription may batch up to `maxEventsPerBatch` events in a request, and a request holds at most `maxBytes` of body (an event alone over it is sent alone); a receiver answers within `timeoutSeconds`; a failing batch is retried with backoff (`retryWaitsSeconds`, then every `laterWaitSeconds`, each varied by up to 20 percent) for `retryHours` after its first failure, then the subscription is suspended `DELIVERY_FAILED`. These are constants, not settings.

- laterWaitSeconds: Seconds between later retries, after the waits in `retryWaitsSeconds`.
- maxBytes: Most bytes of body in one request; an event larger than that is sent alone.
- maxEventsPerBatch: Most events in one request.
- retryHours: Hours after the first failure that retries go on; then the subscription is suspended `DELIVERY_FAILED`.
- retryWaitsSeconds: Seconds waited before each of the first retries. Every wait varies by 20 percent.
- timeoutSeconds: Seconds the receiver has to answer.
