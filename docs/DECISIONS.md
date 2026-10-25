# Architecture decisions

## ADR-001 — Focus on RDM

**Status:** Accepted; clarified by ADR-032 (other domains only through generic, composable capabilities)

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

**Status:** Accepted; live/draft application consolidated by ADR-026 and ADR-027

Hierarchy uses `parent_object_id` for efficient navigation and a typed relation for semantics. The
service layer creates and moves both atomically and prevents cycles.

Changing a parent updates the live parent and typed containment edge together unless the caller
explicitly selects a workspace draft. In a draft, the same change stays staged; activation revalidates
the merged graph and applies both representations together. Historical revisions never change in place
(ADR-026/ADR-027 supersede ADR-024’s former draft-only timing).

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

**Status:** Accepted; live/draft application consolidated by ADR-026 and ADR-027; the database
backing delivered in 0.9 J2a (2026-10-07, D75–D78)

Attribute types may declare `features.unique`. Uniqueness is enforced at create and update by the
service layer, scoped to a single workspace and to the attribute type key. This keeps the runtime
generic (no object-type or domain branches) and avoids inventing one physical unique index per dynamic
attribute type. `json` values are excluded because their equality is not order-stable; declaring
`unique` on a `json` type is rejected at model load. The race window under concurrent writers was
closed by the workspace lock (0.9.0-alpha.1 PG3). Since 0.9 J2a the database holds live unique values
too: a dedicated table (`unique_attribute_values`) kept by PostgreSQL triggers, under a deferred
unique constraint, so a value written past the rule is refused at the end of its write and at commit.
A partial index was rejected: it cannot be deferred, its predicate would change with each release,
and a long text exceeds an index row.

Live writes enforce configured uniqueness against live content. Draft validation checks the effective
candidate, and activation rechecks the merged live graph after applying any configured conditional
predicate. Historical revisions do not reserve a current unique value. ADR-026/ADR-027 supersede the
former assumption that activation is the only live validation boundary.

## ADR-011 — Relation instance CRUD mutates only non-parent edges

**Status:** Accepted; live/draft mutation scope consolidated by ADR-026 and ADR-027

Live relation records support canonical create/read/update/delete. Historical snapshots are read-only.
Updates and deletes carry the relation `expectedVersion`; an explicitly selected draft additionally
requires its aggregate version. Version claims are atomic and return
`409 version_conflict` on a stale claim. Relation identity —
`relationTypeKey`, `fromObjectId`, `toObjectId` — is immutable; only the relation `attributes` are
updatable. Re-targeting an ordinary edge is expressed as delete + create. ADR-022's mapping aggregate
is the intentional exception: it performs the required delete and create in one atomic set
replacement rather than exposing a partially changed mapping.

Parent-containment and hierarchy edges — relation types named in the target object type's
`behavior.parentRelationTypeKeys` and written atomically on object parent changes — are
engine-maintained and therefore rejected by the relations API (`422 immutable_relation`). Keeping them
read-only prevents `parent_object_id` and the typed relation from diverging; the record Parent operation
updates both atomically in live or explicitly selected draft context.

Required non-parent relations remain readable and may update declared relation attributes, but cannot
be independently deleted because doing so would invalidate their dependent object. They are created
atomically with that object in the selected live/draft context and removed through its deletion impact.

## ADR-012 — Preview destructive graph cascades and derive ownership from relation bindings

**Status:** Accepted; live/draft application consolidated by ADR-026 and ADR-027

Deleting a live record removes it and its owned dependants immediately after the required impact
confirmation. An explicitly draft-scoped deletion affects only that candidate until activation. When
dependencies exist, a non-cascading request returns an impact report and changes nothing; callers
confirm `cascade=true` to remove owned dependants. Impact is recomputed and applied transactionally.
Independent associated records survive. Neither path rewrites immutable historical snapshots.
ADR-026/ADR-027 supersede the former draft-only deletion rule.

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

**Status:** Accepted; live/draft application consolidated by ADR-026 and ADR-027

A Translation is contained by a Translation Group and is also a lifecycle-dependent representation of
exactly one translated object. The translated object therefore owns the Translation through the shared,
required `object-has-translation` one-to-many relation. Domain, Codelist and Master Value are explicit
allowed source types; later model releases extend the same relation with additional source types rather
than introducing runtime key branches or wildcard application membership.

Translation creation accepts model-derived initial relationships and saves the record, parent edge,
target edge and fields together in the selected live or draft context. Draft changes become live only
when activation applies the coordinated changes. Required relations cannot be deleted independently.
`uniqueToAncestorTypeKey: language` with the configured `active == true` business predicate is checked
for live writes, draft validation and the final merged graph at activation. This prevents duplicate
available Translations for one target and Language while allowing unavailable current content and
immutable historical workspace revisions. Activation, including after a draft parent change, rechecks
the constraint.

## ADR-015 — Resolve one database-selected model snapshot per request

**Status:** Accepted

The singleton database runtime-state row is the authority for the active installed model release.
`MODEL_PATH` is bootstrap input only: startup validates and installs that content when needed, but a
different bootstrap file does not implicitly replace an already selected release.

Each live-data request resolves runtime state once and uses the corresponding immutable parsed
`EngineModel` and metadata release for every model-dependent operation. ADR-027 extends the explicit
context contract: draft/history requests resolve their pinned supported model instead, consistently
through validation and response composition; WP8.1 implements the missing historical boundary. The process registry may cache snapshots by
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

**Status:** Accepted; deletion of an unused workspace added by the 2026-09-26 amendment below (0.8 D27)

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

**Amendment (2026-09-26, Base 0.8 D27 / W6).** A key cannot be renamed, so a mistyped key otherwise
stays forever. A workspace may therefore be deleted when it is not the default, has no objects and no
change sets, and has never been published; everything else is retired. Publications are never
removed, so a published workspace, even one whose publications are all withdrawn, can only be retired.
`DELETE /api/v1/workspaces/{workspaceKey}?expectedVersion=N` sits behind the same
`WORKSPACE_ADMIN_MUTATIONS_ENABLED` flag and refuses, in order, `404 workspace_not_found`,
`409 workspace_is_default`, `409 workspace_has_publications`, `409 workspace_not_empty` (with
`objectCount` and `changeSetCount`) and `409 version_conflict`, changing nothing. Retired workspaces
follow the same rule. A deleted key may be created again. Like create, rename and retire, deletion
records no audit event; audit events that named the key remain. Single-workspace responses state
`deletable` and `deleteBlockedBy` (`default`, `published`, `notEmpty`) so clients do not infer the rule.
The sentences above that say a workspace cannot be deleted and that there is no `DELETE` route are
superseded by this amendment.

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

Mapping-grid configuration is deliberately not part of schema 0.5 or the Base 0.6 release. Product 0.7
introduces schema 0.6 with the `mappingGrid` discriminated branch (WP-2, delivered 2026-09-12). Schema
0.6 is a strict superset of 0.5; a schema 0.5 model remains valid and activatable under schema 0.6.
This keeps schema 0.5 and the daily-operations release independently implementable.

The compiler dispatches explicitly by schema version and returns `unsupported_schema_version` with
the supplied and supported versions. The runtime supports schema 0.5 and 0.6 as active models and does
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

