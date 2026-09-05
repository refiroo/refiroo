# Delivery roadmap

This roadmap sequences product outcomes rather than isolated screens or endpoints. Each milestone must
remain model-driven, work with at least two object or relation configurations, preserve typed values and
optimistic concurrency, and keep public collections cursor-paged.

## Current baseline — Base 0.5

The operational foundation is complete:

- Versioned JSON application model with startup validation and immutable installed releases
- Stable public UUIDs for metadata and runtime entities, with Alembic-managed schema upgrades
- Generic object CRUD, typed attribute-value CRUD and mutable non-containment relation CRUD
- Atomic object-version and relation-version concurrency claims with structured API errors
- Parent containment maintained atomically as both an indexed hierarchy and typed relation
- Model-declared relation attributes, cardinality and scoped uniqueness validation
- Dependency previews and explicit transactional graph cascades for object deletion
- Model-composed collection and detail UI with typed forms and accessible confirmations
- Cross-application, workspace-bounded relation lookup using server-side search and cursor paging
- Translation lifecycle support with required targets and active target/language uniqueness
- Optional Domain/Codelist representations by System Values without coupling their hierarchies
- Backend and frontend regression suites, linting, production builds and CI coverage
- Database-selected immutable runtime releases, editable drafts, side-effect-free compilation and
  compatibility-gated installation/activation through the global Models workbench
- Explicit workspace and URL-backed collection state, signed built-in sort cursors, bounded relation
  expansion and indexed cursor-paged object history

The `mappingGrid` and `tree` view types still use the generic collection renderer. Integration-scale
queries, bulk operations, authentication, authorization and distributed model activation remain
intentionally outside this baseline.

Base 0.5 closed the most visible object-management gaps, made the installed model lifecycle explicit
and supplied the paged relation/query primitives the next mapping workspace needs. Model 0.6 now
proves relation-centric querying and mutation; translation and hierarchy reuse those bounded-query
and composition patterns. Production hardening still precedes unrestricted self-service publishing
and graphical model design.

## Base 0.5 — Operational base and model lifecycle foundation (complete)

### Product outcome

A data steward can manage runtime objects efficiently across an explicit workspace, and a model
administrator can inspect, validate, compare and stage model releases without editing an installed
snapshot. Activation is deliberate, compatibility-checked and disabled by default until its protected
administrative boundary is enabled.

### Delivery scope

1. Establish one authoritative active-model registry so runtime validation, metadata discovery and the
   UI all use the same immutable release snapshot.
2. Add cursor-paged release discovery and detail APIs, plus side-effect-free validation, canonical
   compilation, semantic diff and runtime-data compatibility analysis.
3. Add optimistic-concurrency model drafts. Installing a valid draft creates a new immutable inactive
   release; it never overwrites the source JSON file or an installed release.
4. Add compatibility-gated, atomic activation with an explicit feature flag. Record install and
   activation audit events; leave multi-node propagation and authorization enforcement to production
   hardening.
5. Make workspace context explicit throughout object routes, creation, lookups and navigation. Add
   URL-backed search, state, page-size and built-in sort controls with stable cursor semantics.
6. Replace unpaged relation expansion with a cursor-paged contract and expose cursor-paged object audit
   history suitable for a generic detail panel.
7. Standardize collection, lookup and detail loading, empty, retry and optimistic-conflict behavior;
   add practical row actions without introducing object-type-specific UI.
8. Add a lightweight model workbench for JSON draft editing/import/export, validation diagnostics,
   release comparison and installation. A graphical schema designer, migration executor and
   unrestricted publishing UI are explicitly deferred.
9. Exercise object management with at least two object types and a non-default workspace, and exercise
   model lifecycle tests with compatible and incompatible candidate releases.

### Exit gate

- Every request observes one coherent active release; metadata and runtime validation cannot disagree.
- Validate and compile have no persistence side effects, installed releases are immutable, and
  duplicate release identities or content return deterministic conflicts.
- Activation cannot strand existing objects, attribute values or relations and cannot silently race a
  concurrent activation.
