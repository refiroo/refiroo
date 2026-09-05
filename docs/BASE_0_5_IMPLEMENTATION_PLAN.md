# Base 0.5 implementation plan

**Status:** Complete (2026-09-05)
**Target:** Model release 0.5  
**Scope:** Operational object management, model lifecycle foundations and a lightweight model
workbench  
**Depends on:** The completed model 0.4 runtime CRUD slice  
**Unlocks:** Base 0.6 usable operations and core relation-driven mapping

## Execution status

| Work package | Status | Evidence |
|---|---|---|
| WP0 — Checkpoint and lock contracts | Complete | Model 0.4 checkpoint `98f7cdd`; ADR-015 through ADR-018; lifecycle API shapes; OpenAPI contract test |
| WP1 — Make the active release authoritative | Complete | Runtime-state migration; bootstrap installer; request snapshots; release read APIs |
| WP2 — Add the compiler, semantic diff and compatibility analyzer | Complete | Stable diagnostics; canonical compiler; key-based diff; bounded runtime checks |
| WP3 — Persist drafts and install immutable releases | Complete | Versioned drafts, atomic install, capability gate and audit |
| WP4 — Implement guarded activation | Complete | Dual-token activation, compatibility gate, audit and readiness failure handling |
| WP5 — Upgrade object and relation query foundations | Complete | Signed keyset cursors; bounded relation/history pages; indexed audit subjects |
| WP6 — Improve generic object management UI | Complete | URL/workspace state; generic actions; retry states; paged relations/history |
| WP7 — Add the lightweight model workbench | Complete | Global Models route; capability-gated drafts; validation/diff/install/activation workflow |
| WP8 — Release integration and documentation | Complete | Starter release 0.5.0; operations runbook; complete OpenAPI error/page contract; release gates |

## Handoff instructions

Before implementation, read `AGENTS.md` and the project documents it lists. The current worktree
contains the model 0.4 implementation and documentation changes; make a Git checkpoint before starting
this slice and preserve unrelated changes.

Implement the work packages below in order. Each package should be independently reviewable and leave
the test suite passing. Do not branch on starter application, object-type, attribute-type or relation
keys. Do not edit `model/rdm-starter.json` merely to drive generic administration UI.

## Product outcome

Base 0.5 makes the existing generic engine pleasant and safe to operate before specialized mapping and
translation workspaces are added:

1. A user works in an explicit workspace and can find, filter, sort, page, inspect and act on objects
   with predictable loading, error and conflict behavior.
2. Large relation panels and object history remain bounded and navigable.
3. An administrator can save a candidate as a draft, validate and compile it without side effects,
   compare it with an installed release, install an immutable release and activate only a compatible
   release.
4. The runtime, metadata endpoints and frontend always agree on which immutable model release is
   active.

## Scope boundaries

### Included

- One authoritative active-model selection and immutable request snapshots
- Release catalogue and release detail
- Persisted editable drafts with optimistic concurrency
- Side-effect-free validation, canonical compilation, semantic diff and compatibility checks
- Immutable install and guarded atomic activation
- A JSON-based model workbench with diagnostics and diff summaries
- Explicit workspace context and improved generic object collection/detail behavior
- Built-in-field search, state filtering, sorting and page-size controls
- Cursor-paged relation expansion and object audit history
- Documentation, migrations, audit records and automated tests

### Deferred

- Graphical node/edge or drag-and-drop model design
- Automatic runtime-data transformation or destructive schema migration
- Distributed cache invalidation for multi-process or multi-node activation
- OIDC, roles and model-defined authorization
- Arbitrary attribute filtering/sorting, bulk upsert, import/export jobs and change feeds
- Dedicated mapping, translation and hierarchy renderers
- Editing installed release JSON or writing model files on the server

`Save` means persist an editable database draft. `Install` means create an immutable release from a
successfully compiled draft. `Activate` means select an installed compatible release. These are three
separate operations.

## Architecture decisions to record first

Add durable decisions to `docs/DECISIONS.md` before implementing their dependent packages:

