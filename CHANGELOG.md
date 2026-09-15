# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Build 0.7 WP-5 review: enforce ancestor-scoped constraints against the final replacement graph,
  and reject missing required ancestors in generic draft relation writes as in live writes. Reject
  required-ownership replacement irrespective of relation orientation. Explicit empty application/view
  keys fail validation instead of selecting unconfigured reads. Twelve HTTP regressions cover these
  boundaries, preserved tokens and valid replacements within one ancestor scope.

- Build 0.7 WP-10B: draft activation now refuses new, removed or updated live relations in exact
  mutable binding sets the draft touched, including previously unmapped sets. It compares the
  immutable source/live edge identities and versions before applying any rows. Refusals preserve
  the draft, live data and revision designation and include bounded mapping-set diagnostics with
  recovery instructions. Unrelated live mapping work and existing containment/ownership merge
  behavior remain covered. WP-5 acceptance adds independent-binding isolation, required-ownership
  and clearing refusals, and overlapping generic create/update/delete versus mapping saves.

- Build 0.7 WP-10A, found in WP-4 review: confirmed live/draft object cascades now advance both
  directional relation-set versions for removed edges. Stale mapping target continuations return
  `409 mapping_version_conflict` with refresh guidance; previews and rejected deletes leave versions
  unchanged. Regression coverage exercises both directions and contexts.

- Build 0.7 WP-1/WP-2 review fixes: scope accessibility exceptions to known targets and node counts,
  fail visual comparisons on missing baselines outside explicit update mode, reject `mappingGrid`
  under schema 0.5, and allow the documented offline schema 0.4 recovery to select a compatible
  schema 0.5 or 0.6 candidate. The CLI reports expected refusals without a traceback, and the draft
  context regression now checks the current named-draft and version presentation. Visual capture
  waits for loaded panels, and the model-workbench baseline now covers the loaded release detail.

### Changed

- Build 0.7 WP-14 composes model-defined table and mapping views as lenses of one contextual
  collection. One application browser now presents virtual collection groups alongside runtime
  hierarchy records, replacing the separate Browse hierarchy / Views modes. Direct-parent scope,
  typed field facets and mapping coverage state are visible and URL-backed. Mapping coverage applies
  parent/state filters before cursor pagination in live, draft and immutable-revision contexts, and
  cursor fingerprints bind both values. This remains generic over configured applications, object
  types, relations and renderers; Master, Systems and Translations remain starter examples.

- The WP-8A/WP-8B review retained atomic mapping actions while removing duplicate configured name
  columns and requiring explicit review before retrying after a mapping-version conflict. Historical
  mapping reads now use revision projections and expose no mutation controls. Focused package evidence
  covers both configured mapping directions, direct-parent scope, visible mapping-state filtering,
  live replacement, narrow layout and the composed page's accessibility. WP-9 still owns comprehensive
  suites and visual-baseline release acceptance.

- Extended the planned 0.7 design and delivery documentation after plan review: WP-1–WP-3 remain
  frozen; later packages specify bounded view-based mapping reads, stable retained relation identities,
  typed attributes, direction-aware constraints and atomic whole-candidate draft compatibility.
  Mapping UI is split into WP-8A coverage and WP-8B actions; WP-9 expands integration/a11y/visual
  evidence, with conditional WP-10 for confirmed foundation gaps. This is documentation work, not
  implementation delivery or release acceptance evidence.

### Added

- Build 0.7 WP-7 browser draft version selection (ADR-028 frontend). Draft creation offers an
  optional model-release selector when multiple releases are installed; default is the active release.
  Draft list cards and detail header show each draft's model release key and version. An informational
  banner explains the state when a draft's version differs from the active release, and activation is
  disabled with a tooltip. A "Change model version" action in secondary draft actions loads available
  releases, attempts the pin change via the WP-6 PATCH endpoint, shows incompatibility diagnostics
  on failure and reloads the model context on success. Dirty-input protection via the existing
  `allowNavigation()` guard before applying version changes. Model-context refresh after pin change
  reloads the draft, pinned model and active release state; external pin change detection via
  `useEffect` + `useRef` in `LoadedDraft`. `WorkspaceDraft` type extended with `modelReleaseKey` and
  `modelReleaseVersion`. 169 frontend tests (5 new), zero lint errors, production build passes.

