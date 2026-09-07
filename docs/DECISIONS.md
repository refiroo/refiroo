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

**Status:** Accepted; lifecycle application amended by ADR-024

Hierarchy uses `parent_object_id` for efficient navigation and a typed relation for semantics. The
service layer creates and moves both atomically and prevents cycles.

ADR-024 changes when that mutation becomes effective. Changing a parent edits only the selected
workspace draft. Workspace activation validates cycles and atomically publishes both the active parent
projection and its typed containment edge; a published workspace revision is never changed in place.

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

**Status:** Accepted; lifecycle application amended by ADR-024

Attribute types may declare `features.unique`. Uniqueness is enforced at create and update by the
service layer, scoped to a single workspace and to the attribute type key. This keeps the runtime
generic (no object-type or domain branches) and avoids inventing one physical unique index per dynamic
attribute type. `json` values are excluded because their equality is not order-stable; declaring
`unique` on a `json` type is rejected at model load. The tradeoff is a race window under concurrent
writers; a database-level constraint (partial unique index or a dedicated unique-key table) is the
planned hardening for PostgreSQL.

Under ADR-024, draft validation may report a prospective uniqueness conflict, but workspace activation
is the authoritative check across the complete candidate graph after applying any model-declared
conditional uniqueness predicate. Historical workspace revisions do not reserve a unique value.

## ADR-011 — Relation instance CRUD mutates only non-parent edges

**Status:** Accepted; mutation scope amended by ADR-024

Active and historical relation routes are read-only. Draft-scoped `GET`, `PATCH` and `DELETE` routes
give mutable relation records full read and mutation support with the same optimistic concurrency as
draft object records: mutations carry `expectedVersion`, claim it atomically, and return
`409 version_conflict` on a stale claim. Relation identity —
`relationTypeKey`, `fromObjectId`, `toObjectId` — is immutable; only the relation `attributes` are
updatable. Re-targeting an ordinary edge is expressed as delete + create. ADR-022's mapping aggregate
is the intentional exception: it performs the required delete and create in one atomic set
replacement rather than exposing a partially changed mapping.

Parent-containment and hierarchy edges — relation types named in the target object type's
`behavior.parentRelationTypeKeys` and written atomically on object parent changes — are
engine-maintained and therefore rejected by the relations API (`422 immutable_relation`). Keeping them
read-only prevents `parent_object_id` and the typed relation from diverging; reparenting always changes
the workspace draft and workspace activation rewrites both atomically.

Required non-parent relations remain readable and may update declared relation attributes, but cannot
be independently deleted because doing so would invalidate their dependent object. They are created
atomically with that object inside the workspace draft and removed through draft deletion impact.

## ADR-012 — Preview destructive graph cascades and derive ownership from relation bindings

**Status:** Accepted; lifecycle application amended by ADR-024

Under ADR-024, deleting a record is a change to a mutable workspace draft. When candidate dependencies
exist, a deletion request returns a structured impact report and mutates nothing; callers must repeat
it with `cascade=true` to authorize recursive removal of the reported owned dependants from that
draft. The impact is recomputed and applied transactionally. Independent associations are removed or
retained according to their binding in the same candidate graph. Active and historical workspace
revisions remain unchanged until activation and forever afterward.

Any mutable workspace draft may be discarded with optimistic concurrency. Physical purge of stable
identities, published workspace revisions and audit history is a separately authorized retention
operation deferred beyond Base 0.6.

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

This keeps containment ownership with the system hierarchy. Removing a Domain or Codelist from a
workspace draft with cascade removes the association from that candidate graph but preserves the
System Value; removing its System or System Group continues to cascade through system containment.

## ADR-014 — Create required translation targets atomically

**Status:** Accepted; lifecycle application amended by ADR-024

A Translation is contained by a Translation Group and is also a lifecycle-dependent representation of
exactly one translated object. The translated object therefore owns the Translation through the shared,
required `object-has-translation` one-to-many relation. Domain, Codelist and Master Value are explicit
allowed source types; later model releases extend the same relation with additional source types rather
than introducing runtime key branches or wildcard application membership.