*Superseded by [ADR-042](#adr-042--each-workspace-runs-its-own-model-release) (2026-10-15): each
workspace runs its own model, and the schema-language window is 0.11 V4's.* Workspace-scoped
model-release assignment is deliberately separate. It can later provide staged
per-workspace migration, but running workspaces on different schema-language versions
requires the engine to serve every pinned parser and contract concurrently; workspace pinning does
not remove that compatibility obligation. That future capability is sequenced with executable data
migration, protected administration and a bounded supported-version window.

## ADR-022 — Version complete relation sets for atomic mapping

**Status:** Accepted for product 0.7; live/draft scope consolidated by ADR-026 and ADR-027.
Relation-set version persistence delivered in WP-3 (2026-09-12); mapping query APIs delivered in
WP-4 and cascade-deletion participation in WP-10A (2026-09-14). Atomic mapping replacement delivered
in WP-5 (2026-09-14).

Mapping concurrency belongs to the complete directional relation set, not to an object or one relation
instance. A source object may currently have zero, one or several matching edges, so neither an object
version nor an individual relation version can protect create, remove, replace and ambiguous-state
resolution consistently. Mapping mutations target stable records in a live workspace or an explicitly
selected design draft. Live replacement is immediately visible; draft replacement remains staged.
This replaces ADR-024’s former draft-only mapping scope.

The `relation_set_versions` table (delivered in WP-3) stores one optimistic integer version for an exact binding:
workspace and explicit live/draft context, relation type, `fromObjectTypeKey`, `toObjectTypeKey`, stable anchor object and `outgoing`
or `incoming` direction. Including both endpoint types prevents two allowed bindings of the same
relation type from sharing and replacing each other's set. Every generic relation create, attribute
update or delete atomically increments the outgoing and incoming sets for that exact binding.
WP-10A also advances both sets for each incident edge removed by confirmed live/draft object cascades;
preview and rejected deletions leave versions unchanged.
Mapping-grid rows return this value as `mappingVersion`; a previously untouched set has version zero,
claimed safely under the scope's database uniqueness constraint.

The product 0.7 mapping operation accepts explicit content context and direction,
`relationTypeKey`, physical `fromObjectTypeKey`/`toObjectTypeKey`, the row anchor
`sourceObjectId`, `expectedMappingVersion`, a nullable `targetObjectId` and
relation attributes. Endpoint type keys remain required when the target is null so removal cannot
broaden its scope. A null target removes the complete selected-target set and permits omitted or empty
attributes. A non-null target replaces the complete set with exactly that target, allowing one
operation to create, replace or resolve an ambiguous mapping. The service validates workspace status
and draft status when a draft is selected, candidate endpoint records, endpoint types, direction, the exact allowed relation binding,
cardinality and typed relation attributes. Mapping views reject containment and required ownership
bindings because the record operation owns those relationships. The former draft-nested PUT proposal
is superseded; the canonical live/optional-draft route and request contract are delivered and documented
in [API.md](API.md#product-07-mapping-api-wp-4-and-wp-5-delivered).

The transaction conditionally claims the relation-set version, deletes obsolete edges, preserves or
updates the selected edge or creates it when absent, increments the set version and commits. A stale
claim returns `409 mapping_version_conflict` with the current version and bounded current-target
summaries; nothing changes. Requesting the already-current target with identical attributes is an
idempotent no-op with no version increment or audit event.

One mapping-transition audit event records old and new target and relation identities, while the
underlying relation audit remains available. Live and draft generic relation mutation routes participate
in the same set-version maintenance and therefore cannot bypass mapping concurrency. A retired
workspace, closed draft or endpoint absent from the candidate graph cannot be mutated through the
mapping operation. Draft application must also preserve live mapping-set conflict protection; live
replacement must not require workspace activation. WP-10B compares complete source/live relation
identities and versions in the exact directional mutable binding sets the draft touched. New,
removed or updated live edges in those sets refuse activation under `409 version_conflict` with
`mapping_set_changed` diagnostics. Containment and required ownership retain existing graph/record
merge rules. Unrelated live sets survive. An intervening add/remove cycle that leaves the complete
source graph and all surviving relation versions identical is not a divergence under this check.

### 0.7 implementation detail — later packages, 2026-09-12

WP-1–WP-3 are frozen; this clarification governs WP-4 onward and does not review their implementation.
Coverage and candidate reads identify the application/view supplying the existing configuration.
Target details may omit both view keys for binding-only name projection; conflict continuation carries
the selected view identity, or null view identities for the binding-only projection. Coverage and conflict
responses carry exact target counts with bounded previews and cursor-paged continuation, and coverage
state and version describe a consistent read. Replacement retains the selected existing relation;
omitted attributes preserve its values, while an explicit object replaces the set under typed
validation. One selected target is the operation rule, separate from direction-aware cardinality.
Later integration acceptance checks generic-write races, both directional sets and draft activation
against live same-set changes. Confirmed foundation gaps belong to conditional WP-10, not frozen WP-3.
WP-4 reads, WP-5 replacement, WP-10A cascade invalidation and WP-10B activation set-conflict
checks are delivered; composed acceptance
remains planned. See the mapping API section in [API.md](API.md) and [0.7 plan](BASE_0_7_IMPLEMENTATION_PLAN.md).

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

**Status:** Accepted workspace aggregate; current data authority and write timing amended by ADR-026
and consolidated by ADR-027. Supersedes the rejected ADR-020 per-object lifecycle.

A workspace owns coordinated data drafts and immutable historical revisions. Object, attribute,
containment and relation records retain stable public identities; they have no independent publication
lifecycle. A coordinated activation applies one validated change set and records one immutable snapshot.

The original draft-only mutation rule and wholesale replacement of active projections are superseded.
Current data is live and editable without a draft. Activation applies authored changes over the current
live graph, preserving unrelated live work and refusing conflicts. A historical revision cannot be
edited or used as a direct restore operation.

History keeps the draft source (`derivedFromRevisionId`, where sourced from a revision) distinct from
activation supersession (`supersedesRevisionId`). ADR-027 adds a fresh current-live starting point that
must not pretend the last published revision contains later live edits. Drafts and revisions pin a model
release; current implementation gaps and migration restrictions are recorded in the Base 0.6 plan.

Publication retirement removes the current-publication designation and retains live data and history.
It does not withdraw live reads or make a workspace read-only. Catalogue retirement is the separate
read-only control. Cursor binding follows the actual live/draft/history context, not a blanket active-
revision rule; see `API.md` and ADR-027.

The corrective migration preserves workspace keys and public record identities, materializes an initial
revision from each unambiguous graph and removes rejected per-object lifecycle authority. Physical
purge of history remains outside Base 0.6.

## ADR-025 — Keep generic CRUD independent of workspace publication

**Status:** Accepted; draft-required clauses amended by ADR-026 and consolidated by ADR-027.

Objects, typed fields, containment, relations and translations use one generic CRUD contract. Live
writes do not require a draft; explicitly selecting `workspaceDraftId` stages the same operations.
`workspaceRevisionId` selects immutable history and cannot be combined with draft context. Workspace
identity remains explicit in routing and must be preserved across the complete user journey.

Live updates/deletes claim the record version. Draft updates/deletes additionally claim the draft
version; creating a new record has no pre-existing record version to claim. Live object creation needs
an explicit workspace key; existing-record mutation resolves the record's workspace. See `API.md` for
route-specific inputs rather than adding unsupported workspace fields to every payload.

Workspace endpoints own draft creation, validation, activation and publication history. Record endpoints
remain canonical; nested draft-object/relation resources and per-record publication controls are not a
second public API. Required initial relationships, typed data, uniqueness, containment, deletion impact
and concurrency retain their generic semantics. Empty collections are successful empty pages.

## ADR-026 — Active workspaces are live-writable for data; drafts are the design path

**Status:** Accepted 2026-09-07; live CRUD and delta-merge implementation recorded in Slices 0–5.
The fresh current-live draft base is implemented for SQLite by WP8.1-B; later authority and browser
checks remain implementation work. The earlier blanket “implemented” label overstated completion.
ADR-027 consolidates the accepted 2026-09-08 product
answers without treating documentation acceptance as runtime delivery.

### Motivation — the product statement was the arbiter

`PRODUCT.md` names the primary users: *"data owners maintaining canonical codes and names"* and *"local
data stewards maintaining translations and availability."* Maintaining reference data is a continuous,
day-to-day operation: a data owner adds a new canonical value, edits a code's label, retires an obsolete
value. ADR-024/ADR-025 (and the WP7/WP8 implementation they drove) interpreted every record write as a
staged, released mutation: an active workspace was immutable for **both** model and data, and every
write required a `workspaceDraftId` followed by a later atomic activation that created a new workspace
revision and retired the previous one. For an RDM that forces each single value edit through a release
ceremony. The product statement said the operator edits reference data continuously; the lifecycle
decisions said the opposite. That inconsistency is the root cause this decision corrects.

### Decision

A workspace distinguishes two layers, and each has its own write rule:

1. **The model is immutable on an active workspace.** Schema/application-model change is not performed by
   editing an active workspace in place. This was already true (model releases are global and immutable;
   workspace drafts/revisions pin a release) and remains true.
2. **The active workspace's data content is live and writable.** Object, typed-attribute, containment and
   relation writes against the active workspace take effect directly on the live object store
   (`RdmObject` / `AttributeValue` / `ObjectRelation`), are immediately visible to active reads, are
   optimistically locked at the **record** level (`expectedVersion`) and audited per change. They do not
   create a workspace draft, a workspace revision or any "release."

Therefore `workspaceDraftId` becomes **optional** on record writes:

- **Supplied** → the write stages into that workspace draft (the unchanged copy-on-write machinery and
  `expectedWorkspaceDraftVersion` claim), for review and later atomic activation.
- **Omitted** → the write applies directly to the active workspace's live object store, claiming only the
  record version.

The **workspace draft remains the design playground**: a separate, safe surface to author objects,
values and relationships independently of the live store; application-definition drafts remain a
separate concept. When
the design is ready it is brought to the active workspace through validation + activation, retiring the
superseded state.

The standalone record-CRUD service functions — `create_object_record`, `update_object_record`
(`services/objects.py`), relation CRUD helpers (`services/relations.py`) and the deletion/cascade plan
module (`services/deletion.py`) — are restored and remain **independently maintained and referenced**.
They are not helpers of the workspace-draft functions; they are the service layer for record writes,
with the workspace-draft path layered on top for the design surface.

### Amendments to prior decisions

- ADR-024's *"No active object or relation mutation endpoint may bypass this draft"* is amended to apply
  to the **design path**; data-content writes against the active workspace no longer require a draft.
- ADR-025's *"Every write requires `workspaceDraftId`"* is amended: writes **may** target the active live
  store directly; a draft is required only when the caller chooses the design path.
- Immutable workspace revisions, activation/retirement, history, lineage, cursor binding and lifecycle
  audit remain exactly as ADR-024/ADR-025 specify for the design path. Published/historical revision
  content stays immutable; provenance for live data edits is the per-record version plus the audit trail.

### Resolved decision — activation is a delta-merge over live content

The owner locked option (b): direct live data writes are allowed **at any time**, including while a
design draft is open, and activation applies the draft as a **delta over the current live content**, not
a wholesale replacement.

- Required target: a draft started from live captures a fresh immutable snapshot of **current live
  content** and its record versions at creation. WP8.1-B implements this for SQLite; unsupported
  database dialects receive an explicit refusal. Empty drafts are development/bootstrap support, not
  the ordinary user starting flow. Historical-source creation remains a distinct choice.
- At activation the delta is the draft's created/updated/tombstoned rows relative to that base.
  Activation applies **only those rows** onto the current live projection, with **per-record version
  conflict detection**: any record the draft touched must still sit at exactly the version it had in the
  draft's base snapshot, so a concurrent live edit of the same record always conflicts rather than being
  silently overwritten. A draft-created id that already exists live is an `id_collision`, and a draft
  edge that would duplicate a live `(type, from, to)` edge is a `duplicate_edge`; every conflict is
  reported under `409 version_conflict` with `details.conflicts` (kind, id, code, expected/actual
  version) before anything is written.
- Objects created or edited live that the draft never touched are **preserved**.
- Activation then re-validates the **merged** live graph (whole-graph), writes one new immutable
  `WorkspaceRevision` snapshot of the merged content, advances `active_revision_id`, retires the
  previous active revision and deletes the draft — all atomic.
- Any conflict or validation failure rolls back and **publishes nothing**; both the draft and the live
  content are preserved for the caller to reconcile.

Active reads resolve the **live projection** (`RdmObject`/`AttributeValue`/`ObjectRelation`); revision
snapshots (`WorkspaceRevisionObject`/`WorkspaceRevisionRelation`) serve **history only**
(`workspaceRevisionId`). Live provenance is the per-record `version` plus `AuditEvent` under the
`object`/`relation` aggregates; live writes never mint a workspace revision. A revision snapshots the
full merged live content, so a draft branched from an old revision never drops unrelated newer live
content its membership did not contain. This replaces the pre-correction wholesale projection rebuild
in `activate_draft`.

### Process note — how the discrepancy happened and how to avoid repeating it

The inconsistency was **structural and unflagged**: the product brief (`PRODUCT.md`) described the
continuous-maintenance RDM job, while the lifecycle decisions (ADR-020 → ADR-024/ADR-025) and the WP6-WP8
packages implemented every write as a staged, released mutation — and each package passed its own gate.
The standalone record-CRUD functions, which are the natural home for live active writes, were treated as
dead and deleted even though their behaviour is what `PRODUCT.md` promises. The conflict surfaced only
after delivery, when the removal was challenged.

Going forward, at **every** stage gate test the candidate against the product statement —
*"what does a data owner do every day, and does this decision allow it without ceremony?"* — and surface
any tension in the gate report rather than after. Never delete code, even code with zero current callers,
without recording the intent and obtaining sign-off. State the two layers explicitly in every decision:
**product model / schema** (released, immutable) versus **reference-data content** (live, editable,
versioned by record and audit). If a later decision contradicts an earlier one, say so at the time and
record the amendment, as ADR-026 does here.

## ADR-027 — Consolidate live data, draft sources and reviewed historical migration

**Status:** Accepted product direction, 2026-09-08, from the user's GAP-01–GAP-08 answers in
`product-functionality/PLANNING_HANDOFF.md`. Implementation is partial; Base 0.6 WP8.1/WP9/WP10 and
product 0.11 own the remaining work described below. This decision consolidates ADR-026 and explicitly
amends obsolete draft-only and restore wording in ADR-006/010/011/012/014/022/024/025.

### Data authority and ordinary work

The selected immutable application-model release defines current rules. Live `RdmObject`,
`AttributeValue` and `ObjectRelation` rows define current data, including records created since the
latest publication and data in readable catalogue-retired workspaces. Model compatibility must examine
all live content served under that model; revision membership is not a substitute for this population.

Normal create/update/delete, typed fields, translations, parent changes and ordinary relationships
remain direct live operations with validation, record concurrency and audit. Optional workspace data
drafts contain coordinated data changes. Model drafts contain proposed definitions. One never silently
changes the other. All browser paths must retain workspace context and use familiar generic controls.

### Draft sources and application

The normal choices are **current live data** and **a selected historical revision**. Current-live
creation captures a consistent immutable internal base, including fields, records, relationships,
parent structure, model identity and record versions. It includes edits since the latest publication
and works when live data has no publication. Creating this base must not activate anything or create a
user-visible publication. Empty draft creation remains only a development/bootstrap concern; a new
empty workspace can use the same current-live choice and obtain an empty base naturally.

Historical derivation retains the source revision and its pinned definition. “Retired” here means a
historical publication revision; a catalogue-retired workspace remains read-only. It does not restore the
active workspace: only deliberately authored changes are candidates for application. A live-start base
and the historical publication used for lineage are distinct identities; an implementation must not
label an older publication as the actual current-live base.

Normal activation applies authored changes over current live data, preserves unrelated changes and
revalidates the merged graph. A touched-record conflict or invalid graph changes neither live data nor
the draft. Older history is not an undo button. Immutable history must be interpreted with its pinned
model; unsupported historical schemas receive an explicit refusal, not interpretation under guessed
current definitions. Supporting historical content does not imply every obsolete schema language can
run indefinitely.

### Publication designation and history order

Publication retirement clears the current-publication designation. Live records remain available;
this action does not withdraw consumer reads, set a business availability field or retire the catalogue
workspace. Catalogue retirement remains the read-only control. The confirmation and result must say so.
Workspace revision history is **newest first** with a deterministic unique pagination tie-breaker;
the former oldest-first behavior was an implementation defect, not an alternate accepted UX.

Current live cursors bind endpoint/query/workspace/order, without a model or publication revision token.
They survive publication and are not frozen dataset snapshots. Draft and history cursors bind their
selected identities and query. A stronger future consistency guarantee requires an explicit contract
change and tests, not a documentation-only assertion that tokens already contain those identities.

### Historical drafts incompatible with the active definition

The user requires a warning and **confirm schema replacement with potential data loss, or cancel**
when a historical draft cannot be applied under the current active definition. Preserve that requirement
as a reviewed model-and-data migration flow in product 0.11, alongside GAP-08's accepted migration and
workspace-model assignment boundary. Base 0.6 activation does not override the compatibility check for
this case.

The preview names one selected workspace and one installed immutable target release, normally the
historical draft’s pinned release. Confirmation migrates current live data to that target and changes
only the selected workspace’s model assignment; it does not quietly move the draft onto today’s model.
The flow identifies source/current/target definitions, proposed conversions, removed/changed fields
and relationships, and potential data loss before explicit confirmation. Bind
confirmation to that reviewed plan and the current data/model versions; changed inputs invalidate it.
Cancellation changes nothing. A confirmed execution transforms data and switches the applicable model
selection atomically, validates the result against the target definition and preserves immutable
history. Failure leaves the prior usable state and draft intact, with actionable diagnostics.

Model selection is global today. A historical-data action must not silently replace the definition
for other workspaces. The 0.11 plan must use its workspace-scoped assignment/migration capability; the action must not
switch the global model as a shortcut. Selecting an older model release
never mutates that immutable release. Model release and `schemaVersion` are distinct; unsupported
model-language versions require executable parser/runtime support before any confirmed migration. Loss approval authorizes the reviewed transformation, not data
that violates the target rules, silent conflict overwrite or arbitrary deletion.

Until the migration path is implemented, Base 0.6 preserves incompatible drafts and explains the pinned
and active model mismatch. Cancellation/back remains available; it must not present an enabled
confirmation promising an unsupported schema override.

### Acceptance and delivery

- WP8.1 corrects live compatibility population, current-live bases, pinned historical interpretation
  and newest-first history before accepting the dependent design UI.
- WP9 restores live CRUD, optional draft modes, immutable history and truthful retirement wording.
- WP10 executes SC-01–SC-06, SC-08, SC-12–SC-14 in the appropriate channels, including live-only model
  incompatibility, historical typing after a model switch and migration/startup boundaries.
- Product 0.7–0.9 specialists and integration preserve live maintenance with optional staging.
- Product 0.11 validates preview, explicit loss confirmation, cancellation, stale-review refusal,
  atomic migration/switch, history preservation and isolation of unaffected workspaces.

Decision acceptance is not implementation evidence. Every package and release records the stories,
actual channels exercised, failure outcomes, skips and simplicity comparison from the product
validation guide. No component-only pass establishes a complete browser journey.

## ADR-028 — One draft may prepare the next model version while live keeps the current one

**Status:** Accepted product direction, 2026-09-10. Backend version selection delivered in WP-6
(2026-09-14); browser selection remains WP-7. The work splits across two
releases: letting a draft work under a version the user chooses is **product 0.7 work**, and moving a
draft onto a version its content does not already fit is **product 0.11 work**, reusing the conversion
machinery ADR-027 already places there.

### The requirement

A draft works under a model version the user chooses, while live data keeps the version it is on
today. An administrator installs the next version — installing alone changes nothing for anyone — and
one draft is created against it; inside that draft the user sees the new fields, rules and views.
Other drafts, the live records, the immutable history and every other workspace keep using the version
that serves live data. When the administrator activates the new version, live data moves to it, the
draft that prepared it activates through the ordinary path because its version is now the active one,
and any draft still on the old version is either thrown away — which changes no data — or explicitly
moved onto the new version.

Choosing a version is an edit to that single draft and to nothing else: it is not a way to force a
model change past the compatibility check, and it does not switch the version used anywhere else.
Ordinary activation is unchanged, and a draft whose version differs from the active release is refused
with `workspace_draft_model_release_conflict`.

### Moving a draft onto a new version

A draft whose content does not already satisfy the new version cannot be served under it. That case is
a data conversion rather than a version choice: it needs the conversion, loss-preview and
exact-confirmation machinery ADR-027 places in 0.11, applied to that draft and the live data under it.

The review names the source, current and target versions, the changes it would make and any draft
content that would be lost; confirming applies exactly the draft and version that were reviewed;
cancelling, a stale review or a failure leaves the draft, its version, live data and history
untouched. A conversion never deletes draft content to make the new version accept it.

### Acceptance

Product 0.7 delivery requires: a draft can be created against, or explicitly moved onto, an installed
release the deployment can parse and support; an unavailable, corrupt or unsupported target is refused
with the existing pinned-model error codes; draft reads, writes and validation use the version chosen
for that draft rather than the global selection; live data, immutable history, other drafts and other
workspaces are unchanged whenever a draft's version changes; and no path activates a draft whose
version differs from the active one.

Product 0.11 delivery additionally requires: a preview and confirm-or-cancel contract bound to the
exact reviewed versions, whole-graph revalidation under the target, and conversion of stored content
the target does not already accept. Nothing on any path forces a change through, moves a draft without
being asked, or switches the version used across the product; and reading, editing and discarding a
draft under a version that has since been replaced keeps working without needing model agreement.

### ADR-028 0.11 delivery — V3, 2026-10-18

Moving a change set onto a release its content does not fit is delivered for the release its
workspace runs (0.11 V3, D87–D96): a `migration` job naming the change set previews every conversion,
loss and refusal of its content over live data as it is now, and applies only on confirmation of the
reviewed change set version and the workspace's assignment and feed position. Content the target has
no place for is removed only once the loss is accepted; a rule the content breaks is refused and never
resolved by removing anything (D90). The change set's base becomes live data captured at the move.
Moving onto a release the workspace does not run, when the content does not fit, is not offered
(`MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`; TODO).

### ADR-028 0.7 implementation detail — WP-6/WP-7, 2026-09-12

Creation against a selected model and explicit version changes require the complete effective
candidate graph to already satisfy it: immutable base plus authored changes minus tombstones.
Compatibility checks include inherited content, not only authored rows, and use a draft-scoped
validation boundary rather than the unchanged live-table compatibility analyzer. Creation refusal
leaves no draft/base. Version change claims the draft token and validates/updates the pin atomically;
failure leaves content, pin and version unchanged. The captured active snapshot identity stays separate
from the chosen pin. Historical-source creation retains its source model; another selection is explicit.
Browser context transitions reload the pinned model and all dependent routes, views, forms, lookups and
cursors, protecting dirty input and detecting external pin changes. A differing pin may be an older
release, so explanations name pinned and active versions neutrally. No conversion or activation bypass
is added. WP-6 implements the backend boundaries; browser context transitions remain WP-7. These are
later-package requirements, not foundation implementation amendments.

## ADR-029 — Compose model-defined views as contextual collection lenses

**Status:** Accepted product direction, 2026-09-15; delivery belongs to Base 0.7 WP-14.

### Motivation

The initial browser exposed configured views and runtime containment as two mutually exclusive
navigation modes. Top-level tables consequently flattened contained records across their governing
parents, while each `mappingGrid` declaration added another visually similar global table. Although
the projections were technically model-driven, a steward could not reliably answer which governed
collection a row belonged to or what scope a change affected. Adding more relation bindings would
multiply that usability failure.

The three starter applications are model content for one RDM use case, not engine modules. Navigation
and filtering must therefore derive from arbitrary applications, object types, containment relations,
view definitions and supported semantic renderer types. Runtime code must not recognize Master,
Systems, Translations or any of their keys.

### Decision

The application-facing UI has five distinct concepts:

1. **Context** identifies workspace, application, Live/Draft/History and an optional containing object.
2. **Collection** identifies the view's row/source object type.
3. **Lens** is one model-declared presentation or task over that collection, such as `table` or
   `mappingGrid`.
4. **Query** is the URL-backed search, typed filters, scope, sort and cursor trail supported by the
   selected lens.
5. **Detail composition** remains the application-defined presentation of one object.

The sidebar exposes one model-driven application browser rather than a `Browse hierarchy` / `Views`
switch. It contains virtual collection entries and runtime containment records. Selecting a containing
record may open a compatible direct-child collection with that parent as visible scope; selecting a
record still opens its configured detail. Applications without containment remain usable through
their root collection entries.

Schema 0.5/0.6 view declarations remain valid and independently addressable. For these schemas the UI
groups them deterministically by source object type: `table.objectTypeKey`, or the physical source side
selected by a `mappingGrid` direction. Views in one group are lenses within one collection workspace.
Mapping therefore retains its dedicated query, bounded coverage, target selection and relation-set
concurrency semantics without requiring a duplicate primary navigation destination. Existing view URLs
remain canonical and shareable.

Filters are model-aware and predictable, not personalized. The current containing-object scope and
the model-declared filter fields remain visible; controls use declared value types. A configured
mapping lens additionally exposes its defined zero/one/many coverage states. All filtering is
server-side, cursor-bound and bounded. An explicit unscoped collection remains available, but it must
not be confused with a scoped collection; model-configured ancestor/path columns provide context where
needed.

No arbitrary relation is silently promoted to mapping. `mapped`, `unmapped` and `ambiguous` are valid
only for a configured mapping lens whose one-selected-target operation gives zero/one/many that task
meaning. If several mapping declarations share a source type, their model labels distinguish the
lenses. Opposite directions do not require duplicate sidebar entries.

### Compatibility and extension

This decision does not change schema 0.6. Grouping is a presentation rule over fields that already
identify the source type. A later schema may declare collection/lens composition explicitly after at
least two real models demonstrate ambiguity that cannot be represented honestly by this rule.

A different domain using the same table, relation-coverage or hierarchy interaction requires model
configuration only. A fundamentally different interaction shape requires a new typed generic
view/lens contract and renderer in the engine registry, never an application-key branch.

Base 0.7 uses existing direct-parent object filtering and adds the same optional parent scope plus
coverage-state filtering to mapping coverage. Arbitrary-depth lazy traversal, path-revealing hierarchy
search and hierarchy restructuring remain product 0.8; the 0.7 application browser must not imply that
its currently loaded runtime tree is an unbounded hierarchy query.

### Acceptance

- One application browser exposes collections and containment records without a navigation-mode toggle.
- Two views with the same source type appear as lenses in one collection workspace.
- A configured mapping remains generic across different bindings and directions.
- Parent scope, mapping state, typed filters, search and cursor state remain URL-backed and survive
  compatible lens/detail navigation.
- An application with no mapping view shows no mapping affordance; an application without containment
  still exposes its collections.
- Live, Draft and History retain the same visible scope, with all history mutations absent.
- No frontend or backend branch names a starter application, object type or relation key.

## ADR-030 — Cursor and position paging with continuous scrolling

**Status:** Accepted, 2026-09-25; delivery belongs to Base 0.8 Track S
([plan](BASE_0_8_IMPLEMENTATION_PLAN.md)). Closes the open offset/limit pagination decision.

### Motivation

Object types, hierarchy depth and relation volume come from the model and its data. A first level may
hold 7 records or 7000, and one record may have 1500 relations. A 1000-record probe showed that
Previous/Next paging without totals is tedious, that the sidebar tree is incomplete at volume, and that
draft and history reads load whole sets into memory. Random-access page numbers were requested for UI
tables and considered for integration clients.

### Decision

Collections support two paging modes. Each request uses exactly one of them.

1. **Cursor mode** (existing): `cursor` continues after or before a row. Cursors stay signed and
   bound to endpoint, ordering and filters. The API adds backward cursors (`prevCursor`), a last-page
   read, an `anchor` cursor that reopens a page, and `seek` by sort value.
2. **Position mode** (new): `position=N` returns the page starting at row N of the filtered, sorted
   list. Supplying both `position` and `cursor` is refused with a machine-readable error.
3. Every page, in either mode, returns `prevCursor`, `nextCursor` and `anchor`. With `includeTotal=true`
   it also returns `totalCount` and `startIndex`.
4. The UI scrolls with cursors and jumps with positions. Scrolling keeps a bounded window of pages,
   prefetches toward both edges and evicts pages far from the viewport, so memory and DOM size do not
   grow with scroll distance. Clicking or dragging the proportional scrollbar, or entering a page
   number, sends one position request; scrolling onward from the landed page uses its cursors.
   *Revised 2026-10-19 (0.11 X6, D156, D161):* the list is drawn by row number. Its scroll space
   spans the whole list, sized from the total, and only the rows near the view are drawn; the
   browser's own scrollbar replaces the proportional one. Every read is the reader's page; a
   scrollbar drag or a fling reads one position where the view rests.
5. Consistency differs by mode and is documented. Cursor reads never repeat or skip a row when data
   changes between requests. A position read addresses rows by number, so a concurrent insert or
   delete before that row moves the landing point, and consecutive position reads can repeat or miss
   a row at a page boundary. Integration clients that read a whole list should use cursors; clients
   that need page numbers may use positions and accept that behavior.
6. A position read costs a scan over the skipped rows. Seek by value remains available as the fast jump
   for very large lists.

### Consequences

- The AGENTS.md invariant becomes: collections page with cursors or positions; the UI scrolls with
  cursors and jumps with positions.
- Draft and history reads must run in the database; loading whole sets per page is incompatible with
  a prefetching UI or a position jump.
- The API changes are additive; the OpenAPI lock is re-baselined in the delivering package.

### Acceptance

- Any collection in a generated model with 100,000 records scrolls both ways with flat memory and jumps
  by scrollbar or page number, in live, draft and history contexts.
- A concurrent insert between cursor reads causes no repeated or skipped row.
- A request with both `position` and `cursor` is refused.
- No frontend or backend branch names a starter application, object type or relation key.

## ADR-031 — Workspace terminology and deployment capability boundaries

**Status:** Accepted, 2026-09-25; delivery belongs to Base 0.8 Track W
([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#track-w--workspace-terminology-and-capability-boundaries)).
The rename is recorded as resolved: every layer changes in one planned package without aliases, and
Git history traces the previous names.

### Motivation

"Workspace" had three meanings: the catalogue scope chosen in the selector, the prefix of its drafts
and revisions (`WorkspaceDraft`, `WorkspaceRevision`), and the 0.8 steward screens ("translation
workspace", "hierarchy workspace"). "Draft" had two: model drafts and data drafts. The Live / Draft /
Historical badge looked like a second workspace selection unrelated to the selector.

`WORKSPACE_ADMIN_MUTATIONS_ENABLED` also bundled two different concerns. It gated catalogue
administration (create, rename, retire, set default) and the routine steward workflow of data drafts
(create, update, delete, validate, activate). An operator protecting the catalogue also removed
coordinated data changes.

### Decision

**Terms.** One meaning per word, applied to the database, API, backend, frontend, tests and docs:

| Concept | Term | Replaces |
| --- | --- | --- |
| Named governed scope holding reference data | **Workspace** | unchanged |
| Current, directly editable data of a workspace | **Live** | unchanged |
| Optional group of data changes published together | **Change set** | workspace draft, design draft |
| Immutable snapshot created by publishing a change set | **Publication**, identified as "Publication N" | workspace revision, historical snapshot |
| Editable model JSON | **Model draft** | unchanged; now the only "draft" |
| Immutable installed model | **Model release** | unchanged |
| Removing a publication's current designation | **Withdraw** (status `withdrawn`) | publication retirement |
| 0.8 steward screens | **Relation matrix**, **Hierarchy editor** | translation/hierarchy workspace, Translation editor |

_Amended 2026-09-28:_ Milestone A was first named "Translation editor". It is the **Relation
matrix**, a generic lens that any application may declare; translations by language is one example
configuration of it ([EXAMPLE_MODEL.md](EXAMPLE_MODEL.md)).

A workspace has live data, change sets and publications, and runs on one model release. Live, a
change set and a publication are ways of viewing one workspace, not workspaces themselves.

**Verbs.** One verb per action: **publish** a change set (creates Publication N and makes its changes
live), **install** a model draft (creates an immutable model release), **activate** a model release
(makes it serve the installation). "Activate" is never used for change sets. **Withdraw** a
publication removes its current-publication designation (status `withdrawn`); live data and history
are unchanged. **Retire** is reserved for the workspace catalogue action that makes a workspace
read-only.

**Publication numbering.** A publication is referred to by its number, e.g. **Publication 12**; the
date is secondary. The number is a per-workspace counter (`publicationNumber`, the existing
`revision_number`): the next number is the highest in the workspace plus one. It continues across
model releases and never restarts, so the number alone names one publication of a workspace. Each
publication records its model release, shown beside the number where useful ("Publication 12 · model
0.8.0 · 3 Sep 2026"). The counter is not a version: it has no parts and is never labelled "version",
so the only version users see is the model release's.

**Capability boundaries.** Three operation groups, each with its own gate:

1. **Workspace administration** — create, rename, retire, set default. Gated by
   `WORKSPACE_ADMIN_MUTATIONS_ENABLED` (default on until authentication exists). The flag is narrowed
   to exactly this group.
2. **Change-set workflow** — create, update, delete, validate, publish, discard, and withdraw a
   publication. Ordinary steward
   operations like live edits: always registered, refused in a retired workspace.
3. **Model administration** — model drafts, install, activate. Gated by
   `MODEL_ADMIN_MUTATIONS_ENABLED` (default off, single process), unchanged from ADR-017.

**Deployment capability versus authorization.** The flags stay environment settings and stay after
authentication. They answer "does this installation expose the operation at all"; authorization in
0.12 answers "who may use it here" within that limit
([ADR-044](#adr-044--authorization-action-groups-roles-and-grants); corrected from "0.11" in 0.12 P0):

| Layer | Lives in | Set by | Arrives |
| --- | --- | --- | --- |
| Deployment capability | Environment, read at startup | Operator | Now |
| Authorization | Database (roles and grants are runtime data, never in a model release), managed in the UI and the API | A principal holding Security administration | 0.12 (moved from 0.11, 2026-09-29; ADR-044) |

They are environment settings rather than UI settings because:

- **A switch cannot guard itself.** Before authentication, anyone who reaches the UI could turn a UI
  toggle back on. The guard must live outside the API it guards.
- **They take effect at startup.** A disabled group's routes are not registered, so the operation
  does not exist rather than being refused per request. Model administration is also tied to process
  topology (`WEB_CONCURRENCY=1` until cross-process release propagation), which only the operator
  starting the processes knows.
- **The exposure decision belongs to the operator.** The same build can run as an open local sandbox
  or behind a public URL; that choice sits beside `DATABASE_URL` and `CORS_ORIGINS`.

The UI may show the effective capabilities read-only (from `GET /api/v1/capabilities`) so a user sees
why an action is unavailable. It never edits them.

**Split deployment.** Because each group is a separate startup capability, several API instances may
share one database with different exposure, for example an internal administration instance with
model administration enabled and a public instance with both administration flags off. See
[Architecture](ARCHITECTURE.md#deployment-topology) for what holds today and
the open caveats.

### Consequences

- Change-set routes move from the workspace administration router to an always-registered router.
  Deployments that set `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false` keep coordinated data changes.
- Stored audit event and aggregate names are renamed by migration together with tables and columns;
  change-set "activated" events become "published".
- ADR-026 and other earlier text saying "activation" of a draft reads as "publishing" a change set.
- A browser screen for workspace administration becomes possible and is shown only when the
  capability is enabled; until a second workspace exists the selector is read-only.
- The 0.12 authorization work adds roles within these three groups; it does not remove the flags.

### Acceptance

- No API route, field, table, column, stored event name, UI label or document uses "workspace draft",
  "design draft", "workspace revision" or "historical snapshot" for these concepts; "activate" is not
  used for change sets and "retire" is not used for publications.
- With `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false`, catalogue mutations are absent and the change-set
  workflow still works end to end.
- `MODEL_ADMIN_MUTATIONS_ENABLED` behavior is unchanged.

## ADR-032 — Reach other domains only through generic, composable capabilities

**Status:** Accepted, 2026-09-26. Clarifies ADR-001; nothing is scheduled
([composable domains](COMPOSABLE_DOMAINS.md)).

### Motivation

The model-driven core, with live editing, change sets pinned to a chosen model release, delta-merge
publishing and immutable publications, also fits MDM-lite (moderate-volume master domains consolidated
from source systems) and small, specific product catalogues. Growing toward them by adding
domain-specific features would split the engine into several products and break the rule that the
runtime is unaware of domain keys.

### Decision

- RDM remains the design centre (ADR-001). MDM-lite and small catalogues are applications modelled on
  the engine, not modules built into it.
- A capability motivated by another domain is admitted only when it passes the admission tests in
  [COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md#admission-tests-for-a-new-capability): nameable without
  the domain word, two real cases, a closed declarative vocabulary, composition with the full data and
  model lifecycle, and a starter model that shows it.
- High-volume party MDM, a full PIM and a general rules language in the model are out of scope.
- Current work keeps the doors listed in
  [COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md#doors-to-keep-open) open: record identity and
  redirects, value provenance, derived values, redaction within immutable history, keyed inbound
  upsert, reusable matching and review vocabulary, and additive value types.

### Consequences

- Plans touching identity, attribute storage, audit or history, bulk APIs, the consumer API `match`
  declaration or mapping coverage state whether a door is affected.
- A door may be closed only by an explicit product decision recorded here.
- Starter models for other domains are the evidence that the capabilities compose; they carry no
  runtime branch.

## ADR-033 — Store relation matrix cell states as a derived, rebuildable index

**Status:** Accepted, 2026-09-27 (Base 0.8 A3b; closes A2's D12 budget exception).

### Motivation

A relation matrix's row state filter decides over every row (D11, D12). Deriving each cell from
records per request walks every cell record under the selected columns and pairs it with its row;
at full volume that took seconds, once per paging statement. A stored ancestor table would remove the
walk but not the pass over every cell.

### Decision

- `matrix_cell_states` stores, per owner and **matrix shape**, each non-empty cell's (row, column,
  record count, count meeting the binding's condition). A shape is what a view declares and the model
  derives: relation type and direction, row, column and cell types, the container types between column
  and cell, and the condition. Its key hashes that definition, so views with the same shape share
  states and nothing names a starter type, relation or application.
- Owners: a workspace's `live` records, each `publication`, each private change set `base`, each
  `change_set` overlay, and a per-workspace publication `history` holding the first publication that
  held a record in each cell (for `historyOnly`, including a publication read's "earlier ones").
- A change set stores rows only for the row records its changes touch; those replace **all** of the
  base's rows for that record, marked by a sentinel row with an empty column. Chosen over a full copy
  per change set, which would cost a whole workspace per change set.
- `matrix_state_builds` records that one owner's states of one shape are complete, with the shape's
  definition, so maintenance needs no model. Which owners need which shapes follows from the models in
  use: live the active release's, a change set and its base the change set's release's, a
  publication its own and those of change sets based on it, the history all of them. Building and
  dropping is one idempotent sync, run at startup (each build committed separately), on model
  activation, change set creation and release change, publishing and workspace creation or deletion.
- Maintenance recomputes, never adjusts: an ORM `before_flush` hook notes relation ends, parent moves,
  attribute values and change set rows a write touches; before commit the touched rows are recomputed
  from records in each built shape. Core statements outside the ORM note their changes explicitly.
  Publishing copies live's states to the new publication and extends the history.
- A read uses stored states only when every owner it needs is built; otherwise it derives the cells
  from records as before. The filter's matching rows are read once per request and every paging
  statement filters by that list.
- The migration creates the tables empty; the startup sync is the backfill. Keeping one builder avoids
  a second implementation of the cell semantics in migration SQL, and a stopped build resumes.

### Consequences

- Records remain the only source of truth; `matrix_states.verify` rebuilds every stored owner and
  shape from records and compares, and every matrix test runs it after its writes.
- A missed maintenance path costs a wrong filter until the next rebuild, not an error, so each new
  write path that bypasses the ORM must note its changes; the tests cover every current one.
- Startup and activation take seconds at full volume when a shape is new; publishing adds one copy of
  live's states.
- Composable-domains doors (ADR-032): none affected; the table is a derived index over existing
  records, like `snapshot_attribute_values`.

## ADR-034 — A record's type can change: derived mapping, preview and apply, history as the way back

**Status:** Accepted, 2026-09-29 (Base 0.8 C0; decides D37–D43). Amends ADR-026 for one operation.
The API design is in [API.md](API.md#product-08-restructuring-api-milestone-c-design).

### Motivation

A hierarchy that has to change shape — a level inserted or removed, a branch moved to a place where
another type is allowed — can today only be rebuilt by deleting records and recreating them. That
loses the records' IDs, history and relationships, and every integration that holds an ID sees a
delete and a create. Nothing in the engine changes a record's type: every read and write route carries
the type (`/objects/{type}/{id}`) and no update accepts a new one.

### Decision

- **Identity is kept (D37).** A record whose type changes keeps its ID, creation time, history and
  every relationship the new type may have. It is one record reclassified, not a delete and a create;
  the 0.9 change feed reports it as a `reclassified` event.
- **Change sets only (D38).** A type change is staged in a change set and reaches live data only by
  publishing it, after the P2 review screen has shown it. This is a stated exception to ADR-026's
  "live by default": a type change is a structural operation over a subtree, not a single-value
  correction. Ordinary object writes never change a type, live or in a change set; only the
  restructuring operation does.
- **Same application (D39).** The new type must be one of the record's application's object types,
  as a move already requires for the parent.
- **The mapping is derived, not declared (D40).** Nothing is added to the model. The possible types
  at a place are those the model allows there (the parent's type through a parent relation type, or
  `rootCreatable` at the top). Each attribute of the new type is suggested a source, in order: the same
  attribute type; display attribute to display attribute; the one `unique` and `required` attribute
  to the one attribute of the other type that is also both; the built-in `name` always stays. A pair
  must have the same value type, or a widening that loses nothing (`text` to `longText`, `integer` to
  `decimal`); nothing else converts. A mapped value must also pass the new binding's validation, or it
  is an input to provide. The user can change any suggestion, and one choice per (old type, new type)
  pair applies to every record of that pair in the operation.
- **Relationships are kept, not mapped.** A relationship stays when the model binds the same relation
  type, in the same direction, between the other end's type and the new type; otherwise it has no
  place and is removed. The containment edge is kept when the new type's parent relation to its parent
  is the same relation type, and otherwise replaced by the one the model allows, as a move does. A
  required relation the new type has and the record lacks is an input, like a required attribute.
- **Descendants follow level by level.** A child the record's new type may still contain keeps its
  type, and the cascade stops there. Otherwise the child becomes a type the new parent may contain:
  the only one, or the one chosen once per (child type, new parent type) pair; with none possible the
  operation is refused.
- **Preview, then apply.** An operation is first planned: each record's new type and parent, each
  value and relationship as kept, mapped, restored or without a place, the inputs still needed and any
  refusals. The preview is not stored. It returns a digest of the complete plan together with the
  change set version it read; applying sends both back, and the engine recomputes the plan in the write
  transaction and refuses when either differs. A change set's content changes only through writes
  that advance its version, so the version and digest together bind the apply to what was reviewed.
- **Nothing is silently lost.** Each type change records a `reclassified` audit event with the
  record's full before state (name, parent, typed values, and the relationships it lost with their
  attributes) and the mapping used. A later type change offers values and relationships back from the
  record's *effective* reclassifications — those of the current change set and of change sets that
  were published, never of a discarded one — when the new type has a place for them again. A
  relationship offered back keeps its former relation ID.
- **Same rules as single writes.** Uniqueness, uniqueness scopes, required values and relations,
  cycles and concurrency are checked by the existing services in the same transaction; the typed
  value index, matrix cell states, relation set versions and the search index follow as for any
  change-set write. The preview runs the same checks, so a preview without refusals applies unless the
  change set changed.
- **Publishing needs nothing new.** A change set row already carries its type, and publishing already
  writes the authored type to live. The existing per-record version claim refuses a record edited live
  since the change set's base (`409 version_conflict`). A live change the record's version does not
  show — a new relationship or child the new type may not have, a value now colliding — fails the
  merged-graph validation (`422 workspace_graph_invalid`). As for other conflicts, the recovery is a
  new current-live change set; there is no rebase. Publications keep the type they were published with.
- **Routes keep their type segment (D42).** A request naming a type the record does not have in the
  selected context returns `409 object_type_changed` with the current type, for any record found under
  another type; the browser follows it to the current route.
- **Bounded (D41, D44).** One operation changes at most 500 records. C0 set 5,000; C2 measured the
  preview's dry run through the per-record write path at 48 s for 4,772 records and 2.8 s for 479, and
  D44 lowered the limit so the preview stays interactive. A larger one is refused with the limit in the
  error, never cut short. Raising it needs a set-wise write path for plans.
- **Release (D43).** 0.8.0 waits for Milestone C: it releases after R2, not after R1b.

### Consequences

- No new tables or columns: the change set row's type, the audit payload and the existing publish
  merge carry the operation. The change lists (P2a) gain the type on both sides of an entry.
- The history read keeps omitting values; the full before state lives in the stored audit payload,
  where the engine reads it for offer-backs and the 0.9 feed will carry it.
- A reviewed plan goes stale whenever its change set changes, or when publishing another change set
  changes what is offered back to one of its records.
- Composable-domains doors (ADR-032): identity stays open (the ID is kept, and `object_type_changed`
  tells a client where the record now is); attribute storage stays open (values move between bindings
  and never convert lossily); audit/history gains the `reclassified` kind, which the 0.9 change feed
  and consumer API must carry. Bulk APIs, `match` and effective dates are not touched.

### Amendment (Base 0.11 V1, D71, 2026-10-17)

A workspace's migration to another release changes record types in live data: its type mappings
(D70) reclassify every record of a mapped type, keeping IDs and history, with the attribute rules
above (same attribute, display to display). This is the one exception to D38's "change sets only": a
change set cannot hold the switch of a workspace's release, and the migration's confirmed preview,
which lists every record it reclassifies and is bound to the workspace's feed position, stands in
for the change set's review. Each record still records a `reclassified` audit event with its full
before state. A migration's value conversions (D69) are wider than D40's two widenings, each
checked value by value and a value that does not convert listed as a loss; a type change in a change
set keeps D40's rule.

## ADR-035 — Model authoring is an editor of operations on a model draft; a spreadsheet is one way to start it

**Status:** Accepted as direction, 2026-09-29 (Product 0.10). The design and its open decisions
(A-D1–A-D12) are in [MODEL_AUTHORING.md](MODEL_AUTHORING.md). Moves the structured designer's first
part from 1.0 to 0.10; renumbers production hardening to 0.11 and security to 0.12.

### Motivation

Reference data arrives as spreadsheets whose structure is flattened into cells, repeated columns and
several sheets. In the source system this engine comes from, each upload needs hand-written model JSON
and a bespoke import script. The engine's success criterion — a new application defined and released
without Python or TypeScript — silently assumes that work. A visual builder alone does not remove it:
the hard parts are mapping the workbook onto the model, validation and reviewing the load.

### Decision

- **One editor for model and mapping.** It edits a model draft together with import profiles. Opened on
  a workbook it starts from an inferred proposal; opened without one it is the structured model designer
  (US-P05).
- **Every edit is a server-side operation** on the draft at its expected version, validated by the
  installation validators and recorded in the draft's history. The editor never writes model JSON, and
  undo applies an inverse operation.
- **Inference proposes operations and never decides.** It is deterministic profiling over a pattern
  catalogue; an optional assistant may add proposals. Decisions the administrator changed are pinned
  and survive re-inference and new workbook versions.
- **An import profile is a declarative, model-referencing contract** executed by the 0.9 import job. It
  replaces the per-upload script, is stored separately from model releases and is re-checked against the
  release it runs under.
- **The lifecycles do not change.** The model goes draft → immutable release → activation; data goes
  through an import job, into a change set by default, reviewed on the existing change set review screen.
- **Operation classes.** Additive operations are always allowed; draft-only ones while their elements are
  unreleased; changes to released structure are migrations, shown with their impact and enabled in 1.0
  on the 0.11 migration boundary.
- **A list is an object type.** Picklists are limited by relation bindings, not by filtering a shared
  list type by a record's name; the model does not reference runtime records.
- **Structured, not canvas-first.** Drag and drop is a fast path with a keyboard equivalent; layout
  editing selects and orders generic components and never positions pixels.

### Consequences

- 0.9 D3 widens: the import file contract is the import profile, with XLSX and several sheets, and
  0.9 Track J designs it (MODEL_AUTHORING package A1).
- Model drafts gain an operation history and an operation API beside the whole-model patch, which the
  JSON workbench keeps.
- Models built from workbooks have many small list types; applications declare navigation groups
  (A-D2), the explicit navigation composition ADR-029 deferred until a real model needed it.
- 1.0 keeps migration-class operations, protected publish and rollback, and extension packaging.
- Composable-domains doors (ADR-032): identity and inbound flow use 0.9 upsert keys; provenance gains a
  natural source name (the profile); value types convert through the attribute registry; `match` and
  mapping coverage are not touched.

## ADR-036 — A batch is a job: one mechanism for bulk writes, imports and exports

**Status:** Accepted, 2026-09-29 (Base 0.9 design; decides D1, D10–D14). The design is in
[INTEGRATION_API.md](INTEGRATION_API.md) sections P, B and J.

### Motivation

Bulk writes, imports and exports each need outcomes per item, safe retries, cancellation, resumption
after a restart, retention and a cause recorded on the changes they make. Built per feature, these
would be defined three times with three sets of edge cases, and a synchronous bulk call whose
response is lost could not be read back at all.

### Decision

- **Every bulk write, import and export is a persisted job** with its parameters, state, stage,
  progress and one outcome per item. A synchronous batch is a job run inline within the synchronous
  limit; everything else runs in the background. The caller chooses (`run`), never the size.
- **Items go through the single-write services.** A bulk item is validated and written exactly as the
  equivalent single write, with the same error codes; bulk adds addressing by key, upsert and
  relation-set replacement, not a second validation path.
  **Amended 2026-10-02 (0.9.0-alpha.1 PG3b, PG-D12–PG-D15):** the services are split into a decide
  step and a write step. A chunk's items are decided in order by the single writes' decide steps,
  each seeing the items before it, and the accepted ones are written together in multi-row
  statements; a single write is a batch of one through the same code, so the rules and codes are
  still the single writes'. No item has a savepoint: a refused item writes nothing, and a bulk
  write that fails on a row the rules could not see is redone item by item.
- **Two failure policies, named per request:** `atomic` (all or nothing, bounded) and `independent`
  (each item in its own savepoint, committed in chunks). No default, and no "stop at first error".
- **Outcomes** are `applied` (with `created`, `updated`, `unchanged` or `deleted`), `rejected` (with
  the single-write code) or `unprocessed` (with a reason). A processed batch answers `200`; its
  `result` says whether everything applied.
- **No silent overwrite.** Updates need `expectedVersion`; an upsert that finds a record needs one too
  unless the request declares `onExisting: "overwrite"`, which is audited.
- **Idempotency keys** replay a finished job's response and refuse a reused key with a different body.
- **Chunks commit with their outcomes and the job's checkpoint**, so a resumed job never repeats or
  skips an item; a lease lets 0.11 run workers on several nodes without a contract change.
- **A job pins the model release** at creation and fails with `model_release_changed` when it moves.
- **Staging is the change set.** A job targets live data or a named change set (ADR-026); there is no
  separate staging store.
- **Limits are settings**, reported by capabilities and named in the refusal. Files live in a
  configured directory, not in database rows; jobs, outcomes, files and idempotency keys share one
  retention.
- **Job creation is a deployment capability group** (`INTEGRATION_JOBS_ENABLED`, ADR-031), on by
  default; reads are ungated until 0.12.

### Consequences

- The job table, outcome table, worker and lease are delivered with the first bulk package, not as an
  unused layer.
- Every applied item records the job as the cause of its audit entries, which the feed and consumer
  events report and a later value-source field builds on (ADR-032, provenance).
- Imports are batches built from a file: an import profile turns rows into batch items, and the
  preview runs those items in a rolled-back transaction, so preview and execution share code.

## ADR-037 — The audit log is the ordered source of the change feed and consumer events

**Status:** Accepted, 2026-09-29 (Base 0.9 design; decides D5, D8, D15, D16, C-D8, C-D11). The design
is in [INTEGRATION_API.md](INTEGRATION_API.md#f-change-feed) section F.

### Motivation

Integrations need an ordered, resumable stream of changes, and consumers need events about the objects
they read. The audit log is already written in the same transaction as every change, so it can serve
as the outbox without a second write path. Two gaps stood in the way, found against the code on
2026-09-29: the audit `sequence_id` is allocated at insert, not at commit, so on PostgreSQL two live
writers can commit out of sequence order; and a publish wrote one event without the records it
changed, whose edits had been audited earlier as change-set edits.

### Decision

- **One source.** The raw feed reads the audit log; consumer events are derived from the feed. Both
  are positioned by the same number, so their positions compare.
- **A per-workspace feed position in commit order.** Every audit entry that changes live data takes the
  next position from a counter on the workspace row, locked until commit. A live write takes that lock
  before any record row, as publish already does. Positions are gapless and never commit out of
  order, on SQLite and PostgreSQL alike. Writes in one workspace serialize; workspaces stay
  independent. Change-set edits, validation and model administration take no position.
- **A publish records what it changes.** It writes one audit entry per record it applies to live, each
  with a position and the publish as its cause, then the `published` entry. A publication's
  `feedPosition` is that entry's position, and the publication equals live data there, which makes a
  publication a valid re-sync baseline.
- **Entries carry identity and changed keys, never values**, including for `reclassified`, whose full
  before state stays in the audit log only. Readers fetch values when they need them; a redaction
  never rewrites the feed. _Amended 2026-10-25 (0.12 RH1, D389, D16 revised for history only):_ a
  record's history answers the values each entry stored, with the value before from the record's
  previous entry; the feed and consumer events are unchanged, and a redaction must also clean the
  values the audit log stores (COMPOSABLE_DOMAINS, History and erasure).
- **Retention is a setting** (30 days by default) shared by the raw feed and consumer events; an
  expired position answers `410` with the baselines to recover from (a publication or an export, each
  with its position). The setting does not prune the audit log.

### Consequences

- Migration adds `workspace_key` and `feed_position` to `audit_events` and a counter to `workspaces`;
  the feed starts empty, with no backfill.
- Every live write path acquires the workspace lock first; the first F package audits the write paths
  for this order and measures its cost against the 0.8 budgets.
- A publish of many records writes many audit entries, bounded like the equivalent single writes; the
  "publishing never amplifies events per object" rule is withdrawn.
- A visibility watermark over transaction IDs is not needed, and 0.11 exercises the same mechanism on
  PostgreSQL rather than a new one.

## ADR-038 — Business validity is a declared effective period, separate from history and publications

**Status:** Accepted, 2026-09-29 (Base 0.9 design; decides D6, D7, C-D14). The model language is in
[APPLICATION_MODEL.md](APPLICATION_MODEL.md#effective-period-effectiveperiod), reads in
[INTEGRATION_API Q4](INTEGRATION_API.md#q4-effective-periods-and-asof-d6).

### Motivation

Reference data often has business validity: a code valid from one date, retired on another. It is
easy to confuse with record history ("what did the record say then") and with publications ("what did
we release then"). SC-11 requires the three to stay separate, and the engine must not hard-code which
attributes carry validity.

### Decision

- **Declared, not inferred.** An object type declares at most one `effectivePeriod` over two `date`
  attributes it binds. Nothing else carries business validity.
- **Semantics.** Inclusive start, exclusive end, either may be empty (since always, open); dates have
  no time zone; overlaps between records are allowed and all are returned. An end not after its start
  is refused.
- **`asOf` is a filter over values.** It combines with any content context (live, change set,
  publication) and never selects one; a publication read never applies business dates unless `asOf`
  is also given.
- **Types without a period** refuse `asOf` (`as_of_not_supported`), except in the consumer XREF across
  types, which filters the types that declare one and names them in `asOfApplied` (C-D14).
  **Amended 2026-09-30 (Base 0.9 Q4, D21):** the management cross-type lookup refuses `asOf` with the
  per-type route instead. It lists several types and a period belongs to one, as a model-declared
  filter does; no management story needs a dated lookup across types.
- **One schema step.** The declaration and consumer API definitions arrive together in schema 0.8.

### Consequences

- Validity is ordinary attribute data: it is edited, versioned, audited, published and fed like any
  other value, and history and publications need no change.
- `dateTime` periods, several periods per type and period-aware uniqueness wait for a real case.

## ADR-039 — The "Open" visual direction: light, ruled surfaces with colour kept for context and state

**Status:** Accepted, 2026-10-05, by the user "for now" (U-D6, Track U U1). It may be revisited on
what U2 and U6 show in the product. The mockups are on the
[U1 canvas](https://claude.ai/artifact/GmafaZfJ6PxbXs8rGVysMc) (Direction B), and the plan is
[SETTINGS_AND_UI_PLAN.md](SETTINGS_AND_UI_PLAN.md#ui-foundation). It works within
[ADR-023](#adr-023--build-rdm-ui-components-on-react-aria-behavior): React Aria behind `ui/`
wrappers, with every style owned by RDM tokens.

### Motivation

The U1 audit of the 0.8 baselines found four near-white surfaces that do not separate regions, one
green used for actions, navigation, selection, status and plain values, and a data context
(live, change set, publication) that is easy to miss. Two directions were drawn on the same three
screens. The user chose B, "Open", over A, "Framed" (a dark frame with raised panels).

### Decision

- **Surfaces.** Light throughout. A white top bar and a warm light-grey rail, each separated by a
  1px line. Content sits on the page, not in cards. Sections and tables are separated by rules: a
  stronger rule under a section heading or table header, a light rule between rows. Dark mode
  redefines the same semantic tokens.
- **Colour has one meaning each.** The indigo accent is used only for the primary action, the
  selected lens tab and links. Selection (current collection, current row, current settings page)
  has its own indigo tint. The current application is shown by an ink underline, not by colour.
  Status hues appear only for states: green for live, amber for a change set, violet for a
  publication, red for errors and conflicts.
- **Data context.** In live data, a green "Live" chip with a one-line explanation at the top of
  the page. In a change set, an amber band across the full width of the content, above the page
  title, naming the change set with its state and its Review, Validate and Publish actions; it
  stays visible while the page scrolls. A publication uses the same band in violet. Changed fields
  and records carry the amber marker, with the live value shown beside a changed one.
- **Values are data, not status.** Booleans and other values are plain text. Pills are kept for
  states and versions.
- **Type.** Instrument Sans for text and JetBrains Mono for codes, keys and URLs, both under the
  SIL Open Font Licence. They are bundled with the engine and served from it, since the UI must
  work without internet access (as the API reference page does, V1). Hierarchy comes from size and
  weight: page titles 30px semibold, section headings 15px semibold, column headers 12px semibold
  in the tertiary ink.
- **Shell.** The top bar holds the product mark, then the workspace switcher, then the
  applications as underlined tabs, with Settings and the account at the right. Settings uses the
  same frame and the same top bar (no tab current, Settings current) with a grouped side
  navigation in the rail. _Revised 2026-10-06 (U-D14): Settings first had a top bar of its own
  ("{product} / Settings", "Back to applications"). Revised 2026-10-11 (0.10 N1, the user's
  request): below 760px the top bar shows no application tabs in any area; an application page's
  band is one line whose workspace, application and data context each open their choice, and
  Settings returns through its Back link._

### Consequences

- U2 turns the mockup's values into the three token layers and checks every text and border pair
  for WCAG AA contrast in light and dark. Every visual baseline changes; each is re-recorded with
  its screenshot inspected, surface by surface (U2 the shell, U3 settings, U6 the rest).
- The two fonts and their licences are added to OPEN_SOURCE in U2.
- Direction A's ideas that B does not use (a dark frame, raised panels) are not carried over
  piecemeal. A change of direction is a new decision.
- _Note 2026-10-06 (U-D8):_ the user kept a `Card` component in U2, since the UI is not final.
  Whether content sits on the page or in cards is judged in the product after U2 and U6, not ruled
  out in advance.

## ADR-040 — The "Atlas" visual direction: today's calm shell, a colour for every kind of record

**Status:** Accepted, 2026-10-06, by the user ("looks good, let's see it implemented"), after
comparing five looks on the same screen with real data on the
[look canvas](https://claude.ai/artifact/P4BpxdQdyVYTAaQMRGnRFB) (look E, "the mixture").
Supersedes [ADR-039](#adr-039--the-open-visual-direction-light-ruled-surfaces-with-colour-kept-for-context-and-state)
where they differ; ADR-039's shell, type and shapes stay. Works within
[ADR-023](#adr-023--build-rdm-ui-components-on-react-aria-behavior). The design rules are in
[SETTINGS_AND_UI_PLAN § Atlas](SETTINGS_AND_UI_PLAN.md#atlas-adr-040); the package is
[UA](SETTINGS_AND_UI_PLAN.md#ua-the-atlas-redesign).

### Motivation

After U2 and U3 the user found the UI incoherent and not good to look at: parts of the product
were in different generations of style, the record browser did not show what contains what (type
groups, folders and records looked alike), and colour carried almost no meaning. Building the
direction slice by slice from written rules, judged by tests, had drifted from the mockups. The
user asked for a design that is clean and professional but also colourful and playful, and chose
look E: the current app's structure with the "Atlas" colour system.

### Decision

- **Kept from the current app:** the top bar (mark, product name, the applications as plain tabs
  with an ink underline, Settings and the account at the right), the warm light-grey rail with the
  workspace switcher at its top (as before U2), Collections and Browse records, Instrument Sans and
  JetBrains Mono, and the moderate shapes: 6px on controls and chips, 8px on cards.
- **Colour means a kind of record.** Every object type has one hue from a fixed palette, used the
  same way everywhere it appears: its tile in the collections, its icon in the tree, its chip in a
  table column and in breadcrumbs, the record header and the related records in the inspector. A
  soft fill with a dark ink of the same hue, at 4.5:1. The engine stays unaware of type keys: the
  hue comes from the model (U-D13).
- **Colour means where you are.** Green for live data, amber for a change set, violet for a
  publication: the context strip, its dots and the change markers.
- **The record browser shows structure:** the type icon on every record, indent guides for
  containment, counts at the right, and the selected record highlighted in its type's colour.
- **Applications** each carry a small coloured tile in the top bar, with more space between the
  product name and the tabs.
- **One accent for actions:** indigo for the primary action and links, as before.

### Consequences

- UA restyles every surface in one pass, starting from the record browser, and replaces the older
  styles instead of layering on them. The user judges each surface by screenshots before the next.
- Tests guard behaviour, accessibility and contrast; they are not evidence that a screen looks
  right.
- The design before UA is kept at the git tag `ui-before-atlas`, so it can be compared or restored;
  how is in [UA's revert point](SETTINGS_AND_UI_PLAN.md#ua-the-atlas-redesign).

## ADR-041 — Model drafts change through recorded operations

**Status:** Accepted, 2026-10-11, by the user with the
[Base 0.10 A0 plan](BASE_0_10_IMPLEMENTATION_PLAN.md#a0-plan-2026-10-11) (D4, D17, D19). Builds on
[ADR-035](#adr-035--model-authoring-is-an-editor-of-operations-on-a-model-draft-a-spreadsheet-is-one-way-to-start-it).
The contract is in [API.md § Model authoring](API.md#model-authoring-product-010-designed).

### Motivation

ADR-035 made the editor an editor of operations. Undo, redo, a stale editor catching up, inference
proposals and a profile following a renamed element all need the same thing: each change to a draft
as a typed record with what it changed and how to take it back. Until 0.10 a draft changed only by a
whole-model `PATCH`, and its audit events record which top-level fields changed, not how.

### Decision

- **Every change to a draft is an operation stored in the draft's history**: kind, parameters,
  inverse, draft version, author and time, grouped in steps (one request, one step). A whole-model
  `PATCH` is recorded as one `replaceModel` operation with the previous model as its inverse, so
  the history is complete whichever client wrote.
- **The inverse is stored when the operation is applied**, not derived later, so undo never depends
  on the model staying as it was. Undo and redo are new steps that apply inverses; nothing in the
  history is rewritten.
- **The history belongs to the draft** and is deleted with it. A release keeps none: it is an
  immutable snapshot, and its differences from another release are the semantic diff.
- **Elements are named by key** in operations, never by position, so an operation means the same
  after the model around it changed.
- **What is released is decided against the draft's base release**, and an installation makes the
  release it created the new base.
- **The server produces layout changes**: generated views and panels for a new type, and the
  placement of an attached attribute or allowed relation, so every client gets the same model from
  the same operations.

### Consequences

- The editor never writes model JSON; integrators can drive the same changes through the API.
- Operations may leave a draft invalid between steps; validation stays the compiler's and installation
  refuses an invalid draft as before.
- Migration-class changes (1.0) are new kinds in the same history, applied through ADR-034's
  restructuring of records.

## ADR-042 — Each workspace runs its own model release

**Status:** Accepted, 2026-10-15, by the user with the
[Base 0.11 P0 plan](BASE_0_11_IMPLEMENTATION_PLAN.md#p0-plan-2026-10-15) (D4–D11, D23–D29).
Supersedes the closing paragraph of
[ADR-021](#adr-021--introduce-strict-typed-views-in-schema-05). The contract is in
[API.md § Workspace models](API.md#workspace-models-product-011).

### Motivation

Different workspaces of one organisation's instance must be able to run different models, not only
different versions of one model, each installed, activated and migrated without touching the others
(the user, 2026-10-15). Until 0.11 one singleton row (`model_runtime_state`) named the release every
request resolved, and activation checked and switched every workspace at once. This is not
multi-tenancy: hosting stays one instance per organisation.

### Decision

- **A model is the line of releases sharing one `release.key`.** Releases stay instance-wide,
  immutable and installed once; only their assignment is per workspace.
- **Every workspace names its release** (`workspaces.model_release_id`). Nothing follows a default:
  a workspace created without a release starts on the default workspace's release, and changing the
  default workspace moves nothing. The singleton `model_runtime_state` and `model_releases.is_active`
  are removed.
- **A request resolves its workspace first, then that workspace's release.** No request combines two
  snapshots; a read spanning workspaces resolves each workspace's snapshot on its own and names it in
  every item. A route that names no workspace reads the default workspace.
- **The commit guard is per workspace:** a write checks under a share lock on its workspace's row that
  the workspace still runs the release it was validated under; activation locks that row.
- **A read is held to its release too** (0.11 N1, D166): a request that did not commit checks before
  it answers that its workspace still runs the release it resolved, and is refused otherwise, so no
  request answers one release's model over another's data in any process.
- **Activation targets one workspace.** Its compatibility check, contract check, unique values,
  matrix states and subscription suspension cover that workspace only. A change set pinned to a
  release its workspace no longer runs cannot publish until it is moved or discarded.
- **What was instance-wide follows the workspace's model:** import profiles are bound to a model,
  jobs and dry runs resolve their workspace, consumer API definitions, events and webhooks are per
  workspace, and a consumer API key may mean different contracts in two workspaces.
- **A workspace whose release cannot be loaded is unavailable on its own;** the others serve.
- **Schema versions 0.5–0.10 run side by side**, since every one compiles into the same internal
  model; the window and its conversion rules are written down in 0.11 V4.
- **Data meets across models only through a move** (0.11 Track X): there are no relationships
  between workspaces, and a moved record is a counterpart whose origin is recorded.

### Consequences

- About 30 modules change from "the active release" to "the workspace's release" (M1–M4); while every
  workspace names the same release, behaviour is 0.10's.
- Snapshot propagation across processes (N1) and model-derived indexes (Q2) are built per workspace
  from the start.
- Workspace groups owning a model history (unscheduled) stay possible: release identities remain
  instance-wide.

## ADR-043 — Identity and tokens issued by the engine

**Status:** Accepted, 2026-10-23, by the user with the
[Base 0.12 P0 plan](BASE_0_12_IMPLEMENTATION_PLAN.md#p0-plan-2026-10-22) (D224, D225, D234, D235,
D250–D254; D251 amended by the user: access tokens last an hour). Implements C-D1. The contract is in
[API.md § Security](API.md#security-product-012-designed).

### Motivation

Until 0.12 nothing is authenticated: every route answers anyone who reaches it, and changes record a
cause but no actor. 0.12 must authenticate people and systems on the management API, the frontend and
the consumer APIs alike (ROADMAP), with no API keys and no credential in a URL (C-D1).

### Decision

- **The engine is the OAuth 2.0 authorization server** and issues one token format for every
  caller: the browser (authorization code with PKCE `S256`), clients (client credentials) and the
  "try it" console. A sign-in provider (OpenID Connect) may prove who a person is; the engine still
  issues the token. Local accounts exist beside providers, for the first administrator, small
  installations and a way back. SAML and LDAP are not supported.
- **Principals:** users and OAuth clients. Both are deactivated, never deleted, so history always
  resolves a name (D237).
- **An access token proves who, never what.** A JWT signed with ES256: subject, principal kind,
  audience (`management` or `consumer`), expiry and, for a person, the session. Permissions are
  looked up on the server per request (ADR-044), together with whether the principal is active and
  the session open, so a change applies on the next request and a token's lifetime (an hour) is not a
  security window for revocation.
- **The browser** keeps the access token in memory and the refresh token in an `HttpOnly`, `Secure`,
  `SameSite=Strict` cookie read only by the token and revocation endpoints. Refresh tokens are
  opaque, stored hashed and rotated on every use; a reused one ends the session. The frontend and the
  engine share a site.
- **Signing keys** live in the database, sealed under `SECRETS_ENCRYPTION_KEY` (the one setting for
  every sealed secret, replacing `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`), published at
  `/oauth/jwks` by `kid`, rotated every 30 days with the previous key verifying until its tokens
  expire, and retired at once by "rotate now". Refresh tokens and client secrets are never signed
  with them, so a rotation needs no action from anyone.
- **Passwords** (local accounts): 15–128 characters without composition rules, common ones refused,
  hashed with Argon2id; failed sign-ins slowed per account and address, never locked. MFA is left to
  the sign-in provider.
- **No switch turns authentication off.** Development and tests use real tokens; the first
  administrator comes from a CLI command on the server.
- **Open routes:** `/health`, `/health/live`, `/openapi.json`, `/docs` and its script, and the OAuth
  endpoints, which answer errors in the RFC's shape. Everything else needs a token.

### Consequences

- Every test harness obtains real tokens (I1); the browser reads its job stream and downloads with
  `fetch`, since `EventSource` and links cannot carry the header.
- Local accounts have an optional second factor, an authenticator app with recovery codes, which an
  administrator can require with every password (0.12 I4b, D383–D388; D225 revised); OPERATIONS still
  advises a provider in production. Passkeys are a second factor and a way in alone (0.12 I4c,
  D389–D394), verified by `webauthn`, bound to the host of `PUBLIC_URL`; the engine's pages run one
  script of its own where a passkey is offered, and none elsewhere (D390; D275 revised).
- A stolen access token works for up to an hour while its holder stays active.
- A person signing in through a provider is found by the provider and the token's subject, never by
  e-mail, and created at their first sign-in (0.12 I3, D363); someone with a local account becomes
  a second person. A provider's groups are groups of the engine whose membership each sign-in sets
  (D364). Local sign-in can be turned off once a provider works, the administrators made on the
  server keeping it as the way back (D365).
- An administrator moves a provider identity onto the person who already had a local account after
  the first sign-in made a new one, never automatically and never by e-mail (0.12 I4a, D377); it
  moves the identity and provider groups, deactivates the new person, and is refused for a person
  with a password, direct roles or local groups (D378). Signing out of a provider is per provider and
  off by default (D379); the app signs out by navigation so the engine can send the browser on with
  the ID token it kept sealed (D380). While local sign-in is off, the last person who keeps it
  cannot lose it (D381).

## ADR-044 — Authorization: action groups, roles and grants

**Status:** Accepted, 2026-10-23, by the user with the
[Base 0.12 P0 plan](BASE_0_12_IMPLEMENTATION_PLAN.md#p0-plan-2026-10-22) (D226–D231, D236, D241,
D243–D249, D255–D257). Z2 (2026-10-23) settled how the write-unit check works (D289–D297). Corrects ARCHITECTURE's "model-configurable permissions" and ADR-031's
release number. The catalogue is in [API.md § Security](API.md#security-product-012-designed).

### Motivation

Every operation must be authorized against what the caller may do in that workspace, and the exit
gate asks that no administrative, bulk, job, feed or consumer path bypass it. An administrator
thinks in jobs ("may publish"), not in 157 routes, and people who should only read, or only propose,
must be served as well as stewards (the user's ideas, 2026-10-22).

### Decision

- **Every route declares its action; actions belong to action groups** named after journeys
  (Browse, Edit live, Work in change sets, Publish, Approve publications, Bulk and import, Copy and
  move, Model authoring, Model release, Workspace administration, Integration administration, Feed,
  Operations, Security administration). A route without a declaration fails the contract test.
- **Roles are sets of action groups.** Nine predefined, read-only roles named after the personas
  (Reader, Contributor, Data steward, Data owner, Model administrator, Workspace administrator,
  Integration administrator, Operator, Security administrator); custom roles are made from scratch or
  copied.
- **Grants** give a role to a user, a group or a client, at the instance or in a workspace, and may
  narrow **writes** to applications and record types. Reads are per workspace: a reader sees the
  whole workspace, because relations, coverage, the lookup, the feed and exports cross applications;
  data some readers must not see goes in its own workspace. A client is granted a consumer API in a
  workspace instead of a role (Z3, D306–D309): one API in one workspace, never narrowed, never at
  the instance; only such a grant opens the consumer data routes, checked by the consumer router
  after the token and the workspace and before the definition, so a caller without a grant cannot
  probe which API keys exist.
- **Roles and grants are runtime data,** in the database, managed through the API and the Security
  pages. They are never part of a model release: a model must not be able to grant itself access, and
  roles change without a release. Grants refer to applications and record types as data; a grant
  naming one the model no longer has is reported, never widened.
- **Two checks on every path:** at the route, for the action and the workspace; at the write unit,
  for the record types written, tested once over the work's distinct types against what the
  caller's grants allow there (Z2: a record whose application or type a grant names, grants adding
  up, a relationship by either end, D289–D291). Bulk work, imports, moves, publications, type
  changes and jobs pass both; a job runs with its requester's permissions, checked at submission,
  confirmation and each step (D294). The write unit learns the caller from a writer the route check
  or the worker puts on the session, and writes nothing without one (D292).
- **Every change names its actor, from the same writer** (Z4, D313): each audit entry records the
  person or client the session writes as, beside its cause (a job's entries name the requester, a
  publication's the publisher), or the engine when nobody is; names are resolved when read (D237).
  Changes to access and sign-ins are security events in the same log (D317, D318). Consumer events
  name no actor (D239).
- **Live and change-set writes are separate permissions** on the same routes: the request's
  `changeSetId` decides which is checked. This is what lets a Contributor change data only by
  proposing it.
- **Lists are filtered to what the caller may browse; a named resource the caller may not use is
  refused** with `403 FORBIDDEN` naming the action, its groups and the workspace.
- **Permissions are looked up per request** from a per-process cache kept by a generation number
  that PostgreSQL triggers raise when a grant, role, group, membership or principal changes, read
  in the request's authentication statement (Z1, D278, which replaced `pg_notify`: no cross-process
  signal existed to reuse).
- **Deployment flags stay** as defence in depth: a flag decides whether the installation exposes an
  operation, a role whether this caller may use it. The workspace administration flag stays on by
  default, now protected by a role.

### Consequences

- The catalogue's upkeep: each new route names its action, which the contract test enforces and the
  OpenAPI document publishes.
- One cached lookup per request.
- No record-level or field-level rules; they come only on demonstrated need.

## ADR-045 — Change-set publication approvals

**Status:** Accepted, 2026-10-22, by the user (D232, D233, D242), recorded with the
[Base 0.12 P0 plan](BASE_0_12_IMPLEMENTATION_PLAN.md#p0-plan-2026-10-22). Moves change-set
publication approvals from 1.0's protected publishing into 0.12 (Track A, after the cut line);
approving a model activation or a rollback stays in 1.0.

### Motivation

With live editing and change-set work as separate permissions, a Contributor's change set otherwise
waits until someone notices it. PRODUCT.md requires a stated benefit and an explicit decision for any
mandatory review step, because a data owner's daily correction must stay live when saved (ADR-026).

### Decision

- **No one is forced through an approval** unless a role or a workspace policy asks for it. With the
  predefined roles, a steward publishes in one step, as before.
- **A change set may be submitted** (frozen; an edit withdraws the submission), then **approved**
  (which publishes it, bound to the reviewed version and the workspace's active publication) or
  **sent back** with a comment. A holder of Approve publications with "own" approves their own in the
  same step as publishing; a workspace's four-eyes policy removes "own" there.
- **Each decision is a row of its own** (who, when, version, outcome, comment), so several approvers
  or ordered stages can be added later without a contract change.
- **Notifications:** a per-principal inbox in the engine (API and top bar) and webhook events for each
  step; no e-mail. An organisation's own process tool drives longer processes through the events and
  the API; there is no workflow engine.

### Consequences

- Track A: three packages after 0.12's cut line; if 0.12 must ship sooner they follow in 0.12.x.
- A person learns of a request only in the app unless the organisation routes the events.