- Build 0.7 WP-5 atomic mapping replacement API: `PUT /api/v1/workspaces/{workspaceKey}/mappings`
  atomically creates, replaces or removes a mapping for one source in a configured relation binding.
  Supports live and draft contexts with optimistic concurrency via `expectedMappingVersion` and
  `expectedWorkspaceDraftVersion`. Direction-aware cross-cardinality enforcement (one-to-one always,
  one-to-many outgoing only). Retained relation identity when resolving ambiguous→mapped. Typed
  attribute semantics: omitted preserves retained edge values, explicit replaces, `{}` clears. Null
  target with non-empty attributes rejected. Idempotent no-ops with valid tokens produce no version
  increment or audit event. Stale tokens return `409 mapping_version_conflict` with bounded preview.
  Single-direction set version increments avoid double counting. Containment and required-ownership
  bindings rejected. Mapping-transition audit events with old/new targets and relation identities.
  After acceptance follow-up: 73 replacement/activation integration tests; 486 backend tests pass
  on SQLite.

- Build 0.7 mapping list API: `GET /api/v1/workspaces/{workspaceKey}/mappings` returns cursor-paged
  live/draft edges with optional binding, direction and name filters, directional set tokens, stored
  typed relation attributes and optional view-specific projections. Omitting direction returns both
  orientations of each edge; this supplements source-grouped coverage for integration reads.

- Build 0.7 WP-4 mapping query APIs: workspace-scoped coverage, candidate search and version-bound
  target details resolve the selected `mappingGrid` view under the live or draft-pinned model.
  SQL pagination and batched reads return typed projections, mapped/unmapped/ambiguous states,
  exact counts and at most 20 target summaries with explicit continuation. Cursors bind workspace,
  context, model release, view, direction and query configuration. The mapping
  browser workflow remains pending; replacement was subsequently delivered in WP-5. The WP-4
  reviewed backend suite passed 401 tests on SQLite;
  this does not establish composed product 0.7 or browser acceptance.

- Schema 0.6 `mappingGrid` view contract (Build 0.7 WP-2). The model language now accepts
  `schemaVersion: "0.6"` alongside `"0.5"`. `MappingGridViewDefinition` joins `TableViewDefinition`
  in a Pydantic discriminated union on `ViewDefinition.type`. Backend validation checks relation
  binding existence, rejects containment (`parentOf`) and required-ownership bindings, validates
  source/target columns against attached attributes, and verifies candidate search fields are
  searchable target-type attributes. The starter model advances to schema 0.6 / content release 0.7.0
  with two mapping grid views: `system-to-master-mapping` (outgoing) in RDM Systems and
  `master-to-system-mapping` (incoming) in RDM Master. Frontend `ViewDefinition` is a TypeScript
  discriminated union with type-safe narrowing; its initial placeholder was subsequently replaced by
  the WP-8/WP-14 contextual lens. 11 new backend tests cover parse, activation, backward compatibility
  and all validation rejection paths.

- Relation-set version persistence and generic participation (Build 0.7 WP-3). Every generic relation
  write (create, update, delete) now atomically maintains exact-binding set versions in both the
  outgoing and incoming directions. The `relation_set_versions` table tracks the optimistic version
  of each (workspace, optional draft, relation type, from/to object-type pair, anchor object,
  direction) combination. Rows are created lazily on first touch with version 1; untouched sets have
  implicit version 0. Draft-scoped and live-scoped versions are independent. Draft deletion cascades
  set-version rows; draft activation merges draft mutation counts into live set versions. A partial
  unique index protects live-context uniqueness where `workspace_draft_id IS NULL`. 9 focused tests
  cover all mutation paths, independent bindings, draft/live isolation, cascade and activation merge.
  All 379 backend tests pass.

