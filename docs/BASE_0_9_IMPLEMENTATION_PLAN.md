# Base 0.9 implementation plan

**Status:** Planned; implementation starts after 0.8.0. The [document set](#design-documents) is
accepted (2026-09-28). All [decisions](#decisions) D1–D16 and CONSUMER_API C-D1–C-D16 are accepted
(2026-09-29). [INTEGRATION_API.md](INTEGRATION_API.md) sections P, B, F, Q and J, the schema 0.8
section and ADR-036–038 are drafted (2026-09-29). Work packages Q1–Q4, B1–B3, F1–F2, C1–C16, V1–V2,
J1–J4 and R are specified (2026-09-29) and delivered in the order of the
[delivery queue](#delivery-queue), each by the [delivery steps](#how-a-package-is-delivered).
**Delivered:** [Q1](#q1-cross-type-lookup) (2026-09-29), [Q2](#q2-workspace-edge-list) (2026-09-29),
[Q3](#q3-model-aware-query) (2026-09-30).

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

**Status: designed, not implemented.** The design (§P) and its decisions (D1, D10–D14, ADR-036) are
accepted; no code exists yet. Track P has **no package of its own**: it is delivered inside the
first bulk packages, so it is never an unused layer:

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
and `asOf` (C16, after Track Q's effective periods), then events C9–C13 without signing; C7 access
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

**Names.** Package IDs are Q1–Q4, B1–B3, F1–F2, C1–C16 (CONSUMER_API's), J1–J4, V1–V2, T1 and R. The API
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
| 0 | — | 0.8.0 released | C5, R1b and R2 pass |
| 1 | [Q1](#q1-cross-type-lookup) | — | `GET /objects` across types — **delivered 2026-09-29** |
| 1a | [E1–E3](BACKEND_BOUNDARIES_PLAN.md) | Q1 | Backend tiers, one rule set, one write path; no contract change — **delivered 2026-09-29** |
| 2 | [Q2](#q2-workspace-edge-list) | — | Edge list with publication context, published as `/workspaces/{key}/relations` — **delivered 2026-09-29** |
| 3 | [Q3](#q3-model-aware-query) | Q1 | `POST …/queries/objects`: criteria, one relation hop, `select`, `expand` — **delivered 2026-09-30** |
| 4 | [C1](#c1-consumer-api-definitions) | — | `consumerApis` schema and validation; opens schema 0.8 — **delivered 2026-09-30** |
| 5 | [Q4](#q4-effective-periods-and-asof) | Q3, C1 | `effectivePeriod` in schema 0.8, `asOf` on reads; starter 0.9.0; SC-11 (API) |
| 6 | [V1](#v1-api-reference-page) | — | Scalar at `/docs` with the management API; a filler, any time before V2 |
| 7 | [B1](#b1-job-model-and-inline-object-batches) | — | **Track P (§P1–P5, P7)**, `POST /batches` with object items, inline |
| 8 | [F1](#f1-feed-positions) | B1 | Feed position in commit order, publish entries (D15), lock order |
| 9 | [B2](#b2-background-jobs) | B1 | **Track P (§P6)**: worker, chunks, lease, resume, cancel, retention |
| 10 | [B3](#b3-relation-and-relation-set-items) | B1 | Relation items and `replaceRelationSet` |
| 11 | [F2](#f2-feed-read-retention-and-recovery) | F1 | `GET /workspaces/{key}/feed`, retention, `410` with baselines |
| 12 | [T1](#t1-track-checkpoint-q-b-f) | Q4, B2, B3, F2 | Track checkpoint for Q, B and F: their groups, budgets and a composed journey |
| 13 | C2 | C1 | Consumer object and projections |
| 14 | C3 | C2 | Lists |
| 15 | C4 | C2 | Consumer index and XREF scoring |
| 16 | C5 | C4 | XREF parameters |
| 17 | C14 | C4 | Batch resolve |
| 18 | C15 | C5 | Crosswalk |
| 19 | C6 | C3, C4, F1 | ETag, publications with `eventSequence`, OpenAPI per definition, API index |
| 20 | [V2](#v2-consumer-sources) | V1, C6 | Consumer contracts as reference sources |
| 21 | C8 | C3–C6, C14, C15 | Parity acceptance; the consumer read line's checkpoint |
| 22 | C16 | C2, Q4 | `asOf` in the consumer tier; SC-11 (consumer) |
| 23 | C9 | C2 | Event definitions |
| 24 | C10 | C9, F2 | Event deriver, event store, pull feed |
| 25 | C11 | C10 | Subscriptions |
| 26 | C12 | C11 | Dispatcher |
| 27 | C13 | C12 | Event acceptance; the events line's checkpoint |
| — | _cut line (D9)_ | | _If R is out of reach, 0.9.0 releases here with R-a and Track J moves to 0.9.1_ |
| 28 | [J1](#j1-export) | Q3, Q4, B2, F1 | Export jobs |
| 29 | [J2](#j2-import-profiles-and-file-reading) | B3 | Import profiles, XLSX/CSV/JSON Lines reading, rows to items |
| 30 | [J3](#j3-import-preview-and-execution) | J2, B2 | Import preview, confirm, execute |
| 31 | [J4](#j4-import-screen-and-sc-10) | J1, J3, F2 | The SC-10 screen and SC-10 acceptance |
| 32 | [R](#r-build-acceptance-and-release) | all | Build acceptance and release |

**Order revised 2026-09-30, after Q3.** The queue delivers first what later packages build on, while
little depends on it yet, and keeps self-contained packages as fillers:

- **C1, then Q4**: schema 0.8 opens once and Track Q closes; the starter becomes content release 0.9.0
  once, and every later package that touches the model (C2 onward) builds on a settled schema.
- **B1, then F1 before B2**: F1 takes a per-workspace lock on every live write and fixes the lock
  order (INTEGRATION_API F3). The background worker (B2) is then built on that order from the start
  instead of being retrofitted. F1 needs only B1.
- **V1** is independent of every other package: it is delivered wherever a gap suits, early enough
  that the reference page can be used to review contracts as they land. V2 follows C6.
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

## Sequence and dependencies

```text
Track P:  inside B1 (§P1–P5, P7) and B2 (§P6); no package of its own
Track Q:  Q1 ─ Q3 ─ Q4            Q2 (alone)          Q4 also needs C1 (schema 0.8)
Track V:  V1 ────────────────── V2                    V2 needs C6
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
Track J:  J1                                       needs Q3, Q4, B2, F1
          B3 ─ J2 ─ J3 ─ J4                        J3 needs B2; J4 needs J1, F2
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
change set and as a publish diagnostic; `asOf` on the per-type list, Q1 (with `asOfApplied`) and Q3;
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
If a D13 default does not fit its budget, lower it here and record the new value in D13.

**Groups:** `jobs` (new), `records`, `change_sets`, `startup`, `contract`, `volume`.

**Exit:** a batch contract in API.md; D13 confirmed or amended.

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
beside it recorded.

**Groups:** `jobs`, `change_sets`, `startup`, `volume`.

**Exit:** background execution in API.md; restart behaviour documented in the operations notes.

#### B3: Relation and relation-set items

**Design:** §B4 (ADR-022). **Needs:** B1.

**Scope:** `createRelation`, `ensureRelation`, `updateRelation`, `deleteRelation` and
`replaceRelationSet` in batches, with relation-set claims and P4 for sets; the mapping PUT and
`replaceRelationSet` share one service, extended from one target to a set (the mapping replacement is already one flow over live data and change sets since E3).

**Tests:** each op against its single-write route; a set replaced with kept, added and removed
targets; cardinality, ancestor scope, required and containment refusals; set versions advanced once
per affected set; the `transition` audit entry; the relation matrix state kept current
(`matrix_states.verify`); a record and its required relation in one atomic batch.

**Groups:** `jobs`, `mapping`, `matrix`, `records`, `contract`.

**Exit:** relation items in API.md.

## Track F — Change feed

#### F1: Feed positions

**Design:** §F1–§F3, ADR-037 (D5, D15, D16). **Needs:** B1 (the job cause).

**Scope:** migration adding `audit_events.workspace_key`, `audit_events.feed_position` (unique per
workspace) and `workspaces.feed_position`; `record_audit_event` assigns positions for live changes
under the workspace row lock; **every live write path takes that lock first**: in `LiveWrites._begin`, the seam
every live write opens (E3, [BACKEND_BOUNDARIES_PLAN](BACKEND_BOUNDARIES_PLAN.md)), which
`test_boundaries` keeps the only writer of live rows; publish writes one entry per record it applies, with the publish as
cause, then `published`; the `reclassified` entry's feed form; `publications.feed_position`.

**Tests:** positions gapless and in commit order under concurrent writers (two connections, on
SQLite); a rolled-back write leaves no gap; change-set edits take none; a publish's entries equal the
records it changed; a batch's entries carry the job; lock order (no deadlock between a publish and a
live write of a record it touches).

**Budget:** the added statement per write against the 0.8 write budgets; a publish of 10,000 records.

**Groups:** `feed` (new), `records`, `change_sets`, `mapping`, `matrix`, `startup`, `volume`.

**Exit:** C-D15 holds by test: a publication equals live data at its `feedPosition`.

#### F2: Feed read, retention and recovery

**Design:** §F4, §F5 (D8). **Needs:** F1.

**Scope:** `GET /api/v1/workspaces/{key}/feed` with `after`, `pageSize`, `kind`, `objectTypeKey`;
`nextAfter`, `headPosition`, `earliestPosition`; the bounded filtered scan; `FEED_RETENTION_DAYS`;
`410 feed_position_expired` naming the active publication and its position.

**Tests:** follow, stop and resume without loss or repeat; filters with sparse matches; `410` at and
past the floor; re-sync from a publication then the feed missing nothing (SC-10's feed half).

**Budget:** a 500-entry page at head and deep in a 1,000,000-entry feed.

**Groups:** `feed`, `contract`, `volume`.

**Exit:** the feed in API.md; SC-10's feed half passes at API level.

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

## Track C — Consumer API

Scope, order and acceptance are in [CONSUMER_API.md](CONSUMER_API.md#delivery-packages); C7 moved to
0.12. Each C package follows the delivery steps above; the table adds what this plan needs.

| Package | Needs | Groups | Exit |
| --- | --- | --- | --- |
| C1 | 0.8.0 | `consumer` (new), `model`, `contract` | Schema 0.8 accepts `consumerApis` (and nothing else yet); the breaking-change check (C-D2, C-D4) |
| C2 | C1 | `consumer`, `contract` | Get by ID with projections, ancestor fields and typed values |
| C3 | C2 | `consumer`, `queries`, `volume` | Lists with and without a parent, ADR-030 paging |
| C4 | C2 | `consumer`, `volume` | XREF scoring deterministic; `expect=one` |
| C5 | C4 | `consumer` | Every parameter kind on XREF |
| C14 | C4 | `consumer`, `volume` | Batch resolve equal to `xref?expect=one` per item; C-D13 limit confirmed |
| C15 | C5 | `consumer` | Crosswalk with `target_not_found` and `ambiguous_target` |
| C6 | C3, C4, F1 | `consumer`, `contract` | Publications with `eventSequence` (= `feedPosition`), OpenAPI per definition, API index, resolved `workspace` named (C-D16) |
| C8 | C3–C6, C14, C15 | `consumer`, `volume` | Parity scenarios 1–13 and 16 pass on the fixture model |
| C16 | C2, Q4 | `consumer` | `asOf` everywhere; SC-11's consumer half; parity scenario 15 |
| C9 | C2 | `consumer`, `model` | `events` validated and in the contract check |
| C10 | C9, F2 | `feed`, `consumer` | Deriver checkpoint per workspace; pull feed with `410` |
| C11 | C10 | `feed`, `contract` | Subscriptions API under its capability, host allowlist, suspension on model change |
| C12 | C11 | `feed` | Ordered per-change and coalesced delivery, retry, suspend, resume |
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

#### V2: Consumer sources

**Needs:** V1, C6. **Scope:** the page lists every installed consumer definition and contract version
from the API index as separate sources. **Tests:** sources follow a model release that adds and
removes a definition. **Groups:** `consumer`, `contract`; `test:browser:v1`.

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

**Design:** §J5. **Needs:** J1, J3, F2.

**Scope:** the minimal import screen from the workspace (choose a file and a profile, preview,
counts, binding report, rejected rows paged, confirm or cancel, result); SC-10 end to end; the screen
in the accessibility and visual gates, light and dark.

**Groups:** `jobs`; frontend `vitest related`; `test:browser:j4` (new); `test:a11y`, `test:visual`.

**Exit:** SC-10 passes, with its simplicity check (failed rows acted on without redoing successful
work).

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

## Decisions

All accepted 2026-09-29 as recommended (D3 and D10 revised the same day, D5 revised after a code
check, D15 and D16 added by that check, D17–D19 raised by Q3).

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
| D13 | Batch and job limits | Synchronous batch 1,000 items and 5 MB; `atomic` job 10,000 items; background job 1,000,000 items and 200 MB upload; all settings, reported by capabilities, confirmed against the volume fixture in the first B package | B, J |
| D14 | Retention of jobs, outcomes, files and idempotency keys | 7 days, one setting; afterwards the job is `expired` with its summary kept | B, J |
| D15 | How a publish appears in the audit log | Found 2026-09-29: publishing writes one `published` event with no per-record subjects (`workspace_audit.record_change_set_published`), and the records it changes in live were audited earlier as change-set edits. The feed could not tell what a publish changed. Publish now writes one audit entry per record it applies to live (`created`, `updated`, `deleted`, `reclassified`), each with identity and changed field keys (no values), subjects, a feed position and the `published` event as its cause. Bounded like single writes; replaces the "publishing never amplifies events per object" rule | F, C |
| D16 | The `reclassified` payload in feeds | Its stored before state (ADR-034) stays in the audit log. Feed entries and consumer events carry identity and changed keys only (C-D7, erasure door) | F, C |
| D17 | Query item shape with `select` and `expand` | **Accepted 2026-09-29 (Q3).** Items always carry `id`, `objectTypeKey` and `version`. Without `select`, the rest of the object list's item; with it, the selected values under `fields`, keyed by field (built-ins, attributes, `ancestor:<type>` as `{id, name}` of the ancestor of that type nearest the root), not as item properties, since attribute keys are model keys and could equal one. `expanded` holds one entry per `expand` in request order: `relationTypeKey`, `direction`, `count`, `items` (`relationId`, `object`) and `nextCursor`, a signed cursor that continues on `GET /relations`, as the mapping conflict continuation does | Q |
| D18 | Criteria at the other end of a hop | **Accepted 2026-09-29 (Q3).** The object list's rule over the types the binding allows there: built-in fields always, an attribute only when that is one type binding it as filterable; otherwise `invalid_query` at the criterion | Q |
| D19 | Errors of the query body | **Accepted 2026-09-29 (Q3).** The body's shape (JSON types of known properties, unknown properties, bounds such as `pageSize` and `limit`) is `422 request_validation_error`, as on every other body. What depends on the model (field, operator, value for the field's type, binding, `select`, `expand`, `sort`, `asOf`) is `422 invalid_query` with `details.path`, a JSON pointer into the body | Q |

## Next

Decisions are accepted and the design documents are drafted (2026-09-29). Remaining before and during
implementation:

1. Review the drafted INTEGRATION_API sections B, F, Q and J, the schema 0.8 section and ADR-036–038
   (before B1 for B and P, before F1 for F, before J1 for J).
2. Release 0.8.0.
3. Deliver the [queue](#delivery-queue) from Q1, one package per instruction ("deliver Q1").
