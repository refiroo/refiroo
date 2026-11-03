# Model editor inventory (what a model administrator can do in the browser)

Source: `frontend/src` read 2026-11-02 (read-only). Paths are under `frontend/src/features/` unless stated.
Abbreviations: ME = `model-editor/ModelEditor.tsx`, OP = `model-editor/operations.ts`, EP = `model-editor/ElementPanel.tsx`,
MP = `model-editor/ModelPane.tsx`, TP = `model-editor/TypePreview.tsx`, LY = `model-editor/layout.ts`, CA = `model-editor/ConsumerApis.tsx`.
"Ref" column: yes = reachable on the reference instance without installing or activating, as long as a draft exists (Create draft needs only the model-admin capability, not an install); no = needs an installed/activated release or a second workspace. Not verified against a running instance (read-only task): treat "yes" as "by the code, a draft is enough".
"ai-later" = 0.16 AI feature. Every operation below is one history step on the draft (undo/redo); the editor never edits a file.

Menu items for an element are the `OPERATIONS` entries in OP, shown by `OperationsMenu` (`model-editor/OperationsMenu.tsx`): a "⋯"/menu button per row, also on Shift+F10 or the context-menu key in the model pane (MP:278-297). Items marked "draftOnly" in OP are refused or need a migration once the element is part of a release (`needsMigration`, OP:2138); the key of a released element is fixed ("Key fixed: released", EP:121-124).

## 0. Where things are (screens)

| Screen | Path | File |
| --- | --- | --- |
| Models list | Settings › Model (title "Model", eyebrow "Administration"); buttons "New from a workbook", "New draft"; list of models with pills "Runs the default workspace", "Retired", "Draft" | model-admin/ModelWorkbench.tsx:359-376, 262-279 |
| A model | tabs Overview / Releases / Drafts / Structure (counts in labels) | model-admin/ModelPage.tsx:30-37, 226; header "Model" |
| A release | "Immutable release" page | model-admin/ModelReleaseDetail.tsx |
| A draft, JSON view | draft page "JSON model" | model-admin/ModelDraftEditor.tsx |
| Model editor (a draft) | Settings › Model › draft › "Open in editor"; full width; also from a workspace's "Edit model" | ME:1-12; model-admin/ModelDraftEditor.tsx:195 |
| Migration page | after activating a release that needs a migration | model-admin/MigrationPage.tsx |
| Copy and move | Settings › "Copy and move" (page `moves`) | moves/MovesPage.tsx, moves/MoveEditor.tsx |
| Workspace page | Settings › Workspaces › a workspace: "Edit model", "Copy or move data…", applications list | workspaces/WorkspaceAdmin.tsx:577-595, 795-850 |

## 1. Models list, a model, its tabs (Settings › Model)

| # | Action (UI words) | Where | File:line | Ref |
| --- | --- | --- | --- | --- |
| 1.1 | "New draft" (opens the Create draft dialog) | Model › header | ModelWorkbench.tsx:376 | yes |
| 1.2 | "New from a workbook" (Create draft dialog with a workbook; starts proposing) | Model › header | ModelWorkbench.tsx:369; model-admin/CreateDraftDialog.tsx:130 | yes (ai-later for the proposing part? no: the inference is the 0.10 A6 inference, not the 0.16 AI) |
| 1.3 | Create draft dialog: "Draft name"; "Starting document" = "Installed release" / "Empty model" / "Import JSON"; "Base release"; "JSON document" + "Or choose a JSON file"; for a workbook: "Workbook" (XLSX or CSV), "Compare with the records of", the Propose choices (see 7) | dialog "Create draft", eyebrow "Model candidate" | CreateDraftDialog.tsx:130-239 | yes |
| 1.4 | "New draft from <version>" (draft from the newest release) | Model › Overview / Drafts tab | ModelPage.tsx:244 | no (needs an installed release; the reference instance very likely has one) |
| 1.5 | Overview tab: "Newest release", "Installed", workspaces running this model, each with "Change model…" (opens Activate dialog) | Model › Overview | ModelPage.tsx:102-136 | no |
| 1.6 | Releases tab: list "Releases of <model>", pill "Retired" | Model › Releases | ModelPage.tsx:156-173 | no |
| 1.7 | Drafts tab: list "Drafts of <model>" (open a draft) | Model › Drafts | ModelPage.tsx:196 | yes |
| 1.8 | Structure tab: read-only structure of a chosen release: "Release" picker, tables "Attributes" (Attribute, Type, Rules), "Relations" (Relation, Other type, Reads in reverse); note "Read only. Open a release to compare it or export it." | Model › Structure | model-admin/ModelStructure.tsx:67-132, 240-308 | no (needs a release) |
| 1.9 | "Drafts without an installed model" list when no release exists | Model list | ModelWorkbench.tsx:336 | yes |
| 1.10 | Banner "Model mutations are disabled. Installed releases remain available for read-only inspection and export." | Model | ModelWorkbench.tsx:393 | n/a |