Translation creation inside a workspace draft accepts model-derived initial relationships. Activating
the workspace draft publishes the Translation, its containment edge, target edge, attributes and audit
events atomically with every other candidate change. Required relations cannot be deleted
independently. `uniqueToAncestorTypeKey: language` together with the model-declared `active == true`
business predicate is enforced across the complete candidate workspace graph. This prevents duplicate
available Translations for one target and Language while allowing unavailable current content and
immutable historical workspace revisions. Activation, including after a draft parent change, rechecks
the constraint.

## ADR-015 — Resolve one database-selected model snapshot per request

**Status:** Accepted

The singleton database runtime-state row is the authority for the active installed model release.
`MODEL_PATH` is bootstrap input only: startup validates and installs that content when needed, but a
different bootstrap file does not implicitly replace an already selected release.

Each request resolves runtime state once and uses the corresponding immutable parsed `EngineModel`
and metadata release for every model-dependent operation. The process registry may cache snapshots by
release public ID and content hash, but it must not independently choose the active release. This
prevents one request from combining JSON from one release with metadata rows from another.

## ADR-016 — Separate mutable drafts, immutable installation and activation

**Status:** Accepted

A model draft is mutable database content with a public UUID and an optimistic integer version.
Validation and compilation are side-effect-free. Installing a successfully compiled draft creates or
returns one content-addressed immutable release and its metadata projection; it does not activate that
release. The same content hash is idempotent, while reuse of a release key and version with different
content is a conflict.

Activation is a separate operation. Installed model JSON is never edited in place and model
administration never writes back to the server-side bootstrap file. This separation keeps authoring,
reproducible installation and runtime selection independently auditable.

## ADR-017 — Guard activation with runtime compatibility and deployment topology

**Status:** Accepted

Activation conditionally updates the singleton runtime-state row using both its expected version and
the expected active release public ID. Before that update, the candidate is parsed again and checked
against stored runtime data. A candidate requiring data migration is not activated by Base 0.5; the
operation returns structured compatibility diagnostics and changes nothing.

Model-administration mutations are absent unless `MODEL_ADMIN_MUTATIONS_ENABLED=true`. The flag is a
deployment safety guard, not authorization. While mutations are enabled, Base 0.5 supports only one
API process because it has no cross-process snapshot invalidation mechanism. The repository's
container command runs one Uvicorn process and is the supported topology. Multi-worker or multi-node
mutation enablement must be rejected until release propagation and identity-based authorization are
implemented.

The database commit is authoritative. A process publishes the newly selected immutable snapshot only
after commit; if refresh fails, readiness becomes unhealthy instead of serving a guessed or mixed
model.

## ADR-018 — Bind opaque cursors to query semantics

**Status:** Accepted

Collection cursors are opaque client tokens. A cursor encodes or integrity-protects the selected sort,
its unique sequence-ID tie-breaker and a fingerprint of all effective filters. Reusing it with a
different filter, direction or sort returns `invalid_cursor`; clients pass `nextCursor` back unchanged
and never parse it.

This permits built-in sorting and pagination to evolve without exposing database sequence IDs or
allowing a cursor to silently traverse a different result set. Every ordering is deterministic and
uses the internal sequence only as the final, non-public tie-breaker.

## ADR-019 — Persist and retire globally scoped workspaces

**Status:** Accepted

Workspaces are runtime-owned, globally scoped database records rather than definitions in an immutable
application-model release. A workspace administrator provisions them through a first-class
administration API. Until authentication and authorization are implemented, workspace mutation routes
are capability-gated and enabled by default. That flag is a deployment control, not an authorization
boundary; operators that expose the API outside a trusted environment must disable mutations or add an
external access-control layer.

Each workspace has an immutable, case-sensitive stable key, a mutable presentation label, an
`active` or `retired` status, timestamps and an optimistic-concurrency version. Keys are trimmed,
non-empty and no longer than 160 characters. New keys should use lower-kebab-case, but migration and
runtime behavior preserve existing keys without normalization. A workspace cannot be deleted or have
its key renamed in Base 0.6.

