# API principles and contract

## Entity identifiers

Every entity exposed by the API carries a stable public `id`. IDs are **never** the internal database
sequence numbers.

| Entity | `id` format | Additional key | Notes |
|---|---|---|---|
| Application | UUID v4 | `key` (string slug) | Generated at model install time |
| Object type | UUID v4 | `key` (string slug) | Generated at model install time |
| Attribute type | UUID v4 | `key` (string slug) | Generated at model install time |
| Relation type | UUID v4 | `key` (string slug) | Generated at model install time |
| Object | UUID v4 | — | Generated at creation time |
| Attribute value | UUID v4 | — | Generated at creation time |
| Object relation | UUID v4 | — | Generated at creation time |

**Type entities** (application, object type, attribute type, relation type) are identified by both a
UUID `id` and a human-readable `key`. URL paths and model references use `key`; the `id` appears in
every API response body alongside `key`. The `id` is assigned when a model release is installed and
remains stable across application restarts as long as the release is active.

**Instance entities** (object, attribute value, object relation) are identified by UUID `id` only.
URL paths use `id`; there is no separate key. Attribute values are child resources: they are addressed
under their parent object by the attribute type's `key`
(`/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}`); their UUID `id` appears in every
response body. See [Attribute value endpoints](#attribute-value-endpoints).

Future custom entity types follow the same convention: every type and every instance receives a UUID
`id` in its API response.

### Response shape — type entities

Type-entity responses include both `id` and `key` at the top level:

```json
{
  "id": "a1b2c3d4-...",
  "key": "master-value",
  "name": "Master value",
  ...
}
```

### Response shape — instance entities

Instance-entity responses include `id` and reference their type by `key`:

```json
{
  "id": "e5f6a7b8-...",
  "objectTypeKey": "master-value",
  "name": "Initial train",
  ...
}
```

Relation responses include the relation's own `id`, plus the referenced object IDs and relation type
key:

```json
{
  "id": "c9d0e1f2-...",
  "relationTypeKey": "system-value-maps-to-master",
  "fromObjectId": "e5f6a7b8-...",
  "toObjectId": "f3a4b5c6-...",
  ...
}
```

## Model endpoints

- `GET /api/v1/model`
- `GET /api/v1/applications`
- `GET /api/v1/applications/{applicationKey}`
- `GET /api/v1/attribute-types`
- `GET /api/v1/attribute-types/{attributeTypeKey}`
- `GET /api/v1/object-types`
- `GET /api/v1/object-types/{objectTypeKey}`
- `GET /api/v1/relation-types`
- `GET /api/v1/relation-types/{relationTypeKey}`
- `GET /api/v1/object-type-relations`

URL paths use stable model keys. Every response body includes the entity `id` (UUID) alongside the
`key`. Internal metadata sequence IDs are never part of the contract.

Relation types and object-type relations are separate resources. A **relation type** defines reusable
forward/reverse semantics and orientation. An **object-type relation** binds one relation type to an
allowed source and target object type and supplies cardinality, required status, attributes and
binding features. Relation-type responses include these bindings under `allowedPairs`; the flat
`object-type-relations` endpoint remains available for discovery and compatibility and can be
filtered with `fromObjectType` and `toObjectType` query parameters.

### Base 0.5 model-lifecycle contract

The following contract is locked for Base 0.5 implementation. WP1 implements the active-model headers
and installed-release catalogue/detail endpoints. WP2 implements inline validation and installed
release diff with runtime compatibility; WP3 implements capabilities, drafts and installation, and
WP4 implements guarded activation. All IDs are UUID v4 strings, timestamps are UTC ISO
8601 values and model hashes are lowercase SHA-256 hex strings. JSON field names use the camelCase
forms shown here.

#### Capabilities and active model

- `GET /api/v1/capabilities`
- `GET /api/v1/model`

Capabilities return deployment-supported operations explicitly:

```json
{
  "modelAdmin": {
    "readReleases": true,
    "manageDrafts": false,
    "install": false,
    "activate": false
  }
}
```

`readReleases` remains true when mutations are disabled. `manageDrafts` and `install` are true only
when `MODEL_ADMIN_MUTATIONS_ENABLED=true`; `activate` follows the same gate. The flag is a deployment
guard, not an authorization mechanism. Mutation enablement requires a single process; startup rejects
`WEB_CONCURRENCY` values greater than one until cross-process release propagation exists.

`GET /api/v1/model` continues to return the active `EngineModel` body and adds:

- `ETag: "<modelHash>"`; and
- `X-Model-Release-Id: <releaseId>`.

Both headers and the body come from the same request-scoped installed release snapshot.

#### Installed releases

- `GET /api/v1/model-releases?releaseKey=...&active=...&pageSize=...&cursor=...`
- `GET /api/v1/model-releases/{releaseId}?includeModel=false`
- `GET /api/v1/model-releases/{releaseId}/diff?againstReleaseId=...`
- `GET /api/v1/model-runtime-state`
- `POST /api/v1/model-releases/{releaseId}/activation`

The collection returns the standard `{items, nextCursor}` page. A release summary and detail share
this identity shape; `model` is included only on detail when `includeModel=true`:

```json
{
  "id": "6f57924d-...",
  "key": "rdm-starter",
  "name": "RDM starter model",
  "version": "0.5.0",
  "schemaVersion": "0.4",
  "modelHash": "7c9d...",
  "installedAt": "2026-09-04T12:00:00Z",
  "active": false,
  "model": {}
}
```

`model` is absent, rather than `null`, unless requested. Release list and detail are always readable;
release installation and activation are mutation-gated.

Metadata and release cursors are signed opaque tokens bound to their endpoint, ordering and effective
filters. Changing a cursor or reusing it with different filters returns `422 invalid_cursor`.

Diff uses the requested installed release as its structural baseline and the path notation used by
diagnostics:

```json
{
  "againstReleaseId": "412c4041-...",
  "releaseId": "6f57924d-...",
  "changes": [
    {
      "kind": "changed",
      "path": "/objectTypes/master-value/name",
      "before": "Master value",
      "after": "Canonical value"
    }
  ],
  "compatibility": {
    "classification": "compatible",
    "activeReleaseId": "412c4041-...",
    "diagnostics": []
  }
}
```

`kind` is `added`, `changed` or `removed`. `before` is absent for additions and `after` is absent for
removals. A present `before` or `after` may contain JSON `null`; omission and a real null value are
distinct. Set-like key memberships such as application object types and allowed relation attributes
are compared by stable key rather than array position. Compatibility always assesses activation
against current runtime data and identifies the active release used for that assessment; it is
independent of a non-active structural diff baseline.

Activation accepts both concurrency tokens:

```json
{
  "expectedRuntimeVersion": 3,
  "expectedActiveReleaseId": "412c4041-..."
}
```

Clients obtain those tokens from `GET /api/v1/model-runtime-state`, which returns the same runtime
state shape without mutating it. The workbench refreshes this state immediately before activation.

It returns the complete new runtime state:

```json
{
  "activeReleaseId": "6f57924d-...",
  "activeModelHash": "7c9d...",
  "version": 4,
  "updatedAt": "2026-09-04T12:05:00Z"
}
```

Activation reparses the installed active and candidate models and checks current stored data in the
same transaction as its conditional runtime-state update. It commits that selection before refreshing
the process registry. A post-commit registry refresh failure returns `503
model_registry_refresh_failed`; `/health` then reports `503` and model-dependent requests are refused
rather than using a guessed snapshot (`503 model_registry_unavailable`). Restarting successfully
reloads the database-selected release. If an installed release fails reparsing, activation returns
`500 invalid_installed_model` and leaves runtime state unchanged.

#### Drafts, validation, compilation and installation

- `GET /api/v1/model-drafts?pageSize=...&cursor=...`
- `GET /api/v1/model-drafts/{draftId}`
- `POST /api/v1/model-drafts`
- `PATCH /api/v1/model-drafts/{draftId}`
- `DELETE /api/v1/model-drafts/{draftId}?expectedVersion=...`
- `POST /api/v1/model-validations`
- `POST /api/v1/model-drafts/{draftId}/compile`
- `POST /api/v1/model-drafts/{draftId}/installation`

Create accepts `name`, optional `baseReleaseId` and an inline `model`. Patch accepts
`expectedVersion` plus at least one of `name` or `model`. Draft responses use:

```json
{
  "id": "899e8f66-...",
  "name": "Add canonical value label",
  "baseReleaseId": "412c4041-...",
  "model": {},
  "version": 2,
  "createdAt": "2026-09-04T11:00:00Z",
  "updatedAt": "2026-09-04T11:15:00Z"
}
```

Delete succeeds with HTTP `204` and no body. Inline validation accepts `{ "model": {} }` and returns:

```json
{
  "valid": false,
  "diagnostics": [
    {
      "severity": "error",
      "code": "unknown_object_type",
      "path": "/applications/rdm-master/objectTypeKeys/3",
      "message": "Object type 'missing' does not exist"
    }
  ]
}
```

Diagnostic severity is `error` or `warning`; `path` is a JSON Pointer. Compatibility diagnostics
additionally include a positive `count` of the violating stored rows or groups. Validation diagnostics
omit `count`.

Compile and installation both accept `{ "expectedVersion": 2 }`. Compile is side-effect-free and
returns:

```json
{
  "valid": true,
  "model": {},
  "modelHash": "7c9d...",
  "diagnostics": [],
  "againstReleaseId": "412c4041-...",
  "changes": [
    {
      "kind": "changed",
      "path": "/product/name",
      "before": "RDM Engine",
      "after": "Reference Data Engine"
    }
  ],
  "compatibility": {
    "classification": "compatible",
    "activeReleaseId": "412c4041-...",
    "diagnostics": []
  }
}
```

`model` is the parsed canonical model. `againstReleaseId` identifies the draft's installed base
release, falling back to the active release when the draft has no available base; `changes` is the
key-based semantic diff used for pre-install review and preserves the distinction between omission and
an explicit JSON `null`. Compatibility classification is `compatible`,
`migration_required` or `invalid`; invalid compilation returns `valid: false`, omits `model` and
`modelHash`, and uses `invalid`. Installation repeats compilation and compatibility analysis and
returns the installed release detail with `model` absent. A newly installed release returns HTTP
`201`; an idempotent retry for identical content returns HTTP `200`. Installation never activates the
release. Installations are serialized inside the supported single API process so concurrent drafts
with identical content resolve to the same immutable release rather than racing the uniqueness
constraints.

Every draft endpoint and the installation and activation endpoints return HTTP `404` when model
administration mutations are disabled. Validation, capabilities, installed-release reads and diff
are not mutation-gated. Lifecycle conflicts use:

- `409 version_conflict` for a stale draft version;
- `409 release_identity_conflict` for the same release key/version with different content;
- `422 invalid_model` when installation recompilation fails;
- `409 activation_conflict` for stale runtime-state tokens; and
- `409 model_migration_required` when stored data prevents activation.

As elsewhere, errors use the shared `{ "error": { "code", "message", "details" } }` envelope.

### Base 0.5 OpenAPI lock

The complete canonical default OpenAPI document digest through WP7, plus readable path/method and
component-schema inventories, are asserted by `backend/tests/test_openapi_contract.py`. A separate
enabled-mode inventory asserts the mutation-gated draft surface. Any public shape change therefore
requires an intentional contract-test update. Later Base 0.5 packages update the lock in the same
change that implements each planned contract.

All metadata collection endpoints accept an opaque `cursor` and a `pageSize` from 1 to 500 (default
100). They return:

```json
{
  "items": [],
  "nextCursor": null
}
```

Pass a non-null `nextCursor` unchanged to retrieve the next page. Metadata cursors are derived from
stable model keys, never database sequence IDs.

### Applications response

`GET /api/v1/applications` returns a cursor page of applications under `items`.
`GET /api/v1/applications/{applicationKey}` returns a single application. Each item uses this shape:

```json
{
  "id": "dfe8e61a-...",
  "key": "rdm-master",
  "name": "RDM Master",
  "description": "Canonical reference data organized into domains and codelists",
  "icon": "database",
  "color": "#6657d9",
  "state": "active",
  "objectTypeKeys": ["domain", "codelist", "master-value"],
  "defaultView": "domains",
  "views": [
    {
      "key": "domains",
      "name": "Domains",
      "type": "table",
      "objectTypeKey": "domain",
      "objectTypeId": "638513ce-...",
      "config": { "columns": ["name", "domain-code", "description", "active"] }
    }
  ],
  "details": [
    {
      "objectTypeKey": "domain",
      "objectTypeId": "638513ce-...",
      "panels": [
        {
          "key": "codelists",
          "type": "children",
          "config": {
            "objectTypeKeys": ["codelist"]
          }
        }
      ]
    }
  ],
  "settings": {}
}
```

Every singular `objectTypeKey` has a matching `objectTypeId` at all nesting levels — views, details
and panel configs. Plural `objectTypeKeys` arrays do not carry parallel IDs. All IDs are resolved
from the same model release in a single lookup.

### Attribute-types response

`GET /api/v1/attribute-types` returns a cursor page of attribute types under `items`.
`GET /api/v1/attribute-types/{attributeTypeKey}` returns a single attribute type. Each item uses this
shape:

```json
{
  "id": "52c4a9c3-...",
  "key": "active",
  "name": "Active",
  "description": null,
  "valueType": "boolean",
  "default": true,
  "features": { "filterable": true },
  "validation": {},
  "ui": {}
}
```

### Object-types response

`GET /api/v1/object-types` returns a cursor page of object types under `items`.
`GET /api/v1/object-types/{objectTypeKey}` returns a single object type. Each item contains the object
type's `id`, its `key`, metadata and its attribute bindings with resolved names and value types:

```json
{
  "id": "aee2626d-...",
  "key": "master-value",
  "name": "Master value",
  "pluralName": "Master values",
  "description": "Canonical reference value independent of source systems",
  "icon": "circle-dot",
  "displayAttributeTypeKey": "value-name",
  "attributes": [
    {
      "id": "2a6ad50c-...",
      "attributeTypeKey": "master-id",
      "name": "Master ID",
      "valueType": "text",
      "required": true,
      "readOnly": false,
      "order": 10
    }
  ],
  "features": { "rootCreatable": false },
  "behavior": {
    "parentRelationTypeKeys": [
      "codelist-contains-value",
      "master-value-has-child"
    ]
  },
  "validation": {}
}
```

Each attribute binding carries its own `id` (the binding's UUID, not the global attribute type's),
the resolved `name` and `valueType` from the attribute type definition, and the binding-specific
`required`, `readOnly` and `order` fields.

### Relation-types response

`GET /api/v1/relation-types` returns a cursor page of relation types under `items`.
`GET /api/v1/relation-types/{relationTypeKey}` returns a single relation type. Each item contains the
relation type's `id`, forward and reverse keys and names, and the allowed object-type pairs nested
under `allowedPairs`:

```json
{
  "id": "3bfbca7d-...",
  "key": "domain-contains-codelist",
  "name": "Contains codelist",
  "reverseKey": "codelist-belongs-to-domain",
  "reverseName": "Belongs to domain",
  "isOriented": true,
  "features": { "parentOf": true, "creatableOnChildAdd": true },
  "allowedPairs": [
    {
      "id": "b59e61b5-...",
      "fromObjectTypeKey": "domain",
      "toObjectTypeKey": "codelist",
      "cardinality": "one-to-many",
      "required": false,
      "attributeTypeKeys": [],
      "features": {}
    }
  ]
}
```

Each allowed pair carries its own `id` (the binding's UUID). A single relation type may permit
multiple object-type pairs — for example a reusable "contains" relation allowed between several
parent/child combinations. The relation type's own `id` identifies the type itself; each pair's
`id` identifies the specific binding.

## Object endpoints

- `GET /api/v1/objects/{objectTypeKey}` — list objects of a type
- `POST /api/v1/objects` — create an object
- `GET /api/v1/objects/{objectTypeKey}/{objectId}` — get one object
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}` — update an object
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}` — delete an object

Collections accept `cursor`, `pageSize`, `applicationKey`, `workspaceKey`, `parentObjectId`, repeatable
`state`, `search` and `sort`. Supported sorts are `name`, `state`, `createdAt` and `updatedAt`; prefix a
sort with `-` for descending order. Omitting `sort` preserves creation sequence order. Every ordering
uses the internal sequence as a non-public final tie-breaker. Page size defaults to 100 and has a
documented maximum of 500. `nextCursor` is null only when that traversal is complete.

Object cursors are signed opaque tokens bound to the object type, selected sort and every effective
filter, including workspace and the normalized set of repeated states. A malformed token, a changed
sort or filter, or reuse for another collection returns `422 invalid_cursor`. Predicates use keyset
positions rather than offsets, so duplicate names and timestamps remain deterministic and inserts do
not cause already traversed rows to repeat.

`DELETE` requires `expectedVersion` and accepts optional `cascade` (default `false`). Without cascade,
an object that has no children or non-parent relations is deleted normally. If dependencies exist, the
request performs no deletion and returns `409 object_has_dependents` with a structured impact report:

```json
{
  "error": {
    "code": "object_has_dependents",
    "message": "Deleting this object requires cascade confirmation",
    "details": {
      "rootObject": { "id": "...", "name": "Connections", "objectTypeKey": "domain" },
      "objectsToDelete": [
        { "id": "...", "name": "Timetables", "objectTypeKey": "codelist", "reason": "child", "viaObjectId": "..." }
      ],
      "relationshipsToRemove": [
        {
          "id": "...",
          "relationTypeKey": "maps-to",
          "fromObject": { "id": "...", "name": "Source value", "objectTypeKey": "source-value" },
          "toObject": { "id": "...", "name": "Target value", "objectTypeKey": "target-value" },
          "fkPk": false,
          "relatedObjectWillBeDeleted": false
        }
      ],
      "objectCount": 2,
      "relationshipCount": 2
    }
  }
}
```

Retrying with `cascade=true` recursively deletes all containment descendants and their attributes, and
removes every relationship incident to the deletion set. Optional and many-to-many non-parent links
are unlinked without deleting the other endpoint. A directed, required `one-to-one` or `one-to-many`
binding has PK→FK ownership semantics; cascading from its `from` owner also deletes its `to` dependent,
including that dependent's own containment descendants. The complete operation and its audit events
commit atomically. A stale root `expectedVersion` returns HTTP 409.

### Create request

`POST /api/v1/objects` accepts a JSON body. Extra fields are rejected.

| Field | Required | Description |
|---|---|---|
| `id` | No | UUID v4. When provided, the object is created with this ID; rejected if already exists. When omitted, a new UUID is generated. |
| `applicationKey` | Yes | Application the object belongs to. |
| `objectTypeKey` | Yes | Type of the object to create. |
| `name` | Yes | Display name (1–500 characters). |
| `workspaceKey` | No | Defaults to `"default"`. |
| `parentObjectId` | No | Parent object UUID. Required for non-root-creatable types. |
| `state` | No | Defaults to `"active"`. |
| `attributes` | No | Array of attribute values (see below). |
| `initialRelations` | Conditionally | Required non-parent relationships created atomically with the object. |

```json
{
  "id": "c5588b49-...",
  "applicationKey": "rdm-master",
  "objectTypeKey": "domain",
  "name": "Connections",
  "parentObjectId": null,
  "attributes": [
    { "attributeTypeKey": "domain-code", "value": "CONNECTIONS" },
    { "attributeTypeKey": "description", "value": "Connections domain" }
  ]
}
```

Each `initialRelations` item contains `relationTypeKey`, `direction` relative to the new object,
`otherObjectId`, and optional relation `attributes`. If a model binding is required at the new object's
target side, creation returns `422 missing_required_relations` unless a matching incoming relation is
provided. Object, attributes, containment, initial relationships and audit events commit in one
transaction. For example, a Translation is created with its target as follows:

```json
{
  "applicationKey": "rdm-translations",
  "objectTypeKey": "translation",
  "parentObjectId": "translation-group-uuid",
  "name": "Czech timetable type",
  "attributes": [
    { "attributeTypeKey": "translated-value", "value": "Spoj" }
  ],
  "initialRelations": [
    {
      "relationTypeKey": "object-has-translation",
      "direction": "incoming",
      "otherObjectId": "translated-object-uuid"
    }
  ]
}
```

### Attribute format

Attributes are arrays of objects in both requests and responses:

**Request** (create and update) — each item has `attributeTypeKey` and `value`:

```json
[
  { "attributeTypeKey": "domain-code", "value": "CONNECTIONS" },
  { "attributeTypeKey": "active", "value": true }
]
```

**Response** — each item adds its attribute-value `id`, plus `name` and `valueType` resolved from the
model:

```json
[
  { "id": "51d92c5e-...", "attributeTypeKey": "domain-code", "name": "Domain code", "valueType": "text", "value": "CONNECTIONS" },
  { "id": "ca5121a7-...", "attributeTypeKey": "active", "name": "Active", "valueType": "boolean", "value": true }
]
```

### Attribute uniqueness

An attribute type may declare `"features": { "unique": true }`. Values for such an attribute are
enforced unique per workspace across all objects that carry that attribute type. Create and update
return `409 duplicate_attribute_value` when a value collides. Uniqueness is supported for the scalar
value types (`text`, `longText`, `integer`, `decimal`, `boolean`, `date`, `dateTime`); declaring it on
a `json` type is rejected at model load. Enforcement is service-level (see `docs/DECISIONS.md`); a
database-level constraint is planned.

### Update request

`PATCH /api/v1/objects/{objectTypeKey}/{objectId}` accepts a partial update. Only provided fields
are changed. `expectedVersion` is always required and is claimed atomically; stale or concurrent
writes return HTTP 409.

```json
{
  "name": "Renamed domain",
  "attributes": [
    { "attributeTypeKey": "description", "value": "Updated description" }
  ],
  "expectedVersion": 1
}
```

### Attribute value endpoints

Attribute values are child resources of an object, addressable one at a time. An object can carry at
most one stored value per attached attribute type, so the URL leaf is the attribute type's `key`:

- `GET /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — read one stored value
- `POST /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — set a value that is not yet stored
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — update a stored value
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}?expectedVersion={n}` — remove a stored value

`GET` returns a single attribute response item plus `objectVersion`, the current concurrency token for
the containing object. `POST` and `PATCH` return the full object response. All three mutating endpoints
require `expectedVersion` — the object's current `version` — and atomically claim the next version, so
concurrent requests cannot both write from the same version. Returning the token from `GET` and the
full object from successful mutations gives callers the version required for the next write.

```json
{
  "id": "51d92c5e-...",
  "attributeTypeKey": "description",
  "name": "Description",
  "valueType": "longText",
  "value": "Connections domain",
  "objectVersion": 1
}
```

`POST` and `PATCH` share a request body:

```json
{
  "value": "Connections domain",
  "expectedVersion": 1
}
```

- `POST` creates only when no value is stored for the key (`409 attribute_already_exists` otherwise).
- `PATCH` updates only a stored value (`404 attribute_not_found` when the key has no value yet).
- `DELETE` removes a stored value and returns 204. Required attributes cannot be deleted
  (`422 cannot_delete_required_attribute`); read-only attributes are rejected with
  `422 read_only_attributes`. Deleting an optional value reverts that attribute to "not stored".

Value validation, type normalization and per-workspace uniqueness behave exactly as in the object
create/update flows — `unknown_attributes`, `invalid_attribute_value`, numeric bounds and
`duplicate_attribute_value` all apply. Object-level `atLeastOneOf` rules are also checked against the
complete resulting attribute set. Stale `expectedVersion` values return `409 version_conflict`.

### Error responses

All API errors, including request validation and unmatched routes, return a unified JSON envelope
with a machine-readable `code` and a human-readable `message`. Validation errors additionally include
a `details` array.

```json
{
  "error": {
    "code": "object_already_exists",
    "message": "An object with ID 'c5588b49-...' already exists"
  }
}
```

## Relation endpoints

- `POST /api/v1/relations`
- `GET /api/v1/relations?objectId={id}&direction={outgoing|incoming|both}&relationTypeKey={key}`
- `GET /api/v1/relations/{relationId}`
- `PATCH /api/v1/relations/{relationId}`
- `DELETE /api/v1/relations/{relationId}?expectedVersion={n}`

`GET /api/v1/relations` accepts its existing `objectId`, `direction` and `relationTypeKey` filters plus
bounded `pageSize` (1–500, default 100) and opaque `cursor`. It returns
`{"items": [...], "nextCursor": null}` rather than an unbounded array. The cursor is signed and bound
to the anchor object, direction, relation type and anchor workspace; malformed or mismatched cursors
return `422 invalid_cursor`. Both relation endpoint objects are joined in the anchor object's
workspace before projection, preventing a corrupt or legacy cross-workspace edge from being exposed.

This page shape is an intentional pre-1.0 breaking change. Callers must follow `nextCursor` unchanged
and must not parse it.

Relation creation validates the relation type, source and target object types, workspace, cardinality,
configured ancestor-scoped uniqueness and relation attributes. Relation attribute keys must appear in
the matched allowed pair's `attributeTypeKeys`; values are normalized and validated using the referenced
global attribute-type definitions. Undeclared keys return `422 unknown_relation_attributes`, and type or
numeric-bound failures use the same errors as object attributes.
`fromObjectId` and `toObjectId` must be UUID v4. Parent relations are normally created through object
parent operations rather than directly.

Each relation response carries a stable public `id`, the relation type, source and target object ids,
the relation `attributes` and an optimistic-concurrency `version`. `GET /api/v1/relations/{relationId}`
reads one relation; an unknown id returns `404 relation_not_found`.

`PATCH /api/v1/relations/{relationId}` accepts `{"attributes": {...}, "expectedVersion": n}`. The
relation identity (`relationTypeKey`, `fromObjectId`, `toObjectId`) is immutable; only `attributes`
can be replaced. Replacement attributes are validated against the original allowed pair in the same
transaction as the version claim. `DELETE` returns 204 and removes the relation row. Both mutations
take `expectedVersion` and atomically claim the version, returning `409 version_conflict` when the
claim is stale.

Engine-maintained parent-containment and hierarchy relations — those named in the target object type's
`behavior.parentRelationTypeKeys` and written atomically on parent changes — are read-only through this
API. Creating, updating or deleting them directly returns `422 immutable_relation`; changing them is
done through object parent operations.

A required non-parent relation returns `422 required_relation` when independently deleted. It is part
of the dependent object's validity and lifecycle; delete or replace the dependent object through the
owning workflow instead.

## Object audit history

- `GET /api/v1/objects/{objectTypeKey}/{objectId}/history?cursor=...&pageSize=...`

History is ordered newest first by occurrence time and an internal non-public sequence tie-breaker.
It returns the standard bounded page and includes events recorded directly for the object plus events
for relations connected to it. The indexed `audit_event_subjects` projection supplies identity; the
read path never searches JSON audit payloads.

Each history item contains `id`, `aggregateType`, public `aggregateId`, `action`, `version`,
`changedFields`, `attributeTypeKeys` and `occurredAt`. `attributeTypeKeys` names affected object or
relation attributes without returning their values. The response deliberately omits the internal
sequence ID and complete before/after values. History cursors are signed and bound to the object
identity, type and workspace; mismatches return `422 invalid_cursor`.

## Planned integration endpoints

- Model-aware query with explicit `select` and `expand`
- Bounded bulk create/update/upsert with per-item results
- Asynchronous import/export jobs
- Ordered change feed and webhook subscriptions

There will be no equivalent of enumerating numeric attribute IDs `1..1000` or using `take: 0` for a full
extract.
