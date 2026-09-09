# Delivery roadmap

This roadmap sequences product outcomes rather than isolated screens or endpoints. Each milestone stays
model-driven, exercises at least two object or relation configurations, preserves typed values and
optimistic concurrency, and keeps public collections cursor-paged.

The release train is 0.6 for daily live operations and optional coordinated design, 0.7 for core mapping, 0.8 for translation and
hierarchy, 0.9 for integration APIs, 0.10 for production hardening and staged workspace model rollout,
and 1.0 for self-service model authoring and extensions.

## Current development baseline — Base 0.5 foundation and Base 0.6 progress

The operational foundation is complete:

- Versioned JSON application model with startup validation and immutable installed releases
- Stable public UUIDs and Alembic-managed schema upgrades
- Generic object CRUD, typed attribute CRUD and mutable non-containment relation CRUD
- Optimistic concurrency with structured API errors
- Atomic parent containment as hierarchy and typed relation
- Model-declared cardinality, relation attributes and scoped uniqueness
- Dependency previews and explicit graph cascades for current physical deletion behavior
- Model-composed collection/detail UI and server-side relation lookup
- Database-selected model releases, drafts, compilation, diff, compatibility and guarded activation
- URL-backed workspace/list state, stable cursors, bounded relation expansion and audit history

Base 0.6 WP1-WP3 have delivered the UI foundation, workspace discovery and strict schema 0.5 typed
tables. WP4 delivered per-object revisions, but that publication boundary was rejected before release.
WP5 and WP6 introduced workspace draft/revision storage. WP7 restored generic CRUD and WP8 added
lifecycle orchestration; ADR-026 restored direct live writes and conflict-aware draft activation.
The product review identifies remaining authority and browser gaps; recorded package completion does
not close those gaps. WP8.1-A/B/C corrects them before the affected WP9 flows
are accepted, followed by WP10 integration and release validation. Integration-scale operations,
authentication and distributed activation are not present.

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

## Product release 0.6 — Daily live operations and optional coordinated design

### Product outcome

A steward can select a known workspace, find records with typed filters and sorts, and maintain live
records, fields, parents, relationships and translations without a draft. For coordinated changes,
the steward may choose a design draft, validate it and activate all its changes together while
preserving unrelated live work. History distinguishes the source of a draft from the publication
superseded at activation.

Product traceability: US-D01–D14, US-W01–W08, US-L01–L02, US-P06 and US-U01;
SC-01–SC-06, SC-08 and the existing-workbench part of SC-12. Source and outcome definitions live in
[product functionality](product-functionality/README.md).

### Delivery scope

1. Freeze task-based interaction behavior for workspace selection, tables, draft editing, history,
   activation, retirement and conflict recovery.
2. Build ADR-023's RDM-owned accessible UI foundation and clarify application/view/workspace/object
   context across desktop and narrow layouts.
3. Implement ADR-019's global workspace catalogue, singleton default state, bounded discovery and
   selector. Until authentication exists, `WORKSPACE_ADMIN_MUTATIONS_ENABLED` is enabled by default;
   operators must treat it as a deployment switch, not authorization.
4. Introduce schema 0.5 with a strict `table` contract and typed server-side daily-use filters/sorts.
   Schema 0.4 stays stored/listable/exportable but is not runnable.
5. **Done:** Replace rejected ADR-020 contract with ADR-024's workspace-level publication boundary.
6. **Done:** Add workspace revision/draft persistence and correctively migrate Base 0.5
   or WP4-shaped data without changing stable workspace, object or relation IDs; remove per-object
   lifecycle authority after conversion.
7. Restore the established generic object, attribute, containment, relation and translation CRUD over
   workspace-backed storage. Live, draft and history select the data context while preserving the CRUD contract;
   no nested draft-object/relation API is introduced.
8. Complete workspace-level draft/revision discovery, graph validation, atomic activation and
   publication retirement.
9. Restore/reuse generic CRUD UI for live writes and explicitly selected optional drafts. Carry the
   workspace through list, detail, lookup, history and return. Render empty related collections as
   successful empty states, and preserve input during validation/conflict recovery.
10. Complete browser, keyboard, accessibility, visual, migration, package and real integration
   validation without skipped CRUD suites.

### Exit gate

