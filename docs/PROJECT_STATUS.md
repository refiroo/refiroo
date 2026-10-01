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
- Background bulk jobs, relation batch items, imports/exports, change feeds and webhooks remain
  planned (0.9); the model-aware query, `asOf` and inline object batches with upsert are delivered.
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