- UI-07 automated accessibility and visual-regression gates (WP-1). `npm run test:a11y` runs
  axe-core WCAG 2.1 AA checks on 9 core page types across two object types; `npm run test:visual`
  compares viewport screenshots against committed baselines using pixelmatch. ~16 color-contrast
  violations fixed, definition-list structure corrected, sidebar landmark added. Two known violations
  allowlisted with tracked references. Light-theme baselines committed; dark-theme baselines deferred
  until a dark theme exists.

## [0.6.0] - 2026-09-11

### Changed

- Implemented WP8.1-A model authority boundaries. Compatibility now examines all authoritative live
  objects, attributes and relations, including catalogue-retired workspaces. Draft and historical
  reads resolve their pinned supported model before filters, typed responses and relation expansion;
  missing, corrupt or unsupported pins and workspace-context mismatches return structured errors.

- WP8.1-B captures an immutable current-live draft base including post-publication edits, model and
  record versions, with live data that has no prior publication. Historical source remains separate.

- WP8.1-C delivers newest-first revision history with deterministic cursor retry. Designation
  retirement preserves live access and history; catalogue retirement rejects writes.

- Reviewed the uncommitted WP8 implementation against the live/draft API contracts. Corrected
  activation and cascade deletion ordering, association confirmation and ownership checks, atomic
  draft version claims, public relation UUID reads, retired-workspace publication guards, and
  read-only attribute handling, draft containment validation and cross-workspace ID collisions.
  Added request-boundary and audit-migration regression coverage. Cascade confirmation now requires
  the signed token from the exact displayed preview and rejects any intervening hierarchy change with
  no deletion or audit side effects. Missing tokens are rejected before stale-version checks, draft
  deletion verifies the route object type, live deletion serializes against workspace retirement and
  inconsistent cross-workspace graph edges are refused. The frontend adapter carries both live and
  draft confirmation context.

- Reconciled technical documentation and delivery planning with the accepted product stories and
  GAP-01–GAP-08 answers. ADR-027 consolidates live data, optional copied drafts, immutable history,
  truthful publication retirement and newest-first history. Corrected API documentation against
  current payloads and cursor behavior.

- Implemented ADR-026 live active data writes: the active workspace is live-writable for **data**.
  `workspaceDraftId` is optional on record writes — present stages into the design draft; absent
  writes directly to the live active object store (record `expectedVersion` claim + audit, no
  workspace revision). Active reads resolve the live projection; activation is a delta-merge of the
  draft onto current live content with per-record version conflict detection (`version_mismatch` /
  `id_collision` / `duplicate_edge`), merged-graph validation and a merged revision snapshot that
  preserves live-only records. Restored `services/objects.py` CRUD functions, `services/relations.py`
  helpers and `services/deletion.py` as the live write path basis; added the workspace-audit seam and
  a corrective migration widening the audit `aggregate_id` column to host live object/relation ids.
  Amends ADR-024/ADR-025 write-context clauses for data content.

- Corrective Base 0.6 WP6 persistence: workspace drafts and immutable workspace revisions own the
  staged/historical graph; ADR-026 subsequently restores live-row current-data authority. The migration
  converts only unambiguous Base 0.5/rejected-WP4 workspace graphs,
  preserves public object and relation UUIDs, and removes per-object lifecycle persistence.

- The backend now requires Python 3.14. The local version pin, package metadata, Ruff target, CI
  runtime, container base image and development documentation all use 3.14; Python 3.12
  compatibility is no longer maintained.

- Frontend structure refactor, phases 0–4 of `docs/FRONTEND_STRUCTURE_REFACTOR.md`. No API
  contract, model contract or architectural change. `frontend/src` is reorganized into `app/`,
  `features/`, `ui/`, `model/`, `routing/`, `lib/`, `types/` and `styles/`, with every internal
  import going through an `@/` alias. `types.ts` and `utils/model.ts` are split by concern behind a
  barrel, the four overloaded components are split into 28 modules, and `styles.css` becomes four
  layers whose built output is byte-identical.