1. **Active model authority.** The database runtime-state row identifies the active installed release.
   A request resolves that row once and uses one immutable parsed `EngineModel` snapshot for all model
   checks. `MODEL_PATH` is bootstrap input, not a second runtime authority.
2. **Draft and release lifecycle.** Drafts are mutable and versioned; releases are immutable and
   content-addressed. Validation and compilation do not write. Installation does not activate.
3. **Activation safety boundary.** Activation uses an optimistic expected runtime-state version and is
   blocked by incompatible runtime data. The mutation route is disabled by default. Base 0.5 supports
   coherent activation in the current single-process deployment only; production multi-node
   propagation and authorization are later gates.
4. **Cursor evolution.** Collection cursors are opaque, encode the selected sort plus a unique
   tie-breaker and are invalid when reused with different filters or sort. Clients must never parse
   them.

Do not change `schemaVersion` solely for lifecycle storage or UI. Increment the schema-language version
only if the declarative `EngineModel` contract itself changes.

## API contract

Names below are the target public contract. Use UUID4 public IDs; never expose database sequence IDs.
All collections return `{items, nextCursor}` and accept bounded `pageSize` plus opaque `cursor`.

### Active model and releases

- `GET /api/v1/capabilities` reports deployment-supported features, including
  `modelAdmin.readReleases`, `modelAdmin.manageDrafts`, `modelAdmin.install` and
  `modelAdmin.activate`; the UI does not infer permissions from failed requests.
- `GET /api/v1/model` returns the active model and adds response headers
  `ETag: "<modelHash>"` and `X-Model-Release-Id: <publicId>`.
- `GET /api/v1/model-releases` lists immutable releases, filterable by release key and activation
  status.
- `GET /api/v1/model-releases/{releaseId}` returns identity, version, schema version, hash, install
  time, activation status and optionally the JSON definition through `includeModel=true`.
- `GET /api/v1/model-releases/{releaseId}/diff?againstReleaseId=...` returns structured additions,
  changes and removals by JSON path plus a compatibility summary.
- `POST /api/v1/model-releases/{releaseId}/activation` accepts
  `{expectedRuntimeVersion, expectedActiveReleaseId}`. It either atomically selects the release and
  returns the new runtime state or changes nothing.

Release collection and detail are read-only regardless of the administration mutation flag. Return
`409 release_identity_conflict` if the same release key/version has different content and
`409 activation_conflict` for stale runtime state.

### Drafts, validation, compilation and installation

- `GET /api/v1/model-drafts` and `GET /api/v1/model-drafts/{draftId}` discover drafts.
- `POST /api/v1/model-drafts` saves `{name, baseReleaseId?, model}` and returns draft version 1.
- `PATCH /api/v1/model-drafts/{draftId}` saves `{expectedVersion, name?, model?}` and increments the
  version atomically.
- `DELETE /api/v1/model-drafts/{draftId}?expectedVersion=...` deletes only the draft.
- `POST /api/v1/model-validations` accepts inline `{model}` and returns `{valid, diagnostics}` without
  persistence. Diagnostics contain `severity`, `code`, `path` and `message`.
- `POST /api/v1/model-drafts/{draftId}/compile` accepts `{expectedVersion}` and returns the parsed
  canonical model, SHA-256 hash, diagnostics and compatibility report without persistence.
- `POST /api/v1/model-drafts/{draftId}/installation` accepts `{expectedVersion}`. It repeats compile
  and compatibility analysis in the same operation, creates metadata for one immutable inactive
  release and returns it. Identical content is idempotent; conflicting identity is not.

All draft and mutation routes are unavailable with `404` unless
`MODEL_ADMIN_MUTATIONS_ENABLED=true`. This avoids advertising an unprotected write surface. The flag
is a deployment guard, not authorization; production enablement still requires Milestone 5 identity
and permissions.

### Compatibility classifications

The compiler returns one of:

- `compatible`: activation can proceed without changing stored runtime data.
- `migration_required`: stored data would become invalid; Base 0.5 blocks activation.
- `invalid`: model/schema validation failed and no compatibility claim is made.

At minimum, runtime-data checks must block:

