# Base 0.9 implementation plan

**Status:** Planned; implementation starts after 0.8.0. The [document set](#design-documents) is
accepted (2026-09-28). All [decisions](#decisions) D1–D16 and CONSUMER_API C-D1–C-D16 are accepted
(2026-09-29). [INTEGRATION_API.md](INTEGRATION_API.md) sections P, B, F, Q and J, the schema 0.8
section and ADR-036–038 are drafted (2026-09-29). Work packages Q1–Q4, B1–B3, F1–F2, C1–C16, V1–V2,
J1–J4 and R are specified (2026-09-29) and delivered in the order of the
[delivery queue](#delivery-queue), each by the [delivery steps](#how-a-package-is-delivered).
**Delivered:** [Q1](#q1-cross-type-lookup) (2026-09-29), [Q2](#q2-workspace-edge-list) (2026-09-29),
[Q3](#q3-model-aware-query) (2026-09-30), [C1](#c1-consumer-api-definitions) (2026-09-30),
[Q4](#q4-effective-periods-and-asof) (2026-09-30), [V1](#v1-api-reference-page) (2026-09-30),
[B1](#b1-job-model-and-inline-object-batches) (2026-10-01), [B2](#b2-background-jobs) (2026-10-01),
the interim release 0.9.0-alpha.1 (2026-10-03), [F1](#f1-feed-positions) (2026-10-03, with the feed
read, D31), [B3](#b3-relation-and-relation-set-items) (2026-10-03, D35–D39),
[F2](#f2-feed-retention-and-recovery) (2026-10-03, D40–D41), [T1](#t1-track-checkpoint-q-b-f) (2026-10-03),
[T1a](#t1a-copies-inside-the-database) (2026-10-04), [T1b](#t1b-one-error-code-pattern) (2026-10-04),
[C2](#c2-consumer-object-and-projections) (2026-10-04, C-D21–C-D26), C3–C5 and
[C14](#c14-batch-resolve) (2026-10-05, C-D47–C-D53), [C15](#c15-crosswalk) (2026-10-05, C-D54–C-D58),
[CN1](#cn1-the-consumer-apis-name-in-public-contracts) (2026-10-05, C-D59), [C6a](#c6a-publications) (2026-10-05, C-D60–C-D68), [C6b](#c6b-the-contract-documents) (2026-10-05, C-D69–C-D70), [V2](#v2-consumer-sources) (2026-10-05), [C8](#c8-parity-acceptance) (2026-10-05, C-D72–C-D75), [C16](#c16-asof-in-the-consumer-tier) (2026-10-05, C-D76–C-D80), [C9](#c9-event-definitions) (2026-10-05, C-D81–C-D86), [C10](#c10-event-deriver-event-store-and-pull-feed) (2026-10-06, C-D87–C-D92, C-D95), [U2](SETTINGS_AND_UI_PLAN.md#u2-delivery-record) (2026-10-06, U-D7–U-D9), [C11](#c11-subscriptions) (2026-10-06, C-D96–C-D102), [C12](#c12-the-dispatcher) (2026-10-06, C-D103–C-D111), [C13](#c13-event-acceptance) (2026-10-06, C-D112–C-D114), [U3](SETTINGS_AND_UI_PLAN.md#u3-delivery-record) (2026-10-06, U-D10–U-D11).
**U5, the Webhooks page, is implemented (2026-10-07)** ([record](SETTINGS_AND_UI_PLAN.md#u5-record-2026-10-07)), and so is **U5a**, webhook names and the delivery log with the page revised ([record](SETTINGS_AND_UI_PLAN.md#u5a-record-2026-10-07)). The screenshots of UA (the Atlas redesign, ADR-040), U5, U5a and C17 were approved by the user on 2026-10-07; U4's (the Integration pages, [record](SETTINGS_AND_UI_PLAN.md#u4-record-2026-10-07)) await approval.

**Target:** Product 0.9.0, [integration-grade APIs](ROADMAP.md#product-release-09--integration-grade-apis).
Effective dates and consumer API definitions extend the model, so the starter becomes content release
0.9.0 on a new schema language version (D7).

**Depends on:** Product 0.8.0 released (R1, R1b and R2; 0.8.0 includes Milestone C, D43). Milestone C
adds a `reclassified` audit event (a record's type changes and its ID stays, ADR-034), whose stored
payload holds the record's full before state. The change feed, webhooks and consumer API must represent
that event (0.8 D37). Planning and design documents may proceed while Milestone C and R2 finish;
implementation starts after 0.8.0.

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
   (`engine/records/attributes.apply_attribute_values`). Bulk is a first-class service, not a loop over
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

Excluded: all authentication and authorization, for the management and consumer APIs alike (the 0.12
security release, D10), PostgreSQL deployment and multi-node delivery coordination (0.11; the 0.9 designs
must not depend on SQLite's single writer, D5), a UI for jobs or subscriptions beyond what SC-10 needs
(D3), lossless file round trips (SC-10), and exactly-once delivery.

## Design documents

A build of integration contracts cannot be carried by one plan. The 0.8 plan mixes design and delivery
records in 2,800 lines, and those contracts outlive the build. Here the plan sequences and records
delivery; the contracts live in design documents that the packages reference instead of restating.

| Document | Holds | State |
| --- | --- | --- |
| This plan | Outcome, principles, tracks, packages, sequence, decisions, delivery records, acceptance | Draft; document set accepted 2026-09-28 |
| [CONSUMER_API.md](CONSUMER_API.md) | Read-only consumer tier: `consumerApis` definitions, XREF, lists, read index, batch resolve, crosswalk, `asOf`, publications, API index, consumer events, subscriptions, webhook delivery, packages C1–C16, decisions C-D1–C-D16 | Accepted; C-D1–C-D16 decided 2026-09-29 |
| [INTEGRATION_API.md](INTEGRATION_API.md) | Management-side integration contracts: shared primitives (idempotency keys, item outcomes, failure policies, job lifecycle), bulk writes and upsert keys, bulk relations and mapping, import/export jobs and the file format contract, the raw change feed, advanced query, cross-type lookup (0.8 P1) and the workspace edge list (0.8 P3) | All sections (P, B, F, Q, J) drafted 2026-09-29 |
| [APPLICATION_MODEL.md](APPLICATION_MODEL.md) | Schema language additions: effective-period declaration, `consumerApis` (with `targetable`); no upsert key declaration (D2) | [Schema 0.8 section](APPLICATION_MODEL.md#schema-08-additions-product-09) drafted 2026-09-29; `consumerApis` delivered in C1 |
| [DECISIONS.md](DECISIONS.md) | ADRs for durable choices: the job and idempotency model; the audit log as the ordered outbox for both feeds; effective dating | ADR-036, ADR-037, ADR-038 accepted 2026-09-29 |
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
| 10 | Built-in API reference (Scalar) | — | V | This plan (V1, V2) |

## Tracks overview

**Track P — shared primitives** ([INTEGRATION_API P](INTEGRATION_API.md#p-shared-primitives)). A
synchronous batch is a job run inline, so bulk writes, import and export share one mechanism: the job
model (states, progress, paged results, cancellation, resumption after restart), idempotency keys, the
item-outcome vocabulary (`applied`, `rejected`, `unprocessed`, each with a stable code) and failure
policies (D1). B and J use them; the feed (F) is positioned by its feed position instead.

**Status: §P1–P5 and P7 delivered in B1, §P6's background run in B2 (both 2026-10-01); job files (D12) arrive with J (D27).** The design
(§P) and its decisions (D1, D10–D14, D23–D26, ADR-036) are accepted. Track P has **no package of its
own**: it is delivered inside the first bulk packages, so it is never an unused layer:

| Part of §P | Delivered in |
| --- | --- |
| §P1 job record, §P2 items and outcomes, §P3 failure policies, §P4 per-item concurrency, §P5 idempotency, §P7 limits and capabilities | [B1](#b1-job-model-and-inline-object-batches) |
| §P6 background execution: chunks, lease and resumption, cancellation, model release changes, retention, job files | [B2](#b2-background-jobs) |

Q, V and C1, which come before B1 in the queue, do not use jobs.

**Track Q — queries and lookup.** Cross-type `GET /objects` over built-in fields (0.8's P1); publication
context and naming for the existing workspace edge list (0.8's P3); advanced model-aware query with explicit
criteria, ordering, `select` and `expand` (D4); effective periods declared in the model and `asOf`
reads (D6, D7).

**Track B — bulk writes.** Bounded batches of object create, update and upsert, and of relation and
mapping operations, live or in a named change set, with per-item outcomes, a documented batch maximum
and idempotent retry. Upsert keys are the public ID or declared unique attributes (D2).

**Track J — import and export jobs.** Import: destination, file format and import profile (D3,
[MODEL_AUTHORING A1](MODEL_AUTHORING.md#delivery)), a preview that changes no data, execution under the chosen failure policy and itemized
results. Export: an explicit workspace, context (live, change set or publication), scope and format;
retrievable output that cannot be mistaken for a complete export when partial. Import executes through
Track B.

**Track F — change feed.** The raw management feed: ordered record changes from the audit sequence,
position, retention and `410` recovery (D5, D8). Consumer events and webhooks (CONSUMER_API C9–C13)
derive from the same sequence (C-D11), so positions compare.

**Track C — consumer API.** CONSUMER_API C1–C6 and C8 (read tier), batch resolve (C14), crosswalk (C15)
and `asOf` (C16, after Track Q's effective periods), then events C9–C13, with full-object payloads and signed webhooks (C-D7, C-D12 revised 2026-10-05); C7 access
control moved to 0.12 (C-D1). Its open decisions C-D2–C-D16 are settled first.

**Track V — API reference** (Track D in earlier drafts). Scalar at `/docs`, bundled script by default, CDN by setting, management
and every active consumer contract as separate OpenAPI sources; the route stays outside the OpenAPI
locks.

**R — build acceptance.** SC-10, SC-11, CONSUMER_API C8 and C13, the ROADMAP 0.9 exit gate, volume
budgets on the 0.8 Track S fixture, and the full suites per AGENTS.md.

## How a package is delivered

As in 0.8: each package below is one vertical slice, delivered on the instruction **"deliver
`<package>`"** (for example "deliver Q1"), in the order of the [delivery queue](#delivery-queue).

1. **Read** the package entry, the design sections it cites, the ADRs it names and `AGENTS.md`.
   `§Q3` means section Q3 of [INTEGRATION_API.md](INTEGRATION_API.md); C packages cite
   [CONSUMER_API.md](CONSUMER_API.md).
2. **Stop on a gap.** If the design does not cover a case, or the package would break a product
   invariant, record a new decision (D17 onward) with a recommendation here and ask before coding, as
   0.8 did (D20–D44).
3. **Build** the slice: migration when the package names one, service, route, OpenAPI lock
   re-baseline (checked by diffing the document), frontend only where the scope says so. Nothing
   branches on application, type, attribute or relation keys (principle 3).
4. **Test** with the groups the package lists plus the changed boundary per
   [EXECUTION_GUIDE §2](testing/EXECUTION_GUIDE.md#2-changed-boundary--selected-checks). A new test
   module goes into `TEST_GROUPS` and the guide's table in the same change. No full suite before R.
5. **Record** under the package: **Delivered YYYY-MM-DD.**, what was built, where it differs from
   the design (and amend the design section), and **Checks:** the groups run with their counts, and
   what was not run and why. Move a delivered contract from INTEGRATION_API or CONSUMER_API into
   [API.md](API.md).
6. **Update** CHANGELOG (Unreleased), PROJECT_STATUS and TODO. Commit only when asked.

A package starts when every package it **needs** is delivered. Packages without a dependency between
them may be delivered in either order.

**Names.** Package IDs are Q1–Q4, B1–B3, F1–F2, C1–C16 (CONSUMER_API's), J1–J4, V1–V9, T1 and R. The API
reference track, called D in earlier drafts, is **Track V** so its packages do not read as decisions
D1–D16.

### Test groups and runners added in 0.9

| Group or runner | Introduced by | Covers |
| --- | --- | --- |
| `jobs` marker | B1 | Jobs, outcomes, idempotency, batches, background execution, import profiles, imports and exports |
| `feed` marker | F1 | Feed positions, publish entries, the feed read, retention; consumer events and delivery (C9–C13) |
| `consumer` marker | C1 | Consumer definitions, reads, XREF, batch resolve, crosswalk, publications, parity |
| `test:browser:v1` | V1 | The reference page served offline, with its sources |
| `test:browser:j4` | J4 | The import preview screen and the SC-10 journey |

Existing groups carry on: `queries` (Q1–Q4), `records`, `change_sets`, `mapping`, `model`,
`startup` (every migration), `contract` (every route change) and `volume` (every budget).

## Delivery queue

| # | Package | Needs | Scope in one line |
| --- | --- | --- | --- |
| 0 | — | 0.8.0 released | C5, R1b and R2 pass — **met 2026-09-29**, 0.8.0 released |
| 1 | [Q1](#q1-cross-type-lookup) | — | `GET /objects` across types — **delivered 2026-09-29** |
| 1a | [E1–E3](BACKEND_BOUNDARIES_PLAN.md) | Q1 | Backend tiers, one rule set, one write path; no contract change — **delivered 2026-09-29** |
| 2 | [Q2](#q2-workspace-edge-list) | — | Edge list with publication context, published as `/workspaces/{key}/relations` — **delivered 2026-09-29** |
| 3 | [Q3](#q3-model-aware-query) | Q1 | `POST …/queries/objects`: criteria, one relation hop, `select`, `expand` — **delivered 2026-09-30** |
| 4 | [C1](#c1-consumer-api-definitions) | — | `consumerApis` schema and validation; opens schema 0.8 — **delivered 2026-09-30** |
| 5 | [Q4](#q4-effective-periods-and-asof) | Q3, C1 | `effectivePeriod` in schema 0.8, `asOf` on reads; starter 0.9.0; SC-11 (API) — **delivered 2026-09-30** |
| 6 | [V1](#v1-api-reference-page) | — | Scalar at `/docs` with the management API; a filler, any time before V2 — **delivered 2026-09-30** |
| 7 | [B1](#b1-job-model-and-inline-object-batches) | — | **Track P (§P1–P5, P7)**, `POST /batches` with object items, inline — **delivered 2026-10-01** |
| 8 | [F1](#f1-feed-positions) | B1 | Feed position in commit order, publish entries (D15, D32), lock order, the feed read (D31) — **delivered 2026-10-03** |
| 9 | [B2](#b2-background-jobs) | B1 | **Track P (§P6)**: worker, chunks, lease, resume, cancel, retention — **delivered 2026-10-01**, before F1 |
| 9a | [PG1–PG2](POSTGRESQL_RUNTIME_PLAN.md) with [H1](TEST_HARNESS_PLAN.md) | B2 | PostgreSQL only: runtime, baseline migration, the test harness with seeded databases built once, PostgreSQL forms — **delivered 2026-10-01** |
| 9b | [H2–H3](TEST_HARNESS_PLAN.md) | PG2 | Parallel test runs (H2 **delivered 2026-10-01**); time ceilings, full-size budgets out of everyday runs (H3); no product change — **delivered 2026-10-01** |
| 9c | [PG3–PG5](POSTGRESQL_RUNTIME_PLAN.md) | PG2 | The per-workspace write lock and concurrency tests; PG3b batch writes decided in memory and written in bulk (PG-D12–PG-D17); existing data carried over; budgets on PostgreSQL with the 100,000-item batch measured once; released as 0.9.0-alpha.1 — **delivered 2026-10-03** (PG4 dropped), tagged `v0.9.0-alpha.1` |
| 10 | [B3](#b3-relation-and-relation-set-items) | B1 | Relation items and `replaceRelationSet` — **delivered 2026-10-03** |
| 11 | [F2](#f2-feed-retention-and-recovery) | F1 | Retention, `410` with baselines, the deep read budget (the read moved to F1, D31) — **delivered 2026-10-03** |
| 12 | [T1](#t1-track-checkpoint-q-b-f) | Q4, B2, B3, F2 | Track checkpoint for Q, B and F: their groups, budgets and a composed journey — **delivered 2026-10-03** |
| 12a | [T1a](#t1a-copies-inside-the-database) | T1 | Amendment: change-set bases and publications copied inside PostgreSQL — **delivered 2026-10-04** |
| 12b | [T1b](#t1b-one-error-code-pattern) | T1a | Amendment: error codes in upper case across every API (C-D25) — **delivered 2026-10-04** |
| 13 | [C2](#c2-consumer-object-and-projections) | C1, T1b | Consumer object and projections: get by ID — **delivered 2026-10-04** |
| 14 | [C3](#c3-consumer-lists-and-parameters) | C2 | Lists and parameters (C-D27–C-D33) — **delivered 2026-10-04**, `sortBy` reads brought within budget by [C3a](#c3a-attribute-sorts-read-in-value-order) ([record](#c3-delivery-record)) |
| 14a | [C3a](#c3a-attribute-sorts-read-in-value-order) | C3 | Amendment: attribute sorts read in value order (D46–D48) — **delivered 2026-10-04** ([record](#c3a-delivery-record)) |
| 14b | [C3b](#c3b-several-values-the-standard-way) | C3 | Amendment: several values as OpenAPI serialises them, `%2C` for a comma in a value (C-D32 amended) — **delivered 2026-10-04** ([record](#c3b-delivery-record)) |
| 15 | [C4](#c4-xref-lookup-and-scoring) | C2, C3b | XREF lookup and scoring (C-D34–C-D41) — **delivered 2026-10-05** ([record](#c4-delivery-record)) |
| 16 | [C5](#c5-xref-parameters) | C4 | XREF parameters: every kind on XREF, `scoresFrom` (C-D42–C-D46) — **delivered 2026-10-05** ([record](#c5-delivery-record)) |
| 17 | [C14](#c14-batch-resolve) | C4, C5 | Batch resolve: one scoring path with XREF, exact rules first (C-D47–C-D53) — **delivered 2026-10-05** ([record](#c14-delivery-record)) |
| 17a | [C14a](#c14a-repeated-lookups-resolved-once-the-batch-profiled) | C14 | Amendment: repeated lookups resolved once; the batch profiled — **delivered 2026-10-05** |
| 17b | [C14b](#c14b-the-ancestor-walk-and-the-contains-selects-made-cheap) | C14a | Amendment: the ancestor walk and the contains selects made cheap — **delivered 2026-10-05** |
| 18 | [C15](#c15-crosswalk) | C5, C14 | Crosswalk: `to.{parameter}` on every read, `target`, `TARGET_NOT_FOUND`, `AMBIGUOUS_TARGET` (C-D54–C-D58) — **delivered 2026-10-05** ([record](#c15-delivery-record)) |
| 18a | [CN1](#cn1-the-consumer-apis-name-in-public-contracts) | C15 | Amendment: the consumer API namespace is `consumerApi` in public contracts, not `apiKey` (U-D1) — **delivered 2026-10-05** ([record](#cn1-delivery-record)) |
| 19 | [C6a](#c6a-publications) | C3, C4, F1, CN1 | `publication` reads with `latest`, the publications list with `eventSequence`, ETag, publication indexes and D47's sort (C-D60–C-D68) — **delivered 2026-10-05** ([record](#c6a-delivery-record)) |
| 19a | [C6b](#c6b-the-contract-documents) | C6a | OpenAPI per definition, the API index (C-D69, C-D70) — **delivered 2026-10-05** ([record](#c6b-delivery-record)) |
| 20 | [V2](#v2-consumer-sources) | V1, C6b | Consumer contracts as reference sources — **delivered 2026-10-05** ([record](#v2-delivery-record)) |
| 20a | [U4](SETTINGS_AND_UI_PLAN.md#u4-the-integration-pages) | UA, C6b, V2 | Settings › Integration: Consumer APIs, Jobs and feed, API reference; a starter consumer API (U-D5) — **implemented 2026-10-07**, screenshots awaiting the user's approval ([record](SETTINGS_AND_UI_PLAN.md#u4-record-2026-10-07)) |
| 21 | [C8](#c8-parity-acceptance) | C3–C6, C14, C15 | Parity acceptance; the consumer read line's checkpoint; `objectType` in projections, the parent keyed by output names (C-D72–C-D75) — **delivered 2026-10-05** ([record](#c8-delivery-record)) |
| 22 | [C16](#c16-asof-in-the-consumer-tier) | C2, Q4 | `asOf` in the consumer tier; SC-11 (consumer) (C-D76–C-D80) — **delivered 2026-10-05** ([record](#c16-delivery-record)) |
| 23 | [C9](#c9-event-definitions) | C2 | Event definitions (C-D81–C-D86) — **delivered 2026-10-05** ([record](#c9-delivery-record)) |
| 24 | [C10](#c10-event-deriver-event-store-and-pull-feed) | C9, F2 | Event deriver, event store, pull feed (C-D87–C-D92, C-D95) — **delivered 2026-10-06** ([record](#c10-delivery-record)) |
| 25 | [C11](#c11-subscriptions) | C10 | Subscriptions API, signing key, allowlist, suspension on model change and retirement (C-D96–C-D102) — **delivered 2026-10-06** ([record](#c11-delivery-record)) |
| 26 | [C12](#c12-the-dispatcher) | C11 | Dispatcher: per-change and coalesced delivery, signing, retries, the delivery suspensions (C-D103–C-D111) — **delivered 2026-10-06** ([record](#c12-delivery-record)) |
| 26a | [U5](SETTINGS_AND_UI_PLAN.md#u5-the-webhooks-page) | U4, C12 | Settings › Integration › Webhooks over the subscriptions API (U-D3) — **implemented 2026-10-07**, screenshots approved by the user 2026-10-07 ([record](SETTINGS_AND_UI_PLAN.md#u5-record-2026-10-07)) |
| 26b | [U5a](SETTINGS_AND_UI_PLAN.md#u5a-webhook-names-the-delivery-log-and-the-webhooks-page-revised) | U5, C12 | Webhook names, the delivery log (`/deliveries`, `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`, C-D115–C-D119) and the Webhooks page revised: the dialog rebuilt, Configuration and Deliveries tabs; revised the same day with resending an event by hand (C-D129–C-D131, revision `20261007_02`) and an event's object linked to its record — **implemented 2026-10-07**, screenshots approved by the user 2026-10-07 ([record](SETTINGS_AND_UI_PLAN.md#u5a-record-2026-10-07)) |
| 27 | [C13](#c13-event-acceptance) | C12 | Event acceptance; the events line's checkpoint; the delivery budget (C-D112–C-D114) — **delivered 2026-10-06** ([record](#c13-delivery-record)) |
| 27a | [U2](SETTINGS_AND_UI_PLAN.md#u2-the-foundation-and-the-shell) | U1 | UI foundation: token layers, regions, data-context band, `PageHeader`, `StatusPill` and `Card`, the shell (U-D7–U-D9) — **delivered 2026-10-06** ([record](SETTINGS_AND_UI_PLAN.md#u2-delivery-record)) |
| 27b | [U3](SETTINGS_AND_UI_PLAN.md#u3-the-settings-area) | U2 | Settings area: About, Appearance, Deployment (read-only, U-D2), Workspaces and Model moved; `GET /api/v1/system` (U-D10, U-D11) — **delivered 2026-10-06** ([record](SETTINGS_AND_UI_PLAN.md#u3-delivery-record); [revised the same day](SETTINGS_AND_UI_PLAN.md#u3-revisions-after-delivery-2026-10-06)) |
| 27c | [UA](SETTINGS_AND_UI_PLAN.md#ua-the-atlas-redesign) | U3 | The Atlas redesign of every surface (ADR-040, U-D12, U-D13), each surface approved by the user from screenshots; today's design tagged `ui-before-atlas`. Comes before U4 and U5 by the user's choice (2026-10-06); folds in U6 — **implemented 2026-10-06–07** (UA0–UA7 and their revisions), approved by the user 2026-10-07 ([records](SETTINGS_AND_UI_PLAN.md#ua0-record-2026-10-06)) |
| 27d | [C17](#c17-webhook-delivery-choices-batching-payload-and-cloudevents) | U5a | Webhook delivery choices: one event per request or batched, with the object or notification only, RDM JSON or CloudEvents; `coalesced` retired (C-D120–C-D128) — **implemented 2026-10-07**, screenshots approved by the user 2026-10-07 ([record](#c17-record-2026-10-07)) |
| — | _cut line (D9)_ | | _If R is out of reach, 0.9.0 releases here with R-a and Track J moves to 0.9.1_ |
| 28 | [J1](#j1-export) | Q3, Q4, B2, F1 | Export jobs: JSON Lines, CSV and XLSX, one snapshot, the manifest on the job (D49–D56) — **delivered 2026-10-07** ([record](#j1-record-2026-10-07)) |
| 28a | [J1u](#j1u-export-in-the-ui-and-job-notifications-outline) | J1 | Export in the UI: the dialog, the job page, notifications pushed over a per-job event stream (D57–D63) — **delivered 2026-10-07**, screenshots approved by the user ([record](#j1u-record-2026-10-07)) |
| 29 | [J2](#j2-import-profiles-and-file-reading) | B3 | Import profiles, XLSX/CSV/JSON Lines reading, rows to items |
| 30 | [J3](#j3-import-preview-and-execution) | J2, B2 | Import preview, confirm, execute |
| 31 | [J4](#j4-import-screen-and-sc-10) | J1u, J3, F2 | The SC-10 screen and SC-10 acceptance |
| 31a | [Track K](#track-k--bulk-selection-and-editing-in-collections) | J4, UA | Bulk selection and bulk edits in collections over `POST /batches`; packages K1–K5 planned in detail when the track starts — **added 2026-10-06** |
| V | [V3–V9](#v3v9-the-management-api-documented-plan-2026-10-07) | V2 | The management API documented: the starter extended, content and examples beside the document, the error catalogue; V3 first, then V4–V8 in any order, then V9. **Independent fillers; block no release** (V-D9) — **planned 2026-10-07**, V-D1 open |
| 32 | [R](#r-build-acceptance-and-release) | all except Track V's V3–V9 | Build acceptance and release |

**Order revised 2026-09-30, after Q3.** The queue delivers first what later packages build on, while
little depends on it yet, and keeps self-contained packages as fillers:

- **C1, then Q4**: schema 0.8 opens once and Track Q closes; the starter becomes content release 0.9.0
  once, and every later package that touches the model (C2 onward) builds on a settled schema.
- **B1, then F1 before B2**: F1 takes a per-workspace lock on every live write and fixes the lock
  order (INTEGRATION_API F3). The background worker (B2) is then built on that order from the start
  instead of being retrofitted. F1 needs only B1.
- **V1** is independent of every other package: it is delivered wherever a gap suits, early enough
  that the reference page can be used to review contracts as they land. V2 follows C6b.
- **T1** checks Tracks Q, B and F together after F2, which have no acceptance package of their own;
  C8 and C13 serve the consumer lines. R then confirms the build rather than discovering problems.

**Deviations.** A defect, a revised decision or a new need found during a package is sorted by one
question: does it change something the next package builds on? If so, it is fixed first as a named
amendment package here (as 0.8 did with B5b and R1b), with its own record and checks, before the
queue continues. If not, it goes into TODO against the package it belongs to. A revised decision
keeps its number, with the date and reason (as D3 and D5), and delivered packages it affects get an
amendment, not a silent edit.

After C2, the consumer read line (C3–C8, C14–C16) and the events line (C9–C13) are independent;
the queue lists one order that respects both.

**Track U, approved 2026-10-05** (U-D1–U-D5;
[SETTINGS_AND_UI_PLAN](SETTINGS_AND_UI_PLAN.md#packages-track-u)): settings and the UI foundation.
U1 (the visual direction, no product code) is a filler at any time. Then U-D6 is taken, and U2 and U3
follow C13, before J4 (_revised 2026-10-06 by the user: U2 is delivered alongside C10_). The other rows are in the queue above. U4 needs U3, so if U3 has not landed
when V2 is done, U4 waits for it. Above the cut line (D9).

## Sequence and dependencies

```text
Track P:  inside B1 (§P1–P5, P7) and B2 (§P6); no package of its own
Track Q:  Q1 ─ Q3 ─ Q4            Q2 (alone)          Q4 also needs C1 (schema 0.8)
Track V:  V1 ────────────────── V2 ─ V3 ─ V4…V8 ─ V9     V2 needs C6b; V3–V9 block no release (V-D9)
Track B:  B1 ─┬─ B2
              └─ B3
Track F:  B1 ─ F1 ─ F2                                F1 before B2 (lock order)
Track T:  Q4, B2, B3, F2 ─ T1                         checkpoint for Q, B and F
Track C:  C1 ─ C2 ─┬─ C3 ───────────────┐
                   ├─ C4 ─┬─ C5 ─ C15 ──┤
                   │      └─ C14 ───────┤
                   │   C3, C4, F1 ─ C6 ─┴─ C8
                   ├─ C16                          needs Q4
                   └─ C9 ─ C10 ─ C11 ─ C12 ─ C13   C10 needs F2
          ── cut line (D9) ──
Track J:  J1 ─ J1u                                 J1 needs Q3, Q4, B2, F1
          B3 ─ J2 ─ J3 ─ J4                        J3 needs B2; J4 needs J1u, F2
Track K:  J4, UA ─ K1 ─ K2 ─ K3                    K4 and K5 as decided in K1's planning
Release:  Q2, T1, C8, C13, C16, V2, J4 → R          (R-a without J at the cut line)
```

## Track Q — Queries

#### Q1: Cross-type lookup

**Design:** §Q1 (0.8 P1). **Needs:** 0.8.0.

**Scope:** `GET /api/v1/objects` in live, change-set and publication contexts, under ADR-030 paging:
repeatable `objectTypeKey`, `applicationKey`, `parentObjectId` or `topLevel`, `search` on the name,
built-in filters (`id`, `name`, `objectTypeKey`, `parentObjectId`, `createdAt`, `updatedAt`) and
sorts (`name` default, `id`, `objectType`, `createdAt`, `updatedAt`). Items have the per-type list's
shape. Model-declared filters on this route are refused with `422 invalid_filter` naming the per-type
route. No route on `/objects/{objectTypeKey}` changes.

**Tests:** each filter and sort in each context; types narrowed and not; the same query giving the
same records in live, a change set and a publication (the S2 parity rule); cursor binding; a type-key
branch check over the renamed model.

**Budget:** a name search and a first page over the Track S fixture's 110,000 records of mixed types
within the per-type list's budget in each context.

**Groups:** `queries`, `contract`, `volume`.

**Exit:** the route is in API.md and the OpenAPI lock; budgets recorded.

**Delivered 2026-09-29.** `GET /api/v1/objects` ([API.md](API.md#cross-type-lookup-base-09-q1)),
answered by `engine/reads/object_lookup.py` through the per-type list's builders:
`refine_object_query` for live data and a new `snapshot_reads.snapshot_object_query`, which
`build_snapshot_object_query` now calls with one type, for change sets and publications. So paging,
seek, positions, overlay position reads and context parity are the per-type list's own. Beyond the
design:

- `search` is on the name only, as §Q1 says; searchable attributes stay on the per-type list.
- A refused model-declared filter or sort names the per-type route in its message and in
  `details.route`, and lists the built-in fields (`details.builtInFields`, `builtInSorts`).
- An unknown `objectTypeKey` is `404 unknown_object_type` and an unknown `applicationKey`
  `404 unknown_application`, as on the per-type list; a type outside the named application is
  `422 invalid_object_type_for_application`.
- Cursors bind the sorted, de-duplicated type set, under their own scopes (`object-lookup`,
  `object-lookup-change-set`, `object-lookup-publication`), so neither list accepts the other's cursors.
- **Found on the way:** a live page of deep records (the fixture's cells, five levels down) loaded
  every ancestor as a whole ORM record for its `path`: 163 ORM rows for a 20-row page, over the
  6-per-row budget, on the per-type list as much as on the lookup. Live paths now read the four
  columns a path shows, as change-set and publication paths already did: 84 rows. No response changes.

- **Found on the way:** the fixture no longer has the 110,000 records this package's budget names.
  Since 0.8 A2 it also holds the relation matrix, so the workspace has 258,000 live records of six
  types (the publication 261,000). The budget is held at that size; J1's export budget names the
  same outdated figure.
- **Found on the way:** with no type named, a change set's base arm read every base row through the
  plain owner index, whole rows included, and sorted them: a first page took 123 ms. The lookup now
  narrows by every type the list can hold, which changes no result (activation refuses to remove a
  type in use, and a change set is checked whole against the release it pins) and lets SQLite read
  the `(owner, type, name, id)` page indexes: 9 ms.
- **Found on the way:** a change-set name search took 152 ms. The match on the name, applied outside
  the change set's projection, is pushed into its arms after the anti-join that hides replaced base
  rows, and SQLite evaluates a row's terms in the order written, so the anti-join probed every base
  row. `object_projection` takes `name_search` and writes it first in each arm: 80 ms. The per-type
  list's search also matches attribute values, so it cannot move there; it keeps its 74 ms.

**Budgets** (full-volume Track S fixture, SQLite 3.53.4, 20-row pages, median of 5 warm runs through the app;
`ms · statements · ORM rows` in live, change set and publication):

| Request | Live | Change set | Publication |
| --- | --- | --- | --- |
| lookup: first page, every type | 4.7 ms · 8 · 84 | 8.8 ms · 9 · 4 | 5.0 ms · 8 · 3 |
| lookup: search by name, total | 71.7 ms · 6 · 33 | 80.0 ms · 7 · 4 | 72.7 ms · 5 · 3 |
| lookup: two types, first page | 3.2 ms · 4 · 64 | 5.0 ms · 6 · 4 | 2.8 ms · 4 · 3 |
| objects: search by name, total (per-type, for comparison) | 33.3 ms · 6 · 33 | 73.8 ms · 7 · 4 | 36.4 ms · 5 · 3 |

Before the two fixes the change set took 122.7 ms and 159.9 ms for the first two rows (the full
`volume_baseline.py --scale 1` run). All are within the 100 ms budget. The three `lookup:` scenarios are
in `volume_baseline.py`, so `test_volume_baseline` holds their statement counts and row budgets at 1%
and 4% scale. The first page over every type shows cells five levels down, which is where the path cost
above showed.

**Checks:** `test_cross_type_lookup` (new, `queries` + `change_sets`; 8 tests × the generated and
the renamed model: 16 passed) — every filter, sort, type narrowing and scope in live data, an overlay
change set, a publication change set and a publication, giving the same records in the same order;
items equal to the per-type list's; search on the name only; timestamps live and refused elsewhere;
refusals; cursor binding by context, query and list; positions, `from=end`, backward pages, seek and
totals. Groups `queries`, `records`, `contract` and `volume` together (`-m "queries or records or
contract or volume"`): 337 passed and 2 failed, the two OpenAPI inventories that locked `/objects` to POST;
updated, `test_openapi_contract` 8 passed with the re-baselined lock (one added operation, checked by
diffing the document against 0.8.0). `ruff check app/ tests/` clean. They cover the changed
`snapshot_reads` builder (`test_context_read_parity`, `test_paging_contract`,
`test_change_set_position_reads`), the search predicate (`test_search_index`) and the live path
change's callers (`test_parent_candidates`, `test_relation_matrix`).

Not run: the rest of the `change_sets` group, since the snapshot builder's change is covered by the
tests the execution guide names for it; `startup`, since there is no migration; frontend checks, since
nothing in the frontend changed. The full suites wait for R.

#### Q2: Workspace edge list

**Design:** §Q2 (0.8 P3). **Needs:** 0.8.0.

**Scope:** `publicationId` on `GET /workspaces/{key}/mappings` (exclusive with `changeSetId`, `422
mutually_exclusive_context`), and the same handler published at `GET /workspaces/{key}/relations`. One
response shape; `GET /relations` unchanged.

**Tests:** the three contexts, both routes returning the same pages, cursor binding per route and
context.

**Groups:** `mapping`, `queries`, `contract`.

**Exit:** both routes documented as one edge list in API.md.

**Delivered 2026-09-29.** `GET /api/v1/workspaces/{key}/relations` and `/mappings` are one edge list
([API.md](API.md#workspace-edge-list-mapping-list-base-09-q2)): both routes take one query dependency
(`EdgeListQuery` in `management/routers/mapping.py`) and call `list_mappings`, which now reads a
publication through the same `context_projection` (live, change set or publication) the mapping
coverage, candidate and target reads use. Differences from the design and the scope above:

- The scope named `422 conflicting_context`; every other read, this router's included, answers
  `422 mutually_exclusive_context`, so the edge list does too (§Q2 amended).
- A publication's rows carry `mappingVersion: 0`, as mapping coverage does for an immutable set.
- The route passes its cursor scope (`mapping-list`, `workspace-relations`), and the cursor binds
  `publicationId`, so a cursor is refused on the other route and in another context.
- `/relations` carries the `mapping` and `relations` tags. The `/mappings` operation changes only by the
  added `publicationId` parameter; no schema changed.
- **Found on the way:** `list_mappings` began its snapshot by hand and imported `union_all` inside the
  function; it now calls `begin_snapshot_read` and imports at module level (AGENTS.md).

**Checks:** `test_workspace_edge_list` (new, `mapping` + `queries`; 6 passed) — a publication, live
data changed after it and a later change set each holding different edges; both routes walked page by
page giving identical items and totals in each context; the publication read through a view (fields
from its stored attributes, `mappingVersion` 0); both contexts together and an unknown publication
refused on both routes; cursors refused on the other route and in each other context. Groups
`mapping`, `queries` and `contract` together (`-m "mapping or queries or contract"`): 281 passed, with
the re-baselined OpenAPI lock (checked by diffing the document against HEAD: `/mappings` gains
`publicationId`, `/relations` is added with identical parameters and responses, components unchanged)
and the paging inventory at 25 collections. `ruff check app/ tests/` clean.

Not run: `change_sets` beyond the modules these groups include, since the change-set projection is
unchanged and only moved behind `context_projection`; `startup`, since there is no migration; `volume`,
since no query changed; frontend checks, since nothing in the frontend changed. The full suites wait for R.

#### Q3: Model-aware query

**Design:** §Q3 (D4). **Needs:** Q1.

**Scope:** `POST /api/v1/workspaces/{key}/queries/objects` with `where` (AND of the object list's
criteria, `ancestor:<type>` by ID, one `related` hop with `not`), one `sort`, `select`, `expand`
(≤20 per item, with `count` and a `GET /relations` continuation), `context`, paging by `cursor` or
`position` with the body hash bound. `asOf` is accepted by the grammar and refused as
`as_of_not_supported` until Q4. `422 invalid_query` with a JSON pointer.

**Tests:** every operator by value type through the query and through the list giving the same
records; a hop in both directions, with `not`, into a type without the filtered attribute; `select`
and `expand` shapes; contexts; cursors refused for another body; generated and renamed models.

**Budget:** a one-hop criterion and a page with a 20-row expansion over 100,000 records: recorded
from a first measurement, with a target of the per-type list's filtered page plus one statement per
expansion.

**Groups:** `queries`, `contract`, `volume`.

**Exit:** the query contract is in API.md; budgets recorded.

**Delivered 2026-09-30.** `POST /api/v1/workspaces/{key}/queries/objects`
([API.md](API.md#model-aware-query-base-09-q3)). The body is `models/queries.py` (`ModelQuery`); the
engine checks it against the model and builds it in `engine/reads/model_query.py`, through the
per-type list's builders (`refine_object_query` live, `snapshot_object_query` in a change set or
publication), so a list criterion means the same in both and in every context. The list's filter rules
are now public in `object_query.py` (`filter_value_type`, `filter_operators`, `parse_filter_value`,
`typed_filter_predicates`) and the query applies them, not a copy. `management/projections/model_query.py`
pages the plan and renders items and expansions. Taken ahead of V1 and C1 in the queue, since it needs
only Q1. Decisions D17–D19 were raised before coding and accepted as recommended. Differences from the
design, and where it was silent:

- `ancestor:<type>` and the hop are sets the record's parent or ID must be in (`SetFilter`), applied to
  every part of a change set's union. The ancestor walk collects containers only (the ancestor and the
  records below it that can hold the queried type), and a record matches when its parent is one of them.
  Any ancestor of the type matches, so a nesting type matches at each level; `select` of
  `ancestor:<type>` shows the one nearest the root, as `path` does.
- Live, a positive hop or an ancestor drives the read: the type and workspace terms are written so no
  index serves them (`matrix_cells.unindexed`), or SQLite reads every record of the type to probe the
  set (a 1,500-record hop's total: 126 ms against 10 ms).
- The walk's recursive step is a `CROSS JOIN` (`common/sql.py`). SQLite 3.53, which the app runs,
  plans it with the table outside and the one-row queue inside, reading the whole owner at each step
  (550 ms against 2 ms); the 3.43 CLI plans it well, so a plan checked in the CLI proves nothing here.
- An expansion is one `UNION ALL` statement per `expand` with one arm per item, each ordering and
  limiting its own rows as `GET /relations` does and counting the item's relations. A window over all
  of them first sorted every relation (a 20,000-child group: 111 ms against 30). The cursor is the one
  `GET /relations` issues for the last row shown; that list's scope and cursor filters are now
  `relation_scope` and `relation_filters` in `relation_queries.py`, used by both. In a change set or
  publication the count reads relations only, not their other ends, which a valid context always holds.
- `not` stands beside `related`; `parentObjectId` is a built-in criterion but not a sort; `sequenceId`
  is not a field. `from` and `includeTotal` page as on every list; `seek` is not offered.

**Budget** (volume fixture at full scale, 100,000 items; SQLite 3.53; 20-row pages; median of five;
time · statements · ORM rows), measured on the kept `volume_baseline.py --scale 1 --only-queries`
database after the fixes above:

| Request | Live | Change set | History |
| --- | --- | --- | --- |
| query: one-hop criterion, total | 12.2 ms · 6 · 64 | 52.2 ms · 8 · 5 | 36.9 ms · 7 · 4 |
| query: inverted hop, first page | 5.8 ms · 5 · 64 | 10.7 ms · 7 · 5 | 4.1 ms · 6 · 4 |
| query: ancestor criterion, total | 26.9 ms · 6 · 64 | 48.3 ms · 8 · 5 | 6.0 ms · 7 · 4 |
| query: 20-row expansion of 1,500 citations | 8.6 ms · 8 · 66 | 14.8 ms · 9 · 5 | 7.9 ms · 8 · 4 |
| query: 20-row expansion of 20,000 children | 43.8 ms · 8 · 66 | 91.0 ms · 9 · 5 | 67.6 ms · 8 · 4 |

The first measurement, before the fixes, was 287 · 94 · 73 ms for the hop's total, 1,140 · 1,858 ·
435 ms for the ancestor's and 191 · 400 · 130 ms for the 20,000-child expansion. All are now within
100 ms; an expansion adds one statement and costs about what `GET /relations` costs for the record
(41 · 74 · 64 ms for the heavy group in the 0.8 record), which meets the target.

**Checks:** `test_model_query` (new, `queries` + `change_sets`; 6 tests × the generated and renamed
models, 12 passed): every non-search parity criterion and sort (32) through the list and the query
giving identical items in live data, a change set and a publication; `ancestor:` at two depths, on a
nesting type, with a field criterion and a sort, and its refusals; a hop outgoing and incoming, on a
built-in and on an attribute, inverted, into a third type, combined with `ancestor:`, with a change
set that adds, removes and cascades relations; `select` and `expand` shapes, with the expansion's
cursor continuing on `GET /relations` exactly; cursors refused for another body, context and route;
position, `from=end` and the way back with totals; every refusal at its pointer, and the shape
errors. Groups `queries`, `change_sets`, `records`, `mapping` and `contract` together: 575 passed,
with the re-baselined OpenAPI lock (checked by diffing the document against HEAD: one path and eleven
schemas added, nothing changed) and the paging inventory extended to the body-paged query.
`test_volume_baseline` (with the five `query:` scenarios in every context at both scales) and
`test_boundaries`: 7 passed. `ruff check app/ tests/` clean.

Not run: `startup`, since there is no migration; frontend checks, since nothing in the frontend
changed. The full suites wait for R.

#### Q4: Effective periods and `asOf`

**Design:** §Q4, [APPLICATION_MODEL schema 0.8](APPLICATION_MODEL.md#effective-period-effectiveperiod),
ADR-038 (D6, D7). **Needs:** Q3, C1 (schema 0.8 opened).

**Scope:** `effectivePeriod` in the schema 0.8 validator (two distinct `date` attributes the type
binds; refused at its path in schema ≤0.7); the write rule `422 invalid_effective_period` live, in a
change set and as a publish diagnostic; `asOf` on the per-type list and Q3, refused on Q1 (D21, amended
2026-09-30: Q1 was to filter with `asOfApplied`);
the starter becomes content release 0.9.0 on schema 0.8 with periods declared on the types that bind
`valid-from` and `valid-to`; C1's breaking-change check counts removing a period from an exposed type.
SC-11's text is amended: dates carry no time zone, so its "configured
time zone" case becomes "a date, not a time".

**Tests:** the boundary itself, each side of it, open start and end, overlaps; `asOf` combined with a
change set and a publication; `as_of_not_supported`; a mixed-type lookup; SC-11's API half on the
starter; schema 0.7 releases still activate; a release adding and one removing a period.

**Groups:** `model`, `records`, `change_sets`, `queries`, `contract`, `startup` (starter bootstrap).

**Exit:** SC-11 passes through the management API; the schema 0.8 section is marked delivered for
`effectivePeriod`.

**Delivered 2026-09-30.** Effective periods and `asOf`
([API.md](API.md#effective-periods-and-asof-base-09-q4)). Decisions D20–D22 were raised before coding;
D20 and D22 were accepted as recommended, and D21 after discussion removed `asOf` from the management
lookup (ADR-038 and §Q4 amended). What was built:

- **Model.** `effectivePeriod` on an object type (`EffectivePeriodDefinition` in `models/schema.py`,
  omitted from the canonical document when absent, so earlier hashes hold), checked in
  `validation/object_type_rules.py` at `/objectTypes/<type>/effectivePeriod`: schema 0.8, bound, `date`,
  two different attributes.
- **Write rule** `rules.effective_period`, written once. It runs inside
  `validate_object_attribute_rules`, which every path already calls (live create, update, attribute
  patch and delete, change-set create and attribute delete, change-set validation, type changes,
  restructuring), and explicitly in the change-set update and attribute patch, which defer
  `atLeastOneOf` to validation but must refuse a bad period at the write (the scope names change-set
  writes). It reads the values after the write, normalized or in their stored JSON form.
- **Reads.** `as_of_predicate` in `object_query.py` over the list's typed value columns (no start after
  the date, no end on or before it), applied by `refine_object_query`, which the live list, the
  change-set and publication lists and the model query all build through, so the date means the same
  in every context. `asOf` is bound into cursors only when set (`as_of_filter`), so earlier cursors
  stay valid. The list takes a strict `CalendarDate` (`YYYY-MM-DD` only; Pydantic's `date` also took
  times and Unix timestamps); the query keeps D19's `invalid_query` at `/asOf`. The lookup refuses
  `asOf` in `object_lookup.refuse_as_of` (D21).
- **Releases.** `compatibility.py` counts records a newly declared or moved period would refuse (D20);
  `consumer_contract.py` adds the exposed types with a period to the contract, so removing one is
  `consumer_contract_version_required` at `/consumerApis/<key>/objectTypes/<type>`.
- **Starter** content release 0.9.0 on schema 0.8, with a period on `master-value` (the only type
  binding `valid-from` and `valid-to`). On a copy of the development database it installs beside the
  active 0.8.0 at start, and activates: no stored period is inverted, and 67 of its 68 master values
  are effective on 2026-09-30.

Differences from the design: the lookup (D21); the model query dates the queried records only (D22);
an activation gate the design did not state (D20). SC-11's "configured time zone" became "a date,
not a time" in ACCEPTANCE_SCENARIOS, as the scope said.

**Checks:** `test_effective_periods` (new, `queries` + `records` + `change_sets` + `model`; 21 passed):
the starter's period and every validation refusal at its path on the starter and a renamed copy; a
model without a period keeping its canonical form in 0.7 and 0.8; the consumer contract break and
its release by a higher version; on a generated model and its renamed copy, the boundary, each side,
open start and end, overlaps and later starts at four dates in live data, a change set that moves
two periods, and a publication, through the list and the query in pages of two, with a criterion
and a sort; cursors refused for another date or none; `as_of_not_supported` on a type binding a date
without a period and on the lookup; malformed dates; the write refusal on create, update and
attribute patch, live and in a change set, with open periods accepted; the validation diagnostic
for a period stored another way; a release removing the period (then `asOf` refused), and one adding
it back refused with a count of 1 until the record is fixed; and SC-11 on the starter and its
renamed copy (an old value, its replacement and a transitional overlap, by list and query with
`ancestor:`, live and in a publication). `test_rule_parity` gains the refusal on create, update and
attribute patch, pinned the same in both contexts (4 passed). Groups `model`, `consumer`,
`model_admin`, `records`, `change_sets`, `queries` and `contract` together: 894 selected, 872 passed
and 22 failed on the first run. The failures were tests that turn the starter into an earlier schema
(now meeting its 0.8 period), the starter's version asserts and the OpenAPI lock. `starter_at_schema`
now strips what 0.8 added, the schema upgrade tests take the 0.8 starter as the current candidate and
add 0.7 to the ones derived, and the lock was re-baselined after diffing the document against HEAD:
an optional `asOf` date on `GET /objects/{objectTypeKey}`, an optional, refused `asOf` on
`GET /objects` and `ModelQuery.asOf`'s description, nothing else. Rerun after the fixes:
`test_model` and `test_consumer_api_model` (210 passed), `test_api`'s vertical slice and
`test_model_schema_upgrade` (10 passed), `contract` (47 passed), `startup` (62 passed, for the
starter bootstrap) and `test_boundaries` (2 passed). A smoke start on a copy of the development
database, then activation of 0.9.0 there, as above. `ruff check app/ tests/` clean.

Not run: `volume`, since no statement changes without `asOf` and the dated predicate is two
correlated `NOT EXISTS` on the (record, attribute) value key, the shape of a typed filter; a budget for
dated reads is recorded in TODO against T1. Frontend checks, since nothing in the frontend changed: the browser types
declare no object-type field it reads, and the starter's version appears only in mocked unit fixtures.
The full suites wait for R, where the browser runners start on the 0.9.0 starter.

## Track B — Bulk writes

#### B1: Job model and inline object batches

**Design:** §P, §B1–§B3, §B5–§B7, ADR-036 (D1, D2, D10, D11, D13, D14). **Needs:** 0.8.0.

**Scope:** Track P (§P1–§P5, §P7) lands here, used from the start:
- migration: `jobs`, `job_items` (outcomes in item order) and `idempotency_keys`;
- the job service: states, counts, `result`, model release pin, audit cause on every applied item;
- `POST /api/v1/batches` with `run: inline` only (`background` is `422 run_not_available` until B2),
  both policies, live and change-set context, object items `create`, `update`, `upsert`, `delete`,
  record references and upsert keys;
- `onExisting`, `Idempotency-Key`, `GET /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/items`;
- limits as settings in `GET /capabilities`; `INTEGRATION_JOBS_ENABLED`.

**Tests:** each item op against its single-write route giving the same codes; each P2 outcome and
`result`; `atomic` rollback marking the others `unprocessed`; `independent` with a child after a
rejected parent; each P4 case (`version_required`, overwrite audited with the previous version,
`unchanged` writing nothing); each P5 idempotency row; reference errors; change-set claim; capability
off registers no creating route; generated and renamed models.

**Budget (confirms D13):** an inline independent batch of 1,000 upserts, an atomic batch of 10,000
creates, live and in a change set, on the fixture; per-item cost recorded against the single write.
If a D13 default does not fit its budget, lower it here and record the new value in D13. Since H3
(2026-10-01) `test_batch_volume` carries `budget` and runs only at a release's acceptance; PG3b
replaces its timed check with statement counts at two seeded sizes (PG-D17).

**Groups:** `jobs` (new), `records`, `change_sets`, `startup`, `contract`, `volume`.

**Exit:** a batch contract in API.md; D13 confirmed or amended.

**Delivered 2026-10-01.** The design left four questions, decided before coding as recommended: D23
(atomic is sequential), D24 (`unchanged` before the version claim), D25 (the 10,000-item atomic
budget at engine level) and D26 (an upsert's `initialRelations` only when it creates). The budget
raised two more, also decided as recommended: the change-set lookup fix below, and D13 confirmed
with a SQLite lock wait. What was built:

- **Migration** `20260930_01`: `jobs` (parameters, state, stage, progress, counts, `result`, the
  pinned release, the change set's version after the job, `expiresAt`), `job_items` (one outcome per
  item, in item order) and `idempotency_keys` (route and workspace scope, request fingerprint), and
  `cause_kind` and `cause_id` on `audit_events`. An interrupted run completes on the next start; a
  table of another shape is refused with a recovery instruction.
- **The single writes split** into an `apply_…` core that does not commit and the route's committing
  wrapper: live create, update and delete (`records/objects.py`, `deletion.py`) and their change set
  counterparts (`change_sets/records.py`). Routes behave as before; a batch item calls the core in a
  savepoint of its own, so a rejected item leaves nothing, even after writing a row.
- **`engine/jobs/`**: `store.py` (job record, outcomes, counts and result, idempotency, the job
  reads), `batches.py` (the context, the policies, record references and upsert keys, `unchanged`,
  P4) and `inline.py` (limits, the idempotency key, one transaction). In a change set the job holds
  the version claim (`ChangeSetWrites.hold_claim`) for all items; a job that changed nothing leaves
  the version. Every audit entry an item writes carries the job as its cause (`audit_cause`), shown
  as `cause` in object history; an overwrite stores `overwrite.previousVersion`, which is not a
  changed field.
- **Routes**: `POST /batches` (registered with `INTEGRATION_JOBS_ENABLED`, on by default), `GET
  /jobs`, `/jobs/{id}`, `/jobs/{id}/items` (always registered). `GET /capabilities` gains
  `integrationJobs` with the limits as settings: `BATCH_MAX_ITEMS`, `BATCH_MAX_BYTES`,
  `ATOMIC_JOB_MAX_ITEMS`, `JOB_RETENTION_DAYS`.
- **Matrix states across savepoints**: SQLAlchemy dispatches `before_commit` and `after_rollback` for
  each savepoint, so the stored matrix states were recomputed once per item. A batch now runs its items
  under `matrix_states.deferred`, and the outer savepoint applies the notes once; a rejected item's
  notes are recomputed from the records then, which leaves its rows' states as they were.
- **Change-set lookups** (`snapshot_reads._effective`): the base arm excluded the change set's rows
  with `NOT IN`, for which SQLite lists every row the change set holds on each statement, so each write
  into a change set cost in proportion to the change set's size (a lookup 65 µs at 500 own rows, 361
  µs at 4,000). It is now a correlated `NOT EXISTS` probed by the (change set, record) key: 39 µs at
  4,000; the base arms' access paths are unchanged, and a 20,000-record count and position page read
  in 7.2 ms and 12.4 ms instead of 7.8 ms and 19.5 ms.
- **`SQLITE_LOCK_WAIT_SECONDS`** (60 by default; D13): a SQLite write waits that long for another
  transaction's writer lock instead of failing at the driver's 5 s.

Differences from the design, amended in INTEGRATION_API: the job has `changeSetVersion` and
`parameters` (`run`, `onExisting`); the inline response is the outcome page with its ADR-030 fields
plus `job`, and an outcome carries only its status's fields; `413 batch_too_large` names
`details.setting`; request-level `invalid_batch_context` and `run_not_available`; an inline job is
committed with its items, so a release activated meanwhile refuses the request with nothing saved
(no failed job), and `idempotency_in_progress` arises only for B2's background jobs; an initial
relation's other end is `object` (a reference); a live delete's outcome has no `version`.

Composable domains (ADR-032): bulk APIs are touched and no door is affected; items and keys are
resolved from the model (unique attributes, bindings), and the job cause on audit entries is the
provenance the value-source door builds on.

**Checks:** `test_batches` (new, `jobs` + `records` + `change_sets`; 26 passed on the generated model
and its renamed copy): each item op refused with its single write's code, live and in a change set
(duplicate unique value, unknown attribute, missing parent, taken ID, stale version, dependants
without a preview token); items applying with their single writes' versions and audit entries and the
job as cause; independent items seeing earlier applied ones and a row-writing rejection leaving
nothing; atomic rollback with no audit entries and the change set's version unchanged; upserts with
`version_required`, overwrite, `unchanged` and stale claims; upsert by ID and type mismatch; upsert
initial relations only on create; reference and key refusals at their pointers; request-level
refusals creating no job; the capability off; idempotency replay, reuse, workspace scope, in progress
and expiry; job and outcome paging, filters and shapes; refs; a release activated before commit.
`test_batch_matrix_states` (new, `jobs` + `matrix`; 1 passed): stored matrix states after batches with
items refused after writing a row and an atomic batch rolled back, on the starter's translation
matrix, live and in a change set. `test_jobs_migration` (new, `startup` + `jobs`; 4 passed): upgrade from `20260928_01`
with history intact and batches served across a restart, an interrupted run and a refused table
(also through the application: `/health` 503), the settings and their refusals, and a write waiting
1.5 s for a held writer lock and giving up with a 1 s wait. `test_batch_volume` (new, `volume` +
`jobs`; 5 passed, 116 s) at scale 0.005, per item: single create 16 statements live and 42 in the
change set; 1,000 upserts with half updates 20.5 (3.3 s) and 34.0 (6.8 s); the same re-sent,
all `unchanged`, 9.0 (1.2 s) and 8.0 (2.0 s); 1,000 atomic creates 15.0 (2.3 s) and 26.0 (5.3 s);
10,000 atomic creates 15.0 (29 s) and 26.0 (55 s), 5.5 ms per item in the change set against 5.3 at
1,000. Groups `startup`, `records`, `change_sets`, `mapping`, `matrix`, `queries`, `contract` and
`jobs` without volume: 609 passed and one failure fixed (the A6 index test counted every schema
difference of a database two revisions back; it now counts its own tables'; 4 passed). `volume`
without `jobs`: 62 passed, read budgets held with the new lookup. The OpenAPI lock re-baselined after
diffing the document: four paths and the new schemas added, `AuditEventResponse.cause` and
`CapabilitiesResponse.integrationJobs` added, nothing else changed. `ruff check app/ tests/` clean.
Smoke start on a copy of the development database at `20260928_01`: migrated to `20260930_01`,
`/health` ok, `integrationJobs` reported, an atomic upsert batch applied and replayed by its key.

Not run: `model`, `model_admin`, `workspaces` and `consumer`, which the changed boundaries do not
select; frontend format, lint and build, since nothing under `frontend/` changed. The full suites
wait for R.

#### B2: Background jobs

**Design:** §P6 (chunks, lease, cancellation, model release, retention). **Needs:** B1.

**Scope:** the rest of Track P (§P6). `run: background` with `202`; an in-process worker taking queued jobs; chunks that commit
data, outcomes and the checkpoint together; `leaseOwner`/`leaseExpiresAt` and pick-up after restart;
`POST /jobs/{id}/cancel`; `model_release_changed` between chunks; the retention sweep turning jobs
`expired` (D14); `JOB_FILE_DIR` with size and checksum (D12), used by J.

**Tests:** resume after a crash between chunks and inside one (no item repeated or skipped);
cancellation before, between and after chunks, and of an atomic job; a release activated mid-job; a
lost change-set claim; lease expiry and a second worker; retention; the worker off with the capability.

**Budget:** a 100,000-item background batch on the fixture: throughput and the live write latency
beside it recorded. Since H3 (2026-10-01) `test_background_volume` carries `budget` and runs only
at a release's acceptance; the 100,000-item batch is measured once at PG5 (PG-D17).

**Groups:** `jobs`, `change_sets`, `startup`, `volume`.

**Exit:** background execution in API.md; restart behaviour documented in the operations notes.

**Delivered 2026-10-01**, before F1 by instruction (B2 needs only B1): a chunk takes no lock of its
own before the write path's, so F1's workspace lock lands in the chunks' writes with no change to
the worker. The design left four questions, decided before coding: D27 (a `job_inputs` table, not a
column or a job file), D28 (cancel as a request the worker carries out, designed for PostgreSQL),
D29 (an unexpected chunk failure fails the job) and D30 (defaults). What was built:

- **Migration** `20261001_01`: `job_inputs` (one row per item of a background job, removed when it
  finishes), and on `jobs` `lease_owner`, `lease_expires_at`, `cancel_requested_at` and an index by
  state. An interrupted run completes on the next start; an inputs table of another shape is refused.
- **`engine/jobs/`**: `batches.run_items` applies any index range of items (an inline batch is one
  call, a chunk another) and stops between items when asked; `store.py` records outcomes per chunk,
  stops a job (the unreached items' `unprocessed` outcomes in one `INSERT … SELECT` from their
  inputs) and expires jobs; `background.py` queues a batch with its inputs, requests a cancel and
  opens a chunk's context under the pinned release; `worker.py` claims a job under a lease, runs a
  chunk (data, outcomes and checkpoint in one transaction, the lease checked under a row lock before
  commit), stops it on cancel, release change, refused context or failure, sweeps retention hourly,
  and runs on a thread started by the lifespan when jobs are enabled and the model is healthy. It
  waits for a wake-up (a job queued or cancelled in this process), the expiry of a lease held
  elsewhere, or a minute; a graceful stop releases its leases.
- **Routes**: `POST /batches` with `run: background` answers `202` with the job (its limits
  `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES`); `POST /jobs/{id}/cancel` (`202`, `409
  job_finished`), registered with `INTEGRATION_JOBS_ENABLED`. The job gains `cancelRequestedAt`,
  `leaseOwner` and `leaseExpiresAt`; `integrationJobs.limits` gains the background limits and
  `chunkItems`; `runModes` lists `background`.
- **`db.begin_transaction`**: SQLite's driver begins no transaction before a `SAVEPOINT`, so a chunk
  whose first write is inside its batch savepoint committed at the savepoint's release (found by the
  lease test). A chunk now opens its transaction first, on SQLite as `BEGIN IMMEDIATE` (a read-first
  transaction is refused when another connection writes); a no-op on PostgreSQL, listed in TODO's
  SQLite debt.
- **Live unique-value lookups** (`LiveLookup.unique_value_holder`): the budget's live run slowed as
  it went (2.25 ms per item at the start, 5.17 ms after 30,000 creates). Live `attribute_values` had
  no index by value, so each unique check and key reference read every value of the attribute.
  `ix_attribute_values_key_text` (attribute, text value, record) in `20261001_01` makes it a seek, as
  the change set side's `ix_snapshot_attribute_values_owner_key_text` already did: 1.96 to 2.13 ms
  per item over 30,000. Text values only, like the change set side; other value types' unique checks
  wait for 0.11's model-derived indexes (TODO). Single writes and B1's inline batches gain the same.

Differences from the design, amended in INTEGRATION_API: the lost claim's code is
`change_set_version_conflict`; each chunk that changes something advances the change set's version
by one, and `changeSetVersion` is the version the job holds; a change set job pins the change set's
release; `job_finished` is new; `JOB_FILE_DIR` moves to J (D27); the retention sweep runs only where
the worker runs.

**Found: SQLite blocks writes beside a background job.** The worker takes the writer lock again as
soon as a chunk commits, and a waiting write retries only at its busy handler's interval, so it waits
for the whole job, not one chunk, and fails after `SQLITE_LOCK_WAIT_SECONDS`. Not worked around (the
engine targets PostgreSQL); recorded in the budget, in README's restart notes and in TODO.

Composable domains (ADR-032): bulk APIs are touched and no door is affected; the job cause on audit
entries is unchanged, and inputs are the request's items, resolved from the model as in B1.

**Budget** (`test_background_volume`, scale 0.005, 100,000 creates through the route and the worker
thread, live writes made beside it): live, submission 5.0 s (job and 100,000 inputs), run 231 s
(433 items/s), 15.0 statements per item against 16 for a single create, 2.15–2.44 ms per item by
quarter; in the change set, submission 4.6 s, run 663 s (151 items/s), 26.1 statements per item
against 42, 6.0–7.2 ms by quarter. Writes beside the job: live, 2 served after 51–53 s and 2 refused
after 62 s; in the change set, 4 served (median 15 s, max 45 s) and 9 refused, the SQLite finding
above. Before the value index the live run took 805 s (124 items/s). **Restated on PostgreSQL
(0.9.0-alpha.1 PG5, 2026-10-03):** live, submission 5.9 s, run 52 s (1,918 items/s), 0.50–0.56 ms per
item by quarter; in the change set, submission 5.9 s, run 64 s (1,572 items/s), 0.61–0.69 ms by
quarter. Writes beside the job: live, 78 served (median 0.12 s, max 0.35 s), in the change-set run
115 served (median 0.01 s, max 0.18 s), none refused: a write in the job's workspace waits for one
chunk at most (PG3). The latency bound is that wait; the change set's 64 s misses PG-D17's minute by
4 s ([POSTGRESQL_BUDGETS E7](POSTGRESQL_BUDGETS.md#e7-pg-d17-in-a-change-set-64-s-for-100000-items-target-under-60-s)).

**Checks:** `test_background_jobs` (new, `jobs` + `change_sets`; 42 passed on the generated model
and its renamed copy): queued and applied in chunks with outcomes, counts, inputs removed, the job
as cause; later chunks seeing earlier ones with an item's unset fields kept unset; a change set's
version per chunk; an atomic job as one chunk, rolled back on a rejection; resumption after a crash
between and inside chunks with no item repeated or skipped (outcome indexes, records and audit
entries counted); a second worker waiting for the lease and a worker that lost it committing
nothing; a graceful stop releasing its leases; cancel of a queued job, between chunks, after it
finished (`job_finished`) and of an atomic job inside its chunk; a release activated between chunks
and during one, a change set moved to another release, a lost change set claim, a retired workspace
and an unexpected error with its correlation ID; idempotency while queued, reuse and replay; retention
with the summary kept and the key then new; the capability off (no worker, no cancel route); the
lifespan's worker thread completing a job; typed values. `test_jobs_migration` (`startup` + `jobs`;
7 passed, 3 new): upgrade from `20260930_01` keeping B1's jobs and running background jobs across a
restart, an interrupted B2 run completing and an inputs table of another shape refused (`/health`
503), the new settings and their refusals, and the live unique lookup's query plan using the value
index. `test_batches` (26 passed; the `run_not_available` case became the background limit).
`test_background_volume` (new, `volume` + `jobs`; 2 passed, 15 min). Groups `jobs`,
`change_sets`, `startup`, `records`, `queries` and `contract` without `volume`: 622 passed. `volume`
without the background budget: 67 passed, read budgets held with the new index. The OpenAPI lock
re-baselined after diffing the document: removing B2's additions (the cancel path, the 202 on
`POST /batches` and its description, three job fields, three limits) gives B1's hash exactly. `ruff
check app/ tests/` clean. Smoke start on a copy of the development database at `20260928_01`:
migrated to `20261001_01`, `/health` ok, a 1,200-item background batch completed `partial` with the
duplicate rejected at its index, retried while running (`409 idempotency_in_progress`) and replayed
(`202`); a cancel sent while a 3,000-item job ran waited for the writer lock and found it finished
(`409 job_finished`, the SQLite limit of D28); a process killed with `kill -9` at 4,000 of 20,000
items, restarted with a 5 s lease, resumed and completed with 20,000 records, 20,000 outcomes and no
rejection; a graceful stop left no lease.

Not run: `matrix`, `mapping`, `model`, `model_admin`, `workspaces` and `consumer` beyond the modules
the selected groups include, which the changed boundaries do not select; a cancel request
committing while a chunk runs, which needs PostgreSQL (TODO); frontend format, lint and build, since
nothing under `frontend/` changed. The full suites wait for R.

#### B3: Relation and relation-set items

**Design:** §B4 (ADR-022). **Needs:** B1.

**Scope:** `createRelation`, `ensureRelation`, `updateRelation`, `deleteRelation` and
`replaceRelationSet` in batches, with relation-set claims and P4 for sets; the mapping PUT and
`replaceRelationSet` share one service, extended from one target to a set (the mapping replacement is already one flow over live data and change sets since E3).

**Added 2026-10-02 (H4c, the user's decision; corrected the same day):** the relation-set version on
the anchored relationship read. A claimed write (`expectedRelationSetVersion`, here and on
`POST`/`DELETE /relations`) works for every binding. Its version is readable from a relation matrix row
(`relationSetVersion`) or a mapping coverage row (`mappingVersion`, the same counter), which need a
declared view, and from the workspace edge list (`GET /workspaces/{key}/relations`, `mappingVersion`
per edge), which needs none. The gap: the edge list shows only existing edges and is not anchored to a
record, so a record with no relationship of the binding (never had one, or all removed) has no row to
read its version from, and a client must search or page the workspace's edges to find one record's.
`GET /relations?objectId=…` returns the anchor's set version per binding and direction, including an
empty set, so an integrator can read a record's set and replace it under a claim. Journey J13.5.

**Tests:** each op against its single-write route; a set replaced with kept, added and removed
targets; cardinality, ancestor scope, required and containment refusals; set versions advanced once
per affected set; the `transition` audit entry; the relation matrix state kept current
(`matrix_states.verify`); a record and its required relation in one atomic batch.

**Groups:** `jobs`, `mapping`, `matrix`, `records`, `contract`.

**Exit:** relation items in API.md.

**Delivered 2026-10-03**, in three slices (B3a–B3c) after one plan. The design left five questions:
the user decided D35 (relation items in bulk, not one by one) and D36 (a replacement keeps a
required relationship its record needs); D37–D39 were accepted with the plan. What was built:

- **B3a, relation writes as batches of one.** `records/relation_writes.py` decides a relation
  create, attribute change and delete over a batch lookup, with the claimed set checked against the
  set as the items before it leave it. The lookup gains changed relations (version + 1), relations by
  ID (live too) and set versions (stored plus the chunk's advances, prefetched). Both write units
  write changed relations through the ORM, so the matrix states follow. The single live and
  change-set relation routes are batches of one through these steps (AGENTS: one decide step).
  `GET /relations?objectId=…` gains `relationSets`: every non-containment set the record anchors in
  the listed direction and types, with its version, `0` when untouched, live and in a change set
  (D38; journey J13.5).
- **B3b, relation items.** `createRelation`, `ensureRelation`, `updateRelation` and `deleteRelation`
  in `POST /batches`, the ends by reference, decided in the bulk segments with object items (D35).
  `from` is a Python keyword: the field is `from_` with the JSON alias `from`, accepted and written
  only under the alias, so background inputs round-trip (unit test).
- **B3c, set replacement.** `records/relation_sets.py` decides a set replacement. The removals come
  first, then each added target through `rules.relation` over what came before, so cardinality at
  both ends and ancestor scope keep their codes. An equal set is `unchanged` before the claim (D37).
  The anchor's set advances once and each other record's set whose set changed once. One `transition`
  entry with `newTargets` takes no feed position (`AuditEntry.feed`). The mapping PUT is now its adapter
  with one target or none: endpoint refusals, the clear rule, the change set claim and the conflict
  preview stay its own; its version is checked before an unchanged save, as before. D36 refuses
  removing a required relationship whose record has no other.

Differences from the design, amended in INTEGRATION_API §B4–B6:

- `ensureRelation` takes an optional `expectedVersion`.
- A relation item's outcome has `relationSetVersion` when it claimed a set.
- A set replacement's outcome has `relationIds: {created, kept, removed}`.
- A target listed twice is `duplicate_relation`; a wrong-typed anchor or target is
  `reference_type_mismatch` (D39).

Found and changed:

- **Duplicates.** Relating the same two records twice with one type answered `500` live, the unique
  constraint reached unhandled (reproduced on the previous code). In a change set the duplicate was
  staged, by reading the code: only `(change_set_id, relation_id)` is unique there. Both are now
  `409 duplicate_relation` (journey J13.3).
- **Update order.** A relationship update checked its values before its version live, and its
  version first in a change set. Both now check the version first; `test_relations` pinned the
  change-set order.
- **Change-set delete audit.** A change-set relationship delete wrote no audit entry; it now
  writes one, as the mapping save's removals did.
- **Replaced test.** `test_mapping_replacement`'s case that patched the private `_get_set_version`
  to fake a stale read before the conditional claim was removed: the claim is now compared in memory
  under the workspace lock. The J10.4 and J10.5 journeys and `test_pg3_concurrency` hold the
  behaviour.
- **Tier rule.** The set step first sat in `engine/operations/`, which `test_boundaries` forbids
  `engine/jobs/` to import; it lives in `engine/records/`.

Composable domains (ADR-032): bulk APIs and relation-set versions are touched; no door is affected.
Items resolve from the model (bindings, unique attributes), and the job cause on every relation
entry is the provenance the value-source door builds on.

**Checks:**

- **Journey cases** (each on two configurations, each confirmed failing first):
  - J13.5, the anchored read with an empty set, live and in a change set;
  - J13.3, a duplicate relationship refused live and in a change set (failing on the previous code
    with the unhandled unique violation);
  - J11.7, relation items with their single codes and an overwrite, and in a change set to
    publication;
  - J10.10, a set replaced by kept, added and removed targets with each set's version, unchanged,
    stale, missing version and overwrite, and eight refusals;
  - J10.9, the mapping PUT refusing a required relationship's last removal and applying once the
    record has another (D36);
  - J11.8, a record, its required relationship and its set in one atomic batch, and its rollback.
- **Unit tests:** stored matrix states after relation items, a set replacement and an atomic
  rollback, live and in a change set (`matrix_states.verify`); relation items round-tripping a
  background job's stored form, with `from_` refused.
- **`test_batch_statements`** gains relationship items. Half are creates and half replace a set of
  two, all named by key: 33 and 40 statements live for 100 and 500 items, 36 and 43 in the change
  set, at both seeded sizes. That is constant; before the set versions were prefetched it was 82 to
  289. Budget 44 and 47, allowance 8 for `IN` lists past 500 values.
- **Groups:** `records`, `mapping`, `matrix`, `feed`, `contract` parallel, 600 passed (1 min 47 s);
  `change_sets` and `jobs` without those, 323 passed (1 min 4 s); their serial part, 3 passed. Split
  in two so each run stays under the 2-minute ceiling. `test_api_journeys` and the layout check, 10
  passed. Over 10 s: existing modules only, plus `test_batch_statements`' module fixture (14.6 s on
  its first test, now measuring three kinds).
- **OpenAPI lock** re-baselined after diffing the document against the previous commit: 8 schemas
  added, `BatchRequest.items`, `JobItemResponse` and `RelationPage` extended, and the
  `POST /batches` description; no path added or removed. `ruff check app/ tests/` clean.

Not run: `startup` (no migration, no lifespan change), `queries`, `model`, `model_admin`,
`workspaces`, `consumer` and `volume`, which the changed boundaries do not select. Frontend format,
lint and build were not run either: nothing under `frontend/` changed, and the mapping save's
response is unchanged. The full suites wait for T1/R.

## Track F — Change feed

#### F1: Feed positions

**Design:** §F1–§F3, ADR-037 (D5, D15, D16). **Needs:** B1 (the job cause).

**Scope** (after [PG3](POSTGRESQL_RUNTIME_PLAN.md#pg3-concurrency), which takes the workspace row
lock in `LiveWrites` already; F1 adds the counter under it): migration adding
`audit_events.workspace_key`, `audit_events.feed_position` (unique per
workspace) and `workspaces.feed_position`; `record_audit_event` assigns positions for live changes
under the workspace row lock; **every live write path takes that lock first**: in `LiveWrites._begin`, the seam
every live write opens (E3, [BACKEND_BOUNDARIES_PLAN](BACKEND_BOUNDARIES_PLAN.md)), which
`test_boundaries` keeps the only writer of live rows; publish writes one entry per record it applies, with the publish as
cause, then `published`; the `reclassified` entry's feed form; `publications.feed_position`.

**Tests:** positions gapless and in commit order under concurrent writers (two connections, on
PostgreSQL); a rolled-back write leaves no gap; change-set edits take none; a publish's entries equal the
records it changed; a batch's entries carry the job; lock order (no deadlock between a publish and a
live write of a record it touches).

**Budget:** the added statement per write against the 0.8 write budgets; a publish of 10,000 records.

**Groups:** `feed` (new), `records`, `change_sets`, `mapping`, `matrix`, `startup`, `volume`.

**Exit:** C-D15 holds by test: a publication equals live data at its `feedPosition`.

**Amended 2026-10-03 (the user's decisions D31, D32):** the feed read of §F4 (`GET
/workspaces/{key}/feed` with `after`, `pageSize`, `kind`, `objectTypeKey`, the bounded filtered scan)
moves here from F2, so the journey tests read positions through the API; a publish writes relation
entries too. D33 (`after` past the head) and D34 (what the filters match) were accepted with the plan.

**Delivered 2026-10-03.** Journey J26 (steps 1–2) and its variants J26.1–J26.5 were written first
and confirmed failing (the route did not exist). What was built:

- **Migration** `20261003_02`:
  - `workspaces.feed_position`, the counter (0).
  - On `audit_events`: `workspace_key`, `feed_position` (unique per workspace, the read's index),
    `model_release_id` (FK, `RESTRICT`) and `feed_subject`. `feed_subject` is the identity an entry
    names: object type and application, plus the previous type for `reclassified`; relation type and
    ends. Today's audit payloads lack the type of an update, and a later delete leaves nothing to
    look it up by.
  - `publications.feed_position`.
  - No backfill.
- **`engine/records/feed.py`:** `take_positions` runs one `UPDATE … RETURNING` on the workspace row,
  under the lock `LiveWrites._begin` already holds. It returns the first position and the active
  release, leaves `updated_at` as it is, and costs one statement per audit flush, not per entry.
- **The write unit records feed entries.** `LiveWrites.record` and `record_all` give a live
  write's audit entries consecutive positions, while `ChangeSetWrites` records the same calls
  without any, so a change-set edit cannot take one.
  - The live audit sites moved to the unit: value set and delete, the decided writes of `bulk.py`
    (single writes and batches), relation create, update and delete, the deletion cascade (now one
    multi-row insert, relations before records) and the live side of the mapping save. Decided
    entries carry their `subject`.
  - The `published` and `withdrawn` events take positions under the publish's and the withdrawal's
    own row locks.
- **Publish** (`change_sets/publish.py`):
  - The merge already loads live records, values and relations. It keeps them, and
    `publish_entries` compares each authored row with live:
    - `created`, `updated` or `reclassified`, naming the changed fields (`objectType`, `name`,
      `parentObjectId`, `attributes`) and attribute types;
    - an `updated` entry with no field when only the version differs;
    - none for an equal row;
    - then relations removed, relations created or updated, and records removed (D32).
  - The entries are written with the publication as cause. `published` is recorded after them, and
    its position is `publications.feed_position`.
- **Read:** `engine/reads/feed.py` reads the head from the counter, then the entries up to it. An
  unfiltered page is the next `pageSize` positions. A filtered one scans at most ten pages' worth
  and answers `nextAfter` at the scan's end when it is not full.
  - The presenter shares one field derivation with record history. Explicit `changedFields` lists
    are used whenever an entry stores them: a type change and, now, a publish entry.
  - `AuditCause.kind` gains `publication`, since a publish's entries carry record subjects and show
    in record history.

Differences from the design, amended in INTEGRATION_API §F:
- **Containment relations** are no feed entry of their own, live or published. A live create or
  move never audited its containment relation (the record's `parentObjectId` names it); the live
  cascade did. That cascade audit stays and takes no position, and the publish leaves them out too,
  judged under the child's type before or after (a reclassified child's containment relation
  changes type).
- **`cause` of a single write** is `{kind: "user"}` in the feed and omitted in history, as before.
  `restructuring` is never a feed cause, since a restructuring reaches live data through its publish.
- **The publish's `published` entry** has the publishing user, not the publication, as cause.

Composable domains (ADR-032): audit/history and bulk APIs are touched and no door is affected. Feed
entries carry names, never values (D16, the erasure door), and `cause` stays additive (provenance).

**Budget** (measured once with a scratch script on an empty database, deleted afterwards):
- A single create: 18 statements, one of them the feed counter (+1 against the PG3b write).
- A publish: two counter statements (its entries, then `published`), and its entries in multi-row
  inserts (11 for 10,000 entries).
- A publish of 10,000 renamed records: 43.6 s and 40,239 statements. The ~4 statements per record are
  the existing `apply_publication`, which reads each authored record and rewrites its values one
  record at a time. The share the feed adds was not measured separately. Recorded in TODO as a
  publish cost to address with F2's or T1's budgets.
- `test_volume_baseline` (live write statements equal at 1× and 4×) and `test_batch_statements`
  (per-item budgets) hold unchanged.

**Checks:**
- **J26 journey tests** (`tests/journeys/test_j26_follow_changes.py`, new): 12 passed, six cases
  on two configurations each.
- **`test_pg3_concurrency`:** two new cases pass. One is a write held after taking its position and
  before commit, with the next write waiting and getting the next position. The other is a publish
  and a live rename of a record it changes: no deadlock, the rename refused `version_conflict`, and
  the feed listing the publish's entry, then `published`.
- **Unit tests** of `publish_entries` (`tests/unit/engine/change_sets/test_publish.py`, new): 3
  passed.
- **`test_startup`:** `HEAD` is `20261003_02`, and two new cases pass. One is an upgrade from
  `20261003_01` with audit history (inserted as an older release left it; the history keeps no
  position, the feed is empty, and the next write takes position 1, across two starts). The other is
  an interrupted revision rolled back and recovered on the next start. With `test_schema_drift`: 16
  passed.
- **`test_foreign_keys`:** 2 passed with the new rule.
- **`test_openapi_contract`:** 8 passed. The lock was re-baselined after diffing the document:
  without the feed path, `FeedPage`, `FeedEntry`, `FeedCause` and `AuditCause`'s `publication`, it
  hashes to the previous lock exactly.
- **`test_api_journeys`:** 5 passed, with the route, its parameters and `feed_position_ahead`
  mapped.
- **Groups** `feed`, `records`, `change_sets`, `mapping`, `matrix`, `startup`, `jobs` and `contract`
  without `volume`: 908 passed and 2 failed (`test_foreign_keys`, then fixed and rerun), in 2 min
  26 s against the 2-minute package ceiling. That is over: this package's boundary, a shared write
  path, selects most groups. Their serial part: 2 passed. `volume` without `budget`: 67 passed.
- **`ruff check app/ tests/`:** clean.
- **Smoke start** on a copy of the development database at `20261001_02`: migrated to
  `20261003_02`, `/health` ok, and an empty feed. A create took position 1, and a publish of its
  rename gave an `updated` entry with the publication as cause, then `published` at 3. The copy
  was dropped.

Not run:
- `model`, `model_admin`, `queries`, `workspaces` and `consumer` beyond the modules the selected
  groups include, which the changed boundaries do not select;
- the `budget` modules (a release's acceptance);
- frontend checks, since nothing under `frontend/` changed.

The full suites wait for R.

#### F2: Feed retention and recovery

**Design:** §F5 (D8). **Needs:** F1.

**Scope:** `FEED_RETENTION_DAYS`; `earliestPosition` from the retention floor; `410
feed_position_expired` naming the active publication and its position. The feed read itself was
delivered by F1 (D31).

**Tests:** `410` at and past the floor; re-sync from a publication then the feed missing nothing
(SC-10's feed half). Follow, resume and sparse filters are F1's J26 tests.

**Budget:** a 500-entry page at head and deep in a 1,000,000-entry feed.

**Groups:** `feed`, `contract`, `volume`.

**Exit:** retention and recovery in API.md; SC-10's feed half passes at API level.

**Delivered 2026-10-03.** D40 and D41 were decided with the plan. Journey J26 step 3 and variant
J26.6 were added to the catalogue, and five cases were written first. Four were confirmed failing;
the no-publication case passed already, since nothing expired before F2, and stays as D40's guard.
What was built:

- **Setting** `FEED_RETENTION_DAYS` (default 30, a positive integer), reported by `GET /capabilities`
  as `changeFeed.retentionDays`.
- **Floor** (`engine/reads/feed.py`):
  - The read loads the head and the active publication in one statement.
  - With a publication that has a position, one probe finds the first entry within the period, and
    `earliestPosition` is the lower of that and the publication's position + 1 (D40). Otherwise it
    is 1.
  - `after` below `earliestPosition − 1` is `410 feed_position_expired`, with `earliestPosition`,
    `headPosition` and `publication` (`id`, `publicationNumber`, `feedPosition`). The export is J1's
    (D41).
- **Publications** carry `feedPosition`, so a reader holding one knows where to follow on.
- **Migration** `20261003_03`: the partial index `ix_audit_events_feed_time` (`workspace_key`,
  `occurred_at`, `feed_position`, feed entries only), so the floor is one index probe, however long
  the feed and however busy other workspaces are.
- **Volume fixture:** a feed of 1,000,000 × scale entries, all older than any retention period, with
  publication 1 at its middle. There are three feed scenarios in `volume_baseline.py`: a 500-entry
  page at the head, one at the earliest position, and one filtered to the 1 % of group entries.
  T1 measures them at full volume.

Differences from the design, amended in INTEGRATION_API §F5:
- The floor never passes the baseline, and no baseline means nothing expires (D40).
- The export baseline waits for J1 (D41).

Composable domains (ADR-032): audit/history is touched. No door is affected: entries still carry
names, never values, and the audit log is not pruned.

**Budget** (measured once with a scratch script, deleted afterwards). The script used the volume
fixture with a tiny record set and the full 1,000,000-entry feed, seeded in 23 s, with the median of
5 runs per read:
- At the head: 25.8 ms, 4 statements, 500 rows.
- At the earliest position, the feed's middle: 35.2 ms, 4 statements, 500 rows.
- Filtered there: 25.0 ms, 4 statements, 50 rows.
- `after=0`: `410`, naming publication 1 at 500,000.

At 1 % and 4 % scale the three reads cost the same statements (`test_volume_baseline`).

**Checks:**
- **J26 journey tests:** 22 passed, J26.6's five cases on two configurations each. Two slips in the
  test code were corrected before the cases passed. One read `earliestPosition` with `after=0`,
  which the case itself expects to be refused. The other compared whole entries after the aging
  had moved their `occurredAt`; it now compares event IDs. No case's given/when/then changed.
- **`test_startup`:** `HEAD` is `20261003_03`, and two new cases pass:
  - an upgrade from `20261003_02` with a feed entry 400 days old: answered, with nothing expired,
    across two starts;
  - an interrupted revision rolled back and recovered on the next start.
- **`test_openapi_contract`:** the lock was re-baselined after diffing the document. Without
  `changeFeed`, `ChangeFeedCapabilities`, `feedPosition` and the feed route's new sentence, it hashes
  to the previous lock exactly.
- **J20:** its exact list of capability groups gained `changeFeed`. The package's change made the
  old list wrong.
- **`tests/unit/test_config.py`:** 10 passed, with `FEED_RETENTION_DAYS` among the settings.
- **Groups** `feed`, `contract`, `startup` and `volume` without `budget`: 219 passed in 49 s. Their
  serial part: 1 passed.
  - A first run failed with "database does not exist": another pytest run on this machine started
    meanwhile, and its session start drops every test database. The rerun after it ended passed.
  - Over 10 s: four existing tests at 11–13 s in one of two runs (none in the other):
    `test_batch_statements` live creates, a position-read case, `test_matrix_states` publishing and
    `test_volume_baseline`.
- **`ruff check app/ tests/`:** clean.
- **Smoke start** on a copy of the development database at `20261001_02`: migrated to `20261003_03`
  with the index, `/health` ok, `changeFeed.retentionDays` 30, and the feeds empty with
  `earliestPosition` 1. The copy was dropped.

Not run:
- the `budget` modules (a release's acceptance);
- the groups the changed boundary does not select;
- frontend checks, since nothing under `frontend/` changed.

The full suites wait for R.

**Delivered 2026-10-03** with the user's decisions D40 (the floor never passes the active
publication's position; without one nothing expires) and D41 (the export baseline is J1's). Journey
J26 step 3 and variant J26.6 were written first: four of their five cases failed, and the fifth,
nothing expiring without a publication, held already and guards D40. What was built:

- **Setting** `FEED_RETENTION_DAYS` (default 30), reported by `GET /capabilities` as
  `changeFeed.retentionDays`. The group names no `setting`, since it gates nothing.
- **Read** (`engine/reads/feed.py`):
  - The workspace's head and its active publication are read in one statement.
  - With a publication, `earliestPosition` is the lower of its `feedPosition + 1` and the time
    floor: the first entry within the period, or the head + 1. One probe of the new partial index
    finds it, since positions and times rise together under the workspace lock.
  - `after` below `earliestPosition − 1` is `410 feed_position_expired`, with `earliestPosition`,
    `headPosition` and `publication` (`id`, `publicationNumber`, `feedPosition`).
- **Publications** carry `feedPosition`, `null` before F1.
- **Migration** `20261003_03`: `ix_audit_events_feed_time` on `audit_events (workspace_key,
  occurred_at, feed_position)` where `feed_position` is set.
- **Volume fixture:** the feed scaled from 1,000,000 entries, every one older than any retention
  period, with publication 1 at the middle position. Three new read scenarios: a 500-entry page at
  the head, one at the earliest position, and one filtered there.

Differences from the design, amended in INTEGRATION_API §F5: the floor clamp (D40) and the
publication as the only baseline until J1 (D41).

Composable domains (ADR-032): audit/history is touched and no door is affected. The audit log is
not pruned, and entries still carry names, never values.

**Budget**, measured once with a scratch script (a small record set and a 1,000,000-entry feed,
deleted afterwards), median of five:
- A page at the head: 25.8 ms.
- A page at the earliest position, the feed's middle: 35.2 ms.
- That page filtered to one entry in a hundred: 25.0 ms.

Each costs 4 statements. `after=0` answers the `410` naming the publication at 500,000. The
statements hold equal at 1× and 4× in `test_volume_baseline`.

**Checks:**
- **J26 journey tests:** 22 passed, the five new cases on two configurations each.
  - Two slips in the test code were fixed after the first run: reading `earliestPosition` with
    `after=0`, which the case itself expects refused, and comparing whole entries after the aging
    moved their `occurredAt`. They now compare event IDs. No case's given/when/then changed.
- **Groups** `feed`, `contract`, `volume` and `startup` without `budget`: 217 passed and 2 failed,
  in 1 min 22 s.
  - The 2 failures were `test_j20_discover`, which asserted exactly three capability groups, each
  with a `setting`. This package's `changeFeed` group made that wrong, so it now names the gated
  groups and the retention. Its module: 6 passed.
  - One rerun failed once at startup with "database does not exist", from the harness's shared
    server, and passed twice after. Unexplained, and noted here.
  - The groups' serial part: 1 passed.
- **Adjacent modules** for the publication and capability shapes: `test_workspaces`, the
  `test_wp8_*` publish, history and withdrawal modules, `test_model_lifecycle`, journeys J05–J08,
  J12, J19 and J21, and `unit/test_config`: 188 passed.
- **`test_startup`:** `HEAD` is `20261003_03`, and two new cases pass. One upgrades from
  `20261003_02` with a 400-day-old feed entry, which is still answered across two starts. The other
  is an interrupted revision rolled back and recovered on the next start.
- **`test_openapi_contract`:** re-baselined after diffing the document. Without `changeFeed`,
  `feedPosition` and the route's description, it hashes to the previous lock exactly.
- **`ruff check app/ tests/`:** clean.
- **Smoke start** on a copy of the development database at `20261001_02`: migrated to
  `20261003_03` with the index, `/health` ok, capabilities report 30 days, and empty feeds with
  `earliestPosition` 1. The copy was dropped.

Not run:
- the `budget` modules (a release's acceptance);
- groups the changed boundaries do not select;
- frontend checks, since nothing under `frontend/` changed.

The full suites wait for R.

## Track T — Checkpoints

#### T1: Track checkpoint (Q, B, F)

**Needs:** Q4, B2, B3, F2. Added 2026-09-30 with the revised queue.

**Scope:** Tracks Q, B and F checked together, since each package was checked only at its own
boundary and none of the three tracks has an acceptance package. Not a build acceptance: no full
suite and no browser runners.
- The groups the three tracks own, run together once: `queries`, `jobs`, `feed`, `change_sets`,
  `records`, `mapping`, `contract`, `startup` (every migration since 0.8.0 on one upgrade path) and
  `volume`.
- Every Q, B and F budget at full volume in one `volume_baseline.py --scale 1` run, recorded against
  each package's own figure.
- One composed API journey across them: a batch job writes records and relations in the background
  while a reader follows the feed; the model-aware query, with `asOf`, and the edge list read the
  same state in live data, a change set and a publication; a resumed and a cancelled job leave the
  feed and the reads consistent.

**Exit:** all pass, or each failure is fixed as an amendment package or recorded against the package
it belongs to, before C2.

**Delivered 2026-10-03.** What was built and found:

- **Composed journey** (`tests/journeys/test_j24_j26_composed.py`, J24, J26, J23.3, J22.2). It has
  three cases, each on generated A and B, written from this section and approved with the plan:
  - A background job of dated records and relationships, resumed by a second worker, followed by a
    reader through the feed.
  - A job into a change set, then published.
  - An independent job cancelled between chunks and an atomic job cancelled mid-run.

  The feed, the dated model query and the edge list agree in every case. All six passed on the
  first run, since T1 changes no behaviour, so they could not be confirmed failing first.
- **Volume fixture.** It moves to schema 0.8; items declare an effective period (`vol-valid-from`,
  `vol-valid-until`). Three quarters of the items apply on 2026-06-30. The period values take their
  row IDs from a random stream of their own, so every other ID stays as before. There are five
  dated scenarios, `--only-dated` and `--only-publish` (`publish_scenario`).
- **Defect: more than 65,535 parameters.** Creating a change set from current live data and
  publishing listed every record's ID as statement parameters, so both answered `500` in a
  workspace over about 65,000 records (found at 258,000). They now select by workspace. The publish
  checks each relationship end with a primary-key probe: an `OR` of two `IN` subqueries cannot be
  hashed, and on the full fixture it ran for 30 minutes before it was cancelled.
  - Regression test `test_capturing_and_publishing_a_whole_workspace_bind_no_parameter_per_record`:
    the largest parameter list at 0.5 % and 2 % must be equal. Without the fix it fails (3,892 →
    11,604); with it, it passes in 10 s.
- **Defect: quadratic flush.** The typed value index's flush hook (`engine/indexes/snapshot_values.py`)
  read `session.new` once per row, and SQLAlchemy builds that set anew on every read. A flush of n
  rows cost n². At 4 % volume, creating a change set from current live took 28.1 s and now takes
  4.6 s; publishing took 29.9 s and now takes 6.0 s.
- **Defect: applying a publish flushed per record.** `LiveWrites.apply_publication` queried each
  changed record and relationship on its own, and each query first flushed a session holding the
  whole workspace. Its attribute deletes also evaluated every loaded object. It now takes records
  from what is already loaded, loads relationships in bounded chunks, adds new records without a
  flush each, flushes explicitly, and deletes without session synchronisation. For 1,000 changes in
  26,000 records, it went from 24.3 s to about 2 s (profiled).
- **Stopgap: copies in bulk from Python.** The publication's rows and a change set's base are
  written in multi-row statements with their typed index rows (`snapshot_values.insert_object_rows`),
  not one ORM object per row. The rows are still built in Python; T1a replaces this with copies
  made inside the database.

**Budgets at full volume** (`--only-dated --scale 1 --repeat 3`, 10 s in all; median · statements ·
ORM rows):

| Request | Live | Change set | History |
| --- | --- | --- | --- |
| objects: dated, first page | 5.1 ms · 5 · 85 | 82.1 ms · 6 · 4 | 4.8 ms · 5 · 3 |
| objects: dated, total | 39.8 ms · 6 · 85 | **161.2 ms** · 7 · 4 | 57.8 ms · 6 · 3 |
| children: heavy parent, dated first page | 4.6 ms · 5 · 79 | 21.4 ms · 6 · 4 | 4.7 ms · 5 · 3 |
| query: dated, first page | 4.7 ms · 5 · 85 | 89.2 ms · 7 · 5 | 5.9 ms · 6 · 4 |
| query: dated ancestor criterion, total | **110.6 ms** · 6 · 79 | **148.1 ms** · 8 · 5 | **140.3 ms** · 7 · 4 |

Four reads are over 100 ms. All four count 75,000 dated records or read a change set's overlay, the
shape of PG5's open exceptions. Their statements hold at 1× and 4× (`test_volume_baseline`). They are
recorded in [POSTGRESQL_BUDGETS](POSTGRESQL_BUDGETS.md#e8-dated-totals-and-change-set-dated-pages-0-9-t1)
with the post-1.0 fixes.

**Publish** (`--only-publish --scale 0.1`): 1,000 renamed records in a workspace of 26,000 records
took 25.0 s, 4,241 statements and 274,402 ORM rows. After the fixes above it takes 11.3 s and 2,148
statements. That is still too slow, and for a design reason: publishing and creating a change set
load the whole workspace into Python as ORM objects, merge and validate it there, and write it
back. Their cost grows with the workspace, not with the change; at full volume a publish would take
about 2 minutes, by linear extrapolation. F1's figure (43.6 s for 10,000 records) was on an empty
database.

**Decided with the user (2026-10-03): set work runs in the database.** Copies, merges and
whole-set checks are set operations inside PostgreSQL; Python decides and issues statements, and bulk
data does not travel through it (AGENTS.md, ARCHITECTURE). The copy design stays: a change set keeps
its frozen base, and a publication stays a frozen copy. Considered and set aside: storing only deltas
(as ArcGIS, SAP MDG and Oracle Workspace Manager do) and versioning every row.

Two probes on a scratch clone of the full fixture (one run each, about ±30 %):
- Copying the whole workspace by `INSERT … SELECT` took about 33 s: records with their values
  aggregated to JSON 8.5 s, relationships 15.4 s, the typed value index 9.4 s. Most of that is
  maintaining the copy tables' 17 indexes row by row.
- Loading into tables without indexes, then building the 17 indexes once, took about 14.5 s (5.7 s
  load, 8.9 s indexes). Two whole-workspace rule checks in SQL took 0.41 s and 0.05 s.

**Then decided (2026-10-03):**
- Creating a change set and publishing move into PostgreSQL as plain `INSERT … SELECT` on the
  existing tables. No partitioning, no asynchronous job, no notification stream.
- The size target for both before 1.0 is the volume fixture at 0.1 scale (about 26,000 records).
  250,000 records and more is deferred until after 1.0, in TODO next to the PG5 exceptions:
  partitioned snapshot tables, these operations as background jobs with a notification, and
  validation in SQL. Revisit when MDM is taken up.
- Delivered as the amendment [T1a](#t1a-copies-inside-the-database), before C2.

**Not re-measured.** The Q1–Q3 reads and every other read in the table are unchanged since PG5's
table of the same day ([POSTGRESQL_BUDGETS §3](POSTGRESQL_BUDGETS.md#3-results-at-pg5s-close)). The
feed pages are F2's figures from the same day. The B budgets are PG5's `budget` run. The full
`--scale 1` replay was dropped at the user's request (2026-10-03): it ran for 38 minutes because of
the `OR` query above and produced no table.

**Checks:**
- **The T1 groups together** (`queries`, `jobs`, `feed`, `change_sets`, `records`, `mapping`,
  `contract`, `startup`, `volume`): 1,056 passed and 3 failed, in 3 min 47 s; the serial part,
  3 passed. All three failures came from the fixture change: the dated one-hop scenario filled less
  than a page at the small scale, and the period rows drew from the shared random stream. Both were
  fixed, and the two modules passed (37).
- **After the flush and parameter fixes:** `change_sets`, `queries`, `feed` and `volume` (the
  guide's selection for these paths): 604 passed, in 2 min 15 s; the serial part, 2 passed.
- **After the `EXISTS` fix:** the plan was checked with `EXPLAIN` on the full seed (one index probe
  per relationship end). The regression test and the publishing cases of J26 and the composed
  journey: 7 passed, in 17 s.
- **After the apply fix and the bulk copies:** the publish and change-set journeys (J05/J06, J17,
  J26, the composed journey), `test_matrix_states`, `test_context_read_parity` and the regression
  test: 72 passed, in 32 s. At the user's request, testing stayed minimal: the guide's full
  selection for these paths (`change_sets`, `queries`, `feed`, `volume`, 2 min 15 s) was not run
  again after these last two changes.
- **Startup:** `test_a_baseline_database_upgrades_to_the_trigram_search_indexes` upgrades the
  PostgreSQL baseline to `HEAD` through all five revisions and starts twice. That is the one
  upgrade path since 0.8.0, which ran on SQLite with no migration from it.
- **`ruff check app/ tests/`:** clean.

Not run: the frontend, since nothing under `frontend/` changed; the browser runners (the volume
model's items show two more fields in the `s7` screenshots, which are inspected, not baselines).

Composable domains (ADR-032): no door is affected; the fixes change no contract.

#### T1a: Copies inside the database

**Status:** delivered 2026-10-04; approved 2026-10-03 (the J05.1 case extended by the user with a parent move and an added relationship).
**Needs:** T1. **Before:** C2.

**Behaviour:** none changes. Creating a change set from current live data and publishing answer the
same, with the same refusals; a change set's base and a publication hold exactly what they hold today.
Only where the work is done changes: the copies are made inside PostgreSQL instead of through Python.

**Scope:**
1. **Value encoding in one SQL function.** A migration creates `rdm_value_json(value_type, text_value,
   integer_value, decimal_value, boolean_value, date_value, datetime_value, json_value) RETURNS json`.
   It is immutable and gives the JSON form `stored_json_value` gives:
   - text as a string, integers and booleans as JSON values;
   - decimals as strings without trailing zeros or an exponent (`trim_scale`), with the existing
     Python encoding’s 28-significant-digit, half-even rounding preserved (clarified and approved
     2026-10-04 after the 30-digit case exposed the difference from plain `trim_scale`);
   - dates as `YYYY-MM-DD`;
   - `dateTime` as UTC in Python's `isoformat()` form, microseconds only when not zero, then `+00:00`;
   - JSON as stored, and null as null.

   It matches today's encoding: since WP-10E, every live `dateTime` is held as a UTC instant.
2. **Creating a change set from current live data** (`lifecycle._capture_current_live`). Three
   statements in the capture's transaction and snapshot, as today:
   - base records by `INSERT … SELECT` from the live records, with their values aggregated by
     `json_object_agg` over `rdm_value_json`;
   - base relationships by `INSERT … SELECT`;
   - the base's typed index copied from the live typed values.

   The live membership is no longer loaded into Python for the capture. A change set from a publication
   copies nothing today and is unchanged.
3. **Publishing** (`publish.publish_change_set`). The publication is copied from live data after the
   change is applied, since live data then is the merged result: records, relationships and the typed
   index by `INSERT … SELECT`, as in 2.
   - The merge and the whole-graph validation stay in Python (decided: rules are written once, in
     `rules.py` and `graph_diagnostics`). They still load the workspace, which the 0.1-scale target
     allows. Validation in SQL is deferred until after 1.0 (TODO).
   - Applying the change stays per changed record, so its cost follows the size of the change.
4. **Matrix states.** The copies from live to a base and to a publication (`matrix_states._copy`) and
   the publication's additions to the workspace history become `INSERT … SELECT`.
5. **Removed:** the T1 stopgap (`snapshot_values.insert_object_rows`). The flush hook stays for the
   ORM writes of change-set rows. Every bulk copy keeps its index through `snapshot_values` and
   `matrix_states`, as AGENTS.md requires.

**Test cases** (for approval, written first, confirmed failing where the behaviour is new):
- **Unit, `tests/unit/engine/records/test_values.py`: the SQL encoding equals Python's.** Given every
  value type in `VALUE_COLUMNS` and generated edge values for each:
  - text: empty, quotes, backslashes, non-Latin;
  - integers: 0, negative, the column's bounds;
  - decimals: trailing zeros, large and small exponents, negative, zero, 30 digits;
  - booleans; dates: years 1 and 9999, a leap day;
  - `dateTime`: with and without microseconds, given in UTC and in another offset;
  - JSON: objects, arrays and scalars; and null.

  When each is stored as a live value and encoded by `rdm_value_json`, then the JSON equals
  `stored_json_value` of the same value. A value type without a SQL branch fails the test, which
  holds the value-types door (below). This is the only new case that fails before the code.
- **Journey, J05.1 (from current live data):** given records of a type holding text, integer,
  decimal, boolean, date and `dateTime` values, and relationships between them; when a change set is
  created from current live data and, in it, one record's values are edited, one record is moved
  to another parent and one relationship is added, and the change set is published; then:
  - every record reads with identical values live, in the change set and in the publication;
  - the moved record has its new parent and the added relationship exists in all three contexts;
  - a filter on each value type finds the same records in all three contexts;
  - the publication holds what live data held at its feed position.

  It runs on two configurations. It passes today, so it guards the change rather than failing first.
- **Unchanged, rerun as acceptance:** the publish and change-set journeys (J05, J06, J17, the
  publishing cases of J26, the composed journey), `test_matrix_states` and `test_context_read_parity`.
- **The T1 regression test, strengthened:** creating a change set from current live data and
  publishing bind the same parameters and **cost the same number of statements** at 0.5 % and 2 %
  of the fixture. Copies made by `INSERT … SELECT` cost a fixed number of statements, so a per-record
  path fails it.
- **Startup:** the existing `test_startup` cases cover the new revision (a clean start to `HEAD`, the
  baseline upgraded through every revision, a restart). Creating a function is transactional, so an
  interrupted run leaves the previous revision; no new case. One smoke start on a copy of the
  development database.

**Measurement:**
- `volume_baseline.py --only-publish --scale 0.1` before and after, with the capture timed as its own
  row. Before T1a: publish 11.3 s.
- One `--only-publish --scale 1` run at the close, to confirm it completes; its time is recorded only.

**Checks at close:** the cases above, `ruff check app/ tests/`. No group runs beyond them, at the
user's request.

**Composable domains (ADR-032):** attribute storage and the value-types door are touched. A new value
type now needs a branch in `rdm_value_json` as well as its registry entry. The unit test enumerates
`VALUE_COLUMNS`, so the type cannot ship without one. The door stays open: adding the type is still
additive, with no contract change.


**Implementation and evidence (2026-10-04):**
- Revision `20261004_01` installs `rdm_value_json`. The SQL encoding test was written first and
  failed for the absent function. Its 30-digit case then exposed Python's existing precision of
  28 significant digits; the user approved retaining that result in SQL, including half-even ties.
- `snapshot_values.copy_live` issues three `INSERT … SELECT` statements for records with JSON
  values, relationships and the typed index. Current-live capture no longer loads the workspace
  into Python. Publication copies live only after its delta has been applied and flushed, under
  the existing workspace lock. The Python merge and graph validation are unchanged.
- Matrix states copy with `INSERT … SELECT`; history adds only previously unseen cells with a SQL
  anti-join. A history shape absent from the current model retains its SQL-derived fallback.
  The T1 `insert_object_rows` stopgap is removed; the ORM typed-index hook is retained.
- J05.1's typed-values, parent-move and added-relationship case passed on both generated models
  before and after implementation. The strengthened T1 regression passes at 0.005 and 0.02 scale:
  both the maximum parameter count and the statement count remain the same.

**Focused checks:**
- `.venv/bin/python -m pytest tests/test_startup.py tests/test_matrix_states.py
  tests/test_context_read_parity.py tests/journeys/test_j05_j06_publish.py
  tests/journeys/test_j17_review.py tests/journeys/test_j26_follow_changes.py
  tests/journeys/test_j24_j26_composed.py -q --tb=short`: **88 passed**, 82.81 s.
- After the decimal clarification, `.venv/bin/python -m pytest
  tests/unit/engine/records/test_values.py
  tests/journeys/test_j05_j06_publish.py::test_typed_values_moves_and_relationships_survive_capture_and_publish
  tests/test_volume_baseline.py::test_capturing_and_publishing_a_whole_workspace_bind_no_parameter_per_record
  -q --tb=short`: **4 passed**, 23.95 s. The final SQL encoding covers every `VALUE_COLUMNS` entry,
  nulls, generated integers and decimals, signed odd/even rounding ties, date boundaries and offsets.
- Cases over 10 s were rebuilding schema-dependent seeds (10.2–11.2 s), rather than slow new
  assertions; the new journey's warm baseline on both models took 2.98 s. No full suites or group
  expansion were run. One existing Starlette/httpx deprecation warning remains.
- A bounded independent review of the migration and copy paths found no issues.
- Smoke start on an isolated dump/restore of the development database: healthy startup and model
  reads; downgrade to `20261003_03`, a conflicting function causing an actionable migration refusal
  and `/health` 503 with the previous revision retained, then removal of that conflict, successful
  upgrade to `20261004_01` and healthy restart. The copy and dump were removed.

**0.1-scale measurement** (`.venv/bin/python -m tests.volume_baseline --only-publish --scale 0.1`;
capture is now timed separately). "After" is the run on the reused seed, after the review fixes:

| Request | Before | After |
| --- | --- | --- |
| Current-live capture | 7,737.1 ms · 106 statements · 160,701 ORM rows | 3,283.1 ms · 38 · 7 |
| Publish 1,000 renamed records | 11,196.5 ms · 2,148 statements · 274,402 ORM rows | 9,020.9 ms · 2,081 · 274,402 |

A run straight after the volume seed is rebuilt (a new schema revision) publishes in about 57 s:
56,334.0 ms at first delivery and 57,211.2 ms after the review fixes, both on a freshly built seed.
On the reused seed the same flow takes 9.1 s, with every statement timed: all 4,599 statements of
capture, staging and publish together took 7.9 s, the slowest the two relationship copies (1.3 s
each). The slow first run belongs to the freshly built seed (the Python process waits on
PostgreSQL), not to the publish; the engine's statements are the same in both runs. The unchanged
merge and validation still load the workspace, as approved.

**Full-scale completion probe**, once as approved:
`.venv/bin/python -m tests.volume_baseline --only-publish --scale 1` completed with HTTP 201 for
capture and 200 for publishing 10,000 renamed records. Seed setup took 204.0 s separately.
Capture: **55,581.9 ms · 38 statements · 7 ORM rows**. Publication: **118,969.3 ms · 20,153
statements · 2,704,503 ORM rows**. This is completion evidence only, with no latency gate at this
size; the 0.1-scale size target and post-1.0 large-workspace work are unchanged.

`ruff check app/ tests/` and `git diff --check` passed. Temporary clones, dump, probe scripts and
the private test server were cleaned up; the pre-existing development server was retained.

**Review fixes (2026-10-04):**
- **Defect, reported:** a live decimal of 1e-16383 was written and read, but capturing current live
  and publishing answered `500` (`value overflows numeric format`). `rdm_value_json` rounded with a
  `numeric` step of scale 28 plus the leading zeros, beyond PostgreSQL's 16,383. Below about
  1e-974 the halved step also fell under the 1,000-digit division scale, so a 28-digit value with an
  odd last digit silently lost one in its last place. Revision `20261004_02` adds
  `rdm_decimal_text`, which rounds on the digit string, and redefines `rdm_value_json` as one
  `STABLE` `CASE` expression, which PostgreSQL now inlines (`EXPLAIN VERBOSE`). The function had been
  called per value: the decimal branch's subquery and the `IMMUTABLE` label over the stable
  `to_char` both prevented inlining. A new revision rather than an edited one, since the development
  database already held `20261004_01`; the downgrade restores that revision's definition.
- **Typed index:** a copied base or publication indexes a decimal in its JSON form
  (`rdm_decimal_text`), as the flush hook derives it, so both hold what they held before T1a.
- **Tests:** the encoding test adds 1e-16383, 1e+131071, the odd-digit case near 1e-1000, carries,
  ties and generated decimals at every scale, and the calendar's ends for `dateTime`. It also checks
  the copied index decimal. A new J05.1 case reproduces the report through the API. The J05.1 typed
  case now checks content at the feed position: live moves on after the publication, which keeps
  what live held there. Outside the suite, 4,016 generated decimals were compared with Python on
  PostgreSQL 17, with no difference; downgrade and upgrade again were checked there too.
- **Checks:** the encoding test, `test_startup`, `test_matrix_states`, `test_context_read_parity`,
  J05/J06, J17, J26, the composed journey and the T1 regression test: 92 passed, in 1 min 36 s.
- **Found, not fixed (pre-existing, outside T1a):** a live `dateTime` within the session zone's
  offset of the calendar's end (9999-12-31T23:00Z and later in a `+01:00` session) is stored but
  cannot be read: the driver reads `timestamptz` in the session's zone and Python has no year 10000.

Functional/API evidence only; there is no changed UI, accessibility or appearance to accept.
Comprehensive build acceptance remains deferred to the build's release package.

#### T1b: One error-code pattern

**Status:** decided 2026-10-04 (C2, C-D25); planned and approved 2026-10-04, D42–D45 as
recommended; **delivered 2026-10-04**. **Needs:** T1a.
**Before:** C2. **Groups:** the full backend and frontend suites once at its close (user's
go-ahead, 2026-10-04), and `startup` for the migration.

**Behaviour.** Every error code of every API of the engine is written in upper case
(`OBJECT_NOT_FOUND`, `VERSION_CONFLICT`); today every code is lower case. The meaning, status and
message of every refusal stay as they are; only the spelling of codes changes. This is a breaking
change for API clients, accepted before 1.0, and the CHANGELOG says so.

**What is a code (D42).** Every machine-readable name of a failure or a finding:
- `error.code` in every error body: refusals, request validation (`REQUEST_VALIDATION_ERROR`), HTTP
  errors and `INTERNAL_ERROR`;
- the error inside a batch or job item outcome, a job's own error, and an unprocessed item's
  `reason` (`BATCH_ROLLED_BACK`, `JOB_CANCELLED`, `MODEL_RELEASE_CHANGED`, `JOB_FAILED`);
- diagnostic codes: model validation and its JSON-pointer refusals, compatibility and consumer
  contract diagnostics, and the graph-validation findings a change set's validation and publish
  report.

Not codes, and unchanged: status, state, stage, action, kind and classification values (`applied`,
`rejected`, `created`, `compatible`, `migration_required`), model keys and setting names.
`version_required` is both a refusal code and a classification value of the consumer contract
diff; only the code changes.

**Inventory (2026-10-04):** 153 distinct codes, raised at about 315 places in `app/`. Tests assert
them about 935 times, in 78 files. The frontend compares or holds about 100 occurrences, in about
20 files. The documents mention codes about 1,200 times, in 23 of them. The OpenAPI document lists
the four `reason` values, so its lock is re-baselined.

**Approach.**
1. **Tests first.** The assertions are rewritten to upper case, and a few journey and older tests
   across the areas are run to confirm they fail. Then the code changes.
2. **Backend.** Codes are renamed where they are produced: the code argument of `api_error`, the
   refusal helpers, the `code` of error and diagnostic dicts, `ModelReferenceError` and the
   diagnostics, and the `reason` literals. A global search and replace is not used, since a code
   string can also be another value (`version_required`). The rewrite is a script over the syntax
   tree that changes only those positions; whatever it cannot place is changed by hand and
   listed in the record.
3. **Stored codes (D43).** Revision `20261004_03` upper-cases the codes and reasons already stored in
   `jobs.error` and `job_items.outcome`, for every key named `code` or `reason`, as one set statement
   per table. Jobs are kept 7 days; without it, a finished job read after the upgrade would still
   answer lower case. The downgrade lower-cases them again. Nothing else stores a code (idempotency
   keys refer to their job).
4. **Frontend.** Every comparison with a code, and every test fixture holding one, changes to upper
   case. The UI shows messages, not codes, so no screen changes. A browser runner is not needed;
   that is confirmed during the work, and any code the UI displays would be listed.
5. **Documents (D44).** The current contract documents change: API.md, INTEGRATION_API,
   CONSUMER_API (its two upper-case codes become the pattern), USER_JOURNEYS refusals, API_JOURNEYS,
   COVERAGE_MAP, OPERATIONS and CURRENT_FUNCTIONALITY. Delivered plan records and earlier CHANGELOG
   entries are history and stay as written.
6. **Keeping the pattern (D45).** One check in the `contract` group, beside `test_boundaries`:
   every code literal at the places listed in step 2 is upper case. A new lower-case code then
   fails the build instead of reaching a client.

**Decisions (accepted 2026-10-04 as recommended):**

| # | Question | Decision |
| --- | --- | --- |
| D42 | Which strings are codes | The list above: error codes, item and job errors, unprocessed `reason` values, diagnostic codes. Statuses, actions, kinds and classifications are not |
| D43 | Codes already stored in job results | Upper-case them in the migration, so a client never sees both spellings |
| D44 | Documents | Current contract documents change; history (delivered plan records, earlier CHANGELOG entries) stays as written |
| D45 | Keeping one pattern | One static check of the code literals in the `contract` group |

**Test cases.** No new journey: every journey's refusals are asserted by code already, and those
assertions are the cases, rewritten first and confirmed failing. New: the D45 check. For the
migration: `test_startup` covers the clean start, the upgrade through every revision and the
restart. One case checks a stored job outcome with a lower-case code and reason reads upper case
after the upgrade, and lower case again after the downgrade.

**Checks at close:**
- the full backend suite once, parallel and serial parts, expected about 4 to 5 minutes, announced
  before it starts;
- the frontend `npm run test` once, then `npm run format`, `npm run lint` and `npm run build`;
- `ruff check app/ tests/`;
- a smoke start on a copy of the development database (upgrade to `20261004_03`, restart), copy
  removed afterwards.

Not run: the browser runners, a11y and visual suites, unless step 4 finds a displayed code.

**Composable domains (ADR-032):** no door is affected; codes change spelling, not meaning.

**Delivered 2026-10-04.** What was built:
- **Backend:** 542 code literals renamed in 67 files, located through the syntax tree. The two
  `version_required` classification sites (`presenters.py`, `schemas/model.py`) keep their case.
  The analysis found 490 code positions and 175 distinct codes, more than the inventory's 153:
  the graph-validation findings and the job failure codes. Restructuring's and the
  relation matrix's camel-case `reason` values (`atLeastOneOf`, `alreadyLinked`) and the parent
  candidates' (`descendant`) name why something applies, so they are not codes and keep their case.
- **Stored codes:** revision `20261004_03` upper-cases `jobs.error.code`,
  `job_items.outcome.error.code` and `job_items.outcome.reason`, one statement each. The downgrade
  lower-cases them.
- **Frontend:** 102 lines in 41 files, including the client's own `UNEXPECTED_RESPONSE`. Two screens
  show codes: model diagnostics (`ModelDiagnostics.tsx`, the code in bold) and a change-set conflict
  without a message (`ChangeSets.tsx`). No visual baseline shows either; the `model-workbench`
  baseline was inspected and holds no diagnostics.
- **Documents:** API.md (with the pattern stated under "Error responses"), USER_JOURNEYS,
  API_JOURNEYS, INTEGRATION_API, CONSUMER_API, ARCHITECTURE, APPLICATION_MODEL, OPERATIONS,
  UI_ACCEPTANCE, EXECUTION_GUIDE and COVERAGE_MAP. History stays as written (D44): the delivered
  plans, DECISIONS, PROJECT_STATUS's delivery summaries and earlier CHANGELOG entries.
- **D45:** `tests/test_error_codes.py` (group `contract`), with a case showing it finds a
  lower-case code.
- **OpenAPI lock** re-baselined: lower-casing the seven codes in the document (the four job reasons
  and three error examples) gives the previous document's hash exactly.

**Found on the way (a T1a defect):** three `test_wp81b_current_live_bases` cases patched
`lifecycle._load_live_membership` to commit a concurrent write in the middle of a capture, and T1a
removed that function. T1a's focused checks did not include the module, so it surfaced here. The
cases now inject the write around `copy_live` at the same point in the transaction, and all 14 pass:
a write committed during the capture does not reach the base, so T1a's SQL copy reads the capture's
snapshot. One parity case name, `duplicate_initial_relation`, equals a code. The rename had changed
it as a dictionary key, and it was restored.

**Checks:**
- Tests first: the backend assertions (963 lines in 79 files) were rewritten, and J02, J11 and
  `test_rule_parity` were confirmed failing before the code changed.
- **The full backend suite, once:** 1,461 passed and 12 failed, in 4 min 2 s; the serial part,
  3 passed. The 12 were the T1a capture cases (3), the parity case name (8), and
  `test_every_error_code_is_listed`, whose extraction pattern matched lower-case codes only (1).
  After the fixes, `test_wp81b_current_live_bases`, `test_rule_parity` and `test_api_journeys`:
  14 + 13 passed.
- `test_startup`: the clean start, the baseline upgrade and the new stored-codes case (an atomic
  batch's refused item and rolled-back items, down to `20261004_02` and up again): 3 passed.
- **The frontend, once:** `npm run test` 381 passed in 43 files; `format` unchanged; `lint` 0 errors
  and the 8 known warnings; `build` passed.
- `ruff check app/ tests/` clean.
- **Smoke start** on a copy of the development database: upgraded from `20261004_01` to
  `20261004_03`, healthy on two starts, a missing record answering `OBJECT_NOT_FOUND`. The copy
  holds no job results, so the stored-code rewrite is covered by the startup case. The copy was
  dropped.

Not run: the browser runners, a11y and visual suites. Five runner scripts changed only in the codes
their API assertions compare; no baseline shows a code.

## Track C — Consumer API

Scope, order and acceptance are in [CONSUMER_API.md](CONSUMER_API.md#delivery-packages); C7 moved to
0.12. Each C package follows the delivery steps above; the table adds what this plan needs.

| Package | Needs | Groups | Exit |
| --- | --- | --- | --- |
| C1 | 0.8.0 | `consumer` (new), `model`, `contract` | Schema 0.8 accepts `consumerApis` (and nothing else yet); the breaking-change check (C-D2, C-D4) |
| C2 | C1 | `consumer`, `contract` | Get by ID with projections, ancestor fields and typed values |
| C3 | C2 | `consumer`, `queries`, `volume` | Lists with and without a parent, ADR-030 paging |
| C4 | C2 | `consumer`, `volume` | XREF scoring deterministic; `expect=one` |
| C5 | C4 | `consumer`, `contract`, `volume` | Every parameter kind on XREF; `scoresFrom` |
| C14 | C4, C5 | `consumer`, `contract`, `volume` | Batch resolve equal to `xref?expect=one` per item; C-D13 limit confirmed by C-D53's budget |
| C15 | C5, C14 | `consumer`, `contract` | Crosswalk on XREF, get by ID, lists and batch resolve, with `TARGET_NOT_FOUND` and `AMBIGUOUS_TARGET` (C-D54–C-D58) |
| C6 (as [C6a](#c6a-publications) and [C6b](#c6b-the-contract-documents), C-D71) | C3, C4, F1 | `consumer`, `queries`, `contract`, `startup`, `volume` | Publications with `eventSequence` (= `feedPosition`), OpenAPI per definition, API index, resolved `workspace` named (C-D16); the document describes the `to.` names and `target` (C15); **task (D47):** C3a's value-order attribute sort for the publication (and change set) contexts, over `snapshot_attribute_values`, with its budget recorded |
| C8 | C3–C6, C14, C15 | `consumer`, `volume` | Parity scenarios 1–13 and 16 pass on the fixture model |
| C16 | C2, Q4 | `consumer` | `asOf` everywhere; SC-11's consumer half; parity scenario 15 |
| C9 | C2 | `consumer`, `model` | `events` validated and in the contract check |
| C10 | C9, F2 | `feed`, `consumer` | Deriver checkpoint per workspace; pull feed with `410` |
| C11 | C10 | `feed`, `contract` | Subscriptions API under its capability, host allowlist, suspension on model change |
| C12 | C11 | `feed` | Ordered per-change and coalesced delivery, retry, suspension (`DELIVERY_FAILED`, `FILTER_MATCHES_NOTHING`, `HOST_NOT_ALLOWED`); resume with C-D93's check is built in C11 |
| C13 | C12 | `feed`, `volume` | Event scenarios 1–9, 11–13 and parity scenario 14; bulk-volume delivery budget |

#### C1: Consumer API definitions

**Delivered 2026-09-30.** Schema 0.8 is open and accepts `consumerApis` and nothing else yet
([APPLICATION_MODEL](APPLICATION_MODEL.md#consumer-api-definitions-consumerapis),
[CONSUMER_API rules](CONSUMER_API.md#definition-shape)). Decisions C-D17–C-D20 were raised before
coding and accepted as recommended. What was built:

- **Shape** in `models/schema.py` (`ConsumerApiDefinition` and its parts; parameters are a union on
  `kind`, so a parameter's options are checked by its kind). `from` keeps its spelling in the canonical
  document; absent optional parts are omitted, so releases without definitions keep their hash.
- **References** in `engine/model/validation/consumer_api_rules.py`, the last rule of the chain, each
  refused at `/consumerApis/<key>/…`. The rules CONSUMER_API left open are recorded there under
  "Delivered in C1": URL-safe keys, the identity as `id` or a `unique` attribute, reserved and unique
  output names, route and ancestor checks. `events` stays an unknown field until C9.
- **Contract** in `engine/model/consumer_contract.py`: `output_contract` derives what consumers read
  (types and public names, output fields with value types, projection shapes from cardinality and
  their fields, weights, lists, parameter kinds), with the same field resolution validation uses;
  `contract_diagnostics` compares a candidate with the active release (C-D17, C-D18). C2 builds its
  reads on the same resolution.
- **Where the check shows:** `consumerContracts` on draft compile and release diff (classification
  `compatible` or `version_required`), and activation refused with `409
  consumer_contract_version_required` after the data compatibility check
  ([API.md](API.md#installed-releases)). A separate block rather than a new
  `compatibility` classification, since a contract break is not a data migration.

Found on the way: CONSUMER_API's own example names a list's parent parameter like a definition
parameter (`codelist`), so that is allowed rather than refused as a clash.

**Checks:** `test_consumer_api_model` (new, `consumer` + `model` + `model_admin`; 87 passed): CONSUMER_API's
reference definition reduced to the starter compiles, round-trips its canonical hash and yields the
expected contract, on the starter and on a copy with every key renamed; schema 0.7 and `events`
refused; 26 reference refusals each at its pointer; shape errors at theirs; 12 breaking changes each
reported at its path and released by a higher `contractVersion`; additions compatible; a lower version
and a removed definition reported; a cardinality change in the model turning a projection from an
array into an object; and, on a database of its own, draft compile, release diff and activation (a
break refused with the active release unchanged, then accepted under version 2). Groups `consumer`,
`model`, `model_admin` and `contract` together: 404 passed, with the re-baselined OpenAPI lock
(checked by diffing the document against HEAD: `ModelConsumerContractsResponse` added and
`ModelReleaseDiffResponse.consumerContracts`; the draft routes are outside the locked document) and
four tests updated for the supported schema list now ending in 0.8. `ruff check app/ tests/` clean.

Not run: `startup`, since no migration or startup path changed (schema 0.8 needs no table; the
supported list is exercised by `model_admin`'s recovery and activation tests); `volume`, since no read
changed; frontend checks, since nothing in the frontend changed (it types `schemaVersion` as a
string). The full suites wait for R.

#### C2: Consumer object and projections

**Delivered 2026-10-04** ([record](#c2-delivery-record)). Planned 2026-10-04; decisions C-D21–C-D26
settled and test cases 1–7 approved by the user the same day. **Needs:** C1 and the amendment [T1b](#t1b-one-error-code-pattern) (error codes
in upper case). **Groups:** `consumer`, `contract`.

**Behaviour.** A consuming system reads one business object by its object ID:

```text
GET /api/consumer/{apiKey}/v{contractVersion}/objects/{id}?workspace=…
```

The answer is the definition's shared object ([CONSUMER_API](CONSUMER_API.md#the-shared-object)),
built from the definition alone. XREF results and list items (C3, C4) reuse it unchanged. Data is
read live, from the active release's definition. Change sets are never read (C-D6), and
`publication` arrives in C6.

- **Identity (C-D24).** `{id}` is the engine's object ID, unique across the database
  (`ix_objects_id`), whether generated or assigned by a client (B1's upsert by ID). The answer is that
  object when its type is exposed; otherwise, for a deleted record, or for an unknown ID,
  `404 OBJECT_NOT_FOUND`. Other identifiers, such as an attribute holding a former system's ID, are
  found with XREF (`expect=one`), which searches attributes (C4). No guard for several objects: the
  unique index makes that state impossible, and a check no test can reach is not built.
- **The `id` role** names the output field of the object ID (for example `masterId`); its source is
  the built-in `id`. C1's validation is narrowed to that: another source is refused at
  `/consumerApis/<key>/object/id/source`. A former system's ID is published as an ordinary
  attribute field. A migration that wants to keep a former ID *as* the object ID assigns it as the
  object ID, which B1 accepts when it is a UUID.
- **Roles and attributes.** Each role (`code`, `name`, `active`, `validFrom`, `validTo`) and each
  further attribute takes the first of its sources that has a value, then its `default`, then
  `null`. Empty text is no value, as everywhere in the engine (required fields, `atLeastOneOf`,
  uniqueness), so a consumer never receives `""`. Values keep their declared types, in the
  management API's encoding: integers and booleans as JSON values, decimals as strings without
  trailing zeros, dates as `YYYY-MM-DD`, `dateTime` as UTC. Every declared field is always present;
  a field the definition does not declare never appears. `objectType` is the type's public name.
- **Parent (C-D22).** `parent` is an object or `null`, never omitted. It has the declared `fields`,
  each read through the same roles from the parent record. When the parent's type is not exposed,
  its `objectType` is `null`: a model key never appears in the contract.
- **Hierarchy and path (C-D21).** `hierarchy` lists the ancestors, from the top down to the parent,
  without the object itself; `path` joins them with `/`. For an object at the top, `hierarchy` is
  `[]` and `path` is `""`. Both use each ancestor's `name` role, falling back to its built-in name,
  and walk the parents (never split on `/`).
- **Projections.** Each projection reads the records related through its relation and direction.
  Its shape comes from cardinality (C1's `projection_shape`): an object or `null`, or an array,
  `[]` when empty. A field reads `name`, `id`, an attribute, or `ancestor:<type>.<field>` (the
  nearest ancestor of that type). Array items are ordered by the related record's name, then its
  ID. The related records need not be exposed types.
- **Workspace (C-D16, C-D23).** `workspace` selects the workspace, defaulting to the deployment's
  default. Get by ID answers the bare shared object, the shape XREF items have, and names the
  workspace it read in the `RDM-Workspace` header, on every consumer response. C3 and C4's envelopes
  also carry it as a field.
- **Parameters.** An unknown parameter answers `400 UNKNOWN_PARAMETER`, naming it. C2 builds the
  parameter handling C3 extends. In C2 every declared definition parameter answers
  `400 PARAMETER_NOT_SUPPORTED`, naming it, because no kind is applied yet. C3 applies the kinds,
  and from then on only a parameter that does not apply to get by ID is refused.
- **Not found.** An unknown `apiKey` answers `404 CONSUMER_API_NOT_FOUND`. A `contractVersion` other
  than the installed one (C-D3) answers `404 CONTRACT_VERSION_NOT_FOUND`, naming the installed
  version. An unknown or retired workspace answers `404 WORKSPACE_NOT_FOUND`.

**Design.**
- `app/consumer/` is created as the tier ([BACKEND_BOUNDARIES_PLAN](BACKEND_BOUNDARIES_PLAN.md#tier-rules)):
  its router mounts at `/api/consumer` and reads only through `engine`, never `management`. Errors
  use the engine's envelope (`ApiError`, rendered by the app-wide handlers).
- Every read finds its records in its own way (get by ID by the object ID; C3 by parent and position;
  C4 by score), then builds the shared object in one place: `engine/reads/consumer_objects.py`
  composes objects **for a set of IDs**. The statements are fixed in number, whatever the set's size:
  one for the records and their values, one recursive CTE for every ancestor needed (of the objects
  and of projected records), and one per projection. Nothing is loaded per object. Field resolution
  is C1's (`consumer_contract`), so the validated contract and the composed response cannot drift
  apart.
- The consumer routes stay out of the management OpenAPI document (`include_in_schema=False`); C6
  generates one document per definition. The OpenAPI lock is unchanged.
- No migration and no index: get by ID seeks the object ID's unique index. The consumer index
  belongs to C4.

**Decisions (settled with the user, 2026-10-04):**

| # | Question | Decision |
| --- | --- | --- |
| C-D21 | Do `hierarchy` and `path` include the object itself? | No: the ancestors from the top down. At the top, `[]` and `""` |
| C-D22 | `parent.objectType` when the parent's type is not exposed | `null`; the other parent fields are read as usual |
| C-D23 | How get by ID names the resolved workspace (C-D16) | The `RDM-Workspace` header on every consumer response; get by ID stays the bare shared object; collection envelopes also carry it as a field |
| C-D24 | What `{id}` in get by ID is | The object ID only, unique across the database. Other identifiers go through XREF, whose `409 AMBIGUOUS_MATCH` names a faulty migration's duplicates. No `409` in get by ID: it could never occur, so it could never be tested, and it is not built. The `id` role's source is the built-in `id` (C1 narrowed). Database-backed uniqueness for `unique` attributes is recorded in TODO for a later build |
| C-D25 | Error code pattern | Upper case across every API of the engine, done first as the amendment T1b |
| C-D26 | When a source has no value | Absent, `null` or empty text, as everywhere in the engine. Not a new rule |

**Journey.** New: **J28 — Read a business object through a consumer API** (actor: consuming
system; channel: consumer API), with the J28 variants below, in USER_JOURNEYS and API_JOURNEYS.
Both generated configurations get a consumer definition, structure `Capi`, with their own keys,
public names and output names. It exposes `R` and `R2` (under `R`), with the `id` role,
`code` (`R2.u`, then `R.u`), `name`, `active` (`R.b`, default `true`), typed attributes (`R.n` with a
default, `R.dt`), `parent`, `path` and `hierarchy`. Its projections are `B11` outgoing (object or
`null`) and `Bown` outgoing, with `ancestor:G.name` (an array). The example model holds no
definition, so J28 runs on generated A and B. Adding `Capi` changes their models once, which
rebuilds their seeds once.

**Test cases** (journey tests, written first and confirmed failing):
1. **J28 The shared object.** Given an `R` with typed values, `R.u` set and `R2.u` empty text, one
   `B11` target, two `Bown` dependants under different `G`s, and an `R2` under it. When each is read
   by its object ID. Then each answers exactly the declared fields with declared types:
   - `code` skips the empty text and reads `R.u`, and the unset attribute takes its default;
   - `R`'s parent is `null`, its `hierarchy` `[]` and `path` `""`; `R2`'s parent names `R`, and its
     `hierarchy` is `[R's name]`;
   - the `B11` projection is an object, and `null` on a record without the relationship;
   - the `Bown` projection is an array ordered by name, with each `G`'s name; a record with no
     dependants has `[]`.
2. **J28.1 Identity is the object ID.** Given an `R` created with a client-assigned ID and one with a
   generated ID. When read by those IDs, then each is found. When read by its `R.u` value, then
   `404 OBJECT_NOT_FOUND`.
3. **J28.2 Live data, never unpublished work.** When a record is changed live, the next read shows
   the change. A record created only in an open change set is `404 OBJECT_NOT_FOUND` until the
   change set is published, then found.
4. **J28.3 Another workspace.** Given a record in W1 and one in W2. When read with `workspace=W2`,
   and without it. Then each is found only in its own workspace, named in `RDM-Workspace` (the
   default when omitted). An unknown workspace is `404 WORKSPACE_NOT_FOUND`.
5. **J28.4 Refusals.** An unknown `apiKey` is `404 CONSUMER_API_NOT_FOUND`. Version 2 of a
   version-1 API is `404 CONTRACT_VERSION_NOT_FOUND`. A record of a type the definition does not
   expose is `404 OBJECT_NOT_FOUND`. `pagesize=5` is `400 UNKNOWN_PARAMETER`, naming it. A declared
   parameter is `400 PARAMETER_NOT_SUPPORTED`.
6. **J28.5 The contract follows the release** (with J25.2). When a release changes `B11` to
   one-to-many and raises `contractVersion` to 2, then `v1` answers `404
   CONTRACT_VERSION_NOT_FOUND`, and `v2` returns the projection as an array.
7. **J25 (changed): the `id` role's source.** A definition whose `id` source is an attribute is
   refused with `422 INVALID_MODEL` at `/consumerApis/<key>/object/id/source`.

No unit tests: the logic with edge cases (sources, defaults, shapes) is what the journeys assert,
and field resolution is C1's, already tested. **Checks:** the J28 and J25 cases, the `consumer` and
`contract` groups, `test_boundaries`, and `ruff check app/ tests/`. No migration, so no `startup`
group.

**Docs at delivery:** API.md gains the consumer get by ID; CONSUMER_API records C-D21–C-D26 and
changes its identity text and example (`masterId` from the object ID, a former ID as an attribute
field); USER_JOURNEYS adds J28 and amends J25, API_JOURNEYS adds the route; CURRENT_FUNCTIONALITY
and PRODUCT describe reading one business object.

**Composable domains (ADR-032):** the identity door is narrowed for consumers: get by ID uses the
object ID; other identifiers stay searchable through XREF. Attribute storage, audit and the `match`
declaration are untouched. No door closes.

##### C2 delivery record

**Delivered 2026-10-04.** What was built:

- **Tier.** `app/consumer/` with its router at `/api/consumer` (`include_in_schema=False`), reading
  only through the engine; errors use the engine's envelope. The route checks its own parameters
  against the definition, so the app-wide unknown-parameter check
  (`management/query_parameters.py`) skips a route marked `reads_own_parameters`; the management
  tier's `422 UNKNOWN_PARAMETER` is unchanged, the consumer tier answers `400` as specified.
- **Composition.** `engine/reads/consumer_objects.py`: `ConsumerObjects.compose` builds the shared
  object for a set of IDs with one statement for the records and their values, one per projection,
  and one recursive CTE for every ancestor the objects and their projected records need; field types,
  shapes and `ancestor:` references come from `consumer_contract`. `consumer_definition` resolves
  the `apiKey` and contract version; `read_consumer_object` is get by ID. Defaults are encoded like
  stored values (decimal strings without trailing zeros, `dateTime` in UTC).
- **Validation.** C1's identity rule narrowed: the `id` role's source is `["id"]`, refused otherwise
  at `/object/id/source`.
- **Configurations.** Generated A and B declare `Capi`, with their own API keys (`ledger-api`,
  `x7-registry`), public names and output names held as `Capi.…` structure keys; `World.with_consumer_api`
  now adds its definition beside the configuration's instead of replacing them.

**Differences from the plan:**

- **`R2.u` became optional** in the generated configurations. Test case 1's given ("`R2.u` empty
  text", read by `code` before `R.u`) cannot be produced through the API while `R2` requires
  `R2.u`, since a required attribute refuses empty text; with it optional, the `R2` record carries
  empty `R2.u` and `R.u`, and `code` skips the empty text as the case says. The case text is
  unchanged. No other journey depended on `R2.u` being required (J11 sets it).
- **J28.3** also asserts that a retired workspace answers `404 WORKSPACE_NOT_FOUND`, which the
  behaviour section states.
- **J28.5** is marked with J25.2 as well, as the case names.
- **Not confirmed failing first:** case 7 (J25, the identity source) was written after the
  validation change, so it passed on its first run; cases 1–6 failed before the route existed (12
  failures, `404 HTTP_ERROR`).
- Reserved names not yet served (`publication`, `asOf`, `to.…`) answer `400 UNKNOWN_PARAMETER` until
  their packages (C6, C16, C15).

**Checks:** J28 and J25 journey tests on generated A and B (20 passed). Groups `consumer` (107) and
`contract` (66) together, parallel: 172 passed and `test_api_journeys` failed until API_JOURNEYS
listed the new codes, then passed (5); the serial part selects nothing for these groups.
`test_boundaries` (in `contract`) holds the new tier. Named risks from shared changes: J08.2 (the
consumer-API helper now keeps `Capi`), J11 (`R2.u` optional) and J21.8 (the parameter check's skip):
24 passed. OpenAPI lock unchanged (in `contract`). `ruff check app/ tests/` clean. Not run: `startup`
(no migration or startup path changed), `volume` (no budget yet; the fixed statement count is by
construction, not measured), the frontend (unchanged), the full suites (R).

#### C3: Consumer lists and parameters

**Delivered 2026-10-04** ([record](#c3-delivery-record)). Planned 2026-10-04; decisions C-D27–C-D33
were settled with the user the same day. **Needs:** C2.
**Groups:** `consumer`, `queries`, `contract`, `volume`.

**Behaviour.** A consuming system reads a declared list of business objects, page by page, and narrows
it and get by ID with the definition's parameters:

```text
GET /api/consumer/{apiKey}/v{contractVersion}/lists/{listKey}?{parentParameter}=…&{parameters}&{paging}&workspace=…
```

- **Items** are the shared object, built by C2's composition, so a list item equals get by ID's
  answer for the same record and parameters. A list holds records of its `objectType` only, read
  live in the workspace (C-D6, C-D16). Change sets are never read; `publication` arrives in C6 and
  `asOf` in C16, and until then both answer `400 UNKNOWN_PARAMETER`.
- **Without a parent value** a list holds every record of its type in the workspace, each item
  showing its `parent`. That holds whether or not the list declares a parent parameter.
- **With a parent value (C-D27, C-D28).** The parent parameter is an optional filter that takes
  object IDs only, never names or codes. It keeps the records of the list's type anywhere below that
  record. This matters where the model lets a type sit under several parent types: with cities under
  a country or under a region, cities filtered on Czechia include Brno, which sits under Moravia, and
  Brno's `parent` is still Moravia. A city under another country is not included. Several IDs give
  the records below any of them (C-D32).
- **Order (C-D29).** The list's optional `sortBy` attribute first, with records that have no value
  last, then name, then creation order. Every page of a read keeps that order.
- **Paging (C-D30)** works as on the management lists (ADR-030):
  - cursors both ways (`cursor`), with `anchor` reopening a page;
  - `position` to jump to a row;
  - `from=end` for the last page;
  - `seek` by the sort value;
  - `includeTotal=true` for `totalCount` and `startIndex`;
  - `pageSize` from 1 to 100, default 20.

  The envelope:

  ```jsonc
  { "items": [ … ], "workspace": "…", "pageSize": 20,
    "nextCursor": "…", "prevCursor": "…", "anchor": "…", "totalCount": 412, "startIndex": 40 }
  ```

  `workspace` is also in the `RDM-Workspace` header (C-D23). `totalCount` and `startIndex` are `null`
  unless `includeTotal=true`.
- **Parameters (C-D31, C-D32, C-D33).** From C3, every definition parameter applies to get by ID and to
  every list. The kinds `objectType`, `ancestor`, `related` (through a projection, `self` or a shared
  projection) and `projection` filter the set, and `projection` also limits a projection's items.
  - A parameter takes several values, repeated (`codelist=A&codelist=B`), comma-separated
    (`codelist=A,B`) or both. The values are alternatives, and different parameters combine with
    AND.
  - ~~In a value, `\,` is a comma and `\\` a backslash~~: not approved; replaced by C3b (a comma in a
    value is `%2C`).
  - On get by ID the set has one record, so a parameter that filters the record out answers
    `404 OBJECT_NOT_FOUND`.
  - `scoresFrom` has no effect outside XREF (C4, C5), and `to.…` arrives in C15.
- **Which parameter answers what.** A name the API knows but the route does not apply answers
  `400 PARAMETER_NOT_SUPPORTED`, naming it: a list's parent parameter on get by ID or on another list,
  or a paging name on get by ID. Any other name answers `400 UNKNOWN_PARAMETER`.
- **Refusals.**
  - An unknown `listKey` answers `404 LIST_NOT_FOUND`.
  - A parent ID that is no record of the parent types in the workspace answers
    `404 PARENT_NOT_FOUND`, naming it.
  - An `objectType` value that is not an exposed public name answers `400 UNKNOWN_OBJECT_TYPE`, naming
    the public names.
  - A page size outside 1–100 answers `400 INVALID_PAGE_SIZE`.
  - The shared paging refusals keep their codes (`INVALID_CURSOR`, `CONFLICTING_PAGE_PARAMETERS`,
    `INVALID_POSITION`, `INVALID_SEEK`) with status `400`, the consumer tier's status for a request
    error (as C2 did for `UNKNOWN_PARAMETER`).

**Design.**

- **Route** `GET /{apiKey}/v{contractVersion}/lists/{listKey}` in `app/consumer/router.py`. C2's
  `_check_parameters` grows into one check per route. It takes the names the route serves and the
  names the definition knows, and gives the two answers above. It splits each parameter's values,
  repeated and comma-separated, with the escape, in one place.
- **Filters** in `engine/reads/consumer_parameters.py`. Each parameter becomes a SQL predicate on the
  record (`RdmObject.id`), so a filter, its total and a position jump stay in the database. Get by ID
  and the lists use it in C3, and XREF (C4, C5) and batch resolve (C14) reuse it.
  - A value first finds its candidates: the records of the listed types that match it, read
    through the same index reads a search uses. Text is compared ignoring case; a value that does not
    parse for a typed field does not match that field.
  - An `ancestor` parameter keeps the candidates' descendants: a recursive CTE walks down from them
    through the records of the container types only, and a record is kept when its parent is one of
    them (as Q3's ancestor criterion does; amended at delivery).
  - `self` keeps the candidates themselves.
  - A projection route is an `EXISTS` over the projection's relation and direction. A shared projection
    is an `EXISTS` over two relationships of that projection meeting in one record. Through a shared
    projection, the matching record itself is kept only by `self`.
  - A `projection` parameter's match fields are fields of the projected records, so
    `ancestor:<type>.<field>` resolves the same way, through the ancestor's candidates.
- **Lists** in `engine/reads/consumer_lists.py`.
  - The list's statement comes from `build_object_query`, the per-type list's builder: the type, the
    workspace and the `sortBy` sort, with its typed sort keys, records without a value last, and its
    seek.
  - Parent IDs become the same container walk, and the parameters add their predicates.
  - `paginate_statement` pages it under the scope `consumer-list:<apiKey>:<listKey>`. The cursor binds
    the workspace, the parent IDs, every parameter value and the contract version, so a cursor never
    carries over to another read.
  - `ConsumerObjects.compose` builds the page's IDs. It now also takes the `projection` parameters'
    limits as predicates on the projection's statement, so limiting is SQL as well. A page still costs
    a fixed number of statements, whatever its size or the list's length.
- **Model.**
  - `sortBy` is optional on a list (schema 0.8, which is not yet in a product release). It names a
    scalar attribute, not JSON, bound to the list's type, and is refused otherwise at
    `/consumerApis/<key>/lists/<list>/sortBy`. `output_contract` includes it, so changing or removing
    it is a breaking change (C-D18 extended, C-D29).
  - `from`, `seek` and `includeTotal` join the reserved parameter names (C-D30).
- **No migration and no new index.** A list without a parent value in name order reads
  `ix_objects_type_name` (workspace, type, name, sequence). A `sortBy` list joins the typed value, as
  the per-type list does. The consumer index belongs to C4.

**Decisions (settled with the user, 2026-10-04; C-D32's escape excepted, see C3b):**

| # | Question | Decision |
| --- | --- | --- |
| C-D27 | Does a parent value keep the parent's direct children, or every record of the list's type below it? | Every record of the list's type below it. Where a type can sit under several parent types (cities under a country or a region), a city under a region of the country is included, and a city under another country is not. Each item's `parent` is its direct parent. The parent parameter is an optional filter: without it, the list holds every record of its type |
| C-D28 | How a list's parent is named | By object ID only, with no free-text matching: a consumer reads the parent's list first and uses the IDs it returns. An ID that is no record of the parent types is `404 PARENT_NOT_FOUND`. Amends CONSUMER_API's Lists text ("identity, name or declared code fields") and C8's parity scenario 10, whose name and code cases go through an `ancestor` parameter declared on a list without a parent |
| C-D29 | List order. CONSUMER_API names "the definition's sort field", which the schema does not have | An optional `sortBy` on a list. Records without a value come last, then name, then creation order (what every engine list ends with, served by `ix_objects_type_name`; CONSUMER_API's "then ID" is amended). A change to `sortBy` is a breaking change |
| C-D30 | Paging modes | As on the management lists: cursors both ways with `anchor`, `position`, `from=end`, `seek` and `includeTotal`, with `pageSize` 1–100 (default 20). `from`, `seek` and `includeTotal` become reserved names. The reference's `page` and `returnedCount` are not carried over (`startIndex` and the length of `items` give them) |
| C-D31 | Where parameters apply | Every definition parameter applies to get by ID and to every list; on get by ID it filters a set of one (`404 OBJECT_NOT_FOUND` when filtered out). `PARAMETER_NOT_SUPPORTED` stays for a known name a route does not apply. Batch resolve (C14) applies its `defaults` to by-ID items this way |
| C-D32 | Parameter values | **The escape was not approved by the user and is replaced by [C3b](#c3b-several-values-the-standard-way) (2026-10-04).** Several values per parameter, repeated, comma-separated or both, as alternatives; different parameters combine with AND (as the management API's repeated filters do). The escape is the engine's own, `\,` and `\\`, since a server decodes `%2C` to a comma before the engine sees it. XREF's comma-separated `query` (C4) uses the same escape. Text matches ignoring case; a value that does not parse for a typed field does not match it. `ancestor` matches at any depth; through a shared projection, the matching record itself is kept only by `self`. An unknown `objectType` value is `400 UNKNOWN_OBJECT_TYPE`. Commas on the management API's repeated filters are recorded in TODO |
| C-D33 | Scope between C3 and C5 | C3 delivers all four kinds for lists and get by ID, including `objectType` and the shared-projection route; C5 becomes XREF's use of them, with `scoresFrom`. CONSUMER_API's C3 and C5 rows are amended |

**Journey.** J28 gains the list variants: its status says lists follow in C3, and a list is still a
consumer reading business objects. New variants J28.6–J28.10, and J28.4 changes. USER_JOURNEYS and
API_JOURNEYS add the route, `sortBy` and the new codes. Generated A and B's `Capi` gains:

- `D` exposed, with the same roles; its `code` is `null`.
- A projection over `Bscope`, outgoing.
- The lists: `all` (`R`, no parent, `sortBy` `R.n`), `entries` (`R2` under `R`) and `permits` (`D`
  under `G`). In B, a `D` is two levels below its `G`, through `M`. The tests put each `D` under an
  `M` in A as well.
- The parameters: `container` (`ancestor`, `M` by name, replacing C2's single parameter), `permit`
  (`projection` over `Bown`, matching `ancestor:G.name`, `requireMatch`), `token` (`related`, `K` by
  name through `B11`), `peer` (`related`, `R` by name through `self` and the shared `Bscope`) and
  `kind` (`objectType`).

Their keys and names are `Capi.…` keys. The change rebuilds the two seeds once. If C1's validation
refuses `D` with roles whose sources it lacks, the case stops and asks rather than reshaping `Capi`.

**Test cases** (journey tests, written first and confirmed failing):

1. **J28.6 Every object of a type.** Given five `R`, two of them without `R.n`, an `R` only in an open
   change set, and some `R2`. When `all` is read with `pageSize=2` to the end through `nextCursor`, back
   through `prevCursor`, at `position=2`, with `from=end`, and with `seek` on an `R.n` value. Then:
   - each live `R` appears once, by `R.n` and then name, the two without a value last;
   - the `R2` and the change set's `R` are absent;
   - with `includeTotal=true`, `totalCount` is 5 and `startIndex` follows the page; without it, both
     are `null`;
   - each item equals its get by ID answer;
   - `workspace` is named in the field and in the header.
2. **J28.7 Below a parent.** Given `R` "North" with two `R2` and "South" with one; and two `G`, each
   with an `M` holding `D`. Then:
   - `entries` by North's ID gives its two `R2`; by North's and South's IDs, repeated or
     comma-separated, all three; without a parent value, all three, each with its `parent`;
   - `permits` by one `G`'s ID gives the `D` two levels below it and none of the other `G`'s;
   - North's name answers `404 PARENT_NOT_FOUND`, and so do a `K`'s ID and an unknown ID.
3. **J28.8 Parameters narrow a list.**
   - `permits` with `container` keeps the `D` of that `M`.
   - `token` keeps the `R` whose `B11` target has that name, in another case as well.
   - `peer=Ra` keeps `Ra` (through `self`) and `Rb` (it shares a `Bscope` `D`), and not `Rc`.
   - `permit` limits each `R`'s permits to that `G`'s and drops the `R` without one, and `totalCount`
     follows.
   - `kind` with `R`'s public name keeps every `R`, with `R2`'s keeps none, and with an unknown name
     answers `400 UNKNOWN_OBJECT_TYPE`.
   - Two values of `token`, repeated and comma-separated, keep the `R` matching either. A `K` named
     "Bonds, Notes" is matched by `token=Bonds\, Notes` and not by `token=Bonds`.
   - Two parameters together give the records both keep.
4. **J28.9 Parameters on get by ID.**
   - `permit` limits the array.
   - An `R` without such a permit, or with a `container` that does not match, answers
     `404 OBJECT_NOT_FOUND`.
   - `pageSize`, or a list's parent parameter, answers `400 PARAMETER_NOT_SUPPORTED`.
5. **J28.10 Paging refusals.**
   - An unknown list answers `404 LIST_NOT_FOUND`.
   - `pageSize=0` and `pageSize=101` answer `400 INVALID_PAGE_SIZE`.
   - `cursor` with `position` answers `400 CONFLICTING_PAGE_PARAMETERS`.
   - A cursor from `all` sent with a different `token` answers `400 INVALID_CURSOR`.
6. **J28.4 (changed).** C2's case of a declared parameter answering `400 PARAMETER_NOT_SUPPORTED`
   becomes a list's parent parameter on get by ID.
7. **J25 (changed): `sortBy` and the reserved names.**
   - An unknown attribute, a JSON attribute and an attribute the list's type does not bind are each
     refused at `/consumerApis/<key>/lists/<list>/sortBy`.
   - Changing `sortBy` is reported as `version_required`.
   - A parameter named `from`, `seek` or `includeTotal` is refused as reserved.

**Volume.** A new module, `test_consumer_list_volume` (`consumer`, `volume`). The volume model gains
a consumer definition over `vol-group` and `vol-item`:

- items under a group (the parent by ID);
- every item, with `sortBy` on the rank;
- one `ancestor` parameter.

The change rebuilds the volume seeds once. At scales 0.01 and 0.04, these reads each cost the same
statements, with rows bounded per listed row as S1's budgets require:

- a first page;
- the next cursor page;
- a `position` jump to the middle;
- a parent list;
- a filtered list with `includeTotal`.

Each is timed once at full volume with `volume_baseline.py` against the 100 ms read budget, and the
figures are recorded here. A read over budget is reported with its cause and not tuned in a loop.

No unit tests beyond the volume budget. The edge cases (parent filter, the kinds, values, order) are
what the journeys assert, and the composition is C2's. **Checks:** the J28 and J25 cases on generated
A and B, the groups `consumer`, `queries` (the shared builder), `contract` (the route,
`test_boundaries`, the API inventory) and `volume` (the new module), and `ruff check app/ tests/`. No
migration, so no `startup` group.

**Docs at delivery:**

- API.md gains consumer lists and the parameters on get by ID.
- CONSUMER_API records C-D27–C-D33 and amends:
  - the Lists endpoint text (parent by ID, order, paging, envelope);
  - the reserved names;
  - the C3 and C5 rows;
  - parity scenario 10;
  - the "not carried over" table (`page`, `returnedCount`).
- APPLICATION_MODEL gains `sortBy`.
- USER_JOURNEYS amends J28; API_JOURNEYS adds the route and the codes.
- TODO records commas on the management API's repeated filters.
- CURRENT_FUNCTIONALITY and PRODUCT describe reading a list.

**Composable domains (ADR-032):** identity, attribute storage, audit and the `match` declaration are
untouched. The product catalogue's `lists/products?category=…&position=…` (CONSUMER_API's
`catalogue` example) is served by this package, so the door is exercised rather than narrowed.

##### C3 delivery record

**Delivered 2026-10-04.** What was built:

- **Route** `GET /api/consumer/{apiKey}/v{contractVersion}/lists/{listKey}` in `app/consumer/router.py`.
  One parameter check serves both routes (`_Parameters.check`): a name the API does not know is
  `400 UNKNOWN_PARAMETER`, a known one the route does not apply `400 PARAMETER_NOT_SUPPORTED`; values
  are split once, repeated and comma-separated (C3 split on `\,`; replaced by C3b's raw-query
  split). The shared paging refusals answer `400` on this tier.
- **Parameters** in `engine/reads/consumer_parameters.py`: each kind is a predicate on the record
  (`objectType`, `ancestor`, `related` through a projection, `self` or a shared projection, and
  `projection` with `requireMatch`), and a `projection` parameter is also a limit on that projection's
  items, which `ConsumerObjects.compose` now applies in SQL. Get by ID filters its set of one with the
  same predicates (`404 OBJECT_NOT_FOUND` when filtered out).
- **Lists** in `engine/reads/consumer_lists.py`: `build_object_query` with the list's `sortBy`, the name
  key inserted before the creation-order tiebreak (C-D29), the parent IDs and the parameters as
  predicates, `paginate_statement` under `consumer-list:<apiKey>:<listKey>` with the workspace, parent
  IDs, parameter values and contract version bound into the cursor; the page composed by C2's
  `ConsumerObjects`.
- **Model:** `sortBy` on a list (schema 0.8), refused at `/lists/<list>/sortBy` when it is not an
  attribute the list's type binds or holds JSON; part of `output_contract`, so changing it is breaking
  (reported at `/lists`, as C1 reports other list changes). `from`, `seek` and `includeTotal` reserved.
- **Configurations:** generated A and B's `Capi` gained `D`, the `Bscope` projection, the three lists
  and the five parameters; list keys are URL keys in B as well (`x7-…`). The volume model gained a
  consumer definition (`vol-consumer`: items by group, items by rank, an ancestor parameter).

**Differences from the plan:**

- **Below a parent or an ancestor** walks only the records of the types that can contain the listed
  type, from the start records down, and keeps the records whose parent is one of them
  (`consumer_parameters.below`), as Q3's ancestor criterion does. The plan's recursive CTE over every
  descendant was built first and measured 793 ms for the 20,000 items under the heavy group at full
  volume (each step merge-joined the whole parent index); with the container walk it is 7.4 ms.
- **`INVALID_PAGE_PARAMETER`** (`400`) is added for `from` other than `start`/`end` and `includeTotal`
  other than `true`/`false`; the plan named no code for them. A non-integer `pageSize` is
  `INVALID_PAGE_SIZE`, a non-integer `position` `INVALID_POSITION`.
- **`objectType` values** compare with the public names exactly (case-sensitive); match fields compare
  text ignoring case, as specified.
- **J28 case 1 (C2's, approved)** now lists the `Bscope` projection among the declared fields: the plan
  adds that projection to `Capi`, so the shared object gains the field. No assertion was weakened.
- **Not confirmed failing first:** the J25 case (`sortBy` refusals, its breaking change, the reserved
  names) was written after the model change and passed on its first run. The other cases failed
  before the route existed (12 failures: J28.4 and J28.6–J28.10 on A and B).
- The volume definition's ancestor parameter matches a group by ID, name or code; the budget reads use
  the ID.

**Volume.** `test_consumer_list_volume` (`consumer`, `volume`): at scales 0.01 and 0.04 each of the
five reads executes the same statements (6–10) and loads at most 25 ORM rows. Full volume
(`volume_baseline.py --only-consumer --scale 1 --repeat 3`, warm median, after the container walk):

| Read | Time · statements · rows |
| --- | --- |
| First page of every item by rank (`sortBy`) | **478.9 ms** · 9 · 24 |
| Next cursor page (`sortBy`) | **2,571.4 ms** · 10 · 25 |
| Position jump to the middle (`sortBy`) | **690.4 ms** · 9 · 24 |
| 20,000 items under a parent (name order) | 7.4 ms · 6 · 24 |
| Ancestor filter with `includeTotal` (`sortBy`, 20,000 matches) | **147.7 ms** · 10 · 24 |

**Over budget: every read ordered by `sortBy`.** Cause (one `EXPLAIN ANALYZE` each): the per-type
list's attribute sort reads the value through correlated subqueries (`_attribute_scalar`), so no index
serves the order and each page computes them for all 100,000 items and sorts them (`top-N heapsort`
over a bitmap scan of the type). A cursor page is worse: its keyset predicate repeats the subquery
eight more times per row, and the backward probe for `prevCursor` runs a second full pass (1.1 s and
1.4 s). The plan's "joins the typed value, as the per-type list does" assumed a join; the live per-type
list uses subqueries. This is POSTGRESQL_BUDGETS E3 (sort by an attribute under the 20,000-child
parent, 104 ms) over a whole type instead of one parent, decided in Base 0.8 as D26 (an indexed sort
key per record, after 0.9). Not tuned in C3; the user chose an index on the values as its own package,
[C3a](#c3a-attribute-sorts-read-in-value-order), after a check of that route on the full-volume seed.

**Checks:** J28 and J25 on generated A and B (32 passed; after the container walk J28 again, 22).
Groups `consumer`, `queries`, `contract` and `volume` in parallel: 410 passed in 1 min 32 s
(`test_api_journeys` with the new route and codes, `test_boundaries`, the OpenAPI lock unchanged);
their serial part: 1 passed. Named risk from the volume model gaining a definition, the modules
outside these groups that load it: `test_model`, `test_restructuring_planner`, `test_type_changes`,
`test_restructuring_api`, 167 passed. `test_consumer_list_volume` after the walk change: passed.
`ruff check app/ tests/` clean. Not run: `startup` (no migration or startup path changed), the
frontend (unchanged), the full suites (R).

#### C3a: Attribute sorts read in value order

**Delivered 2026-10-04** ([record](#c3a-delivery-record)). **Planned 2026-10-04; decisions D46–D48 approved by the user the same day** (D47 with its context
work made a task of C6); test cases approved by the user the same day. An amendment raised by C3's full-volume budget: the user asked
on 2026-10-04 whether the sort could be solved in C3, route 1 below was checked once on the
full-volume seed, and the user agreed to a package of its own. **Needs:** C3. **Before:** C4.
**Groups:** `queries`, `consumer`, `volume`, `startup`, `contract`.

**Behaviour:** none changes. A list sorted by an attribute (a consumer list's `sortBy`, and the
management per-type list's `sort=<attribute>`, ascending or descending) answers the same rows in the
same order, with the same cursors, positions, seeks, totals and refusals. Records without a value
still come last in both directions. Only how the order is read changes: through an index in value
order, instead of computing every record's value and sorting the whole set on every page.

**Evidence (route 1, checked 2026-10-04 on a clone of the full-volume seed, 100,000 items with 1,000
distinct ranks, one index added in the clone, `EXPLAIN ANALYZE`):**

| Read | C3 today | Records with a value, through the index |
| --- | --- | --- |
| First page by rank | 479 ms | 1.0 ms |
| Next cursor page | 2,571 ms | 0.6 ms, and 0.5 ms for the backward probe |
| Ancestor filter, 20,000 items | 148 ms | 2.0 ms for the page |
| Position 50,000 | 690 ms | 94–102 ms |
| Total (`includeTotal`) | — | about 55 ms |

PostgreSQL walks the index in value order, reads each record by ID, sorts only within one value by
name (`Incremental Sort`) and stops at the page's end. Records without a value cannot share the
statement: one `UNION ALL` ordered as a whole sorts everything again (111–115 ms). Read on their own,
in name order with an anti-join, they cost 1 ms when such records exist and 56 ms when none does
(the anti-join has to see every record to find none).

**Design.**

- **Migration:** one index per typed value column of `attribute_values` that has none:
  `(attribute_type_key, <integer|decimal|boolean|date|datetime>_value, object_id)`. Text already has
  `ix_attribute_values_key_text`. JSON is not sortable.
- **Two parts, in order.** The live attribute sort becomes two parts: the records with a value,
  joined to their value and ordered by it (then name, then creation order), and the records without
  one, ordered by name (then creation order). `paginate_statement` gains a way to page parts read
  one after the other, as it gained `Overlay` for a base and its overlay: the keyset keeps the
  null-rank key, so a cursor names its part; a page read past the first part's end continues into the
  second; a position subtracts the first part's count when it lies beyond it; a total adds the
  parts' counts; `from=end` and backward reads start in the last part. Each part costs a fixed
  number of statements, so the budgets' statement counts stay constant.
- **Where:** in `object_query`'s live attribute sort (`LIVE_OBJECT_COLUMNS`), which the per-type
  list and the consumer lists share. The change set and publication contexts read
  `snapshot_attribute_values` and keep their sort until a package needs it (C6's publication-pinned
  lists, which then records its own budget); a relation list's attribute sort is unchanged.
- **Seek** by a value seeks in the first part; `seek` past every value lands at the second part's
  start, as today.

**Decisions (approved by the user, 2026-10-04):**

| # | Question | Decision |
| --- | --- | --- |
| D46 | Index the values or store a sort key per record (Base 0.8 D26)? | Index the values now (route 1): one migration, no write-path change, and the checked reads fall to 1–2 ms. 0.8 D26's stored key stays after 0.9 for what the index cannot serve: few distinct values (a boolean sorts a whole group of equal values by name, up to half the type, unchecked) and deep positions (about 100 ms at row 50,000, either way) |
| D47 | Which contexts | Live only, the contexts C3 reads. Change sets and publications are a task of C6, which reads publications through a consumer API (recorded in C6's row) |
| D48 | Which lists | The shared live attribute sort, so the management per-type list's attribute sort gains it too (POSTGRESQL_BUDGETS E3, 104 ms under the 20,000-child parent, expected to fall); not the ancestor sort (`ancestor:<type>`), which reads another table |

**Test cases** (approved; behaviour is unchanged, so they guard the change rather than fail first):

1. **J28.6 (unchanged)** already pages a `sortBy` list across both parts: by value, records without a
   value last, cursors both ways, `position`, `from=end`, `seek` and totals, on generated A and B.
2. **J21 (one new case): an attribute sort across both parts.** Given records of a type, some without
   the sorted attribute and some sharing a value. When the per-type list is read sorted by it,
   ascending and descending, with `pageSize=2`, to the end through `nextCursor`, back through
   `prevCursor`, at a position in each part, with `from=end`, a `seek` and `includeTotal`. Then each
   record appears once, by value then name, the records without a value last in both directions, and
   `totalCount` and `startIndex` follow. On two configurations.
3. **Unchanged, rerun:** `test_paging_contract` and `test_change_set_position_reads` (their
   `vol-rank` sorts), `test_volume_baseline` and `test_consumer_list_volume` (statements constant at
   two sizes; the parts may add statements once, not per row).
4. **Startup:** the existing `test_startup` cases cover the revision (clean start to `HEAD`, upgrade
   through every revision, restart). Creating indexes is transactional, so an interrupted run leaves
   the previous revision. One smoke start on a copy of the development database.

**Measurement:** once, warm, at full volume after the change (the seed rebuilds once for the
migration): `volume_baseline.py --only-consumer`, and the `children: heavy parent by rank` row of the
read table for E3. A read still over 100 ms is recorded with its cause, not tuned.

**Docs at delivery:** POSTGRESQL_BUDGETS (E3 restated or closed), ARCHITECTURE's list reading,
CHANGELOG, PROJECT_STATUS and TODO (C3's `sortBy` item closed or restated). No API or model contract
changes.

**Composable domains (ADR-032):** attribute storage gains indexes and keeps its shape; identity,
audit, the bulk APIs and the `match` declaration are untouched. No door closes.

##### C3a delivery record

**Delivered 2026-10-04.** What was built:

- **Migration** `20261004_04`: `ix_attribute_values_key_{integer,decimal,boolean,date,datetime}` on
  `(attribute_type_key, <typed value>, object_id)`, declared on `AttributeValue` as well.
- **Two parts** in `object_query._value_order_parts`: the live attribute sort's records with a value
  (joined to it, null rank constant 0) and without one (an anti-join, null rank constant 1), with the
  same key names, parse and format, so cursors, seek and positions are unchanged. `ObjectQuery.parts`
  carries them; `ObjectQuery.then_by_name` adds the consumer lists' name key to every part.
- **Paging in parts** in `paginate_statement(parts=…)`: a page reads the parts in turn (in reverse
  backward), a position skips a part whole by its count when the part returns nothing, a total and a
  start index add the parts' counts in one statement, and `seek` takes the part's keys. The per-type
  list, the relation matrix's rows and the consumer lists pass the parts.

**Differences from the plan:**

- **The containers are read first** (`consumer_parameters.below`), approved by the user after the
  closing measurement: with the value-order parts the ancestor filter with a total rose from 148 to
  215 ms, because PostgreSQL estimated the walk's recursive CTE at 953,267 rows when it held one
  group and hashed every rank value instead of walking the index. Reading the containers first and
  binding them as a list, as a search binds its candidates (`SEARCH_CANDIDATE_LIMIT`, past which the
  walk stays a subquery), brought it to 101 ms. One statement more for a parent or ancestor filter.
- **J21.9** is a new variant in USER_JOURNEYS (the plan said "one new J21 case"). It passed before
  the change, as planned: behaviour is unchanged.

**Measurement** (full volume, live, warm median of 3; before → after):

| Read | C3 | C3a |
| --- | --- | --- |
| Consumer: first page of every item by rank | 479 ms | 9.7 ms · 9 · 24 |
| Consumer: next cursor page | 2,571 ms | 11.9 ms · 11 · 25 |
| Consumer: position jump to the middle | 690 ms | **123.2 ms** · 9 · 24 (the deep-position limit D46 names) |
| Consumer: 20,000 items under a parent | 7.4 ms | 7.1 ms · 7 · 24 |
| Consumer: ancestor filter with `includeTotal` | 148 ms | **100.7 ms** · 11 · 24 |
| Per-type list: children of the heavy parent by rank (E3) | 104 ms | 9.9 ms · 9 · 84 |

The position jump and the ancestor filter with its total stay at or just over 100 ms and are
recorded, not tuned further (TODO). Relation lists by rank are unchanged (their sort is not C3a's).

**Checks:** J21 and J28 (42 passed; J21.9 on generated A and B). Groups `queries`, `consumer`,
`volume` and `contract` in parallel: 412 passed in 1 min 48 s, seeds rebuilt once for the migration;
their serial part with `startup`: 1 passed. `startup` (with `HEAD` at `20261004_04` in
`test_startup`: clean bootstrap, upgrade through every revision, restart, the refusals): 94 passed.
`matrix` (the relation matrix's rows take the parts): 116 passed. After the containers-first change:
J28 (22) and `test_consumer_list_volume` passed. Smoke start on a copy of the development database at
`20261004_01`: migrated to `20261004_04` with the indexes, healthy, restarted healthy, and an
attribute-sorted list read ascending, from the end and at a position; the copy and its log removed.
`ruff check app/ tests/` clean. Not run: the frontend (unchanged), the full suites (R).

#### C3b: Several values the standard way

**Delivered 2026-10-04** ([record](#c3b-delivery-record)). Planned 2026-10-04; the amended C-D32
approved by the user the same day, the test cases with the go-ahead to deliver. An
amendment reopening C3's C-D32: the `\,` escape recorded there was not approved by the user (they had
asked whether it was standard; it is not), and C4's C-D38 needs the rule settled. **Needs:** C3.
**Before:** C4. **Groups:** `consumer`, `contract`.

**Behaviour.** A consumer API parameter takes several values the way OpenAPI 3 serialises a list in a
query (`style: form`), built on RFC 3986:

- **repeated** (`token=A&token=B`, `explode: true`, OpenAPI's default), or
- **comma-separated** (`token=A,B`, `explode: false`), where the separating comma is a literal comma in
  the URL and a comma inside a value is percent-encoded as `%2C` (RFC 3986 §2.2: data that would
  conflict with a reserved delimiter is percent-encoded; OpenAPI's `allowReserved: false` default).

So `token=Bonds%2C%20Notes` is one value, "Bonds, Notes"; `token=Bonds,Notes` is two. An HTTP library
given the value "A,B" sends `A%2CB`, one value, which is the safe reading. A backslash has no meaning
(`\,` is gone). Both forms may be combined; values are alternatives, different parameters combine
with AND (unchanged). This applies to every definition parameter and a list's parent parameter, and to
XREF's `query` (C4), which keeps the reference's `query=a,b`.

**Design.** The split moves from the decoded parameters to the raw query string: the consumer router
reads `request.scope["query_string"]`, splits it on `&` and each pair on its first `=`, splits a value
on literal commas, and only then decodes each piece (`+` as a space and percent-escapes, as Starlette
decodes them). `consumer_parameters.split_values` is removed; the router's `_Parameters` holds the
split values. Single-valued names (`workspace`, the paging names) read the whole decoded value, as
today. No engine, model or migration change.

**Decision (approved by the user, 2026-10-04):**

| # | Question | Decision |
| --- | --- | --- |
| C-D32 (amended) | How a value holding a comma is written | Percent-encoded as `%2C`; a literal comma separates values; no escape character. The industry standard (OpenAPI 3 `form` with `explode: false`, RFC 3986), which every HTTP library already produces. Replaces C3's `\,` and `\\` |

**Test cases** (journey tests, J28.7 and J28.8 changed by this decision; the comma-separated cases are
written into the URL as a client types them, since an HTTP library percent-encodes a comma given inside
a value):

1. **J28.8 (changed): several values.** `token=Gold%20token,Bonds%2C%20Notes` keeps both `R`;
   `token=Bonds%2C%20Notes` keeps the one whose `K` is "Bonds, Notes"; `token=Bonds,Notes` (two values,
   neither a `K`'s name) keeps none; `token=Bonds\,%20Notes` keeps none (a backslash is no escape);
   repeated `token` values keep either, as before; `peer` and `token=Bonds%2C%20Notes` together keep
   the record both keep.
2. **J28.7 (changed): parent IDs.** North's and South's IDs as `ledger=<north>,<south>` written into the
   URL give all three `R2`, as repeated values do; the same two IDs sent through the HTTP library as
   one value "<north>,<south>" (encoded `%2C`) are one ID that is no record: `404 PARENT_NOT_FOUND`.

Confirmed failing before the change: case 1's `%2C` and backslash assertions and case 2's encoded
assertion. No unit tests: the split is what the journeys assert. **Checks:** J28 on generated A and B,
the `consumer` and `contract` groups, `ruff`.

**Docs at delivery:** API.md's parameter values; CONSUMER_API C-D32 amended (its record corrected:
the escape was not approved); C3's record and plan text; USER_JOURNEYS J28.8; CHANGELOG (C3's entry
corrected); TODO's item on commas in the management API's filters restated with the standard rule.

**Composable domains (ADR-032):** no door is affected; the change is how a request is read.

##### C3b delivery record

**Delivered 2026-10-04.** The consumer router splits the raw query string (`_listed_values`): on `&`,
each pair on its first `=`, each value on literal commas, and only then decodes each piece with
`unquote_plus`, as Starlette decodes its parameters. `consumer_parameters.split_values` is removed.
The journey harness gained `consumer_list_typed`, which sends a query exactly as typed: httpx, like
other HTTP libraries, percent-encodes a comma given inside a value (checked: `n1,n2` is sent as
`n1%2Cn2`), and given parameters it replaces a query written into the URL.

No difference from the plan. **Checks:** the changed J28.7 and J28.8 failed first on generated A and
B (4 failures: the encoded IDs were split, and "Bonds, Notes" as one value did not match); after the
change J28 passed (22). Groups `consumer` and `contract` in parallel: 186 passed (their serial part
selects none). `ruff check app/ tests/` clean. Not run: `volume` (the statements are unchanged, only
the request's reading), `startup` (no migration), the frontend, the full suites (R).

#### C4: XREF lookup and scoring

**Delivered 2026-10-05** ([record](#c4-delivery-record)). **Planned 2026-10-04; decisions C-D34–C-D41
and the test cases approved by the user the same day** (C-D37 with a documentation requirement; C-D38
after C3's escape was reopened as C3b). **Needs:** C2, and C3's
parameter check with C3b's value splitting. **Groups:** `consumer`, `queries`, `contract`, `volume`.

**Behaviour.** A consuming system finds business objects by what it knows, a code, an ID, a name or a
related record's value, and takes the best match:

```text
GET /api/consumer/{apiKey}/v{contractVersion}/xref?query=…&expect=any|one&pageSize=…&workspace=…
```

- **Candidates** are the live records of the exposed types in the workspace. Change sets are never
  read; `publication` arrives in C6, `asOf` in C16.
- **Terms.** `query` holds one or more terms, comma-separated or repeated, as C3b reads every list
  of values (a comma inside a term is `%2C`).
  An object's score is its best score over the terms (C-D38).
- **Own score for a term.** Each `match.own` rule compares the term with a field of the object: exact
  is equality ignoring case (typed fields by their parsed value), contains is a substring of a text
  field. The object's exact weights add up; its contains weights add up and count only when no exact
  weight applied (C-D35).
- **Promoted score.** Each `match.promoted` entry reads its projection's related records: each takes
  its first matching rule in `firstMatch` order and passes that weight to the exposed objects it is
  related to through the projection; with `preferTargetTypes`, a related record that relates to an
  object of a preferred type passes it only to those (C-D36). An object's score is the higher of its
  own and its best promoted score.
- **Order:** score, then the type's public name, then name, then object ID (CONSUMER_API's
  deterministic order). Each item is the shared object with `matchScore`.
- **`expect=any`** (the default) pages the results; **`expect=one`** answers the single top result,
  `404 NO_MATCH` when nothing matched and `409 AMBIGUOUS_MATCH` when the top score is shared (C-D40).
- **Definition parameters** answer `400 PARAMETER_NOT_SUPPORTED` until C5 applies them to XREF with
  `scoresFrom` (C-D33).

**Evidence (checked 2026-10-04 on a clone of the full-volume seed, nothing kept).** Read-time scoring
written directly in SQL over the existing indexes (the trigram indexes for contains and for exact
equality ignoring case, `ix_objects_id` for the ID), with the reference's weights: own rules ID 1000,
code 500/40, name 200/30; a promoted rule from items to the groups they cite, code 80, name 75, code
contains 10. One statement for the page, one for the count:

| Term | Matches | Page | Count |
| --- | --- | --- | --- |
| Exact item code, other case (`item-009905`) | 1 | 17.5 ms | 17.2 ms |
| Exact group code, promoted to 1,500 citing items | 1,501 | 17.3 ms | 14.6 ms |
| Contains, 4 characters (`0099`) | 231 | 12.5 ms | 11.4 ms |
| Contains, 3 characters (`099`) | 1,419 | 31.0 ms | 27.3 ms |
| Contains, 2 characters (`99`, no trigram) | 3,971 | 104.1 ms | 92.1 ms |
| Contains, in every record (`item`) | 100,000 | 475.2 ms | 289.0 ms |

Identifier lookups, promotion and selective contains stay well within 100 ms without a maintained
index. A term matching nearly every record does not, and a maintained match table would not change
that: its matches still have to be scored and sorted (C-D34, C-D37).

**Design.**

- **Route** `GET /{apiKey}/v{contractVersion}/xref` in `app/consumer/router.py`, with C3's parameter
  check: it serves `query`, `expect`, `workspace` and the paging names except `seek` and
  `includeTotal` (C-D39); definition parameters are known and not applied (C5).
- **Scoring** in `engine/reads/consumer_xref.py`, one statement: per term and rule, the matching
  records (`UNION ALL` of the own rules' matches, through the indexes a search uses, and the promoted
  rules' related records joined back to their owners through the projection's relation), the own and
  promoted scores per object, the best over terms. Python builds the statement from the definition;
  nothing is scored row by row in Python (AGENTS, set work in the database).
- **Broad terms** (C-D37): before scoring, one bounded statement counts the matches up to
  10,000 (`INDEXED_MATCH_LIMIT`), as a search reads its candidates; past it the request answers
  `400 QUERY_TOO_BROAD`, naming the limit. Contains needs 3 characters (`MIN_INDEXED_LENGTH`); a
  shorter term matches exactly only.
- **Paging** with `paginate_statement(rows=True)` over the scored rows, keyed by score (descending),
  public type name, name and object ID; the cursor binds the terms, the workspace and the contract
  version. The page is composed by C2's `ConsumerObjects`, with `matchScore` added.
- **Validation** (schema 0.8, not yet released): a `contains` weight on a field that holds no text
  (`id` or a typed attribute) is refused at `/consumerApis/<key>/match/…/contains`, since it could
  never match.
- **No migration.** The consumer index of CONSUMER_API's "Read index" is not built (C-D34).
  _Changed at delivery with the user's agreement:_ migration `20261005_01` adds `lower(…)` indexes
  for exact matches ([record](#c4-delivery-record)).

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D34 | A maintained consumer index (a match table per definition and workspace, updated in every live write and rebuilt on install), or scoring at read time? | Read time, over the existing indexes. The check above meets the budget for identifiers, promotion and selective contains; the maintained table would add write-path upkeep and a rebuild on every install, and would not serve a term matching everything either. Amends CONSUMER_API's "Read index". Revisit only on a measured need. **Approved 2026-10-04** |
| C-D35 | How own weights combine | Exact weights add up; contains weights add up and count only when no exact weight applied, as the reference does. **Approved 2026-10-04** |
| C-D36 | How promotion combines | A related record takes its first matching `firstMatch` rule and passes the weight to its owners through the projection; an owner's score is the higher of its own and its best promoted weight. `preferTargetTypes`: a related record relating to an owner of a preferred type passes its weight only to those owners. **Approved 2026-10-04** |
| C-D37 | Short and broad terms | Contains from 3 characters, the engine's search minimum; a shorter term matches exactly only (the 2-character case above cost 104 ms). A query matching more than 10,000 records answers `400 QUERY_TOO_BROAD`, a documented limit rather than a silent cap or a 0.5 s read. **Approved 2026-10-04, with a requirement:** both limits (3 characters for contains, 10,000 matches) must be stated very clearly in the user documentation: API.md, the per-definition OpenAPI (C6), CURRENT_FUNCTIONALITY and the error's own message |
| C-D38 | Terms | **Approved 2026-10-04, with C3b.** Comma-separated (a comma inside a term as `%2C`) or repeated `query`; empty terms dropped; no term is `400 QUERY_REQUIRED`; at most 100 terms (`400 TOO_MANY_TERMS`), as a request limit; the best score over the terms counts |
| C-D39 | Paging and the envelope | `{ "results": […], "query": [terms], "workspace", "pageSize", "nextCursor", "prevCursor", "anchor", "totalCount", "startIndex" }`. `totalCount` is always present, as in the reference: the scored set is counted anyway. Cursors both ways, `position` and `from=end`; `seek` (a score is not something a caller seeks) and `includeTotal` answer `400 PARAMETER_NOT_SUPPORTED`. **Approved 2026-10-04** |
| C-D40 | `expect=one` | The bare shared object with `matchScore`, as get by ID answers; `404 NO_MATCH`; `409 AMBIGUOUS_MATCH` with `details.candidates` (the tied objects' ID, public type, name and score, at most 10) and `details.count`. Paging names with `expect=one` answer `400 PARAMETER_NOT_SUPPORTED`. **Approved 2026-10-04** |
| C-D41 | `matchScore` | Every XREF result carries `matchScore`, an integer, after the declared fields; lists and get by ID do not. **Approved 2026-10-04** |

**Journey.** New: **J29 — Resolve a business object through a consumer API** (actor: consuming
system; channel: consumer API), in USER_JOURNEYS and API_JOURNEYS. Generated A and B's `Capi` gains a
`match`: own `id` 1000, `R.u` and `R2.u` 500/40, `name` 200/30; promoted over `B11` (`K.code` 80,
`name` 75, `K.code` contains 10) and over `Bscope` (`name` 60, `preferTargetTypes` `R2`). `Bscope`
gains a binding from `R2` to `D`, so a `D` can be watched by an `R` and an `R2`. The change rebuilds
the two seeds once.

**Test cases** (approved 2026-10-04; journey tests, written first and confirmed failing):

1. **J29 Scored lookup.** Given an `R` with `R.u` "LED-7", an `R2` named "Led" and an `R` named
   "Ledger seven". When `query=led-7` (another case), `query=Led` and `query=dger`. Then the first
   finds the `R` by its code with `matchScore` 500; the second ranks the `R2` (name exact, 200) above
   the records whose name or code contains it (30 or 40, the higher first); the third finds only by
   contains; ties order by public type name, then name; each result equals get by ID's answer plus
   `matchScore`.
2. **J29.1 Promoted matches.** Given an `R` paired (`B11`) with a `K` whose `K.code` is "TK-9", and a
   `D` named "Watch zone" watched (`Bscope`) by an `R` and an `R2`. When `query=tk-9`, and
   `query=Watch zone`. Then the `R` is found with 80; the `D` passes 60 to the `R2` only
   (`preferTargetTypes`); an object matching itself and through promotion keeps the higher score.
3. **J29.2 Several terms.** `query=LED-7,TK-9` and the same as two `query` parameters find both, each
   with its best score; a `K` named "Bonds, Notes" pairing an `R` is matched by `Bonds%2C%20Notes`.
4. **J29.3 `expect=one`.** A unique code answers the bare object with `matchScore`; no match answers
   `404 NO_MATCH`; two records with the same name answer `409 AMBIGUOUS_MATCH` naming both;
   `expect=one&pageSize=5` answers `400 PARAMETER_NOT_SUPPORTED`.
5. **J29.4 Paging.** Given seven records containing a term. With `pageSize=3`: to the end and back
   through the cursors, `position=3`, `from=end`; `totalCount` 7 and `startIndex` on every page; a
   cursor sent with another `query` answers `400 INVALID_CURSOR`.
6. **J29.5 Refusals.** No `query` or only empty terms: `400 QUERY_REQUIRED`; 101 terms:
   `400 TOO_MANY_TERMS`; a definition parameter, `seek` or `includeTotal`:
   `400 PARAMETER_NOT_SUPPORTED`; a two-character term matches exactly only.
7. **J25 (changed):** a `contains` weight on `id` or on an integer attribute is refused at its
   `/match/…/contains` pointer.

`QUERY_TOO_BROAD` is asserted by the volume module (case 8): the journey seeds stay far below 10,000.

8. **Volume.** `test_consumer_xref_volume` (`consumer`, `volume`); the volume definition gains a
   `match` (ID, code, name; promoted through the items' citations). At 0.01 and 0.04, the same
   statements for: an exact code, a promoted group code, a 4-character contains, `expect=one`, and a
   term matching every item refused as `QUERY_TOO_BROAD`. Timed once at full volume with
   `volume_baseline.py --only-consumer` against the 100 ms budget.

No unit tests: the scoring rules' edge cases are what J29 asserts, and term splitting is C3's.
**Checks:** J29 and J25 on generated A and B; the groups `consumer`, `queries`, `contract`
(`test_api_journeys`, `test_boundaries`) and `volume` (the new module); `ruff`. No migration, so no
`startup`.

**Docs at delivery:** API.md gains XREF; CONSUMER_API records C-D34–C-D41 and amends the XREF
endpoint text and "Read index"; USER_JOURNEYS adds J29, API_JOURNEYS the route and codes; APPLICATION_MODEL
notes the `contains` rule; CURRENT_FUNCTIONALITY and PRODUCT describe looking up an object by code.

**Composable domains (ADR-032):** the `match` declaration is read as declared and gains only the
`contains` validation; identity, attribute storage, audit and the bulk APIs are untouched. A product
catalogue's lookup by SKU or name is this route, so the door is exercised, not narrowed.

##### C4 delivery record

**Delivered 2026-10-05.** What was built:

- **Route** `GET /{apiKey}/v{contractVersion}/xref` in `app/consumer/router.py`. The parameter check
  now takes the names each route serves (`_OBJECT`, `_LIST`, `_XREF`, `_XREF_ONE`); every name a
  route serves is known on all of them, so `query` or `expect` on get by ID or a list is
  `400 PARAMETER_NOT_SUPPORTED` rather than `UNKNOWN_PARAMETER`, the existing rule for a known name.
- **Scoring** in `engine/reads/consumer_xref.py`: a select per term, rule and weight (exact or
  contains), combined in one statement: own hits summed per object and term (C-D35), promoted hits
  reduced to each related record's first rule with `DISTINCT ON`, passed through the projection's
  relation with a window for `preferTargetTypes` (C-D36), the maximum per object, ranked by score,
  public type name (a `CASE` over the definition), name and ID. Terms are trimmed and empty ones
  dropped (`xref_terms`). Paging is `paginate_statement(rows=True)`, total always on; the shared
  object is C2's `ConsumerObjects` with `matchScore` added. `expect=one` reads the top 11 rows and
  counts the tie only past 10.
- **Broad terms:** one statement before scoring counts the distinct records the terms match (own
  matches and the related records promotion reads), each select bounded at 10,001, so a common term
  costs no more than the limit; past 10,000 the request is `400 QUERY_TOO_BROAD` naming both limits.
- **Validation:** a `contains` weight on `id` or a typed attribute is refused at
  `/consumerApis/<key>/match/…/contains`.
- **Migration** `20261005_01` (not in the plan; see below): `ix_objects_workspace_lower_name` on
  `objects (workspace_key, lower(name))` and `ix_attribute_values_key_lower_text` on
  `attribute_values (attribute_type_key, lower(text_value))`, declared in the ORM; exact text matches
  compare `lower(column) = lower(term)` through them.
- **Fixtures:** generated A and B's `Capi` has the planned `match` and `Bscope` an `R2`→`D` binding;
  the volume definition gains a `citedGroups` projection (items to the groups they cite) and a
  `match` (ID 1000, code 500/40, name 200/30; promoted code 80, name 75, code contains 10).

**Differences from the plan:**

- **The migration.** The first full-volume run put lookups at 49–72 ms but the too-broad refusal of
  "item" at 317 ms. Its cause: an exact match ignoring case, read through the trigram index, rechecks
  every record containing the term (~50 ms per rule on 100,000 records). Leaving out exact selects a
  contains select covers brought it to 157 ms. Asked how to close, the user chose the `lower(…)`
  indexes within C4 (2026-10-05); with them the counting shortcut was removed again as unnecessary.
- **The refusal stays over budget, recorded** with the user's agreement: 116 ms, chiefly the
  promoted "group code contains" rule, whose trigram candidates are all 100,000 item codes before the
  type filter drops them (TODO). Closing it needs the record type in the value index.
- **Volume test limit.** The test shapes hold at most 4,000 items, below 10,000, so
  `test_consumer_xref_volume` lowers the limit to 500 to assert the refusal's statements; the
  full-volume run meets the real limit.
- **Added:** `400 INVALID_EXPECT` for an `expect` other than `any` or `one` (no approved case covers
  it); trimming spaces around terms.

**Budgets at full volume** (`volume_baseline.py --only-consumer --scale 1 --repeat 3`, warm median ·
statements · ORM rows; the last column after the migration):

| Request | First run | Without `lower()` indexes, exact covered | Delivered |
| --- | --- | --- | --- |
| An item's code, another case | 56.1 ms | 43.2 ms | 34.1 ms · 7 · 3 |
| A group's code promoted to its 1,500 citing items | 71.8 ms | 63.3 ms | 53.2 ms · 8 · 3 |
| 4-character contains (`0099`) | 49.3 ms | 42.5 ms | 57.5 ms · 7 · 3 |
| `expect=one` | 55.1 ms | 42.8 ms | 35.6 ms · 7 · 3 |
| A term in every item, `QUERY_TOO_BROAD` | **316.8 ms** | **157.2 ms** | **115.7 ms** · 3 · 3 |

The delivered run followed a seed rebuild, and its contains figure is the only one that rose (the
first rounds after a rebuild read cold, POSTGRESQL_BUDGETS). C3's list scenarios in the same runs
match C3a's figures with one statement more each, for the new projection.

**Checks:** J29 (12 cases on generated A and B) and the new J25 case confirmed failing first (no
route; the validation missing), then passing. Groups `consumer`, `queries` and `contract` in
parallel after the last change: 389 passed in 1 min 3 s (their serial part selects none).
`test_consumer_xref_volume`: equal statements at 0.01 and 0.04 (7–8 per lookup, 3 for the refusal),
rows within budget. `startup` with `HEAD` at `20261005_01` (clean bootstrap, upgrade through every
revision, restart, the refusals): 94 passed. `test_schema_drift` passed, and it names the new index
when it is dropped from a clone (checked once). The development database was migrated to
`20261005_01` by the user's own `uvicorn --reload` when the migration appeared, and serves healthy
with both indexes; a copy of it started healthy twice and answered the XREF route; the copy and its
log removed. `ruff check app/ tests/` clean. Not run: the frontend (unchanged), the full suites (R).

#### C5: XREF parameters

**Planned 2026-10-05; decisions C-D42–C-D46 and the test cases approved by the user the same day.**
**Needs:** C4, and C3's parameter predicates. **Groups:** `consumer`, `contract`, `volume`.

**Behaviour.** A consuming system narrows a lookup by what else it knows: the type it expects, the
codelist or region a value belongs to, the system whose code it holds. XREF takes the definition's
parameters, as get by ID and the lists have since C3:

```text
GET /api/consumer/{apiKey}/v{contractVersion}/xref?query=…&{parameters}&expect=any|one&pageSize=…&workspace=…
```

- **Every parameter kind** (`objectType`, `ancestor`, `related` through a projection, `self` or a
  shared projection, and `projection`) applies to XREF with C3's meaning and C3b's values: several
  values of one parameter are alternatives, different parameters combine with AND.
- **Filters act on the scored objects** (C-D42), as the reference applies them after scoring: an object
  is a result when it scored and every parameter keeps it. `totalCount`, the pages, and `expect=one`'s
  top result and tie all follow the narrowed set, so a parameter can resolve an `AMBIGUOUS_MATCH`.
- **`projection` parameters** limit that projection's items in each result, as on a list; with
  `requireMatch` they also drop the objects left with none.
- **`scoresFrom`** (C-D43): a `projection` parameter declaring it also limits which related records
  pass scores. In every `match.promoted` entry over its projection, only the related records the
  parameter matches pass their weight to their owners. The objects' own scores are untouched, and
  `preferTargetTypes` chooses among the owners of the records that pass. Without the parameter in
  the request, it has no effect. This is the reference's `system`: "also limits which system values
  score".
- **Unchanged:** the broad-term limit counts what the terms match before parameters (C-D44); a list's
  parent parameter on XREF stays `400 PARAMETER_NOT_SUPPORTED`; an unknown `objectType` value answers
  `400 UNKNOWN_OBJECT_TYPE`, as on lists.

**Design.**

- **Route:** `get_xref` drops `filters=False` from `_Parameters.check`, so definition parameters are
  applied rather than refused, and builds `consumer_filter` as the other routes do.
- **Filter:** `ConsumerFilter` gains `scoring`, projection name to a predicate on the related record.
  `consumer_filter` fills it from the `projection` parameters that declare `scoresFrom`, using the item
  predicate `limits` already holds; several over one projection combine with AND.
- **Scoring** (`engine/reads/consumer_xref.py`): `_Scoring` takes the filter.
  - `ranked()` adds `filter.on(RdmObject)` to the join of the best scores to the records. The
    predicates read at most the scored rows, which the count before scoring bounds at 10,000.
  - `_passed()` joins each best hit's related record and applies the projection's `scoring`
    predicate before the hit passes to its owners.
  - `matched_count` is unchanged (C-D44).
- **Composition:** `read_xref` passes the filter to `ConsumerObjects.compose`, so projection limits
  shape the results as on lists.
- **Paging:** the cursor binds every parameter's values with the terms, the workspace and the
  contract version, as the list cursor does, so a cursor sent with other parameters is
  `400 INVALID_CURSOR`.
- **Validation** (schema 0.8, not yet released): `scoresFrom` on a parameter whose projection no
  `match.promoted` entry reads, or in a definition without `match`, is refused at
  `/consumerApis/<key>/parameters/<name>/scoresFrom` (C-D45).
- **Contract:** `output_contract` records each `projection` parameter's `scoresFrom`, so turning it on
  or off is `version_required`, reported at `/parameters/<name>/scoresFrom` (C-D46).
- **No migration and no new index.** Basis, not yet measured: the filters run on at most 10,000 scored
  rows, and their candidate reads are C3's, which hold the list budgets. Timed once at delivery
  (case 5).

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D42 | Where parameters act in XREF | An object is a result when it scored and every parameter keeps it. A parameter is a condition on the object itself, so applying it before or after scoring gives the same results: an object's score does not depend on which other objects are kept. Only where it is evaluated differs: once on the scored objects (at most 10,000, bounded by C-D44's count) rather than repeated in every rule's select per term and weight. The one parameter effect that must act before scoring, on the related records, is `scoresFrom` (C-D43). `totalCount`, paging and `expect=one` (top and tie) follow the narrowed set; `projection` limits and `requireMatch` act as on lists (C-D31); the cursor binds the parameter values. **Approved 2026-10-05**, on the understanding that filtering first would not shrink the work: the terms' matches are read either way (C-D44), and what scoring adds over them is small. That is reasoning, not a measurement; the delivery's volume timing (case 5) checks it, and a filter that proves slow after scoring is reported with its cause |
| C-D43 | What `scoresFrom` does | When the request gives a `scoresFrom` parameter, only the related records it matches pass weights in the promoted entries over its projection. Own scores are untouched. `preferTargetTypes` picks among the owners of passing records. Several `scoresFrom` parameters over one projection: a record must match each one (AND, as limits combine). Without the parameter in the request, no effect. **Approved 2026-10-05** |
| C-D44 | Does a parameter bring a broad term under the 10,000-match limit? | No. The limit counts what the terms match, before parameters, as delivered in C4. It bounds the work of reading a term's matches, and a filter applied to 100,000 matches still reads them; counting after parameters would need every predicate in every rule's bounded count, an unmeasured cost. The limit's text stays literally true ("the query matches more than 10,000 records"). API.md states that parameters do not count towards it. **Approved 2026-10-05** |
| C-D45 | `scoresFrom` that could never act | Refused at `/consumerApis/<key>/parameters/<name>/scoresFrom` when no `match.promoted` entry reads the parameter's projection, or the definition has no `match`, as C4 refused a `contains` weight on a field with no text. **Approved 2026-10-05** |
| C-D46 | Is `scoresFrom` part of the contract? | Yes. It changes which objects score under the parameter, so it changes ranking, for C-D4's reason (weights are contract). Turning it on or off is `version_required`. `requireMatch` and `matchFields` stay as C-D18 left them. **Approved 2026-10-05** |

**Journey.** J29 gains variants J29.6 and J29.7, and its status drops "definition parameters on XREF
follow in C5". USER_JOURNEYS and API_JOURNEYS add the parameters on XREF. Generated A and B's `Capi`
gains one parameter, `watchRegion` (`projection` over `Bscope`, matching `ancestor:G.name`,
`scoresFrom`, no `requireMatch`), a `Capi.…` key. `Bscope` already has a promoted entry (`name` 60,
preferring `R2`). A promoted entry over `Bown`, where `permit` sits, would change J29.1's scores, since
every `D` has an owning `R` through `Bown`. The change rebuilds the two seeds once.

**Test cases** (approved 2026-10-05; journey tests, written first and confirmed failing):

1. **J29.6 Parameters narrow XREF.** Given an `R` and an `R2` both named "Twin", and records matching
   "Twin" by contains: an `R` paired (`B11`) with a `K` named "Coin", an `R` with a permit in `G`
   "North", and a `D` under an `M` named "Yard".
   - `kind` with `R`'s public name keeps only the `R`s, and `totalCount` follows. An unknown name
     answers `400 UNKNOWN_OBJECT_TYPE`.
   - `container=Yard` keeps the `D`. `token=coin` (another case) keeps the paired `R`. `peer` keeps
     through `self` and the shared `Bscope`.
   - `permitRegion=North` keeps the `R` with a North permit and limits its `permits` to North's.
   - Two parameters keep what both keep. Each kept result has the score it has without parameters.
   - `query=Twin&expect=one` answers `409 AMBIGUOUS_MATCH`; with `kind` naming `R2`'s public name, it
     answers the `R2`.
   - A cursor sent with another `kind` answers `400 INVALID_CURSOR`. A list's parent parameter answers
     `400 PARAMETER_NOT_SUPPORTED`.
2. **J29.7 `scoresFrom`.** Given two `D`s named "Gate zone", one below `G` "North" and one below "South".
   An `R2` "North watcher" watches (`Bscope`) the North one, an `R2` "South watcher" the South one, and
   an `R2` named "Gate zone" watches the South one.
   - `query=Gate zone` finds both `D`s and the `R2` named "Gate zone" (200 each, own), and both
     watchers (60, promoted).
   - With `watchRegion=North`: the North watcher keeps 60, and its `watchedPermits` holds only the
     North `D`. The South watcher is absent. The `D`s and the `R2` named "Gate zone" keep 200, since
     own scores are untouched and no `requireMatch` drops them.
3. **J29.5 (changed):** a definition parameter is no longer `PARAMETER_NOT_SUPPORTED` on XREF; a list's
   parent parameter, `seek` and `includeTotal` still are.
4. **J25 (changed):** `scoresFrom` on a parameter over `Bown` (no promoted entry) is refused at its
   `/parameters/<name>/scoresFrom` pointer; turning `watchRegion`'s `scoresFrom` off is reported as
   `version_required`.
5. **Volume.** `test_consumer_xref_volume` gains two scenarios. The volume definition gains a
   `projection` parameter over `citedGroups` by code with `scoresFrom` (rebuilding the volume seeds
   once):
   - the cited group's code with the ancestor parameter on the heavy group (a filter over the 1,500
     promoted items);
   - the same code with the new parameter on that group (the `scoresFrom` path).

   Both must execute the same statements at 0.01 and 0.04. Each is timed once at full volume with
   `volume_baseline.py --only-consumer` against the 100 ms budget. A read over budget is reported
   with its cause, not tuned in a loop.

No unit tests: the kinds' edge cases are C3's journeys, and what C5 adds (where filters act,
`scoresFrom`) is what J29.6 and J29.7 assert. **Checks:** J29, J28 (the shared filter) and J25 on
generated A and B; the groups `consumer`, `contract` (`test_api_journeys`, `test_boundaries`) and
`volume` (the changed module); the modules that load the volume model, as C3 named them (`test_model`,
`test_restructuring_planner`, `test_type_changes`, `test_restructuring_api`); `ruff`. No migration, so
no `startup`. Not `queries`, since `object_query` is unchanged.

**Docs at delivery:** API.md's XREF section gains the parameters and `scoresFrom`, states that
parameters do not count towards the 10,000-match limit (C-D44), and drops "until C5" from
`PARAMETER_NOT_SUPPORTED` and the parameter notes. CONSUMER_API records C-D42–C-D46, amends the XREF
endpoint text and marks the C5 row delivered. APPLICATION_MODEL notes the `scoresFrom` rule.
USER_JOURNEYS and API_JOURNEYS update J29. CURRENT_FUNCTIONALITY describes narrowing a lookup.

**Composable domains (ADR-032):** the `match` and `parameters` declarations are read as declared and
gain only the `scoresFrom` rule and its contract entry. Identity, attribute storage, audit and the
bulk APIs are untouched. A product catalogue's lookup of a SKU within a category (an `ancestor`
parameter) or of a supplier's code (a `projection` parameter with `scoresFrom`) is this route, so the
door is exercised, not narrowed. Crosswalk (C15) and batch resolve (C14) build on the same filter.

##### C5 delivery record

**Delivered 2026-10-05**, as designed. The route applies the definition's parameters
(`_Parameters.check` lost its `filters` switch, which no route needs any more); `ConsumerFilter`
gained `scoring`; `_Scoring.ranked()` filters the scored objects and `_passed()` joins each best hit's
related record to the `scoresFrom` predicate; `read_xref` composes with the filter and binds the
parameter values into the cursor. `scoresFrom` is validated at its pointer (C-D45) and recorded in
`OutputContract.scores_from`, a change reported at `/parameters/<name>/scoresFrom` (C-D46). Generated
A and B's `Capi` gained `watchRegion` (`Capi.watch`); the volume definition gained `cites`
(`projection` over `citedGroups` by code, `scoresFrom`). No migration.

**Differences from the plan:** none in behaviour. J29.5's case now sends the list parent parameter
where it sent `token`, and asserts that `token` is applied.

**Budgets at full volume** (`volume_baseline.py --only-consumer --scale 1 --repeat 3`, after the seed
rebuild, warm median · statements · ORM rows):

| Request | Time |
| --- | --- |
| A group's code, within the heavy group (ancestor filter over the promoted items) | 56.7 ms · 9 · 3 |
| A group's code, `scoresFrom` on the group | 60.9 ms · 8 · 3 |
| C4's lookups in the same run (code, promoted code, contains, `expect=one`) | 29.0–50.0 ms |
| C4's too-broad refusal (recorded over budget in C4) | 107.6 ms |

Both new reads hold the 100 ms budget, which bears out C-D42's reasoning: filtering after scoring
added 7–11 ms over the unfiltered promoted lookup. C3's list figures match C3a's and C4's.

**Checks:** the J29.5–J29.7 and new J25 cases confirmed failing first (8 failures:
`PARAMETER_NOT_SUPPORTED` on XREF and the missing validation), then J25, J28 and J29 passing on
generated A and B (52). Groups `consumer` and `contract` in parallel after the last change: 191 passed
in 24 s, `test_consumer_xref_volume` among them (equal statements at 0.01 and 0.04, 8–9 per narrowed
lookup); their serial part selects none. The modules that load the volume model (`test_model`,
`test_restructuring_planner`, `test_type_changes`, `test_restructuring_api`) and
`test_consumer_api_model`: 254 passed. `ruff check app/ tests/` clean. Not run: `startup` (no
migration), `queries` (`object_query` unchanged), the frontend (unchanged), the full suites (R).

#### C14: Batch resolve

**Delivered 2026-10-05** ([record](#c14-delivery-record)). **Planned 2026-10-05; decisions C-D47–C-D53
and the test cases approved by the user the same day** (the full-volume timing of case 6 cleared to
run once; the contains reads, the index and the budgeted batches changed at delivery with the user).
**Needs:** C4, C5 (the parameters items carry). **Groups:** `consumer`, `contract`, `volume`.

**Behaviour.** A flow translating a file of codes resolves them in one call instead of one XREF
request per row ([CONSUMER_API "Batch resolve"](CONSUMER_API.md#batch-resolve)). It is a read: POST
only carries the list, and nothing changes.

```text
POST /api/consumer/{apiKey}/v{contractVersion}/resolve?workspace=…
{ "defaults": { "codelist": "Currency" },
  "items": [ { "ref": "row-1", "query": "CHF" },
             { "ref": "row-2", "query": ["EUR", "Euro"], "codelist": "Legacy" },
             { "ref": "row-3", "id": "7f3c…" } ] }
```

- **Each item** is resolved exactly as `xref?expect=one` (by `query`) or get by ID (by `id`), with
  its own parameters over `defaults`. Scoring, parameters (C5, `scoresFrom` included), tie rules and
  the per-item limits (100 terms, 10,000 matches, 3 characters for contains) are XREF's.
- **Each outcome** is the single read's answer for that item, in item order: `found` with the
  object, or `not_found`, `ambiguous` or `rejected` with the error the single read answers (C-D48).
- **The batch** holds at most 1,000 items, a setting reported by capabilities; over it the request is
  `413 BATCH_TOO_LARGE` and nothing is resolved (C-D13, C-D50).
- **Not yet:** `publication` (C6), `asOf` (C16) and `to.{parameter}` (C15) arrive with their packages,
  for every item at once; until then they are refused as on the other consumer routes today.

**Evidence (checked 2026-10-05 on a clone of the volume seed at 10,000 items, the trigram and
`lower(…)` indexes added to match the current schema; nothing kept).** C4's scoring rewritten as one
statement over a terms relation `(item, term)`, each rule's match joined per term (`LATERAL`, bounded
at 10,001 as C4's count is), with the volume weights (ID 1000, code 500/40, name 200/30; promoted
group code 80, name 75, code contains 10). Terms: item codes in another case, every tenth a group code,
every fiftieth a miss.

| Items | Every rule | Exact rules only |
| --- | --- | --- |
| 1 | 3.5 ms | — |
| 100 | 161 ms | — |
| 1,000 | 1,480 ms | 35 ms |

- **One statement, not one per item.** Repeating XREF per item would cost C4's 34–57 ms per lookup
  at full volume, 35–57 s for 1,000. The set statement's cost grows with the items only through the
  per-term index reads.
- **Contains is 97 % of the cost.** Each term runs three trigram probes (code contains, name contains,
  promoted code contains), 0.3–0.5 ms each here. A trigram probe reads posting lists that grow with
  the data, so at 100,000 items this is likely several seconds per 1,000 items (not measured; the
  full-volume seed is not built). The exact rules read B-tree indexes and stay at 35 ms.
- **Bounding each probe is required.** Unbounded, PostgreSQL flattened the name-contains join into
  1,000 × 11,000 comparisons (5.5 s); with the bound it probes the index per term.

**Design.**

- **Route** `POST /{apiKey}/v{contractVersion}/resolve` in `app/consumer/router.py`. The query string
  serves `workspace` only; a definition parameter there is `400 PARAMETER_NOT_SUPPORTED` (it belongs
  in `defaults`). The body is checked as a whole first (C-D49), then the item count (C-D50).
- **One scoring path** (C-D51). `_Scoring` takes a terms relation `(item, term)` instead of literal
  terms, and `read_xref` becomes a batch of one item, so XREF and batch resolve cannot drift apart.
  Typed terms are parsed in Python into one column per value type; contains arms skip terms shorter
  than 3 characters; every per-term arm is a bounded `LATERAL`.
- **Groups.** Items are grouped by their effective parameters (defaults overlaid with the item's),
  since a `ConsumerFilter` is built per parameter set. Each group runs the same statements for all its
  items, so the statements grow with the distinct parameter sets, not with the items.
- **Exact first** (C-D52). Per group: one statement scores every item with the exact rules and counts
  their matches; an item whose top is decided by them is answered from that. Only the items left
  undecided run the full C4 scoring with contains, in one more statement and its bounded count.
  "Decided": the top score is above the most any contains match can give (the sum of the own contains
  weights, or the highest promoted contains weight), and every object at the top score got it from
  an own exact rule or from a promoted rule with no contains weight earlier in `firstMatch`. Then no
  contains match can reach, raise or break the top, and the result equals full scoring.
- **Ranking per item** with `row_number()` over `(item)` in C4's order, the top 11 rows per item read,
  ties counted only past 10, as C4's `expect=one`.
- **By ID**: one `ConsumerObjects.compose` per group over its by-ID items (C-D31's filtering of a set
  of one, for many). **Composition** of the found objects: one `compose` per group, `matchScore`
  added to the XREF items.
- **Setting** `CONSUMER_RESOLVE_MAX_ITEMS` (default 1,000) in `app/config.py`; `GET /capabilities`
  gains `consumerApi: { resolveMaxItems, setting }` (C-D50).
- **No migration and no new index.** _Changed at delivery with the user's agreement:_ migration
  `20261005_02` adds a trigram index on names holding the workspace and type ([record](#c14-delivery-record)).

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D47 | The request | Body `{ "defaults": {…}, "items": [ … ] }`. An item has an optional `ref` (1–200 characters, as P2), exactly one of `query` or `id`, and definition parameters by name (`ref` and `id` are already reserved names, C1). `query` and every parameter value are a string or an array of strings: JSON carries a list itself, so no comma splitting (C-D32 is how a URL lists values; `"Bonds, Notes"` is one term). An item's parameter replaces the default of the same name, not merged. The query string carries only `workspace` (later `publication`, `asOf`) |
| C-D48 | The outcome | `{ "items": [ { "index", "ref", "status", "object" or "error" } ], "workspace", "counts": { "found", "notFound", "ambiguous", "rejected" } }`, in item order, unpaged (the batch is bounded), named `items` as the integration API's outcomes (P2). `found` carries the single read's body (with `matchScore` for a query). The other statuses carry the single read's error, code, message and details unchanged: `not_found` is `NO_MATCH` or `OBJECT_NOT_FOUND`, `ambiguous` is `AMBIGUOUS_MATCH` with its `candidates` and `count`, `rejected` is the single read's `400` code with `details.pointer` into the item. So "equal to the single read" is checkable item by item. A processed batch answers `200` whatever its outcomes |
| C-D49 | Request or item refusal | Refused as a whole (`400`, nothing resolved): a body that is not the documented shape (not JSON, `items` missing or empty, an item or value of the wrong JSON type), an unknown or unapplied name in `defaults` (every item would fail), a definition parameter in the query string, an unknown workspace (`404`). Rejected per item: both or neither of `query` and `id`, an unknown or unapplied name in the item (`expect`, paging names), and every refusal XREF or get by ID gives an item (`QUERY_REQUIRED`, `TOO_MANY_TERMS`, `QUERY_TOO_BROAD`, `UNKNOWN_OBJECT_TYPE`) |
| C-D50 | The limit | 1,000 items (C-D13), `CONSUMER_RESOLVE_MAX_ITEMS`, reported by `GET /capabilities` as `consumerApi.resolveMaxItems`; over it `413 BATCH_TOO_LARGE` with `details.setting`, `maximum` and `items`, B1's code and shape. No byte limit of its own: the item and term limits bound the work. The per-definition OpenAPI (C6) states the maximum |
| C-D51 | One scoring path | XREF becomes a batch of one item, as single writes became batches of one in PG3b: one implementation, so batch resolve equals `xref?expect=one` by construction. Items are grouped by their effective parameters, one set of statements per group. Basis: the table above. Cost: C4's and C5's XREF statements change and are re-timed against 100 ms at delivery (case 6). A batch whose every item has different parameters runs one group per item, close to a loop; per-item parameters inside one statement would mean rewriting C3's parameter predicates to read values from a relation, recorded in TODO for a measured need |
| C-D52 | Exact first, and C-D37 for `expect=one` | Score exact rules first and run contains only for the items they leave undecided (the rule in "Design"). Basis: exact rules 35 ms, contains 1,445 ms of 1,480 for 1,000 items; a file of codes is mostly exact hits. **Amends C-D37 for `expect=one`** (XREF and batch alike, one path): an item decided by its exact matches is answered without reading contains matches, so a contains term matching more than 10,000 records no longer refuses it; the limit still applies to the exact matches, and to contains when it is read. `expect=any` is unchanged, since it pages every match |
| C-D53 | The budget | A batch of 1,000 identifiers (codes, IDs, exact names; misses included) with at most 10 distinct parameter sets: **1 s** at full volume, beside B1's 1,000 upserts at 0.8 s. Recorded, not budgeted: 1,000 terms that all need contains, and 1,000 items with distinct parameters. Meeting the budget confirms C-D13's 1,000. A read over it is reported with its cause, not tuned in a loop |

**Journey.** J29 gains variants J29.8–J29.10 (batch resolve) in USER_JOURNEYS and API_JOURNEYS
(the route, `BATCH_TOO_LARGE` on the consumer tier); J29.3 notes C-D52. No fixture change: generated
A and B's `Capi` exercises both evaluation paths, since a code or name hit (500, 200) is above its
largest contains sum (110), while a promoted hit (80, 60) is not. The volume definition is unchanged.

**Test cases** (journey tests, written first and confirmed failing):

1. **J29.8 A mixed batch.** One batch holding J29's lookups as items: a code in another case, a
   name, a promoted code, two terms in one item, a `Bonds, Notes` term as one string, an object ID,
   an unknown ID, a miss and the two records sharing a name. Then: outcomes in item order with
   `index` and `ref`; each `found` equals the `xref?expect=one` (or get by ID) body; each `not_found`
   and `ambiguous` equals that read's `404` or `409` error; `counts` add up.
2. **J29.9 Defaults and item parameters.** `defaults` `kind` with `R`'s public name narrows every
   item; an item giving `kind` with `R2`'s replaces it; an item resolving the "Twin" `409` with
   defaults alone is `found` with its own `kind`; a by-ID item filtered out by `container` is
   `not_found`; `watchRegion` (`scoresFrom`) in `defaults` gives J29.7's scores.
3. **J29.10 Refusals.** Per item, `rejected` with the single read's code and a pointer into the item:
   both `query` and `id`; neither; `expect`; `pageSize`; an unknown name; an empty term list; 101
   terms. As a whole: an unknown name in `defaults`, a definition parameter in the query string
   (`400`), an unknown workspace (`404`), and, with the limit set to 5 for the test, 6 items
   (`413 BATCH_TOO_LARGE` naming the setting). `GET /capabilities` reports the limit.
4. **J25:** unchanged (no model rule is added).
5. **Volume.** `test_consumer_xref_volume` gains batch scenarios at 0.01 and 0.04: 10 and 100 items
   (codes, promoted codes, misses, a contains-only term) execute the same statements at both scales
   and both sizes; 100 items over 3 parameter sets execute three groups' statements. With the match
   limit lowered as in C4, an `expect=one` decided by an exact code is answered while a contains term
   in it matches past the limit, and an undecided item is `rejected` `QUERY_TOO_BROAD`.
6. **Timed once at full volume** (`volume_baseline.py --only-consumer`; no full-volume seed exists on
   the server now, so the run builds one and is announced with its expected time first): the C-D53 batch against 1 s; the two recorded
   batches; C4's and C5's lookups again against 100 ms, since their path changed (C-D51).

No unit tests beyond the decided rule: one unit test of the "decided" predicate over weights (own
contains sum, a promoted contains before an exact rule), since journeys reach only the generated
weights. **Checks:** J29, J28 and J25 on generated A and B; the groups `consumer`, `contract`
(`test_api_journeys`, `test_boundaries`, the capabilities lock) and `volume` (the changed module);
`tests/unit/test_config.py`; `ruff`. No migration, so no `startup`; not `queries` (`object_query`
unchanged).

**Docs at delivery:** API.md gains batch resolve and the capability, and amends XREF's `expect=one`
limit text (C-D52); CONSUMER_API records C-D47–C-D53, amends "Batch resolve" and C-D37, and marks the
C14 row delivered; OPERATIONS adds `CONSUMER_RESOLVE_MAX_ITEMS`; USER_JOURNEYS and API_JOURNEYS add
J29.8–J29.10; CURRENT_FUNCTIONALITY describes resolving many values in one call.

**Composable domains (ADR-032):** no model change; batch resolve reads the `match` and `parameters`
declarations as XREF does. Identity, attribute storage, audit and the bulk APIs are untouched. A
product catalogue's translation of a supplier's SKU file is this route, so the door is exercised, not
narrowed. Crosswalk (C15) adds `to.{parameter}` to items on the same path.

##### C14 delivery record

**Delivered 2026-10-05.** What was built:

- **Route** `POST /{apiKey}/v{contractVersion}/resolve` in `app/consumer/router.py`: the URL serves
  `workspace` only (`_Parameters.check(..., applies_definition=False)`); the body is read whole and
  checked by `_resolve_items` (shape `400 REQUEST_VALIDATION_ERROR` with a pointer, `413
  BATCH_TOO_LARGE`, names in `defaults`), each item's own names, `query`/`id` and terms becoming
  that item's refusal (C-D47, C-D49, C-D50).
- **Batch** in `engine/reads/consumer_resolve.py`: items grouped by their effective parameters, one
  `consumer_filter`, one `resolve_lookups` and one `ConsumerObjects.compose` per group; outcomes
  carry the single read's body or error, a rejection's `path` turned into a pointer into the item
  or `defaults` (C-D48). Get by ID's refusal is shared (`consumer_objects.object_not_found`).
- **One scoring path** (C-D51) in `engine/reads/consumer_xref.py`: the terms of every lookup are a
  relation bound as arrays; exact matches of every term are one `LATERAL` select per rule; contains
  matches are one bounded select per term and rule with the pattern bound; `tops()` answers each
  lookup's matched count and top 11 rows (with the tie size and whether it is safe) in one
  statement. `read_xref`'s `expect=one` is `resolve_lookups` for one lookup; `expect=any` pages the
  same scored statement.
- **Exact first** (C-D52): `contains_ceiling` and `safe_positions` decide whether the exact rules
  settle a lookup; the unsettled ones are scored with every rule, at most 200 contains terms to a
  statement (`CONTAINS_TERMS_PER_STATEMENT`).
- **Migration** `20261005_02` (not in the plan; see below): the `btree_gin` extension and
  `ix_objects_type_name_trigram` (GIN over workspace, type and `name gin_trgm_ops`), declared in
  the ORM. Startup now requires and creates both `pg_trgm` and `btree_gin`, refusing with one
  message naming the missing ones.
- **Setting** `CONSUMER_RESOLVE_MAX_ITEMS` (1,000), reported by `GET /capabilities` as
  `consumerApi`. `UNKNOWN_OBJECT_TYPE` names its parameter in `details.path`.

**Differences from the plan** (each decided with the user on 2026-10-05):

- **Contains reads per term.** The first full-volume run put single XREF over budget (85–131 ms)
  and contains-only batches at 31 ms per item. Cause: a pattern read from the terms relation is
  planned as matching ~1,300 records, so each probe intersected the type index and hash-joined every
  record (19.6 ms against 3.4 ms with the pattern bound). Contains matches are now one select per
  term with the pattern bound; exact matches stay one `LATERAL` per rule.
- **The index.** The user chose trigram indexes holding the key columns as well (`btree_gin`). Measured: the
  name index reads as fast as a bound pattern and stays; the same index on attribute values made
  PostgreSQL underestimate a term matching every value and read them all in one process (the
  too-broad refusal 181 ms against 127 ms without it), for about 1.5 ms per ordinary probe, and was
  dropped. The development database, migrated by the user's `uvicorn --reload` while the migration
  still held both indexes under earlier names, was brought to the delivered schema by hand
  (two renames, then the value index dropped); it serves healthy.
- **The budgeted batches** (C-D53 restated with the user): the first run's identifier batch made a
  tenth of its items the group code 1,500 items cite (970 ms of exact scoring) and applied
  parameters that filtered most items off their own match. The budgeted batches now send lookups
  that fit their parameters, with ordinary group codes; those two batches are recorded, not
  budgeted.
- **Test data:** J29.9's by-ID item is filtered out by `container` with no matching M (the
  definition's parameter, no M created).
- **Added:** `QUERY_OR_ID_REQUIRED`; `consumerApi` in J20's capability groups.

**Budgets at full volume** (`volume_baseline.py --only-consumer --scale 1 --repeat 3`, after the seed
rebuild, warm median · statements · ORM rows):

| Request | Budget | Time |
| --- | --- | --- |
| 1,000 identifiers (codes, group codes, IDs, misses, one contains term) | 1 s | **816.5 ms** · 7 · 3 |
| 1,000 items over three parameter sets, each fitting its set | 1 s | **451.2 ms** · 18 · 3 |
| 1,000 identifiers, a tenth the group code 1,500 items cite | recorded | 1,703.1 ms · 7 · 3 |
| 1,000 identifiers over three sets regardless of fit | recorded | 3,996.8 ms · 19 · 3 |
| 1,000 contains-only terms | recorded | 15,441.3 ms · 9 · 3 |
| 1,000 items, each its own parameter value | recorded | 38,418.1 ms · 4,002 · 3 |
| XREF: code, promoted code, contains, `expect=one` | 100 ms | 35.4, 54.4, 65.4, 13.3 ms |
| XREF: within the heavy group, `scoresFrom` | 100 ms | 64.1, 59.2 ms |
| XREF: a term in every item, too broad (over budget since C4) | recorded | 147.1 ms |

The 1,000-identifier batch confirms C-D13's maximum. A contains read costs 3–5 ms per term and rule
at full volume however it is written, so contains-heavy batches take seconds; a batch with a
parameter set per item runs four statements per item (TODO). The too-broad refusal is 147 ms against
C4's 116 ms and C5's 108 ms: both code-contains reads of a term in every item join all 100,000
matching values before their limit stops them (TODO, beside C4's entry).

**Checks:** J29.8–J29.10 confirmed failing first (no route), then J29 (22 on generated A and B).
After the last change: groups `consumer` (129, the volume module and the new unit tests among them),
`startup` (95: clean bootstrap, upgrade through every revision to `20261005_02`, restart, the
extension refusals, schema drift) in parallel, their serial parts selecting none; before the index
change, `contract` (66, the OpenAPI lock re-baselined: removing `consumerApi` gives the previous
document exactly), `queries` (232) and `test_search_index` (4), which the dropped index does not
touch. `test_consumer_xref_volume`: equal statements for 10 and 100 items at both sizes; an
`expect=one` settled by its exact code answered while its contains term matches past the lowered
limit. `ruff check app/ tests/` clean. The development database at `20261005_02` serves healthy
and answers the route. Not run: the frontend (unchanged), the write budgets with the new index
(`budget`, at R), the full suites (R).

#### C14a: Repeated lookups resolved once; the batch profiled

**Delivered 2026-10-05**, asked for by the user after C14 ("can these times be made significantly
shorter?"). **Needs:** C14. **Before:** C15, whose crosswalk items take the same path.

**Built.** `read_resolve` resolves each distinct lookup of a parameter group once: a lookup is its
set of terms (order and repeats do not change a score), and every item that sent it takes its
answer. A file of codes repeats its values, and the fan-out batch sent one heavy lookup 100 times.
J29.8 gains the case: the same lookup sent again, reordered and repeated, has the same answer and
the same ambiguity.

**Profile at full volume** (one run, warm median of three; statements in order: the exact rules, the
contains reads of the unsettled lookups, the records and values, the projection, the ancestors):

| Batch | Wall | SQL | Statements (ms) |
| --- | --- | --- | --- |
| 1,000 identifiers (899 found, 100 not found, 1 ambiguous) | 764 ms | 319 ms | 21.5 · 78.9 · 19.6 · 7.1 · **191.6** |
| Three parameter sets | 455 ms | 290 ms | two groups' ancestor walks 87.3 and 86.0 ms, the rest 2–39 ms |
| Cited group fan-out (C14: 1,703 ms) | 804 ms | 299 ms | 31.0 · 74.7 · 19.9 · 6.7 · 166.7 |

- **The ancestor walk** of the composition (`ConsumerObjects._ancestors`, shared with lists and get by
  ID) is the largest statement: PostgreSQL estimates the recursive walk at 54,540 rows for 540, so
  both its step and the final join hash all 257,758 records. C3a met the same estimate in
  `consumer_parameters.below` and bound the walked rows as a list.
- **Outside SQL**, about 445 ms for 900 objects (composition in Python, encoding the response); not
  yet split.

**Checks:** J29 (22 on generated A and B), `test_consumer_xref_volume` (3), `ruff` clean. Not
run: the rest of `consumer` (its other modules unchanged), the full suites (R).

#### C14b: The ancestor walk and the contains selects made cheap

**Delivered 2026-10-05**, on C14a's profile, with the user's agreement. **Needs:** C14a. **Before:** C15.

**Built.**

- **Ancestor walk** (`ConsumerObjects._ancestors`, shared by get by ID, lists, XREF and batch
  resolve): the walk reads its IDs in one recursive statement, each step finding the parent through a
  `LATERAL` bounded at one row (PostgreSQL flattened an unbounded one back into a join), then the
  records and their values are read by the bound list of IDs, as `consumer_parameters.below` reads
  walked containers since C3a. Before, one statement estimated the walk at 54,540 rows for 540 and
  hashed all 257,758 records and values: 170–192 ms, now 5.1 + 5.4 ms. Each read that composes
  ancestors runs one statement more.
- **Contains selects** read `objects` and `attribute_values` unaliased: each is a subquery of its
  own, and aliasing both tables for each of 313 terms made SQLAlchemy build 6,444 column objects,
  0.47 s of the request, now under 0.1 s.

**Full volume** (one run, warm median of three · statements · ORM rows):

| Request | Budget | C14 | Now |
| --- | --- | --- | --- |
| 1,000 identifiers | 1 s | 816.5 ms | **235.7 ms** · 8 · 3 |
| 1,000 items over three parameter sets | 1 s | 451.2 ms | **227.8 ms** · 21 · 3 |
| Cited group fan-out (C14a: repeated lookups once) | recorded | 1,703.1 ms | 264.8 ms · 8 · 3 |
| Parameters filtering items out | recorded | 3,996.8 ms | 2,431.3 ms · 22 · 3 |
| Contains only (C14a: its 1,000 terms are 100 distinct ones) | recorded | 15,441.3 ms | 1,021.1 ms · 5 · 3 |
| A parameter set per item | recorded | 38,418.1 ms | 35,921.1 ms · 4,002 · 3 |
| XREF lookups (code, promoted, contains, `expect=one`, narrowed, `scoresFrom`) | 100 ms | 13.3–65.4 ms | 14.5–64.8 ms |
| XREF too broad | recorded | 147.1 ms | 145.3 ms |
| Consumer lists (C3a's figures) | 100 ms | 7.9–113.6 ms | 7.5–111.9 ms |

The identifier batch now spends 179 ms in SQL, chiefly the unsettled lookups' contains statement
(98 ms, of which 25 ms executing and the rest planning its 313 selects); the contains-only figure falls
by C14a's deduplication, not cheaper reads. The position jump and the ancestor filter with its total
stay at the budget line, as C3a recorded them.

**Checks:** group `consumer` after the last change: 129 passed (J28, J29 and
`test_consumer_xref_volume`, equal statements at both sizes, among them); `ruff` clean. Not run:
`queries` (no shared code changed), the full suites (R).

#### C15: Crosswalk

**Delivered 2026-10-05** ([record](#c15-delivery-record)). **Planned 2026-10-05; decisions C-D54–C-D58 and the test cases approved by the user the same day**
(no volume case, as proposed).
**Needs:** C5 (the projection limits and `scoresFrom` a target sits beside), C14 (batch items carry
it), C14b. **Groups:** `consumer`, `contract`.

**Behaviour.** "Code X in system A: what is it in system B?" A consuming system holds one
representation of a business object and needs another: a system's code for another system, a value's
translation in another language ([CONSUMER_API "Crosswalk"](CONSUMER_API.md#crosswalk)). It is one
read, not a lookup followed by a get:

```text
GET …/xref?query=CHF&system=SAP&to.system=Oracle&expect=one
GET …/objects/{id}?to.language=es
GET …/lists/{listKey}?…&to.system=Oracle
POST …/resolve   { "defaults": { "system": "SAP", "to.system": "Oracle" }, "items": [ … ] }
```

- **`to.{parameter}`** names a `projection` parameter the definition declares `"targetable": true`,
  with a value matched by that parameter's `matchFields`. It applies to XREF, get by ID, lists and
  batch resolve (in `defaults` and in an item).
- **The plain parameter still decides** matching, scoring and which objects are kept: `system=SAP`
  keeps its `requireMatch` and `scoresFrom` meaning. `to.system` changes no object, score, order,
  total or tie (C-D54).
- **The output:** the projection shows the target items (those matching `Oracle`) instead of the
  plain parameter's, and each object carries them again as `target`, after its declared fields and
  before `matchScore` (C-D54).
- **One object, one target:** where the read answers one object (XREF `expect=one`, get by ID, a
  batch item), `target` is one item, and it must be unique: none is `404 TARGET_NOT_FOUND`, several
  are `409 AMBIGUOUS_TARGET`, each naming the object found. On a page (XREF `expect=any`, lists)
  `target` takes the projection's shape and nothing is refused (C-D55).
- **One target per read** (C-D56); a `to.` name for anything but a targetable parameter is
  `400 UNKNOWN_PARAMETER` (C-D57).
- The engine treats neither systems nor translations specially: any targetable `projection`
  parameter crosswalks.

**Design.**

- **Names** (`app/consumer/router.py`): `_Parameters.check` and `_resolve_items` know `to.<name>` for
  each targetable parameter and apply it where the definition's parameters apply. Several `to.` names
  refuse the read, or in batch resolve the item (or the request, when in `defaults`). The values are
  split as C3b splits a parameter's values (several values are alternatives).
- **Filter** (`engine/reads/consumer_parameters.py`): `ConsumerFilter` gains `target`: the parameter
  name, its projection and the item predicate, built by `_Builder.projection` as a limit is.
  `consumer_filter` sets the projection's limit to the target predicate AND the limits of the other
  parameters over that projection, leaving out the targeted parameter's own limit (else `SAP` AND
  `Oracle` would leave nothing). `records` and `scoring` are built as now, so the plain parameter's
  `requireMatch` and `scoresFrom` are untouched.
- **Composition** (`ConsumerObjects.compose`): with a target, each object gets `target`: the limited
  projection's items, in the projection's shape. No statement is added: the target is the limit
  `_related` already applies in its select.
- **Uniqueness** (one function beside `object_not_found`, used by `read_consumer_object`,
  `read_xref`'s `expect=one` and `read_resolve`): after the object is decided, the projection's
  items decide `target`: one is the item, none `TARGET_NOT_FOUND`, several `AMBIGUOUS_TARGET`. In a
  batch the item's status follows the error's status, as C-D48 maps every error (`not_found`,
  `ambiguous`), with `details.pointer` to the item's or `defaults`' `to.` name.
- **Grouping and paging:** batch items group by their effective parameters, `to.` included, so the
  statements still grow with the parameter sets. The list and XREF cursors do not bind `to.` values,
  since they change no row or order.
- **Contract** (`engine/model/consumer_contract.py`): `OutputContract` records the targetable
  parameters; turning `targetable` off is `version_required` at `/parameters/<name>/targetable`,
  turning it on is not (C-D58).
- **Validation:** none added. `targetable` exists only on a `projection` parameter (schema 0.8,
  `extra="forbid"`), `to.` is a reserved name prefix and `target` a reserved output name since C1.
- **No migration, no index, no new setting.**

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D54 | What `to.{p}` does | **Approved 2026-10-05.** The projection over which `p` is declared shows the items `to.{p}` matches, AND the limits of any *other* parameters over that projection; `p`'s own limit is replaced, not combined (`system=SAP&to.system=Oracle` would otherwise show nothing). The same items are added as `target` after the declared fields, before `matchScore`. `p`'s `requireMatch` and `scoresFrom` act as without the target, and `to.{p}` may be sent without `p`. It keeps and drops no object and changes no score, order, `totalCount` or tie: CONSUMER_API's "the plain parameter still decides matching and scoring". So the cursors do not bind it |
| C-D55 | `target`'s shape, and where it must be unique | **Approved 2026-10-05.** A read that answers one object (XREF `expect=one`, get by ID, a batch item) answers one target: `target` is the item, `404 TARGET_NOT_FOUND` with none, `409 AMBIGUOUS_TARGET` with several. Details: the object's `id` and `objectType`, the `parameter`, and for the ambiguity `count` and `targets` (the items as projected, at most 10, as `AMBIGUOUS_MATCH`'s candidates). The object is decided first: a shared top score stays `409 AMBIGUOUS_MATCH` even if only one candidate has a target, since the target does not decide matching. A page (XREF `expect=any`, lists) refuses nothing: `target` takes the projection's shape (an array, or an object or `null` for a projection of one), empty where an object has no target. Codes in upper case (C-D25), amending CONSUMER_API's `target_not_found` and `ambiguous_target`. Get by ID is one object, so it is counted with `expect=one`; CONSUMER_API named only `expect=one` and batch resolve |
| C-D56 | Several targets in one read | **Approved 2026-10-05.** One `to.` name per read; a second is `400 MULTIPLE_TARGETS` naming both (in batch resolve: the item rejected, or the request when both are in `defaults`; an item's `to.` name replaces a different one from `defaults` rather than adding a second). `target` is then one field, as CONSUMER_API's text has it. Several *values* of one `to.` name are alternatives (C3b), so `to.system=Oracle,SAP` is allowed and with `expect=one` is ambiguous when both exist. A consumer needing two representations makes two reads or batches |
| C-D57 | A `to.` name that cannot target | **Approved 2026-10-05.** `to.<name>` exists only for a targetable parameter. Any other `to.` name, of an unknown, non-projection or non-targetable parameter, is `400 UNKNOWN_PARAMETER` (C3's code and shape), its message naming the targetable parameters. In batch resolve, per C-D49: in an item it rejects the item, in `defaults` the request |
| C-D58 | Is `targetable` part of the contract? | **Approved 2026-10-05.** Yes, as a capability consumers call: turning it off is `version_required` at `/parameters/<name>/targetable` (a consumer's `to.` read would start failing); turning it on adds a capability and needs no new version, as adding a field does not (C-D2) |

**Journey.** J29 gains variants J29.11–J29.14 (crosswalk) in USER_JOURNEYS and API_JOURNEYS (the
`to.` name on every route, `TARGET_NOT_FOUND`, `AMBIGUOUS_TARGET`, `MULTIPLE_TARGETS`). Generated A
and B's `Capi` declares `watch` and `permit` targetable. `watch` (over `Bscope`) gives the cases:
`Bscope` from `R2` to `D` has no scope rule, so an `R2` can watch two `D`s in one `G`. `permit`
(over `Bown`) is needed only as a second targetable parameter for `MULTIPLE_TARGETS`, and `token`
(`related`) is the non-targetable name. The change rebuilds the two seeds once. The volume definition
is unchanged.

**Test cases** (journey tests, written first and confirmed failing):

Given an `R` "Ledger X" (code `LX`) watching (`Bscope`) a `D` below `G` "North" and a `D` below
"South"; an `R` "Ledger Y" (`LY`) watching only a North `D`; an `R2` "Entry Z" (`EZ`) watching two
`D`s below "South".

1. **J29.11 Crosswalk with `expect=one`.**
   - `query=LX&to.watchRegion=South&expect=one` answers Ledger X with `target` the South item; its
     `watchedPermits` holds only that item, and `matchScore` is the one without `to.`.
   - `watchRegion=North&to.watchRegion=South` on `LX` gives the same answer: the plain parameter does
     not limit the output when the target is given.
   - `LY` answers `404 TARGET_NOT_FOUND` naming Ledger Y; `EZ` answers `409 AMBIGUOUS_TARGET` naming
     Entry Z, with `count` 2 and both items; `to.watchRegion=North,South` on `LX` is
     `409 AMBIGUOUS_TARGET`.
   - Two records sharing a name, only one with a South target: `409 AMBIGUOUS_MATCH`.
2. **J29.12 Pages and get by ID.** Get by ID of Ledger X with `to.watchRegion=South` has `target` the
   item; of Ledger Y, `404 TARGET_NOT_FOUND`; of Entry Z, `409 AMBIGUOUS_TARGET`. The list `all`
   (every `R`) with `to.watchRegion=South` keeps every ledger with the same `totalCount`, each
   `target` an array (Ledger Y's empty); a cursor from the page without `to.` reads the next page
   with it. XREF `expect=any` for a term both ledgers match: both, same scores and order.
3. **J29.13 Batch resolve.** `defaults` `to.watchRegion=South`; items `LX`, `LY`, `EZ`, Ledger X by ID,
   and `LY` with its own `to.watchRegion=North`: `found` (with `target`), `not_found`
   (`TARGET_NOT_FOUND`), `ambiguous` (`AMBIGUOUS_TARGET`), `found`, `found`; each outcome equals the
   single read's answer, with `counts` adding up.
4. **J29.14 Refusals.** `to.token` and `to.nothing` are `400 UNKNOWN_PARAMETER`;
   `to.watchRegion=South&to.permitRegion=North` is `400 MULTIPLE_TARGETS`. In batch resolve, the same
   in an item rejects that item with a pointer into it, and `to.token` in `defaults` refuses the
   request.
5. **J25 (changed).** A candidate release turning `targetable` off for `watchRegion` is reported
   `version_required` at `/parameters/<name>/targetable`; one turning it back on needs no new
   version. `targetable` on the `ancestor` parameter `container` is refused at its pointer: C1's
   schema, asserted here, not expected to fail first.

No unit tests: the target adds no logic with edge cases beyond what J29.11–J29.14 walk. No volume
case: the target is the projection limit C3 already applies in the same select, so it adds no
statement. That is the design's reasoning, not a measurement; a `test_consumer_xref_volume` batch
with `to.` would check it, at the cost of the volume definition and seeds rebuilt once, and is left
out unless the user asks for it. **Checks:** J29, J28 and J25 on generated A and B; the
groups `consumer` and `contract` (`test_api_journeys`, `test_boundaries`, the OpenAPI lock, which
should not change, since the consumer routes are outside the management document); `ruff`. No
migration, so no `startup`; not `queries` (`object_query` unchanged), not `volume`.

**Docs at delivery:** API.md gains crosswalk on the four routes and the three codes; CONSUMER_API
records C-D54–C-D58, amends "Crosswalk" (codes in upper case, get by ID with `expect=one`, the
replaced limit) and marks the C15 row delivered; APPLICATION_MODEL notes `targetable` in the
contract; USER_JOURNEYS and API_JOURNEYS add J29.11–J29.14; CURRENT_FUNCTIONALITY describes
translating a value from one representation to another in one read. C6's per-definition OpenAPI
then describes `to.` names and `target` (noted for C6).

**Composable domains (ADR-032):** the `match` declaration is untouched; the `parameters`
declaration gains `targetable`'s contract entry. Identity, attribute storage, audit, the bulk APIs
and mapping coverage are untouched. A product catalogue's "our SKU in the supplier's numbering" is a
targetable `projection` parameter over the supplier links, so the door is exercised, not narrowed.

##### C15 delivery record

**Delivered 2026-10-05**, as designed, with the decisions C-D54–C-D58 and the approved cases.

- **Names** (`app/consumer/router.py`): `to.<name>` is known and applied for each targetable
  parameter on get by ID, lists and XREF, and in batch resolve's `defaults` and items (in the URL of
  batch resolve it is `PARAMETER_NOT_SUPPORTED`, as a definition parameter is). An unknown `to.` name
  answers `UNKNOWN_PARAMETER` naming the targetable ones; a second is `MULTIPLE_TARGETS`
  (`details.parameters`, and the `path` or `pointer` of the second). An item's `to.` name drops the
  defaults' one.
- **Filter** (`consumer_parameters.py`): `consumer_filter` takes the `to.` value with the
  parameters; `ConsumerFilter.target` names it and its projection, and the projection's limit is the
  target's items AND the other parameters' limits over it, the targeted parameter's own left out.
  `records` and `scoring` are built as before. `without_target` keeps `to.` values out of the list
  and XREF cursors.
- **Composition and uniqueness** (`consumer_objects.py`): `compose` adds `target` (the limited
  projection, in its shape) after the declared fields; `one_target` turns it into the single item or
  refuses, for get by ID, XREF `expect=one` and each batch item, where `item_error` points the
  refusal at the `to.` name in `defaults` or the item. No statement is added.
- **Contract** (`consumer_contract.py`): `OutputContract.targetable`; turning it off is
  `version_required` at `/parameters/<name>/targetable`.
- **Differs from the plan:** J25's last case found a defect, not expected: a shape error inside a
  typed union was reported at a path holding Pydantic's tag (`…/parameters/zone/ancestor/targetable`,
  and for views and panels `…/views/1/tree/config/pageSize`), a node the document does not have, so
  the model draft editor's "go to path" could not find it. `compiler.document_location` leaves the
  tag out (a segment before the last that is no key of its object but one of its values), with a
  unit test (`tests/unit/engine/model/test_compiler.py`, mapped to `model` in `UNIT_GROUPS`). Three
  older `test_model.py` cases (13 parametrised) pinned the tagged path and now assert the document's
  pointer. Shape errors still locate a list item by position (`/consumerApis/0/…`), as before.
- **Docs:** API.md (the Crosswalk section, the codes on the parameters and batch resolve tables),
  CONSUMER_API (C-D54–C-D58, "Crosswalk" amended, C15 delivered), APPLICATION_MODEL, USER_JOURNEYS and
  API_JOURNEYS (J29.11–J29.14), CURRENT_FUNCTIONALITY; C6's row notes the `to.` names for its OpenAPI.

**Checks:** the new journey cases failed first (8 crosswalk, 2 J25), then pass;
`pytest -n auto -m "consumer or contract or model"` 407 cases, 394 passed and 13 failed on the
older tagged-path assertions, which were then updated: `tests/test_model.py` 123 passed; J25, J28
and J29 68 passed; the serial part of those groups is empty; `ruff check app/ tests/` clean. Not run:
`volume` (no statement added, the design's reasoning, not measured), `queries` (`object_query`
unchanged), `startup` (no migration), the full suites (R).

#### CN1: The consumer API's name in public contracts

**Planned 2026-10-05; C-D59 decided by the user the same day (no new field).** Amends C2–C5, C14,
C15 and the designs of C6, C9–C11 per [U-D1](SETTINGS_AND_UI_PLAN.md#decisions).
**Needs:** C15. **Groups:** `consumer`, `contract`.

**Behaviour.** An integrator reading the consumer API's documentation sees the definition's name
written as `consumerApi` everywhere it appears: the route `/api/consumer/{consumerApi}/v{contractVersion}/…`,
and, once C6 and C11 build them, the API index entries, the subscription filter and body, and the
webhook and event bodies. Nothing reads as a credential. The model keeps `key`, as every model
element does, and the error codes stay (`CONSUMER_API_NOT_FOUND` already says it).

**What carries it today** (checked 2026-10-05):

- **On the wire: nothing.** No response field, error detail or query parameter carries the name.
  `CONSUMER_API_NOT_FOUND` has no `details`, and `CONTRACT_VERSION_NOT_FOUND`'s `details` holds only
  `contractVersion`. The consumer router is left out of OpenAPI (`include_in_schema=False`), so the
  path parameter's name (`api_key`) is invisible to clients. The SETTINGS plan's line that "the route
  and error details carry it" is wrong about error details. It is corrected with this package.
- **In the code:** the path parameter `api_key` on the four routes (`app/consumer/router.py`) and
  `consumer_definition(model, api_key, …)` (`engine/reads/consumer_objects.py`), plus docstrings in
  the router, `models/schema.py` and the journey helpers (`tests/journeys/scenario.py`, J28.4's text).
  The frontend has no occurrence.
- **In the documents:** API.md (four route lines, the `CONSUMER_API_NOT_FOUND` row), CONSUMER_API
  (25: the Security note, the section "The `apiKey`", the endpoint list, the API index, subscriptions,
  webhook bodies, the events route, C-D1 and C-D18), APPLICATION_MODEL, USER_JOURNEYS, API_JOURNEYS,
  PROJECT_STATUS and TODO.

So CN1 changes no response. Its value is that C6 (the API index), C9–C11 (events, subscriptions)
and V2 (the per-definition OpenAPI) are built from designs that already say `consumerApi`, and that
the route documentation reads correctly before C6 publishes it in OpenAPI.

**Design.**

- **Code:** the path parameter becomes `consumer_api` on the four routes, so C6's OpenAPI would
  show `{consumer_api}` if a route were ever included as is. V2's document writes paths literally
  (SETTINGS plan, "Versions in the documentation"), so no placeholder appears there either way.
  `consumer_definition` takes `consumer_api`. Docstrings say `{consumerApi}`. Error messages keep
  their wording ("Consumer API 'x' not found"). The internal cursor scope
  `consumer-list:<key>:<listKey>` is not public and stays.
- **Living documents:** every occurrence above becomes `consumerApi` (route placeholder `{consumerApi}`).
  CONSUMER_API's section is renamed "The consumer API name (`consumerApi`)", keeps its points (not a
  credential, model-key format, stable across versions, several per model) and its examples table,
  and its anchor link from the Security note follows. The planned contracts change field for field:
  the API index entry's `apiKey` → `consumerApi`; `GET /api/v1/consumer-subscriptions?consumerApi=…`;
  the subscription body's `"consumerApi": "rdm"`; both webhook bodies and the events route. C-D1 and
  C-D18 keep their decisions with the new word.
- **History stays as written.** Delivery records (C2–C15 in this plan) and released CHANGELOG
  entries describe what was delivered under the old name; they are not rewritten. CHANGELOG
  Unreleased gains one entry. This plan's undelivered text (the queue row, C6's row) uses the new
  name.
- **Same word, other contract:** `GET /api/v1/capabilities` already has a `consumerApi` group
  (`{"resolveMaxItems": 1000, "setting": …}`), an object describing the consumer API capability. The
  new field is a string naming one definition, in other routes. The shapes differ and neither
  document defines both, so both stay.
- **No model change, no migration, no new error code.**

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| C-D59 | Should the two not-found errors gain `details.consumerApi`? | **Decided 2026-10-05 by the user: no.** U-D1 renames the field where it is carried, and no error carries it. Adding it would be a new field, not a rename. The caller sent the name in the URL. No not-found error in the engine echoes the identifier it was given (`OBJECT_NOT_FOUND`, `MODEL_RELEASE_NOT_FOUND`, `ATTRIBUTE_NOT_FOUND` carry no `details`). `CONTRACT_VERSION_NOT_FOUND`'s `details.contractVersion` is different: it tells the caller something new, the version that is served. The SETTINGS plan's "error details" is corrected to "the route" |

**Journey.** No journey changes behaviour. USER_JOURNEYS (J28, J29) and API_JOURNEYS (the four
consumer route rows) change only the placeholder. `test_api_journeys` reduces every `{…}` to `{}`
before it compares routes, so the inventory check is unaffected.

**Test cases:** none new. A journey test asserts what a user sees, and what a user sees does not
change, so no case can fail first. Existing cases show that the renamed path parameter still routes
every request: J28 (get by ID, lists, J28.4's `CONSUMER_API_NOT_FOUND` and
`CONTRACT_VERSION_NOT_FOUND`) and J29 (XREF, batch resolve, crosswalk) on generated A and B. J28.4's
docstring says "an unknown consumer API name".

**Checks:** J28 and J29 (`--journey`); the `contract` group's `test_api_journeys` and
`test_boundaries`; `ruff check app/ tests/`. Not run: `volume` (no statement changes), `startup`
(no migration), `queries`, the frontend (unchanged), the full suites (R). A final
`grep -rn "apiKey\|api_key"` over `backend/app`, `backend/tests` and the living documents lists
only history (delivery records, released CHANGELOG entries) and the U-D1 text that records the
rename.

**Docs at delivery:** listed under Design. SETTINGS_AND_UI_PLAN marks CN1 delivered and corrects
"the route and error details". CONSUMER_API records C-D59. PROJECT_STATUS and TODO drop "CN1 comes
before C6".

**Composable domains (ADR-032):** a rename in documentation and internal names. The `match`
declaration, identity, attribute storage, audit, the bulk APIs and mapping coverage are untouched.
No door is affected.

##### CN1 delivery record

**Delivered 2026-10-05**, as designed, with C-D59 (no new field).

- **Code:** the four consumer routes take `consumer_api` (`app/consumer/router.py`), as does
  `consumer_definition` (`engine/reads/consumer_objects.py`); the docstrings in the router,
  `models/schema.py`, `tests/journeys/scenario.py` and J28.4 say `{consumerApi}`. Error codes,
  messages and `details` are unchanged.
- **Docs:** API.md (route lines, the `CONSUMER_API_NOT_FOUND` row); CONSUMER_API (the Security note,
  "The consumer API name (`consumerApi`)" with its anchor, the endpoint list, the API index,
  subscriptions, both webhook bodies, the events route, C-D1, C-D18, and C-D59 recorded);
  APPLICATION_MODEL, USER_JOURNEYS, API_JOURNEYS, PROJECT_STATUS, TODO, CHANGELOG (Changed); the
  SETTINGS plan's "route and error details" corrected. Delivery records above and released CHANGELOG
  entries keep `apiKey`, as planned.
- **Differs from the plan:** none.

**Checks:** no new case, as planned (no response changes). J28 and J29 on generated A and B
(`--journey J28 --journey J29`): 52 passed in 50 s; `test_api_journeys` and `test_boundaries`: 8
passed; `ruff check app/ tests/` clean. A grep for `apiKey`/`api_key` finds none in `backend/app`,
`backend/tests` or `frontend/src`; in the documents only history (delivery records, released
CHANGELOG entries) and the text recording the rename. Not run: `volume` (no statement changed),
`startup` (no migration), `queries`, the frontend (unchanged), the full suites (R).

#### C6: Publications, ETag, the OpenAPI per definition and the API index

**Planned 2026-10-05. Approved by the user on 2026-10-05:** C-D60 (with a note for the user
documentation, in TODO), C-D61–C-D71 and the test cases of C6a and C6b. C6 is delivered as C6a,
then C6b (C-D71).
**Needs:** C3, C4, F1 (and C14, C15, CN1, which the reads now carry). **Design:**
[CONSUMER_API "Consistency", "Publications", "API index"](CONSUMER_API.md#endpoints),
[SETTINGS_AND_UI_PLAN "Versions in the documentation"](SETTINGS_AND_UI_PLAN.md#versions-in-the-documentation),
C-D15, C-D16, D47.

**What exists today** (checked 2026-10-05):

- **Publications are already recorded.** `publications.feed_position` holds the position of each
  publication's `published` feed entry (F1, set in `change_sets/publish.py`), so `eventSequence`
  needs no migration. It is `null` for publications made before F1's revision. A new publication
  marks the previous one `withdrawn`, and a publication can also be withdrawn with no successor
  (`withdraw_publication`), so a workspace has at most one `active` publication, and possibly none.
  Each publication is pinned to the model release it was published under (`model_release_id`).
- **A publication's rows** are `publication_objects` (`object_id`, type, name, parent, attributes as
  JSON), `publication_relations` (`relation_id`, ends, type) and its typed values in
  `snapshot_attribute_values` (`owner_id` = the publication). The volume seed already holds a full
  publication of the 110,000 records (`volume_fixture.py`).
- **Every consumer read is written against live tables.** `consumer_objects`, `consumer_lists`,
  `consumer_parameters` and `consumer_xref` (about 1,600 lines) name `RdmObject`, `AttributeValue`
  and `ObjectRelation` directly, scoped by `workspace_key`. Reading a publication means reading the
  same statements over the publication's rows instead. This is the largest part of C6.
- **The indexes C4 and C14 added** (`lower(name)`, `lower(text_value)`, the per-type name trigram)
  and C3a's value-order indexes exist on live tables only. A pinned XREF or sorted list would scan
  the publication's rows without matching ones.
- **No ETag** anywhere in the engine. A live workspace's `feed_position` rises with every live write
  and every publish or withdrawal (F1), which makes it the data version of live data.
- **No OpenAPI for consumers.** The consumer router is `include_in_schema=False`.
  `engine/model/consumer_contract.output_contract` already derives what a definition returns (field
  types, projection shapes, lists, parameter kinds, targetable parameters): the source for the
  document's schemas. `common/pagination.paginate_sequence` pages an in-memory list, which the API
  index needs (definitions live in the model, not in a table).

**The split** (C-D71, approved). C6 has two independent halves. Reading publications touches every
consumer read, adds a migration and needs a volume budget. Documenting the API touches no read.
Delivered as one package it would be several times C15. So:

- **C6a: publications.** `publication` on every read (by ID and `latest`), the publications list
  with `eventSequence`, ETag and `If-None-Match`, the publication indexes and D47's sort.
  **Groups:** `consumer`, `queries`, `contract`, `startup`, `volume`.
- **C6b: the contract documents.** The OpenAPI document per definition and the API index
  `GET /api/consumer`. **Needs:** C6a, so the document describes the final read contract
  (`publication`, the ETag, `304`, the publications route) once. **Groups:** `consumer`, `contract`.

V2 then needs C6b. Queue rows 19 and 19a replace row 19.

##### C6a: Publications

**Delivered 2026-10-05** ([record](#c6a-delivery-record)).

**Behaviour.** A consuming system extracts a consistent snapshot and reads it as long as it needs,
while live data changes:

```text
GET …/publications?workspace=north                 newest first: id, publishedAt, eventSequence, status
GET …/lists/{listKey}?publication=latest           pinned to the active publication; RDM-Publication names it
GET …/lists/{listKey}?cursor=…                     the cursor keeps the publication, even after a newer one
GET …/objects/{id}?publication={id}                one record as published
GET …/xref?query=CHF&publication={id}&expect=one   resolve against the snapshot
POST …/resolve?publication=latest                  every item against the snapshot
```

- Every read, crosswalk (`to.`) and every parameter included, answers from the publication exactly
  as it would from live data holding the same records: same shape, order, scores, paging and
  refusals.
- A response names the publication it read in the `RDM-Publication` header, and the collection
  envelopes in `publication` (`null` for live), as C-D16 and C-D23 name the workspace.
- Every `GET` read answers an `ETag`; a request with a matching `If-None-Match` gets `304` with no
  body. A pinned read's ETag never changes; a live one changes with any live write in the workspace.
- `eventSequence` is where a consumer follows events from after extracting a publication (C-D15;
  the events arrive in C10).

**Design.**

- **One read over two sources** (`engine/reads/consumer_source.py`, new). A `ConsumerSource` names
  where a read's rows are: the objects (entity, `id`, type, name, parent columns), the values (entity
  and its owner condition), the relations (entity, `id`, ends, type) and the scope condition
  (`workspace_key = …` or `publication_id = …`). `LIVE` builds it over `objects`,
  `attribute_values` and `object_relations`; `publication(id)` over `publication_objects`,
  `snapshot_attribute_values` and `publication_relations`. `consumer_objects`, `consumer_lists`,
  `consumer_parameters`, `consumer_xref` and `consumer_resolve` take a source where they take
  `workspace_key` today, and build every statement through it. The live source yields the statements
  of today, so live budgets keep their statement counts (checked by the existing volume tests).
  This mirrors `ObjectColumns` (`object_query`), which serves the management lists in every context;
  consumer lists keep building on it, with the publication's columns from `snapshot_reads`.
- **The `publication` name** (`app/consumer/router.py`): a reserved name on objects, lists, XREF
  and in batch resolve's URL (C-D47's "the URL takes only `workspace`" gains `publication`), never
  in an item. `latest` or an ID is resolved after the workspace (C-D61, C-D62), then the model:
  a pinned read uses the publication's release (C-D60).
- **Cursors** bind the resolved publication (C-D64): `consumer-list:<key>:<listKey>` and XREF's scope
  gain it.
- **ETag** (`app/consumer/etag.py`, new): computed from the data version read **before** the data,
  so a tag is never newer than the body it labels (C-D65). Compared after the read.
- **The publications list** (`engine/reads/consumer_publications.py`, new): newest first by
  publication number, `paginate_statement` with the list paging names (no `seek`).
- **Migration** (one revision): on `publication_objects`, `(publication_id, lower(name))` and the
  `btree_gin` trigram `(publication_id, object_type_key, name)`; on `snapshot_attribute_values`,
  `(owner_id, attribute_type_key, lower(text_value))` and one value-order index per typed column,
  `(owner_id, attribute_type_key, <integer|decimal|boolean|date|datetime>_value, object_id)`. The
  `snapshot_attribute_values` ones are partial, `WHERE owner_kind = 'publication'` (C-D67, C-D68).
- **D47's sort**: C3a's two-part attribute sort (records with a value through the index, then those
  without) for the publication context of `object_query`, which consumer pinned lists and the
  management per-type list in publication context share. Not the change-set context (C-D67).
- **No new setting.** `publication` joins the reserved names.

**Decisions** (status per row; a row without one is a recommendation awaiting approval):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D60 | Which definition reads a publication made under another model release? | **Approved 2026-10-05; to be stated very clearly in the user documentation (TODO, "Open decisions").** **The publication's release**, when it declares the same `consumerApi` at the requested `contractVersion`: its definition and its model read its rows, as the management API reads a publication with its pinned release. The publication's keys mean what its release says (a later release may reuse a key with another type). Otherwise `409 PUBLICATION_CONTRACT_MISMATCH` with `details.publication` and the `contractVersion` that release declares (`null` if none). The route still checks the version against the active release first (C-D3). Consequence: after a release raising the contract version, consumers cannot read older publications through the new version; the next publication serves it. The alternative, reading old rows with the active definition, would answer fields the publication cannot hold as `null`, indistinguishable from "no value" |
| C-D61 | What `latest` means, and which publications are readable | **Approved 2026-10-05**, after clarifying that the active publication is always the newest one or none: they differ only after a withdrawal with no successor. `latest` is the workspace's **active** publication; with none (never published, or the last one withdrawn without a successor) `404 PUBLICATION_NOT_FOUND`, `details.publication: "latest"`. This amends CONSUMER_API's "the newest publication": a withdrawn publication has been taken back and should not be served as current. **By ID, any publication of the workspace is readable**, active or withdrawn: publications are immutable, every publish withdraws its predecessor, and an extract pinned to one must be able to finish |
| C-D62 | A publication of another workspace | **Approved 2026-10-05.** Looked up in the resolved workspace (`workspace`, or the default, C-D16); another workspace's ID is `404 PUBLICATION_NOT_FOUND`, as get by ID treats another workspace's record (C2). No workspace is inferred from the ID, so a request means the same whatever the default is |
| C-D63 | How a response names the publication | **Approved 2026-10-05.** `RDM-Publication: {id}` on every response of a pinned read, refusals included (as `RDM-Workspace`, C-D23). Lists, XREF pages and batch resolve gain `publication` in the envelope, `null` when live: an additive field. Get by ID and `expect=one` stay the bare object |
| C-D64 | Cursors and `latest` | **Approved 2026-10-05.** A cursor binds the resolved publication. With a cursor, `latest` continues in the cursor's publication even after a newer one is published, so an extract pages every object once (C8 scenario 13). A cursor from a live read sent with `publication`, from a pinned read sent without it, or with a different explicit ID, is `400 INVALID_CURSOR` |
| C-D65 | The ETag | **Approved 2026-10-05.** **Value:** opaque, documented as such: for live, the workspace, its feed position and the active release; for a pinned read, the publication and the release that reads it; with `:{contractVersion}`, as CONSUMER_API writes it. The release is in it because a compatible release (an added field, C-D2) changes a response without changing the data or the contract version. **Routes:** every `GET` that answers `200` (get by ID, lists, XREF, the publications list; C6b's documents). Not batch resolve: HTTP answers `304` only to `GET` and `HEAD`. **Comparison:** after the read, per RFC 9110 (`*`, several tags, weak comparison); a match answers `304` with the ETag and the `RDM-` headers and no body. Comparing before the read would save the read, but the tag is one data version for every read of the workspace, so a tag sent to another URL could answer `304` for a record that does not exist. Saving the read is left in TODO for a measured need. **Granularity:** any live write in the workspace changes the tag, also one this API does not show; conservative, documented |
| C-D66 | The publications list item | **Approved 2026-10-05.** `id`, `publishedAt`, `eventSequence` (`null` before F1's revision) and `status` (`active` or `withdrawn`), newest first by publication number. Paging as the lists: cursors both ways, `position`, `from=end`, `includeTotal`; `seek` is `400 PARAMETER_NOT_SUPPORTED` (no name order to seek in). Definition parameters are `PARAMETER_NOT_SUPPORTED` there. `status` is added to CONSUMER_API's three fields so a consumer sees which publication `latest` reads |
| C-D67 | D47: which contexts get the value-order sort | **Approved 2026-10-05.** **Publications** only, consumer and management alike (they share the publication columns). Not change sets: their rows are a base and an overlay in one union, which cannot be walked in one index's order, and consumers never read them (C-D6). The change-set sort stays as it is, recorded in TODO. D47 is amended accordingly. The indexes are partial on `owner_kind = 'publication'`, so change-set base and change-set writes do not maintain them |
| C-D68 | Indexes for pinned XREF and lists | **Approved 2026-10-05.** The live indexes of C3a, C4 and C14, built for publications (Design, Migration), so a pinned read keeps the live budgets. Cost: each publish copies the whole live graph into the publication (T1a), and these indexes are maintained on that copy. T1a's publish budget is measured once more at full volume and recorded; if it degrades beyond its budget, the finding is reported before going further |

**Journey.** J28 gains J28.11–J28.14, J29 gains J29.15, both in USER_JOURNEYS and API_JOURNEYS (the
publications route, `publication` on four routes, `PUBLICATION_NOT_FOUND`,
`PUBLICATION_CONTRACT_MISMATCH`, `304`). C8 scenario 13 is then reachable. No model or seed change:
the generated configurations already declare lists, XREF and a targetable parameter; the cases
publish through the management API.

**Test cases** (journey tests, on generated A and B, written first and confirmed failing; approved 2026-10-05):

Given a workspace with records `L1` "Ledger One" (code `L1`) and `L2`, a list of their type, and a
publication `P1` made through the management API; then, live, `L1` renamed "Ledger Uno", `L3`
created and `L2` deleted.

1. **J28.11 Pinned to a publication.** Get by ID of `L1` with `publication=P1` answers "Ledger One",
   live answers "Ledger Uno"; `L2` is found in `P1` and `404 OBJECT_NOT_FOUND` live; `L3` is
   `404 OBJECT_NOT_FOUND` in `P1`. The list read in `P1` holds `L1` and `L2` with `publication: P1`
   in the envelope; live holds `L1` and `L3` with `publication: null`. Every pinned response carries
   `RDM-Publication: P1`. A projection and a parameter read from `P1` show the published relations.
2. **J28.12 `latest` and paging an extract.** `publication=latest` reads `P1`. A list read pinned to
   `latest` with `pageSize=1` gives a cursor; a second publication `P2` is published; the cursor
   continues in `P1` to the end, each `P1` record once, every page naming `P1`; a new read with
   `latest` reads `P2`. Pinned to `P1` by ID after `P2`, `P1` (now withdrawn) still answers. `P2`
   withdrawn without a successor: `latest` is `404 PUBLICATION_NOT_FOUND`.
3. **J28.13 Refusals.** An unknown publication ID, and `P1` read with another `workspace`:
   `404 PUBLICATION_NOT_FOUND`. A live list cursor sent with `publication=P1`, and a `P1` cursor sent
   with `publication=P2`: `400 INVALID_CURSOR`. `publication` inside a batch resolve item: the item
   `rejected` with `PARAMETER_NOT_SUPPORTED`. A release raising the contract version to 2:
   `v2/…?publication=P1` is `409 PUBLICATION_CONTRACT_MISMATCH` naming version 1; after a
   publication under the new release, `latest` reads it.
4. **J28.14 The publications list and ETag.** The list holds `P2` then `P1`, `P2` `active` and `P1`
   `withdrawn`, each `eventSequence` equal to the `feedPosition` of its `published` entry in the
   management feed; it pages with cursors and `includeTotal`; `seek` is `PARAMETER_NOT_SUPPORTED`.
   A live get by ID answers an `ETag`; the same request with `If-None-Match` is `304` with no body
   and the `RDM-Workspace` header; after a live write to another record, `200` with a new tag. A
   pinned read's tag is unchanged by the live write. A compatible release (one added field) changes
   the live tag. Batch resolve answers no `ETag`.
5. **J29.15 Resolving against a publication.** `xref?query=L1&expect=one&publication=P1` finds `L1`
   by its published code after its live code changed, where live answers `404 NO_MATCH`; with
   `to.<targetable>` the target is the published one. Batch resolve with `publication=P1` answers
   each item as the pinned single read does, with `publication: P1` in the envelope.
6. **J21 (unchanged behaviour, one case):** the management per-type list in a publication's context
   sorted by an attribute, across both parts (C3a's J21 case, run with `publicationId`), guarding
   C-D67. Not expected to fail first.

**Unit tests:** `If-None-Match` parsing and comparison (`*`, lists, `W/`, malformed), generated over
tag shapes: the only logic with edge cases of its own.

**Volume:** `test_consumer_list_volume` and `test_consumer_xref_volume` gain their scenarios pinned
to the seed's publication, holding the same statements as the data grows fourfold. Wall times at
full volume measured once with `volume_baseline.py --only-consumer` and recorded here, beside the
live ones, and T1a's publish copy measured once (C-D68). The migration means the seeds are rebuilt
once.

**Checks:** the new cases fail first, then pass; J28, J29 and J21 (`--journey`); groups `consumer`,
`queries` (`object_query`'s publication sort), `contract` (`test_api_journeys`, `test_boundaries`;
the management OpenAPI lock unchanged), `startup` (clean bootstrap, upgrade from `20261005_02`,
restart, interrupted migration, lifespan, a smoke start on a copy of the development database),
the two consumer volume tests; `ruff`. Not run: the frontend (unchanged), the full suites (R).

**Docs at delivery:** API.md (the `publication` name on four routes, the publications route, ETag
and `304`, the codes); CONSUMER_API (C-D60–C-D68, "Consistency" and "Publications" amended,
`latest` as the active publication); D47 amended; USER_JOURNEYS and API_JOURNEYS (J28.11–J28.14,
J29.15); CURRENT_FUNCTIONALITY (reading a consistent snapshot); POSTGRESQL_BUDGETS (the pinned
reads); TODO (the change-set sort, comparing before the read).

**Composable domains (ADR-032):** identity untouched (publication IDs are existing public IDs).
Attribute storage gains indexes, not a shape. Audit is read, not changed. Bulk APIs, the `match`
declaration and mapping coverage are untouched. A catalogue publishing a price list version for
shops to extract is a pinned list: the door is exercised.

##### C6a delivery record

**Delivered 2026-10-05**, with C-D60–C-D68 and the approved cases.

- **One read over two sources** (`engine/reads/consumer_source.py`): `ConsumerSource` is the
  workspace's live data or one publication. A publication's rows are presented in the live tables'
  shape (each live class mapped onto a subquery of `publication_objects`, the publication's
  `snapshot_attribute_values` or `publication_relations`, with `adapt_on_names`), so
  `consumer_objects`, `consumer_parameters`, `consumer_xref`, `consumer_resolve` and
  `consumer_lists` build the same statements over either; the live source yields today's
  statements. An alias of a publication entity is a fresh, anonymous subquery (aliasing a mapped
  subquery would alias the live table; two aliases share one `FROM` in `_shared`).
- **Lists** pinned to a publication use the publication's object query (`snapshot_object_query`),
  shared with the management publication lists; `ObjectQuery.record` names the listed record's
  columns for the parameter predicates, and `then_by_name` reads its name. **D47 (C-D67):**
  `value_order_parts` (formerly C3a's live-only helper) now serves the publication context too, so
  the management per-type list, the cross-type lookup and the relation matrix in a publication's
  context read an attribute sort in two parts as well.
- **Router** (`app/consumer/router.py`): `publication` on get by ID, lists, XREF and batch resolve's
  URL; `latest` is the active publication, or with a pinned cursor that cursor's publication, read
  from the cursor's signed scope (`common/cursors.signed_scope`); the publication's release must
  declare this API at the version (`PUBLICATION_CONTRACT_MISMATCH`), and the parameters are checked
  again against its definition when it differs from the active one. `RDM-Publication` on every
  pinned response; `publication` in the list, XREF and resolve envelopes. Cursor scopes carry
  `:publication:<id>` for a pinned read. `GET …/publications` (`engine/reads/consumer_publications.py`).
- **ETag** (`app/consumer/etag.py`): a digest of the data version (the workspace's feed position,
  read with the workspace before the data, or the publication) and the release, then
  `:{contractVersion}`; compared after the read; `304` with the ETag and `RDM-` headers. Not on
  batch resolve.
- **Migration** `20261005_03`: `publication_objects` (`publication_id`, `lower(name)`) and the
  `btree_gin` trigram (`publication_id`, `object_type_key`, `name`); on `snapshot_attribute_values`,
  partial on `owner_kind = 'publication'`, (`owner_id`, `attribute_type_key`, `lower(text_value)`)
  and five value-order indexes. Declared in `models/database.py`.
- **Differs from the plan:** a pinned list's records sharing the sort value and name follow their
  object ID, not creation order: a publication records none (as the management publication lists
  already do, J21.6). The plan's "same order" holds otherwise. Envelopes order `publication` after
  `workspace`.

**Full-volume timings** (`volume_baseline.py --only-consumer --scale 1 --repeat 3`, warm median ·
statements · ORM rows; measured once, after the seed rebuild the migration needed):

| Read | Live | Pinned to the seed's publication |
| --- | --- | --- |
| List: first page by rank | 10.5 ms · 11 · 24 | 14.5 ms · 13 · 5 |
| List: next cursor page | 12.2 ms · 13 · 25 | 18.3 ms · 15 · 5 |
| List: position jump to the middle | 113.8 ms · 11 · 24 | 117.4 ms · 13 · 5 |
| List: 20,000 items under a parent | 9.9 ms · 9 · 24 | 15.0 ms · 11 · 5 |
| List: ancestor filter with `includeTotal` | 95.9 ms · 13 · 24 | 120.2 ms · 15 · 5 |
| XREF: an item's code, another case | 28.7 ms · 8 · 3 | 41.5 ms · 10 · 5 |
| XREF: a group's code promoted to its citing items | 48.5 ms · 9 · 3 | 66.9 ms · 11 · 5 |
| XREF: 4-character contains | 49.4 ms · 7 · 3 | 57.5 ms · 9 · 5 |
| XREF: `expect=one` | 12.8 ms · 7 · 3 | 18.8 ms · 9 · 5 |
| XREF: within the heavy group | 63.3 ms · 10 · 3 | 79.6 ms · 12 · 5 |
| XREF: `scoresFrom` on the group | 52.2 ms · 9 · 3 | 73.5 ms · 11 · 5 |
| XREF: a term in every item, `QUERY_TOO_BROAD` | 132.5 ms · 3 · 3 | 161.9 ms · 5 · 5 |

A pinned read costs two statements more (the publication and its release) and 4–24 ms more. Over
100 ms, live and pinned alike: the position jump to the middle (D46's known deep-position cost) and
the refusal of a term in every item (C-D37's known cost, live 116–133 ms); the ancestor filter with
a total is 96 ms live and 120 ms pinned. Not investigated further in this package (no measurement
loop); the batch resolve figures of the same run were measured live only.

**Publish with the new indexes (C-D68),** `--only-publish`, each once: at full volume, capture
48.7 s and publish of 10,000 renamed records 137.1 s (T1a's probe: 55.6 s and 119.0 s, both on a
freshly built seed), the same 20,153 statements and 2,704,503 rows. At 0.1 scale (the budgeted size,
11 s): 60.4 s, on a seed built in the same run, where T1a recorded 56–57 s on a fresh seed and 9.1 s
on a reused one. Then once on the reused seed, at the user's request: **10.8 s** (capture 3.6 s), the
same 2,081 statements: within the 11 s budget, and 1.7 s (about 19 %) above T1a's 9.1 s, the cost of
maintaining the new indexes on the publication's copy. Which index costs what was not measured; the
`btree_gin` trigram on `publication_objects` is the likeliest. The margin to the budget is now 0.2 s.

**Checks:** the 10 new journey cases failed first (`publication` unknown, the publications route
missing), then pass; the J21.9 publication guard passed before and after. J28, J29, J21, J25, J05,
J06 and J07: 134 passed. Groups `consumer`, `queries` and `contract` in parallel: 437 passed in
1 min 6 s (their serial part selects none); `matrix`: 108 passed; J16: 18 passed; `startup` with
`HEAD` at `20261005_03` and a new case (an interrupted run of the revision rolls back to
`20261005_02`; with the cause removed it upgrades and starts twice): 96 passed;
`test_schema_drift` passed. Unit: `tests/unit/consumer/test_etag.py`, 30 passed. Volume:
`test_consumer_list_volume` and `test_consumer_xref_volume`, with the pinned scenarios, same
statements at both sizes: 4 passed. `ruff check app/ tests/` clean. **Smoke:** a copy of the
development database downgraded to `20261005_02` upgraded on start, published, served a
1,610-record publication list sorted by an attribute (first page, end, middle), and started again
healthy; the copy dropped. The development database itself was migrated to `20261005_03` by the
running `uvicorn --reload` and answers `/health` ok. Not run: the frontend (unchanged), the full
suites (R).

##### C6b: The contract documents

**Delivered 2026-10-05** ([record](#c6b-delivery-record)).

**Behaviour.** An integrator discovers the consumer APIs and gets a typed contract for each:

```text
GET /api/consumer                                   the installed definitions, paged
GET /api/consumer/{consumerApi}/v{contractVersion}/openapi.json
```

- **The API index** lists, for each definition of the active release: `consumerApi`, `name`,
  `contractVersion` and `openapi` (the document's URL, after the deployment's root path), ordered by
  `consumerApi`, paged (C-D69).
- **The document** describes this definition's API as it answers, so a client generator or Scalar
  (V2) gives a working client: per SETTINGS_AND_UI_PLAN, literal paths with no `{consumerApi}` or
  `{contractVersion}` placeholders and one path per list, `info.title` the definition's `name`,
  `info.version` the contract version, `info.description` naming the declaring release, `servers`
  after the root path. A release raising the version moves the document; the old URL answers
  `404 CONTRACT_VERSION_NOT_FOUND`.

**Design.**

- **Builder** (`engine/model/consumer_openapi.py`, new; engine tier, no FastAPI): one function from
  the model and a definition to a dict, OpenAPI 3.1. Schemas come from `output_contract`: the shared
  object (each declared field with its JSON type, `null` allowed where a field can have no value,
  `parent`, `path`, `hierarchy`), each projection as an object, nullable object or array by its
  cardinality, `matchScore` on XREF results, `target` where `to.` is given. Each definition parameter
  is a query parameter on the routes that apply it (C-D31), an array with `style: form`,
  `explode: true` (C-D32); each targetable one adds its `to.` name; reserved names (`workspace`,
  `publication`, paging, `query`, `expect`) with their bounds. Responses: `200` with `ETag`,
  `RDM-Workspace` and `RDM-Publication` headers, `304`, and each route's error codes through one
  shared error schema. The documented limits are written where they apply: contains from 3
  characters and the 10,000-match limit (C-D37, as its approval required), 100 terms, `pageSize`
  1–100, the resolve maximum from `CONSUMER_RESOLVE_MAX_ITEMS` (C-D50).
- **Routes** (`app/consumer/router.py`): `GET /api/consumer` and `…/openapi.json`, both with the ETag
  of the active release (C-D65). They stay out of the management document.
- **No migration, no setting, no frontend.** V2 lists the index's documents on `/docs`.

**Decisions** (status per row; a row without one is a recommendation awaiting approval):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D69 | The API index entry and paging | **Approved 2026-10-05.** `{ "consumerApi", "name", "contractVersion", "openapi" }`, plus `description` when the model has one; ordered by `consumerApi`; paged as the lists (cursors both ways, `position`, `from=end`, `includeTotal`) through `paginate_sequence`, since definitions are in the model, not a table. No `workspace`: definitions are not per workspace. The index names no model release; `info.description` of each document does |
| C-D70 | How the document is checked | **Approved 2026-10-05.** Add `openapi-spec-validator` as a **dev** dependency (it brings `jsonschema`): the journey test checks the document is valid OpenAPI 3.1 and that a real `200` of each route validates against its documented schema, so the document cannot drift from the answers. Without it, the tests can only assert chosen facts, and a wrong schema would surface only in a client generator. Cost: one dev dependency, no runtime one |
| C-D71 | Split C6 into C6a and C6b | **Approved 2026-10-05.** Yes, as above: C6a's reads first, then C6b documents them. Each is one vertical slice with its own record and checks |

**Journey.** J20 gains J20.3 (the API index) and J20.4 (a consumer API's document) in USER_JOURNEYS
and API_JOURNEYS; C8 scenario 16 is then reachable.

**Test cases** (journey tests, on generated A and B; approved 2026-10-05):

1. **J20.3 The API index.** It lists the configuration's definition with its `consumerApi`, `name`,
   `contractVersion` and an `openapi` URL that answers `200`. A release adding a second definition
   lists both, in key order, paging with `pageSize=1`; a release removing it lists one again. A
   paging refusal answers as the lists' do. A matching `If-None-Match` is `304`.
2. **J20.4 The document.** `info.version` is the contract version, `info.title` the name. Every path
   is literal (`/api/consumer/<key>/v<n>/xref`, one per list), none holds `{consumerApi}` or
   `{contractVersion}`. The document is valid OpenAPI 3.1. A real answer of get by ID, a list page,
   XREF (`any` and `one`, with `to.`), batch resolve and the publications list each validates against
   its documented `200` schema. A definition parameter appears on the routes that apply it, with
   `style: form`; the targetable one's `to.` name appears; the contains and 10,000-match limits
   appear in XREF's description. After a release raising the version to 2, `v2/openapi.json` has
   `info.version` `"2"` and `v2` in every path, and `v1/openapi.json` is
   `404 CONTRACT_VERSION_NOT_FOUND`.

No unit tests: the builder's logic is walked by J20.4 on two configurations. **Checks:** J20, J28;
groups `consumer`, `contract` (`test_api_journeys`, `test_boundaries`, the management OpenAPI lock
unchanged); `ruff`. Not run: `volume` (the documents read only the model), `startup` (no
migration), the frontend, the full suites (R).

**Docs at delivery:** API.md (the index, the document); CONSUMER_API (C-D69–C-D71; "API index" and
"Generated OpenAPI" amended); SETTINGS_AND_UI_PLAN ("Versions in the documentation" delivered);
USER_JOURNEYS and API_JOURNEYS (J20.3, J20.4); CURRENT_FUNCTIONALITY; OPEN_SOURCE only if a runtime
dependency were added (none is).

**Composable domains (ADR-032):** documentation of an existing contract. No door is affected.

##### C6b delivery record

**Delivered 2026-10-05**, with C-D69 and C-D70 and the approved cases.

- **Builder** (`engine/model/consumer_openapi.py`, engine tier): `consumer_openapi(model, definition,
  root_path, resolve_max_items)` writes the OpenAPI 3.1 document from `output_contract`: the
  `Object` and `ScoredObject` schemas with every declared field typed (nullable unless it is the
  `id` role, the `name` role, `path`, `hierarchy` or has a `default`), a `Projection_<name>` schema
  per projection, `target` where a parameter is targetable, the list, XREF, publications and resolve
  envelopes, and one error schema; the five operations with their parameters, headers, `304` and
  codes; the limits in the descriptions and bounds. Every object schema refuses undeclared fields.
- **Routes** (`app/consumer/router.py`): `GET /api/consumer` (the index, `paginate_sequence` by
  `consumerApi`) and `GET /api/consumer/{consumerApi}/v{contractVersion}/openapi.json`, both tagged
  by the active release and the root path; their query names are checked as on the reads.
- **Dev dependency** `openapi-spec-validator` (with `jsonschema`), C-D70; the README's tools table
  names it. No runtime dependency, so OPEN_SOURCE is unchanged.
- **Differs from the plan:** none. Checked once by hand that the response validation is strict:
  a corrupted answer (a text where an integer is declared, an undeclared field, a missing field, a
  text `matchScore`) is rejected; that check was not kept.

**Checks:** J20.3 and J20.4 failed first (no route), then pass on generated A and B; J20: 10 passed.
Groups `consumer` and `contract` in parallel: 239 passed in 36 s (their serial part selects none),
the management OpenAPI lock unchanged. `ruff check app/ tests/` clean. Not run: `volume` (the
documents read only the model), `startup` (no migration), the frontend (unchanged), the full suites
(R).

**Found after delivery (2026-10-05):** a list whose parent parameter shares a definition parameter's
name, which C1 allows and CONSUMER_API's reference definition does (`domain`, `codelist`), listed the
name twice on that list's operation, so the document was not valid OpenAPI (`Duplicate parameter`).
The route reads the name as the parent there, so the document now lists it once, as the parent.
Found while adding consumer APIs to the operators example model; held by
`tests/unit/engine/model/test_consumer_openapi.py` over that model, which failed before the fix.

#### C8: Parity acceptance

**Delivered 2026-10-05** ([record](#c8-delivery-record)), with C-D75 raised during delivery. **Planned 2026-10-05; decisions C-D72–C-D74 and the test cases approved by the user the same day.**
**Needs:** C3–C6, C14, C15 (all delivered). **Groups:** `consumer`, `model`, `contract`, `volume`.
**Design:** [CONSUMER_API "Reference implementation"](CONSUMER_API.md#reference-implementation),
"Definition shape", the C8 scenarios.

**Behaviour.** The consumer read line's checkpoint. CONSUMER_API's promise is that "the reference
response must be reproducible from a definition alone": a consumer of the production gateway can
move to the engine by a definition, with only the documented differences ("Behavior the engine does
not carry over"). Each C package proved its own mechanism on generated A and B, whose shapes are
abstract (`R`, `Bscope`, `watch`). C8 proves the whole on a model shaped like the reference
deployment's (codelists, locations, availability, systems, translations, a single-valued self
relation), through the calls integration flows make: XREF with `system`, take the top result, read
one to three fields from it.

**What exists today** (checked 2026-10-05):

- **The documented definition validates.** A scratch probe (not kept): the starter plus a `location`
  type below a codelist, `operator-code` and `internal-only`, `available-at-location`
  (value → location, many-to-many), `alternative-for` (value → value, one-to-one) and
  `system-value-maps-to-master` also bound to `location`; with CONSUMER_API's "Definition shape"
  written out (its `…` filled with `domain`, the `values` and `all-values` lists) the release
  compiles with no diagnostic.
- **One field of the reference object cannot be declared.** The reference's `alternative` items
  carry `objectType` (`{ "objectType", "masterId", "code", "name" }`). A projection field reads `id`,
  `name`, an attribute or `ancestor:<type>.<field>` of the related record, not its type: adding
  `"objectType": "objectType"` to the probe's `alternative` is refused at
  `/consumerApis/rdm/projections/alternative/fields/objectType`. C-D73.
- **Scenario coverage on generated A and B.** Scenarios 1, 2, 5, 9 (J29, J29.3), 3 (J29.1
  `preferTargetTypes`), 6–8 (J29.6, J28.8), 10 (J28.7, J28.8), 11 (J29.8), 12 (J29.11–J29.13), 13
  (J28.12) and 16 (J20.3) each have a journey test of the mechanism. Not covered anywhere: the
  reference's shapes together on one object, a translated name scoring through a promoted
  translation on a translation-shaped model, and crosswalk to a translation (`to.language`), since
  the documented `language` parameter is not `targetable`.
- **Budgets.** Every consumer read was measured at full volume by its package
  (`volume_baseline.py --only-consumer --scale 1 --repeat 3`): lists (C3, C3a), XREF (C4, C5), batch
  resolve (C14) and the pinned reads (C6a). _Corrected at delivery:_ C6a's run has three reads over
  100 ms, not only the deep positions of
  [POSTGRESQL_BUDGETS E3](POSTGRESQL_BUDGETS.md#e3-sort-by-an-attribute-under-the-20000-child-parent-104-150-and-142-ms-live-closed-by-09-c3a):
  the position jump (114/117 ms), the pinned ancestor filter with a total (120 ms) and the
  too-broad refusal (133/162 ms), each recorded in C6a's record.
  Since C6a, no file under `engine/reads/` changed; `consumer/router.py` gained C6b's two document
  routes and nothing on a read's path. The figures sit in five delivery records, not in one table.
- **The operators example model** (`model/rdm-operators-timetables.json` 0.6.0) has every structure the
  fixture needs, but its one `rdm` API is a different design on purpose: every type exposed, `id`
  output as `id`, system values and translations as objects of their own, so a bare `expect=one` on a
  code is ambiguous there ([DOCUMENTATION_PLAN](DOCUMENTATION_PLAN.md)). It does not reproduce the
  reference. C-D72.

**Design.**

- **Fixture** (`tests/journeys/configurations.py`, `parity()`; C-D72): the starter model, read from
  `rdm-starter.json` so it follows the starter, plus the extension of the probe above (fixture content,
  not product scope), plus CONSUMER_API's definition with `alternative` (with `objectType`, C-D73)
  and `duration` added and `language` declared `targetable`. Not in `all_configurations()`, so no
  generic journey runs on it. One model-only seed, built once (seed once, reuse).
- **Dataset**, written by one `POST /batches` per module (records and relationships, inline), about
  40 records:
  - Domain Transport (`HC`) › codelist Timetable types (`MOT`) › Train (`CONS`), Follow-up
    (`FUP`), Tram (`VAC`), Standard (`STD`); Train's alternative is Follow-up.
  - Codelist Stations (`CLIN`) › locations Central Station (`CEN`, operator `BR1`) and North Station
    (`NOR`).
  - Domain Finance (`FIN`) › codelist Currencies (`CUR`) › Swiss franc (`CHF`, master ID
    `MV-0001`), Euro (`EUR`), Standard (`STD`).
  - Systems SAP and Oracle. SAP `CHF` (external ID `1001`) and Oracle `SFR` (`O-77`) map to Swiss
    franc; SAP `LOC-9` (`9001`) maps only to North Station; SAP `FU-1` maps to Follow-up and to
    Central Station.
  - Train is available at Central Station, Tram at North Station. So each `location`
    route has a record of its own: Train by availability only, Follow-up by the shared system
    value only.
  - German (`de`): Eisenbahn for Train, Schweizer Franken for Swiss franc. (No translation is a
    substring of its object's name, so a translation's score is never hidden by the object's own
    contains score.)
- **Shape check**, on every answer: valid against the definition's own OpenAPI document (C6b's
  validator, C-D70). On one XREF result and one list item: the keys are the reference shared object's
  keys, mapped by the "does not carry over" table (`masterId` is the object ID and the former ID is
  `formerId`; `parent` always present; `description` in both; `alternative` an object or `null`;
  booleans and dates typed; no `page` or `returnedCount`).
- **`objectType` in a projection** (C-D73): `engine/model/validation/consumer_api_rules.py` accepts
  the source `objectType` when every type the projection reaches is exposed, and refuses it at the
  field's path otherwise; `consumer_contract.output_contract` types it as the exposed public names
  (the OpenAPI schema an `enum`); the composition writes the related record's public name. Adding it
  to a projection adds a field (not breaking, C-D2); removing it is `version_required`, as for any
  field. No statement is added: the related select already reads the type key.
- **No migration, no index, no setting, no route.**

**Decisions** (status per row):

| # | Question | Decision |
| --- | --- | --- |
| C-D72 | Which model the parity scenarios run on | **Approved 2026-10-05.** A test-only fixture, the starter plus a small extension and CONSUMER_API's printed definition (as CONSUMER_API's C8 row says), not the operators example model. The operators model's API is a deliberately different design (every type exposed, `id` not `masterId`, system values as objects), so it would need a second definition written to match the reference, and the example would then carry a test's needs; a later edit to the example would break acceptance. The fixture also proves that the definition CONSUMER_API prints is valid and answers as documented. The operators model keeps its OpenAPI test |
| C-D73 | The reference's `objectType` inside projection items (`alternative`) | **Approved 2026-10-05.** Allow `objectType` as a projection field source, the related record's public type name, only where every type the projection reaches is exposed by the definition (otherwise there is no public name; refused at the field). Two real cases: the reference's `alternative`, and a projection over a relation with several target types (the operators model's `mapsTo`, where an item is a value or a location). The alternative, a new row in "does not carry over", would leave a mixed projection whose items cannot be told apart |
| C-D74 | The C8 volume budgets | **Approved 2026-10-05.** No new full-volume run. Every consumer read was measured at full volume by its package, and nothing on a read's path changed since C6a, so a rerun would repeat C6a's figures. C8 collects them into one consumer table in POSTGRESQL_BUDGETS (each row with the package that measured it) and runs the `volume` group, whose statement counts at two sizes hold them. C-D73 adds a field, not a statement, which `test_consumer_xref_volume` confirms. CONSUMER_API's "Budgets are set against the 0.8 Track S volume fixture (C8)" becomes "set per package, collected in C8" |
| C-D75 | The parent's keys (raised during delivery) | **Approved 2026-10-05.** The parity shape check found that the reference's parent is `{objectType, name, code, masterId}`, the object's own field names, while the engine keyed it by role (`id`, `code`, `name`), so a flow that reads `masterId` from the object and then from `parent` found it only on the object. The parent's fields are now keyed by the roles' output names, as the object's own fields; `objectType` stays. Pre-1.0, so the shape changes for every definition whose `id`, `code` or `name` output is not the role name (generated A and B's `ledgerId`); the alternative, a row in "does not carry over", was not taken |

**Journey.** No new journey: a consumer migrating from the gateway walks J28 and J29. The parity
module is the evidence for the variants it walks on the reference-shaped model (API_JOURNEYS), and
USER_JOURNEYS' J28 and J29 "Evidence today" name it.

**Test cases** (`tests/journeys/test_j28_j29_parity.py`, on the `parity` configuration, written
first). Except C-D73's, they test delivered behaviour on a new model, so they are expected to pass
on the first run, as T1's did; that is recorded, not engineered around. Each is one call or a few,
named by its CONSUMER_API scenario:

1. **Scenarios 1 and 5.** `query=MV-0001` (the global ID, `master-id`) scores Swiss franc 1000;
   `query=CHF` finds it first with 500, its SAP value's promoted 80 adding nothing (the higher
   wins); `query=franc` finds it by contains only, below any exact score; `query=CHF,EUR` has both
   currencies, each with its best term.
2. **Scenario 2.** `query=1001` finds Swiss franc with 75 (the SAP value's external ID, promoted);
   with `system=SAP` the same, `systemVariants` holding only the SAP item; with `system=Oracle`
   nothing, since only Oracle values may score (`scoresFrom`).
3. **Scenario 3.** `query=9001&expect=one` answers North Station; `query=FU-1` scores Central Station
   and not Follow-up (`preferTargetTypes`).
4. **Scenario 4.** `query=Eisenbahn` finds Train with 60; `query=Berat` with 12.
5. **Scenario 6.** `query=STD` with `codelist=MOT`, `codelist=Timetable types`, `domain=HC` or
   `domain=Transport` keeps the timetable Standard only.
6. **Scenarios 7 and 8.** On `lists/all-values`, `location=CEN` keeps Train (availability)
   and Follow-up (shared system value), not Tram or Standard; `location=North Station` keeps
   Tram; `query=CEN&location=CEN` keeps Central Station itself (`self`). With `system=SAP`
   added, `location=CEN` keeps Follow-up only.
7. **Scenario 9.** `query=STD&expect=one` is `409 AMBIGUOUS_MATCH` naming both Standards in the
   documented order (score, public type, name, ID); with `codelist=CUR` it answers the currency.
8. **Scenario 10.** `lists/values?codelist=<MOT's ID>` holds the four timetable types; with
   `language=de` only Train, its `translations` limited to German; `lists/all-values` with
   `codelist=MOT` or `codelist=Timetable types` (the `ancestor` parameter, C-D28) the same four;
   `lists/values?codelist=MOT` is `404 PARENT_NOT_FOUND` (a code is no parent, C-D28).
9. **Scenario 11.** Batch resolve, items `CHF` with `system=SAP`, `9001` with `system=SAP`,
   `nothing`, `STD`, and one with both `query` and `id`: `found`, `found`, `not_found`, `ambiguous`,
   `rejected`, in item order; each `found` equals its `xref?expect=one` answer.
10. **Scenario 12.** `query=CHF&system=SAP&to.system=Oracle&expect=one` answers Swiss franc with
    `target` the `SFR` item; `query=EUR&to.system=Oracle&expect=one` is `404 TARGET_NOT_FOUND`;
    after a second Oracle value is mapped to Swiss franc, the first read is `409 AMBIGUOUS_TARGET`;
    `query=CONS&to.language=de&expect=one` answers `target` the Eisenbahn item.
11. **Scenario 13.** A change set is published; `lists/all-values?publication=latest&pageSize=2`
    names the resolved publication; a second change set adding a value is published between pages;
    following the cursor reads every value of the first publication once and not the new one.
12. **Scenario 16.** `GET /api/consumer` lists `rdm` with its OpenAPI URL, and that document
    validates.
13. **The reference shape** (beside every case: each answer valid against the document). Get by ID
    of Train has `alternative` the object `{objectType: "CodelistValue", masterId, code,
    name}` of Follow-up, `availableAt` an array with Central Station, `parent` the codelist, `path`
    and `hierarchy` from the walk; Swiss franc's `alternative` is `null`, Transport's `parent`
    `null`, `isActive` a boolean, `validFrom` `null`; the XREF result and the list item for
    Train are the same object apart from `matchScore`.
14. **J25 (changed, C-D73).** A candidate release with `objectType` in a projection that reaches a
    type the definition does not expose is refused at that field; removing `objectType` from
    `alternative` is `version_required` at its path, adding it is not. These fail first.

No unit tests: C-D73's rule is walked by J25 and case 13. **Checks:** the parity module and J25,
J28 and J29 on their configurations; then the C8 groups together once, `consumer`, `model`,
`contract` and `volume` (the checkpoint run, as T1); `ruff`. No migration, so no `startup`; not
`queries` (no shared read changed); the frontend unchanged.

**Exit:** scenarios 1–13 and 16 pass on the fixture, or each failure is fixed as an amendment or
recorded against its package, before C16.

**Docs at delivery:** CONSUMER_API: the C8 row delivered, "Definition shape" gains `alternative`
with `objectType`, `duration` and `targetable` on `language` (so the crosswalk example's
`to.language=es` matches the printed definition), the "Budgets" sentence (C-D74), C-D72–C-D74
recorded; APPLICATION_MODEL notes `objectType` as a projection source; API.md the field;
POSTGRESQL_BUDGETS the consumer table; USER_JOURNEYS (J28, J29 evidence) and API_JOURNEYS;
EXECUTION_GUIDE's `consumer` row gains the module; CURRENT_FUNCTIONALITY says a projection can name
each related record's type.

**Composable domains (ADR-032):** the `match` declaration is untouched. The projection declaration
gains `objectType`, which a product catalogue's mixed "related items" (a part or an accessory) needs
in the same way, so the door is used, not narrowed. Identity, attribute storage, audit, the bulk APIs
and mapping coverage are untouched.

##### C8 delivery record

**Delivered 2026-10-05**, with C-D72–C-D74 as approved, C-D75 raised and approved during delivery,
and the approved cases.

- **Fixture** (`tests/journeys/configurations.py`, `parity()`): the starter with `location` below a
  codelist, `operator-code`, `internal-only`, `available-at-location`, `has-duration`,
  `alternative-for` (one-to-one) and `system-value-maps-to-master` bound to `location`; and
  CONSUMER_API's definition written out (`_reference_definition`). Not in `all_configurations()`.
  Its dataset (29 records and 12 relationships, one atomic `POST /batches`) is the seed
  `scenario-parity`, built once.
- **Parity module** (`tests/journeys/test_j28_j29_parity.py`): 13 tests, scenarios 1–13 and 16 and
  the reference shape. Every `200` answer is validated against the definition's own OpenAPI document
  (`Parity.conforms`).
- **C-D73** (`engine/model/consumer_contract.py`): `projection_field_type` resolves the source
  `objectType` as text where the definition exposes every type the projection reaches; validation
  (`consumer_api_rules`) and the contract use it, and `ConsumerObjects` writes the related record's
  public name. No statement added.
- **C-D75** (`consumer_contract.parent_keys`): the parent's fields keyed by the roles' output names,
  in the composition (`ConsumerObjects._parent`), the contract and the OpenAPI document's parent
  schema (whose nullable `code` is now found by its output name).
- **Defect in the test groups:** `JOURNEY_GROUPS` had no `J29`, so since C4 none of the 32 J29
  journey tests was selected by `-m consumer`; each package ran J29 by name, but the group runs left
  it out. `J29` is mapped to `consumer` (the group grows from 129 to 215 with the parity module and
  the unit tests counted since).
- **Budgets** (C-D74): POSTGRESQL_BUDGETS §7 collects the consumer figures (C6a's run for lists and
  XREF, C14's for batch resolve), with the three reads over 100 ms and their causes. No new run.
- **Differs from the plan:**
  - The plan's "all within 100 ms except the deep positions" was wrong; corrected above.
  - The OpenAPI schema types a projection's `objectType` field as a nullable string, not an `enum`
    of public names: the contract records value types only, and an `enum` would be its first
    exception. The answers validate against the document.
  - C-D75 and the J29 group mapping were not in the plan.
  - Translations are under language › translation group; the plan's dataset named only the
    languages. Spanish (Cita médica) was added so that `language=de` visibly limits `translations`.

**Checks:**
- **Failing first:** the parity module could not load its model until C-D73 (every test errored at
  `alternative.objectType`). After C-D73, 12 of 13 passed on their first run, as expected for
  delivered behaviour; the reference shape failed on `parent` (C-D75). The new J25 case (2 on
  generated A and B) and J28's two changed parent assertions (4) failed with the app changes stashed
  and pass with them. Three failures on the way were the test's own (commas sent encoded, the
  candidates' key, `POST /objects` with `parent` instead of `parentObjectId`), fixed in the test.
- **Targeted:** the parity module, J25, J28, J29, J20 and `test_consumer_openapi`: 106 passed.
- **The C8 groups together** (`consumer`, `model`, `contract`, `volume`, in parallel): 538 passed
  and 2 failed in 1 min 13 s. Both failures were `test_consumer_api_model`'s pinned parent contract
  (`id`, C-D75), updated; that module then passed (87). Serial part: 1 passed.
- `ruff check app/ tests/`: clean.
- Not run: `startup` (no migration), `queries` (no shared read changed), the frontend (unchanged),
  the browser runners, the full suites (R).

**Composable domains (ADR-032):** the projection declaration gains `objectType` (C-D73); the `match`
declaration, identity, attribute storage, audit, the bulk APIs and mapping coverage are untouched.

#### C16: `asOf` in the consumer tier

**Delivered 2026-10-05** ([record](#c16-delivery-record)). **Planned 2026-10-05; decisions C-D76–C-D80 and the test cases approved by the user the same day.**
**Needs:** C2, Q4 (both delivered); built on C3–C15 and C6a, since `asOf` reaches every read they
added. **Groups:** `consumer`, plus `queries` for the one shared function it touches (below).
**Design:** [CONSUMER_API "Business dates: `asOf`"](CONSUMER_API.md#business-dates-asof), C-D14,
ADR-038, Q4 and its D21–D22, SC-11.

**Behaviour.** "Which values apply on 1 July?" An integration flow asks the consumer API for a
reference list as it stands on a business date: the old values before a cut-over day, their
replacements from it. Today the consumer tier cannot answer: `asOf` is a reserved name and every
consumer read refuses it as `400 UNKNOWN_PARAMETER`. After C16:

```text
GET …/lists/{listKey}?asOf=2026-07-01           the list's records effective that day, every page
GET …/objects/{id}?asOf=2026-07-01              the record, or 404 if it is not effective that day
GET …/xref?query=CHF&asOf=2026-07-01            dated types filtered, undated ones not (C-D14)
POST …/resolve?asOf=2026-07-01                  every item as its single read answers
```

- A date is effective by the type's declared period, as on the management API (ADR-038): no start
  after it, no end on or before it, an empty start or end open. Only a declared period dates a
  record; a type with none is never dated from a date field it happens to bind.
- `asOf` combines with `publication` (the publication's values, under the release it was published
  under) and with every definition parameter, crosswalk target and paging parameter.
- The publications list and the API index do not serve it (`400 PARAMETER_NOT_SUPPORTED`, as
  `publication` there).

**What exists today** (checked 2026-10-05):

- **The predicate.** `object_query.as_of_predicate` dates records over an `ObjectColumns` (two
  correlated `NOT EXISTS` on the value key); `build_object_query` and `build_snapshot_object_query`
  take `as_of`; `as_of_filter` binds it into a cursor only when set. The consumer reads other than
  lists select through `ConsumerSource` entities, not `ObjectColumns`, so they cannot call it as it
  stands.
- **The consumer side.** `asOf` is in `RESERVED_PARAMETERS` (C1) but in no route's names, so every
  read answers `UNKNOWN_PARAMETER`. `consumer_contract.OutputContract.as_of` already records the
  exposed types with a period, and removing one is `version_required` (Q4). The per-definition
  OpenAPI document does not mention `asOf`.
- **Fixtures.** Generated A and B have `E` (period over `E.from`/`E.to`) and `F` (the same
  attributes, no period), used by J23; `Capi` exposes neither. The parity fixture's starter declares
  a period on `master-value` (public `CodelistValue`) and none on `location`. The volume fixture's
  `Item` is dated and `Group` is not, both exposed by its definition, so dated consumer reads can be
  measured without changing it.
- **The example model.** `rdm-operators-timetables.json` dates `master-value`, `operator` and
  `location`, all exposed by its `rdm` API.

**Design.**

- **One rule** (`engine/reads/object_query.py`): the body of `as_of_predicate` becomes
  `effective_on(values, value_match, period, as_of)`, over any values entity and its relation to the
  record; `as_of_predicate` calls it. Management reads are unchanged, statement for statement.
- **Parameter** (`app/consumer/router.py`): `asOf` joins the names of get by ID, lists, XREF and
  batch resolve (not the publications list or the index). It is parsed once as a strict
  `YYYY-MM-DD` (as the management list's `CalendarDate`); anything else is `400 INVALID_AS_OF`
  (C-D79).
- **Filter** (`engine/reads/consumer_parameters.py`): `consumer_filter` takes `as_of`. With it,
  `ConsumerFilter` gains a record predicate and `as_of_applied`, the public names of the dated
  types the read can return: the exposed types, narrowed by an `objectType` parameter when sent.
  The predicate is, per dated type, its `object_type_key` and `effective_on` over
  `source.values`; the undated types pass (C-D14). It is decided from the read's model (`_Read.model`),
  so a pinned read dates by its publication's release. Because every read already applies
  `narrowed.on(record)` (lists, get by ID, XREF's kept objects, batch resolve's groups), the date
  reaches them all through the filter, and the list no longer needs `build_object_query`'s own
  `as_of`.
- **Refusals by route** (C-D77): a list of an undated type, an XREF or batch whose returnable types
  have no period, and a get by ID of an undated type's record answer `400 AS_OF_NOT_SUPPORTED`.
  Get by ID with `asOf` reads the record's type first (one indexed select) so it can tell an
  undated type (`400`) from a dated record not effective (`404 OBJECT_NOT_FOUND`).
- **Only the read's objects are dated** (C-D76): projection items, ancestors, parameter candidates
  and XREF's promoting records are read as without `asOf`.
- **Naming what was dated** (C-D78): `asOfApplied` in the list, XREF and batch resolve bodies, and
  the `RDM-As-Of-Applied` header on every answer to a dated read.
- **Cursors:** the list and XREF cursors bind `asOf` when set (`as_of_filter`), so a cursor refuses
  another date or none, and cursors issued without `asOf` stay valid for reads without it.
- **ETag:** unchanged. The date is in the URL, and the data the tag covers is the same.
- **OpenAPI** (`engine/model/consumer_openapi.py`): `asOf` on get by ID, XREF and batch resolve when
  the definition exposes a dated type, and on each list whose type is dated; `INVALID_AS_OF` and
  `AS_OF_NOT_SUPPORTED` in the refusals; `asOfApplied` in the envelopes; the header. The document
  follows `OutputContract.as_of`, which the contract check already guards.
- **No migration, no index, no setting, no model change.** The value key index serves the
  predicate, as in Q4.

**Decisions** (status per row):

| # | Question | Decision |
| --- | --- | --- |
| C-D76 | Which records `asOf` dates | **Approved 2026-10-05.** The objects the read returns, and nothing they are found through or carry: projection items, the parent and `path`, the records a parameter matches (`location=CEN`) and the records that promote an XREF score are read as without `asOf`. This is D22's answer for the model query and CONSUMER_API's text ("keeps only objects"). The cost is real in the operators example: `availableAt` there can list a location whose period has ended; a consumer that needs it can output the location's `validFrom`/`validTo` as projection fields. Dating every record of a dated type the read touches would answer "the world on that date", but needs its own decision for each of the four places above, and a declaration that turns it on can be added later without breaking this one |
| C-D77 | Refuse or filter, route by route | **Approved 2026-10-05.** As CONSUMER_API states, with three cases it leaves open. Lists: an undated list type is `400 AS_OF_NOT_SUPPORTED` before reading. Get by ID: an unknown ID is `404 OBJECT_NOT_FOUND`; a record of an undated type is `400 AS_OF_NOT_SUPPORTED`; a dated record not effective that day is `404 OBJECT_NOT_FOUND`, as a parameter that narrows it out is (C-D31). XREF: C-D14 over the types the read can return (narrowed by an `objectType` parameter); when none of them is dated, `400 AS_OF_NOT_SUPPORTED`, since an undated answer would look dated (D21's reason). Batch resolve: `asOf` is the request's query parameter and applies to every item (CONSUMER_API); each item answers as its single read, so a by-ID item of an undated type is `rejected` with `AS_OF_NOT_SUPPORTED` while a by-query item is filtered as XREF is (C-D48). A pinned read dates by the publication's release. Details: `objectTypes` (public names) and `path` `/query/asOf`. `400`, the consumer tier's status for a request error, not the management API's `422` |
| C-D78 | How a read says what was dated | **Approved 2026-10-05.** `asOfApplied` (the dated public names, sorted) in the list, XREF and batch resolve bodies, and the `RDM-As-Of-Applied` header (the same names, comma-separated) on every answer to a read that sent `asOf`, including get by ID and XREF `expect=one`, whose bodies are the bare object, as C-D23 names the workspace. Both are absent when `asOf` is not sent, so undated reads are unchanged. CONSUMER_API names `asOfApplied` for XREF only; on a list or a get by ID it holds the one type and is there so a client reads every route the same way |
| C-D79 | A malformed date | **Approved 2026-10-05.** `400 INVALID_AS_OF` at `/query/asOf` for anything but one `YYYY-MM-DD` calendar date: a time, a time zone, an impossible date, two values (several values are alternatives elsewhere, C3b, but one read has one date), as `INVALID_EXPECT` is for `expect`. In batch resolve `asOf` in `defaults` or an item is refused as `publication` there is (C-D49): the date belongs to the request |
| C-D80 | The budget | **Approved 2026-10-05.** Measured once at full volume on the volume fixture (`Item` dated, `Group` not), not tuned in C16: the dated `Item` list live and pinned (first page with a total, a deep position), a dated mixed XREF (`asOfApplied` `["Item"]`), and a dated 1,000-item batch resolve. Recorded in POSTGRESQL_BUDGETS §7 beside the undated figures. A read over 100 ms, or the batch over C-D53's 1 s, is reported with its cause and options, and the next step is the user's. `test_consumer_list_volume` and `test_consumer_xref_volume` each gain a dated read, holding their statement counts at both sizes: the predicate adds none, get by ID one |

**Journey.** J23 gains its consumer variants in USER_JOURNEYS and API_JOURNEYS: **J23.6** a
consumer list and get by ID on a date, page by page; **J23.7** XREF and batch resolve across dated
and undated types with `asOfApplied`; **J23.8** the refusals. J23's status becomes delivered on both
APIs. Generated A and B's `Capi` exposes `E` (`Rate`) and `F` (`Fee`) with the lists `rates` and
`fees`, so the variants run on both configurations; the seeds rebuild once. Each test has its own
database clone, so the types' records do not reach J28 or J29. `test_consumer_api_model`'s pinned
contract for `Capi` gains the two types.

**Test cases** (journey tests, written first and confirmed failing):

Given, on generated A and B, J23's records: `E` "Old rate" ending 2026-07-01, "New rate" from
2026-07-01, "Standing rate" with no period values, "Future rate" from 2027-01-01, and "Transitional
rate" from 2026-06-15 to 2026-07-15; an `F` "Flat rate"; an `R` "Rate ledger".

1. **J23.6 A list on a date, page by page.** `lists/rates?asOf=2026-06-30&pageSize=1`, followed by
   its cursors, holds Old, Standing and Transitional; at `2026-07-01` (the boundary) New, Standing
   and Transitional, not Old. The body has `asOfApplied` `["Rate"]` and the header says `Rate`. The
   first cursor sent with another date, or none, is `400 INVALID_CURSOR`. `lists/fees?asOf=…` is
   `400 AS_OF_NOT_SUPPORTED` naming `Fee`.
2. **J23.6 Get by ID.** Old rate at `2026-06-30` answers it, with the header; at `2026-07-01`
   `404 OBJECT_NOT_FOUND`; the fee with `asOf` is `400 AS_OF_NOT_SUPPORTED`; an unknown ID
   `404 OBJECT_NOT_FOUND`. Without `asOf` all three rates answer and no header is sent.
3. **J23.6 Pinned.** After a publication, New rate's start is moved live to 2026-08-01:
   `lists/rates?publication=latest&asOf=2026-07-15` holds New rate, the live list on that date does
   not.
4. **J23.7 XREF across types.** `xref?query=rate&asOf=2026-06-30` holds Old, Standing,
   Transitional, Flat rate and Rate ledger, not New or Future, each with the score it has without
   `asOf`, and `asOfApplied` `["Rate"]`. With `kind=Ledger` it is `400 AS_OF_NOT_SUPPORTED`.
   `query=New rate&expect=one` is `404 NO_MATCH` at `2026-06-30` and answers New rate at
   `2026-07-01`, with the header.
5. **J23.7 Batch resolve.** `POST resolve?asOf=2026-06-30`, items "Old rate", "New rate", the fee by
   ID and Old rate by ID: `found`, `not_found`, `rejected` (`AS_OF_NOT_SUPPORTED`), `found`; each
   equals its single read's answer; the body has `asOfApplied`.
6. **J23.8 Refusals.** `asOf=2026-06-30T00:00`, `2026-02-30` and `2026-06-30,2026-07-01` are
   `400 INVALID_AS_OF` at `/query/asOf` on a list, a get by ID, XREF and batch resolve; `asOf` on
   the publications list is `400 PARAMETER_NOT_SUPPORTED`; in a resolve item it rejects the item,
   in `defaults` the request.
7. **Parity scenario 15** (the parity module, on the reference-shaped model). Swiss franc ends
   2026-07-01 and a replacement value "Swiss franc 2026" starts that day; an overlapping value runs
   across it. `lists/all-values?codelist=CUR&asOf=…` on each side, at the boundary and across the
   overlap; `xref?query=CHF&asOf=…` answers the value effective that day, `asOfApplied`
   `["CodelistValue"]`, with a location still found undated; get by ID of a location with `asOf` is
   `400 AS_OF_NOT_SUPPORTED` (SC-11's "an unconfigured list must not invent effective-date
   behaviour"). Every `200` validates against the definition's OpenAPI document, which now declares
   `asOf`.

**Unit tests:** `test_consumer_openapi` gains one: `asOf` documented on `lists/rates` and not on
`lists/fees`, the header and `asOfApplied` declared. `effective_on` has no case of its own: it is
`as_of_predicate`'s body, which `test_effective_periods` and J23.1–J23.5 walk unchanged.

Not covered by a case: a publication made under a release where the type had no period (the read is
refused, as the design says). Building it needs a release removing the period, which is
`version_required` and then fails on the contract version; the design's one line (`_Read.model`) is
its evidence.

**Checks:** J23 (all variants, since `as_of_predicate` is reshaped), J28, J29, J25, J20 and the
parity module on their configurations; `test_effective_periods`, `test_consumer_openapi`,
`test_consumer_api_model`; `test_consumer_list_volume` and `test_consumer_xref_volume`; then the
`consumer` group once; the C-D80 measurement once; `ruff`. Not `startup` (no migration), not
`contract` (the consumer routes are outside the management document, and no management route
changes), not the frontend (unchanged).

**Exit:** SC-11 passes through the consumer API; parity scenario 15 passes; C-D80's figures are
recorded.

**Docs at delivery:** API.md: `asOf` on the four consumer routes, `INVALID_AS_OF`,
`AS_OF_NOT_SUPPORTED`, `asOfApplied` and the header; CONSUMER_API: C-D76–C-D80 recorded, "Business
dates" amended (codes in upper case, get by ID's `404`, the refusal for an XREF with no dated type,
`asOfApplied` on every collection), the C16 row delivered; ACCEPTANCE_SCENARIOS: SC-11's consumer
half delivered; USER_JOURNEYS and API_JOURNEYS: J23.6–J23.8; CURRENT_FUNCTIONALITY: a consumer can
read a list as it stands on a business date; POSTGRESQL_BUDGETS §7: the dated rows.

**Composable domains (ADR-032):** the `match` declaration is untouched (dating does not change a
score), and so are identity, attribute storage, audit, the bulk APIs and mapping coverage. A product
catalogue's "the price list valid on 1 July" is a declared period on its price type read through
the same parameter, so the door is used, not narrowed; C-D76 leaves dated projections as a later,
additive declaration.

##### C16 delivery record

**Delivered 2026-10-05**, as designed, with C-D76–C-D80 and the approved cases.

- **One rule** (`engine/reads/object_query.py`): `effective_on(values, value_match, period, as_of)`
  is ADR-038's rule over any values table; `as_of_predicate` calls it, so management statements are
  unchanged.
- **Filter** (`engine/reads/consumer_parameters.py`): `consumer_filter` takes `as_of`. The record
  predicate is an AND, per dated exposed type, of `effective_on` with the type test inside each
  `NOT EXISTS` (records of other types pass), over a fresh alias of the source's values (so its
  subqueries never correlate with a values table the enclosing statement reads). `ConsumerFilter` carries `as_of`, `dated` (the exposed types with a
  period), `returnable` (the exposed types, narrowed by an `objectType` parameter) and
  `as_of_applied`. `as_of_not_supported` is the one refusal.
- **Reads:** lists refuse an undated type and bind `asOf` into the cursor (`as_of_filter`); get by ID
  reads the record's type first (`consumer_objects.undated_refusal`, one statement, only with
  `asOf`); XREF refuses when no returnable type is dated and binds the date into its cursor; batch
  resolve takes the request's date, rejects a lookup with no dated type and a by-ID item of an
  undated type (pointer at the item, or its `id`), and reads the by-ID types in one statement per
  parameter group. Lists, XREF pages and batch resolve carry `asOfApplied`.
- **Router** (`app/consumer/router.py`): `asOf` joins the names of get by ID, lists, XREF and batch
  resolve; `_as_of` parses one `YYYY-MM-DD` day (`400 INVALID_AS_OF`); `_Read` keeps the filter it
  built, and `_answer` sets `RDM-As-Of-Applied` on a dated answer: the body's `asOfApplied`, the
  record's type for get by ID, the read's dated types for `expect=one`.
- **OpenAPI** (`engine/model/consumer_openapi.py`): `asOf` on get by ID, XREF and batch resolve when
  the definition exposes a dated type, on a list when its type is dated; the two codes, the header
  and an optional `asOfApplied` on the three envelopes.
- **Fixtures:** generated A and B's `Capi` exposes `E` (`Rate`) and `F` (`Fee`) with the lists
  `rates` and `fees`; the seeds rebuilt once. J23.5's release removing `E`'s period now raises
  `Capi`'s contract version, since `E` is exposed (Q4's contract rule). J20.4's literal paths gain
  the two lists. `JOURNEY_GROUPS` maps J23 to `consumer` as well as `queries`, so `-m consumer`
  selects the consumer variants (the J29 defect C8 found, avoided).

**Differs from the plan:**
- The dated XREF volume scenario reads 10 a page: at the smallest test shape the lookup holds 18
  results, under one 20-row page, which the pager counts without its count statement, so the
  statements differed by one between sizes; with 10 a page both sizes page (T1 met the same with its
  dated hop).
- A batch item refused for its date points at the item (a lookup) or its `id` (a by-ID item), since
  `asOf` is not in the item.
- `test_api_journeys` needed the code listed in its own backticks; API_JOURNEYS records it so.

**The first full-volume run** (`volume_baseline.py --only-consumer --scale 1 --repeat 3`; one earlier
attempt was killed when another pytest session dropped its database) found the dated lists far over
budget: the first page with a total 1,325 ms live and 1,821 ms pinned, the position jump 612 and
859 ms. Cause (`EXPLAIN ANALYZE` on the full seed): the predicate was written as an OR over the types
("undated, or this type and effective"), which PostgreSQL cannot turn into anti-joins, so the count
over C3a's first part walked all 257,758 rank values with two per-row subqueries (1,230 ms of the
read). With the user's agreement the predicate became an AND with the type test inside each check:
the same statement plans hash anti-joins and takes 150 ms (72 ms undated). J23, the parity module,
the consumer volume tests and `test_effective_periods` were rerun (63 passed).

**C-D80's figures** (full volume, after the fix; list and XREF scenarios and the identifiers batch,
dated and not, measured once with `--repeat 3`; warm median · statements · ORM rows):

| Read | Live | Pinned to a publication |
| --- | --- | --- |
| List: dated, first page with `includeTotal` | **192.3 ms** · 12 · 24 | **201.4 ms** · 14 · 5 |
| List: dated, position jump to the middle | **204.1 ms** · 11 · 24 | **231.9 ms** · 13 · 5 |
| List: undated, position jump / ancestor filter with total (same run) | 110.7 / 99.8 ms | 118.2 / 118.6 ms |
| XREF: a group's code, dated (10 a page) | 72.3 ms · 9 · 3 | 85.8 ms · 11 · 5 |
| Batch resolve: 1,000 identifiers, dated (budget 1 s) | **2,224.9 ms** · 10 · 3 | — |
| Batch resolve: 1,000 identifiers, undated (same run) | 265.6 ms · 8 · 3 | — |

Every other consumer read is within a few ms of POSTGRESQL_BUDGETS §7. Over budget, recorded and not
tuned (C-D80):
- **The dated lists** count or skip 75,000 dated records (three quarters of 100,000 effective):
  twice the undated read, the shape of T1's dated totals ([E8](POSTGRESQL_BUDGETS.md#e8-dated-totals-and-change-set-dated-pages-0-9-t1)).
- **The dated batch** runs two statements more: the by-ID type read, and a contains pass. A quarter of
  the identifiers name a record not effective on the date, so their exact match is filtered out and
  exact-first (C-D52) cannot settle them; their contains matches are read, 3–5 ms per term and rule.
  This is C14's recorded "parameters filtering items out" shape (2.4–2.6 s), reasoned from the
  statement count, not profiled. A file of codes valid on the date settles as the undated batch does.

**Checks:**
- **After the predicate fix:** J23, the parity module, `test_consumer_list_volume`,
  `test_consumer_xref_volume` and `test_effective_periods`: 63 passed.
- **Failing first:** the 12 new J23 cases (J23.6–J23.8, on generated A and B) failed with the app
  changes stashed (`UNKNOWN_PARAMETER`), J23.1–J23.5 passing with the fixture change; parity scenario
  15 failed the same way; the new `test_consumer_openapi` case failed (1 of 2). All pass with C16.
- **Targeted:** J23 (24 passed); the parity module's scenario 15; `test_consumer_openapi` (2);
  `test_consumer_list_volume` and `test_consumer_xref_volume` (4: equal statements at both sizes
  with the dated reads); the `consumer` group in parallel, 215 passed in 40 s (before J23 joined it; with J23 the group holds
  246, the guide's `queries` count restated as 247);
  `test_effective_periods`, J20, `test_api_journeys`, `test_error_codes` and `test_boundaries`
  together: 40 passed and 3 failed (J20.4's pinned list paths, the new code unlisted), fixed, then J20
  and `test_api_journeys` 17 passed; J18, J08 and the composed J24/J26 (which edit the generated
  model or use `E`): 34 passed.
- `ruff check app/ tests/`: clean.
- **Not run:** `startup` (no migration), `contract` beyond the modules above (the consumer routes are
  outside the management document), the rest of `queries` (`as_of_predicate`'s statements are
  unchanged; `test_effective_periods` and J23 cover it), the frontend (unchanged), the full suites
  (R).

**Composable domains (ADR-032):** the `match` declaration, identity, attribute storage, audit, the
bulk APIs and mapping coverage are untouched; a price list valid on a date reads through the same
parameter.

#### C9: Event definitions

**Delivered 2026-10-05** ([record](#c9-delivery-record)). Planned 2026-10-05; decisions C-D81–C-D86
approved by the user the same day, the test cases with the instruction to deliver.
**Needs:** C2 (events are about the shared object and its projections); built on C1's validation
and contract check. **Groups:** `consumer`, `model`.
**Design:** [CONSUMER_API "Event definitions (model)"](CONSUMER_API.md#event-definitions-model),
"What counts as a change", C-D2, C-D7, C-D8, C-D11; INTEGRATION_API F6.

**Behaviour.** A model author declares, in a consumer API definition, which changes its consumers are
told about: which exposed types, which kinds of change, and for an update which outputs count. The
release validates the declaration at its JSON pointer, and the contract check guards it, so a
release cannot quietly stop telling a consumer what it relied on. Nothing is derived or delivered
yet: C9 is the declaration only, as C1 was for the reads.

```jsonc
"events": [{
  "key": "reference-data-changed",
  "objectTypes": ["master-value", "codelist", "location"],
  "changes": ["created", "updated", "deleted"],
  "watch": {
    "fields": ["masterId", "code", "name", "isActive", "validFrom", "validTo", "valueName"],
    "projections": ["systemVariants", "translations"]
  }
}]
```

- An author drafts a definition with `events`, compiles it and sees each mistake at its pointer;
  installs and activates it; reads it back in the model.
- A later draft that removes an event, or makes one tell less, is `version_required`, as removing a
  field is; one that tells more is compatible.
- Consumers see no change on the wire in C9: no event is produced, and the pull feed, its OpenAPI
  path and subscriptions arrive with C10 and C11. C9 fixes the contract they implement.

**What exists today** (checked 2026-10-05):

- **`events` is refused** as an unknown field (`ConsumerApiDefinition` is `extra="forbid"`), pinned by
  `test_consumer_api_model` (`unknown_field` at `/consumerApis/0/events`) and stated in CONSUMER_API's
  "Not yet" line.
- **Validation** (`engine/model/validation/consumer_api_rules.py`, `_Definition.check`) already
  knows every output name of a definition (`_check_object` returns them, `_check_projections`
  checks them), the exposed types and the URL key rule (`_URL_KEY`) that lists use.
- **The contract** (`engine/model/consumer_contract.py`) derives `OutputContract` and compares two
  with `_breaking_changes`; events are a new part of both.
- **CONSUMER_API's example** names `watch.fields` by role (`id`, `active`) and attribute key
  (`valueName`) mixed, while the event body reports `changed` by output name (`systemVariants`). Under
  the reference definition the roles' outputs are `masterId` and `isActive`, so the example cannot
  mean both (C-D81).
- **No route, migration or frontend** reads a consumer definition's events; the frontend reads no
  `consumerApis` at all. The operators example model declares a consumer API without events.

**Design.**

- **Shape** (`models/schema.py`): `ConsumerEvent` with `key`, `objectTypes` (model keys, at least
  one), `changes` (`created`, `updated`, `deleted`, at least one) and an optional `watch`
  (`ConsumerEventWatch`: `fields` and `projections`, each a tuple of names, omitted when empty).
  `ConsumerApiDefinition.events` is a tuple, default empty and omitted from the canonical document
  when empty, so releases without events keep their hash (as `lists` and C1's optional parts).
- **Rules** (`consumer_api_rules._Definition._check_events`, after the lists), each refused with
  `INVALID_MODEL` (or `DUPLICATE_KEY`, `UNKNOWN_OBJECT_TYPE`, as C1 names them) at
  `/consumerApis/<key>/events/<event>/…` (C-D84). The output names come from `_check_object`'s
  result, so watch and the object read one list.
- **Contract** (`consumer_contract.OutputContract.events`): per event key its types, changes and its
  watched names (`None` for "every output"); `_breaking_changes` reports what C-D85 lists at
  `/events` or `/events/<event>/{objectTypes,changes,watch}`.
- **Reserved names** (`RESERVED_PARAMETERS`): `event` and `after`, which the pull feed's URL takes
  beside the definition's parameters (C-D86).
- **The meaning of an event** (C-D82, C-D83) is decided here and written into CONSUMER_API, since the
  contract check depends on it (a narrower watch is breaking because a receiver hears less). C10
  implements it; C9 adds no runtime code.
- **No migration, no route, no setting, no frontend.** The management OpenAPI lock should not change
  (the model document is not typed in it); checked once.

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D81 | What `watch.fields` names | **Approved 2026-10-05.** The object's **output names**, as a consumer reads them and as an event's `changed` reports them: each role's `output` (`masterId`, `isActive`), each attribute field's name, the `parent`, `path` and `hierarchy` outputs, and `objectType`, which every object carries. Not role names or model keys: the author would write one name and the receiver read another. `watch.projections` names projections (also output names). CONSUMER_API's example is amended to `masterId` and `isActive` |
| C-D82 | When an object counts as `updated` | **Approved 2026-10-05.** When a read of the object by ID would answer differently in a watched output (every output without `watch`), for a change in live data. That includes changes in other records the object shows: its parent's fields, an ancestor's name in `path` or `hierarchy`, a projected record's declared fields (and its ancestors' through `ancestor:`), and a projection gaining or losing an item, also when the relation itself was deleted ("What counts as a change"). So renaming a codelist makes `updated` for each of its values that watches `path` or `parent`: one event per affected object, batched in delivery (C12). Not a change: a period starting or ending with no data change (no write happens), edits in a change set, model releases. The alternative, counting only the object's own record and its projection membership, is cheaper for C10, but a receiver caching `path` would never learn it is stale; an author who does not want the fan-out leaves `path` and `parent` out of `watch`. C10 measures the fan-out of renaming a large container |
| C-D83 | A type change (ADR-034, `reclassified`) | **Approved 2026-10-05.** No fourth change kind. Seen from one event: an object whose type moves out of the event's `objectTypes` (or out of the definition) is `deleted`; one moving in is `created`; one moving between two of its types is `updated` with `objectType` among the changed outputs. A receiver then needs only the three kinds the declaration names, and 0.8 D37's requirement that consumer APIs represent `reclassified` is met by this mapping |
| C-D84 | Declaration rules | **Approved 2026-10-05.** Event keys are unique in a definition and URL-safe (lowercase letters, digits, hyphens; the subscription body and the pull feed's `event=` carry them), as list keys. `objectTypes`: at least one, each exposed by the definition, no repeats. `changes`: at least one of the three, no repeats. `watch`, when given, names at least one output or projection, each declared, no repeats; refused when `changes` has no `updated`, since it could never act (C-D45's pattern). Shape errors (an unknown change kind, a wrong JSON type) are reported at their position, as other shape errors are (`/consumerApis/0/events/0/changes/0`) |
| C-D85 | What in an event is contract | **Approved 2026-10-05.** A receiver depends on being told. Breaking (`version_required`): removing an event; removing a type or a change kind from it; removing a watched name, or adding `watch` where there was none (both mean fewer events). Compatible: adding an event, a type, a change kind or a watched name, and dropping `watch` (more events; receivers already tolerate repeats and unknown objects, at-least-once). An output removed from the object is already breaking as a field (C-D2), so a watch naming it adds no second diagnostic. This states C-D2's "removing an event, or narrowing its types or changes" for `watch` too |
| C-D86 | Names the pull feed takes | **Approved 2026-10-05.** `event` and `after` join the reserved parameter names now, since `GET …/events?event=…&after=…&{parameters}` puts them beside the definition's parameters (C10). A definition parameter so named would be shadowed. Checked: no fixture, example or starter declares a parameter with either name. Pre-1.0, a definition that did would be refused at activation with the pointer, as C3 reserved `from`, `seek` and `includeTotal` |

**Journey.** J25 gains **J25.3** (declare events) and **J25.4** (events in the contract) in
USER_JOURNEYS; J25's status says events are declared from C9 and produced from C10. No new route or
code, so API_JOURNEYS changes only J25's row text. Generated A and B's `Capi` is unchanged: the cases
add events to a draft, as J25's other cases change `Capi` in a draft, so no seed rebuilds. The parity
fixture's `_reference_definition` gains CONSUMER_API's event (with C-D81's names), so the printed
example is validated whole, as C8 did for the definition; its small seed rebuilds once, and C13 can
use it.

**Test cases** (journey tests on generated A and B, written first and confirmed failing: today
`events` is an unknown field):

1. **J25.3 Declare events.** A draft gives `Capi` two events: one over `R` and `R2` with all three
   changes, watching `Capi.code`, `Capi.name`, `Capi.parent` and the projection `Capi.B11`; one over
   `D` with `created` and `deleted` and no `watch`. It compiles valid and `compatible` against the
   active release (adding events), installs and activates, and the model read returns both events
   as declared.
2. **J25.3 Refusals,** each a draft compiled invalid and its installation refused `422
   INVALID_MODEL` at its pointer under `/consumerApis/<Capi>/events/<event>`: a type not exposed
   (`K`) and an unknown type (`…/objectTypes`); a repeated event key and a key with an upper-case
   letter (`…/key`); `changes` empty, and a repeated kind (`…/changes`); `watch.fields` naming a role
   rather than its output (`active` where `Capi.active` is `isActive`) and an unknown name
   (`…/watch/fields`); an unknown projection (`…/watch/projections`); an empty `watch` and a `watch`
   with only `created` and `deleted` (`…/watch`). An unknown change kind (`renamed`) is a shape error
   at `/consumerApis/<n>/events/0/changes/0`. A parameter named `event` or `after` is refused as
   reserved at `…/parameters/<name>`.
3. **J25.4 Events in the contract.** With case 1's events active at contract version 1, drafts at
   the same version: removing the `D` event (`/events`), removing `R2` from the first
   (`…/objectTypes`), removing `deleted` from it (`…/changes`), removing `Capi.parent` from its
   watch and adding a watch to the `D` event (`…/watch`) are each `version_required` at their path,
   and activation of one is refused `409 CONSUMER_CONTRACT_VERSION_REQUIRED`; with contract version
   2 it activates. Adding a third event, adding `E` (`Rate`, exposed since C16) to the first event's
   types, adding `updated` to the `D` event, adding `Capi.n` to the watch and dropping the first
   event's `watch` are each `compatible`.
4. **Changed:** `test_consumer_api_model`'s case pinning `events` as `unknown_field` is replaced by a
   round trip: a definition with events keeps its canonical hash across compile and read, and one
   without events keeps the hash it has today.

No unit tests: the rules are table-like and walked by case 2 on two configurations; the contract by
case 3. **Checks:** J25 and the parity module on their configurations (the parity seed's rebuild
validates the printed event); `test_consumer_api_model`; the `consumer` and `model` groups once;
`test_openapi_contract` once (expected unchanged); `ruff`. Not run: `startup` (no migration),
`volume` (no read or write path changes), `feed` (nothing derived yet), `contract` beyond the lock,
the frontend (unchanged), the full suites (R).

**Exit:** a release declares events, validated at their pointers and guarded by the contract check;
CONSUMER_API states what an event means (C-D82, C-D83), which C10 implements.

**Docs at delivery:** CONSUMER_API: "Event definitions" amended (output names, the rules, the
contract, the meaning of `updated` and of a type change), the reserved names gain `event` and
`after`, the "Not yet: `events`" line removed, C-D81–C-D86 recorded, the C9 row delivered;
APPLICATION_MODEL: `events` in the schema 0.8 section; USER_JOURNEYS: J25.3, J25.4 and J25's
status; CURRENT_FUNCTIONALITY: a consumer API declares its change events (produced from C10).

**Composable domains (ADR-032):** the declaration is generic: types, outputs and projections of any
definition, with no branch on a key. A product catalogue telling shops that a price or a supplier
link changed is an event over its exposed types watching those outputs, so the door is used, not
narrowed. Identity, attribute storage, audit, the bulk APIs, the `match` declaration and mapping
coverage are untouched; audit stays the outbox C10 reads (C-D8).

##### C9 delivery record

**Delivered 2026-10-05**, as designed, with C-D81–C-D86.

- **Shape** (`models/schema.py`): `ConsumerEvent` (`key`, `objectTypes`, `changes`, optional
  `watch`) and `ConsumerEventWatch` (`fields`, `projections`); `ConsumerApiDefinition.events`. Empty
  `events`, `fields` and `projections` are left out of the canonical document, so a definition
  without events keeps its hash (the operators example and every installed release).
- **Rules** (`consumer_api_rules._Definition._check_events`): C-D84 over the outputs `_check_object`
  returns, plus `objectType`; `event` and `after` in `RESERVED_PARAMETERS` (C-D86).
- **Contract** (`consumer_contract`): `OutputContract.events` of `EventContract`s;
  `_event_changes` reports C-D85's narrowings at `/events` or `/events/<event>/{objectTypes,changes,watch}`.
- **Fixtures:** the parity configuration's definition carries CONSUMER_API's event (seed rebuilt
  once, 0.6 s). Generated A and B are unchanged; the J25 cases add events in drafts.
- **Docs:** CONSUMER_API ("Event definitions" with C-D81–C-D85, the reserved names, C-D81–C-D86, the
  C9 row), APPLICATION_MODEL, USER_JOURNEYS (J25.3, J25.4, J25's status), CURRENT_FUNCTIONALITY,
  EXECUTION_GUIDE's `consumer` and `model` counts (254 and 348; `model` had read 302 since before
  C9), CHANGELOG, PROJECT_STATUS, TODO.

**Differs from the plan:**
- A repeated event key is refused at `/events/<event>` (`DUPLICATE_KEY`), as a repeated list key is,
  not at `…/key`; a key with an upper-case letter at `…/key`, as planned.
- J25.4's compatible additions add `E` (exposed since C16) to an event's types; the plan first named
  `K`, which `Capi` does not expose.

**Checks:**
- **Failing first:** the six J25.3 and J25.4 cases (generated A and B) and the two
  `test_consumer_api_model` round trips failed (`events` an unknown field); all pass.
- **Targeted:** J25, the parity module and `test_consumer_api_model`: 127 passed.
- **Groups** `consumer` and `model` in parallel: 487 passed in 51 s; their serial part selects none.
- `test_openapi_contract` (8) and `test_api_journeys` (5) passed, the lock unchanged.
- `ruff check app/ tests/`: clean.
- **Not run:** `startup` (no migration), `volume` (no read or write path changed), `feed` (nothing
  derived), the frontend (unchanged), the full suites (R).

#### C10: Event deriver, event store and pull feed

**Delivered 2026-10-06** ([record](#c10-delivery-record)). Planned 2026-10-05. Decisions C-D87–C-D92
approved by the user the same day (C-D89 with a note, amended in delivery), and C-D7 and C-D12
revised with C-D91 amended (full-object payloads, signing in 0.9); C-D95 found and decided in
delivery.
**Needs:** C9 (the declaration and what an event means, C-D82, C-D83), F2 (positions, the retention
floor and the `410` baseline). **Groups:** `feed`, `consumer`, `startup` (migration), `contract`
(route), `volume` (deriver cost, C-D82's fan-out, once).
**Design:** CONSUMER_API "What counts as a change", "Event definitions", "Delivery", "Pull feed", "How
events are produced"; C-D7 (revised), C-D8, C-D9, C-D11, C-D15, C-D16; INTEGRATION_API F3–F6; D40.

**Behaviour.** After a change to live data commits, the engine turns its feed entries into the
consumer events its definitions declare, in position order and without the write waiting. An
integrator reads them per consumer API, filtered like a list, and resumes where it stopped:

```text
GET /api/consumer/{consumerApi}/v{contractVersion}/events?workspace=…&event=…&after=…&cursor=…&pageSize=…&payload=…&{parameters}
```

```jsonc
{
  "workspace": "main",
  "items": [{
    "eventId": "…", "position": 184223, "occurredAt": "2026-10-06T10:14:03Z",
    "event": "reference-data-changed", "change": "updated", "contractVersion": 1,
    "objectType": "CodelistValue", "id": "…", "code": "…", "name": "…",
    "changed": ["path", "parent"],
    "cause": { "kind": "publication", "id": "…" },
    "stateAt": 184230,      // payload=full (default): the object as get-by-ID answers it, at this position
    "object": { "masterId": "…", "code": "…", "name": "…", "path": [ … ], "translations": [ … ] }
  }],
  "cursor": "…",            // resume token: the next page, or the next poll when caught up
  "caughtUp": false,
  "headPosition": 184230,   // the position events are derived up to
  "earliestPosition": 170001
}
```

- A live write, a batch and a publish make events; change-set work, model releases and refused or
  rolled-back writes make none (the audit log is the outbox, C-D8).
- Renaming a container makes `updated` for each object below it that shows its name (`parent`,
  `path`, `hierarchy`, an `ancestor:` field of a projection), one per object (C-D82).
- An expired position answers `410 EVENTS_EXPIRED` naming the active publication and its
  `eventSequence`; the receiver reads the publication's lists and follows on from there (C-D15).
- Each event carries the object as get-by-ID answers it, so a receiver keeping a copy never calls
  back; `payload=identity` leaves it out (C-D7 revised). A `deleted` event has no object.

**What exists today** (checked 2026-10-05):

- **The outbox.** Each live change's audit entry has `workspace_key`, `feed_position`,
  `model_release_id`, `cause_kind`/`cause_id` and `feed_subject` (object type and application, or a
  relation's type and both ends, kept for after a delete). Live entries keep values in `changes`
  (`name` from and to, `attributes`); publish entries keep names only (`changedFields`,
  `attributeTypeKeys`, D15, D16). `management/presenters._changed` reduces both to names, in the
  management tier, which the engine cannot import.
- **Deletes.** An object's delete entry holds its type and cascade root, a relation's its type and
  ends; neither holds `code` or `name`, and after commit the record is gone.
- **The raw feed read** (`engine/reads/feed.read_feed`, `_time_floor`) computes the retention floor
  (D40) and the `410` baseline; the deriver and the pull feed reuse the rule.
- **Releases.** `ModelRegistry.resolve_release` resolves any installed release, not only the active
  one.
- **Consumer reads.** `ConsumerObjects` composes outputs from roles, attribute fields, `parent`,
  `path`, `hierarchy` and projections (with `ancestor:` fields); `consumer_parameters.consumer_filter`
  turns parameters into SQL predicates over a live record alias; `consumer/etag.entity_tag` tags a
  read by its data version; `consumer_contract` holds C9's `EventContract`s.
- **The job worker** (`engine/jobs/worker.py`) is an in-process thread started in the lifespan, with
  an hourly sweep; tests drive it themselves (`run_job_worker` False, `run_until_idle`).
- **The volume fixture** has a heavy group of 20,000 items and a consumer definition
  (`volume_baseline.consumer_scenarios`), so C-D82's container rename can be measured there.
- **Nothing** derives or stores consumer events; there is no `/events` route, and the per-definition
  OpenAPI has no events path.

**Design.**

- **One vocabulary.** `_changed` moves to `engine/records/feed.changed_names`; the presenters import
  it. The feed's answer does not change.
- **Impact plan** (`engine/events/plan.py`), compiled once per release and definition with events and
  cached by release: for each kind of raw change, which objects it reaches and which outputs it
  changes. Built only from the definition's sources, so nothing branches on a key:
  1. an exposed record's own change: `created`, `deleted`; for `updated`, the outputs whose sources
     are among the changed names (`name`, attribute keys; a move changes `parent`, `path` and
     `hierarchy`); a type change by C-D83;
  2. a record the `parent` block reads (its `code` sources, `name`, type): its exposed children's
     `parent`;
  3. a record `path` or `hierarchy` names: its exposed descendants at any depth;
  4. a projected record whose read fields changed: the owners through the projection's relation, the
     projection named;
  5. an ancestor an `ancestor:` field reads, renamed, or a projected record moved: the projected
     records below it, then their owners;
  6. a relation of a projection's type created or deleted: the owner end (its ends are in the entry).
- **Deriver** (`engine/events/deriver.py`): per workspace, the entries after its checkpoint up to the
  head, 500 at a time, in one REPEATABLE READ transaction. Entries are grouped by their release
  (C-D88); each impact is one set statement (owners through relations, descendants through a recursive
  query on `parent_object_id`), and the events go in with `INSERT … SELECT`, never row by row. One
  event per position, definition, event and object, its `changed` merged, kept only when the event's
  `objectTypes`, `changes` and `watch` take it (C-D82, C-D87). `code` and `name` are read in the same
  statement (C-D89). Events and the checkpoint commit together, so a crash repeats and skips nothing;
  `eventId` is a UUIDv5 of the entry's `eventId`, the definition, the event and the object, so a
  derivation repeated from the same state gives the same IDs.
- **Store** (migration `20261006_01_consumer_events`): `consumer_events` (`event_id` unique,
  `workspace_key`, `consumer_api`, `contract_version`, `event_key`, `position`, `ordinal`, `change`,
  `object_id`, model type key and public name, `code`, `name`, `changed`, cause, `occurred_at`,
  `model_release_id`), unique on (`workspace_key`, `consumer_api`, `position`, `ordinal`), which is
  also the read's index. `consumer_event_checkpoints` (`workspace_key` key, `position`): the migration
  starts each workspace by C-D92; a new workspace starts at 0.
- **Running it** (`engine/events/worker.py`): a thread beside the job worker, started in the lifespan
  when the registry is ready. Once a second it compares each workspace's feed position with its
  checkpoint (one statement) and derives where they differ; the write path is untouched. It locks a
  workspace's checkpoint row `FOR UPDATE SKIP LOCKED`, so two processes never derive one range, and
  takes no workspace lock, so a write never waits for it. Tests drive it (`run_event_deriver` False,
  `run_until_idle`).
- **Retention:** the hourly sweep deletes events below the raw feed's floor (`FEED_RETENTION_DAYS`,
  never past the active publication's position + 1, D40) with one `DELETE` per workspace. The audit
  log is not pruned.
- **Pull feed** (`engine/reads/consumer_events.py`, the route in `consumer/router.py`), paged and
  filtered by C-D90 and C-D91. With `payload=full` the page's objects are composed by get-by-ID's code
  (`ConsumerObjects.compose` over the page's object IDs, one call per page, the request's parameters
  applied as on a list), under the contract version served; `stateAt` is the feed position read with
  them, as the `ETag` reads it. An event whose object no longer exists has no `object` (every
  `deleted`, and an earlier event of an object deleted since, whose own `deleted` follows). With
  `payload=identity` nothing is composed. `payload` joins the
  reserved parameter names (C-D86's list); no model or fixture declares a parameter so named
  (checked 2026-10-05). An unknown `event` is `400 UNKNOWN_EVENT`; a definition without events
  `404 EVENTS_NOT_DECLARED`; `after` past the raw feed's head `409 EVENT_POSITION_AHEAD` (a position
  derived later is not ahead: the page is empty and `caughtUp` true); an expired one `410
  EVENTS_EXPIRED` (C-D92). The `ETag`'s data version is the checkpoint, so a poller gets `304` until
  a new event is derived.
- **Contract documents:** a definition with events gets `GET …/events` in its OpenAPI, with its
  parameters, `payload` and the event item, whose `object` is the definition's object schema (present
  with `payload=full`); the API index is unchanged. The management OpenAPI lock should not
  change; checked once.
- **No frontend, no setting** (retention is shared; the pull feed is a consumer read, ungated until
  0.12).

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D87 | How the deriver knows a watched output changed | **Approved 2026-10-05.** From the names the entry records (the feed's changed fields and attribute types), not by comparing values: an output changed when one of its sources is among them. Publish entries keep names only (D15, D16), so values cannot be compared for every entry. So an `updated` may name an output whose answer stayed the same (a value rewritten unchanged; a second source written while the first is set); receivers re-read, as at-least-once already asks. The alternative, before and after values in every entry, changes the write path C-D8 keeps unchanged and copies values the erasure door wants kept out of the feed |
| C-D88 | Which release an entry is derived under, and which events a version serves | **Approved 2026-10-05.** The release the entry was written under (`model_release_id`), so an activation between a write and its derivation cannot change its events. Each event keeps its definition's `contractVersion`. The pull feed at `v{N}` serves every event of the consumer API, whatever version derived it, each naming its own: serving only vN's would drop, without a word, the changes made just before a version change from a receiver resuming across it (principle 6). Reading `v{N}` once it is no longer installed stays `404 CONTRACT_VERSION_NOT_FOUND`, as for reads |
| C-D89 | What owners and identity are read from | **Approved 2026-10-05.** _Amended 2026-10-05 (found in delivery), by the user:_ `code` and `name` are not stored with the event; they are read when a page is read or a batch sent, by the same read as the full object (C-D7 revised), so the event store keeps no values (the erasure door is untouched) and the value encoding is not repeated in SQL. Owners are still resolved at derivation. Approved originally with the user's note that a deletion must say so: a `deleted` event always carries `change: "deleted"` with the object's `id` and public `objectType` (both kept in the entry), and only `code` and `name` are `null`. Live data when the deriver runs, a moment after commit, not the state at the entry's position. A projected record's owners are its relations then; one deleted since is an entry of its own naming the former owner, so no owner is missed, only reached at the later position. `code` and `name` are the object's values then, `null` when it no longer exists (always for `deleted`: the entry holds no values, D16). The alternative, deriving inside the write's transaction, sees the exact state but puts C-D82's fan-out on the write path, which C-D8 rules out |
| C-D90 | How the pull feed's parameters filter | **Approved 2026-10-05.** Against live data at the read, through the lists' predicates (C3) on the event's object; `objectType` against the type stored with the event. An event whose object no longer exists (every `deleted`) passes every other parameter, since there is no state to test. CONSUMER_API's "state after the change, last state for a deletion" would need a snapshot per event, which C-D7 declined; a receiver told of a deletion outside its scope ignores an ID it never had. `publication`, `asOf` and `to.` are `400 PARAMETER_NOT_SUPPORTED` there. C11's subscription filters reuse this |
| C-D91 | How the pull feed pages and resumes | **Approved 2026-10-05.** _Amended 2026-10-05 with C-D7's revision:_ `pageSize` by payload: `full` 1–100, default 100, as the lists, since each item is a whole object; `identity` as below. Originally: `after={position}` starts after a position (a publication's `eventSequence`, or `0`); the response's opaque `cursor` continues from the last item, inside a position too, which a container rename can fill with thousands of events (F6). Events never change, so the cursor is a lasting resume token; `caughtUp` says the derived head is reached. `pageSize` 1–1,000, default 500, as the raw feed (items are small, unlike the lists' objects). A filtered page scans at most ten pages of events and may come back short or empty with the cursor advanced (as F4) |
| C-D7 (revised) | What an event carries | **Approved 2026-10-05.** Fully event driven: `payload=full` (default) carries the object exactly as get-by-ID answers it with the request's or subscription's parameters, composed by get-by-ID's code when the page is read or the batch sent, under the contract version served, never stored, labelled `stateAt`. `payload=identity` leaves it out, as snapshot and thin events are offered side by side; it costs one switch, since events, positions and IDs are shared. A `deleted` event has no object. `payload` is reserved. Replaces "identity only; receivers read the object" |
| C-D12 (revised) | Webhook signing | **Approved 2026-10-05.** Signed in 0.9: with data in events, a forged one could plant false reference data. C11 generates the key on create and returns it once; C12 signs every request. Not in C10 (no webhook yet); recorded here because C-D7's revision causes it. 0.12 keeps rotation |
| C-D95 | A projection over a containment relation | **Approved 2026-10-05 (found in delivery).** The validator allows a projection over a parent–child relation (none is declared today), but the feed names no parent for a delete, nor the former parent of a record a publish moved, so a removed or moved child's former parent could not be found. Each record's feed subject now also names its `parentObjectId`, and its `previousParentObjectId` when it moved, on every path that builds one (`feed.object_subject`). The raw feed's answer is unchanged. The deriver then updates both parents. Rejected: refusing such projections (closes a door), or the current parent only (a silent loss) |
| C-D92 | Where derivation starts, and what expires | **Approved 2026-10-05.** An existing workspace starts at its active publication's `feedPosition` (`0` without one), so a receiver re-syncing from that publication (C-D15) finds every later event; earlier entries are not derived (their state is gone). Events expire with the raw feed's floor (D40); `after` below `earliestPosition - 1`, or below the start, is `410 EVENTS_EXPIRED` with the active publication and its `eventSequence`; with no publication nothing expires. Starting at the head instead would put the active publication's position below the earliest one, so the `410`'s own baseline would be refused |

**Journey.** USER_JOURNEYS gains **J30 — Follow a consumer API's changes** (integrator, API,
US-I05): J30.1 own changes, J30.2 what an object shows, J30.3 batches and publishes, J30.4 reading
and filters, J30.5 expiry and re-sync; C11–C13 add webhooks to it. J25's status says events are
produced from C10. API_JOURNEYS gains the route, its parameters and codes. Generated A and B's `Capi`
gains C9's two events (from J25.3) plus a third, over `R` and `R2` without `watch`, so their seeds
rebuild once; the parity fixture already carries CONSUMER_API's event.

**Test cases** (journey tests on generated A and B, written first and confirmed failing: the route
is `404`), each read after the test runs the deriver:

1. **J30.1 Own changes.** Creating an `R` makes `created` under the first and third events; renaming
   it `updated` with `changed` `[name]`; setting `R.n` makes `updated` `[score]` under the third event
   only (not watched by the first); deleting it `deleted` with `code` and `name` `null`. Each item's
   `position` equals the raw feed entry's, `cause` `user`. A `D` created and deleted makes the second
   event's two items; editing it makes none there.
2. **J30.2 What an object shows.** Renaming an `R` makes `updated` for its `R2` children with
   `parent`, `path` and `hierarchy` (the first event's watch keeps `parent`); renaming the `K` an `R`
   projects through `B11` makes `updated` `[pairedToken]` for that `R`; renaming a `G` makes
   `updated` `[permits]` for each `R` owning a `D` below it (`ancestor:G.name`); deleting the `B11`
   relation makes `updated` `[pairedToken]` for the former owner.
3. **J30.3 Batches and publishes.** A background batch's items make events with the job as `cause`; a
   change set publishing several changes makes events at its entries' positions with the publication
   as `cause`, all at or below its `eventSequence`; change-set edits and discard, a rejected item and
   a refused write make none.
4. **J30.4 Reading.** `event=` narrows to one event; `kind`, `container` and `token` narrow as the
   list does; a deleted `R` passes `container` (C-D90). With `pageSize=2`, a position holding five
   events is read whole by cursor, and the cursor of a caught-up page later returns the next events.
   With `payload=full` (default) each item's `object` equals get-by-ID of that object read at the
   same moment with the same parameters (`permit` limiting `permits` on both), and a `deleted` item
   has none; `payload=identity` returns the same items, positions and `eventId`s without `object` and
   `stateAt`; `pageSize=101` is `400 INVALID_PAGE_SIZE` with `full` and allowed with `identity`.
   `ETag` answers `304` until a new event is derived. Refusals: `400 UNKNOWN_EVENT`, `400
   PARAMETER_NOT_SUPPORTED` (`publication`, `asOf`), `400 INVALID_PAGE_SIZE`, `409
   EVENT_POSITION_AHEAD`, `404 WORKSPACE_NOT_FOUND`, `404 EVENTS_NOT_DECLARED` (a definition without
   events).
5. **J30.5 Expiry and re-sync.** With entries aged past retention (as J26.6 ages them), `after` below
   the floor is `410 EVENTS_EXPIRED` naming the active publication and its `eventSequence`; reading
   that publication's list and following from its `eventSequence` ends with live data; without a
   publication nothing expires.
6. **The deriver.** Writes made while it is stopped, then derived together, give the events (and
   `eventId`s) derived one write at a time; two derivers at once derive each range once; a release
   activated between a write and its derivation leaves the event under the write's release (C-D88).
7. **Unit** (`tests/unit/engine/events/test_plan.py`): the plan built from a definition, each impact
   kind, and C-D83's type change seen from an event (moving out `deleted`, in `created`, between two of
   its types `updated` with `objectType`).
8. **Startup:** the migration on a clean database and from `20261005_03` with a workspace that has a
   publication (its checkpoint at the publication's position); the lifespan starts the deriver.
9. **Volume, measured once:** deriving 500 live entries and a 10,000-entry publish at both seeded
   sizes (the same statements per page), and renaming the 20,000-item heavy group with `path` watched
   (events written, wall time), recorded in POSTGRESQL_BUDGETS §7 as C-D82 asks; the pull feed's first
   page and a filtered page at both sizes, each with `payload=full` (100 composed objects: the same
   statements at both sizes, as get-by-ID's budget) and `payload=identity`.

**Checks:** J30 on generated A and B; the plan's unit tests; the `feed` and `consumer` groups once;
`startup` (migration and lifespan); `test_openapi_contract` and `test_api_journeys` (the lock
expected unchanged); the new `test_consumer_event_volume` once; `ruff`. Not run: the frontend
(unchanged), the write groups (the write path is untouched; `presenters` only imports the moved
vocabulary, covered by J26 in `feed`), the full suites and `budget` (R).

**Exit:** live changes become consumer events in position order without slowing writes; the pull feed
pages, filters, resumes and expires them with a re-sync path, with the object or without it; C-D82's
fan-out is measured.

**Docs at delivery:** CONSUMER_API ("Pull feed", "How events are produced", C-D87–C-D92, `payload`
among the reserved names, the C10 row; C-D7's and C-D12's revisions are already written); API.md (the events read); ARCHITECTURE (the deriver, its checkpoint and lock, the two tables);
OPERATIONS (shared retention, the deriver's head beside the feed's); USER_JOURNEYS J30 and J25's
status; API_JOURNEYS; CURRENT_FUNCTIONALITY; EXECUTION_GUIDE (new modules and counts);
POSTGRESQL_BUDGETS §7; CHANGELOG, PROJECT_STATUS, TODO.

**Composable domains (ADR-032):** the deriver reads the audit log and leaves it as it is, and the plan
is built from any definition's sources. One door is touched: **erasure**. Events keep `code` and
`name` copies for up to the retention period, so a future erasure must reach `consumer_events` too
(added to COMPOSABLE_DOMAINS at delivery). A `full` event's object is composed when read or sent and
never stored, so it adds nothing to that. Identity, attribute storage, the bulk APIs, `match` and
mapping coverage are untouched.

##### C10 delivery record

**Delivered 2026-10-06**, as designed, with C-D87–C-D92, C-D7's revision (both payloads), C-D89's
amendment and C-D95.

- **Feed subject and vocabulary** (`engine/records/feed.py`): a record's entry names its
  `parentObjectId`, and its `previousParentObjectId` when it moved, on the live update and the
  publish (C-D95); `changed_names` moved there from `management/presenters`, which imports it. The
  raw feed's answer is unchanged.
- **Plan** (`engine/events/plan.py`): `FeedChange.of` reads an entry by name; `EventPlan` turns a
  page's changes into `Own` rows (the record's own change) and `Reach` rows (children, descendants,
  self and descendants, each optionally through a projection's relation to its owners), from the
  definition alone (C-D82, C-D87).
- **Deriver** (`engine/events/deriver.py`, `worker.py`): `derive_page` per workspace, 500 entries,
  REPEATABLE READ, the checkpoint row `FOR UPDATE SKIP LOCKED`; per release and definition one
  `INSERT … SELECT` over parallel-array CTEs, a recursive descendant walk and relation joins,
  merged per position and object, classified per event (C-D83 in SQL), ordered by `row_number()`.
  `EventDeriver` polls once a second, sweeps hourly through `reads/feed.retention_floor` (made
  public from `read_feed`), and starts in the lifespan as `app.state.event_deriver`
  (`run_event_deriver` False in tests that derive themselves).
- **Store** (migration `20261006_01`): `consumer_events` and `consumer_event_checkpoints`, existing
  workspaces started at their active publication's position (C-D92).
- **Pull feed** (`engine/reads/consumer_events.py`, the route in `consumer/router.py`): `after` or
  `cursor`, `caughtUp`, both payloads with their page sizes, `event` and the definition's parameters
  (C-D90), the bounded narrowed scan, `409 EVENT_POSITION_AHEAD`, `410 EVENTS_EXPIRED`, the ETag
  over the checkpoint, one REPEATABLE READ snapshot so `stateAt` is exact. `ConsumerObjects`
  gains `identities` (`code` and `name`, one statement). `payload` is a reserved parameter name;
  `event`, `after` and `payload` are route names, so other reads answer `PARAMETER_NOT_SUPPORTED`
  for them.
- **Contract documents**: a definition with events gets `GET …/events` with `Event` and
  `EventPage`; the management OpenAPI lock is unchanged.
- **Docs**: CONSUMER_API (pull feed, how events are produced, the filters line, reserved names,
  C-D87–C-D92 and C-D95, the C10 row), API.md (consumer events), ARCHITECTURE, OPERATIONS,
  USER_JOURNEYS (J30; J29 added to the integration row it was missing from), API_JOURNEYS,
  CURRENT_FUNCTIONALITY, EXECUTION_GUIDE (`feed` 55, `consumer` 276, `volume` 77), POSTGRESQL_BUDGETS
  §7, INTEGRATION_API F6, CHANGELOG, PROJECT_STATUS, TODO.

**Differs from the plan:**
- **Identity is read at delivery** (C-D89 amended by the user): `code` and `name` are not stored, so
  the event store keeps no values and the erasure door is untouched; COMPOSABLE_DOMAINS needs no
  note.
- **C-D95** (found in delivery, decided by the user): the feed subject names the parents, so a
  projection over a containment relation (allowed by the validator, declared nowhere today) misses
  no former parent.
- **The journey configurations are unchanged**: J30's tests activate a release with events, as
  J25.3 does, since events seeded into `Capi` would break J25.3 and J25.4; no seed rebuilt.
- **Case 6** compares two derivations of the same state. Derived as each write happens, a rename
  does not reach a child created after it; derived later, it does, since reach is read when the
  deriver runs (C-D89). Both are correct under C-D89; the test pins the repeatable one.
- **The event ID** is an MD5 digest of the entry, definition, event and object, written as a UUID,
  computed in the `INSERT … SELECT` (the plan said UUIDv5; PostgreSQL has no built-in v5).
- **No 10,000-entry publish case in the volume test**: the small seeds hold too few items, and a
  publish's entries take the same page path as live ones, which the 500-entry case pins.
- **Volume applications start no deriver thread**: its poll landed in a test that counts every
  statement (`test_capturing_and_publishing_a_whole_workspace_bind_no_parameter_per_record`); the
  thread is also left out of `measure`.

**Checks:**
- **Failing first:** the 14 J30 cases (generated A and B) failed (no deriver); all pass.
- **Targeted:** J30 14, the plan's unit tests 6, the OpenAPI test 3, the C10 startup cases with
  the clean boot 3, `test_consumer_event_volume` 2: all passed.
- **Groups** `records`, `change_sets`, `mapping`, `matrix`, `feed`, `jobs`, `consumer`, `model`,
  `startup` and `contract` in parallel: 1,493 passed, 3 failed (`test_api_journeys`' error-code
  inventory and the two `test_foreign_keys` cases, which name every rule); the inventories updated,
  those 7 cases passed. Their serial part: 3 passed.
- **`volume`** in parallel: 76 passed after volume applications stopped starting the deriver
  thread (1 failed before, above).
- **Full volume, once** (C-D82): the heavy group's rename tells 20,001 objects in 724 ms, 5
  statements; the reads 11.5–54.5 ms (POSTGRESQL_BUDGETS §7).
- `ruff check app/ tests/`: clean.
- **Not run:** `queries`, `workspaces`, `model_admin` (no boundary of theirs changed), the frontend
  (unchanged), `budget` and the full suites (R).

#### C11: Subscriptions

**Delivered 2026-10-06** ([record](#c11-delivery-record)). Planned 2026-10-06. Decisions C-D96–C-D102 approved by the user the same day; C-D93 and C-D94
(decided 2026-10-05) and C-D7's and C-D12's revisions apply as written.
**Needs:** C10 (the events, their positions, `410 EVENTS_EXPIRED` and its baseline, C-D90's filter
rule). **Groups:** `feed`, `contract` (new routes, capabilities), `startup` (migration, the setting
checked at start), `model_admin` (activation suspends), `workspaces` (retirement suspends, deletion
refused).
**Design:** CONSUMER_API "Subscriptions (runtime, not model)", "Delivery" (the parts C11 stores),
"Security (0.12)"; C-D7 (revised), C-D10, C-D12 (revised), C-D16, C-D88, C-D90, C-D93, C-D94;
ADR-031 (capability groups).

**Behaviour.** An operator (or a script) tells the engine where a consumer API's events go. A
subscription names the consumer API, the workspace, the events, filters in the definition's own
parameters, the target URL, the delivery mode and the payload. The engine checks it against the
active definition and the deployment's host allowlist, generates its signing key and returns the
key once. The subscription is then managed through the API: read, edited with optimistic
concurrency, suspended, resumed and deleted. A model activation or a workspace retirement that the
subscription can no longer follow suspends it with a machine-readable reason; nothing rewrites it.
**Nothing is sent in C11**: the dispatcher (C12) delivers what C11 stores.

```text
POST   /api/v1/consumer-subscriptions                       201, the signing key in this answer only
GET    /api/v1/consumer-subscriptions?consumerApi=…&workspaceKey=…&status=…&cursor=…&pageSize=…
GET    /api/v1/consumer-subscriptions/{id}
PATCH  /api/v1/consumer-subscriptions/{id}                  { "expectedVersion": 3, … }
POST   /api/v1/consumer-subscriptions/{id}/suspend          { "expectedVersion": 3 }
POST   /api/v1/consumer-subscriptions/{id}/resume           { "expectedVersion": 4, "acknowledgeLoss": false }
DELETE /api/v1/consumer-subscriptions/{id}?expectedVersion=…
```

```jsonc
// POST body
{
  "consumerApi": "rdm",
  "workspaceKey": "main",                 // optional: the default workspace, resolved and stored
  "events": ["reference-data-changed"],   // required, at least one
  "filters": { "type": "Location", "codelist": ["Country", "Region"] },
  "url": "https://integration.example.com/hooks/rdm",
  "mode": "perChange",                    // or "coalesced"
  "debounceSeconds": 60,                  // coalesced only, 1–600
  "payload": "full",                      // or "identity" (C-D7)
  "startAfter": 184100                    // optional (C-D97): default the workspace's feed head
}

// answer (a read leaves out signingSecret)
{
  "id": "…", "consumerApi": "rdm", "contractVersion": 1, "workspaceKey": "main",
  "events": ["reference-data-changed"], "filters": { … }, "url": "…",
  "mode": "perChange", "debounceSeconds": null, "payload": "full",
  "status": "active",                     // or "suspended"
  "suspension": null,                     // { "reason", "message", "details", "suspendedAt" }
  "acknowledgedThrough": 184100,          // the position delivery continues after
  "signingKeyCreatedAt": "…",
  "version": 1, "createdAt": "…", "updatedAt": "…",
  "signingSecret": "rdmwh_…"              // create only, never again (C-D12)
}
```

- An operator subscribes, keeps the key, reads the subscription back, edits its URL or filters with
  the version they read, suspends it and resumes it.
- A filter scopes as the same parameter on a list (C-D90); one the definition does not declare, or
  one a list does not take (`workspace`, `publication`, `asOf`, `to.…`, `payload`), is refused at
  its pointer, as batch resolve refuses an item's.
- A URL outside the allowlist, or plain HTTP to anything but an allowlisted loopback host, is
  refused at create, edit and resume (C13 scenario 11).
- Activating a release that drops the subscription's consumer API, one of its events or one of its
  filters suspends it with `MODEL_CHANGED`; one that raises the contract version suspends it with
  `CONTRACT_VERSION_CHANGED` (C13 scenario 12).
- Resuming after the subscription's unacknowledged events expired is `409 EVENTS_EXPIRED` with the
  lost range and the baseline, unless `acknowledgeLoss` is true (C-D93).

**What exists today** (checked 2026-10-06):

- **Capability groups** are settings read in `config.Settings` and copied onto `app.state` in
  `create_app`; a gated router is mounted only when its setting is on, so its routes are `404` and
  absent from the OpenAPI document (model administration, `jobs.write_router`). `GET /capabilities`
  reports each group with the `setting` that enables it. No subscription setting exists.
- **The definition and its events**: `reads/consumer_objects.consumer_definition` resolves the active
  release's definition (`404 CONSUMER_API_NOT_FOUND`); the events route refuses a definition without
  events (`404 EVENTS_NOT_DECLARED`) and an unknown event (`400 UNKNOWN_EVENT`).
- **Filters**: `reads/consumer_parameters.consumer_filter` turns parameter values into predicates,
  and its builder finds a value's candidates (`_Builder.candidates`). The name checks
  (`UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`, JSON values as batch resolve takes them,
  `_names_refused`, `_json_values`) live in `consumer/router.py`, which the management tier cannot
  import (`tests/test_boundaries.py`).
- **Positions**: `reads/consumer_events.derived_head` and `reads/feed.retention_floor` give the
  derived head, the earliest kept position and the `410` baseline that C-D93's check needs.
- **Activation** (`engine/model/releases.activate_model_release`) runs in one transaction holding
  the runtime-state row; **retirement and deletion** of a workspace in
  `engine/workspaces/catalogue.update_workspace` and `delete_workspace`. A retired workspace can be
  reactivated.
- **No symmetric cipher** is available: the runtime dependencies are FastAPI, Pydantic, SQLAlchemy,
  psycopg, Alembic and Uvicorn (`pyproject.toml`); `hmac` and `secrets` (stdlib) sign and generate.
- **Nothing** stores subscriptions; there is no `/consumer-subscriptions` route.

**Design.**

- **Setting** `CONSUMER_SUBSCRIPTIONS_ENABLED` (default `false`, C-D10) mounts the router
  (C-D102). `CONSUMER_WEBHOOK_ALLOWED_HOSTS` (comma-separated, default empty) and
  `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (C-D96) join `Settings`; with the capability on and no
  encryption key, startup refuses with the instruction to generate one (the command in OPERATIONS).
  `GET /capabilities` gains `consumerSubscriptions` (`manageSubscriptions`, `allowedHosts`,
  `setting`).
- **Engine** (`engine/events/subscriptions.py`): create, update, suspend, resume, delete and the two
  hooks below; the checks in one function used by create, edit and resume:
  1. the consumer API exists in the active release and declares events; each named event exists;
  2. each filter names a definition parameter a list takes, with text or a list of texts; the
     consumer router's name and value checks move to `engine/reads/consumer_parameters` so both
     tiers use them (the consumer answers do not change);
  3. each filter value matches at least one record now (C-D100), through the builder's candidates;
  4. the URL passes the allowlist (C-D101);
  5. the workspace exists and is active.
  A subscription records the contract version it was accepted under; the dispatcher composes `full`
  objects under it (C-D99).
- **Hooks.** `activate_model_release` calls `subscriptions.on_activation(session, model)` before it
  commits; it checks every active subscription against the new release by rules 1–2 and suspends
  in one `UPDATE … FROM (VALUES …)` (subscriptions are configuration, few, decided in Python and
  written as one set statement). `update_workspace` retiring a workspace suspends its active
  subscriptions with one `UPDATE`; `delete_workspace` refuses a workspace with subscriptions
  `409 WORKSPACE_HAS_SUBSCRIPTIONS` (C-D99).
- **Store** (migration `…_consumer_subscriptions`, named at delivery): `consumer_subscriptions`
  (`public_id` unique, `consumer_api`, `contract_version`, `workspace_key` → `workspaces.key`,
  `event_keys` text[], `filters` jsonb, `url`, `mode`, `debounce_seconds`, `payload`, `status`,
  `suspension_reason`, `suspension_details` jsonb, `suspended_at`, `acknowledged_position`,
  `acknowledged_ordinal`, `signing_key` bytea (encrypted), `signing_key_created_at`, `version`,
  `created_at`, `updated_at`); indexed on (`consumer_api`, `created_at`, `public_id`) for the list
  and on `workspace_key`. The acknowledged position and ordinal are where delivery continues, inside
  a position too, as the pull feed's cursor (C-D91); C12 advances them and adds its delivery state.
- **Routes** (`management/routers/consumer_subscriptions.py`, schemas in
  `management/schemas/consumer_subscriptions.py`): the list pages through `PageQuery` (ADR-030),
  newest first, filtered by `consumerApi`, `workspaceKey` and `status`. Codes: `404
  SUBSCRIPTION_NOT_FOUND`; `409 VERSION_CONFLICT`; `400 CONSUMER_API_NOT_FOUND`,
  `EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT`, `UNKNOWN_PARAMETER`, `PARAMETER_NOT_SUPPORTED`,
  `FILTER_MATCHES_NOTHING`, `INVALID_WEBHOOK_URL`, `WEBHOOK_HOST_NOT_ALLOWED`, each with its body
  pointer (a body field, so `400`, unlike a route segment's `404`); `404 WORKSPACE_NOT_FOUND`
  (retired too, as consumer reads); `409 SUBSCRIPTION_NOT_SUSPENDED`,
  `SUBSCRIPTION_ALREADY_SUSPENDED`; on resume `409 SUBSCRIPTION_NEEDS_EDIT` with each failed check's
  code and pointer in `details.errors`, and `409 EVENTS_EXPIRED` (C-D93). `startAfter` takes the pull
  feed's `after` rules: `410 EVENTS_EXPIRED`, `409 EVENT_POSITION_AHEAD`.
- **Not audited.** Subscription changes write no `audit_events` entry: that log is the outbox of data
  changes, and every feed reader would have to skip a configuration entry. `updatedAt`, `version`
  and the suspension fields hold the state; who changed it waits for 0.12's actors.
- **Signing key**: 32 bytes from `secrets`, shown as `rdmwh_` and base64url, encrypted with AES-GCM
  under the deployment key (C-D96) before it is stored; reads never return it. C12 decrypts it to
  sign.
- **Contract documents:** the management OpenAPI lock is built with the capability off, so it changes
  only by `consumerSubscriptions` in the capabilities response (re-baselined, diffed); a second
  contract case builds the document with the capability on and checks the routes, as model
  administration's is checked. The consumer documents do not change.
- **No frontend** (the Webhooks page is U5, after C12), **no dispatcher, no HTTP client** (C12).

**Decisions** (status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D96 | How the signing key is kept at rest (left to C11 by CONSUMER_API) | **Approved 2026-10-06.** Encrypted with AES-GCM under `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, a deployment secret kept outside the database; required when the capability is on, and startup refuses without it, naming the setting and the command that generates one. HMAC needs the key itself, so it cannot be hashed like a password. Stored in plain text, a database backup or a read replica would let whoever holds it forge signed events that plant data in every receiver, which is what C-D12's revision guards against. Adds `cryptography` as a runtime dependency; 0.12's JWTs need it too. The stored value carries a format prefix, so 0.12 can re-encrypt under a new deployment key without a schema change |
| C-D97 | Where a new subscription starts | **Approved 2026-10-06.** After the workspace's feed head when it is created, so it receives the changes that follow and nothing earlier; `startAfter` may name an earlier position (a publication's `eventSequence`, as a receiver starting from that publication's lists does, C-D15), checked as the pull feed's `after`: below the earliest kept `410 EVENTS_EXPIRED` with the baseline, past the head `409 EVENT_POSITION_AHEAD`. The feed head, not the derived head: events derived later for positions after it are delivered, so a lagging deriver loses nothing. Rejected: starting at 0 (floods a receiver with up to 30 days of history it did not ask for) |
| C-D98 | One switch, or `enabled` and suspension | **Approved 2026-10-06.** One: `status` is `active` or `suspended`, and suspension always has a reason; CONSUMER_API's `enabled` field is dropped. Suspending by hand is `POST …/suspend` (`SUSPENDED_BY_USER`); every reason is undone by `POST …/resume`. Resume re-runs create's checks against the active release, the allowlist and the workspace, so CONSUMER_API's "needs an edit first after `MODEL_CHANGED` or `FILTER_MATCHES_NOTHING`" is a check, not a rule per reason: a resume that would fail is `409 SUBSCRIPTION_NEEDS_EDIT` listing what to fix. After `CONTRACT_VERSION_CHANGED` the resume records the new version as accepted. C-D93's loss check applies to every resume. Reasons: `SUSPENDED_BY_USER`, `MODEL_CHANGED`, `CONTRACT_VERSION_CHANGED`, `WORKSPACE_RETIRED` (C11); `DELIVERY_FAILED`, `FILTER_MATCHES_NOTHING`, `HOST_NOT_ALLOWED` (C12). Two switches would let a subscription be enabled and suspended at once, with two answers to "why is nothing arriving" |
| C-D99 | When a model change or a workspace retirement suspends | **Approved 2026-10-06.** In the transaction that causes it, so no event is ever composed under a definition the subscription was not checked against. Activation: a missing consumer API, event or filter parameter, or a filter parameter of another kind, is `MODEL_CHANGED` with each finding's pointer; otherwise a different `contractVersion` is `CONTRACT_VERSION_CHANGED`, since only one version is served (C-D3) and the `full` object's shape would change without the receiver agreeing. An already suspended subscription keeps its reason; its resume re-checks. Retirement: `WORKSPACE_RETIRED` at once; undelivered events stay until retention, and after a reactivation a resume continues from them (C-D93 if they expired). Deleting a workspace that has subscriptions is refused `409 WORKSPACE_HAS_SUBSCRIPTIONS`: a workspace change never removes another owner's configuration (as C-D94). Rejected: checking lazily in the dispatcher (the API would show `active` for a subscription that can no longer be served) |
| C-D100 | A filter value that matches nothing when the subscription is created | **Approved 2026-10-06.** Refused `400 FILTER_MATCHES_NOTHING` at create, edit and resume, at `/filters/{name}`. C-D94 suspends a subscription whose filter stops matching; accepting one that matches nothing would create it only for C12 to suspend it, and a typo would pass silently. A receiver waiting for a record not yet created subscribes after it exists |
| C-D101 | What the host allowlist accepts | **Revised 2026-10-07, by the user:** no host allowlist; any host over HTTPS, plain HTTP only to `localhost`, `127.0.0.1` or `::1`. `CONSUMER_WEBHOOK_ALLOWED_HOSTS`, `allowedHosts` in capabilities, `WEBHOOK_HOST_NOT_ALLOWED` and the `HOST_NOT_ALLOWED` suspension are removed: webhook targets are not deployment configuration that needs a restart. The dispatcher's address checks (C-D107) stay. Was: **Approved 2026-10-06.** `CONSUMER_WEBHOOK_ALLOWED_HOSTS` lists host names, compared ignoring case, each exact or `*.` followed by a domain (any depth below it, not the domain itself); IP addresses only as written. Any port. The URL is absolute HTTPS, without user information or fragment, at most 2,048 characters; plain HTTP only to `localhost`, `127.0.0.1` or `::1`, and only when listed (CONSUMER_API's "allowlisted local hosts in development" without a separate mode). Empty, the default, allows nothing: create is `400 WEBHOOK_HOST_NOT_ALLOWED` naming the setting. The list is reported in capabilities, so the Webhooks page (U5) can say what is allowed. A host removed from the list later is caught by C12 before it sends (`HOST_NOT_ALLOWED`); name resolution and redirects are C12's |
| C-D102 | What the capability gates | **Approved 2026-10-06.** The whole group: with `CONSUMER_SUBSCRIPTIONS_ENABLED` off, no subscription route is mounted (reads included) and C12 delivers nothing; stored subscriptions are kept and continue when it is turned on. Model administration keeps reads ungated because releases exist whatever the setting; a subscription exists only to be delivered, and its URL names hosts inside the deployment, so an unauthenticated read of it off is no use and some exposure (until 0.12) |

**Journey.** J30 gains **J30.6 Subscribe** (create, read, list, edit, suspend, resume, delete; the
key once; the refusals) and **J30.7 A subscription the model or workspace leaves behind** (activation,
retirement, the resume checks, C-D93). API_JOURNEYS gains the routes and codes; J30's status says
subscriptions are managed from C11 and delivered from C12. The tests run with the capability on, the
allowlist naming `hooks.example.test` and `localhost`, and an encryption key, set before the test
application starts; J30's configurations and release with events are reused, so no seed is rebuilt.

**Test cases** (journey tests on generated A and B, written first and confirmed failing: the routes
are `404`):

1. **J30.6 Subscribe.** Create with two events, a `kind` and a `container` filter and `full`: `201`
   with `status` `active`, `contractVersion` the active one, `acknowledgedThrough` the feed head and
   `signingSecret`; a read and the list return it without the key. With `startAfter` at an earlier
   position, `acknowledgedThrough` is that position. `PATCH` with the read version changes the URL and
   filters and raises `version`; a stale one is `409 VERSION_CONFLICT`. Suspend: `suspended`,
   `SUSPENDED_BY_USER`; suspend again `409 SUBSCRIPTION_ALREADY_SUSPENDED`; resume: `active`; resume
   again `409 SUBSCRIPTION_NOT_SUSPENDED`. Delete with the version: gone, `404
   SUBSCRIPTION_NOT_FOUND`. The list pages by cursor and narrows by `consumerApi` and `status`.
2. **J30.6 Refusals, each at its pointer:** an unknown consumer API, a definition without events, an
   unknown event, an undeclared filter, `asOf` and `to.…` as filters, a filter value no record has,
   `http://hooks.example.test/…`, a host outside the list, a URL with user information, a retired
   workspace, `debounceSeconds` with `perChange`, `startAfter` below the floor (`410`) and past the
   head (`409`). The same URL and filter checks on `PATCH`.
3. **J30.7 Model change.** Activating a release that removes an event a subscription names suspends it
   `MODEL_CHANGED` with the event's pointer; one that removes a filter's parameter likewise; one that
   only raises `contractVersion` suspends it `CONTRACT_VERSION_CHANGED`, and its resume records the
   new version; a subscription the release still serves stays `active`. Resuming the
   `MODEL_CHANGED` one unedited is `409 SUBSCRIPTION_NEEDS_EDIT`; after removing the event, it
   resumes.
4. **J30.7 Workspace.** Retiring a workspace suspends its subscriptions `WORKSPACE_RETIRED`; a resume
   is `409 SUBSCRIPTION_NEEDS_EDIT` (workspace inactive); after reactivation it resumes. Deleting a
   workspace with a subscription is `409 WORKSPACE_HAS_SUBSCRIPTIONS`.
5. **J30.7 Expired events (C-D93).** A suspended subscription whose acknowledged position falls below
   the floor (entries aged as J30.5 ages them): resume is `409 EVENTS_EXPIRED` with `fromPosition`,
   `toPosition`, the active publication and its `eventSequence`; with `acknowledgeLoss: true` it
   resumes with `acknowledgedThrough` at the floor.
6. **Capability.** With the setting off the routes are `404` and capabilities say
   `manageSubscriptions: false`; on, they report the allowlist.
7. **Unit:** the allowlist (exact, wildcard depth, the domain itself, case, IP, loopback over HTTP,
   user information, fragment, length); the key's encryption round trip and a wrong deployment key
   refused.
8. **Startup:** the migration on a clean database and from `20261006_01`; the capability on without
   an encryption key refuses to start with the setting named (no traceback).

**Checks:** J30.6 and J30.7 on generated A and B; the unit tests; the `feed` group once; `startup`
(migration, the refusal); `test_openapi_contract` (lock re-baselined for capabilities, the gated
document) and `test_api_journeys`; the `model_admin` and `workspaces` groups (activation and
retirement call the hooks); `test_foreign_keys` (the new reference); `ruff`. Not run: `consumer`
(the consumer answers are unchanged; the moved name checks are covered by J28's and J29's refusal
cases, run as targeted modules), `volume` (no read or write path of data changes; subscriptions are
configuration), the frontend, `budget` and the full suites (R).

**Exit:** subscriptions are managed through the API with the signing key generated and shown once,
checked against the definition, the allowlist and the workspace, and suspended with a reason when a
model activation or retirement leaves them behind; resume refuses a silent loss.

**Docs at delivery:** CONSUMER_API (Subscriptions: the shape without `enabled`, the reasons,
`startAfter`, the key at rest; C-D96–C-D102; the C11 row); API.md (the subscriptions API and the
capabilities group); ARCHITECTURE (the table, the hooks, the key's encryption); OPERATIONS (the three
settings, generating the encryption key, what turning the capability off does); USER_JOURNEYS J30.6
and J30.7; API_JOURNEYS; CURRENT_FUNCTIONALITY; EXECUTION_GUIDE (new modules, counts, the
changed-boundary row); SETTINGS_AND_UI_PLAN's Webhooks row (suspend and resume as above);
CHANGELOG, PROJECT_STATUS, TODO. The C12 row above says the resume check is built in C11.

**Composable domains (ADR-032):** no door is affected. Subscriptions are deployment configuration;
identity, attribute storage, audit/history (configuration is not audited, the audit log is
unchanged), the bulk APIs, `match` and mapping coverage are untouched. Filter values name records by
code or name, as a stored query would, and hold no record data for erasure to reach.

##### C11 delivery record

**Delivered 2026-10-06**, as designed, with C-D96–C-D102.

- **Settings** (`config.py`): `CONSUMER_SUBSCRIPTIONS_ENABLED`, `CONSUMER_WEBHOOK_ALLOWED_HOSTS` and
  `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY` (32 bytes, URL-safe base64); `python -m
  app.cli.generate_key` prints a key. `cryptography` is a runtime dependency.
- **Sealing** (`common/sealing.py`): AES-256-GCM with a format byte and the subscription's ID as
  associated data (C-D96).
- **Rules** (`engine/events/subscription_rules.py`): the definition checks (consumer API, events,
  each event, each filter's name from the model's reserved names and the definition's parameters),
  the activation hook `suspend_left_behind` (called by `activate_model_release` before it commits)
  and the retirement hook (called by `update_workspace`). It imports only the model and the table,
  so neither caller imports the reads.
- **Service** (`engine/events/subscriptions.py`): create, edit, suspend, resume, delete and the
  paged list; each change claims the version under `FOR UPDATE`; the filter values through
  `reads/consumer_parameters.unmatched_values` (C-D100), the URL through `webhook_urls.py`
  (C-D101), positions through `reads/consumer_events.check_after` and `event_window`, factored out
  of the pull feed with its answers unchanged (C-D97, C-D93).
- **Store** (migration `20261006_02`): `consumer_subscriptions`, its workspace reference
  `RESTRICT`; `delete_blocker` gains `subscribed` (`409 WORKSPACE_HAS_SUBSCRIPTIONS`).
- **Routes** (`management/routers/consumer_subscriptions.py`, mounted with the capability) and
  `consumerSubscriptions` in `GET /capabilities`; the management OpenAPI lock re-baselined (diffed:
  the capabilities group and `deleteBlockedBy`'s `subscribed`, nothing else).
- **Docs**: CONSUMER_API (Subscriptions, C-D96–C-D102, the C11 and C12 rows), API.md (consumer
  subscriptions, capabilities, workspace deletion), ARCHITECTURE, OPERATIONS (the settings, the key,
  suspensions), USER_JOURNEYS (J30.6, J30.7, J30's status), API_JOURNEYS, CURRENT_FUNCTIONALITY,
  EXECUTION_GUIDE (groups, counts, the changed-boundary row), SETTINGS_AND_UI_PLAN's Webhooks row,
  CHANGELOG, PROJECT_STATUS, TODO.

**Differs from the plan:**
- **The consumer router is unchanged.** The filter-name checks are built in `subscription_rules`
  from the model's `RESERVED_PARAMETERS`, the definition's parameters, `to.` targets and list
  parents, instead of moving the router's checks to the engine; a filter takes JSON values, so the
  router's query-string handling had nothing to share.
- **A filter parameter whose kind changes** is not looked for separately: the contract check
  refuses that release unless the contract version is raised, so it reaches the subscription as
  `CONTRACT_VERSION_CHANGED`, and the resume checks the values again.
- **A type name the API does not expose** in an `objectType` filter is `400 UNKNOWN_OBJECT_TYPE`,
  as on a read, at its filter pointer (recorded in C-D100).
- **The activation's suspensions** are one executemany `UPDATE` over the rows found, not
  `UPDATE … FROM (VALUES …)`; subscriptions are configuration and few.
- **A `suspension_message` column** holds the reason's text the API answers.
- **The startup refusal** without a usable key is a `RuntimeError` at application construction,
  naming the setting and the command, as `WEB_CONCURRENCY`'s check is; the plan said "no traceback",
  which the existing settings checks do not give either.
- **The frontend** does not yet word `deleteBlockedBy: subscribed` (the Workspaces page shows no
  hint; delete stays disabled): U2 was changing that page, so the hint goes to U3, which moves it
  (TODO).
- **J20's capabilities case** names the fourth gated group.

**Checks:**
- **Failing first:** the 14 cases of `test_j30_subscriptions` (generated A and B) failed (routes
  `404`, no capabilities group); all pass.
- **Targeted:** `test_j30_subscriptions` 14; the allowlist and sealing unit tests 27; the startup
  cases for the C10 and C11 migrations and the key refusal 6; `test_openapi_contract`,
  `test_api_journeys`, `test_foreign_keys`, `test_boundaries` 19: all passed.
- **Groups** `feed`, `startup`, `model_admin`, `workspaces` and `contract` in parallel, once: 540
  passed, 3 failed. J20's capabilities case (both configurations) named three gated groups; updated,
  it passes. `test_the_database_goes_away_while_running[generated-a]` (J12) passed when run again on
  both configurations: it fails when the C10 deriver's once-a-second poll falls inside the outage,
  because the deriver logs the outage's first failure with its traceback and the case allows none.
  That is C10's behaviour, not changed here; recorded in TODO for a decision.
- `ruff check app/ tests/`: clean.
- **Not run:** `consumer` (the consumer router and answers are unchanged; J30 runs in `feed`),
  `volume` (no data read or write path changed), the frontend (unchanged), `budget` and the full
  suites (R).

#### C12: The dispatcher

**Delivered 2026-10-06** ([record](#c12-delivery-record)). Planned 2026-10-06. The user decided C-D103–C-D108 and C-D111 the same day, and C-D109 as a
revision of C-D94 (a filter that stops matching suspends at once), and C-D110 from the user's
proposal (a reset on resume, replacing `acknowledgeLoss`, which revises C-D93). The test cases are
approved (2026-10-06); C12 is ready to deliver. C-D7, C-D12 (both revised), C-D90, C-D93,
C-D98, C-D101 and C-D102 apply as written.
**Needs:** C11 (subscriptions, their acknowledged position, the sealed signing key, the
allowlist). **Groups:** `feed`, `startup` (migration, the dispatcher started in the lifespan),
`contract` (the subscription answer and the capabilities group change).
**Design:** CONSUMER_API "Delivery", "Subscriptions (runtime, not model)" (the C12 reasons),
"Security (0.12)"; C-D7, C-D12, C-D90, C-D93, C-D94, C-D98, C-D101, C-D102; INTEGRATION_API F3
(position order).

**Behaviour.** An active subscription receives its events at its URL, in position order, signed. A
per-change subscription gets POSTs of up to 100 events, each event with its object as get by ID
answers it (or only its identity). A coalesced one gets one POST per event saying "this scope
changed" once the changes pause. A receiver that answers `2xx` acknowledges the batch, and the next
one follows. A receiver that fails is retried with backoff, with the same batch and the same
delivery ID, and nothing later is sent past it. After 24 hours of failures the subscription is
suspended `DELIVERY_FAILED`, and a resume continues from the first unacknowledged event. The
operator sees the delivery state on the subscription: the last success, the failing attempts, the
last error and the next attempt. The dispatcher also suspends a subscription whose host the
allowlist no longer names (`HOST_NOT_ALLOWED`), whose filter no longer matches any record
(`FILTER_MATCHES_NOTHING`, at once, C-D109), and one whose next events expired while it was active
(`EVENTS_EXPIRED`, C-D110).

```http
POST /rdm HTTP/1.1
Host: hooks.example.test
Content-Type: application/json
User-Agent: rdm-engine
RDM-Delivery-Id: 6f1c…                 (the same on every retry of this batch)
RDM-Timestamp: 1791281643              (Unix seconds, new on every attempt)
RDM-Signature: sha256=3b9e…            (hex HMAC-SHA256 of "{timestamp}.{body}" with the signing key)

{ "deliveryId": "6f1c…", "subscriptionId": "…", "consumerApi": "rdm", "contractVersion": 1,
  "workspaceKey": "main", "events": [ … ] }     // CONSUMER_API's per-change body
```

```jsonc
// GET /api/v1/consumer-subscriptions/{id} gains (C-D108)
"delivery": {
  "lastDeliveredAt": "…",          // the last acknowledged POST, null before the first
  "pending": {                     // null when nothing is being retried
    "deliveryId": "…", "throughPosition": 184223,
    "attempts": 3, "failingSince": "…", "lastAttemptAt": "…", "nextAttemptAt": "…",
    "lastError": { "kind": "status", "status": 503, "message": "Service Unavailable" }
  }
}
```

**What exists today** (checked 2026-10-06):

- **Subscriptions** (`consumer_subscriptions`, C11): the consumer API, contract version, workspace,
  `event_keys`, `filters` (each a list of strings), `url`, `mode`, `debounce_seconds`, `payload`,
  `status` and the suspension's reason, message and details; `acknowledged_position` and
  `acknowledged_ordinal`, set at create to the feed head (or `startAfter`) with the ordinal "after
  every event of the position"; `signing_key` sealed with AES-256-GCM, the public ID as associated
  data (`common/sealing.py`). Every change claims `version` under `FOR UPDATE`. No delivery state.
- **The pull feed** (`reads/consumer_events.read_consumer_events`) already reads what a subscription
  receives: events after a `(position, ordinal)` key, narrowed by event keys and the definition's
  parameters (C-D90), each with its identity and, with `full`, its object composed by
  `ConsumerObjects.compose` and labelled `stateAt`. A narrowed read scans at most ten pages and may
  return fewer items with the key advanced. It answers an encoded cursor, not the key.
  `event_window` and `check_after` give the derived head, the earliest kept position and the `410`.
- **The filter check** `reads/consumer_parameters.unmatched_values` answers
  `FILTER_MATCHES_NOTHING` for a value no record matches now (C-D100).
- **The URL check** `events/webhook_urls.check_webhook_url` applies the allowlist (C-D101); it does
  not resolve names. Its docstring leaves resolution and redirects to C12.
- **Background threads** in the API process: the job worker (B2, a lease per job:
  `lease_owner`, `lease_expires_at`) and the event deriver (C10, `events/worker.py`, polling once a
  second, `run_until_idle` for tests, `run_event_deriver` False in tests). `lifespan` starts each
  only when the model is ready. `WEB_CONCURRENCY` may be above 1 when model administration is off,
  so two processes can run a dispatcher.
- **No HTTP client** is a runtime dependency (`httpx` is a dev dependency, for tests).
- **Tests:** `test_j30_subscriptions` starts the application with the capability on, the allowlist
  `hooks.example.test, localhost` and a key; `scenario.derive_events` drives the deriver;
  `test_j30_consumer_events._age` moves entries' times back (J30.5).
- **Outage logging (TODO from C11, decided 2026-10-06 by the user):** the job worker
  (`jobs/worker.py:310`) and the deriver log the first failure of a database outage with
  `logger.exception`, an ERROR with the traceback, against AGENTS.md's rule for expected operational
  failures. J12.8's case (`test_the_database_goes_away_while_running`) allows no ERROR with a
  traceback; it fails when the deriver's once-a-second poll falls inside the outage, and passes with
  the job worker only because it idles 60 s between polls.

**Design.**

- **Thread** `engine/events/dispatcher.py`, `EventDispatcher` beside the deriver: `run_once(now)`,
  `run_until_idle(now)` for tests, `start` and `stop`. `create_app` builds it only with
  `CONSUMER_SUBSCRIPTIONS_ENABLED` (C-D102); `lifespan` starts it when the model is ready and
  `run_consumer_dispatcher` is true. Once a second it claims the subscriptions that are due and
  handles each on a pool of four sender threads; one subscription is never handled twice at once,
  which keeps its order (C-D106).
- **Claim** (C-D106): one statement sets `lease_owner` and `lease_expires_at` (60 s) on up to four
  active subscriptions that are due (`next_attempt_at` is null or past) and not leased, picked
  `FOR UPDATE SKIP LOCKED`, oldest lease first. The lease is renewed before each send. No row lock
  is held while a request is in flight, so an edit, suspend or delete never waits for a receiver.
- **One step for a subscription** (`dispatch_one`):
  1. Read the active release's definition; a subscription the release does not serve is already
     suspended by C11's hook, so nothing here re-checks the model.
  2. Check the URL against today's allowlist; refused → suspend `HOST_NOT_ALLOWED` with C11's
     refusal as details.
  3. Check the acknowledged position against the event window; expired → suspend `EVENTS_EXPIRED`
     with the lost range and the publication (C-D110).
  3a. When events follow the acknowledged position, check each filter value (`unmatched_values`);
     one that matches no record → suspend `FILTER_MATCHES_NOTHING` naming the filter, the value and
     the acknowledged position, before anything is sent (C-D109).
  4. **Per change.** If a batch is pending, read it again: the events in (acknowledged, pending
     end], with the same delivery ID. Otherwise read the next events through the pull feed's read
     with the subscription's events, filters and payload, up to 100, and cut the batch at the byte
     limit (C-D104). Nothing matched but the read advanced → store the advanced position, no POST.
     **Coalesced** (C-D105): count the matching events after the acknowledged position, per event
     key; when the newest is older than `debounceSeconds`, or the oldest older than 10 minutes, send
     one POST per event key in the order of their first positions, through the newest event.
  5. Commit the batch as pending (delivery ID, end key) before sending, so a crash retries the same
     batch with the same ID.
  6. Send (C-D107): resolve the host, refuse a link-local address (and a loopback one unless the URL
     names a loopback host), connect to the checked address with the host name for TLS, POST with
     the headers above, 10 s for the whole exchange, no redirects followed, at most 4 KiB of the
     answer read for the error message.
  7. `2xx`: one transaction checks the lease is still held, sets the acknowledged key to the batch's
     end, clears `pending` and the failure fields, sets `last_delivered_at`. Anything else: records
     the attempt and the next one (C-D103); past 24 hours since `failing_since`, suspends
     `DELIVERY_FAILED` with the last error.
- **Reading through the pull feed.** `read_consumer_events` is split so the dispatcher gets the
  page's items and its last key without a cursor; the pull feed's answers do not change. Objects are
  composed by the same code under the active release, `stateAt` as the pull feed sets it (C-D7). An
  event of an earlier contract version is sent as the pull feed serves it, naming its own version
  (C-D88).
- **Signing** (C-D12): the key is unsealed with the deployment key for each send and not kept in
  memory between sends. The body is the compact JSON's UTF-8 bytes; the signature covers exactly
  them.
- **Versions.** Delivery progress (the acknowledged key, pending batch, failures) does not change
  `version` or `updatedAt`, so an operator's edit is never refused because events were delivered;
  a suspension by the dispatcher does, as any status change (C-D108).
- **C11's operations** keep their contracts and gain: `resume` clears the pending batch and the
  failures, so the next attempt is immediate and from the first unacknowledged event (CONSUMER_API
  "resume continues from the first unacknowledged event"), and gains `reset` (C-D110): `true`
  moves the acknowledged position to the workspace's feed head at the resume. `acknowledgeLoss`
  is removed (C-D93 revised): an amendment of C11's resume and its J30.7 case, which the
  implementing agent changes as the revised decision says. `PATCH` that changes the URL, events,
  filters, mode or payload drops the pending batch (a new one, with a new delivery ID, is built for
  the next attempt, which is immediate), keeping the acknowledged position; `delete` ends delivery,
  and an acknowledgement for a deleted subscription changes nothing.
- **Store** (migration `…_consumer_deliveries`, named at delivery): `consumer_subscriptions` gains
  `lease_owner`, `lease_expires_at`, `pending_delivery_id`, `pending_position`, `pending_ordinal`,
  `attempts`, `failing_since`, `last_attempt_at`, `next_attempt_at`, `last_error` jsonb,
  `last_delivered_at`; a partial index on
  `next_attempt_at` where `status = 'active'`. Existing rows get nulls and zero attempts. The
  reason column has no check constraint, so the four new reasons need no schema change.
- **Capabilities.** `consumerSubscriptions` gains `delivery`: `maxEvents` 100, `maxBytes`,
  `timeoutSeconds` 10, `retryHours` 24, so no limit is undocumented. The management OpenAPI lock is
  re-baselined (diffed: this group only); the gated document's case checks the subscription answer's
  `delivery` and the reasons.
- **Logging.** One line per failed attempt (subscription, delivery ID, status or error kind) at
  INFO, one WARNING per suspension; no traceback for a receiver's failure, since it is the
  receiver's state, not the engine's.
- **Outage logging in the three loops** (decided 2026-10-06 by the user; an amendment of B2's and
  C10's code). One helper the job worker, the deriver and the dispatcher share: a failure to reach
  the database (a connection error) is one plain ERROR line saying what failed and that the thread
  retries every 2 s, with the traceback at DEBUG; the once-a-minute reminder and the "reaches the
  database again" line stay. Any other exception keeps its traceback at ERROR: it is a defect in the
  engine's code, and the traceback is the only way to find it. J12.8's case holds it unchanged.
- **No frontend** (the Webhooks page is U5), **no pull-feed change**, **no new setting**: the batch
  size, byte limit, timeout and retry window are constants reported in capabilities. CA bundles come
  from the system trust store, which `SSL_CERT_FILE` overrides (OPERATIONS); an outbound proxy is
  not supported in 0.9 (TODO, for the user to place).

**Decisions** (each proposed; status per row):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D103 | The retry schedule | **Approved 2026-10-06.** The user asked for it to be documented well (DOCUMENTATION_PLAN, points to state clearly). After a failed attempt the next waits 10 s, 30 s, 1 min, 2 min, 5 min, 10 min, 30 min, then every hour, each with ±20 % jitter, until 24 hours after the first failure of the batch (`failing_since`); then `DELIVERY_FAILED`, with the last error and the delivery ID in the details. About 30 attempts in all: short outages are bridged within minutes, and a receiver down for a day is not hammered. The clock starts at the first failure of the batch, not the subscription, so one success resets it. Constants, reported in capabilities; a setting would be added only on a real need |
| C-D104 | The byte limit of a `full` batch | **Approved 2026-10-06.** The user asked for it to be documented well (DOCUMENTATION_PLAN, points to state clearly). 1 MiB of body. Events are added in order while the body stays within it; an event that alone exceeds it is sent alone, since skipping it would break order and lose a change. 1 MiB passes the default request limits of common receivers (nginx's default is 1 MiB, most frameworks allow more), and 100 typical objects stay well below it. `identity` batches are small and stop at 100 |
| C-D105 | How coalesced mode decides and what it sends | **Approved 2026-10-06.** Stateless over the event store: at each look, the matching events after the acknowledged position, per event key; send when the newest is `debounceSeconds` old, or the oldest 10 minutes old, by `occurredAt`. One POST per event key (the body names one `event`), in the order of their first positions; the acknowledged key moves to the newest event counted once every POST of the round is acknowledged. A failure retries the round as per-change does. `payload` does not apply: the body carries no objects (CONSUMER_API's body); a `full` subscription in coalesced mode is accepted as C11 does and documented as such, rather than changing C11's contract. Rejected: a debounce timer per subscription in memory (lost on restart, and two processes would disagree) |
| C-D106 | Several processes, and a slow receiver | **Approved 2026-10-06.** A lease per subscription in the row, as the job worker's (B2): 60 s, renewed before each send; an acknowledgement commits only while the lease is held. Four sender threads per process, one subscription each at a time, so a receiver timing out (10 s) delays only its own subscription. Rejected: holding the row's lock during the request (an operator's edit would wait up to 10 s), and one sequential loop (one slow receiver delays every other) |
| C-D107 | What the dispatcher checks when it connects (left to C12 by C-D101) | **Approved 2026-10-06.** It resolves the host at each attempt and connects to an address it checked, never resolving twice, so a name cannot be pointed elsewhere between the check and the connection. A link-local address (`169.254.0.0/16`, `fe80::/10`, which hold cloud metadata services) is always refused; a loopback address only when the URL names a loopback host the allowlist lists. Private ranges are allowed: integrations inside the organisation's network are the common case, and the allowlist names them. A refused address is a failed attempt (`kind: "address"`), retried, since a DNS change may be temporary. Redirects are not followed: a `3xx` is a failed attempt naming the `Location`, so a receiver cannot send events to an unlisted host. TLS is verified against the system trust store. The client is the standard library's `http.client` and `ssl`, which allow connecting to a checked address with the name for TLS; no runtime dependency is added. No outbound proxy in 0.9 |
| C-D108 | What the operator sees of delivery, and whether it changes `version` | **Approved 2026-10-06.** The subscription answer gains `delivery` (shape above): the last acknowledged POST, and the batch being retried with its attempts, first failure, last and next attempt and last error (`kind` `status`, `timeout`, `connection`, `tls`, `address`, `redirect`, with `status` and up to 200 characters of the answer or error). Delivery progress changes neither `version` nor `updatedAt`, which describe the configuration an operator edits; otherwise every delivered batch would make an edit read with the previous version fail `409 VERSION_CONFLICT`. A suspension raises `version`. No delivery history is kept (a log per attempt is U5's or later's question); the receiver has the delivery IDs. _Amended 2026-10-07 (U5a, C-D116, the user): every request and attempt is logged, kept for `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`_ |
| C-D109 | When `FILTER_MATCHES_NOTHING` is decided (C-D94) | **Decided 2026-10-06 by the user, revising C-D94.** At once: when events follow a subscription's acknowledged position, the dispatcher checks each filter value before it sends; a value that matches no record suspends the subscription `FILTER_MATCHES_NOTHING`, naming the filter, the value and the acknowledged position. The deletions are not delivered first. A record a filter names is not deleted by accident: whoever deletes it is changing the structure, and the subscription's owner edits the filter. Nothing is lost: the acknowledged position does not move, so after the edit and resume the events from it are delivered, the deletions among them (a deletion passes every filter but the type, C-D90). Replaces the proposal to wait until the deletions were delivered (two steps and two columns), which the user judged overengineered |
| C-D110 | An active subscription whose next events expired, and a reset on resume | **Decided 2026-10-06 by the user** (their proposal, with `reset` replacing `acknowledgeLoss`). An active subscription whose acknowledged position has expired (the capability turned back on after the retention period, C-D102, or the process down that long) is suspended `EVENTS_EXPIRED` with the lost range and the publication to re-sync from. **Resume gains `reset`** (any reason): `true` starts delivery after the workspace's feed head at the resume, as a new subscription starts (C-D97), and the receiver re-syncs what it missed itself (a publication's lists today, an export job from J1); without it, delivery continues from the first unacknowledged event, and a resume whose unacknowledged events expired is refused `409 EVENTS_EXPIRED` as C-D93 has it, its message naming `reset`. A gap-free re-sync resets first and reads after: changes in between arrive twice, never not at all. `reset` replaces `acknowledgeLoss` (C-D93 revised, delivered in C11): `acknowledgeLoss` continues from the earliest event still kept, so the receiver still has a gap to repair by a re-sync, after which the kept tail only repeats it; two ways to accept a loss would also need explaining on the Webhooks page. Replacing it is a revision of C-D93 and an amendment of C11's resume, done in C12 |
| C-D111 | Retry of a batch whose events changed meanwhile | **Approved 2026-10-06.** A pending batch is fixed by its range (acknowledged key to end key) and its delivery ID; each attempt reads that range again and composes the objects again, so a retry carries the current state (`stateAt` later than before, as CONSUMER_API says) and the same events, as events never change. A filter or payload edit drops the pending batch (C-D108's PATCH rule), so a batch never mixes configurations under one delivery ID |

**Journey.** J30 gains **J30.8 Receive** (per change, coalesced, filters and payload, signature,
order and batches, the delivery state) and **J30.9 A receiver that fails or a subscription that
cannot continue** (retries, `DELIVERY_FAILED` and resume, `HOST_NOT_ALLOWED`,
`FILTER_MATCHES_NOTHING`, `EVENTS_EXPIRED`). J30's status says webhooks are delivered from C12. The
tests start a receiver on `localhost` (the standard library's HTTP server in a thread, in the test
module, answering as each case scripts: `200`, `503`, a slow answer, a redirect, recording each
request's headers and body) and drive the dispatcher with `run_until_idle(now=…)` and a clock the
test moves, as `derive_events` drives the deriver; no test waits on real time. J30's
configurations, release with events and settings are reused; no seed is rebuilt.

**Test cases** (approved by the user 2026-10-06; journey tests on generated A and B, written first
and confirmed failing: nothing is delivered):

1. **J30.8 Per change.** A `full` subscription; create, change and delete exposed records: one POST
   with the events in position order, CONSUMER_API's body, each object equal to get by ID with the
   subscription's filters, the deletion without an object. `RDM-Signature` verifies with the
   `signingSecret` over `"{RDM-Timestamp}.{body}"`; a body changed by one byte does not.
   `acknowledgedThrough` is the last event's position and `delivery.lastDeliveredAt` is set.
2. **J30.8 Batches.** A batch job of 250 exposed items: three POSTs of 100, 100 and 50 in position
   order, the second sent only after the first was answered; with `identity`, no `object` or
   `stateAt`. An event the subscription does not name, or a record its filter excludes, is not sent;
   a change only outside its scope moves `acknowledgedThrough` with no POST.
3. **J30.8 Coalesced.** With `debounceSeconds` 60, a few changes: nothing while the dispatcher's
   clock is less than 60 s past the newest event, then one POST with `fromPosition`, `toPosition`,
   `eventCount` and `objectTypes`. Events whose oldest is aged 10 minutes (as J30.5 ages entries)
   while a new one has just arrived: a POST at once, and the next after the pause.
4. **J30.9 Retries.** The receiver answers `503`: nothing later is sent; the subscription shows
   `delivery.pending` with the attempts, `lastError` and `nextAttemptAt`; the next attempt carries
   the same `RDM-Delivery-Id` and a new timestamp. A redirect and a slow answer (past 10 s) are
   failed attempts of their kind. The receiver recovers: the batch and the ones after it arrive in
   order, `pending` is `null`, `version` unchanged.
5. **J30.9 Suspension and resume.** The receiver fails for 24 hours on the test clock: `suspended`,
   `DELIVERY_FAILED` with the last error, `version` raised. Further changes are not sent. Resume:
   every event from the first unacknowledged one arrives, in order, none skipped.
6. **J30.9 Host and filter.** The application restarted with an allowlist without the host: the
   subscription is `HOST_NOT_ALLOWED` before any request. A subscription filtered on one container;
   the container and its records are deleted: no request is sent and the subscription is
   `FILTER_MATCHES_NOTHING` naming the filter, the value and its acknowledged position (C-D109).
   After the filter is edited to another container and the subscription resumed, the deletions
   arrive.
7. **J30.9 Expired while active, and reset.** Events past the subscription's position aged beyond
   retention (as J30.5): `EVENTS_EXPIRED` with the range and the publication; a plain resume is
   `409 EVENTS_EXPIRED`; a resume with `reset` is `active` with `acknowledgedThrough` at the feed
   head, and only changes made after it arrive. A subscription suspended by hand while changes are
   made, resumed with `reset`, receives none of them (C-D110).
8. **Two dispatchers.** Two dispatchers on one database (two processes' leases) handle one
   subscription through 300 events: each batch arrives once, in order.
9. **Unit:** the outage helper (a connection error logged without a traceback, then once a minute;
   another exception with it); the retry schedule and the 24-hour cut; the byte-limit cut (an event alone over the
   limit is sent alone); the signature over known bytes; the address check (link-local refused,
   loopback only for a loopback URL, private allowed); the coalesced decision over event times.
10. **Startup:** the migration on a clean database and from `20261006_02`; with the capability off,
    no dispatcher starts.

**Checks:** J30.8 and J30.9 on generated A and B; the unit tests; the C11 cases (`test_j30_subscriptions`,
edit and resume change); the `feed` group once; `startup` (migration; J12.8's outage case and J24's background-job cases for the shared outage
logging); `test_openapi_contract` (lock
re-baselined for capabilities, the gated document) and `test_api_journeys`; `ruff`. Not run:
`consumer` (no consumer answer changes; the pull feed's split read is covered by
`test_j30_consumer_events`, run as a targeted module), `volume` (the bulk-volume delivery budget is
C13's), the frontend, `budget` and the full suites (R).

**Exit:** active subscriptions receive their events in order, in signed batches of at most 100 and
1 MiB or as coalesced notices; failures are retried with the same delivery ID and suspend after
24 hours; host, filter and expiry suspensions carry their reasons; a resume continues from the first
unacknowledged event; the delivery state is visible on the subscription.

**Docs at delivery:** the retry schedule (C-D103) and the byte limit (C-D104) are documented in
full, as the user asked (2026-10-06; DOCUMENTATION_PLAN, points to state clearly): each wait and its
jitter, when the 24 hours start and what resets them, what a receiver should answer and how fast;
how a batch is cut, the event sent alone over the limit, and the request size a receiver's server
must accept, with nginx's default as the example. Then CONSUMER_API (Delivery: the headers' exact
form, the byte limit, the retry schedule, coalesced per event, redirects and addresses, the
reasons, `reset` and the order "reset, then re-sync"; C-D94 revised, C-D103–C-D111; the C12 row);
API.md (the `delivery` object, the reasons, the capabilities group); ARCHITECTURE (the dispatcher
thread, the lease, the pending batch); OPERATIONS (what a receiver must answer, the trust store and
`SSL_CERT_FILE`, no proxy, link-local refusal, the suspensions and what to do for each);
USER_JOURNEYS J30.8 and J30.9; API_JOURNEYS; CURRENT_FUNCTIONALITY; OPERATIONS also states what
the background threads log during a database outage and how to see the traceback (DEBUG); EXECUTION_GUIDE (new modules,
counts); SETTINGS_AND_UI_PLAN's Webhooks row (the delivery state U5 shows); CHANGELOG,
PROJECT_STATUS, TODO.

**Composable domains (ADR-032):** no door is affected. Delivery reads the events and composes
objects through get by ID; identity, attribute storage, audit/history, the bulk APIs, `match` and
mapping coverage are untouched, and the store gains delivery state only, no record values.

##### C12 delivery record

**Delivered 2026-10-06**, as designed, with C-D103–C-D111 and C-D93 and C-D94 revised.

- **Dispatcher** (`engine/events/dispatcher.py`): the claim (one `UPDATE … WHERE sequence_id IN
  (SELECT … FOR UPDATE SKIP LOCKED)`, a 60 s lease, least recently handled first), one step per
  subscription (the host, expiry and filter checks, then the batch, stored as pending before it is
  sent), the outcome recorded under the lease, and the thread with four senders. `create_app` builds
  it only with the capability on; `lifespan` starts it where the model is served
  (`run_consumer_dispatcher`).
- **Delivery** (`engine/events/delivery.py`): the limits, the retry schedule, the coalesced
  decision, the encoding (as the API writes values), the 1 MiB cut, the signature and the headers.
- **Client** (`engine/events/webhook_client.py`): the standard library's `http.client` and `ssl`;
  one resolution per attempt, the address check, a connection to the checked address with the host
  name for TLS, no redirects, 4 KiB of the answer, failures by kind.
- **The pull feed's read** (`reads/consumer_events.py`) is split into `event_filters` and
  `event_page` (with an optional end key, `through`); `read_consumer_events` answers as before.
- **C11's service**: `resume` takes `reset` (C-D110) and clears a failing batch; `PATCH` drops it
  (`clear_delivery`); `secret_text` gives the key as `signingSecret` shows it; the four reasons are
  constants in `subscription_rules`.
- **Outage logging** (`common/outage.py`): `OutageLog` and `database_unreachable`, used by the job
  worker, the deriver and the dispatcher; the TODO from C11 is closed.
- **Store** (migration `20261006_03`): the delivery columns and `ix_consumer_subscriptions_due`.
- **API**: the subscription's `delivery` (`SubscriptionDelivery`, `PendingDelivery`,
  `DeliveryError`), `EVENTS_EXPIRED` among the reasons, `reset` on resume,
  `consumerSubscriptions.delivery` (`WebhookDeliveryLimits`) in capabilities; the management OpenAPI
  lock re-baselined (diffed: the capabilities group's description and `delivery`, nothing else).
- **Docs**: CONSUMER_API (Delivery rewritten, the retry schedule and the size limit stated in full
  as the user asked; C-D93 and C-D94 revised; C-D103–C-D111; the C12 row), API.md (capabilities,
  the subscription's `delivery` and reasons, resume's `reset`, "Webhook delivery"), ARCHITECTURE
  (the dispatcher, the outage log), OPERATIONS (outage lines, a Delivery section: what a receiver
  must do, a failing receiver, each suspension and its fix, addresses, TLS and `SSL_CERT_FILE`, no
  proxy, several processes), USER_JOURNEYS (J30.8, J30.9, J30's status), API_JOURNEYS,
  CURRENT_FUNCTIONALITY, EXECUTION_GUIDE (groups, counts, two changed-boundary rows),
  SETTINGS_AND_UI_PLAN's Webhooks rows, DOCUMENTATION_PLAN (the two points to state clearly, added
  at planning), CHANGELOG, PROJECT_STATUS, TODO.

**Differs from the plan:**
- **The signature's key is the `signingSecret` text**, exactly as the create answered it, not the
  32 bytes it encodes: a receiver uses what it was given, with no decoding to get wrong.
- **Capabilities also report the schedule** (`retryWaitsSeconds`, `laterWaitSeconds`), so the whole
  retry rule is readable from the API, not only the window.
- **A coalesced round has one delivery ID; each notice's `deliveryId`** is derived from it and the
  event key (UUID 5), so each request has its own ID and keeps it on every retry.
- **An object deleted after its event** is sent without an object, as the pull feed answers it
  (C-D7: composed when sent). The first draft of case 1 expected an object for every event that is
  not a deletion; the case's text is unchanged, its assertion was corrected to C-D7.
- **The host and two-dispatcher cases** build a second `EventDispatcher` on the application's
  session factory (one with another allowlist), standing for a second process, instead of
  restarting the application.
- **Lease renewals and `RDM-Timestamp`** take the later of the round's clock and the real clock, so
  a long round's later sends renew the lease for real time, while a test's clock still leads.
- **Tests changed by the package's own decisions:** C11's expired-resume case uses `reset` and reads
  the feed head from the `410` details (after aging, the feed read is itself expired); C11's two
  capabilities cases include `delivery`; J24.6 and the worker's unit outage case expect no traceback.
- **Found and fixed during the build:** the claim's subqueries were not correlated to the outer row
  inside `UPDATE … IN (SELECT …)`, so with several subscriptions the claim failed; the batches case
  found it.
- **Documents and code that differed:** EXECUTION_GUIDE's `jobs` count (78) was stale; it is 145.
- **Your development database:** a `uvicorn --reload` process (not started here) was running and
  will have applied `20261006_03` to it on reload.

**Checks:**
- **Failing first:** the 16 cases of `test_j30_delivery` (generated A and B) failed (no dispatcher);
  all pass.
- **Targeted:** `test_j30_delivery` 16; the unit tests of delivery, the client and the outage log
  44; the startup cases (the upgrade from `20261006_02` with a subscription and two starts, the
  interrupted revision, C11's upgrade, the clean boot, the failed migration) 5;
  `test_openapi_contract`, `test_api_journeys`, `test_boundaries` 17; `test_j30_subscriptions`,
  `test_j30_consumer_events`, `test_j24_background_job`, `test_j20_discover`, the worker's unit tests
  and J12.8's outage case 61: all passed.
- **The thread**, once, by a throwaway case (deleted): three subscriptions delivered through the
  sender pool, then the thread stopped.
- **Groups**, once each: `feed`, `startup` and `contract` in parallel, 324 passed in 1 min 25 s (no
  serial part); `consumer`, 366 passed in 1 min 54 s (its serial part empty); `jobs`, 144 passed in
  36 s and its serial part 1.
- `ruff check app/ tests/`: clean.
- **Not run:** `volume` (the split read issues the same statements; the bulk delivery budget is
  C13's), `model_admin` and `workspaces` (their hooks are unchanged), the frontend (unchanged),
  `budget` and the full suites (R).

#### C13: Event acceptance

**Delivered 2026-10-06** ([record](#c13-delivery-record)). Planned 2026-10-06; C-D112–C-D114 and the test cases approved by the user the same day.
**Needs:** C12 (delivered). **Groups:** `feed`, `consumer`, `volume` (the events line's checkpoint
run, as C8 ran the read line's).
**Design:** CONSUMER_API "C13 event scenarios", "Subscriptions (runtime, not model)", "Delivery",
"Pull feed"; C8 scenario 14; C-D7, C-D89, C-D90, C-D94, C-D103–C-D110.

**Behaviour.** The events line's checkpoint, as C8 was the read line's. C9–C12 each proved its own
mechanism: events in the pull feed (C10), subscriptions (C11), delivery (C12). C13 proves the
CONSUMER_API scenarios end to end, from a write through the deriver and the dispatcher to a
receiver, compared with the pull feed and the lists. It also adds the delivery budget the
scenarios name, which C10's budgets did not cover. No journey is added and no product change is
planned. A case that finds a defect is fixed in C13 when the fix stays in the events code; anything
larger becomes an amendment package ("Deviations"). C-D114 may add documentation only.

**What exists today** (checked 2026-10-06):

| # | CONSUMER_API scenario | Evidence today | Left for C13 |
| --- | --- | --- | --- |
| 1 | A watched field makes `updated`, an unwatched one none | J30.1 (`test_an_objects_own_changes_are_told`: the watched event leaves out the score change) | — |
| 2 | Editing a projected record updates its owner, naming the projection | J30.2 (the K's rename) | — |
| 3 | Deleting the projecting relation updates the former owner | J30.2 (last step) | — |
| 4 | A publish with many changes: one event per object, one cause, in batches | J30.3 (a publish of two changes, pull feed); J30.8 batches (250 items from a batch job, not a publish) | A publish of more than 100 changes, delivered |
| 5 | A rolled-back write makes no event | J30.3 (a refused write; an independent batch's failed item); J26 (an atomic batch rolled back, raw feed only) | The atomic rollback, at the events and the receiver |
| 6 | Change-set edits, validation and discard make no event | J30.3 (edits); J26 (validation and discard, raw feed only) | Validation and discard, at the events and the receiver |
| 7 | Filters scope deliveries as the list or XREF parameters do | J30.4 (pull feed: type, related and projection narrowings against a list); J30.8 (a type filter that matches nothing sent) | A delivered, filtered subscription compared with the list; a record leaving the scope (C-D114) |
| 8 | Coalesced mode: once after the debounce, at the maximum wait | J30.8 (`test_a_coalesced_subscription_is_told_once_the_changes_pause`) | — |
| 9 | A failing receiver: retries in order, suspension, resume delivers everything | J30.9 (retries; 24 hours; resume) | — |
| 10 | _0.12:_ signature fails after rotation | Signing in 0.9 is verified by J30.8; rotation is 0.12 (C-D1, C-D12) | Out of scope |
| 11 | A disallowed or non-HTTPS target refused at create and update | J30.6 (`test_a_subscription_the_definition_or_deployment_cannot_serve_is_refused`, create and edit) | — (wording, below) |
| 12 | A release removing a subscribed event suspends with a reason | J30.7 | — |
| 13 | The pull feed and webhooks carry the same events; `410` beyond retention | J30.8 (one request against the pull feed); J30.5 (`410`) | The same comparison over many batches and a publish |
| C8 14 | After `410`, a re-sync from a publication misses nothing and repeats only seen events | J30.5 (the publication's list and the events after its `eventSequence` end at live data) | The webhook form: `EVENTS_EXPIRED`, `reset`, re-sync (C-D110's order) |
| — | A bulk-volume delivery budget | C10 measured derivation and the pull feed at full volume (POSTGRESQL_BUDGETS §7) | Delivery not measured |

Also found:

- **No kept test runs the two threads.** The journey application starts neither the deriver nor
  the dispatcher (`run_event_deriver`, `run_consumer_dispatcher` false); tests drive them with
  `derive_events` and `dispatch`. C12 ran the dispatcher's thread once in a throwaway case.
  Nothing kept shows that a write reaches a receiver on its own in a running application.
- **A record leaving a filter's scope is never told to that subscription.** Filters apply to the
  object's live state when the events are read or sent (C-D90), and no earlier state is kept
  (C-D7, C-D89). A record moved to a parent outside an `ancestor` filter, or edited so that a
  `related` or `projection` filter no longer matches it, has its `updated` event filtered out. A
  receiver following the filtered subscription keeps a copy it should drop, and nothing tells it.
  Deletions pass every filter but the type (C-D90), so this concerns moves and edits only. Neither
  CONSUMER_API, USER_JOURNEYS nor OPERATIONS states it. C-D114.
- **The dispatcher's cost.** The claim takes only subscriptions with events of their API waiting
  (`EXISTS` on `consumer_events`), so a caught-up subscription costs a share of one statement per
  second per process. A step reads the definition, the event window, each filter's values
  (`unmatched_values`) and a page (`event_page`), then commits the pending batch and, after the
  POST, the acknowledgement. Not measured at volume.
- **Documents that differ from the code:** USER_JOURNEYS J30.7 still says a resume after expired
  events is "refused unless the loss is acknowledged" (`acknowledgeLoss`, replaced by `reset` in
  C12, C-D110). CONSUMER_API scenario 11 says a "non-HTTPS" target is refused, while C-D101 allows
  plain HTTP to a listed loopback host. Both are corrected in C13's documents.

**Design.**

- **Acceptance module** `tests/journeys/test_j30_acceptance.py` (journey `J30`), on generated A
  and B with J30's structures (`LEDGER`) and settings (`SUBSCRIPTIONS`), reusing J30's helpers and
  C12's `Receiver`. No new configuration and no new seed (C-D112).
- **The comparison** used by several cases: the requests a receiver got, flattened, against the
  pull feed read after the same position with the same events, filters and payload, by
  `(eventId, position, change, id, changed)`; with `full`, each object against get by ID. Objects
  are composed when sent (C-D7), so they are compared with get by ID at the end, not with each
  other.
- **Delivery budget** (C-D113): `volume_baseline.event_scenarios` (`--only-events`) gains the
  delivery steps after the heavy group's rename (20,001 events at one position), with a receiver on
  `localhost` that answers `200` at once: a `full` and an `identity` subscription created before
  the rename and delivered through its events by `run_until_idle`; the cost of one batch (claim,
  step, acknowledgement: time, statements, ORM rows); the whole delivery; a coalesced round over
  the 20,001 events; and the claim with 100 caught-up subscriptions. `test_consumer_event_volume`
  holds the statements of a batch and of the claim at its two sizes. The full volume is measured
  once and recorded in POSTGRESQL_BUDGETS §7.
- **No migration, route, setting or frontend.**

**Decisions** (status per row):

| # | Question | Decision |
| --- | --- | --- |
| C-D112 | How C13 proves the scenarios | **Approved 2026-10-06.** As C8 and T1 did: a scenario a journey test already walks is cited in the table above, not tested again; the gaps get one composed module through a real receiver on generated A and B, compared with the pull feed and the lists. Not on C8's `parity` fixture or the operators model: events have no reference behaviour to reproduce, and scenario 2's "system value" is the example of a projected record, which J30.2 walks on both configurations. The cases test delivered behaviour, so except case 3's leaving-the-scope step (C-D114) they are expected to pass on the first run; that is recorded, not engineered around |
| C-D113 | The bulk-volume delivery budget | **Approved 2026-10-06.** The rename of the heavy group (20,001 events at one position, C10's fan-out) delivered to one subscription with a receiver that answers at once. **A batch of 100 `full` events within 100 ms** of engine time (claim, step and acknowledgement, the receiver's time excluded), the read budget: the pull feed's `full` page takes 25.5 ms (C10), and the send and two commits are added. **The whole delivery within 30 s** (about 670 events a second for one subscription); estimated at about 10 s (201 batches at about 45 ms), not measured. **The claim with 100 caught-up subscriptions within 10 ms**, since every process runs it once a second. Statements per batch and per claim equal at both sizes. One full-volume run, announced at delivery: about 6 minutes if the volume seed is rebuilt after C12's migration, about 2 otherwise. A figure over its budget is recorded with its cause, as C16's were; fixing it is the user's call |
| C-D114 | A record that leaves a subscription's filter | **Approved 2026-10-06.** Keep C-D90's rule in 0.9 and state its consequence where a receiver's author reads it (CONSUMER_API Subscriptions and Pull feed, OPERATIONS Delivery, USER_JOURNEYS J30.4 and J30.8): a filtered subscription is told of the records in its scope, and of deletions; it is not told when a record moves out of the scope or an edit stops it matching. A receiver that must drop such records subscribes with the type filter only and applies the narrower filter itself, or reconciles from the list with the same parameters. Case 3 pins the behaviour. Not fixed now because telling "left the scope" needs the object's state before the change, which events do not keep (C-D89), while filters are read at send time; checking each filter kind (`ancestor`, `related`, `projection`) against a before state is a design of its own. Not checked: how much of a before state the audit entries already hold. A TODO for the user to place; the alternative is an amendment package before R |

**Journey.** No new journey or variant. J30's status says the events are closed by C13;
USER_JOURNEYS' J30 "Evidence today" names the acceptance module.

**Test cases** (approved by the user 2026-10-06; journey tests on generated A and B; each a few calls, named by its
CONSUMER_API scenario):

1. **Scenarios 4 and 13: a publish delivered.** Given a `full` and an `identity` subscription to
   the event over every change. When a change set creates 150 R by one batch, renames one existing
   R twice and deletes another, and is published. Then each receiver gets requests of at most 100
   events in position order, each after the previous one was answered; one event per changed
   object, the twice-renamed one once; every event's cause the publication, at or below its
   `eventSequence`. What each received equals the pull feed's read with its events and payload,
   and each `full` object equals get by ID.
2. **Scenarios 5 and 6: what makes no event.** Given a `full` subscription. When an atomic batch
   whose last item is refused is rolled back, a write with a stale version is refused, and a change
   set is edited, validated and discarded; then one record is renamed live. Then the receiver gets
   one request holding only the rename's events, and `acknowledgedThrough` is the feed's head.
3. **Scenario 7 and C-D114: filters scope as the lists do.** Given three subscriptions narrowed
   by the definition's type, related and projection parameters, one each. When records in and out
   of each scope are created, changed and deleted. Then each receiver got the events of exactly the
   objects the list returns under the same parameter, plus the deletions of its type. When the
   relationship that put an R in the related filter's scope is removed, the list no longer returns
   it and that subscription receives nothing of the change (C-D114's rule), while the unfiltered
   subscription receives the `updated` event.
4. **C8 scenario 14 and C-D110: a re-sync after expiry.** Given a `full` subscription suspended by
   hand while records are written and a change set is published, then the entries aged past
   retention (as J30.5). When it is resumed, the answer is `409 EVENTS_EXPIRED` naming `reset`;
   resumed with `reset`, one more record is written, then the receiver reads the live list and
   applies what it receives for further writes and deletions. Then its copy equals the live list:
   nothing missed, and the only event repeated is the write between the reset and the list read,
   for an object the list already gave.
5. **The threads deliver on their own.** Given the application started as a deployment runs it,
   with the deriver's and the dispatcher's threads (the two run flags on), and a subscription. When
   a record is created. Then the receiver gets its event within 10 s, without the test driving
   either thread; on shutdown both threads stop and the subscription holds no lease. (It waits on
   real time, about 2 s: one poll of each thread.)
6. **Volume:** `test_consumer_event_volume` holds the statements of a delivered batch and of the
   claim at the small and large sizes, and the ORM rows a batch loads within
   `ROWS_PER_LISTED_ROW` per event.

No unit tests: C13 adds no logic.

**Checks:** the acceptance module on generated A and B; `test_consumer_event_volume`; then the
groups `feed`, `consumer` and `volume` together once (the checkpoint run). C12's `consumer` run took
1 min 54 s alone, so together they may exceed the 2-minute ceiling: announced with the expected time
at delivery, and run on the user's go-ahead. The full-volume `--only-events` run once (C-D113),
announced. `ruff`. Not run: `startup` (no migration; case 5 starts the threads through the
lifespan), `contract` (no route or code changes), the frontend, the browser runners, `budget` and
the full suites (R).

**Exit:** every C13 scenario but 10 has a journey test that passes on generated A and B; the
delivery budget is measured and recorded; C-D114 is decided and documented. Each failure is fixed
as an amendment or recorded against its package before the queue continues.

**Docs at delivery:** CONSUMER_API (the C13 row delivered; scenario 11 worded as C-D101; C8
scenario 14's "(with C13)" closed; C-D112–C-D114; C-D114's consequence under Subscriptions and
Pull feed); POSTGRESQL_BUDGETS §7 (the delivery rows); OPERATIONS (Delivery: throughput, and a
receiver whose records leave its filter); USER_JOURNEYS (J30's status; J30.7's resume corrected to
`reset`; J30.4 and J30.8 the leaving-the-scope sentence; evidence); API_JOURNEYS; EXECUTION_GUIDE
(the module, counts); TODO (C-D114's follow-up for the user to place; the roadmap item "Ordered
change feed and retryable webhooks" checked); CHANGELOG, PROJECT_STATUS.

**Composable domains (ADR-032):** no door is affected. C13 adds tests, a budget and documents; the
event store, identity, attribute storage, audit/history, the bulk APIs, `match` and mapping coverage
are untouched. C-D114's later fix, if the user places one, would read the audit's before state and
states its door then.

##### C13 delivery record

**Delivered 2026-10-06**, with C-D112–C-D114 as approved and the approved cases.

- **Acceptance module** (`tests/journeys/test_j30_acceptance.py`, journey `J30`): the five cases
  on generated A and B (10 tests), through C12's `Receiver`, compared with the pull feed
  (`_feed`) and the R list (`_listed`, every page).
- **Delivery budget** (C-D113): `volume_baseline.delivery_scenarios`, run by `event_scenarios`
  (`--only-events`), with a receiver on `localhost` that answers at once: the claim with caught-up
  subscriptions, a batch of each payload, the whole rename, a coalesced round. `SUBSCRIPTION_SETTINGS`
  turns the capability on for the run and for `test_consumer_event_volume`, which holds the
  statements of the claim, both batches and the round at its two sizes. `volume_app` now also keeps
  the dispatcher's thread off, as it does the deriver's.
- **C-D114** documented: CONSUMER_API ("Leaving the scope" under Subscriptions, the pull feed's
  narrowing), OPERATIONS (Delivery), USER_JOURNEYS (J30.4, J30.8); the fix is a TODO for the user to
  place.
- **Docs**: CONSUMER_API (the C13 row, scenario 11's wording, C8 scenario 14 closed,
  C-D112–C-D114), POSTGRESQL_BUDGETS §7 (Webhook delivery), OPERATIONS (throughput, filtered
  subscriptions), USER_JOURNEYS (J30's status and evidence; J30.7's resume corrected to `reset`),
  EXECUTION_GUIDE (the module in `feed`, the delivery rows, counts), TODO (the roadmap item
  checked, C-D114's follow-up), CHANGELOG, PROJECT_STATUS. API_JOURNEYS unchanged: no route, code or
  parameter changed.

**Figures** (full volume, 110,254 objects, POSTGRESQL_BUDGETS §7): the claim with 100 caught-up
subscriptions 4.9 ms · 1 statement (budget 10 ms); a batch of 100 `full` events 61.1 ms · 24
(budget 100 ms), `identity` 22.4 ms · 20; the rename's 20,001 events to one subscription 5.8 s
`full` (budget 30 s) and 4.0 s `identity`, 201 batches each; a coalesced round 34.6 ms · 15. Every
budget is met; the plan's estimate (about 45 ms a batch, 10 s in all) was close for the whole and
low for the batch.

**Differs from the plan:**
- **Case 3's removed record** is related to a token of its own: B11 is one-to-one, so a second
  record cannot be related to the filtered token. Its deletion passes every filter either way
  (C-D90), which is what the step shows.
- **`test_consumer_event_volume` uses 10 caught-up subscriptions**, not 100: with 100 it rose to
  11.4 s (over the 10 s line), spent creating and deleting subscriptions, while the claim is one
  statement however many there are. The full-volume run keeps 100. It now takes 5 s.
- **The checkpoint run took 1 min 24 s**, within the 2-minute ceiling, not over it as the plan
  feared.

**Found:** no defect. Every case passed on its first run, as C-D112 expected for delivered
behaviour; case 3's leaving-the-scope step confirms C-D114's rule (the token-filtered subscription
gets nothing when the relationship is removed; the type-filtered one gets the update).

**Checks:**
- **Targeted:** `test_j30_acceptance` 10 passed (generated A and B, 22 s);
  `test_consumer_event_volume` 2 passed.
- **The events line's checkpoint** (`feed`, `consumer`, `volume` together, in parallel): 484
  passed in 1 min 24 s; serial part 1 passed. Groups now: `feed` 166, `consumer` 376, `volume` 77.
- **Full volume** `volume_baseline.py --only-events --scale 1 --repeat 3`, once, announced and
  approved (seed rebuilt, 332 s; about 7 minutes in all).
- `ruff check app/ tests/`: clean.
- **Not run:** `startup` (no migration; case 5 starts the deriver's and the dispatcher's threads
  through the lifespan of a second application on the same database), `contract` (no route or code
  changed), the frontend (unchanged), the browser runners, `budget` and the full suites (R).

#### C17: Webhook delivery choices: batching, payload and CloudEvents

**Planned 2026-10-07** at the user's request, after a review of the delivery modes against industry
practice. **Decisions C-D120–C-D128 and the test cases approved by the user the same day**, with
C-D123 changed: no subscription is in production, so nothing is converted. **Checked against the
code after the U5a resend revision (2026-10-07):** the resend lives in `engine/events/resend.py`
and branches on the `kind` column this package drops; the dispatcher's branch is `_per_change`, not
`_batch`; `headers` fixes the content type; a batch's list of requests exists only for coalesced;
the Deployment page, `WebhookDeliveries` and the U5 runner show coalesced or notice states. The
Contract, Design and test cases below now say what happens to each; no approved decision changed.
**Needs:** U5a (webhook names and the delivery log share the subscription, the dispatcher, the
dialog and the delivery log's rows). **Groups:** `feed`, `consumer`, `contract`, `startup`
(migration). Amends C-D105 (retired), C-D104 (the event cap becomes a subscription setting) and
U5a's C-D119 (no notice rows).

**Why.** A subscription today chooses `mode` (`perChange` or `coalesced`) and `payload` (`full` or
`identity`). The two modes are not two ways of grouping the same messages. `perChange` sends the
events, up to 100 in a request. `coalesced` sends a different message, a count of changes for each
event key after the changes pause, with no event IDs or objects. So `payload` does nothing there:
a `coalesced` subscription with `payload: full` is accepted and the `full` is ignored silently
(C-D105). Neither name is an industry term. Practice (checked 2026-10-07) treats delivery as two
independent choices:

- **What a message carries.** Fowler's *event notification* vs *event-carried state transfer*.
  Stripe's *thin* vs *snapshot* events. Microsoft Graph's *basic* vs *rich* notifications
  (`includeResourceData`).
- **How many events a request holds.** Azure Event Grid sends one event per request by default.
  Batching is opt-in per subscription (`maxEventsPerBatch` 1–5,000, `preferredBatchSizeInKilobytes`
  up to 1,024), and a batch succeeds or fails as a whole. CloudEvents' HTTP binding has a *batched*
  content mode, a JSON array under `application/cloudevents-batch+json`.

Summaries like `coalesced` exist only as a safeguard at volume, not as a subscriber's choice.
Salesforce Change Data Capture merges one identical change to many records into one event with
`recordIds`, and sends an overflow event past 100,000 changes in a transaction. EIP's nearest
pattern is the Aggregator, with a completeness condition that may be a timeout.

**Behaviour.** An operator creating or editing a webhook makes three independent choices. Every
combination is valid and does what it says.

1. **Requests: one event per request** (the default) **or batched, up to N events** (N from 2 to
   1,000). A batch also stops at 1 MiB. It holds what is waiting when it is sent and never waits to
   fill up.
2. **Content: with the object** (`full`, the default) **or notification only** (`identity`: the
   event's identity, its change and the changed outputs).
3. **Format: RDM JSON** (the default, today's body) **or CloudEvents 1.0**: one structured event per
   request, or a batched array.

Order, at-least-once delivery, retries, suspension, signing and the delivery log work as before,
per request. `coalesced` mode and `debounceSeconds` are removed. Its use, "run an export when data
changes", is a batched, notification-only subscription: one request per batch of changes, and the
receiver can ignore the details.

**What it costs.** Requests to a subscriber go one at a time, to keep the order (C12). With one
event per request, 10,000 changes become 10,000 requests in a row: about 8 minutes at 50 ms per
answer, longer for a slow receiver. The dispatcher already starts the next request at once while
work remains, without the one-second poll (C12), so the receiver's speed is the limit. Each request
also costs the dispatcher one claim, one events read and one record. The docs and the dialog say
that batching is the choice for bulk changes.

**Contract.**

- **Subscription** (create, `PATCH`, every answer):
  - `maxEventsPerBatch` is an integer from 1 to 1,000, default 1.
  - `format` is `rdm` (default) or `cloudevents`.
  - `payload` is unchanged.
  - `mode` and `debounceSeconds` are removed. Sending either is `422 REQUEST_VALIDATION_ERROR`, as
    any unknown field is.
  - An edit of `maxEventsPerBatch`, `format` or `payload` drops a batch being retried, as other
    edits do. Only a name edit keeps it (C-D115).
- **Capabilities.** `consumerSubscriptions.delivery.maxEvents` becomes `maxEventsPerBatch` (1,000),
  the most a subscription may set. `maxBytes` stays 1 MiB.
- **RDM JSON requests.** Today's per-change body, with 1 to `maxEventsPerBatch` events in `events`.
  A single event still comes in the envelope, so a receiver's code does not change with the batch
  size. `Content-Type: application/json`.
- **CloudEvents requests.**
  - With `maxEventsPerBatch` 1, one event in *structured* mode
    (`Content-Type: application/cloudevents+json; charset=utf-8`).
  - Otherwise a JSON array of structured events
    (`Content-Type: application/cloudevents-batch+json; charset=utf-8`), also when a batch holds one
    event, so the content type depends on the subscription and not on the traffic.
  - Each event:

    ```json
    {
      "specversion": "1.0",
      "id": "<eventId>",
      "source": "/api/consumer/rdm/v1/events?workspace=main",
      "type": "rdm.timetable-type-changed.updated",
      "subject": "TimetableType/<id>",
      "time": "<occurredAt>",
      "datacontenttype": "application/json",
      "rdmsubscription": "<subscriptionId>",
      "data": { "...": "the event exactly as the RDM JSON body carries it" }
    }
    ```

  - `data` is the same object as an item of the RDM JSON `events` array, with `position`,
    `changed`, `cause`, `stateAt` and `object` per `payload`. A receiver therefore handles `data`
    with the same code in either format.
- **Headers in both formats.** `RDM-Delivery-Id`, `RDM-Timestamp` and `RDM-Signature` (HMAC over
  `"{timestamp}.{body}"`) are unchanged. The signature covers the whole body, CloudEvents attributes
  included, which is why structured mode is used rather than binary.
- **Removed.** The coalesced body, `COALESCE_MAX_SECONDS`, and U5a's notice rows: the delivery
  log's `kind` is always events, so the field is dropped.
- **Resend** (C-D129–C-D131). `eventId` becomes required: the empty body that resent a notice is
  `422 REQUEST_VALIDATION_ERROR`, and the "a notice was given one" cause of
  `404 EVENT_NOT_IN_DELIVERY` goes. C-D129's "a notice is resent as it was" is retired with the
  notices.

**Design.**

- **Storage.** Revision `20261007_03`, after U5a's `_01` (the delivery log) and `_02` (manual
  resend), works on `consumer_subscriptions`:
  - Adds `max_events_per_batch` (integer, not null, check 1–1,000) and `format` (`rdm` or
    `cloudevents`, not null, default `rdm`).
  - Existing rows take the defaults (1, `rdm`), whatever their mode was (C-D123).
  - Drops `mode`, `debounce_seconds` and their check, and `consumer_webhook_requests.kind`
    (U5a's `events`/`notice`) with its check.
- **Dispatcher.**
  - `_per_change` (the only branch left, renamed `_next_batch`) reads
    `page_size = max_events_per_batch` events instead of `delivery.MAX_EVENTS`, which becomes the
    cap of 1,000 (`MAX_EVENTS_PER_BATCH`).
  - `delivery.fitting` measures the body in the subscription's format: the RDM envelope with its
    `events`, the CloudEvents array, or (at 1) the single structured event, which always fits alone.
  - `_coalesced`, `coalesce_due`, `COALESCE_MAX_SECONDS` and `DEFAULT_DEBOUNCE_SECONDS` are deleted.
    A batch is now always one request, so `_Batch`'s list of `(delivery_id, body)` pairs, which
    exists only for a coalesced round, becomes one body, and `delivery_log.open_batch` takes one.
  - `delivery.headers` takes the content type (today it is fixed to `application/json`).
  - The delivery log (`engine/events/delivery_log.py`, U5a) loses its notice row in `rows_of`,
    which is built from a notice body's `event` and `toPosition`. `rows_of` takes the RDM events
    the batch was built from, not the encoded body, so the log rows are the same in both formats.
    `open_batch` stops writing `kind`, and `DeliveryDetail.kind` leaves the answer.
  - **Manual resend** (U5a revision, `POST …/deliveries/{deliveryId}/resend`) lives in
    `engine/events/resend.py`. Its `_body` rebuilds a request from the stored body and today
    branches on `request.kind`; that branch goes with the column. It tells the stored format from
    the body itself, which is unambiguous: a JSON array is a CloudEvents batch, an object with
    `specversion` a structured CloudEvent, an object with `events` an RDM envelope. It finds the
    event by `eventId` (`id` in a CloudEvent) and sends it alone in that request's content type (a
    batched request's event as an array of one) with a new delivery ID. A resend keeps the format
    of the request it repeats, even when the subscription's format was edited since, because it
    repeats what was sent. `409 DELIVERY_NOT_SENT` stays: with one request per batch a `queued` row
    lives only between the batch's log and its first attempt, or after a stop in between, which no
    journey reaches reliably, so a unit test of `_body` holds it (below).
  - Encoding goes in one function per format in `delivery.py`. The CloudEvents encoder builds
    `source`, `type` and `subject` from the subscription and the event alone, so a retry composes
    the same attributes (C-D111).
- **Frontend.**
  - The dialog's Delivery section has three groups. **Requests**: "One event per request" /
    "Batched, up to [N] events", with the cost line when one is chosen. **Content**: "With the
    object" / "Notification only". **Format**: "RDM JSON" / "CloudEvents 1.0".
  - The mode and wait fields go. The detail shows the three choices.
  - `WebhookDeliveries` loses its notice branches (the "A notice" request kind, "A notice: no event
    ID", the confirmation's "notice" wording) and the row text "per notice".
  - Settings › Deployment's "Delivery batch" line reads the renamed capability: "up to 1,000
    events, 1 MiB".
  - Types and capabilities follow the contract.
- **Not changed.** The pull feed stays RDM JSON (C-D127). Ordering, leases, retries, suspensions,
  `reset` and signing are unchanged.

**Decisions** (approved by the user, 2026-10-07):

| # | Question | Recommendation |
| --- | --- | --- |
| C-D120 | How is batching set? | **One field, `maxEventsPerBatch`, 1 to 1,000, default 1**; 1 means one event per request. A separate switch plus a size would allow "single with size 50", a combination that means nothing. 1,000 matches the pull feed's identity page. With `full`, the 1 MiB cap usually ends a batch first |
| C-D121 | Is the 1 MiB cap per subscription? | **No, it stays fixed** and reported in capabilities. It protects the receiver's request-size limit (nginx's default is exactly 1 MiB). Event Grid's own byte setting is only a preference |
| C-D122 | The default | **One event per request, as the user asked**, with `full` and `rdm`. Existing subscriptions take the same defaults (C-D123) |
| C-D123 | What happens to existing subscriptions? | **Nothing special (the user): no subscription is in production.** The migration gives every existing row the defaults; no conversion, suspension or CHANGELOG note for it |
| C-D124 | Rename `payload`'s values? | **No: `identity` and `full` stay.** The pull feed shares the parameter, and no single standard pair of names exists (Stripe's thin/snapshot, Graph's basic/rich). The UI says "Notification only" and "With the object"; the docs map them to Fowler, Stripe and Graph |
| C-D125 | Which CloudEvents content modes? | **Structured for one event per request, batched otherwise; not binary.** Binary mode puts the attributes in headers, which the HMAC signature does not cover, and batched mode is defined only for structured formats |
| C-D126 | How are the CloudEvents attributes filled? | As shown above. **`id`** is the `eventId`, a UUID, so `source` + `id` is unique. **`source`** is the relative path of the definition's events read with the workspace: a URI-reference, as the spec allows, since the engine has no public base URL setting. **`type`** is `rdm.{event}.{change}`, which is not the reverse-DNS prefix the spec recommends (a SHOULD): the engine owns no domain and deployments differ. **`subject`** is `{objectType}/{id}` and **`time`** is `occurredAt`. **`rdmsubscription`** is the one extension, because the batched array has no envelope. **`dataschema`** is left out. **`data`** is the RDM event unchanged |
| C-D127 | CloudEvents on the pull feed too? | **No, not in this package.** The pull feed is read by the engine's own clients in RDM JSON. A `format` parameter can be added later without breaking anything |
| C-D128 | Adopt the CloudEvents *webhook* spec (an `OPTIONS` handshake, bearer tokens, `429 Retry-After`, `410 Gone`)? | **No.** Receivers are registered by an operator and every request is HMAC-signed (C-D12). The handshake and bearer tokens would be a second trust scheme. C17 adopts the event format and its HTTP binding only |

**Journey.** J30.6 (subscribe) gains the three choices and loses `mode` and `debounceSeconds`.
J30.8 (delivery) gains one-event-per-request, the batch size and CloudEvents, and loses the
coalesced variant. J30.10 (U5a's log) loses notice rows. USER_JOURNEYS and API_JOURNEYS change
accordingly. C13's acceptance scenario 8 ("coalesced mode delivers once after the debounce
window") is retired with the mode.

**Test cases** (journey tests on generated A and B with `test_j30_delivery`'s receiver, written
first and confirmed failing):

1. **One per request by default.** Given a subscription created without `maxEventsPerBatch`, when
   three records change, then the receiver gets three requests in position order, each an RDM JSON
   envelope with one event. The answer and capabilities show the default and the cap of 1,000.
2. **Batched.** Given `maxEventsPerBatch: 2` and five changes, then requests of 2, 2 and 1 events
   arrive in order. Given 1,000 and `full`, a large change set splits at 1 MiB before 1,000 events.
3. **Notification only in both shapes.** `identity` with one per request and with a batch carries
   no `object` or `stateAt`. `full` carries the object as get-by-ID answers it.
4. **CloudEvents.** With `format: cloudevents` and one per request, the request is
   `application/cloudevents+json` with `specversion`, `id` = the event ID, `source`, `type`,
   `subject`, `time`, `rdmsubscription`, and `data` equal to the RDM JSON event for the same change.
   Batched, it is `application/cloudevents-batch+json`, an array in position order. Both bodies
   verify against `RDM-Signature`.
5. **Refusals and edits.** `maxEventsPerBatch` 0 or 1,001, an unknown `format`, or `mode` /
   `debounceSeconds` sent is `422 REQUEST_VALIDATION_ERROR`. A `PATCH` of `format` while a batch is
   retried drops it, and the next request has a new delivery ID in the new format.
6. **Resend in CloudEvents.** A manual resend of an event delivered as CloudEvents, from one
   request per event and from a batch, arrives as that one event in the original content mode,
   with a new delivery ID, the same `id` (the event ID) and `RDM-Redelivery: manual`.
7. **Migration** (AGENTS.md): upgrade from `20261007_02` with an existing subscription, which reads
   back with the defaults; then two starts, and an interrupted run recovering.

The coalesced cases are removed: `test_j30_delivery`'s coalesced test, U5a's case 5
(`test_a_coalesced_subscriptions_deliveries_are_its_notices`), the coalesced round in
`volume_baseline` and `test_consumer_event_volume`, `coalesce_due`'s unit tests in
`tests/unit/engine/events/test_delivery.py`, the frontend's coalesced fields, notice rows in
`WebhooksPage.test`, and `e2e/u5-webhooks.mjs`'s coalesced webhook, notice row and the dialog shot
with the wait showing. The resend revision's case 3
(`test_a_notice_is_resent_and_what_cannot_be_resent_is_refused`) is rewritten on a per-change
subscription: an event ID not in a request is `404 EVENT_NOT_IN_DELIVERY` and a missing `eventId`
is `422`. Unit tests: `delivery.fitting` and the two encoders (attribute filling, both content
types, the byte cap), and `resend._body` (its three stored shapes, and `409 DELIVERY_NOT_SENT` for a
request with no stored body).

**Checks.** The cases above and `--journey J30`, `test_startup` for the migration,
`test_consumer_event_volume`, `test_openapi_contract` (the subscription schemas and capabilities
change; re-baselined with the difference stated), `ruff`. Frontend: the Webhooks unit tests,
`format`, `lint`, `build`; `test:browser:webhooks` updated to the three choices, with screenshots
of the dialog and the detail at 1440px and 390px, light and dark, for the user's approval as for U5.
UI_ACCEPTANCE's U5-1 row names the three choices. Not run: the full suites (R).

**Docs at delivery.**

- **CONSUMER_API:** Delivery and its bodies, the CloudEvents mapping, C-D105 marked retired.
- **API.md:** subscriptions, capabilities and the webhook delivery section.
- **Others:** USER_JOURNEYS, API_JOURNEYS, CURRENT_FUNCTIONALITY, PRODUCT, OPERATIONS (the
  throughput note) and CHANGELOG (Changed).

**Composable domains (ADR-032):** the change is to delivery only. Event definitions, the event
store, identity, audit and the bulk APIs are untouched, so no door is affected.

#### C17 record (2026-10-07)

Implemented as planned, with the amendments from the check against the code; screenshots approved
by the user on 2026-10-07 (the dialog's Delivery section at 1440px batched as CloudEvents and at 390px dark,
the detail with Requests, Content and Format at both widths, a CloudEvents webhook's deliveries and
an opened event whose request body is the batched array).

- **Backend.** `models/commands.py`: `maxEventsPerBatch` (1–1,000, default 1) and `format` on create
  and `PATCH`, `mode` and `debounceSeconds` gone (an unknown field, so `422`), `DeliveryResend.eventId`
  required. `delivery.py`: `RequestFormat` writes a request's body and content type in either
  format and fits a batch to 1 MiB measured in it; `cloudevent` and `events_source` fill the
  attributes from the subscription and the event alone; `headers` takes the content type;
  `coalesce_due` and `COALESCE_MAX_SECONDS` gone. `dispatcher.py`: `_next_batch` (was `_per_change`)
  reads `max_events_per_batch` events; `_coalesced` gone; `_Batch` is one request (its events, body
  and content type). `delivery_log.py`: `rows_of` takes the events the batch was built from, so the
  rows are the same in both formats; `log_request` logs one request (the dispatcher's batch or a
  resend). `resend.py`: `resend_body` tells the stored format from the body (an array, an object with
  `specversion`, an object with `events`) and sends the event alone in its content type. Revision
  `20261007_03` adds the two columns with the defaults, drops `mode`, `debounce_seconds` and
  `consumer_webhook_requests.kind`, and deletes logged notice requests.
- **Beyond the plan, stated here.** With notices gone, an event row always has an event ID, change,
  type and object ID: the migration makes those four columns `NOT NULL`, and `DeliveryRow` and
  `DeliveryEvent` answer them as strings, never `null` (a narrowing of the U5a contract, which
  allowed `null` only for notices). In `volume_baseline`, the coalesced round is replaced by a batch
  of 100 `full` events as CloudEvents, so `test_consumer_event_volume` still holds eleven
  scenarios; it was not measured at full volume.
- **Frontend.** `WebhookDialog`'s Delivery section: **Requests** ("One event per request" / "Batched"
  with "Up to (events)", 2 to the capability's 1,000, and the cost line), **Content** ("With the
  object" / "Notification only") and **Format** ("RDM JSON" / "CloudEvents 1.0", the help naming
  the content type). The detail shows Requests, Content and Format (`webhookText` holds the labels
  for both). `WebhookDeliveries` loses its notice branches; Settings › Deployment reads "Up to
  1,000 events, 1 MiB". Types, the capabilities fixture and `api.resendDelivery` (an event ID
  always) follow the contract. Built on the record-link revision another session finished in the
  same files the same day.
- **Tests the change made wrong**, changed: the J30 cases that assert batches of 100
  (`test_j30_delivery`'s first, many-events and two-dispatcher cases, `test_j30_acceptance`'s
  publish case, `test_j30_delivery_log`'s list and resend cases) subscribe with
  `maxEventsPerBatch: 100` or 10, which keeps what each is about; J30.6's capability and create
  assertions; `test_startup`'s head; the OpenAPI lock, re-baselined (renaming `maxEventsPerBatch`
  back to `maxEvents` with the previous description gives the previous hash exactly, checked);
  `WebhooksPage.test`'s fixtures, create and edit cases.
- **Test cases.** All seven are written: 1–5 in `test_j30_delivery` and `test_j30_subscriptions`,
  6 in `test_j30_delivery_log` (both content modes), 7 in `test_startup` (upgrade from
  `20261007_02` with a coalesced subscription, a notice and an events request; the interrupted run
  refused naming `format`; two starts; a downgrade); unit tests for both encoders, the fitting in
  both formats and `resend_body`'s three shapes and `409`. **They were written beside the code, not
  before it, so they were not confirmed failing first** as the plan asked. The coalesced and notice
  cases are removed as listed.
- **Checks.** Backend: `--journey J30` (86 passed after the acceptance case's batch size, 1 min 8 s),
  `test_startup`, `test_openapi_contract`, `test_foreign_keys`, `test_boundaries` and
  `tests/unit/test_config.py` (94 passed, 28 s), `tests/unit/engine/events` (all passed),
  `test_consumer_event_volume` (2 passed, 19 s: the statements equal at both sizes, the CloudEvents
  batch included), `ruff check`. Frontend: `vitest run` on settings and ui (79 passed), `tsc`,
  `lint` (0 errors, the 7 recorded warnings), `build`. Browser: `test:browser:webhooks` (19 checks,
  axe 0 violations on the list, detail, deliveries and dialog, light and dark), the record-link
  step included. Not run: the full suites (R).

## Track V — API reference

#### V1: API reference page

**Design:** ROADMAP 0.9 item 10. **Needs:** 0.8.0.

**Scope:** Scalar at `/docs`, replacing Swagger UI and ReDoc; the standalone script pinned and bundled
with the engine (licence recorded in OPEN_SOURCE), a setting to load it from a CDN; the management
OpenAPI as the first source; the route outside the OpenAPI document.

**Tests:** the page and its bundled script served with no network; the CDN setting; the OpenAPI lock
unchanged; old `/redoc` answers `404`.

**Groups:** `contract`; runner `test:browser:v1` (new).

**Exit:** `/docs` documented in the README and API.md.

**Delivered 2026-09-30.** No decision was needed. What was built:

- **The page** in `management/reference/` (the management tier: the page documents that API, and V2
  can read installed consumer definitions through the engine from there). `GET /docs` renders Scalar
  over one source, the management OpenAPI (`/openapi.json`, following a proxy's `root_path`); the
  source list is built per request, so V2 adds consumer contract versions beside it. Both routes are
  `include_in_schema=False`; FastAPI's Swagger UI, its OAuth redirect and ReDoc are switched off.
- **The script**: `@scalar/api-reference` 1.72.2's `dist/browser/standalone.js`, unchanged, with
  Scalar's MIT `LICENSE`, served at `/docs/scalar/standalone.js` and shipped as package data.
  [OPEN_SOURCE](OPEN_SOURCE.md#third-party-code-shipped-with-the-engine) records it and how to upgrade.
- **The setting** `RDM_API_REFERENCE_SCRIPT`: `bundled` (default) or `cdn`, which loads the same
  version from jsDelivr under the bundled file's SHA-384 (`integrity`), so a CDN cannot serve
  different code. Any other value stops startup naming the setting, as `WEB_CONCURRENCY` does.

Differences from the design, found in the browser: the scope said "works without internet access",
but Scalar by default loads web fonts from `fonts.scalar.com` and, on `localhost` and `127.0.0.1`,
offers its hosted agent, an MCP generator, a developer toolbar and a hosted-client link. The page
turns all of them off (`withDefaultFonts`, `telemetry`, `agent`, `mcp`, `showDeveloperTools`,
`hideClientButton`). The first attempt still loaded the fonts: the script mounts a second,
unconfigured instance on any element with the id `api-reference` by itself, so the page mounts on
`rdm-api-reference`, and a test holds that. Unknown routes answer the engine's existing
`404 http_error`, not a new code.

**Known limitation (not gated):** axe reports violations in Scalar's own markup: `color-contrast` and
`landmark-unique` at both widths, and `scrollable-region-focusable` at 390px. The engine does not
author that markup, so the runner reports them as evidence rather than failing; the page is outside
the product UI's `test:a11y` gate.

**Checks:** `test_api_reference` (new, `contract`; 5 passed): the page with the bundled script, the
management source and the offline options, and no other host named on it; the bundled script served
byte for byte, its SHA-384 equal to the pinned integrity, its licence present; the CDN setting
(case and spaces ignored) naming the pinned version with its integrity; an unknown setting refusing
to start; a `root_path` followed by the script and the source; `/redoc` and `/docs/oauth2-redirect`
`404`, and no `/docs` path in the OpenAPI document. Group `contract`: 52 passed, the OpenAPI lock
digest unchanged (no re-baseline). `test_startup` (2 passed), since settings parsing changed.
`ruff check app/ tests/` clean. `test:browser:v1` (new): a real backend on a fresh database with no
Vite, Chromium aborting every request that leaves the engine's origin (none did, at either width); the
page title, the API's heading and an operation by its path; the bundled script and `/openapi.json`
loaded from the engine; the agent, MCP, toolbar and hosted-client controls absent; the "try it"
console's `GET /api/v1/capabilities` answered 200 by the engine; 1440px and 390px without
horizontal overflow; `/redoc` `404`. Appearance inspected in the runner's screenshots at both widths
(system fonts, sidebar and operations at 1440px, the collapsed menu at 390px). `test:gate-helpers`
(5 passed: the new runner is listed in the execution guide).

Not run: frontend format, lint and build, since nothing under `frontend/src` changed (the runner and
the `package.json` script only); the CDN setting in a browser, since the runner has no network (the
integrity is checked against the bundled file instead, and the file was compared with jsDelivr's copy
when it was pinned); `test:a11y` and `test:visual`, which cover the product UI. The full suites wait
for R.

#### V2: Consumer sources

**Needs:** V1, C6b. **Scope:** the page lists every installed consumer definition and contract version
from the API index as separate sources. **Tests:** sources follow a model release that adds and
removes a definition. **Groups:** `consumer`, `contract`; `test:browser:v1`.

_Amendment, approved 2026-10-05, also to C6:_ each source is labelled
`{name} · v{contractVersion}`. Its document writes the namespace and version into every path, with
no placeholder parameters, and carries the contract version as `info.version`. A release raising
the version shows the new one, and the old document answers `404 CONTRACT_VERSION_NOT_FOUND`
([SETTINGS_AND_UI_PLAN](SETTINGS_AND_UI_PLAN.md#versions-in-the-documentation)).

##### V2 delivery record

**Delivered 2026-10-05**, as specified; no decision was needed. Journey variant J20.5 was added to
the catalogue and its test written first, and it failed on both configurations (the page had the
management source only). What was built:

- **Sources** (`management/reference/__init__.py`, `consumer_sources`): after the management API,
  one source per consumer API of the active release, in `consumerApi` order as the API index lists
  them, titled `{name} · v{contractVersion}`, slug `consumer-{consumerApi}-v{contractVersion}` (the
  prefix keeps a definition named `management` from taking the management source's slug), URL after
  the deployment's root path. Built per request, so a release shows on the next page load.
- **One URL** for a definition's document: `consumer_openapi_path` in
  `engine/model/consumer_openapi.py`, used by the page, the API index and the document's own paths,
  so the three cannot name different URLs.
- **Without an active model** (none installed, the registry unhealthy, an unsupported schema) the
  page still shows the management API, whose routes then report the cause.

**Found on the way (in the browser):** when a reader picks a source, Scalar writes
`?api=<slug>` into the address and reads it back on load, and the app-wide unknown-parameter check
refused it (`UNKNOWN_PARAMETER`), so a reloaded or shared link to a consumer API's source answered an
error instead of the page. `/docs` now declares `api` (the page ignores it; Scalar reads it). J20.5
opens the page with it.

**Checks:** J20.5 failed first, then J20 and `test_api_reference`: 17 passed (V1's tests unchanged:
their database has no installed model, so they also cover the fallback). Groups `consumer` and
`contract` in parallel: 241 passed in 34 s (the serial part selects none); the management OpenAPI
lock unchanged. `test:browser:v1`, extended: the starter started with one consumer API; at 1440px and
390px the page lists `Codelists · v1` after the management API, `?api=consumer-codes-v1` opens it with
its document read from the engine (its title and a list's path shown), nothing leaves the engine's
origin, and the V1 checks still pass. Screenshots inspected at both widths. `ruff check app/ tests/`
clean. Not run: `volume` and `startup` (no read or migration changed), frontend format, lint and
build (only the runner changed), the full suites (R).

#### V3–V9: The management API documented (plan, 2026-10-07)

**Status:** planned at the user's request (2026-10-07). V-D2–V-D10 decided by the user 2026-10-07;
V-D1 (where the text lives) is open. Independent of every release (V-D9).

**Why.** `/docs` shows every management operation, but the document behind it says very little.
Measured on `create_app()` on 2026-10-07: 74 operations by default (about 91 with model
administration and webhooks enabled). 74 have a summary and 15 a description. No operation documents
an error response besides the shared default envelope. 151 of 373 parameters and 75 of 176 schemas are
described. `info.description` is one line, and the eleven tags have no text. The document has three
examples. The behaviour is recorded in API.md, INTEGRATION_API, CONSUMER_API and the code. API.md is
written for builders and organised by delivery, so an integrator reading `/docs` cannot learn from it
what an operation is for, how it behaves, what it refuses, or what a real exchange looks like.

**Outcome.** For every management operation, `/docs` states:

- **what it is for**, with the use cases;
- **how it behaves**: contexts (workspace, change set, publication, `asOf`), versions and optimistic
  concurrency, paging, ordering, defaults and side effects (audit, feed, events);
- **its limitations**: limits, what it does not do, and the operation to use instead;
- **its errors**: each status with the codes it can carry, what each code means and what the client
  should do;
- **an example request and response**, recorded from a run against the extended starter's seeded
  database (V-D3), not written by hand: one per operation to start (V-D4).

Each tag gets an area overview: the concepts, how its operations fit together, and the common
sequences, for example "create a change set, edit, validate, publish". The document's own
description covers the conventions every operation shares: identifiers, contexts, versions, paging,
the error envelope, idempotency, and the optional surfaces with the settings that enable them.

**Sources, in order of authority:** the code (what the API does), then API.md, INTEGRATION_API and
CONSUMER_API (what was decided), then the journey catalogue (what the use cases are). Where the code
and the documents disagree, see V-D7.

##### Decisions

| # | Question | Decision |
| --- | --- | --- |
| V-D1 | Where does the text live? | **Open; the user asked for a minimal footprint in the code (2026-10-07).** Recommendation: **the code holds no documentation text and no examples.** One function merges a content directory into the generated OpenAPI document when the app builds it, the way FastAPI's documented `app.openapi()` override does. The directory is `backend/app/management/reference/content/`, shipped as package data like the bundled Scalar script. It holds an `index.md` for the document's conventions and, per tag, one Markdown file with the area overview and a section for each operation, headed by its method and path (`POST /api/v1/objects`) and holding the purpose, behaviour, limitations, errors and parameter notes. It also holds `errors.md`, the code catalogue (V-D5), and `examples/`, one JSON file per operation with its named example requests and responses, written by the recording (V-D3). Keys are method and path, the public contract, not FastAPI's generated `operationId`, which follows Python function names. The in-code descriptions that already exist (15 operations, 151 parameters, 75 schemas) stay. New field text goes in the code only where the field is otherwise undescribed and a sentence is enough. A section naming a route that no longer exists fails the V-D6 check. API.md remains the builders' contract record (DOCUMENTATION_PLAN "Not included"). API.md says what was decided and why, and `/docs` says how to use it |
| V-D2 | Which model and data do the examples use? | **Decided by the user 2026-10-07: the bundled starter, extended until it holds every capability the documentation must show, both for the examples and for demonstrating the engine.** The extension is a new content release of the starter, shipped to every new deployment, so a reader can repeat every example on a fresh install. The starter has no transport content (domains, codelists, master values such as delivery methods, systems and translations). Today it holds only part of the structures the journey tests name (checked in `configurations.py`, `example()`): a root type with a unique code, and languages, translation groups and translations with a scoped uniqueness rule. It lacks a self-hierarchy, a many-to-many relation with its own attributes, a one-to-one relation, a type ladder to restructure across, the integer range, required, read-only-with-default and at-least-one rules, and a consumer API with match rules and every parameter kind. V3 lists every capability the documented operations need, maps each to the starter type that shows it or to the smallest addition in the same domain, and adds them. The journey tests on the `example` configuration then cover more structures, because the starter holds more. `rdm-operators-timetables` is not used, because timetables, resources and roles read as a transport domain |
| V-D3 | Where do the examples come from? | **Decided by the user 2026-10-07: recorded from a run, and kept current by a rule, not by a comparison check.** A reference scenario calls the public API on the extended starter's seed, built once and reused. Each step records a request and its response into the operation's example file, normalised: IDs become stable readable placeholders (consistent across steps, so a created ID reappears in the next request) and times are fixed. Each step asserts only the status and code it records. The rule (V-D8): a change to a route's behaviour or shape regenerates that route's examples in the same change, and the git diff of the example files shows the change for review. There is no committed-versus-rerun comparison |
| V-D4 | How many cases? | **Decided by the user 2026-10-07: one example per operation to start**, the operation's main successful use. The errors are described in text (V-D5), not shown as examples. After V3, the user looks at how the examples read, how much space they take and how manageable they are, and decides whether more are added (more use cases, error examples) |
| V-D5 | How are errors documented? | **Decided by the user 2026-10-07: a few sentences for every error code**, in the code catalogue `errors.md`, written once per code: what the code means, why it happens with a hint at the usual root cause, and what the client does about it. Today a code carries a short message at the place it is raised; the catalogue explains it. Each operation lists its statuses as OpenAPI responses with the codes each can carry, linked to the catalogue, from reading the operation's code path. One check: every code the backend raises (the set `test_api_journeys` already collects) has a catalogue entry and is listed on at least one operation |
| V-D6 | How does completeness stay visible? | **Approved by the user 2026-10-07.** A contract test from V3 on lists every operation without a content section or example, every parameter and schema field without a description, every content section or example naming a route that does not exist, and every code without a catalogue entry. It compares them with a committed gap list that may only shrink. Each package empties the list for its area, and V9 deletes the list. The text is written for integrators: no package or decision IDs and no history (DOCUMENTATION_PLAN principle 1). Each statement can be checked against the code |
| V-D7 | What if the code and API.md disagree? | **Decided by the user 2026-10-07: logged, highlighted and decided separately.** The package documents what the code does, records the discrepancy in TODO under "API documentation discrepancies" (the route, what API.md says, what the code does, where) and lists it at the top of its record and its report, so it is not missed. The decision (fix the code or correct API.md) is taken separately. API.md is read on every prompt, so few discrepancies are expected |
| V-D8 | How does the documentation stay current? | **Approved by the user 2026-10-07, as part of the coding-agent guide.** V3 adds the rule to AGENTS.md (working method, the documentation step) and to "How a package is delivered", step 3: a change that adds or changes a management route updates its content section, its error listing and catalogue entries, and regenerates its examples, in the same change |
| V-D9 | Where in the queue? | **Decided by the user 2026-10-07: Track V's V3–V9 are independent and block no release, neither 0.9.0 nor 1.0.** They are fillers taken when chosen. R and R-a do not wait for them. DOC2's audit of the OpenAPI descriptions is done here instead, and DOC2 keeps the settings, limits and model language references; DOCUMENTATION_PLAN gets a pointer in V3 |
| V-D10 | Document size | **Approved by the user 2026-10-07.** Examples stay short: pages of two or three items, and long arrays trimmed in the recording with a note saying so. The document is 290 KB today. V3 measures it with V3's examples, projects the full size and reports. If the projection is over about 2 MB, examples are served as separate files that the document references, not inline. Measured once and not tuned in a loop |

##### Packages

Each package documents one area completely by V-D1–V-D6 and empties its part of the gap list. Its
tests are the `reference` group (new in V3: the recording run, whose steps assert their status and
code) and `contract` (the OpenAPI lock, re-baselined for each package by diffing the document). Each
package covers about 10–25 operations.

| Package | Needs | Area (operations) |
| --- | --- | --- |
| **V3** Foundation and the service | V2 | The starter extended (V-D2: the capability inventory, the additions, a new content release, the `example` configuration's structure map updated). The mechanism: the content directory and its merge (V-D1), the scenario harness and recording (V-D3), the error catalogue and per-operation responses (V-D5), the gap list and its check (V-D6), and the size measurement (V-D10). The V-D8 rule in AGENTS.md and the delivery steps. Text: the document's conventions, every error code's catalogue entry, and the `system`, `health`, `capabilities`, `workspaces` and workspace runtime state operations (about 12). Ends with the user's review of how the examples look (V-D4) |
| **V4** Records | V3 | Objects: create, read, update, delete, the per-type list and the cross-type lookup, the model-aware query, attribute values, history and parent candidates (15). Contexts, `asOf`, filters and sorts, uniqueness and required rules, moving a record |
| **V5** Relations and mappings | V3 | Relations (5), the edge list and the mapping reads and replacement (5), and the relation matrix (3). Relation rules, cardinality, containment as a relation, coverage |
| **V6** Change sets and publications | V3 | Change sets (list, create, read, update, delete, model release, object and relation changes, validation, publication), restructuring preview and apply, publications (read, list, withdrawal) (17). How a change set merges onto live data, conflicts, publication snapshots |
| **V7** Bulk and following changes | V3 | `POST /batches` with every item kind, jobs (read, list, items, cancel), the feed, and the export routes once J1 is delivered (about 8). Idempotency, failure policies, item outcomes, background runs, feed positions, retention and `410` |
| **V8** The model | V3 | Model reads (applications, types, relations, placements, the model, runtime state), releases, diffs and activations, validations, and the model administration surface when enabled (about 25). The model is the bulk of the area overview: the operations are simple reads, but what they describe is the whole engine |
| **V9** Webhooks, and close-out | V3, V4–V8 | Consumer subscriptions: create, read, update, suspend, resume, delete, deliveries and resend (10). Retries, batching and signing, as DOCUMENTATION_PLAN's points require. Then the close-out: the gap list empty and deleted, the V-D5 check passing over the whole document, the API.md pointer to `/docs` added, and the DOC2 audit item marked done |

**Not included:** the consumer read API (`/consumer/...`). Its documents are generated per
definition from the model, and their descriptions are a separate question (TODO once V-D1 is
approved). Also excluded: tutorials and how-to guides (DOCUMENTATION_PLAN 0.13) and translations.

**Composable domains (ADR-032):** no door is affected. The text describes contracts and does not change
them. The examples use one configuration of generic capabilities and are presented as such.

## Track J — Import and export

#### J1: Export

**Design:** §J4. **Needs:** Q3, Q4, B2, F1.

**Scope:** `POST /api/v1/exports` as a background job: context, scope (types, subtree, `where`,
`asOf`), relations included, JSON Lines and CSV (a ZIP for several types); one database snapshot; the
manifest with counts, context, feed position, release, format and SHA-256; `GET /jobs/{id}/output`
only when `completed`.

**Tests:** each context and scope; the snapshot unaffected by writes during the export; the feed
position as a baseline (F2's re-sync from an export); a JSON Lines export re-imported by a batch as
all `unchanged`; cancelled and failed exports with no output.

**Budget:** 110,000 records to JSON Lines and CSV on the fixture.

**Groups:** `jobs`, `queries`, `feed`, `volume`.

**Exit:** export in API.md; SC-10's export sentence passes.

##### J1 plan (2026-10-07)

**Planned 2026-10-07. D49, D50, D52, D53 (revised: a worker of its own for exports), D54 and D55
accepted by the user the same day. D51 revised after the user's review: the formats are JSON Lines,
CSV and XLSX (the user's decision), with one table layout for CSV and XLSX. The layout, D56 and the test
cases approved with the user's go-ahead to implement, 2026-10-07. The UI to start an export and follow it is a package of its own,
[J1u](#j1u-export-in-the-ui-and-job-notifications-outline), before J4.** Checked
against the code at `6053996`: the job table, the worker (`engine/jobs/worker.py`, which today runs
batch chunks only), the model query's builders (`engine/reads/model_query.py`, `object_query.py`,
`snapshot_reads.py`), the feed floor (`engine/reads/feed.py`), `begin_snapshot_read` and the
`rdm_value_json` SQL function (revision `20261004_01`). Backend only; the screen is J4's.

**Behaviour.** An integrator asks for an export of a stated scope of one workspace: live data, one
change set or one publication; one or several object types, each with its own criteria, optionally
only below one record, optionally on a business date; with or without relationships; as JSON Lines,
CSV or XLSX. The export runs in the background as a job. When it completes, the job states what the file
holds (counts per type, context, the feed position it was read at, release, format, size, SHA-256)
and the file is downloaded from the job. Everything in the file was read at one instant, so a live
export is a baseline: the integrator follows the feed from the export's position and misses nothing.
A JSON Lines export sent back as a batch to the same workspace changes nothing (every item
`unchanged`); CSV and XLSX share one table layout that J2's import reads back the same way. Every
record carries its version, so an edited file re-imported updates only the rows nobody changed
since the export. A cancelled or failed export has no file.

**Contract.**

- **`POST /api/v1/exports`** (registered with `INTEGRATION_JOBS_ENABLED`, D10) answers `202` with
  the queued job (`kind: export`). Body:

  ```json
  {
    "workspaceKey": "main",
    "context": { "changeSetId": null, "publicationId": null },
    "scope": {
      "types": [
        { "objectTypeKey": "codelist", "where": [ { "field": "codelist-code", "op": "eq", "value": "MOT" } ] },
        { "objectTypeKey": "code" }
      ],
      "parentObjectId": null,
      "asOf": null
    },
    "include": { "relations": "withinScope" },
    "format": "jsonl"
  }
  ```

  - `context` as in Q3: empty for live, or exactly one of `changeSetId` and `publicationId`.
  - `scope.types` (1 or more, each type once): `where` is Q3's criteria for that type, `related`
    hops and `ancestor:<type>` included. `parentObjectId` keeps only records below that record, at
    any depth. `asOf` (D50) dates the types that declare an effective period.
  - `include.relations` (D50): `none`, `withinScope` (default: both ends exported) or `all` (every
    non-containment relationship of an exported record).
  - `format`: `jsonl`, `csv` or `xlsx`.
  - No `Idempotency-Key`: an export writes no data, and a repeated request only makes a second job.
- **Refusals at the request**, checked before the job is stored, with JSON pointers into the body:
  `422 INVALID_QUERY` (an unknown type, field, operator or binding, `details.path`
  `/scope/types/0/where/0/field`; Q3's code, since these are Q3's criteria), `422 AS_OF_NOT_SUPPORTED`
  (no scoped type declares a period), `422 INVALID_AS_OF` (_as delivered, `INVALID_QUERY` at
  `/scope/asOf`, Q3's rule_), `404 PARENT_NOT_FOUND`,
  `404 WORKSPACE_NOT_FOUND`, `404 CHANGE_SET_NOT_FOUND`, `404 PUBLICATION_NOT_FOUND`,
  `422 REQUEST_VALIDATION_ERROR` (shape, both context IDs, a type listed twice).
- **The job.** `GET /jobs/{id}` as today. An export job adds `output` once completed (D52):
  `{ "format", "contentType", "counts": { "records": { "<type>": n }, "relations": { "<relation type>": n } }, "context": {
  "workspaceKey", "changeSetId", "changeSetVersion", "publicationId" }, "feedPosition", "asOf",
  "asOfApplied", "modelReleaseId", "bytes", "sha256" }`. `progress.total` is the number of records
  and relationships in scope, counted in the snapshot; `processed` rises as they are written.
  `result` stays `null` for an export (its values describe item outcomes). `parameters` holds the
  request's `scope`, `include` and `format`.
- **`GET /api/v1/jobs/{id}/output`** serves the file: `application/x-ndjson`, `text/csv` or
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, with `Content-Disposition`
  (`export-{jobId}.jsonl|csv|xlsx`), `ETag` and
  `Repr-Digest: sha-256=:…:` (RFC 9530) from the stored checksum. Refusals: `404 JOB_NOT_FOUND`,
  `404 JOB_HAS_NO_OUTPUT` (a batch), `409 JOB_NOT_COMPLETED` (queued, running, failed or cancelled;
  `details.state`), `410 JOB_EXPIRED`, `410 JOB_OUTPUT_MISSING` (the file is gone from
  `JOB_FILE_DIR`: run the export again; the operator message names the setting).
- **JSON Lines** (D49): one batch item per line. Records first, as `upsert` items keyed by
  `{ "id": … }` with `objectTypeKey`, `applicationKey`, `name`, `parent: { "id": … }`, `expectedVersion`
  (the record's version in the snapshot, D49), `attributes`
  (values in their declared types, absent values left out) and, for each required binding into the
  record's type, `initialRelations`. Then relationships as `ensureRelation` items (`relationTypeKey`,
  `from`, `to` by ID, `attributes`). Order: records by containment depth, then the model's type
  order, then ID; relationships by type, then ID. The same data gives the same bytes and checksum.
- **The table layout** (D51), shared by CSV and XLSX. One table of records and one of
  relationships. Columns are keys, never labels:
  - **Records:** `objectTypeKey`, `id`, `version`, `name`, `parentObjectId`, then one `#{attributeTypeKey}`
    column per attribute type any exported type binds, in the model's order. Attribute types are
    global (one meaning and value type in every row), so a cell is empty where the row's type does
    not bind that attribute or the record has no value. The `#` keeps an attribute whose key is
    `name` or `id` apart from the built-in columns (the model reserves no attribute keys).
  - **Relationships:** `relationTypeKey`, `id`, `fromId`, `toId`, then `#{attributeTypeKey}` per
    attribute any exported relation binding carries.
  - **Orientation columns**, ignored on import, prefixed `~`: `~parentPath` on records;
    `~fromName`, `~fromObjectTypeKey`, `~toName`, `~toObjectTypeKey` on relationships.
  - Rows in the JSON Lines order.
- **CSV:** both tables in one file, records first: the union of their columns, a row being a record
  when `objectTypeKey` is filled and a relationship when `relationTypeKey` is. UTF-8 with a BOM (so
  Excel reads the characters), RFC 4180, comma. A value in the API's canonical text (dates ISO 8601,
  decimals as the API writes them, booleans `true`/`false`, a JSON value as JSON text); an empty
  cell is no value. Values are not altered against spreadsheet formula injection: the file is data
  and keeps it exactly (OPERATIONS says so).
- **XLSX:** a sheet `Records` and a sheet `Relationships`, each one named Excel table (`records`,
  `relationships`) whose header row is the keys, with a row of readable labels (the model's names)
  above the table, outside it. Cells are typed: text as text (so `007` stays `007`), integers and
  decimals as numbers, booleans as booleans, dates as date cells, a JSON value as JSON text. A
  number Excel cannot hold exactly (more than 15 significant digits) is written as text in its
  canonical form, so a machine reader can trust every value. Data validation lists for
  `objectTypeKey`, `relationTypeKey`, boolean columns and attributes with allowed values, from a
  hidden sheet `Lists`. No import settings, manifest or user lists in the workbook (D52). A table
  past Excel's 1,048,576 rows continues on `Records 2` (table `records_2`) and so on.
- **The feed's `410 FEED_POSITION_EXPIRED`** gains `details.export: { "href": "/api/v1/exports" }`
  beside `publication` (D41, additive). The floor is unchanged (D54).
- **Settings:** `JOB_FILE_DIR` (D55). No new limit: an export is a read and streams to disk; its size
  is reported, not capped (P7 caps writes and uploads).

**Design.**

- **Storage.** Revision after `20261007_03` adds `jobs.output` (JSON, nullable). The file's path is
  derived from the job ID, never stored.
- **Validation at the request** (`engine/jobs/exports.py`, new): each type's criteria go through
  `model_query`'s existing checks with the pointer prefixed, so a criterion means here what it
  means in `POST …/queries/objects`. The job pins the context's release (P6).
- **Two workers** (D53). The process starts a second `JobWorker` that claims only `export` jobs; the
  existing one claims only `batch` jobs (a `kinds` filter on the claim, each with its own owner
  name and thread). The lease already lets several workers share the queue safely (B2, built for
  0.11's several nodes). The export worker runs an export as one step under the same lease, cancel
  and stop rules (`MODEL_RELEASE_CHANGED`, `JOB_FAILED` with a correlation ID, D29), so a batch never
  waits behind an export and an export never waits behind a batch. A queued or cancelled export
  wakes the export worker; `INTEGRATION_JOBS_ENABLED` off starts neither, and a graceful stop
  releases both workers' leases.
- **One snapshot** (D53). The export opens a `REPEATABLE READ, READ ONLY` transaction (_as
  delivered, not `READ ONLY`: PostgreSQL refuses temporary tables there_)
  (`begin_snapshot_read`) and in it reads the workspace's feed head (`workspaces.feed_position`,
  which commits with its entries under the workspace lock), counts the scope, and streams every
  file. Cancel requests, lease renewal and progress go through a second, short session every
  10,000 rows and between files, because the snapshot cannot see a cancel committed after it began.
  A crashed export restarts from the beginning when its lease expires; nothing resumes mid-file.
- **Set work in PostgreSQL** (AGENTS.md). Per type, one statement selects the scope's records
  through the model query's builders (the same `ObjectQuery` and `SetFilter`s, so `where`,
  `ancestor:`, `related` and `asOf` select the same records in every context) and builds each line
  in the database: `json_build_object` with attributes aggregated through `rdm_value_json`, read
  with a server-side cursor; CSV through `COPY (SELECT …) TO STDOUT (FORMAT csv)`; XLSX rows
  selected and encoded the same way and written by XlsxWriter (BSD, checked against OPEN_SOURCE
  before it is added) in its constant-memory mode. Python writes the bytes and cells, counts and
  hashes; it never holds the set. _As delivered: XLSX is written as sheet XML by the engine's own
  `engine/jobs/xlsx.py` (see the record)._ Change sets and publications read
  through `snapshot_reads` like every other context read.
- **Files.** Written to `{JOB_FILE_DIR}/{jobId}.partial`, then renamed with the extension once the
  checksum is stored in the same commit as `completed`. A cancel, a failure or a restart deletes the
  partial file; retention (D14) deletes the file with the job's outcomes; startup removes `.partial`
  files whose job is not running here.
- **Feed floor** (`feed.py`): the `410` details gain `export`; nothing else changes (D54).

**Decisions** (for approval):

| # | Question | Recommendation |
| --- | --- | --- |
| D49 | What a JSON Lines line is | **Accepted 2026-10-07 by the user.** **`upsert` by `{id}` and `ensureRelation`, not §J4's `create` and `createRelation`.** A `create` of an existing record is refused, so §J4's file could not be re-imported as the package's own test requires and §J2 promises ("an export re-imports as upserts"). Required relationships also ride on the upsert as `initialRelations` (used only on create), so a record that requires one can be created from the file. **Limit:** object IDs are unique across the instance, so the file loads into the same workspace or another instance, not into a second workspace of the same instance; copying a workspace is a different feature. Relationship IDs are not carried. **Amended 2026-10-07 by the user: each record carries its version** (`expectedVersion` on the upsert line, a `version` column in the tables), so a re-imported edited file updates the rows nobody changed since the export and refuses only a row changed in the engine meanwhile (`VERSION_CONFLICT`), instead of needing `onExisting: overwrite`; an unchanged row stays `unchanged`, decided before the version (D24). §J4's "versions are not carried" is amended; history still is not |
| D50 | The scope's shape | **Accepted 2026-10-07 by the user.** **`where` per type; `parentObjectId` and `asOf` shared; `include.relations` `none` / `withinScope` (default) / `all`.** §J4 names types, `where` and `asOf` without saying which type a criterion is for; Q3's criteria belong to one type. `asOf` follows the consumer API (C-D76–C-D80): types without a period are exported undated, the manifest names the dated ones (`asOfApplied`), and only a scope with no dated type is refused. `all` can name records outside the file; a re-import then needs them present (`REFERENCE_NOT_FOUND` otherwise) |
| D51 | Formats and the table layout | **Formats JSON Lines, CSV and XLSX: decided by the user 2026-10-07** (XLSX is a machine format as much as a human one). **Layout approved 2026-10-07 with the go-ahead to implement:** one table layout for CSV and XLSX as in the contract above: a records table and a relationships table keyed by column keys, attribute columns `#{attributeTypeKey}` (attribute types are global, so one column means one thing in every row), orientation columns `~…` ignored on import, the record's `version` (D49); CSV both tables in one file, XLSX two named tables with typed cells. The first recommendation (a file per type, a ZIP) is withdrawn: it rested on attributes differing per type, which the global attribute types rule out. §J4's "one file per type (a ZIP when several)" is amended. The source system's export (reviewed 2026-10-07) also keeps every type in one sheet, relationships in another with orientation columns |
| D52 | Where the manifest lives | **Accepted 2026-10-07 by the user.** **On the job only (`output`), with the checksum also in `Repr-Digest` and `ETag`.** A manifest line would make a JSON Lines file no longer a list of batch items, and a manifest only in a ZIP would differ by format. One home, read before downloading |
| D53 | One snapshot for a long export | **Accepted 2026-10-07 by the user, revised: exports run on a worker of their own.** **One read-only `REPEATABLE READ` transaction for the whole export, restarted whole after a crash; no chunked resume.** Resuming a file across transactions would need an exported snapshot kept open across processes, which a crash loses anyway. **Exports get their own worker thread**, claiming only exports while the existing worker claims batches, so neither kind waits behind the other; the lease already supports several workers (B2). **Cost:** one thread, and two database connections while an export runs (the snapshot and the short cancel and progress checks), well within SQLAlchemy's default pool. Exports wait for each other. A long-open snapshot holds back PostgreSQL's cleanup of rows changed meanwhile until the export ends; not noticeable at the expected duration (measured by D56), noted in OPERATIONS |
| D54 | D40 revisited: does a workspace without a publication keep every entry? | **Accepted 2026-10-07 by the user.** **Yes, keep D40.** The audit log is not pruned (F5), so letting entries expire there saves nothing and only takes away a reader's incremental catch-up; the export is offered beside the publication in the `410` (D41). The floor stays as it is |
| D55 | `JOB_FILE_DIR` | **Accepted 2026-10-07 by the user.** **Default `var/job-files` under the project root (used when the setting is not set), created at start; a start with jobs enabled and the directory not writable is refused with the path and the setting's name.** Reported by `GET /capabilities` as present, never as a path. 0.11's several nodes need shared storage behind it (D12) |
| D56 | The budget's size | **Approved 2026-10-07 with the go-ahead to implement.** **The fixture's whole live workspace, 258,000 records and their relationships, to JSON Lines, CSV and XLSX, measured once and announced.** The 110,000 in this package's outline predates 0.8 A2 (TODO). Target: under 60 s each, memory flat (no set held in Python). A `volume` test at 0.1 scale holds statements and time per run |

**Journey.** J27 (exchange a supplier file) gains its export variants; USER_JOURNEYS and API_JOURNEYS
(the two routes, the codes, `JOB_FILE_DIR`) change with it:

- **J27.1 Export a stated scope**: live, change set or publication; types with criteria, a subtree,
  a date; with or without relationships; JSON Lines, CSV or XLSX.
- **J27.2 The export as a baseline**: a live export names the feed position it was read at; the
  reader follows the feed from there and ends with live data.
- **J27.3 Round trip**: a JSON Lines export sent back as a batch changes nothing.
- **J27.4 No partial output**: a cancelled, failed or expired export serves no file.

**Test cases** (journey tests on generated A and on the example or generated B, through the API,
written first and confirmed failing):

1. **Live JSON Lines.** Given records of `R` and `C` under `P` with `Bnn` relationships, when an
   export of `R` with a criterion on `R.n` and of `C`, `withinScope`, completes, then its output has
   one `upsert` per matching record, parents before children, then one `ensureRelation` per
   relationship with both ends exported; `output.counts` match; `sha256` and `bytes` match the
   downloaded body and `Repr-Digest`; `feedPosition` equals the feed's head before the export.
2. **Other contexts and scopes.** In a change set, the export holds a record only the change set
   has and names the change set and its version, `feedPosition` `null`. A publication's export, after
   a later live edit, holds the published values and the publication's `feedPosition`. `parentObjectId`
   keeps only that subtree; `asOf` dates the dated type, exports the other undated and names it in
   `asOfApplied`.
3. **One snapshot.** Given an export that has taken its snapshot, when a record is created and
   another renamed and committed before the export finishes, then the file has neither change, and
   both appear in the feed after the manifest's `feedPosition`. (The write is committed from the
   export's first cancel check, the point where the snapshot is held, through the job's own seam; not
   a sleep.)
4. **Baseline recovery.** Given a reader whose position expired, the `410` names the publication and
   `export`; the reader runs a live export, follows the feed from its `feedPosition`, applies the
   entries, and holds exactly the live records and values.
5. **Round trip.** The JSON Lines output of case 1, sent as `POST /batches` (background,
   `independent`, `onExisting: overwrite`) to the same workspace: every item `applied` with action
   `unchanged`; the feed head does not move.
6. **CSV and XLSX.** An export of two types with relationships as CSV is one file whose header is
   the layout's keys (`objectTypeKey`, `id`, `version`, `name`, `parentObjectId`, `#…`,
   `relationTypeKey`, `fromId`, `toId`, `~…`), records then relationships, typed values in canonical
   text; as XLSX, the `records` and `relationships` tables hold the same rows, with a code `007`
   as text, a date as a date cell and an integer as a number. Both match the JSON Lines export's
   counts and versions.
7. **No partial output.** A cancelled export answers `409 JOB_NOT_COMPLETED` on its output and leaves
   no file; an export whose release changes before it runs fails `MODEL_RELEASE_CHANGED` with no
   output; an expired export answers `410 JOB_EXPIRED` and its file is gone; a batch job's output is
   `404 JOB_HAS_NO_OUTPUT`.
8. **Refusals.** An unknown type, a bad criterion (`422 INVALID_QUERY` at its pointer), `asOf` with
   no dated type, an unknown parent, both context IDs, a type listed twice; with
   `INTEGRATION_JOBS_ENABLED` off the route is absent and job reads still answer.

Plus the migration checks (AGENTS.md): upgrade from `20261007_03`, two starts, an interrupted run
recovering, and the start refused with an unwritable `JOB_FILE_DIR`. Unit tests only where the edge
cases are real: the record order (depth, type order, self-hierarchies), the CSV text and the XLSX
cell of every value type (nulls, quoting, the 15-digit rule).

**Checks.** The cases above, `--journey J27` and `--journey J26` (the `410` details), `jobs`,
`queries` and `feed` as the guide selects them, `test_startup` for the migration and the directory,
`test_openapi_contract` (re-baselined, difference stated), `ruff`. The `volume` test at 0.1 scale;
the full-size budget (D56) once, announced with its expected time and run only on the go-ahead. No
frontend change. Not run: the full suites (R).

**Docs at delivery.** API.md (exports, the output route, the job's `output`, the `410` field),
INTEGRATION_API §J2 (the layout J2 reads), §J4 and §F5 amended by D49–D54, OPERATIONS (`JOB_FILE_DIR`, disk use, the snapshot's
cost), USER_JOURNEYS, API_JOURNEYS, CURRENT_FUNCTIONALITY, PRODUCT, ACCEPTANCE_SCENARIOS (SC-10's
export sentence), USER_STORIES (US-I08), CHANGELOG, PROJECT_STATUS, TODO (the 110,000 item closed).

**Composable domains (ADR-032):** a bulk read beside the bulk APIs; identity, attribute storage,
audit, the `match` declaration and mapping coverage are untouched, so no door is affected. The
export carries no domain concept: scope, items and files are the engine's generic ones.

##### J1 record (2026-10-07)

**Delivered 2026-10-07.** Decisions D49–D56 approved by the user (D49, D50, D52, D54, D55 on
review; D53 revised with a worker of its own; D51's formats chosen by the user, its layout, D56 and
the test cases with the go-ahead to implement). The eight test cases were written first and
failed (collection: no export module), then passed.

**Built.**

- `POST /api/v1/exports` (`management/routers/jobs.py`, `engine/jobs/exports.py`, `models/exports.py`):
  checks the request against the model (each type's criteria through `plan_model_query`, refused at
  the body's pointer) and queues a job of kind `export`; nothing is stored when it is refused.
- The export worker: a second `JobWorker` (`kinds=("export",)`, thread `rdm-export-worker`, no
  sweep) beside the batch worker, which now claims `batch` jobs only. An export runs in one step from
  one `REPEATABLE READ` snapshot: the scope into temporary tables by set statements (records through
  the query builders, depth inside the file, parent paths, relationships, required relationships),
  then the file. Cancel, lease and progress go through the worker's own short session every 10,000
  rows (`should_stop`); a crash restarts the export.
- Formats: JSON Lines built by PostgreSQL (`json_build_object`, streamed); CSV by `COPY … TO STDOUT`;
  XLSX as SpreadsheetML written straight into the ZIP (`engine/jobs/xlsx.py`): inline strings,
  typed cells, two named tables, a hidden `Lists` sheet for the dropdowns.
- `GET /api/v1/jobs/{jobId}/output` with `ETag` and `Repr-Digest`; the job's `output` (D52);
  `JobFiles` in `JOB_FILE_DIR` (`engine/jobs/files.py`), reconciled at start and with each sweep.
- Revision `20261007_04` (`jobs.output`); `JOB_FILE_DIR` (D55), checked at start; the feed's `410`
  names `export` (D41, D54).

**Where it differs from the plan.**

- **Not `READ ONLY`.** PostgreSQL refuses `CREATE TEMPORARY TABLE` in a read-only transaction. The
  snapshot is plain `REPEATABLE READ`, writes only its temporary tables, and is rolled back.
- **XLSX writer.** XlsxWriter's streaming mode cannot add tables, so the first writer used openpyxl's
  write-only workbook (MIT): 72.8 s at full size, over D56's 60 s. The user chose to make it faster
  in J1: the workbook is now written as sheet XML by the engine itself, 31.5 s. openpyxl stays as a
  test dependency only, to read workbooks back. No library was added to the engine.
- **An invalid `asOf`** is `422 INVALID_QUERY` at `/scope/asOf`, as Q3 refuses it, not a new
  `INVALID_AS_OF`. A context of another workspace is `422 WORKSPACE_CONTEXT_MISMATCH`, as on every
  context read.
- **Relationships carry their version too**: `expectedVersion` on `ensureRelation`, a `version`
  column in the tables, so an edited relationship is claimed like a record.
- **`counts.records`** names every exported type, zero included.
- **CSV's cancel check** comes between its two `COPY` statements (a `COPY` cannot pause), not every
  10,000 rows.
- **Dropdowns** cover the type columns and boolean columns: the model has no list of allowed values
  to offer.
- **Test case 5** sends the file back with the default `onExisting` (the versions make `overwrite`
  unnecessary) and adds the edited file: one record updated, one refused `VERSION_CONFLICT`, the rest
  `unchanged`. Case 6 checks the shared layout in CSV and XLSX. These follow D49's and D51's revisions.

**Found on the way.**

- **A file renamed into place could be reconciled away.** The sweep removed a file whose job was
  still `running` in the moment between the rename and the commit that completes it; a running job
  now keeps its file under either name.
- **Test runs shared one job file directory.** `conftest.py` set `JOB_FILE_DIR` once and the xdist
  workers inherited it, so another worker's application, reconciling the directory against its own
  database, removed a running export's file (one `JOB_FAILED` in the first group run). Each worker,
  journey application, seed build and the volume script now has a directory of its own, removed when
  it ends. Two script runs had left an empty `var/job-files` in the project; removed.
- `test_boundaries` bans `json_each` and `json_type…` as another database's SQL; the export uses
  PostgreSQL's `jsonb_each` and `jsonb_typeof`.

**Checks.**

- J27 journey tests (9 tests on two configurations each, 18 cases) and J26's expired-position test
  updated for `details.export`; `test_export_volume` (statements at two sizes); unit
  `tests/unit/engine/jobs/test_xlsx.py` (22: every value type read back, the 15-digit rule, text
  escapes, column letters). After the last change: J27 and the volume test 19 passed in 18 s; the
  unit tests 22 passed; `test_boundaries`, `test_api_journeys`, `test_openapi_contract`, the config and
  main unit tests 62 passed.
- The guide's selection for `engine/jobs/*`, `reads/feed.py` and the lifespan, before the XLSX
  writer and the harness fixes: `jobs or feed or contract or startup` in parallel, 556 passed in
  1 min 45 s; its serial part 1 passed.
- Startup (AGENTS.md): upgrade from `20261007_03` with the column added by hand refused and rolled
  back, then two starts and a downgrade; a clean start; an unwritable `JOB_FILE_DIR` refused with the
  path and the setting: 4 passed.
- OpenAPI lock re-baselined: two paths, eight `Export*` schemas and `JobResponse.output` added,
  nothing else changed (diffed against `HEAD`).
- Budget (D56), measured with the user's go-ahead: POSTGRESQL_BUDGETS §8. JSON Lines 23.1 s, CSV
  24.4 s, XLSX 31.5 s at 257,758 records and 316,616 relationships.
- `ruff check app/ tests/` clean.
- Smoke on the development server (its `--reload` restart applied `20261007_04` to the development
  database; `/health` ok): one XLSX export of two types through `POST /exports`, run by the export
  worker's own thread, completed and downloaded with its `Repr-Digest`. The journey tests run the
  worker by hand, so this is the evidence for the thread.

**Not run or not verified.** The full suites (R). No frontend change, so no frontend checks. The
XLSX files were read back by openpyxl only, not opened in Excel or Numbers. The round trip of CSV
and XLSX through an import waits for J2. Memory during an export was not measured with an
instrument.

#### J1u: Export in the UI and job notifications (outline)

**Added 2026-10-07 by the user**, while planning J1. An outline, planned in detail with its journeys,
screens and decisions when it is next. **Needs:** J1. J4 reuses its job page and notifications.

**Behaviour.** From a collection or the workspace, a user opens an export dialog (context, types,
criteria, subtree, date, relationships, format) and starts the export. A notification says it has
started. When the job finishes, a notification says so, with a link to the job's page and, for a
completed export, a link that downloads the file. A failed or cancelled job's notification links to
the job page, which shows the error (the user, 2026-10-07; errors stay off toasts, U3). The job page
shows state, progress, the manifest (D52), the download and any error; Settings › Integration ›
Jobs and feed links each job to it.

**Notifications are pushed, never polled (the user, 2026-10-07).**

- `GET /api/v1/jobs/{jobId}/events`: a server-sent event stream for one job. It sends the job's
  current state at once, then each change (running, progress, finished), sends the final state and
  ends. A job already finished answers with its final state and ends. A public route like any
  other, so a script can follow a job as the UI does.
- Inside the engine, a job's state change sends a PostgreSQL `NOTIFY` in the transaction that
  commits it, so only committed changes are announced; each process listens on one connection and
  passes events to its open streams. It works unchanged with several nodes (0.11), which share the
  database.
- The browser opens a stream when it starts a job and remembers the jobs it started in that tab, so
  a reload reopens their streams. A closed browser receives nothing; the job page and the jobs list
  still show the result.
- One connection per running job: past about five at once from one tab, HTTP/1.1's six connections
  per site make later streams wait; HTTP/2 lifts it. Proxies must not buffer the stream (OPERATIONS).

**Also:** toasts that can carry links (`ui/Toast` takes text only today); the job page in the
accessibility and visual gates, light and dark.

**Not in J1u:** notifications to a closed browser (Web Push, which sends through the browser
vendor's service), and per-person notifications, which need the users of 0.12.

##### J1u plan (2026-10-07)

**Planned 2026-10-07 at the user's request to implement J1u. D57 and D60 accepted by the user the
same day, D59 decided by the user (8 seconds); D58, D61–D63 and the test cases approved the same
day.** Checked against the code after J1: `ui/Toast` takes a text message only;
`features/settings/JobsPage` lists jobs without a page per job; Settings routes have a detail form
for webhooks (`/settings/webhooks/{id}`) to follow; the collection page's `PageHeader` has one
action (Add); a collection carries its filters, search and parent scope in the URL; no route
streams and nothing in the engine uses `LISTEN`/`NOTIFY`. **Needs:** J1 (delivered).

**Behaviour.**

1. On a collection page, **Export** opens a dialog prefilled from the page: its object type, the
   data context (live, the change set or the publication being viewed), its filters and its parent
   scope. The user may add types of the same application, a date, the relationships and a format,
   and starts the export. Settings › Integration › Jobs has **New export** for any types of a chosen
   workspace (D57).
2. A notification says the export has started, with a link to its job page.
3. When it finishes, a notification says so: completed with **Download** and **View job**; failed or
   cancelled with **View job** only (the user, 2026-10-07: the job page shows the error). Like every
   notification it stays 8 s, longer while hovered or focused (D59).
4. The job page (`/settings/jobs/{jobId}`) shows the state, progress while running, the error,
   **Cancel** while it can be cancelled, and for a completed export the manifest (context, feed
   position, release, counts per type, size, checksum) and **Download**. It updates as the job
   changes. Each row of the jobs list opens its page.
5. Updates are pushed, never polled (the user, 2026-10-07): the browser opens a job's event stream
   when it starts the job, and the job page opens it while shown. A reload reopens the streams of
   the jobs this tab started; a closed browser receives nothing.

**Contract.**

- `GET /api/v1/jobs/{jobId}/events` (a read, always registered): `text/event-stream`. It sends the
  job at once (`event: job`, `data:` the `JobResponse` as `GET /jobs/{id}` answers it), then the job
  again after each change of its state, progress, cancel request or output, and ends after a final
  state (`completed`, `failed`, `cancelled`, `expired`). A finished job is sent once and the stream
  ends. A comment line (`: keep-alive`) every 15 s keeps proxies from closing an idle stream.
  `404 JOB_NOT_FOUND` before the stream starts. `X-Accel-Buffering: no` and `Cache-Control:
  no-cache` so a proxy passes events at once. Each event carries the whole job, so a reconnecting
  client needs no `Last-Event-ID`.
- No other route changes. Starting an export is J1's `POST /exports`; the download is J1's
  `GET /jobs/{id}/output`.

**Design.**

- **Notification at commit** (D58). Revision after `20261007_04` adds a trigger on `jobs`: after an
  insert, or an update that changes `state`, `processed`, `total`, `cancel_requested_at` or
  `output`, `pg_notify('rdm_job_events', job id)`. PostgreSQL delivers a notification only when its
  transaction commits, and a trigger catches every path that changes a job, the worker's, the
  routes' and the store's, including future ones. Lease renewals alone notify nothing.
- **One listener per process** (`engine/jobs/events.py`): a thread holding one connection that
  `LISTEN`s and hands each job ID to the streams waiting for it (an asyncio queue per stream, fed
  through the event loop). Started in the lifespan where the model is served, as the deriver is;
  it reconnects after an outage with the `OutageLog`. Several processes each listen to the same
  database, so 0.11's nodes need no change.
- **The stream** (`management/routers/jobs.py`): an async generator. It subscribes before reading
  the job, so no change falls between the read and the subscription; on each notification it reads
  the job again (one short query) and sends it unless unchanged. A client that disconnects ends it.
- **Frontend.**
  - `ui/Toast` gains actions (links or buttons); the region and timing stay one component (U-D14).
  - `features/jobs/`: `useJobStream(jobId)` over `EventSource`; `JobNotifications`, a provider in
    the app shell that remembers the jobs this tab started (`sessionStorage`), keeps one stream per
    running job and shows the notifications; `ExportDialog` (`ui/Modal`); `JobPage`.
  - The collection page's header gains **Export** beside Add (also in a read-only context: an export
    changes nothing), shown while the deployment lets jobs be created
    (`capabilities.integrationJobs.createJobs`).
  - The dialog: types (this collection's checked; the application's other types listed), the
    context as a read-only line, the collection's filters as `where` criteria with their labels, the
    parent scope as "Only below …" (checked when the page is scoped), the search left out with a
    sentence saying so (D60), a date when a chosen type declares a period, relationships (none,
    both ends exported, all; default both ends), the format (XLSX, CSV, JSON Lines; default XLSX,
    D61). A refusal shows inline at its field, from the error's JSON pointer.
  - Settings › Jobs: rows link to their page; **New export** opens the same dialog with a workspace
    chooser and no prefill.
  - Download is a plain link to `/api/v1/jobs/{id}/output` (`download` attribute).
- **Not changed:** the engine's export, its worker, the batch pages.

**Decisions** (for approval):

| # | Question | Recommendation |
| --- | --- | --- |
| D57 | Where does a user start an export? | **Accepted 2026-10-07 by the user; kept as delivered after review the same day** (a collection's Export offers its application's types; New export on Jobs and feed offers every type, so several applications export together from there). **On a collection page (prefilled from it) and from Settings › Jobs (New export, any types of a workspace).** The collection is where the user already chose a type, a context, filters and a scope; Jobs is where exports are followed. No export in the record detail or the tree, which are about one record |
| D58 | How the engine learns a job changed | **Approved 2026-10-07 by the user.** **A trigger on `jobs` with `pg_notify`, delivered at commit.** Notifying from Python would need every path that changes a job to remember it; the trigger cannot be forgotten, and an aborted transaction notifies nothing |
| D59 | How long the finished notification stays | **Decided 2026-10-07 by the user: 8 seconds, as every notification** (longer while hovered or focused). The recommendation was until dismissed. Only the finished notification of a job this tab started is shown |
| D60 | The collection's search in an export | **Accepted 2026-10-07 by the user.** **Left out, said in the dialog.** The model query has no full-text search; carrying it as a name criterion would export a different set than the page shows. Filters carry over exactly (the same field, operator and value) |
| D61 | The dialog's default format | **Approved 2026-10-07 by the user.** **XLSX**: the person in the browser most often opens the file; integrations use the API and choose |
| D62 | The job page's address | **Approved 2026-10-07 by the user.** **`/settings/jobs/{jobId}`**, a detail of Jobs as webhooks have, so the notification's link and the list's rows open one page |
| D63 | Several jobs at once in one tab | **Approved 2026-10-07 by the user.** **One stream per running job the tab started, no limit**; HTTP/1.1's six connections per site make a seventh wait (OPERATIONS says so); HTTP/2 lifts it |

**Journey.** J27.6 (new): *start an export in the browser and follow it*, the UI channel of J27.1
and J27.4, and J24's job stream: J24.7 (new) *follow a job as it changes* through the API (any job
kind). USER_JOURNEYS, API_JOURNEYS (the route, `JOB_NOT_FOUND`) and UI_ACCEPTANCE (a row for the
dialog, the job page and the notification) change.

**Test cases.**

Journey tests (API, generated A and B):

1. **The stream follows a job to its end.** Given a queued export, when a client opens its events
   and the export worker runs it, then the client receives the job queued, then running with
   progress, then completed with `output`, and the stream ends. A batch job's stream does the same
   for its chunks.
2. **A finished job is sent once.** The stream of a completed job sends it and ends at once; an
   unknown job is `404 JOB_NOT_FOUND`.
3. **A cancel reaches the stream.** A cancel request is sent as the job with `cancelRequestedAt`,
   then `cancelled`.
4. **Only committed changes are sent.** A batch whose chunk rolls back (an atomic batch with a
   rejected item) sends no state the job never committed.

Unit tests: the stream's formatting and keep-alive; `Toast` with actions and `persistent`; the
dialog's request from a collection (filters to `where`, scope, context, search left out); the
pointer of a refusal shown at its field.

Browser runner `test:browser:j1u` (real backend, two object types or models, keyboard, 390px):
from a collection with a filter, Export, the dialog prefilled, start, the started notification, the
finished notification with Download and View job, the downloaded file's name, the job page with the
manifest; a cancelled export's notification and page; New export from Jobs; the dialog's refusal at a
field. Screenshots of the dialog, the notification and the job page at 1440px and 390px, light and
dark, for the user's approval, and the three surfaces in `test:a11y` and `test:visual`.

**Checks.** The journey and unit tests above; `jobs`, `contract` (the new route; OpenAPI re-baseline)
and `startup` (the trigger's migration: upgrade, two starts, an interrupted run); frontend `vitest
related`, `format`, `lint`, `build`; `test:browser:j1u`; the a11y and visual scenarios of the changed
surfaces. Not run: the full suites (R).

**Docs at delivery.** API.md (the events route), OPERATIONS (proxies and the connection limit),
ARCHITECTURE (the listener), USER_JOURNEYS, API_JOURNEYS, UI_ACCEPTANCE, CURRENT_FUNCTIONALITY,
PRODUCT, CHANGELOG, PROJECT_STATUS, TODO.

**Composable domains (ADR-032):** notifications about jobs and a screen over existing routes;
identity, attribute storage, audit, bulk APIs, `match` and mapping coverage are untouched.

##### J1u record (2026-10-07)

**Delivered 2026-10-07; the screenshots approved by the user the same day.** D57–D63 and the test cases
approved by the user before coding (D59 their choice: 8 seconds). The four stream cases were written
first and failed (no route), then passed.

**Built.**

- **Backend.** Revision `20261007_05`: the `jobs_notify` trigger (`pg_notify` at commit on a change
  of state, progress, total, cancel request or output). `engine/jobs/events.py`: one listener thread
  per process (`rdm-job-listener`) holding a psycopg connection that `LISTEN`s and wakes the streams
  of the job named. `GET /api/v1/jobs/{jobId}/events`: an async server-sent event stream, subscribed
  before its first read, sending the job at once and after each change, ending after a final state,
  with a keep-alive comment every 15 s. `db.libpq_url`.
- **Frontend.** `features/jobs/`: `useJobStream` (EventSource, closed at a final state),
  `JobNotificationsProvider` (the jobs a tab started, remembered in `sessionStorage`, one stream
  each), `ExportDialog`, `JobPage`, `exportRequest` (filters to criteria, a pointer to its field),
  `jobText` (the job labels, moved from `JobsPage` so the list, the page and the notifications share
  them). `ui/Toast` carries links and an `info` tone; the toast region and the notifications moved
  to the app root, so they work on every page. `ui/Choice` extracted from the webhook dialog, and
  the webhook dialog's `webhook-form*` styles renamed `dialog-form*`, so both dialogs share one form
  (U-D14). A collection page shows **Export** when the app shell passes `onExport` (while jobs can be
  created); Jobs and feed has **New export** and links each job to `/settings/jobs/{jobId}`.

**Where it differs from the plan.**

- **The page's parent narrowing.** A collection narrowed to a parent shows that parent's direct
  children; the export's `scope.parentObjectId` means any depth. To export what the page shows, the
  dialog sends the narrowing as a `parentObjectId eq` criterion on the page's type, not as
  `scope.parentObjectId`. The checkbox reads "Only the {records} this page is narrowed to".
- **Capabilities and notifications are read by the app shell**, which passes an optional `onExport`
  to the collection views; a generic view reads no app service, and a view without it offers no
  export (the collection tests needed no change).
- **Each stream read opens a short session of its own** (`app.state.session_factory`), not the
  request's: a stream outlives its request and must not hold a connection while a job runs.
- **The browser runner** does not cancel an export from the browser (an export of the seed finishes
  before a cancel can reach it); it shows a cancelled job's page with a batch queued behind a large
  one, and the cancelled notification is held by `JobNotifications.test`. A refusal at a field is
  held by `ExportDialog.test`; the browser cannot make the engine refuse a prefilled dialog.
- **The comprehensive gates.** The three surfaces were checked with axe and screenshots in the
  runner, as U4 and U5 were; adding them to `test:a11y` and `test:visual` (scenarios and baselines)
  belongs to build acceptance (R), which runs those gates (TODO).

**Found on the way.**

- **The listener's outage was logged as a defect.** J12's database outage test failed: a raw
  psycopg `OperationalError` was not recognised as an unreachable database (only SQLAlchemy's
  wrapper was), so the listener logged a traceback at ERROR. `database_unreachable` now reads a
  psycopg connection's error by the same SQLSTATE rule; regression cases in
  `tests/unit/common/test_outage.py`; J12 passes.
- **The test client cannot follow a stream**: Starlette's `TestClient` buffers a streamed response
  until it ends. The stream tests serve the journey application over HTTP on a local port
  (uvicorn, lifespan off) and read it with httpx, as a browser does.
- The toast test reached the toast as its message's parent; the message now sits in a body element,
  so the test finds the toast by its class.

**Checks.**

- Backend: `test_j24_job_stream` (4 tests on two configurations, 8 cases); the trigger's startup
  test (upgrade from `20261007_04` refused with the function present, two starts, downgrade); the
  OpenAPI lock re-baselined (only `GET /jobs/{job_id}/events` added, diffed against J1's document);
  `jobs or feed or contract or startup` in parallel, 565 passed and J12's two cases failed before the
  outage fix; after it, `jobs or feed or startup` 496 passed in 1 min 42 s, the serial part 1 passed;
  `ruff` clean.
- Frontend: `vitest related` over the changed files, 287 passed (`ExportDialog.test` 4,
  `JobNotifications.test` 3, the existing Settings, routes, toast and collection tests); `format`,
  `lint` (0 errors; the 7 warnings are in files this package did not touch), `build`.
- Browser (`test:browser:j1u`): 12 checks at 1440px and 390px on Domains (filtered to one record,
  XLSX) and Systems (CSV): Export by keyboard, the started and completed notifications, the
  downloaded file's name and size, the job page's counts; New export from Jobs and feed; a cancelled
  batch's page; axe 0 violations on the dialog, the notification and the job page, light and dark.
  Screenshots inspected: the choices wrapped onto two rows and squeezed at 390px, and the dialog's
  eyebrow repeated its title; fixed (one row, stacked on a phone; no eyebrow).

**Not run.** The full suites and `test:a11y`, `test:visual` (R).

#### J2: Import profiles and file reading

**Design:** §J2, §J3, [MODEL_AUTHORING import profile](MODEL_AUTHORING.md#import-profile).
**Needs:** B3.

**Scope:** `import-profiles` CRUD with optimistic concurrency and validation against a release (a
path per binding); readers for XLSX (values, not formulas), CSV and JSON Lines; conversion through
the attribute registry; source ordering by references; match keys resolved to IDs with
`reference_ambiguous`; rows to batch items, including `relatedRecord` and `relationFlags`. A new
reader library is checked against OPEN_SOURCE before it is added.

**Tests:** every binding kind on the starter and on the generated model (a translation-like and a
system-mapping-like `relatedRecord` on the starter, the same binding on the generated model's own
types); each file format with the same content giving the same items; profile validation against
another release; cycles.

**Groups:** `jobs`, `model`, `contract`.

**Exit:** the profile JSON is final in §J3 and MODEL_AUTHORING's outline points to it (0.10 A1 builds
on it).

#### J3: Import preview and execution

**Design:** §J1. **Needs:** J2, B2.

**Scope:** `POST /api/v1/imports` (multipart); validating, preview (rolled back, `complete` up to the
preview limit, `sample` beyond), the binding report, `awaiting_confirmation`,
`POST /jobs/{id}/confirm`, direct `execute`, row outcomes with sheet and row.

**Tests:** the preview changing nothing and predicting execution's codes when nothing changed
between; SC-10's file (new value, existing value, invalid number, duplicate key) under both
policies; an interrupted import resumed and retried with its idempotency key creating no duplicate;
`sample` beyond the limit; an expired preview.

**Budget:** a 10,000-row preview and a 100,000-row execution on the fixture.

**Groups:** `jobs`, `records`, `change_sets`, `volume`.

**Exit:** SC-10's import half passes at API level.

#### J4: Import screen and SC-10

**Design:** §J5. **Needs:** J1u (its job page and notifications), J3, F2.

**Scope:** the minimal import screen from the workspace (choose a file and a profile, preview,
counts, binding report, rejected rows paged, confirm or cancel, result); SC-10 end to end; the screen
in the accessibility and visual gates, light and dark.

**Groups:** `jobs`; frontend `vitest related`; `test:browser:j4` (new); `test:a11y`, `test:visual`.

**Exit:** SC-10 passes, with its simplicity check (failed rows acted on without redoing successful
work).

## Track K — Bulk selection and editing in collections

**Added 2026-10-06 by the user**, after Track J, which brings the job screens it reuses. The
packages below are an outline; each is planned in detail, with its journeys and decisions, when the
track starts.

**Outcome.** In a collection a user selects records (by hand, a range, or every record a search and
filters match) and changes them together: attribute values, and the relations the table does not
show, such as setting the duration of the selected timetable types or adding a role to all of
them, in live data or a change set. The UI writes through `POST /batches` (B1–B3), so it is one
client of the bulk API rather than a second write path, and every action the model allows for the
type is offered, read from the model (the relation types a type may have, their direction and
cardinality); no screen knows a type key.

**Packages (outline):**
- **K1: selection.** A selection column in `ui/ObjectTable` (pointer, Shift for a range, keyboard),
  the selection's count and "select all matching" kept as the search and filters rather than as
  IDs, the bulk action bar's frame; no writes.
- **K2: attribute edits and delete.** Set or clear an attribute, delete; a preview of what will
  change; inline or background run with progress, cancel and per-item results linking to each
  record (the job screens from Track J).
- **K3: relation edits.** For each relation type the model allows: add (`ensureRelation`), remove
  (`deleteRelation`) and replace (`replaceRelationSet`), choosing targets with the record picker.
- **K4 (if decided): query-scoped batches.** A batch whose items are "every record matching these
  criteria", decided in the engine, so a large selection is neither paged through nor sent as IDs;
  an API capability integrators get too.
- **K5 (if decided): relation columns.** A view may declare a relation as a column, shown as record
  chips (`ui/RecordChip`), so the result of a bulk relation edit is visible in the list.

**Decisions for K1's planning:** how "all matching" meets optimistic concurrency (versions read at
selection, or an explicit "apply to current values" that the invariant allows only when stated);
enumerated IDs or K4; the limits a UI selection meets (`integrationJobs.limits`); what the UI does
when `INTEGRATION_JOBS_ENABLED` is off; `independent` or `atomic` as the UI's default; a change set's
version claim for a long job. Composable-domains line (ADR-032): bulk APIs are used, not changed,
unless K4 is taken.

## R: Build acceptance and release

**Scope:** after every package in the queue (or R-a at the cut line):
- the full backend `pytest` suite, frontend `npm run test`, Ruff, format, lint and build, every
  browser runner, `test:a11y` and `test:visual`;
- migration checks for every 0.9 table and column (jobs, outcomes, idempotency keys, feed positions,
  profiles, consumer events, subscriptions): clean bootstrap, upgrade from the 0.8.0 head with data,
  restart, interrupted migration, a smoke start on a copy of the development database;
- a schema 0.8 release installing and activating over schema 0.7 releases;
- SC-10, SC-11, C8 and C13, the ROADMAP 0.9 exit gate, and every volume budget;
- PROJECT_STATUS, ROADMAP, TODO, CHANGELOG, API.md and the functionality catalogue updated; residual
  gaps recorded.

**R-a (cut line):** the same without Track J and SC-10's import and export halves, which move to
0.9.1 with their own acceptance.

**Exit:** all gates pass, or each failure is explained and tracked; Base 0.9.0 is ready to release.

## Composable domains check (ADR-032)

This build touches every door in [COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md#doors-to-keep-open):

- **Identity:** upsert keys and feed events must leave room for a retired-ID redirect; a bulk result or
  feed entry for a merged record must be expressible later without a breaking change.
- **Provenance:** bulk and import are the first writes with an origin other than a user edit. The job or
  batch that caused a change is recorded on its audit entry, so a value-source field stays additive.
- **Derived values:** export and consumer projections read values; neither assumes every value is stored.
- **History and erasure:** feed entries and events carry identity and changed field keys, not value
  blobs (C-D7), so a redaction never has to rewrite the feed. A `full` event's object (C-D7 revised)
  is composed at delivery and never stored.
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

## Decisions

All accepted 2026-09-29 as recommended (D3 and D10 revised the same day, D5 revised after a code
check, D15 and D16 added by that check, D17–D19 raised by Q3), D20–D22 raised by Q4 (2026-09-30),
D23–D26 raised by B1, which also confirmed D13 (2026-10-01), D27–D30 raised by B2 (2026-10-01),
D31–D34 raised by F1 (2026-10-03), D35–D39 raised by B3 (2026-10-03), and D40–D41 raised by F2
(2026-10-03).

| # | Question | Decision | Blocks |
| --- | --- | --- | --- |
| D1 | Failure policy and staging for bulk writes | Two policies, chosen per request: `atomic` (all or nothing) and `independent` (each item on its own). No "stop at first error". Change-set context by `changeSetId` is the only staging mode | B, J |
| D2 | Upsert key | The public ID, or one attribute declared unique on the object type (ADR-010), named per request. No composite keys in 0.9. An ambiguous or missing key is a per-item `rejected` | B, J |
| D3 | Import/export file formats and UI | **Revised 2026-09-29 (ADR-035):** import runs an *import profile*, the declarative mapping from sheets and columns to model elements that the 0.10 editor produces ([MODEL_AUTHORING.md](MODEL_AUTHORING.md#import-profile)). Formats: XLSX (several sheets, values not formulas), CSV (UTF-8, header row) and JSON Lines; export stays CSV and JSON Lines. A job may name a stored profile or carry one inline; a CSV whose headers equal field keys needs no profile. Bindings: field or attribute, parent or relation by match key (with delimiter split), flag columns to one relation, translations (row or column per language), system mapping, value maps. 0.9 delivers the contract and its execution (MODEL_AUTHORING A1), a minimal import-preview screen for SC-10 and API-only job administration; the editor is 0.10 | J |
| D4 | Advanced query scope | Criteria over built-in fields, declared attributes and one relation hop, combined with AND; ordering over one declared sort key plus the unique tie-breaker; `select` and `expand` from the model. OR groups and multiple sort keys wait for a second real case | Q |
| D5 | Feed ordering on a multi-writer database | **Revised 2026-09-29 after checking the code:** the audit `sequence_id` is allocated at insert, not commit, and live writes take no workspace-wide lock, so on PostgreSQL two writers can commit out of sequence order. Instead of a visibility watermark, every change that reaches live data takes a per-workspace **feed position** from a counter on the workspace row, locked until commit; feed order is commit order by construction. Writes in one workspace serialize (as SQLite already does); workspaces stay independent. Lock order: workspace row first (INTEGRATION_API F3) | F |
| D6 | Effective-date semantics | An object type declares one effective period from two `date` attributes: inclusive start, exclusive end, open end allowed, overlaps allowed and all returned. Dates have no time zone; `asOf` is a date. `dateTime` periods wait for a real case | Q |
| D7 | Schema language version | One new schema language version (0.8) carries both `consumerApis` and effective periods, with the starter at content release 0.9.0 | Q, C |
| D8 | Raw feed retention and recovery | Same retention setting as consumer events (C-D9, 30 days default). Past it, `410 feed_position_expired` and a publication or export as the re-sync baseline | F |
| D9 | 0.9 cut line | The scope is several times 0.8's. Deliver in order Q (P1, P3) → B → F → C → J, with V (the API reference) at any time, and allow a 0.9.x split after C if R is not in reach | All |
| D10 | Credentials and gates before 0.12 | **Credentials decided 2026-09-29:** none in 0.9. No API keys and no credential in a URL; 0.12 brings engine-provided OAuth 2.0 with JWT, HMAC-signed webhooks and UI administration of both (CONSUMER_API C-D1). **Gate, recommended:** job creation and cancellation form a deployment capability group, `INTEGRATION_JOBS_ENABLED` (ADR-031), on by default like live writes, since a bulk write is no more privileged than the single writes it batches; job reads and the raw feed are ungated like other reads until 0.12 | B, J, F, C |
| D11 | Upserts without a version claim | Update items need `expectedVersion`. An upsert that finds a record without one is rejected `version_required` unless the request declares `onExisting: "overwrite"`, which is audited and reports the previous version (INTEGRATION_API P4) | B, J |
| D12 | Where job files live | A configured directory (`JOB_FILE_DIR`) with size and checksum on the job, not database rows. 0.11 multi-node needs shared storage behind the same setting | J |
| D13 | Batch and job limits | Synchronous batch 1,000 items and 5 MB; `atomic` job 10,000 items; background job 1,000,000 items and 200 MB upload; all settings, reported by capabilities, confirmed against the volume fixture in the first B package. **Confirmed 2026-10-01 (B1)** on the fixture at scale 0.005: an item costs about its single write (creates 15 statements live and 26 in a change set, against 16 and 42 for a single create; upserts with half updates 20.5 and 34.0), and the time per item stays flat as the change set grows once its lookups probe by key. A batch is one transaction holding SQLite's writer lock: 1,000 upserts 3.3 s live and 6.8 s in a change set, 10,000 atomic creates 29 s and 55 s. The defaults stay, and `SQLITE_LOCK_WAIT_SECONDS` (60 by default) lets other writes wait for that lock instead of failing at the driver's 5 s; an operator who wants shorter waits lowers the limits. The background limits are B2's. **Restated on PostgreSQL (0.9.0-alpha.1 PG5, 2026-10-03):** since PG3b items are decided in memory and written in bulk: 1,000 upserts 0.8 s live and in a change set (0.06 statements per item), 10,000 atomic creates 5.4 s live and 17.8 s in a change set (0.01–0.02 per item); a batch holds its workspace's lock (PG3), so other writes in that workspace wait and other workspaces do not; `SQLITE_LOCK_WAIT_SECONDS` is gone (PG2). The defaults stay ([POSTGRESQL_BUDGETS](POSTGRESQL_BUDGETS.md)) | B, J |
| D14 | Retention of jobs, outcomes, files and idempotency keys | 7 days, one setting; afterwards the job is `expired` with its summary kept | B, J |
| D15 | How a publish appears in the audit log | Found 2026-09-29: publishing writes one `published` event with no per-record subjects (`workspace_audit.record_change_set_published`), and the records it changes in live were audited earlier as change-set edits. The feed could not tell what a publish changed. Publish now writes one audit entry per record it applies to live (`created`, `updated`, `deleted`, `reclassified`), each with identity and changed field keys (no values), subjects, a feed position and the `published` event as its cause. Bounded like single writes; replaces the "publishing never amplifies events per object" rule | F, C |
| D16 | The `reclassified` payload in feeds | Its stored before state (ADR-034) stays in the audit log. Feed entries and consumer events carry identity and changed keys only (C-D7, erasure door). _Amended 2026-10-05 (C-D7 revised):_ a `full` consumer event is delivered with the object as get-by-ID answers it, composed at delivery and never stored, so the feed and the event store still keep no values beyond the event's identity (C-D89) | F, C |
| D17 | Query item shape with `select` and `expand` | **Accepted 2026-09-29 (Q3).** Items always carry `id`, `objectTypeKey` and `version`. Without `select`, the rest of the object list's item; with it, the selected values under `fields`, keyed by field (built-ins, attributes, `ancestor:<type>` as `{id, name}` of the ancestor of that type nearest the root), not as item properties, since attribute keys are model keys and could equal one. `expanded` holds one entry per `expand` in request order: `relationTypeKey`, `direction`, `count`, `items` (`relationId`, `object`) and `nextCursor`, a signed cursor that continues on `GET /relations`, as the mapping conflict continuation does | Q |
| D18 | Criteria at the other end of a hop | **Accepted 2026-09-29 (Q3).** The object list's rule over the types the binding allows there: built-in fields always, an attribute only when that is one type binding it as filterable; otherwise `invalid_query` at the criterion | Q |
| D19 | Errors of the query body | **Accepted 2026-09-29 (Q3).** The body's shape (JSON types of known properties, unknown properties, bounds such as `pageSize` and `limit`) is `422 request_validation_error`, as on every other body. What depends on the model (field, operator, value for the field's type, binding, `select`, `expand`, `sort`, `asOf`) is `422 invalid_query` with `details.path`, a JSON pointer into the body | Q |
| D20 | Activating a period over stored records it would refuse | **Accepted 2026-09-30 (Q4).** A release that declares a period, or moves one to other attributes, counts the type's live records whose end is not after their start; with any, activation is `409 model_migration_required` with a diagnostic `invalid_effective_period` and its count, as an added `atLeastOneOf` is. Allowing it would leave records every later change set validation refuses although nobody touched them | Q |
| D21 | `asOf` on the management cross-type lookup | **Accepted 2026-09-30 (Q4), amending ADR-038 and §Q4.** Refused as `422 as_of_not_supported` with `details.route` naming the per-type list, as a model-declared filter is: a period belongs to one type, and no management story needs a dated lookup across types. The design's filtering with `asOfApplied` was copied from the consumer XREF, where C-D14 stays (C16). Refused rather than left undeclared, since an undeclared parameter is ignored and an undated answer would look dated | Q |
| D22 | Which records `asOf` dates in the model-aware query | **Accepted 2026-09-30 (Q4).** The queried records only. A hop's far end and expansions are not dated; a date criterion on the hop dates them where that is wanted | Q |
| D23 | What an atomic batch validates against | **Accepted 2026-10-01 (B1).** Its items in order, each through its single write against the data the items before it left, in one transaction; the first rejection rolls everything back. Not a check of the combined end state, which would need deferred checks the single writes lack, a second validation path; swapping two records' unique values is a change set's work | B |
| D24 | `unchanged` and the version claim | **Accepted 2026-10-01 (B1).** An update or upsert whose name, parent and values equal the record's applies as `unchanged` before any version check: it writes nothing, so it overwrites nothing. A retried upsert answers `unchanged` (§P5), and a recurring feed is silent without `onExisting: "overwrite"` | B, J |
| D25 | Where the 10,000-item atomic budget is measured | **Accepted 2026-10-01 (B1).** Through the inline job's engine path (`submit_inline_batch`), which B2's background run reuses, since a request is capped at 1,000 items; the route's budget is the 1,000-upsert batch | B |
| D26 | An upsert's `initialRelations` | **Accepted 2026-10-01 (B1).** Used only when the upsert creates the record, so a type with a required incoming relation can be upserted; on a found record they are ignored (documented). Changing an existing record's relations is B3's relation items | B, J |
| D27 | Where a background job's items wait | **Accepted 2026-10-01 (B2).** A `job_inputs` table, one row per item (`job_id`, `item_index`, `ref`, the item as JSON), inserted with the job in one transaction; a chunk reads its index range from the checkpoint, and the rows are removed when the job reaches a final state. Not a column (a 50 MB value rewritten and parsed whole per chunk) and not a job file: D12's files are raw uploads and export output, while a batch is already parsed items. J's imports write the same table once rows become items. So no B2 path stores a file, and `JOB_FILE_DIR` (D12) moves from B2's scope to the first J package that stores one (J1's output or J2's upload), so it is never an unused layer | B, J |
| D28 | Cancelling a job | **Accepted 2026-10-01 (B2).** `POST /jobs/{id}/cancel` sets `cancelRequestedAt` in one short transaction and answers `202` with the job; a finished job is `409 job_finished`. The worker does every finish, a queued job's included: at the next chunk start for an `independent` job, and between items of an `atomic` job's one chunk, which then rolls back completely. A chunk does not hold the job row locked while it applies items, so the request never waits for a chunk. Designed for PostgreSQL (READ COMMITTED); no SQLite workaround. **To test on PostgreSQL** once it is the engine's database **Amended 2026-10-02 (0.9.0-alpha.1 PG3b):** an `atomic` job looks for a cancel request before every 500 items it decides and before it writes them, since its items are decided in memory and written together; a check per item would cost a statement per item | B, J |
| D29 | A chunk failing for another reason than an item's refusal | **Accepted 2026-10-01 (B2).** The chunk rolls back; the job is `failed` with `error.code` `job_failed`, a message and a correlation ID, and the remaining items are `unprocessed` with `job_failed`. Applied chunks stay. A process that stops mid-chunk is not a failure: its lease expires and the job resumes at its checkpoint | B, J |
| D30 | Background defaults | **Accepted 2026-10-01 (B2).** `JOB_CHUNK_ITEMS` 500; `JOB_LEASE_SECONDS` 120, renewed with each chunk's commit, so a job resumes within that time after a restart; `BACKGROUND_JOB_MAX_ITEMS` 1,000,000 (D13) and a background request body of `BATCH_BACKGROUND_MAX_BYTES` 50 MB (§B1); the retention sweep runs in the worker every hour, so a process with `INTEGRATION_JOBS_ENABLED` off sweeps nothing | B, J |
| D31 | Where the feed read is delivered | **Decided 2026-10-03 by the user (F1).** F1 assigns positions, but without a read no journey test could see them through the API. The read of §F4 (`GET /workspaces/{key}/feed`, `after`, `pageSize`, `kind`, `objectTypeKey`, the bounded scan, `nextAfter`, `headPosition`, `earliestPosition`) moves into F1; F2 keeps retention, `410 feed_position_expired` with baselines and the deep read budget | F |
| D32 | Relation entries of a publish | **Decided 2026-10-03 by the user (F1), amending D15.** A publish writes one entry per record **and relation** it changes in live data, in this order: records created, updated or reclassified; relations removed; relations created or updated; records removed; then `published`. Otherwise a follower never learns of relation changes made through change sets, and a type change's relation changes (§F1) only reach live data through a publish | F, C |
| D33 | `after` past the head | **Accepted 2026-10-03 with the F1 plan.** `409 feed_position_ahead` with `details.headPosition`. Such a position comes from another workspace's feed or a restored database, where new changes reuse its numbers; answering it would silently skip them | F |
| D34 | What the feed filters match | **Accepted 2026-10-03 with the F1 plan.** Repeated values of one filter match any of them; `kind` and `objectTypeKey` combine. `objectTypeKey` matches object entries whose type, or for `reclassified` whose previous type, is listed; relation and publication entries never match it | F |
| D35 | How relation items run in a batch | **Decided 2026-10-03 by the user (B3).** Decided in memory and written in bulk like object items (PG3b), not one by one like delete items: the single relation writes and the mapping save become batches of one through the same decide steps. A chunk of 500 relation items costs 40–43 statements | B, J |
| D36 | A set replacement removing a required relationship | **Decided 2026-10-03 by the user (B3).** Refused `422 required_relation` with `details.objectId` when the record at the removed relationship's other end requires one and has no other, on `replaceRelationSet` and the mapping PUT; clearing a required set stays refused as before | B, J |
| D37 | The outcome of a set replacement | **Accepted 2026-10-03 with the B3 plan.** `action` `updated`, or `unchanged` for a set already equal to the targets, decided before the claim (as D24); `relationSetVersion` and `relationIds: {created, kept, removed}`. Relation items carry `relationId`, `version` and a claimed set's `relationSetVersion`; the counts keep their four actions | B |
| D38 | Set versions on the anchored read | **Accepted 2026-10-03 with the B3 plan.** `GET /relations?objectId=…` names every non-containment set the record anchors in the listed direction and types (`relationSets`), `0` when untouched; live and in a change set (its own versions); none in a publication | B |
| D39 | Refusals of a set replacement | **Accepted 2026-10-03 with the B3 plan.** A target listed twice is `409 duplicate_relation` at `/items/i/targets/j`; a target's refusal points at it; a stale set is `409 relation_set_version_conflict`, while the mapping PUT keeps `mapping_version_conflict` with its preview; the `transition` payload lists `newTargets` | B |
| D40 | The retention floor and the baseline | **Decided 2026-10-03 by the user (F2).** The floor (`earliestPosition`) is the first entry within `FEED_RETENTION_DAYS`, but never past the active publication's `feedPosition + 1`; with no active publication that has a position (never published, withdrawn, or published before F1), nothing expires. Otherwise a publication older than the period is itself expired, so a reader refused `410` gets `410` again after re-reading it, and a workspace with no publication has no baseline until J1's export. It costs nothing: the audit log is not pruned. A withdrawal can lower the floor back to 1. J1 revisits the no-publication case once an export is a baseline any reader can take | F |
| D41 | The export in the `410` details | **Decided 2026-10-03 by the user (F2).** F2's `410` names the active publication only; J1 adds the export route as a second baseline, an additive field | F, J |
| D46 | Index the attribute values or store a sort key per record (Base 0.8 D26)? | **Approved 2026-10-04 (C3a).** Index the values now; 0.8 D26's stored key stays after 0.9 for few distinct values and deep positions | Q, C |
| D47 | Which contexts C3a's sort covers | **Approved 2026-10-04 (C3a).** Live only; change sets and publications are a task of C6. _Amended 2026-10-05 by C-D67 (C6a):_ publications gained it; change sets stay as they are (TODO) | C |
| D48 | Which lists C3a's sort covers | **Approved 2026-10-04 (C3a).** The shared live attribute sort (consumer lists and the management per-type list); not the `ancestor:<type>` sort | Q, C |
| D49 | What a JSON Lines export line is | **Accepted 2026-10-07 by the user (J1).** `upsert` items keyed by `{id}` (required relationships also as `initialRelations`), then `ensureRelation` items, instead of §J4's `create` and `createRelation`, so a re-import changes nothing. Each record line carries its version as `expectedVersion` (amended the same day by the user), so an edited file updates only rows nobody changed since the export. The file loads into the same workspace or another instance, not a second workspace of the same instance (object IDs are instance-wide) | J |
| D50 | The export scope's shape | **Accepted 2026-10-07 by the user (J1).** `where` per type; `parentObjectId` and `asOf` shared, `asOf` dating only the types with a period (as C-D76–C-D80, named in `asOfApplied`) and refused only when none has one; `include.relations` `none`, `withinScope` (default) or `all` | J |
| D51 | Export formats and the table layout | **Formats decided by the user, layout approved, 2026-10-07 (J1).** JSON Lines, CSV and XLSX. CSV and XLSX share one table layout: records and relationships keyed by column keys, `#{attributeTypeKey}` attribute columns (attribute types are global), `~` orientation columns an import ignores, each record's `version`; CSV both tables in one file, XLSX two named tables with typed cells | J |
| D52 | Where an export's manifest lives | **Accepted 2026-10-07 by the user (J1).** On the job only (`output`), never in the file; the checksum also in `Repr-Digest` and `ETag` on the download | J |
| D53 | One snapshot for a long export | **Accepted 2026-10-07 by the user (J1), revised the same day.** One read-only `REPEATABLE READ` transaction per export, restarted whole after a crash; cancel, lease and progress through a second short session. Exports run on a worker thread of their own, so batches and exports never wait for each other | J |
| D54 | D40 revisited after the export | **Accepted 2026-10-07 by the user (J1).** D40 stays: a workspace without a publication keeps every feed entry, since the audit log is not pruned; the `410` names the export beside the publication (D41) | F, J |
| D55 | `JOB_FILE_DIR` | **Accepted 2026-10-07 by the user (J1).** Without the setting the engine uses `var/job-files` under the project root, created at start; with jobs enabled, a directory that cannot be written refuses the start, naming the path and the setting | J |
| D56 | The export budget | **Approved 2026-10-07 (J1).** The whole live volume workspace (258,000 records) to each format once, under 60 s each; measured 23.1, 24.4 and 31.5 s (POSTGRESQL_BUDGETS §8) | J |

## Next

Decisions are accepted and the design documents are drafted (2026-09-29). Remaining before and during
implementation:

1. Review the drafted INTEGRATION_API sections F and J (before F1 for F, before J1 for J); B and P
   were settled by B1's decisions (D23–D26) and amended where it delivered them.
2. Release 0.8.0.
3. Deliver the [queue](#delivery-queue) from Q1, one package per instruction ("deliver Q1").
