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

The `mappingGrid` and `tree` types still resolve to the generic collection renderer. Attribute filters,
workspace discovery, authoritative runtime-object revisions, integration-scale operations,
authentication and distributed activation are not present. Base 0.6 addresses the common operational
foundation before specialist workspaces.

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

A steward can select a known workspace, use typed table filters and sorts, create a populated root
draft, revise an active or historical revision, retire the current revision without replacement and
later reactivate through a new draft. History makes derivation and supersession independently visible.

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
5. Implement ADR-020 authoritative runtime-object revisions, populated root drafts, drafts derived from
   active or retired history, activation, direct retirement and explicit lifecycle discovery.
6. Migrate Base 0.5 object state without changing stable object IDs. Replace published-object physical
   deletion with retirement and preserve immutable history.
7. Deliver the coherent lifecycle UI and browser, keyboard, accessibility, visual, migration and
   package validation.

### Exit gate

- Workspace resolution is catalogue-backed, URL-stable and retired scopes are read-only.
- Schema 0.5 table views are typed, validated and honestly rendered.
- Daily-use filters/sorts are typed, bounded and cursor-stable.
- Revision storage is authoritative; active projections are transactional derivatives.
- Root drafts, historical branching, activation and direct retirement are understandable and atomic.
- Retired objects remain discoverable, readable, draftable and capable of later activation.
- Derivation and supersession history are distinct and conflicts preserve local input.
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
4. Provide one atomic replace operation for zero or one target with recoverable conflict context.
5. Reuse generic draft creation when target creation is allowed; activation remains explicit.
6. Audit mapping transitions and underlying relation changes.
7. Prove the contract and renderer with two relation bindings whose types, direction and labels differ.

### Exit gate

- Mapping pages and candidates are bounded and avoid per-row requests.
- Concurrent replacement cannot lose a valid mapping or replace another binding's edges.
- Unmapped and ambiguous rows have the same set-level concurrency protection.
- Generic relation routes cannot bypass the mapping token.
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
3. Create a populated translation root draft from a cell and activate it atomically with required
   containment/target relationships.
4. Edit or retire translations through drafts and lifecycle actions, never direct active-row mutation.
5. Enforce target/language uniqueness among active revisions at activation.

Exit: missing and retired translations are distinguishable; writes preserve drafts on conflict; the
matrix remains bounded for representative target/language volumes.

### Milestone B — Hierarchy workspace

A steward browses and maintains deep model-defined hierarchies through lazy loading.

1. Define a strict typed `tree` view contract.
2. Add cursor-paged root/child traversal with bounded path context.
3. Create children as populated drafts and perform rename, state or parent changes through draft
   activation.
4. Validate cycles and publish `parent_object_id` plus the typed edge atomically at activation.
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
3. Bounded bulk root-draft creation, draft updates, activation and upsert with per-item outcomes and
   idempotency.
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
