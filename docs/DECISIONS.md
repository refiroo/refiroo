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

## ADR-010 — Enforce attribute uniqueness at the service layer

**Status:** Accepted

Attribute types may declare `features.unique`. Uniqueness is enforced at create and update by the
service layer, scoped to a single workspace and to the attribute type key. This keeps the runtime
generic (no object-type or domain branches) and avoids inventing one physical unique index per dynamic
attribute type. `json` values are excluded because their equality is not order-stable; declaring
`unique` on a `json` type is rejected at model load. The tradeoff is a race window under concurrent
writers; a database-level constraint (partial unique index or a dedicated unique-key table) is the
planned hardening for PostgreSQL.

## ADR-011 — Relation instance CRUD mutates only non-parent edges

**Status:** Accepted

`GET`, `PATCH` and `DELETE /api/v1/relations/{relationId}` give mutable relation instances full read and
mutation support with the same optimistic concurrency as objects: mutations carry `expectedVersion`,
claim it atomically, and return `409 version_conflict` on a stale claim. Relation identity —
`relationTypeKey`, `fromObjectId`, `toObjectId` — is immutable; only the relation `attributes` are
updatable. Re-targeting an edge is expressed as delete + create.

Parent-containment and hierarchy edges — relation types named in the target object type's
`behavior.parentRelationTypeKeys` and written atomically on object parent changes — are
engine-maintained and therefore rejected by the relations API (`422 immutable_relation`). Keeping them
read-only prevents `parent_object_id` and the typed relation from diverging; reparenting always goes
through object parent operations, which rewrite both atomically.

Required non-parent relations remain readable and may update declared relation attributes, but cannot
be independently deleted because doing so would invalidate their dependent object. They are created
atomically with that object and removed through its lifecycle operation.

## ADR-012 — Preview destructive graph cascades and derive ownership from relation bindings

**Status:** Accepted

Object deletion remains non-cascading by default. When dependencies exist, the API returns a structured
impact report and mutates nothing; callers must repeat the request with `cascade=true` to authorize the
reported class of destructive operation. The cascade is recomputed and executed transactionally.

Containment descendants are always owned by their parent. For non-parent relations, only a directed
binding that is both `required` and single-valued at the target (`one-to-one` or `one-to-many`) carries
PK→FK ownership from the `from` endpoint to the `to` endpoint. Cascade follows that direction. Optional
and many-to-many relations are associations and are only unlinked. Cardinality alone is insufficient
to infer ownership, and mappings must not accidentally delete independent target objects.

## ADR-013 — Keep system containment separate from reference representations

**Status:** Accepted

System Values remain children of a System or System Group. A Domain or Codelist's representation in an
external system is expressed as the optional `reference-has-system-representation` association instead
of reparenting the System Value or duplicating it in the master hierarchy. The relation type permits
both Domain → System Value and Codelist → System Value bindings, with shared one-to-many cardinality so
a represented System Value belongs to at most one reference structure while each reference structure
may have multiple system representations.

This keeps lifecycle ownership with the system hierarchy. Deleting a Domain or Codelist with cascade
removes the association but preserves the System Value; deleting its System or System Group continues
to cascade through system containment independently.

## ADR-014 — Create required translation targets atomically

**Status:** Accepted

A Translation is contained by a Translation Group and is also a lifecycle-dependent representation of
exactly one translated object. The translated object therefore owns the Translation through the shared,
required `object-has-translation` one-to-many relation. Domain, Codelist and Master Value are explicit
allowed source types; later model releases extend the same relation with additional source types rather
than introducing runtime key branches or wildcard application membership.

Object creation accepts model-derived initial relationships so the Translation, its containment edge,
its target edge, attributes and audit events commit atomically. Required relations cannot be deleted
independently. `uniqueToAncestorTypeKey: language` with an `active == true` target condition prevents
duplicate active translations for one target and Language while allowing the same target in other
Languages and inactive historical records. Activation and hierarchy moves recheck the constraint.
