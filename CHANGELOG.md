# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
