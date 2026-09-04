# Project status

## Current baseline

Model release `0.4.0` is an executable vertical slice of a generic reference-data engine. The versioned JSON
model is the source of truth for applications, global attribute types, object types and bindings,
relation types, allowed source/relation/target triples and UI views.

The starter model contains three configurable applications—RDM Master, RDM Systems and RDM
Translations—but the runtime contains no branches for those names or their object-type keys.

Base 0.5 WP3 is complete. The singleton database runtime-state row selects the authoritative installed
release, and source JSON remains bootstrap input only. Each request uses one immutable model and
metadata snapshot. Read-only release APIs now include key-based semantic diff and bounded runtime-data
compatibility analysis, while inline model validation returns stable JSON-path diagnostics without
persistence side effects. Mutation-gated, versioned drafts can be edited and compiled, then installed
atomically as inactive immutable releases without changing the active runtime selection.

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

- `model/rdm-starter.json`: schema-language 0.4 model with 22 attributes, 9 object types, 13 relation
  types, 16 allowed triples, three applications, collection views and typed detail compositions. Domain
  and Codelist objects can have optional System Value representations without joining the independent
  system containment hierarchy.
- Translation objects support translated name, description and value content, are contained by a
  Translation Group, and have exactly one required target chosen from every explicitly configured
  translatable Master object type. Active Target and Language combinations are unique.
- `backend/app/models/schema.py`: executable model contract with uniqueness, cross-reference and parent
  relation validation.
- `backend/app/services/model_compiler.py`, `model_diff.py` and `model_compatibility.py`:
  side-effect-free canonical compilation, stable JSON-path diagnostics, key-based structural diff and
  bounded runtime-data compatibility checks exposed through validation and release-diff APIs.
  Compatibility covers object and relation attribute constraints and relation-type-wide cardinality;
  diffs distinguish JSON null from omission and ignore ordering for set-like stable-key memberships.
- `backend/app/services/model_drafts.py`, `model_releases.py` and the model-management router:
  persisted draft CRUD with optimistic concurrency, side-effect-free draft compilation and atomic,
  idempotent immutable installation serialized across drafts in the supported single-process
  topology. Complete model JSON is excluded from lifecycle audit payloads, and all write routes are
  absent unless model administration mutations are enabled.
- `backend/app/models/database.py` and `backend/app/db.py`: immutable model-release metadata plus runtime objects, typed attribute
  values, typed relations and audit events.
- `backend/app/services/attributes.py`: attribute validation, defaults and typed persistence conversion.
- `backend/app/routers` and `backend/app/services`: metadata discovery, generic object CRUD,
  search/cursors, concurrency checks, hierarchy maintenance, relation instance CRUD
  (create/read-one/update/delete) with optimistic concurrency, cardinality checks and model-declared,
  typed relation attributes — engine-maintained
  parent-containment relations are read-only through the relations API; object-scoped attribute-value
  endpoints
  (`GET`/`POST`/`PATCH`/`DELETE` on `/objects/{type}/{id}/attributes/{attributeTypeKey}`) set, read,
  update and delete single stored values with the same validation, uniqueness and object-version
  concurrency as object writes. Standalone reads expose the current object version, and mutations
  atomically claim that version before writing; `backend/app/main.py` contains application assembly
  only.
- Workspace-scoped attribute uniqueness for `features.unique` (`409 duplicate_attribute_value`) and
  transactional object deletion with a structured dependency preview and explicit cascade option.
  Cascade recursively deletes containment descendants, unlinks independent associations, and follows
  directed required single-valued PK→FK bindings to dependent objects.
- `backend/app/migrations`: versioned Alembic database migrations are the single source of schema truth;
  the initial migration provisions new databases and upgrades existing ones, and startup runs only
  `alembic upgrade head`.
- `frontend/src`: model-generated application/view navigation, searchable runtime explorer, stable
  routes, view and panel component registries, cursor-paged collections, composable object details and
  full runtime CRUD for objects, individual typed attribute values and mutable relationships. Relation
  creation derives valid endpoint types and direction from the loaded model, uses cross-application
  server-side lookup, and keeps engine-managed containment edges read-only.
  Required non-parent bindings are selected in the generated object form and created atomically with
  the new object and its containment relation.
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

## Known gaps

- Configured `mappingGrid` and `tree` views still resolve through the registry to the generic
  collection renderer; dedicated interactions are not implemented yet.
- Relation expansion is currently an unpaged object-detail query; high-volume relation tables need a
  cursor-paged expansion endpoint before production scale.
- Relations support full instance CRUD (create/read-one/update/delete with optimistic concurrency);
  bulk relation endpoints and a cursor-paged expansion remain.
- Attribute uniqueness is enforced at the service layer; a database-level unique constraint/index
  remains before multi-writer PostgreSQL deployment.
- Ancestor-scoped relationship uniqueness is enforced transactionally by the service layer; database
  hardening remains for multi-writer PostgreSQL deployment.
- Integration-grade filtering, sorting, bulk upsert, imports/exports, change feeds and webhooks remain.
- OIDC, permissions and PostgreSQL performance/index work remain.
- The starter model is representative, not a one-to-one migration of every supplied source type.

## Next vertical slice

Complete the bounded Base 0.5 operational foundation before building the dedicated mapping workspace:

1. **Done (WP1):** Make the database-selected installed release the single authoritative runtime
   model snapshot.
2. **Done (WP2):** Add validation, canonical compilation, semantic diff and runtime-data compatibility
   analysis.
3. **Done (WP3):** Add versioned drafts and immutable installation.
4. Add guarded, compatibility-checked activation.
5. Make workspace and URL-backed collection state explicit in the generic object UI.
6. Add stable built-in sorting, cursor-paged relation expansion and cursor-paged object audit history.
7. Add the lightweight JSON model workbench, with model mutations disabled by default.

See `docs/BASE_0_5_IMPLEMENTATION_PLAN.md` for the implementation-ready work packages and
`docs/ROADMAP.md` for the exit gate and sequenced milestones that follow.

The first three work packages are complete; WP4 (guarded activation) is next.

## Coding-agent handoff

Open the repository root, then start a new coding chat with:

> Read `AGENTS.md` and `docs/PROJECT_STATUS.md`, then summarize the current model and implement the next
> incomplete work package in `docs/BASE_0_5_IMPLEMENTATION_PLAN.md`. Preserve all product invariants,
> its scope boundaries and the work-package order. Before editing, report the current worktree status
> and identify the API, persistence, backend tests and generic UI components that will change.

Make a Git checkpoint before the first new slice. Run
`backend/.venv/bin/python -m ruff check backend`,
`backend/.venv/bin/python -m pytest backend/tests -q`, `npm --prefix frontend test`,
`npm --prefix frontend run build` and `git diff --check` before considering it complete.
