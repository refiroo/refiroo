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

**Status:** Accepted for product 0.7; live/draft scope consolidated by ADR-026 and ADR-027

Mapping concurrency belongs to the complete directional relation set, not to an object or one relation
instance. A source object may currently have zero, one or several matching edges, so neither an object
version nor an individual relation version can protect create, remove, replace and ambiguous-state
resolution consistently. Mapping mutations target stable records in a live workspace or an explicitly
selected design draft. Live replacement is immediately visible; draft replacement remains staged.
This replaces ADR-024’s former draft-only mapping scope.

The planned `relation_set_versions` contract stores one optimistic integer version for an exact binding:
workspace and explicit live/draft context, relation type, `fromObjectTypeKey`, `toObjectTypeKey`, stable anchor object and `outgoing`
or `incoming` direction. Including both endpoint types prevents two allowed bindings of the same
relation type from sharing and replacing each other's set. Every generic relation create, attribute
update or delete atomically increments the outgoing and incoming sets for that exact binding.
Mapping-grid rows return this value as `mappingVersion`; a previously untouched set has version zero,
claimed safely under the scope's database uniqueness constraint.

The product 0.7 mapping operation accepts explicit content context and direction,
`sourceObjectTypeKey`, `targetObjectTypeKey`, `expectedMappingVersion`, a nullable `targetObjectId` and
relation attributes. Endpoint type keys remain required when the target is null so removal cannot
broaden its scope. A null target removes the complete selected-target set and requires empty
attributes. A non-null target replaces the complete set with exactly that target, allowing one
operation to create, replace or resolve an ambiguous mapping. The service validates workspace status
and draft status when a draft is selected, candidate endpoint records, endpoint types, direction, the exact allowed relation binding,
cardinality and typed relation attributes. Mapping views reject containment and required ownership
bindings because the record operation owns those relationships. The former draft-nested PUT proposal
is superseded; freeze the canonical live/optional-draft route and request contract in the 0.7 package
before implementation. No mapping endpoint is delivered by this decision.

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
replacement must not require workspace activation.

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
The fresh current-live draft base and dependent authority checks remain implementation work; the earlier
blanket “implemented” label overstated completion. ADR-027 consolidates the accepted 2026-09-08 product
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
  content** and its record versions at creation. The current implementation only supports empty or
  selected-revision bases; WP8.1 must close this gap. Empty drafts are development/bootstrap support,
  not the ordinary user starting flow. Historical-source creation remains a distinct choice.
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
current oldest-first behavior is an implementation correction, not an alternate accepted UX.

Current live cursors bind endpoint/query/workspace/order, without a model or publication revision token.
They survive publication and are not frozen dataset snapshots. Draft and history cursors bind their
selected identities and query. A stronger future consistency guarantee requires an explicit contract
change and tests, not a documentation-only assertion that tokens already contain those identities.

### Historical drafts incompatible with the active definition

The user requires a warning and **confirm schema replacement with potential data loss, or cancel**
when a historical draft cannot be applied under the current active definition. Preserve that requirement
as a reviewed model-and-data migration flow in product 0.10, alongside GAP-08's accepted migration and
workspace-model assignment boundary. It is not implemented by adding a force flag to Base 0.6 activation.

The preview names one selected workspace and one installed immutable target release, normally the
historical draft’s pinned release. Confirmation migrates current live data to that target and changes
only the selected workspace’s model assignment; it does not silently repin the draft to today’s model.
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
