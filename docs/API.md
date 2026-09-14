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
  },
  "workspaceAdmin": {
    "manageWorkspaces": true
  }
}
```

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
reloads the database-selected release. Historical releases using an unsupported schema return `422
unsupported_schema_version`; if a supported installed release fails reparsing, activation returns
`500 invalid_installed_model`. Both failures leave runtime state unchanged.

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
- `422 unsupported_schema_version` when activation targets a historical release whose schema is not
  supported by the runtime;
- `409 activation_conflict` for stale runtime-state tokens; and
- `409 model_migration_required` when stored data prevents activation;
- `500 invalid_installed_model` when persisted release JSON cannot be reparsed for diff or activation;
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

## Workspace endpoints

- `GET /api/v1/workspaces?search=...&status=active|retired|all&pageSize=...&cursor=...`
- `GET /api/v1/workspaces/{workspaceKey}`
- `POST /api/v1/workspaces`
- `PATCH /api/v1/workspaces/{workspaceKey}`
- `GET /api/v1/workspace-runtime-state`
- `PATCH /api/v1/workspace-runtime-state`

Workspace keys are immutable and case-sensitive. Discovery defaults to active records and uses a
filter-bound keyset cursor; detail reads include retired records. Updates claim the workspace version,
and changing the default claims the independent singleton runtime-state version. The current default
cannot be retired, and there is no delete or rename route. Unknown explicit scopes return
`workspace_not_found`; retired scopes remain readable but all object, attribute and relation writes
return `workspace_retired`.

Create/update/default-switch routes are absent when `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false`.
The flag defaults to true only for the pre-authentication development posture; exposed deployments
must disable it or protect the API with external access control.

## Workspace data drafts and publication history — current API and accepted targets

ADR-024 replaces the rejected WP4 object-lifecycle surface. Object-draft, object-revision, activation
and object-retirement endpoints from WP4 are migration history, not public contracts; clients and UI
must not call them. WP6 implemented the workspace-revision storage and corrective migration, WP7
restored the canonical record resources over that storage, and WP8 completed and tested the workspace
lifecycle surface below. ADR-026 restored direct live writes; ADR-027 records the remaining WP8.1
corrections. Current behavior and accepted targets are distinguished below; no new endpoint is
implemented by this documentation update.

- `GET|POST /api/v1/workspaces/{workspaceKey}/drafts` lists cursor-paged drafts or creates a draft
  from an explicit source. `source: "currentLive"` captures a private immutable base from the current
  live graph; it includes typed fields, parent/typed containment edges, independent relations, record
  versions and the selected model identity, and works when no publication exists. It creates neither a
  public revision nor an activation. `source: "revision"` requires `derivedFromRevisionId` and retains
  the selected immutable historical revision as the source. For compatibility, omitted `source` keeps
  the old meaning: a supplied `derivedFromRevisionId` is historical derivation and its absence creates
  the documented empty development/bootstrap root. `currentLive` rejects a revision id and `revision`
  rejects its absence with request validation errors; clients must not infer current data from the last
  publication.
- `GET|PATCH|DELETE /api/v1/workspace-drafts/{draftId}` reads, names or discards a mutable draft.
  PATCH and DELETE claim `expectedVersion`.
- The existing canonical object, attribute, containment and relation resources retain their paths,
  request/response shapes and CRUD semantics. `workspaceKey` selects the live active projection for
  active reads, `workspaceDraftId` selects the effective mutable draft for draft reads and writes, and
  `workspaceRevisionId` selects an immutable historical revision. Draft and historical contexts are
  mutually exclusive. Writes are draft-gated only when the caller supplies `workspaceDraftId` (with
  `expectedWorkspaceDraftVersion`); draft updates and deletes also claim the existing record's
  `expectedVersion`, while draft creation has no prior record version. Without a draft, mutations
  target the live store; updates/deletes claim the record `expectedVersion`, while creation has no
  previous record version; an existing object or relation
  supplies its workspace context. Only a live object create requires `workspaceKey`. This execution context is not a second public CRUD
  dialect. In particular, `/api/v1/workspace-drafts/{draftId}/objects` and
  `/api/v1/workspace-drafts/{draftId}/relations` are explicitly not public resources. Canonical draft record
  updates/deletes use `expectedVersion` and `expectedWorkspaceDraftVersion`; internal service models
  use different names and are not a second client contract. Live writes never mutate a revision snapshot.
- `POST /api/v1/workspace-drafts/{draftId}/validation` validates the complete effective graph without
  publication. `POST /api/v1/workspace-drafts/{draftId}/activation` requires
  `expectedDraftVersion` and nullable `expectedActiveRevisionId`.
  Stored read-only values, including model defaults, are valid snapshot content and are checked for
  their declared types and constraints; ordinary writes and attribute deletion still enforce the
  binding's read-only restriction.
- `GET /api/v1/workspaces/{workspaceKey}/revisions` and
  `GET /api/v1/workspace-revisions/{revisionId}` expose cursor-paged immutable history and bounded
  snapshot reads. Revision discovery is newest first by revision number and public UUID as a unique
  descending tie-breaker. Its cursor is bound to the workspace and descending sort; an ascending,
  malformed or differently scoped cursor returns `422 invalid_cursor` with
  `Workspace revision cursor is invalid`. Pages contain 1–500 items and exact retry is deterministic.
- `POST /api/v1/workspaces/{workspaceKey}/retirement` retires the active workspace content revision
  under `expectedActiveRevisionId` and clears its publication designation. It retains the live
  records; it does not retire, delete or change any individual object, and it is not a user-facing
  data-withdrawal operation.

A workspace revision snapshots one graph: objects, typed attributes, containment (both parent
projection and typed edge), required ownership relations and independent relations. Stable object and
relation UUIDs remain integration identities but have no lifecycle state. Drafts pin `modelReleaseId`;
revisions persist a `modelReleaseId` as their historical model identity. Activation against another
resolved model returns
`workspace_draft_model_release_conflict` and never rebases implicitly. Activation delta-merges the
draft onto the current live content and snapshots the merged graph, so a draft branched from an old
revision preserves newer live records it never touched (ADR-026). Conflicts are
`workspace_draft_version_conflict`, `workspace_active_revision_conflict`,
`workspace_draft_model_release_conflict`, and
`version_conflict` — activation reports every per-record merge divergence under `409 version_conflict`
with `details.conflicts` (`kind`, `id`, `code` `version_mismatch`/`id_collision`/`duplicate_edge`,
expected/actual version) — plus `422 workspace_graph_invalid` when the merged graph fails whole-graph
validation. Draft and historical collection cursors bind their selected context identity and query
filters; malformed/mismatched tokens return `422 invalid_cursor`. Live collection cursors bind the
effective live workspace and query filters. Current cursor
tokens do not bind a model or revision ID unless that context is itself selected.

Current-live snapshot capture is implemented and validated for SQLite. PostgreSQL and other dialects
currently return `409 workspace_draft_snapshot_unsupported` for this operation. The
service starts an explicit `BEGIN IMMEDIATE` transaction before reading the graph, which excludes
independent SQLite live/model writers through the base commit. It compares the request's selected model
release with `model_runtime_state` under that reservation; a lock conflict or changed selection returns
`409 workspace_draft_snapshot_retry` with an actionable retry message. Other database dialects return
`409 workspace_draft_snapshot_unsupported` rather than silently offering a weaker, potentially mixed
snapshot. The private base is deleted with its draft on discard or activation and is never a public
revision or publication lineage.

Draft responses return `source: "currentLive"`, `"revision"` or `"empty"`; `empty` reports a
compatible legacy/bootstrap draft and is not a normal new-draft source choice. The private base ID is
not exposed.

Historical draft and revision reads resolve their pinned supported model before field/filter metadata,
typed responses or relationship expansion. Missing, corrupt or unsupported pins return structured
errors and never fall back to the active model. Supplying `workspaceKey` with a draft or revision must
match that context; draft and revision IDs remain mutually exclusive. Live writes continue to resolve
the active model, while draft writes validate and respond using the draft's pinned model.

These refusals use the normal error envelope. A context mismatch is `422` with
`{"error":{"code":"workspace_context_mismatch","message":"workspaceKey does not match the selected context","details":{"workspaceKey":"...","contextWorkspaceKey":"..."}}}`.
A missing pinned release is `409` with code `pinned_model_unavailable`; an invalid pinned document is
`409` with `pinned_model_invalid` and its diagnostics; and an unsupported schema is `409` with
`unsupported_pinned_model_schema`, including `modelReleaseId`, `schemaVersion`, and
`supportedSchemaVersions: ["0.5", "0.6"]` in details.
>
> **Target — product 0.10 historical model migration.** Preview incompatibilities and potential data
> loss for one workspace and a named installed target release (normally the historical draft’s pin),
> then confirm the exact reviewed plan or cancel. Confirmed execution migrates live data to that target and changes
> only the selected workspace model assignment atomically. Model drafts and data drafts remain separate;
> target validity, conflict checks and parser support still apply. Nothing today overrides them.
>
> **Target — product 0.7 draft version selection (ADR-028).** A workspace draft may be created against,
> or explicitly moved onto, any installed release the deployment supports, so one draft prepares a
> candidate release while another continues on the release serving live data. The target must be
> installed, parseable and supported; refusal reuses the existing pinned-model envelope
> (`pinned_model_unavailable`, `pinned_model_invalid`, `unsupported_pinned_model_schema`) rather than
> introducing a weaker success path. Choosing a release is an edit to that draft and never changes
> another draft, another workspace or the active selection. It does not make ordinary activation accept
> a mismatched model: the refusal above still holds, and a draft whose version differs from the active
> release cannot activate. Once a prepared release is activated and begins serving live data, a draft
> still on the replaced release remains readable and editable under its own version and must be
> explicitly moved or discarded before it can activate.
>
> **0.7 compatibility and atomicity detail (WP-6/WP-7, planned).** Current-live draft creation
> against a selected release and explicit pin changes validate the complete effective candidate graph,
> including inherited content and tombstones, under that release. Incompatible content returns
> `409 draft_content_incompatible` with bounded diagnostics; creation leaves no draft/base, and failed
> changes leave content, pin and version unchanged. Version change atomically claims the expected draft
> version, validates and updates the pin, increments its version and audits old/new release identities.
> The snapshot's captured active release/runtime token is separate from the chosen draft pin.
> Historical-source creation retains its source pin; another selection is a subsequent explicit change.
> The browser reloads all model-dependent navigation, forms, lookups and caches, resets obsolete cursors
> and protects dirty input on local or externally detected pin changes.
>
> **Target — product 0.10 moving a draft onto an incompatible release (ADR-028).** Moving a draft onto
> a release whose rules its stored content does not already satisfy requires the conversion machinery
> above, applied to that draft's own candidate graph and its current-live base: a review reports the
> conversions and any potential loss of draft-authored content, and applies only on confirmation of the
> exact reviewed draft and release versions. Cancel, stale review or revalidation failure changes the
> draft, its version, live data and history not at all, and a move never deletes draft content to make a
> target fit.

## Generic runtime CRUD contract

The following routes remain the canonical generic runtime CRUD contract. Workspace lifecycle changes
the selected storage/publication context, not these operations. Historical reads are read-only; the
same operations write either to an explicitly selected mutable workspace draft or, without one, directly
to the live active store (explicit workspace on creation, record version on updates/deletes). There are no object drafts, object
revisions or object lifecycle endpoints.

Content context extends rather than replaces the established payloads. Collection and identity reads
use their existing active `workspaceKey` context by default; optional `workspaceDraftId` selects the
effective draft and optional `workspaceRevisionId` selects immutable history. Those two optional
contexts are mutually exclusive. POST, PATCH and DELETE use `workspaceDraftId` plus
`expectedWorkspaceDraftVersion` only for the draft path. A live object create must provide
`workspaceKey`; a draft create infers it from the draft. Live object updates, attribute writes and
relation mutations infer the workspace from their existing record(s), so their payloads do not add
`workspaceKey`. Successful draft record mutation responses supply `workspaceDraftVersion`. It has no usable value
for live/history responses; the nullable response fields currently serialize as null where unset.
Draft GET paths do not consistently populate it, so read the draft resource for its current aggregate
version rather than assuming every record read returns one.

- `GET /api/v1/objects/{objectTypeKey}` — list objects of a type
- `POST /api/v1/objects` — create an object
- `GET /api/v1/objects/{objectTypeKey}/{objectId}?workspaceDraftId={id}|workspaceRevisionId={id}` — get one object from draft or history; omit both for the live active projection
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}` — update an object
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}` — delete an object

Object collections accept `cursor`, `pageSize`, `applicationKey`, `workspaceKey`, optional
`workspaceDraftId` or `workspaceRevisionId`, `parentObjectId`, `search`, one `sort` and typed filters named
`filter.<field>.<operator>=<value>`. Built-in fields and model attributes with the corresponding
`filterable` or `sortable` feature are available; JSON attributes are excluded. Prefix a sort with
`-` for descending order. Null and unset attribute values sort last in either direction, and every
ordering uses the internal sequence as a non-public final tie-breaker. Omitting `sort` preserves
creation sequence order. Page size defaults to 100 and has a documented maximum of 500.
`nextCursor` is null only when that traversal is complete.

Text filters support `eq`, `contains`, `startsWith` and `isNull`; number, date and datetime filters
support `eq`, `lt`, `lte`, `gt`, `gte` and `isNull`; booleans support `eq` and `isNull`. Attribute
fields also support `isUnset`. `isNull` and `isUnset` take `true` or `false`; boolean values use the
same lexical form, while dates and datetimes use ISO 8601. Exact equality is case-sensitive and the
two text matching operators are case-insensitive. Different filters combine with AND; repeated `eq`
for one field combines with OR. Invalid grammar, capability, operator or typed input returns
`422 invalid_filter` (or `invalid_sort`) with `details.path` identifying the query parameter.

Object cursors are signed opaque tokens. Live cursors bind object type, selected sort, effective live
workspace and every effective normalized filter; they do not bind a model or revision. Draft and
historical cursors additionally bind their selected draft or revision context. A malformed token, a
changed sort/filter/context or reuse for another collection returns `422 invalid_cursor`. A live
publication switch alone does not invalidate the cursor. Live predicates use keyset
positions rather than offsets, so duplicate names and timestamps remain deterministic and inserts do
not cause already traversed rows to repeat merely by shifting offsets. Live changes to sort keys may
affect traversal; a live cursor is not a snapshot-consistent export.

Draft-context `DELETE` requires `workspaceDraftId`, `expectedWorkspaceDraftVersion` and
`expectedVersion`; live `DELETE` requires only `expectedVersion`. Both accept optional `cascade`
(default `false`). A draft delete changes only the selected workspace draft; live reads remain
unchanged until activation. Without cascade,
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
versions, workspace/draft and model context. If an object, attribute, parent link or incident
relationship changes before confirmation, deletion changes nothing and returns `409
deletion_preview_changed`: `The object was modified by another session. Please retry.` The client must
request and display a fresh preview. A missing token returns `409 deletion_preview_required`; a token
cannot be reused for another object, workspace, draft or model.

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
| `workspaceKey` | Yes for live create; No for draft create | Required without `workspaceDraftId`; inferred from the draft when targeting one. A supplied key must match the selected draft or revision context. |
| `workspaceDraftId` | No | Optional mutable workspace draft that receives the record. Omit it for a live create. |
| `expectedWorkspaceDraftVersion` | When targeting a draft | Aggregate workspace-draft concurrency claim. |
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
transaction. The first create example is live. For the optional staged path, supply the draft and its
version; for example, a Translation with its target can be created in a selected draft as follows:

```json
{
  "applicationKey": "rdm-translations",
  "objectTypeKey": "translation",
  "workspaceKey": "default",
  "workspaceDraftId": "workspace-draft-uuid",
  "expectedWorkspaceDraftVersion": 4,
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
are changed. `expectedVersion` is required for live and draft updates. `workspaceDraftId` is optional;
when present, `expectedWorkspaceDraftVersion` is required as well. Claims are atomic; stale writes
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

For a draft update, add `workspaceDraftId` and `expectedWorkspaceDraftVersion` to the same payload.
The preceding example is a normal live correction and does not create a workspace revision.

### Attribute value endpoints

Attribute values are child resources of an object, addressable one at a time. An object can carry at
most one stored value per attached attribute type, so the URL leaf is the attribute type's `key`:

Attribute GET routes accept optional `workspaceDraftId` or `workspaceRevisionId` using the same
mutually exclusive content-context rules as object reads.

- `GET /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — read one stored value
- `POST /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — set a value that is not yet stored
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}` — update a stored value
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}?expectedVersion={n}&workspaceDraftId={id}&expectedWorkspaceDraftVersion={n}` — remove a stored value

