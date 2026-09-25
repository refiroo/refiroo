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

**Status:** Accepted; live/draft application consolidated by ADR-026 and ADR-027

Attribute types may declare `features.unique`. Uniqueness is enforced at create and update by the
service layer, scoped to a single workspace and to the attribute type key. This keeps the runtime
generic (no object-type or domain branches) and avoids inventing one physical unique index per dynamic
attribute type. `json` values are excluded because their equality is not order-stable; declaring
`unique` on a `json` type is rejected at model load. The tradeoff is a race window under concurrent
writers; a database-level constraint (partial unique index or a dedicated unique-key table) is the
planned hardening for PostgreSQL.

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

Workspace-scoped model-release assignment is deliberately separate. It can later provide staged
tenant or governance-domain migration, but running workspaces on different schema-language versions
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
product 0.10 own the remaining work described below. This decision consolidates ADR-026 and explicitly
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
as a reviewed model-and-data migration flow in product 0.10, alongside GAP-08's accepted migration and
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
for other workspaces. The 0.10 plan must use its workspace-scoped assignment/migration capability; the action must not
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
- Product 0.10 validates preview, explicit loss confirmation, cancellation, stale-review refusal,
  atomic migration/switch, history preservation and isolation of unaffected workspaces.

Decision acceptance is not implementation evidence. Every package and release records the stories,
actual channels exercised, failure outcomes, skips and simplicity comparison from the product
validation guide. No component-only pass establishes a complete browser journey.

## ADR-028 — One draft may prepare the next model version while live keeps the current one

**Status:** Accepted product direction, 2026-09-10. Backend version selection delivered in WP-6
(2026-09-14); browser selection remains WP-7. The work splits across two
releases: letting a draft work under a version the user chooses is **product 0.7 work**, and moving a
draft onto a version its content does not already fit is **product 0.10 work**, reusing the conversion
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
exact-confirmation machinery ADR-027 places in 0.10, applied to that draft and the live data under it.

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

Product 0.10 delivery additionally requires: a preview and confirm-or-cancel contract bound to the
exact reviewed versions, whole-graph revalidation under the target, and conversion of stored content
the target does not already accept. Nothing on any path forces a change through, moves a draft without
being asked, or switches the version used across the product; and reading, editing and discarding a
draft under a version that has since been replaced keeps working without needing model agreement.

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