## 2. Releases (model-admin/ModelReleaseDetail.tsx)

| # | Action | Where | File:line | Ref |
| --- | --- | --- | --- | --- |
| 2.1 | "Export JSON" (download the immutable release) | release page | ModelReleaseDetail.tsx:299 | no |
| 2.2 | "Create draft from release" | release page | :304 (handler onCreateDraft) | no |
| 2.3 | "Activate in a workspace…" (opens Activate dialog, shown while some workspace does not run it) | release page | :309 | no (activating) |
| 2.4 | "Retire…" (confirm "Retire <name> <version>?"), "Bring back" (undo a retirement), "Delete…" (confirm "Delete <name> <version>?") | release page | :314-351 | no |
| 2.5 | Pills "Immutable release", "Retired", "Run by no workspace", "Runs this release"; notices "Retired", "Historical release" | release page | :256-277, 409, 512 | no |
| 2.6 | "Technical details": Release ID and Content hash with "Copy" | release page | :368-395 | no |
| 2.7 | "Release history" › "Changes in this release": "Compare with" picker (an earlier release; "No earlier release"), table of semantic changes (Kind, Path, Before, After), "No semantic changes: ... define the same model.", notice "Comparison unavailable" | release page | :417-490; model-admin/ModelDiff.tsx:39-50 | no |
| 2.8 | "Activation check": per workspace, whether its stored data would fit ("Checking each workspace's stored data…") | release page | :493-512 | no |
| 2.9 | Install dialog "Install and activate" (from the editor, see 6) | editor | model-editor/InstallDialog.tsx | no |

## 3. Activating into a workspace and migrating