Exactly one active workspace is the default. Changing the default is atomic, and the current default
cannot be retired. Omitting `workspaceKey` resolves the catalogue's current default; an explicitly
supplied unknown key returns `404 workspace_not_found` and never falls back or implicitly provisions a
record. Active workspaces permit reads and writes. Retired workspaces remain discoverable and readable
for historical and audit access, while object, attribute and relation mutations in their scope return
`409 workspace_retired`.

The schema migration creates the `default` workspace and backfills every distinct key already stored
on an object. A backfilled non-default label initially equals its key. Objects then reference the
catalogue so future rows cannot introduce orphan workspace keys. Discovery is searchable and
cursor-paged; the UI shows labels, retains stable keys in URLs, identifies retired workspaces and does
not accept a free-text key. Base 0.6 requires the administration API but not a workspace-management UI.

The deployment flag is `WORKSPACE_ADMIN_MUTATIONS_ENABLED` and defaults to `true` until authentication
exists. Runtime capabilities expose `workspaceAdmin.manageWorkspaces` so clients can hide unavailable
actions without treating the value as identity or permission evidence. The administration contract is:

- `GET /api/v1/workspaces?search=...&status=active|retired|all&pageSize=...&cursor=...` for
  cursor-paged discovery, with `status=active` as the default;
- `GET /api/v1/workspaces/{workspaceKey}` for active or retired detail;
- `POST /api/v1/workspaces` for creation;
- `PATCH /api/v1/workspaces/{workspaceKey}` for label or status changes with `expectedVersion`;
- `GET /api/v1/workspace-runtime-state` and `PATCH /api/v1/workspace-runtime-state` for reading and
  atomically changing `defaultWorkspaceKey` with the runtime state's own expected version.

The singleton `workspace_runtime_state` row, rather than a mutable flag copied onto catalogue rows,
owns the default key and its concurrency version. There is no workspace `DELETE` route.

## ADR-020 — Version runtime objects through immutable revisions

**Status:** Superseded by ADR-024 before Base 0.6 release

This decision was implemented in WP4 and then rejected because it placed publication lifecycle on
individual records rather than on the workspace governance boundary. The text below is retained as a
record of the superseded design and must not guide new implementation.

Runtime object lifecycle is an engine-owned revision contract with `draft`, `active` and `retired`
states; it is not an open string or application-model extension. A stable logical object identity owns
immutable revisions. Active and retired revisions are read-only. Existing objects change only by
creating a mutable draft from a selected active or retired revision, editing that complete draft and
activating it. This contract does not increment the application-model `schemaVersion`.

An existing-object draft always clones a revision and is never an empty persisted document. A genuinely
new logical object begins with a root draft whose lineage source is null, but the create request must
supply the initial required object data rather than save a blank placeholder. Multiple drafts may
branch from the same or different revisions; each draft has its own optimistic-concurrency version.

Lineage records two distinct edges. `derivedFromRevisionId` identifies the immutable revision whose
content was copied into the draft. `supersedesRevisionId` identifies the revision that was active when
the draft was activated. Activating a draft derived from an earlier retired revision therefore keeps
that retired revision as its source while truthfully recording which later active revision it
replaced. Activation requires both the expected draft version and expected active revision identity,
revalidates the complete candidate and atomically retires the current active revision and promotes the
draft. A stale active identity returns a recoverable conflict and changes neither revision.

A revision snapshots object-owned content: core fields, parent, typed attributes and required ownership
relationships. Independent associations and mappings continue to target the stable logical object and
retain their own relation versions and audit history. The starter model's `active` boolean remains
business availability data and is independent of revision lifecycle.

