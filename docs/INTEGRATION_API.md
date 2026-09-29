# Integration API (Product 0.9)

Status: design drafted 2026-09-29. The management-side integration contracts of
[Base 0.9](BASE_0_9_IMPLEMENTATION_PLAN.md). All sections are drafted on the accepted decisions
(D1–D16); each track's packages reference them and amend them when delivery finds a gap.

The [consumer API](CONSUMER_API.md) is a separate, read-only tier with its own contract versions.
[API.md](API.md) remains the reference for delivered endpoints: each package moves its contract there
when it is delivered, and this document keeps the design and its reasons.

| Section | Contents | Track | State |
| --- | --- | --- | --- |
| [P](#p-shared-primitives) | Items and outcomes, failure policies, per-item concurrency, idempotency, jobs, limits | P | Draft |
| [B](#b-bulk-writes) | Bulk object create, update, upsert and delete; record references and upsert keys; bulk relations and relation-set replacement | B | Draft |
| [J](#j-import-and-export) | Import (file contract as an import profile per [MODEL_AUTHORING](MODEL_AUTHORING.md#import-profile), preview, execute) and export (scope, context, output) | J | Draft |
| [F](#f-change-feed) | Raw change feed: entries, per-workspace position, retention, recovery, consumer events | F | Draft |
| [Q](#q-queries) | Cross-type lookup (0.8 P1), workspace edge list (0.8 P3), model-aware query, effective periods and `asOf` | Q | Draft |

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
| `unprocessed` | The item was not applied and not refused on its own merits | `reason`: `batch_rolled_back`, `job_cancelled`, `model_release_changed` or `job_failed` |

`unchanged` is an upsert or update whose values equal the stored record. It bumps no version, writes
no audit entry and produces no feed event, so re-sending a recurring feed is cheap and silent
downstream.

A rejection uses the single-write error code (`duplicate_attribute_value`, `version_conflict`,
`parent_cycle`, …) because the item went through the same service (plan principle 1). Codes that
exist only for batches are listed with the section that introduces them.

A finished job reports counts (`applied`, `rejected`, `unprocessed`, and `applied` split by action) and
a `result`: `applied` (every item applied), `partial` (some applied, some not) or `rejected` (none
applied). A processed batch answers `200` whatever its `result`; the caller reads `result`, never the
status code alone, to learn whether everything applied. Request-level failures (malformed body, over
the limit, unknown workspace or change set, disabled capability) answer with the normal error envelope
and create no job.

### P3: Failure policies (D1)

Each request names its policy; there is no default, so no caller gets one by accident.

- **`atomic`**: all items apply or none do. Every item is validated against the batch's combined
  result, then everything commits in one transaction. If any item is rejected, every other item is
  `unprocessed` with `batch_rolled_back`. The size is limited by the atomic maximum (D13).
- **`independent`**: each item stands alone. Items apply in order, each inside a savepoint; a rejected
  item rolls back only itself. Work commits in chunks (P6), so a failure later in the job never undoes
  an earlier applied item.

Within `independent`, a later item may depend on an earlier one in the same batch (a child after its
parent). It sees the earlier item only if that item applied; otherwise it is rejected on its own
terms (for example `object_not_found` for its parent), not skipped.

**Change-set context.** With `changeSetId`, the batch writes into that change set instead of live
(ADR-026) and claims `expectedChangeSetVersion` once for the whole job, like one single write. The
completed job reports the change set's new version. An `independent` job in a change set holds the
claim between chunks: a concurrent writer to the same change set makes the remaining items
`unprocessed` with `job_failed` and the job fails with `version_conflict`.

### P4: Per-item concurrency (D11)

Updates never silently overwrite a newer version.

- **Update** items require `expectedVersion`, as a single update does.
- **Upsert** items may carry `expectedVersion`. Without it, an upsert that finds an existing record is
  rejected with `version_required`, unless the request declares `onExisting: "overwrite"`. Then the
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
| Same key, same fingerprint, job still running | `409 idempotency_in_progress` with the job ID and `Retry-After` |
| Same key, different fingerprint | `422 idempotency_key_reused`; nothing runs |
| Key older than retention (D14) | Treated as new |

The header is optional. Without it, a retried request is still safe where the item is idempotent: a
create with a client-supplied `id` answers `object_already_exists`, and an upsert answers `unchanged`.
Retrying a create without an `id` and without a key can duplicate records; the reference says so
explicitly.

### P6: Jobs

```text
GET  /api/v1/jobs?workspaceKey=…&kind=…&state=…   (ADR-030 paging)
GET  /api/v1/jobs/{jobId}
GET  /api/v1/jobs/{jobId}/items?status=…           (outcomes in item order, ADR-030 paging)
POST /api/v1/jobs/{jobId}/cancel
GET  /api/v1/jobs/{jobId}/output                   (export and preview output; section J)
```

Jobs are created by their own routes (sections B and J), which return `202` with the job for background
work, or the finished job for a synchronous batch.

**Shape.** `id`, `kind` (`batch`, `import`, `export`), `workspaceKey`, `changeSetId`, `policy`,
`modelReleaseId`, `state`, `stage` (kind-specific, for example `validating`, `previewed`,
`applying`), `progress` (`total` when known, `processed`), the counts and `result` of P2, `error` for
a job-level failure, `createdAt`, `startedAt`, `finishedAt` and `expiresAt`.

**States.** `queued` → `running` → `completed` | `failed` | `cancelled`. An import also passes
`awaiting_confirmation` after its preview (section J). `expired` replaces any final state when
retention ends: the job's summary remains, its item outcomes and files are removed. `failed` is a
job-level failure (unreadable file, `model_release_changed`, a lost change-set claim), never "some items
were rejected"; that is `completed` with `result: partial`.

**Chunks and resumption.** A background job works in chunks. Each chunk's data writes, item outcomes
and the job's checkpoint commit in one transaction, so a job resumed after a crash starts at the first
uncommitted item and never repeats or skips one. An `atomic` job is one chunk. The worker holds a
lease on the job (`leaseOwner`, `leaseExpiresAt`); a restarted process picks up running jobs whose
lease expired. The worker runs in the application process while the engine is single-node (0.9); the
lease is what lets 0.11 run it on several nodes without a contract change.

**Model release.** A job pins the active model release when it is created (ADR-015 extended from a
request to a job). If the active release changes before the job finishes, the next chunk fails the job
with `model_release_changed`: applied chunks stay applied, and every remaining item is `unprocessed`
with that reason.

**Cancellation.** Cancel takes effect between chunks. Items not reached are `unprocessed` with
`job_cancelled`; an `atomic` job rolls back completely.

**Audit cause.** Every applied item writes the same audit entries as the equivalent single write, plus
the job ID as the cause. The feed and consumer events report it (`cause: {kind: "job", id}` in
CONSUMER_API), and a later value-source field builds on it (ADR-032, provenance).

**Files (D12).** Uploaded and exported files are stored in a configured directory (`JOB_FILE_DIR`)
with their size and checksum recorded on the job; they are not database rows. Output is served only
by a `completed` job, so partial output cannot be mistaken for a complete one.

**Capability (D10).** Job execution is a deployment capability group (ADR-031),
`INTEGRATION_JOBS_ENABLED`, on by default like live writes. A process with it off registers no route
that creates or cancels a job and runs no worker; job reads stay available.

### P7: Limits (D13)

Every limit is a setting reported by `GET /api/v1/capabilities` and named in the error that enforces
it (`413 batch_too_large` with the limit in `details`). Recommended defaults, to be confirmed against
the 0.8 Track S volume fixture in the first B package:

| Limit | Default |
| --- | --- |
| Synchronous batch | 1,000 items and 5 MB body |
| `atomic` job | 10,000 items |
| Background job | 1,000,000 items; upload 200 MB |
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
  and is limited by the synchronous maximum (`413 batch_too_large` above it); `background` answers
  `202` with the queued job. The caller chooses; the size never switches the response shape silently.
- **`onExisting`**: `reject` (the default) or `overwrite`, for upserts without `expectedVersion` (P4,
  D11). It applies to the whole request, so an authoritative feed opts in once.
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
`invalid_record_key`. No match is `reference_not_found`; a match of another type than named is
`reference_type_mismatch`, both naming the JSON pointer of the reference. References resolve against
the batch's context as it stands when the item runs, so they see earlier applied items of the same
batch (P3). The import profile's non-unique match keys (J3) resolve to IDs before they reach a batch;
a batch never matches by name.

### B3: Object items

| `op` | Required | Semantics |
| --- | --- | --- |
| `create` | `applicationKey`, `objectTypeKey`, `name` | As `POST /objects`: optional `id`, `parent` (a reference), `attributes`, `initialRelations` (ends as references) |
| `update` | `target`, `expectedVersion` | As `PATCH /objects/…`: `name`, `parent` (a move, B2 of 0.8), `attributes` merged as a single PATCH merges them, including its treatment of `null` |
| `upsert` | `objectTypeKey`, `applicationKey`, `key`, `name` | Finds the record by `key`; creates it as `create` when absent; otherwise updates it as `update` under P4 |
| `delete` | `target`, `expectedVersion` | As `DELETE` without `cascade`: a record with children or non-parent relations is rejected `object_has_dependants` (without a preview token). A batch removes dependants itself, children before parents |

**Upsert key (D2).** `key` is `{ "id": "…" }` (a client-assigned public ID, used on create) or
`{ "attributeTypeKey": "…" }`, naming a unique attribute whose value the item's own `attributes`
supply (`missing_record_key` otherwise). No composite keys in 0.9. A key that finds a record of
another type or application is `reference_type_mismatch`; an upsert never changes a record's type
(that is restructuring, ADR-034).

**Unchanged.** An update or upsert whose name, parent and attributes equal the stored record applies
as `unchanged` (P2): no version, audit entry or feed entry. With `onExisting: "overwrite"` the check
runs first, so re-sending an unchanged feed never needs a version.

**Cascade** stays out of batches in 0.9: its preview token binds one record's confirmed impact, which
a batch cannot show. Deleting a subtree is a batch of deletes in child-first order.

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
`expectedRelationSetVersion` the item follows P4: `version_required` unless `onExisting: "overwrite"`.
It writes the same per-relation audit entries and one `transition` entry as the mapping PUT, and one
relation-set version increment per affected set.

Containment relations are never items: a parent changes through an object's `parent`
(`immutable_relation` otherwise).

### B5: Outcomes and responses

Outcomes are P2's, in item order, each with its `ref`. An applied object item reports `id`,
`objectTypeKey` and `version`; a relation item `relationId` and `version`; a set replacement the
anchor's new `relationSetVersion` and the created, kept and removed relation IDs.

```json
{
  "job": { "id": "…", "kind": "batch", "state": "completed", "result": "partial",
           "counts": { "applied": 1, "rejected": 1, "unprocessed": 0,
                       "created": 1, "updated": 0, "unchanged": 0, "deleted": 0 } },
  "items": [
    { "index": 0, "ref": "row-2", "status": "applied", "action": "created",
      "id": "…", "objectTypeKey": "codelist", "version": 1 },
    { "index": 1, "ref": "row-2/map", "status": "rejected",
      "error": { "code": "relation_set_version_conflict", "message": "…",
                 "details": { "pointer": "/items/1/expectedRelationSetVersion", "relationSetVersion": 4 } } }
  ],
  "nextCursor": null
}
```

An inline response carries the first page of outcomes (page size 1,000, so every inline batch fits);
later pages come from `GET /jobs/{id}/items`.

### B6: Codes introduced by batches

`batch_too_large` (413), `version_required`, `invalid_record_key`, `missing_record_key`,
`reference_not_found`, `reference_type_mismatch` (per item), and the P5 idempotency codes. Every
other rejection is the single write's code.

### B7: Audit, feed and cost

Each applied item writes the audit entries of its single-write equivalent with the job as cause
(P6), so object history, the feed (F) and consumer events see a batch as its individual changes. The
first B package confirms the D13 limits on the 0.8 Track S volume fixture and records budgets:
per-item cost of an inline independent batch of 1,000 upserts, an atomic batch of 10,000 creates,
and a 100,000-item background batch, live and in a change set.

## F: Change feed

The raw management feed lists every change to a workspace's live data in commit order. Sync tools
follow it; consumer events (CONSUMER_API) are derived from it.

### F1: What the feed contains

| Source | Feed entries |
| --- | --- |
| Live create, update, delete, move of a record; attribute value writes | One per record change (`object`) |
| Live relation create, update, delete; relation-set replacement | One per relation change (`relation`) |
| Type change (ADR-034) | `reclassified` for the record, plus its relation changes |
| Publishing a change set | One per record the publish applies to live (D15), then one `publication` entry |
| Withdrawing a publication | One `publication` entry |
| Batch, import job | The entries of its items, with the job as cause |
| Change-set edits, validation, discard; model administration | None: they change no live data |

The mapping `transition` audit entry is not a feed entry; its relation entries are.

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
- `cause`: `{kind: "user"}`, `{kind: "job", id}`, `{kind: "publication", id}` or
  `{kind: "restructuring", id}`. Provenance (ADR-032) extends it additively.
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
- Cost: writes to one workspace serialize, as they already do on SQLite's single writer; different
  workspaces stay independent on PostgreSQL. The first F package measures the added statement per
  write against the 0.8 write budgets.
- No backfill: the feed starts empty at the 0.9 migration. Earlier changes remain in object history;
  a reader starts from a baseline (F5).

### F4: Reading

```text
GET /api/v1/workspaces/{workspaceKey}/feed?after={position}&pageSize=…&kind=…&objectTypeKey=…
```

- `after` is the last position the reader processed (`0` for the start). The position is public and
  stable, so it is the resume token itself; no cursor is needed.
- `pageSize` 1–1,000, default 500. `kind` and `objectTypeKey` (repeatable) filter.
- The response carries `items`, `nextAfter` (the position to pass next), `headPosition` (the highest
  committed position) and `earliestPosition` (the retention floor). A filtered page scans at most ten
  times `pageSize` positions; it may return fewer items, even none, with `nextAfter` advanced, so a
  sparse filter never costs an unbounded scan.
- The reader is caught up when `nextAfter` equals `headPosition`.
- Ungated like other reads until 0.12 (D10).

### F5: Retention and recovery (D8)

- `FEED_RETENTION_DAYS` (default 30), shared with consumer events (C-D9). Positions older than the
  floor expire: `after` below `earliestPosition - 1` answers `410 feed_position_expired`. The audit
  log itself is not pruned by this setting; object history is unaffected.
- The `410` details name the recovery baselines: the workspace's active publication with its
  `feedPosition`, and the export route (J4). A reader re-reads the baseline, then follows the feed
  from the baseline's position.
- A publication's `feedPosition` is the position of its `published` entry; it equals live data at
  that position (C-D15, verified). An export records the position it read at.

### F6: Consumer events

Consumer events are derived from feed entries (C-D8, C-D11). One entry can produce several events
(a publish entry of a projected record updates each owning object) and several entries can
coalesce into one delivery. Each consumer event carries the `position` of the entry that caused it,
so positions compare with the raw feed and with a publication's `eventSequence`, which is its
`feedPosition`. The consumer pull feed pages by `after` position plus an opaque cursor within one
position. The deriver keeps a checkpoint per workspace and reads the feed like any reader.

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

### Q2: Workspace edge list (0.8 P3)

`GET /api/v1/workspaces/{workspaceKey}/mappings` already lists edges of any relation type. It gains
`publicationId` (exclusive with `changeSetId`), and the same handler is published as
`GET /api/v1/workspaces/{workspaceKey}/relations`, the name integrators look for. Both routes return
the one edge shape; `/mappings` remains for the mapping views. `GET /api/v1/relations` keeps its
anchored shape.

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
  operators or bindings are `422 invalid_query` with a JSON pointer.
- Budgets on the volume fixture: a one-hop criterion and a page with a 20-row expansion over 100,000
  records.

### Q4: Effective periods and `asOf` (D6)

A type declares one business validity period in the model (APPLICATION_MODEL, schema 0.8):

```json
"effectivePeriod": { "startAttributeTypeKey": "valid-from", "endAttributeTypeKey": "valid-to" }
```

- Both attributes are `date` attributes the type binds. The start is inclusive, the end exclusive; an
  empty start means "since always", an empty end "open". A write whose end is not after its start is
  `422 invalid_effective_period`. Overlapping periods of different records are allowed.
- `asOf=YYYY-MM-DD` on the per-type list, the cross-type lookup, the model-aware query and exports
  returns the records effective on that date. It is a filter over values, not history: it combines
  with any context (live, change set, publication) and never reads a publication by itself.
- A type without a period answers `422 as_of_not_supported`. In the cross-type lookup, the types with
  a period are filtered and the others are not, and the response names the filtered types in
  `asOfApplied` (as C-D14).
- `dateTime` periods wait for a real case.

## J: Import and export

### J1: Import flow

```text
POST /api/v1/imports                 multipart: file + request (JSON)
POST /api/v1/jobs/{jobId}/confirm    run an import that awaits confirmation
POST /api/v1/jobs/{jobId}/cancel
GET  /api/v1/jobs/{jobId}/items      row outcomes, with sheet and row
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

### J2: File contract

| Format | Rules |
| --- | --- |
| XLSX | One or several sheets; cell values, never formulas (a formula's cached value is read); dates from date cells or ISO 8601 text |
| CSV | UTF-8 (a BOM is accepted), RFC 4180 quoting, a header row, comma by default or a declared delimiter |
| JSON Lines | One batch item (B3, B4) per line; no profile. The export format, so an export re-imports as upserts |

Values convert through the attribute registry by the target attribute's value type, with the same
canonical forms as the API (API.md, attribute format). A value that does not convert rejects its
row with `invalid_attribute_value` and the column. Empty cells are "no value", never an empty string,
unless a value map says otherwise.

### J3: Import profile

The profile fixes the outline of [MODEL_AUTHORING](MODEL_AUTHORING.md#import-profile). It is runtime
data per workspace, not model content, since it names sheets and columns of files:

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
- Consistency: the export reads one database snapshot, and a live export records the feed position of
  that snapshot, so it serves as a re-sync baseline (F5). A publication export is its publication.
- Output is served only by a `completed` job, with a manifest: counts per type, context, feed
  position, model release, format and SHA-256. A failed or cancelled export has no output, so a
  partial file cannot be taken for a complete one. Round trips preserve records, values, parents and
  relations; versions and history are not carried (SC-10 excludes lossless round trips).

### J5: The SC-10 screen

One minimal screen, reached from the workspace: choose a file and a stored profile (or none), start a
preview, read the counts, the binding report and the rejected rows (paged, with sheet and row), then
confirm or cancel and read the result. No profile editing (0.10), no job list beyond the workspace's
recent imports.

### J6: Capability and files

Job creation (imports, exports, background batches) is under `INTEGRATION_JOBS_ENABLED` (D10). Files
live in `JOB_FILE_DIR` with size and checksum on the job (D12) and follow job retention (D14), except
a profile's latest source file kept for the 0.10 editor (0.10 D5).