- removing an application or object type used by an existing object;
- removing or unbinding an attribute type with stored values;
- changing a stored attribute's declared value type;
- removing an allowed relation triple used by an existing relation;
- changing a used relation attribute type or removing its declaration;
- changing parent-relation semantics in a way that invalidates existing containment;
- making a binding or required relation mandatory when existing objects do not satisfy it;
- introducing uniqueness or cardinality rules violated by current data.

Presentation-only changes and unused additive definitions are compatible. Never infer compatibility
from the semantic version string alone.

### Object-management additions

- `GET /api/v1/objects/{objectTypeKey}` retains existing filters and adds repeatable `state` plus
  `sort=name|-name|state|-state|createdAt|-createdAt|updatedAt|-updatedAt`. Default ordering remains
  stable and every ordering uses the sequence ID as its final tie-breaker.
- Object creation from every UI context sends the selected `workspaceKey`; candidate and parent
  lookups retain that same workspace boundary.
- `GET /api/v1/relations` returns a page rather than an unbounded array and accepts `cursor` and
  bounded `pageSize`. Preserve `objectId`, `direction` and `relationTypeKey` filters.
- `GET /api/v1/objects/{objectTypeKey}/{objectId}/history` returns cursor-paged object, attribute and
  connected-relation audit events ordered newest first.

Changing relation expansion from an array to a page is an intentional pre-1.0 breaking change. Update
the frontend and `docs/API.md` in the same package. Arbitrary dynamic-attribute filters remain in
Milestone 4.

## Work packages

### WP0 — Checkpoint and lock contracts

**Status:** Complete (2026-09-04)

Files:

- `docs/DECISIONS.md`
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- this plan

Tasks:

1. Commit or otherwise checkpoint the current model 0.4 worktree before implementation.
2. Record the four architecture decisions above and confirm the endpoint/request/response names.
3. Capture the current OpenAPI document or contract tests so breaking changes are deliberate.
4. Confirm the deployment is single-process while mutable model administration is enabled.

Exit: decisions are accepted, API shapes are testable and implementation does not need to invent
lifecycle semantics mid-slice.

Completion record:

- checkpointed the validated model 0.4 worktree in Git commit `98f7cdd`;
- accepted ADR-015 through ADR-018 and documented the supported single-process mutation topology;
- locked lifecycle endpoint names, payload fields, omission rules, diagnostics and conflicts in
  `docs/API.md`; and
- added `backend/tests/test_openapi_contract.py` to pin the current model 0.4 path/method and schema
  inventory before Base 0.5 introduces deliberate contract changes.

### WP1 — Make the active release authoritative

**Status:** Complete (2026-09-04)

Files:

- `backend/app/models/database.py`
- new Alembic revision under `backend/app/migrations/versions/`
- `backend/app/db.py`
- `backend/app/services/model_loader.py`
- new `backend/app/services/model_registry.py`
- `backend/app/main.py`
- `backend/app/routers/model.py`
- focused backend tests

Tasks:

1. Add a singleton `model_runtime_state` row with the active release foreign key, optimistic `version`
   and update timestamp. Add uniqueness for `(release_key, release_version)`.
2. Migrate the existing active release into runtime state. Reject ambiguous legacy active rows with a
   precise startup failure; do not guess.
3. Split bootstrap loading from runtime resolution. Startup validates the configured JSON, installs it
   only if absent, initializes runtime state only when no active release exists, then loads the active
   database snapshot.
4. Introduce a registry that caches immutable parsed models by release public ID/hash. Resolve runtime
   state once per request and pass the resolved snapshot through service dependencies.
5. Remove queries that independently search for `ModelRelease.is_active`; metadata IDs and model JSON
   must come from the same resolved release.
6. Add `ETag` and release ID headers and release catalogue/detail APIs.
7. Keep a compatibility transition for `is_active` only inside persistence code, then remove it in a
   later migration; application code must use runtime state.

Tests:

- first startup, restart with identical content and startup with a different bootstrap file;
- metadata/model coherence after selecting a release;
- no duplicate install by hash or release identity;
- migration from the model 0.4 database;
- two simulated requests cannot observe mixed metadata/model snapshots.

