# Current functionality catalogue

What the product does today, function by function, with the browser and the API kept apart so that
backend coverage is not mistaken for a complete user experience. Reviewed 2026-10-02 against Base 0.8
(released 2026-09-29) and the 0.9 packages delivered by then (Q1–Q4, C1, V1, B1, B2 and the
0.9.0-alpha.1 PostgreSQL work PG1–PG3b); each later 0.9 package updated it on delivery, up to Base
0.9's completion (2026-10-11). Statuses use the
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
| F21 | Read by business date (`asOf`) | Fields only | Available | 0.9 Q4, C16 |
| F22 | Load data in bulk as jobs | Validated: imports previewed and loaded from a collection or Jobs; jobs listed and cancelled in Settings | Available | 0.9 B1–B2; import screen 0.9 J4 |
| F23 | Declare consumer APIs and read through them | JSON model editing; each shown in Settings | Definitions; reading one business object; reading lists; looking up by code; reading a publication; an index and a typed document per API; following change events; subscribing to them | 0.9 C1–C6, C10, C11; Webhooks page U5 |
| F24 | Read the API reference | Available at `/docs`, each source linked from Settings | Not applicable | 0.9 V1, V2 |
| F25 | Follow changes in order | Not applicable | Available | 0.9 F1; retention and recovery 0.9 F2 |

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

An application with many collections can arrange them in labelled groups. The sidebar shows the
collections in no group first, then each group as a section that folds and unfolds; the model says
whether a group starts folded, and each reader's own choice is remembered in their browser. A folded
group holding the open collection is marked. A group's name opens its page, which lists its
collections with a search by name; each opens in the data the reader is looking at (live, a change
set or a publication).

Limits: dedicated form and dashboard views do not exist; structured model design is 0.10; groups
have one level and their page shows no record counts.

Evidence: [application shell](../../frontend/src/app/AppShell.tsx),
[sidebar](../../frontend/src/features/objects/Explorer.tsx),
[group page](../../frontend/src/features/objects/NavigationGroupPage.tsx),
[view registry](../../frontend/src/features/objects/views/registry.ts),
[model language](../APPLICATION_MODEL.md).

## F02 — Workspace discovery and administration

**User outcome:** A person knows which dataset they are working in and cannot land in an invented or
misspelled workspace.

Users select a workspace by label or search; its key stays in the page address, and one workspace is
the default. Retired workspaces stay readable and are visibly read only. With a single workspace the
selector is a label.

Settings › **Workspaces** lists every workspace beside the selected one, which can be created,
renamed, retired, reactivated, deleted and made the default, each protected against concurrent
changes; each workspace has its own address. Confirmations appear as toasts. A workspace that was ever published can
only be retired; **Delete…** is for correcting a mistyped key on an empty workspace. Workspace
administration is a deployment setting (on by default until sign-in exists, not a permission); when it
is off the screen is read only and names the setting.

Each workspace names the model and release it runs, in the selector and in Settings › Workspaces,
and a new workspace starts on the default workspace's model or on another installed release chosen
when it is created.

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
checks and the difference between a missing optional field and a stored null. Each active filter is
a pill beside the search, opening its editor or removed with ×; ＋ Filter lists the view's fields by
group and opens one editor per field: the common conditions to choose from and the rest under More,
a yes/no applied as it is chosen, a relationship as is any of, has none or has any with the records
ticked in a list. On a phone the editor is a sheet whose button says how many records it will show.
Where the view offers a relationship, the filter keeps the records related to any of chosen records,
to none, or to any; its pill names the chosen records, also after a reload. The selection's "all
matching", every bulk change and Export read the same filtered records.

A collection or a record's table may show, where the model declares it, a column of each row's
related records of one relationship as chips in their type's colour, on one line: as many as the
column's width holds, then "+N more" for the rest, and no "+N more" when they all fit; resizing the
column shows more or fewer at once. It shows the relationships of the data being viewed (live, a change set or a
publication). Where a row can hold only one such record, the column sorts by its name, rows without
one last; a column that can hold several does not sort, and none filters. A column hidden in the
table's display settings is not read. A column may also show a field of the related records, or of a
record above them, instead of their names: a translation by its language's code, for example ("ar
cs en +4 more"); such a column does not sort. Through the API, any list of a type can carry the same
related records (`expand`), with such a field, for any relationship the type has.

Where a collection's data can be written and the deployment lets jobs be created, records can be
selected in its table: by checkbox, a Shift range, the rows shown, or every record the search and
filters match (Cmd+A), with single records left out. The bar above the table says what is selected
and offers Change values, Change relationships and Delete.
A selection larger than one bulk change may hold is refused with the count, the limit and what to
do.

**Change values…** changes the selected records together: each field (not read-only or hidden ones)
is kept, set to a value or cleared (never a required one), several in one change, and the change
either changes the records that can change or nothing unless every one can. Nothing is written
before a preview says how many records will change, how many already hold what is asked and which
will be refused and why, each refused record openable; Apply then decides every record again and
shows the result. Records changed by someone else since they were shown are refused rather than
overwritten. The selection stays after a change, so a second change follows the first, and Preview
again repeats a change for what it did not change. Leaving the dialog before applying cancels the
preview, whether by Back, closing it or clicking outside; View job keeps it waiting, to be applied
or cancelled on its job page.

**Delete…** deletes the selected records, each with the records inside it and the records it owns;
its relationships to other records are removed and those records stay. Before anything is deleted
the preview says how many selected records go, how many records go with them by type, how many
relationships are removed and how many of those reach records that stay, and which selected records
go with another selected one. The button names the whole ("Delete 352 records"). Deleting removes
exactly what the preview showed for each record: one changed meanwhile (a child added, a record
edited) is refused and named, the rest are deleted, and Preview again shows it as it is now. The
deleted records leave the selection.

**Change relationships…** changes the selected records' relationships of one kind: any the model
allows the type, in either direction, except a parent and a record's owner. What it offers follows
how many each side may hold: add and remove records together, replace them with the records chosen,
set the one record each selected record holds, or clear them; a required relationship is never
removed or cleared. The relationship is chosen from pills and what to do from a segmented choice;
the other records are ticked in a searchable list. Remove lists only the records the selection
holds, each with how many selected records hold it; Add marks those already held. The dialog says
how many changes the selection makes and explains, before sending, a change larger than the
deployment allows. The preview counts the relationships added, removed and already
as asked and names each refused record; Apply refuses a record whose relationships of that kind
changed since the preview and applies the rest. Relationship values are not changed here; a
record's relationships page changes them. Where the list shows the relationship as a column, the
rows show the change once applied.

