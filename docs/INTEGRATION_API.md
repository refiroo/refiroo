# Integration API (Product 0.9)

Status: design drafted 2026-09-29. The management-side integration contracts of
[Base 0.9](BASE_0_9_IMPLEMENTATION_PLAN.md). All sections are drafted on the accepted decisions
(D1–D16); each track's packages reference them and amend them when delivery finds a gap.

The [consumer API](CONSUMER_API.md) is a separate, read-only tier with its own contract versions.
[API.md](API.md) remains the reference for delivered endpoints: each package moves its contract there
when it is delivered, and this document keeps the design and its reasons.

| Section | Contents | Track | State |
| --- | --- | --- | --- |
| [P](#p-shared-primitives) | Items and outcomes, failure policies, per-item concurrency, idempotency, jobs, limits | P | P1–P5 and P7 delivered in B1, P6's background run in B2 ([API.md](API.md#background-jobs)); job files with J |
| [B](#b-bulk-writes) | Bulk object create, update, upsert and delete; record references and upsert keys; bulk relations and relation-set replacement | B | Object items delivered in B1 (inline) and B2 (background) ([API.md](API.md#batches-and-jobs-base-09-b1-b2-b3)); B4 in B3 |
| [J](#j-import-and-export) | Import (file contract as an import profile per [MODEL_AUTHORING](MODEL_AUTHORING.md#import-profile), preview, execute) and export (scope, context, output) | J | Draft |
| [F](#f-change-feed) | Raw change feed: entries, per-workspace position, retention, recovery, consumer events | F | Draft |
| [Q](#q-queries) | Cross-type lookup (0.8 P1), workspace edge list (0.8 P3), model-aware query, effective periods and `asOf` | Q | Draft; Q1 delivered |

## P: Shared primitives

Bulk writes (B), import and export (J) are built from the primitives below. The change feed (F) is
not: it is positioned by sequence, not by job, and its recovery is separate from retrying a job
(SC-10).

### P1: One mechanism — a batch is a job

Every bulk write and every import or export is a **job**: a persisted record with its parameters, its
state and one outcome per item. A synchronous bulk request creates a job of kind `batch` and runs it
inline within the synchronous limit (D13), returning its outcomes in the response. A larger batch, an
import or an export runs the same job in the background.

So a sync batch whose response is lost can be read back by job ID or replayed by idempotency key; a
background job resumes after a restart; and outcomes, cancellation, retention and audit cause are
implemented once.

### P2: Items and outcomes

A batch request carries `items`. Each item may carry a client `ref` (1–200 characters), echoed in its
outcome so the caller can match it to a source row without relying on position.

Each item ends in exactly one status:

| Status | Meaning | Carries |
| --- | --- | --- |
| `applied` | The item's change is committed | `action`: `created`, `updated`, `unchanged` or `deleted`; the record's `id`, type key and new `version` |
| `rejected` | The item was evaluated and refused | `error` in the API error envelope shape: the same `code` a single write returns for the same cause, `message`, and `details` with a JSON pointer into the item |
| `unprocessed` | The item was not applied and not refused on its own merits | `reason`: `BATCH_ROLLED_BACK`, `JOB_CANCELLED`, `MODEL_RELEASE_CHANGED` or `JOB_FAILED` |

`unchanged` is an upsert or update whose values equal the stored record. It bumps no version, writes
no audit entry and produces no feed event, so re-sending a recurring feed is cheap and silent
downstream. It is decided before any version claim (D24, B1): an item that would write nothing can
overwrite nothing, so it needs no `expectedVersion` and a stale one does not refuse it.

The three statuses are fixed. The `action` and `reason` values may grow: a later merge or retired-ID
redirect ([composable domains](COMPOSABLE_DOMAINS.md#identity)) adds an action, as it does in the feed
(F2). The OpenAPI document lists today's values; readers must treat an action or reason they do not
know as applied or unprocessed by its status, never as an error.

A rejection uses the single-write error code (`DUPLICATE_ATTRIBUTE_VALUE`, `VERSION_CONFLICT`,
`PARENT_CYCLE`, …) because the item went through the same service (plan principle 1). Codes that
exist only for batches are listed with the section that introduces them.

A finished job reports counts (`applied`, `rejected`, `unprocessed`, and `applied` split by action) and
a `result`: `applied` (every item applied), `partial` (some applied, some not) or `rejected` (none
applied). A processed batch answers `200` whatever its `result`; the caller reads `result`, never the
status code alone, to learn whether everything applied. Request-level failures (malformed body, over
the limit, unknown workspace or change set, disabled capability) answer with the normal error envelope
and create no job.

### P3: Failure policies (D1)

Each request names its policy; there is no default, so no caller gets one by accident.

- **`atomic`**: all items apply or none do. Items apply in order in one transaction, each through its
  single write against the data the items before it left (D23, B1: sequential, not a check of the
  combined end state, so swapping two records' unique values needs a change set). The first rejected
  item rolls everything back, and every other item is `unprocessed` with `BATCH_ROLLED_BACK`. The size
  is limited by the atomic maximum (D13).
- **`independent`**: each item stands alone. Items apply in order, each inside a savepoint; a rejected
  item rolls back only itself. Work commits in chunks (P6), so a failure later in the job never undoes
  an earlier applied item.

Within `independent`, a later item may depend on an earlier one in the same batch (a child after its
parent). It sees the earlier item only if that item applied; otherwise it is rejected on its own
terms (for example `OBJECT_NOT_FOUND` for its parent), not skipped.

**Change-set context.** With `changeSetId`, the batch writes into that change set instead of live
(ADR-026) and claims `expectedChangeSetVersion` once for the whole job, like one single write. The
completed job reports the change set's new version (`changeSetVersion`); a job that changed nothing
leaves the version as it was. An `independent` job in a change set holds the
claim between chunks: a concurrent writer to the same change set makes the remaining items
`unprocessed` with `JOB_FAILED` and the job fails with `CHANGE_SET_VERSION_CONFLICT` (B2: each chunk
that changes something advances the version by one, and the job's `changeSetVersion` is the version
it holds).

### P4: Per-item concurrency (D11)

Updates never silently overwrite a newer version.

- **Update** items require `expectedVersion`, as a single update does.
- **Upsert** items may carry `expectedVersion`. Without it, an upsert that finds an existing record it
  would change is rejected with `VERSION_REQUIRED`, unless the request declares `onExisting: "overwrite"`. Then the
  item is read and written in one savepoint, so no concurrent write is lost between them. The audit
  entry records that it overwrote without a version claim, and the outcome reports the previous
  version. A recurring feed from an authoritative source opts in explicitly; nothing does so by default.
- **Relations and mapping** use relation-set versions (ADR-022), specified in section B.

### P5: Idempotency

A POST that creates a job accepts an `Idempotency-Key` header (1–200 printable characters). The key is
scoped to the route and the workspace, and stored with a fingerprint of the request: a SHA-256 of the
canonical JSON body, or of the uploaded file's checksum plus the job parameters.

| Retry | Answer |
| --- | --- |
| Same key, same fingerprint, job finished | The original job's response, with `Idempotent-Replayed: true`. Nothing runs again |
| Same key, same fingerprint, job still running | `409 IDEMPOTENCY_IN_PROGRESS` with the job ID and `Retry-After` |
| Same key, different fingerprint | `422 IDEMPOTENCY_KEY_REUSED`; nothing runs |
| Key older than retention (D14) | Treated as new |

The header is optional. Without it, a retried request is still safe where the item is idempotent: a
create with a client-supplied `id` answers `OBJECT_ALREADY_EXISTS`, and an upsert answers `unchanged`.
Retrying a create without an `id` and without a key can duplicate records; the reference says so
explicitly.

An inline batch writes its job, its items' changes, their outcomes and its key in one transaction, so
its key names a finished job; a background job's key is stored with the queued job, and
`IDEMPOTENCY_IN_PROGRESS` answers it until the job finishes (B2). A replayed background job answers
`202` with the job as it is now. A key's expiry follows its job's `expiresAt`. The `409` carries
`Retry-After` (B1).

### P6: Jobs

```text
GET  /api/v1/jobs?workspaceKey=…&kind=…&state=…   (ADR-030 paging)
GET  /api/v1/jobs/{jobId}
GET  /api/v1/jobs/{jobId}/items?status=…           (outcomes in item order, ADR-030 paging)
POST /api/v1/jobs/{jobId}/cancel                  (202 with the job; B2)
GET  /api/v1/jobs/{jobId}/output                   (export and preview output; section J)
```

Jobs are created by their own routes (sections B and J), which return `202` with the job for background
work, or the finished job for a synchronous batch.

**Shape.** `id`, `kind` (`batch`, `import`, `export`), `workspaceKey`, `changeSetId`,
`changeSetVersion`, `policy`, `parameters` (the kind's other choices: `run` and `onExisting` for a
batch, B1), `modelReleaseId`, `state`, `stage` (kind-specific, for example `validating`, `previewed`,
`applying`), `progress` (`total` when known, `processed`), the counts and `result` of P2, `error` for
a job-level failure, `createdAt`, `startedAt`, `finishedAt` and `expiresAt`; B2 adds
`cancelRequestedAt`, `leaseOwner` and `leaseExpiresAt`.

**States.** `queued` → `running` → `completed` | `failed` | `cancelled`. An import also passes
`awaiting_confirmation` after its preview (section J). `expired` replaces any final state when
retention ends: the job's summary remains, its item outcomes and files are removed. `failed` is a
job-level failure (unreadable file, `MODEL_RELEASE_CHANGED`, a lost change-set claim), never "some items
were rejected"; that is `completed` with `result: partial`.

**Chunks and resumption.** A background job works in chunks. Each chunk's data writes, item outcomes
and the job's checkpoint commit in one transaction, so a job resumed after a crash starts at the first
uncommitted item and never repeats or skips one. An `atomic` job is one chunk. The worker holds a
lease on the job (`leaseOwner`, `leaseExpiresAt`); a restarted process picks up running jobs whose
lease expired. The worker runs in the application process while the engine is single-node (0.9); the
lease is what lets 0.11 run it on several nodes without a contract change.

As delivered (B2, D27–D30): a background job's items wait in a `job_inputs` table, one row per item,
stored with the queued job and removed when it finishes (D27). A chunk is `JOB_CHUNK_ITEMS` (500)
items. The lease (`JOB_LEASE_SECONDS`, 120) is renewed with each chunk's commit; a chunk does not
hold the job row while it applies items, and before committing it locks the row and checks that it
still holds the lease, rolling back when another worker took the job over. A worker stopping
gracefully releases its leases. A failure other than an item's refusal rolls back the chunk and
fails the job with `JOB_FAILED` and a correlation ID (D29). Items the job did not reach get their
`unprocessed` outcome in one statement from their inputs, so `progress.processed` equals `total`
once the job is finished.

**Model release.** A job pins the active model release when it is created (ADR-015 extended from a
request to a job). If the active release changes before the job finishes, the next chunk fails the job
with `MODEL_RELEASE_CHANGED`: applied chunks stay applied, and every remaining item is `unprocessed`
with that reason. A job in a change set pins the change set's release (B2): moving the change set to
another release fails it the same way, and a release activated while a live chunk runs refuses that
chunk at commit (0.8 W5), which then counts as not reached. An inline batch is one chunk committed with its job, so a release activated while
it runs refuses the request (`409 MODEL_RELEASE_CHANGED`) and nothing is saved, the job included (B1).

**Cancellation.** Cancel takes effect between chunks. Items not reached are `unprocessed` with
`JOB_CANCELLED`; an `atomic` job rolls back completely.

As delivered (B2, D28): the route sets `cancelRequestedAt` in one short transaction and answers `202`;
a finished job is `409 JOB_FINISHED`. The worker does every finish, a queued job's included, at the
next chunk; an `atomic` job's chunk checks before every 500 items it decides and before it writes
them (0.9.0-alpha.1 PG3b). The design relies on PostgreSQL's READ
COMMITTED: a cancel request commits while a chunk runs and the chunk's next read sees it.

**Audit cause.** Every applied item writes the same audit entries as the equivalent single write, plus
the job ID as the cause. The feed and consumer events report it (`cause: {kind: "job", id}` in
CONSUMER_API), and a later value-source field builds on it (ADR-032, provenance).

**Files (D12).** Uploaded and exported files are stored in a configured directory (`JOB_FILE_DIR`)
with their size and checksum recorded on the job; they are not database rows. Output is served only
by a `completed` job, so partial output cannot be mistaken for a complete one. A batch's items are
not a file (D27); the directory arrives with the first package that stores one (J1 or J2).
_Delivered in J1:_ `JOB_FILE_DIR` (default `var/job-files`, D55) holds `{jobId}.partial` while an
export writes and `{jobId}.{extension}` once it completes; a file is kept while its job is completed
and removed when the job expires, fails or is cancelled; no path is stored on the job.

**Retention (D14, B2).** The worker expires finished jobs past `expiresAt` every hour: the job becomes
`expired` with its summary kept, and its outcomes, inputs and idempotency keys are removed. A process
with the capability off runs no worker and so expires nothing.

**Capability (D10).** Job execution is a deployment capability group (ADR-031),
`INTEGRATION_JOBS_ENABLED`, on by default like live writes. A process with it off registers no route
that creates or cancels a job and runs no worker; job reads stay available.

### P7: Limits (D13)

Every limit is a setting reported by `GET /api/v1/capabilities` (`integrationJobs.limits`) and named
in the error that enforces it (`413 BATCH_TOO_LARGE` with `details.setting`, `details.maximum` and the
request's `items` or `bytes`, B1). Recommended defaults, to be confirmed against
the 0.8 Track S volume fixture in the first B package:

| Limit | Default |
| --- | --- |
| Synchronous batch | 1,000 items and 5 MB body |
| `atomic` job | 10,000 items |
| Background job | 1,000,000 items; upload 200 MB (J); a JSON batch body of 50 MB (B2, `BATCH_BACKGROUND_MAX_BYTES`) |
| Retention of jobs, outcomes, files and idempotency keys (D14) | 7 days |

## B: Bulk writes

A batch applies many writes through the same services as the single-write routes (plan principle 1).
It adds addressing by key, upsert and relation-set replacement; it adds no second validation path.

### B1: Routes

```text
POST /api/v1/batches        items, policy, context; runs inline or in the background
```

Every batch is a job of kind `batch` (P1) and is read back through `/api/v1/jobs`. One route serves
objects, relations and relation sets, because an atomic load often needs all three in one
transaction (a record, its required relation and its mapping).

```json
{
  "workspaceKey": "main",
  "policy": "atomic",
  "run": "inline",
  "onExisting": "reject",
  "items": [
    { "ref": "row-2", "op": "upsert", "objectTypeKey": "codelist", "applicationKey": "rdm-master",
      "key": { "attributeTypeKey": "codelist-code" },
      "name": "Timetable types",
      "parent": { "objectTypeKey": "domain", "key": { "attributeTypeKey": "domain-code", "value": "CONNECTIONS" } },
      "attributes": [ { "attributeTypeKey": "codelist-code", "value": "MOT" } ] },
    { "ref": "row-2/map", "op": "replaceRelationSet", "relationTypeKey": "system-value-maps-to-master",
      "fromObjectTypeKey": "system-value", "toObjectTypeKey": "master-value", "direction": "outgoing",
      "anchor": { "id": "…" }, "targets": [ { "object": { "id": "…" } } ],
      "expectedRelationSetVersion": 3 }
  ]
}
```

- **Context.** `workspaceKey` for live, or `changeSetId` with `expectedChangeSetVersion` (P3); exactly
  one. Items carry no context of their own.
- **`policy`** is required: `atomic` or `independent` (P3, D1).
- **`run`** is required: `inline` answers `200` with the finished job and its first page of outcomes
  and is limited by the synchronous maximum (`413 BATCH_TOO_LARGE` above it); `background` answers
  `202` with the queued job. The caller chooses; the size never switches the response shape silently.
- **`onExisting`**: `reject` (the default) or `overwrite`, for upserts without `expectedVersion` (P4,
  D11). It applies to the whole request, so an authoritative feed opts in once.
- **`stage`** (0.9 K2, D112, D113): `execute` (the default) or `preview`, a background batch run
  without writing and waiting for confirmation ([B8](#b8-previewing-a-batch-09-k2)).
- **Body size.** A JSON batch is bounded by the request body limit (a setting, 50 MB by default). A
  larger load is an import of a JSON Lines file whose lines are these items (J2), with the background
  job limits.
- `Idempotency-Key` as in P5.

### B2: Record references

Wherever an item names an existing record (the target of an update, a parent, a relation end, a
relation-set anchor or target) it takes a **reference**:

| Form | Resolves to |
| --- | --- |
| `{ "id": "…" }` | The record with that public ID |
| `{ "objectTypeKey": "…", "key": { "attributeTypeKey": "…", "value": … } }` | The record of that type whose value of an attribute declared `unique` is that value |

A key reference uses only attributes declared `unique` on the type (ADR-010), whose uniqueness is per
workspace, so it matches at most one record. An attribute not declared unique is refused per item as
`INVALID_RECORD_KEY`. No match is `REFERENCE_NOT_FOUND`; a match of another type than named is
`REFERENCE_TYPE_MISMATCH`, both naming the JSON pointer of the reference. References resolve against
the batch's context as it stands when the item runs, so they see earlier applied items of the same
batch (P3). The import profile's non-unique match keys (J3) resolve to IDs before they reach a batch;
a batch never matches by name.

### B3: Object items

| `op` | Required | Semantics |
| --- | --- | --- |
| `create` | `applicationKey`, `objectTypeKey`, `name` | As `POST /objects`: optional `id`, `parent` (a reference), `attributes`, `initialRelations` (`relationTypeKey`, `direction`, `object`: a reference, `attributes`) |
| `update` | `target`, `expectedVersion` | As `PATCH /objects/…`: `name`, `parent` (a move, B2 of 0.8), `attributes` merged as a single PATCH merges them, including its treatment of `null` |
| `upsert` | `objectTypeKey`, `applicationKey`, `key`, `name` | Finds the record by `key`; creates it as `create` when absent; otherwise updates it as `update` under P4. Its `initialRelations` are used only when it creates (D26, B1); an absent `parent` keeps a found record where it is |
| `delete` | `target`, `expectedVersion` | As `DELETE`, with its optional `cascade` and `deletionPreviewToken` (0.9 K2b): without `cascade` a record with children or non-parent relations is rejected `OBJECT_HAS_DEPENDANTS` with its impact and token; with it the record goes with its dependants under the impact its token confirms |

**Upsert key (D2).** `key` is `{ "id": "…" }` (a client-assigned public ID, used on create) or
`{ "attributeTypeKey": "…" }`, naming a unique attribute whose value the item's own `attributes`
supply (`MISSING_RECORD_KEY` otherwise). No composite keys in 0.9. A key that finds a record of
another type or application is `REFERENCE_TYPE_MISMATCH`; an upsert never changes a record's type
(that is restructuring, ADR-034).

**Unchanged.** An update or upsert whose name, parent and attributes equal the stored record applies
as `unchanged` (P2): no version, audit entry or feed entry. With `onExisting: "overwrite"` the check
runs first, so re-sending an unchanged feed never needs a version.

**Cascade (0.9 K2b, D120–D123; PG-D18).** A cascading delete item is confirmed per item by the
single delete's token: a batch preview computes each item's impact and token, and confirming
carries the tokens into the stored items, so execution deletes exactly what was previewed and
refuses an item whose impact changed (`DELETION_PREVIEW_CHANGED`); an execute batch sends its tokens
itself (`DELETION_PREVIEW_REQUIRED` without one). Items are decided in order: a record several
items reach belongs to the earliest, and a record an earlier item of the job deleted answers
`unchanged` with `deletedWithItem`. A delete's outcome and its dependants refusal carry `impact`
(counts by type and the token, never lists); a preview adds `deletion` totals. A run of delete items
is set work in PostgreSQL, live and in a change set, and the single `DELETE` runs through the same
path ([API.md](API.md#deleting-with-what-depends-on-it-09-k2b)).

### B4: Relation items

| `op` | Required | Semantics |
| --- | --- | --- |
| `createRelation` | `relationTypeKey`, `from`, `to` | As `POST /relations`, ends as references; optional `attributes` and a relation-set claim (`expectedRelationSetVersion`, `relationSetDirection`) |
| `ensureRelation` | `relationTypeKey`, `from`, `to` | Idempotent create: when a relation of that type already joins the two ends, `unchanged` if its attributes equal the item's (or the item has none), otherwise an update under P4 with the relation's `expectedVersion` |
| `updateRelation` | `id`, `expectedVersion`, `attributes` | As `PATCH /relations/{id}` |
| `deleteRelation` | `id`, `expectedVersion` | As `DELETE /relations/{id}`; optional relation-set claim |
| `replaceRelationSet` | binding (`relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction`), `anchor`, `targets` | The complete directional set of one anchor becomes `targets`, under `expectedRelationSetVersion` (ADR-022) |

`replaceRelationSet` is the mapping operation generalised from one target to a set: `targets` is a
list (possibly empty) of `{ "object": reference, "attributes"?: {…} }`. Existing relations to a
retained target keep their identity; omitted `attributes` keep a retained relation's values, an
explicit object replaces them (as the 0.7 mapping PUT). Cardinality, ancestor-scoped uniqueness,
required and containment bindings are refused with the codes of the mapping PUT. Without
`expectedRelationSetVersion` the item follows P4: `VERSION_REQUIRED` unless `onExisting: "overwrite"`.
It writes the same per-relation audit entries and one `transition` entry as the mapping PUT, and one
relation-set version increment per affected set.

Containment relations are never items: a parent changes through an object's `parent`
(`IMMUTABLE_RELATION` otherwise).

As delivered (B3, D35–D39, contract in [API.md](API.md#batches-and-jobs-base-09-b1-b2-b3)): relation
items are decided in memory through the single relation writes' decide steps and written in bulk
with the object items around them (D35); the single routes and the mapping PUT are batches of one
through the same steps. A set claim is checked against the set as the items before it leave it,
under the workspace's or change set's lock. `ensureRelation` takes an optional `expectedVersion`
for the update it may become. `replaceRelationSet` decides `unchanged` before its claim (D37, as
D24); removing a relationship whose other record requires one and has no other is
`REQUIRED_RELATION` (D36, also on the mapping PUT); a target listed twice is `DUPLICATE_RELATION`,
and an anchor or target of another type than the binding's end is `REFERENCE_TYPE_MISMATCH` (D39).
The anchored read `GET /relations?objectId=…` names every set the record anchors with its version
(`relationSets`, D38). The `transition` entry lists `newTargets` and takes no feed position.

### B5: Outcomes and responses

Outcomes are P2's, in item order, each with its `ref`. An applied object item reports `id`,
`objectTypeKey` and `version` (none after a live delete); a relation item `relationId` and `version`; a set replacement the
anchor's new `relationSetVersion` and the created, kept and removed relation IDs. As delivered (B3,
D37): a relation item's `version` is absent after a delete and its claimed set's new
`relationSetVersion` is added; a set replacement's `action` is `updated` or `unchanged` and its IDs
are `relationIds: {created, kept, removed}`.

```json
{
  "job": { "id": "…", "kind": "batch", "state": "completed", "result": "partial",
           "counts": { "applied": 1, "rejected": 1, "unprocessed": 0,
                       "created": 1, "updated": 0, "unchanged": 0, "deleted": 0 } },
  "items": [
    { "index": 0, "ref": "row-2", "status": "applied", "action": "created",
      "id": "…", "objectTypeKey": "codelist", "version": 1 },
    { "index": 1, "ref": "row-2/map", "status": "rejected",
      "error": { "code": "RELATION_SET_VERSION_CONFLICT", "message": "…",
                 "details": { "pointer": "/items/1/expectedRelationSetVersion", "relationSetVersion": 4 } } }
  ],
  "nextCursor": null
}
```

An inline response carries the first page of outcomes (page size 1,000, so every inline batch fits);
later pages come from `GET /jobs/{id}/items`. As delivered (B1) the response is that page, with its
ADR-030 navigation fields, plus `job`; an outcome carries only its status's fields.

### B6: Codes introduced by batches

`BATCH_TOO_LARGE` (413), `VERSION_REQUIRED`, `INVALID_RECORD_KEY`, `MISSING_RECORD_KEY`,
`REFERENCE_NOT_FOUND`, `REFERENCE_TYPE_MISMATCH` (per item), and the P5 idempotency codes. Every
other rejection is the single write's code. Request level (B1): `INVALID_BATCH_CONTEXT` (not exactly
one of `workspaceKey` and `changeSetId`) and, until B2, `run_not_available`. B2: `JOB_FINISHED` (409,
cancelling a finished job). B3 adds none: relation items answer with the single relation writes'
codes, `VERSION_REQUIRED` (P4) and the reference codes of B2.

### B7: Audit, feed and cost

Each applied item writes the audit entries of its single-write equivalent with the job as cause
(P6), so object history, the feed (F) and consumer events see a batch as its individual changes. The
first B package confirms the D13 limits on the 0.8 Track S volume fixture and records budgets:
per-item cost of an inline independent batch of 1,000 upserts, an atomic batch of 10,000 creates,
and a 100,000-item background batch, live and in a change set. B1 recorded the first two in D13; the
background batch is B2's.

### B8: Previewing a batch (0.9 K2)

A background batch sent with `stage: preview` runs as an import's preview does (§J1, D80, D82,
D83): its first `JOB_PREVIEW_MAX_ITEMS` items run independently whatever the policy, in one
transaction rolled back whole, and the job waits in `awaiting_confirmation` with the preview's
summary and outcomes. `POST /jobs/{jobId}/confirm` removes those outcomes and runs the stored items
from the first as an execution: one execution path, and execution is authoritative. The preview
needs a background run (D113): a waiting preview is a job state the worker confirms, so an inline
one would answer outcomes and then still need the worker. The UI's bulk changes (Track K) send
every change this way (D114), and an integrator gets a dry run of any batch.

## F: Change feed

The raw management feed lists every change to a workspace's live data in commit order. Sync tools
follow it; consumer events (CONSUMER_API) are derived from it. **Delivered by F1 (2026-10-03):** F1–F4,
with the read moved into F1 (D31); the contract is in [API.md](API.md#change-feed-base-09-f1-f2).
**Delivered by F2 (2026-10-03):** F5, amended by D40 and D41.

### F1: What the feed contains

| Source | Feed entries |
| --- | --- |
| Live create, update, delete, move of a record; attribute value writes | One per record change (`object`) |
| Live relation create, update, delete; relation-set replacement | One per relation change (`relation`) |
| Type change (ADR-034) | `reclassified` for the record, plus its relation changes |
| Publishing a change set | One per record and relation the publish changes in live data (D15, D32): records created, updated or reclassified; relations removed; relations created or updated; records removed; then one `publication` entry |
| Withdrawing a publication | One `publication` entry |
| Batch, import job | The entries of its items, with the job as cause |
| Change-set edits, validation, discard; model administration | None: they change no live data |

The mapping `transition` audit entry is not a feed entry; its relation entries are. A containment
relation is the record's parent, which the record's entry names (`parentObjectId`); it is not an entry
of its own, live or published (F1, as a live move already audited it).

### F2: Entry shape

```json
{
  "position": 18422,
  "eventId": "…",
  "occurredAt": "2026-10-14T10:14:03Z",
  "kind": "object",
  "action": "updated",
  "id": "…",
  "objectTypeKey": "master-value",
  "applicationKey": "rdm-master",
  "version": 7,
  "changedFields": ["name", "attributes"],
  "attributeTypeKeys": ["description"],
  "cause": { "kind": "job", "id": "…" },
  "modelReleaseId": "…"
}
```

- `kind`: `object`, `relation` or `publication`. A relation entry carries `relationTypeKey`,
  `fromObjectId` and `toObjectId` instead of `objectTypeKey`; they identify the ends even after a
  delete.
- `action`: `created`, `updated`, `deleted`, `reclassified` (with `previousObjectTypeKey`), or for a
  publication `published` and `withdrawn`.
- `changedFields` and `attributeTypeKeys` are the object-history vocabulary: names, never values
  (D16, the erasure door). A reader that needs values reads the record.
- `cause`: `{kind: "user"}`, `{kind: "job", id}` or `{kind: "publication", id}`. A restructuring
  changes a change set, never live data, so it reaches the feed through its publish. Provenance
  (ADR-032) extends `cause` additively.
- An object entry also carries `applicationKey`; a publication entry's `id` is the publication's
  and its `version` the publication number.
- A later merge or retired-ID redirect adds an action (`merged`, with the surviving ID); readers must
  ignore actions they do not know.

### F3: Position and ordering (D5)

`position` is a per-workspace integer, gapless and strictly increasing in commit order.

- `workspaces` gains a `feed_position` counter; `audit_events` gains `workspace_key` and a nullable
  `feed_position`, unique per workspace. Entries that change no live data (F1) have none.
- A live write takes the workspace row lock (`SELECT … FOR UPDATE`) **before any record row**,
  increments the counter for each entry it writes and holds the lock until commit. Publish already
  locks the workspace first, so the lock order is one rule: workspace, then records.
- A transaction with several entries gets consecutive positions. A rolled-back transaction rolls back
  its counter too, so there are no gaps, and no reader ever sees a position commit before a lower one.
- Cost: writes to one workspace serialize, as they already do under the workspace lock
  (0.9.0-alpha.1 PG3); different workspaces stay independent. The first F package measures the added statement per
  write against the 0.8 write budgets.
- No backfill: the feed starts empty at the 0.9 migration. Earlier changes remain in object history;
  a reader starts from a baseline (F5).

### F4: Reading

```text
GET /api/v1/workspaces/{workspaceKey}/feed?after={position}&pageSize=…&kind=…&objectTypeKey=…
```

- `after` is the last position the reader processed (`0` for the start). The position is public and
  stable, so it is the resume token itself; no cursor is needed.
- `pageSize` 1–1,000, default 500. `kind` and `objectTypeKey` (repeatable) filter: values of one
  filter match any of them, and the two combine. `objectTypeKey` matches object entries whose type,
  or for `reclassified` whose previous type, is listed; relation and publication entries never match
  it (D34).
- `after` past `headPosition` is `409 FEED_POSITION_AHEAD` with `details.headPosition` (D33): such a
  position was not read from this workspace's feed, or the database was restored, and new changes
  reuse its numbers.
- The response carries `items`, `nextAfter` (the position to pass next), `headPosition` (the highest
  committed position) and `earliestPosition` (the retention floor). A filtered page scans at most ten
  times `pageSize` positions; it may return fewer items, even none, with `nextAfter` advanced, so a
  sparse filter never costs an unbounded scan.
- The reader is caught up when `nextAfter` equals `headPosition`.
- Ungated like other reads until 0.12 (D10).

### F5: Retention and recovery (D8)

- `FEED_RETENTION_DAYS` (default 30), shared with consumer events (C-D9). Positions older than the
  floor expire: `after` below `earliestPosition - 1` answers `410 FEED_POSITION_EXPIRED`. The audit
  log itself is not pruned by this setting; object history is unaffected.
- The floor is the first entry within the period, but never past the active publication's
  `feedPosition + 1`; with no active publication that has a position, nothing expires (D40). Otherwise
  a baseline older than the period would itself be expired, and a workspace with no publication
  would have none to re-read.
- The `410` details name the recovery baseline: the workspace's active publication with its
  `feedPosition`. A reader re-reads the baseline, then follows the feed from the baseline's position.
  The export route (J4) joins as a second baseline when J1 delivers it (D41); J1 then revisits
  whether a workspace without a publication still keeps every entry. _Delivered in J1:_ the `410`
  names `export: {href: "/api/v1/exports"}`; a workspace without a publication still keeps every
  entry (D54).
- A publication's `feedPosition` is the position of its `published` entry; it equals live data at
  that position (C-D15, verified). An export records the position it read at.

### F6: Consumer events

Consumer events are derived from feed entries (C-D8, C-D11). One entry can produce several events
(a publish entry of a projected record updates each owning object) and several entries can
coalesce into one delivery. Each consumer event carries the `position` of the entry that caused it,
so positions compare with the raw feed and with a publication's `eventSequence`, which is its
`feedPosition`. The consumer pull feed pages by `after` position plus an opaque cursor within one
position. The deriver keeps a checkpoint per workspace and reads the feed like any reader.
_Delivered in C10 (2026-10-06):_ the pull feed's contract is in
[API.md](API.md#consumer-events-base-09-c10); a record's entry also names its parent, and its previous
parent when it moved, kept with the entry and not shown in the feed's answer (C-D95).

## Q: Queries

### Q1: Cross-type lookup (0.8 P1)

```text
GET /api/v1/objects?workspaceKey=…|changeSetId=…|publicationId=…&objectTypeKey=…&…
```

- The object list's paging, context and cursor rules (ADR-030), over every type, or the types named
  by a repeatable `objectTypeKey`; `applicationKey`, `parentObjectId` or `topLevel` narrow it.
- Built-in fields only: `search` matches the name; filters on `id`, `name`, `objectTypeKey`,
  `parentObjectId`, `createdAt`, `updatedAt`; `sort` by `name` (default), `id`, `objectType`,
  `createdAt`, `updatedAt`. Model-declared filters and sorts stay on the per-type route, where their
  types are known.
- Items have the per-type list's item shape, including `objectTypeKey` and attributes, so one item
  shape serves both lists.
- Budget: a name search over 100,000 records of mixed types within the per-type list's budget.

_Delivered in Q1 (2026-09-29); the contract is in [API.md](API.md#cross-type-lookup-base-09-q1). A
model-declared filter or sort is refused with `details.route` naming the per-type route. With no type
named, the list narrows by every declared type, which changes no result and lets the page indexes
serve it. The budget holds over the fixture's 258,000 records: see the
[Q1 record](BASE_0_9_IMPLEMENTATION_PLAN.md#q1-cross-type-lookup)._

### Q2: Workspace edge list (0.8 P3)

`GET /api/v1/workspaces/{workspaceKey}/mappings` already lists edges of any relation type. It gains
`publicationId` (exclusive with `changeSetId`: `422 MUTUALLY_EXCLUSIVE_CONTEXT`, the code every other
read uses), and the same handler is published as
`GET /api/v1/workspaces/{workspaceKey}/relations`, the name integrators look for. Both routes return
the one edge shape; `/mappings` remains for the mapping views. `GET /api/v1/relations` keeps its
anchored shape. Each route's cursors are its own. Delivered in 0.9 Q2; the contract is in
[API.md](API.md#workspace-edge-list-mapping-list-base-09-q2).

### Q3: Model-aware query (D4)

```text
POST /api/v1/workspaces/{workspaceKey}/queries/objects
```

A read with a body, because criteria over relations do not fit query parameters. It changes nothing
and needs no capability.

```json
{
  "objectTypeKey": "master-value",
  "context": { "publicationId": "…" },
  "asOf": "2026-10-01",
  "where": [
    { "field": "active", "op": "eq", "value": true },
    { "field": "ancestor:codelist", "op": "eq", "value": "…codelist id…" },
    { "related": { "relationTypeKey": "system-value-maps-to-master", "direction": "incoming",
                   "where": [ { "field": "external-id", "op": "startsWith", "value": "EPIC-" } ] } }
  ],
  "sort": "-updatedAt",
  "select": ["name", "code", "ancestor:codelist"],
  "expand": [ { "relationTypeKey": "system-value-maps-to-master", "direction": "incoming",
                "select": ["name", "external-id"], "limit": 20 } ],
  "pageSize": 100
}
```

- **`where`** is a list combined with AND. A criterion is a field, operator and value with the object
  list's grammar: the same fields (built-ins and attributes the type binds with `filterable`), the
  same operators per value type and the same typed input, plus `ancestor:<type>` with `eq` on the
  ancestor's ID (new here; it reads the containment path, not a relation hop). One
  relation hop: `related` is true when at least one record at the other end of that binding matches
  its own `where` (built-ins and that type's filterable attributes, no further hop); `"not": true`
  inverts it. OR groups, nested hops and several sort keys wait for a second real case (D4).
- **`sort`**: one field as on the object list, then the unique tie-breaker.
- **`select`** names the returned fields; omitted, items are the list's item shape. Items always carry
  `id`, `objectTypeKey` and `version`.
- **`expand`** adds, per item, the records at the other end of a binding the type has: at most
  `limit` (1–20) with `select`, plus `count` and a continuation for `GET /relations`. Expansion is
  batched per page, never a query per item.
- **`asOf`** (Q4). **Context**: live by default, `changeSetId` or `publicationId`.
- Paging as ADR-030 with `cursor` or `position`; the cursor binds a hash of the body. Unknown fields,
  operators or bindings are `422 INVALID_QUERY` with a JSON pointer.
- Budgets on the volume fixture: a one-hop criterion and a page with a 20-row expansion over 100,000
  records.

_Delivered in Q3 (2026-09-30); the contract is in [API.md](API.md#model-aware-query-base-09-q3).
Settled on the way (D17–D19): `not` stands beside `related` in the criterion; with `select`, values
are under `fields` and `ancestor:<type>` gives the `id` and `name` of the ancestor nearest the root;
`expanded` holds `count`, the first `limit` records with their `relationId`, and `nextCursor` for
`GET /relations`; the body's shape is `REQUEST_VALIDATION_ERROR` and what depends on the model
`INVALID_QUERY`. `parentObjectId` is a built-in criterion but not a sort. The budgets hold: see the
[Q3 record](BASE_0_9_IMPLEMENTATION_PLAN.md#q3-model-aware-query)._

### Q4: Effective periods and `asOf` (D6)

A type declares one business validity period in the model (APPLICATION_MODEL, schema 0.8):

```json
"effectivePeriod": { "startAttributeTypeKey": "valid-from", "endAttributeTypeKey": "valid-to" }
```

- Both attributes are `date` attributes the type binds. The start is inclusive, the end exclusive; an
  empty start means "since always", an empty end "open". A write whose end is not after its start is
  `422 INVALID_EFFECTIVE_PERIOD`. Overlapping periods of different records are allowed.
- `asOf=YYYY-MM-DD` on the per-type list, the model-aware query and exports returns the records
  effective on that date. It is a filter over values, not history: it combines
  with any context (live, change set, publication) and never reads a publication by itself.
- A type without a period answers `422 AS_OF_NOT_SUPPORTED`. **Amended in Q4 (D21, 2026-09-30):** the
  cross-type lookup lists several types, and a period belongs to one, so it refuses `asOf` with the
  per-type route, as it refuses a model-declared filter. The design had it filter the types with a
  period and name them in `asOfApplied`, copied from the consumer XREF (C-D14); no management story
  needs a dated lookup across types, and C-D14 stays with XREF (C16).
- `dateTime` periods wait for a real case.

_Delivered in Q4 (2026-09-30); the contract is in [API.md](API.md#effective-periods-and-asof-base-09-q4).
The model query dates the queried records only (D22), and activating a release that declares a
period over records it would refuse is `MODEL_MIGRATION_REQUIRED` with their count (D20)._

## J: Import and export

### J1: Import flow

```text
POST /api/v1/imports                 multipart: file + request (JSON)
POST /api/v1/jobs/{jobId}/confirm    run an import that awaits confirmation
POST /api/v1/jobs/{jobId}/cancel
GET  /api/v1/jobs/{jobId}/items      item outcomes, each with its sheet and row (ref=)
GET  /api/v1/jobs/{jobId}/rows       outcomes by row (J3, D84)
```

The request names the context (as B1), `policy`, `onExisting`, the profile (`profileKey` of a stored
profile, an inline `profile`, or neither for a JSON Lines file or a CSV whose headers are field keys
with `objectTypeKey` given) and `stage`: `preview` or `execute`.

1. **Validating.** The file is stored (D12), parsed and bound: every column binding is resolved
   against the pinned model release and every row converted to batch items (J3). Failures that stop
   the file (unreadable, a sheet or column the profile names that is missing, a binding that no
   longer resolves) fail the job with the path of each.
2. **Preview.** The items run through the batch services in a transaction that is rolled back, in the
   same order and policy as execution, so the preview predicts outcomes with the same codes. Up to the
   preview limit (a setting, default the atomic maximum, 10,000 items) the preview is `complete`;
   beyond it, every row is still parsed and bound, the first items run, and the preview says
   `sample` with the counts it covers. The job waits in `awaiting_confirmation` with counts by
   action (`created`, `updated`, `unchanged`, `rejected`), paged row outcomes and a binding report per
   column (resolved, converted, value-mapped and empty counts).
3. **Execute** on confirm, or directly with `stage: execute`. Execution is authoritative: data may have
   changed since the preview, and outcomes are recorded as they happen. A preview not confirmed within
   retention (D14) expires.

_Delivered in J2 (2026-10-07, D64, D67, D72):_ `POST /imports` with `stage: execute`; the file and the
request are one `multipart/form-data` body (`file`, `request` as JSON); binding stores the rejected rows
as the job's first outcomes and the items as its inputs in one commit, and each item's `ref` names its
row (`{sheet}!{row}`). Under `atomic` a rejected row ends the job before any item runs. `preview`,
`awaiting_confirmation`, confirm and the binding report are J3's. The contract is in
[API.md](API.md#imports-base-09-j2-j3).

_Amended in J3 (2026-10-07, D80–D87):_
- **The preview runs every item independently, whatever the policy (D80)**, not "in the same policy
  as execution": an atomic run stops at the first refusal and would show one problem per round trip.
  `result` states what the request's policy would give (`rejected` for `atomic` with any refusal).
  With no refusal, its outcomes equal an atomic run's, since each item sees the items before it
  either way.
- **Confirming binds the stored file again and executes it as `stage: execute` (D81)**, rather than
  running the preview's items: matches resolve against the data at execution, so "execution is
  authoritative" holds for the matches too.
- **The preview is one transaction rolled back whole**; its outcomes are recorded in a short one
  after (D82).
- **A sample (D83):** binding covers every row; items run in execution order up to
  `JOB_PREVIEW_MAX_ITEMS` (`IMPORT_PREVIEW_MAX_ITEMS` before 0.9 K2), so a sample previews records
  before relationships, and a row counts as
  previewed only once all its items ran.
- **Confirm, cancel and expiry (D87):** confirm is idempotent and checks the context again, a refusal
  leaving the job waiting; cancel finishes a waiting job at once (amending D28, where the worker does
  every finish: no worker claims a waiting job); a waiting job expires after D14's retention from the
  preview's end.
- Outcomes page by row (D84), a row names every failing cell (D85), and the binding report is on every
  import once bound (D86).

### J2: File contract

| Format | Rules |
| --- | --- |
| XLSX | One or several sheets; cell values, never formulas (a formula's cached value is read); dates from date cells or ISO 8601 text |
| CSV | UTF-8 (a BOM is accepted), RFC 4180 quoting, a header row, comma by default or a declared delimiter |
| JSON Lines | One batch item (B3, B4) per line; no profile. The export format, so an export re-imports as upserts |
| An export's table layout (J1, D51) | CSV or XLSX as an export writes them ([API.md](API.md#exports-base-09-j1)): `objectTypeKey` or `relationTypeKey` per row, built-in columns by key (with `applicationKey` on records, D71, added in J2), `#{attributeTypeKey}` columns, `~` columns ignored; read without a profile. XLSX text may hold Excel's `_xHHHH_` escapes, which the reader decodes (all XLSX text is decoded so) |

Values convert through the attribute registry by the target attribute's value type, with the same
canonical forms as the API (API.md, attribute format). A value that does not convert rejects its
row with `INVALID_ATTRIBUTE_VALUE` and the column. Empty cells are "no value", never an empty string,
unless a value map says otherwise. _As delivered (J2):_ a cell of only spaces is empty too, text is
otherwise kept as written, and "no value" leaves the attribute out of the item, so an import never
clears a value.

### J3: Import profile

The profile fixes the outline of [MODEL_AUTHORING](MODEL_AUTHORING.md#import-profile). It is runtime
data, not model content, since it names sheets and columns of files. _Amended in J2 (D65):_ profiles
are instance-wide, not per workspace: a profile maps a file to the model, which is instance-wide,
and the import names the workspace.

```text
POST/GET/PUT/DELETE /api/v1/import-profiles[/{key}]   (versioned, optimistic concurrency)
```

- **Sources** each load one object type from a sheet (or a block: first and last column and row),
  with a `headerRow` and an `upsertKey` (D2). Sources run in the order of their references (a source
  whose parent or relation targets another source's type runs after it); a cycle is an invalid
  profile.
- **Column bindings:** `field` (`name`), `attributeTypeKey`, `parent`, `relation` and `relationFlags`
  as in the outline; `relatedRecord`; `ignore`. `parent` and `relation` match by a field or attribute
  (`matchBy`), optionally split on a delimiter and mapped through a value map. A match key need not be
  unique: the job resolves it to IDs, and a value matching several records rejects the row with
  `reference_ambiguous`, naming the candidates' count.
- **`relatedRecord`** is the generic binding for a record that belongs to the row's record through a
  relation: it upserts a record of a named type, under a parent found by `matchBy` (for example the
  group holding one language's translations), related to the row's record by a named binding, with columns for its own fields. The
  outline's translation and system-mapping bindings are profiles of this one binding, not engine
  concepts (ADR-032); the 0.10 editor offers them as patterns.
- **Rows to items.** A row becomes an `upsert` of its record, `ensureRelation` items for relation and
  flag columns (or a `replaceRelationSet` when the binding declares `"replace": true`), and the items of
  its related records. A row's outcome is its worst item's, with every item's outcome available.
- **Validation** at save and at job start against the pinned release, with a path per binding. A
  profile records the release it was checked against (MODEL_AUTHORING).

_Final in J2 (2026-10-07, D66, D69, D70):_ the profile's JSON is [API.md's](API.md#import-profiles):
each source names its `applicationKey`; `key` is `{attributeTypeKey}` (unique) or `{column}` (the
public ID) or absent; `record: "existing"` writes only a row's relationships and related records;
`block`, `trueValues` on flags and fixed `value` matches are added; `translations` and
`systemMapping` are not bindings of their own but profiles of `relatedRecord`, which finds its record
through the relationship and its parent (D70); `modelReleaseKey` is the engine's `checkedAgainst`.
Rows repeating a key are one record when their values agree and all rejected
`DUPLICATE_KEY_IN_FILE` otherwise (D69). Source order counts parents, relationships and related
records' parents, so two sources whose relationships point at each other's types are a cycle; a
relationship needs no order inside a run, since relationships run after every record. Matches and
keys are resolved in PostgreSQL over the file's rows and the context's records (D68).

### J4: Export

```text
POST /api/v1/exports
```

- Request: `workspaceKey`; `context` (live, `changeSetId` or `publicationId`); `scope`: object types,
  optionally under one `parentObjectId` (a subtree), with `where` and `asOf` as in Q3; `include`
  relations whose both ends are in scope, or all relations of the exported records; `format` `jsonl`
  or `csv`.
- Output: JSON Lines of B3 `create` items with IDs, then B4 `createRelation` items; CSV as one file per
  type (a ZIP when several), with field keys as headers and parents and relation ends as IDs.
  _Amended in J1 (D49, D51):_ JSON Lines holds `upsert` items keyed by ID with the record's version
  as `expectedVersion`, then `ensureRelation` items, so a re-import changes nothing; CSV and XLSX
  share one table layout (records and relationships, `#{attributeTypeKey}` columns), CSV as one file.
- Consistency: the export reads one database snapshot, and a live export records the feed position of
  that snapshot, so it serves as a re-sync baseline (F5). A publication export is its publication.
- Output is served only by a `completed` job, with a manifest: counts per type, context, feed
  position, model release, format and SHA-256. A failed or cancelled export has no output, so a
  partial file cannot be taken for a complete one. Round trips preserve records, values, parents and
  relations; versions and history are not carried (SC-10 excludes lossless round trips). _Amended in
  J1:_ each record carries its version, so an edited file updates only records nobody changed since
  the export; history is not carried. The manifest is the job's `output`, never in the file (D52).
  _Delivered in J1 (2026-10-07):_ the contract is in [API.md](API.md#exports-base-09-j1); `format`
  also takes `xlsx`; `scope.types` carries a `where` per type, and `asOf` dates the types with a
  period (D50); exports run on a worker of their own from one snapshot (D53).
  _Amended in J5 (2026-10-08, D96, D97):_ an export loads into a second workspace of the instance with
  `otherWorkspaceIds: "counterparts"`, as that workspace's own records with derived IDs.

### J5: The SC-10 screen

One minimal screen, reached from the workspace: choose a file and a stored profile (or none), start a
preview, read the counts, the binding report and the rejected rows (paged, with sheet and row), then
confirm or cancel and read the result. No profile editing (0.10), no job list beyond the workspace's
recent imports.

### J6: Capability and files

Job creation (imports, exports, background batches) is under `INTEGRATION_JOBS_ENABLED` (D10). Files
live in `JOB_FILE_DIR` with size and checksum on the job (D12) and follow job retention (D14), except
a profile's latest source file kept for the 0.10 editor (0.10 D5).