The stable `objects` row owns public identity, workspace, application and object type. Revision and
draft tables are the write authority for object-owned content; draft edits never mutate a current
active projection.
Each revision or draft pins the immutable `modelReleaseId` used to validate its snapshot. Activation
requires the draft's pinned release to equal the workspace's currently resolved release. A mismatch
returns `409 draft_model_release_conflict`; rebasing a draft to another release is explicit future work.
When a draft is cloned from history, the source revision keeps its original release identity but the
copied candidate is validated against and pins the currently resolved release. Incompatible historical
content returns structured validation diagnostics and creates no partial draft.
Any query-optimized active columns or child tables are transactionally derived projections, never a
second write authority. Activation publishes the candidate snapshot and updates the stable object's
active-revision pointer and projections in one transaction.

The current active revision may also be retired without a replacement. The operation supplies
`expectedActiveRevisionId`, atomically clears the stable object's active pointer and retires that
revision. The logical object remains discoverable through retired/history queries and any active or
retired revision can seed a later draft and activation. Retirement is therefore distinct from
supersession and from any model-defined business-availability attribute.

Object history exposes a cursor-paged lineage with revision identity, lifecycle state, source,
superseded revision, timestamps and activation events. The UI labels both “Created from” and
“Superseded on activation”, renders active and retired snapshots without edit controls and offers
“Create draft from this revision” on either. Draft editing and activation remain explicit separate
steps, and conflicts preserve local draft input.

The migration converts each existing object and its current object-owned data into an initial revision:
`active` becomes active, `draft` becomes a root draft and `retired` becomes retired. Any other stored
state stops the migration with explicit affected values and counts; migration never guesses a lifecycle
meaning or silently rewrites data. Existing stable object IDs are preserved, and the current runtime
projection remains available for bounded queries and stable relation endpoints.

The API separates current, draft and historical concerns: active collection/detail routes return only
the current active projection by default; explicit retired discovery finds logical objects with no
active revision; draft list/detail/create/patch/delete routes manage mutable drafts; revision
list/detail routes expose immutable history; activation and retirement are explicit actions. More than
one draft may exist for a logical object. Immutable revisions and audit history are retained; physical
purge is outside Base 0.6.

## ADR-021 — Introduce strict typed views in schema 0.5

**Status:** Accepted

Schema 0.5 replaces the open top-level view configuration bag with a discriminated, extra-forbidden
contract for the implemented `table` view type. This is a model-language change, so it is not applied
retroactively to schema 0.4. New schema 0.5 releases cannot declare `mappingGrid`, `form`, `dashboard`
or `tree` views until those view types have typed contracts and honest renderers.

A table view requires one `objectTypeKey` and a configuration containing unique, non-empty `columns`,
`filterFields`, `sortFields`, a `defaultSort` and a bounded `pageSize`. Each field is a supported
built-in field or an attribute bound to the selected object type. Attribute value types determine the
filter operators and editors. The default sort must be one of the declared sort fields; a leading `-`
selects descending order.

The corresponding object query uses `filter.<field>.<operator>=<value>`. Filters on different fields
and operators combine with AND; repeated `eq` values for one field combine with OR. Text supports
`eq`, `contains`, `startsWith`, `isNull` and, for attributes, `isUnset`. Numbers, dates and datetimes
support `eq`, `lt`, `lte`, `gt`, `gte`, `isNull` and attribute `isUnset`; booleans support `eq`,
`isNull` and attribute `isUnset`. JSON is neither filterable nor sortable in this daily-use contract.
Values are parsed according to their declared type, dates and datetimes use ISO 8601 lexical forms,
`isNull`/`isUnset` take boolean values, and invalid input returns a path-addressable error. Exact
equality is case-sensitive; `contains` and `startsWith` are case-insensitive. Null and an absent
attribute remain distinct. A request selects one declared sort as `sort=<field>` or `sort=-<field>`.
Sorts place null and unset values last in either direction and always append a hidden unique internal
tie-breaker. API capability follows attribute features and types; a view's declared fields are the
UI-visible subset. Cursor fingerprints include the normalized filters and sort.

Mapping-grid configuration is deliberately not part of schema 0.5 or Base 0.6. The focused mapping
release will introduce schema 0.6 with the additional discriminated branch and the ADR-022 runtime
contract. This keeps schema 0.5 and the daily-operations release independently implementable.

