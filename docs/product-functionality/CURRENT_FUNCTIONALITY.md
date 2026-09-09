# Current functionality catalogue

This catalogue retains the 2026-09-07 assessment with targeted source-review corrections on
2026-09-08. “Browser” and “API” are kept separate so that backend coverage is not mistaken for a
complete user experience. No application tests were executed for this documentation update; see the
[review boundary](PLANNING_HANDOFF.md#authority-and-review-boundary).

## Summary

| ID  | Function                                                  | Browser             | API            | Current assessment               |
| --- | --------------------------------------------------------- | ------------------- | -------------- | -------------------------------- |
| F01 | Model-defined applications                                | Implemented         | Available      | Browser validation pending       |
| F02 | Workspace discovery and selection                         | Implemented         | Available      | Non-default detail gap           |
| F03 | Find, filter, sort and page through records               | Implemented         | Available      | Browser validation pending       |
| F04 | Inspect a record and its context                          | Default only        | Available      | Non-default context is dropped   |
| F05 | Maintain live records                                     | Temporarily unwired | Available      | WP9 must enable browser editing  |
| F06 | Maintain typed field values                               | Components present  | Available      | Browser completion is WP9        |
| F07 | Maintain containment and hierarchy                        | Components present  | Available      | Specialist tree is roadmap       |
| F08 | Maintain ordinary relationships                           | Components present  | Available      | Dedicated mapping is roadmap     |
| F09 | Maintain translations                                     | Components present  | Available      | Translation workspace is roadmap |
| F10 | Preview and confirm dependent deletion                    | Components present  | Available      | Browser completion is WP9        |
| F11 | Inspect record history                                    | Default only        | Available      | Non-default context is dropped   |
| F12 | Prepare a workspace design draft                          | Unavailable         | Available      | Browser completion is WP9        |
| F13 | Validate and activate a design draft                      | Unavailable         | Available      | Browser completion is WP9        |
| F14 | Browse immutable workspace history and retire publication | Unavailable         | Available      | Browser completion is WP9        |
| F15 | Inspect and release application models                    | Implemented         | Available      | Browser validation pending       |
| F16 | Consume stable, bounded APIs                              | API concern         | Available      | Advanced integration is roadmap  |
| F17 | Recover from concurrent changes                           | Partial UI          | Available      | Full browser journeys pending    |
| F18 | Use accessible and responsive foundations                 | Foundation present  | Not applicable | Real-browser proof pending       |
| F19 | Operate and recover the service                           | Operator messages   | Available      | Production hardening is roadmap  |

## F01 — Model-defined applications

**User outcome:** A team can offer different reference-data applications without developing a new
backend and frontend for each domain.

Users can move between model-defined applications and views. The starter currently demonstrates Master,
Systems and Translations. Navigation, record types, fields, relationships, tables and detail layouts are
read from the installed application model. The runtime is not supposed to recognize starter names as
special cases.

What users experience:

- application and view navigation generated from the active model;
- labels and fields appropriate to the selected record type;
- configured detail panels for attributes, children, relationships, tables and hierarchy; and
- a safe fallback detail composition when no tailored detail layout is supplied.

Limits:

- only a strict table is currently supported as a top-level view;
- mapping grids, dedicated forms, dashboards and tree views are rejected until honest implementations
  exist; and
- structured self-service model design is a later roadmap capability.

Evidence: [application shell](../../frontend/src/app/AppShell.tsx),
[view registry](../../frontend/src/features/objects/views/registry.ts),
[application model specification](../APPLICATION_MODEL.md).

## F02 — Workspace discovery and selection

**User outcome:** A person knows which governed dataset they are viewing and does not accidentally work
in an invented or misspelled workspace.

Users can select a known workspace by label, search the catalogue and retain the stable workspace key
in the page address. One workspace is the default when a link omits the selection. Retired workspaces
remain readable and are visibly read-only.

Workspace administrators can, through the API, create a workspace, change its label or status and
atomically select the default. A workspace key cannot be renamed or deleted. The current default cannot
be retired.

Safety and limits:

- an unknown explicit key fails rather than silently falling back;
- catalogue retirement is different from retiring a published data revision;
- workspace administration is controlled by a deployment setting that defaults on in the current
  pre-authentication product; this is not user authorization; and
- no workspace-management screen is currently documented as complete.

Current browser limitation: selecting and listing a non-default workspace works, but opening a record
does not currently carry that workspace into the detail, history or relationship requests. The backend
then resolves the omitted context to the default workspace and rejects the mismatched record. Until WP9
repairs the complete context handoff, the browser detail journey is reliable only for the default
workspace.

Evidence: [workspace selector](../../frontend/src/features/workspaces/WorkspaceSelector.tsx),
[workspace service](../../backend/app/services/workspaces.py), [ADR-019](../DECISIONS.md#adr-019--persist-and-retire-globally-scoped-workspaces).

## F03 — Find, filter, sort and page through records

**User outcome:** A steward can locate a value in a large workspace without downloading everything or
searching only what the browser has already loaded.

The browser provides model-defined collection tables with:

- free-text search across names and configured searchable fields;
- typed filters selected by the table definition;
- one configured sort at a time, including descending order;
- a declared page size and forward/backward cursor navigation;
- empty and retryable error states; and
- URL-backed workspace, search, filter, sort and page-size state.

Supported daily-use filters include text equality/contains/starts-with, numeric and date comparisons,
boolean equality, null checks and the distinction between a missing optional field and a stored null.
Filters combine predictably and invalid typed input is rejected.

Limits:

- multi-sort, relation-expanded filtering and integration-scale query expressions are deferred;
- pages are intentionally bounded; there is no “return everything” shortcut; and
- changing the query or content context invalidates a cursor that no longer represents the same list.

Evidence: [collection view](../../frontend/src/features/objects/CollectionView.tsx),
[typed query tests](../../backend/tests/test_typed_table_queries.py), [ADR-021](../DECISIONS.md#adr-021--introduce-strict-typed-views-in-schema-05).

## F04 — Inspect a record and its context

**User outcome:** A user can understand a record without reconstructing its meaning from separate raw
tables.

For the default workspace, the current browser can open a record from a collection or explorer and show
model-defined:

- breadcrumbs and parent path;
- title, type and descriptive fields;
- typed attributes;
- contained children;
- incoming and outgoing relationships;
- related tables and hierarchy context; and
- independently paged audit history.

Opening and returning retains the originating collection address so the user does not lose the search,
filters or sort that led to the record. Failed reads have explicit retry and back actions.

Current limitation: detail, history, attribute and relationship requests omit the selected workspace
context. Opening a record from a non-default workspace therefore fails rather than completing this
journey.

Evidence: [object detail](../../frontend/src/features/objects/ObjectDetail.tsx),
[panel registry](../../frontend/src/features/objects/panels/registry.tsx).

## F05 — Maintain live reference-data records

**User outcome:** A data owner can add or correct an everyday reference value without opening a draft
or publishing a release.

The API supports creating, editing and deleting records directly in an active workspace. A successful
change is immediately visible to active reads, advances the record version and produces audit history.
It does not create a workspace draft or workspace revision.

Record creation can include its typed fields, parent and permitted initial relationships in the same
request. This is existing generic behavior, not translation-specific orchestration: the live
`create_object_record` service checks required incoming relationships, creates the record and its
initial relationships in the request transaction, then commits. This does not imply a general
multi-record transaction API or automatic creation of missing target records. Browser completion and
direct end-to-end failure evidence remain required by SC-03.

The same record operation can instead name a workspace design draft. In that case it changes the draft
candidate and remains separate from live data until activation.

Current implementation gap: generic object forms exist and are tested, but record detail currently
passes an unconditional `readOnly` instruction to its panels. This is not a product rule. WP9 must
remove that temporary wiring limitation and expose normal live editing, while also allowing an
explicitly selected design draft as an alternative context.

Evidence: [object API](../../backend/app/routers/objects.py),
[record creation service](../../backend/app/services/objects.py),
[object form](../../frontend/src/features/objects/ObjectFormDialog.tsx),
[temporary detail-page wiring](../../frontend/src/features/objects/ObjectDetail.tsx),
[ADR-026](../DECISIONS.md#adr-026--active-workspaces-are-live-writable-for-data-drafts-are-the-design-path).

## F06 — Maintain typed field values

**User outcome:** A value remains a number, boolean, date or other declared type instead of becoming an
unreliable text representation.

The product supports text, long text, integer, decimal, boolean, date, date/time and JSON values. It
enforces required fields, defaults, read-only bindings, numeric ranges, cross-field “at least one” rules
and configured uniqueness. Users can add, change and remove an individual optional value through the
API.

Interface components distinguish a missing optional value from a stored false, zero, empty or null
value and provide model-appropriate editors. They are not currently connected to a writable detail
journey.

Evidence: [attribute service](../../backend/app/services/attributes.py),
[attribute panel](../../frontend/src/features/objects/panels/AttributesPanel.tsx).

## F07 — Maintain containment and hierarchy

**User outcome:** A steward can place a record under the right parent while the product preserves the
meaning and integrity of the hierarchy.

Creating or moving a contained record updates both its efficient parent path and its meaningful typed
parent relationship as one operation. The product rejects a wrong parent type, a cycle or an attempt to
edit the engine-managed parent relationship separately.

The browser can inspect hierarchy through the explorer, breadcrumbs, hierarchy panels and child tables.
Generic parent selection exists in the record form but is not currently connected to a writable flow.
Lazy specialist tree browsing and keyboard reparenting are planned for 0.8.

Evidence: [explorer](../../frontend/src/features/objects/Explorer.tsx),
[hierarchy panel](../../frontend/src/features/objects/panels/HierarchyPanel.tsx),
[ADR-006](../DECISIONS.md#adr-006--maintain-containment-and-typed-parent-relations).

## F08 — Maintain ordinary relationships

**User outcome:** A user can connect records using business-meaningful relationship names and rules.

The API supports listing relationships in either direction, creating ordinary relationships, editing
their declared attributes and removing them. It validates the record types, permitted direction,
cardinality, requiredness and typed relationship attributes. Parent relationships are visible but
cannot be changed through ordinary relationship controls.

Generic browser components support related-record lookup, creation, edit, delete, paging and following
a linked record. They are temporarily disabled by the incomplete detail-page wiring, not by the product
contract.

This function is not the dedicated mapping product. Today a generic relationship can represent a
mapping, but coverage states, atomic replacement, candidate workflow and mapping-specific concurrency
arrive in product 0.7.

Evidence: [relations API](../../backend/app/routers/relations.py),
[relations panel](../../frontend/src/features/objects/panels/RelationsPanel.tsx),
[ADR-011](../DECISIONS.md#adr-011--relation-instance-crud-mutates-only-non-parent-edges).

## F09 — Maintain translations

**User outcome:** A localization steward can store translated content for a governed target and
language without creating an invalid or duplicate active translation.

Translations currently use the same generic record and relationship behavior as other reference data.
A translation can be created with its group, target and content in one valid operation. The configured
model allows Domain, Codelist and Master Value targets, requires meaningful translated content and
prevents duplicate business-active target/language combinations.

Backend behavior is available and generic interface components exist, but there is no complete writable
browser journey. A coverage matrix and translation-focused workflow are planned for 0.8.

Evidence: [translation tests](../../backend/tests/test_translations.py),
[ADR-014](../DECISIONS.md#adr-014--create-required-translation-targets-atomically).

## F10 — Preview and confirm dependent deletion

**User outcome:** A person understands what else will be removed before confirming a destructive
change.

A first deletion attempt can return a structured impact preview without changing data. It identifies
contained children, owned dependants and affected relationships. The caller must explicitly confirm a
cascade before the product removes owned dependants. Independent associated records are unlinked rather
than accidentally deleted.

For a live edit, deletion takes effect immediately and is audited. For a design draft, it becomes a
candidate removal and does not alter live or historical content before activation. Historical snapshots
and audit history are never retroactively erased.

The two-stage browser dialog exists but is not currently reachable because detail-page mutation wiring
is incomplete.

Evidence: [deletion service](../../backend/app/services/deletion.py),
[ADR-012](../DECISIONS.md#adr-012--preview-destructive-graph-cascades-and-derive-ownership-from-relation-bindings).

## F11 — Inspect record history

**User outcome:** A user can see how a record and its connected relationships changed over time.

Object detail includes an independently paged history panel. Loading older entries does not discard
already loaded history, and a failed next page can retry the exact continuation. Audit output is
bounded and avoids exposing complete model documents or unrelated sensitive configuration.

Limits: authenticated actor identity is not yet available, and real-browser validation remains part of
WP10.

Evidence: [history panel](../../frontend/src/features/objects/panels/HistoryPanel.tsx),
[audit service](../../backend/app/services/audit.py).

## F12 — Prepare a workspace design draft

**User outcome:** A team can prepare a coordinated graph change without disturbing live data.

Through the API a user can start from a private immutable copy of current live content or derive a
draft from a selected immutable revision, give it a name, list and open drafts, edit records through
the normal record APIs, and discard the draft. Current-live capture includes changes made since the
latest publication and works without a publication. A derived draft presents the selected historical
base together with its changes. Starting from history is not a full rollback: only explicitly authored
draft changes are applied at activation, while untouched newer live data is preserved.

Draft edits use both record versions and a draft-wide version. Drafts pin the application-model release
against which they are validated. Current-live capture is implemented for SQLite and explicitly refused
on unsupported database dialects. The browser has no workspace draft destination or editor yet.

Evidence: [workspace routes](../../backend/app/routers/workspaces.py),
[workspace revision service](../../backend/app/services/workspace_revisions.py).

## F13 — Validate and activate a design draft

**User outcome:** A coordinated design change is checked as a complete dataset and either becomes live
in full or not at all.

Validation checks the complete effective graph without publishing. Activation applies the draft's
changes over the latest live content, preserves unrelated live changes and detects conflicts on every
record the draft touched. It then validates the merged result and creates one immutable revision.

If a version, identity, model-release or graph check fails, neither the live dataset nor the draft is
partially changed. The response explains the conflicts so the user can reconcile them. The browser
review, validation and activation journey remains WP9 work.

Evidence: [activation merge tests](../../backend/tests/test_wp8_activation_merge.py),
[whole-graph validation tests](../../backend/tests/test_wp8_graph_validation.py),
[ADR-026 activation decision](../DECISIONS.md#resolved-decision--activation-is-a-delta-merge-over-live-content).

## F14 — Browse workspace history and retire publication

**User outcome:** A user can understand publication lineage, inspect a frozen snapshot and stop
designating a revision as current without deleting its history.

The API lists immutable workspace revisions newest first with bounded deterministic cursor paging and
exposes a selected snapshot for record and
relationship reads. It keeps “created from” separate from “superseded on activation,” so branching from
older history remains truthful.

The user confirmed newest-first order in GAP-05, and WP8.1-C implements that API boundary. The browser
history journey remains assigned to WP9/WP10.

Publication retirement clears the current published revision under a concurrency check while retaining
workspace identity, historical revisions and stable record identities. It is distinct from retiring the
workspace catalogue entry. Current retirement leaves the live store readable and writable in an
active catalogue workspace; it is not a withdrawal of data from consumers. The browser has no
workspace history or retirement flow yet. GAP-04 accepted this distinction; ADR-027 and the revised
interaction specification provide the wording for implementation.

Evidence: [workspace history tests](../../backend/tests/test_wp8_history.py),
[retirement tests](../../backend/tests/test_wp8_retirement.py).

## F15 — Inspect and release application models

**User outcome:** A model administrator can evolve what applications mean without editing the active
definition in place.

The Models workbench is the most complete administrative browser flow. Users can inspect installed
releases, see the active release, review summaries and differences, assess compatibility and export
model JSON. When model mutations are enabled, an administrator can create or import an editable JSON
draft, save it with conflict protection, validate and compile it, install an immutable inactive release
and activate a compatible release with fresh runtime-state claims.

Installation never activates automatically. A historical release remains immutable. Mutating controls
are absent unless the deployment enables them; the setting is a safety gate, not authorization.
Administration mutations currently require a single API process.

Evidence: [model workbench](../../frontend/src/features/model-admin/ModelWorkbench.tsx),
[model draft editor](../../frontend/src/features/model-admin/ModelDraftEditor.tsx),
[ADR-016](../DECISIONS.md#adr-016--separate-mutable-drafts-immutable-installation-and-activation).

## F16 — Consume stable, bounded APIs

**User outcome:** A developer can read and change reference data using stable identifiers and explicit
contracts rather than screen-specific endpoints or database IDs.

The API exposes model metadata, workspaces, records, typed values, relationships, history, model
releases and workspace design lifecycle. Collections use bounded cursor pages. Cursors are opaque and
bound to the original query. Public record and relationship identifiers are stable UUIDs; model
concepts use stable keys.

Errors are structured and distinguish not found, invalid input, conflict, retired scope and unavailable
service conditions. This current API is sufficient for bounded interactive use, not yet for large-scale
exchange. Bulk operations, resumable imports/exports, change feeds and webhooks are roadmap items.

Evidence: [API reference](../API.md), [cursor decision](../DECISIONS.md#adr-018--bind-opaque-cursors-to-query-semantics).

## F17 — Recover from concurrent changes

**User outcome:** One user's save does not silently overwrite another user's newer work.

Mutations to existing records, relationships, model drafts and workspace drafts, together with
activation and retirement actions, use explicit expected versions or expected active identities.
Read-only checks such as draft validation do not claim a version. A stale mutation fails and preserves
the user's candidate or local input where the interface owns it. Draft activation reports record-level
merge conflicts and publishes nothing.

Current model-workbench screens include conflict recovery. Generic data forms contain recovery behavior
but are not connected to the current record-detail journey. Complete browser recovery journeys remain
part of WP9/WP10.

Evidence: [model workbench tests](../../frontend/src/features/model-admin/ModelWorkbench.test.tsx),
[workspace activation tests](../../backend/tests/test_wp8_activation.py).

## F18 — Accessible and responsive foundations

**User outcome:** Core navigation and controls remain understandable and operable with a keyboard and
on narrow screens.

The interface has a skip link, labelled navigation and regions, semantic tables, visible focus,
keyboard-operated menus, shared modal focus containment and restoration, Escape handling, scroll lock,
dirty/busy dismissal guards and a narrow-screen navigation control. Feature code uses product-owned
semantic controls so behavior stays consistent.

Limits: component tests run in a simulated browser. No real-browser workflow, screen-reader,
automated-accessibility or visual-regression release gate has yet proved the composed product. WP10 owns
that evidence.

Evidence: [application shell](../../frontend/src/app/AppShell.tsx),
[shared modal](../../frontend/src/ui/Modal.tsx), [UI model](../UI_MODEL.md).

## F19 — Operate and recover the service

**User outcome:** An operator can tell whether the service is ready and receive an actionable recovery
instruction instead of a framework traceback for expected startup problems.

The service exposes health/readiness, uses controlled database migrations, retains a database-selected
active model, and refuses unsafe or ambiguous upgrades. Known model-schema and database-migration
failures keep the service unhealthy and report the failed condition, safe recovery action and exact
command. Backups and application/schema rollback are separate from activating an older compatible model
release.

Limits: production PostgreSQL scale, multi-node propagation, authenticated administration, metrics and
full backup/restore rehearsal are planned for 0.10.

Evidence: [application startup](../../backend/app/main.py), [architecture runbook](../ARCHITECTURE.md#upgrade-backup-and-rollback-operations).