`GET` returns one stored value with `objectVersion`, the containing object's version. Current draft
attribute GET does not populate `workspaceDraftVersion`; the optional field is null. Read the draft
resource to obtain its aggregate version. `POST`/`PATCH` return the full object response; successful
draft writes populate the resulting draft version. Live writes have no draft claim or usable draft
version. `DELETE` returns 204.

All attribute mutations require the object's `expectedVersion`. Only explicitly draft-scoped writes
also require `workspaceDraftId` and `expectedWorkspaceDraftVersion` (body for POST/PATCH, query for
DELETE). Both claims apply atomically in draft context; live mutations claim only the object version.

```json
{
  "id": "51d92c5e-...",
  "attributeTypeKey": "description",
  "name": "Description",
  "valueType": "longText",
  "value": "Connections domain",
  "objectVersion": 1,
  "workspaceDraftVersion": null
}
```

This read does not supply a draft version, even when the record was requested through a draft.
Historical values are immutable; live values remain writable. Null draft metadata is not a read-only
flag.

`POST` and `PATCH` share a request body:

```json
{
  "value": "Connections domain",
  "expectedVersion": 1,
  "workspaceDraftId": "workspace-draft-uuid",
  "expectedWorkspaceDraftVersion": 6
}
```

- `POST` creates only when no value is stored for the key (`409 attribute_already_exists` otherwise).
- `PATCH` updates only a stored value (`404 attribute_not_found` when the key has no value yet).
- For a live POST/PATCH, omit both draft fields from the example. For live DELETE, supply only
  `expectedVersion`; the draft query fields shown in the route list are optional context.
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
- `DELETE /api/v1/relations/{relationId}?expectedVersion={n}&workspaceDraftId={id}&expectedWorkspaceDraftVersion={n}`

