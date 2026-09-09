# Project status

## Current development baseline — reviewed 2026-09-08

Base 0.5 is the completed operational/model-release foundation. Base 0.6 remains in development on a
working tree with uncommitted backend and documentation changes. The starter model is content release
0.6.0 on schema language 0.5; that version does not establish completion of product 0.6.

The generic model defines applications, object types, reusable fields, allowed relationships and views.
Master, Systems and Translations are configurable starter examples; runtime code must remain unaware
of their keys. The selected immutable model governs current behavior; the configured source JSON is
bootstrap input, not a parallel activation mechanism.

## Accepted product direction and actual availability

ADR-026 restored direct live reference-data maintenance. ADR-027 consolidates the user's accepted
GAP-01–GAP-08 answers and distinguishes accepted targets from implementation evidence.

| Area | Present foundation | Remaining delivery |
| --- | --- | --- |
| Live data | Generic object, field, parent, relation and translation APIs; record concurrency and audit | Complete browser authoring and non-default workspace context |
| Optional data drafts | Empty or historical-revision sources, effective membership, validation and delta merge | Fresh current-live bases including post-publication edits and no prior publication |
| Historical data | Immutable revision storage and read APIs | Consistent pinned-model interpretation; newest-first discovery |
| Publication retirement | Removes current-publication designation while retaining live data/history | Truthful browser confirmation and direct regression evidence |
| Model administration | Immutable releases, JSON drafts, validation/diff/install/activation workbench | Compatibility population must include all authoritative live data; history must use its pin |
| UI foundation | Catalogue selection, typed tables, generic panels, RDM wrappers and modal behavior | Reachable complete live/draft/history journeys with browser/accessibility/visual evidence |
| Specialist workflows | Generic data semantics to reuse | Mapping 0.7, translation/hierarchy 0.8, integration 0.9 |
| Production and model migration | Basic readiness and actionable startup refusal | Authenticated production operation, staged assignments and reviewed historical model migration in 0.10 |

Ordinary live saves create neither a draft nor a revision. Draft activation applies authored changes
over current live data, preserves unrelated live work and publishes nothing on a touched-record conflict
or invalid merged graph. Historical derivation is not a direct restore. Publication retirement does
not withdraw live data or make the workspace read-only; catalogue retirement is the read-only control.
Data drafts and application-definition drafts are different concepts.

The current default/non-default browser gap and disconnected record controls are documented in the
[functionality catalogue](product-functionality/CURRENT_FUNCTIONALITY.md). A component or API present
in code does not establish that a browser user can complete its story.

## Next delivery sequence

1. **WP8.1-B:** immutable current-live draft bases, independent of publication lineage, including upgrade
  preservation of existing drafts and migration/startup evidence.
2. **WP8.1-C:** newest-first history and explicit retirement/history behavior tests.
3. **WP9:** complete live CRUD, optional copied drafts and immutable history through generic browser
   controls, preserving workspace context, typed inputs, conflicts, keyboard and narrow-layout behavior.
4. **WP10:** composed frontend/backend scenarios, authority/concurrency boundaries, browser accessibility
   and visual evidence, migration/lifespan, packaging and public-contract checks.

The accepted historical-model warning and confirm-or-cancel behavior belongs to the planned 0.10
workspace assignment/migration flow. Until it exists, Base 0.6 preserves incompatible drafts and reports
the mismatch. No force flag or implicit global schema override is part of the current contract.

See [implementation plan](BASE_0_6_IMPLEMENTATION_PLAN.md), [delivery queue](TODO.md),
[roadmap](ROADMAP.md) and [product acceptance scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md).

## Evidence boundary

The subsequent [WP8 implementation review](../review-notes/wp8-implementation-review-2026-09-08.md)
reviewed the uncommitted diff and corrected confirmed lifecycle/CRUD defects. Its backend, frontend,
migration and installed-wheel evidence is recorded separately; it does not close the remaining
WP8.1-B/C–WP10 work.
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

- `model/rdm-starter.json`: schema-language 0.5/content-release 0.6.0 model with 22 attributes, 9 object
  types, 13 relation types, 16 allowed triples, three applications, collection views and typed detail compositions. Domain
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
  values, typed relations and audit events.
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
  Workspace lifecycle UI is not yet complete. Generic object, attribute, relation and translation
  controls must be restored for live writes with optional draft context; failed collection and lookup
  reads remain retryable, while genuinely empty relationship/translation collections render as empty
  states and engine-maintained containment edges remain read-only.
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

- No complete browser CRUD/draft/history journey is claimed until WP9/WP10 evidence exists.
- Current-live draft capture remains in WP8.1-B; newest-first history and retirement behavior remain in
  WP8.1-C. WP8.1-A now covers all authoritative live compatibility rows and pinned model interpretation
  for draft/history reads; stored revision/model IDs are resolved before query and response semantics.
- Schema 0.5 supports strict table views; `mappingGrid`, top-level `form`, `dashboard` and `tree` are
  not implemented renderers. Specialist mappings and tree/translation coverage follow the roadmap.
- Advanced queries, effective-date/as-of semantics, bulk upsert, imports/exports, change feeds and
  webhooks remain planned; no synchronous collection has an undocumented unlimited mode.
- The model workbench remains JSON-centred; structured authoring and extensions are 1.0 work.
- Multi-writer uniqueness hardening, PostgreSQL performance, authenticated access, actor attribution,
  observability, backup/restore rehearsal and multi-node model propagation remain production work.
- Global model selection is current authority. Workspace-scoped migration/assignment and confirmed
  potential-loss historical model changes require 0.10 and supported parser/runtime versions.
- The starter remains representative rather than a one-to-one reproduction of the source export.

## Historical delivery record

Base 0.5 delivered runtime model selection, model compilation/diff/compatibility, versioned drafts,
immutable install, guarded activation, bounded query/audit improvements and the JSON workbench.
Base 0.6 WP1–WP3 delivered UI primitives, workspace catalogue and typed tables. WP4's individual-object
publication design was rejected before release and removed through the corrective WP6 migration;
WP5 refroze workspace scope, WP7 restored generic CRUD and WP8 implemented lifecycle services.
ADR-026 then restored direct live data and delta merge. Those records do not make WP8.1-B/C–WP10
complete.
The earlier plans and changelog preserve delivery details; do not rebuild rejected object lifecycle.

## Coding-agent handoff

Read `AGENTS.md`, the product stories/scenarios, ADR-027, `BASE_0_6_IMPLEMENTATION_PLAN.md`, `API.md`
and `BASE_0_6_INTERACTION_SPEC.md`. Preserve the dirty tree and start with WP8.1-A, then B/C before
accepting dependent WP9 design/history behavior. Complete WP9 and WP10 against the named stories.
Use one implementation owner per slice, focused verification and appropriate review. Do not commit
unless explicitly requested. Summarize each completed batch while work continues so scope can be
corrected before the entire task finishes.

For implementation run backend Ruff/tests, frontend lint/format/tests/build and `git diff --check`
using the exact commands in the Base 0.6 plan. Also execute the named browser, migration/startup and
wheel gates on Python 3.14. Report evidence and limits; no documentation change counts as a runtime fix.
