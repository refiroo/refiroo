# Base 0.9 implementation plan

**Status:** Planning started 2026-09-28. The [document set](#design-documents) is accepted
(2026-09-28). [INTEGRATION_API.md](INTEGRATION_API.md) section P (shared primitives) is drafted and
raises D11–D14. No work package is specified yet; each track gets its packages once its design
document section and decisions are accepted.

**Target:** Product 0.9.0, [integration-grade APIs](ROADMAP.md#product-release-09--integration-grade-apis).
Effective dates and consumer API definitions extend the model, so the starter becomes content release
0.9.0 on a new schema language version (D7).

**Depends on:** Product 0.8.0 released (R1 and R1b), and 0.8 Milestone C (structure refactoring, R2), which
adds a `reclassified` audit event (a record's type changes and its ID stays). The change feed, webhooks
and consumer API must represent that event (0.8 D37). Planning and design documents may proceed while
B5 and R1b finish; implementation starts after 0.8.0.

## Product outcome

External systems exchange and synchronize reference data through stable, resumable contracts rather
than UI endpoints or undocumented limits. An integration can load and upsert batches with per-item
outcomes and safe retries, run import and export jobs with a preview, follow an ordered change feed or
receive webhooks, ask model-aware queries (including business-date questions where the model declares
them), and read a model-declared consumer API whose contract is independent of the management API.
One built-in reference page documents every API.

## Principles and exclusions

1. **Same rules as single writes.** A bulk item, an import row and a mapping replacement go through the
   same services, validation, uniqueness and optimistic concurrency as one record written from the UI
   (`services/attributes.apply_attribute_values`). Bulk is a first-class service, not a loop over
   route handlers, but it adds no second validation path.
2. **Live by default, change set on request.** Every write targets live data unless the request names
   a change set (ADR-026). The roadmap's "explicit optional staging mode" is that change-set context,
   not a new staging area.
3. **Generic.** No branch on application, object-type, attribute or relation keys. File columns,
   upsert keys, query fields, effective periods, consumer outputs and events are resolved from the
   model.
4. **Bounded or resumable.** Every collection pages under ADR-030; every job result is paged and every
   batch has a documented maximum. Nothing returns "everything" in one response.
5. **Machine-readable outcomes.** Partial failure, lifecycle stage and every refusal have a stable code;
   no `success` hides a partial result.
6. **At-least-once, never silent loss.** Feeds and webhooks are ordered and resumable; receivers
   deduplicate. An expired position answers with an explicit recovery path.
7. **Additive to the management API.** Existing routes and response shapes do not change.

Excluded: all authentication and authorization, for the management and consumer APIs alike (the 0.11
security release, D10), PostgreSQL deployment and multi-node delivery coordination (0.10; the 0.9 designs
must not depend on SQLite's single writer, D5), a UI for jobs or subscriptions beyond what SC-10 needs
(D3), lossless file round trips (SC-10), and exactly-once delivery.

## Design documents

A build of integration contracts cannot be carried by one plan. The 0.8 plan mixes design and delivery
records in 2,800 lines, and those contracts outlive the build. Here the plan sequences and records
delivery; the contracts live in design documents that the packages reference instead of restating.

| Document | Holds | State |
| --- | --- | --- |
| This plan | Outcome, principles, tracks, packages, sequence, decisions, delivery records, acceptance | Draft; document set accepted 2026-09-28 |
| [CONSUMER_API.md](CONSUMER_API.md) | Read-only consumer tier: `consumerApis` definitions, XREF, lists, read index, batch resolve, crosswalk, `asOf`, publications, API index, consumer events, subscriptions, webhook delivery, packages C1–C16, decisions C-D1–C-D16 | Proposed; C-D1 decided (security in 0.11), others open |
| [INTEGRATION_API.md](INTEGRATION_API.md) | Management-side integration contracts: shared primitives (idempotency keys, item outcomes, failure policies, job lifecycle), bulk writes and upsert keys, bulk relations and mapping, import/export jobs and the file format contract, the raw change feed, advanced query, cross-type lookup (0.8 P1) and the workspace edge list (0.8 P3) | Section P drafted; B, J, F, Q to write |
| [APPLICATION_MODEL.md](APPLICATION_MODEL.md) | Schema language additions: effective-period declaration, `consumerApis`, any upsert key declaration | Section per addition |
| [DECISIONS.md](DECISIONS.md) | ADRs for durable choices: the job and idempotency model; the audit log as the ordered outbox for both feeds; effective dating | One ADR per choice, when accepted |
| [API.md](API.md) | The delivered management API reference. Each package moves its delivered contract here, as 0.7 and 0.8 did; "Planned integration endpoints" then points to `INTEGRATION_API.md` | Updated per package |

One `INTEGRATION_API.md` rather than one document per feature, because bulk writes, import, export and
the feed share the same primitives: a split would define item outcomes, idempotency and job status
several times. The consumer tier stays separate because its contract is versioned independently and
has a different audience.

## Scope inventory

Roadmap 0.9 items, the stories and scenarios they answer, and the track that owns them:

| # | Roadmap item | Stories / scenarios | Track | Design home |
| --- | --- | --- | --- | --- |
| 1 | Advanced model-aware queries | US-I09, SC-10 extension | Q | INTEGRATION_API |
| 2 | Effective dates and `asOf` | US-I06, SC-11 | Q | APPLICATION_MODEL, ADR |
| 3 | Bulk create, update, upsert; optional change set | US-I03, SC-10 | B | INTEGRATION_API |
| 4 | Asynchronous import/export, preview, resumable status | US-I04, US-I07, US-I08, SC-10 | J | INTEGRATION_API |
| 5 | Ordered change feed and webhooks | US-I05, SC-10 | F | INTEGRATION_API (raw feed), CONSUMER_API (events) |
| 6 | Bulk relation and mapping operations | US-I03 | B | INTEGRATION_API |
| 7 | Position paging | — | — | Delivered in 0.8 Track S (ADR-030) |
| 8 | Cross-type lookup, general edge list (0.8 P1, P3) | US-I02 | Q | INTEGRATION_API |
| 9 | Consumer API | CONSUMER_API C8, C13 | C | CONSUMER_API |
| 10 | Built-in API reference (Scalar) | — | D | This plan (one package) |

## Tracks

**Track P — shared primitives** ([INTEGRATION_API P](INTEGRATION_API.md#p-shared-primitives)). A
synchronous batch is a job run inline, so bulk writes, import and export share one mechanism: the job
model (states, progress, paged results, cancellation, resumption after restart), idempotency keys, the
item-outcome vocabulary (`applied`, `rejected`, `unprocessed`, each with a stable code) and failure
policies (D1). B and J use them; the feed (F) is positioned by sequence instead. They are designed
first and delivered with the first bulk package rather than as an unused layer.

**Track Q — queries and lookup.** Cross-type `GET /objects` over built-in fields (P1); publication
context and naming for the existing workspace edge list (P3); advanced model-aware query with explicit
criteria, ordering, `select` and `expand` (D4); effective periods declared in the model and `asOf`
reads (D6, D7).

**Track B — bulk writes.** Bounded batches of object create, update and upsert, and of relation and
mapping operations, live or in a named change set, with per-item outcomes, a documented batch maximum
and idempotent retry. Upsert keys are the public ID or declared unique attributes (D2).

**Track J — import and export jobs.** Import: destination, file format (D3), column-to-field
association, a preview that changes no data, execution under the chosen failure policy and itemized
results. Export: an explicit workspace, context (live, change set or publication), scope and format;
retrievable output that cannot be mistaken for a complete export when partial. Import executes through
Track B.

**Track F — change feed.** The raw management feed: ordered record changes from the audit sequence,
position, retention and `410` recovery (D5, D8). Consumer events and webhooks (CONSUMER_API C9–C13)
derive from the same sequence (C-D11), so positions compare.

**Track C — consumer API.** CONSUMER_API C1–C6 and C8 (read tier), batch resolve (C14), crosswalk (C15)
and `asOf` (C16, after Track Q's effective periods), then events C9–C13 without signing; C7 access
control moved to 0.11 (C-D1). Its open decisions C-D2–C-D16 are settled first.

**Track D — API reference.** Scalar at `/docs`, bundled script by default, CDN by setting, management
and every active consumer contract as separate OpenAPI sources; the route stays outside the OpenAPI
locks.

**R — build acceptance.** SC-10, SC-11, CONSUMER_API C8 and C13, the ROADMAP 0.9 exit gate, volume
budgets on the 0.8 Track S fixture, and the full suites per AGENTS.md.

## Provisional sequence

```text
Design:   INTEGRATION_API P section + D1, D2 → B;  D3 → J;  D5, D8 → F;  D4, D6, D7 → Q;  C-D* → C
Track P:  delivered inside the first B package
Track Q:  P1, P3 (no dependencies) ─ advanced query ─ effective dates (schema)
Track B:  objects bulk → relations/mapping bulk
Track J:  export (needs Q scope) ; import preview → import execute (needs B)
Track F:  raw feed → consumer events C9–C13 (need C2)
Track C:  C1 → C2 → C3 ∥ C4 → C5 → C6 → C7 → C8
Track D:  any time; consumer sources after C6
Release:  Q, B, J, F, C, D → R
```

P1, P3, Track D and C1 have no open design dependency and can start as soon as 0.8.0 is released.

## Composable domains check (ADR-032)

This build touches every door in [COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md#doors-to-keep-open):

- **Identity:** upsert keys and feed events must leave room for a retired-ID redirect; a bulk result or
  feed entry for a merged record must be expressible later without a breaking change.
- **Provenance:** bulk and import are the first writes with an origin other than a user edit. The job or
  batch that caused a change is recorded on its audit entry, so a value-source field stays additive.
- **Derived values:** export and consumer projections read values; neither assumes every value is stored.
- **History and erasure:** feed entries and events carry identity and changed field keys, not value
  blobs (C-D7), so a redaction never has to rewrite the feed.
- **Inbound flow:** Track B is this door; recurring feeds and one-off loads use one contract.
- **Matching and review:** the consumer `match` declaration stays independent of `mappingGrid`
  vocabulary.
- **Value types:** file formats and query operators convert through the attribute registry, never a
  hard-coded list of value types.

## Invariant notes

- **Staging mode.** Read as a separate staging store, roadmap item 3 would conflict with ADR-026. This
  plan reads it as the existing change-set context (principle 2); D1 records it.
- **Effective dates versus history.** Business validity, change history and publication time stay
  separate (SC-11). An `asOf` query never reads a publication, and a publication read never applies
  business dates unless both are requested.
- **Result caps.** Every batch maximum and job limit is documented and returned in errors; none is a
  silent truncation.

## Open decisions

To settle before the named track's packages are written. The recommendation is the planning default.

| # | Question | Recommendation | Blocks |
| --- | --- | --- | --- |
| D1 | Failure policy and staging for bulk writes | Two policies, chosen per request: `atomic` (all or nothing) and `independent` (each item on its own). No "stop at first error". Change-set context by `changeSetId` is the only staging mode | B, J |
| D2 | Upsert key | The public ID, or one attribute declared unique on the object type (ADR-010), named per request. No composite keys in 0.9. An ambiguous or missing key is a per-item `rejected` | B, J |
| D3 | Import/export file formats and UI | CSV (UTF-8, header row) and JSON Lines. Columns map to declared fields by key, overridable per job. No XLSX in 0.9, although TODO lists "CSV/Excel": XLSX is a later additive format. A minimal import-preview screen for SC-10; job administration is API-only | J |
| D4 | Advanced query scope | Criteria over built-in fields, declared attributes and one relation hop, combined with AND; ordering over one declared sort key plus the unique tie-breaker; `select` and `expand` from the model. OR groups and multiple sort keys wait for a second real case | Q |
| D5 | Feed ordering on a multi-writer database | The audit `sequence_id` is not commit order on PostgreSQL. The feed publishes a sequence only once no lower sequence can still commit (visibility watermark), designed now and exercised in 0.10 | F |
| D6 | Effective-date semantics | An object type declares one effective period from two `date` attributes: inclusive start, exclusive end, open end allowed, overlaps allowed and all returned. Dates have no time zone; `asOf` is a date. `dateTime` periods wait for a real case | Q |
| D7 | Schema language version | One new schema language version (0.8) carries both `consumerApis` and effective periods, with the starter at content release 0.9.0 | Q, C |
| D8 | Raw feed retention and recovery | Same retention setting as consumer events (C-D9, 30 days default). Past it, `410 feed_position_expired` and a publication or export as the re-sync baseline | F |
| D9 | 0.9 cut line | The scope is several times 0.8's. Deliver in order Q (P1, P3) → B → F → C → J, with D at any time, and allow a 0.9.x split after C if R is not in reach | All |
| D10 | Credentials and gates before 0.11 | **Credentials decided 2026-09-29:** none in 0.9. No API keys and no credential in a URL; 0.11 brings engine-provided OAuth 2.0 with JWT, HMAC-signed webhooks and UI administration of both (CONSUMER_API C-D1). **Gate, recommended:** job creation and cancellation form a deployment capability group, `INTEGRATION_JOBS_ENABLED` (ADR-031), on by default like live writes, since a bulk write is no more privileged than the single writes it batches; job reads and the raw feed are ungated like other reads until 0.11 | B, J, F, C |
| D11 | Upserts without a version claim | Update items need `expectedVersion`. An upsert that finds a record without one is rejected `version_required` unless the request declares `onExisting: "overwrite"`, which is audited and reports the previous version (INTEGRATION_API P4) | B, J |
| D12 | Where job files live | A configured directory (`JOB_FILE_DIR`) with size and checksum on the job, not database rows. 0.10 multi-node needs shared storage behind the same setting | J |
| D13 | Batch and job limits | Synchronous batch 1,000 items and 5 MB; `atomic` job 10,000 items; background job 1,000,000 items and 200 MB upload; all settings, reported by capabilities, confirmed against the volume fixture in the first B package | B, J |
| D14 | Retention of jobs, outcomes, files and idempotency keys | 7 days, one setting; afterwards the job is `expired` with its summary kept | B, J |

## Next

1. Review INTEGRATION_API section P and settle D1, D10, D11, D13 and D14, which it rests on.
2. Settle D2 and D9, then write section B.
3. Settle CONSUMER_API C-D2–C-D16 (C-D1 decided).
4. Write packages for Track Q's P1 and P3 and Track D, which have no open decisions.
