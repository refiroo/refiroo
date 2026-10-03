# Current functionality catalogue

What the product does today, function by function, with the browser and the API kept apart so that
backend coverage is not mistaken for a complete user experience. Reviewed 2026-10-02 against Base 0.8
(released 2026-09-29) and the 0.9 packages delivered since (Q1–Q4, C1, V1, B1, B2 and the
0.9.0-alpha.1 PostgreSQL work PG1–PG3b). Statuses use the
[status vocabulary](README.md#status-vocabulary). The overview is [PRODUCT.md](../PRODUCT.md).

## Summary

| ID | Function | Browser | API | Notes |
| --- | --- | --- | --- | --- |
| F01 | Model-defined applications | Validated | Available | Four collection lenses |
| F02 | Workspace discovery and administration | Validated | Available | Administration is a deployment setting |
| F03 | Find, filter, sort and page through records | Validated | Available | Any size (0.8 Track S) |
| F04 | Inspect a record and its context | Validated | Available | Every workspace and context |
| F05 | Maintain live records | Validated | Available | Live by default, change set optional |
| F06 | Maintain typed field values | Validated | Available | Inline editing |
| F07 | Maintain containment and hierarchy | Validated | Available | Tree lens; restructuring in a change set |
| F08 | Maintain relationships and mappings | Validated | Available | Mapping grid lens |
| F09 | Maintain translations and coverage | Validated | Available | Relation matrix lens |
| F10 | Preview and confirm dependent deletion | Validated | Available | |
| F11 | Inspect record history | Validated | Available | No authenticated actor until 0.12 |
| F12 | Prepare a change set | Validated | Available | From live data or a publication |
| F13 | Review, validate and publish a change set | Validated | Available | |
| F14 | Browse publications and withdraw one | Validated | Available | |
| F15 | Inspect and release application models | Validated | Available | Mutations are a deployment setting |
| F16 | Use stable, bounded APIs | Not applicable | Available | |
| F17 | Recover from concurrent changes | Validated | Available | |
| F18 | Accessible and responsive interface | Validated | Not applicable | Automated gates |
| F19 | Operate and recover the service | Operator messages | Available | Production hardening is 0.11 |
| F20 | Query and look up across the data | Not applicable | Available | 0.9 Q1–Q3 |
| F21 | Read by business date (`asOf`) | Fields only | Available | 0.9 Q4 |
| F22 | Load data in bulk as jobs | Unavailable | Available | 0.9 B1–B2; import screen 0.9 J4 |
| F23 | Declare consumer APIs | JSON model editing | Definitions only | 0.9 C1; serving is in progress |
| F24 | Read the API reference | Available at `/docs` | Not applicable | 0.9 V1 |

"Validated" means a composed real-browser runner covers the journey against a real backend
(`frontend/e2e/`). The acceptance runs are recorded in the release plans.

## F01 — Model-defined applications

**User outcome:** A team offers different reference-data applications without building a backend and
frontend for each.

Users move between model-defined applications and their collections in one application browser.
Navigation, record types, fields, relationships, collection views and detail layouts are read from the
installed model; the runtime does not recognise the example applications' names. A collection offers
the views declared over its record type as lenses: table, mapping grid, relation matrix and tree. A
record's detail page is composed of configured panels (fields, children, relationships, tables,
hierarchy, history), with a sensible default when the model declares none.

Limits: dedicated form and dashboard views do not exist; structured model design is 0.10.

Evidence: [application shell](../../frontend/src/app/AppShell.tsx),
[view registry](../../frontend/src/features/objects/views/registry.ts),
[model language](../APPLICATION_MODEL.md).

## F02 — Workspace discovery and administration

**User outcome:** A person knows which dataset they are working in and cannot land in an invented or
misspelled workspace.

Users select a workspace by label or search; its key stays in the page address, and one workspace is
the default. Retired workspaces stay readable and are visibly read only. With a single workspace the
selector is a label.

The **Workspaces** screen lists every workspace and creates, renames, retires, reactivates, deletes and
sets the default, each protected against concurrent changes. A workspace that was ever published can
only be retired; **Delete…** is for correcting a mistyped key on an empty workspace. Workspace
administration is a deployment setting (on by default until sign-in exists, not a permission); when it
is off the screen is read only and names the setting.

