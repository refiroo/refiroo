# Delivery roadmap

This roadmap sequences product outcomes rather than isolated screens or endpoints. Each milestone stays
model-driven, exercises at least two object or relation configurations, preserves typed values and
optimistic concurrency, and keeps public collections cursor-paged.

The release train is 0.6 for versioned daily operations, 0.7 for core mapping, 0.8 for translation and
hierarchy, 0.9 for integration APIs, 0.10 for production hardening and staged workspace model rollout,
and 1.0 for self-service model authoring and extensions.

## Current baseline — Base 0.5

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
WP5 and WP6 retain the workspace-level contract and authoritative workspace-revision persistence. WP7
is a stopped recovery slice that restores generic CRUD over that storage; WP8-WP10 then complete
workspace lifecycle orchestration, CRUD UI integration and release validation. Integration-scale
operations, authentication and distributed activation are not present.

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

## Product release 0.6 — Versioned daily operations

### Product outcome

A steward can select a known workspace, use typed table filters and sorts, edit several related
records inside one workspace draft, validate the complete graph and publish one immutable workspace
revision atomically. Workspace history makes derivation and supersession independently visible.

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
6. **Done:** Add authoritative workspace revision/draft persistence and correctively migrate Base 0.5
   or WP4-shaped data without changing stable workspace, object or relation IDs; remove per-object
   lifecycle authority after conversion.
7. Restore the established generic object, attribute, containment, relation and translation CRUD over
   workspace-backed storage. Workspace context changes the backing snapshot, not the CRUD contract;
   no nested draft-object/relation API is introduced.
8. Complete workspace-level draft/revision discovery, graph validation, atomic activation and
   publication retirement.
9. Restore/reuse generic CRUD UI inside an explicit workspace draft, with empty related collections
   rendered as empty states.
10. Complete browser, keyboard, accessibility, visual, migration, package and real integration
   validation without skipped CRUD suites.

### Exit gate

- Workspace resolution is catalogue-backed, URL-stable and retired scopes are read-only.
- Schema 0.5 table views are typed, validated and honestly rendered.
- Daily-use filters/sorts are typed, bounded and cursor-stable.
- Workspace revision storage is authoritative; active object/relation projections are transactional derivatives.
- Workspace drafts, historical branching, validation, activation and publication retirement are
  understandable and atomic.
- Published and historical workspace snapshots remain readable; objects have no independent lifecycle.
- Workspace derivation and supersession history are distinct and conflicts preserve local input.
- The complete repository definition of done passes on the supported toolchain.

The implementation handoff is [`BASE_0_6_IMPLEMENTATION_PLAN.md`](BASE_0_6_IMPLEMENTATION_PLAN.md).

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
4. Provide one draft-scoped atomic replace operation for zero or one target with recoverable conflict context.
5. Reuse workspace-draft object creation when target creation is allowed; workspace activation remains explicit.
6. Audit mapping transitions and underlying relation changes.
7. Prove the contract and renderer with two relation bindings whose types, direction and labels differ.

### Exit gate

- Mapping pages and candidates are bounded and avoid per-row requests.
- Concurrent replacement cannot lose a valid mapping or replace another binding's edges.
- Unmapped and ambiguous rows have the same set-level concurrency protection.
- Draft-scoped generic relation routes cannot bypass the mapping token or active publication boundary.
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
3. Create or update a translation in the selected workspace draft with required containment/target relationships.
4. Publish translation changes through workspace activation, never direct active-row mutation.
5. Enforce target/language uniqueness in the complete candidate workspace graph at activation.

Exit: missing candidate translations and translations present only in workspace history are
distinguishable; writes preserve the workspace draft on conflict; the matrix remains bounded for
representative target/language volumes.

### Milestone B — Hierarchy workspace

A steward browses and maintains deep model-defined hierarchies through lazy loading.

1. Define a strict typed `tree` view contract.
2. Add cursor-paged root/child traversal with bounded path context.
3. Create children and perform rename, state or parent changes inside the selected workspace draft.
4. Validate cycles and publish `parent_object_id` plus the typed edge atomically with the workspace revision.
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
3. Bounded bulk workspace-draft record creation, updates and upsert with per-item outcomes and idempotency.
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
- Workspace-scoped model-release assignment: resolve workspace before its immutable snapshot, migrate
  its data, then atomically switch its release
- Explicit mixed-schema conversion rules and a bounded supported schema-version window
- First-public-release licensing, contribution/security policies and compatibility commitment

### Exit gate

- Authorization cannot be bypassed through administrative or bulk APIs.
- Multi-writer concurrency and uniqueness invariants hold in production-like tests.
- Workspace migration, release switch, rollback and restore are rehearsed without mixed-model requests.
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

## Cross-cutting release rules

Every milestone follows the repository definition of done:

- State user-visible behavior before implementation and extend the model only for configurable
  behavior.
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