Exit: there is one runtime authority and all current behavior still passes against it.

Completion record:

- added the singleton, versioned `model_runtime_state` authority and unique release identity through
  Alembic, including deterministic adoption of exactly one legacy active release;
- separated source-file bootstrap loading from database runtime selection, preserving an existing
  selection when a different bootstrap release is installed;
- added an immutable request snapshot registry keyed by release UUID and hash, and passed one resolved
  model through all model-dependent router and service operations;
- removed application-layer selection through `ModelRelease.is_active`; the legacy flag is synchronized
  only inside bootstrap persistence during the transition;
- added coherent, standards-compliant `ETag` and `X-Model-Release-Id` headers plus signed,
  filter-bound cursor paging for the release catalogue and release detail endpoints; and
- expanded migration, bootstrap, snapshot-coherence, release API and OpenAPI contract tests.

### WP2 — Add the compiler, semantic diff and compatibility analyzer

**Status:** Complete (2026-09-04)

Files:

- new `backend/app/services/model_compiler.py`
- new `backend/app/services/model_diff.py`
- new `backend/app/services/model_compatibility.py`
- `backend/app/models/api.py`
- new or existing model-management router
- `backend/tests/test_model.py`
- new `backend/tests/test_model_lifecycle.py`
- new `backend/tests/test_model_compatibility.py`

Tasks:

1. Convert Pydantic and cross-reference failures into stable diagnostics with JSON paths. Keep parsing
   independent of the database.
2. Canonicalize a valid model exactly once and return the same hash used by release installation.
3. Implement key-based semantic diff for releases, applications, global attribute types, object types,
   bindings, relation types, allowed triples, views and detail compositions. Do not treat array order as
   identity where a stable key exists.
4. Implement runtime-data compatibility checks listed above using bounded aggregate/existence queries,
   not full table loads.
5. Expose inline validation and installed-release diff APIs.
6. Keep invalid, incompatible and internal failures distinct and machine-readable.

Tests use at least one safe presentation change, one safe unused addition and each blocking class.
Verify validation/compile leave all database row counts unchanged.

Exit: a candidate can be explained before anything is saved, installed or activated.

Completion record:

- added side-effect-free model compilation with stable machine-readable diagnostics, JSON Pointer
  paths and the canonical SHA-256 implementation shared by bootstrap release installation;
- added semantic diff keyed by stable definition/binding identities so definition-array reordering is
  not reported as a model change;
- added bounded aggregate, existence and recursive-hierarchy compatibility checks for every Base 0.5
  blocking class, including required bindings, cardinality and scoped uniqueness;
- hardened cardinality checks across all allowed pairs sharing one relation type and applied tightened
  numeric bounds to both object and relation attribute storage;
- exposed inline validation and installed-release diff APIs, keeping invalid installed content,
  migration requirements and internal failures distinct; and
- preserved JSON nulls and set-like key semantics in diffs, expanded precise diagnostic paths, and
  added focused compiler, diff, compatibility, side-effect and OpenAPI contract tests.

### WP3 — Persist drafts and install immutable releases

**Status:** Complete (2026-09-04)

Files:

- `backend/app/models/database.py`
- new Alembic revision
- `backend/app/models/api.py`
- new `backend/app/services/model_drafts.py`
- new `backend/app/services/model_releases.py`
- new `backend/app/routers/model_management.py`
- `backend/app/config.py`
- `backend/app/main.py`
- lifecycle and migration tests

Tasks:

1. Add `model_drafts` with public ID, name, optional base release, JSON content, integer version,
   created/updated timestamps and no metadata child rows.
2. Implement draft CRUD with conditional version claims and `409 version_conflict`.
3. Refactor metadata installation from `db.py` into a focused transactional release service.
4. Compile again inside installation; never trust a prior client compile result.
5. Insert the release and every metadata projection in one transaction. Installation is inactive and
   never mutates a prior release or server-side JSON file.
6. Make same-hash installation idempotent and same-key/version/different-hash installation a conflict.
7. Audit draft creation/update/delete and release installation without storing the complete model JSON
   in the audit payload.