The compiler dispatches explicitly by schema version and returns `unsupported_schema_version` with
the supplied and supported versions. Base 0.6 supports schema 0.5 as an active runtime model and does
not implement a schema 0.4 compatibility adapter. Immutable schema 0.4 releases may remain stored,
listed and exported as historical JSON, but cannot be activated or used as the selected runtime model.
Startup fails clearly when runtime state still selects one.

Because the project has no production compatibility commitment, development databases either reset
and bootstrap schema 0.5 or use the 0.6 distribution's one-shot offline schema-transition command
before starting its web process. That command opens the existing database without resolving a runtime
model, validates and installs the supplied schema 0.5 candidate, performs the normal runtime-data
compatibility analysis and atomically selects it with runtime-state concurrency. It changes nothing on
failure and is not a schema 0.4 request-time adapter.
The starter becomes content release 0.6.0 on schema 0.5; its currently declared tree is represented
honestly as a table until a typed tree contract exists, while its mapping view is omitted until schema
0.6 can represent and render that task honestly. Compatibility adapters are added only when a published
schema has an explicit support commitment.

Workspace-scoped model-release assignment is deliberately separate. It can later provide staged
tenant or governance-domain migration, but running workspaces on different schema-language versions
requires the engine to serve every pinned parser and contract concurrently; workspace pinning does
not remove that compatibility obligation. That future capability is sequenced with executable data
migration, protected administration and a bounded supported-version window.

## ADR-022 — Version complete relation sets for atomic mapping

**Status:** Accepted; amended by ADR-024

Mapping concurrency belongs to the complete directional relation set, not to an object or one relation
instance. A source object may currently have zero, one or several matching edges, so neither an object
version nor an individual relation version can protect create, remove, replace and ambiguous-state
resolution consistently. Under ADR-024, mappings target stable object identities inside one explicit
workspace draft and are published with that complete workspace revision; they never mutate active
relations directly.

`relation_set_versions` stores one optimistic integer version for an exact allowed binding:
workspace draft, relation type, `fromObjectTypeKey`, `toObjectTypeKey`, stable anchor object and `outgoing`
or `incoming` direction. Including both endpoint types prevents two allowed bindings of the same
relation type from sharing and replacing each other's set. Every generic relation create, attribute
update or delete atomically increments the outgoing and incoming sets for that exact binding.
Mapping-grid rows return this value as `mappingVersion`; a previously untouched set has version zero,
claimed safely under the scope's database uniqueness constraint.

`PUT /api/v1/workspace-drafts/{draftId}/mappings/{relationTypeKey}/{sourceObjectId}` accepts explicit direction,
`sourceObjectTypeKey`, `targetObjectTypeKey`, `expectedMappingVersion`, a nullable `targetObjectId` and
relation attributes. Endpoint type keys remain required when the target is null so removal cannot
broaden its scope. A null target removes the complete selected-target set and requires empty
attributes. A non-null target replaces the complete set with exactly that target, allowing one
operation to create, replace or resolve an ambiguous mapping. The service validates workspace and
draft status, candidate endpoint records, endpoint types, direction, the exact allowed relation binding,
cardinality and typed relation attributes. Mapping views reject containment and required ownership
bindings because those edges are governed as object-owned changes inside the same workspace draft.

The transaction conditionally claims the relation-set version, deletes obsolete edges, preserves or
updates the selected edge or creates it when absent, increments the set version and commits. A stale
claim returns `409 mapping_version_conflict` with the current version and bounded current-target
summaries; nothing changes. Requesting the already-current target with identical attributes is an
idempotent no-op with no version increment or audit event.

One mapping-transition audit event records old and new target and relation identities, while the
underlying relation audit remains available. Draft-scoped generic relation mutation routes participate
in the same set-version maintenance and therefore cannot bypass mapping concurrency. A retired
workspace, closed draft or endpoint absent from the candidate graph cannot be mutated through the
mapping operation. The mapping transition becomes externally visible only when the workspace draft is
activated.

## ADR-023 — Build RDM UI components on React Aria behavior

**Status:** Accepted