- Workspace resolution is catalogue-backed, URL-stable and retired scopes are read-only.
- Schema 0.5 table views are typed, validated and honestly rendered.
- Daily-use filters/sorts are typed, bounded and cursor-stable.
- Live object, field and relation storage is authoritative for current data; workspace revisions are
  immutable historical snapshots. Ordinary live saves create neither a draft nor a revision.
- A draft started from current live data includes post-publication edits and works without an existing
  publication. This requirement is not satisfied by selecting the latest stored revision.
- Activation preserves unrelated live changes and publishes nothing on a touched-record conflict or
  invalid merged graph.
- Workspace drafts, historical branching, validation, activation and publication retirement are
  understandable and atomic.
- Published and historical workspace snapshots remain readable; objects have no independent lifecycle.
- Workspace derivation and supersession history are distinct and conflicts preserve local input.
- The complete repository definition of done passes on the supported toolchain.

The live-write rules above incorporate ADR-026 directly. The implementation handoff is
[`BASE_0_6_IMPLEMENTATION_PLAN.md`](BASE_0_6_IMPLEMENTATION_PLAN.md); the
[product planning handoff](product-functionality/PLANNING_HANDOFF.md) identifies outstanding
implementation evidence and documentation reconciliation. These are release requirements, not a claim
that the current development tree has passed the complete journey gate.

## Product release 0.7 — Core mapping

### Product outcome

A steward can review mapping coverage and safely create, remove or replace one mapping without
navigating low-level relation screens.

### Delivery scope

1. Introduce schema 0.6 with a strict `mappingGrid` branch; reject containment and required ownership
   bindings as independently mutable mappings.
2. Add cursor-paged batched mapping rows with mapped, unmapped and ambiguous states and server-side
   candidate search.
3. Implement ADR-022 exact-binding relation-set versions across mapping and generic relation writes.
4. Provide atomic replacement with zero or one target where the binding permits it, directly live
   or in an explicitly selected design draft, with recoverable conflict context.
5. Reuse ordinary record creation in the selected context when target creation is allowed; target
   creation must not silently change the mapping, and draft activation remains explicit.
6. Audit mapping transitions and underlying relation changes.
7. Prove the contract and renderer with two relation bindings whose types, direction and labels differ.

### Exit gate

- Mapping pages and candidates are bounded and avoid per-row requests.
- Concurrent replacement cannot lose a valid mapping or replace another binding's edges.
- Unmapped and ambiguous rows have the same set-level concurrency protection.
- Generic relation writes and mapping writes in each supported content context enforce the same
  relation-set concurrency boundary. A draft cannot be used to bypass live conflict detection.
- Schema 0.6 is explicitly dispatched and the schema 0.5 transition has a documented reset or
  migration path appropriate to the pre-production compatibility policy.

## Product release 0.8 — Translation and hierarchy workspaces

The two independently gated milestones may ship together, but neither may weaken runtime revision
semantics.

### Milestone A — Translation workspace

A localization steward works by target and language, sees missing coverage and edits translations
without manually traversing containment.

1. Define a typed translation view from model-declared object, language, containment and relation keys.
2. Add a bounded matrix/coverage query rather than one request per cell.
3. Create or update a translation live, or in an explicitly selected design draft, with the required
   parent and target relationships in one valid operation.
4. Keep ordinary translation corrections direct; use workspace activation only for deliberately staged
   changes. Model changes retain their separate release lifecycle.
5. Enforce target/language uniqueness during live writes and draft validation, and recheck the final
   merged graph during activation.

Exit: missing candidate translations and translations present only in workspace history are
distinguishable; conflicts preserve entered content and any selected draft; the matrix remains bounded for
representative target/language volumes.

### Milestone B — Hierarchy workspace

A steward browses and maintains deep model-defined hierarchies through lazy loading.

1. Define a strict typed `tree` view contract.
2. Add cursor-paged root/child traversal with bounded path context.
3. Create children and perform rename, model-defined availability or parent changes live, with an
   explicitly selected design draft as the coordinated alternative.
4. Validate cycles and update `parent_object_id` plus the typed edge atomically in the chosen context;
   staged changes are revalidated with the merged live graph at activation.
5. Exercise mixed-type containment and recursive self-hierarchy configurations.

Exit: traversal is bounded; reparenting changes both representations or neither; keyboard navigation
and focus/loading/error behavior are covered.