8. Gate every draft/write route with `MODEL_ADMIN_MUTATIONS_ENABLED`.
9. Expose the effective read/write capabilities so the frontend can hide unavailable actions without
   probing protected endpoints.

Exit: drafts are recoverably editable and release installation is atomic, immutable and reproducible.

Completion record:

- added a versioned `model_drafts` table with optional installed-release provenance and no metadata
  child projection;
- added cursor-paged draft CRUD with atomic optimistic version claims and mutation-gated route
  registration;
- refactored immutable metadata installation into a focused transactional release service shared by
  bootstrap and draft installation;
- recompiled and reassessed persisted content during installation, preserving the active runtime
  selection and providing hash idempotence plus release-identity conflicts;
- serialized installation across drafts in the supported single-process mutation topology so
  concurrent identical requests remain idempotent;
- recorded concise draft/install lifecycle audit events without storing complete model documents; and
- exposed capabilities that distinguish always-readable releases from enabled draft/install writes,
  while leaving activation disabled until WP4.

### WP4 — Implement guarded activation

Files:

- `backend/app/services/model_releases.py`
- `backend/app/services/model_registry.py`
- `backend/app/routers/model_management.py`
- `backend/app/errors.py`
- lifecycle/concurrency tests

Tasks:

1. Re-run model parsing and compatibility inside the activation transaction.
2. Conditionally update runtime state using both expected runtime version and expected active release
   public ID.
3. Commit runtime state before publishing the new immutable snapshot to the process registry; if the
   registry refresh fails, mark readiness unhealthy and do not serve a guessed model.
4. Return `409 model_migration_required` with diagnostic paths/counts when stored data blocks the
   candidate, and `409 activation_conflict` for a concurrent selection.
5. Record old/new release IDs and hashes in an audit event.
6. Reject mutation enablement in a documented multi-worker configuration until release propagation is
   implemented.

Exit: activation is all-or-nothing, concurrency-safe for the supported deployment and observable.

Completion record:

- added the mutation-gated activation route and complete runtime-state response;
- reparsed active and candidate installed JSON and ran bounded compatibility checks inside the
  activation transaction;
- conditionally claimed runtime state using both expected version and expected active release ID,
  returning structured migration-required and activation-conflict errors without mutation;
- committed the authoritative selection before refreshing the process registry, marking health
  unhealthy and refusing model-dependent requests if publication fails;
- recorded old/new release UUIDs and hashes in activation audit events; and
- rejected mutation enablement when `WEB_CONCURRENCY` configures more than one worker.

### WP5 — Upgrade object and relation query foundations

Files:

- `backend/app/models/api.py`
- `backend/app/models/database.py`
- a new Alembic revision for audit subjects
- `backend/app/routers/objects.py`
- `backend/app/services/objects.py`
- `backend/app/routers/relations.py`
- `backend/app/services/relations.py`
- new focused audit read service/router if needed
- backend query, relation and audit tests
- `docs/API.md`

Tasks:

1. Introduce signed or integrity-checked opaque cursor payloads containing sort, tie-breaker and a
   fingerprint of effective filters. Reject malformed or mismatched cursors with `invalid_cursor`.
2. Add the bounded built-in sorts and repeatable state filter. Preserve index-friendly predicates and
   deterministic tie-breaking.
3. Page relation expansion and update every caller; no compatibility path may fetch an unbounded set.
4. Add an indexed `audit_event_subjects` projection linking one event to each affected object public
   ID. Populate it for new object, attribute and relation events and backfill existing relation events
   only where their recorded endpoint IDs make that deterministic.
5. Add cursor-paged audit history for one object by joining the subject projection, including object,
   attribute and connected-relation events. Do not query JSON payloads for identity and do not expose
   internal numeric IDs or complete sensitive before/after blobs.
6. Verify workspace filters on object lists, parent/candidate lookup and related objects.
7. Add representative pagination tests with duplicate names/timestamps, inserts between pages and a
   mismatched-cursor request.

Exit: Base 0.5 and the Base 0.6 mapping slice can share stable bounded query primitives.

