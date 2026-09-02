# Project status

## Current baseline

Version `0.3.0` is an executable vertical slice of a generic reference-data engine. The versioned JSON
model is the source of truth for applications, global attribute types, object types and bindings,
relation types, allowed source/relation/target triples and UI views.

The starter model contains three configurable applications—RDM Master, RDM Systems and RDM
Translations—but the runtime contains no branches for those names or their object-type keys.

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

- `model/rdm-starter.json`: schema-language 0.3 model with 21 attributes, 9 object types, 12 relation
  types, 12 allowed triples, three applications, collection views and typed detail compositions.
- `backend/app/model_schema.py`: executable model contract with uniqueness, cross-reference and parent
  relation validation.
- `backend/app/database.py`: immutable model-release metadata plus runtime objects, typed attribute
  values, typed relations and audit events.
- `backend/app/attribute_values.py`: attribute validation, defaults and typed persistence conversion.
- `backend/app/main.py`: metadata discovery, generic object CRUD, search/cursors, concurrency checks,
  hierarchy maintenance, relation creation/traversal and cardinality checks.
- `frontend/src`: model-generated application/view navigation, searchable runtime explorer, stable
  routes, view and panel component registries, cursor-paged collections, composable object details and
  shared typed create/edit forms.
- Tests cover model validation and a Domain → Codelist containment flow including the generated typed
  relation, search/cursor behavior, update concurrency and deletion behavior. Composition tests mutate
  panel order, visibility, fields and relation-table configuration without renderer changes.

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
- Relations can be created and traversed but do not yet have update/delete or bulk endpoints.
- Integration-grade filtering, sorting, bulk upsert, imports/exports, change feeds and webhooks remain.
- Alembic migrations, OIDC, permissions and PostgreSQL performance/index work remain.
- The starter model is representative, not a one-to-one migration of every supplied source type.

## Next vertical slice

Build a dedicated relation-driven mapping workspace without hardcoding the starter relation or object
type keys in the renderer:

1. Add a batched relation-expansion query suitable for a mapping grid.
2. Render source objects, candidate/selected target objects and mapping state from `view.config`.
3. Support unmapped/mapped filtering, create mapping, replace mapping and remove mapping.
4. Add optimistic concurrency and audit coverage for remapping.
5. Exercise the component with a second synthetic relation in tests to preserve generic behavior.

## Coding-agent handoff

Open the repository root, then start a new coding chat with:

> Read `AGENTS.md` and `docs/PROJECT_STATUS.md`, then summarize the current model and implement the next
> mapping-workspace vertical slice. Preserve all product invariants. Before editing, identify the API,
> model, backend tests and generic UI component that will change.

Make a Git checkpoint before the first new slice. Run `python -m ruff check backend`,
`python -m pytest backend/tests` and `npm --prefix frontend run build` before considering it complete.