Relation GET routes accept optional `workspaceDraftId` or `workspaceRevisionId` under the same
mutually exclusive content-context rules as object reads. POST/PATCH use optional draft fields in
the body; DELETE uses them in query parameters. Supplying `workspaceDraftId` requires the draft version.
Live update/delete claim only the relation `expectedVersion`; creation has no existing relation version.
Endpoints identify their workspace; live mutation payloads do not accept a new `workspaceKey` field.

`GET /api/v1/relations` accepts its existing `objectId`, `direction` and `relationTypeKey` filters plus
bounded `pageSize` (1–500, default 100) and opaque `cursor`. It returns
`{"items": [...], "nextCursor": null}` rather than an unbounded array. A legitimate collection with
no matching relationships returns `{"items": [], "nextCursor": null}`. The cursor is signed and bound
to the anchor object, direction, relation type and effective workspace. Draft/history continuations
add their selected context identity; live continuations do not bind an active revision or model.
Publication alone does not invalidate a live continuation. Malformed or mismatched cursors return `422 invalid_cursor`. Both relation endpoint objects are joined in the anchor object's
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

`PATCH /api/v1/relations/{relationId}` accepts `{"attributes": {...}, "expectedVersion": n,
"workspaceDraftId": "...", "expectedWorkspaceDraftVersion": n}`. The
example is draft-scoped; omit its two draft fields for a live update. The relation identity
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