| # | Action | Where | File:line | Ref |
| --- | --- | --- | --- | --- |
| 3.1 | Activate dialog (eyebrow "Workspace model"): "Workspace" picker, fieldset "Release", check results "Compatible with <ws>'s data" / "A migration is needed" / "A different model" / "A consumer API needs a higher contract version" / "Could not be checked" / "Not activated" | Change model… or Activate in a workspace… | model-admin/ActivateDialog.tsx:186-344 | no |
| 3.2 | Migration page: preview, review items by outcome with a choice per item: "Became <name>" per candidate or "Not kept" ("Its records and their relationships are removed." / "Its values are removed."); "Cancel the preview", "Preview again", "Back to the proposal", "Open the change set"; notices "Preview cancelled", "Not migrated", "Something went wrong" | after activation needing migration | model-admin/MigrationPage.tsx:102-126, 358-660; MigrationRows.tsx | no |
| 3.3 | Conflict screen: a review that went stale ("MIGRATION_REVIEW_STALE") — notice with "Close" / "Preview again" | Migration page | MigrationPage.tsx:166-167, 264-266, 629-660 | no |
| 3.4 | Impact summary (what the activation changes) | Activate / Install / Apply dialogs | model-admin/ImpactSummary.tsx | no |
| 3.5 | "Edit model" on a workspace (opens the editor on the draft of the model the workspace runs; hidden without Model authoring, Model release and Browse, or for a retired workspace) | Settings › Workspaces › workspace; workspace ⋯ menu | workspaces/WorkspaceAdmin.tsx:584; workspaces/useEditModel.ts | no (needs a workspace running a release; yes on the reference's default workspace) |
| 3.6 | "Apply to <workspace>" / "Apply to this workspace…" (editor opened from a workspace: main action, replaces Install) with notices "Not valid", "Nothing to apply yet", "Some records must move first", "Your records stay as they are", "Not applied"; "Applying…" | editor bar | model-editor/ApplyDialog.tsx:165-275, ME:988 | no |
| 3.7 | Workspace page shows applications of the workspace's own model and "<model> · schema N" | Workspaces | WorkspaceAdmin.tsx:764, 795-850 | yes |
| 3.8 | "Not in this model" screen when a bookmark names an application/collection/type the workspace's model lacks | shell | workspaces/NotInModel.tsx | yes |

## 4. The model editor frame (ME)

Layout: header bar; left pane (optional "Source" pane when the draft came from a workbook, then "Model" pane with tabs "Model" and "Consumer APIs"); centre (selected element / preview / layout editor / column / list / matrix / consumer API); bottom drawer "Issues and history" (or "Issues, history and dry run"), closed until opened, state remembered per browser (ME:BOTTOM_KEY ~l.95, drawer ~l.857). Below 760px the panes become tabs "Source", "Model", <selected name>, "Issues N" (ME:1197-1204). Panes are resizable ("Resize the model pane", "Resize the source pane", ME:1221-1233).

| # | Action (UI words) | Where | File:line | Ref |
| --- | --- | --- | --- | --- |
| 4.1 | Draft facts: "About this draft" (base release, "A new model", "The draft's version: one more with every step", "Saved as you go: closing keeps the draft and its proposals.", validity "N errors"/"N warnings"/"Valid") | header | ME:907-965 | yes |
| 4.2 | Rename the draft (title is editable text, "Model draft") | header | ME:907 (PageHeader title) / EditableText | yes |
| 4.3 | "Undo" / "Redo" buttons (icon buttons "Undo the last step", "Redo" on phone) | header | ME:~975-1025 | yes |
| 4.4 | "JSON" link ("Open as JSON" on phone) to the JSON editor | header | ME:~1020, 994 | yes |
| 4.5 | "Install and activate…" | header / "More actions" menu | ME:~1036, 995; InstallDialog.tsx | no |
| 4.6 | "Apply to <ws>" (primary, replaces 4.5 when opened from a workspace) | header | ME:~1030 | no |
| 4.7 | "Load into a change set…" (only with a workbook source) | header / More actions | ME:1000; LoadDialog.tsx | no |
| 4.8 | "Add a workbook…" / "Upload a newer workbook…" | More actions | ME:514, 1005; AddWorkbookDialog.tsx | yes |
| 4.9 | "Propose again…" (only when a workbook is profiled) | More actions | ME:582; ProposeDialog.tsx | yes (ai-later: no, it is the 0.10 inference) |
| 4.10 | "Close" (returns to the models, the workspace or the AI journey it was opened from) | header / More actions | ME:570-572, 993 | yes |
| 4.11 | "Delete draft…" (confirm "Delete this draft?"; "This removes only the editable draft. Installed releases are not changed.") | More actions | ME:576-580; model-admin/DeleteDraftDialog.tsx:39 | yes |
| 4.12 | Add menu "Add to the model" (+ icon, tooltip "Add"): Application…, Object type…, Attribute type…, Relation type…, Navigation group… (see 5.1); on the Consumer APIs tab "Add a consumer API" | left pane header | ME:645-660; OP:561-630 | yes |
| 4.13 | Empty draft message "The draft is empty. Add an application to start." | Model tab | ME:667 | yes |
| 4.14 | Dialog for every operation: form from `fields`, "Not applied" error notice, confirm-style for removals; preview beside the form for matrices | OperationDialog | model-editor/OperationDialog.tsx:100-266 | yes |
| 4.15 | Keyboard: in the model pane Up/Down/Home/End move, Enter or Space select, Right/Left unfold/fold a section, Shift+F10 or the context-menu key opens the operations menu of the selected row | Model pane | MP:278-297 | yes |
| 4.16 | Phone: tab bar replaces the panes; drags are off (`canDrag={!phone}`), menus do everything | editor | ME:1197, 673 | yes |

## 5. Model pane tree (MP) and what each element offers

Tree rows (MP:83-159): each application (name), under it its navigation groups (collapsible, MP:108) and the types listed, nested by containment hierarchy (MP:94); then sections "Relation types" (containment ones shown "<name> (containment)", MP:128-137), "Attribute types" (MP:145), and the row "Relationship matrix" (MP:159). Selecting a row opens its panel in the centre (EP).

### 5.1 Draft level (Add menu)
| Item | Fields in the dialog | OP line |
| --- | --- | --- |
| "Application…" (Add an application) | name | 564 |
| "Object type…" (Add an object type) | Application, Name, Plural name ("Optional; the name with an s when left empty"), Stands ("At the top level" / "Under <type>"), Containment relation ("A new containment relation" or an existing one), Relation name (from the parent), Reverse name (from the child) | 581, 285-345 |
| "Attribute type…" | Name, Value type, Features (Searchable, Filterable, Sortable, Unique) | 591, 353-365 |
| "Relation type…" | names (key/reverse) | 607 |
| "Navigation group…" | Application, Label, "Folded when the sidebar opens" | 620, 372-388 |

### 5.2 Application (selection "application", EP:485-): header with rename in place, facts "N object types", "N navigation groups", ⋯ menu
| Item | OP/EP line | Notes |
| --- | --- | --- |
| Rename… (also inline rename of the title) | OP:632; EP:491 | label only; key stays |
| Change key… | OP:643 | until released |
| Add an object type… (button "Object type") | OP:652; EP:~548 | |
| List an existing type… (button) | OP:673 | puts a type of another application into this one's navigation |
| Add a relation matrix… (button "Relation matrix") | OP:660; EP:~575 | see 6.4 |
| Add a navigation group… | OP:699 | |
| Remove application | OP:706 (confirm) | |
Tables on the panel: "Object types" (Type, Stands, Attributes, Relations, State), "Views" (View, Kind = Table / Tree / Relation matrix / Mapping grid, Shows, State; EP:110-113, 558-590), "Navigation groups" (Group, Collections, Starts = Open/Folded; EP:597-662). Icons and colours of applications/types are shown (HueTile) but there is no editor for them in the UI (not found). Navigation: only navigation groups (label, folded or open, order, which collections they hold); there is no "navigation bar" editor beyond that.

### 5.3 Navigation group (EP:597-662, OP:1477-1540)
| Item | OP |
| --- | --- |
| Rename… (also inline "Label" cell) | 1477 |
| Start unfolded / Start folded (also inline "Starts" cell Open/Folded) | 1487 |
| Change key… | 1501 |
| Move up / Move down (order of groups) | 1511, 1521 |
| Remove group | 1531 |
| Move to group… (on a type: "Place <type> in a navigation group": Application, Group) | 805 |

### 5.4 Object type (selection "type", EP:240-480)
Header: type tile, name (inline rename), key facts ("Key fixed: released"/"Key editable until released"), buttons "Preview" (opens 6.1) and ⋯ menu; line "in <apps>" / "in no application"; tabs "Attributes (N)" and "Relations (N)".
| Item (menu label) | OP | Notes |
| --- | --- | --- |
| Rename… | 766 | |
| Change key… | 788 | draftOnly |
| Move to… (Move to dialog, see 8) | 797 | also by drag and drop |
| Move to group… | 805 | navigation group |
| Stop listing in this application | 756 | from an application row |
| New attribute… (button "New attribute") | 852 | creates and attaches an attribute type |
| Attach an existing attribute… (button) | 873 | |
| Allow a relation… (button) | 903 | |
| Split… | 912 | "Attributes that move to it", "Relation name (from <type>)" |
| Merge into… | 953 | "Into" |
| Remove type | 972 (confirm) | |
Attributes tab (EditorTable, columns Attribute, Value type, Required, Unique, Read-only, Shared with, State; EP:300-400). Inline edits (EditableCell, `model-editor/EditableCell.tsx`; click the value, choose/enter, saved as a step): name, Value type, Required (Yes/No), Unique (Yes/No), Read-only (Yes/No). Rows are draggable (grip icon; "Drag onto a type in the model pane to move it", EP:287-317). Relations tab: columns Relation, Cardinality (inline), Required (inline; "Containment" for containment), Which records (inline; opens candidates dialog), State; "Open the relationship matrix" button (EP:470-480).

### 5.5 Attribute on a type (row menu, OP:983-1190)
Rename…, Change key… (1005), Move to… (1014, also drag), Make required / Make optional (1022), Make read-only / Make editable (1037), Make unique / Allow repeated values (1052), Value type… (1066), Turn into a list type… (1078; "Relation name (from <type>)", "Which records may be chosen"), Move up / Move down (field order, 1144/1161), Detach from <type> (1180).

### 5.6 Attribute type (selection "attributeType", EP:778-870, OP:1191-1280)
Facts: value type; table "Attached to" (Type, Required, Read-only inline; State). Menu: Rename…, Change key…, Features… (Searchable, Filterable, Sortable, Unique), Value type…, Attach to a type…, Remove attribute type. Value types (OP:168): Text, Long text, Whole number, Decimal number, Yes or no, Date, Date and time, JSON.
Not found in the UI: default values, validity/effective-period (valid from/to) settings on attributes (the strings validFrom/validTo appear only as consumer-API roles, consumer.ts:26), formats/lengths, choice lists as a value type (a "list type" is a relation to a type, 5.5).

### 5.7 Relation type (selection "relationType", EP:679-776, OP:1284-1380)
Facts: key, reverse key ("Reverse key"); section "Names" (editable name, "Reverse name"); table "Allowed between" (From, To, Cardinality, Required, Which records, State). Menu: Rename…, Change keys…, Allow between two types… (From, To), Remove relation type.
### 5.8 Relation (a pair, OP:1383-1470)
Cardinality and required… (Many to one, One to many, One to one, Many to many), Make required / Make optional, Which records may be chosen… (criteria editor "Criteria" per end: `model-editor/CandidatesField.tsx`, `candidates.ts`), Remove relation. "Allow a relation…" form: To, Relation type (grouped "Already reaching <type>" / "Other relation types", or "A new relation type"), Name (from <type>), Reverse name, Cardinality, Required (OP:392-500).
Ownership/containment: a relation type marked containment is how hierarchy is expressed (new type "Stands … Under <type>", containment relation chosen or created). A separate "one per" rule (`uniquePer`) is shown in hints (OP:~228) but no editor was found.

### 5.9 Relationship matrix (selection "matrix", RelationshipMatrix.tsx, ME:793)
Heading "Relationship matrix", "Which relation types may join which types · rows are the “from” end"; grid of all types, each cell lists relations ("contains" for containment, shorthand 1:1, 1:n, n:1, n:n); arrow keys move, Enter/click selects a pair (aria "Selected pair"); side panel lists the pair's relations with menus and offers to allow one; resizable "Resize the selected pair panel" (RelationshipMatrix.tsx:65-181).

## 6. Views and layouts

### 6.1 Preview (TP; ME:757-777; buttons "Preview" on a type)
Centre shows the type's real "Record page" and "Table" tabs rendered from the draft over live records of a workspace; band choices "Workspace: <label>" picker, "Record: <name>" picker and "Show an empty record"; message "The draft has N issues, so it cannot be previewed" with "Show issues"; buttons "Edit layout", "Back to definition". Controls are shown disabled. (TP:193-440) Ref: yes (reads the active model's records through a workspace).
### 6.2 Layout editor ("Edit layout" band "Layout editor", TP; layout.ts)
Tabs "Record page" and "Table". Record page: regions "Main" and "Side"; each Panel is a frame with a grip and a menu "Layout of panel <title>": Move up, Move down, Move to <other region>, Hide / Show ("It stays on the page, hidden"), Rename…, Columns… (list panels), Sort… , Add fields…, Remove from page ("Undo puts it back") (TP:578-645; LY:222-340). Each Field frame: Move up, Move down, Move to <panel>, Remove from panel (TP:655-682). "New field group" button (Title, Fields; LY:235-263), "Declare its page" button when the type has no page ("The model declares no detail page for <type>…"; TP:~318). Fields shown with "No value" placeholders. Drag by grip: panel to a region or onto another panel, field onto a field or panel (TP:471-487, 700-780, `dropOnField`, `dropOnPanel`).
Table tab: per table view, tool buttons "Columns", "Filters" and "Default sort: <field> ↑/↓" (dialogs `tableColumnsSpec`, `tableFiltersSpec`, `tableSortSpec`, LY:387-448; fields Columns, Filters, "Sorted by", "Descending"); column frames with menu Move left, Move right, Remove column, drag to reorder (TP:883-920, 126-135). Empty table: "No records yet. The table will show …"; "The draft declares no table view for <plural>." No density editor, no tree-view or mapping-grid editor, no view creation for tables or trees found (only relation matrix views are created in the UI).
### 6.3 View (row in an application's Views table, menu "Operations for the view <name>")
Rename… (OP:717, a `setViewProperty` name), for relation matrix: Change… (736), Remove relation matrix (746).
### 6.4 Relation matrix view (matrixView.ts; form OP:496-558)
"Add a relation matrix…" form: Rows (types connected to another type under a parent), Each cell shows, Columns ("One column per record of a type the cell's records sit under"), Column heading, Fields in a cell (ordered), Row columns (ordered), "What people can do in a cell" (checkboxes), Name; preview pane beside it (`MatrixPreviewPane.tsx`).