Completion record:

- replaced raw object sequence cursors with signed keyset positions bound to built-in sorting and all
  effective application, workspace, parent, state and search filters;
- added repeatable state filtering and deterministic name, state, created and updated sorting;
- changed relation expansion to a workspace-checked bounded page and updated backend and frontend
  callers, including incremental relation-panel loading;
- added and backfilled the indexed audit-subject projection, attaching new object, attribute and
  relation events to every affected object without JSON identity queries; and
- exposed cursor-paged, newest-first object history with safe change-key summaries and regression
  coverage for duplicate positions, inserts, workspace boundaries and mismatched cursors.

### WP6 — Improve generic object management UI

**Status:** Complete (2026-09-05)

Files:

- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/CollectionView.tsx`
- `frontend/src/components/ObjectDetail.tsx`
- `frontend/src/components/ObjectFormDialog.tsx`
- `frontend/src/components/ObjectLookup.tsx`
- new `WorkspaceSelector.tsx`, `ObjectToolbar.tsx` and `HistoryPanel.tsx`
- `frontend/src/styles.css`
- focused frontend tests

Tasks:

1. Add explicit workspace context to the URL and app shell, defaulting to `default`. Preserve it across
   application/view/detail navigation and browser back/forward.
2. Send the workspace on create, collection, parent lookup and relation candidate lookup. Clear a
   selected parent/candidate if the workspace changes.
3. Put search, state, sort and page size in URL query state. Changing a filter resets the cursor;
   browser navigation restores the prior collection state.
4. Add generic row actions for open, edit and delete where existing model semantics allow them. Reuse
   current dialogs and dependency/conflict behavior.
5. Add reusable loading, empty, inline error and retry states to collections, detail panels and object
   lookups. A failed lookup must not become an empty successful result.
6. Adapt relation panels to pages with next/previous or load-more behavior and independent panel state.
7. Add an audit-history detail panel/timeline with action, timestamp, aggregate version and concise
   change summary. Actor remains absent until authentication exists.
8. Preserve focus, keyboard operation, semantic tables/forms and user input after recoverable errors.

Tests:

- two distinct object types through the same components;
- create and lookup in a non-default workspace;
- URL restoration for filters/sort/page size;
- retry after failed collection and lookup requests;
- version conflict refresh and paged relation/history behavior.

Exit: common object work no longer requires fragile navigation or unbounded panel requests.

Completion record:

- made workspace context explicit in the app shell and every list/detail URL, preserving it through
  application, view, object and browser navigation and applying it to collection, create, parent and
  cross-application candidate requests;
- added URL-backed search, repeatable state, built-in sort and page-size controls whose changes reset
  local cursor history while browser navigation restores the prior query;
- added model-generic collection row actions that reuse the existing edit, dependency-preview,
  cascade-confirmation and optimistic-conflict flows;
- added retryable loading, empty and error states for collections, explorer data, embedded panels and
  object lookups without presenting failed requests as successful empty results;
- retained independent bounded relation-panel paging and added a bounded object-history timeline with
  concise field/attribute summaries and incremental loading; and
- expanded frontend coverage for two generic object types, a non-default workspace, URL restoration,
  retries, version-conflict refresh and paged relation/history behavior.

### WP7 — Add the lightweight model workbench

**Status:** Complete (2026-09-05)

Files:

- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/App.tsx` and route helpers
- new `frontend/src/components/model/ModelWorkbench.tsx`
- new draft editor, diagnostics, release list/detail and diff components under that directory
- `frontend/src/styles.css`
- focused frontend tests

Tasks:

1. Add a global Models route outside starter-application navigation. Read-only release list/detail stay
   visible; draft and mutation actions appear only when the backend capability response enables them.
2. Support draft creation from an empty/imported JSON document or an installed release. Use a plain
   accessible text editor for 0.5; do not add a large editor dependency without a separate decision.
3. Debounce local syntax feedback but run authoritative validation on the backend. Link diagnostics to
   line/path where possible and preserve invalid input while errors are shown.