- The generic view and panel registries are rendered as elements rather than called as functions.
  Nothing was broken, but a panel component gaining state would have made `ObjectDetail`'s hook
  order depend on which panels a model declares as visible. The panel registry is keyed by the
  `PanelDefinition` discriminant, removing its per-entry casts, and both registries now live in
  their own modules.

- Client error handling is consolidated in `api/errors`. `isApiError` replaces five untyped casts
  used to detect optimistic-concurrency conflicts, and `errorMessage` replaces 36 inline
  expressions. Seven messages that reached the UI as `Error: …` now read like every other message.

- Cursor paging and search debouncing are consolidated into `useCursorPages`, `useCursorFeed` and
  `useDebouncedValue`, replacing two incompatible paging implementations across seven components.

- Every dialog shares one modal shell, `ui/Modal`. Five dialogs previously rebuilt the same backdrop
  and disagreed about its behavior. `ObjectFormDialog`, `AttributeValueDialog` and
  `RelationFormDialog` now close on Escape and return focus to whatever opened them; Tab is trapped
  inside an open dialog; the page no longer scrolls behind one; and two dialogs that carried
  hardcoded `aria-labelledby` ids now generate them, so opening two cannot produce duplicate ids.

- Frontend redesign (UI-01–UI-06). Compact neutral sidebar with workspace/application/view
  navigation; Browse hierarchy default with browser-local expand/collapse persistence; accessible
  mobile navigation drawer. Focused collections with search, typed filter popover, sort, display
  controls, sticky headings, comfortable/compact density and mobile-aware column prioritisation.
  Full-width record inspector with collection-origin preservation through reload/Back/Forward,
  contextual action menus, dirty-edit navigation guards and cross-application related-record return.
  Inline typed field editing with explicit save/cancel, null/removal distinction, saved/error
  feedback and retained coherent multi-field forms. Pointer and keyboard resizable navigation rail,
  inspector and table columns with browser-local display preferences. Refined draft catalogue,
  named-draft strip, consistent error/loading/empty/confirmation treatment and composed
  desktop/mobile visual review. UI-07 (automated accessibility and visual-regression gates) is
  deferred to 0.7.

### Added

- WP9 complete generic browser tasks in live, draft and history contexts. Slice A implements live
  workspace navigation with cursor-position restoration and retry/content preservation. Slice B
  implements direct live Add/Edit/Delete with typed fields, ordinary relationships and translations,
  conflict reconciliation and signed deletion confirmation. Slice C implements optional current-live
  drafts, shared draft authoring, validation, activation and discard with aggregate concurrency and
  conflict feedback. Slice D implements newest-first immutable history, pinned-model reads, historical
  draft sources and truthful publication retirement. SC-01–SC-06 and SC-08 have isolated real-backend
  browser evidence with two configured object types at desktop and 390px mobile widths.

- WP10 composed release validation: product scenarios exercised against a real browser and backend,
  including live CRUD without a draft, optional staging, current-live draft bases, concurrency and
  delta merge, whole-graph atomic failure, live-only compatibility and pinned historical typing.
  Keyboard/focus/narrow-layout journeys, migration/lifespan, packaging and public-contract checks.
  Automated accessibility and visual-regression tooling (UI-07) is deferred; manual keyboard and
  focus checks are recorded.

- Base 0.6 WP7 corrective CRUD restoration: the established generic object, attribute, relation and
  translation CRUD contract is restored over WP6 workspace storage. Originally draft-scoped, it was
  extended by ADR-026 to direct live writes plus optional drafts. No per-record lifecycle or nested
  public CRUD resources are introduced, and the
  original CRUD, attribute, cascade and translation suites are restored and enabled.