## 7. Consumer APIs (CA; left pane tab "Consumer APIs")
Editable in the UI: yes. Add menu: "Consumer API…" (Key, Types to expose). Selected API panel (CA:930-975): facts "Contract version N", "Compatible with what consumers read" / "Needs contract version N+1" / "Checked once the draft is valid"; tabs "Types and related", "Fields (N)", "Operations", "Filters (N)", "Schema", "Message example". API menu (OP:1578-1935): Rename…, Describe…, Raise contract version to N+1, Change key…, Edit as JSON…, Remove consumer API; item menus: Expose a type…, Add field…, Parent, path and hierarchy…, Add related…, Add list…, Add XREF rule…, Add a match through a related block…, Add custom event…, Add filter…, Move up/Move down, Sources… (first non-empty), Matches on…, Fields…, Edit as JSON…, Remove. Operations tab toggles "Get by ID", xref, resolve, per type (CA:542-563). Tables: Public name, Output name, Via, Serves, Role, Served type, Default, Within the filter, Sorted by, weight "Exact"/"Contains", "Also match through", "First of", "Prefers", Key/Types/Changes/Watches, Name/Verb/What it reads/Matches on/Options. Filter options include "Score only matching items" (OP:1873). Ref: yes.

## 8. Drag and drop, hierarchy, keyboard alternatives (all interactions of that kind)
| # | Drag (source -> target) | Result | Keyboard / menu alternative | File:line | Ref |
| --- | --- | --- | --- | --- | --- |
| 8.1 | Type row in the model pane -> another type | opens "Move <type> to…" with target "Under <type>" (re-parents with its subtree) | Type menu "Move to…" (OP:797) | MP:351-380; ME:457-476 | yes |
| 8.2 | Type row -> an application row | opens Move to… to that application's top level ("At the top level"); another application's moves the type with the types under it | same | MP:363; ME:457 | yes |
| 8.3 | Type row -> beside the tree ("Dropping a type here puts it at the top level") | top level | same | MP:64 | yes |
| 8.4 | Attribute row (grip, table of attributes) -> a type row in the pane | opens Move to… for the attribute ("Its columns in views and place in panels move with it") | Attribute menu "Move to…" (OP:1014) | EP:287-317; ME:457-465 | yes |
| 8.5 | Source-file column (workbook pane) -> a type row, or beside the tree | opens "Map to…" with the target chosen | Column menu / button "Map to…" | SourcePane.tsx:331-333, 585-587; MP:42; ME:637-641 | yes |
| 8.6 | Drag near the top/bottom edge of the pane | scrolls the pane | n/a | MP:12-14 | yes |
| 8.7 | Panel/field/column frames in the layout editor (grip, "Drag to move; the menu moves it by keyboard") | reorder, change region, change panel, reorder columns | Frame menu: Move up/down/left/right, Move to <region/panel> | TP:471-487, 700-780, 883-920; LY:32-130 | yes |
| 8.8 | Navigation groups and attributes ordering | no drag; "Move up"/"Move down" menu items | group menu OP:1511-1530; attribute OP:1144-1170; consumer item OP:1938-1950 | | yes |
Move to… dialog (MoveToDialog.tsx:172-259): "Move <name> to…", "Find a target" combobox (type, Up/Down, Enter), "Take it out of" (when a type is listed in several applications), "Containment relation" ("A new containment relation" or existing), notices "Not moved". Phone: no drags.
Hierarchies: expressed only via containment relation types; arranged by 5.1 object type "Stands", Move to…, Split…, Merge into…, and the Relationship matrix. No separate hierarchy-level or tree-view editor was found.