There will be no equivalent of enumerating numeric attribute IDs `1..1000` or using `take: 0` for a full
extract.

## Product 0.7 mapping API (WP-4 delivered; WP-5 planned)

WP-4 delivers the three mapping query endpoints below. Atomic replacement remains planned in
WP-5; composed acceptance remains in WP-9. WP-1–WP-3 scopes remain frozen.

- `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` takes `applicationKey`, `viewKey`,
  explicit `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction`, bounded `pageSize`,
  `cursor`, optional source search and optional `workspaceDraftId`. The effective model resolves the
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
- Cursors bind workspace, live/draft context, effective model release, view, direction and query
  configuration. Unknown view/binding is `404`; mismatched configuration and cursors are explicit
  validation errors. The frozen detail route is
  `GET /api/v1/workspaces/{workspaceKey}/mapping-targets`, with the same required view and explicit
  binding parameters as coverage, plus `sourceObjectId`, required nonnegative `mappingVersion`,
  optional `cursor`, `pageSize` (1–100; default 20), and optional `workspaceDraftId`.
  It returns `{mappingVersion, targetCount, items, nextCursor}`. An observed-version mismatch returns
  `409 mapping_version_conflict` with an instruction to refresh coverage and the current version in
  `error.details.mappingVersion`. A cursor for another version, anchor or context is `422 invalid_cursor`.