## Product release 0.9 — Integration-grade APIs

### Product outcome

External systems exchange and synchronize reference data through stable, resumable contracts rather
than UI endpoints or undocumented limits.

### Delivery scope

1. Advanced model-aware queries beyond configured daily-use table filters.
2. Model-driven effective dates and `asOf` behavior where explicitly configured.
3. Bounded live bulk creation, update and upsert, with an explicit optional staging mode, per-item
   outcomes, documented failure policy and safe retry/idempotency semantics.
4. Asynchronous import/export with validation previews and resumable job status.
5. Ordered change feed and retryable webhooks.
6. Bounded bulk relation/mapping operations with explicit concurrency semantics.

### Exit gate

- Every collection and job result is bounded or resumable.
- Partial failures and lifecycle stages are machine-readable.
- Bulk contracts are first-class services, not loops over UI calls.

## Product release 0.10 — Production hardening and staged model rollout

### Product outcome

The engine runs safely with multiple writers, authenticated administrators and workspaces that can be
migrated between immutable model releases in controlled stages.

### Delivery scope

- PostgreSQL deployment, model-derived indexes and representative performance tests
- Database-backed uniqueness hardening
- OIDC authentication and authorization for application, object-type and operation scopes
- Audit identity, metrics, structured logging, health/readiness, backup and restore rehearsal
- Multi-node immutable-snapshot propagation and protected model/workspace administration
- Executable workspace-scoped data migration plans
- Historical-draft model replacement targeting one workspace and a named installed immutable release
  (normally the historical pin), with a preview of incompatibilities and potential data loss,
  confirmation bound to the exact reviewed versions or cancel, and atomic model/data application;
  this is the accepted GAP-02 extension, not a force flag on ordinary activation
- Workspace-scoped model-release assignment: resolve workspace before its immutable snapshot, migrate
  its data, then atomically switch its release
- Explicit mixed-schema conversion rules and a bounded supported schema-version window
- First-public-release licensing, contribution/security policies and compatibility commitment

### Exit gate

- Authorization cannot be bypassed through administrative or bulk APIs.
- Multi-writer concurrency and uniqueness invariants hold in production-like tests.
- Workspace migration, release switch and operator backup recovery are rehearsed without mixed-model
  requests. Historical data drafts are not direct dataset restore operations.
- Confirmed historical migration validates transformed data, preserves immutable history, affects only
  the selected workspace assignment, and changes nothing on cancel, stale review or execution failure.
- Supported schema versions and their migration/removal dates are published.

Workspace pinning is a staged-rollout mechanism, not a substitute for schema compatibility: every
schema version that can be pinned must have a parser, runtime contract and data path supported by the
same deployment.

## Product release 1.0 — Self-service model authoring and extensions

### Product outcome

An authorized administrator evolves applications through structured, reference-aware tools beyond the
JSON workbench and lifecycle foundation.

### Delivery scope

- Structured designer with reference-aware catalogues, forms and relationship matrices
- Read-only dependency visualization where it materially improves comprehension
- Protected publish, activation and rollback workflows built on the 0.10 migration boundary
- Extension packaging and reusable model modules after two concrete reuse cases

### Exit gate

- Published releases remain immutable and reproducible.
- Unsafe model changes remain blocked until an explicit migration succeeds.
- Extensions cannot introduce application-specific branches into the runtime.

## Product traceability for later milestones

| Milestone | Stories | Acceptance scenarios | Dependency to preserve |
| --- | --- | --- | --- |
| 0.7 mapping | US-M01–M04 | SC-07 | Complete generic record/relationship flows; live and draft conflict protection |
| 0.8 translation/hierarchy | US-L03–L04, US-H01–H02 | SC-09, separately gated workflows | Generic translation and parent editing remain usable |
| 0.9 integration | US-I03–I09 | SC-10–SC-11 and advanced-query extension | Same validation and workspace rules as individual writes |
| 0.10 production | US-S01, US-O03–O06, US-P07 | SC-13 | Protected operation, measured recovery and consistent model selection |
| 1.0 authoring | US-P05, US-P08 | SC-12 through structured tools and reuse cases | Existing immutable definitions, validation and release safety |

Earlier milestones are pre-production functionality; 0.10 is the gate for authenticated shared
production operation. Release numbers specify sequence, not dates. Detailed format, query, validity,
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