Evidence: [workspace selector](../../frontend/src/features/workspaces/WorkspaceSelector.tsx),
[workspace administration](../../frontend/src/features/workspaces/WorkspaceAdmin.tsx),
[W4 runner](../../frontend/e2e/w4-workspace-admin.mjs),
[workspace catalogue](../../backend/app/engine/workspaces/catalogue.py),
[ADR-019](../DECISIONS.md#adr-019--persist-and-retire-globally-scoped-workspaces).

## F03 — Find, filter, sort and page through records

**User outcome:** A steward finds a value in a large workspace without downloading everything.

Collections offer free-text search over names and searchable fields, typed filter facets declared by
the view, and one sort at a time from a column header or the Sort menu. Lists of any size scroll
continuously in both directions, show their total and jump to a page, a value, the start or the end.
Search, filters, sort and position live in the page address, so a link or a reload returns to the same
place. The same works in live data, in a change set and in a publication.

Filters cover text equality, contains and starts-with, numeric and date comparisons, booleans, null
checks and the difference between a missing optional field and a stored null.

Limits: one sort at a time in the browser; queries across relationships are API-only (F20). Pages are
always bounded.

Evidence: [collection view](../../frontend/src/features/objects/CollectionView.tsx),
[S7 volume runner](../../frontend/e2e/s7-volume-acceptance.mjs),
[ADR-030](../DECISIONS.md#adr-030--cursor-and-position-paging-with-continuous-scrolling).

## F04 — Inspect a record and its context

**User outcome:** A user understands a record without piecing it together from raw tables.

From a collection, the tree or a search, a record opens with its path, fields, children, relationships
in both directions, related tables and history. Returning keeps the list's search, filters, sort and
position. Failed reads offer retry and back. This works in every workspace and in change set and
publication contexts.

Evidence: [object detail](../../frontend/src/features/objects/ObjectDetail.tsx),
[panel registry](../../frontend/src/features/objects/panels/registry.tsx),
[WP9 navigation runner](../../frontend/e2e/wp9-navigation.mjs).

## F05 — Maintain live records

**User outcome:** A data owner adds or corrects an everyday value without a change set or a release.

Records are created, edited and deleted directly in an active workspace. A save is immediately
visible, advances the record version and is recorded in history; it creates no change set or
publication. A new record can carry its fields, parent and required relationships in one request.
The same actions can instead target a selected change set (F12).

Evidence: [object form](../../frontend/src/features/objects/ObjectFormDialog.tsx),
[WP9 authoring runner](../../frontend/e2e/wp9-authoring.mjs),
[object routes](../../backend/app/management/routers/objects.py),
[write rules](../../backend/app/engine/records/rules.py),
[ADR-026](../DECISIONS.md#adr-026--active-workspaces-are-live-writable-for-data-drafts-are-the-design-path).

## F06 — Maintain typed field values

**User outcome:** A value stays a number, boolean, date or other declared type instead of unreliable
text.

Fields are text, long text, integer, decimal, boolean, date, date-time or JSON. The engine enforces
required fields, defaults, read-only bindings, numeric ranges, "at least one of" rules and uniqueness
(also within an ancestor). In the browser a field is edited in place with an editor for its type, and a
missing optional value is kept distinct from a stored false, zero, empty or null value.

Evidence: [inline editor](../../frontend/src/features/objects/panels/InlineAttributeEditor.tsx),
[attribute panel](../../frontend/src/features/objects/panels/AttributesPanel.tsx),
[attribute values](../../backend/app/engine/records/attributes.py).

## F07 — Maintain containment and hierarchy

**User outcome:** A steward places a record under the right parent while the hierarchy keeps its
meaning and integrity.

Creating or moving a contained record updates its parent and its typed parent relationship together.
A wrong parent type, a cycle or a separate edit of the engine-managed parent relationship is refused.

The sidebar tree reads any hierarchy by parent at any size and depth, by keyboard or pointer, and its
search lists matching records of every type with their path. A model-declared tree view adds editing:
from a node's menu, add a child of any type the node may contain, rename, set availability and move
through a searchable list of valid parents, or drag and drop, including to the top level. Invalid
destinations are listed disabled with the reason. A move is live, or staged in a selected change set;
a publication's tree is read only.

In a change set the tree also restructures (ADR-034): **Move to…** and a drag offer places where the
record's type cannot stand but another can (**Becomes <type>**), and the menu adds **Change type…**,
**Insert level above…**, **Remove this level…** and **Change type of all <type> in here…**, each only
where the model allows it. A preview shows every record's new type, values and origin, what has no
place (kept in history) and the values still needed. Records keep their IDs and history; live data
changes type only when the change set is published.

Limits: touch drag is 0.11.

Evidence: [tree lens](../../frontend/src/features/objects/TreeView.tsx),
[record tree](../../frontend/src/features/objects/RecordTree.tsx),
[B4 runner](../../frontend/e2e/b4-hierarchy-acceptance.mjs),
[C5 runner](../../frontend/e2e/c5-restructuring-acceptance.mjs),
[restructuring](../../backend/app/engine/operations/restructuring.py),
[ADR-006](../DECISIONS.md#adr-006--maintain-containment-and-typed-parent-relations),
[ADR-034](../DECISIONS.md#adr-034--a-records-type-can-change-derived-mapping-preview-and-apply-history-as-the-way-back).

## F08 — Maintain relationships and mappings

**User outcome:** A user connects records by business-meaningful relationships, and a mapping steward
resolves system values to their shared meaning.

Relationships are listed in both directions, created, edited (their own fields) and removed, with the
record types, direction, cardinality, requiredness and field types validated. Parent relationships are
shown but changed only by moving the record (F07). Related records are found by server-side search.

A mapping grid shows each source value as mapped, unmapped or ambiguous across the whole list, with
counts, target previews and a state filter. Choosing, replacing or clearing a target is one atomic
action that keeps the existing relationship's identity and fields; a concurrent change is reported with
the current mapping instead of overwritten. This works live and in a change set; publishing refuses a
change set whose mappings diverged from live data.

Evidence: [mapping grid](../../frontend/src/features/objects/MappingGridView.tsx),
[relations panel](../../frontend/src/features/objects/panels/RelationsPanel.tsx),
[SC-07 runner](../../frontend/e2e/sc07-mapping-acceptance.mjs),
[mapping replacement](../../backend/app/engine/operations/mapping_replacement.py),
[ADR-022](../DECISIONS.md#adr-022--version-complete-relation-sets-for-atomic-mapping).

## F09 — Maintain translations and coverage

**User outcome:** A localisation steward stores translations without creating invalid or duplicate
ones, and sees where translations are missing.

Translations are ordinary records and relationships: a translation is created with its group, target
and content in one valid operation, and a second active translation for the same target and language
is refused.

A relation matrix shows records against the values of an ancestor type, for example values by
language, each cell current, missing, inactive or held only in history. It filters to gaps across the
whole list. From a cell the steward creates, corrects or restores a translation, live or in a change
set, and the same view links and unlinks system values.

Evidence: [relation matrix](../../frontend/src/features/objects/RelationMatrixView.tsx),
[A5 runner](../../frontend/e2e/a5-matrix-acceptance.mjs),
[ADR-014](../DECISIONS.md#adr-014--create-required-translation-targets-atomically),
[ADR-033](../DECISIONS.md#adr-033--store-relation-matrix-cell-states-as-a-derived-rebuildable-index).

## F10 — Preview and confirm dependent deletion

**User outcome:** A person sees what else will be removed before confirming a destructive change.

Deleting first returns an impact preview without changing data: contained children, owned dependants
and affected relationships. Removing owned dependants needs explicit confirmation; independent
records are unlinked, not deleted. A live deletion is immediate and recorded; in a change set it is a
staged removal. Publications and history are never erased.

Evidence: [delete dialog](../../frontend/src/features/objects/ObjectDeleteDialog.tsx),
[deletion](../../backend/app/engine/records/deletion.py),
[ADR-012](../DECISIONS.md#adr-012--preview-destructive-graph-cascades-and-derive-ownership-from-relation-bindings).

## F11 — Inspect record history

**User outcome:** A user sees how a record and its relationships changed over time.

The record page has an independently paged history, newest first; loading older entries keeps those
already shown, and a failed page can be retried. Entries made by a bulk job name the job as their
cause. History is bounded and does not expose whole model documents.

Limits: no authenticated actor until 0.12.

Evidence: [history panel](../../frontend/src/features/objects/panels/HistoryPanel.tsx),
[audit](../../backend/app/engine/records/audit.py).

## F12 — Prepare a change set

**User outcome:** A team prepares a coordinated change without disturbing live data.

A change set starts from current live data (including edits since the last publication) or from a
selected publication, and is named, listed, opened and discarded. Records are edited in it through the
same screens and API as live data. Starting from an earlier publication is not a rollback: only what
the change set changes is applied when it is published.

A change set can be prepared against another installed model version than the one live data uses,
and moved between compatible versions (ADR-028); it can be published only once its version is the
active one.

Evidence: [change sets](../../frontend/src/features/workspaces/ChangeSets.tsx),
[WP9 change set runner](../../frontend/e2e/wp9-change-sets.mjs),
[SC-15 runner](../../frontend/e2e/sc15-model-version-acceptance.mjs),
[change set lifecycle](../../backend/app/engine/change_sets/lifecycle.py),
[ADR-028](../DECISIONS.md#adr-028--one-draft-may-prepare-the-next-model-version-while-live-keeps-the-current-one).

## F13 — Review, validate and publish a change set

**User outcome:** A coordinated change is checked as a whole and becomes live in full or not at all.

**Review changes** lists every record and relationship the change set adds, changes or removes, with
type, location and the fields that differ; a row opens to a before/after table, and a moved record
names both parents. Validation checks the complete result without publishing. Publishing applies the
change set's changes over current live data, keeps unrelated live edits, detects conflicts on every
record and mapping it touched, validates the merged result and creates one publication. Any conflict
or failure publishes nothing and keeps both the change set and live data, with the conflicts listed.

Evidence: [review screen](../../frontend/src/features/workspaces/ChangeSetReview.tsx),
[P2 runner](../../frontend/e2e/p2-change-review.mjs),
[publishing](../../backend/app/engine/change_sets/publish.py).

## F14 — Browse publications and withdraw one

**User outcome:** A user inspects what a publication contained and stops designating it as current
without losing history.

Publications are listed newest first; each is a read-only snapshot that can be browsed like live data.
"Created from" and "superseded by" are kept apart, so starting from older history stays truthful.
Withdrawing the current publication removes only the designation; live data and earlier publications
stay. This is different from retiring a workspace.

Evidence: [publications](../../frontend/src/features/workspaces/Publications.tsx),
[WP9 publications runner](../../frontend/e2e/wp9-publications.mjs).

## F15 — Inspect and release application models

**User outcome:** A model administrator evolves what applications mean without editing the active
definition in place.

The **Models** workbench lists installed releases and the active one, with summaries, technical
details, comparisons between releases and JSON export. With model administration enabled (a
deployment setting, one API process), an administrator edits a JSON draft with conflict protection,
validates and compiles it, installs an immutable release and activates a compatible one. Installing
never activates. Activation is refused when existing data would not fit, and also when a consumer API
contract changes incompatibly without a new contract version (F23). Releases on unsupported older
schemas stay inspectable and exportable.

Limits: the structured editor and spreadsheet onboarding are 0.10.

Evidence: [model workbench](../../frontend/src/features/model-admin/ModelWorkbench.tsx),
[draft editor](../../frontend/src/features/model-admin/ModelDraftEditor.tsx),
[WP11 runner](../../frontend/e2e/wp11-model-admin.mjs),
[ADR-016](../DECISIONS.md#adr-016--separate-mutable-drafts-immutable-installation-and-activation).

## F16 — Use stable, bounded APIs

**User outcome:** A developer reads and changes reference data through stable identifiers and explicit
contracts, not screen-specific endpoints or database IDs.

The API exposes the model, workspaces, records, typed values, relationships, history, model releases,
change sets and publications. Records and relationships have stable UUIDs; model concepts have stable
keys. Every list is paged with signed cursors bound to the query, or by position, with totals on
request. Errors are structured and distinguish not found, invalid input, conflict, retired scope and
unavailable service. Integration-scale functions are F20–F23; the reference page is F24.

Limits: no change feed, webhooks, file import or export yet (0.9); every API is unauthenticated until
0.12.

Evidence: [API contracts](../API.md),
[ADR-018](../DECISIONS.md#adr-018--bind-opaque-cursors-to-query-semantics).

## F17 — Recover from concurrent changes

**User outcome:** One person's save never silently overwrites another's newer work.

Changes to records, relationships, mapping sets, model drafts and change sets, and activation and
retirement, carry an expected version. A stale change fails, keeps the user's input and shows the
current state. Publishing reports record-level conflicts and publishes nothing. On PostgreSQL, two
writers racing in one workspace can never both break a rule (a unique value, a cycle, a cardinality);
the second is refused with the same message as a single write.

Evidence: [WP9 authoring runner](../../frontend/e2e/wp9-authoring.mjs),
[write path](../../backend/app/engine/records/writes.py).

## F18 — Accessible and responsive interface

**User outcome:** Navigation and controls work by keyboard and on narrow screens.

The interface has a skip link, labelled regions, semantic tables and trees, visible focus, keyboard
menus and shortcuts, managed dialog focus, dirty-input guards, narrow-screen navigation, light and dark
mode, resizable panels and display preferences. An automated accessibility gate (axe) and a visual
regression gate cover the main screens in both themes.

Limits: no screen-reader user testing has been recorded.

Evidence: [accessibility gate](../../frontend/e2e/accessibility-gate.mjs),
[visual regression gate](../../frontend/e2e/visual-regression-gate.mjs), [UI model](../UI_MODEL.md).

## F19 — Operate and recover the service

**User outcome:** An operator knows whether the service is ready and gets an actionable instruction
instead of a traceback.

The service reports health, runs controlled migrations, keeps the active model in the database and
refuses unsafe states (wrong database, wrong collation, unknown revision, unsupported model schema,
failed migration) with what to do. Backups and application rollback are separate from activating an
older model release. Background jobs survive restarts.

Limits: performance at production scale, several servers, metrics and rehearsed restore are 0.11.
The engine does not copy old SQLite development databases.

Evidence: [operations guide](../OPERATIONS.md), [application startup](../../backend/app/main.py).

## F20 — Query and look up across the data

**User outcome:** An integration finds the records it needs with one request instead of walking the
data page by page.

- **Cross-type lookup** lists records of every type, or several named types, by name and built-in
  fields, narrowed to an application, a parent or the top level.
- **Workspace edge list** lists every relationship of any type in a workspace.
- **Model-aware query** lists one record type by field criteria with typed values, by ancestor at any
  depth and by a related record (or its absence), with one sort, chosen fields returned and up to 20
  related records included per item.

All three work in live data, a change set or a publication and page like every other list.

Evidence: [query contracts](../API.md#model-aware-query-base-09-q3),
[model query](../../backend/app/engine/reads/model_query.py),
[cross-type lookup](../../backend/app/engine/reads/object_lookup.py).

## F21 — Read by business date (`asOf`)

**User outcome:** An integration reads the values valid on a business date, separately from record
history and publications.

A record type may declare an effective period over two of its date fields (start inclusive, end
exclusive, either open). An end not after its start is refused on every write. `asOf=YYYY-MM-DD` on the
per-type list and the model-aware query returns the records valid on that date, in any context. In the
example model, master values carry a period. In the browser the two dates are ordinary fields; there is
no date filter yet.

Evidence: [effective periods](../API.md#effective-periods-and-asof-base-09-q4),
[ADR-038](../DECISIONS.md#adr-038--business-validity-is-a-declared-effective-period-separate-from-history-and-publications).

## F22 — Load data in bulk as jobs

**User outcome:** An integration loads or synchronises many records with per-item results and safe
retries, instead of looping over single calls.

A batch of create, update, upsert and delete items runs live or in a change set, inline (up to 1,000
items) or in the background (up to 1,000,000). Records are addressed by ID or by a unique field's
value, so a recurring feed and a one-off load use the same contract. The caller chooses all-or-nothing
or item-by-item; every item goes through the same rules as a single write and gets its own outcome.
An idempotency key makes a retry return the first result. Background jobs report progress, survive
restarts without repeating or skipping an item, and can be cancelled. Jobs and their outcomes are
kept for a configurable retention.

Limits: relationship and mapping items, and file import and export with a preview screen, follow in
0.9.

Evidence: [batch contracts](../API.md#batches-and-jobs-base-09-b1-b2),
[jobs](../../backend/app/engine/jobs/),
[ADR-036](../DECISIONS.md#adr-036--a-batch-is-a-job-one-mechanism-for-bulk-writes-imports-and-exports).

## F23 — Declare consumer APIs

**User outcome:** A model administrator defines the read-only contract other systems will use, and
cannot break it by accident.

The model (schema 0.8) declares consumer APIs: their public names, exposed record types and fields,
lookup parameters and lists, each with a contract version. Every reference is validated. Comparing
releases reports contract changes, and activation refuses a breaking change without a higher contract
version.

Limits: the consumer API endpoints themselves (lookup by code, lists, crosswalks, events) are being
delivered in 0.9; today only the definitions exist.

Evidence: [consumer API design](../CONSUMER_API.md),
[contract check](../../backend/app/engine/model/consumer_contract.py).

## F24 — Read the API reference

**User outcome:** A developer explores and tries the API from a page served by the engine itself.

`/docs` renders the management API's OpenAPI document with Scalar. The script is bundled, so the page
works without internet access and loads nothing from elsewhere; a setting loads it from a CDN instead.
Its "try it" console calls the engine that served it.

Evidence: [API reference page](../API.md#api-reference-page-base-09-v1),
[reference module](../../backend/app/management/reference/__init__.py).
