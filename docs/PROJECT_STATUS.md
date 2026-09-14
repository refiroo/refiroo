# Project status

## Current development baseline — released 2026-09-11

Base 0.5 is the completed operational/model-release foundation. Base 0.6 is released. The starter
model is content release 0.7.0 on schema language 0.6. Next development targets product 0.7 (core
mapping, schema 0.6, draft version selection). WP-1 (accessibility gates), WP-2 (schema 0.6
`mappingGrid` view contract), WP-3 (relation-set version persistence), WP-4 (mapping query APIs),
WP-5 (atomic mapping replacement), WP-6 (backend draft version selection) and WP-7 (browser draft
version selection) are delivered.
Bounded WP-10A cascade invalidation and WP-10B draft-activation mapping-set conflict fixes are delivered.

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
| Optional data drafts | Complete: current-live and historical source selection, shared browser editing, validation and delta merge | — |
| Historical data | Complete: newest-first browser discovery, pinned-model immutable reads and historical draft derivation | — |
| Publication retirement | Complete: truthful browser confirmation removes only the designation while retaining live data/history | — |
| Model administration | Complete: immutable releases, JSON drafts, validation/diff/install/activation workbench | Browser administration acceptance (0.7+) |
| UI foundation | Complete: catalogue selection, typed tables, generic panels, redesigned navigation/collections/inspector/inline editing, automated accessibility and visual-regression gates (UI-07) | — |
| Specialist workflows | Schema 0.6 `mappingGrid` contract, live/draft coverage, target-detail, candidate APIs and atomic mapping replacement delivered; placeholder frontend renderer | Mapping UI 0.7, translation/hierarchy 0.8, integration 0.9 |
| Production and model migration | Basic readiness and actionable startup refusal | Authenticated production, staged assignments and reviewed historical model migration 0.10; draft version selection 0.7 |

Ordinary live saves create neither a draft nor a revision. Draft activation applies authored changes
over current live data, preserves unrelated live work and publishes nothing on a touched-record conflict
or divergent touched mutable relation set, or invalid merged graph. Historical derivation is not a direct restore. Publication retirement does
not withdraw live data or make the workspace read-only; catalogue retirement is the read-only control.
Data drafts and application-definition drafts are different concepts.

The current default/non-default browser gap and disconnected record controls are documented in the
[functionality catalogue](product-functionality/CURRENT_FUNCTIONALITY.md). A component or API present
in code does not establish that a browser user can complete its story.

## Next delivery sequence — product 0.7

1. **Typed `mappingGrid` (WP-2, delivered 2026-09-12):** schema 0.6 with a strict `mappingGrid` view
   contract, discriminated union dispatch, full validation rules and a frontend placeholder renderer.
   WP-4 delivered 2026-09-14: cursor-paged batched mapping coverage, exact counts with bounded
   version-bound target details, view-specific typed projections and candidate search in live/draft
   contexts. WP-5 delivered 2026-09-14: atomic mapping replacement with retained identity, typed
   attributes and direction-aware validation. Mapping UI follows in WP-8A/WP-8B.
2. **ADR-022 relation-set versions (WP-3, delivered 2026-09-12):** exact-binding relation-set versions
   integrated into all generic relation writes in live and optional-draft contexts. Atomic mapping
   replacement is delivered in WP-5.
3. **ADR-028 draft version selection:** WP-6 backend delivered 2026-09-14: installed-release
   creation, whole-candidate compatibility, atomic audited pin changes and pinned model/metadata
   reads. WP-7 browser version selection and model-context refresh delivered 2026-09-14:
   model-release selector in draft creation, release display on draft cards and detail, informational
   banner and activation refusal when versions differ, version-change action with incompatibility
   diagnostics, model-context refresh after pin change, and dirty-input protection via navigation
   guards. Scheduled WP-11 follows WP-7 before composed WP-9 acceptance: correct unsupported historical
   release diff/compile refusals, informative frontend states and actionable internal-error diagnostics.
   See its bounded scope and acceptance criteria in the implementation plan.
4. **UI-07 (carried from 0.6, delivered 2026-09-12):** automated accessibility and visual-regression
   gates using the existing Playwright harness with `@axe-core/playwright` and visual comparison
   baselines. Light-theme baselines committed; dark-theme baselines deferred until a dark theme exists.

Moving a draft onto a version its content does not already fit, and the accepted historical-model
warning and confirm-or-cancel behavior, belong to the planned 0.10 workspace assignment/migration flow.

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
triggers bounded WP-10 work before acceptance. Dark baselines stay deferred until dark mode exists.

### WP-4 delivery and review — 2026-09-14

WP-4 mapping queries and the WP-10A cascade-deletion version fix are committed in `0c459ef`.
Pending WP-3 relation-write participation, draft cleanup/activation and migration test expectations
were committed separately in `022abec`. Both commits together contain the code covered by the final
401-test backend run on SQLite; Ruff passed. WP-4 integration checks cover paging, bounded ambiguous
sets, view-specific projections, draft pins, concurrent reads and stale continuation rejection after
live/draft cascades in both directions. The review found no further confirmed issues.