Coverage and candidates use the view's configured page size by default (an explicit `pageSize` must
be 1–100). Search is a literal, case-insensitive substring, limited to 500 characters. Coverage searches
name and attached attributes selected by `sourceColumns`; candidates search only `candidateSearchFields`.
Views select the returned fields independently of the physical binding. Candidate lookup removes
occupied target-side objects for one-to-one bindings and outgoing one-to-many views; source-dependent
ancestor/graph constraints and final cardinality checks remain the save operation's responsibility.
The mapping queries read effective draft overlays and tombstones in SQL, page before projection, and
batch bounded target previews and exact counts within the same transaction as model and version reads.

Object summaries contain `id`, `objectTypeKey`, `name` and a `fields` dictionary keyed by the declared
columns. Attributes retain JSON types (including numeric decimals, integers and booleans); missing
values are `null`. Built-in fields include `id`, `name`, the model's `objectType` label, `path` as a
slash-separated name path, `ancestor:<type>` as the ancestor name, and timestamps. Draft snapshots do
not store object timestamps, so draft timestamp fields are `null`. Each target summary also preserves
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

An ambiguous row reports the complete `targetCount`, up to 20 targets and `targetsNextCursor`.
Pass that cursor to `mapping-targets` with the row's source ID and mapping version to continue beyond
the preview. A candidate page is `{items: [object-summary, ...], nextCursor}`.

