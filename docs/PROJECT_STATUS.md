# Project status

## Current development baseline — Base 0.8 released 2026-09-29

**Base 0.8 is released (2026-09-29)**: scalable browsing (Track S), workspace terminology and
capability boundaries (Track W), the relation matrix (Milestone A), the hierarchy editor (Milestone B),
the change set review (P2) and hierarchy restructuring (Milestone C). The starter model is content
release 0.8.0 on schema language 0.7. Next is 0.9, integration-grade APIs
([plan](BASE_0_9_IMPLEMENTATION_PLAN.md)): **Q1, the cross-type lookup `GET /objects`, is delivered
(2026-09-29)**, and so is the backend boundaries refactor E1–E3 ([record](BACKEND_BOUNDARIES_PLAN.md):
tiers, one rule set for live data and change sets, one write path; no contract change), and so is
**Q2, the workspace edge list** (`publicationId` on `/mappings`, the same list at
`/workspaces/{key}/relations`, 2026-09-29), and so is **Q3, the model-aware query**
(`POST /workspaces/{key}/queries/objects`: criteria, `ancestor:<type>`, one relation hop, `select`,
`expand`; D17–D19; 2026-09-30). The queue was reordered after Q3
([delivery queue](BASE_0_9_IMPLEMENTATION_PLAN.md#delivery-queue)), and **C1, consumer API definitions**
(schema 0.8 opened with `consumerApis`, the breaking-change check at activation; C-D17–C-D20;
2026-09-30) is delivered, and so is **Q4, effective periods and `asOf`** (`effectivePeriod` in schema
0.8, the `invalid_effective_period` write rule, `asOf` on the per-type list and the model query, the
starter as content release 0.9.0 on schema 0.8; SC-11 passes through the management API; D20–D22;
2026-09-30), and so is **V1, the API reference page** (Scalar at `/docs` over the management API,
the script bundled so the page works offline, `RDM_API_REFERENCE_SCRIPT=cdn` to load it from a CDN;
2026-09-30), and so is **B1, the job model and inline object batches** (`POST /batches` with create,
update, upsert and delete items under `atomic` or `independent`, record references by unique key,
idempotency keys, `GET /jobs`; D23–D26, D13 confirmed; 2026-10-01), and so is **B2, background
jobs** (`run: background`, the in-process worker with chunks, lease, resumption, cancellation,
release and claim stops, and retention; D27–D30; 2026-10-01; delivered before F1, whose
workspace lock the chunks' write path will take). On SQLite a background job blocks other writes
until it ends. Next is the interim release **0.9.0-alpha.1, PostgreSQL runtime**
([plan](POSTGRESQL_RUNTIME_PLAN.md): PostgreSQL only, decisions PG-D1–PG-D10 accepted 2026-10-01),
with the test harness ([plan](TEST_HARNESS_PLAN.md): seeded databases built once and reused until
the schema, model or seed changes, inside PG1; parallel runs and budget sizes after PG2), then F1.
**PG1 is delivered (2026-10-01):** PostgreSQL only with the startup refusals, one baseline migration,
ICU root collation (PG-D11), `scripts/postgres.sh`, and the test harness's private server with seeds
built once (H1's core); `startup` and `contract` pass except four tests that need PG2. **PG2 is
delivered (2026-10-01):** current-live capture on a REPEATABLE READ snapshot, row locks instead of
SQLite's writer lock, `pg_trgm` search (revision `20261001_02`), the matrix forms with a linear state
build (0.1 volume in 7 s), names ordered as the database orders them, every foreign-key rule pinned,
no dialect branch in `app/`, and the browser runners on the development server with their seeds;
every backend group except `volume` passes on PostgreSQL. **H2 is delivered (2026-10-01):**
`pytest -n auto` runs the suite on one worker per core with a session database each; timing-based
`serial` tests (the `volume` group and two timer tests) run in a second invocation without `-n`. The
968 parallel tests take 1 min 49 s; the whole serial suite took 28 min 39 s, 21 min of it the two
full-size budgets ([record](TEST_HARNESS_PLAN.md#h2-parallel-runs)). The test plan was revised
the same day with [time ceilings](TEST_HARNESS_PLAN.md#time-ceilings), and PG-D12–PG-D17 accepted:
batch items decided in memory and written in bulk
([PG3b](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk)), with large
batch deletes noted to revisit (PG-D18). **H3 is delivered (2026-10-01):** the two full-size
budgets carry `budget` and leave every run whose `-m` does not name it, `serial` is narrowed to three
wall-time tests, the summary lists tests over 10 s and the wall time, and the ceilings are rules in
AGENTS.md; the full suite without `budget` takes 2 min 41 s (2.7×, short of the 4× target). Its run
found a deadlock between a relation create and a mapping save on one edge, recorded for PG3
([record](TEST_HARNESS_PLAN.md#h3-budgets-out-of-everyday-runs-the-time-ceilings-enforced)). **PG3
is delivered (2026-10-02):** every live write locks its workspace row (`FOR NO KEY UPDATE`) before
it reads, so live writes of one workspace serialize and workspaces write in parallel; the lock
order (workspace, change set, runtime state, records, job row) is in ARCHITECTURE, H3's deadlock is
gone, the cascade deletion's table locks are removed, and `test_pg3_concurrency` races every
checked invariant and the D28 job cases on two connections
([record](POSTGRESQL_RUNTIME_PLAN.md#pg3-concurrency)). Its seven groups took 2 min 7 s, over the
2-minute ceiling, so H4 is due. Its amendment the same day locks the workspace for change-set
writes too (key share), so a retirement waits for them; the activation deadlock found in PG3 and the
time of one chunk beside a live write moved into PG3b's scope. **PG3b is delivered (2026-10-02):**
create, update and upsert items are decided in memory through the single writes' decide steps over
a batch lookup (preloaded per chunk, each item seeing the items before it) and written together in
multi-row statements; a single write is a batch of one through the same code, delete items keep
their per-item path, and a bulk write failing on a row the rules could not see is redone item by
item. A chunk costs 30–49 statements for 100 or 500 items at both seeded sizes (a live upsert item
cost 20.5 before) and 0.25–0.46 s for 500 items; the release is checked before matrix states are
written, so PG3's activation deadlock is closed; an `atomic` job looks for a cancel request every
500 items and before writing (D28 amended). The package's review found that a single live update
would overwrite a write committed between its read and its lock; it now reads again under the
lock ([record](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk)). Its
four groups took 2 min 31 s, over the ceiling (H4). **Testing consolidation planned (2026-10-02):**
an audit of the 1,063-case backend suite found it written per work package after the code, from the
code, with no test tied to a user journey and every package over its ceiling. The user decided a
[testing strategy](testing/STRATEGY.md) (unit tests for each piece of code's purpose, journey tests
for every user journey of every client, the API as the product, specification-first test cases) and
[H4](TEST_HARNESS_PLAN.md#h4-testing-consolidation) moves the suite onto it in slices H4a–H4e.
**H4a is delivered and approved (2026-10-02):** the journey catalogue (26 generic journeys, 138 variants,
every client) and the API inventory mapping every route, parameter, error code and setting to journeys,
with seven decisions, all taken the same day ([record](TEST_HARNESS_PLAN.md#h4a-the-journey-catalogue)). **H4b is delivered
(2026-10-02):** journey markers checked against the catalogue, the journey and unit layout, the API
inventory check, selection by change (`pytest-testmon`, on the C tracer) with `tests.affected` for
what coverage cannot see, and the trace report; mutation testing was tried and dropped in favour of
planted faults per area in H4d ([record](TEST_HARNESS_PLAN.md#h4b-traceability-and-selection)).
**H4c is delivered (2026-10-03):** journey tests for every catalogue entry with an API or operator
side, with every deviation decided ([record](TEST_HARNESS_PLAN.md#h4c-journey-tests)). **H4d, the unit
layer and the move, runs in 14 area slices** ([plan](TEST_HARNESS_PLAN.md#h4d-the-unit-layer-and-the-move));
**H4d-1, jobs and batches, is delivered (2026-10-03):** four old modules (73 cases) replaced by unit
tests of the job engine (62 cases) and four checks merged into J11 and J12, with all 14 planted faults
caught. **H4 then stopped (user's decision, 2026-10-03):** H4d-2 onwards and H4e are postponed and
no dependency of any release up to 1.0, and test work per package is capped in proportion to the
feature (AGENTS.md, Testing). **PG4 is dropped (2026-10-03):** the SQLite data was moved by hand, so
no copy command is built. **PG5 is delivered and 0.9.0-alpha.1 released (2026-10-03):** every volume
budget re-measured on PostgreSQL (statements and rows hold; 143 of 154 full-volume reads within
100 ms), the 100,000-item batch measured once (52 s live, 64 s in a change set), the SQLite planner
constructs removed, name search through trigram indexes with candidates read first (revision
`20261003_01`), and the eleven remaining read exceptions deferred to the first fixes after 1.0, with a
complete handoff in [POSTGRESQL_BUDGETS.md](POSTGRESQL_BUDGETS.md)
([record](POSTGRESQL_RUNTIME_PLAN.md#pg5-budgets-acceptance-and-release)). **F1 is delivered
(2026-10-03):** the change feed `GET /workspaces/{key}/feed`.
- Every change to live data has a position, gapless and in commit order, taken under the workspace
  lock (revision `20261003_02`).
- A publish writes one entry per record and relationship it changed, then `published` (D15, D32).
- The read pages by position with bounded filters, and refuses a position past the head (D31–D34).

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#f1-feed-positions)). **B3 is delivered (2026-10-03):**
relationship items in batches.
- `createRelation`, `ensureRelation`, `updateRelation`, `deleteRelation` and `replaceRelationSet`
  (any number of targets) are decided in memory and written in bulk, 40–43 statements per chunk
  (D35).
- The single relationship writes and the mapping save are batches of one through the same steps.
- A replacement keeps a required relationship its record needs (D36).
- `GET /relations?objectId=…` names each set's version, an empty set included (D38).
- A duplicate relationship is `409 duplicate_relation` (live it answered 500).

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#b3-relation-and-relation-set-items)). **F2 is delivered
(2026-10-03):** feed retention and recovery.
- `FEED_RETENTION_DAYS` (30) sets how long the feed answers a position, reported by
  `GET /capabilities`; an older one is `410 feed_position_expired`, naming the active publication
  and its `feedPosition` to re-read (revision `20261003_03`).
- The earliest position never passes the active publication's, and a workspace without one keeps
  every entry (D40); the export as a second baseline is J1's (D41).
- A 500-entry page costs 4 statements, 25–35 ms, at the head and the middle of a 1,000,000-entry
  feed.

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#f2-feed-retention-and-recovery)). **T1 is delivered
(2026-10-03):** the checkpoint for Tracks Q, B and F.
- A composed journey (a background job followed through the feed, with dated queries and the edge
  list in live data, a change set and a publication) passes.
- Two defects in creating a change set from current live data and in publishing are fixed. Both
  answered `500` above about 65,000 records (a parameter list per record), and both flushed in
  quadratic time.
- Dated reads are measured at full volume, four of them over 100 ms (POSTGRESQL_BUDGETS E8).
- Applying a publish no longer flushes per record. Publishing 1,000 changes in 26,000 records now
  takes 11.3 s instead of 25.0 s.
- At T1, publishing and creating a change set copied the workspace through Python. Decided: the
  copies move into PostgreSQL as plain `INSERT … SELECT` (amendment T1a), sized for the volume
  fixture at 0.1 scale; larger workspaces are deferred until after 1.0.

([record](BASE_0_9_IMPLEMENTATION_PLAN.md#t1-track-checkpoint-q-b-f)). **T1a is delivered
(2026-10-04):** current-live bases and publications copy records, relationships and typed values
inside PostgreSQL, with matrix states and history cells also copied by set statements. Revisions
`20261004_01` and `20261004_02` add the shared SQL value encoding, preserving the existing 28-digit
decimal rounding at every scale a decimal column holds (the review found 1e-16383 answering `500`).
At 0.1 scale, capture takes 3.3 s instead of 7.7 s and loads 7 ORM rows rather than the whole
workspace; publishing 1,000 changes takes 9.0 s instead of 11.2 s. The full-size completion probe
passes; publication merge and graph validation remain in Python
([evidence](BASE_0_9_IMPLEMENTATION_PLAN.md#t1a-copies-inside-the-database)). **T1b is delivered
(2026-10-04):** every error code on every API is upper case (`OBJECT_NOT_FOUND`), stored job
results included (revision `20261004_03`); a breaking change for clients comparing codes
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#t1b-one-error-code-pattern)). **C2 is delivered
(2026-10-04):** the consumer API tier at `/api/consumer` with get by ID, which answers a definition's
shared object (roles, attributes, parent, path, hierarchy and projections) read live by the object
ID, in the default or a named workspace (`RDM-Workspace`); a consumer API's identity is now always
the object ID (C-D21–C-D26, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c2-delivery-record)). **C3 is
delivered (2026-10-04):** consumer lists (every record of a type, or those below parent IDs, in the
list's `sortBy` order, with ADR-030 paging) and every parameter kind on lists and get by ID
(C-D27–C-D33). **C3a is delivered (2026-10-04):** lists sorted by an attribute read in value order through new
indexes (migration `20261004_04`), so consumer lists by `sortBy` page in 10–12 ms at full volume
(were 0.5–2.6 s) and the live E3 exception is closed (9.9 ms); a deep position jump (123 ms) and an
ancestor filter with its total (101 ms) remain at the budget line (D46–D48,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c3a-delivery-record)). **C3b is delivered (2026-10-04):**
consumer API parameters list several values as OpenAPI 3 serialises a list in a query, repeated or
comma-separated with `%2C` for a comma inside a value; C3's `\,` escape, which the user had not
approved, is withdrawn ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#c3b-delivery-record)). **C4 is
delivered (2026-10-05):** XREF lookup (`GET /api/consumer/{apiKey}/v{n}/xref`): the definition's
`match` scores live records at read time, own and promoted weights, several terms, deterministic
order, paging with a total, `expect=one` with `404 NO_MATCH` and `409 AMBIGUOUS_MATCH`; contains from
3 characters, `400 QUERY_TOO_BROAD` past 10,000 matches. Exact matches read new `lower(…)` indexes
(migration `20261005_01`); lookups take 34–58 ms at full volume and the too-broad refusal 116 ms,
recorded (C-D34–C-D41, [record](BASE_0_9_IMPLEMENTATION_PLAN.md#c4-delivery-record)). **C5 is
delivered (2026-10-05):** the definition's parameters narrow XREF, acting on the scored objects, and a
`projection` parameter with `scoresFrom` limits which related records pass scores; `scoresFrom` is
validated and part of the contract (C-D42–C-D46,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c5-delivery-record)). **C14 is delivered (2026-10-05):** batch
resolve (`POST /api/consumer/{apiKey}/v{n}/resolve`), up to 1,000 lookups or IDs, each outcome the
single read's answer; XREF became a batch of one, seeking a single best match with exact rules first;
a trigram index on names with workspace and type (`btree_gin`, migration `20261005_02`); 1,000
lookups in 816 ms at full volume (C-D47–C-D53,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c14-delivery-record)). **C14a and C14b (2026-10-05):** repeated
lookups resolved once, the ancestor walk read by ID and contains selects built without aliases; the
1,000-lookup batch now takes 236 ms. **C15 is delivered (2026-10-05):** crosswalk, `to.{parameter}`
on get by ID, lists, XREF and batch resolve with `target`, `TARGET_NOT_FOUND`, `AMBIGUOUS_TARGET` and
`MULTIPLE_TARGETS`; `targetable` is part of the contract (C-D54–C-D58,
[record](BASE_0_9_IMPLEMENTATION_PLAN.md#c15-delivery-record)). Next: CN1, in the order of the
[delivery queue](BASE_0_9_IMPLEMENTATION_PLAN.md#delivery-queue).

Base 0.5 is the completed operational/model-release foundation. Base 0.6 is released (2026-09-11).
**Base 0.7 is released (2026-09-25)**: core mapping, schema 0.6 and draft version selection. The starter
model is content release 0.7.0 on schema language 0.6. WP-1 (accessibility gates), WP-2 (schema 0.6
`mappingGrid` view contract), WP-3 (relation-set version persistence), WP-4 (mapping query APIs),
WP-5 (atomic mapping replacement), WP-6 (backend draft version selection) and WP-7 (browser draft
version selection) are delivered.
WP-8A/WP-8B and WP-14 are delivered (committed in `f8e39a8`, 2026-09-15): mapping is a lens of a
contextual collection inside one model-driven application browser rather than a separate primary
destination. The Base 0.7 frontend redesign (`936a70e`) and dark mode with the settings menu
(`315e6f7`) followed on 2026-09-24, then WP-12 and WP-13A/B/C. All triggered WP-10 slices (A–G) are
delivered; WP-10E/F/G closed on 2026-09-25. **WP-9 composed build acceptance passed on 2026-09-25**:
SC-07 and SC-15 run as composed browser + API journeys (`test:browser:sc07`, `test:browser:sc15`,
`test_build07_wp9_acceptance.py`), the full backend/frontend suites, all browser runners and the
accessibility and visual gates are green, and WP-10H/I/J found on the way are closed. The draft
timestamp decision it surfaced is delivered as WP-10K (not recorded in drafts and history).

**0.8 delivery record.** [Track S](BASE_0_8_IMPLEMENTATION_PLAN.md#work-packages--track-s) (S1–S8,
scalable browsing, ADR-030) and [Track W](BASE_0_8_IMPLEMENTATION_PLAN.md#track-w--workspace-terminology-and-capability-boundaries)
(W1–W6, ADR-031 terminology and capability boundaries) were delivered on 2026-09-26. Next are the
relation matrix (Milestone A, a generic rows × ancestor-columns view; A1 schema 0.7 `relationMatrix`
contract delivered 2026-09-27; A2 relation matrix query, A3 writes from a cell and A3b stored cell
states for the row state filter (ADR-033) delivered 2026-09-27; the A4 lens and A5 acceptance
delivered 2026-09-28; A6, the snapshot table index drift found in A2, delivered 2026-09-28)
and hierarchy editor (Milestone B; B1 schema 0.7 `tree` contract delivered 2026-09-28; B2 move targets with
D14 eligibility delivered 2026-09-28, the matrix container move a known budget exception, D29; B3 tree
lens and B4 acceptance delivered 2026-09-28; B5 drag and drop in the tree lens, added in the Milestone B
review, delivered 2026-09-29; its amendment B5b (move to the top level) delivered 2026-09-29, which
closes Milestone B; D34–D36 accepted),
and P2 (P2a change lists API and P2b review screen delivered 2026-09-28; D31–D33 accepted), then R1 build
acceptance (passed 2026-09-28, without B5; [record](BASE_0_8_IMPLEMENTATION_PLAN.md#r1-build-acceptance-and-release))
and its amendment R1b for B5 and B5b. Milestone C (structure refactoring: type changes derived from
the model, with preview and history as the way back; C0–C5 and R2) was added 2026-09-28; C0 is
delivered 2026-09-29 with [ADR-034](DECISIONS.md#adr-034--a-records-type-can-change-derived-mapping-preview-and-apply-history-as-the-way-back)
and D37–D43 accepted; C1, a record's type change in the engine with the D42 refusal, is delivered
2026-09-29; C2, the restructuring planner (possible types, the cascade, the D40 mapping, offers back,
refusals, the plan digest), is delivered 2026-09-29; its dry run took 48 s at C0's 5,000-record limit, so D44 lowers
the D41 limit to 500 records (a 2.8 s preview); C3, the restructuring API (preview and apply for `move`,
`changeType`, `insertLevel`, `removeLevel` and `changeTypeUnder`, parent candidates' `includeTypeChanges`),
is delivered 2026-09-29; C4, restructuring in the tree lens (Move to… and drag to places that change
the type, Change type…, Insert level above…, Remove this level…, Change type of all … in here…, the
preview by record and by type pair, the review's type change and the browser following D42), is
delivered 2026-09-29. C5, the milestone acceptance (`test:browser:c5` on the starter and generated
models, SC-17, US-H03; the preview and dialogs in both gates), is delivered 2026-09-29, which completes
Milestone C; on the way it made change set validation linear (D46; 125 s → 1.4 s at 2% volume) and
fixed a reclassified-then-removed record in the review and the lens's late refocus. **R1b and R2
passed together on 2026-09-29** ([record](BASE_0_8_IMPLEMENTATION_PLAN.md#r2-milestone-c-build-acceptance)):
the full backend suite (829), Vitest (381), all 22 browser runners and both gates are green with no
fix or re-baseline, and no migration was needed. D43 is resolved, and **0.8.0 is released (2026-09-29).**
Residual 0.7 gaps are listed in the
[plan's WP-9 record](BASE_0_7_IMPLEMENTATION_PLAN.md#wp-9-composed-product-validation--sc-07-and-sc-15).

The generic model defines applications, object types, reusable fields, allowed relationships and views.
Master, Systems and Translations are configurable starter examples; runtime code must remain unaware
of their keys. The selected immutable model governs current behavior; the configured source JSON is
bootstrap input, not a parallel activation mechanism.

## Accepted product direction and actual availability

ADR-026 restored direct live reference-data maintenance. ADR-027 consolidates the user's accepted
GAP-01–GAP-08 answers and distinguishes accepted targets from implementation evidence.

| Area | 0.6 state | Next |
| --- | --- | --- |
| Live data | Complete: generic object, field, parent, relation and translation APIs and browser controls; record concurrency and audit | — |
| Optional change sets | Complete: current-live and historical source selection, shared browser editing, validation and delta merge | — |
| Historical data | Complete: newest-first browser discovery, pinned-model immutable reads and historical draft derivation | — |
| Publication withdrawal | Complete: truthful browser confirmation removes only the designation while retaining live data/history | — |
| Workspace administration | Complete (0.8 W3–W6): Workspaces screen to create, rename, retire, reactivate, delete an unused workspace and choose the default, gated by `WORKSPACE_ADMIN_MUTATIONS_ENABLED`; the change-set workflow is always available | — |
| Model administration | Complete: immutable releases, JSON drafts, validation/diff/install/activation workbench | Browser administration acceptance (0.7+) |
| UI foundation | Complete: catalogue selection, typed tables, generic panels, redesigned navigation/collections/inspector/inline editing, automated accessibility and visual-regression gates (UI-07); 0.7 redesign (header application tabs, Live/Drafts/History control, record tree, Filter popover), dark mode and settings menu; WP-9 a11y/visual acceptance passed | — |
| Specialist workflows | Schema 0.6 `mappingGrid` contract, live/draft/revision coverage, target-detail, candidate APIs, atomic replacement and contextual mapping lens with in-context target creation delivered; SC-07 composed acceptance passed | Lazy arbitrary-depth hierarchy/translation specializations 0.8; integration 0.9 |
| Production and model migration | Basic readiness and actionable startup refusal | Production hardening, staged assignments and reviewed historical model migration 0.11; authentication and authorization 0.12 |

Ordinary live saves create neither a change set nor a publication. Publishing a change set applies authored changes
over current live data, preserves unrelated live work and publishes nothing on a touched-record conflict
or divergent touched mutable relation set, or invalid merged graph. Historical derivation is not a direct restore. Publication withdrawal does
not withdraw live data or make the workspace read-only; catalogue retirement is the read-only control.
Change sets and application-definition drafts are different concepts.

The current default/non-default browser gap and disconnected record controls are documented in the
[functionality catalogue](product-functionality/CURRENT_FUNCTIONALITY.md). A component or API present
in code does not establish that a browser user can complete its story.

## Product 0.7 delivery sequence (released 2026-09-25)

1. **Typed `mappingGrid` (WP-2, delivered 2026-09-12):** schema 0.6 with a strict `mappingGrid` view
   contract, discriminated union dispatch, full validation rules and an initial frontend placeholder.
   WP-4 delivered 2026-09-14: cursor-paged batched mapping coverage, exact counts with bounded
   version-bound target details, view-specific typed projections and candidate search in live/draft
   contexts. WP-5 delivered 2026-09-14: atomic mapping replacement with retained identity, typed
   attributes and direction-aware validation. WP-8A/WP-8B and WP-14 now implement the composed UI.
2. **ADR-022 relation-set versions (WP-3, delivered 2026-09-12):** exact-binding relation-set versions
   integrated into all generic relation writes in live and optional-draft contexts. Atomic mapping
   replacement is delivered in WP-5.
3. **ADR-028 draft version selection:** WP-6 backend delivered 2026-09-14: installed-release
   creation, whole-candidate compatibility, atomic audited pin changes and pinned model/metadata
   reads. WP-7 browser version selection and model-context refresh delivered 2026-09-14:
   model-release selector in draft creation, release display on draft cards and detail, informational
   banner and activation refusal when versions differ, version-change action with incompatibility
   diagnostics, model-context refresh after pin change, and dirty-input protection via navigation
   guards. WP-11 delivered 2026-09-15: unsupported-schema diff/compile/activation refusals return structured 422,
   correlation-ID error boundary, API client HTML/non-JSON hardening, compact Modal version-change dialog,
   supported-schema pinned-model loading, shell-aligned workspace error recovery and historical-release
   informational state. Non-retryable pinned-schema limitations do not offer Retry. Focused wide/narrow
   browser evidence is recorded. WP-12 delivered 2026-09-24: explained, copyable Release ID and
   content hash under Technical details; release history compares the recorded predecessor (or a
   labelled installation-order fallback, or an explicit baseline) to the selected release, including
   the active one, while activation readiness stays current-active to candidate.
4. **UI-07 (carried from 0.6, delivered 2026-09-12):** automated accessibility and visual-regression
   gates using the existing Playwright harness with `@axe-core/playwright` and visual comparison
   baselines. Light-theme baselines committed; dark mode and dark baselines followed on 2026-09-24.
5. **Contextual collections (WP-8A/WP-8B/WP-14, delivered 2026-09-15 in `f8e39a8`):** one generic application browser combines collection entry points and runtime
   hierarchy. Views sharing a source type are collection lenses; mapping adds visible server-backed
   coverage state and atomic actions without adding another primary navigation destination. Direct-parent
   scope is URL-backed and valid in live, draft and immutable-revision contexts. ADR-029 records the
   durable terminology and the 0.7/0.8 boundary.

Moving a draft onto a version its content does not already fit, and the accepted historical-model
warning and confirm-or-cancel behavior, belong to the planned 0.11 workspace assignment/migration flow.

See [implementation plan](BASE_0_7_IMPLEMENTATION_PLAN.md), [delivery queue](TODO.md),
[roadmap](ROADMAP.md) and [product acceptance scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md).

### 0.7 plan review boundary — 2026-09-12

This is the historical plan-review boundary. WP-1–WP-3 scopes are frozen and delivered.
WP-1/WP-2 fixes were subsequently committed in `3de2f88`; WP-3 participation and mapping
query review evidence follows below. The plan review established later-package requirements, not foundation
defects or new runtime pass evidence. WP-4/WP-5 add view-specific bounded reads, retained relation
identities and direction-aware mapping validation. WP-6/WP-7 add atomic complete-candidate compatibility
and browser model-context refresh; both are delivered. WP-8A delivers coverage; WP-8B adds mapping actions. WP-9 extends
new-control accessibility/visual evidence and checks independent bindings, differing same-schema
releases, generic-write races and activation/live set conflicts. Confirmed missing foundation behavior
triggers bounded WP-10 work before acceptance. Dark mode and dark baselines were added on 2026-09-24.

### WP-4 delivery and review — 2026-09-14

WP-4 mapping queries and the WP-10A cascade-deletion version fix are committed in `0c459ef`.
Pending WP-3 relation-write participation, draft cleanup/activation and migration test expectations
were committed separately in `022abec`. Both commits together contain the code covered by the final
401-test backend run on SQLite; Ruff passed. WP-4 integration checks cover paging, bounded ambiguous
sets, view-specific projections, draft pins, concurrent reads and stale continuation rejection after
live/draft cascades in both directions. The review found no further confirmed issues.

This was backend query evidence at the WP-4 boundary. Atomic replacement (WP-5) was subsequently
delivered and reviewed; WP-8A/WP-8B and WP-14 browser work is delivered, while composed product 0.7
acceptance (WP-9) remains pending.

### WP-5 acceptance and WP-10B activation hardening — 2026-09-14

WP-5 acceptance now includes an independent allowed binding in live/draft contexts, ownership and
clearing refusals, and overlapping real HTTP generic create/update/delete versus replacement.
WP-10B reproduced activation accepting a new live edge in a mapping set the draft cleared. Activation
now compares complete source/live relation identities and versions in touched mutable, non-ownership
binding sets and refuses divergence before applying rows. Diagnostics identify binding, anchor and
direction, preserve the draft/live graph/revision, and explain safe reapplication under current live
context. Current-live and revision-derived drafts, both directions and unrelated live mapping work
are exercised. API and ADR-022 contracts and the WP-8B consumer handoff are reconciled.

The final follow-up also closes ancestor-scope validation gaps in mapping/generic draft writes,
rejects non-oriented ownership replacement, and rejects empty supplied view identities. Twelve
HTTP regressions exercise these refusals and valid final-graph replacement.

The final implementation gate passed 486 backend tests (including 73 replacement/activation cases),
Ruff, frontend format/lint (zero errors, 12 existing warnings), 164 frontend tests and build. These
are API/integration and component results on SQLite; recorded in the active implementation plan.
WP-8A/WP-8B browser delivery was subsequently composed through WP-14. WP-9 US-M01–M04 acceptance
remains separate; PostgreSQL concurrency is not established.

### WP-8/WP-14 contextual-browser delivery and review — 2026-09-15

The then-uncommitted WP-8 renderer was reviewed as part of WP-14; both were committed in `f8e39a8`.
Mapping coverage and actions now render as a lens of the same source collection as its table views. The application rail presents collection
groups and runtime hierarchy in one model-driven browser. Direct-parent scope, typed field facets and
mapping coverage state are visible and URL-backed; the server applies parent/state filters before
cursor pagination. Live, draft and immutable-revision reads resolve their governing model and data
projection. No renderer branches on the starter application or object-type keys.

The review removed duplicate configured identity fields and corrected mapping-conflict handling so a
steward must inspect the returned current targets before explicitly continuing with a retry. The final
package gate passed 39 backend mapping/OpenAPI tests, 95 frontend component/adapter/routing tests,
Ruff, frontend format, lint (zero errors, 12 configured warnings) and production build. A six-check
real-backend/browser journey covers direct-parent composition, table/mapping lens changes, both
configured directions, live replacement, narrow layout and an axe check. Comprehensive suites and
reviewed visual baselines remain WP-9 build acceptance.

### Frontend redesign and dark mode — 2026-09-24

The Base 0.7 UX pass (`936a70e`) reworked the generic shell and renderers without changing routes,
data contexts, API contracts or the model: applications as header tabs, a segmented Live / Drafts /
History control, a collapsed-by-default record tree, one Filter popover, lens tabs with a scope banner,
a record header with a visible Edit action and a rewritten token stylesheet. Mapping lenses gained a
segmented coverage filter, row-click to map, a candidate radio list, **Save and next** and an explicit
**Remove mapping**. `315e6f7` added a dark token set with a System / Light / Dark choice, the settings
menu and dark accessibility scenarios and baselines, and aligned the Models page. Presentation rules
are in [UI model](UI_MODEL.md); reviewed light and dark baselines are committed.

### WP-10E/F/G — 2026-09-25

- **WP-10E:** timestamp columns use one UTC column type, so SQLite keeps the instant and every
  response carries an explicit offset (server timestamps as well as `dateTime` fields). Decimals read
  back in one form without trailing zeros in every context. The browser's zone-less workaround is
  removed. No local database holds a live `dateTime` value, and offsets lost earlier cannot be
  recovered, so no data migration was added.
- **WP-10F:** a target created from a mapping lens goes to the application the user chooses; every
  application containing the target type is listed, the lens's application is the default, and parent
  choices are limited to that application's types.
- **WP-10G:** the narrow candidate search keeps its height; draft-mismatch and historical-revision
  notices name releases by key and version.

Evidence: the full backend suite (533 passed; run once because the column type affects every
timestamp read), 167 affected frontend component tests, Ruff, frontend format, lint (zero errors, 11
warnings) and build. `test:browser:wp13c` (12 checks) creates, selects and saves a target in both
directions, live and in a draft, and checks the narrow search height and mismatch text.
`test:browser:authoring`, `test:browser:publications` and `test:browser:wp14` pass. The changed
screenshots were inspected at 1440px and 390px. The full frontend suite and the a11y/visual gates
remain WP-9.

## Evidence boundary

The subsequent [WP8 implementation review](../review-notes/wp8-implementation-review-2026-09-08.md)
reviewed the uncommitted diff and corrected confirmed lifecycle/CRUD defects. Its backend, frontend,
migration and installed-wheel evidence is recorded separately; subsequent packages now close WP8.1-A
through WP9, while composed release acceptance remains in WP10.
The follow-up closes SC-04's service boundary: cascade confirmation requires the signed identity from
the exact displayed preview and rejects intervening hierarchy changes without deleting data. Live
deletion also claims active workspace status for the transaction and refuses stored graph edges that
cross workspace boundaries. The frontend adapter carries live or draft confirmation context. The WP9
browser control must show the returned retry message when it becomes reachable.

Prior WP0–WP8 and ADR-026 reports record backend/component/build validation at their own snapshots.
This technical-documentation update ran document/contract/traceability checks only; it did not execute
runtime, browser or migration suites. Prior green totals cannot close the newly identified gaps.
Release acceptance needs the actual evidence specified by WP10, with relevant skips reported as gaps.

## Product correction retained from the ADR-026 retrospective

Earlier lifecycle decisions routed every reference-data edit through a draft and release ceremony,
contradicting continuous maintenance in the product statement. The correction restores live editing
and keeps coordinated data changes optional. Every future gate must ask whether a data owner can
still perform daily work without unnecessary steps. Model definitions, live data and history each
need explicit authority; an appended amendment does not repair contradictory canonical instructions.
Record capability removals and contract reversals for explicit product review before implementing them.

## Source evidence incorporated

The supplied RDM application package declares 3 applications, 23 object types, 27 attribute types, 72
relation types and 55 allowed object-type relations. The accompanying API examples show:

- object-type metadata with features and attribute bindings;
- a custom-overview query that asks for numeric attribute and relation IDs;
- a relation-type catalogue declaring 201 entries, with 20 complete entries in the captured excerpt;
- forward/reverse relation names, orientation and typed relation features; and
- separate runtime retrieval for the Master and Translation applications.

The engine keeps the useful object–attribute–relation separation and configurable applications. It
intentionally replaces numeric integration IDs, unbounded `take: 0` queries and UI-coupled endpoint
configuration with stable keys, explicit schemas, cursor pagination and resource APIs.

## Implemented

- `model/rdm-starter.json`: schema-language 0.7/content-release 0.8.0 model (Base 0.8 S4R2; relations panels declare sort options) with 22 attributes, 9 object
  types, 13 relation types, 16 allowed triples, three applications, table and mapping grid collection
  views and typed detail compositions. Domain
  and Codelist objects can have optional System Value representations without joining the independent
  system containment hierarchy.
- Translation objects support translated name, description and value content, are contained by a
  Translation Group, and have exactly one required target chosen from every explicitly configured
  translatable Master object type. Active Target and Language combinations are unique.
- `backend/app/models/schema.py`: executable model contract with uniqueness, cross-reference and parent
  relation validation.
- `backend/app/engine/model/compiler.py`, `model/diff.py` and `model/compatibility.py`:
  side-effect-free canonical compilation, stable JSON-path diagnostics, key-based structural diff and
  bounded runtime-data compatibility checks exposed through validation and release-diff APIs.
  Compatibility covers object and relation attribute constraints and relation-type-wide cardinality;
  diffs distinguish JSON null from omission and ignore ordering for set-like stable-key memberships.
- `backend/app/engine/model/drafts.py`, `model/releases.py` and the model-management router:
  persisted draft CRUD with optimistic concurrency, side-effect-free draft compilation and atomic,
  idempotent immutable installation serialized across drafts in the supported single-process
  topology. Complete model JSON is excluded from lifecycle audit payloads, and all write routes are
  absent unless model administration mutations are enabled.
- Guarded release activation with runtime-data compatibility diagnostics, dual-token optimistic
  concurrency, old/new release audit identities and hashes, post-commit registry refresh, unhealthy
  readiness on publication failure and startup rejection of configured multi-worker mutation mode.
- `backend/app/models/database.py` and `backend/app/db.py`: immutable model-release metadata plus runtime objects, typed attribute
  values, typed relations, exact-binding relation-set versions and audit events.
- `backend/app/engine/records/attributes.py`: attribute validation, defaults and typed persistence conversion.
- The Base 0.5/pre-WP6 `backend/app/routers` and `backend/app/services` implementation established
  generic object CRUD, search/cursors, concurrency checks, hierarchy maintenance and relation instance
  CRUD (create/read-one/update/delete) with optimistic concurrency, cardinality checks and
  model-declared typed relation attributes. WP6 removed these public mutation routes before their
  workspace-backed replacements existed; corrective WP7 restored their behavior selectively from Git
  history. Engine-maintained parent-containment relations remain read-only through the relation API. The
  established object-scoped attribute-value endpoints
  (`GET`/`POST`/`PATCH`/`DELETE` on `/objects/{type}/{id}/attributes/{attributeTypeKey}`) set, read,
  update and delete single stored values with the same validation, uniqueness and object-version
  concurrency as object writes. Standalone reads expose the current object version, and mutations
  atomically claim that version before writing; `backend/app/main.py` contains application assembly
  only.
- Git history retains workspace-scoped attribute uniqueness and transactional object deletion with
  dependency preview/cascade behavior. WP7 restored those generic semantics in the selected workspace
  draft without restoring rejected WP4 lifecycle. ADR-026 also restores these semantics for live writes.
- `backend/app/migrations`: versioned Alembic database migrations are the single source of schema truth;
  the initial migration provisions new databases and upgrades existing ones, and startup runs only
  `alembic upgrade head`. The environment-aware `app.cli.database_upgrade` command and startup
  boundary turn failures into actionable, credential-safe operator messages without tracebacks. The
  WP4 migration recovers only recognized empty SQLite DDL from an interrupted attempt and refuses
  unsafe cleanup. Startup regression coverage now exercises clean boot, restart, preceding-revision
  upgrade, interrupted-DDL recovery and maintenance-mode refusal against real temporary databases.
- `frontend/src`: model-generated application/view navigation, searchable runtime explorer, stable
  workspace-explicit routes, view and panel component registries, URL-backed searchable/filterable/
  sortable cursor-paged collections, composable object details and cursor-paged audit history.
  Complete workspace lifecycle UI with live CRUD, optional drafts, newest-first immutable history,
  historical draft sources, truthful publication withdrawal and conflict reconciliation. Frontend
  redesign (UI-01–UI-06) delivers compact navigation, focused collections, record inspector, inline
  field editing, resizable panels and refined draft presentation. Failed collection and lookup reads
  remain retryable; genuinely empty relationship/translation collections render as empty states;
  engine-maintained containment edges remain read-only.
- The global model workbench provides release inspection and structured model summaries in read-only
  deployments, and capability-gated JSON draft, validation, diff, installation and activation flows in
  the supported model-administration topology.
- Tests cover model validation and a Domain → Codelist containment flow including the generated typed
  relation, search/cursor behavior, update concurrency and deletion behavior. Composition tests mutate
  panel order, visibility, fields and relation-table configuration without renderer changes. Frontend
  unit tests (Vitest + Testing Library) exercise the model helpers and generic renderers with two
  object types. Frontend adapter and helper tests also cover typed field conversion, structured API
  errors, cross-application lookup queries and incoming/outgoing relationship derivation.

## Important design decisions

- Global attribute definitions and object-type bindings are separate.
- Relation definitions and permitted object-type triples are separate.
- Containment stores both an indexed parent ID and a semantic typed relation, updated atomically.
- Attribute values use typed columns rather than a single string or opaque JSON value.
- Model releases are immutable; a changed definition requires a new release key/version.
- Vendor exports and their numeric IDs are source research, not distributable runtime dependencies.

See `docs/DECISIONS.md` for the durable decisions and `AGENTS.md` for coding invariants.

## Remaining limitations

- Automated accessibility gates (`npm run test:a11y`) and visual-regression gates
  (`npm run test:visual`) are delivered. No violation is allowlisted: WP1-001 was fixed on
  2026-09-24 and WP1-002 by Base 0.8 S5 (its exception was removed in S7). Light baselines cover the core
  page types and dark baselines a representative subset; the accessibility gate runs core pages
  and the settings menu in both themes.
- Schema 0.6 supports strict table and `mappingGrid` collection lenses. Exact-binding relation-set
  versions are integrated into all generic relation writes; coverage, target details, candidate
  search and atomic replacement are delivered with the contextual mapping lens (WP-8/WP-14). Base 0.7
  limits contextual hierarchy queries to direct-parent scope. Lazy arbitrary-depth traversal and
  specialist translation/tree renderers follow the 0.8 roadmap; top-level `form`, `dashboard` and
  `tree` are not implemented renderers.
- Imports/exports and webhooks remain planned (0.9); the
  model-aware query, `asOf`, inline and background object batches with upsert, and the change feed
  read are delivered.
  No synchronous collection has an undocumented unlimited mode.
- The model workbench remains JSON-centred; the structured editor and spreadsheet onboarding are 0.10
  work ([MODEL_AUTHORING.md](MODEL_AUTHORING.md)), changes to released structure and extensions 1.0.
- Multi-writer uniqueness hardening, PostgreSQL performance, authenticated access, actor attribution,
  observability, backup/restore rehearsal and multi-node model propagation remain production work.
- The version serving live data is chosen globally today. Per-workspace migration/assignment, moving
  a draft onto a version its content does not fit, and confirmed potential-loss historical model
  changes require 0.11 and supported parser/runtime versions. A draft can work under a compatible
  version the user chooses (ADR-028; WP-6 backend, WP-7 browser). A draft on a replaced version can be read, edited and discarded,
  but activation still requires agreement with the active model.
- The starter remains representative rather than a one-to-one reproduction of the source export.

## Historical delivery record

Base 0.5 delivered runtime model selection, model compilation/diff/compatibility, versioned drafts,
immutable install, guarded activation, bounded query/audit improvements and the JSON workbench.
Base 0.6 WP1–WP3 delivered UI primitives, workspace catalogue and typed tables. WP4's individual-object
publication design was rejected before release and removed through the corrective WP6 migration;
WP5 refroze workspace scope, WP7 restored generic CRUD and WP8 implemented lifecycle services.
ADR-026 then restored direct live data and delta merge. WP8.1-A–C subsequently closed the remaining
backend authority, draft-source and history/retirement corrections; WP9 completed the isolated
browser journeys; WP10 validated the composed product. The frontend redesign (UI-01–UI-06) delivered
compact navigation, focused collections, record inspector, inline field editing, resizable panels
and refined draft presentation. UI-07 was carried into early 0.7.
UI-07 (automated accessibility and visual-regression gates) was delivered in early 0.7 (2026-09-12).
WP-2 (schema 0.6 `mappingGrid` view contract) was delivered 2026-09-12: discriminated union dispatch,
full validation rules, starter model 0.7.0 with two mapping grid views, and the initial frontend
placeholder later replaced by WP-8/WP-14. WP-3 (relation-set version persistence) was delivered 2026-09-12: `relation_set_versions`
table with lazy row creation, integrated into all six generic relation mutation paths (live and draft),
draft deletion cascade and activation merge. The earlier plans and changelog preserve delivery details;
do not rebuild rejected object lifecycle.

## Coding-agent handoff

Read `AGENTS.md`, the product stories/scenarios, ADR-027, `ROADMAP.md`, `API.md` and `TODO.md`.
Base 0.7 is released (2026-09-25): WP-1–WP-9, WP-10A–K, WP-11, WP-12, WP-13A/B/C and WP-14, plus the
2026-09-24 frontend redesign and dark mode. WP-13A's [coverage map](testing/COVERAGE_MAP.md), WP-13B's
[execution guide](testing/EXECUTION_GUIDE.md) and WP-13C's [UI acceptance](testing/UI_ACCEPTANCE.md)
supply the audited selections. **0.8 in progress**: Tracks S and W are delivered; next are the
Relation matrix and Hierarchy editor milestones, P2 and R1
([plan](BASE_0_8_IMPLEMENTATION_PLAN.md), [roadmap](ROADMAP.md)).
Use one implementation owner per slice, focused verification and appropriate review. Do not commit
unless explicitly requested. Summarize each completed batch while work continues so scope can be
corrected before the entire task finishes.

Use the focused work-package checks in `AGENTS.md`; expand for actual shared-boundary risk.
Run startup/migration and other named boundary checks only where relevant; comprehensive suites
and browser gates belong to WP-9. WP-13 supplies audited selections and UI acceptance guidance.
Report evidence and limits; no documentation change counts as a runtime fix.
