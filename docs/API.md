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

## Query parameters

Every route accepts only the query parameters it documents. Any other, a misspelt `pagesize` for
example, is `422 UNKNOWN_PARAMETER` naming each in `details.parameters` (and the first in
`details.path`, `/query/<name>`), so a client never silently gets another answer than it asked for
(decided 2026-10-02, H4c D-3). The per-type object list and the cross-type lookup also take the
`filter.<field>.<operator>` family.

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
the same filters. Combining two selectors returns `422 CONFLICTING_PAGE_PARAMETERS` with the
parameters in `details.parameters`; a negative `position` is `422 REQUEST_VALIDATION_ERROR`.

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
with another sort, filter or context returns `422 INVALID_CURSOR`. Cursors issued before 0.8 continue
forward as before, except those of a changed default order (S4R4): object lists without `sort` and
mapping coverage and candidates now list by name, so their earlier cursors are refused with
`422 INVALID_CURSOR`; reload the list from its first page.

`seek` takes the lexical form of the sorted field (ISO 8601 for dates, `true`/`false` for booleans)
and applies to the sort in effect, which is the name when a list is not sorted; rows without a
value, which sort last, follow the seeked rows. A seek value that does not parse returns
`422 INVALID_SEEK`.

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
- `GET /api/v1/model/consumer-apis/{consumerApi}`

URL paths use stable model keys. Every response body includes the entity `id` (UUID) alongside the
`key`. Internal metadata sequence IDs are never part of the contract.