## 9. Conflicts and resolution screens (every one found)
| # | Screen | Words | File:line | Ref |
| --- | --- | --- | --- | --- |
| 9.1 | Editor: a step refused because someone else moved the draft on | notice "Another change came first": "Your change was not applied: the draft changed since you opened it. Applied since: … The model below shows the newer version."; buttons "Apply mine again" / "Discard mine" | ME:1121-1150, 308-330 | yes (needs two editors) |
| 9.2 | JSON view: saving against a newer draft version | "A newer draft version exists. Your local JSON is preserved." with "Reload saved version" and "Copy local JSON" | model-admin/ModelDraftEditor.tsx:235-247 | yes |
| 9.3 | Migration review gone stale | Migration page stale notice (refused at confirmation or found by the execution) with "Close"/"Preview again" | MigrationPage.tsx:264-266, 629-660 | no |
| 9.4 | Undo of a step others depend on | dialog "Undo the steps that depend on it too?" (dependants) | ME:1266 | yes |
| 9.5 | Profile key belongs to another model / key conflict (workbook) | `ProfileKeyConflict.tsx`; LoadDialog "The profile's key belongs to another model" with use-existing key | model-editor/ProfileKeyConflict.tsx; LoadDialog.tsx:243; IssuesAndHistory "onUseProfileKey" | yes |
| 9.6 | Draft vs. a newer release: the install dialog compares with the base release ("Comparing with the base release"), classification "Compatible with stored data" / "Activation needs a migration" / "Checked when activated"; the base release of the draft is shown in "About this draft". No merge/rebase of a draft onto a newer release was found: the way is "Create draft from release" again (not found as an automatic resolution). | InstallDialog.tsx:374-430; ActivateDialog.tsx | no |
| 9.7 | Apply: "Some records must move first" (data does not fit; offers the move) | ApplyDialog.tsx:221 | no |
| 9.8 | Contract conflict: "A consumer API needs a higher contract version" / install "Activation is refused while a consumer API needs a higher contract version." | ActivateDialog.tsx:314; InstallDialog.tsx:545-560 | no |
| 9.9 | Mapping in Copy and move: "The mapping names other releases than the workspaces run" with "Use the releases the workspaces run" | moves/MoveEditor.tsx:517-534 | no |