The frontend adopts `react-aria-components` as its accessible behavior layer while retaining an
RDM-owned component system, visual language and plain-CSS implementation. The library owns difficult
composite-widget mechanics such as dialog/overlay focus, combobox and listbox navigation, selects,
menus, popovers, tabs and tooltips. Native semantic HTML remains preferred for straightforward
buttons, inputs, forms, tables, headings and links.

Feature code imports semantic wrappers from `frontend/src/ui/` and never imports React Aria directly.
An ESLint restricted-import rule enforces this boundary. RDM wrappers own product behavior and API
shape, including mutation-busy dismissal guards, dirty-form confirmation, validation summaries,
loading/error/empty presentation and action hierarchy. The existing `Modal` API is retained where
practical while its focus, Escape, portal and outside-interaction mechanics move behind the wrapper.

RDM owns typography, spacing, color, borders, focus indicators, density, responsive rules and all
component styling through documented CSS tokens. React Spectrum or another pre-styled design system is
not adopted. The declarative application model continues to select semantic view and field behavior;
it never names React Aria components, DOM structures, CSS classes, pixels or icons.

Lucide is the single general-purpose icon source and is exposed through an RDM `Icon` wrapper.
Decorative icons are hidden from assistive technology; an icon-only interactive control must receive
an explicit accessible name. Text glyphs are not used as improvised interface icons.

Adoption is incremental: WP1 proves the wrappers in the shell, workspace selection and one complete
object workflow before broader replacement. Browser keyboard and automated accessibility tests remain
release gates because a primitive library cannot prove that application composition, labels, errors or
task flows are accessible.

## ADR-024 — Publish runtime data as immutable workspace revisions

**Status:** Accepted; supersedes ADR-020

A workspace is the unit of runtime-data governance and publication. It owns zero or one active
immutable content revision, any number of immutable historical revisions and any number of mutable
workspace drafts. Objects, attributes, containment and relations are records within that aggregate;
they do not independently enter draft, active or retired lifecycle states.

This boundary prevents a published workspace from becoming an accidental mixture of independently
activated record versions. Cross-record requirements, uniqueness, cardinality, containment and
mapping consistency can be validated against one candidate graph and published together. Stable
object and relation UUIDs remain addressable across workspace revisions for integration references and
audit, but stable identity does not imply an independent publication lifecycle.

A root workspace draft begins empty. A derived draft uses copy-on-write storage over one selected
workspace revision. Draft edits may use record-level optimistic versions for useful concurrent editor
feedback, while the workspace draft also has an aggregate version. Activation requires the expected
draft version and expected active workspace revision ID, validates the complete effective graph under
the draft's pinned application-model release and atomically changes the workspace revision pointer and
all active query projections. No active object or relation mutation endpoint may bypass this draft.

Workspace lineage has two separate edges. `derivedFromRevisionId` identifies the immutable workspace
revision used as the draft base. `supersedesRevisionId` identifies the workspace revision active when
the draft was published. Branching from older history therefore remains truthful even when activation
replaces a newer revision. Published and historical snapshots are read-only.

Publication retirement clears the active content-revision pointer under an expected-revision claim and
retains the workspace, stable record identities, immutable revisions and audit history. It does not
iterate through objects to mark each one retired. This content operation is distinct from ADR-019's
catalogue status: catalogue retirement controls whether a workspace may be mutated, while content
retirement controls whether it currently publishes a dataset. Product language and API names must
keep those concepts distinct.

Each workspace draft and revision pins the immutable application-model release used for validation.
Activation against a different currently resolved model release returns
`workspace_draft_model_release_conflict`; Base 0.6 does not silently rebase. Collection cursors bind to
the workspace plus active revision or draft identity so a publication switch cannot continue a page
against different content.

The rejected ADR-020 tables, object active-revision pointers and object activation/retirement endpoints
are pre-release implementation debt, not a supported compatibility surface. The corrective migration
preserves workspace keys and public object/relation UUIDs, materializes one initial workspace revision
from each unambiguous effective graph and removes the duplicate object-lifecycle authority. Physical
purge of workspace history remains outside Base 0.6.