- Object and relation collections remain bounded under alternate sorting, filters and workspace
  context, with opaque stable cursors.
- The model workbench remains key-agnostic and its write operations are unavailable unless model-admin
  mutation is explicitly enabled.
- The migration upgrade path, backend/frontend suites, Ruff, production build and documentation pass.

The implementation-ready task order, contracts and file-level handoff are in
[`BASE_0_5_IMPLEMENTATION_PLAN.md`](BASE_0_5_IMPLEMENTATION_PLAN.md).

## Model 0.6 / Milestone 1 — Relation-driven mapping workspace

### Product outcome

A data steward can select a known workspace, see mapping coverage, find target candidates, create or
remove mappings and safely replace a mapping without navigating object-by-object. The renderer must
not know starter keys such as `system-value-maps-to-master`.

### Delivery scope

1. Add a first-class workspace catalogue and bounded discovery API, with stable keys and presentation
   labels, then replace the Base 0.5 free-text workspace-key field with an accessible catalogue-backed
   selector. Keep the selected stable key in the URL and preserve it across application, view and
   object navigation. Define catalogue authority, provisioning and unknown/retired-workspace behavior
   before implementation; do not infer the list by issuing unbounded object queries.
2. Define and validate a typed `mappingGrid` view configuration: source type, target type, relation,
   displayed fields, direction and permitted actions.
3. Add a cursor-paged, batched relation-expansion query that returns source rows with selected targets
   and avoids per-row relation requests.
4. Support mapped and unmapped filtering plus server-side candidate search; ambiguous multi-mapping
   state must be explicit rather than silently selecting one edge.
5. Implement create, remove and safe replace operations with optimistic concurrency. Replacement must
   have an atomic backend contract rather than exposing a delete-then-create failure window in the UI.
6. Allow a target object to be created from the mapping workflow when the model permits creation, then
   select it without embedding object-type-specific form logic.
7. Add bounded bulk mapping after the single-row contract is proven, with per-row outcomes and no
   client-side loop over individual mutation endpoints.
8. Record relation audit events for every mapping transition and expose enough history to explain who
   or what changed a mapping once identity is available.
9. Exercise the backend contract and renderer with the starter mapping and a second synthetic relation
   whose object types, labels and direction differ.

### Exit gate

- The mapping workspace remains responsive with cursor-sized pages and batched expansions.
- Normal workspace selection is catalogue-backed rather than free text; the selected workspace remains
  explicit in the URL and scopes object creation, lookup and collection requests consistently.
- Concurrent remapping returns a recoverable conflict and never loses the previously valid mapping.
- Bulk failures identify affected rows without obscuring successful or unchanged mappings.
- Model validation rejects incomplete or incompatible mapping-grid configuration with a precise path.
- Backend tests, frontend tests, Ruff, the frontend production build and documentation all pass.

## Milestone 2 — Translation workspace

### Product outcome

A localization steward can work by target object and language, see missing coverage and edit translation
content without manually traversing Language and Translation Group containment.

### Delivery scope

1. Define a typed translation-workspace view from object, language, containment and target-relation
   keys already present in the model.
2. Add a bounded matrix/coverage query for selected target rows and languages; do not construct the
   matrix through one request per cell.
3. Support missing-translation filtering, create-in-cell, edit, activation/deactivation and navigation
   to the underlying runtime objects.
4. Preserve the existing required-target lifecycle and active target/language uniqueness rules under
   concurrent edits.
5. Prove the renderer against at least two translatable object types without adding starter-key
   branches.

### Exit gate

- Missing and inactive translations are distinguishable and filterable.
- All writes use current object versions and surface scoped uniqueness conflicts without losing input.
- Matrix queries and UI rendering remain bounded as the number of targets and languages grows.

## Milestone 3 — Hierarchy workspace

### Product outcome

A data steward can browse and maintain deep model-defined hierarchies using lazy loading rather than a
flat table or a full-tree download.

### Delivery scope

1. Define and validate typed `tree` view configuration for root types, child types, labels, columns and
   allowed creation/reparenting actions.