## 10. Issues, history, undo (IssuesAndHistory.tsx; history.ts)
| # | Action | Words | Line | Ref |
| --- | --- | --- | --- | --- |
| 10.1 | Drawer tab "Issues (N)": diagnostics list, each selects the element; "No issues: the draft is valid and can be installed."; fix actions (e.g. remove a panel naming a removed field; "Use as the profile's key") | IssuesAndHistory.tsx:78-127 | yes |
| 10.2 | Drawer tab "History": steps newest first (state "Applied", "Undone", "JSON edit"), per-step "Undo", "Earlier steps" (load more), "No steps yet." | :132-170 | yes |
| 10.3 | Undo/Redo (header), undoing a step restores key-follow (`followKeyChange`) | history.ts | yes |
| 10.4 | Dry run tab (with a workbook) "Dry run · <state>": figures per type, rows refused (dialog "Rows of <sheet> refused for <type>") | DryRunPanel.tsx | yes |
| 10.5 | Compare with the active release: only on the Install/Apply dialogs ("changes" lines) and the release page (2.7); not a standing compare view in the editor | InstallDialog.tsx:394; ApplyDialog.tsx | no |

## 11. JSON
| # | Action | Words | File:line | Ref |
| --- | --- | --- | --- | --- |
| 11.1 | "JSON" (editor header) / "Open as JSON" (More actions) -> JSON workbench of the draft | ME:994, 513 | yes |
| 11.2 | JSON page: "Draft name", "JSON model" text area, "JSON syntax: …", "Authoritative validation" (diagnostics with go-to-path), model summary, buttons "Save draft", "Compile and compare", "Export JSON", panel "Canonical model" ("Ready for review"/"Invalid", model hash), semantic diff, "Install immutable release…" (confirm "Install this model release?"), "Open in editor", "Delete draft" | model-admin/ModelDraftEditor.tsx:195-316 | yes except install (no) |
| 11.3 | Import JSON when creating a draft ("Import JSON", "Or choose a JSON file") | CreateDraftDialog.tsx:190-222 | yes |
| 11.4 | "Export JSON" of a release | ModelReleaseDetail.tsx:299 | no |
| 11.5 | Consumer API "Edit as JSON…" and item "Edit as JSON…" (a `json` field in the dialog) | OP:1920, 2019 | yes |
| 11.6 | JSON edits in history appear as "JSON edit" | IssuesAndHistory.tsx:24 | yes |