4. Save with `expectedVersion`; on conflict retain the local content and offer reload/copy, never
   overwrite silently.
5. Show canonical hash, semantic diff and compatibility classification before enabling installation.
6. Require confirmation for installation and activation. Clearly state that installation does not
   activate and that incompatible activation is blocked.
7. Add download/export of draft or release JSON in the browser. Do not write arbitrary server paths.
8. Provide a read-only structured summary of applications, types, relations and views. Defer visual
   graph manipulation and runtime-data migration controls.

Exit: an administrator can complete the safe candidate-to-installed lifecycle without pretending that
Base 0.5 is a full graphical designer.

Completion record:

- added a global, URL-addressable Models workbench outside application navigation with always-readable
  installed release catalogue, detail, structured summaries and browser JSON export;
- added capability-gated draft creation from empty, imported or installed JSON, an accessible plain
  text editor, debounced syntax and authoritative validation feedback, and JSON-path navigation;
- preserved unsaved content across optimistic version conflicts with explicit reload and copy recovery;
- extended side-effect-free draft compilation with a base-release semantic diff and exposed read-only
  runtime-state concurrency tokens needed for safe activation;
- required explicit installation and activation confirmation, displayed canonical hash and runtime
  compatibility before installation, and blocked incompatible activation in the UI; and
- added focused API, route and component tests covering read-only mode, lifecycle concurrency,
  conflict recovery and pre-install review.

### WP8 — Release integration and documentation

Files:

- `model/rdm-starter.json` only for its release identity/version after contracts are final
- `README.md`
- `CHANGELOG.md`
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/APPLICATION_MODEL.md` if the schema-language contract changed
- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`

Tasks:

1. Upgrade the starter content release to 0.5 without changing `schemaVersion` unless the language
   changed.
2. Document bootstrap versus active database release, admin feature flags, single-process limitation,
   draft/install/activate semantics and rollback procedure.
3. Document every new cursor, error code and response header and the relation-expansion breaking
   change.
4. Mark completed work packages and move `PROJECT_STATUS.md` to Base 0.6 only after all Base 0.5
   exit criteria pass.
5. Add a changelog entry and migration/backup notes.

Completion record:

- promoted the bundled starter content to release `0.5.0` while retaining model-language schema
  `0.4`;
- documented database-selected runtime authority, bootstrap behavior, mutation flags, the supported
  single-process topology and the draft/validate/install/activate lifecycle;
- documented cursor contracts, active-model headers, lifecycle failures, the relation-page breaking
  change and separate model-content versus application/schema rollback procedures;
- added a generated OpenAPI error-envelope schema with cursor, concurrency and request-validation
  examples while preserving the locked bounded collection schemas;
- added migration coverage proving a model 0.4 active release and runtime object survive upgrade, and
  verified fresh boot, mutation-disabled/enabled surfaces and wheel migration packaging; and
- completed the Base 0.5 documentation and changelog and prepared the roadmap transition that was
  later refined into the Base 0.6 usability and core-mapping release.

## Required validation

Run from the repository root:

```bash
backend/.venv/bin/python -m ruff check backend
backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

Also verify:

- a fresh database migrates and boots;
- a model 0.4 database upgrades without losing its active release or runtime data;
- the packaged wheel contains every Alembic revision;
- model-admin mutation routes are absent by default and work only in the documented supported mode;
- the generated OpenAPI document contains bounded collection schemas and structured error examples.

## Definition of done

Base 0.5 is complete only when:

- model runtime, metadata and UI use one coherent immutable release snapshot;
- validation and compilation are side-effect-free;
- draft writes and activation use optimistic concurrency;
- incompatible releases cannot be activated and installed releases cannot be edited;
- all object/relation/history collections are bounded and workspace-consistent;
- generic UI behavior is proven with two object types and a non-default workspace;
- the workbench contains no starter-key branches and mutation is disabled by default;
- migrations, tests, linting, production build and documentation all pass.

Do not begin the Base 0.6 mapping slice by bypassing an unfinished Base 0.5 contract. The mapping grid
should consume the paged relation/query foundation delivered here rather than adding a second
relation-expansion API.