- Base 0.6 WP8 workspace lifecycle orchestration. Root and
  history-derived workspace drafts, whole-graph validation, atomic activation that writes one immutable
  workspace revision of the merged live graph and applies authored changes in one transaction after the
  ADR-026 correction,
  cursor-paged immutable revision history, and publication retirement under an expected active-revision
  claim. Draft/revision/validation/activation/retirement events use dedicated workspace aggregates with
  bounded identity payloads, kept separate from record-level `object-draft` and `relation` audit
  events. Objects, typed attributes, containment and relations remain ordinary records through the
  canonical generic CRUD routers; no per-object lifecycle or nested workspace-draft CRUD resources
  exist.

- Database migration failures now produce a credential-safe operator message with the current and
  target revisions, recovery command, backup requirement and escalation details. Startup enters
  maintenance mode without a traceback, and the WP4 migration safely retries recognized empty SQLite
  DDL left by an interrupted attempt. Real-database startup, restart and interruption regression tests
  cover the failure that previously left the development application unable to boot.

- Base 0.6 authoritative runtime-object revisions. Stable logical objects now own model-pinned,
  optimistic drafts and immutable active/retired snapshots with separate derivation and supersession
  lineage. Root and historical drafts, explicit activation, cursor-paged history, retired discovery,
  direct retirement and ownership-cascade retirement are public API contracts. Activation publishes
  core fields, typed attributes, containment and required relationships atomically; independent
  associations and published identity survive retirement. The Alembic transition preserves object
  UUIDs, migrates known active/draft/retired rows and rejects unknown legacy states with counts.
  Post-implementation hardening conditionally claims the final draft version during activation,
  prevents compatibility adapters from drifting the lifecycle projection and rejects corrupt
  cross-workspace retirement graphs.
  This pre-release design was subsequently rejected as the wrong publication boundary. ADR-024 and
  corrective WP5 froze workspace-level journeys, fixtures and API design; WP6 supplied the corrected
  persistence, WP7 restored generic CRUD and WP8 completed workspace orchestration, with WP9-WP10
  delivering the UI and release validation. These object-lifecycle APIs are not a compatibility
  commitment.

- Frontend lint and format tooling: ESLint 10 with `typescript-eslint` and
  `eslint-plugin-react-hooks`, and Prettier. `AGENTS.md` listed "linting passes" in the definition
  of done, but the frontend had no linter. Dependencies are pinned instead of `"latest"`, build
  tooling moves to `devDependencies`, and the Dockerfile uses `npm ci`; TypeScript is pinned to 6.x
  because `typescript-eslint` cannot yet parse with the TypeScript 7 native compiler.

- An application-level smoke test covering the extracted router: model-driven shell rendering, deep
  collection URLs, fallback when a URL names a retired application, and returning from an object to
  the collection and workspace it was opened from.

### Fixed

- A detail panel naming an object type that a later release retired now reports it instead of
  crashing the detail screen through a non-null assertion.
- Modals restore focus to their opener even when a form field uses `autoFocus`; cursor feeds ignore
  late load-more responses after their query changes or reloads; and cancelling a failed relationship
  deletion clears its action-specific error without blocking relation paging.

## [0.5.0] - 2026-09-05

### Added

- A global model workbench with always-readable installed releases and capability-gated JSON draft
  creation/import/editing, validation diagnostics, canonical compilation, semantic comparison,
  browser export, immutable installation and guarded activation. Optimistic conflicts preserve local
  input, and mutation controls remain absent by default.

- Base 0.5 generic object-management UI. Workspace context is explicit in the app shell and URLs;
  collection search, repeatable state filters, built-in sorting and page size survive browser
  navigation; generic rows expose existing edit/delete semantics; failed collections, panels and
  lookups are retryable; and object details show bounded, incrementally loaded audit history.

- Base 0.5 object and relation query foundations. Object collections now support repeatable state
  filters and stable built-in sorting through signed, filter-bound keyset cursors. Relation expansion
  is a bounded workspace-checked page, and object history uses an indexed audit-subject projection to
  include object, attribute and connected-relation events without exposing internal sequences or full
  before/after payloads.