## 12. Draft from a workbook (source pane; ModelEditor with `hasSource`)
| # | Action | Words | File:line | Ref |
| --- | --- | --- | --- | --- |
| 12.1 | New from a workbook / "Add a workbook…" / "Upload a newer workbook…" (dialog fields "Workbook" - "An XLSX workbook or a CSV file", "Compare with the records of") | AddWorkbookDialog.tsx:62-91 | yes |
| 12.2 | Propose choices (also in "Propose again"): "A new application", "A new model", "Additions to the model", "Nothing: I will map it by hand"; field "Application name"; progress "Proposing from the workbook" ("Editing is paused until the proposals are applied") | ProposeFields.tsx:46-95; ProposeDialog.tsx:31; ProposingProgress.tsx | yes |
| 12.3 | Source pane: file name, tabs per sheet ("<sheet> · rows"), "Columns"/"Lists" of a sheet; hint "Drag a column onto the model, or use Map to… in its menu."; sheet menu "Ignore this sheet"; import profile "Profile key", "Profile name" (editable) | SourcePane.tsx:106-306, 529-539 | yes |
| 12.4 | Column panel: header "Column X of <sheet>", status pill, buttons "Map to…", "Ignore"; facts "Feeds", "Read as", "Matched by", "Split on" (select "Do not split" + delimiters), "Not found", "Value map" ("Add a value map…"/"Edit value map…"), "Key" ("Use as the key of the rows" / "Not the key: … is not unique"), "Dry run"; "Statistics" (Filled, Values read as, Most frequent values, Placeholders, Delimiters, Shares values with) | ColumnPanel.tsx:111-345 | yes |
| 12.5 | Map to… dialog: "What the column holds" (attribute / parent / relation), "Attribute name", "Value type" (proposed from cells), "Split a cell on", "Matched by" ("The record's name", "Its name"…), "Which <type>", "The column naming it", "Create the … records a cell names that do not exist", "The record a Y relates the row to" | MapColumnDialog.tsx:211-424 | yes |
| 12.6 | Value map dialog: "Text in the file" -> "Becomes", remove row | ValueMapDialog.tsx:95-160 | yes |
| 12.7 | List panel (lists found in a sheet): "Adjust list…" (dialog "Header row", "Last row", "First column", "Last column", range), "Load" / drop; facts "Under", "Cells", "Note", "Loads"; notice "Not loaded" | ListPanel.tsx:91-181; AdjustListDialog.tsx:152-192 | yes |
| 12.8 | Evidence / "why proposed": "Proposed" pill on elements still as proposed; centre note says why, with alternatives to pick ("Proposed because", `ProposedBecause.tsx`) | ProposedBecause.tsx; ME:560-566 | yes (inference 0.10 A6; the 0.16 AI-based design is ai-later: `ai-tasks/DesignModel.tsx`, `ai-tasks/ModelProposal.tsx`) |
| 12.9 | Load into a change set dialog: "Load <file> into a change set": "Open a change set", "Load the rows" | LoadDialog.tsx:178-243 | no |
| 12.10 | AI model design (ai-later): "DesignModel" and "ModelProposal" pages under Settings › AI tasks | ai-tasks/DesignModel.tsx, ModelProposal.tsx | ai-later |

## 13. Install and activate dialog (InstallDialog.tsx)
"Install and activate": fields "Release key", "Version" (hint base release), "Name"; fieldset "Activate into": "An existing workspace" (picker, with "Other model" warning) or "A new workspace" (NewWorkspaceFields); "Comparing with the base release", change lines ("No model element changes."), notices "Valid"/"Not valid" (with "Show issues"), "A new workspace", "Compatible with stored data", "Activation needs a migration", "Checked when activated"; contract table "Compatible"; outcome "Installed, not active"; error "Not installed". Ref: no.