### Planned atomic replacement (WP-5)

- `PUT /api/v1/workspaces/{workspaceKey}/mappings` accepts explicit physical endpoint type keys,
  relation type, direction, `sourceObjectId` (the row anchor), nullable `targetObjectId`,
  `expectedMappingVersion`, optional relation `attributes` and optional draft context with
  `expectedWorkspaceDraftVersion`. Incoming direction reverses row/target roles, not physical keys.
  Null removes only the exact selected set. Non-null replaces it with one selected target.
- Validate status, endpoint identities and the effective model; reject containment/required ownership.
  Clearing is allowed only where empty is valid. The operation's one-target rule does not change the
  binding's direction-aware cardinality or broaden validation to overwrite another source's mapping.
- Claim tokens before no-op detection. A stale mapping token returns `409 mapping_version_conflict`
  with current version/count/preview/continuation and no changes. Draft aggregate conflicts remain
  distinct. Preserve the selected existing relation identity, remove obsolete edges, update selected
  attributes or create an absent edge, and maintain all affected outgoing/incoming versions through
  the foundation service atomically without double increments.
- Omitted attributes preserve a retained edge's values; for a new edge they supply no explicit values
  and normal defaults/validation apply. An explicit attribute object replaces the complete set;
  `{}` clears only where valid. Null target requires omitted or empty attributes. Typed writes use
  the canonical validation boundary. An identical complete state with valid tokens is a no-op with
  no version increment or audit. Changes retain underlying relation audit and add one transition
  event with old/new target and relation identities, including attribute-only changes.

WP-9 verifies generic-write/mapping races, both directional sets, independent bindings and draft
activation versus live same-set changes. Confirmed missing foundation capabilities trigger a bounded
WP-10 slice and block acceptance; they do not retroactively change WP-3 scope.
