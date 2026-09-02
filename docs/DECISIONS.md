# Architecture decisions

## ADR-001 — Focus on RDM

**Status:** Accepted

The engine supports configurable applications but is optimized for reference data, mapping,
translation, hierarchy and integration—not general enterprise data governance.

## ADR-002 — Own an independent model language

**Status:** Accepted

Source packages and responses inform requirements but are not runtime contracts. The project owns its
schema, stable keys, database, API terminology and interface.

## ADR-003 — Use object–attribute–relation persistence

**Status:** Accepted; replaces the initial JSON-attribute prototype

Objects, typed attribute values and typed relations use separate relational tables. This aligns the
database with the meta-model and supports per-attribute typing, indexing, history and inheritance later.
Unlike the observed source API, typed values are not reduced to strings.

## ADR-004 — Separate definitions from bindings

**Status:** Accepted

Attribute and relation types are reusable global definitions. Object-type attribute bindings and
allowed object-type relation triples specify context, required/read-only behavior and cardinality.

## ADR-005 — Install immutable model releases

**Status:** Accepted

Validated JSON models are hashed and installed into versioned metadata tables. Existing releases are
not rewritten. Runtime objects reference stable keys so model migrations can be explicit.

## ADR-006 — Maintain containment and typed parent relations

**Status:** Accepted

Hierarchy uses `parent_object_id` for efficient navigation and a typed relation for semantics. The
service layer creates and moves both atomically and prevents cycles.

## ADR-007 — Generate UI behavior, not markup

**Status:** Accepted

The model selects semantic components. React owns layout, accessibility and visual quality. UI
configuration does not embed backend endpoints.

## ADR-008 — Cursor pagination is mandatory

**Status:** Accepted

Collection APIs have documented bounded pages. Full export uses a job or change feed, never an
undocumented `take: 0` convention.

## ADR-009 — Compose object details in the application model

**Status:** Accepted

Object types own reusable data semantics while applications own task-oriented detail composition. A
typed panel registry maps declarative `attributes`, `children`, `relations`, `table` and `hierarchy`
definitions to generic React components. This permits a shared object type to be presented differently
by two applications without backend URLs, markup, vendor element names or key-specific renderer
branches in the model.
