# API principles and contract

## Entity identifiers

Model metadata and runtime graph entities exposed by the API carry a stable public `id`. IDs are
**never** internal database sequence numbers. A workspace is the deliberate exception: its immutable,
case-sensitive `key` is its public identity and its administration responses do not invent a second ID.

| Entity | `id` format | Additional key | Notes |
|---|---|---|---|
| Application | UUID v4 | `key` (string slug) | Generated at model install time |
| Object type | UUID v4 | `key` (string slug) | Generated at model install time |
| Attribute type | UUID v4 | `key` (string slug) | Generated at model install time |
| Relation type | UUID v4 | `key` (string slug) | Generated at model install time |
| Object | UUID v4 | — | Generated at creation time |
| Attribute value | UUID v4 | — | Generated at creation time |
| Object relation | UUID v4 | — | Generated at creation time |
| Workspace | Stable key | `key` | Runtime-owned global catalogue record |

**Type entities** (application, object type, attribute type, relation type) are identified by both a
UUID `id` and a human-readable `key`. URL paths and model references use `key`; the `id` appears in
every API response body alongside `key`. The `id` is assigned when a model release is installed and
remains stable across application restarts as long as the release is active.

**Instance entities** (object, attribute value, object relation) are identified by UUID `id` only.
URL paths use `id`; there is no separate key. Attribute values are child resources: they are addressed
under their parent object by the attribute type's `key`
(`/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}`); their UUID `id` appears in every
response body. See [Attribute value endpoints](#attribute-value-endpoints).

Future model types and graph instances follow the same UUID convention. Runtime administration
resources may instead define an explicit stable-key identity, as the workspace catalogue does.

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

## Collection paging

Every collection endpoint pages in one of two modes (Base 0.8 S3,
[ADR-030](DECISIONS.md#adr-030--cursor-and-position-paging-with-continuous-scrolling)). A request
selects its page with **at most one** of these parameters; none reads the first page.

| Parameter | Reads |
| --- | --- |
| `cursor` | The page after (`nextCursor`) or before (`prevCursor`) a row, or the page an `anchor` reopens |
| `from=end` | The last page (`from=start`, the default, is the first page) |
| `position=N` | The page starting at zero-based row `N` of the filtered, sorted list |
| `seek=<value>` | The page starting at the first row whose sort value is at or after the value (at or before it for a descending sort); objects, relations and mapping coverage only |

`pageSize` keeps its per-endpoint default and maximum. `includeTotal=true` adds counts, taken under
the same filters. Combining two selectors returns `422 conflicting_page_parameters` with the
parameters in `details.parameters`; a negative `position` is `422 request_validation_error`.

Every page returns its items in list order, followed by the navigation fields:

```json
{
  "items": [],
  "nextCursor": null,
  "prevCursor": null,
  "anchor": null
}
```

With `includeTotal=true` the page adds `"totalCount"` and `"startIndex"` after `anchor`.

- `nextCursor` continues after the last row and `prevCursor` before the first; each is `null` only
  at that end of the list. A backward read returns rows in list order, so walking back from the end
  can yield a short first page.
- `anchor` reopens this page from its first row: keep it (for example in a URL) instead of a trail of
  cursors. It is `null` for an empty page.
- `totalCount` and `startIndex` (the number of matching rows before the first row) are present only
  with `includeTotal=true`; otherwise they are omitted and cost nothing. They are never `null`.
- A position at or past the end returns no items, `startIndex` equal to `totalCount`, and a
  `prevCursor` to the last page.

**Consistency.** Cursor reads never repeat or skip a row when data changes between requests: a
cursor names a row by its sort values, so inserts and deletes elsewhere do not move it. Position
reads address rows by number, so a concurrent insert or delete before row `N` moves the landing
point, and consecutive position reads can repeat or miss a row at a page boundary. Read a whole list
with cursors; use positions for jumps (a scrollbar or a page number). A position read costs a scan
over the skipped rows; `seek` is the fast jump in a very large list.

Cursors stay signed, opaque and bound to their endpoint, ordering, filters and context; reusing one
with another sort, filter or context returns `422 invalid_cursor`. Cursors issued before 0.8 continue
forward as before, except those of a changed default order (S4R4): object lists without `sort` and
mapping coverage and candidates now list by name, so their earlier cursors are refused with
`422 invalid_cursor`; reload the list from its first page.

`seek` takes the lexical form of the sorted field (ISO 8601 for dates, `true`/`false` for booleans)
and applies to the sort in effect, which is the name when a list is not sorted; rows without a
value, which sort last, follow the seeked rows. A seek value that does not parse returns
`422 invalid_seek`.

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
WP4 implements guarded activation. All IDs are UUID v4 strings, timestamps are ISO 8601 UTC
values with an explicit offset (`2026-09-25T08:15:00Z`) on every database, and model hashes are lowercase SHA-256 hex strings. JSON field names use the camelCase
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
    "activate": false,
    "setting": "MODEL_ADMIN_MUTATIONS_ENABLED"
  },
  "workspaceAdmin": {
    "manageWorkspaces": true,
    "setting": "WORKSPACE_ADMIN_MUTATIONS_ENABLED"
  }
}
```

Each group names in `setting` the deployment setting that enables its mutations, so a client can tell
an operator what to change without knowing the server's configuration names.

`readReleases` remains true when mutations are disabled. `manageDrafts` and `install` are true only
when `MODEL_ADMIN_MUTATIONS_ENABLED=true`; `activate` follows the same gate. The flag is a deployment
guard, not an authorization mechanism. Mutation enablement requires a single process; startup rejects
`WEB_CONCURRENCY` values greater than one until cross-process release propagation exists.
`workspaceAdmin.manageWorkspaces` follows `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, which defaults to true
until authentication exists. It is a deployment capability and not evidence of caller authorization.

`GET /api/v1/model` continues to return the active `EngineModel` body and adds:

- `ETag: "<modelHash>"`; and
- `X-Model-Release-Id: <releaseId>`.

Both headers and the body come from the same request-scoped installed release snapshot.

#### Installed releases

- `GET /api/v1/model-releases?releaseKey=...&active=...&pageSize=...&cursor=...`
- `GET /api/v1/model-releases/{releaseId}?includeModel=false`
- `GET /api/v1/model-releases/{releaseId}/diff?againstReleaseId=...`
- `GET /api/v1/model-releases/{releaseId}/activations?pageSize=...&cursor=...`
- `GET /api/v1/model-runtime-state`
- `POST /api/v1/model-releases/{releaseId}/activation`

The collection returns the standard [page](#collection-paging). A release summary and detail share
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

Release activations read the recorded selections of one release as the active model, oldest first,
from the existing audit trail. Each item names the release it replaced, so the first item identifies
the predecessor the release was introduced over. It is an always-readable, cursor-paged standard
[page](#collection-paging) (default `pageSize` 100, maximum 500); an unknown release returns `404
model_release_not_found`:

```json
{
  "items": [
    {
      "eventId": "0b1c...",
      "kind": "activated",
      "previousReleaseId": "6f57924d-...",
      "runtimeVersion": 2,
      "occurredAt": "2026-09-14T12:00:00Z"
    }
  ],
  "nextCursor": null
}
```

`kind` is `activated` for a guarded API activation and `schemaUpgraded` for the offline schema-upgrade
selection. The initial bootstrap selection is not an audited activation, so a release first selected
by bootstrap has no item for it; clients must not infer activation history from installation order.

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
independent of a non-active structural diff baseline. If either the candidate or baseline release uses
an unsupported schema, diff returns `422 unsupported_schema_version` with details identifying the
affected release. Missing releases return `404 model_release_not_found`.

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
reloads the database-selected release. Historical releases using an unsupported schema return `422
unsupported_schema_version`; if a supported installed release fails reparsing, activation returns
`500 invalid_installed_model`. Both failures leave runtime state unchanged.

Activation and live writes exclude each other (Base 0.8 W5). Activation reserves the database writer
(`BEGIN IMMEDIATE` on SQLite) before its compatibility check, so the check sees every live write that
committed before the switch. A request that resolved the active release — a live object, attribute,
relation or mapping write, a deletion, a publish or a change-set creation — rereads the active release
inside its own transaction before committing. If another release was activated after the request
resolved its model, nothing is saved and it returns `409 model_release_changed` with
`details.resolvedReleaseId` and `details.activeReleaseId`; the client reloads the model and retries.
If live writes keep the database busy past the connection's busy timeout, activation returns
`409 model_activation_retry` and the selection is unchanged.

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

The draft collection uses the standard bounded page, ordered by `updatedAt` descending with public ID
as its deterministic tie-breaker. Its signed cursor is bound to the draft endpoint and must be passed
back unchanged; malformed or cross-endpoint reuse returns `422 invalid_cursor`.

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
are not mutation-gated. Lifecycle errors use:

- `404 model_draft_not_found` for an unknown draft ID;
- `404 model_release_not_found` for an unknown draft base, release, activation candidate or diff
  participant;
- `409 version_conflict` for a stale draft version;
- `409 release_identity_conflict` for the same release key/version with different content;
- `422 invalid_model` when installation recompilation fails;
- `422 unsupported_schema_version` when diff, compilation or activation involves a release whose schema
  is not supported by the runtime (details include `releaseId`, `schemaVersion`,
  `supportedSchemaVersions` and `operation`; the schema value comes from the stored model document
  when compilation detects a metadata/document mismatch);
- `409 activation_conflict` for stale runtime-state tokens;
- `409 model_activation_retry` when live writes held the database for longer than the busy timeout;
  the selection is unchanged and the activation may be retried;
- `409 model_migration_required` when stored data prevents activation;
- `500 invalid_installed_model` when persisted release JSON with a supported schema cannot be reparsed
  for diff or activation (distinguished from unsupported schema, which returns 422);
- `503 model_runtime_state_unavailable` when no authoritative active selection can be read;
- `503 model_registry_refresh_failed` when activation committed but the process could not publish the
  new selection; and
- `503 model_registry_unavailable` while a process has marked its request registry unhealthy.

As elsewhere, errors use the shared `{ "error": { "code", "message", "details" } }` envelope.

### OpenAPI lock

The complete canonical default OpenAPI document digest for the current implementation, plus readable
path/method and component-schema inventories, are asserted by
`backend/tests/test_openapi_contract.py`. Separate enabled-mode inventories assert the optional model
and workspace administration surfaces. Any public shape change therefore requires an intentional
contract-test update.

Every operation also documents the shared `ApiErrorResponse` envelope as its default error response.
The generated contract includes representative `invalid_cursor`, `version_conflict` and
`request_validation_error` examples; concrete status codes and endpoint-specific codes remain as
documented in the sections above.

All metadata collection endpoints accept a `pageSize` from 1 to 500 (default 100) and the
[collection paging](#collection-paging) parameters except `seek`, and return the standard page
(`items`, `nextCursor`, `prevCursor`, `anchor`, and with `includeTotal=true` `totalCount` and
`startIndex`). Pass cursors back unchanged. Metadata cursors are derived from stable model keys, never database sequence IDs.

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

## Workspace endpoints

- `GET /api/v1/workspaces?search=...&status=active|retired|all&pageSize=...&cursor=...`
- `GET /api/v1/workspaces/{workspaceKey}`
- `POST /api/v1/workspaces`
- `PATCH /api/v1/workspaces/{workspaceKey}`
- `DELETE /api/v1/workspaces/{workspaceKey}?expectedVersion=N`
- `GET /api/v1/workspace-runtime-state`
- `PATCH /api/v1/workspace-runtime-state`

Workspace keys are immutable and case-sensitive. Discovery defaults to active records and uses a
filter-bound keyset cursor; detail reads include retired records. Updates claim the workspace version,
and changing the default claims the independent singleton runtime-state version. The current default
cannot be retired. A workspace is renamed by changing its `label`; there is no way to change a key.
Unknown explicit scopes return
`workspace_not_found`; retired scopes remain readable but all object, attribute and relation writes
return `workspace_retired`.

**Deleting a workspace** ([ADR-019 amendment](DECISIONS.md#adr-019--persist-and-retire-globally-scoped-workspaces))
corrects a mistyped key. `DELETE /workspaces/{workspaceKey}?expectedVersion=N` returns `204` when the
workspace is not the default, was never published and has no objects and no change sets; active and
retired workspaces follow the same rule, and the key can be created again. Refusals are checked in
this order in one transaction and change nothing:

| Status | Code | When |
|---|---|---|
| 404 | `workspace_not_found` | the key does not exist |
| 409 | `workspace_is_default` | it is the current default |
| 409 | `workspace_has_publications` | it has ever been published (withdrawn publications count); retire it instead |
| 409 | `workspace_not_empty` | it has objects or change sets; `details` carries `objectCount` and `changeSetCount` |
| 409 | `version_conflict` | `expectedVersion` is stale; `details.currentVersion` |
| 409 | `workspace_delete_retry` | other writes held the database for longer than the busy timeout; retry |

Single-workspace responses (`GET`, `POST` and `PATCH /workspaces/{workspaceKey}`) add `deletable` and,
when it is false, `deleteBlockedBy`: `default`, `published` or `notEmpty`, in the refusal order above.
The paged list omits both. A live write that resolved a workspace before it was deleted or retired is
refused when it commits (`404 workspace_not_found` or `409 workspace_retired`), and nothing is saved.

Create/update/delete/default-switch routes are absent when `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false`.
The flag gates only this catalogue administration: the change-set and publication routes below are
always registered and return `workspace_retired` in a retired workspace.
The flag defaults to true only for the pre-authentication development posture; exposed deployments
must disable it or protect the API with external access control.

## Change sets and publications — current API and accepted targets

A workspace has live data, change sets and publications ([ADR-031](DECISIONS.md#adr-031--workspace-terminology-and-deployment-capability-boundaries)).
A **change set** is an optional group of data changes published together; **publishing** it creates
**Publication N**, an immutable snapshot, and makes its changes live. **Withdrawing** a publication
removes its current designation. Model drafts and model releases are a separate lifecycle
([model endpoints](#model-endpoints)).

ADR-024 replaces the rejected WP4 object-lifecycle surface. Object-draft, object-revision, activation
and object-retirement endpoints from WP4 are migration history, not public contracts; clients and UI
must not call them. WP6 implemented the publication storage and corrective migration, WP7 restored the
canonical record resources over that storage, and WP8 completed and tested the lifecycle surface
below. ADR-026 restored direct live writes; ADR-027 records the remaining WP8.1 corrections; Base 0.8
W2 gave every route, field and error code its ADR-031 name.

**Route shape.** Collections stay nested under their workspace
(`/workspaces/{workspaceKey}/change-sets`, `/workspaces/{workspaceKey}/publications`); a single change
set or publication is addressed flat by its global ID (`/change-sets/{changeSetId}`,
`/publications/{publicationId}`), including its actions. New endpoints follow the same rule.

- `GET|POST /api/v1/workspaces/{workspaceKey}/change-sets` lists cursor-paged change sets or creates
  one from an explicit source. `source: "currentLive"` captures a private immutable base from the
  current live graph; it includes typed fields, parent/typed containment edges, independent relations,
  record versions and the selected model identity, and works when no publication exists. It creates
  no publication. `source: "publication"` requires `derivedFromPublicationId` and retains the selected
  immutable publication as the source. For compatibility, omitted `source` keeps the old meaning: a
  supplied `derivedFromPublicationId` derives from that publication and its absence creates the
  documented empty development/bootstrap root. `currentLive` rejects a publication ID and
  `publication` rejects its absence with request validation errors; clients must not infer current
  data from the last publication.
- `GET|PATCH|DELETE /api/v1/change-sets/{changeSetId}` reads, names or discards a change set. PATCH
  and DELETE claim `expectedVersion`. An unknown ID returns `404 change_set_not_found`.
- The existing canonical object, attribute, containment and relation resources retain their paths,
  request/response shapes and CRUD semantics. `workspaceKey` selects live data, `changeSetId` selects
  the effective content of a change set for reads and writes, and `publicationId` selects an
  immutable publication. Change-set and publication contexts are mutually exclusive. Writes go into a
  change set only when the caller supplies `changeSetId` (with `expectedChangeSetVersion`); change-set
  updates and deletes also claim the existing record's `expectedVersion`, while a create has no prior
  record version. Without a change set, mutations target live data; updates/deletes claim the record
  `expectedVersion`, while creation has no previous record version; an existing object or relation
  supplies its workspace context. Only a live object create requires `workspaceKey`. This execution
  context is not a second public CRUD dialect: there are no `/change-sets/{changeSetId}/objects` or
  `/change-sets/{changeSetId}/relations` resources. Live writes never change a publication.
- Change-set creation accepts optional `modelReleaseId` (installed public UUID). Current-live creation
  captures the active data and versions while pinning the chosen release; the complete copied graph
  must fit before creation commits. Creation from a publication retains that publication's pin and
  refuses a simultaneous release selection. Change-set responses include `modelReleaseId`,
  `modelReleaseKey` and `modelReleaseVersion`.
- `PATCH /api/v1/change-sets/{changeSetId}/model-release` accepts `modelReleaseId` and
  `expectedChangeSetVersion`. It claims the change-set version, checks the complete effective graph
  (base plus authored content minus tombstones) under the target, then changes only that pin. Success
  increments the change-set version and audits old/new public release identities. A valid request
  selecting the current pin is a no-op. Stale claims return `409 change_set_version_conflict`.
  Declared attribute type changes for stored effective object/relation values require conversion,
  even if a target normalizer could accept the old value. Populated containment also retains its
  source model semantics; changing those requires conversion. Missing required fields are not
  defaulted during compatibility checks. Incompatible content returns
  `409 change_set_content_incompatible` with `details.diagnostics` (at most 20), `diagnosticCount` and
  `diagnosticsTruncated`; refusal leaves content, pin and version unchanged. Uniqueness conflict ID
  previews are also bounded to 20 with exact count/truncation metadata. No conversion is performed.
  Missing, unsupported and invalid targets use `pinned_model_unavailable`,
  `unsupported_pinned_model_schema` and `pinned_model_invalid` respectively.
- `/model` and model metadata reads accept `changeSetId` or `publicationId` and resolve that context's
  installed model. Metadata cursors are bound to the release identity. Change-set record reads, writes
  and graph validation use the change set's pin even when it differs from active; agreement with the
  active release is a separate requirement for publishing. Discard does not require model agreement.
- `POST /api/v1/change-sets/{changeSetId}/validation` validates the complete effective graph without
  publishing. `POST /api/v1/change-sets/{changeSetId}/publication` publishes it and requires
  `expectedChangeSetVersion` and nullable `expectedActivePublicationId`. Stored read-only values,
  including model defaults, are valid publication content and are checked for their declared types and
  constraints; ordinary writes and attribute deletion still enforce the binding's read-only
  restriction.
- `GET /api/v1/workspaces/{workspaceKey}/publications` and `GET /api/v1/publications/{publicationId}`
  list and read publications. A publication carries `publicationNumber`, its `status` (`active` while
  it is the workspace's current publication, otherwise `withdrawn`), `publishedAt`, `withdrawnAt`,
  `derivedFromPublicationId`, `supersedesPublicationId` and its `modelReleaseId`, `modelReleaseKey`
  and `modelReleaseVersion`, so a client can show "Publication 12 · model 0.8.0 · 3 Sep 2026".
  `publicationNumber` is a per-workspace counter that never restarts, not a version. The list is
  newest first by publication number with the public UUID as a unique descending tie-breaker. Its
  cursor is bound to the workspace and descending sort; an ascending, malformed or differently scoped
  cursor returns `422 invalid_cursor` with `Publication cursor is invalid`. Pages contain 1–500 items
  and exact retry is deterministic. An unknown ID returns `404 publication_not_found`.
- `POST /api/v1/publications/{publicationId}/withdrawal` withdraws the workspace's current
  publication: its status becomes `withdrawn` and the workspace no longer has a current publication.
  The path ID is the concurrency claim, so a publication that is no longer current returns
  `409 workspace_active_publication_conflict`. It retains the live records and every publication; it
  does not retire the workspace or change any individual record. A retired workspace refuses it with
  `409 workspace_retired`.

A publication snapshots one graph: objects, typed attributes, containment (both parent projection
and typed edge), required ownership relations and independent relations. Stable object and relation
UUIDs remain integration identities but have no lifecycle state. Change sets pin `modelReleaseId`;
publications record the `modelReleaseId` they were published under. Publishing against another
resolved model returns `409 change_set_model_release_conflict` and never rebases implicitly.
Publishing delta-merges the change set onto the current live content and snapshots the merged graph,
so a change set started from an earlier publication preserves newer live records it never touched
(ADR-026). Conflicts are `change_set_version_conflict`, `workspace_active_publication_conflict`,
`change_set_model_release_conflict`, and `version_conflict` — publishing reports every per-record merge
divergence under `409 version_conflict` with `details.conflicts` (`kind`, `id`, `code`
`version_mismatch`/`id_collision`/`duplicate_edge`, expected/actual version) — plus
`422 workspace_graph_invalid` when the merged graph fails whole-graph validation. Publishing also
compares complete source/live relation identities and versions for exact directional mutable binding
sets touched by the change set. A divergent set adds a diagnostic with `kind: "mapping-set"`,
`code: "mapping_set_changed"`, `id`/`anchorObjectId`, physical binding type keys, `direction`,
expected/actual target counts and a recovery message. At most 20 mapping-set diagnostics are
returned; `details.mappingSetConflictCount` gives the exact total and
`details.mappingSetConflictsTruncated` indicates omitted mapping-set diagnostics. No graph is applied,
no publication is created, and the change set remains available. Review current live mappings and
reapply intended changes in a new current-live change set before publishing; validating the unchanged
conflicting change set does not resolve the conflict. Containment/ownership use their existing merge
rules. Identical source/live edge identities and surviving edge versions count as the same graph, even
if an intervening addition was later removed. Change-set and publication collection cursors bind
their selected context identity and query filters; malformed/mismatched tokens return
`422 invalid_cursor`. Live collection cursors bind the effective live workspace and query filters.
Cursor tokens do not bind a model or publication ID unless that context is itself selected.

Current-live capture is implemented and validated for SQLite. PostgreSQL and other dialects currently
return `409 change_set_snapshot_unsupported` for this operation. The service starts an explicit
`BEGIN IMMEDIATE` transaction before reading the graph, which excludes independent SQLite live/model
writers through the base commit. It compares the request's captured active release with
`model_runtime_state` under that reservation, separately from the selected change-set pin; a lock
conflict or changed active selection returns `409 change_set_snapshot_retry` with an actionable retry
message. Other database dialects return `409 change_set_snapshot_unsupported` rather than silently
offering a weaker, potentially mixed capture. The private base is deleted with its change set on
discard or publish and is never a publication or part of publication lineage.

Change-set responses return `source: "currentLive"`, `"publication"` or `"empty"`; `empty` reports a
compatible legacy/bootstrap change set and is not a normal source choice. The private base ID is not
exposed.

Change-set and publication reads resolve their pinned supported model before field/filter metadata,
typed responses or relationship expansion. Missing, corrupt or unsupported pins return structured
errors and never fall back to the active model. Supplying `workspaceKey` with a change set or
publication must match that context; change-set and publication IDs remain mutually exclusive. Live
writes continue to resolve the active model, while change-set writes validate and respond using the
change set's pinned model.

These refusals use the normal error envelope. A context mismatch is `422` with
`{"error":{"code":"workspace_context_mismatch","message":"workspaceKey does not match the selected context","details":{"workspaceKey":"...","contextWorkspaceKey":"..."}}}`.
A missing pinned release is `409` with code `pinned_model_unavailable`; an invalid pinned document is
`409` with `pinned_model_invalid` and its diagnostics; and an unsupported schema is `409` with
`unsupported_pinned_model_schema`, including `modelReleaseId`, `schemaVersion`, and
`supportedSchemaVersions: ["0.5", "0.6"]` in details.
>
> **Target — product 0.10 historical model migration.** Preview incompatibilities and potential data
> loss for one workspace and a named installed target release (normally the pin of a change set started from a publication),
> then confirm the exact reviewed plan or cancel. Confirmed execution migrates live data to that target and changes
> only the selected workspace model assignment atomically. Model drafts and change sets remain separate;
> target validity, conflict checks and parser support still apply. Nothing today overrides them.
>
> **Product 0.7 change-set version selection (ADR-028; backend delivered in WP-6).** A change set may be created against,
> or explicitly moved onto, any installed release the deployment supports, so one change set prepares a
> candidate release while another continues on the release serving live data. The target must be
> installed, parseable and supported; refusal reuses the existing pinned-model envelope
> (`pinned_model_unavailable`, `pinned_model_invalid`, `unsupported_pinned_model_schema`) rather than
> introducing a weaker success path. Choosing a release is an edit to that change set and never changes
> another change set, another workspace or the active selection. It does not make publishing accept
> a mismatched model: the refusal above still holds, and a change set whose version differs from the
> active release cannot be published. Once a prepared release is activated and begins serving live
> data, a change set still on the replaced release remains readable and editable under its own version
> and must be explicitly moved or discarded before it can be published.
>
> **0.7 compatibility and atomicity detail (WP-6 backend delivered; WP-7 browser pending).**
> Current-live change-set creation
> against a selected release and explicit pin changes validate the complete effective candidate graph,
> including inherited content and tombstones, under that release. Incompatible content returns
> `409 change_set_content_incompatible` with bounded diagnostics; creation leaves no change set or base, and failed
> changes leave content, pin and version unchanged. Version change atomically claims the expected change-set
> version, validates and updates the pin, increments its version and audits old/new release identities.
> The capture's active release/runtime token is separate from the chosen change-set pin.
> Creation from a publication retains its source pin; another selection is a subsequent explicit change.
> WP-7 will reload model-dependent browser navigation, forms, lookups and caches, reset obsolete
> cursors and protect dirty input on local or externally detected pin changes.
>
> **Target — product 0.10 moving a change set onto an incompatible release (ADR-028).** Moving a change set onto
> a release whose rules its stored content does not already satisfy requires the conversion machinery
> above, applied to that change set's own candidate graph and its current-live base: a review reports the
> conversions and any potential loss of content authored in the change set, and applies only on confirmation of the
> exact reviewed change-set and release versions. Cancel, stale review or revalidation failure changes the
> change set, its version, live data and publications not at all, and a move never deletes change-set
> content to make a target fit.

## Generic runtime CRUD contract

The following routes remain the canonical generic runtime CRUD contract. Workspace lifecycle changes
the selected storage/publication context, not these operations. Publication reads are read-only; the
same operations write either to an explicitly selected mutable change set or, without one, directly
to the live active store (explicit workspace on creation, record version on updates/deletes). There are no object drafts, object
publications or object lifecycle endpoints.

Content context extends rather than replaces the established payloads. Collection and identity reads
use their existing active `workspaceKey` context by default; optional `changeSetId` selects the
effective change set and optional `publicationId` selects an immutable publication. Those two optional
contexts are mutually exclusive. POST, PATCH and DELETE use `changeSetId` plus
`expectedChangeSetVersion` only for the change set path. A live object create must provide
`workspaceKey`; a change set create infers it from the change set. Live object updates, attribute writes and
relation mutations infer the workspace from their existing record(s), so their payloads do not add
`workspaceKey`. Successful change set record mutation responses supply `changeSetVersion`. It has no usable value
for live/publication responses; the nullable response fields currently serialize as null where unset.
Change set GET paths do not consistently populate it, so read the change set resource for its current aggregate
version rather than assuming every record read returns one.

- `GET /api/v1/objects/{objectTypeKey}` — list objects of a type
- `POST /api/v1/objects` — create an object
- `GET /api/v1/objects/{objectTypeKey}/{objectId}?changeSetId={id}|publicationId={id}` — get one object from a change set or a publication; omit both for the live active projection
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}` — update an object
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}` — delete an object

Object collections accept the [collection paging](#collection-paging) parameters (including `seek`),
`pageSize`, `applicationKey`, `workspaceKey`, optional
`changeSetId` or `publicationId`, `parentObjectId` or `topLevel`, `search`, one `sort` and typed filters named
`filter.<field>.<operator>=<value>`. Filters take built-in fields and attributes with the
`filterable` feature. `sort` takes `name`, `id`, `objectType` (ordered by the type's model name, then
by name), live `createdAt`/`updatedAt`, or any attribute the type binds, flagged `sortable` or not
(S4R3 revision). JSON attributes are excluded from both. Prefix a sort with
`-` for descending order. Null and unset attribute values sort last in either direction, and every
live ordering uses the internal sequence as a non-public final tie-breaker; change sets and publications record
no creation sequence, so there the record ID is the final tie-breaker. Omitting `sort` orders by name
in every context (S4R4); before 0.8 it listed live records in creation order and change-set and publication
records by ID. Page size defaults to 100 and has a documented
maximum of 500. `nextCursor` is null only when that traversal is complete.

`topLevel=true` (Base 0.8 S4) lists only records without a parent, so a tree can page a root type
without loading its descendants; it holds in change-set and publication contexts too. It cannot be combined
with `parentObjectId` (`422 mutually_exclusive_scope`). A branch whose children have several types
pages each child type separately with `parentObjectId`; there is no mixed-type list.

Search, typed filters and sort mean the same in live, change-set and publication contexts (Base 0.8 S2): the
same query over the same data returns the same records in the same order, apart from the order of
records that tie on the sort. `search` matches the record name and model attributes with the
`searchable` feature, case-insensitively, in every context. A change-set or publication page costs its own
rows, not the size of the change set or publication.

`search` is a literal substring: `%`, `_` and quotes match themselves. Case folding covers ASCII
letters only (SQLite's `LIKE`), so `Ü` matches `Ü` but not `ü`; this is unchanged by the search index.
Since Base 0.8 S8 (D25), a search of three or more characters looks up attribute values through a
trigram index over text values, reading only the records whose values contain the text; names are
matched on the type's name index, about 20 ms per 100,000 records. A name search with its total over
100,000 records takes about 35 ms in live data and a publication and 75 ms in a change set (0.7–0.9 s before). A
one- or two-character search has no trigram to look up and reads each record's values (0.4–0.7 s
over 100,000 records when few names match); so does a phrase present in more than 10,000 text values,
where reading the index would cost more than it saves (about 0.4 s when it is in every value and no
name). The index narrows which records are read, never which match: every path returns the same
records. The index is SQLite's (FTS5); on PostgreSQL, until its trigram form arrives with
0.10, a search reads each record's values with the same results. A first page, or a `position` page, that reaches the end of the list reports its
`totalCount` without a second count.

Change sets and publications record no timestamps. In a `changeSetId` or `publicationId` context,
object and relation responses return `createdAt` and `updatedAt` as `null`, and a filter or sort on
either field is refused with `422 invalid_filter` or `invalid_sort` (“Created is not recorded in change sets
or publications”) instead of matching nothing. Live responses always carry both timestamps.

Text filters support `eq`, `contains`, `startsWith` and `isNull`; number, date and datetime filters
support `eq`, `lt`, `lte`, `gt`, `gte` and `isNull`; booleans support `eq` and `isNull`. Attribute
fields also support `isUnset`. `isNull` and `isUnset` take `true` or `false`; boolean values use the
same lexical form, while dates and datetimes use ISO 8601. Exact equality is case-sensitive and the
two text matching operators are case-insensitive. Different filters combine with AND; repeated `eq`
for one field combines with OR. Invalid grammar, capability, operator or typed input returns
`422 invalid_filter` (or `invalid_sort`) with `details.path` identifying the query parameter.

Object cursors are signed opaque tokens. Live cursors bind object type, selected sort, effective live
workspace and every effective normalized filter; they do not bind a model or publication. Change-set and
publication cursors additionally bind their selected change-set or publication context. A malformed token, a
changed sort/filter/context or reuse for another collection returns `422 invalid_cursor`. A live
publication switch alone does not invalidate the cursor. Live predicates use keyset
positions rather than offsets, so duplicate names and timestamps remain deterministic and inserts do
not cause already traversed rows to repeat merely by shifting offsets. Live changes to sort keys may
affect traversal; a live cursor is not a snapshot-consistent export.

Change-set context `DELETE` requires `changeSetId`, `expectedChangeSetVersion` and
`expectedVersion`; live `DELETE` requires only `expectedVersion`. Both accept optional `cascade`
(default `false`). A change set delete changes only the selected change set; live reads remain
unchanged until it is published. Without cascade,
an object that has no children or non-parent relations is deleted normally. If dependencies exist, the
request performs no deletion and returns `409 object_has_dependants` with a structured impact report:

```json
{
  "error": {
    "code": "object_has_dependants",
    "message": "Object has dependant records or relationships; repeat with cascade=true",
    "details": {
      "objectsToDelete": [
        {
          "id": "...",
          "name": "Timetables",
          "objectTypeKey": "codelist",
          "applicationKey": "rdm-master",
          "parentObjectId": "...",
          "reason": "child"
        }
      ],
      "objectsToRetire": [
        {
          "id": "...",
          "name": "Timetables",
          "objectTypeKey": "codelist",
          "applicationKey": "rdm-master",
          "parentObjectId": "...",
          "reason": "child"
        }
      ],
      "relationshipsToRemove": [
        { "id": "...", "relationTypeKey": "maps-to" }
      ],
      "objectCount": 2,
      "relationshipCount": 1,
      "retainedAssociationCount": 1,
      "deletionPreviewToken": "opaque-signed-token"
    }
  }
}
```

Confirming requires both `cascade=true` and the opaque `deletionPreviewToken` returned by that exact
preview. The token locks the displayed hierarchy and incident relationships, including their record
versions, workspace/change set and model context. If an object, attribute, parent link or incident
relationship changes before confirmation, deletion changes nothing and returns `409
deletion_preview_changed`: `The object was modified by another session. Please retry.` The client must
request and display a fresh preview. A missing token returns `409 deletion_preview_required`; a token
cannot be reused for another object, workspace, change set or model.

Deletion is always confined to one workspace. If inconsistent stored data contains a containment or
relationship edge into another workspace, the operation changes nothing and returns `409
workspace_graph_invalid` so the data can be repaired safely.

A matching confirmation recursively deletes all containment descendants and their attributes, and
removes every relationship incident to the deletion set. Optional and many-to-many non-parent links
are unlinked without deleting the other endpoint. A directed, required `one-to-one` or `one-to-many`
binding has PK→FK ownership semantics; cascading from its `from` owner also deletes its `to` dependent,
including that dependent's own containment descendants. The confirmed hierarchy is re-read and
compared inside the deletion transaction before any delete or audit persists. The complete operation
and its audit events commit atomically. A stale root `expectedVersion` returns HTTP 409.

`objectsToDelete` contains the dependent rows, while `objectCount` includes the root object. The
duplicate `objectsToRetire` key is retained for legacy compatibility and has the same rows; it does
not mean that this delete retires records. `retainedAssociationCount` counts incident relationships
with an endpoint outside the deletion set.

### Create request

`POST /api/v1/objects` accepts a JSON body. Extra fields are rejected.

| Field | Required | Description |
|---|---|---|
| `id` | No | UUID v4. When provided, the object is created with this ID; rejected if already exists. When omitted, a new UUID is generated. |
| `applicationKey` | Yes | Application the object belongs to. |
| `objectTypeKey` | Yes | Type of the object to create. |
| `name` | Yes | Display name (1–500 characters). |
| `workspaceKey` | Yes for live create; No for change set create | Required without `changeSetId`; inferred from the change set when targeting one. A supplied key must match the selected change set or publication context. |
| `changeSetId` | No | Optional mutable change set that receives the record. Omit it for a live create. |
| `expectedChangeSetVersion` | When targeting a change set | Aggregate change-set concurrency claim. |
| `parentObjectId` | No | Parent object UUID. Required for non-root-creatable types. |
| `attributes` | No | Array of attribute values (see below). |
| `initialRelations` | Conditionally | Required non-parent relationships created atomically with the object. |

```json
{
  "id": "c5588b49-...",
  "applicationKey": "rdm-master",
  "objectTypeKey": "domain",
  "name": "Connections",
  "workspaceKey": "default",
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
transaction. The first create example is live. For the optional staged path, supply the change set and its
version; for example, a Translation with its target can be created in a selected change set as follows:

```json
{
  "applicationKey": "rdm-translations",
  "objectTypeKey": "translation",
  "workspaceKey": "default",
  "changeSetId": "change-set-uuid",
  "expectedChangeSetVersion": 4,
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

`text`, `longText`, `integer` and `boolean` values are JSON strings, numbers and booleans. A
`decimal` is a decimal string (`"12.5"`), a `date` an ISO 8601 date (`"2026-07-01"`) and a
`dateTime` an ISO 8601 date-time. Requests may send a `decimal` as a JSON number. Every context
returns one canonical form: a `decimal` without trailing zeros (`"12.50"` reads back as `"12.5"`,
`"7.0"` as `"7"`) and a `dateTime` as the same instant in UTC with an explicit offset
(`"2026-12-24T18:00:00+01:00"` reads back as `"2026-12-24T17:00:00+00:00"`). A zone-less `dateTime`
in a write or filter is read as UTC. Live, change set and publication reads use the same forms, so equal
values compare equal for uniqueness, and filters and sorts compare values by their declared type in
every context.

### Attribute uniqueness

An attribute type may declare `"features": { "unique": true }`. Values for such an attribute are
enforced unique per workspace across all objects that carry that attribute type. Create and update
return `409 duplicate_attribute_value` when a value collides. Uniqueness is supported for the scalar
value types (`text`, `longText`, `integer`, `decimal`, `boolean`, `date`, `dateTime`); declaring it on
a `json` type is rejected at model load. Enforcement is service-level (see `docs/DECISIONS.md`); a
database-level constraint is planned.

### Update request

`PATCH /api/v1/objects/{objectTypeKey}/{objectId}` accepts a partial update. Only provided fields
are changed. `expectedVersion` is required for live and change set updates. `changeSetId` is optional;
when present, `expectedChangeSetVersion` is required as well. Claims are atomic; stale writes
return HTTP 409. Live payloads do not accept `workspaceKey`.

```json
{
  "name": "Renamed domain",
  "attributes": [
    { "attributeTypeKey": "description", "value": "Updated description" }
  ],
  "expectedVersion": 1
}
```

For a change set update, add `changeSetId` and `expectedChangeSetVersion` to the same payload.
The preceding example is a normal live correction and does not create a publication.

### Attribute value endpoints

Attribute values are child resources of an object, addressable one at a time. An object can carry at
most one stored value per attached attribute type, so the URL leaf is the attribute type's `key`:

Attribute GET routes accept optional `changeSetId` or `publicationId` using the same
mutually exclusive content-context rules as object reads.

- `GET /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — read one stored value
- `POST /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — set a value that is not yet stored
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — update a stored value
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}?expectedVersion={n}&changeSetId={id}&expectedChangeSetVersion={n}` — remove a stored value

`GET` returns one stored value with `objectVersion`, the containing object's version. Current change set
attribute GET does not populate `changeSetVersion`; the optional field is null. Read the change set
resource to obtain its aggregate version. `POST`/`PATCH` return the full object response; successful
change set writes populate the resulting change set version. Live writes have no change set claim or usable change set
version. `DELETE` returns 204.

All attribute mutations require the object's `expectedVersion`. Only explicitly change-set-scoped writes
also require `changeSetId` and `expectedChangeSetVersion` (body for POST/PATCH, query for
DELETE). Both claims apply atomically in change set context; live mutations claim only the object version.

```json
{
  "id": "51d92c5e-...",
  "attributeTypeKey": "description",
  "name": "Description",
  "valueType": "longText",
  "value": "Connections domain",
  "objectVersion": 1,
  "changeSetVersion": null
}
```

This read does not supply a change set version, even when the record was requested through a change set.
Publication values are immutable; live values remain writable. Null change set metadata is not a read-only
flag.

`POST` and `PATCH` share a request body:

```json
{
  "value": "Connections domain",
  "expectedVersion": 1,
  "changeSetId": "change-set-uuid",
  "expectedChangeSetVersion": 6
}
```

- `POST` creates only when no value is stored for the key (`409 attribute_already_exists` otherwise).
- `PATCH` updates only a stored value (`404 attribute_not_found` when the key has no value yet).
- For a live POST/PATCH, omit both change set fields from the example. For live DELETE, supply only
  `expectedVersion`; the change set query fields shown in the route list are optional context.
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
a `details` array. Unexpected internal errors use code `internal_error` and include a
`correlationId` in `details`; the same identifier appears in server logs for operator diagnosis.
A write validated under a model release that was replaced before it committed returns
`409 model_release_changed` and saves nothing (see model activation).

```json
{
  "error": {
    "code": "object_already_exists",
    "message": "An object with ID 'c5588b49-...' already exists"
  }
}
```

Internal error example:

```json
{
  "error": {
    "code": "internal_error",
    "message": "The GET /api/v1/model-releases operation failed unexpectedly. Retry or contact support with reference a1b2c3d4e5f6.",
    "details": { "correlationId": "a1b2c3d4e5f6" }
  }
}
```

## Relation endpoints

- `POST /api/v1/relations`
- `GET /api/v1/relations?objectId={id}&direction={outgoing|incoming|both}&relationTypeKey={key}` (`relationTypeKey` repeatable)
- `GET /api/v1/relations/{relationId}`
- `PATCH /api/v1/relations/{relationId}`
- `DELETE /api/v1/relations/{relationId}?expectedVersion={n}&changeSetId={id}&expectedChangeSetVersion={n}`

Relation GET routes accept optional `changeSetId` or `publicationId` under the same
mutually exclusive content-context rules as object reads. POST/PATCH use optional change set fields in
the body; DELETE uses them in query parameters. Supplying `changeSetId` requires the change set version.
Live update/delete claim only the relation `expectedVersion`; creation has no existing relation version.
Endpoints identify their workspace; live mutation payloads do not accept a new `workspaceKey` field.

`GET /api/v1/relations` accepts its existing `objectId`, `direction` and `relationTypeKey` filters plus
bounded `pageSize` (1–500, default 100) and the [collection paging](#collection-paging) parameters,
including `seek`. It returns the standard page rather than an unbounded array; a legitimate collection
with no matching relationships returns an empty `items`. The cursor is signed and bound
to the anchor object, direction, relation types, search and effective workspace.

Base 0.8 S4 adds `search` and `sort`, revised in S4R1 to mean what they mean on an object list, for
the related record (the other end of each relation), in live, change-set and publication contexts:

- `relationTypeKey` may repeat to list several relation types together.
- `search` matches the related record by name or by any attribute its type binds as `searchable`, as
  a literal, case-insensitive substring. A relation list is bounded by its anchor, so it reads each
  related record's values rather than the S8 trigram index.
- `sort` takes a field of the related record: `name`, `objectType` (its type's model name), any
  non-JSON attribute one of the related types binds, or `ancestor:<type>`, the name of its ancestor of
  that type (as in its `path`; a type met twice resolves to the one nearest the root). `relationship`
  orders by the label each row shows: the relation type's `name` when the anchor is the source, its
  `reverseName` otherwise. Label sorts break ties by name. Prefix `-` for descending. Records without
  the value come last in either direction. `createdAt` and `updatedAt` (the related record's) are
  live only; change sets and publications record no timestamps, so they answer `422 invalid_sort`.
- An attribute sort over several related types puts records whose type lacks the attribute last. An
  ancestor sort needs the listed relations to reach one object type, decided by the anchor record's
  type, `direction` and `relationTypeKey` from the model's allowed relations; otherwise
  `422 invalid_sort`. An `ancestor:<type>` the related type cannot sit under is refused too.
- Without `sort` the list is in name order in every context. Ties break on the relation.
- `seek` takes a value of the sorted field (a name by default).

Change-set and publication relation items carry the related record's `path`, as live items do. A relation page
for a record the context does not hold answers `404 object_not_found` in every context. Change set and
history continuations add their selected context identity; live continuations do not bind an active
publication or model. Publication alone does not invalidate a live continuation. Malformed or
mismatched cursors return `422 invalid_cursor`; cursors issued before S4R1 are refused. Live, the
anchor must be in the selected workspace and the related record is joined in it before projection,
preventing a corrupt or legacy cross-workspace edge from being exposed.

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

`PATCH /api/v1/relations/{relationId}` accepts `{"attributes": {...}, "expectedVersion": n,
"changeSetId": "...", "expectedChangeSetVersion": n}`. The
example is change-set-scoped; omit its two change set fields for a live update. The relation identity
(`relationTypeKey`, `fromObjectId`, `toObjectId`) is immutable; only `attributes`
can be replaced. Replacement attributes are validated against the original allowed pair in the same
transaction as the version claim. `DELETE` returns 204 and removes the relation row. Both mutations
take `expectedVersion` and atomically claim the version, returning `409 version_conflict` when the
claim is stale.

Engine-maintained parent-containment and hierarchy relations — those named in the target object type's
`behavior.parentRelationTypeKeys` and written atomically on parent changes — are read-only through this
API. Creating, updating or deleting them directly returns `422 immutable_relation`; changing them is
done through object parent operations.

A required non-parent relation returns `422 required_relation` when independently deleted. It is part
of the dependent graph's validity and ownership semantics; delete or replace the dependent object
through the owning workflow instead.

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
- Consumer API: a separate read-only tier with model-declared XREF lookup and lists
  ([CONSUMER_API.md](CONSUMER_API.md))

There will be no equivalent of enumerating numeric attribute IDs `1..1000` or using `take: 0` for a full
extract.

## Product 0.7 mapping API (WP-4 and WP-5 delivered)

WP-4 delivers the mapping query endpoints below. WP-5 delivers the atomic replacement
endpoint. Composed acceptance remains in WP-9. WP-1–WP-3 scopes remain frozen.

- `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` takes `applicationKey`, `viewKey`,
  explicit `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction`, bounded `pageSize`,
  `cursor`, optional source search, optional direct `parentObjectId` scope, optional
  `state=mapped|unmapped|ambiguous` and one optional `changeSetId` or `publicationId`.
  Parent and state filtering happen
  before pagination. The effective model resolves the
  configured `mappingGrid`; supplied binding fields must match. Display fields and candidate search
  fields come from that view, so views sharing a binding can differ without a schema extension.
- `GET /api/v1/workspaces/{workspaceKey}/mapping-candidates` takes the same view/context identity,
  `objectTypeKey` matching the configured target side, search and cursor pagination. Eligibility is
  direction-aware; final existence, type, cardinality and graph constraints are checked on save.
- Coverage rows expose typed source/display fields, mapping state, `mappingVersion`, exact
  `targetCount`, at most 20 target summaries and a continuation for remaining targets. State reflects
  the complete count. A cursor-paged target-detail query identifies the same view/binding/anchor and
  observed version; changed versions require refresh. Conflict responses use the same bounded preview
  convention. Coverage fields and version describe one consistent read.
- Cursors bind workspace, live/change-set/publication context, effective model release, view, direction, parent scope,
  mapping state and query
  configuration. Unknown view/binding or parent is `404`; a parent whose model-defined containment
  cannot hold the view's source type and mismatched configuration/cursors are explicit validation
  errors. A valid parent with no matching direct children returns an empty page. The frozen detail route is
  `GET /api/v1/workspaces/{workspaceKey}/mapping-targets`, with the same explicit binding parameters as coverage
  and optional paired `applicationKey`/`viewKey` for view-specific projection, plus `sourceObjectId`, required nonnegative `mappingVersion`,
  optional `cursor`, `pageSize` (1–100; default 20), and one optional `changeSetId` or
  `publicationId`.
  It returns the page's `items` and [paging fields](#collection-paging), then `mappingVersion` and `targetCount`. An observed-version mismatch returns
  `409 mapping_version_conflict` with an instruction to refresh coverage and the current version in
  `error.details.mappingVersion`. A cursor for another version, anchor or context is `422 invalid_cursor`.
  Confirmed live/change-set object cascade deletion advances both directional set versions for every
  removed edge, so existing continuations also require refresh after a cascade. Preview, refused
  and stale-delete requests leave set versions unchanged.

Coverage and candidates use the view's configured page size by default (an explicit `pageSize` must
be 1–100). Search is a literal, case-insensitive substring, limited to 500 characters. Coverage searches
name and attached attributes selected by `sourceColumns`; candidates search only `candidateSearchFields`.
Coverage-state filters use the complete effective relation set, in both directions, before selecting
the requested source page. Views select the returned fields independently of the physical binding. Candidate lookup removes
occupied target-side objects for one-to-one bindings and outgoing one-to-many views; source-dependent
ancestor/graph constraints and final cardinality checks remain the save operation's responsibility.
The mapping queries read effective change-set overlays/tombstones or immutable publications in SQL,
page before projection, and
batch bounded target previews and exact counts within the same transaction as model and version reads.

Object summaries contain `id`, `objectTypeKey`, `name` and a `fields` dictionary keyed by the declared
columns. Attributes retain JSON types (including numeric decimals, integers and booleans); missing
values are `null`. Built-in fields include `id`, `name`, the model's `objectType` label, `path` as a
slash-separated name path, `ancestor:<type>` as the ancestor name, and timestamps. Change-set snapshots do
not store object timestamps, so change set timestamp fields are `null`. Each target summary also preserves
`relationId` and the stored relation `attributes` for future replacement operations.

For example, a coverage page has this shape (cursor strings are opaque):

```json
{
  "items": [{
    "source": {"id": "source-public-id", "objectTypeKey": "source-type", "name": "Source", "fields": {"name": "Source"}},
    "state": "mapped",
    "mappingVersion": 2,
    "targetCount": 1,
    "targets": [{"relationId": "relation-public-id", "attributes": {}, "object": {"id": "target-public-id", "objectTypeKey": "target-type", "name": "Target", "fields": {"name": "Target"}}}],
    "targetsNextCursor": null
  }],
  "nextCursor": null
}
```

The page also carries the [collection paging](#collection-paging) fields (omitted above).
Coverage lists sources and candidates list targets by name, then ID (S4R4; previously by ID).
Coverage accepts `seek` by source name; candidates and target details page without it.
An ambiguous row reports the complete `targetCount`, up to 20 targets and `targetsNextCursor`.
Pass that cursor to `mapping-targets` with the row's source ID and mapping version to continue beyond
the preview. A candidate page is `{items: [object-summary, ...], nextCursor}`.

### Mapping list

- `GET /api/v1/workspaces/{workspaceKey}/mappings` returns a flat, cursor-paged list of mapping edges.
  All filter parameters are optional:
  - `relationTypeKey` — filter to one relation type.
  - `fromObjectTypeKey`, `toObjectTypeKey` — filter to a specific object-type pair.
  - `direction` (`outgoing` | `incoming`) — when omitted, each edge appears **twice** (once per
    direction with swapped source/target), so consumers see the full picture without prior knowledge
    of direction semantics. When supplied, each edge appears once in the requested orientation.
  - `applicationKey` + `viewKey` — both required together; controls column projection only (the view's
    source/target display columns enrich the `fields` dict). Without a view, default projection returns
    `id`, `objectTypeKey`, `name` and an empty `fields` dict.
  - `changeSetId` — read from a change set snapshot instead of live data.
  - `search` — case-insensitive substring on source or target name (max 500 characters).
  - `cursor`, `pageSize` (1–100; defaults to 20 without a view, or the view's configured page size).
- Returns the standard page. Each item contains `relationId`, `relationTypeKey`, `direction`
  (`"outgoing"` or `"incoming"`), `source` and `target` object summaries, the stored relation
  `attributes` and the source anchor's `mappingVersion`.
- Pages with the [collection paging](#collection-paging) parameters except `seek`.
- Unlike coverage, the list shows only existing edges — unmapped sources do not appear. This is useful
  for export, integration, flat-list views, and ad-hoc exploration where the source-anchored grouping
  of coverage is not needed and parameters may not be known upfront.

```json
{
  "items": [{
    "relationId": "relation-public-id",
    "relationTypeKey": "system-value-maps-to-master",
    "direction": "outgoing",
    "source": {"id": "source-id", "objectTypeKey": "system-value", "name": "SV-1", "fields": {}},
    "target": {"id": "target-id", "objectTypeKey": "master-value", "name": "MV-1", "fields": {}},
    "attributes": {},
    "mappingVersion": 2
  }, {
    "relationId": "relation-public-id",
    "relationTypeKey": "system-value-maps-to-master",
    "direction": "incoming",
    "source": {"id": "target-id", "objectTypeKey": "master-value", "name": "MV-1", "fields": {}},
    "target": {"id": "source-id", "objectTypeKey": "system-value", "name": "SV-1", "fields": {}},
    "attributes": {},
    "mappingVersion": 1
  }],
  "nextCursor": null
}
```

### Atomic replacement (WP-5 delivered)

- `PUT /api/v1/workspaces/{workspaceKey}/mappings` accepts `relationTypeKey`, `fromObjectTypeKey`,
  `toObjectTypeKey`, `direction` (outgoing/incoming), `sourceObjectId` (the row anchor), nullable
  `targetObjectId`, `expectedMappingVersion` (≥0), optional relation `attributes` dict and optional
  `changeSetId` with `expectedChangeSetVersion`. Incoming direction reverses source/target
  roles, not the physical type keys. Null target removes the exact selected set; non-null replaces it
  with one selected target.
- Returns `{sourceObjectId, mappingVersion, state, relationId?, changeSetVersion?}`. State is
  `"mapped"` or `"unmapped"`.
- Validates workspace status, endpoint identities and the effective model. Rejects containment
  bindings (`422 immutable_relation`) and required-ownership bindings
  (`422 required_ownership_binding`). Clearing a required relation is `422 required_relation`.
- Direction-aware cross-cardinality is enforced: one-to-one always; one-to-many on outgoing
  direction only. Violations return `409 cardinality_violation`. Ancestor-scoped uniqueness is
  validated against the final graph, excluding edges being replaced. Duplicate scopes return
  `409 duplicate_relation_scope`; a missing required ancestor returns `422 relation_ancestor_required`
  in both mapping and generic relation writes, live or change set.
- Tokens are checked before no-op detection. A stale mapping token returns `409 mapping_version_conflict`
  with `{mappingVersion, targetCount, targets (≤20), targetsNextCursor}` in error details and no
  changes. Change set aggregate conflicts remain distinct (`409 change_set_version_conflict`).
  Large conflict sets include a signed continuation cursor and the selected `applicationKey`/`viewKey`;
  pass these with the binding, source and returned version to `GET /mapping-targets`. When no mapping
  view exists, omit both view keys for a binding-only name projection. Coverage and candidate reads
  still require a declared view. Supplying only one view key is rejected. Explicit empty view keys
  are supplied identities and fail lookup; they never select the binding-only fallback.
  Change set context requires `expectedChangeSetVersion` (`409 change_set_required` if omitted).
- Preserves the selected existing relation identity when the target is retained, removes obsolete
  edges, updates selected attributes or creates a new edge. Maintains all affected outgoing/incoming
  set versions atomically without double increments: the source anchor is incremented once per
  direction, each affected target is incremented once in the opposite direction.
- Omitted `attributes` preserve a retained edge's values; for a new edge they supply no explicit
  values and normal defaults/validation apply. An explicit attribute object replaces the complete set;
  `{}` clears. Null target with non-empty attributes is `422 invalid_clear_attributes`. Typed writes
  use the canonical validation boundary. An identical complete state with valid tokens is a no-op
  with no version increment or audit event.
- Changes record underlying per-relation audit events (created/updated/deleted) and one mapping
  `transition` event with old/new targets, relation identities and attributes.

WP-9 verifies generic-write/mapping races, both directional sets, independent bindings and change set
activation versus live same-set changes. Confirmed missing foundation capabilities trigger a bounded
WP-10 slice and block acceptance; they do not retroactively change WP-3 scope.