## 14. Workspaces' models and model mappings (Settings › Copy and move)
| # | Action | Words | File:line | Ref |
| --- | --- | --- | --- | --- |
| 14.1 | Moves page: title "Copy and move", eyebrow "Data operations", button "New copy or move…", section "Mappings" (Mapping, From model, To model, Version, Updated; "Load more mappings"), section "Recent copies and moves" (Workspaces, Operation Move/Copy, State, Change sets, Created) | moves/MovesPage.tsx:58-182 | no (needs two models/workspaces) |
| 14.2 | New dialog "New copy or move": "From workspace", "To workspace", fieldset "Mapping": "A new mapping, proposed" or an existing one, "Name of the new mapping"; "Open the editor" | NewMoveDialog.tsx:135-212 | no |
| 14.3 | Mapping editor: tabs "Mapping", "Source", "Target", "Not <copied/moved>"; top: "From", "To", "Mapping" with version and "Change…" (choose another mapping), mode radio group "Copy or move", Undo, Redo; row per source type "<source> to <target>" with a select ("Map <type> to…" for unmapped types), per attribute a select of target attributes or not mapped, "Set a default…" / "Change…" / "Clear" default value, relationships (rows per relation, with direction and alternatives) | moves/MoveEditor.tsx:340-460, 738-747; MappingPane.tsx:53-190, 271-283; mappingRows.ts | no |
| 14.4 | Evidence and alternatives: side note "Why this step" — summary, evidence lines (`evidenceText`), alternatives "<X> becomes <Y> instead" selectable; "This row is yours: set by hand, or nothing proposed it. Undo brings back what was proposed." Scores are in the data (`types/moves.ts:122-126`) but no score is shown in the UI (not found). | MoveEditor.tsx:631-655; mappingRows.ts:367-404 | no |
| 14.5 | Dry run of every item: figures "Create", "Update", "Relationships carried", "Relationships dropped"; notices "The dry run waits for the mapping", "The dry run did not run" ("Dry run again"); report "Items that cannot …" by reason, "Values not carried" table (Type, Field, Records, Code), "Open the mapping" | MoveEditor.tsx:466-554, 860-900; MoveReport.tsx | no |
| 14.6 | Selection: "Dry run this selection" dialog — "Records" choice, "Type of the record", "The record" | moves/SelectionDialog.tsx:91-181 | no |
| 14.7 | Start copy/move: "<Move/Copy> N records into workspace <ws>", "Name of the change set of workspace <ws>" | moves/StartMoveDialog.tsx:42-85 | no |
| 14.8 | "Copy or move data…" on a workspace (starts 14.2 from the workspace) | WorkspaceAdmin.tsx:590 | no |
| 14.9 | Read-only notices: "Copying and moving are read-only here", "This editor reads only" | MovesPage.tsx:70; MoveEditor.tsx:510 | n/a |

## 15. Not found in the UI (checked, so the docs must not promise them)
Editing icons or colours of applications/types/groups; default values or valid-from/valid-to on attributes; creating table or tree views or editing tree/mapping-grid views (only table columns/filters/default sort in the layout editor, and relation-matrix create/change/remove); density; translations/labels beyond the single name/plural/label per element; a rebase/merge of a draft onto a newer release; a standing "compare draft with active release" view in the editor (only inside Install/Apply and on the release page); mapping scores displayed.

## Counts (rows or constructs listed)
1 Models list and model tabs: 10; 2 Releases: 9; 3 Activate/migrate/workspace: 8; 4 Editor frame: 16; 5 Model pane elements: draft 5 adds, application 7 ops, group 6, type 11 ops plus 5 inline edits, attribute 11, attribute type 5 ops, relation type 4, relation 5, matrix 1 (about 70 operations); 6 Views and layout: about 25 (preview 4, layout panel 9, field 4, table 7, view 3, matrix form 8); 7 Consumer APIs: about 30 operations, 6 tabs; 8 Drag/keyboard: 8 drag or arrangement rows plus Move to dialog; 9 Conflicts: 9; 10 Issues/history: 5; 11 JSON: 6; 12 Workbook: 10 (+1 ai-later); 13 Install: 1; 14 Mappings: 9. ai-later items: 1 (the AI task pages `ai-tasks/DesignModel.tsx`, `ModelProposal.tsx`; not read in detail).

## Not established
Whether the reference instance has the model-admin capabilities, an installed release or a second workspace (Ref column is by code only); exact line numbers marked with "~" were approximated from grep; permissions per role (who sees which button) beyond `useEditModel`; contents of `ai-tasks/*` and `MatrixPreviewPane`, `ProfileKeyConflict`, `DryRunPanel` internals were not read in full; inline-edit coverage of every table cell was read for the type, group, relation and attribute-type tables only.