An application of a schema 0.10 model may carry `navigation` (`groups`, each with `key`, `label`,
`collections` and `collapsed`), served by `GET /model` and the application routes as written, and
left out when the model declares none (0.10 N1, [APPLICATION_MODEL](APPLICATION_MODEL.md#navigation-groups-navigation-schema-010)).
It is presentation only: no route reads or filters by it.

Relation types and object-type relations are separate resources. A **relation type** defines reusable
forward/reverse semantics and orientation. An **object-type relation** binds one relation type to an
allowed source and target object type and supplies cardinality (`one-to-one`, `one-to-many`,
`many-to-one` or `many-to-many`; [APPLICATION_MODEL](APPLICATION_MODEL.md#relation-types) says which end
each limits), required status, attributes and binding features. Relation-type responses include these bindings under `allowedPairs`; the flat
`object-type-relations` endpoint remains available for discovery and compatibility and can be
filtered with `fromObjectType` and `toObjectType` query parameters.

**A consumer API definition expanded (Base 0.9 C18).** `GET /api/v1/model/consumer-apis/{consumerApi}`
answers one definition of the context's model (the same context parameters and `ETag` as
`GET /model`) in schema 0.9 with every default written out (CONSUMER_API C-D137): `exposes` and a
public name for every exposed type, each operation offered, the events `perType` makes written out
under `custom` (with `perType: false`), every rule of `matchOn` (`field: "code"` written as the
code field's sources), each filter with its verb and `matchOn`, each list's `within.types`, every
field written out with `from` as a list. A schema 0.8 release's definitions read the same way.
Expanding the answer gives the same definition. An unknown `consumerApi` is
`404 CONSUMER_API_NOT_FOUND` (`details.consumerApi`). The UI's Webhooks page reads events, filters
and public names from it, never from the model document.

```json
{
  "key": "rdm", "name": "RDM API", "contractVersion": 1,
  "exposes": ["domain", "codelist", "master-value"],
  "publicNames": { "domain": "Domain", "codelist": "Codelist", "master-value": "CodelistValue" },
  "object": { "fields": { "id": { "role": "id", "from": ["id"] }, "…": "…" }, "parent": { "output": "parent", "fields": ["objectType", "id", "code", "name"] }, "path": "path", "related": { "…": "…" } },
  "operations": {
    "objects": {}, "xref": { "matchOn": ["…"], "alsoMatchThrough": ["…"] }, "resolve": {},
    "lists": { "codelists": { "of": "codelist", "within": { "filter": "domain", "types": ["domain"] } } },
    "events": { "perType": false, "custom": [{ "key": "values-changed", "…": "…" }] }
  },
  "filters": { "domain": { "under": ["domain"], "matchOn": ["id", "domain-code", "name"] } }
}
```

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
  },
  "integrationJobs": {
    "createJobs": true,
    "runModes": ["inline"],
    "limits": { "batchMaxItems": 1000, "batchMaxBytes": 5242880, "atomicJobMaxItems": 10000, "previewMaxItems": 10000, "retentionDays": 7 },
    "setting": "INTEGRATION_JOBS_ENABLED"
  },
  "changeFeed": { "retentionDays": 30 },
  "consumerApi": { "resolveMaxItems": 1000, "setting": "CONSUMER_RESOLVE_MAX_ITEMS" },
  "consumerSubscriptions": {
    "manageSubscriptions": false,
    "delivery": {
      "maxEventsPerBatch": 1000, "maxBytes": 1048576, "timeoutSeconds": 10.0,
      "retryWaitsSeconds": [10, 30, 60, 120, 300, 600, 1800], "laterWaitSeconds": 3600,
      "retryHours": 24
    },
    "setting": "CONSUMER_SUBSCRIPTIONS_ENABLED"
  }
}
```

`changeFeed.retentionDays` is `FEED_RETENTION_DAYS`: how long the [change feed](#change-feed-base-09-f1-f2)
answers a position. `consumerApi.resolveMaxItems` is the most items one consumer
[batch resolve](#batch-resolve) holds, named in `setting`. `consumerSubscriptions.manageSubscriptions`
says whether the [subscriptions API](#consumer-subscriptions-base-09-c11) is served
(`CONSUMER_SUBSCRIPTIONS_ENABLED`) and its subscriptions delivered, and `delivery` how
[webhooks are delivered](#webhook-delivery-base-09-c12): the events and bytes one request holds, the
receiver's timeout, and the retry waits and window. These are constants, not settings.

Each group names in `setting` the deployment setting that enables its mutations, so a client can tell
an operator what to change without knowing the server's configuration names.

`readReleases` remains true when mutations are disabled. `manageDrafts` and `install` are true only
when `MODEL_ADMIN_MUTATIONS_ENABLED=true`; `activate` follows the same gate. The flag is a deployment
guard, not an authorization mechanism. Mutation enablement requires a single process; startup rejects
`WEB_CONCURRENCY` values greater than one until cross-process release propagation exists.
`workspaceAdmin.manageWorkspaces` follows `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, which defaults to true
until authentication exists. It is a deployment capability and not evidence of caller authorization.

#### What the deployment runs (`GET /api/v1/system`)

Read-only and behind no capability, like `/capabilities` (for administrators once roles exist,
0.12). It answers what the deployment runs and how it is configured, read on one session:

```json
{
  "engine": { "version": "0.9.0", "managementApi": "v1" },
  "schemaLanguages": ["0.5", "0.6", "0.7", "0.8", "0.9", "0.10"],
  "activeModelRelease": {
    "id": "…", "key": "rdm-starter", "name": "RDM Starter Model", "version": "0.9.0",
    "schemaVersion": "0.8", "activatedAt": "2026-10-06T08:00:00Z"
  },
  "database": { "revision": "20261006_03" },
  "settings": [
    { "name": "FEED_RETENTION_DAYS", "group": "limits", "description": "Days the change feed and consumer events answer a position", "value": 14, "default": 30, "source": "environment" },
    { "name": "RDM_CURSOR_SIGNING_KEY", "group": "runtime", "description": "Signs pagination cursors; …", "value": null, "default": null, "source": "default" }
  ]
}
```

- `engine.version` is the product version, the same as the API document's `info.version`.
- `activeModelRelease.activatedAt` is the runtime state's `updatedAt`: when the release was activated
  or its schema upgraded.
- `database.revision` is the migration revision the database is at.
- `settings` lists every setting the engine reads, once, in the order and groups of
  [OPERATIONS § Settings](OPERATIONS.md#settings) (`runtime`, `capabilities`, `limits`, `webhooks`).
  `value` and `default` keep their types (integers, booleans, lists). `source` is `environment` when
  the variable is set to a non-empty value, otherwise `default`. Values are those the process read at
  startup; they change only with a restart.
- Secrets (`RDM_CURSOR_SIGNING_KEY`, `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`) report `value` and
  `default` as `null`; only `source` says whether they are set. `DATABASE_URL` is reported without its
  password (also a `password` query parameter), or `null` when it cannot be read as a URL.

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
MODEL_RELEASE_NOT_FOUND`:

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
filters. Changing a cursor or reusing it with different filters returns `422 INVALID_CURSOR`.

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
an unsupported schema, diff returns `422 UNSUPPORTED_SCHEMA_VERSION` with details identifying the
affected release. Missing releases return `404 MODEL_RELEASE_NOT_FOUND`.

**Consumer API contracts (Base 0.9 C1).** Diff and draft compile also return `consumerContracts`:
the candidate's consumer API definitions (`consumerApis`) checked against the **active**
release's, which is what consumers read (CONSUMER_API C-D17):

```json
"consumerContracts": {
  "classification": "version_required",
  "activeReleaseId": "412c4041-...",
  "diagnostics": [
    {
      "severity": "error",
      "code": "CONSUMER_CONTRACT_VERSION_REQUIRED",
      "path": "/consumerApis/rdm/object",
      "message": "Consumer API 'rdm' removes output field 'sortOrder'; raise contractVersion above 1 to release it"
    }
  ]
}
```

`classification` is `compatible` or `version_required`. A definition that keeps its
`contractVersion` must not remove or retype an output field (a parent field included), rename or stop
exposing a type, remove a related block or change its shape or fields, change scoring weights, remove
or change a list or a filter's verb, or stop offering an operation (C-D2, C-D4, C-D18, C-D132); each
such change is an error at the part of the definition the author wrote (C-D141). Weights compare only
while both releases offer XREF, so offering it again is an addition. A lower `contractVersion` than the active one is
`CONSUMER_CONTRACT_VERSION_DECREASED`. Additions are compatible, and a raised `contractVersion`
releases any change. A definition the candidate no longer declares is a `CONSUMER_API_REMOVED`
warning and does not change the classification.

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
MODEL_REGISTRY_REFRESH_FAILED`; `/health` then reports `503` and model-dependent requests are refused
rather than using a guessed snapshot (`503 MODEL_REGISTRY_UNAVAILABLE`). Restarting successfully
reloads the database-selected release. Historical releases using an unsupported schema return `422
UNSUPPORTED_SCHEMA_VERSION`; if a supported installed release fails reparsing, activation returns
`500 INVALID_INSTALLED_MODEL`. Both failures leave runtime state unchanged.

Activation and live writes exclude each other (Base 0.8 W5). Activation locks the runtime-state row
for update before its compatibility check, so the check sees every live write that committed before
the switch. A request that resolved the active release — a live object, attribute,
relation or mapping write, a deletion, a publish or a change-set creation — rereads the active release
inside its own transaction before committing. If another release was activated after the request
resolved its model, nothing is saved and it returns `409 MODEL_RELEASE_CHANGED` with
`details.resolvedReleaseId` and `details.activeReleaseId`; the client reloads the model and retries.
A write about to commit waits for an activation in progress, and an activation waits for writes
already checking their release (0.9.0-alpha.1: row locks; `model_activation_retry` is no longer
returned).

#### Drafts, validation, compilation and installation

- `GET /api/v1/model-drafts?pageSize=...&cursor=...`
- `GET /api/v1/model-drafts/{draftId}`
- `POST /api/v1/model-drafts`
- `PATCH /api/v1/model-drafts/{draftId}`
- `DELETE /api/v1/model-drafts/{draftId}?expectedVersion=...`
- `POST /api/v1/model-validations`
- `POST /api/v1/model-drafts/{draftId}/compile`
- `POST /api/v1/model-drafts/{draftId}/installation`
- `POST /api/v1/model-drafts/{draftId}/operations`, `GET /api/v1/model-drafts/{draftId}/operations`,
  `POST /api/v1/model-drafts/{draftId}/undo`, `POST /api/v1/model-drafts/{draftId}/redo` (0.10 A2,
  [below](#draft-operations))

Create accepts `name`, optional `baseReleaseId` and an inline `model`. Patch accepts
`expectedVersion` plus at least one of `name` or `model`; a `model` is recorded in the draft's
history as one `replaceModel` step of origin `patch` (0.10 A2, ADR-041). Draft responses use:

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
back unchanged; malformed or cross-endpoint reuse returns `422 INVALID_CURSOR`.

Delete succeeds with HTTP `204` and no body. Inline validation accepts `{ "model": {} }` and returns:

```json
{
  "valid": false,
  "diagnostics": [
    {
      "severity": "error",
      "code": "UNKNOWN_OBJECT_TYPE",
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
  },
  "consumerContracts": {
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
`modelHash`, and uses `invalid`. `consumerContracts` (above, under diff) is present when the draft
is valid. Installation repeats compilation and compatibility analysis and
returns the installed release detail with `model` absent. A newly installed release returns HTTP
`201`; an idempotent retry for identical content returns HTTP `200`. Installation never activates the
release. Installations are serialized inside the supported single API process so concurrent drafts
with identical content resolve to the same immutable release rather than racing the uniqueness
constraints.

Every draft endpoint and the installation and activation endpoints return HTTP `404` when model
administration mutations are disabled. Validation, capabilities, installed-release reads and diff
are not mutation-gated. Lifecycle errors use:

- `404 MODEL_DRAFT_NOT_FOUND` for an unknown draft ID;
- `404 MODEL_RELEASE_NOT_FOUND` for an unknown draft base, release, activation candidate or diff
  participant;
- `409 VERSION_CONFLICT` for a stale draft version;
- `409 RELEASE_IDENTITY_CONFLICT` for the same release key/version with different content;
- `422 INVALID_MODEL` when installation recompilation fails, also for a schema 0.8 document that
  declares `consumerApis`, whose diagnostic is `UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`
  naming schema 0.9; draft compile and `POST /model-validations` report the same diagnostic with
  `valid: false` (Base 0.9 C18, CONSUMER_API C-D134), and startup refuses such a file named by
  `RDM_MODEL_PATH`. A stored 0.8 release still activates and reads;
- `422 UNSUPPORTED_SCHEMA_VERSION` when diff, compilation or activation involves a release whose schema
  is not supported by the runtime (details include `releaseId`, `schemaVersion`,
  `supportedSchemaVersions` and `operation`; the schema value comes from the stored model document
  when compilation detects a metadata/document mismatch);
- `409 ACTIVATION_CONFLICT` for stale runtime-state tokens;
- `409 MODEL_MIGRATION_REQUIRED` when stored data prevents activation;
- `409 CONSUMER_CONTRACT_VERSION_REQUIRED` when a consumer API definition changes what the active
  release's consumers read without a higher `contractVersion` (details are the `consumerContracts`
  errors); the selection is unchanged (Base 0.9 C1);
- `500 INVALID_INSTALLED_MODEL` when persisted release JSON with a supported schema cannot be reparsed
  for diff or activation (distinguished from unsupported schema, which returns 422);
- `503 MODEL_RUNTIME_STATE_UNAVAILABLE` when no authoritative active selection can be read;
- `503 MODEL_REGISTRY_REFRESH_FAILED` when activation committed but the process could not publish the
  new selection; and
- `503 MODEL_REGISTRY_UNAVAILABLE` while a process has marked its request registry unhealthy.

As elsewhere, errors use the shared `{ "error": { "code", "message", "details" } }` envelope.

### API reference page (Base 0.9 V1, V2)

`GET /docs` serves the API reference, rendered by [Scalar](https://github.com/scalar/scalar) (MIT)
from the OpenAPI documents: the management API (`/openapi.json`) is its first source, followed by
each consumer API of the active release (0.9 V2), in `consumerApi` order, labelled
`{name} · v{contractVersion}` and read from the document the [API index](#api-index-and-documents) names.
The sources are built per request, so a release that adds, removes or re-versions a consumer API shows
on the next page load. A link opens a source with `?api=<slug>`: `management`, or
`consumer-{consumerApi}-v{contractVersion}` for a consumer API (the Settings › API reference page
links each this way). Swagger UI and ReDoc are gone:
`/redoc` and `/docs/oauth2-redirect` answer `404`.

The Scalar standalone script is pinned (1.72.2) and bundled with the engine, served at
`/docs/scalar/standalone.js`, so the page works without internet access. Set
`RDM_API_REFERENCE_SCRIPT=cdn` to load the same version from jsDelivr instead; the script tag carries
the bundled file's integrity hash, so the browser refuses any other bytes. The default is `bundled`,
and any other value stops startup with a message naming the setting. The page turns off Scalar's web
fonts, telemetry, hosted agent, MCP generator, developer toolbar and hosted-client link, so nothing it
loads leaves the engine. Its "try it" console sends requests to the engine that served the page,
unauthenticated like the management API until 0.12.

Neither route is in the OpenAPI document, so the page does not affect the [OpenAPI lock](#openapi-lock).

### OpenAPI lock

The complete canonical default OpenAPI document digest for the current implementation, plus readable
path/method and component-schema inventories, are asserted by
`backend/tests/test_openapi_contract.py`. Separate enabled-mode inventories assert the optional model
and workspace administration surfaces. Any public shape change therefore requires an intentional
contract-test update.

Every operation also documents the shared `ApiErrorResponse` envelope as its default error response.
The generated contract includes representative `INVALID_CURSOR`, `VERSION_CONFLICT` and
`REQUEST_VALIDATION_ERROR` examples; concrete status codes and endpoint-specific codes remain as
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
`WORKSPACE_NOT_FOUND`; retired scopes remain readable but all object, attribute and relation writes
return `WORKSPACE_RETIRED`.

**Deleting a workspace** ([ADR-019 amendment](DECISIONS.md#adr-019--persist-and-retire-globally-scoped-workspaces))
corrects a mistyped key. `DELETE /workspaces/{workspaceKey}?expectedVersion=N` returns `204` when the
workspace is not the default, was never published and has no objects and no change sets; active and
retired workspaces follow the same rule, and the key can be created again. Refusals are checked in
this order in one transaction and change nothing:

| Status | Code | When |
|---|---|---|
| 404 | `WORKSPACE_NOT_FOUND` | the key does not exist |
| 409 | `WORKSPACE_IS_DEFAULT` | it is the current default |
| 409 | `WORKSPACE_HAS_PUBLICATIONS` | it has ever been published (withdrawn publications count); retire it instead |
| 409 | `WORKSPACE_NOT_EMPTY` | it has objects or change sets; `details` carries `objectCount` and `changeSetCount` |
| 409 | `WORKSPACE_HAS_SUBSCRIPTIONS` | it has [webhook subscriptions](#consumer-subscriptions-base-09-c11); delete them first, or retire it |
| 409 | `VERSION_CONFLICT` | `expectedVersion` is stale; `details.currentVersion` |

Single-workspace responses (`GET`, `POST` and `PATCH /workspaces/{workspaceKey}`) add `deletable` and,
when it is false, `deleteBlockedBy`: `default`, `published`, `notEmpty` or `subscribed`, in the
refusal order above. Retiring a workspace suspends its subscriptions (`WORKSPACE_RETIRED`).
The paged list omits both. A live write that resolved a workspace before it was deleted or retired is
refused when it commits (`404 WORKSPACE_NOT_FOUND` or `409 WORKSPACE_RETIRED`), and nothing is saved.

Create/update/delete/default-switch routes are absent when `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false`.
The flag gates only this catalogue administration: the change-set and publication routes below are
always registered and return `WORKSPACE_RETIRED` in a retired workspace.
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
  and DELETE claim `expectedVersion`. An unknown ID returns `404 CHANGE_SET_NOT_FOUND`.
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
  selecting the current pin is a no-op. Stale claims return `409 CHANGE_SET_VERSION_CONFLICT`.
  Declared attribute type changes for stored effective object/relation values require conversion,
  even if a target normalizer could accept the old value. Populated containment also retains its
  source model semantics; changing those requires conversion. Missing required fields are not
  defaulted during compatibility checks. Incompatible content returns
  `409 CHANGE_SET_CONTENT_INCOMPATIBLE` with `details.diagnostics` (at most 20), `diagnosticCount` and
  `diagnosticsTruncated`; refusal leaves content, pin and version unchanged. Uniqueness conflict ID
  previews are also bounded to 20 with exact count/truncation metadata. No conversion is performed.
  Missing, unsupported and invalid targets use `PINNED_MODEL_UNAVAILABLE`,
  `UNSUPPORTED_PINNED_MODEL_SCHEMA` and `PINNED_MODEL_INVALID` respectively.
- `/model` and model metadata reads accept `changeSetId` or `publicationId` and resolve that context's
  installed model. Metadata cursors are bound to the release identity. Change-set record reads, writes
  and graph validation use the change set's pin even when it differs from active; agreement with the
  active release is a separate requirement for publishing. Discard does not require model agreement.
- `POST /api/v1/change-sets/{changeSetId}/validation` validates the complete effective graph without
  publishing. It answers `200` with `{ "valid": true|false, "diagnostics": [...] }`: an invalid graph
  is `valid: false` with a diagnostic per problem, naming the records, not an error response. `POST /api/v1/change-sets/{changeSetId}/publication` publishes it and requires
  `expectedChangeSetVersion` and nullable `expectedActivePublicationId`. Stored read-only values,
  including model defaults, are valid publication content and are checked for their declared types and
  constraints; ordinary writes and attribute deletion still enforce the binding's read-only
  restriction.
- `GET /api/v1/change-sets/{changeSetId}/object-changes` and
  `GET /api/v1/change-sets/{changeSetId}/relation-changes` (Base 0.8 P2a) list only what the change set
  changes, one entry per record or relation it touched, read against its **source** (its current-live
  base or publication; nothing for an empty root). They are read-only entries about records, not a
  record dialect. Each entry has a `kind` (D31): `added` (no source row), `changed` (a source row) or
  `removed` (deleted, with a source row). A record created and deleted inside the change set is left
  out, as publishing skips it. `before` is the record as the source holds it and `after` as the change
  set does; each is `null` where the kind has none. *Before* is not current live: whether live moved
  since is what validation and publishing report (`VERSION_CONFLICT`).
  - An object entry carries `kind`, `objectId`, `objectTypeKey`, `applicationKey`, `before`/`after`
    (`objectTypeKey`, `name`, `parentObjectId`, typed `attributes` in the object read's shape,
    `version`), `changedFields` and `path`: where the change set puts an added or changed record, or
    where the source held a removed one. `changedFields` names what differs between the sides
    (`objectType` when a type change made them differ, Base 0.8 C1; then `name`, `parent`, then
    attribute keys in binding order); a missing side holds nothing, so an added or
    removed record names every field it holds. A `changed` entry can name none — edited back to its
    source values — and is still listed: its version advanced and publishing claims it against live.
    A move is `changed` with `parent`, and carries `beforePath`: where the source held the record
    (root first, ending with the record); `beforePath` is `null` on every other entry (Base 0.8 P2b).
  - A relation entry carries `kind`, `relationId`, `relationTypeKey`, `containment`, `fromObject` and
    `toObject` (`objectId`, `objectTypeKey`, `name`: as the change set holds the record, or the source
    for a removed end), `before`/`after` (`attributes`, `version`) and `changedFields` (attribute
    keys). `containment` marks an engine-maintained parent edge: its type is one of the `to` end
    type's `parentRelationTypeKeys` under the change set's model. The lists include these edges so an
    integration sees every row that publishes (D32); a move lists one removed and one added edge.
  - Filters: repeatable `kind`; repeatable `objectTypeKey` on objects; repeatable `relationTypeKey` and
    `containment` (`true` only parent edges, `false` none; both when omitted) on relations. A type key
    not in the change set's model returns `422 UNKNOWN_OBJECT_TYPE` or `422 UNKNOWN_RELATION_TYPE`
    with `details.path` and `details.key`; an unknown kind is a request validation error. There is no
    search.
  - Objects list by (`objectTypeKey`, name, `objectId`), the change set's name (a removed record keeps
    its name); relations by (`relationTypeKey`, `relationId`). Both page as every collection does
    ([Collection paging](#collection-paging)), `pageSize` 1–500 (default 100); cursors are bound to
    the change set and filters. An unknown change set returns `404 CHANGE_SET_NOT_FOUND`. There is no
    publication context: what a publication changed against its predecessor is the 0.9 change feed.
- `GET /api/v1/workspaces/{workspaceKey}/publications` and `GET /api/v1/publications/{publicationId}`
  list and read publications. A publication carries `publicationNumber`, its `status` (`active` while
  it is the workspace's current publication, otherwise `withdrawn`), `publishedAt`, `withdrawnAt`,
  `derivedFromPublicationId`, `supersedesPublicationId` and its `modelReleaseId`, `modelReleaseKey`
  and `modelReleaseVersion`, so a client can show "Publication 12 · model 0.8.0 · 3 Sep 2026".
  `feedPosition` is the position of its `published` entry in the
  [change feed](#change-feed-base-09-f1-f2): live data at that position is the publication, so a feed
  reader re-reads it and follows on from there. It is `null` for a publication made before the feed
  existed.
  `publicationNumber` is a per-workspace counter that never restarts, not a version. The list is
  newest first by publication number with the public UUID as a unique descending tie-breaker. Its
  cursor is bound to the workspace and descending sort; an ascending, malformed or differently scoped
  cursor returns `422 INVALID_CURSOR` with `Publication cursor is invalid`. Pages contain 1–500 items
  and exact retry is deterministic. An unknown ID returns `404 PUBLICATION_NOT_FOUND`.
- `POST /api/v1/publications/{publicationId}/withdrawal` withdraws the workspace's current
  publication: its status becomes `withdrawn` and the workspace no longer has a current publication.
  The path ID is the concurrency claim, so a publication that is no longer current returns
  `409 WORKSPACE_ACTIVE_PUBLICATION_CONFLICT`. It retains the live records and every publication; it
  does not retire the workspace or change any individual record. A retired workspace refuses it with
  `409 WORKSPACE_RETIRED`.

A publication snapshots one graph: objects, typed attributes, containment (both parent projection
and typed edge), required ownership relations and independent relations. Stable object and relation
UUIDs remain integration identities but have no lifecycle state. Change sets pin `modelReleaseId`;
publications record the `modelReleaseId` they were published under. Publishing against another
resolved model returns `409 CHANGE_SET_MODEL_RELEASE_CONFLICT` and never rebases implicitly.
Publishing delta-merges the change set onto the current live content and snapshots the merged graph,
so a change set started from an earlier publication preserves newer live records it never touched
(ADR-026). Conflicts are `CHANGE_SET_VERSION_CONFLICT`, `WORKSPACE_ACTIVE_PUBLICATION_CONFLICT`,
`CHANGE_SET_MODEL_RELEASE_CONFLICT`, and `VERSION_CONFLICT` — publishing reports every per-record merge
divergence under `409 VERSION_CONFLICT` with `details.conflicts` (`kind`, `id`, `code`
`VERSION_MISMATCH`/`ID_COLLISION`/`DUPLICATE_EDGE`, expected/actual version) — plus
`422 WORKSPACE_GRAPH_INVALID` when the merged graph fails whole-graph validation. Publishing also
compares complete source/live relation identities and versions for exact directional mutable binding
sets touched by the change set. A divergent set adds a diagnostic with `kind: "mapping-set"`,
`code: "MAPPING_SET_CHANGED"`, `id`/`anchorObjectId`, physical binding type keys, `direction`,
expected/actual target counts and a recovery message. At most 20 mapping-set diagnostics are
returned; `details.mappingSetConflictCount` gives the exact total and
`details.mappingSetConflictsTruncated` indicates omitted mapping-set diagnostics. No graph is applied,
no publication is created, and the change set remains available. Review current live mappings and
reapply intended changes in a new current-live change set before publishing; validating the unchanged
conflicting change set does not resolve the conflict. Containment/ownership use their existing merge
rules. Identical source/live edge identities and surviving edge versions count as the same graph, even
if an intervening addition was later removed. Change-set and publication collection cursors bind
their selected context identity and query filters; malformed/mismatched tokens return
`422 INVALID_CURSOR`. Live collection cursors bind the effective live workspace and query filters.
Cursor tokens do not bind a model or publication ID unless that context is itself selected.

Current-live capture reads the graph from one database snapshot (REPEATABLE READ), so live writes
committing meanwhile are not mixed into it, and holds share locks on the workspace and runtime-state
rows, so neither a retirement nor a model activation commits while it runs. It compares the request's
captured active release with `model_runtime_state`, separately from the selected change-set pin. A
changed active selection, or a workspace or runtime-state row changed after the snapshot began,
returns `409 CHANGE_SET_SNAPSHOT_RETRY` with an actionable retry message and saves nothing
(0.9.0-alpha.1; `change_set_snapshot_unsupported` is no longer returned). The private base is deleted
with its change set on discard or publish and is never a publication or part of publication lineage.

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
`{"error":{"code":"WORKSPACE_CONTEXT_MISMATCH","message":"workspaceKey does not match the selected context","details":{"workspaceKey":"...","contextWorkspaceKey":"..."}}}`.
A missing pinned release is `409` with code `PINNED_MODEL_UNAVAILABLE`; an invalid pinned document is
`409` with `PINNED_MODEL_INVALID` and its diagnostics; and an unsupported schema is `409` with
`UNSUPPORTED_PINNED_MODEL_SCHEMA`, including `modelReleaseId`, `schemaVersion`, and
`supportedSchemaVersions: ["0.5", "0.6"]` in details.
>
> **Target — product 0.11 historical model migration.** Preview incompatibilities and potential data
> loss for one workspace and a named installed target release (normally the pin of a change set started from a publication),
> then confirm the exact reviewed plan or cancel. Confirmed execution migrates live data to that target and changes
> only the selected workspace model assignment atomically. Model drafts and change sets remain separate;
> target validity, conflict checks and parser support still apply. Nothing today overrides them.
>
> **Product 0.7 change-set version selection (ADR-028; backend delivered in WP-6).** A change set may be created against,
> or explicitly moved onto, any installed release the deployment supports, so one change set prepares a
> candidate release while another continues on the release serving live data. The target must be
> installed, parseable and supported; refusal reuses the existing pinned-model envelope
> (`PINNED_MODEL_UNAVAILABLE`, `PINNED_MODEL_INVALID`, `UNSUPPORTED_PINNED_MODEL_SCHEMA`) rather than
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
> `409 CHANGE_SET_CONTENT_INCOMPATIBLE` with bounded diagnostics; creation leaves no change set or base, and failed
> changes leave content, pin and version unchanged. Version change atomically claims the expected change-set
> version, validates and updates the pin, increments its version and audits old/new release identities.
> The capture's active release/runtime token is separate from the chosen change-set pin.
> Creation from a publication retains its source pin; another selection is a subsequent explicit change.
> WP-7 will reload model-dependent browser navigation, forms, lookups and caches, reset obsolete
> cursors and protect dirty input on local or externally detected pin changes.
>
> **Target — product 0.11 moving a change set onto an incompatible release (ADR-028).** Moving a change set onto
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
- `GET /api/v1/objects` — list objects of any type ([cross-type lookup](#cross-type-lookup-base-09-q1))
- `POST /api/v1/objects` — create an object
- `GET /api/v1/objects/{objectTypeKey}/{objectId}?changeSetId={id}|publicationId={id}` — get one object from a change set or a publication; omit both for the live active projection
- `PATCH /api/v1/objects/{objectTypeKey}/{objectId}` — update an object
- `DELETE /api/v1/objects/{objectTypeKey}/{objectId}` — delete an object

Object collections accept the [collection paging](#collection-paging) parameters (including `seek`),
`pageSize`, `applicationKey`, `workspaceKey`, optional
`changeSetId` or `publicationId`, `parentObjectId` or `topLevel`, `search`, one `sort` and typed filters named
`filter.<field>.<operator>=<value>`. Filters take built-in fields and attributes with the
`filterable` feature. `asOf=YYYY-MM-DD` keeps the records effective on a date, on a type that
declares an [effective period](#effective-periods-and-asof-base-09-q4). `sort` takes `name`, `id`, `objectType` (ordered by the type's model name, then
by name), live `createdAt`/`updatedAt`, or any attribute the type binds, flagged `sortable` or not
(S4R3 revision). JSON attributes are excluded from both. Prefix a sort with
`-` for descending order. Null and unset attribute values sort last in either direction, and every
live ordering uses the internal sequence as a non-public final tie-breaker; change sets and publications record
no creation sequence, so there the record ID is the final tie-breaker. Omitting `sort` orders by name
in every context (S4R4); before 0.8 it listed live records in creation order and change-set and publication
records by ID. Page size defaults to 100 and has a documented
maximum of 500. `nextCursor` is null only when that traversal is complete.

**Relation columns (Base 0.9 K5, D140–D145).** `expand=<key>` (repeatable) adds to each
item the records at the other end of one relationship: `<key>` is a relation type's `key` (the
type's outgoing relationships) or `reverseKey` (its incoming ones), which share one namespace, and
the type must have a binding of it at that end. Each item then carries `expanded`, one entry per
`expand` in the request's order, in the shape of the [model-aware query](#model-aware-query-base-09-q3)'s
expansions: `relationTypeKey`, `direction`, `count` (how many related records the item has), `items`
(the first `expandLimit`, 1–20, default 3, in name order, each `{relationId, object: {id,
objectTypeKey, version, fields: {name}}}`) and `nextCursor`, which continues on `GET /relations` with
the item as `objectId`, or is null when `items` holds them all. Without `expand` the items are as
before and carry no `expanded`. An unknown key, a key the type has no binding of, or the same key
twice are `422 INVALID_EXPAND` with `details.parameter` `expand` and the `value`. There is no fixed
number of keys: the type's relationships bound them, and the page size and `expandLimit` bound the
response (D142, revised in 0.9 K6a).
Every context reads its own relationships; `asOf` dates the listed records, not the related ones.
`expand=<key>.<field>` (Base 0.9 K5a, D148, D150) also reads a field of each related record, written
as in a consumer API definition: `name`, an attribute one of the types at the other end binds, or
`ancestor:<type>.<field>` (`name` or an attribute of that ancestor, the one nearest the root). The
entry then names it in `field`, and each record's `fields` holds its value beside `name`, typed as
stored, `null` where the record has none; the records keep their name order. A key may contain a
dot, so the text resolves as the whole key when it is one, otherwise as the longest key it starts
with. A field that does not resolve, or holds JSON, is `INVALID_EXPAND`; a sort by such a column is
`INVALID_SORT` (D151).
A page of 100 with two keys took 45 ms live, 31 ms in a change set and 21 ms in a publication on the
0.1 volume fixture: one statement per key for the whole page.

**Relationship filters (Base 0.9 K6, D153–D158).** `filter.related:<key>.eq=<record ID>`
(repeatable) keeps the records related, through the relationship `<key>` names, to any of those
records; `filter.related:<key>.isNull=true` those related to none, `=false` those related to any. Any
relationship the type has a binding of may be named, whatever a view offers; several relationships
combine with AND, and with the search and the other filters. An ID no record has matches nothing.
Totals, positions and cursors hold, and a cursor binds the filter. Another operator, an unknown key,
a key the type has no binding of or a field form (`related:<key>.<field>`) is `422 INVALID_FILTER`.
The condition is the [model-aware query](#model-aware-query-base-09-q3)'s `related` hop, so the list
and the query, and an export with that criterion, select the same records in every context. On the
0.1 volume fixture a 100-row page with its total took 11–26 ms live and in a publication and 32–54 ms
in a change set.

**The records a relationship may choose (Base 0.9 K7, D168–D177).** A model may limit, per
relationship binding and end, which records may be chosen there (the binding's `candidates`,
[APPLICATION_MODEL](APPLICATION_MODEL.md#which-records-a-relationship-may-choose-schema-09-base-09-k7)).
`candidateFor=<key>&anchorTypeKey=<type>` on `GET /objects/{objectTypeKey}` lists the records a
record of `anchorTypeKey` may choose through `<key>`, a relation key (the anchor at the `from` end)
or reverse key (at the `to` end): the path type's records that meet the criteria the binding sets at
their end, in live data, a change set or a publication, with the search, filters, sort and paging
unchanged; every record when the end sets none. The two come together; a key the anchor's type has
no binding of, or one whose other end is not the path type, is `422 INVALID_FILTER` with
`details.path` `/query/candidateFor`. The relationship view's `mapping-candidates` and the relation
matrix's `link-candidates` apply their binding's criteria without a parameter.

```http
GET /api/v1/objects/permit?candidateFor=ledger-reserves-permit&anchorTypeKey=ledger&search=west
```

A new relationship whose end does not meet that end's criteria is refused on every write path, live
and in a change set: `POST /relations`, a new record's `initialRelations`, a set replacement's
added records, and batch and import items (`createRelation`, `ensureRelation`,
`replaceRelationSet`): `422 RELATION_CANDIDATE_REFUSED` with `details` `relationTypeKey`, `end`
(`from` or `to`), `objectId` and `criteria`, the JSON pointer of the criteria in the model. Only
relationships a write adds are checked: one a record already holds is kept when the data changes so
it no longer meets the criteria, an `ensureRelation` finding it answers `unchanged`, and a set
replacement may keep it (D175).

`sort=related:<key>` (or `-related:<key>`) orders by the related record's name where the key is
single-valued for the type: exactly one binding stands behind it and the type's end of it holds at
most one relationship (`one-to-one`, `one-to-many` read from `to`, `many-to-one` read from `from`).
Records without one sort last in both directions, as with an attribute, and every paging mode
works over it. A key a record can hold several of is `422 INVALID_SORT`. 10,000 records sorted by
it: 95 ms live, 39 ms in a change set, 31 ms in a publication (0.1 volume fixture).

`topLevel=true` (Base 0.8 S4) lists only records without a parent, so a tree can page a root type
without loading its descendants; it holds in change-set and publication contexts too. It cannot be combined
with `parentObjectId` (`422 MUTUALLY_EXCLUSIVE_SCOPE`). A branch whose children have several types
pages each child type separately with `parentObjectId`, or reads them together through the
[cross-type lookup](#cross-type-lookup-base-09-q1) over built-in fields.

Search, typed filters and sort mean the same in live, change-set and publication contexts (Base 0.8 S2): the
same query over the same data returns the same records in the same order, apart from the order of
records that tie on the sort. `search` matches the record name and model attributes with the
`searchable` feature, case-insensitively, in every context. A change-set or publication page costs its own
rows, not the size of the change set or publication.

`search` is a literal substring: `%`, `_` and quotes match themselves. Case folding is Unicode's,
under the database's ICU root collation (0.9.0-alpha.1, PG-D11), so `ü` matches `Ü`; the search
index does not change it.
A search of three or more characters reads its candidates from trigram indexes (`pg_trgm` GIN) over
record names and text values (Base 0.8 S8, D25; 0.9.0-alpha.1 PG-D7 and PG5): the per-type list first
reads the records whose name or searchable value contains the text, and when there are at most 1,000
it reads only those. A phrase in more records, or a one- or two-character search (no trigram to look
up), matches every record of the type instead; a value phrase in more than 10,000 values is matched
per record too, where reading the index would cost more than it saves. The indexes narrow which
records are read, never which match: every path returns the same records. Over 100,000 records
(PostgreSQL, PG5's closing measurement, [POSTGRESQL_BUDGETS](POSTGRESQL_BUDGETS.md)) a name or code
search with its total takes 12–23 ms in every context; a phrase in every record (a total of 100,000)
76 ms live, 104 ms in a publication and 211 ms in a change set, and a two-character one 52–54 ms and
154 ms in a change set. A first page, or a `position` page, that reaches the end of the list reports
its `totalCount` without a second count.

Change sets and publications record no timestamps. In a `changeSetId` or `publicationId` context,
object and relation responses return `createdAt` and `updatedAt` as `null`, and a filter or sort on
either field is refused with `422 INVALID_FILTER` or `INVALID_SORT` (“Created is not recorded in change sets
or publications”) instead of matching nothing. Live responses always carry both timestamps.

Text filters support `eq`, `contains`, `startsWith` and `isNull`; number, date and datetime filters
support `eq`, `lt`, `lte`, `gt`, `gte` and `isNull`; booleans support `eq` and `isNull`. Attribute
fields also support `isUnset`. `isNull` and `isUnset` take `true` or `false`; boolean values use the
same lexical form, while dates and datetimes use ISO 8601; a datetime filter also takes a date
(`YYYY-MM-DD`), compared by that whole day in UTC: `eq` within the day, `lt` before it, `lte` up to
its end, `gt` after it, `gte` from its start (0.9 R-F6). Exact equality is case-sensitive and the
two text matching operators are case-insensitive. Different filters combine with AND; repeated `eq`
for one field combines with OR. Invalid grammar, capability, operator or typed input returns
`422 INVALID_FILTER` (or `INVALID_SORT`) with `details.path` identifying the query parameter.

Object cursors are signed opaque tokens. Live cursors bind object type, selected sort, effective live
workspace and every effective normalized filter; they do not bind a model or publication. Change-set and
publication cursors additionally bind their selected change-set or publication context. A malformed token, a
changed sort/filter/context or reuse for another collection returns `422 INVALID_CURSOR`. A live
publication switch alone does not invalidate the cursor. Live predicates use keyset
positions rather than offsets, so duplicate names and timestamps remain deterministic and inserts do
not cause already traversed rows to repeat merely by shifting offsets. Live changes to sort keys may
affect traversal; a live cursor is not a snapshot-consistent export.

Change-set context `DELETE` requires `changeSetId`, `expectedChangeSetVersion` and
`expectedVersion`; live `DELETE` requires only `expectedVersion`. Both accept optional `cascade`
(default `false`). A change set delete changes only the selected change set; live reads remain
unchanged until it is published. Without cascade,
an object that has no children or non-parent relations is deleted normally. If dependencies exist, the
request performs no deletion and returns `409 OBJECT_HAS_DEPENDANTS` with a structured impact report:

```json
{
  "error": {
    "code": "OBJECT_HAS_DEPENDANTS",
    "message": "Object has dependant records or relationships; repeat with cascade=true",
    "details": {
      "objectsToDelete": [
        {
          "id": "...",
          "name": "Delivery methods",
          "objectTypeKey": "codelist",
          "applicationKey": "rdm-master",
          "parentObjectId": "...",
          "reason": "child"
        }
      ],
      "objectsToRetire": [
        {
          "id": "...",
          "name": "Delivery methods",
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
DELETION_PREVIEW_CHANGED`: `The object was modified by another session. Please retry.` The client must
request and display a fresh preview. A missing token returns `409 DELETION_PREVIEW_REQUIRED`; a token
cannot be reused for another object, workspace, change set or model.

Deletion is always confined to one workspace. If inconsistent stored data contains a containment or
relationship edge into another workspace, the operation changes nothing and returns `409
WORKSPACE_GRAPH_INVALID` so the data can be repaired safely.

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

The token is the same a batch's delete item gives and takes for the record in the same context and
model (0.9 K2b, D120): a token from this refusal confirms a [batch delete
item](#deleting-with-what-depends-on-it-09-k2b), and one from a batch's preview confirms this
`DELETE`. The single delete and a batch's delete items run through one deletion path, as set
statements whatever the impact's size (D123).

### Cross-type lookup (Base 0.9 Q1)

`GET /api/v1/objects` lists records of every object type in one collection, for a lookup by name,
ID, type, parent or timestamps when the record's type is not known. It takes the object list's
context (`workspaceKey`, or `changeSetId` or `publicationId`, exclusive), [paging](#collection-paging)
(including `seek`) and `pageSize` (default 100, maximum 500), and:

- `objectTypeKey`, repeatable, narrows to those types; every type when omitted. An unknown type is
  `404 UNKNOWN_OBJECT_TYPE`. `applicationKey` narrows to the application's records, and a named type
  outside it is `422 INVALID_OBJECT_TYPE_FOR_APPLICATION`.
- `parentObjectId` or `topLevel` (not both, `422 MUTUALLY_EXCLUSIVE_SCOPE`).
- `search` matches the name only, case-insensitively, with the object list's literal-substring rules.
  Searchable attributes belong to their types; search them on the per-type list.
- `filter.<field>.<operator>` on built-in fields only: `id`, `name`, `objectTypeKey`,
  `parentObjectId` (text operators) and live `createdAt`, `updatedAt` (date-time operators).
- `sort` by `name` (default), `id`, `objectType` (the type's model name, then the name), and live
  `createdAt`, `updatedAt`; `-` for descending.

A model-declared field has a type only on its object type's list, so a filter or sort on one here is
refused with `422 INVALID_FILTER` or `INVALID_SORT`, whose message and `details.route` name
`GET /api/v1/objects/{objectTypeKey}`; `details.builtInFields` or `details.builtInSorts` lists what
this route takes. Timestamps in change-set and publication contexts are refused as on the per-type
list. `asOf` is refused as `422 AS_OF_NOT_SUPPORTED` with the same `details.route`: an
[effective period](#effective-periods-and-asof-base-09-q4) belongs to one type (D21).

Items have the per-type list's shape, `objectTypeKey`, attributes and `path` included: narrowed to one
type, the lookup returns the same items in the same order as `GET /objects/{objectTypeKey}` sorted by
name. The same query gives the same records in the same order in live data, a change set and a
publication. Cursors bind the context, the sorted set of named types and every filter, so repeating or
reordering `objectTypeKey` keeps a cursor valid; neither this route nor the per-type list accepts the
other's cursors.

Cost over the Track S fixture (258,000 live records of six types, a 261,000-record publication and a
change set over it; PostgreSQL, 0.9.0-alpha.1 PG5; 20-row pages; median of five): a first page over
every type takes 5 ms live, 49 ms in a change set and 40 ms in a publication; two named types
24–32 ms; a name search with its total 8–12 ms. The name search reads the trigram index over record
names; a phrase in very many names matches each record instead, so narrowing by `objectTypeKey`,
`applicationKey` or a parent reduces its cost.

### Model-aware query (Base 0.9 Q3)

`POST /api/v1/workspaces/{workspaceKey}/queries/objects` lists one object type's records matching
criteria over their fields, their ancestors and one relation hop, with the fields and related
records each item returns. It is a read with a body: it changes nothing and needs no capability.

```json
{
  "objectTypeKey": "master-value",
  "context": { "publicationId": "…" },
  "where": [
    { "field": "active", "op": "eq", "value": true },
    { "field": "ancestor:codelist", "op": "eq", "value": "…codelist id…" },
    { "related": { "relationTypeKey": "system-value-maps-to-master", "direction": "incoming",
                   "where": [ { "field": "external-id", "op": "startsWith", "value": "EPIC-" } ] },
      "not": false }
  ],
  "sort": "-code",
  "select": ["name", "code", "ancestor:codelist"],
  "expand": [ { "relationTypeKey": "system-value-maps-to-master", "direction": "incoming",
                "select": ["name", "external-id"], "limit": 20 } ],
  "pageSize": 100
}
```

- **`context`**: live when empty, or `changeSetId` or `publicationId` (both: `422
  MUTUALLY_EXCLUSIVE_CONTEXT`). The context must belong to the path's workspace (`422
  WORKSPACE_CONTEXT_MISMATCH`); an unknown workspace, change set or publication is `404`.
- **`where`** is a list combined with AND. A field criterion is `field`, `op` and `value` with the
  object list's grammar: built-in `id`, `name`, `parentObjectId` and (live only) `createdAt`,
  `updatedAt`, and the attributes the type binds as `filterable`, with the operators of their value
  type. Values keep their JSON type: text and dates as strings, integers as integers, decimals as
  numbers or decimal strings, booleans as booleans; `isNull` and `isUnset` take a boolean. Several
  `eq` criteria on one field are alternatives, as on the list. A criterion the list can express
  selects the same records in the same order through either.
- **`ancestor:<type>`** with `eq` on an ancestor's ID: records under that record at any depth, read
  from the containment path. Any ancestor of that type counts, so with a type that nests, each of
  its levels matches. The type must be one the queried type can sit under. An ID of another type,
  or none, matches nothing.
- **`ancestor:<type>.<field>`** (0.9 K7, D178): records under an ancestor of that type, at any depth,
  whose `name` or attribute meets the criterion with the operators of the field's value type (the
  attribute filterable on the ancestor's type, as for the queried type's own). Criteria on one
  ancestor type are met by one ancestor; any ancestor of that type counts. The ancestors are matched
  first and the walk goes down from them through containers only.
- **`related`**: one relation hop over a binding the queried type has in that `direction`, true
  when at least one record at the other end matches the hop's own `where`; `"not": true` inverts
  it (no such record). The hop's criteria are field criteria over the types the binding allows at
  the other end: built-in fields always, an attribute only when that is one type binding it as
  filterable (D18). No further hop and no ancestor criterion inside a hop. OR groups, nested hops and
  several sort keys wait for a second real case (D4).
- **`sort`**: one field as on the per-type list (`name` by default, `id`, `objectType`, a scalar
  attribute, live `createdAt`, `updatedAt`; `-` for descending), then the unique tie-breaker.
- **`select`** names the fields each item returns (D17). Items always carry `id`, `objectTypeKey`
  and `version`. Without `select`, an item is the object list's item. With it, the values are under
  `fields`, keyed by field: `name`, `workspaceKey`, `applicationKey`, `parentObjectId`, `path`,
  `createdAt`, `updatedAt`, any attribute the type binds (null when the record has none), and
  `ancestor:<type>` as the `id` and `name` of the ancestor of that type nearest the root (null when
  there is none).
- **`expand`** adds, per item, the records at the other end of a binding the type has, one entry per
  expansion in `expanded`, in request order: `relationTypeKey`, `direction`, `count` (all of them),
  `items` (at most `limit`, 1–20, default 20; each `relationId` and `object`, shaped by the
  expansion's `select` as above) in name order, and `nextCursor`. That cursor continues on
  `GET /api/v1/relations` with the item as `objectId`, the same `direction`, `relationTypeKey` and
  context, and the default sort, exactly after the last item shown; null when `items` holds them
  all. `expanded` is omitted when the query expands nothing. A binding may be expanded once.
- **`asOf`** (`YYYY-MM-DD`) keeps the queried records effective on that date by their type's
  declared period; see [effective periods](#effective-periods-and-asof-base-09-q4).
- **Paging** as ADR-030, with the page selection in the body: `cursor`, `position`, `from`
  (`start` or `end`), `includeTotal` and `pageSize` (default 100, maximum 500). The response is a
  page (`items`, `nextCursor`, `prevCursor`, `anchor`, and `totalCount` and `startIndex` with
  `includeTotal`). A cursor binds the context and the whole body but its page selection, so it
  continues this query only; no list accepts a query's cursor, nor the query a list's.

**Errors (D19).** The body's shape is checked as on every body: a wrong JSON type for a known
property, an unknown property or a bound such as `pageSize` or `limit` is `422
REQUEST_VALIDATION_ERROR`. What depends on the model is `422 INVALID_QUERY`, with `details.path` a
JSON pointer to the part that is wrong: an unknown object type (`/objectTypeKey`), a field the type
does not bind or not filterable (`/where/0/field`), an operator its value type lacks
(`/where/0/op`), a value of the wrong type (`/where/0/value`), a binding the type does not have
(`/where/1/related/relationTypeKey` or `/direction`), a criterion inside a hop
(`/where/1/related/where/0/field`), an unknown `select` field (`/select/2`), an expansion
(`/expand/0/…`) or a sort (`/sort`). Timestamps in change-set and publication contexts are refused
as on the per-type list.

Cost over the Track S fixture (100,000 items among 258,000 live records, a publication and a change
set over it; PostgreSQL, 0.9.0-alpha.1 PG5; 20-row pages; median of five), live · change set ·
publication: a hop to the group 1,500 items cite, with its total, 12 · 44 · 14 ms; the inverted hop's
first page 7 · 36 · 6 ms; the 20,000 items under one group by `ancestor:`, with their total,
9 · 69 · 10 ms; a 20-row expansion of 1,500 citations 13 · 16 · 12 ms, and of a group's 20,000
items 71 · 46 · 41 ms. Each expansion is one statement for the whole page, which reads the anchor's
relations first and their records by ID.

### Effective periods and `asOf` (Base 0.9 Q4)

An object type may declare one business validity period in the model (schema 0.8,
[APPLICATION_MODEL](APPLICATION_MODEL.md#effective-period-effectiveperiod), ADR-038): two `date`
attributes it binds, the start inclusive and the end exclusive, either of them empty for "since
always" or "open". Validity is ordinary attribute data, so it is edited, versioned, audited and
published like any other value.

**Writes.** A record whose end is not after its start is refused with `422
INVALID_EFFECTIVE_PERIOD`, live and in a change set alike: on create, update, a single-attribute
`PATCH`, a type change and restructuring. The check reads the record's values after the write, so
an update that sets only the end is checked against the stored start. `details` names
`startAttributeTypeKey`, `endAttributeTypeKey`, `start` and `end`. Change-set validation and
publishing report the same code as a diagnostic, with `details.objectId`. Periods of different
records may overlap.

**Reads.** `asOf=YYYY-MM-DD` keeps the records effective on that date: no start after it and no end
on or before it.

- `GET /api/v1/objects/{objectTypeKey}` takes `asOf` in every context (live, `changeSetId`,
  `publicationId`) with every other parameter. It is a filter over values: it never selects a
  publication, and a publication read is not dated unless `asOf` is given.
- The [model-aware query](#model-aware-query-base-09-q3) takes `asOf` in its body. It filters the
  queried records only; a hop's far end and expansions are not dated (D22), and a date criterion on
  the hop dates them where that is wanted.
- The [cross-type lookup](#cross-type-lookup-base-09-q1) lists several types, and a period belongs
  to one, so `asOf` there is refused (D21), as a model-declared filter is.

A cursor binds `asOf`, so it continues only the same date; an undated cursor is not accepted with a
date, nor the reverse.

| Request | Refusal |
| --- | --- |
| `asOf` on a type that declares no period | `422 AS_OF_NOT_SUPPORTED`, `details.path` (`/query/asOf` on the list, `/asOf` in the query) and `details.objectTypeKey`. A date attribute alone never makes a type dated |
| `asOf` on `GET /objects` | `422 AS_OF_NOT_SUPPORTED` with `details.route` naming the per-type list |
| `asOf` that is not a calendar date (a time, a timestamp, `2026-02-30`) | List: `422 REQUEST_VALIDATION_ERROR`. Query: `422 INVALID_QUERY` at `/asOf` |

**Model releases.** Adding or removing a period changes no stored data. Activating a release that
declares a period, or moves one to other attributes, counts the live records of the type whose end
is not after their start: with any, activation is refused as `409 MODEL_MIGRATION_REQUIRED`
(the release diff and draft compile classify it `migration_required`) with a diagnostic
`INVALID_EFFECTIVE_PERIOD` at `/objectTypes/<type>/effectivePeriod` and its `count`
(D20). A consumer API definition that exposes a type whose period is removed needs a higher
`contractVersion` (`CONSUMER_CONTRACT_VERSION_REQUIRED` at `/consumerApis/<key>/exposes/<index>`).

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
target side, creation returns `422 MISSING_REQUIRED_RELATIONS` unless a matching incoming relation is
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
  "name": "Czech delivery method",
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
return `409 DUPLICATE_ATTRIBUTE_VALUE` when a value collides, live and in a change set alike: the
message names the attribute, and `details` carry its `attributeTypeKey` and the record holding the
value as `conflictingObjectId`. Empty text is no value, so any number of records may leave a unique
text attribute empty (both decided 2026-10-03, H4c). Uniqueness is supported for the scalar
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

### Moving a record (Base 0.8 B2)

A `PATCH` with `parentObjectId` moves the record: its parent and its typed containment relation
change together, live or in a change set. The new parent must be of a type the record's
`parentRelationTypeKeys` allow, in the same application and workspace (`422 INVALID_PARENT_TYPE`,
`422 PARENT_WRONG_SCOPE`); `null` makes it a root where its type is `rootCreatable`
(`422 PARENT_REQUIRED` otherwise). The record itself or a record under it is refused as
`422 PARENT_CYCLE`. Publishing a change set revalidates the merged graph, so a move the change set
made valid but live has since made cyclic is refused as `422 WORKSPACE_GRAPH_INVALID` with a
`CONTAINMENT_CYCLE` diagnostic, and the change set and live data stay as they were.

Only the moved record's parent and edge are written, so a move costs about what a rename does
however many records lie under it. A live move re-checks ancestor-scoped uniqueness
(`uniqueToAncestorTypeKey`) for the records under the moved one whose scope record is above it, and
only for bindings that can reach them (`409 DUPLICATE_RELATION_SCOPE`). Moving a container of many
relation matrix cells recomputes their rows' stored cell states and is a known 0.8 budget exception
(D29).

`GET /api/v1/objects/{objectTypeKey}/{objectId}/parent-candidates` lists where the record could move:
every record of a type that can contain it, in its application and workspace, in name order. It
takes `workspaceKey` (live) or `changeSetId`, `parentObjectTypeKey` to list one of those types
(another is `422 INVALID_PARENT_TYPE` with the `permitted` types), `search` (the name or a
searchable field, as on an object list) and the paging parameters (`pageSize` 1–100, default 50).
A record not in the context is `404 OBJECT_NOT_FOUND`. Publications are read-only and have no move
targets.

Each item has `id`, `objectTypeKey`, `name`, `path` (root first, ending with the candidate) and
`eligible`. A candidate the move would refuse or would not change stays in the list, so pages and
totals stay truthful (D14), with a `reason`:

- `self`: the record itself, listed when its type may contain its own;
- `descendant`: a record under it, which would make a cycle;
- `currentParent`: where it already is.

`descendant` is read from the candidate's path in the request's context, so a change set's own moves
count. A page costs a fixed number of statements plus one per hierarchy level for the paths.

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

- `POST` creates only when no value is stored for the key (`409 ATTRIBUTE_ALREADY_EXISTS` otherwise).
- `PATCH` updates only a stored value (`404 ATTRIBUTE_NOT_FOUND` when the key has no value yet).
- For a live POST/PATCH, omit both change set fields from the example. For live DELETE, supply only
  `expectedVersion`; the change set query fields shown in the route list are optional context.
- `DELETE` removes a stored value and returns 204. Required attributes cannot be deleted
  (`422 CANNOT_DELETE_REQUIRED_ATTRIBUTE`); read-only attributes are rejected with
  `422 READ_ONLY_ATTRIBUTES`. Deleting an optional value reverts that attribute to "not stored".

Value validation, type normalization and per-workspace uniqueness behave exactly as in the object
create/update flows — `UNKNOWN_ATTRIBUTES`, `INVALID_ATTRIBUTE_VALUE`, numeric bounds and
`DUPLICATE_ATTRIBUTE_VALUE` all apply. Object-level `atLeastOneOf` rules are also checked against the
complete resulting attribute set. Stale `expectedVersion` values return `409 VERSION_CONFLICT`.

### Error responses

All API errors, including request validation and unmatched routes, return a unified JSON envelope
with a machine-readable `code` and a human-readable `message`. Every code is written in upper case
(`OBJECT_NOT_FOUND`), on every API of the engine: error bodies, the errors and unprocessed `reason`
of batch and job item outcomes, and validation diagnostics (0.9 T1b). Status, action, kind and
classification values are not codes and stay in lower case. Validation errors additionally include
a `details` array. Unexpected internal errors use code `INTERNAL_ERROR` and include a
`correlationId` in `details`; the same identifier appears in server logs for operator diagnosis.
A write validated under a model release that was replaced before it committed returns
`409 MODEL_RELEASE_CHANGED` and saves nothing (see model activation). A stale `expectedVersion` on a
record or relation write (an update, a move, a delete or a single value's write, live or in a change
set, and a batch item's) returns `409 VERSION_CONFLICT` with `details.currentVersion`, the version to
read again before retrying (decided 2026-10-03, H4c).

```json
{
  "error": {
    "code": "OBJECT_ALREADY_EXISTS",
    "message": "An object with ID 'c5588b49-...' already exists"
  }
}
```

Record IDs are unique across the instance. When the ID a create gives belongs to a record of
another workspace, `OBJECT_ALREADY_EXISTS` says so, live and in a change set alike: the message names
that workspace and `details.workspaceKey` holds it (0.9 J4a). The common cause is a file with record
IDs, such as an export, sent to a second workspace of the instance; it loads only into the workspace
it came from (D49).

Internal error example:

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "The GET /api/v1/model-releases operation failed unexpectedly. Retry or contact support with reference a1b2c3d4e5f6.",
    "details": { "correlationId": "a1b2c3d4e5f6" }
  }
}
```

#### Further error codes

Codes the sections above do not describe (documented 2026-10-03, H4c decision D-4), with the journey
whose tests meet them ([USER_JOURNEYS](product-functionality/USER_JOURNEYS.md)). A batch item
refused by a single write's rule carries the same code in its outcome.

| Code | Status | Where | Meaning |
| --- | --- | --- | --- |
| `INVALID_POSITION` | 422 | every paged collection | `position` below zero; `details.path` `/query/position` (J21.1) |
| `WORKSPACE_RUNTIME_STATE_MISSING` | 500 | workspace reads and writes | The workspace catalogue's runtime row is missing: a damaged database, not a client error |
| `WORKSPACE_KEY_REQUIRED` | 422 | `POST /objects` | A live create without `workspaceKey` (and without `changeSetId`) (J03) |
| `UNKNOWN_APPLICATION` | 404 | `POST /objects`, batch items, `GET /applications/{key}`, `GET /objects` | `applicationKey` names no application of the model (J03.2, J20) |
| `OBJECT_TYPE_NOT_IN_APPLICATION` | 422 | `POST /objects` | The application does not hold the object type (J03.2) |
| `UNKNOWN_ATTRIBUTE_TYPE` | 404 | `GET /attribute-types/{key}` | No attribute type with that key in the selected model (J20) |
| `ATTRIBUTE_BELOW_MINIMUM`, `ATTRIBUTE_ABOVE_MAXIMUM` | 422 | every value write | A number outside the attribute's declared `minimum` or `maximum` (J02.5) |
| `MISSING_REQUIRED_ATTRIBUTES` | 422 | create, update, type change | A value the type requires is absent; the message names the fields (J03) |
| `OBJECT_ATTRIBUTE_RULE_VIOLATION` | 422 | create, update, single-value writes, type change | An `atLeastOneOf` rule is not met; `details` `rule` and `attributeTypeKeys` (J02.5, J03) |
| `DUPLICATE_INITIAL_RELATION` | 422 | `POST /objects`, batch creates | `initialRelations` repeats one relationship (type, direction and record), live and in a change set alike (J03.4) |
| `INVALID_RELATION_PAIR` | 422 | relation create, `initialRelations` | The model allows no relationship of that type between the two records' types (J13.3) |
| `RELATION_WRONG_SCOPE` | 422 | relation create, `initialRelations` | The two records are in different workspaces (J13) |
| `RELATION_CANDIDATE_REFUSED` | 422 | relation create, `initialRelations`, set replacement, batch and import items | An end of a new relationship does not meet the criteria the model's binding sets there (`candidates`); `details` `relationTypeKey`, `end`, `objectId`, `criteria` (0.9 K7, J13.9, J03.9) |
| `RELATION_ENDPOINT_MISSING` | 422 | relation create, `initialRelations` | An end names a record the context does not hold, live and in a change set alike (decided 2026-10-03, H4c); change-set validation reports it as a diagnostic (J13.3, J05) |
| `CHANGE_SET_SOURCE_INVALID` | 422 | `POST /workspaces/{key}/change-sets` | `source` is not `currentLive` or `publication`, a publication source lacks `sourcePublicationId`, or a current-live source names one (J05) |
| `CHANGE_SET_BASE_INVALID` | 409 | mapping reads in a change set | The change set's base, or its base publication, is missing or belongs to another workspace: a damaged change set (J10) |
| `CHILD_TYPE_NOT_ALLOWED` | 422 | `changeType`, restructuring | The new type cannot contain one of the record's children; the restructuring plan reports it as `noPossibleType` (J15) |
| `REQUIRED_RELATION_WITHOUT_PLACE` | 422 | `changeType`, restructuring | The new type cannot hold a relationship another record requires (J15) |
| `RELATION_ALREADY_EXISTS` | 409 | change back in a change set | A relationship the change back restores already exists in the change set (J15.1) |
| `WORKSPACE_ALREADY_EXISTS` | 409 | `POST /workspaces` | The key is taken, by an active or a retired workspace (J19) |
| `DEFAULT_WORKSPACE_CANNOT_BE_RETIRED` | 409 | `PATCH /workspaces/{key}` | Retiring the default workspace (J19) |
| `MAPPING_VIEW_REQUIRED` | 422 | `GET /workspaces/{key}/mapping-targets` | `applicationKey` and `viewKey` must come together (J10) |
| `INCOMPLETE_VIEW_IDENTITY` | 422 | `GET /workspaces/{key}/relations` | `applicationKey` and `viewKey` must come together (J22.2) |
| `MAPPING_VIEW_NOT_FOUND` | 404 | mapping reads, the edge list | The view is not a relationship view of that application in the selected model (J10, J22.2) |
| `MAPPING_VIEW_BINDING_MISMATCH` | 422 | mapping reads | The relationship type, types or direction differ from the view's (J10) |
| `MAPPING_BINDING_NOT_FOUND` | 404 | mapping reads | The model allows no such relationship between the named types (J10) |
| `MAPPING_CANDIDATE_TYPE_MISMATCH` | 422 | `GET /workspaces/{key}/mapping-candidates` | The candidate type is not the view's target side (J10.3) |
| `MAPPING_PARENT_NOT_FOUND` | 404 | `GET /workspaces/{key}/mapping-coverage` | `parentObjectId` is not in the selected context (J10) |
| `MAPPING_PARENT_SCOPE_MISMATCH` | 422 | `GET /workspaces/{key}/mapping-coverage` | That parent's type cannot contain the view's source records (J10) |
| `MAPPING_SOURCE_NOT_FOUND` | 404 | `GET /workspaces/{key}/mapping-targets` | The source record is not in the selected context (J10) |
| `MAPPING_ENDPOINT_NOT_FOUND` | 404 | `PUT /workspaces/{key}/mappings` | The source or a target is not in the context (J10) |
| `MAPPING_ENDPOINT_TYPE_MISMATCH` | 422 | `PUT /workspaces/{key}/mappings` | The source or a target is not of the binding's type (J10) |
| `FEED_POSITION_AHEAD` | 409 | `GET /workspaces/{key}/feed` | `after` is past the feed's head; `details.headPosition` (J26) |

## Relation endpoints

- `POST /api/v1/relations`
- `GET /api/v1/relations?objectId={id}&direction={outgoing|incoming|both}&relationTypeKey={key}` (`relationTypeKey` repeatable)
- `GET /api/v1/relations/{relationId}`
- `GET /api/v1/relations/held?objectTypeKey={type}&relationTypeKey={key}&direction={outgoing|incoming}&objectId={id}`
  (`objectId` repeatable): what a set of records holds through one relationship ([below](#what-a-set-of-records-holds-09-k6a))
- `GET /api/v1/workspaces/{workspaceKey}/relations`: every edge in a workspace, in live data, a change
  set or a publication ([workspace edge list](#workspace-edge-list-mapping-list-base-09-q2))
- `PATCH /api/v1/relations/{relationId}`
- `DELETE /api/v1/relations/{relationId}?expectedVersion={n}&changeSetId={id}&expectedChangeSetVersion={n}&expectedRelationSetVersion={n}&relationSetDirection={outgoing|incoming}`

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
  live only; change sets and publications record no timestamps, so they answer `422 INVALID_SORT`.
- An attribute sort over several related types puts records whose type lacks the attribute last. An
  ancestor sort needs the listed relations to reach one object type, decided by the anchor record's
  type, `direction` and `relationTypeKey` from the model's allowed relations; otherwise
  `422 INVALID_SORT`. An `ancestor:<type>` the related type cannot sit under is refused too.
- Without `sort` the list is in name order in every context. Ties break on the relation.
- `seek` takes a value of the sorted field (a name by default).

Change-set and publication relation items carry the related record's `path`, as live items do. A relation page
for a record the context does not hold answers `404 OBJECT_NOT_FOUND` in every context. Change set and
history continuations add their selected context identity; live continuations do not bind an active
publication or model. Publication alone does not invalidate a live continuation. Malformed or
mismatched cursors return `422 INVALID_CURSOR`; cursors issued before S4R1 are refused. Live, the
anchor must be in the selected workspace and the related record is joined in it before projection,
preventing a corrupt or legacy cross-workspace edge from being exposed.

This page shape is an intentional pre-1.0 breaking change. Callers must follow `nextCursor` unchanged
and must not parse it.

Live and in a change set the page also names, as `relationSets`, every relationship set the record
anchors in the listed `direction` and relation types (Base 0.9 B3, D38): one entry per binding its
type takes part in other than containment, with `relationTypeKey`, `fromObjectTypeKey`,
`toObjectTypeKey`, `direction` and `relationSetVersion`, which is `0` for a set no write has touched.
A set with no relationship (never had one, or all removed) is named too, so an integrator reads a
record's set and claims its version on a create, a delete or a batch's `replaceRelationSet` without
a matrix or mapping view. In a change set the versions are the change set's own. A publication is
read-only and names none.

A relation type the model does not declare is `422 UNKNOWN_RELATION_TYPE` on every write, live and in
a change set (`GET /relation-types/{key}` answers an unknown key with `404`).
Relation creation validates the relation type, source and target object types, workspace, cardinality,
configured ancestor-scoped uniqueness and relation attributes. A relation of the type already joining
the same two records is `409 DUPLICATE_RELATION`, live and in a change set (Base 0.9 B3; live it
answered `500` before). Relation attribute keys must appear in
the matched allowed pair's `attributeTypeKeys`; values are normalized and validated using the referenced
global attribute-type definitions. Undeclared keys return `422 UNKNOWN_RELATION_ATTRIBUTES`, and type or
numeric-bound failures use the same errors as object attributes.
`fromObjectId` and `toObjectId` must be UUID v4. Parent relations are normally created through object
parent operations rather than directly.

Each relation response carries a stable public `id`, the relation type, source and target object ids,
the relation `attributes` and an optimistic-concurrency `version`. `GET /api/v1/relations/{relationId}`
reads one relation; an unknown id returns `404 RELATION_NOT_FOUND`.

`PATCH /api/v1/relations/{relationId}` accepts `{"attributes": {...}, "expectedVersion": n,
"changeSetId": "...", "expectedChangeSetVersion": n}`. The
example is change-set-scoped; omit its two change set fields for a live update. The relation identity
(`relationTypeKey`, `fromObjectId`, `toObjectId`) is immutable; only `attributes`
can be replaced. Replacement attributes are validated against the original allowed pair in the same
transaction as the version claim. `DELETE` returns 204 and removes the relation row. Both mutations
take `expectedVersion` and claim it under the workspace's write lock, returning `409 VERSION_CONFLICT`
when the claim is stale; an update checks the version before its attributes (Base 0.9 B3, as change
sets did).

Engine-maintained parent-containment and hierarchy relations — those named in the target object type's
`behavior.parentRelationTypeKeys` and written atomically on parent changes — are read-only through this
API. Creating, updating or deleting them directly returns `422 IMMUTABLE_RELATION`; changing them is
done through object parent operations.

Create and delete may also claim one end's relation set (ADR-022, Base 0.8 A3): with
`expectedRelationSetVersion` and `relationSetDirection` (body fields on `POST`, query parameters on
`DELETE`), the write succeeds only while the set anchored at that end — `outgoing` is the from end's,
`incoming` the to end's, for the relation's exact binding and context — is still at the version the
caller read, such as a relation matrix row's `relationSetVersion`. A newer set refuses the whole write
with `409 RELATION_SET_VERSION_CONFLICT` and `details` `anchorObjectId`, `direction` and the current
`relationSetVersion`; naming only one of the two is `422 RELATION_SET_CLAIM_INCOMPLETE`. A claimed
create responds with the set's new `relationSetVersion`. Without a claim, a write still advances both
ends' sets, as does every relation an object create adds through `initialRelations`.

A breach of a binding's `uniqueToAncestorTypeKey` scope in live data, on a relation create, an object
create with `initialRelations`, an object edit, a move or a set replacement, returns
`409 DUPLICATE_RELATION_SCOPE` with `details` `ancestorObjectTypeKey`, `ancestorObjectId`, and the
record already in the scope as `conflictingObjectId` with its relation `conflictingRelationId`. A
change set is a draft and holds the same breach, so its edits can come in any order (a new owner
added before the old one is removed): the write succeeds, the relation matrix shows the cell as
`several` with `conflict`, and validation and publishing report it as a diagnostic with
`conflictingObjectId` (publishing refuses with `422 WORKSPACE_GRAPH_INVALID`). A related record with
no ancestor of the scope type is refused at once in both (`422 RELATION_ANCESTOR_REQUIRED`).
Decided 2026-10-03 (H4c).

A required non-parent relation returns `422 REQUIRED_RELATION` when independently deleted. It is part
of the dependent graph's validity and ownership semantics; delete or replace the dependent object
through the owning workflow instead.

### What a set of records holds (0.9 K6a)

`GET /api/v1/relations/held` answers what a selection's Remove offers (D165): the records at the other
end of one relationship type from the named records, each once, with `count`, how many of the named
records hold it. `objectTypeKey` is the named records' type and `direction` reads from them
(`outgoing` when they are the relationship's from end). `objectId` repeats, at most 500 per read; the
records come in name order and page by the [collection paging](#collection-paging) parameters with
`pageSize` 1–500 (default 100), in live data, a change set (`changeSetId`) or a publication
(`publicationId`). A named record the context does not hold, or one holding nothing, adds nothing.
Each item is `{object: {id, objectTypeKey, name}, count}`.

A selection larger than one read is asked in batches and the counts added up per record; the UI
names 200 records a read, which keeps the address within common URL limits.

| Code | Status | When |
| --- | --- | --- |
| `UNKNOWN_RELATION_TYPE` | 422 | `relationTypeKey` is not in the model |
| `INVALID_RELATION_PAIR` | 422 | The type has no binding of the relationship in that direction |
| `TOO_MANY_RECORDS` | 422 | More than 500 `objectId`; `details.limit` |
| `MUTUALLY_EXCLUSIVE_CONTEXT` | 422 | Both `changeSetId` and `publicationId` |

## Object audit history

- `GET /api/v1/objects/{objectTypeKey}/{objectId}/history?cursor=...&pageSize=...`

History is ordered newest first by occurrence time and an internal non-public sequence tie-breaker.
It returns the standard bounded page and includes events recorded directly for the object plus events
for relations connected to it. The indexed `audit_event_subjects` projection supplies identity; the
read path never searches JSON audit payloads.

Each history item contains `id`, `aggregateType`, public `aggregateId`, `action`, `version`,
`changedFields`, `attributeTypeKeys` and `occurredAt`, and `cause` when a job made the change
(`{"kind": "job", "id": …}`, Base 0.9 B1) or a publish applied it to live data
(`{"kind": "publication", "id": …}`, Base 0.9 F1, D15). `attributeTypeKeys` names affected object or
relation attributes without returning their values. The response deliberately omits the internal
sequence ID and complete before/after values. History cursors are signed and bound to the object
identity, type and workspace; mismatches return `422 INVALID_CURSOR`.

## Batches and jobs (Base 0.9 B1, B2, B3)

Bulk writes run as **jobs** ([ADR-036](DECISIONS.md#adr-036--a-batch-is-a-job-one-mechanism-for-bulk-writes-imports-and-exports);
design and reasons in [INTEGRATION_API P and B](INTEGRATION_API.md#p-shared-primitives)). B1 delivers
object items run inline, B2 background runs and cancellation, B3 relationship items and set
replacement.

```text
POST /api/v1/batches                                   (INTEGRATION_JOBS_ENABLED)
POST /api/v1/jobs/{jobId}/cancel                       (INTEGRATION_JOBS_ENABLED)
POST /api/v1/jobs/{jobId}/confirm                      (INTEGRATION_JOBS_ENABLED; a previewed batch, 0.9 K2)
GET  /api/v1/jobs?workspaceKey=…&kind=…&state=…        newest first, ADR-030 paging
GET  /api/v1/jobs/{jobId}
GET  /api/v1/jobs/{jobId}/items?status=…&ref=…         outcomes in item order, ADR-030 paging
```

### Request

```json
{
  "workspaceKey": "main",
  "policy": "independent",
  "run": "inline",
  "onExisting": "reject",
  "items": [
    { "ref": "row-2", "op": "upsert", "applicationKey": "rdm-master", "objectTypeKey": "codelist",
      "key": { "attributeTypeKey": "codelist-code" },
      "name": "Delivery methods",
      "parent": { "objectTypeKey": "domain", "key": { "attributeTypeKey": "domain-code", "value": "LOGISTICS" } },
      "attributes": [ { "attributeTypeKey": "codelist-code", "value": "MOT" } ] }
  ]
}
```

- **Context:** `workspaceKey` for live data, or `changeSetId` with `expectedChangeSetVersion`;
  exactly one (`422 INVALID_BATCH_CONTEXT`; a change set without its version is
  `409 CHANGE_SET_REQUIRED`). A job in a change set claims the version once for all its items: it
  advances by one when anything changed, and not at all otherwise.
- **`policy`** (required, no default): `atomic` applies every item or none; `independent` applies each
  item on its own. Items apply in order, each against the data the items before it left, so a later
  item sees an earlier applied one (a child after its parent). In `atomic` the first rejection rolls
  everything back and every other item is `unprocessed` (`BATCH_ROLLED_BACK`).
- **`run`** (required): `inline` runs the job in the request and answers `200` with its outcomes;
  `background` queues it and answers `202` with the job ([Background jobs](#background-jobs)). The
  size never switches the run.
- **`stage`** (0.9 K2): `execute` (the default) or `preview`, which runs the items without writing
  anything and waits for confirmation ([Previewing a batch](#previewing-a-batch-09-k2)). A preview
  is a background job: with `run: inline` it is `422 REQUEST_VALIDATION_ERROR`.
- **`onExisting`**: `reject` (default) or `overwrite`, for upserts that find a record and carry no
  `expectedVersion`.
- **`otherWorkspaceIds`**: `refuse` (default) or `counterparts` (0.9 J5). Record IDs are unique
  across the instance, so an ID another workspace's record holds names nothing here and creating a
  record with it is refused (`OBJECT_ALREADY_EXISTS`, `REFERENCE_NOT_FOUND`, both naming that
  workspace). With `counterparts` such an ID stands for its **counterpart**, this workspace's own
  record derived from it ([Counterparts](#counterparts-base-09-j5)): created with the counterpart's
  ID the first time, found by it after. IDs this workspace's records hold, and IDs no record holds,
  are used as given.
- **`Idempotency-Key`** header (optional, 1–200 printable characters), scoped to the route and the
  workspace. The same key with the same request answers the original job's response again with
  `Idempotent-Replayed: true` and runs nothing (a background job: `202` with the job as it is now);
  with another request it is `422 IDEMPOTENCY_KEY_REUSED`; while its job is queued or running,
  `409 IDEMPOTENCY_IN_PROGRESS` with `Retry-After`. A key lives as long as its job; past retention it
  counts as new. Without a key, retrying a `create` without an
  `id` can create the record twice; an upsert, or a create with an `id`, is safe to retry.
- **Limits** (settings, reported by `GET /capabilities` as `integrationJobs.limits`): inline,
  `BATCH_MAX_ITEMS` (1,000) and `BATCH_MAX_BYTES` (5 MB body); background, `BACKGROUND_JOB_MAX_ITEMS`
  (1,000,000) and `BATCH_BACKGROUND_MAX_BYTES` (50 MB body); either run, `ATOMIC_JOB_MAX_ITEMS`
  (10,000) for `atomic`. Over a limit is `413 BATCH_TOO_LARGE` with `details.setting`,
  `details.maximum` and the request's `items` or `bytes`. `chunkItems` reports `JOB_CHUNK_ITEMS`.

### Items

A **record reference** is `{ "id": "…" }` or `{ "objectTypeKey": "…", "key": { "attributeTypeKey": "…",
"value": … } }`, where the attribute is declared `unique` and bound to the type. It resolves in the
batch's context as it stands when the item runs.

| `op` | Fields | Applies as |
| --- | --- | --- |
| `create` | `applicationKey`, `objectTypeKey`, `name`; optional `id`, `parent` (reference), `attributes`, `initialRelations` (`relationTypeKey`, `direction`, `object` reference, `attributes`) | `POST /objects` |
| `update` | `target` (reference), `expectedVersion`; optional `name`, `parent` (reference, or `null` for the top level), `attributes` | `PATCH /objects/…`: only the fields given change |
| `upsert` | `applicationKey`, `objectTypeKey`, `key`, `name`; optional `parent`, `attributes`, `initialRelations`, `expectedVersion` | Finds the record by `key` and updates it as `update`, or creates it as `create`. `key` is `{ "id": "…" }` (the ID a new record gets) or `{ "attributeTypeKey": "…" }`, a unique attribute whose value the item's `attributes` supply. `initialRelations` are used only when it creates; an absent `parent` keeps an existing record where it is |
| `delete` | `target`, `expectedVersion`; optional `cascade` (default `false`) and `deletionPreviewToken` | `DELETE /objects/…`: without `cascade` a record with dependants is `OBJECT_HAS_DEPENDANTS` with its `impact`; with it the record goes with its dependants under the impact its token confirms ([deleting with what depends on it](#deleting-with-what-depends-on-it-09-k2b)) |
| `createRelation` | `relationTypeKey`, `from`, `to` (references); optional `attributes`, `expectedRelationSetVersion` with `relationSetDirection` | `POST /relations` |
| `ensureRelation` | `relationTypeKey`, `from`, `to`; optional `attributes`, `expectedVersion` | Creates the relationship unless one of the type already joins the two records; then `unchanged` when `attributes` are omitted or equal, otherwise an update of its attributes |
| `ensureNoRelation` | `relationTypeKey`, `from`, `to`; optional `expectedVersion` | Deletes the relationship of the type joining the two records, as `DELETE /relations/{id}` does; `unchanged` when none joins them ([relationships by their ends](#relationships-by-their-ends-09-k3)) |
| `updateRelation` | `id`, `expectedVersion`, `attributes` | `PATCH /relations/{id}`: the attributes are replaced |
| `deleteRelation` | `id`, `expectedVersion`; optional `expectedRelationSetVersion` with `relationSetDirection` | `DELETE /relations/{id}` |
| `replaceRelationSet` | `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction`, `anchor` (reference), `targets` (each `{ "object": reference, "attributes"?: {…} }`, possibly empty); optional `expectedRelationSetVersion` | The anchor's set of that binding in that direction becomes the targets, as `PUT /mappings` replaces one |

An item's validation, refusals and audit entries are its single write's. An update or upsert whose
name, parent and values equal the record's is applied as `unchanged`, whatever its version claim: it
writes no version, audit entry or change. Otherwise an update needs a current `expectedVersion`
(`VERSION_CONFLICT`), and an upsert that finds a record needs one too (`VERSION_REQUIRED`) unless the
request declares `onExisting: "overwrite"`; then it writes over the version it read, reports it as
`previousVersion` and records it in the audit entry. An upsert never changes a record's type or
application (`REFERENCE_TYPE_MISMATCH`).

Relationship items are decided as the single relationship writes decide them, with the same codes,
and written in bulk with the object items around them, so a chunk costs a constant number of
statements whatever its mix (D35). An `ensureRelation` that would change a relationship's values
needs its `expectedVersion`, or `onExisting: "overwrite"` (`VERSION_REQUIRED` otherwise; an
overwrite reports `previousVersion`). A claimed set (`expectedRelationSetVersion` with
`relationSetDirection`, or a `replaceRelationSet`'s version) is checked against the set as the items
before it leave it (`409 RELATION_SET_VERSION_CONFLICT` with `anchorObjectId`, `direction` and the
current `relationSetVersion`); [the record's relationship list](#relation-endpoints) names every
set's version. A containment relationship is never an item (`IMMUTABLE_RELATION`): a parent changes
through an object's `parent`.

**`replaceRelationSet`.** A target the anchor already relates to keeps its relationship: omitted
`attributes` keep its values, an explicit object replaces them. The others are removed and the new
ones created in the listed order, each checked as a single create over what came before, so
cardinality at either end (`CARDINALITY_VIOLATION`), ancestor scope (`DUPLICATE_RELATION_SCOPE`,
`RELATION_ANCESTOR_REQUIRED`) and the values answer with their single codes, pointing at
`/items/{i}/targets/{j}`. A set equal to the targets is `unchanged`, whatever its version claim;
otherwise `expectedRelationSetVersion` must be the set's version, or the request declares
`onExisting: "overwrite"` (`VERSION_REQUIRED` otherwise). Refused as well: a required-ownership
binding (`REQUIRED_OWNERSHIP_BINDING`), an empty set on a required binding, or removing a
relationship whose other record requires one and has no other (`REQUIRED_RELATION`, with
`details.objectId`), a record listed twice (`DUPLICATE_RELATION`), and an anchor or target of
another type than the binding's end (`REFERENCE_TYPE_MISMATCH`). The anchor's set advances by one,
and each record whose own set changed by one. Each relationship removed, changed or created gets
its audit entry and feed entry, and one `transition` entry in the anchor's history names the
previous and new targets (not in the feed).

### Response

A processed batch answers `200` with the finished job and the first page of its outcomes (up to
1,000; later pages from `GET /jobs/{id}/items`). Read `job.result`: `applied` (every item),
`partial` or `rejected` (none). A request refused as a whole creates no job; that includes a model
release activated while it ran (`409 MODEL_RELEASE_CHANGED`, nothing saved).

```json
{
  "items": [
    { "index": 0, "ref": "row-2", "status": "applied", "action": "created",
      "id": "…", "objectTypeKey": "codelist", "version": 1 },
    { "index": 1, "ref": "row-3", "status": "rejected",
      "error": { "code": "DUPLICATE_ATTRIBUTE_VALUE", "message": "…",
                 "details": { "pointer": "/items/1/attributes", "…": "…" } } },
    { "index": 2, "ref": null, "status": "unprocessed", "reason": "BATCH_ROLLED_BACK" }
  ],
  "nextCursor": null, "prevCursor": null, "anchor": "…",
  "job": {
    "id": "…", "kind": "batch", "workspaceKey": "main", "changeSetId": null, "changeSetVersion": null,
    "policy": "independent", "parameters": { "run": "inline", "onExisting": "reject" },
    "modelReleaseId": "…", "state": "completed", "stage": null,
    "progress": { "total": 3, "processed": 3 },
    "counts": { "applied": 1, "rejected": 1, "unprocessed": 1,
                "created": 1, "updated": 0, "unchanged": 0, "deleted": 0 },
    "result": "partial", "error": null,
    "createdAt": "…", "startedAt": "…", "finishedAt": "…", "expiresAt": "…",
    "cancelRequestedAt": null, "leaseOwner": null, "leaseExpiresAt": null
  }
}
```

An outcome carries only its status's fields. `applied`: `action` (`created`, `updated`,
`unchanged`, `deleted`), `id`, `objectTypeKey`, `version` (none after a live delete), after an
overwrite `previousVersion` and, when the record written is a counterpart, `sourceId` (0.9 J5). A relationship item's has `relationId`, the relationship's `version`
(none after a delete) and, when it claimed a set, the set's new `relationSetVersion`. A
`replaceRelationSet`'s has `action` `updated` or `unchanged`, the anchor's `relationSetVersion`, the
version it found (`previousRelationSetVersion`, 0.9 K3) and `relationIds` (`created`, `kept`,
`removed`); its refusals name that version too (`details.relationSetVersion`). An `ensureNoRelation`
that found no relationship is `unchanged` without `relationId`. `rejected`: `error` with the single write's code, or one of
`INVALID_RECORD_KEY`, `MISSING_RECORD_KEY`, `REFERENCE_NOT_FOUND`, `REFERENCE_TYPE_MISMATCH` and
`VERSION_REQUIRED`; `details.pointer` is a JSON pointer into the request. A `REFERENCE_NOT_FOUND`
whose ID is a record of another workspace says so: the message names what the reference is for (the
parent, the target, a relationship's start or end) and the workspace, and `details.workspaceKey`
holds it (0.9 J4a). `unprocessed`: `reason`.
Every audit entry an item writes names the job as its cause (`cause: {"kind": "job", "id"}` in object
history). A job's outcomes and idempotency key are kept for `JOB_RETENTION_DAYS` (7) after it
finishes; `expiresAt` says until when. Then the job is `expired`: its summary (`counts`, `result`,
`error`, `progress`, times) remains, and its outcomes and key are removed, so
`GET /jobs/{id}/items` answers `200` with an empty page.

### Background jobs

`run: background` answers `202` with the job, `queued`, once the job and its items are stored; a
request refused before that (context, limits, a stale `expectedChangeSetVersion`, a model release
activated meanwhile) creates no job. A worker in the API process then runs it:

- **Chunks.** An `independent` job applies `JOB_CHUNK_ITEMS` (500) items per transaction; an
  `atomic` job is one transaction. A chunk commits its changes, their outcomes and the job's
  `progress.processed` together, so outcomes page in as chunks commit, and after a crash the job
  resumes at its first item without an outcome: no item is applied twice or skipped. Items see
  earlier chunks' applied items.
- **Lease.** `leaseOwner` and `leaseExpiresAt` name the worker running the job; the lease is renewed
  with each chunk (`JOB_LEASE_SECONDS`, 120). Another worker, or the process after a restart, takes
  the job over once the lease expires; a worker stopping gracefully releases it at once.
- **In a change set** the job holds the change set's claim: each chunk that changes something
  advances the version by one, and `changeSetVersion` is the version the job holds (its claim while
  it runs, the version it left once finished). A write to the change set by anyone else between
  chunks makes the job `failed` with `CHANGE_SET_VERSION_CONFLICT`.
- **Stops.** Before each chunk the worker reads the job. A cancel request finishes it `cancelled`;
  a model release no longer the one the job pinned (live: the active release; in a change set: the
  change set's) makes it `failed` with `error.code` `MODEL_RELEASE_CHANGED`; another refusal of its
  context (a retired workspace, a lost change set claim) makes it `failed` with that error; any other
  failure rolls back the chunk and makes it `failed` with `JOB_FAILED` and `details.correlationId`,
  the log entry's. Items the job did not reach are `unprocessed` with `JOB_CANCELLED`,
  `MODEL_RELEASE_CHANGED` or `JOB_FAILED`; chunks committed before stay applied, and `result` says
  what applied. `progress.processed` equals `progress.total` once the job is finished.

`POST /jobs/{jobId}/cancel` answers `202` with the job and `cancelRequestedAt` set; it waits for no
chunk. The worker carries it out at the job's next chunk (a queued job before its first item); an
`atomic` job looks for it before every 500 items it decides and before it writes them, and rolls
back completely. An import preview waiting for confirmation (0.9 J3) is cancelled at once: it is
`cancelled` with `finishedAt` set, its file removed and its preview's outcomes kept to read until
retention. Cancelling again changes nothing; a
finished job is `409 JOB_FINISHED` with `details.state`, an unknown one `404 JOB_NOT_FOUND`.

### Previewing a batch (0.9 K2)

A background batch sent with `stage: "preview"` is queued and run by the worker as an
[import's preview](#preview-and-confirmation) is: its first `JOB_PREVIEW_MAX_ITEMS` items run
independently, whatever the policy, in one transaction that is rolled back, so no record,
relationship, feed entry, audit entry or event is written and a change set keeps its version. The
job then waits in `awaiting_confirmation` with `preview` (`coverage`, `items`, `counts`, `result`,
`previewedAt`; no `rows`, which only an import has), and its outcomes read at `/items`, where
`applied` means it would apply.

`POST /jobs/{jobId}/confirm` queues it again: the preview's outcomes are removed and the stored items
run from the first as `stage: "execute"` would, so **execution is authoritative**: a record changed
since its preview is refused `VERSION_CONFLICT` then, and an `atomic` batch with a refusal writes
nothing. Confirm's
refusals (`409 CHANGE_SET_VERSION_CONFLICT` when the change set changed since the request's
`expectedChangeSetVersion`, `409 MODEL_RELEASE_CHANGED`, `410 JOB_EXPIRED`), cancelling a waiting
preview and retention are the import's. The `Idempotency-Key` answers with the waiting job.

A preview whose delete items would delete anything adds `preview.deletion`: `objectCount`,
`objectsByType` (`{objectTypeKey: count}`), `relationshipCount` and `retainedAssociationCount`
over them all (0.9 K2b, D121).

### Deleting with what depends on it (0.9 K2b)

A `delete` item deletes its record as `DELETE /objects/{type}/{id}` does, with its rules (D120):

- **Without `cascade`** a record with dependants (containment descendants, records it owns through a
  required oriented `one-to-one` or `one-to-many` relation) or a relationship other than its
  containment edges is refused `409 OBJECT_HAS_DEPENDANTS`, whose `details.impact` gives its counts
  and token; a record with neither is deleted.
- **With `cascade`** the item needs `deletionPreviewToken`, the token of the impact the client was
  shown: without one it is refused `409 DELETION_PREVIEW_REQUIRED`; when the record's version or its
  impact (a record or relationship added, removed or changed) differs from what the token confirms,
  `409 DELETION_PREVIEW_CHANGED`, and nothing of that item is deleted.
- **In a preview** (`stage: "preview"`) a cascading item needs no token: the preview computes each
  item's impact and token, and `POST /jobs/{jobId}/confirm` puts each token into its stored item, so
  execution deletes exactly what was previewed and refuses only the items whose impact changed. An
  item the preview did not delete itself (refused, or gone with another item) is refused
  `DELETION_PREVIEW_CHANGED` if it stands on its own at execution, and a `sample` preview's
  unpreviewed items are refused `DELETION_PREVIEW_REQUIRED`: each delete is confirmed by its own
  preview.

An applied delete's outcome carries `impact`: `objectCount` (the record with those going with it),
`objectsByType`, `relationshipCount`, `retainedAssociationCount` and `deletionPreviewToken`; counts,
never lists, since one record may own thousands (D121). The single `DELETE`'s `409` keeps its lists.

**Items are decided in order.** A record reached by several items' impacts belongs to the earliest
of them, as deleting them one after another would leave it. A record an earlier item of the same job
deleted (a child selected after its parent, in this chunk or an earlier one) is `applied` with
`action: "unchanged"` and `deletedWithItem`, that item's index (D122); a record deleted otherwise is
refused `REFERENCE_NOT_FOUND` as before. A run of consecutive delete items is decided and written
together as set statements (D123): their statements do not grow with the number of items or the
size or depth of their impacts. The deletions are audited per record and relationship with the job
as cause (live: in the feed, each record's relationships before its records; in a change set, a
`change-set-object` `deleted` entry per record, as its creates and updates have).

### Relationships by their ends (0.9 K3)

**`ensureNoRelation`** removes a relationship named by its type and its two records, so a client
removing many need not read each relationship's ID and version first, and sending the item again
answers `unchanged` (D129). When a relationship of that type joins `from` to `to`, it is deleted with
the single delete's rules, audit and feed entries and codes: `IMMUTABLE_RELATION` for a containment,
`REQUIRED_RELATION` for a required binding, and `VERSION_CONFLICT` when `expectedVersion` is sent and
stale (without it the relationship found is removed whatever its version). An item whose ends' types
the binding does not allow is `INVALID_RELATION_PAIR`. Its outcome is `deleted` with `relationId`,
or `unchanged` when the records are not related.

**A previewed set replacement claims what it showed** (D130). In a preview a `replaceRelationSet`
needs no `expectedRelationSetVersion`: it runs as if it claimed the set's version as found, and its
outcome or refusal names that version (`previousRelationSetVersion`, or `details.relationSetVersion`).
`POST /jobs/{jobId}/confirm` puts that version into each stored replacement that had no claim, in the
same step that carries delete tokens, so execution refuses `RELATION_SET_VERSION_CONFLICT` exactly the
sets changed since the preview and applies the rest (nothing under `atomic`). A `sample` preview's
unpreviewed replacements have no claim and are refused `VERSION_REQUIRED`; the UI therefore never
sends a replacement larger than one preview (D131). Without a preview the claim rules are as before.

## Exports (Base 0.9 J1)

- `POST /api/v1/exports` (registered with `INTEGRATION_JOBS_ENABLED`)
- `GET /api/v1/jobs/{jobId}/output`

An export writes a stated scope of one workspace to a file, as a background job of kind `export`.
`POST /exports` answers `202` with the job, `queued`. When the job is `completed`, its `output`
describes the file and `GET /jobs/{jobId}/output` serves it.

```json
{
  "workspaceKey": "main",
  "context": {"changeSetId": null, "publicationId": null},
  "scope": {
    "types": [
      {"objectTypeKey": "codelist", "where": [{"field": "codelist-code", "op": "eq", "value": "MOT"}]},
      {"objectTypeKey": "code"}
    ],
    "parentObjectId": null,
    "asOf": null
  },
  "include": {"relations": "withinScope"},
  "format": "jsonl"
}
```

- **`context`**: empty for live data, or one change set or one publication.
- **`scope.types`**: one or more object types, each once, each with its own `where`: the criteria of
  the [model-aware query](#model-aware-query-base-09-q3) (fields, `ancestor:<type>`, one `related`
  hop), which select the same records here in every context.
- **`scope.parentObjectId`**: only records below that record, at any depth.
- **`scope.asOf`**: a date. The types that declare an effective period export the records effective
  on it; the others are exported undated, and `output.asOfApplied` names the dated ones (D50).
- **`include.relations`**: `none`, `withinScope` (the default: both ends exported) or `all` (every
  relationship of an exported record, whose other end may not be in the file). Containment is never
  a relationship here: it is the record's parent.
- **`format`**: `jsonl`, `csv` or `xlsx`.
- No `Idempotency-Key`: an export changes nothing, and a repeated request makes a second job.

**One snapshot.** Everything in the file is read at one instant. A live export's
`output.feedPosition` is the feed head it read at, so a reader follows the feed from there and misses
nothing; a publication's is the publication's own position (`null` when it was published before
positions existed); a change set's is `null`, since change set work is not in the feed.

**The job.** `parameters` holds the request's `context`, `scope`, `include` and `format`; `result`
stays `null` (an export has no item outcomes); `progress.total` is the number of records and
relationships in scope, and `processed` rises as they are written. A completed export's `output`:

```json
{
  "format": "jsonl",
  "contentType": "application/x-ndjson",
  "counts": {"records": {"codelist": 1, "code": 240}, "relations": {"maps-to": 312}},
  "context": {"workspaceKey": "main", "changeSetId": null, "changeSetVersion": null, "publicationId": null},
  "feedPosition": 18422,
  "asOf": null,
  "asOfApplied": [],
  "modelReleaseId": "…",
  "bytes": 183044,
  "sha256": "…"
}
```

`counts.records` names every exported type, zero included. The manifest lives on the job only, never
in the file (D52). A cancelled or failed export has no `output` and no file, so a partial file
cannot be taken for a complete one. Cancel, model release changes, `JOB_FAILED` and retention
(`JOB_RETENTION_DAYS`) work as for [background jobs](#background-jobs); an export is restarted from
the beginning after a crash, never resumed half way.

**JSON Lines** (D49). One batch item per line: records first, as `upsert` items keyed by ID, then
relationships as `ensureRelation` items. Records come parents before children (by depth inside the
file, then the model's type order, then ID); the same data gives the same bytes.

```json
{"op": "upsert", "objectTypeKey": "code", "applicationKey": "rdm", "key": {"id": "…"}, "name": "Follow-up", "parent": {"id": "…"}, "expectedVersion": 3, "attributes": [{"attributeTypeKey": "code-value", "value": "08-IC-002"}], "initialRelations": []}
{"op": "ensureRelation", "relationTypeKey": "maps-to", "from": {"id": "…"}, "to": {"id": "…"}, "attributes": {}, "expectedVersion": 1}
```

- `parent` is left out for a record at the top level; values keep their declared types, and a record
  without a value has no entry for it.
- `expectedVersion` is the record's (or relationship's) version in the snapshot. The file sent back
  to `POST /batches` in the same workspace changes nothing: every item is `unchanged`, decided
  before the version (D24). Edited and sent back, it updates only the records nobody changed since
  the export; a record changed meanwhile is `VERSION_CONFLICT`.
- `initialRelations` carries the relationships the record's type requires (a required binding into
  it), so a record that requires one can be created from the file.
- Object IDs are unique across the instance: as they are, the file loads into the workspace it came
  from or into another instance. Into a second workspace of the same instance it loads with
  `otherWorkspaceIds: "counterparts"`, as that workspace's own records
  ([Counterparts](#counterparts-base-09-j5); D49 amended by 0.9 J5). Relationship IDs and history are
  not carried.

**CSV and XLSX** (D51) share one table layout, read back by the import (0.9 J2):

| Table | Columns |
| --- | --- |
| Records | `objectTypeKey`, `applicationKey` (0.9 J2, D71), `id`, `version`, `name`, `parentObjectId`, one `#{attributeTypeKey}` per attribute type an exported type binds (the model's order), `~parentPath` |
| Relationships | `relationTypeKey`, `id`, `version`, `fromId`, `toId`, one `#{attributeTypeKey}` per attribute type their bindings carry, `~fromName`, `~fromObjectTypeKey`, `~toName`, `~toObjectTypeKey` |

Attribute types are global, so a `#` column means one thing in every row; it is empty where the row's
type does not bind the attribute or the record has no value. The `#` keeps an attribute keyed `name`
or `id` apart from the built-in columns. `~` columns are for orientation and an import ignores them.

- **CSV** (`text/csv`): one file, UTF-8 with a BOM, RFC 4180, comma. Its header is the union of both
  tables' columns (`objectTypeKey`, `applicationKey`, `relationTypeKey`, `id`, `version`, `name`,
  `parentObjectId`, `fromId`, `toId`, the `#` columns, the `~` columns); records first, then relationships, a row
  being a record when `objectTypeKey` is filled. Values in the API's canonical text (dates ISO 8601,
  decimals as the API writes them, `true`/`false`, a JSON value as JSON text); an empty cell is no
  value. Text is written as stored: a spreadsheet opening the file may read a value beginning with
  `=` as a formula.
- **XLSX** (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`): the sheets
  `Records` and `Relationships`, each one named table (`records`, `relationships`) whose header row
  is the column keys, below a row of readable labels. Cells are typed: text as text (never a number
  or a formula), integers and decimals as numbers when Excel holds them exactly (up to 15 significant
  digits; beyond, as text in canonical form), booleans as booleans, dates as date cells; a date-time
  and a JSON value as text. A character XML cannot hold is written as Excel's `_xHHHH_`. The type
  columns and boolean columns offer dropdowns from a hidden `Lists` sheet. A table past a sheet's
  1,048,576 rows continues on `Records 2` (table `records_2`) and so on.

### A workbook for people (Base 0.9 J6)

`layout: "people"` (the default is `technical`, the tables above) asks for a workbook people work
in, shaped by one type's collection, which an import reads back as it was written (D179–D190):

```json
{
  "workspaceKey": "main",
  "scope": {"types": [{"objectTypeKey": "system-value", "where": []}]},
  "format": "xlsx",
  "layout": "people",
  "people": {
    "columns": ["name", "value-code", "related:system-value-maps-to-master", "active"],
    "sheets": ["system-value-maps-to-master"],
    "columnFields": {}
  }
}
```

- **`people.columns`**: the main sheet's columns as a table view names them (`name`, `id`, `path`,
  `createdAt`, `updatedAt`, an attribute the type binds, `related:<key>` or
  `related:<key>.<field>`), in that order; the name and the type's attributes when left out.
- **`people.sheets`**: relation keys or reverse keys of the type, each given a sheet of its own; a
  parent relationship is refused (a parent is the record's own field).
- **`people.columnFields`**: for a `related:<key>` column, the field its cells show instead of the
  related records' names (as `related:<key>.<field>` would).
- `include` is not read; one type, `xlsx` only. `output.layout` is `people` and `output.sheets` names
  the sheets in order (the hidden profile sheet left out); `counts.records` counts the main sheet's
  records and the owned records of a sheet, `counts.relations` the rows of relationship sheets.

**The main sheet**, titled with the type's plural name: one header row of the columns' labels
(frozen, with an AutoFilter), one row per record by name; values typed as the table shows them
(numbers, date cells, Yes or No for a boolean, offered as a dropdown, other text as text); then hidden
columns: each editable relation column's set version, `Record ID` and `Record version`. A relation
column holds every related record's name, or the field, in name order, `"; "` between them (no limit
per row, D190). The name column is filled in the type's hue and each relation column in its related
type's, the header in the type's, bold (the eight hues of the app's light theme, the slot the type's
position in the model, D184).

**What loads back** (D183). The name, the writable values, and a relation column of names or of a
unique field its one related type requires: its list replaces the record's set of that relationship,
under the set version written beside it. Every other column is a **summary**, its header marked
`(not imported)`: `id`, `path`, the timestamps, a read-only value, a field that identifies nothing, a
relationship over several types or a parent one, one with a sheet of its own, one reaching the type a
sheet of owned records holds, and one whose longest cell passes Excel's 32,767 characters (cut there,
and given a sheet of its own, D189). An empty cell never clears a value or a set, as for any import.

**A relationship's sheet** (D182), titled with the relationship's name:

- An **owning** relationship (one binding, from the type, required: the far records exist only
  through it) holds **those records**: their name and values, their parent by name (one column per
  type they may stand under), the owner by name, and hidden `Record ID`, `Record version` and
  `Owner ID`. A row edits its record; a row without an ID creates one under its parent, owned by its
  owner.
- Any other holds **the relationships**: the exported record and the related record by name, the
  relationship's values, the related type's display field for orientation (`(not imported)`), and
  hidden `Record ID`, `Related record ID` and `Relationship version`. A row adds a relationship or
  changes its values, never removes one (D187); a row without IDs names both records by name. A
  relationship over several types is written read-only.

**Its own profile** (D185, D186). A hidden sheet `Import profile` holds the import profile that reads
the workbook (A1 `rdm-engine import profile`, B1 what the workbook is as JSON: `objectTypeKey`,
`collection`, `workspaceKey`, `exportJobId`, `exportedAt`; column A from row 2 the profile's JSON),
checked when it is written. Every row claims its version, so a record or relationship changed since
the export is refused `VERSION_CONFLICT`, and a set changed since `RELATION_SET_VERSION_CONFLICT`.

**Columns per parent** (0.9 J6a, D191–D195). `people.ownedColumns` lays an owned relationship's sheet
out as one row per exported record and, for each parent, a column per field:

```json
"ownedColumns": {"object-has-translation": {"parents": ["<a translation group's ID>"], "fields": ["translated-name"]}}
```

- **`parents`**: records added to those already holding an owned record of an exported one (a new
  language's group), each one the owned type can stand under, in the exported context.
- **`fields`**: `name` or the owned type's writable attributes; those attributes when omitted.
- A header names its field and parent, and the parent's ancestor of the type the binding declares
  its records unique within (`uniqueToAncestorTypeKey`) when that is higher ("Translated name ·
  DE-MASTER · German"); the columns go by that ancestor's name, then the parent's. Hidden: a version
  per parent (`Version · …`) and `Record ID`.
- A cell holds its row's owned record under that parent. Filled where empty, the import creates one
  under the parent, owned by the row's record; edited, it updates it under the row's version claim;
  cleared, nothing changes. A pair with several owned records (possible outside a conditional
  uniqueness scope) holds their values joined by "; " and its version cell `not loaded`, so the
  import leaves it out and the rest of the row loads (D195).
- More than a sheet's 16,384 columns (parents × (fields + 1) + 2) fails the job with
  `INVALID_EXPORT_LAYOUT` at `/people/ownedColumns/<key>`.

**Lists to choose from** (0.9 J6a, D196–D198). A cell naming one other record offers a dropdown (an
Excel list rule) of the records its relationship may choose, from a sheet `List · <types>` (with the
relationship's name when its candidates narrow it): the records meeting the binding end's
candidates (K7, "The records a relationship may choose") in the context, by the value the cells hold, with
the name, the display field and the path; not imported. Such cells are: a main column of one
relationship holding one record, a relationship sheet's related record, an owned record row's
parent and owner. A pointer cell holds the name, or the field chosen for that relationship's main
column when it identifies its records (D198); IDs stay the hidden keys of the rows. A list rule
checks what is typed, not what is pasted: the import still refuses a value that finds no record.
`people.referenceLists` names the relationships whose cells get lists (relation keys of a column or a
sheet); every one when omitted, none with `[]`.

**Borders** (D199). Every written cell, header included, has a thin grey border.

**Refusals.** `422 INVALID_EXPORT_LAYOUT` with `details.path`: several types (`/scope/types`), a
format other than `xlsx` (`/format`), a column the type's table cannot show or named twice
(`/people/columns/{i}`), a relationship the type does not have, a parent one or named twice
(`/people/sheets/{i}`), a field for a column that is not a relation column of names or that the far
types lack (`/people/columnFields/{column}`), and `people` without `layout: "people"` (`/people`);
columns per parent for a relationship that owns nothing or has no sheet
(`/people/ownedColumns/{key}`), a parent the owned type cannot stand under or not in the context
(`…/parents/{i}`), a field that is not `name` or a writable attribute, or named twice (`…/fields/{i}`);
a list for a relationship the workbook does not name (`/people/referenceLists/{i}`).

**Following a job.** `GET /api/v1/jobs/{jobId}/events` (0.9 J1u) is a server-sent event stream for
any job: `event: job` with the job as `GET /jobs/{jobId}` answers it, sent at once and again after
each committed change of its state, progress, cancel request or output; the stream ends after the
job is `completed`, `failed`, `cancelled` or `expired`, and a job already finished is sent once.
Nothing is polled: the database tells the engine of each change at commit (D58). A comment line
(`: keep-alive`) every 15 s keeps an idle stream open; `Cache-Control: no-cache` and
`X-Accel-Buffering: no` let it pass proxies. Each event carries the whole job, so a client that
reconnects needs no `Last-Event-ID`. An unknown job is `404 JOB_NOT_FOUND` before the stream starts.

**Output.** `GET /jobs/{jobId}/output` serves the file with its content type,
`Content-Disposition: attachment; filename="export-{jobId}.{jsonl|csv|xlsx}"`, `ETag` (the SHA-256)
and `Repr-Digest: sha-256=:…:` (RFC 9530).

**Refusals.** At the request, before a job is stored: an unknown type, field, operator or binding is
`422 INVALID_QUERY` with `details.path`, a JSON pointer into the body (`/scope/types/1/where/0/field`;
an invalid date at `/scope/asOf`); `asOf` with no exported type that declares a period is
`422 AS_OF_NOT_SUPPORTED`; an unknown parent `404 PARENT_NOT_FOUND`; an unknown workspace, change
set or publication `404 WORKSPACE_NOT_FOUND`, `CHANGE_SET_NOT_FOUND`, `PUBLICATION_NOT_FOUND`; a
context of another workspace `422 WORKSPACE_CONTEXT_MISMATCH`; both context IDs, a type named twice
or a body of the wrong shape `422 REQUEST_VALIDATION_ERROR`. On the output: `404 JOB_NOT_FOUND`,
`404 JOB_HAS_NO_OUTPUT` (a batch), `409 JOB_NOT_COMPLETED` with `details.state`, `410 JOB_EXPIRED`
(retention removed the file), `410 JOB_OUTPUT_MISSING` (the file is gone from `JOB_FILE_DIR`).

## Imports (Base 0.9 J2, J3)

- `GET /api/v1/import-profiles`, `GET /api/v1/import-profiles/{profileKey}`
- `POST /api/v1/import-profiles`, `PUT /api/v1/import-profiles/{profileKey}`,
  `DELETE /api/v1/import-profiles/{profileKey}?expectedVersion=` (registered with
  `INTEGRATION_JOBS_ENABLED`)
- `POST /api/v1/imports`, `POST /api/v1/jobs/{jobId}/confirm` (registered with
  `INTEGRATION_JOBS_ENABLED`)
- `GET /api/v1/jobs/{jobId}/rows?status=…` (an import's outcomes by row, ADR-030 paging)

An import loads a file into one workspace, live or into a change set, as a background job of kind
`import`. The file is an XLSX workbook or a CSV file read through an **import profile**, or, without
one, a JSON Lines file of batch items or an export's CSV or XLSX tables.

### Import profiles

A profile says how a file's sheets and columns become records and relationships of the model. It is
stored once for the instance (D65) and names model keys only, never data of a workspace beyond the
fixed values it matches. A list pages in key order (ADR-030).

```json
{
  "key": "supplier-codes",
  "name": "Supplier codes",
  "csv": {"delimiter": ","},
  "sources": [
    {
      "sheet": "Codes",
      "headerRow": 1,
      "block": {"firstColumn": "A", "lastColumn": "H", "lastRow": null},
      "applicationKey": "master",
      "objectTypeKey": "master-value",
      "record": "upsert",
      "key": {"attributeTypeKey": "master-id"},
      "columns": [
        {"column": "Code", "attributeTypeKey": "value-code"},
        {"column": "Name", "field": "name"},
        {"column": "Order", "attributeTypeKey": "sort-order", "valueMap": "placeholders"},
        {"column": "List", "parent": {"objectTypeKey": "codelist", "matchBy": {"attributeTypeKey": "codelist-code"}}},
        {"column": "Systems", "relation": {"relationTypeKey": "system-value-maps-to-master", "direction": "incoming",
          "objectTypeKey": "system-value", "matchBy": {"attributeTypeKey": "value-code"}, "split": ";"}},
        {"columns": ["Web", "Phone"], "relationFlags": {"relationTypeKey": "offered-by", "objectTypeKey": "channel",
          "matchBy": {"field": "name"}, "targets": {"Web": "Web booking", "Phone": "Phone booking"}}},
        {"column": "Name (de)", "relatedRecord": {"relationTypeKey": "object-has-translation",
          "applicationKey": "translations", "objectTypeKey": "translation",
          "parent": {"objectTypeKey": "translation-group", "matchBy": {"attributeTypeKey": "group-code"}, "value": "DE-MASTER"},
          "attributeTypeKey": "translated-name"}},
        {"column": "Comment", "ignore": true}
      ]
    }
  ],
  "valueMaps": {"placeholders": {"N/A": null, "-": null}}
}
```

- **A source** loads one object type of one application from a sheet (the first sheet when
  `sheet` is left out; a CSV file is one sheet), from its `headerRow`, optionally within a `block`.
  Columns the profile does not name are ignored; a header names a column by its text.
- **`key`** finds a row's existing record: `{"attributeTypeKey"}`, an attribute declared `unique`
  whose value the row's own column supplies, or `{"column"}`, a column holding the public ID.
  Without a key every row creates a record, so sending such a file twice creates its records twice. A found record is updated (under `onExisting`, below);
  otherwise a record is created. `record: "existing"` finds each row's record by its key and writes
  only its relationships and related records (a sheet of translations, one row per language).
- **Bindings**, one kind per column: `field: "name"`; `attributeTypeKey` (a writable attribute the
  type binds); `parent`; `relation` (`relationTypeKey` and `direction` from the row's record,
  `outgoing` by default; `split` cuts a cell into several values; `replace: true` makes the matched
  records the whole set, a `replaceRelationSet`, instead of adding to it); `relationFlags` (columns
  that each stand for one record; a cell holding a boolean TRUE, 1 or one of `trueValues`, by default
  `x`, `yes`, `y`, `true`, `1` ignoring case, relates the row's record to it); `relatedRecord`;
  `ignore`.
- **`matchBy`** finds the record a cell names: `{"field": "name"}`, `{"field": "id"}` or
  `{"attributeTypeKey"}`, unique or not. It looks at the context's records and at the records the
  same file creates or changes, so a row can name a record another sheet or row of the file loads.
- **`relatedRecord`** (D70) is a record of `objectTypeKey` under the record `parent` finds (a fixed
  `value`, or the row's cell in `column`), related to the row's record by `relationTypeKey`; this
  column fills its `name` (`field`) or one attribute. Columns naming the same relation, type and
  parent fill one related record. It is the record that relationship already joins to the row's
  record under that parent (narrowed by `matchBy: {"attributeTypeKey"}`, one of its own values), or
  a new one; a new related record takes its name from its `field: "name"` column, else from its
  first value. A translation and a system mapping are profiles of this binding (ADR-032).
- **`valueMaps`** map a cell's text to another value (`null`: no value) before it is converted or
  matched; a column names one with `valueMap`.
- **One relationship per row** (0.9 J6): a `relation` binding's `idColumn` holds the related
  record's ID, which finds it when the cell is filled (the binding's own cell is matched otherwise);
  `attributes` (`[{"column", "attributeTypeKey"}]`, attributes the binding carries) are the
  relationship's values, written with it (an `ensureRelation` with `attributes`). Neither goes with
  `split` or `replace`. `versionColumn` claims a version: with `replace` the set's
  (`expectedRelationSetVersion`, from 0), otherwise the relationship's (`expectedVersion`).
- **`key.versionColumn`** (0.9 J6, D186) holds the version a row claims for the record its key finds
  (`expectedVersion`), so a record changed since the file was written is `VERSION_CONFLICT`.
  **`key.nameColumn`**, beside a `key.column` and with `record: "existing"`, finds a row's record by
  its name when its ID cell is empty (none: `REFERENCE_NOT_FOUND`; several: `REFERENCE_AMBIGUOUS`).
- **`relatedRecord.versionColumn`** (0.9 J6a, D194) holds the version a row claims for the related
  record it finds (`expectedVersion` on its upsert); the text `not loaded` leaves that related record
  out of the row (D195).
- **Sources run in order** of their references: a source whose parent, relationship or related
  record's parent names a type another source loads runs after it. Sources that reference each
  other are refused (`SOURCE_CYCLE`).

**Checked against the model.** Saving a profile checks it against the active model release, and a
profile is refused with every problem at once: `422 INVALID_IMPORT_PROFILE` with
`details.problems`, each `{path, code, message}` with a JSON pointer into the profile (codes
`UNKNOWN_APPLICATION`, `UNKNOWN_OBJECT_TYPE`, `TYPE_NOT_IN_APPLICATION`, `UNKNOWN_ATTRIBUTE`,
`ATTRIBUTE_NOT_BOUND`, `ATTRIBUTE_READ_ONLY`, `KEY_NOT_UNIQUE`, `KEY_NOT_BOUND`,
`UNKNOWN_RELATION_TYPE`, `RELATION_NOT_ALLOWED`, `PARENT_NOT_ALLOWED`, `UNKNOWN_VALUE_MAP`,
`FLAG_WITHOUT_TARGET`, `SOURCE_CYCLE`). A stored profile answers with `version`, `checkedAgainst`
(the release it was saved against), `createdAt`, `updatedAt`, and `valid` and `problems` as it reads
under the active release now, so a profile a later release broke shows what to fix.

`PUT` replaces the whole profile at `expectedVersion` in the body; `DELETE` takes `expectedVersion`
as a parameter. Refusals: `409 IMPORT_PROFILE_EXISTS`, `404 IMPORT_PROFILE_NOT_FOUND`,
`409 IMPORT_PROFILE_VERSION_CONFLICT` with `details.currentVersion`.

### Sending a file

`POST /api/v1/imports` takes `multipart/form-data` with two parts: `file`, and `request`, JSON:

```json
{
  "workspaceKey": "main",
  "changeSetId": null,
  "expectedChangeSetVersion": null,
  "profileKey": "supplier-codes",
  "profile": null,
  "format": null,
  "policy": "independent",
  "onExisting": "overwrite",
  "stage": "execute"
}
```

- The context as a batch's: `workspaceKey` for live data, or `changeSetId` with
  `expectedChangeSetVersion`.
- `profileKey` names a stored profile, `profile` gives one inline; neither for a JSON Lines file, an
  export's tables or a [workbook for people](#a-workbook-for-people-base-09-j6), which is read through
  the profile it carries (0.9 J6, D185): checked against the context's release as an inline one, and
  stored on the job as `parameters.profile` with `embedded`, what the workbook says it is.
- `format`: `xlsx`, `csv` or `jsonl`; otherwise from the file name (`.xlsx`, `.csv`, `.jsonl`,
  `.ndjson`). A legacy `.xls` workbook is refused: save it as XLSX.
- `policy`, `onExisting` and `otherWorkspaceIds` as on
  [batches](#batches-and-jobs-base-09-b1-b2-b3). A file without versions updates found records only
  with `onExisting: "overwrite"` (audited with the version it replaced); a row equal to its record is
  `unchanged` either way. With `otherWorkspaceIds: "counterparts"` another workspace's export loads
  as this workspace's own records ([Counterparts](#counterparts-base-09-j5)), and a profile's
  `matchBy: {"field": "id"}` finds a counterpart too.
- `stage: "execute"` runs the import as soon as its file is bound; `stage: "preview"` runs it
  without writing anything and waits for confirmation ([below](#preview-and-confirmation)).
- `Idempotency-Key` as on batches: it covers the request and the file's SHA-256, so a retry answers
  with the first job (`Idempotent-Replayed: true`) and another file under the same key is
  `422 IDEMPOTENCY_KEY_REUSED`.

It answers `202` with the queued job. Its `parameters` hold `policy`, `onExisting`,
`otherWorkspaceIds`, `stage`, the
`profile` as the job uses it (`key` and `version`, or the inline one, and its `definition`) and the
`file` (`name`, `format`, `bytes`, `sha256`). Refused before a job is stored: `413 IMPORT_TOO_LARGE`
(`details.setting` `IMPORT_MAX_BYTES`, `maximum`, `bytes`), `422 UNSUPPORTED_FILE_FORMAT`,
`422 INVALID_IMPORT_PROFILE` (a stored profile no longer valid, or an inline one, with its
problems), `404 IMPORT_PROFILE_NOT_FOUND`, the context's codes as for a batch, and
`422 REQUEST_VALIDATION_ERROR` (a part missing, or `request` of the wrong shape).

### What the job does

The worker first **binds** the file (`stage: binding`, `progress.total` `null`): it reads every row,
converts each value by its attribute's type, finds each row's record and resolves every match, then
stores the rows as batch items (`stage: applying`, `progress.total` the rows rejected plus the items)
and runs them as a [background batch](#background-jobs) does. Each item's `ref` names its row:
`{sheet}!{row}` (`csv!{row}`, `jsonl!{line}`), the row's number in the sheet. A row becomes an
`upsert` of its record (by its ID), then the upserts of its related records, then `ensureRelation`
items for its relationship and flag columns (or one `replaceRelationSet` per set). Records run by
source order, then depth, so parents come first; related records and relationships after every
record.

**A row that cannot be bound** is rejected before anything runs, with the column in
`details.column`, and its items are left out. A row with cells that do not convert names every one
of them: its error is the first cell's, and `details.cells` lists each failing cell's `column`,
`code` and `message`. The refusals: `INVALID_ATTRIBUTE_VALUE` (and the attribute's range
codes), `REFERENCE_NOT_FOUND` and `REFERENCE_AMBIGUOUS` (`details.count`) for a match finding no
record or several, `DUPLICATE_KEY_IN_FILE` (rows with one key and different values, all of them,
`details.rows` naming the others; rows with one key and equal values are one record, and their
relationship columns add up, D69), `REFERENCE_CYCLE` (rows whose parent columns form a ring),
`MISSING_RECORD_KEY` (an empty key attribute; an empty ID column creates a record, except under
`record: "existing"`), `NAME_REQUIRED` (a new record without a name),
`INVALID_NAME` (over 500 characters). Rejected rows are the job's first outcomes, in row order;
under `independent` the other rows load, under `atomic` nothing does and every item is
`unprocessed` with `BATCH_ROLLED_BACK`. A cell left empty, or mapped to `null`, gives no value: an
import never clears a value.

**Notices.** Once bound, an import's job carries `notices`: what the file as a whole means here,
each `{code, message, details}`, empty when there is nothing to say (null before binding and for
other jobs). `RECORD_IDS_OF_ANOTHER_WORKSPACE` (`details.workspaceKey`, `details.rows`) counts the
rows that name their records by IDs of another workspace's records, such as an export of that
workspace: those rows cannot load here, and each is refused naming that workspace (0.9 J4a, D49).
With `otherWorkspaceIds: "counterparts"` the notice is `RECORD_IDS_AS_COUNTERPARTS` (the same
details): the rows load as this workspace's own records (0.9 J5).

**A file that does not fit** fails the job before an item runs, writing nothing:
`IMPORT_FILE_MISMATCH` with `details.problems` (`SHEET_NOT_FOUND`, `HEADER_ROW_NOT_FOUND`,
`COLUMN_NOT_FOUND`, each at the profile's pointer; `NOT_A_TABLE_LAYOUT` without a profile),
`IMPORT_FILE_UNREADABLE` (not a workbook, not UTF-8, broken CSV quoting with its line),
`INVALID_IMPORT_PROFILE` (the profile no longer valid under the job's release),
`IMPORT_TOO_MANY_ITEMS` (more items than `BACKGROUND_JOB_MAX_ITEMS`, or `ATOMIC_JOB_MAX_ITEMS` for an
atomic import) or `IMPORT_FILE_MISSING`. Cancel, model release changes, `JOB_FAILED` and retention
work as for background jobs; the file is removed when the job finishes.

**Without a profile.** A JSON Lines file holds one batch item per line; a line that is not one is
rejected `REQUEST_VALIDATION_ERROR`. An export's CSV or XLSX tables (above) are read back by their
column keys: a records row is an `upsert` by `id` with `version` as `expectedVersion` (a `create`
when `id` is empty), its `#` attributes the type binds and can write; a relationships row an
`ensureRelation` with its version; `~` columns are ignored. A cell that is not an ID, a version or a
known type is `INVALID_CELL`. An unchanged export sent back changes nothing.

**Files.** XLSX cells are read as stored values, never formulas (a formula's cached value), dates
from date cells or ISO 8601 text, Excel's `_xHHHH_` escapes decoded. CSV is UTF-8 with or without a
BOM, RFC 4180, the profile's delimiter (a comma by default), a header row.

### Counterparts (Base 0.9 J5)

A record of workspace `A` loaded into workspace `B` with `otherWorkspaceIds: "counterparts"` becomes
`B`'s **counterpart** of it. Its ID depends on the original ID and `B`'s key alone: the name-based
UUID (SHA-1, as `uuid5`) of `{workspaceKey}/{id}` in the namespace
`2218e355-f627-4a22-a009-bebe5423891c`, marked as version 4 (every record ID the API accepts is a
version-4 UUID). In Python: `UUID(bytes=uuid5(NAMESPACE, f"{workspace_key}/{object_id}").bytes,
version=4)`. So:

- the same file sent again finds what its first load created: every row `unchanged`, and a
  corrected file loads only its corrected rows;
- a workspace's types load file by file, and a batch, an import or a profile matching by ID finds
  the counterparts an earlier load created;
- a change set of `B` uses `B`'s key, so publishing it gives the IDs a live load would;
- `B`'s own records, and IDs no record holds (a file from another instance), are used as given.

Translated: every record ID an item names (an upsert key, a create's ID, a parent, an update or
delete target, a relationship's ends, initial relations, a set's anchor and targets, a profile's ID
key column and `matchBy: {"field": "id"}`). Not translated: relationship IDs (`updateRelation`,
`deleteRelation`), since a relationship loaded from a file gets a new ID, so it has no counterpart.

An item applied to a counterpart reports the counterpart's `id` and the ID it was given as
`sourceId`. The file's `expectedVersion` is ignored on an item found as a counterpart (it is the
other workspace's record's version): `onExisting` decides, after `unchanged`. A reference to a
counterpart not loaded yet is `REFERENCE_NOT_FOUND`, naming the other workspace and saying to load
the file holding it first. Nothing links a counterpart to its original after the load.

### The binding report

Once its file is bound, every import's job (previewed or executed) carries `bindingReport`: per
source, in load order, what binding made of each column's cells. It is `null` before binding and for
a JSON Lines file; an export's table layout reports its `name` and `#` attribute columns with
`objectTypeKey` `null`.

```json
[{ "sheet": "Codes", "objectTypeKey": "master-value", "rows": 12, "rejectedRows": 2,
   "columns": [
     { "column": "Order", "binding": "attributeTypeKey", "target": "sort-order",
       "cells": 12, "empty": 1, "converted": 9, "valueMapped": 1, "refused": 1 },
     { "column": "List", "binding": "parent", "target": "codelist",
       "cells": 12, "empty": 0, "resolved": 10, "notFound": 1, "ambiguous": 1, "refused": 0 } ] }]
```

- `binding` is the profile's kind: `field` (the name), `attributeTypeKey`, `key` (an ID key column),
  `relatedRecord`, which count `converted`, `valueMapped` (a value map replaced the cell) and
  `refused` cells; or `parent`, `relation`, `relationFlags` (one entry per flag column), which count
  `refused` cells (a value that does not convert for an attribute match) and the values that found
  one record (`resolved`), none (`notFound`) or several (`ambiguous`). A split cell holds several
  values; a flag column counts an unset cell as `empty`.
- Every cell is counted, a refused row's too, so a column bound wrongly shows at once: a date column
  with every cell refused, a match column resolving nothing.
- `rejectedRows` counts the source's rows refused by binding.

### Preview and confirmation

An import sent with `stage: "preview"` is bound as an execution would be, then its items run against
the data in one transaction that is rolled back: no record, relationship, feed entry, audit entry or
event is written, and a change set keeps its version. The job's `stage` reads `binding`, then
`previewing`; it then waits in `awaiting_confirmation` with `preview`:

```json
{
  "coverage": "complete",
  "items": { "total": 30, "previewed": 30 },
  "rows": { "total": 12, "previewed": 12, "rejected": 4 },
  "counts": { "created": 1, "updated": 1, "unchanged": 6, "deleted": 0, "rejected": 4 },
  "result": "partial",
  "previewedAt": "2026-10-08T09:00:00Z"
}
```

- The items run **independently, whatever the policy**, so every refusal shows at once; `result` is
  what execution would give under the request's policy: `rejected` for an `atomic` import with any
  refusal, since nothing would be written.
- **`coverage`** is `complete` when every item ran and `sample` when only the first
  `JOB_PREVIEW_MAX_ITEMS` did (10,000, reported as `integrationJobs.limits.previewMaxItems`; named
  `IMPORT_PREVIEW_MAX_ITEMS` and `importPreviewMaxItems` before 0.9 K2, which renamed them).
  Binding still covers every row, so every binding refusal and the whole binding report are there.
  Items run records first and relationships last, so a sample may preview a row's record and not its
  relationships; a row counts in `rows.previewed` only when all its items ran.
- The preview's outcomes read like an execution's (`/items`, `/rows`); `applied` there means it would
  apply. The preview holds the workspace (or the change set's claim) while it runs, as an atomic job
  of its size does.

**`POST /api/v1/jobs/{jobId}/confirm`** (no body) answers `202` with the job queued again and
`confirmedAt` set. The worker binds the stored file again and runs it as `stage: "execute"` would,
so records created, renamed or removed since the preview count: **execution is authoritative**, and
its outcomes replace the preview's (`preview` stays on the job). Confirming a job already confirmed
answers `202` with it unchanged, so a retried request is safe. Refused, leaving the job waiting: the
context's codes checked again as at submission (`409 MODEL_RELEASE_CHANGED`,
`404 WORKSPACE_NOT_FOUND`, `404 CHANGE_SET_NOT_FOUND`, and `409 CHANGE_SET_VERSION_CONFLICT` when
the change set changed since the request's `expectedChangeSetVersion`). A job that is not a waiting
preview (an import or a batch sent with `execute`, an export, a cancelled preview) is
`409 JOB_NOT_AWAITING_CONFIRMATION` with `details.state`; a preview past its retention
`410 JOB_EXPIRED`.

A waiting preview is cancelled at once by `POST /jobs/{jobId}/cancel`; left unconfirmed, it expires
`JOB_RETENTION_DAYS` after its preview ended, and its file goes with it. A retry of the preview's
request with its `Idempotency-Key` answers with the waiting job.

### Outcomes by row

`GET /api/v1/jobs/{jobId}/rows` lists an import's rows in source, then row order (ADR-030 paging),
each with its items' outcomes gathered:

```json
{ "ref": "Codes!4", "sheet": "Codes", "row": 4, "status": "rejected",
  "actions": { "created": 0, "updated": 0, "unchanged": 0, "deleted": 0 },
  "outcomes": [{ "index": 2, "ref": "Codes!4", "status": "rejected",
                 "error": { "code": "INVALID_ATTRIBUTE_VALUE", "message": "…",
                            "details": { "column": "Order", "cells": [ … ] } } }] }
```

A row's `status` is its worst item's (`rejected`, then `unprocessed`, then `applied`), `actions`
counts its applied items, and `outcomes` holds its rejected and unprocessed items; `status=` keeps
rows of one status. Every item of one row reads at `GET /jobs/{jobId}/items?ref=Codes!4`. A sample
preview lists the rows it has outcomes for. A batch or an export has no rows:
`404 JOB_HAS_NO_ROWS`.

## Change feed (Base 0.9 F1, F2)

- `GET /api/v1/workspaces/{workspaceKey}/feed?after=…&pageSize=…&kind=…&objectTypeKey=…`

Every change to a workspace's live data, in commit order. Each has a **position**: a per-workspace
integer, gapless and strictly increasing in commit order. A live write takes its positions under the
workspace lock it already holds, so a transaction's entries are consecutive and one that rolls back
leaves no gap. Change-set edits, validation and discard, and model administration change no live
data and take none. The feed starts empty at revision `20261003_02`; earlier changes remain in
record history.

| Source | Entries |
| --- | --- |
| A live create, update, move, value write or delete of a record | One `object` entry per record |
| A live relationship create, update or delete, a mapping save | One `relation` entry per relationship |
| A batch | Its applied items' entries, with the job as `cause` |
| Publishing a change set | One entry per record and relationship it changed in live data, with the publication as `cause`, in this order: records created, updated or `reclassified`; relationships removed; relationships created or updated; records removed. Then the publication's `published` entry, whose position is the publication's: live data at that position is the publication (D15, D32) |
| Withdrawing a publication | One `withdrawn` entry |

A containment relationship is the record's parent, which the record's entry names
(`parentObjectId`); it is never an entry of its own, live or published.

**Parameters.** `after` (default `0`) is the last position the reader processed. A position is public
and stable, so it is the resume token itself. `pageSize` is 1–1,000 (default 500). `kind`
(`object`, `relation`, `publication`) and `objectTypeKey` are repeatable. Repeated values match any
of them, and the two filters combine. `objectTypeKey` matches object entries whose type, or for
`reclassified` whose previous type, is listed; relation and publication entries never match it
(D34). A filtered page scans at most ten pages' worth of positions, so it may hold fewer entries,
or none, with `nextAfter` advanced. A sparse filter never costs an unbounded scan.

**Response.**
- `items` in position order.
- `nextAfter`: the `after` to pass next.
- `headPosition`: the highest committed position.
- `earliestPosition`: the lowest `after` + 1 the feed answers (see Retention).

The reader is caught up when `nextAfter` equals `headPosition`. An entry:

```json
{
  "position": 18422,
  "eventId": "…",
  "occurredAt": "2026-10-14T10:14:03Z",
  "kind": "object",
  "action": "updated",
  "id": "…",
  "version": 7,
  "objectTypeKey": "…",
  "applicationKey": "…",
  "changedFields": ["name", "attributes"],
  "attributeTypeKeys": ["…"],
  "cause": {"kind": "user"},
  "modelReleaseId": "…"
}
```

- **`action`:** `created`, `updated`, `deleted` and `reclassified` (with `previousObjectTypeKey`)
  for objects; `created`, `updated` and `deleted` for relations; `published` and `withdrawn` for
  publications, whose `id` is the publication's and `version` its number. Readers ignore actions
  they do not know.
- **Relation entries** carry `relationTypeKey`, `fromObjectId` and `toObjectId` instead of the
  object fields; they identify the relationship after a delete.
- **`changedFields` and `attributeTypeKeys`** use the record history's vocabulary: names, never
  values (D16). A reader that needs values reads the record.
- **`cause`** is `{"kind": "user"}` for a single write, `{"kind": "job", "id"}` or
  `{"kind": "publication", "id"}`.
- **`modelReleaseId`** is the release the change ran under.

**Refusals:**
- an unknown workspace: `404 WORKSPACE_NOT_FOUND`
- `after` below 0, or `pageSize` out of range: `422 REQUEST_VALIDATION_ERROR`
- `after` past the head: `409 FEED_POSITION_AHEAD`, with `details.headPosition` (D33). Such a position
  was not read from this workspace's feed, or the database was restored to an earlier state; the
  reader re-reads a baseline.
- `after` below `earliestPosition − 1`, `0` included: `410 FEED_POSITION_EXPIRED` (see Retention).

**Retention and recovery (F2, D8, D40).** Entries older than `FEED_RETENTION_DAYS` (default 30,
reported as `changeFeed.retentionDays` by `GET /capabilities`) expire from the feed; record history
keeps them. `earliestPosition` is the position of the first entry within the period, or `headPosition
+ 1` when every entry is older, but never more than the active publication's `feedPosition + 1`. A
workspace without an active publication with a position (never published, withdrawn, or published
before the feed existed) has nothing to re-read, so nothing expires and `earliestPosition` is `1`.

```json
{
  "error": {
    "code": "FEED_POSITION_EXPIRED",
    "message": "Position 0 has expired: the feed answers from position 500001 on. …",
    "details": {
      "earliestPosition": 500001,
      "headPosition": 1000000,
      "publication": {"id": "…", "publicationNumber": 12, "feedPosition": 500000},
      "export": {"href": "/api/v1/exports"}
    }
  }
}
```

To recover, the reader reads the named publication (the lists with `publicationId`), then follows the
feed with `after` set to its `feedPosition`. The publication equals live data at that position, so
the reader misses nothing. Or it exports live data (`details.export`, [Exports](#exports-base-09-j1))
and follows the feed from the export's `output.feedPosition`, which works in a workspace without a
publication too (0.9 J1, D41). A workspace without a publication still keeps every entry (D54).

A retired workspace's feed stays readable. The feed is ungated like other reads until 0.12 (D10).

## Consumer API (Base 0.9 C2–C6, C10, C14–C16)

A separate, read-only tier at `/api/consumer`, whose contract each consumer API definition in the
active model release declares ([CONSUMER_API.md](CONSUMER_API.md)). Its routes are not in the
management OpenAPI document: each definition serves its own, and the API index lists them
([below](#api-index-and-documents)). Every read takes live data by default, or one publication with
`publication` ([below](#publications-and-caching)), and any read can be dated with `asOf`
([below](#business-dates-asof-on-the-consumer-api)).

### Get by ID

```text
GET /api/consumer/{consumerApi}/v{contractVersion}/objects/{id}?workspace=…&{parameters}
```

Returns the definition's shared object for the record whose **object ID** is `{id}`, read live:

```jsonc
// RDM-Workspace: default
{
  "objectType": "Ledger",                 // the type's public name
  "ledgerId": "7f3c…",                    // the id role: the object ID
  "code": "LED-1",                        // first source with a value, then default, then null
  "name": "Alpha ledger",
  "isActive": false,
  "score": 50,                            // integers and booleans as JSON values
  "openedOn": "2026-03-04",               // dates YYYY-MM-DD; decimals as strings; dateTime in UTC
  "parent": null,                         // or {objectType, ledgerId, code, name}: the roles declared,
                                          // keyed by their output names
  "path": "",                             // ancestors' names joined with "/", top down
  "hierarchy": [],                        // the same names as a list, without the object itself
  "pairedToken": { "tokenName": "Paired token", "tokenCode": "TK-1" },  // at most one: object or null
  "permits": [                            // many: an array ordered by name, then ID; [] when empty
    { "permitName": "Permit a", "regionName": "Region south" }          // ancestor:<type>.<field>
  ]
}
```

- Every declared field is always present and no undeclared field appears. A field takes the first of
  its sources that has a value, then its `default`, then `null`; empty text is no value.
- `parent` holds the fields its declaration lists, each keyed as the object's own field is: the
  `id`, `code` and `name` roles by their output names (`ledgerId` above), and `objectType`. A
  consumer reading a field from an object or its parent uses one name (C-D75).
  `parent.objectType` is `null` when the parent's type is not exposed.
- A projection field with the source `objectType` gives each item's public type name, as the
  object's own `objectType` does. It is allowed where the definition exposes every type the
  projection reaches (C-D73).
- `workspace` selects the workspace (default: the deployment's default); the response names it in the
  `RDM-Workspace` header, also on an error after the workspace was resolved.
- Change sets are never read; a record created in an open change set is not found until published.
- The definition's parameters apply ([below](#parameters)): on a set of one, a parameter that filters
  the record out answers `404 OBJECT_NOT_FOUND`, and a `projection` parameter limits that
  projection's items.

### Lists

```text
GET /api/consumer/{consumerApi}/v{contractVersion}/lists/{listKey}?{within}=…&{filters}&workspace=…
    &pageSize=…&cursor=…|position=…|from=end|seek=…&includeTotal=true
```

A page of the definition's list: the records of the list's `objectType` in the workspace, each item
the shared object above (equal to get by ID's answer for the same record and parameters).

- **Without a parent value** the list holds every record of its type, each showing its `parent`.
- **With a parent value** (the name the list is `within`, by object ID only) it keeps the records of its
  type anywhere below that record, at any depth: cities filtered on a country include those under one
  of its regions, whose `parent` stays the region. Several IDs, repeated or comma-separated, keep the
  records below any of them.
- **Order:** the list's `sortBy` attribute (records without a value last), then name, then creation
  order; without `sortBy`, name then creation order.
- **Paging** as on the management lists (ADR-030): `cursor` (`nextCursor`, `prevCursor`, `anchor`),
  `position`, `from=end`, `seek` (by the sort value: the `sortBy` attribute's, else the name) and
  `includeTotal=true`. `pageSize` is 1–100, default 20. A cursor binds the workspace, the parent IDs,
  every parameter value and the contract version.

```jsonc
// RDM-Workspace: default
{ "items": [ … ], "workspace": "default", "publication": null, "pageSize": 20,
  "nextCursor": "…", "prevCursor": null, "anchor": "…", "totalCount": 412, "startIndex": 0 }
```

`totalCount` and `startIndex` are `null` unless `includeTotal=true`.

### XREF

```text
GET /api/consumer/{consumerApi}/v{contractVersion}/xref?query=…&{parameters}&expect=any|one&workspace=…
    &pageSize=…&cursor=…|position=…|from=end
```

Finds the records of the definition's exposed types that the query's terms match, scored by the
definition's `match`, best first. Each result is the shared object above (get by ID's answer for the
same record) with `matchScore`, an integer, after the declared fields.

- **Terms.** `query` holds one or more terms, comma-separated or repeated, listed as
  [parameter values](#parameters) are (a comma inside a term is `%2C`). Surrounding spaces are
  trimmed and empty terms dropped. An object's score is its best score over the terms.
- **Own score for a term.** Each `match.own` rule compares the term with a field of the object: an
  `exact` weight applies when the field equals the term ignoring case (a typed field by its parsed
  value, the object ID as given); a `contains` weight when a text field holds it, ignoring case. The
  exact weights that apply add up; the contains weights add up and count only when no exact weight
  applied.
- **Promoted score.** Each `match.promoted` entry reads its projection's related records. A related
  record takes the weight of its first matching rule in `firstMatch` order and passes it to the
  exposed objects it relates to through the projection. With `preferTargetTypes`, a related record
  that relates to an object of a preferred type passes its weight only to those. An object's score is
  the higher of its own and its best promoted score.
- **Order:** score (highest first), then the type's public name, then name, then object ID.
- **Limits.** `contains` needs a term of **at least 3 characters**; a shorter term matches exactly
  only. A query whose terms match **more than 10,000 records** (counting its own matches and the
  related records promotion reads) is refused with `400 QUERY_TOO_BROAD` rather than capped or read
  slowly: use a longer or more specific term. Parameters do not count towards the limit: it counts
  what the terms match before parameters narrow it. A query holds **at most 100 terms**.
- **Parameters.** The definition's [parameters](#parameters) narrow the lookup with their meaning on
  lists: an object is a result when it scored and every parameter keeps it, with the score it has
  without them. `totalCount`, the pages and `expect=one` (its top result and tie) follow the narrowed
  set, so a parameter can resolve an `AMBIGUOUS_MATCH`. An `onRelated` filter limits that related
  block's items in each result; with `keepOnlyMatching` it also drops the objects left with none.
- **`scoreOnlyMatching`.** An `onRelated` filter declaring `scoreOnlyMatching`, when the request
  gives it, also limits promotion: in every `alsoMatchThrough` entry over its related block, only the
  related records it matches pass their weight. The objects' own scores are untouched, and
  `preferTypes` chooses among the owners of the records that pass.
- **Paging** as on lists, without `seek` (a score is not something a caller seeks) and without
  `includeTotal`: `totalCount` and `startIndex` are always given. A cursor binds the terms, the
  parameter values, the workspace and the contract version.
- **`expect=one`** answers the single top result as a bare object, as get by ID does; no paging name
  applies with it. A lookup its exact matches settle (the top score is above the most any contains
  match could give, and no contains match could lower it) is answered without reading contains
  matches, so it is refused as `QUERY_TOO_BROAD` only when its exact matches exceed the limit; a
  lookup they do not settle reads contains matches and counts them as above.
- A definition without `match` matches nothing.

```jsonc
// RDM-Workspace: default
{ "results": [ { "objectType": "Ledger", "ledgerId": "7f3c…", "code": "LED-7", …, "matchScore": 500 } ],
  "query": ["led-7"], "workspace": "default", "publication": null, "pageSize": 20,
  "nextCursor": null, "prevCursor": null, "anchor": "…", "totalCount": 1, "startIndex": 0 }
```

| Status | Code | When |
| --- | --- | --- |
| 400 | `QUERY_REQUIRED` | No `query`, or only empty terms |
| 400 | `TOO_MANY_TERMS` | More than 100 terms; `details.limit` and `details.count` |
| 400 | `QUERY_TOO_BROAD` | The terms match more than 10,000 records; `details.limit` and `details.minimumContainsLength` (3) |
| 400 | `INVALID_EXPECT` | `expect` other than `any` or `one` |
| 400 | `PARAMETER_NOT_SUPPORTED` | `seek`, `includeTotal`, a paging name with `expect=one`, or a list's parent parameter |
| 404 | `NO_MATCH` | `expect=one` and nothing matched |
| 409 | `AMBIGUOUS_MATCH` | `expect=one` and the top score is shared; `details.count` and `details.candidates` (the tied objects' `id`, `objectType`, `name` and `matchScore`, at most 10) |

The API, workspace, paging and parameter refusals (`UNKNOWN_OBJECT_TYPE`) are those of the table
below.

### Batch resolve

```text
POST /api/consumer/{consumerApi}/v{contractVersion}/resolve?workspace=…
```

Resolves many values in one call, for a flow translating a file of codes. It is a read: the body
only carries the items, and nothing changes.

```jsonc
{ "defaults": { "kind": "Ledger" },                      // parameters for every item
  "items": [
    { "ref": "row-1", "query": "LED-7" },                 // as xref?query=LED-7&expect=one
    { "ref": "row-2", "query": ["LED-7", "TK-9"], "kind": "Entry" },
    { "ref": "row-3", "id": "7f3c…" } ] }                 // as get by ID
```

- **Items.** Each item holds exactly one of `query` (a text or a list of texts, its terms) and `id`
  (an object ID), an optional `ref` (1–200 characters, echoed in its outcome) and the definition's
  [parameters](#parameters) by name. `defaults` gives parameters to every item; an item's own value
  for a name replaces the default's. Values are a text or a list of texts, alternatives as on the
  URL; JSON lists them itself, so a comma is part of a value (`"Bonds, Notes"` is one term).
- **Each item is resolved as its single read:** by `query` as [XREF](#xref) with `expect=one`
  (scoring, parameters, ties and the limits of 100 terms, 10,000 matches and 3 characters for
  contains), by `id` as [get by ID](#get-by-id).
- **Outcomes** come in item order, unpaged, each with `index` (from 0), `ref` and `status`:
  `found` with `object`, the single read's answer (with `matchScore` for a query); or `not_found`
  (`NO_MATCH`, `OBJECT_NOT_FOUND`), `ambiguous` (`AMBIGUOUS_MATCH` with its `candidates` and
  `count`) or `rejected` with `error`, the single read's error. A rejection's `details.pointer`
  points into the item, or into `defaults` for a value given there. `counts` sums the statuses.
  A processed batch answers `200` whatever its outcomes.
- **Limit.** At most `CONSUMER_RESOLVE_MAX_ITEMS` items (1,000), reported by `GET /capabilities` as
  `consumerApi.resolveMaxItems`; more are refused as a whole and nothing is resolved.
- **Crosswalk.** A [`to.` name](#crosswalk) in `defaults` or in an item; an item's `to.` name
  replaces a different one from `defaults`. A missing or ambiguous target is `not_found`
  (`TARGET_NOT_FOUND`) or `ambiguous` (`AMBIGUOUS_TARGET`), pointing at where the `to.` name was
  given; two `to.` names in an item reject it, in `defaults` refuse the request (`MULTIPLE_TARGETS`).
- The URL takes `workspace` and `publication`, which apply to every item; `publication` in an item
  or in `defaults` is `PARAMETER_NOT_SUPPORTED`. `asOf` (C16) arrives with its package. The answer
  names the publication read in `publication` (`null` when live) and in `RDM-Publication`. Batch
  resolve answers no `ETag`: it is a `POST`.

```jsonc
// RDM-Workspace: default
{ "items": [
    { "index": 0, "ref": "row-1", "status": "found", "object": { "objectType": "Ledger", …, "matchScore": 500 } },
    { "index": 1, "ref": "row-2", "status": "ambiguous",
      "error": { "code": "AMBIGUOUS_MATCH", "message": "…", "details": { "count": 2, "candidates": [ … ] } } },
    { "index": 2, "ref": "row-3", "status": "rejected",
      "error": { "code": "UNKNOWN_OBJECT_TYPE", "message": "…", "details": { "pointer": "/defaults/kind", "…": "…" } } } ],
  "workspace": "default", "publication": null,
  "counts": { "found": 1, "notFound": 0, "ambiguous": 1, "rejected": 1 } }
```

An item is `rejected` for what it holds, and the other items are still resolved:

| Code | When |
| --- | --- |
| `QUERY_OR_ID_REQUIRED` | Both or neither of `query` and `id` |
| `UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED` | A name the API does not know, or one a lookup does not apply (`expect`, a paging name, a list's parent parameter) |
| `MULTIPLE_TARGETS` | Two `to.` names in the item |
| `QUERY_REQUIRED`, `TOO_MANY_TERMS`, `QUERY_TOO_BROAD`, `UNKNOWN_OBJECT_TYPE` | As the single read refuses them |

The request is refused as a whole:

| Status | Code | When |
| --- | --- | --- |
| 400 | `REQUEST_VALIDATION_ERROR` | The body is not JSON or not the shape above (`items` missing or empty, an item or a value of the wrong type, an unknown top-level name); `details.pointer` |
| 400 | `UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`, `MULTIPLE_TARGETS` | In `defaults` (`details.pointer`), or a definition parameter, a `to.` name or another name in the URL |
| 413 | `BATCH_TOO_LARGE` | More items than `CONSUMER_RESOLVE_MAX_ITEMS`; `details.setting`, `maximum` and `items` |

The API and workspace refusals are those of the [parameters](#parameters) table.

### Parameters

Every filter the definition declares is a query parameter of the same name, and applies to get by ID,
to every list (C-D31), to [XREF](#xref) and to [batch resolve](#batch-resolve)'s items:

| Filter | Effect |
| --- | --- |
| `byType` | Keeps records of the named public types; an unknown name is `400 UNKNOWN_OBJECT_TYPE` |
| `under` | Keeps records below a matching record of its types, at any depth |
| `linkedTo` | Keeps records linked to a matching record of its types through its `through` routes: a related block, `itself` (the record itself matches), or `sharedWith:<related>` (both relate to one related record; the matching record itself is kept only by `itself`) |
| `onRelated` | Limits the related block's items to those matching on `matchOn` (`ancestor:<type>.<field>` included); `keepOnlyMatching` also drops records left with none; on XREF, `scoreOnlyMatching` also limits which related records pass scores through the block |

- A value matches a field when it equals it: text ignoring case, typed values by their type. A value
  that does not parse for a typed field does not match that field.
- A parameter takes several values, repeated (`token=A&token=B`), comma-separated (`token=A,B`) or
  both; they are alternatives. Different parameters combine with AND.
- Values are listed as OpenAPI 3 serialises a list in a query (`style: form`, RFC 3986): repeated,
  or separated by a literal comma in the URL. A comma inside a value is percent-encoded as `%2C`, as
  every HTTP library sends it: `token=Bonds%2C%20Notes` is one value, `token=Bonds,Notes` two. A
  backslash has no special meaning.
- `scoreOnlyMatching` matters only to XREF; `asOf` arrives in C16 (until then `400 UNKNOWN_PARAMETER`).
  `workspace` and `publication` are reserved names on every read.

| Status | Code | When |
| --- | --- | --- |
| 404 | `CONSUMER_API_NOT_FOUND` | No definition has this `consumerApi` in the active release |
| 404 | `CONTRACT_VERSION_NOT_FOUND` | The definition serves another contract version; `details.contractVersion` names it |
| 404 | `OPERATION_NOT_OFFERED` | Get by ID, XREF or batch resolve on a definition that does not list the operation under `operations` (C18, C-D132); `details.operation` names it |
| 404 | `WORKSPACE_NOT_FOUND` | Unknown or retired workspace |
| 404 | `OBJECT_NOT_FOUND` | No record with this object ID in the workspace, one of a type the definition does not expose, or one the parameters filter out |
| 404 | `LIST_NOT_FOUND` | The definition declares no list `{listKey}` |
| 404 | `PARENT_NOT_FOUND` | A parent value is no record of the list's parent types in the workspace; `details.parents` names them |
| 400 | `UNKNOWN_PARAMETER` | A name the API does not know; `details.parameters` names them |
| 400 | `PARAMETER_NOT_SUPPORTED` | A name the API knows that this read does not apply: a paging name on get by ID, `query` or `expect` off XREF, or a list's parent parameter on get by ID or another list |
| 400 | `UNKNOWN_OBJECT_TYPE` | An `objectType` value that is not an exposed public name; `details.publicNames` lists them, `details.path` names the parameter |
| 400 | `MULTIPLE_TARGETS` | Two `to.` names; `details.parameters` names them |
| 404 | `TARGET_NOT_FOUND` | Get by ID or XREF `expect=one` with a `to.` name its object has no matching item for |
| 409 | `AMBIGUOUS_TARGET` | Get by ID or XREF `expect=one` with a `to.` name its object has several matching items for |
| 400 | `INVALID_PAGE_SIZE` | `pageSize` outside 1–100 |
| 400 | `INVALID_PAGE_PARAMETER` | `from` other than `start` or `end`, or `includeTotal` other than `true` or `false` |
| 400 | `INVALID_CURSOR`, `CONFLICTING_PAGE_PARAMETERS`, `INVALID_POSITION`, `INVALID_SEEK` | The shared paging refusals, with the consumer tier's status for a request error |

### Crosswalk

"Code X in system A: what is it in system B?" in one read. On get by ID, lists, XREF and batch
resolve, `to.{name}` names an `onRelated` filter the definition declares `"crosswalk": true`,
with values matched by that filter's `matchOn`:

```text
GET …/xref?query=CHF&system=SAP&to.system=Oracle&expect=one
GET …/objects/{id}?to.language=es
```

- **It changes no object, score, order or total.** The plain parameter (`system=SAP`) keeps its
  meaning, `keepOnlyMatching` and `scoreOnlyMatching` included, and `to.system` may be sent without it. Cursors
  do not bind `to.` values, so a cursor from a page without it reads the next page with it.
- **The output.** The projection shows the items `to.system` matches in place of the plain
  parameter's (another parameter's limit over the same projection still applies), and each object
  carries them again as `target`, after its declared fields and before `matchScore`.
- **One object, one target.** Get by ID, XREF `expect=one` and a batch item answer `target` as the
  single item; none is `404 TARGET_NOT_FOUND`, several `409 AMBIGUOUS_TARGET`. Their details name the
  object (`id`, `objectType`) and the `parameter`; an ambiguity adds `count` and up to 10 `targets`,
  as projected. The object is decided first: a shared top score stays `409 AMBIGUOUS_MATCH`.
- **Pages refuse nothing.** On a list or XREF `expect=any`, `target` takes the projection's shape: an
  array (empty where an object has none), or an object or `null` for a projection of one.
- **One target per read.** A second `to.` name is `400 MULTIPLE_TARGETS`; several values of one are
  alternatives, so `to.system=Oracle,SAP` with `expect=one` is ambiguous where both exist. A `to.`
  name of an unknown filter, or one without `crosswalk`, is `400 UNKNOWN_PARAMETER`, its message
  naming the filters that have it.
- Turning `crosswalk` off in a later release needs a new contract version; turning it on does not.

```jsonc
// GET …/xref?query=LX&to.watchRegion=South&expect=one
{ "objectType": "Ledger", "ledgerId": "…", "code": "LX", …,
  "watchedPermits": [ { "watchedName": "South desk" } ],
  "target": { "watchedName": "South desk" },
  "matchScore": 500 }
```

### Business dates (`asOf`) on the consumer API

"Which values apply on 1 July?" `asOf=YYYY-MM-DD` on get by ID, lists, XREF and batch resolve (in
its URL) keeps the records effective that day by their type's declared effective period, the rule of
the management lists ([above](#effective-periods-and-asof-base-09-q4)): no start after the date, no
end on or before it, an empty start or end open.

```text
GET …/lists/{listKey}?asOf=2026-07-01           the list's records effective that day, every page
GET …/objects/{id}?asOf=2026-07-01              the record, or 404 if it is not effective that day
GET …/xref?query=CHF&asOf=2026-07-01            dated types filtered, undated ones not
POST …/resolve?asOf=2026-07-01                  every item as its single read answers
```

- **Only a declared period dates a record.** A list of a type without one, and a get by ID of a
  record of such a type, are `400 AS_OF_NOT_SUPPORTED`; a date attribute alone never makes a type
  dated. A dated record not effective that day is `404 OBJECT_NOT_FOUND` on get by ID, as a
  parameter that filters it out is.
- **XREF and batch resolve across types** filter the dated types and leave the others unfiltered.
  A lookup that can return no dated type (all exposed types undated, or an `objectType` parameter
  naming only undated ones) is `400 AS_OF_NOT_SUPPORTED`: an undated answer would look dated. In
  batch resolve each item answers as its single read: a lookup with no dated type, or a by-ID item
  naming a record of an undated type, is `rejected` (`details.pointer` at the item, or its `id`).
  `asOf` belongs to the request: in `defaults` or an item it is `400 PARAMETER_NOT_SUPPORTED`.
- **Only the returned records are dated.** Projection items, the parent, `path` and `hierarchy`, the
  records a parameter matches and the records that promote an XREF score are read as without
  `asOf`. A consumer that needs a projected record's validity declares its period fields as
  projection fields.
- **What was dated** is named: the list, XREF page and batch resolve bodies carry `asOfApplied`, the
  dated public type names, and every answer to a dated read carries them in the
  `RDM-As-Of-Applied` header (comma-separated), also get by ID and XREF `expect=one`. Without `asOf`
  neither appears.
- **Scores, order and paging** are those of the same read without the date, over the records it
  keeps. List and XREF cursors bind the date: a cursor sent with another date or none is
  `400 INVALID_CURSOR`.
- `asOf` combines with `publication` (the publication's values, dated by the model release it was
  published under), every definition parameter and `to.` target. The publications list and the API
  index do not take it.

```jsonc
// GET …/lists/rates?asOf=2026-06-30          RDM-As-Of-Applied: Rate
{ "items": [ … ], "workspace": "default", "publication": null, "asOfApplied": ["Rate"],
  "pageSize": 20, "nextCursor": "…", … }
```

| Status | Code | When |
| --- | --- | --- |
| 400 | `INVALID_AS_OF` | `asOf` is not one calendar date written `YYYY-MM-DD` (a time, a zone, an impossible day, two values); `details.path` `/query/asOf` |
| 400 | `AS_OF_NOT_SUPPORTED` | The list's type, the record's type, or every type a lookup can return declares no effective period; `details.objectTypes` (public names), `details.path` `/query/asOf` |

### Publications and caching

A consumer that must read one consistent snapshot, an extract paged over minutes or a flow resolving
a file of codes against a fixed state, pins its reads to a publication:

```text
GET /api/consumer/{consumerApi}/v{contractVersion}/publications?workspace=…&pageSize=…&cursor=…|position=…|from=end&includeTotal=true
GET …/lists/{listKey}?publication=latest          the workspace's current publication
GET …/objects/{id}?publication=4b1e…              a publication by its ID
```

- **`publication`** applies to get by ID, lists, XREF and batch resolve (in its URL). Every record,
  value and relationship is read as the publication holds it, whatever live data has done since; the
  read is otherwise the same, its parameters, crosswalk, scores, paging and refusals included. On a
  list, records sharing the sort value and the name follow their object ID (a publication records no
  creation order), as on the management API's publication lists.
- **`latest`** reads the workspace's current (`active`) publication. With none (never published, or
  the current one withdrawn without a successor) it is `404 PUBLICATION_NOT_FOUND`,
  `details.publication: "latest"`. A publication superseded or withdrawn stays readable by its ID.
- **One workspace.** A publication is looked up in the read's workspace (`workspace`, or the
  default); another workspace's ID is not found.
- **The release that shaped it.** A publication is read with the definition of the model release it
  was published under, and only when that release declares this API at the requested contract
  version. After a release that raises the contract version, publications made before it answer
  `409 PUBLICATION_CONTRACT_MISMATCH` (`details.publication`, and `details.contractVersion`: the
  version that release declares, or `null`) until a new publication is made.
- **Naming it.** Every pinned response, refusals included, names the publication in the
  `RDM-Publication` header; lists, XREF pages and batch resolve also in `publication` (`null` when
  live).
- **Cursors** keep their publication: a cursor from a page read with `latest` continues in that
  publication even after a newer one is published, so an extract pages every record once. A live
  cursor sent with `publication`, or a pinned one sent without it or with another publication, is
  `400 INVALID_CURSOR`.
- **The publications list** is the workspace's publications, newest first, paged as the lists are
  (no `seek`: `400 PARAMETER_NOT_SUPPORTED`). Each item has `id`, `publishedAt`, `eventSequence` and
  `status` (`active` or `withdrawn`). `eventSequence` is the feed position of the publication's
  `published` entry: live data at that position equals the publication, so a consumer extracts it
  and then follows changes from there (consumer events, C10). It is `null` for publications made
  before 0.9.0-alpha.1's feed positions.

```jsonc
// GET …/publications?workspace=default
{ "items": [ { "id": "4b1e…", "publishedAt": "2026-10-05T12:00:00+00:00", "eventSequence": 1842, "status": "active" },
             { "id": "90aa…", "publishedAt": "2026-10-01T08:30:00+00:00", "eventSequence": 1530, "status": "withdrawn" } ],
  "workspace": "default", "pageSize": 20, "nextCursor": null, "prevCursor": null, "anchor": "…",
  "totalCount": null, "startIndex": null }
```

**ETag.** Every `GET` that answers `200` carries an `ETag`; sent back as `If-None-Match`, it answers
`304 Not Modified` with no body (and the `ETag` and `RDM-` headers) while nothing it depends on has
changed. The tag is opaque. A live read's tag changes with any live write, publish or withdrawal in
the workspace (also one this API does not show), with a model release activation, and with the
contract version; a pinned read's tag never changes. Batch resolve, a `POST`, carries none. Several
tags, weak tags (`W/`) and `*` are compared as RFC 9110 compares them for `GET`.

| Status | Code | When |
| --- | --- | --- |
| 404 | `PUBLICATION_NOT_FOUND` | No publication with this ID in the read's workspace, or `latest` with no current publication; `details.publication` |
| 409 | `PUBLICATION_CONTRACT_MISMATCH` | The publication's model release declares another contract version of this API, or none; `details.publication`, `details.contractVersion` |

### API index and documents

```text
GET /api/consumer?pageSize=…&cursor=…|position=…|from=end&includeTotal=true
GET /api/consumer/{consumerApi}/v{contractVersion}/openapi.json
```

The **API index** lists the active release's consumer APIs, ordered by `consumerApi` and paged as
the lists are (no `seek`). Definitions are not per workspace, so it takes no `workspace`.

```jsonc
{ "items": [ { "consumerApi": "rdm", "name": "Reference data", "contractVersion": 2,
               "openapi": "/api/consumer/rdm/v2/openapi.json" } ],   // "description" when declared
  "pageSize": 20, "nextCursor": null, "prevCursor": null, "anchor": "…", "totalCount": null, "startIndex": null }
```

Each API's **document** is OpenAPI 3.1 and describes that API at its contract version as it answers:

- **Paths are written out** with the name and version, one per list: `/api/consumer/rdm/v2/xref`,
  `/api/consumer/rdm/v2/lists/products`. Neither is a path parameter. `servers` follows the
  deployment's root path, and the index's `openapi` URL does too.
- **`info`**: `title` is the definition's `name`, `version` the contract version as a string
  (`"2"`), and `description` names the model release that declares it.
- **Operations**: the operations the definition offers (get by ID, XREF and batch resolve when it
  lists them, C18), each list (with the name it is `within`), the publications list and, for a
  definition that declares events, the events read, each with the parameters it applies (filters as
  arrays, `style: form`, an author's `description` before the engine's; each crosswalk filter's `to.`
  name; `asOf` where the read can return a dated
  type, on a list only when its type is dated), the `ETag`, `RDM-Workspace`, `RDM-Publication` and
  `RDM-As-Of-Applied` headers, `304`, and its refusal codes.
- **Schemas** come from the contract the breaking-change check compares: the shared object with every
  declared field typed (decimals as strings, dates and date-times formatted, `null` where a field can
  have no value), each projection as an array or a nullable object by its cardinality, `matchScore`
  on XREF results, `target`, and the envelopes. Answers carry no undeclared field.
- **Limits** are stated where they apply: contains from 3 characters, 10,000 matches and 100 terms on
  XREF, `pageSize` 1–100, and the batch resolve maximum (`CONSUMER_RESOLVE_MAX_ITEMS`).
- One contract version is served per definition (C-D3): after a release raising it, the document is
  at the new version's URL and the old one answers `404 CONTRACT_VERSION_NOT_FOUND` naming the
  current version.

Both answer an `ETag` that changes with the active model release, and `304` to a matching
`If-None-Match`. A query parameter is refused as on the reads (`400 UNKNOWN_PARAMETER`, or
`PARAMETER_NOT_SUPPORTED` for a name a read serves).

### Consumer events (Base 0.9 C10)

A definition that declares `events` ([CONSUMER_API](CONSUMER_API.md#event-definitions-model)) tells
its consumers about changes to live data. The engine derives the events from the workspace's change
feed after each write commits, without the write waiting, and serves them here; webhooks (C11–C12)
will deliver the same events.

```text
GET /api/consumer/{consumerApi}/v{contractVersion}/events?workspace=…&event=…&after={position}|cursor=…&pageSize=…&payload=full|identity&{parameters}
```

```jsonc
// RDM-Workspace: default
{
  "items": [{
    "eventId": "1d0c…",            // the same event read or delivered again has the same ID
    "position": 184223,            // the feed position of the change that caused it
    "occurredAt": "2026-10-06T10:14:03+00:00",
    "event": "reference-data-changed",
    "change": "updated",           // created | updated | deleted
    "contractVersion": 1,          // the version that derived it
    "objectType": "CodelistValue", // public name
    "id": "…", "code": "HU", "name": "Hungary",   // now; null when the object no longer exists
    "changed": ["path"],           // with updated: the watched outputs that changed
    "cause": { "kind": "publication", "id": "…" },   // user | job | publication
    "stateAt": 184230,             // payload=full: the feed position object shows
    "object": { "masterId": "…", "code": "HU", "name": "Hungary", "path": "Europe/Hungary", … }
  }],
  "workspace": "default", "pageSize": 100,
  "cursor": "…",            // continue after the last event read; a lasting resume token
  "caughtUp": false,        // true: every event derived so far is read
  "headPosition": 184230,   // how far events are derived
  "earliestPosition": 170001
}
```

- **What is told.** `created` and `deleted` for an exposed object of the event's types; `updated`
  when a read of the object by ID would answer differently in a watched output, also for a change
  to a record it shows: its parent, an ancestor's name in `path` or `hierarchy`, a projected record
  or its ancestor, a projection gaining or losing an item. Changes are read by name, never by value,
  so `changed` may name an output whose answer stayed the same. A type change is `deleted`,
  `created` or `updated` with `objectType`, as seen from each event. Change-set work, model releases
  and refused writes make none.
- **Where to start.** `after` (default `0`): the last position processed, or a publication's
  `eventSequence` after reading it. Then `cursor`, which continues inside a position too. `after`
  and `cursor` together are `400 CONFLICTING_PAGE_PARAMETERS`; a cursor of another API, workspace,
  `event` or parameters `400 INVALID_CURSOR`; `after` not a whole number `400 INVALID_POSITION`;
  past the feed's head `409 EVENT_POSITION_AHEAD` with `headPosition`. A position the deriver has
  not reached yet answers an empty, caught-up page.
- **Payload.** `full` (default): each event carries its object as get by ID answers it with the same
  parameters, under the contract version served; a deleted object has none. `identity`: no object.
  `pageSize` is 1–100 (default 100) with `full` and 1–1,000 (default 500) with `identity`, else
  `400 INVALID_PAGE_SIZE`; another payload is `400 INVALID_PAYLOAD`.
- **Narrowing.** `event` (one or more keys; `400 UNKNOWN_EVENT` for one not declared) and the
  definition's parameters, applied as on a list to the object in live data now; a type parameter
  matches the type stored with the event; an event whose object no longer exists passes every other
  parameter. `publication`, `asOf` and `to.` names are `400 PARAMETER_NOT_SUPPORTED`. A narrowed
  page scans at most ten pages of events: it may come back short or empty with `caughtUp` false and
  the cursor advanced.
- **Every version.** All events of the API are served, whichever contract version derived them.
- **Expiry.** Events are kept as long as the change feed's entries (`FEED_RETENTION_DAYS`, default
  30), never past the active publication's position. A position below `earliestPosition - 1` is
  `410 EVENTS_EXPIRED` with `earliestPosition`, `headPosition` and `publication`
  (`{id, eventSequence}`, or `null`): read that publication's lists, then the events after its
  `eventSequence`. Without a publication nothing expires. A workspace that existed at the upgrade to
  this release has events from its active publication's position on.
- **Caching.** The `ETag` changes when a new event is derived and when live data changes (a full
  object, or a parameter read against live data, may differ before the event is derived; 0.9 R-F13);
  `304` to a matching `If-None-Match`.
- A definition without events answers `404 EVENTS_NOT_DECLARED`; an unknown or retired workspace
  `404 WORKSPACE_NOT_FOUND`.

### Consumer subscriptions (Base 0.9 C11)

Where a consumer API's events are delivered as webhooks. The routes are served only when
`CONSUMER_SUBSCRIPTIONS_ENABLED=true` (off by default; otherwise `404`, reads included), which also
requires `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` ([OPERATIONS](OPERATIONS.md)). Subscriptions are
deployment data, not part of a model release. [Delivery](#webhook-delivery-base-09-c12) is C12's.

| Route | Answer |
|---|---|
| `POST /api/v1/consumer-subscriptions` | `201`, the subscription with `signingSecret` |
| `GET /api/v1/consumer-subscriptions` (`consumerApi`, `workspaceKey`, `status`, paging) | the subscriptions, newest first (ADR-030) |
| `GET /api/v1/consumer-subscriptions/{id}` | the subscription |
| `PATCH /api/v1/consumer-subscriptions/{id}` | the edited subscription |
| `POST /api/v1/consumer-subscriptions/{id}/suspend` | the subscription, `suspended` (`SUSPENDED_BY_USER`) |
| `POST /api/v1/consumer-subscriptions/{id}/resume` | the subscription, `active` |
| `DELETE /api/v1/consumer-subscriptions/{id}?expectedVersion=N` | `204` |
| `GET /api/v1/consumer-subscriptions/{id}/deliveries` (`status`, paging) | what it delivered, newest first ([below](#the-delivery-log-base-09-u5a)) |
| `GET /api/v1/consumer-subscriptions/{id}/deliveries/{deliveryId}` | one request with its body and attempts |
| `POST /api/v1/consumer-subscriptions/{id}/deliveries/{deliveryId}/resend` | `201`, the new request: an event sent again by hand ([below](#resending-by-hand)) |

The create body names `name` (1–200 characters once trimmed, not unique, U5a), `consumerApi`,
`events` (at least one) and `url`, and optionally
`workspaceKey` (the default workspace, resolved and stored), `filters` (definition parameters, each a
text or a list of texts), how requests are made (C17): `maxEventsPerBatch` (1–1,000, default 1: one
event per request), `payload` (`full`, default, each event with its object; or `identity`, the
notification only) and `format` (`rdm`, default, or `cloudevents`), and `startAfter`.
`PATCH` takes `expectedVersion` with any of `name`, `events`, `filters`, `url`, `maxEventsPerBatch`,
`payload` and `format`; the consumer API and workspace are not edited, and a batch being
retried is dropped (the next attempt is at once) unless only the name changed. `suspend` takes `expectedVersion`; `resume` takes `expectedVersion`
and `reset` (default false).

```jsonc
{
  "id": "…", "name": "Billing system", "consumerApi": "rdm", "contractVersion": 1, "workspaceKey": "main",
  "events": ["reference-data-changed"], "filters": { "type": ["Location"] },
  "url": "https://integration.example.com/hooks/rdm",
  "maxEventsPerBatch": 1, "payload": "full", "format": "rdm",
  "status": "suspended",
  "suspension": { "reason": "MODEL_CHANGED", "message": "…", "suspendedAt": "…",
                  "details": { "errors": [{ "code": "UNKNOWN_EVENT", "message": "…", "pointer": "/events/0" }] } },
  "acknowledgedThrough": 184100,
  "delivery": { "lastDeliveredAt": "…", "pending": null },
  "signingKeyCreatedAt": "…", "version": 3, "createdAt": "…", "updatedAt": "…"
}
```

- **Checks** (create, edit and resume): the consumer API exists in the active release and declares
  events; each event is declared; each filter names a definition parameter (a read's own names and
  `to.` targets are not filters) and each value matches a record now; the URL is absolute HTTPS on
  an allowed host, without user information or fragment, at most 2,048 characters, or HTTP to a
  listed loopback host (`localhost`, `127.0.0.1`, `::1`); the workspace exists and is active.
- **The signing key** is answered once, as `signingSecret` (`rdmwh_` and 43 base64url characters),
  and never by a read; keep it to verify deliveries (C12). It is stored sealed with the deployment
  key.
- **Start.** Delivery continues after `acknowledgedThrough`: the workspace's feed head at create, or
  `startAfter`, refused as the pull feed's `after` is (`410 EVENTS_EXPIRED` with `publication`,
  `409 EVENT_POSITION_AHEAD`).
- **Contract version.** `contractVersion` is the version the subscription was accepted under.
- **Suspension reasons:** `SUSPENDED_BY_USER`; `MODEL_CHANGED` (an activated release no longer
  declares the API, an event or a filter's parameter; `details.errors`); `CONTRACT_VERSION_CHANGED`
  (an activated release serves another version; `details.contractVersion`,
  `details.servedContractVersion`); `WORKSPACE_RETIRED`. The dispatcher (C12) adds
  `DELIVERY_FAILED` (`deliveryId`, `attempts`, `failingSince`, `lastError`), `FILTER_MATCHES_NOTHING`
  (`parameter`, `values`, `pointer`, and `position`, the acknowledged position) and
  `EVENTS_EXPIRED` (`fromPosition`, `toPosition`, `publication`). A suspension raises `version`.
- **Resume** re-runs the checks: a failure is `409 SUBSCRIPTION_NEEDS_EDIT` with each finding's
  `code`, `message` and `pointer` in `details.errors`. It continues after `acknowledgedThrough`, at
  once, the failing batch's retries cleared. If events after `acknowledgedThrough` expired, it is
  `409 EVENTS_EXPIRED` with `fromPosition`, `toPosition` and `publication`. With `reset: true` it
  starts after the workspace's feed head instead, whatever happened before: the receiver re-syncs
  what it missed after the reset (a publication's lists), so nothing falls between. A resume
  accepts the contract version served.
- **Delivery state** (`delivery`, C-D108): `lastDeliveredAt`, when a request was last acknowledged
  (`null` before the first); `pending`, `null` unless a batch is failing: its `deliveryId`, the
  `throughPosition` it ends at, `attempts`, `failingSince`, `lastAttemptAt`, `nextAttemptAt` and
  `lastError` (`kind`: `status`, `redirect`, `timeout`, `connection`, `tls` or `address`; `status`
  when the receiver answered; `message`, at most 200 characters). Delivery changes neither
  `version` nor `updatedAt`.

| Status | Code | When |
|---|---|---|
| 400 | `CONSUMER_API_NOT_FOUND`, `EVENTS_NOT_DECLARED` | at `/consumerApi` |
| 400 | `UNKNOWN_EVENT` | at `/events/{i}` |
| 400 | `UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`, `UNKNOWN_OBJECT_TYPE`, `FILTER_MATCHES_NOTHING` | at `/filters/{name}` |
| 400 | `INVALID_WEBHOOK_URL` | at `/url`: not absolute HTTPS (plain HTTP only to `localhost`, `127.0.0.1` or `::1`), user information, a fragment, or over 2,048 characters |
| 404 | `WORKSPACE_NOT_FOUND` | at `/workspaceKey`: unknown or retired |
| 404 | `SUBSCRIPTION_NOT_FOUND` | the ID |
| 409 | `VERSION_CONFLICT` | `expectedVersion` is stale; `details.currentVersion` |
| 409 | `SUBSCRIPTION_ALREADY_SUSPENDED`, `SUBSCRIPTION_NOT_SUSPENDED` | suspend or resume in the wrong state |
| 409 | `SUBSCRIPTION_NEEDS_EDIT`, `EVENTS_EXPIRED` | resume, above |
| 409 / 410 | `EVENT_POSITION_AHEAD` / `EVENTS_EXPIRED` | `startAfter`, at `/startAfter` |
| 422 | `REQUEST_VALIDATION_ERROR` | the body's shape: an unknown field (also the retired `mode` and `debounceSeconds`), `maxEventsPerBatch` outside 1–1,000, an unknown `format` |

Every refusal changes nothing. Edits, suspensions, resumes and deletions write no audit entry.

#### The delivery log (Base 0.9 U5a)

The dispatcher logs every request it sends (C-D116); a batch is one request. `GET …/deliveries`
lists one row per event of a request, newest first; rows of one request share its outcome, since
delivery is per request (C-D119):

```json
{ "deliveryId": "…", "eventId": "…", "event": "values-changed", "change": "updated",
  "objectType": "CodelistValue", "objectId": "…", "position": 184223,
  "status": "retrying", "attempts": 2, "responseStatus": 503,
  "sentAt": "…", "nextAttemptAt": "…" }
```

`status` is `queued` (built, not sent yet), `sending`, `retrying` (failed; tried again, or waiting
for a resume), `succeeded`, `failed` (the subscription was suspended `DELIVERY_FAILED`) or `dropped`
(an edit or resume dropped the batch, or its events left the subscription). `responseStatus` and
`sentAt` are the latest attempt's; `nextAttemptAt` is set while the batch waits for a retry. The
list narrows by `status`.

`GET …/deliveries/{deliveryId}` answers the request: `deliveryId`, `batchId`, `status`, `events`,
`requestBody` (the JSON of the latest attempt as the receiver got it, in the subscription's format
then, C-D117; `null` before the first), `requestBytes`, `createdAt`, `nextAttemptAt` and `attempts`,
each `number`, `startedAt`, `completedAt`, `durationMs`, `responseStatus`, `error` (`kind` and
`message`, or `null`) and `responseBody` (up to 4 KiB of the answer). An unknown ID is
`404 DELIVERY_NOT_FOUND`, an unknown subscription `404 SUBSCRIPTION_NOT_FOUND`.

Entries are kept for `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS` (7), reported as
`consumerSubscriptions.logRetentionDays` in capabilities; a batch still pending keeps its entries
longer. A deleted subscription's go with it.

##### Resending by hand

`POST …/deliveries/{deliveryId}/resend` with `{"eventId": "…"}` (required) sends that event again
exactly as it was sent in that request, taken from the stored body, alone in a new request with a
new `deliveryId` and a fresh signature (C-D129). It keeps the request's format, even when the
subscription's was edited since: an RDM JSON envelope with the one event, a structured CloudEvent,
or a CloudEvents batch of one (C17). It keeps the `eventId` and adds the
header `RDM-Redelivery: manual`, so a receiver that deduplicates by `eventId` can decide to process
it again (C-D130). It is sent during the call, one attempt with no retry, on any subscription,
suspended ones included; the answer is the new request (`succeeded` or `failed`) with `resendOf`
naming the one it repeats, and the subscription's position and any batch being retried are left
alone (C-D131). Rows and details carry `resendOf` (`null` for the dispatcher's requests).

| Status | Code | When |
|---|---|---|
| 404 | `SUBSCRIPTION_NOT_FOUND`, `DELIVERY_NOT_FOUND` | the IDs |
| 404 | `EVENT_NOT_IN_DELIVERY` | the event was not sent in that request |
| 409 | `DELIVERY_NOT_SENT` | the request was never sent (`queued`), so nothing can be repeated |

### Webhook delivery (Base 0.9 C12)

While `CONSUMER_SUBSCRIPTIONS_ENABLED` is on, every active subscription's events are POSTed to its
URL, in position order, one request at a time per subscription; the next goes after the previous is
acknowledged. [CONSUMER_API "Delivery"](CONSUMER_API.md#delivery) explains each rule.

**Requests** (C17): one event per request (`maxEventsPerBatch: 1`, the default), or batched, up to
`maxEventsPerBatch` events. A request also stops at 1 MiB of body; an event alone over 1 MiB is
sent alone. A batch holds what is waiting when it is sent and never waits to fill up. With one event
per request, a bulk change is that many requests in a row, so batch for bulk changes. Each event is
the pull feed's item, with the object as get by ID answers it under the subscription's filters
(`payload: full`) or the notification only (`identity`); an object deleted since it changed has none.

**RDM JSON** (`format: rdm`): an envelope with 1 to `maxEventsPerBatch` events, also for one.

```json
{
  "deliveryId": "6f1c…", "subscriptionId": "…",
  "consumerApi": "rdm", "contractVersion": 1, "workspaceKey": "main",
  "events": [{
    "eventId": "…", "position": 184223, "occurredAt": "2026-10-06T10:14:03.512000+00:00",
    "event": "reference-data-changed", "change": "updated", "contractVersion": 1,
    "objectType": "MasterValue", "id": "…", "code": "…", "name": "…",
    "changed": ["systemVariants"], "cause": { "kind": "publication", "id": "…" },
    "stateAt": 184230, "object": { … }
  }]
}
```

**CloudEvents 1.0** (`format: cloudevents`), in the HTTP binding's structured mode: with one event
per request, one CloudEvent (`application/cloudevents+json; charset=utf-8`); batched, a JSON array
of them (`application/cloudevents-batch+json; charset=utf-8`), also when a batch holds one event.
`data` is the RDM JSON event unchanged.

```json
{
  "specversion": "1.0", "id": "<eventId>",
  "source": "/api/consumer/rdm/v1/events?workspace=main",
  "type": "rdm.reference-data-changed.updated", "subject": "MasterValue/<id>",
  "time": "<occurredAt>", "datacontenttype": "application/json",
  "rdmsubscription": "<subscriptionId>",
  "data": { "eventId": "…", "position": 184223, "event": "reference-data-changed", "…": "…" }
}
```

**Headers:**

| Header | Value |
|---|---|
| `Content-Type` | `application/json` (RDM JSON), or the CloudEvents type above; the body is compact UTF-8 JSON |
| `User-Agent` | `rdm-engine` |
| `RDM-Delivery-Id` | the request's delivery ID (an RDM JSON body's `deliveryId`); the same on every retry of a batch |
| `RDM-Timestamp` | Unix seconds, new on every attempt |
| `RDM-Redelivery` | `manual` on a resend by hand (U5a); absent otherwise |
| `RDM-Signature` | `sha256=` and the lowercase hex HMAC-SHA256 of `"{RDM-Timestamp}.{body}"`, keyed with the `signingSecret` exactly as the create answered it; it covers a CloudEvent's attributes too |

**The receiver's answer:** any `2xx` acknowledges. Anything else fails the attempt: another status, a
redirect (not followed), no answer within 10 s, a connection or TLS failure, or a refused address
(link-local always; loopback unless the URL names a loopback host). A failed batch is retried with
the same events and `deliveryId` after 10 s, 30 s, 1, 2, 5, 10 and 30 min, then hourly, each ±20 %,
for 24 hours from its first failure; then the subscription is suspended `DELIVERY_FAILED`. Delivery
is at least once: deduplicate by `eventId`.

## Model authoring (Product 0.10, designed)

Designed in the [Base 0.10 A0 plan](BASE_0_10_IMPLEMENTATION_PLAN.md#a0-plan-2026-10-11) from
[MODEL_AUTHORING.md](MODEL_AUTHORING.md) and [ADR-041](DECISIONS.md#adr-041--model-drafts-change-through-recorded-operations).
Each part moves into "delivered" with its package: operations, history and undo with A2, source files
and the dry-run summary with A3, a draft's profiles and the mapping kinds with A5, inferences with A6.
Field-level detail not fixed here is finished in that package's plan. **Delivered by A2
(2026-10-11):** [draft operations](#draft-operations), the [kinds](#kinds) of the model side and the
[history, undo and redo](#history-undo-and-redo). **Delivered by A4a (2026-10-11):** [the draft's
outline](#the-drafts-outline). **Delivered by A4b (2026-10-11):** [the draft's model](#the-drafts-model)
and the detail page kinds. The rest of this section is designed.

- `POST /api/v1/model-drafts/{draftId}/operations`, `GET /api/v1/model-drafts/{draftId}/operations`
- `POST /api/v1/model-drafts/{draftId}/undo`, `POST /api/v1/model-drafts/{draftId}/redo`
- `GET /api/v1/model-drafts/{draftId}/outline` (A4a)
- `GET /api/v1/model-drafts/{draftId}/model` (A4b)
- `POST /api/v1/source-files`, `GET /api/v1/source-files`, `GET /api/v1/source-files/{sourceFileId}`,
  `DELETE /api/v1/source-files/{sourceFileId}?expectedVersion=`
- `GET /api/v1/source-files/{sourceFileId}/profile/sheets`,
  `GET /api/v1/source-files/{sourceFileId}/profile/sheets/{sheet}/columns`
- `GET /api/v1/model-drafts/{draftId}/dry-run`, `POST /api/v1/model-drafts/{draftId}/dry-run`,
  `GET /api/v1/model-drafts/{draftId}/dry-run/rows`
- `GET /api/v1/model-drafts/{draftId}/profiles` (A5)
- `POST /api/v1/model-drafts/{draftId}/inferences`, `GET /api/v1/model-drafts/{draftId}/inferences/{inferenceId}/proposals` (A6)

The draft routes are registered with `MODEL_ADMIN_MUTATIONS_ENABLED`, as the draft routes before them
(reads too, since a draft is administration data). Source files, profiling and dry runs are jobs and
are registered with `INTEGRATION_JOBS_ENABLED` as well (D6).

### Draft operations

```json
{
  "expectedVersion": 7,
  "operations": [
    { "kind": "addObjectType", "applicationKey": "catalogue", "name": "Unit", "pluralName": "Units",
      "parent": null },
    { "kind": "attachAttribute", "objectType": "unit", "attributeType": "code", "required": true }
  ]
}
```

- The operations of one request are applied in order, **all or none**, to the draft's model, and are
  one step of the history: one undo takes back the whole request. The answer (`200`) holds the new
  `version`, the stored entries (each with its `sequence` and `inverse`, as the history lists them),
  the model's `valid` flag and its `diagnostics`, the same list `POST /model-validations` gives for
  the draft's model, and from A3 the dry-run summary of each attached source file.
- **A draft may be invalid between operations.** An operation is refused only when it cannot be
  applied (an unknown element, a key already taken, a list position out of range, a class it may not
  have); a model that does not yet validate (a type without a view, a required attribute no view
  shows) is accepted with its diagnostics, and installation refuses it as it does today. The
  validators are the compiler's; there is no second set.
- **Elements are named by key**, never by a position or a database ID: `objectType`,
  `attributeType`, `relationType`, `applicationKey`; an attribute binding by `objectType` and
  `attributeType`; a relation binding by `relationType`, `from` and `to`; a view by `applicationKey`
  and `view`; a panel by `applicationKey`, `detail` (its object type) and `panel`; a navigation
  group by `applicationKey` and `group`. A key the operation creates is generated from its name when
  omitted (A-D6: lower-case, hyphen-separated ASCII, accents dropped, `-2`, `-3` on a clash).
- **Class** (MODEL_AUTHORING): an additive kind is always applied. A draft-only kind applies while
  every element it touches is absent from the draft's **base release** (the active release when the
  draft has none, D17); otherwise it is refused `409 OPERATION_REQUIRES_MIGRATION` with
  `details.index`, `details.kind`, `details.element` (named as operations name it, e.g.
  `{"objectType": "unit"}` or `{"objectType": "unit", "attributeType": "code"}`),
  `details.baseReleaseId` and `details.impact`: `records`, `values` and `relationships` in live data of
  every workspace and in every change set (D33), each counted exactly up to 10,000 and reported as
  `"10000+"` beyond. Nothing of the request is applied. A key that the active release holds counts as
  released for a draft without a base, even when the draft created it again: its records would carry
  over.
- **The server keeps the model whole.** `setKey` rewrites every reference to the key (bindings,
  views, panels, fields such as `ancestor:<type>` and `related:<key>`, navigation), consumer API
  definitions included: exposed types, public names, field sources, related blocks' `via` and fields,
  lists, XREF rules and filters (0.10 A4c, D54, replacing A2's `namedByConsumerApi` refusal, D29).
  Only an element the base release lacks is re-keyed, so no definition a consumer reads changes; the
  rewrite is undone with the step. A removal leaves a definition naming the removed element alone,
  and the draft's issues point at it. `addObjectType`
  adds the type to its application with a generated table view, and a detail page where the
  application declares its `details` (below); `attachAttribute` and `allowRelation` add the
  attribute or relation to the type's layout unless `"layout": false`. A removal takes with it what
  exists only for the removed element (D31): its bindings, views and detail page, navigation
  entries, the items naming it in other views and panels (a children or relations panel or a tree
  left without its list goes too), and relation types and attribute types it alone used that the
  base release does not hold. The entry's inverse stores what it took.
- **Positions** (D35) are the index in the declared list, 0-based; omitted, the end; out of range,
  `INVALID_OPERATION` (`outOfRange`). Where a list's items carry `order` (attribute bindings, and
  panels within their region), the moved or inserted item takes an `order` between its neighbours',
  and the list is renumbered 10, 20, 30… only when no whole number fits.
- Refusals: `422 INVALID_OPERATION` (`details.index`, `details.pointer` into the request,
  `details.reason`: `unknownKind`, `internalKind`, `unknownParameter`, `missingParameter`,
  `invalidValue`, `unknownElement`, `keyTaken`, `alreadyAttached`, `alreadyAllowed`,
  `alreadyPresent`, `stillBound`, `outOfRange`, `unsupportedSchemaVersion`, `conflict`),
  `409 OPERATION_REQUIRES_MIGRATION`, `409 VERSION_CONFLICT` with `details.operations`, the history
  entries since `expectedVersion` (at most 100, then `details.more: true` and the history route to
  page), `404 MODEL_DRAFT_NOT_FOUND`, `413 OPERATION_BATCH_TOO_LARGE` over
  `MODEL_OPERATION_MAX_ITEMS` (500, `details.limit` and `details.received`).

**Generated layout** for a new object type: a table view keyed from its plural name (`name`, the
attached attributes in order; filter and sort fields `name` and the attributes the features make
filterable or sortable; `defaultSort` `name`; `pageSize` 50), the application's default view when it
has none, and, where the application declares `details`, a detail page (an attributes panel in
`main`; a hierarchy panel in `side` when it has a parent; a children panel when it contains types; a
relations panel, `outgoing`, when a binding names it at its `from` end). A new child type joins its
parent's children panel, or a new one, on each detail page the parent has; the server does not
create a detail page for a type that has none. An attached attribute joins the type's table views
(columns, and filter and sort fields as its features allow) and its first attributes panel; an
allowed relation joins its `from` type's plain outgoing relations panel (relation types and
direction only; a panel with columns, sorts or filters of its own is left alone), or a new one. The same operation from any
client gives the same layout.

**Parameters** not in the table: an element named by `setLabel` and `setKey` is `element`, one of
`{"applicationKey"}`, `{"objectType"}`, `{"attributeType"}`, `{"relationType"}`,
`{"applicationKey", "view"}`, `{"applicationKey", "detail", "panel"}` (`detail` is the page's object
type) and `{"applicationKey", "group"}`. A containment `parent` (D30) is `null` (the top level,
`rootCreatable: true`) or `{"objectTypes": [...], "relationType": "<key>" or {"name",
"reverseName", "key"?, "reverseKey"?}}`: one containment relation type (`parentOf`,
`creatableOnChildAdd`), existing or new, bound `one-to-many` from each parent type. A view or panel
target is `applicationKey` with `view`, with `detail` (the page; its list is `panels`) or with
`detail` and `panel`. A flag (`required`, `readOnly`) and `valueType` may be `null`: the default,
left unwritten, as an inverse writes it back.

#### Kinds

Model side (A2, delivered). The inverse is another kind of the table, or, for a kind that removes or
reshapes several elements, `restoreElements` with the stored prior state of what it changed: those
inverses are exact, so an undo puts back each place, list position and `order` as it was. Where the
A0 design named another kind as the inverse (`splitObjectType`, `detachAttribute`, `moveAttribute`,
`setContainment`, `disallowRelation`), the stored state replaced it in A2, because only it brings back
the layout places the change took.

| Kind | Parameters | Class | Inverse |
| --- | --- | --- | --- |
| `setLabel` | element; any of `name`, `pluralName`, `reverseName`, `description`, `icon`, `color`, `title` | additive | `setLabel` with the old values |
| `setKey` | `element`, `key` (and `reverseKey` for a relation type) | draft-only for an application, type or relation type; additive for a view, panel or group | `setKey` back |
| `setRelease` | any of `key`, `name`, `version` (D18), and `schemaVersion` (a supported version) | additive | `setRelease` back |
| `addApplication` | `key`?, `name`, `description`, `icon`, `color` | additive | `removeApplication` |
| `removeApplication` | `applicationKey` | draft-only | `restoreElements` |
| `addObjectType` | `applicationKey`, `key`?, `name`, `pluralName`, `parent` (`null` or parent type keys and a containment relation type, new or existing), `displayAttribute`? | additive | `removeObjectType` |
| `removeObjectType` | `objectType` | draft-only | `restoreElements` |
| `splitObjectType` | `objectType`, the new type's `name`, `pluralName`? and `key`?, `attributes` (keys to move), `relationType` (key or new) and `cardinality` (default `many-to-many`) joining the type to the new one | draft-only | `restoreElements` |
| `mergeObjectTypes` | `into`, `from` (attributes, bindings and layout of `from` joined into `into`) | draft-only | `restoreElements` |
| `convertAttributeToListType` | `objectType`, `attributeType`, the list type's `name`, `pluralName`? and `key`?, `relationType` (key or new; bound `many-to-many` from the type) | draft-only | `restoreElements` |
| `addAttributeType` | `key`?, `name`, `valueType`, `features` (`searchable`, `filterable`, `sortable`, `unique`), `validation` | additive | `removeAttributeType` |
| `removeAttributeType` | `attributeType` (not bound anywhere) | draft-only | `restoreElements` |
| `setAttributeTypeFeatures` | `attributeType`, features to set | additive; draft-only to add `unique` | `setAttributeTypeFeatures` back |
| `setValueType` | `attributeType`, `valueType`, `validation`? | draft-only | `setValueType` back |
| `attachAttribute` | `objectType`, `attributeType`, `required`, `readOnly`, `position`, `layout` | additive; draft-only when `required` on a released type | `detachAttribute` |
| `detachAttribute` | `objectType`, `attributeType` | draft-only | `restoreElements` |
| `moveAttribute` | `attributeType`, `from`, `to` (a type), `layout` | draft-only | `restoreElements` |
| `setAttributeBinding` | `objectType`, `attributeType`; `required`, `readOnly`, `position` | additive for `position`; draft-only otherwise | `setAttributeBinding` back; `restoreElements` when the move changed an `order` |
| `setContainment` | `objectType`, `parent` (D30; the `parentOf` relation type, its bindings, the type's `parentRelationTypeKeys` and the parents' children panels changed together) | draft-only | `restoreElements` |
| `addRelationType` | `key`?, `reverseKey`?, `name`, `reverseName`, `isOriented` | additive | `removeRelationType` |
| `removeRelationType` | `relationType` (no binding left) | draft-only | `restoreElements` |
| `allowRelation` | `relationType`, `from`, `to`, `cardinality`, `required`, `layout` | additive | `disallowRelation` |
| `disallowRelation` | relation binding | draft-only | `restoreElements` |
| `setRelationRule` | relation binding; `cardinality`, `required`, `candidates`, `uniqueToAncestorTypeKey` | draft-only; additive for `candidates` alone (compatible in a release, 0.9 K7; corrected in A4a) | `setRelationRule` back |
| `addView` | `applicationKey`, `view` (a declaration; a table view may give only `objectTypeKey`, with `key` and `name` optional, and the rest is generated), `position`, `default` | additive | `removeView` |
| `removeView` | view | additive | `addView` with its declaration |
| `insertViewItem` | view or panel, `list` (`columns`, `filterFields`, `sortFields`, `fields`, `panels`, …), `item`, `position` (D19) | additive | `removeViewItem` |
| `moveViewItem` | view or panel, `list`, `item`, `position` | additive | `moveViewItem` back; `restoreElements` when the move changed a panel's `order` |
| `removeViewItem` | view or panel, `list`, `item` | additive | `insertViewItem` at its old position |
| `setViewProperty` | view or panel, `property` (`name`, `defaultSort`, `pageSize`, `region`, `visible`, `title`, …), `value` | additive | `setViewProperty` back |
| `addDetailPage` | `applicationKey`, `objectType` (a type of the application without a page); `page` and `position` only as `removeDetailPage`'s inverse | additive | `removeDetailPage`; `restoreElements` when it started the application's list of pages |
| `removeDetailPage` | `applicationKey`, `objectType` | additive | `addDetailPage` with its declaration and position |
| `addNavigationGroup` | `applicationKey`, `key`?, `label`, `collapsed`, `position` | additive | `removeNavigationGroup` |
| `removeNavigationGroup` | group (its collections return to the top level) | additive | `addNavigationGroup` with its collections |
| `setNavigationGroup` | group; `label`, `collapsed`, `position` | additive | `setNavigationGroup` back |
| `placeCollection` | `applicationKey`, `collection`, `group` (`null`: top level), `position` | additive | `placeCollection` back |
| `replaceModel` | the whole model; written by `PATCH /model-drafts/{id}`, refused in a request | — | `replaceModel` with the previous model |
| `restoreElements` | `undoes` (the operation it takes back), `removes` (the elements that operation created, which putting things back takes away: refused `OPERATION_REQUIRES_MIGRATION` once released) and `changes` (the stored prior state); refused in a request | — | the kind it undid |

Consumer API side (A4c, delivered, D51–D55). A definition (schema 0.9 and later,
[CONSUMER_API](CONSUMER_API.md#definition-shape)) is changed by two whole-definition kinds and four
part verbs that name a part by a JSON **`pointer`** below the definition (`/object/fields`,
`/operations/lists/items`, `/filters/channel/matchOn/0`), as the view verbs name a view's lists. A
keyed map (fields, related blocks, lists, filters, public names) keeps its members in written order,
which is the order fields are served in, so a position places a member as in a list. A change is
refused `INVALID_OPERATION` (`invalidValue`, with where the shape breaks) when the definition would no
longer have the schema 0.9 shape; what it names (sources, relations, types) is reported by the step's
`diagnostics` at the author's pointers, so a draft may be invalid between steps (D52). Definitions are
not released elements: changing one the base release declares is not refused; the contract check
against the active release protects its consumers at activation (D55, C-D17).

| Kind | Parameters | Class | Inverse |
| --- | --- | --- | --- |
| `addConsumerApi` | `name`, `key`? (from the name, A-D6), `exposes` (type keys), `position`; or `definition` (as `removeConsumerApi`'s inverse) | additive | `removeConsumerApi` |
| `removeConsumerApi` | `consumerApi` | additive | `addConsumerApi` with its `definition` and `position` |
| `setConsumerApiPart` | `consumerApi`, `pointer`, `value`: the member or item set (a member its object lacks is added); `null` takes an optional member out; the empty pointer replaces the definition | additive | `setConsumerApiPart` with the old value |
| `insertConsumerApiPart` | `consumerApi`, `pointer` (a list, or a keyed map with `key` naming the member), `value`, `position`; a list or map its object lacks is started | additive | `removeConsumerApiPart` |
| `moveConsumerApiPart` | `consumerApi`, `pointer` (the member or item), `position` | additive | `moveConsumerApiPart` back |
| `removeConsumerApiPart` | `consumerApi`, `pointer` (the member or item) | additive | `insertConsumerApiPart` at its old position |

**The starting definition** `addConsumerApi` writes (D53): `contractVersion` 1; the fields `id`
(role `id`) and `name` (role `name`) and one field per attribute an exposed type binds, in binding
order, named by its key in camelCase (a clash with a taken or reserved name gets a number);
`operations.objects` and a list per exposed type keyed by its plural name. XREF, filters, related
blocks and events are left to the author. Refused `unsupportedSchemaVersion` on a draft below schema
0.9 (`setRelease` raises it), `keyTaken` for a key another definition has, `unknownElement` for an
exposed type the draft lacks.

Mapping and value kinds (A5, named here and specified in A5's plan): `mapColumn`,
`setColumnReading` (text, lookup, relation, relation flag), `splitColumn`, `unpivotColumns`,
`ignoreColumn`, `ignoreSheet`, `setValueMap`, `addValuesToList`. They change the draft's profiles
only; the model-side kinds above also change the profiles when a draft holds them (D13).

### History, undo and redo

`GET /api/v1/model-drafts/{draftId}/operations` lists the draft's history, oldest first, ADR-030 paging
(`from=end` for the latest). Each entry:

```json
{ "sequence": 12, "step": 5, "kind": "attachAttribute",
  "parameters": { "objectType": "unit", "attributeType": "code", "required": true },
  "inverse": { "kind": "detachAttribute", "objectType": "unit", "attributeType": "code" },
  "draftVersion": 8, "author": null, "at": "2026-10-12T09:00:00Z",
  "undone": false, "origin": { "type": "request" } }
```

`step` groups the entries of one request; `origin` is `request`, `undo`, `redo`, `patch` (a
whole-model `PATCH`, recorded as `replaceModel`) or, from A6, `proposal` with its ID. `author` is
`null` until 0.12 brings identities. The history is the draft's and goes with it (D4); a release
keeps none. It answers J08.9.

- **`POST …/undo`** `{ "expectedVersion": 8, "step": 5 }` applies the inverses of a step, last
  entry first, as a new step with origin `undo` (`{"type": "undo", "steps": [5]}`), and marks the
  step's entries `undone`. Without `step` it undoes the latest step not yet undone (an undo step is
  never itself undone; redo takes it back). A step a later, not undone step depends on (D8: one names
  an element the earlier one created or re-keyed) is refused `409 OPERATION_HAS_DEPENDANTS` with
  `details.steps` and `details.dependants` (their steps); the client may undo them first, or send them
  together in `steps` (`{ "expectedVersion": 8, "steps": [5, 6] }`, applied latest first as one step).
  A step already undone, or an undo step, named in `step` or `steps` is `409 NOTHING_TO_UNDO` with
  `details.step`. An inverse that would take away an element released since (an installation, D17)
  is refused `OPERATION_REQUIRES_MIGRATION` as any draft-only operation is.
- **`POST …/redo`** `{ "expectedVersion": 9 }` takes back the latest undo step not yet taken back
  (origin `{"type": "redo", "step": 9}`), so undos are redone most recent first (D32). A request or
  `PATCH` after an undo leaves nothing to redo; an installation does not.
- Refusals: `409 NOTHING_TO_UNDO`, `409 NOTHING_TO_REDO`, `409 OPERATION_HAS_DEPENDANTS`,
  `409 VERSION_CONFLICT` (as above).

**Installation** keeps its route. A successful installation makes the release it created, or the
identical one it found, the draft's base (D17), so what the draft held becomes released. The draft's
`version` is unchanged (D34): the model did not change, and an editor at that version carries on. The editor's "install and activate" is the
existing installation then activation (`POST /model-releases/{id}/activation`), confirmed once by the
user (A-D8); an activation refused after the installation leaves the installed release, and the
editor says so. No combined route: an integrator has both steps already.

### The draft's outline

`GET /api/v1/model-drafts/{draftId}/outline` answers the draft's structure as an editor shows it
(A4a, D36), so a client never works out containment or what is released from the JSON itself. It reads
the draft's document as it is, so a draft that does not validate between steps is outlined with what
can be read, beside its diagnostics.

```json
{
  "version": 9, "baseReleaseId": "…",
  "release": { "key": "catalogue", "name": "Catalogue", "version": "1.2.0", "schemaVersion": "0.10" },
  "baseRelease": { "key": "catalogue", "name": "Catalogue", "version": "1.2.0" },
  "applications": [{ "key": "catalogue", "name": "Catalogue", "objectTypeKeys": ["category", "item", "unit"],
    "tree": [{ "objectType": "category", "children": [{ "objectType": "item", "children": [] }] },
             { "objectType": "unit", "children": [] }],
    "navigation": { "groups": [{ "key": "lists", "label": "Lists", "collapsed": false,
                                 "collections": ["unit"], "mark": "new" }],
                    "ungrouped": ["category", "item"] },
    "mark": "changed" }],
  "objectTypes": [{ "key": "item", "name": "Item", "pluralName": "Items", "rootCreatable": false,
    "parents": ["category"], "mark": "changed",
    "attributes": [{ "attributeType": "code", "name": "Code", "valueType": "text", "required": true,
                     "readOnly": false, "unique": true, "sharedWith": ["category"], "mark": "released" }] }],
  "attributeTypes": [{ "key": "code", "name": "Code", "valueType": "text", "features": { "unique": true },
                       "boundBy": ["category", "item"], "mark": "released" }],
  "relationTypes": [{ "key": "contains-item", "reverseKey": "in-category", "name": "Contains item",
                      "reverseName": "In category", "containment": true, "mark": "released" }],
  "relations": [{ "relationType": "measured-in", "from": "item", "to": "unit", "cardinality": "many-to-one",
                  "required": false, "containment": false, "mark": "new" }],
  "valid": false,
  "diagnostics": [{ "severity": "error", "code": "INVALID_REFERENCE", "path": "/applications/catalogue/views/units",
                    "message": "…", "element": { "applicationKey": "catalogue", "view": "units" } }]
}
```

- **`tree`** is the application's types by containment, as the placements read it: each type no type
  of the application contains, with the types it contains below it, in the application's order. A type
  with several parents appears under each; a containment cycle stops where a type would repeat.
- **`mark`** is `new` when the draft's base release (the active release when the draft has none, D17)
  does not declare the element, `changed` when it declares it differently, and `released` otherwise,
  for applications, types, attribute bindings, attribute types, relation types, allowed relations and
  navigation groups. A type is also `changed` when a relation allowed **from** it was added, changed or
  removed: the relations a type starts are part of it, as its outgoing relations panel shows. The marks
  are those the class check reads, so a draft-only operation is refused on exactly the elements marked
  `released` or `changed`.
- **`navigation.ungrouped`** lists the application's collections in no group, in their sidebar order.
- **`relations[].candidates`**: which records the relationship may choose at each end (0.9 K7), as the
  model declares it; absent when it has none.
- **`diagnostics`** are the compiler's, as `POST /model-validations` gives them for the draft's model,
  each with **`element`**: the element its pointer falls in, named as operations name elements
  (`{"objectType"}`, `{"objectType", "attributeType"}`, `{"relationType", "from", "to"}`,
  `{"applicationKey", "view"}`, `{"applicationKey", "detail"}`, `{"applicationKey", "group"}`,
  `{"consumerApi"}`, …), or `null` for a pointer in no element (the release, the product).
- **`consumerApis`** (A4c): each definition as `key`, `name`, `description`, `contractVersion`,
  `exposes` (each type with its `publicName`, the default written out), `counts` (`fields`, `related`,
  `lists`, `filters`, `events`), `mark` (against the base release's definition of that key) and
  `contract`: the definition checked against what the **active** release's consumers read,
  `classification` `compatible` or `version_required` with the `diagnostics` (each with its
  `element`), as `consumerContracts` of the compile gives them; `null` while the draft does not
  compile (D55).
- Refusals: `404 MODEL_DRAFT_NOT_FOUND`. The route is registered with `MODEL_ADMIN_MUTATIONS_ENABLED`,
  as the other draft routes.

### The draft's model

`GET /api/v1/model-drafts/{draftId}/model` answers the draft compiled as `GET /model` serves the active
model, with its placements as `GET /model/placements` gives them, so a client renders the draft with its
own renderers before installing it (A4b, D43). The editor's preview reads it after every step.

```json
{ "version": 9, "valid": true, "diagnostics": [],
  "model": { "schemaVersion": "0.10", "release": { "…": "…" }, "objectTypes": ["…"], "applications": ["…"] },
  "placements": { "applications": [{ "applicationKey": "catalogue", "topLevelObjectTypeKeys": ["category"],
                                     "parents": ["…"] }] } }
```

- A draft that does not compile answers `200` with `valid: false`, its `diagnostics` (each with its
  `element`, as the outline's) and no `model` or `placements`.
- It reads only: the draft's version and history are unchanged, and no lock is taken.
- Records are not part of it. A client previewing records reads them through the usual routes, which
  serve the active model; the editor shows records of released types that way, and an empty record for
  a type the draft adds (D44).
- Refusals: `404 MODEL_DRAFT_NOT_FOUND`. Registered with `MODEL_ADMIN_MUTATIONS_ENABLED`, as the other
  draft routes.

**A type without a detail page** shows the page the browser falls back to and cannot be laid out by the
view verbs, which name a declared page. `addDetailPage` declares the page a new type gets (an attributes
panel in `main`, a hierarchy panel in `side` when it has a parent, a children panel when it contains
types, a relations panel when a binding names it at its `from` end); the editor's layout editor sends it
as a step of its own (**Declare its page**), since the fallback page names its panels differently. On a
type with a page it is refused `INVALID_OPERATION` (`alreadyPresent`).

### A draft's consumer APIs

`GET /api/v1/model-drafts/{draftId}/consumer-apis/{consumerApi}` answers one consumer API definition of
the draft (A4c, D56): `version`, `valid`, `definition` as written, and when the draft compiles,
`expanded` (every default written out, as `GET /model/consumer-apis/{consumerApi}` serves the active
one) and `contract` (as the outline's). Three documents an integration takes from a draft before it
is installed, each a download of its own:

- `…/schema.json`: the **JSON Schema** (2020-12) of the object message the definition serves (its
  OpenAPI document's `Object` component and the schemas it refers to, under `$defs`), which an
  integration validates messages against or generates types from;
- `…/example.json`: **a message example**, one message valid against that schema, written by the
  server from it: a value of each property's type, a related block as one object or a list of one. No
  record is read, so the consumer tier never reads a model that is not running; messages from real
  records come from the consumer API after activation;
- `…/openapi.json`: the definition's **OpenAPI document** as the consumer tier will serve it.

They read only. Refusals: `404 MODEL_DRAFT_NOT_FOUND`, `404 CONSUMER_API_NOT_FOUND`
(`details.consumerApi`), and for the three documents `422 INVALID_MODEL` with the diagnostics while
the draft does not compile. Registered with `MODEL_ADMIN_MUTATIONS_ENABLED`, as the other draft
routes.

### Source files and their profiles

`POST /api/v1/source-files` is `multipart/form-data` with a `file` and a `request`
`{ "owner": { "draftId": "…" } }` or `{ "owner": { "profileKey": "…" } }`. It answers `201` with the
file and the profiling job:

```json
{ "id": "…", "name": "supplier.xlsx", "format": "xlsx", "bytes": 182044, "sha256": "…",
  "owner": { "draftId": "…" }, "uploadedAt": "…", "version": 1,
  "profile": { "state": "queued", "jobId": "…" } }
```

- A source file is a resource of its own (D5), stored in `JOB_FILE_DIR` under its own name, limited by
  `IMPORT_MAX_BYTES`, deleted with its owner. The latest file per owner is kept while the owner
  exists; an older one is removed `JOB_RETENTION_DAYS` after a newer one arrived.
- Profiling is a job of kind `profile`, on the worker that runs imports. Its rows are staged in
  PostgreSQL and its statistics are set statements over them (principle 6).
- **`GET …/profile/sheets`** (paged) lists sheets with their row count, detected header row and
  blocks (`range`, `headerRow`). **`GET …/profile/sheets/{sheet}/columns`** (paged) gives each
  column's `header`, `letter`, `filled`, `distinct`, `valueTypes` (count per type the attribute
  registry can read), `candidateKey`, `delimiters` (character and share of cells it splits),
  `placeholders` (value and count) and `overlaps` (another column, or a field of a mapped type's
  existing records in a named workspace, with the share of values found). Bounded lists name their
  limit.
- `POST /imports` gains `sourceFileId` in place of the `file` part (D5), so a load names the file
  the editor profiled.
- Refusals: `413 IMPORT_TOO_LARGE`, `422 UNSUPPORTED_FILE_FORMAT`, `404 SOURCE_FILE_NOT_FOUND`,
  `409 SOURCE_FILE_PROFILE_NOT_READY` (`details.state`), `409 VERSION_CONFLICT` on delete.

### The dry-run summary

For a draft with source files and profiles, the 0.9 import preview runs against the draft's compiled
model (not the active release) in a rolled-back transaction, in the workspace the request names. It
writes nothing.

```json
{ "sourceFileId": "…", "workspaceKey": "main", "coverage": "complete",
  "rows": { "total": 200, "run": 200 },
  "sources": [ { "source": 0, "objectType": "unit", "records": { "created": 14, "updated": 0,
                 "unchanged": 0 }, "values": 28, "relationships": 0, "relatedRecords": 0,
                 "rejections": [ { "code": "DUPLICATE_KEY_IN_FILE", "rows": 2 } ] } ],
  "difference": { "sources": [ { "source": 0, "records": { "created": 14 }, "was": { "created": 0 } } ] },
  "draftVersion": 9, "ranAt": "…" }
```

- Each operation's answer carries the summary when the draft holds source files (A5's editor reads it
  there); `GET …/dry-run` reads the latest; `POST …/dry-run` `{ "full": true }` runs every row as a
  job.
- **`coverage`** is `complete` up to `JOB_PREVIEW_MAX_ITEMS` rows (D9's 10,000) and `sample` above it:
  a deterministic sample, the same rows each time, so differences compare like with like. The
  full run is on request. The 1-second budget is measured once in A3 and recorded.
- **`GET …/dry-run/rows`** (paged, `source=`, `status=`, `code=`) lists the rows behind a figure,
  as `/jobs/{id}/rows` does for an import.

### Inferences (A6)

`POST /api/v1/model-drafts/{draftId}/inferences`
`{ "sourceFileId": "…", "mode": "newApplication" | "extend", "applicationKey": "…" }` runs the table
patterns over the file's profile as a job and applies nothing. `GET …/inferences/{id}/proposals`
(paged) lists proposals: `pattern`, `evidence` (the statistics and sample values it rests on),
`operations` (a batch of the kinds above), `alternatives` (other batches), and `disagreements` with
pinned elements. A proposal is accepted by sending its operations, changed or not, with
`"proposalId"` to `POST …/operations`; nothing is applied otherwise. An element a request from the
administrator touched is **pinned**: a later inference reports a disagreement and never proposes to
change it. The optional assistant (A-D5) adds proposals through the same shape and is off unless
configured.

## Planned integration endpoints

Designed in [INTEGRATION_API.md](INTEGRATION_API.md) and sequenced in the
[Base 0.9 plan](BASE_0_9_IMPLEMENTATION_PLAN.md); each contract moves here when its package is delivered.

- Webhook subscriptions
- Consumer API publications and events ([CONSUMER_API.md](CONSUMER_API.md)); get by ID, lists,
  XREF, batch resolve and crosswalk are delivered (above)

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
  `409 MAPPING_VERSION_CONFLICT` with an instruction to refresh coverage and the current version in
  `error.details.mappingVersion`. A cursor for another version, anchor or context is `422 INVALID_CURSOR`.
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

### Workspace edge list (mapping list; Base 0.9 Q2)

- `GET /api/v1/workspaces/{workspaceKey}/relations` is the edge list: a flat, cursor-paged list of
  the workspace's edges of any relation type. The same list was also published as
  `GET /api/v1/workspaces/{workspaceKey}/mappings` until H4c removed it (decided D-1, 2026-10-02); that
  path keeps only the mapping replacement's `PUT` and answers a `GET` with `405`.
  `GET /api/v1/relations` keeps its anchored shape.
  All filter parameters are optional:
  - `relationTypeKey` — filter to one relation type.
  - `fromObjectTypeKey`, `toObjectTypeKey` — filter to a specific object-type pair.
  - `direction` (`outgoing` | `incoming`) — when omitted, each edge appears **twice** (once per
    direction with swapped source/target), so consumers see the full picture without prior knowledge
    of direction semantics. When supplied, each edge appears once in the requested orientation.
  - `applicationKey` + `viewKey` — both required together; controls column projection only (the view's
    source/target display columns enrich the `fields` dict). Without a view, default projection returns
    `id`, `objectTypeKey`, `name` and an empty `fields` dict.
  - `changeSetId` or `publicationId` — read a change set or an immutable publication instead of live
    data; both together are `422 MUTUALLY_EXCLUSIVE_CONTEXT`. A cursor binds its context.
  - `search` — case-insensitive substring on source or target name (max 500 characters).
  - `cursor`, `pageSize` (1–100; defaults to 20 without a view, or the view's configured page size).
- Returns the standard page. Each item contains `relationId`, `relationTypeKey`, `direction`
  (`"outgoing"` or `"incoming"`), `source` and `target` object summaries, the stored relation
  `attributes` and the source anchor's `mappingVersion` (always `0` in a publication, which is
  immutable, as in mapping coverage).
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
  bindings (`422 IMMUTABLE_RELATION`) and required-ownership bindings
  (`422 REQUIRED_OWNERSHIP_BINDING`). Clearing a required relation is `422 REQUIRED_RELATION`, and
  so is replacing a required relation whose other record has no other one (D36, Base 0.9 B3), with
  `details.objectId` naming that record.
- Direction-aware cross-cardinality is enforced at the target's end: one-to-one always; one-to-many
  on the outgoing direction, many-to-one on the incoming direction (Base 0.9 K3a). Violations return
  `409 CARDINALITY_VIOLATION`. Ancestor-scoped uniqueness is
  validated against the final graph, excluding edges being replaced. Duplicate scopes return
  `409 DUPLICATE_RELATION_SCOPE`; a missing required ancestor returns `422 RELATION_ANCESTOR_REQUIRED`
  in both mapping and generic relation writes, live or change set.
- Tokens are checked before no-op detection. A stale mapping token returns `409 MAPPING_VERSION_CONFLICT`
  with `{mappingVersion, targetCount, targets (≤20), targetsNextCursor}` in error details and no
  changes. Change set aggregate conflicts remain distinct (`409 CHANGE_SET_VERSION_CONFLICT`).
  Large conflict sets include a signed continuation cursor and the selected `applicationKey`/`viewKey`;
  pass these with the binding, source and returned version to `GET /mapping-targets`. When no mapping
  view exists, omit both view keys for a binding-only name projection. Coverage and candidate reads
  still require a declared view. Supplying only one view key is rejected. Explicit empty view keys
  are supplied identities and fail lookup; they never select the binding-only fallback.
  Change set context requires `expectedChangeSetVersion` (`409 CHANGE_SET_REQUIRED` if omitted).
- Preserves the selected existing relation identity when the target is retained, removes obsolete
  edges, updates selected attributes or creates a new edge. Maintains all affected outgoing/incoming
  set versions atomically without double increments: the source anchor is incremented once per
  direction, each affected target is incremented once in the opposite direction.
- Omitted `attributes` preserve a retained edge's values; for a new edge they supply no explicit
  values and normal defaults/validation apply. An explicit attribute object replaces the complete set;
  `{}` clears. Null target with non-empty attributes is `422 INVALID_CLEAR_ATTRIBUTES`. Typed writes
  use the canonical validation boundary. An identical complete state with valid tokens is a no-op
  with no version increment or audit event.
- Changes record underlying per-relation audit events (created/updated/deleted) and one mapping
  `transition` event with old/new targets, relation identities and attributes
  (`previousTargets`, `newTargets`). The save is the relation-set replacement a batch's
  `replaceRelationSet` item runs (Base 0.9 B3), with one target or none.

WP-9 verifies generic-write/mapping races, both directional sets, independent bindings and change set
activation versus live same-set changes. Confirmed missing foundation capabilities trigger a bounded
WP-10 slice and block acceptance; they do not retroactively change WP-3 scope.

## Product 0.8 relation matrix API (A2 and A3 delivered)

`GET /api/v1/workspaces/{workspaceKey}/relation-matrix` reads a schema 0.7 `relationMatrix` view
([model contract](APPLICATION_MODEL.md)): rows are records of the view's row type, columns are
records of its column type, and a cell holds the row's related records, through the view's binding
read from the row's end (`direction`), whose nearest ancestor of the column type is that column's
record. Everything comes from the view and its binding.

| Parameter | Meaning |
| --- | --- |
| `applicationKey`, `viewKey` | Required; an unknown application is `404 UNKNOWN_APPLICATION`, an unknown view, or a view of another type, `404 RELATION_MATRIX_VIEW_NOT_FOUND`. |
| `changeSetId` or `publicationId` | Optional read context; both together are `422 MUTUALLY_EXCLUSIVE_CONTEXT`. |
| `parentObjectId` | Only rows directly under this record. A record missing from the context is `404 RELATION_MATRIX_PARENT_NOT_FOUND`; one whose type cannot contain the row type is `422 RELATION_MATRIX_PARENT_SCOPE_MISMATCH`. |
| `search` | Case-insensitive "contains" match on the view's `searchFields` only. |
| `sort` | A row field as on an [object list](#collection-paging); name when omitted. |
| `columnIds` | Repeated; the column records to show, in order, at most 20 (`422 TOO_MANY_COLUMNS`, `422 DUPLICATE_COLUMN_IDS`). An ID that is not a column-type record in the context is `404 RELATION_MATRIX_COLUMN_NOT_FOUND` with the IDs in `details.columnIds`. |
| `columnCursor`, `columnPageSize` | Without `columnIds`, the columns are a name-ordered page of the column type's records (`columnPageSize` 1–20, default 20); pass `columnsNextCursor` or `columnsPrevCursor` back as `columnCursor`. Naming both `columnIds` and `columnCursor` is `422 CONFLICTING_COLUMN_PARAMETERS`. |
| `state` | `one`, `several`, `inactive`, `historyOnly` or `none`: only rows with a cell in that state in any of `columnIds`, decided over every row before paging, so totals count the filtered rows. Requires `columnIds` (`422 RELATION_MATRIX_STATE_REQUIRES_COLUMNS`). |
| `pageSize`, `cursor`, `from`, `position`, `seek`, `includeTotal` | Row paging, as every [collection](#collection-paging); `pageSize` 1–100 defaults to the view's. |

Rows are every record of the row type in the workspace context, including records another
application created: an application may list a type another one owns. Row cursors bind the context,
model, view, parent scope, search, sort, `columnIds` and `state`; column cursors bind the context,
model and view. A cursor used with other values is `422 INVALID_CURSOR`.

Each cell reports one state (D11), decided from the binding alone:

- `one`: exactly one related record under the column meets the binding's
  `uniqueWhenToAttributeEquals` condition (every record meets it when none is declared);
- `several`: more than one does; `conflict` is `true` when the binding's `uniqueToAncestorTypeKey` is
  the column type, which live writes refuse but a change set can hold until validation;
- `inactive`: related records exist and none meets the condition;
- `historyOnly`: none in the context, but an earlier publication of the workspace held one (every
  publication for live and change set reads; those numbered before it for a publication read);
- `none`: none of the above.

The condition and uniqueness scope describe the binding's `to` end, so they apply only when the row
is the `from` end (`direction: outgoing`); read `incoming`, every record meets the condition and
`several` is never a conflict.

```json
{
  "items": [{
    "row": {"id": "row-id", "objectTypeKey": "master-value", "name": "M1",
            "fields": {"name": "M1", "value-code": "VC-M1", "ancestor:codelist": "Codelist"}},
    "relationSetVersion": 3,
    "cells": [{
      "columnId": "column-id",
      "state": "one",
      "conflict": false,
      "recordCount": 2,
      "matchingCount": 1,
      "records": [{"id": "cell-record-id", "name": "M1 en", "version": 1, "relationId": "relation-id",
                   "relationVersion": 1, "meetsCondition": true, "fields": {"translated-name": "…", "active": true}}],
      "publication": null
    }]
  }],
  "nextCursor": null,
  "columns": [{"id": "column-id", "name": "Language en", "label": "en"}],
  "columnsNextCursor": null,
  "columnsPrevCursor": null
}
```

The page carries the [collection paging](#collection-paging) fields (omitted above). `row.fields`
holds the view's `rowColumns`, typed as record reads return them (`path`, `ancestor:<type>`,
`objectType` and timestamps included; timestamps are `null` in change sets and publications).
`label` is the column record's `columnLabelField`. A cell counts every record it holds
(`recordCount`) and those meeting the condition (`matchingCount`), and lists at most five,
those meeting the condition first, then by name. A `historyOnly` cell lists and counts the records of
the latest earlier publication that held any, named by `publication` (`id`, `number`), read-only.
`relationSetVersion` is the row's version of the view's relation set (ADR-022): the directional set
anchored on the row for the view's binding, which a link or unlink from the row claims; `0` until
first changed, and always `0` in a publication. Cell records carry their `version`, `relationId`
and `relationVersion` for writes (A3).

A page costs a fixed number of statements whatever the dataset holds: the rows through the object
query, the columns, every cell of the page in one statement (the page rows' relations, their related
records and one depth-bounded recursive walk up to the column record), the history evidence in one
statement over the workspace's publications, and the field values and set versions. The state filter
reads stored cell states (A3b, ADR-033): the matching rows are found once per request by index and
the page, its total and a position jump filter by them. Where a context's states are not built yet
(for example while a startup build is still running), it derives the cells from records instead,
with the same result. The read holds one database snapshot throughout.

### Writes from a cell (A3)

A cell writes through the generic APIs, live or with `changeSetId` in a change set, each write in one
transaction; the view's `cellActions` say which a client offers:

| Action | Request |
| --- | --- |
| `create` | `POST /api/v1/objects` of the cell type, `parentObjectId` a container from the read below, the row in `initialRelations` (`direction` `incoming` when the view reads `outgoing`, and the reverse), and `cellFields` as `attributes`. The name is the client's to propose. |
| `edit` | `PATCH /api/v1/objects/{cellType}/{id}` with the cell record's `version` as `expectedVersion`, changing `cellFields`. |
| `link` | `POST /api/v1/relations` between the row and a candidate, claiming the row's set: `expectedRelationSetVersion` is the row's `relationSetVersion`, `relationSetDirection` the view's `direction`. |
| `unlink` | `DELETE /api/v1/relations/{relationId}` with the cell record's `relationVersion` as `expectedVersion` and the same claim. |

A stale record, relation or set version is `409 VERSION_CONFLICT` or `409
RELATION_SET_VERSION_CONFLICT`; a uniqueness breach is `409 DUPLICATE_RELATION_SCOPE` naming the
record already in the scope (`conflictingObjectId`). A breach staged in a change set, including one a
moved container brings under another column record, shows as a `several` cell with `conflict` and is
reported by validation and refused at publishing (`422 WORKSPACE_GRAPH_INVALID`), leaving the
change set in place.

`GET /api/v1/workspaces/{workspaceKey}/relation-matrix/containers` lists where a new cell record can
go: the column record and the records under it whose type can directly contain the cell type, walked
through the container types only, in path order.

| Parameter | Meaning |
| --- | --- |
| `applicationKey`, `viewKey` | Required, as for the matrix. A view without `create` in `cellActions` is `422 RELATION_MATRIX_ACTION_NOT_ALLOWED`. |
| `columnId` | Required; a column-type record in the context, else `404 RELATION_MATRIX_COLUMN_NOT_FOUND`. |
| `changeSetId` | Optional; writes happen live or in a change set, so there is no publication context. |
| `search` | Case-insensitive "contains" match on the container's name. |
| `pageSize` (1–100, default 50), `cursor`, `from`, `position`, `includeTotal` | [Collection paging](#collection-paging). Cursors bind the context, view, column and search. |

Each item has `id`, `objectTypeKey`, `name` and `path`, the records from below the column record down
to the container (empty for the column record itself). `defaultContainerId` names the column's only
container, whatever the search and page, and is `null` when it has none or several (D13).

`GET /api/v1/workspaces/{workspaceKey}/relation-matrix/link-candidates` lists the cell-type records
under a column record that a row could be linked to, in name order, with the same parameters plus
`rowId` (a row-type record in the context, else `404 RELATION_MATRIX_ROW_NOT_FOUND`); a view without
`link` is `422 RELATION_MATRIX_ACTION_NOT_ALLOWED`. Each item has `id`, `objectTypeKey`, `name`,
`version`, `path`, the view's `cellFields` as `fields`, and `eligible`. An ineligible candidate is
listed, so totals stay truthful, with a `reason`:

- `alreadyLinked`: the row already relates to it;
- `rowCardinality` or `candidateCardinality`: the binding's cardinality allows no further relation of
  its relation type at that end, as relation creation counts it;
- `scopeTaken`: the binding's `uniqueToAncestorTypeKey` is the column type (read `outgoing`), the
  candidate meets its condition, and the row already holds a record in the column that does. A scope
  of another type is left to the write.

The page carries the row's `relationSetVersion`, which the link claims. A page costs a fixed number of
statements: one walk down from the column record, the page's values and paths (one lookup per
hierarchy level), and for candidates their relations and the row's cell.

## Product 0.8 restructuring API (Milestone C design)

Designed in C0 ([ADR-034](DECISIONS.md#adr-034--a-records-type-can-change-derived-mapping-preview-and-apply-history-as-the-way-back));
C1–C3 deliver it, and this section becomes the contract as they do. **C1 (delivered 2026-09-29)** makes
the `reclassified` audit event, the D42 refusal, the change-list changes and the publishing behaviour
below the contract. **C2 (delivered 2026-09-29)** settles the plan below in the engine's planner
(`engine/operations/restructuring.py`) for `move` and `changeType`. **C3 (delivered 2026-09-29)** adds the
routes, the other operation kinds, the paging of `records` and the parent candidates'
`includeTypeChanges`, so the whole section is now the contract. C5 accepted it end to end, and R2
(2026-09-29) accepted it for release in 0.8.0. A restructuring changes the shape
of a hierarchy inside a change set: records move and change type, keeping their IDs, and a level can be
inserted or removed. There is no live form (D38).

### Operations

- `POST /api/v1/change-sets/{changeSetId}/restructurings/preview` plans an operation and writes
  nothing.
- `POST /api/v1/change-sets/{changeSetId}/restructurings` applies it.

Both take the same body. `operation` names one kind:

| `kind` | Fields | Meaning |
| --- | --- | --- |
| `move` | `objectId`, `parentObjectId` (`null` for the top level), optional `objectTypeKey` | Move a record, changing its type when the target needs it. Without `objectTypeKey`, the current type is kept where allowed, the only possible type is taken, and several possible types are a question in the plan. |
| `changeType` | `objectId`, `objectTypeKey` | Change a record's type under the same parent. |
| `insertLevel` | `parentObjectId` (`null` for the top level), `childObjectIds` (at least one, distinct, each directly under that parent), `objectTypeKey`, `name` | Create a record of `objectTypeKey` under the parent and move the chosen children under it, each keeping its type where the new record can contain it. Its values and relations come from `inputs` under the reserved `objectId` `"new"`; an attribute given no value takes its attribute type's default. |
| `removeLevel` | `objectId` | Delete the record and move its children to its parent, each keeping its type where the parent can contain it. The record is deleted with its relationships, which the plan lists as its `withoutPlace.relationships`; one the other end requires is refused `requiredRelationWithoutPlace`. |
| `changeTypeUnder` | `objectId`, `fromObjectTypeKey`, `objectTypeKey` | Change every record of `fromObjectTypeKey` below `objectId` (not the record itself), at any depth, each under its own parent. The walk reads the whole subtree level by level; only the records it changes count toward the limit. |

The rest of the body:

- `choices.types`: `[{ "objectTypeKey", "parentObjectTypeKey", "newObjectTypeKey" }]`, the type a
  record of `objectTypeKey` becomes under a parent of the new type `parentObjectTypeKey`, where the
  plan asks.
- `choices.mappings`: `[{ "fromObjectTypeKey", "toObjectTypeKey", "attributes": [{ "attributeTypeKey",
  "from" }], "restore" }]`, per type pair. `from` names a source attribute type or is `null` for no
  source; attributes not listed keep the suggestion. `restore` (default `true`) takes the values and
  relationships offered back.
- `inputs`: `[{ "objectId", "attributes": [{ "attributeTypeKey", "value" }], "relations": [{
  "relationTypeKey", "direction", "objectId" }] }]`, per record, in the shapes of object creation's
  `attributes` and `initialRelations`. A `null` value for an optional attribute leaves it empty.
- `expectedChangeSetVersion` (required on apply; optional on the preview, which then answers `409
  CHANGE_SET_VERSION_CONFLICT` when the change set has moved on, and otherwise reports the version it
  read).
- Apply only: `planDigest` from the preview.
- Preview only: `outcome` (a list filtering `records`), `pageSize` (1–500, default 100) and the
  [paging](#collection-paging) fields `cursor`, `position`, `from` and `includeTotal`, one of
  `cursor`, `position` and `from: "end"` at a time (`422 CONFLICTING_PAGE_PARAMETERS`).

`inputs` name each record once, and `childObjectIds` do not repeat; either is a `422` validation
error.

### The plan

The preview answers `200` with:

- `changeSetId`, `changeSetVersion` (read) and `planDigest`, a hash of the change set's identity and
  version, the normalized request (without paging) and the complete resolved plan.
- `status`: `ready`, `needsInput` (inputs or type questions open) or `refused` (a refusal).
- `summary`: `recordCount`, `typeChangeCount`, `moveCount`, `createdCount`, `removedCount`,
  `valuesWithoutPlaceCount`, `relationshipsWithoutPlaceCount`, `restoredCount`, `inputsNeededCount`
  and `refusalCount`.
- `typeQuestions`: `[{ "objectTypeKey", "parentObjectTypeKey", "options", "chosen", "recordCount" }]`.
- `pairs`: one per (old type, new type) pair with its `recordCount`, `restore`, and per attribute of
  the new type its `attributeTypeKey`, `from`, `rule` (`sameType`, `display`, `uniqueRequired`,
  `choice` or `none`), the other compatible sources `alternatives`, and counts `kept`, `mapped`,
  `restored`, `inputs` and `empty`; the source attributes with no place (`withoutPlace`:
  `attributeTypeKey`, `count`), and `relations` (`relationTypeKey`, `direction`, `outcome` `kept` or
  `withoutPlace`, `count`). `name` is always kept and not listed. A rule takes a source only when no
  earlier rule took it; a choice may name any compatible source or `null`, and a source the old type
  does not bind or that is not compatible is `422 INVALID_TYPE_MAPPING`.
- `refusals`: at most 20 operation-level refusals with `refusalCount` and `refusalsTruncated`.
- `records`: a page of the records the operation changes, in plan order (the operation's records,
  then each level down, by name and ID; `insertLevel` lists the created record, then the children it
  takes; `removeLevel` the removed record, then its children). Each has `objectId`, `name`, `path`
  (after the operation, from the root, as `id`, `name` and `objectTypeKey`; a removed record's is
  where it was),
  `before` and `after` (`objectTypeKey`, `parentObjectId`; `before` is `null` for a created record,
  `after` for a removed one; `after.objectTypeKey` is `null` while the record's type question is open
  or it has no possible type, and nothing below it is planned), `outcomes` (`typeChanged`, `moved`, `created`, `removed`), `attributes`
  (`attributeTypeKey`, `from`, `outcome`: `kept`, `mapped`, `restored`, `input`, `default` (a
  created record's attribute type default) or `empty`, and the typed `value`), `withoutPlace` (`attributes` with values; `relationships` with `relationId`,
  `relationTypeKey`, `direction`, the other end's `objectId`, `objectTypeKey` and `name`),
  `restoredRelationships` (the same shape), `inputsNeeded` (`kind` `attribute` or `relation`, the key,
  and `reason`: `required`, `invalidValue`, `atLeastOneOf` (one entry per attribute the rule names)
  or `requiredRelation`) and `refusals`.

The `outcome` filter takes `typeChanged`, `moved`, `withoutPlace`, `restored`, `needsInput` and
`refused`, so a client pages through what needs attention. `records` page by position in the plan
order; the page links are the standard ones, and cursors bind the change set, its version, the
`planDigest` and the filter. A later page of a changed plan is `422 INVALID_CURSOR`.

Refusal codes, per record or for the operation: `noPossibleType` (a level has no type the new parent
can contain), `typeNotAllowed` (the chosen type cannot be here), `application` (another application's
type or parent, D39), `cycle`, `notRoot` (the top level for a type that is not `rootCreatable`),
`uniqueness` (a value or scope collision, naming `conflictingObjectId`), `requiredRelationWithoutPlace`
(a relationship the other end requires and the new type cannot hold, or a removed record takes with
it, naming `conflictingObjectId`), `notInChangeSet` (a named record the change set does not hold) and
`notUnderParent` (an `insertLevel` child that is not directly under the parent). A refusal has `code`, `message`,
`objectId` when it concerns one record, and `details`. A plan with no other refusal, question or input
is dry-run through the change set write services and rolled back, so the preview refuses what applying
would; the first write refused becomes that record's refusal (with the codes above where one fits,
otherwise the engine's error code) and the dry run stops there.

A request the planner cannot read is an error, not a plan: `422 OBJECT_TYPE_UNCHANGED` for a
`changeType` to the record's own type, `422 UNKNOWN_OBJECT_TYPE` for a type the pinned model lacks and
`422 INVALID_TYPE_MAPPING` for a mapping choice as above. A `move` that changes neither the type nor
the parent plans no records.

A record is counted once whatever happens to it. More than 500 (D41, lowered from 5,000 by D44) is
`422 RESTRUCTURING_TOO_LARGE` with `details.limit` and nothing planned. An unknown change set is
`404 CHANGE_SET_NOT_FOUND`; a publication or live context does not exist for this API.

### Apply

The apply recomputes the plan in the write transaction and writes it only when it matches:

- a stale `expectedChangeSetVersion` is `409 CHANGE_SET_VERSION_CONFLICT`;
- a different plan is `409 RESTRUCTURING_PLAN_CHANGED` with the current `planDigest`;
- a plan that is not `ready` is `422 RESTRUCTURING_NOT_READY` with its `summary` and at most 20
  refusals.

Every refusal writes nothing. Success returns `200` with `operationId`, `changeSetId`, the new
`changeSetVersion` (advanced once for the operation), the `summary` and `createdObjectId` (the ID
`insertLevel` gave its record, otherwise `null`). The change set's review
(the change lists below) then shows every record and relationship the operation touched.

What is written: each changed record's row with its new type, parent and values; the containment edge
kept, or removed and added as a move does; relationships without a place removed and those offered
back restored with their former IDs; for `insertLevel` a created record, for `removeLevel` a deleted
one. Derived state (typed value index, matrix cell states, relation set versions, search index)
follows through the existing hooks.

### Audit: `reclassified`

Each type change records one audit event on the record (`aggregateType` `change-set-object`,
`action` `reclassified`, the row's new version), in place of an `updated` event. Its stored payload
holds `changeSetId`, `operationId`, `objectType` (`before`, `after`), the `parent` when it moved, the
mapping used per attribute, and `before`: the record's name, parent, typed values and the
relationships it lost with their attributes and versions. Its subjects are the record and the other
end of each lost relationship, so their histories show it. Records the operation only moves, creates
or deletes record the existing `updated`, `created` and `deleted` events with the same `operationId`
(the `deleted` event names the relationships removed with the record in `relationIds`).

The history read (`GET …/history`) lists the event with `action: "reclassified"`, `changedFields`
naming `objectType` first and then what else changed (`parent`, `attributes`, `relationships`), and
`attributeTypeKeys` naming the attribute types given a value (kept, mapped, restored or an input), the
source of each mapped value, and those without a place; it does not return values, as for other
events. The other end of a lost relationship lists the same event. Offer-backs read
the payloads of a record's `reclassified` events whose `changeSetId` is the current change set or a
published one (a `published` event names it), the latest first. A value is offered from the latest
event whose `before` holds the attribute, only when that event left it without a place and only to an
attribute of the new type that no source fills. A lost relationship is offered, with its former ID,
when it is not effective, its other end exists and the model binds it to the new type.

### Changes to existing reads

- **Type in the route (D42).** Every `/objects/{objectTypeKey}/{objectId}` route — the record,
  attributes, history, parent candidates, and the change-set `PATCH` and `DELETE` — returns
  `409 OBJECT_TYPE_CHANGED` when the record is found in the selected context under another type (it
  was `404 OBJECT_NOT_FOUND` before C1), with `details.objectId`,
  `details.objectTypeKey` (the current type) and `details.requestedObjectTypeKey`. Live keeps the old
  type until the change set is published; a publication keeps the type it was published with. A
  history cursor from the old route is `422 INVALID_CURSOR` on the new one.
- **Change lists (P2a).** An object entry's `before` and `after` gain `objectTypeKey`, and
  `changedFields` names `objectType` first when it differs between the two sides. A removed record
  has no after side, so it never names `objectType`, even when the change set changed its type before
  removing it; its fields follow its source type's order (C5). The `objectTypeKey` filter matches either
  side; the entry's `objectTypeKey` and order stay the change set's. A relation entry's ends read as
  the change set holds them, and it is `containment` when its `to` end's type on either side is a
  child the relation type contains, so a reclassified record's former parent edge is still marked.
- **Parent candidates (B2).** In a change set, `includeTypeChanges=true` also lists records of types
  that can contain another type of the record's application (by the planner's rule: exactly one parent
  relation), each with `objectTypeKeys`, the types the record would become there: its own type under a
  type that already contains it, otherwise the possible types, of which the preview asks for one when
  there are several. `parentObjectTypeKey` may then name any of those types. Without it, the list is
  unchanged and candidates carry no `objectTypeKeys`; with it outside a change set, `422
  TYPE_CHANGES_NEED_CHANGE_SET` (a type changes only in a change set, D38).
- **Placements (C4, D45).** `GET /api/v1/model/placements` (the same `workspaceKey`, `changeSetId` or
  `publicationId` context as `GET /model`, with its `ETag`) answers where the context's model lets
  records stand: per application, `topLevelObjectTypeKeys` (the `rootCreatable` types) and `parents`,
  one per type of the application with `childObjectTypeKeys` (the types it contains) and
  `possibleObjectTypeKeys` (the types a record can become under it: those it contains through exactly
  one parent relation, as the planner decides). It is the engine's one rule; clients read it instead
  of re-deriving containment from the model.
- **Parent candidates within types (C4).** `withinObjectTypeKey` (repeatable, live or in a change set)
  keeps the list to a set of types, for a client that shows only some types, such as a tree view:
  only candidates of those types, and with `includeTypeChanges` only those types in each candidate's
  `objectTypeKeys`; a candidate left with none is not listed. The server filters, so `totalCount`,
  positions and cursors (which bind the set) mean what they mean without it. A type the model lacks
  is `422 UNKNOWN_OBJECT_TYPE` with `details.objectTypeKeys`.

### Publishing

Nothing changes in the publish contract. A reclassified record is an authored row: publishing claims its
base version against live (`409 VERSION_CONFLICT` for a record edited live since the base), writes its
new type, and validates the merged graph (`422 WORKSPACE_GRAPH_INVALID` for a live relationship,
child or value the new type cannot have). Removed relationships follow the existing relation merge
rules, including mapping-set divergence.