- Base 0.5 guarded model activation. Compatible installed releases can be selected with both expected
  runtime version and active-release tokens; incompatible runtime data and stale selections return
  structured conflicts. Activation commits before refreshing the process registry, records old/new
  release IDs and hashes, marks health unhealthy on refresh failure, and rejects mutation enablement
  when `WEB_CONCURRENCY` configures multiple workers.

- Base 0.5 persisted model drafts and immutable installation. Mutation-gated draft APIs support
  optimistic version claims, side-effect-free compilation and atomic content-addressed installation;
  lifecycle audit events retain hashes and identities without copying complete model JSON. The
  capabilities endpoint reports the effective read, draft, installation and activation surface.

- Base 0.5 model compilation and comparison: inline validation returns stable diagnostic codes and
  JSON Pointer paths; installed releases can be compared by semantic, key-based paths; and bounded
  runtime-data checks classify candidates as compatible or migration-required without persisting or
  activating content.

- Base 0.5 model runtime authority: a singleton, versioned database row selects the active immutable
  release; source JSON is bootstrap input only. Requests resolve one cached model/release snapshot,
  `GET /api/v1/model` exposes its hash and release UUID in response headers, and cursor-paged release
  catalogue/detail APIs expose installed snapshots without enabling mutations.

- Complete model-driven Translation CRUD. Translations contain optional translated name, description
  and value fields (with at least one required), belong to a Translation Group, and atomically bind to
  exactly one configured target object. Domain, Codelist and Master Value targets are enabled in the
  starter model; future target types require only another JSON allowed pair. Duplicate active
  target/Language translations are rejected, inactive historical records may coexist, required
  bindings cannot be unlinked, and owner cascade deletes the Translation.

- Optional, model-driven Domain/Codelist-to-System Value representation relationships. Domain and
  Codelist details expose outgoing representations, while System Value details expose their incoming
  reference structures. These associations do not alter system containment and cascade deletion only
  unlinks them. System Value relation tables show the containing System through a generic ancestor
  column and can omit their constant relationship-label column.

- Optional transactional cascade deletion for runtime objects. A non-cascade delete with dependencies
  now returns a structured, non-mutating impact report; the UI renders the affected child objects,
  PK/FK dependents and relationships before allowing explicit cascade confirmation. Cascades delete
  containment descendants, unlink independent relationships and follow directed, required
  single-valued bindings from owner to dependent.

- Model-driven runtime CRUD in the React UI: object create/edit/delete, individual attribute-value
  add/edit/remove, and direction-aware relationship create/edit/delete. Relationship choices come from
  configured panels and allowed object-type triples; candidate lookup is server-side and can cross
  application boundaries within a workspace. Engine-maintained containment edges remain visible but
  immutable.
- A structured frontend `ApiError`, shared typed field renderer, paged object lookup and accessible
  destructive confirmation dialog. Optimistic-concurrency, dependency, uniqueness and cardinality
  failures remain recoverable in their active UI context.

- Standalone object-scoped CRUD for attribute values:
  `GET`/`POST`/`PATCH`/`DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}`.
  A single stored value can now be read, set, updated or removed without rewriting the whole object.
  Mutations require the object's `expectedVersion`, return the full object response, and enforce the
  same validation, read-only/required and workspace-uniqueness rules as object writes. Deleting a value
  on a required or read-only attribute is rejected (`422 cannot_delete_required_attribute` /
  `read_only_attributes`).
- Read-one, update and delete for relation instances:
  `GET`/`PATCH`/`DELETE /api/v1/relations/{relationId}`. `PATCH` replaces relation `attributes`
  (relation identity is immutable) and, like `DELETE`, claims an atomic `expectedVersion`
  (`409 version_conflict` on a stale claim). Engine-maintained parent-containment and hierarchy
  relations — those named in the target object type's `behavior.parentRelationTypeKeys` — are rejected
  for direct create/update/delete with `422 immutable_relation`; they stay atomic through object parent
  operations.
- Workspace-scoped attribute uniqueness for attribute types that declare `features.unique`. Create and
  update now reject a colliding value with `409 duplicate_attribute_value`. Uniqueness is enforced per
  attribute type within a workspace, and declaring `unique` on a `json` value type is rejected at model
  load.