Where the model limits which records a relationship may choose (a binding's `candidates`: by the
records' names or attributes, or an ancestor's), every place that offers records for it offers only
those and says so: the relation form, a new record's required relationship, Change relationships,
the relationship filter, the relationship view and the matrix. A record that does not meet its own
end of the relationship is not offered it, and its panel says why. A new relationship outside the
criteria is refused through the API, alone, in a batch or in an import; one made before stays when
the data changes so it no longer meets them, and can be removed as any other.

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
missing optional value is kept distinct from a stored false, zero, empty or null value. Clicking a value
(or Enter on it) opens its editor, clicking an empty field adds a value, and an optional value is
removed by its trash icon after a confirmation; saving is always explicit (Save or Enter, Escape
cancels), and selecting a value's text to copy it does not open the editor. The record's header
edits its title (usually the name) and subtitle the same way, on the full page and beside a tree,
and offers Add for an empty subtitle; **Edit record**, the form with every field, is in the record's
⋯ menu. A list of records (a collection, or a record's table) edits in its cells too: the cell
under the pointer shows a pencil, and a trash where an optional value or a single relationship is
set, beside its value (always on a touch screen); the pencil opens the value's editor in the cell,
the relationship picker where a record holds one of the kind (only the records the model allows),
or a dialog of ticked records where it holds several, saved together. A click elsewhere in the row,
the value included, still opens the record; a toast says whether the save went to Live or the open
change set. Ancestor columns, containment and owned relationships, read-only and computed fields
and publications show no icons; the keyboard's way is the row's ⋯ menu. The header shows its ID, the `id` every API returns, with a button that copies it. In a
record's relationship tables each row's actions are icons, each with a tooltip: change to another
record, edit the relationship's values, delete; a row that is managed through the parent or
required shows a lock saying so.

Evidence: [inline editor](../../frontend/src/features/objects/panels/InlineAttributeEditor.tsx),
[attribute panel](../../frontend/src/features/objects/panels/AttributesPanel.tsx),
[attribute values](../../backend/app/engine/records/attributes.py).

## F07 — Maintain containment and hierarchy

**User outcome:** A steward places a record under the right parent while the hierarchy keeps its
meaning and integrity.

Creating or moving a contained record updates its parent and its typed parent relationship together.
A wrong parent type, a cycle or a separate edit of the engine-managed parent relationship is refused.

The sidebar tree reads any hierarchy by parent at any size and depth, by keyboard or pointer, and its
search lists matching records of every type with their path. It scrolls as one list with the page
or the sidebar, its type groups start folded and open like records, and a long group reads more as
its end comes into view (with **Show earlier records** above a group opened partway down). Several
records can be selected (Cmd or Ctrl to add or remove one, Shift for a range, Ctrl+Space and
Shift+arrows by keyboard, Escape to clear) without changing the page, and dragged together onto a
new parent, in the sidebar as in a tree view, or moved with **Move to…** (right click or Shift+F10);
one confirmation moves them all or none. A model-declared tree view adds editing:
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
record types, direction, cardinality, requiredness and field types validated. Where a record may hold
only one relationship of a kind (a `many-to-one` binding from its side, `one-to-many` to it), its
panel offers **Set** while it holds none and **Change** and **Delete** on the one it holds, never an
Add that would be refused; Change replaces it in one write and is refused if the relationship
changed after the list was read. Parent relationships are
shown but changed only by moving the record (F07). Related records are found by server-side search.
A record opened beside a tree lens lists them under **Connected**, one row per relationship panel the
record's detail declares, as chips in their types' colours that open the record; they are managed in
the panels' tables on the record's full page, one click away.

A mapping grid shows each source value as mapped, unmapped or ambiguous across the whole list, with
counts, target previews (chips in the target type's colour) and a state filter. Choosing, replacing or clearing a target is one atomic
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
language, each cell current, missing, inactive or held only in history, with its record as a chip in
the record type's colour. It filters to gaps across the
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
cause, and changes a publish applied to live data name the publication. History is bounded and does
not expose whole model documents.

Limits: no authenticated actor until 0.12.

Evidence: [history panel](../../frontend/src/features/objects/panels/HistoryPanel.tsx),
[audit](../../backend/app/engine/records/audit.py).

## F12 — Prepare a change set

**User outcome:** A team prepares a coordinated change without disturbing live data.

A change set starts from current live data (including edits since the last publication) or from a
selected publication, and is named, listed, opened and discarded. Records are edited in it through the
same screens and API as live data. Starting from an earlier publication is not a rollback: only what
the change set changes is applied when it is published. While one is open, an amber strip at the top
of the page names it and carries its actions; changing its model version and discarding it are in
its **More change set actions** menu.

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
stay. This is different from retiring a workspace. Each publication opens from its row, and the row's
menu starts a change set from it or withdraws it; an open publication is shown under a violet strip.

Evidence: [publications](../../frontend/src/features/workspaces/Publications.tsx),
[WP9 publications runner](../../frontend/e2e/wp9-publications.mjs).

## F15 — Inspect and release application models

**User outcome:** A model administrator evolves what applications mean without editing the active
definition in place.

Settings › **Model** lists installed releases and drafts beside the selected one (the active release
when none is chosen), each at its own address, with summaries, technical details, comparisons
between releases and JSON export. With model administration enabled (a
deployment setting, one API process), an administrator edits a JSON draft with conflict protection,
validates and compiles it, installs an immutable release and activates a compatible one. Installing
never activates. Activation is refused when existing data would not fit, and also when a consumer API
contract changes incompatibly without a new contract version (F23). Releases on unsupported older
schemas stay inspectable and exportable.

Each workspace runs a model release of its own, and different workspaces may run different models.
Through the API a workspace is created on a chosen installed release (or on the default workspace's),
and a release is activated into one workspace: only that workspace's data is checked, only its
subscriptions are suspended, and the other workspaces keep their models. The activation names the
workspace's change sets left on its previous release, which cannot be published. Every read and
write runs under its workspace's model; a write is refused, nothing saved, when its workspace was
moved to another release meanwhile. A workspace whose release this version cannot read is unavailable
on its own while the others are served. Through the API, an import profile belongs to one model: it
is read and used in the workspaces running that model, and refused in a workspace running another;
a draft is compared with its own model and shows, for each workspace running that model, what
activating it there would need; a model built from a workbook can be installed and given a new
workspace of its own. The consumer API index and each API's OpenAPI document describe the workspace
asked for. One lookup of records by name, ID, type or parent can read several workspaces at once,
each record under its own workspace's model and naming its workspace and release; naming a type or
application one of those models lacks is refused, naming the workspaces that lack it. Records of a
workspace running another model cannot be loaded as counterparts: each such row is refused and the
rest of the file loads.

In the browser, each workspace shows its own model: switching workspace changes the applications,
the navigation and the pages to that workspace's model, and a toast says when the model or its
release differs. The workspace selector names each workspace's model and release and marks the ones
running another model or another release. An address naming an application, collection or kind of
record the workspace's model lacks opens a page saying so, with the workspaces whose model has it,
instead of another page; so do an unknown workspace and one whose release cannot be loaded. Settings ›
**Model** is laid out as Settings › Workspaces: a list of the models (the default workspace's first,
then the others in use, then the rest, and the drafts of models not installed yet) beside the
selected model's card, which shows where it runs, its newest release, its releases newest first with
the workspaces running each, and the drafts started from its releases with how far behind each is.
A workspace's model is changed with **Change model…** from the model's card or a release's page:
the dialog lists the installed releases grouped by model, the workspace's own first, checks that
workspace's data alone, lists its open change sets that would stay on its previous release and the
workspaces it leaves unchanged, and offers no change when the data does not fit. A page opened
before such a change cannot save under the release it was built on: its save is refused in place,
nothing is saved, and a toast names the workspace's new release with **Reload**. The top bar shows
the default workspace's model's product name on every page. A job's page names its types under its own workspace's model. The model editor previews
records of a workspace running the draft's model, and **Install and activate** puts the release into
an existing workspace or a new one created on it. The lookup over several workspaces has no screen.

Through the API, a workspace's data is migrated to a release it does not fit, of its own model or
another: a preview, which changes nothing, lists every value converted to its new type, every record
whose type changes, everything removed (records of a type the release lacks with what they contain,
values with no place or that do not convert, relationships with no place) and every record the
release would refuse. A type the release renamed can be mapped to its new key so its records keep
their IDs. A preview with refusals cannot be confirmed until the data is fixed; one that removes
anything is confirmed only by accepting the loss. The confirmation is refused when the workspace
changed after the preview; once confirmed, the data and the workspace's release switch together,
each change in the records' history and the workspace's feed, and the other workspaces are not
touched. A migration is also refused when it would change what a consumer API's consumers read
without a new contract version, as activation is.

In the browser, **Change model…** offers **Preview the migration…** when the workspace's data does
not fit the chosen release (where model administration and background jobs run). The migration's page
in Settings › Model says nothing has changed yet, lists what the release no longer has with a choice
for each missing type and field (what it became, or not kept; each choice previews again), counts
the items converted, changed in type, removed and to be fixed, and lists each kind's items page by
page. The removal is accepted with a checkbox and the migration confirmed with **Migrate**; items to
be fixed block it; a workspace changed after the preview asks to preview again; the page says when
the workspace runs the new release.

A change set that works under a release its workspace no longer runs, such as one started from an
older publication, cannot be published as it is. Its bar offers **Move ‹workspace› to ‹release› and
publish…** (where model administration and background jobs run): the same migration page moves the
workspace's data back to the change set's release and says it then publishes the change set. What
would stop the publication, such as a record changed both in the change set and live, is listed with
the items to be fixed. **Migrate and publish** does both in one step, or nothing; the page then names
the new publication. Through the API this is the same migration naming the change set.

The other way round, the change set itself moves onto the release its workspace runs, even when its
content does not fit that release: its bar offers **Move this change set to ‹release›…** (where
background jobs run). The same page then lists what changes in the change set: its values converted
to their new types, its records whose type changes, what the release has no place for (removed from
the change set only once accepted), and what must be fixed first, including a record the change set
changed that was also changed live since it started. Nothing live changes, and the workspace keeps
its release. **Move change set** converts the change set's content and moves it in one step, or
nothing; records it did not change then read as they are live, and it publishes as usual. Through
the API this is a move of the change set, previewed and confirmed as a migration is.

Workspaces may run models written in different versions of the model language at once: every
version from 0.5 to 0.10 is read, written and run side by side, each workspace under its own
release. Raising a model to a newer language version with nothing else changed activates without a
migration, and a migration between models of different versions converts only what the two models
declare differently. A model in a version outside that range is refused when it is installed, with
the supported versions named, and a model file outside it stops the service from starting with what
to do; a workspace on a release a later engine wrote stays unavailable on its own, and the log says
to run that later version.

Through the API, a draft can also be changed step by step with typed operations instead of whole
JSON: add, rename, re-key, split, merge or remove applications, types, attributes and relation
types, set where a type sits in the containment tree, allow relations between types, lay out views
and detail pages, and group an application's collections. New types get a table view and a detail
page from the server. Each request is one step of the draft's history, which can be read, undone and
redone; a step that later steps build on is undone together with them. A key change, removal or
other change that would need a migration of something already released is refused, saying how many
records, values and relationships it would touch. A JSON edit in the workbench is recorded as one
step too.

The **model editor** makes the same changes in the browser. A draft opens in it from Settings ›
Model (**Open in editor**, or straight after **New draft**, which can start from a release or from an
empty model). The model pane shows each application with its types in their containment tree, its
navigation groups, the relation types and the attribute types, each marked new, changed or released.
Choosing an element shows it with its operations: a type's attributes and relations, an application's
types and groups, where a relation type or an attribute type is used. The relationship matrix shows
which relations each type may start to each other type, and a cell allows one. Attributes and types
move with **Move to…**, or by dragging them in the model pane. The issues list links each problem to
its element; the history lists every step in plain words, and any step can be undone from it, with
the steps that depend on it when there are some. If another administrator changed the draft first,
the editor names their steps and asks whether to apply the change again. **Install and activate**
does both in one confirmed step, showing the release version (proposed from the base release), the
differences and whether stored data is affected; a refused activation leaves the release installed
and says so. On a phone the panes are tabs. The JSON workbench stays one click away (**Open as
JSON**).

**Preview** in a type's header shows the type's record page and its table as they will look once the
draft is active, drawn from the draft before it is installed, over a real record of a workspace you
choose (or an empty record for a new type). The page's buttons and fields are shown but disabled:
the preview changes no data. **Edit layout** opens the layout editor over the whole editor, with
**Back to the model editor**: move panels up and down or between the main column and the side, hide
or show them, rename them and choose their columns and sort; move fields, group them into new field
groups and add missing ones; choose a table's columns, filters and default sort. Every change is a
step with undo and redo; each has a menu that works by keyboard, and with a mouse it can be dragged.
A type the model gives no detail page of its own can be given one in a step. After install and
activate, the record screen shows the same layout. A draft with errors is not previewed until they
are fixed or undone.

**Consumer APIs**, the second tab of the editor's left pane, lists the draft's consumer APIs. A new
one starts from the types it exposes, with their fields, Get by ID and a list per type. Each opens with
its tabs: the exposed types and their public names and the related records it serves; its fields,
with their sources (picked in order from what the exposed types and the types above them hold), role
and default, edited in place; which operations it offers, its lists, its
XREF match rules and its custom events; its filters. Two documents an integration takes from it are
shown with Copy and Download: the **Schema** of the message consumers receive and a **Message
example**. Every change is a step with undo. A change the consumers of the active release would
notice is marked "Needs v2" as soon as it is made, with a button that raises the contract version,
and the install dialog lists each consumer API's result; activation waits until each is compatible.
Renaming a key the draft added renames it in the consumer APIs too.

**A workbook against a draft**: an Excel workbook or a CSV file uploaded to a model draft is kept
with it and read once. Its profile lists each sheet's lists (blocks of columns
between empty columns) with their header rows, and each column's filled cells, distinct values, the
types its values can be read as, whether it can identify a row, the characters that split its
values, the values that stand for "nothing" such as N/A, and the other columns, and the records of a
chosen workspace, holding the same values. A dry run then loads the whole file through an import
profile against the draft's model, as if it were installed, and says what the import would do:
records created and changed, values, relationships and the rows refused by reason, what changed
since the last dry run, and the rows behind each figure. It writes nothing; a dry run of a draft
changed meanwhile is cancelled. An import can later name the stored file instead of sending it
again.

The draft keeps its own import profile, built one step at a time like the model: which sheet loads
which type and how a row finds its record, then each column mapped to a name, an attribute, a
parent, a relationship (read as a lookup by name, split on a delimiter, or as Y/N flag columns) or
ignored, values replaced through value maps, and a lookup allowed to create the list values it
names that do not exist yet. Each step is in the draft's history and undone with Undo. The profile
follows the model: renaming a type or an attribute renames it in the profile, a moved attribute
takes its column along, splitting and merging types carry their columns, and a removed attribute
leaves its column marked as no longer mapped until it is mapped again. After each step that could
change the load the dry run runs again by itself. Installing the draft saves its profile for loading
the workbook, and any import may use "create missing values" on a lookup.

**The editor with a workbook.** Settings › Model has **New from a workbook**: a draft of the active
release (or an empty one) with the workbook uploaded to it, opened in the editor; an open draft takes
one, or a newer one, from its ⋯ menu. While the workbook is read the editor says so; then a **source
pane** stands left of the model pane: the sheets as tabs, each with the types it loads, and each
column with its letter, its statistics in a line and its status (key, mapped, not mapped, ignored, or
an issue). Selecting a column shows it in the centre: what it feeds, how it is read and matched, its
split, whether values that do not exist are created, its value map, whether it is the rows' key, the
rows of its source the dry run refused, and its statistics; the type it feeds is marked in the model
pane, and selecting a type marks the columns that feed it. **Map to…**, from the column, by
Shift+F10 in the list, or by dragging the column onto a type in the model pane, asks which type each
row is a record of (proposed from the sheet's name), what the column holds (the name, an attribute
or a new one, the parent, a related record, a flag of a relation, or nothing) and its target, chosen
by typing and arrow keys; it starts the sheet's source when none loads that type, and is one step,
undone with Undo. A value map starts from the column's placeholders. The drawer's **Dry run** tab
shows the figures per source with what they were before the step, each opening the rows behind it.
**Load into a change set…** installs and activates the draft when the model changed (or only saves
the profile when it did not), opens a change set named after the file in a chosen workspace, loads
the stored file through the saved profile, follows the load and opens the change set's review, from
where it is validated and published. Changing the key of the selected element keeps it selected.
Map to… also reads a column as a related record matched by a unique attribute of its type, or as a
value of a related record (its name or an attribute, under a parent record named once or in another
column, created when it does not exist), and the column's centre lists its most frequent values.

**The engine proposes the model and its mapping.** New from a workbook asks what to propose: a new
application (named after the file, or as you name it), additions to the model (the sheets and
columns matched to its types and attributes first, by name and by the values its records hold in a
chosen workspace), or nothing. Once the workbook is read, the engine reads its sheets for known
shapes (the key and the name of each row, a parent repeated on every row with the columns that
belong to it, a code with its name, lists stored as text, Y/N columns of one set, cells holding
several values, translations one row per language or one column per language, columns holding
GUIDs, placeholders such as N/A, names that drift for one code) and writes a first draft into the
editor: each proposal one step of the history ("Proposed: …"), undone like any step, with the dry
run after the last. What is still as the engine proposed it is marked **Proposed** in the model and
source panes; selecting it shows **Proposed because**: what was found, its evidence and the
alternatives (a text attribute instead of a list, a list instead of a parent, yes/no attributes
instead of a set), each one step. Any change makes the element yours, and the mark goes. ⋯ ›
**Propose again…** reads the workbook once more, for instance after a newer version: what is still
as proposed follows it, what you changed stays, and where the workbook reads a column otherwise it
is an issue; a proposal you undid is not applied again. Once installed, the types read Released.
Through the API the proposals can be read before anything is applied.

**A workbook that describes a model.** A sheet listing fields with their types (lookup, flag, text,
number, date, …) and the list each lookup takes its values from, each list on a sheet of its own,
is read before anything else: the engine proposes one type with those fields, each list read from
its sheet by its ID and name, and one set for the flag fields of one target. The description
sheet's columns read **Describes the model**; nothing loads from it. A row whose ID is a placeholder
such as `?` is skipped (the dry run counts it), and a list whose sheet holds only "To be defined" is
added with nothing to load. A flat table naming the same records then comes as **additions to the
model**, after the description is loaded: its sheet is matched to the described type by its
headers, its lists to the stored lists by name, a code column to the stored records by their ID.
Where the file names a code otherwise than the stored record, the stored name stands and the
difference is shown, with loading the file's names as the alternative; values the stored list lacks
are shown with their rows and refused, with creating them on load as the alternative. What the
editor uploads is compared with the default workspace's records.

**A sheet of lists laid out for reading.** A sheet holding no table but many small lists, side by
side and under each other, under section and group titles, is read list by list: each list with
its header, the titles above it and a note under its header ("multiple answers", "multiple choice",
"free field"). Each list is proposed as a list type loading its own part of the sheet by name, the
note row skipped and the note kept as the type's description; a column beside the names filled on
most of their rows is their translation (in the language its header names, else "Language 1",
which you rename), a column of Y and N is a yes/no attribute, a column with only its header is
reported and not read. The lists under one title are grouped in the sidebar. A "free field" or a
header with nothing under it proposes nothing, and the inference says so. In the editor the source
pane shows such a sheet as its lists under their titles, each Proposed, Loaded or Not loaded;
selecting one shows the cells around it, so a value that is no value (a second header row, a
sentence) can be seen. **Adjust list…** sets the rows and columns it loads, its columns keeping what
they load when its header row moves, and can name the list after its new header; **Don't load this
list** takes it out of the load and the model in one step, and proposing again leaves it out; **Load
as a list…** reads a part of the sheet the inference left out as a list. A row under a list's header
that answers none of its yes/no columns (a role under each category) is read as a second header row
and skipped. Three lists or more of the same columns under one title, or under none, can be read as
one list under their headers: on any of them, **Read these N lists as one list under their headers**
makes a list of the headers (the categories) and one list of the values under them, each value
under its header; a value under two headers is two records, and loading the file again changes
nothing. The engine cannot tell headers that are categories from headers that are list names, so
each stays its own list until you choose this. A category's name in another language (the header of
its translation column) and the role in a second header row are not loaded; you add them.

A file of one category's items can be loaded under that category: an import profile's source sets
the parent of every row it loads, and creates it when asked. A list loaded by name finds its records
among their parent's children.

**The next version of a workbook.** Installing a draft with a workbook saves its import profile;
Settings › Data operations › **Import profiles** lists the stored profiles beside the selected one: whether it
still holds against the active model, and its last load (the file, when, what it did with the rows,
and whether it is live, waiting in a change set, published or discarded, with the change set review
or the load's job a click away). On a profile's page, **Upload the next
version…** takes the new file, reads it and checks it against the profile before anything is
written: columns new, missing or renamed (a column under a new header at the same place, holding
the same values), values that name no record yet (created by the load, or refused), records whose
name in the file differs from the live record, records the file no longer names, the profile's
problems against the active model, and what the load would do (records added, changed and
unchanged, rows refused, each list with its rows). **Accept** a rename and **Ignore** a new column
from the page; each saves the profile and checks the file again. Records missing from the file are
kept unless the profile says to delete them, which happens only in a change set: the record goes
with its own relationships, and a record others depend on is refused for you to decide. **Load into
a change set…** opens a new change set with the file loaded; its review lists only what the new
version changes. A lookup column now switches its record's value when the next version names
another (a material changed from Steel to Bamboo), where the relation allows one per record.

Limits: a field's editor cannot be chosen (each value type has one); the draft editor has no control
for what a load does with missing records (Settings › Import profiles and the API set it); the
a category's name in another language is not loaded when lists are read as one list under their
headers;
dragging a list's outline on the grid is not offered (its fields set it); the optional assistant is an interface
only, with no provider. A consumer
API's documents are worked out from the draft; messages from real records come from the consumer API
after activation.

Evidence: [model editor](../../frontend/src/features/model-editor/ModelEditor.tsx),
[A4a runner](../../frontend/e2e/authoring-a4a-model-editor.mjs),
[preview and layout editor](../../frontend/src/features/model-editor/TypePreview.tsx),
[A4b runner](../../frontend/e2e/authoring-a4b-preview-layout.mjs),
[consumer API editor](../../frontend/src/features/model-editor/ConsumerApis.tsx),
[A4c runner](../../frontend/e2e/authoring-a4c-consumer-apis.mjs),
[model workbench](../../frontend/src/features/model-admin/ModelWorkbench.tsx),
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
unavailable service. Integration-scale functions are F20–F23 and F25; the reference page is F24.

Limits: every API is unauthenticated until 0.12.

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
mode, resizable panels and display preferences. On a phone the band under the top bar is one line:
tapping the workspace, the application (with its icon) or Live, the change set or the publication
opens that choice, so the top bar has no application tabs and the navigation drawer holds only the
collections and records; Settings returns to the application through its Back link. Settings › **Appearance** sets the theme and the table
density every table starts from; a view's own density choice overrides it. It also sets the palette
of the record type colours (B, magenta and olive, or A, plum and gold) and when a record's editable
fields show their pencil: on hover and focus (the default), or faintly all the time. An automated accessibility gate (axe) and a visual
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
SQLite was a development database only; the engine offers no migration from it.

Settings › **About** and **Deployment** show what the deployment runs and how it is configured, from
`GET /api/v1/system`: the engine and management API version, the schema languages, the active
release and when it was activated, the database's migration revision, and every setting with its
value, default, source and what it controls, beside the capability groups. Secrets read only as set
or not set, and the database address without its password. Settings change only with a restart.
Every settings page has **Back to {application}** in the top bar, which returns to the page Settings
was opened from (or the home page when Settings was opened first).

Evidence: [operations guide](../OPERATIONS.md), [application startup](../../backend/app/main.py),
[settings catalogue](../../backend/app/config.py), [J31 journey tests](../../backend/tests/journeys/test_j31_system.py),
[settings runner](../../frontend/e2e/u3-settings.mjs).

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
per-type list and the model-aware query returns the records valid on that date, in any context. A
consuming system asks the same question through a consumer API: a list, a record, a lookup or a batch
on a date returns only the records valid that day, names the record types it dated, and refuses a date
for a type that declares no period rather than guessing one. Related items shown with a record are not
dated. In the example model, master values carry a period. In the browser the two dates are ordinary
fields; there is no date filter yet.

Evidence: [effective periods](../API.md#effective-periods-and-asof-base-09-q4),
[on the consumer API](../API.md#business-dates-asof-on-the-consumer-api),
[ADR-038](../DECISIONS.md#adr-038--business-validity-is-a-declared-effective-period-separate-from-history-and-publications).

## F22 — Load data in bulk as jobs

**User outcome:** An integration loads or synchronises many records with per-item results and safe
retries, instead of looping over single calls.

A batch of create, update, upsert and delete items runs live or in a change set, inline (up to 1,000
items) or in the background (up to 1,000,000). A delete item can take a record's dependants with it,
as a single delete does, confirmed record by record: a preview gives each item's impact, and
applying deletes exactly that, refusing a record whose impact changed since; large deletes run as
set operations in the database. Records are addressed by ID or by a unique field's
value, so a recurring feed and a one-off load use the same contract. The same batch relates records,
makes sure a relationship exists, changes or removes one, and replaces a record's whole set of
related records with a list, keeping the relationships it already has; a record's relationship list
names each set's version, so a replacement can claim the set the caller read. The caller chooses all-or-nothing
or item-by-item; every item goes through the same rules as a single write and gets its own outcome.
An idempotency key makes a retry return the first result. A background batch can be previewed
first: it runs without writing anything and says what applying would do, item by item, and is then
applied or cancelled. Background jobs report progress, survive
restarts without repeating or skipping an item, and can be cancelled. Jobs and their outcomes are
kept for a configurable retention.

Settings › Data operations › **Jobs** lists the jobs of every workspace, newest first, with
their state, result and item counts, and cancels a queued or running job after confirming (while
the deployment lets jobs be created). It also shows the batch and job limits and how long the
change feed is kept.

An integration also exports a stated scope of a workspace as a job: live data, a change set or a
publication; chosen types, each with its own criteria; only below one record; on a business date;
with or without relationships; as JSON Lines, CSV or an Excel workbook. Everything in the file is
read at one instant, and the job says what the file holds: counts per type, the context, the change
feed position it equals, the model release, the size and a checksum. A live export is therefore a
starting point for following the change feed. The JSON Lines file sent back as a batch changes
nothing; edited, it updates only the records nobody else changed since the export. CSV and the
workbook hold the same records in one table layout, the workbook with typed cells and dropdowns. A
cancelled or failed export has no file.

In the browser, **Export** on a collection page exports what the page shows (its type, its data
context, its filters and its narrowing to a parent; the search is not carried), with other types of
the application if wanted, a date, the relationships and a format. Settings › Data operations › Jobs
starts an export of any types of a workspace. A notification says the export started, and
another when it finished, with Download and the job's page, or that it failed or was cancelled. Each
job has its own page showing its state and progress as they change, its error, Cancel, and for an
export what the file holds and Download. An integration follows any job the same way through the
API: the engine pushes each change as it commits.

From a collection page, Export also makes a **workbook for people**: one Excel workbook shaped by
the table. Its main sheet holds the columns the table shows, in its order and with its labels, the
values formatted as the table shows them, and each relationship column as every related record's
name (or a field of theirs, such as a unique code) separated by "; ". Under Advanced the user picks
the columns and their order, the field a relationship column shows, and which relationships get a
sheet of their own: the records the exported ones own (their translations, say), or the
relationships themselves with their values. The header stays in view and can be filtered, the name
and relationship columns are coloured as their kinds of record are in the app, and the record's ID
and version sit in hidden columns. A column that cannot say what to change (a relationship edited on
its own sheet, a field that identifies nothing) is marked "(not imported)". Imported back from the
page or Jobs without choosing a profile, the workbook is read as it was written, and the
import's page says so ("Read as exported from System values on 10 Oct 2026"): an untouched workbook
changes nothing; edited values, names and rows change exactly those; a list of names replaces the
record's relationships of that kind, a relationship sheet adds and changes relationships but never
removes one; a record changed by someone else since the export is refused. Clearing a cell clears
nothing, as for any import. An integration asks for the same workbook through the API.

The workbook is also made for filling in. Under Advanced, a relationship whose records belong to the
exported ones (translations, say) can be laid out as **columns per parent**: one row per record and,
for each parent those records stand under (each translation group), a column per chosen field,
headed with the parent and the higher level the records are unique within (its language). Parents
holding records come by themselves, and others are added with the record search, so a new language's
group arrives as an empty column: filled in and imported, it creates every translation in that
language, each under the group and belonging to its row's record. Cells that name one other record
(a single relationship, a relationship sheet's related record, a parent or an owner) offer a list to
choose from, taken from a sheet of the records that relationship may choose; and every cell has a
border.

An integration imports a file the same way, as a job, into live data or a change set: an Excel
workbook or a CSV file through an import profile, or a JSON Lines file of bulk items, or an export's
CSV or workbook sent back. A profile is kept in the engine, under a version, and says how the file's
sheets and columns become records and relationships: which type each sheet loads, which column finds
an existing record, which columns hold names and values, which name a parent or related records
(by name, ID or any value, a cell split into several, or a column per record ticked), value maps
for placeholders, and records that belong to each row's record, such as its translations. A
profile is checked against the model when it is saved and whenever it is used, and every problem is
named where it is. The import finds the records a row names among the existing ones and those the
same file loads, loads parents before their children, and names each outcome by its sheet and row.
A row that cannot load is refused with every cell that failed and why (a value that does not fit, a
name that finds no record or several, one key on rows that disagree, rows that are each other's
parents); the other rows load, or with all-or-nothing none do. A file that does not fit its profile,
or cannot be read, changes nothing. An unchanged export sent back changes nothing.

An import can be previewed first: the whole file is read and tried against the data without
changing anything, and the job then says what loading it would do (how many records would be
created, updated or left unchanged, which rows would be refused and why, and whether the chosen
policy would load anything) together with a report per column of how its cells were read (empty,
converted, mapped, refused, or for a column naming records, found, not found or ambiguous). Outcomes
read row by row. A very large file is previewed in part, saying how much was tried. Confirmed, the
import loads the file as it stands then, so data changed meanwhile counts; cancelled or left, it
ends without writing.

In the browser, **Import** on a collection page loads a file into the data the page shows, live or
its change set, and **New import** on Settings › Data operations › Jobs loads one into a chosen
workspace's live data or one of its change sets. The user picks the file, a stored profile or none,
whether the rows that can load load or nothing does unless every row loads, and whether records the
file finds are updated; the import is always previewed first, and its page opens at once. It shows
what loading would do, the refused rows with each failing cell and its column, and how each column
was read, with columns worth checking marked; **Load the file** loads it and **Cancel import** ends
it. After loading, the page shows what was applied and how to load the refused rows: correct them in
the file and send it again, and rows already loaded come back unchanged. A notification says when a
preview is ready or an import finished, unless its page is already open, and a collection reloads
when an import this tab started loaded into it.

Record IDs are unique across the instance, so a file naming records by their IDs, such as an
export, names another workspace's records when it is sent to a second workspace. Such a file loads
there as that workspace's own records: each record gets an ID derived from its original ID and the
workspace, so the file's parents and relationships arrive whole, the same file sent again changes
nothing, and a workspace's types can be loaded file by file. The browser does this by default and
says so above the preview; an integration asks for it. Refused instead, the import says why above
the preview, and each refused row names the workspace its record belongs to. Nothing links the two
records after the load.

Limits: notifications reach the tab that started the job while it is open; profiles are written
through the API (their editor is 0.10); a relationship of another workspace edited or removed by its
relationship ID is refused (exports carry none); refused rows are listed, not offered as a file to download;
the relationship view in the browser still saves one related record at a time.

Evidence: [batch contracts](../API.md#batches-and-jobs-base-09-b1-b2-b3),
[exports](../API.md#exports-base-09-j1),
[jobs](../../backend/app/engine/jobs/),
[ADR-036](../DECISIONS.md#adr-036--a-batch-is-a-job-one-mechanism-for-bulk-writes-imports-and-exports).

## F23 — Declare consumer APIs and read through them

**User outcome:** A model administrator defines the read-only contract other systems will use, and
cannot break it by accident.

The model (schema 0.9) declares consumer APIs in the order a reader asks about them: which record
types they expose and under which public names, which operations they offer (reading by ID,
looking up, resolving in a batch, lists, events), what a business object looks like, how it is
looked up, how reads are filtered, and a contract version. Whatever an author leaves out takes a
sensible default, and an integrator or the UI can read a definition with every default written out.
Every reference is validated, and a mistake is reported at the place the author wrote it. Comparing
releases reports contract changes, and activation refuses a breaking change without a higher contract
version, such as no longer offering an operation. A definition written for the earlier model language
can no longer be submitted; releases installed with one keep working unchanged.

A consumer API also declares the change events its consumers will be told about: which record types,
whether creations, updates or deletions, and which of the fields and related-record blocks count as
an update. The declaration is validated and is part of the contract, so a release cannot quietly
tell consumers less.

A consuming system follows those events: in the order the changes were made, from a position (the
start, or the moment a publication it read was made), a page at a time, resuming where it stopped.
Each event names the record, what kind of change it was and which watched fields or blocks changed,
including changes to records it shows (its parent, an ancestor's name, a related record), and by
default carries the record itself as a read of it would answer, so the consumer need not ask again.
Events can be narrowed like a list. A consumer that fell behind longer than the retention period is
told which publication to read again.

Where a deployment turns them on, an operator subscribes a web address to some of a consumer API's
events in a workspace, narrowed like a list, and chooses how they arrive: one change per request or
several together (up to a size the operator sets), each with the record or as a notification only,
in the engine's own JSON or as CloudEvents, the open standard many event tools read. Only addresses on hosts the deployment allows are accepted, over HTTPS. The engine makes
the key that will sign every delivery and shows it once. The operator can read, list, edit, pause,
resume and delete subscriptions. A new model release that no longer offers what a subscription asks
for, or that changes its contract version, pauses it with the reason, as does retiring its
workspace; resuming checks it again, and after events it missed have expired the operator is told
which publication to read again and can resume from now on instead.

The engine sends each subscription's changes to its address as they happen, in order, signed with
its key so the receiver can tell the request is genuine: one change per request, or, batched, the
changes waiting, up to the subscription's size and at most 1 MiB per request. Requests go one at a
time to keep the order, so for bulk changes batching is much faster. A receiver
that does not answer is tried again, with growing waits, for up to a day, and nothing later is sent
past the change it missed; the subscription shows the attempts, the last error and when the next try
is. After a day it is paused with the reason, and resuming sends everything from the first change
the receiver did not take. A subscription is also paused, with the reason, when its address's host
is no longer allowed, when a record its filter names no longer exists, or when changes expired
before they could be sent; the operator can then resume from now on and re-read the data.

Settings › Integration › **Webhooks** does all of this on a page. A webhook has a name of its
own. Creating one asks for the name and address, the consumer API and workspace, its events (all,
or a few chosen from a searchable list) and any filters (added one at a time, their values typed as
tags), and how requests are made (one event per request or batched, with the object or the
notification only, RDM JSON or CloudEvents 1.0), and shows the signing key once. Each webhook's page has two tabs. **Configuration** shows
whether it is delivering, retrying or paused, the reason and what fixes it, and edits, pauses,
resumes (from the first change not taken, or from now on) and deletes it. **Deliveries** lists
every change sent or being sent, newest first, with its status, attempts, the receiver's answer and
when it went; opening one shows each attempt with how long it took, the request exactly as sent and
the receiver's answer, as formatted JSON, and can send it again by hand, as it was sent, whatever
happened to it (a delivered one only after confirming), in the format it was first sent in; the
receiver can tell a repeat by a header.
Deliveries are kept for a week by default. A workspace
that cannot be deleted because of its subscriptions lists them, each linked to its page.

A consuming system reads one business object through a declared API by its record ID, at the
API's contract version: exactly the fields the definition declares, values in their declared types,
the parent and the path of ancestors, and the related records each projection names (one object or
a list, by the relationship's cardinality). The parent's fields have the same names as the object's
own, and a projection can name each related record's type. It reads live, published data in the default workspace
or the one it names, and every answer says which workspace it read. Work in a change set is never
visible until it is published.

It also reads a declared list of business objects page by page: every record of the list's type, or
those anywhere below a parent record it names by ID, in the list's declared order. It pages forward
and back, jumps to a row or the end, seeks a value and asks for a total. The definition's parameters
narrow a list and a single read alike: by type, by an ancestor, by a related record or by the items
of a projection, with several values as alternatives.

It also looks business objects up by what it knows: a code, a record ID, a name, or a value of a
related record, such as another system's code for the same thing. Each term scores the matching
records by the weights the definition declares, the best first, so a lookup by an exact code finds
that record ahead of records whose names merely contain it. Several terms can be sent at once. The
results page like a list and always carry a total, or the system asks for exactly one result and is
told when nothing, or more than one equally good record, matched.

The system can narrow a lookup by what else it knows, with the same parameters as a list: the type
it expects, the codelist or region a value belongs to, a related record, or the system whose code it
holds. Only the matching records that every parameter keeps are results, with unchanged scores, so a
parameter can turn an ambiguous lookup into a single answer. A parameter over a projection can also
be declared to limit which related records score: a lookup of another system's code then finds only
the records whose code in that system matches.

A system translating a file of codes resolves up to 1,000 of them in one call. Each item is a
lookup or a record ID, with parameters shared by every item and its own where it differs, and each
gets the answer a single lookup for exactly one result would give: the record, or why there is none
or more than one, or why the item itself was refused, in the order sent.

A consuming system can also translate a value from one representation to another in the same read:
"code X in system A, what is it in system B?", or a value's translation in another language. Any
read (a lookup, a record by ID, a list, a batch) names the representation it wants, through a
parameter the definition marks as a possible target, and each record carries the matching related
item as its target. What is found, its score and its order do not change. Where the read answers
one record, the target must be one item: none and several are told apart, each naming the record.

A consuming system that must read one consistent state, an extract read page by page over minutes
or a file of codes resolved against a fixed state, reads a publication instead of live data: by its
ID, or the workspace's current one. Every read answers from what the publication holds, whatever
has changed live since, and names the publication it read. An extract started on the current
publication finishes in it even when a newer one is published meanwhile. A list of the workspace's
publications shows which is current and where to follow changes from after reading one. A
publication is read with the API's contract as it stood when it was published: after a new contract
version, older publications cannot be read through it until the next publication. Every read also
tells a client or cache whether what it holds is still current, so an unchanged answer is not sent
again.

Limits: matching on part of a value needs at least 3 characters; a shorter term matches whole values
only. A lookup whose terms match more than 10,000 records is refused, asking for a more specific
term, whatever parameters narrow it; a lookup for exactly one result that its whole-value matches
already settle is answered without that count. A lookup holds at most 100 terms, and a batch at most
1,000 items (a setting). A read names one target.

An integrator finds the consumer APIs in an index, each with its name, contract version and the
address of its own OpenAPI document. That document is the API's typed contract at its version: every
path written out with the API's name and version, every field with its type, the parameters each read
takes, its limits and its refusals. A client generated from it reads the API's real answers. When a
release raises the contract version, the index and the document move to the new version.

Settings › Integration › **Consumer APIs** shows each consumer API of the active release, read
only: its name in the address, contract version, base URL and OpenAPI document (each with a copy
button), a link to its source in the API reference, the record types it exposes under their public
names, its lists and its events; it links to the release that declares it. The bundled example
model declares one small consumer API (master data, with an event for changed codelist values), so
a fresh installation has one to show.

A definition alone reproduces the answers of the consumer API the design started from (an API
gateway over the source platform's reference data), apart from the documented differences: a
consumer moves to the engine by writing a definition.

Evidence: [consumer API design](../CONSUMER_API.md),
[contract check](../../backend/app/engine/model/consumer_contract.py).

## F24 — Read the API reference

**User outcome:** A developer explores and tries the API from a page served by the engine itself.

`/docs` renders the management API's OpenAPI document with Scalar, and beside it every consumer API
the active model declares, each labelled with its name and contract version and switched to from the
page's source menu. A model release that adds, removes or re-versions a consumer API shows on the next
page load. Settings › Integration › **API reference** lists the same sources with their versions,
each linked to its source on the page and to its OpenAPI document. The script is bundled, so the page works without internet access and loads nothing from
elsewhere; a setting loads it from a CDN instead. Its "try it" console calls the engine that served it.

Evidence: [API reference page](../API.md#api-reference-page-base-09-v1-v2),
[reference module](../../backend/app/management/reference/__init__.py).

## F25 — Follow changes in order

**User outcome:** An integration keeps another system in step with a workspace by reading what
changed since it last looked, instead of re-reading everything.

Every change to a workspace's live data gets the next number in the workspace's change feed, in the
order the changes were saved, with no gaps. An integration stores the last number it processed,
reads on from there a page at a time and knows it is up to date when it reaches the latest one; after
an interruption it continues from its stored number and recognises anything it has seen by its
number. Each entry says what changed (a record or a relationship, created, changed, removed or given
another type), which fields and attribute types were affected (never their values) and why: a user's
change, a bulk job or a publish. Publishing a change set lists each record and relationship it
changed, then the publication itself, so the publication matches live data at its number. Readers can
filter by kind and by record type. Work inside a change set does not appear until it is published.

Entries stay readable for a retention period, 30 days unless the operator sets another. An
integration that comes back after longer is told its number has expired, and which publication to
re-read: it reads that publication, then follows the feed from the publication's number and misses
nothing. Entries after the workspace's current publication never expire, and a workspace with no
current publication keeps every entry, so there is always a way back.

Limits: re-synchronising from an export instead of a publication follows with export jobs.

Evidence: [feed contract](../API.md#change-feed-base-09-f1-f2),
[positions](../../backend/app/engine/records/feed.py), [read](../../backend/app/engine/reads/feed.py).
