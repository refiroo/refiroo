# Delivery roadmap

This roadmap sequences product outcomes rather than isolated screens or endpoints. Each milestone must
remain model-driven, work with at least two object or relation configurations, preserve typed values and
optimistic concurrency, and keep public collections cursor-paged.

The intended release train is 0.6 for usable operations and core mapping, 0.7 for the specialist
translation and hierarchy workspaces, 0.8 for integration and bulk operations, 0.9 for production
hardening, and 1.0 for protected self-service model authoring. Milestone gates remain independently
reviewable even when two milestones share one product release.

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

Base 0.5 closed the API and lifecycle foundation, but it did not prove that the resulting UI is an
effective daily workspace. Object editing remains split across core-field and individual-attribute
interactions, workspace selection is not catalogue-backed, model-declared attribute filtering and
sorting are not consumed, and semantically distinct views still share the collection renderer.

Base 0.6 therefore combines a bounded usability foundation with the relation-driven mapping workspace.
The mapping workflow is the first concrete test of the new interaction system, preventing both an
open-ended visual redesign and a specialized screen built on known usability gaps. Translation and
hierarchy then reuse the proven bounded-query and interaction patterns. Production hardening still
precedes unrestricted self-service publishing and structured model design.

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

## Product release 0.6 / Milestone 1 — Usable operations and core mapping

### Product outcome

A data steward can select a known workspace, find and filter records, create or edit a complete object,
understand validation and concurrency failures, and manage mappings without navigating object-by-
object. A model administrator can understand and operate the existing safe lifecycle through a clearer
workbench. No renderer may know starter keys such as `system-value-maps-to-master`.

### Delivery scope

1. Establish task-based usability scenarios and an interaction specification before broad visual or
   workflow implementation. Test workspace selection, collection work, complete object editing,
   mapping and the model lifecycle.
2. Introduce a deliberate UI foundation: readable typography and density, consistent accessible
   controls and feedback, an intentional icon system, simpler navigation and task-based responsive
   behavior.
3. Add a first-class workspace catalogue and bounded discovery API, with stable keys and presentation
   labels, then replace the Base 0.5 free-text field with an accessible catalogue-backed selector.
   Define authority, provisioning and unknown/retired-workspace behavior before implementation.
4. Decide the authority for runtime object states and replace accidental free-text state entry with a
   controlled, validated interaction.
5. Define discriminated, validated `table` and `mappingGrid` view configurations. Implement the
   model-declared attribute filtering and sorting required for daily collection and mapping work, while
   preserving URL state and filter-bound cursors.
6. Provide one coherent create/edit experience for core fields, parent, editable typed attributes and
   required relationships. Preserve dirty input and explain recoverable conflicts.
7. Improve the existing model workbench with structured navigation, diagnostic grouping, reliable
   path navigation, base/active/candidate context, draft duplication and unsaved-change protection.
   Continue using the Base 0.5 lifecycle APIs and safety gates.
8. Add a cursor-paged, batched mapping query that returns source rows with selected targets without
   per-row relation requests. Support mapped, unmapped and ambiguous states plus server-side candidate
   search.
9. Implement mapping create, remove and atomic safe replace with optimistic concurrency. Allow target
   creation through the generic object workflow when the model permits it, and audit every transition.
10. Exercise the mapping contract and renderer with the starter mapping and a second synthetic relation
    whose object types, labels and direction differ.
11. Add browser-level journey tests, automated accessibility checks, keyboard coverage and visual
    regression for the shell, collection, object editor, mapping view and model workbench.

Bulk mapping is deferred to the integration and bulk milestone unless the usability baseline shows
that the single-row workspace cannot meet its core task without it.

### Exit gate

- Normal workspace selection is catalogue-backed rather than free text; the selected workspace remains
  explicit in the URL and scopes object creation, lookup and collection requests consistently.
- Table and mapping-grid declarations are typed, validated and rendered according to their actual
  semantics; unsupported semantic views are not silently presented as another view type.
- A steward can create and edit a complete object without switching between core-field and individual-
  attribute edit modes or losing typed values and local input.
- Configured daily-use filters and sorts execute server-side with bounded, stable cursors.
- The mapping workspace remains responsive with cursor-sized pages and batched expansions.
- Concurrent remapping returns a recoverable conflict and never loses the previously valid mapping.
- Model validation rejects incomplete or incompatible mapping-grid configuration with a precise path.
- Core journeys have browser-level, keyboard, accessibility and visual-regression coverage.
- Backend tests, frontend tests, Ruff, the frontend production build, migrations and documentation pass
  on the supported toolchain, including Python 3.12.

The implementation-ready work packages and decision gates are in
[`BASE_0_6_IMPLEMENTATION_PLAN.md`](BASE_0_6_IMPLEMENTATION_PLAN.md). The active delivery queue is in
[`TODO.md`](TODO.md).

## Product release 0.7 / Milestone 2 — Translation workspace

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

## Product release 0.7 / Milestone 3 — Hierarchy workspace

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

## Product release 0.8 / Milestone 4 — Integration-grade APIs

### Product outcome

External systems can exchange and synchronize reference data through stable, resumable contracts that
do not depend on UI endpoints or undocumented limits.

### Delivery scope

1. Advanced model-aware query expressions beyond the configured daily-use filters and sorts delivered
   in Base 0.6.
2. Model-driven effective-date validation and `asOf` filtering for object types that explicitly bind
   configured validity attributes.
3. Bounded bulk create/update/upsert with per-item outcomes, idempotency and explicit concurrency
   semantics.
4. Asynchronous CSV/Excel import and export with validation previews and resumable job status.
5. Ordered change feed with durable cursors, followed by retryable webhook delivery.
6. Bulk relation operations, including bounded bulk mapping with per-item outcomes, and cursor-paged
   general relation expansion shared by mapping and integration consumers.

### Exit gate

- Every collection and job result is bounded or resumable.
- Partial failures are machine-readable and successful items are never reported ambiguously.
- Bulk contracts are first-class service operations, not loops over UI endpoints.

## Product release 0.9 / Milestone 5 — Production hardening

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

## Product release 1.0 / Milestone 6 — Self-service model authoring and extensions

### Product outcome

An authorized administrator can evolve and publish applications through structured, reference-aware
tools beyond the JSON workbench and lifecycle foundations delivered in Base 0.5.

### Delivery scope

- Structured model designer with reference-aware catalogues, forms, relationship matrices and preview
- Read-only dependency graph visualization where it materially improves comprehension; a graph canvas
  is not the default authoring surface
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

Product release and model-language versions are independent. A release increments `schemaVersion` only
when its declarative contract changes and must preserve an explicit compatibility path for installed
older releases.

Detailed current-state evidence and the immediate coding handoff live in
[`PROJECT_STATUS.md`](PROJECT_STATUS.md). Durable tradeoffs belong in [`DECISIONS.md`](DECISIONS.md),
not in this roadmap.