- Frontend unit-test setup (Vitest + Testing Library) covering the model helpers and the generic
  renderers with two object types, run locally and in CI via `npm test`.

### Changed

- The bundled starter content release is now `0.5.0`; its model-language `schemaVersion` remains
  `0.4` because Base 0.5 did not change the declarative schema contract. Existing databases retain
  their database-selected active release until an administrator deliberately activates another
  installed release.
- Release operations now have documented backup and rollback boundaries: back up before migrations,
  use activation for compatible model-content rollback, and restore the matching database backup for
  application/schema rollback rather than editing immutable releases or relying on Alembic downgrade.

- Hardened the Base 0.5 WP2/WP3 lifecycle foundation after review: compatibility checks now include
  numeric relation attributes and enforce cardinality across every allowed pair sharing a relation
  type; compiler diagnostics retain stable paths for top-level validation failures; semantic diffs
  preserve real JSON `null` values and ignore ordering in set-like key collections; and concurrent
  installations are serialized in the supported single-process administration topology.

- Metadata collection endpoints now use opaque cursor pagination with a documented page-size limit.
- Attribute-value response items now include their stable public UUID `id`.
- Relation `fromObjectId`/`toObjectId` and object `parentObjectId` are now validated as UUID v4,
  returning `422 request_validation_error` for non-UUID values.
- Alembic migrations are now the single source of schema truth: the initial migration provisions a new
  database and upgrades an existing one, and startup no longer runs `create_all`.
- Object ancestor paths are resolved in level order (one query per depth level) instead of one query per
  object, removing the N+1 traversal on collections.
- Developer tooling: `.python-version` pins Python 3.12, and generated `*.egg-info`/`*.tsbuildinfo`
  artifacts are removed from version control.

### Fixed

- Model release snapshots are recursively immutable, metadata and release cursors are signed and
  filter-bound, model ETags use valid quoted entity-tag syntax, and release timestamps are normalized
  to UTC even when SQLite returns naive datetimes.
- Relation create and update now reject attributes not declared by the matched allowed pair and
  validate declared values through their global attribute types before persistence.
- Duplicate many-to-many edges supplied through atomic object `initialRelations` now return
  `409 duplicate_relation` and roll back the new object instead of escaping as an internal error.
- The initial Alembic revision now owns a frozen schema snapshot rather than importing live ORM
  metadata, keeping fresh-database upgrades reproducible as later revisions are added.
- Object creation preserves `false` for optional boolean attributes without a configured default
  instead of treating that value as absent.
- Object and standalone attribute-value writes now share an atomic expected-version claim, preventing
  concurrent requests from accepting the same object version and silently overwriting one another.
- Standalone attribute-value `GET` responses now include `objectVersion`, allowing clients to obtain
  the concurrency token required by `POST`, `PATCH` and `DELETE` without fetching the full object.
- Objects that have a parent can now be deleted. Deleting such an object removes its parent containment
  relation atomically, while objects with child objects or non-parent relations (mappings, translations)
  still return `409 object_has_dependents`.
- Partial updates no longer let a required attribute be cleared. Providing a required attribute as
  `null` or empty in a `PATCH` returns `422 missing_required_attributes`; omitting it remains allowed.
- `validation.minimum`/`maximum` on a non-numeric attribute type no longer causes a server error. These
  bounds now apply only to `integer`/`decimal`; non-numeric, non-finite, inverted or misplaced bounds
  are rejected at model load.
- The object form's parent picker now pages through all candidate parents instead of truncating at the
  first page, so a parent beyond the first page is no longer silently lost when editing.

## [0.3.0] - 2026-09-02

Baseline executable vertical slice of the generic reference-data engine: the versioned JSON model
(schema 0.3) as the source of truth for applications, object types, global attribute types, relation
types, allowed object-type triples and UI views, with a FastAPI backend, immutable model releases,
typed attribute storage, cursor-paginated APIs and a generic React UI.
