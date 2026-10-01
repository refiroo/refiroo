# Delivery roadmap

This roadmap sequences product outcomes rather than isolated screens or endpoints. Each milestone stays
model-driven, exercises at least two object or relation configurations, preserves typed values and
optimistic concurrency, and keeps public collections cursor-paged.

The release train is 0.6 for daily live operations and optional coordinated design, 0.7 for core mapping, 0.8 for the relation matrix
(translations among its uses) and hierarchy editing, 0.9 for integration APIs, 0.10 for model authoring and spreadsheet onboarding (one editor for the
model and the import mapping, ADR-035), 0.11 for production hardening and staged workspace model rollout,
0.12 for security (authentication and authorization across the backend, frontend and APIs), and 1.0 for
migration-class model changes, protected publishing and extensions.

## Current development baseline — Base 0.8 released, Base 0.9 next

Base 0.8 is released (2026-09-29): collections at any size (ADR-030), one name per concept and
capability boundaries (ADR-031), the relation matrix (ADR-033), the hierarchy editor with drag and
drop, the change set review, and hierarchy restructuring with a preview and history as the way back
(ADR-034), on schema language 0.7. Next is 0.9, integration-grade APIs. Its first packages (Q1–Q4,
C1, V1, B1, B2) are delivered. Before F1, the interim release
[0.9.0-alpha.1](#interim-release-090-alpha1--postgresql-runtime) moves the engine to PostgreSQL only,
with a test harness that seeds once and runs in parallel ([TEST_HARNESS_PLAN](TEST_HARNESS_PLAN.md)).

Base 0.5 delivered the operational and model-release foundation. Base 0.7 is released (2026-09-25):
core mapping as a lens of one contextual application browser, schema 0.6 `mappingGrid` views,
ADR-022 relation-set concurrency and change sets on a chosen model release (ADR-028). It builds on
Base 0.6, released 2026-09-11:

- Daily live operations: generic object, field, parent, relation and translation CRUD without a draft
- Optional coordinated design: change sets, validation, delta-merge activation over live content
- Immutable newest-first history with pinned-model reads and historical draft sources
- Truthful publication withdrawal (designation only; live data and history remain accessible)
- Complete browser journeys (WP9) with real-backend evidence for two configured object types
- Composed release validation (WP10) including keyboard/focus/narrow-layout and migration/packaging
- Frontend redesign (UI-01–UI-06): compact navigation, focused collections, record inspector, inline
  field editing, resizable panels, display preferences and refined draft presentation
Integration-scale operations, authentication and distributed activation are not present.

## Base 0.5 — Operational base and model lifecycle foundation (complete)

### Product outcome

A steward can manage runtime data in an explicit workspace, and a model administrator can validate,
compare, install and activate immutable model releases through the guarded JSON workbench.

### Exit gate achieved

- Each request observes one database-selected immutable model release.
- Validation and compilation are side-effect-free; installed releases are immutable.
- Activation is compatibility-checked, atomic and concurrency-protected.
- Runtime collections and expansions are bounded and cursor-paged.
- Model-admin mutation is capability-gated and the supported topology is explicit.
- Backend/frontend tests, lint, build, migration and packaging validation pass.

The completed handoff is [`BASE_0_5_IMPLEMENTATION_PLAN.md`](BASE_0_5_IMPLEMENTATION_PLAN.md).

## Product release 0.6 — Daily live operations and optional coordinated design (complete)

Released 2026-09-11. Implementation: [`BASE_0_6_IMPLEMENTATION_PLAN.md`](BASE_0_6_IMPLEMENTATION_PLAN.md).

### Product outcome

A steward can select a known workspace, find records with typed filters and sorts, and maintain live
records, fields, parents, relationships and translations without a draft. For coordinated changes,
the steward may choose a change set, validate it and activate all its changes together while
preserving unrelated live work. History distinguishes the source of a draft from the publication
superseded at activation.

Product traceability: US-D01–D14, US-W01–W08, US-L01–L02, US-P06 and US-U01;
SC-01–SC-06, SC-08 and the existing-workbench part of SC-12. Source and outcome definitions live in
[product functionality](product-functionality/README.md).

### Delivery record

WP1–WP3 delivered the UI foundation, workspace catalogue and typed tables. WP4's per-object publication
boundary was rejected and removed through the corrective WP6 migration. WP5 refroze workspace scope,
WP7 restored generic CRUD and WP8 implemented lifecycle orchestration. ADR-026 restored direct live
writes and delta merge. WP8.1-A–C closed authority, draft-source and history/retirement corrections.
WP9 completed browser journeys for live CRUD, optional drafts, immutable history, historical draft
sources and truthful publication withdrawal. WP10 validated the composed product. The frontend redesign
(UI-01–UI-06) delivered compact navigation, focused collections, record inspector, inline field editing,
resizable panels and refined draft presentation.

## Product release 0.7 — Core mapping and contextual collection workspace (complete)

Released 2026-09-25. Implementation: [`BASE_0_7_IMPLEMENTATION_PLAN.md`](BASE_0_7_IMPLEMENTATION_PLAN.md).

### Product outcome

A steward can enter a model-defined application through one browser, establish the collection's
governing context and review or maintain records through applicable configured lenses. Mapping
coverage and atomic replacement are available as a lens without multiplying global table destinations
or navigating low-level relation screens.

### Delivery scope

1. Introduce schema 0.6 with a strict `mappingGrid` branch; reject containment and required ownership
   bindings as independently mutable mappings. **(WP-2, delivered 2026-09-12.)**
2. Cursor-paged batched mapping rows with mapped, unmapped and ambiguous states, exact target counts,
   bounded version-bound target details and view-specific candidate search in live/draft contexts.
   **(WP-4, delivered 2026-09-14.)**
3. Implement ADR-022 exact-binding relation-set versions across mapping and generic relation writes.
   **(WP-3, delivered 2026-09-12.)**
4. Provide atomic replacement with zero or one target where the binding permits it, directly live
   or in an explicitly selected change set, with recoverable conflict context.
   **(WP-5, delivered and reviewed 2026-09-14.)** Atomic source-set claims and draft aggregate
   tokens protect saves; WP-10B refuses divergent touched live mapping sets before draft activation.
5. Reuse ordinary record creation in the selected context when target creation is allowed; target
   creation must not silently change the mapping, and draft activation remains explicit.
6. Audit mapping transitions and underlying relation changes. **(WP-5, delivered 2026-09-14.)**
7. Prove the contract and renderer with two relation bindings whose types, direction and labels differ.
   **Backend independent-binding isolation and overlapping generic writes are covered by WP-5;
   WP-9 (2026-09-25) adds the composed browser evidence with an independent binding and its own lens.**
8. Let a change set work under a version the user chooses, so one draft prepares the schema 0.6
   release while another stays on the version serving live data. Draft reads, writes and validation
   use the version chosen for that draft instead of the global selection (ADR-028; US-W09, SC-15).
   **(WP-6 backend delivered 2026-09-14; WP-7 browser delivered 2026-09-14.)**
9. Keep ordinary activation unchanged: a draft activates only once its version matches the active
   release, which the existing guarded release-activation path already establishes. Nothing activates
   or moves a draft onto another version while that version differs from the active release. Once the
   new release serves live data, the remaining draft is either thrown away — which needs no model
   agreement — or explicitly moved onto the new release where its content already fits it.
10. UI-07 (carried from 0.6, delivered 2026-09-12): automated accessibility and visual-regression gates
    using the existing Playwright harness with `@axe-core/playwright` and visual comparison baselines.
    Light-theme baselines committed; dark baselines followed with dark mode (2026-09-24).

11. Keep WP-1–WP-3 frozen. Later packages add view-specific bounded mapping reads, retained relation
    identities, direction-aware constraints and atomic whole-candidate draft compatibility checks.
12. Deliver mapping coverage in WP-8A and actions in WP-8B. Extend new-control accessibility/visual
    evidence and composed race/isolation scenarios in WP-9. Confirmed foundation gaps trigger bounded
    WP-10 slices before release acceptance; no speculative foundation changes are scheduled. WP-10A
    cascade invalidation and WP-10B activation set-conflict hardening are delivered on SQLite.
    PostgreSQL concurrency and the mapping browser journeys remain outside this backend evidence.
13. WP-11 (delivered 2026-09-15): distinguish unsupported-schema refusals from corrupt JSON in release
    diff/compile/activation (structured 422), correlation-ID error boundary, API client HTML/non-JSON
    hardening, compact Modal version-change dialog, supported-schema pinned-model loading, retry-aware
    shell-aligned workspace errors and historical-release informational state. WP-12 (delivered
    2026-09-24) adds release identity details and earlier-to-selected release history comparison.
14. WP-14, delivered and committed 2026-09-15, normalizes the
    administrative UI after review of the WP-8A/WP-8B renderer:
    replace the hierarchy/views navigation switch with one application browser, group existing schema
    0.5/0.6 views by source object type as collection lenses, expose visible typed/scope/state facets,
    and add cursor-bound parent/state filtering to mapping coverage. Preserve existing model releases
    and generic renderer semantics; arbitrary-depth hierarchy work remains 0.8.

15. WP-9 (passed 2026-09-25): composed SC-07/SC-15 acceptance and the full build gate. Residual gaps
    (record UUIDs in diagnostics, SQLite-only concurrency) are recorded in the plan.

The [0.7 implementation plan](BASE_0_7_IMPLEMENTATION_PLAN.md) records detailed acceptance criteria
and evidence; [API.md](API.md) documents the delivered endpoints.


### Validation improvement within 0.7

WP-13 delivers a prioritised contract-coverage map, measured affected-area test commands and focused
UI/browser acceptance using the existing design patterns. It preserves distinct regression protection
while reducing redundant execution. All slices close before WP-9; comprehensive suites remain build
acceptance gates rather than per-package requirements. See the [implementation plan](BASE_0_7_IMPLEMENTATION_PLAN.md).

### Exit gate

- Mapping pages and candidates are bounded and avoid per-row requests.
- Concurrent replacement cannot lose a valid mapping or replace another binding's edges.
- Unmapped and ambiguous rows have the same set-level concurrency protection.
- Generic relation writes and mapping writes in each supported content context enforce the same
  relation-set concurrency boundary. A draft cannot be used to bypass live conflict detection.
- Schema 0.6 is explicitly dispatched and the schema 0.5 transition has a documented reset or
  migration path appropriate to the pre-production compatibility policy.
- A draft may be created against, or explicitly moved onto, an installed release the deployment can
  parse and support; unavailable, corrupt or unsupported targets are refused with the existing
  pinned-model error codes, and choosing one never forces a change through or switches the version
  used across the product.
- Choosing a version changes only that draft. Live data, immutable history, other drafts and other
  workspaces are unchanged, and nothing activates a draft whose version differs from the active
  release.
- One application browser exposes contextual collections and records for arbitrary configured
  applications. Table and mapping declarations over one source type are lenses of one collection,
  not duplicate primary navigation destinations.
- Direct-parent scope, declared typed filters and mapping coverage state are visible and server-side;
  their cursor continuations cannot be reused under another query context.

## Product release 0.8 — Relation matrix and hierarchy editor (complete)

The two independently gated milestones may ship together, but neither may weaken live, change-set
or publication semantics. Track S comes first because both milestones browse large, model-defined collections.

### Track S — Scalable browsing

Every collection surface stays bounded for any model: continuous scrolling in both directions with
prefetch and a bounded window, totals, jumps by scrollbar, page number, start, end or value, draft and history reads in the
database, relation search and sort, and a sidebar tree that loads by parent
([ADR-030](DECISIONS.md#adr-030--cursor-and-position-paging-with-continuous-scrolling),
[plan](BASE_0_8_IMPLEMENTATION_PLAN.md)).

Exit: a generated model with 100,000 records scrolls both ways with flat memory in live, draft and
history contexts within recorded budgets, and search answers within budget in every context through a
trigram index over text values (S8). Attribute and ancestor sorts over very large parents are a recorded exception until 0.11.

### Track W — Workspace terminology and capability boundaries

One name per concept (workspace, live, change set, publication, model draft, model release) in
every layer, and one capability gate per operation group: workspace administration, change-set
workflow and model administration
([ADR-031](DECISIONS.md#adr-031--workspace-terminology-and-deployment-capability-boundaries),
[plan](BASE_0_8_IMPLEMENTATION_PLAN.md#track-w--workspace-terminology-and-capability-boundaries)).

Exit: no old name remains; disabling workspace administration leaves change sets working; a second
workspace can be created, selected, made default and retired in the browser.

### Milestone A — Relation matrix

A steward works through a collection against the records of an ancestor type — values by language,
values by system — sees missing and conflicting cells across the whole list and acts in the cell
without manually traversing containment. The capability is generic; the starter's translation and
system views are configurations of it.

1. Define a typed `relationMatrix` view from model-declared row, column and cell object types, the
   binding that joins rows to cell records (either direction, any cardinality) and a closed set of
   cell actions.
2. Add a bounded matrix query with cell states rather than one request per cell.
3. Create, edit, link or unlink a cell's record live, or in an explicitly selected change set, with
   the required parent and relationships in one valid operation.
4. Keep ordinary corrections direct; publish a change set only for deliberately staged changes. Model
   changes retain their separate release lifecycle.
5. Where the binding declares a uniqueness scope, enforce it during live writes and change-set
   validation, and recheck the final merged graph when the change set is published.

Exit: empty cells and cells present only in earlier publications are distinguishable; conflicts
preserve entered content and any selected change set; the matrix remains bounded for representative
row and column volumes; the translation and mapping configurations both work.

### Milestone B — Hierarchy editor

A steward browses and maintains deep model-defined hierarchies through lazy loading.

1. Define a strict typed `tree` view contract.
2. Add cursor-paged root/child traversal with bounded path context.
3. Create children and perform rename, model-defined availability or parent changes live, with an
   explicitly selected change set as the coordinated alternative.
4. Validate cycles and update `parent_object_id` plus the typed edge atomically in the chosen context;
   staged changes are revalidated with the merged live graph when published.
5. Exercise mixed-type containment and recursive self-hierarchy configurations.
6. Move by drag and drop with mouse or pen (B5, added in the Milestone B review): onto a node, into a
   gap between rows or onto a type heading. Drops are accepted or refused by the model's containment
   rules, the target glows green or red with the reason, and the move is confirmed in the same dialog
   as Move to…. A record of a tree root type can also be moved to the top level, by either path
   (B5b, D36). Touch drag follows in 0.11 (D35).

Exit: traversal is bounded; reparenting changes both representations or neither; keyboard navigation
and focus/loading/error behavior are covered; a drop never writes without the move dialog's
confirmation, and a refused target never writes.

### Milestone C — Structure refactoring

Added 2026-09-28; part of 0.8.0 (D43). The design is
[ADR-034](DECISIONS.md#adr-034--a-records-type-can-change-derived-mapping-preview-and-apply-history-as-the-way-back)
(C0, 2026-09-29). A steward reshapes a hierarchy without recreating records.
Moving a record to a place where only another type is allowed changes its type, and its descendants
follow level by level. Named refactorings (change type, insert a level, remove a level, change the
type of all records of one type under a record) run as a preview, then an apply, in a change set.
Nothing is declared in the model: possible types and the attribute mapping are derived from it, and the
user confirms them. Values a new type cannot hold stay in the record's history and are offered back
later ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-c--structure-refactoring)).

Exit: the journey passes on two models; identities, history and permitted relationships survive a type
change; nothing is lost without being shown in the preview; nothing names a type or application.

C0–C5 delivered 2026-09-29; the journey is accepted on the starter and generated models by
`test:browser:c5` (SC-17, US-H03). R1b and R2 passed together on 2026-09-29, and 0.8.0 is released (D43).

## Interim release 0.9.0-alpha.1 — PostgreSQL runtime

Planned 2026-10-01 in [POSTGRESQL_RUNTIME_PLAN.md](POSTGRESQL_RUNTIME_PLAN.md); inserted in the 0.9
queue after B2, before F1. It is a pre-release of 0.9: `main` already carries delivered 0.9
packages, so a 0.8.x patch would misdescribe it (PG-D1).

### Product outcome

The engine runs on PostgreSQL only, with real row-level concurrency. Writes in different workspaces
run in parallel, and writes in one workspace serialize without losing an invariant; a background job
leaves other writes free. Tests run on PostgreSQL from seeded databases built once and reused, and
existing development databases carry over. API, model contract and UI are unchanged.

### Delivery scope

- PostgreSQL as the only runtime and test database. SQLite is removed with its dialect branches,
  settings and migrations, one baseline revision replaces the migration history, and PostgreSQL
  runs from installed binaries only while needed, never as a service (PG1, PG2)
- A test harness whose seeded databases are built once and reused until the schema, model or seed
  code changes, with parallel runs (PG1 with H1; H2, H3)
- `pg_trgm` search indexes and PostgreSQL forms of the relation matrix's change set walk and stored
  state filter (PG2), brought forward from 0.11
- The per-workspace write lock (the lock F1's feed position needs), with every invariant checked in
  code tested under two racing writers (PG3); single-node multi-writer uniqueness, brought forward
  from 0.11
- A one-off copy of existing SQLite databases (PG4)
- Every volume budget re-measured on PostgreSQL (PG5)

### Exit gate

- The full backend suite, the frontend suites and the browser runners pass against PostgreSQL. No
  SQLite or dialect branch remains outside history.
- A second test run seeds nothing; a package's local checks take no longer than on SQLite.
- Two writers racing in one workspace never break an invariant. Two workspaces are written in
  parallel. A cancel request never waits for a job's chunk (0.9 D28).
- The OpenAPI lock is unchanged, and every volume budget is restated on PostgreSQL.

## Product release 0.9 — Integration-grade APIs

### Product outcome

External systems exchange and synchronize reference data through stable, resumable contracts rather
than UI endpoints or undocumented limits.

### Delivery scope

1. Advanced model-aware queries beyond configured daily-use table filters.
2. Model-driven effective dates and `asOf` behavior where explicitly configured.
3. Bounded live bulk creation, update and upsert, with an explicit optional staging mode, per-item
   outcomes, documented failure policy and safe retry/idempotency semantics, keyed by stable model
   keys or declared unique attributes so recurring source feeds use the same contract as one-off
   loads ([inbound flow](COMPOSABLE_DOMAINS.md#inbound-flow)).
4. Asynchronous import/export with validation previews and resumable job status.
5. Ordered change feed and retryable webhooks. Model-declared consumer events, subscriptions and
   webhook delivery are specified in [CONSUMER_API.md](CONSUMER_API.md#change-events-and-webhooks).
6. Bounded bulk relation/mapping operations with explicit concurrency semantics.
7. Position (page-number) paging alongside cursors, with bidirectional cursors, totals and seek by
   value, arrives in 0.8 Track S (ADR-030).
8. Cross-type object lookup (`GET /objects` over built-in fields) and a general relation edge list
   with publication context, moved from 0.8 (Base 0.8 plan P1, P3, D20).
9. Consumer API ([CONSUMER_API.md](CONSUMER_API.md)): a read-only tier for systems that use reference
   data. Model-declared definitions give XREF lookup (search, resolve, get), batch resolve, crosswalk
   between representations, `asOf` reads, lists (with or without a parent), publication discovery and
   one shared object shape across object types, with a contract version independent of the management API. The
   production gateway XREF and list APIs are the functional baseline.
10. Built-in API reference with [Scalar](https://github.com/scalar/scalar) (MIT) at `/docs`, replacing
    FastAPI's default Swagger UI and ReDoc. One page lists the management API and every active
    consumer API contract version as separate OpenAPI sources. The Scalar standalone script is pinned
    and bundled with the engine by default, so the page works without internet access; a setting
    switches to loading it from a CDN instead. The page route stays outside the OpenAPI document, so
    the OpenAPI locks are unaffected. Authentication in the "try it" console follows in 0.12.

Security is not part of 0.9: its APIs are unauthenticated like the management API, and no 0.9
contract uses API keys or puts a credential in a URL. The 0.12 security release covers them
([CONSUMER_API.md](CONSUMER_API.md#security-012)).

### Exit gate

- Every collection and job result is bounded or resumable.
- Partial failures and lifecycle stages are machine-readable.
- Bulk contracts are first-class services, not loops over UI calls.
- The built-in API reference serves every published OpenAPI document with the bundled script and no
  outbound network access, and with the CDN script when so configured.
- A consumer API definition alone reproduces the reference XREF and list responses (CONSUMER_API.md
  C8), with no runtime branch on object-type or relation keys.

## Product release 0.10 — Model authoring and spreadsheet onboarding

### Product outcome

An administrator turns reference data that arrives in spreadsheets into a working application without
writing a model file or an import script. One editor proposes a model and an import mapping from the
uploaded workbook, lets the administrator rename, remap and reorganize both freely with the effect on the
real rows shown after every change, and saves the mapping so the next version of the workbook loads as a
reviewed upsert. Opened without a workbook, the same editor is the structured model designer. Design:
[MODEL_AUTHORING.md](MODEL_AUTHORING.md) (ADR-035); packages and sequence: the provisional
[Base 0.10 plan](BASE_0_10_IMPLEMENTATION_PLAN.md).

### Delivery scope

1. Import profiles: a declarative mapping from sheets and columns to model elements, executed by the
   0.9 import job, with XLSX and several sheets (A1, delivered inside 0.9 Track J).
2. An operation API on model drafts: typed, validated operations with history, undo and version checks;
   additive and draft-only operations (A2).
3. Source profiling and a dry-run summary after every operation (A3).
4. The editor: model pane with the relationship matrix, a preview rendered by the generic renderers,
   and layout editing of views and panels (A4); source and mapping panes, saved and re-run profiles
   (A5). Every drag has a keyboard path.
5. Inference over the table patterns of the catalogue, extending an existing model or starting a new
   application (A6).
6. Model-description sheets and matching across files (A7), and list blocks in sheets laid out for
   reading (A8); both may move to a 0.10.x release.

Changes to released structure (key renames, splits, merges, cardinality) are shown with their impact
and blocked; they are enabled in 1.0 on the 0.11 migration boundary.

### Exit gate

- Two differently shaped workbooks each become an installed application and a reviewed change set
  without writing JSON or code, and every inference was changeable before loading.
- The next version of a workbook loads through its saved profile and the change set review shows only
  its differences.
- Renaming, moving, splitting and merging keep profiles valid; the dry run reflects each operation.
- The editor passes the accessibility and visual gates at desktop and narrow widths.
- No runtime or editor branch on an application, object-type, attribute or relation key.

## Product release 0.11 — Production hardening and staged model rollout

### Product outcome

The engine runs safely with multiple writers and nodes, and workspaces can be migrated between
immutable model releases in controlled stages. Authentication and authorization follow in 0.12.

### Delivery scope

- Production-scale PostgreSQL performance on the runtime 0.9.0-alpha.1 established: the volume
  fixture at full scale, connection pool sizing, and model-derived indexes, including unique checks
  on non-text values (the value indexes cover text only)
- Precomputed sort keys, so attribute and ancestor sorts over very large parents meet the list
  budget (deferred from 0.8, D26)
- Database constraints as a second line behind the per-workspace write lock, for writes that bypass
  the write unit, decided on evidence. Single-node multi-writer uniqueness is delivered in
  0.9.0-alpha.1
- Metrics, structured logging, health/readiness, backup and restore rehearsal (`pg_dump`)
- Multi-node and multi-process operation: immutable-snapshot propagation across processes
  (`WEB_CONCURRENCY` above 1), and the job worker on several nodes through its lease (0.9 B2)
- Executable workspace-scoped data migration plans
- Touch drag in the tree lens (deferred from 0.8 B5, D35): long-press drag that does not conflict with
  scrolling or with opening a record, tested on iOS Safari and Android Chrome
- Historical-draft model replacement targeting one workspace and a named installed immutable release
  (normally the historical pin), with a preview of incompatibilities and potential data loss,
  confirmation bound to the exact reviewed versions or cancel, and atomic model/data application;
  this is the accepted GAP-02 extension, not an override of ordinary activation
- Workspace-scoped model-release assignment: resolve workspace before its immutable snapshot, migrate
  its data, then atomically switch its release
- Moving a draft onto a release its content does not fit: reuse the 0.11 conversion machinery against
  that draft and the live data under it, preview the conversions and any loss of draft-authored
  content, and apply only on confirmation of the exact reviewed draft and release versions, or cancel;
  once the new release serves live data, a draft still on the replaced release is explicitly moved or
  thrown away and is never moved onto another release on its own
- Explicit mixed-schema conversion rules and a bounded supported schema-version window
- First-public-release licensing, contribution/security policies and compatibility commitment

### Exit gate

- Concurrency and uniqueness invariants hold with several processes and nodes on one database, in
  production-like tests at full volume (single-process multi-writer is 0.9.0-alpha.1's gate).
- A tree node can be moved by touch drag on a phone without breaking scrolling or opening a record,
  confirmed in the same move dialog as with a mouse (D35).
- Workspace migration, release switch and operator backup recovery are rehearsed without mixed-model
  requests. Historical change sets are not direct dataset restore operations.
- Confirmed historical migration validates transformed data, preserves immutable history, affects only
  the selected workspace assignment, and changes nothing on cancel, stale review or execution failure.
- Supported schema versions and their migration/removal dates are published.
- Moving a draft onto a release its content does not fit cannot be forced through: the target must be
  installed and supported by the deployment, the conversion is previewed and confirmed against the
  exact reviewed versions or cancelled, and a failed re-check changes nothing.
- Moving a draft changes only that draft. Live data, immutable history, other drafts and other
  workspace assignments are unchanged on the move, on cancel, on a stale review, on an unsupported
  target and on a failed re-check.

Running two model versions side by side is a way to roll a change out gradually, not a way around
compatibility: every version that can be chosen must have a parser and data path the same deployment
supports, and content written under one version cannot be served under another until it is checked or
converted. Activating is never just choosing a version: a draft activates only once its version
matches the active release, which the existing guarded release-activation path establishes.

## Product release 0.12 — Security, authentication and authorization

### Product outcome

Once every earlier capability works, one release secures the backend, the frontend and the consumer
APIs together: every caller is authenticated, every operation is authorized, and changes are attributed
to a proven identity.

### Delivery scope

- OAuth 2.0 provided by the engine, issuing JWT access tokens, for the management API, the frontend and
  the consumer APIs. No API keys, and no credential in a URL
- Authorization for application, object-type and operation scopes, and per consumer API definition for
  OAuth clients
- HMAC signing keys for webhook subscriptions, shown once and rotatable; the `RDM-Signature` header
  added to deliveries (CONSUMER_API C-D12)
- UI administration of OAuth clients and their access, and of webhook subscriptions and their keys
- Audit identity: changes record the authenticated actor
- Protected model and workspace administration, replacing the default-enabled workspace mutation
  posture; deployment capability flags stay as defence in depth (ADR-031)
- Authentication in the API reference "try it" console

### Exit gate

- Authorization cannot be bypassed through administrative, bulk, job, feed or consumer APIs.
- Administrative, ordinary and bulk paths enforce the same authenticated scope (US-S01).
- Webhook receivers can verify every delivery, and a rotated key stops verifying.

## Product release 1.0 — Self-service model authoring and extensions

### Product outcome

An authorized administrator evolves released applications with the 0.10 editor, including changes that
need a migration, and reuses proven definitions.

### Delivery scope

- Migration-class operations in the 0.10 editor (key renames, splits, merges, cardinality changes on
  released structure), each with its impact preview, on the 0.11 migration boundary
- Read-only dependency visualization where it materially improves comprehension
- Protected publish, activation and rollback workflows built on the 0.11 migration boundary
- Extension packaging and reusable model modules after two concrete reuse cases

### Exit gate

- Published releases remain immutable and reproducible.
- Unsafe model changes remain blocked until an explicit migration succeeds.
- Extensions cannot introduce application-specific branches into the runtime.

## Product traceability for later milestones

| Milestone | Stories | Acceptance scenarios | Dependency to preserve |
| --- | --- | --- | --- |
| 0.7 mapping | US-M01–M04, US-W09 | SC-07, SC-15 | Complete generic record/relationship flows; live and draft conflict protection |
| 0.8 translation/hierarchy | US-L03–L04, US-H01–H02 | SC-09, separately gated workflows | Generic translation and parent editing remain usable |
| 0.9 integration | US-I03–I09 | SC-10–SC-11 and advanced-query extension | Same validation and workspace rules as individual writes |
| 0.10 authoring | US-P05 (structured editor), US-P09, US-P10 | SC-12 through the editor; MODEL_AUTHORING exit gate | JSON workbench, model lifecycle, 0.9 import job and change set review unchanged |
| 0.11 production | US-O03–O04, US-O06, US-P07 | SC-13 | Measured recovery and consistent model selection |
| 0.12 security | US-S01, US-O05 | SC-13 identity attribution | Same authenticated scope on every path; existing capability flags retained |
| 1.0 authoring | US-P05 (migration operations), US-P08 | SC-12 through structured tools and reuse cases | Existing immutable definitions, validation and release safety |

### Unscheduled

- **Recorded timestamps in drafts and history.** Since 0.7 (WP-10K), drafts and history report `createdAt`
  and `updatedAt` as not recorded and refuse queries on them. Recording them would add timestamp columns
  to draft, draft-base and revision rows (captured values keep the live timestamps; draft writes set
  their own). That needs a migration and a decision on what `updatedAt` means after activation (draft
  edit time or publication time). Not assigned to a release.
- **Post-1.0 direction: composable domains.** MDM-lite and small, specific product catalogues are
  modelled on the engine from generic capabilities, never built as domain modules (ADR-032). Nothing
  is scheduled; [COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md) records the admission tests, candidate
  capabilities and the doors current work keeps open (identity redirects, value provenance, derived
  values, redaction within immutable history, keyed inbound upsert, reusable matching and review
  vocabulary, additive value types).
- **Workspace groups as owners of a model history.** A possible later step beyond 0.11's
  workspace-scoped release assignment: a group of workspaces owns one model history, so teams in one
  organisation can release their models independently (with dev/test/prod staged rollout inside a
  group), and workspace keys and release identities become unique per group. It is not a tenancy
  mechanism: hosting is one instance per organisation. Groups separate models, so data in different
  groups cannot relate, which works against reference data being used by other domains. One model with
  several applications stays the default. Consider groups only when a real case needs independent model
  release cycles and can do without relations between the groups; relations across models would then
  be a separate, larger feature. Not assigned to a release.

Earlier milestones are pre-production functionality; 0.11 (hardening) and 0.12 (security) together
are the gate for authenticated shared production operation. Release numbers specify sequence, not dates. Detailed format, query, validity,
recovery and reuse contracts must be recorded before their implementation packages. Unscheduled
research candidates do not become release scope merely by appearing in benchmark notes.

## Cross-cutting release rules

Every milestone follows the repository definition of done:

- Name affected story and scenario IDs before implementation, state the smallest successful flow
  and extend the model only for configurable behavior.
- Compare the completed journey with the previous flow. Explain any added mandatory step or removed
  capability through an explicit product decision; preserve direct daily editing.
- Record API, component and composed-browser evidence separately. No relevant skipped journey may be
  counted as accepted.
- Validate new configuration before consuming it and update metadata persistence when contracts change.
- Preserve typed values, stable public IDs, explicit errors and optimistic concurrency.
- Keep implementation free of branches on starter application, object-type or relation keys.
- Update API, model, architecture, decision, status and roadmap documentation together.
- Run backend tests and Ruff, frontend lint/tests/build, migration/package checks and
  `git diff --check`.

Product and schema-language versions are independent. Before the first stable compatibility
commitment, a schema transition may explicitly reject older schemas when it documents a reset or
migration path. Once a schema version is published as supported for production, removing runtime
support requires a documented compatibility/migration window.

Detailed current-state evidence and the immediate coding handoff live in
[`PROJECT_STATUS.md`](PROJECT_STATUS.md). Durable tradeoffs belong in [`DECISIONS.md`](DECISIONS.md).
