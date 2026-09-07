# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Corrective Base 0.6 WP6 persistence: workspace drafts and immutable workspace revisions own the
  runtime graph. The migration converts only unambiguous Base 0.5/rejected-WP4 workspace graphs,
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

### Added

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
  corrective WP5 froze workspace-level journeys, fixtures and API design; WP6-WP8 replace the
  persistence, API and UI boundary. These object-lifecycle APIs are not a compatibility commitment.

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
