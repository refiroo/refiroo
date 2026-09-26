# Current functionality catalogue

This catalogue retains the 2026-09-07 assessment with targeted source-review corrections on
2026-09-08, a WP-4 mapping API update on 2026-09-14 and the focused WP-8/WP-14 browser review on
2026-09-15. Other historical assessments
retain their original evidence boundary. “Browser” and “API” are kept separate so that backend coverage
is not mistaken for a complete user experience. The 2026-09-15 update includes focused backend,
frontend and real-browser package evidence; it is not WP-9 release acceptance. See the
[review boundary](PLANNING_HANDOFF.md#authority-and-review-boundary).

## Summary

| ID  | Function                                                  | Browser             | API            | Current assessment               |
| --- | --------------------------------------------------------- | ------------------- | -------------- | -------------------------------- |
| F01 | Model-defined applications                                | Implemented         | Available      | Contextual browser focused proof |
| F02 | Workspace discovery and selection                         | Implemented         | Available      | Non-default detail repaired (0.6 WP9) |
| F03 | Find, filter, sort and page through records               | Implemented         | Available      | Visible facets; WP9 full gate pending |
| F04 | Inspect a record and its context                          | Implemented         | Available      | Every workspace                  |
| F05 | Maintain live records                                     | Temporarily unwired | Available      | WP9 must enable browser editing  |
| F06 | Maintain typed field values                               | Components present  | Available      | Browser completion is WP9        |
| F07 | Maintain containment and hierarchy                        | Components present  | Available      | Specialist tree is roadmap       |
| F08 | Maintain ordinary relationships                           | Implemented         | Available      | Mapping lens focused proof; WP9 pending |
| F09 | Maintain translations                                     | Components present  | Available      | Translation editor is roadmap    |
| F10 | Preview and confirm dependent deletion                    | Components present  | Available      | Browser completion is WP9        |
| F11 | Inspect record history                                    | Default only        | Available      | Non-default context is dropped   |
| F12 | Prepare a workspace change set                          | Unavailable         | Available      | Browser completion is WP9        |
| F13 | Validate and activate a change set                      | Unavailable         | Available      | Browser completion is WP9        |
| F14 | Browse immutable workspace history and retire publication | Unavailable         | Available      | Browser completion is WP9        |
| F15 | Inspect and release application models                    | Implemented         | Available      | Browser validation pending       |
| F16 | Consume stable, bounded APIs                              | API concern         | Available      | Advanced integration is roadmap  |
| F17 | Recover from concurrent changes                           | Partial UI          | Available      | Full browser journeys pending    |
| F18 | Use accessible and responsive foundations                 | Foundation present  | Not applicable | Real-browser proof pending       |
| F19 | Operate and recover the service                           | Operator messages   | Available      | Production hardening is roadmap  |

## F01 — Model-defined applications

**User outcome:** A team can offer different reference-data applications without developing a new
backend and frontend for each domain.

Users move between model-defined applications and contextual collections in one browser. The starter
currently demonstrates Master, Systems and Translations. Navigation, record types, fields,
relationships, collection lenses and detail layouts are
read from the installed application model. The runtime is not supposed to recognize starter names as
special cases.

What users experience:

- one application browser containing collection entry points and bounded hierarchy records;
- views grouped as named semantic lenses by their model-derived source type;
- labels and fields appropriate to the selected record type;
- configured detail panels for attributes, children, relationships, tables and hierarchy; and
- a safe fallback detail composition when no tailored detail layout is supplied.

Limits:

- strict tables and mapping grids are current top-level renderers; dedicated forms, dashboards and
  tree views remain unsupported until honest implementations exist; and
- structured self-service model design is a later roadmap capability.

Evidence: [application shell](../../frontend/src/app/AppShell.tsx),
[view registry](../../frontend/src/features/objects/views/registry.ts),
[application model specification](../APPLICATION_MODEL.md).

## F02 — Workspace discovery and selection

**User outcome:** A person knows which governed dataset they are viewing and does not accidentally work
in an invented or misspelled workspace.

Users can select a known workspace by label, search the catalogue and retain the stable workspace key
in the page address. One workspace is the default when a link omits the selection. Retired workspaces
remain readable and are visibly read-only. While only one workspace exists, the selector is a read-only
label instead of a control.

Workspace administrators use the global **Workspaces** screen, beside **Models** in the header, or the
**Manage workspaces** entry in the selector: it lists every workspace including retired ones, and
creates, renames, retires, reactivates, deletes and sets the default, each with its version claim. A
concurrent change is shown with the current state and nothing is retried. A workspace key cannot be
changed, and the current default cannot be retired or deleted. **Delete…** corrects a mistyped key: it
is offered only for a workspace that has never been published and has no objects or change sets, asks
for confirmation naming the key, and frees the key to be created again. Otherwise the screen says why
(the default; published, so retire it instead; or not empty). Change sets and publications stay inside each
workspace. The same operations remain available through the API.

Safety and limits:

- an unknown explicit key fails rather than silently falling back;
- catalogue retirement is different from retiring a published data publication;
- a published workspace can only be retired, never deleted, because publications are kept;
- workspace administration is controlled by a deployment setting that defaults on in the current
  pre-authentication product; this is not user authorization. When it is off, the header entry and
  the selector's entry are absent, a direct link shows the catalogue read only, and the Models and
  Workspaces screens name the setting in their capability status.

The selected workspace is carried from the collection into the detail, history, child and relationship
requests, so opening a record works in every workspace. The detail refuses a record that belongs to
another workspace rather than showing it under the wrong selection. The [WP9 navigation runner](../../frontend/e2e/wp9-navigation.mjs) exercises
the journey in a non-default workspace.

Evidence: [workspace selector](../../frontend/src/features/workspaces/WorkspaceSelector.tsx),
[workspace administration](../../frontend/src/features/workspaces/WorkspaceAdmin.tsx),
[W4 browser runner](../../frontend/e2e/w4-workspace-admin.mjs),
[workspace service](../../backend/app/services/workspaces.py), [ADR-019](../DECISIONS.md#adr-019--persist-and-retire-globally-scoped-workspaces).

## F03 — Find, filter, sort and page through records

**User outcome:** A steward can locate a value in a large workspace without downloading everything or
searching only what the browser has already loaded.

The browser provides model-defined collection tables with:

- free-text search across names and configured searchable fields;
- visible, model-labelled typed filter facets selected by the table definition;
- one sort at a time, including descending order, by any data column from its header or from the
  list's icon-only Sort menu, which every table carries;
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

In any workspace, the current browser can open a record from a collection or explorer and show
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

Evidence: [object detail](../../frontend/src/features/objects/ObjectDetail.tsx),
[panel registry](../../frontend/src/features/objects/panels/registry.tsx).

## F05 — Maintain live reference-data records

**User outcome:** A data owner can add or correct an everyday reference value without opening a change set
or publishing a release.

The API supports creating, editing and deleting records directly in an active workspace. A successful
change is immediately visible to active reads, advances the record version and produces audit history.
It does not create a change set or publication.

Record creation can include its typed fields, parent and permitted initial relationships in the same
request. This is existing generic behavior, not translation-specific orchestration: the live
`create_object_record` service checks required incoming relationships, creates the record and its
initial relationships in the request transaction, then commits. This does not imply a general
multi-record transaction API or automatic creation of missing target records. Browser completion and
direct end-to-end failure evidence remain required by SC-03.

The same record operation can instead name a workspace change set. In that case it changes the change set
candidate and remains separate from live data until activation.

Current implementation gap: generic object forms exist and are tested, but record detail currently
passes an unconditional `readOnly` instruction to its panels. This is not a product rule. WP9 must
remove that temporary wiring limitation and expose normal live editing, while also allowing an
explicitly selected change set as an alternative context.

Evidence: [object API](../../backend/app/routers/objects.py),
[record creation service](../../backend/app/services/objects.py),
[object form](../../frontend/src/features/objects/ObjectFormDialog.tsx),
[temporary detail-page wiring](../../frontend/src/features/objects/ObjectDetail.tsx),
[ADR-026](../DECISIONS.md#adr-026--active-workspaces-are-live-writable-for-data-change sets-are-the-design-path).

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
The explorer's record tree reads by parent at any size (Base 0.8 S6): each root type pages its
top-level records, and expanding a record pages each child type separately with its count, in live,
change-set and publication. It scrolls every branch continuously and walks by keyboard to any depth; a search
lists matching records of every type with their ancestor path.
Generic parent selection exists in the record form but is not currently connected to a writable flow.
The typed `tree` view, reparenting and child creation remain planned for 0.8 (Milestone B).

Evidence: [explorer](../../frontend/src/features/objects/Explorer.tsx),
[record tree](../../frontend/src/features/objects/RecordTree.tsx),
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

WP-4/WP-14 deliver model-configured live/change-set/publication mapping coverage with mapped, unmapped and ambiguous
states, exact counts, bounded target previews, version-bound target details and paged candidate search.
WP-5 delivers atomic mapping replacement: `PUT /mappings` creates, replaces or removes a mapping for
one source with retained relation identity, typed attribute semantics, direction-aware cross-cardinality
enforcement, idempotent no-ops, bounded conflict responses and mapping-transition audit events in both
live and change set contexts. WP-10A ensures that cascade object deletion invalidates affected mapping
continuations. WP-10B refuses divergent live sets touched by staged mutable relations before change set
activation, with bounded binding/anchor/direction diagnostics; unrelated live work survives. The
source/live fingerprint uses edge identities and surviving edge versions. WP-8A/WP-8B now provide
the generic coverage and action renderer; WP-14 composes it as a source-collection lens, adds visible
state and direct-parent scope filters, and prevents conflict retry until the returned current mapping
has been reviewed. Focused real-browser proof covers both configured directions and live replacement.
Comprehensive accessibility, visual and composed integration acceptance remain WP-9. PostgreSQL
concurrency remains unverified. See the
[mapping API contract](../API.md#product-07-mapping-api-wp-4-and-wp-5-delivered) and
[0.7 plan](../BASE_0_7_IMPLEMENTATION_PLAN.md). WP-1–WP-3 remain frozen.

Evidence: [mapping query API](../../backend/app/routers/mapping.py),
[relations API](../../backend/app/routers/relations.py),
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

For a live edit, deletion takes effect immediately and is audited. For a change set, it becomes a
candidate removal and does not alter live or historical content before activation. Publications
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

## F12 — Prepare a workspace change set

**User outcome:** A team can prepare a coordinated graph change without disturbing live data.

Through the API a user can start from a private immutable copy of current live content or derive a
change set from a selected immutable publication, give it a name, list and open change sets, edit records through
the normal record APIs, and discard the change set. Current-live capture includes changes made since the
latest publication and works without a publication. A derived change set presents the selected historical
base together with its changes. Starting from history is not a full rollback: only explicitly authored
change set changes are applied at publishing, while untouched newer live data is preserved.

Draft edits use both record versions and a draft-wide version. Drafts pin the application-model release
against which they are validated. The browser can create, open, edit, validate, activate and discard a
draft, and can move it to a compatible installed release. Supported older pins load their exact model;
unsupported or corrupt pins block interpretation and writes without substituting the active model.
Current-live capture is implemented for SQLite and explicitly refused on unsupported database dialects.

Evidence: [workspace routes](../../backend/app/routers/workspaces.py),
[publication service](../../backend/app/services/change_sets.py).

## F13 — Validate and activate a change set

**User outcome:** A coordinated design change is checked as a complete dataset and either becomes live
in full or not at all.

Validation checks the complete effective graph without publishing. Publishing applies the change set's
changes over the latest live content, preserves unrelated live changes and detects conflicts on every
record the change set touched. It then validates the merged result and creates one immutable publication.

If a version, identity, model-release or graph check fails, neither the live dataset nor the change set is
partially changed. The response explains the conflicts so the user can reconcile them. The browser
review, validation and activation journey remains WP9 work.

Evidence: [activation merge tests](../../backend/tests/test_wp8_publish_merge.py),
[whole-graph validation tests](../../backend/tests/test_wp8_graph_validation.py),
[ADR-026 activation decision](../DECISIONS.md#resolved-decision--activation-is-a-delta-merge-over-live-content).

## F14 — Browse workspace history and retire publication

**User outcome:** A user can understand publication lineage, inspect a frozen snapshot and stop
designating a publication as current without deleting its history.

The API lists immutable publications newest first with bounded deterministic cursor paging and
exposes a selected snapshot for record and
relationship reads. It keeps “created from” separate from “superseded on activation,” so branching from
older history remains truthful.

The user confirmed newest-first order in GAP-05, and WP8.1-C implements that API boundary. The browser
history journey remains assigned to WP9/WP10.

Publication withdrawal clears the current published publication under a concurrency check while retaining
workspace identity, earlier publication and stable record identities. It is distinct from retiring the
workspace catalogue entry. Current retirement leaves the live store readable and writable in an
active catalogue workspace; it is not a withdrawal of data from consumers. The browser has no
workspace history or retirement flow yet. GAP-04 accepted this distinction; ADR-027 and the revised
interaction specification provide the wording for implementation.

Evidence: [workspace history tests](../../backend/tests/test_wp8_history.py),
[retirement tests](../../backend/tests/test_wp8_withdrawal.py).

## F15 — Inspect and release application models

**User outcome:** A model administrator can evolve what applications mean without editing the active
definition in place.

The Models workbench is the most complete administrative browser flow. Users can inspect installed
releases, see the active release, review summaries and differences, assess compatibility and export
model JSON. When model mutations are enabled, an administrator can create or import an editable JSON
draft, save it with conflict protection, validate and compile it, install an immutable inactive release
and activate a compatible release with fresh runtime-state claims.

Installation never activates automatically. A historical release remains immutable. Mutating controls
are absent unless the deployment enables them; the setting is a safety gate, not authorization, and the
screen's capability status names it.
Unsupported historical schemas retain metadata/raw JSON inspection and export while semantic comparison
and activation are unavailable. Expected schema refusals are distinct from corrupt installed JSON, and
unexpected failures provide a correlation reference without exposing framework/HTML responses in the UI.
Administration mutations currently require a single API process.

Evidence: [model workbench](../../frontend/src/features/model-admin/ModelWorkbench.tsx),
[model draft editor](../../frontend/src/features/model-admin/ModelDraftEditor.tsx),
[WP-11 API regressions](../../backend/tests/test_build07_wp11.py),
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

Mutations to existing records, relationships, model drafts and change sets, together with
activation and retirement actions, use explicit expected versions or expected active identities.
Read-only checks such as change set validation do not claim a version. A stale mutation fails and preserves
the user's candidate or local input where the interface owns it. Publishing reports record-level
merge conflicts and publishes nothing.

Current model-workbench screens include conflict recovery. Generic data forms contain recovery behavior
but are not connected to the current record-detail journey. Complete browser recovery journeys remain
part of WP9/WP10.

Evidence: [model workbench tests](../../frontend/src/features/model-admin/ModelWorkbench.test.tsx),
[workspace activation tests](../../backend/tests/test_wp8_publish.py).

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
