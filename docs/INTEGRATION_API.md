# Integration API (Product 0.9)

Status: design in progress, started 2026-09-28. The management-side integration contracts of
[Base 0.9](BASE_0_9_IMPLEMENTATION_PLAN.md). Section P is drafted; the other sections are written
before their track's packages. Open questions are the plan's decisions (D1–D14); this document states
the design each recommendation implies and is amended when a decision is taken.

The [consumer API](CONSUMER_API.md) is a separate, read-only tier with its own contract versions.
[API.md](API.md) remains the reference for delivered endpoints: each package moves its contract there
when it is delivered, and this document keeps the design and its reasons.

| Section | Contents | Track | State |
| --- | --- | --- | --- |
| [P](#p-shared-primitives) | Items and outcomes, failure policies, per-item concurrency, idempotency, jobs, limits | P | Draft |
| B | Bulk object create, update, upsert and delete; upsert keys; bulk relations and mapping | B | To write |
| J | Import (file contract as an import profile per [MODEL_AUTHORING](MODEL_AUTHORING.md#import-profile), preview, execute) and export (scope, context, output) | J | To write |
| F | Raw change feed: entries, position, ordering watermark, retention, recovery | F | To write |
| Q | Cross-type lookup (0.8 P1), workspace edge list (0.8 P3), advanced query, `asOf` reads | Q | To write |

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