2. Add cursor-paged root and child traversal suitable for lazy tree expansion, with batched path or
   ancestor context where needed.
3. Implement contextual child creation, rename/state editing and optimistic-concurrency reparenting.
4. Keep cycle prevention and atomic parent-relation maintenance in the existing generic object service.
5. Exercise mixed-type containment and recursive self-hierarchy configurations.

### Exit gate

- No tree interaction requires an unbounded object or relation query.
- Reparenting either updates the parent ID and typed edge together or changes neither.
- Keyboard navigation, focus behavior and loading/error states are covered by frontend tests.

## Milestone 4 — Integration-grade APIs

### Product outcome

External systems can exchange and synchronize reference data through stable, resumable contracts that
do not depend on UI endpoints or undocumented limits.

### Delivery scope

1. Model-aware filtering and sorting over built-in fields and declared filterable/sortable attributes.
2. Model-driven effective-date validation and `asOf` filtering for object types that explicitly bind
   configured validity attributes.
3. Bounded bulk create/update/upsert with per-item outcomes, idempotency and explicit concurrency
   semantics.
4. Asynchronous CSV/Excel import and export with validation previews and resumable job status.
5. Ordered change feed with durable cursors, followed by retryable webhook delivery.
6. Bulk relation operations and cursor-paged general relation expansion shared by mapping and
   integration consumers.

### Exit gate

- Every collection and job result is bounded or resumable.
- Partial failures are machine-readable and successful items are never reported ambiguously.
- Bulk contracts are first-class service operations, not loops over UI endpoints.

## Milestone 5 — Production hardening

### Product outcome

The engine can run safely with multiple writers on PostgreSQL and enforce access appropriate to
real reference-data ownership.

### Delivery scope

- PostgreSQL deployment and model-derived indexes with representative performance tests
- Database-backed hardening for attribute uniqueness and ancestor-scoped relation uniqueness
- OIDC authentication and model-defined application, object-type and operation permissions
- Audit identity, operational metrics, structured logging and health/readiness checks
- Backup, restore and migration rehearsal for immutable model releases and runtime data
- First-public-release preparation from [`OPEN_SOURCE.md`](OPEN_SOURCE.md): select a licence, add
  contribution and security policies, scan dependencies and secrets, verify synthetic examples and
  publish compatibility expectations

### Exit gate

- Concurrency and uniqueness invariants hold under multi-writer integration tests.
- Authorization is enforced at API boundaries and cannot be bypassed through bulk operations.
- Upgrade and restore procedures are documented and exercised against production-like data volumes.

## Milestone 6 — Model administration and extensions

### Product outcome

An authorized administrator can visually evolve and publish applications beyond the JSON workbench
and lifecycle foundations delivered in Base 0.5.

### Delivery scope

- Structured and graphical model designer with reference-aware editing and preview
- Executable runtime-data migration plans for changes that Base 0.5 correctly blocks
- Protected publish, activation and rollback workflows with multi-node release propagation
- Extension packaging and reusable model modules after at least two concrete reuse cases

### Exit gate

- Published releases remain immutable and reproducible.
- A model change that would strand or invalidate runtime data is blocked until an explicit migration
  plan succeeds.
- Extensions cannot introduce application-specific branches into the runtime engine.

## Cross-cutting release rules

Every milestone follows the repository definition of done:

- State user-visible behavior before implementation and extend the model only where configuration is
  required.
- Add startup validation before consuming new configuration and update metadata persistence when the
  model contract changes.
- Keep Python and TypeScript free of branches on starter application, object-type or relation keys.
- Preserve typed values, stable public IDs, explicit machine-readable errors and optimistic
  concurrency.
- Update API, application-model, architecture and project-status documentation when their contracts
  change.
- Run backend tests and Ruff, frontend tests and production build, plus `git diff --check`.

Detailed current-state evidence and the immediate coding handoff live in
[`PROJECT_STATUS.md`](PROJECT_STATUS.md). Durable tradeoffs belong in [`DECISIONS.md`](DECISIONS.md),
not in this roadmap.