This is backend query evidence. Atomic replacement (WP-5) was subsequently delivered and reviewed;
the mapping browser workflow (WP-8A/WP-8B) and composed product 0.7 acceptance (WP-9) remain pending.

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
WP-8A/WP-8B browser delivery and
WP-9 composed US-M01–M04 acceptance remain separate; PostgreSQL concurrency is not established.

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

- `model/rdm-starter.json`: schema-language 0.6/content-release 0.7.0 model with 22 attributes, 9 object
  types, 13 relation types, 16 allowed triples, three applications, table and mapping grid collection
  views and typed detail compositions. Domain
  and Codelist objects can have optional System Value representations without joining the independent
  system containment hierarchy.
- Translation objects support translated name, description and value content, are contained by a
  Translation Group, and have exactly one required target chosen from every explicitly configured
  translatable Master object type. Active Target and Language combinations are unique.
- `backend/app/models/schema.py`: executable model contract with uniqueness, cross-reference and parent
  relation validation.
- `backend/app/services/model/compiler.py`, `model/diff.py` and `model/compatibility.py`:
  side-effect-free canonical compilation, stable JSON-path diagnostics, key-based structural diff and
  bounded runtime-data compatibility checks exposed through validation and release-diff APIs.
  Compatibility covers object and relation attribute constraints and relation-type-wide cardinality;
  diffs distinguish JSON null from omission and ignore ordering for set-like stable-key memberships.
- `backend/app/services/model/drafts.py`, `model/releases.py` and the model-management router:
  persisted draft CRUD with optimistic concurrency, side-effect-free draft compilation and atomic,
  idempotent immutable installation serialized across drafts in the supported single-process
  topology. Complete model JSON is excluded from lifecycle audit payloads, and all write routes are
  absent unless model administration mutations are enabled.
- Guarded release activation with runtime-data compatibility diagnostics, dual-token optimistic
  concurrency, old/new release audit identities and hashes, post-commit registry refresh, unhealthy
  readiness on publication failure and startup rejection of configured multi-worker mutation mode.
- `backend/app/models/database.py` and `backend/app/db.py`: immutable model-release metadata plus runtime objects, typed attribute
  values, typed relations, exact-binding relation-set versions and audit events.
- `backend/app/services/attributes.py`: attribute validation, defaults and typed persistence conversion.
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
  historical draft sources, truthful publication retirement and conflict reconciliation. Frontend
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
  (`npm run test:visual`) are delivered. Two known violations are allowlisted by exact target
  and bounded node count with tracked references.
  Visual baselines cover light theme only (no dark theme exists yet).
- Schema 0.6 supports strict table views and the `mappingGrid` view contract (validated model,
  placeholder frontend renderer). Exact-binding relation-set versions are integrated into all generic
  relation writes. WP-4 mapping coverage, target details and candidate search are delivered;
  replacement (WP-5) is delivered; full mapping grid UI (WP-8A/WP-8B) is next. Top-level `form`, `dashboard`
  and `tree` are not implemented renderers.
  Specialist tree/translation coverage follow the roadmap.
- Advanced queries, effective-date/as-of semantics, bulk upsert, imports/exports, change feeds and
  webhooks remain planned; no synchronous collection has an undocumented unlimited mode.
- The model workbench remains JSON-centred; structured authoring and extensions are 1.0 work.
- Multi-writer uniqueness hardening, PostgreSQL performance, authenticated access, actor attribution,
  observability, backup/restore rehearsal and multi-node model propagation remain production work.
- The version serving live data is chosen globally today. Per-workspace migration/assignment, moving
  a draft onto a version its content does not fit, and confirmed potential-loss historical model
  changes require 0.10 and supported parser/runtime versions; letting a draft work under a version the
  user chooses is 0.7 work (ADR-028). Backend clients can choose compatible draft versions (WP-6);
  browser selection is delivered (WP-7). A draft on a replaced version can be read, edited and discarded,
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
full validation rules, starter model 0.7.0 with two mapping grid views, and a frontend placeholder
renderer. WP-3 (relation-set version persistence) was delivered 2026-09-12: `relation_set_versions`
table with lazy row creation, integrated into all six generic relation mutation paths (live and draft),
draft deletion cascade and activation merge. The earlier plans and changelog preserve delivery details;
do not rebuild rejected object lifecycle.

## Coding-agent handoff

Read `AGENTS.md`, the product stories/scenarios, ADR-027, `ROADMAP.md`, `API.md` and `TODO.md`.
Base 0.6 is released; next work targets product 0.7 (core mapping, schema 0.6, draft version
selection). WP-1 (UI-07 accessibility gates), WP-2 (schema 0.6 `mappingGrid` view contract) and
WP-3 (relation-set version persistence), WP-4 reads, WP-5 replacement, WP-6 backend draft version selection, WP-7 browser draft version selection
and WP-10A/WP-10B hardening are delivered. Continue with WP-8A/WP-8B mapping browser
delivery; WP-11 follows WP-7 before WP-9 composed acceptance.
Use one implementation owner per slice, focused verification and appropriate review. Do not commit
unless explicitly requested. Summarize each completed batch while work continues so scope can be
corrected before the entire task finishes.

For implementation run backend Ruff/tests, frontend lint/format/tests/build and `git diff --check`.
Also execute the named browser, migration/startup and wheel gates on Python 3.14. Report evidence
and limits; no documentation change counts as a runtime fix.
