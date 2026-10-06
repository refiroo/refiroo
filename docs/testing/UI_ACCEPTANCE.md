# UI acceptance

**Package:** Base 0.7 WP-13C, 2026-09-24. **Inputs:** the [coverage map](COVERAGE_MAP.md) (C-UI-*,
C-MAP-UI, C-DR-PIN) and the [execution guide](EXECUTION_GUIDE.md). **Consumers:** every package that
adds or materially changes a user-visible surface, and WP-9.

This document answers two questions: *which existing screen must my new UI look and behave like?* and
*which states of a changed surface have browser evidence, and which do not?* Accessibility checks and
screenshot equality supplement design review; neither establishes that a layout is good. An
uninspected appearance is unverified, not passed.

## 1. Reference patterns

Reuse the named reference's structure, classes and tokens. Introduce a shared component only when a
repeated gap is demonstrated on two surfaces; do not add a second design system or redesign a surface
to fit a new control.

| Pattern | Reference (0.6, retained in 0.7) | Structure to reuse |
| --- | --- | --- |
| Dialog | `ui/Modal` as used by `features/objects/ObjectFormDialog.tsx` | `Modal` (title, optional `eyebrow`, `busy`, `dirty`, `size="compact"` for short forms) wrapping one `<form>`; `Notice` for the error; `.dialog-actions` with Cancel (`secondary`) then the submit (`primary`). Never a hand-rolled `.dialog-backdrop`. |
| Confirmation | `ui/ConfirmDialog` (change set publish/discard, deletion) | States the consequence; destructive action uses `danger`/`danger-ghost`. |
| Field | `ui/AttributeField`, `ui/ObjectLookup`, label-wrapped `<input>/<select>` in `ObjectFormDialog` | Visible `<label>` text wraps the control; required state from the model; typed input types. |
| Actions | Page header action (`ui/PageHeader` `actions`, one `.primary`), `RecordActionMenu`/`ui/ActionMenu`, `ui/ControlPopover` | One primary action per surface; secondary actions in a menu or `<details>` disclosure; icon buttons carry an accessible name. |
| Page surface | `features/objects/CollectionView.tsx` | `ui/PageHeader` (title on the 30px step, description, actions; 0.9 U2); `.surface` (card tokens, U-D8) with toolbar and a continuous list. |
| Shell and data context (0.9 U2) | `app/AppShell.tsx`, `app/DataContextBand.tsx` | The top bar (mark, workspace switcher, application tabs, the **Settings** link and the **Account** popover; U3), the rail with the explorer, and the band naming the data: Live (green `ui/StatusPill`), a change set (amber band with its own bar) or a publication (violet). A context's reports go below the band (`ui/ContextBandSlot`). Status is a `StatusPill` (marker and text); a value is plain text. Colours come from the semantic roles in `styles/tokens.css`, never from primitives. |
| Settings layout (0.9 U3) | `app/SettingsShell.tsx`, `features/settings/DeploymentPage.tsx`, `features/workspaces/WorkspaceAdmin.tsx` | Own frame without workspace or data context: top bar "{product} / Settings" with **Back to applications** and the account; rail `nav aria-label="Settings"` with group headings and `aria-current` links, in the navigation drawer below 760px (a **Settings: {page}** bar opens it). Each page is `ui/SettingsLayout` (group as the eyebrow, the application pages' width) with ruled `ui/Section`s; facts in `ui/DescriptionList`; tables as a labelled, focusable group that stacks row by row below 760px; loading as `ui/Skeleton`; nothing to list as `ui/EmptyState` with its action; form fields as `ui/FormField`; a completed write confirmed by `ui/Toast`, errors inline. Workspaces and Model: the catalogue beside the selected entry's card, each entry at its own address; below 760px they take turns, with a back button (U-D10 as revised). |
| Continuous list (0.8 S5) | `ui/ScrollWindow` in `ui/ObjectTable` (collection lens) | Labelled scrolling region with a sticky header; quiet start and end markers, an edge loading marker only while waiting; a proportional window scrollbar when the window holds part of the list; footer with the visible range, page field, start/end buttons and, where the list seeks, a **Go to** field. Rows carry `aria-rowindex` and the table `aria-rowcount`. |
| Tree (0.8 S6) | `features/objects/RecordTree` in the explorer's **Browse records** | `role="tree"` with one tab stop. Each object type's records form a group headed by an item naming the type and its count (opening its collection); the rows scroll in a bounded `ui/ScrollWindow` whose viewport is the named `group` (a tab stop only while it scrolls, presentational edge markers, announcements through the tree's one live region). `aria-level`, `aria-setsize` and `aria-posinset` from totals; Up/Down cross window edges by loading, Right/Left expand, enter, collapse and return, Home/End, Ctrl+Home/End within a group, Enter opens. |
| Table sort (0.8 S4R3) | Record panel header sort: `CollectionPanelTable` over `ui/ObjectTable`, through `ui/TableSort` | Every data column sorts from its header (quiet icon on hover/focus drawn in the header padding, accent arrow when sorted, toggle on activation, `aria-sort`, name stating the order, polite announcement); only Actions, the computed path, JSON and unrecorded timestamps do not. Every list with sort fields carries the same icon-only `ui/ActionMenu` Sort menu in its toolbar (radio fields plus direction, tooltip). No labelled sort select or popover. |
| Load failure | `ui/InlineError` (a `Notice` titled “Could not load this content” with **Retry**) | Replaces only the failed content; shell, header and previously loaded data stay; Retry repeats the exact request. |
| Empty state | Collection empty row, `.empty-panel` in `ChangeSets` | Says whether nothing exists or nothing matches the current search/filter. |
| Notice | `ui/Notice` tones `info`/`warning`/`error` | Title plus a sentence stating what happened and the safe next action; `focusOnMount` for a failure the user must act on. |
| Disclosure | `<details>` in `ChangeSets` (More change set actions) and `ModelReleaseDetail` (Technical details); `ui/Tabs`; `ui/NavigationDrawer` | Native keyboard operation; identifiers and technical metadata stay collapsed by default. |
| Narrow layout | `styles/responsive.css` at ≤ 720px; 390×844 is the checked phone width | No page-level horizontal scroll; wide tables scroll inside their labelled region; dialogs fit the viewport. |

## 2. Surfaces added or materially changed in 0.7

Navigation is given from a fresh isolated harness (`e2e/helpers/harness.mjs`). The state columns use:
**B** browser evidence (runner named in the last column), **C** component evidence only,
**—** not applicable (reason in the notes), **gap** applicable without evidence.

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | Shell: application tabs, model/schema version, Live / Change sets / Publications, settings menu, dark theme (redesign, 315e6f7); top bar, rail and data-context band to ADR-039 (0.9 U2) | any `/apps/<app>/…` | Shell and data context | C | B | — | B | — | — | B (context failure) | B | B | `wp9-navigation`, `wp9-change-sets`, `wp9-publications`, `App.test` “keeps transient context failures in the shell”, `DataContextBand.test` (three contexts), `SettingsMenu.test`, `tokens.test` (contrast), a11y dark pages, `change-set-editing-*` light and dark |
| S2 | Unified application browser: collections + record tree (WP-14) | sidebar; narrow: **Browse application** | Disclosure (drawer, tree) | C | B | — | B | — | — | C (`Explorer.test`) | B | B | `wp9-navigation`, `wp14-contextual-browser` |
| S3 | Collection lenses, scope banner, Filter popover (WP-14, redesign) | `/apps/rdm-systems/views/systems` → expand System 00 → System values collection | Page surface, `ControlPopover` | C | B | — | B | C (typed filter 422) | — | C (`CollectionView.test`) | B | B | `wp14-contextual-browser`, `wp9-navigation` UI-02 |
| S4 | Mapping lens grid (WP-8A/WP-14) | lens tab **System → Master mapping**; `/apps/rdm-master/views/master-to-system-mapping` | Page surface | C | B incl. filtered-empty | — | B | — | — | **B** | **B** | B (region focusable, row button) | `wp13c-ui-states`, `wp14-contextual-browser` |
| S5 | Mapping dialog: candidates, save/next, remove, conflict (WP-8B) | row **Map/Change** | Dialog | C | **B** incl. no-match, page two (WP-9) | C (`Saving…`) | **B** | C (server error notice; WP-10H: no removal for a required binding) | **B** (also a racing generic write, WP-9) | **B** | **B** | **B** (search focus, Escape restores focus, keyboard-only save) | `wp13c-ui-states`, `sc07-mapping-acceptance`, `MappingGridView.test` (26) |
| S6 | Contextual target creation (WP-8B) | mapping dialog → **Create new …** | Dialog (nested `ObjectFormDialog`) | — | — | — | **B** (WP-10F: create, select, save in both directions, live and change set) | C (no parent type in the chosen application) | — | B (lookup error + Retry shown) | gap | C | `wp13c-ui-states`, `MappingGridView.test` |
| S7 | Mapping in a named change set, inverse direction (WP-8B/WP-7) | `…/master-to-system-mapping?changeSetId=…` | as S4/S5 | — | **B** | — | **B** (live unchanged) | — | C | — | gap (wide only) | B | `wp13c-ui-states` |
| S8 | Change sets list and creation with model version (WP-7) | Change sets tab | Page surface, Dialog | C | B | C | **B** | **B** (WP-9: incompatible release lists the records, keeps the name, leaves no change set) | — | **B** | **B** (refused creation at 390px) | C | `wp13c-ui-states`, `sc15-model-version-acceptance`, `wp9-change-sets` |
| S9 | Draft bar, model mismatch notice, activation refusal (WP-7/WP-11) | open a draft pinned to a non-active release | Notice, Actions | C | **B** | C | B (`wp9-change-sets`; WP-9: the prepared draft after model activation) | **B** (Activate disabled with reason; WP-9 also after the active release moves on) | B (`wp9-change-sets`; WP-9 mapping-set divergence) | C (refresh warning) | **B** | C | `wp13c-ui-states`, `sc15-model-version-acceptance`, `sc07-mapping-acceptance`, `wp9-change-sets` |
| S10 | Change model version dialog (WP-7/WP-11) | change set bar → More change set actions → **Change model version** | Dialog (`compact`) | C | B | C | B | **B** (WP-9: incompatibility diagnostics, pin unchanged) | C | C | B | B (focus trap, dirty Escape) | `wp11-model-admin`, `sc15-model-version-acceptance`, `ChangeSets.test` |
| S11 | Workspace/page load failures (WP-11) | any context read failing | Load failure | — | — | — | B | B (unsupported historical schema: C) | — | **B** (change sets list), B (`wp9-navigation` panels) | C | C | `wp13c-ui-states`, `App.test` |
| S12 | Release detail: identity, Technical details, comparison baseline (WP-12) | Models → release | Page surface, Disclosure | C | B | — | B (copy) | C (unsupported baseline) | — | C | B | B | `wp12-release-identity`, `ModelReleaseDetail.test` |
| S13 | Models page alignment (315e6f7) | header **Models** | Page surface | C | B | — | B | C | C (version conflict) | C | C | C | visual/a11y gate pages (`model-workbench-*`), `ModelWorkbench.test` |
| S14 | Record header, breadcrumb, readable activity (redesign) | open any record | Page surface | C | B | — | B | — | B (`wp9-authoring`) | B | B | B | `wp9-navigation`, `wp9-authoring`, visual baselines |

Not applicable, with reasons: S4 has no pending/refused state of its own (writes happen in S5);
S6 load/empty belong to the nested form's lookups, shown under dependency failure; S7 load and failure
share S4's renderer and code path, so only the context difference (change set overlay, inverse direction) is
checked; S11 has no conflict state.

### Surfaces materially changed in 0.8 Track S

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Continuous lists: collection lens, record panels (with a name-default sort), relation panels (with search and sort), mapping lens, mapping candidates (S5) | any collection; a record's panels; mapping lens | Continuous list | C (`useCursorWindow.test`) | **B** (populated at 10,000 and 72 rows; empty from search: C) | B (edge marker while waiting: component only; not captured in a screenshot) | **B** (scroll both ways, scrollbar click and drag, page number, seek, Ctrl+Home/End, URL anchor reopen, in live, change-set and publication) | B (unknown seek value: InlineError, C) | — (read-only lists; writes keep their own conflict states) | **B** (edge read fails, window kept, Retry in place: `wp9-navigation`); C (`CollectionPanelTable.test`, `RelationsPanel.test`) | **B** (390px, no page overflow) | **B** (arrow keys across page boundaries, focus kept by row identity) | `s5-continuous-lists`, `s7-volume-acceptance`, `wp9-navigation`, `sc07-mapping-acceptance`; gates: `scrolling-list-tree` |
| T3 | Table sort: collection lens, record panels, relation panels (S4R3) | a collection's headers; a record's panels | Table sort | C (`ObjectTable.test`, `RelationsPanel.test`, `CollectionView.test`) | **B** (relation panels on a domain and a codelist; the schema 0.6 volume relation panel, declaring no sort, lists by name and sorts every header including Relationship) | — (a sort is one list read; its loading is T1's) | **B** (header toggles both ways, a never-flagged attribute (value name), record panel attribute sort, the toolbar menu for a field without a column, in live, change-set and publication; request, `aria-sort` and announcement checked) | C (live-only timestamps dropped in change sets and publications; path not sortable) | — (read-only) | as T1 | **B** (390px: relation header sort, the record panel's toolbar menu for its collapsed Sort order column, lens menu; no page overflow) | **B** (headers by Enter, menu opened and chosen by keyboard) | `s5-continuous-lists`, `wp9-navigation`; baselines `collection-table-*`, `record-detail-*`, `change-set-detail-light`, `change-set-editing-light` |
| T4 | Sidebar tree by parent (S6) | explorer **Browse records**, every application | Tree | C (`Explorer.test`: loading note, a failed group) | **B** (1,000 roots, a 2,000-child branch, two child types with one empty on a system; an empty codelist says **Nothing inside**; no matching search result: C) | C (a group's edge marker while waiting, as T1) | **B** (branches show exactly their own children and counts, the heavy branch scrolls end to end, an eight-level keyboard path opens its record, a heading opens its scoped collection, search shows ancestor paths, in live, change-set and publication) | — (read-only; nothing to refuse) | — (read-only; a refresh reloads groups in place) | C (`Explorer.test`: a failed group's error outside the tree, Retry in place) | **B** (390px drawer: touch expand, scroll past the first page, keyboard expand; no page overflow) | **B** (one tab stop; Up/Down across a window edge, Right/Left, Home/End, Ctrl+Home/End in a group, Enter) | `s6-sidebar-tree`, `s7-volume-acceptance`, `wp9-navigation` (incl. `ui03b-hierarchy`), `wp14-contextual-browser`; gates: `scrolling-list-tree` |
| T2 | Object picker: search field over a listbox (S5) | record form **Parent**; relation dialog **Object** | Field | C | **B** | — | **B** (keyboard choice across a page boundary) | C (required: hidden required input) | — | C (`ObjectLookup.test`) | **B** | **B** (combobox with `aria-activedescendant`, Enter chooses) | `s5-continuous-lists`, `wp9-authoring`, `wp13c-ui-states` |

Not applicable, with reasons: the lists hold no writes of their own, so they have no conflict state.
The S5 runner runs axe on the volume lens, the relation panel, the starter lens, the mapping lens
and the picker, and for T3 on the codelist record with its sorted record and relation panels. T3's
pending state is the list read T1 covers. T4 runs axe on the volume tree eight levels deep and the
starter master and systems trees. S7 added the gate scenarios: `test:a11y` and `test:visual` capture
T1 and T4 together (`scrolling-list-tree`, light and dark: the codelist lens mid-list with its window
scrollbar and footer beside a 60-codelist tree branch, focus inside it), and every baseline was
refreshed after inspection for S6's tree heading and the footer fields. The dark scenario found the
footer's page and **Go to** fields on the browser's light field colours (contrast below AA); they
now share the text-input treatment. `test:browser:s7` composes T1 and T4 in live, change-set and publication.

### Surfaces added or materially changed in 0.8 Track W

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W1 | Workspaces screen: catalogue including retired, detail, create, rename, set default, retire, reactivate (W4) | header **Workspaces**; `/workspaces/<key>` | Page surface (Models list-and-detail layout: S13), Dialog, Confirmation | C | **B** (one, two and a retired workspace; a catalogue is never empty, since one workspace always exists) | C (`Creating…`, `Saving…`, `Working…`) | **B** (create, rename, set default, retire; reactivate: C) | **B** (duplicate key kept in the dialog; default cannot be retired: disabled with its reason, refusal inside the confirmation: C) | **B** (concurrent rename and concurrent default switch reported with the current state, nothing retried) | C (`WorkspaceAdmin.test`: capability, catalogue and detail reads, Retry in place) | **B** (390px page, drawer catalogue, rename dialog) | **B** (header link, New workspace and dialog submit by keyboard) | `w4-workspace-admin`; gates: `workspaces-admin` light and dark |
| W4 | Delete an unused workspace from the Workspaces detail (W6) | `/workspaces/<key>` **Delete…** | Confirmation (`ui/ConfirmDialog`), Notice | — (read with the detail) | **B** (deletable new workspace; default: reason and no action; published and not empty: C) | C (`Working…`) | **B** (delete by keyboard, success notice, catalogue and selector drop the key, stale URL not found, corrected key created) | C (refusal after the page loaded closes the confirmation, shows the server message and the new reason) | C (version conflict reported with the current state, nothing retried) | C (other failures inside the confirmation) | **B** (390px detail with Delete beside Reactivate) | **B** (Delete… and the confirmation's second stop by keyboard; Cancel focused first) | `w4-workspace-admin` step 11, `WorkspaceAdmin.test`, `App.test`; gates: `workspaces-admin` (default workspace's reason) |
| W2 | Workspace selector: **Manage workspaces** option, read-only label for one workspace (W4) | sidebar **Workspace** | Field (`ui/Selection` combobox) | C | **B** (one workspace: label; two: combobox listing both after a switch) | — (a switch is a navigation) | **B** (switch in RDM Systems; Manage workspaces from the dropdown and from the label, by keyboard) | — (nothing to refuse) | — (read-only) | C (`WorkspaceSelector.test`: unknown workspace error) | B (shared sidebar at 390px, `wp9-navigation`) | **B** (label button by keyboard; option by pointer, the combobox keyboard contract is React Aria's and `wp9-navigation`'s) | `w4-workspace-admin`, `WorkspaceSelector.test`; every shell baseline shows the label |
| W3 | Deployment capability status on Models and Workspaces (W4) | header **Models** or **Workspaces** | Notice-like status list | — (read with the screen) | **B** (model off and workspace on; model on and workspace off, direct `/workspaces` link read only) | — | — (read only) | — | — | C (Workspaces: failed capability read with Retry) | B | — (static text) | `w4-workspace-admin`, `ModelWorkbench.test`; gates: `model-workbench`, `workspaces-admin` |

Not applicable, with reasons: the selector's switch and the capability status write nothing, so they
have no pending, refused or conflict state. An axe scan with the selector's popover open covers the
popover only: React Aria hides everything outside an open popover from assistive technology, so a
whole-page scan at that moment reports the hidden shell rather than the options (`landmark-one-main`,
`aria-hidden-focus` on the header and explorer). Reactivation and the in-dialog retirement refusal have
component evidence only.

### Surfaces added or materially changed in 0.8 Milestone A

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A4 | Relation matrix lens (A1 placeholder replaced by A4) | sidebar **Codelists** or **Master values** in RDM Translations or RDM Systems; `/apps/<app>/views/<relationMatrix view>` | Page surface; continuous list (`ScrollWindow`) with a pinned row header; Filter in `ui/ControlPopover`; cell dialog `ui/Modal` with the mapping lens's candidate list | **C** (Loading row) | **B** populated and gap-filtered (two row types, both binding shapes); **C** filtered-empty; empty workspace: gap | gap (Saving…/Linking… labels unasserted) | **B** (create, edit, link, unlink; live and change set; one-cell refresh) | **C** (uniqueness breach keeps input and opens the conflicting record) | **C** (stale relation-set claim shows the current cell) | **C** (load failure keeps the page; Retry repeats the request) | **B** (390px: grid, create with container picker, link; no page overflow) | **B** (whole journey by keyboard: arrows across cells and rows, Enter, Escape, focus back on the cell after save) | `views/RelationMatrixView.test` (12), `CollectionView.test`, `routes.test`; `test:browser:a4` (10 checks, axe on five states); read-only publication **B**. A5: `test:browser:a5` (SC-09 by keyboard, publishing from the change set screen, the generated model); gates `test:a11y` (matrix, history-only cell dialog, Filter popover, light and dark) and `test:visual` (`relation-matrix-*` light and dark) |

The placeholder reads nothing and writes nothing, so it has no load, pending, success, refused,
conflict or retry state. Its browser evidence is a one-off harness check (2026-09-27): the two starter
views opened by keyboard at 1440px and 390px, no horizontal overflow, and axe clean at both widths;
it is not kept as a runner because A4 replaces the surface and owns its runner, accessibility and
visual scenarios. The two systems shell baselines were updated for the sidebar's new **Codelists**
and **Master values** entries after inspection; no other baseline changed beyond noise.

### Surfaces added or materially changed in 0.8 Milestone B

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Tree lens placeholder (replaced by B3) | lens switch on the **Domains** (RDM Master) or **Systems** (RDM Systems) collection; `/apps/<app>/views/<tree view>` | The A1 matrix placeholder: page heading, lens switch, empty-state message naming the node types from the model | n/a (reads nothing) | n/a | n/a | n/a | n/a | n/a | n/a | **B** (390px, no overflow) | **B** (lens opened by keyboard) | `CollectionView.test` (two root types), `model.test` (grouping); one-off harness check below; `test:visual` baselines `collection-table-domain-*`, `collection-table-system-light`, `change-set-editing-light` updated for the lens switch |
| B3 | Tree lens (B1 placeholder replaced by B3) | lens switch on **Domains** (RDM Master), **Systems** (RDM Systems) or a generated model's root collection; `/apps/<app>/views/<tree view>`; records open in the inspector beside it | Page surface; the S6 tree (T4) for loading, windows and keyboard; `ui/AnchoredMenu` for the node menu; `ObjectFormDialog` for a child; move dialog `ui/Modal` with the matrix link-candidate list | **C** (tree loading note, as T4) | **B** populated on three trees (two starter shapes, the seven-level generated tree); **C** empty workspace (the view's root type named) | **B** (move dialog: **Moving…** with a status line while the write runs, D29; not asserted); gap (switch dimmed while availability saves) | **B** (add child, rename, availability, move; live and change set; the new or moved node focused, both branches' counts reloaded) | **B** (current parent and descendant listed disabled with their reason); **C** (rename refused keeps the typed name with the reason; a refused move keeps the dialog, choice and reason) | **C** (an availability conflict re-reads the tree so a retry claims the new version); gap (the same for rename and move, untested) | **C** (a failed branch shows Retry without collapsing its siblings, as T4; a refused availability change is a dismissible notice above the tree) | **B** (390px: search, add, rename, availability, move; the record opens full width and Back returns to the tree; no page overflow) | **B** (whole journey by keyboard: search, arrows and type-ahead, Shift+F10 menu, F2, dialogs, focus back on the node after each write and after Escape) | `views/TreeView.test` (11), `CollectionView.test`, `useRouter.test`, `client.test`; `test:browser:b3` (21 checks, axe on eight states: the system tree, both trees after writes, four move dialogs, the volume tree); read-only publication **B**. B4: `test:browser:b4` (SC-09 by keyboard: ancestors-only reveal, the descendant refused in the dialog and the API, new path and containment edge, unrelated branches unchanged, a change set move published from the change set screen; two trees, 1440px and 390px); gates `test:a11y` (tree lens and move dialog, light and dark) and `test:visual` (`tree-lens-*`, `tree-move-dialog-*`) |
| B5 | Drag and drop in the tree lens | a record row of a tree lens whose view allows `move`, live or in a change set, with mouse or pen | B3's tree and `TreeMoveDialog` (confirmation, **Moving…**, refusal, conflict); glow from the `--success-*` and `--danger-*` tokens | n/a (reads nothing until the drop; the dialog loads as B3) | **B** (accepted onto a record, into a gap, onto a heading; two starter trees) | n/a (the dialog's own, as B3) | **B** (the drop opens the dialog with the target chosen; Enter moves it; checked against the API live and in a change set) | **B** (refused target red with its reason in text and a no-drop cursor; release writes nothing); **C** (a server refusal keeps the dialog and choice) | n/a (the dialog re-reads on a version conflict, as B3) | n/a (no read of its own) | n/a: touch pointers never drag (D35); phones keep Move to… (B3, B4 at 390px); **C** a touch pointer starts nothing | n/a by design: Move to… is the keyboard path (WCAG 2.5.7); Escape cancels (**B**) | `model/treeDrop.test` (7), `views/TreeView.test` (6 drag cases), `Explorer.test` (sidebar never drags); `test:browser:b3` Part 3 (5 drags, axe on the refused one); gates `test:a11y` and `test:visual` `tree-drag-{accepted,refused}-{light,dark}` |
| B5b | Move to the top level | **Move to…** on a tree lens record, and a drag onto a top-level heading or gap, where the view allows `move`, live or in a change set | B5's drag and glow; `TreeMoveDialog`'s candidate radios (the **Top level** option reuses their style and disabled-with-reason pill) | n/a (the option is not loaded; the candidates load as B3) | **B** (a nested group of the volume tree's root type offered and moved, by keyboard live and by drag in a change set) | n/a (the dialog's own, as B3) | **B** (Enter moves it; API: no parent, no containment edge; the top-level count rises and focus stays on the row); **C** (confirming sends `parentObjectId: null`) | **B** (a non-root type dragged there live red with **Not shown at the top of this tree**, nothing written; in a change set it becomes a root type instead, C4); **C** (disabled with **Not shown at the top of this tree** and **Current location**; a server refusal keeps the dialog and **Top level** chosen) | n/a (the dialog re-reads on a version conflict, as B3) | n/a (no read of its own) | n/a: Move to… at 390px is B3's; touch never drags (D35) | **B** (Tab reaches **Top level**, Space chooses it, Enter confirms) | `model/treeDrop.test` (top-level cases), `views/TreeView.test` (4 cases); `test:browser:b3` B5b steps (axe on the dialog); a11y and visual gates unchanged (R1b) |

The placeholder reads nothing and writes nothing, so it has no load, pending, success, refused,
conflict or retry state. Its browser evidence is a one-off harness check (2026-09-28): both starter
trees opened by keyboard from their table's lens switch at 1440px and 390px, no horizontal overflow,
and axe clean at both widths. It is not kept as a runner because B3 replaces the surface and B4 owns
its runner, accessibility and visual scenarios.

B3's lens is the tree the sidebar uses (T4), configured by the view, so it inherits T4's window,
edge and retry states; its own states are the actions. The availability switch and the row's ⋯ are
pointer shortcuts hidden from assistive technology: the node menu offers both, and the item's name
states availability. Opening a record from the tree keeps the tree beside it (the inspector split
retained since UI-03, and now kept across history), which is where its visual evidence is: a record
title in the narrow inspector wraps its actions below it. `test:a11y` and `test:visual` scenarios for
the lens and move dialog, light and dark, are B4's.

### Surfaces added or materially changed in 0.8 P2

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2 | Change set review: **Records** and **Relationships** tabs, filter, expandable before/after rows (P2b); **Review changes** on the change set bar and in the publish confirmation | change set bar **Review changes**; `/apps/<app>/change-sets/<id>/changes` (tab, kinds, type, parent links and anchor in the URL) | Page surface (`CollectionView`) with `ui/Tabs`; Continuous list (`ScrollWindow`, `useCursorWindow`) of disclosure rows; Filter in `ui/ControlPopover`; Empty state; Load failure (`InlineError`) | **C** (Loading changes…) | **B** every kind in RDM Master and RDM Systems (added, changed, moved, removed records; added and removed mappings; five parent links on request), **B** empty change set, **B** filtered-empty | n/a (reads only; edge loading is T1's) | **B** (rows match the API entry for entry; expand an edit and a move; open a changed and an added record in the change set; reload keeps tab and filter) | n/a (the screen writes nothing; an unknown type in the URL is dropped: C) | n/a (read-only; a later write refreshes the lists through the shell's refresh) | **C** (a failed read keeps the header and tabs; Retry repeats the same filtered request) | **B** (390px: expanded move and relationships with parent links, no page overflow) | **B** (bar button, arrow keys between rows, Enter/Space expand, filter popover with Escape back to Filter, tab arrows, link Enter) | `ChangeSetReview.test` (14), `routes.test` (2), `client.test` (1); `test:browser:p2` (9 checks, axe on seven states: records, expanded, relationships, 390px, dark records and relationships, empty); gates `test:a11y` (review and relationships, light and dark) and `test:visual` (`change-set-review-*`; `change-set-editing-light` and `change-set-detail-light` updated for the bar's new button) |

The review only reads, so it has no pending, refused or conflict state of its own. It opens in the
change set's context, so the shell reads the change set and its pinned model, and every type,
relationship and field label comes from that model. Parent links are hidden from Relationships by
default (D32); the note beside the filter says so and the record's Parent change shows the move. The
publish confirmation's link is exercised in `ChangeSetReview.test`, not in a browser, because a
browser publish is SC-06's (`wp9-change-sets`). Two baselines changed only in the change set bar's
button row (the new **Review changes** before Validate); both were inspected before being accepted.

### Surfaces added or materially changed in 0.8 Milestone C

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C4 | Restructuring in the tree lens: **Move to…** and drag to a place that changes the type, the node menu's **Change type…**, **Insert level above…**, **Remove this level…** and **Change type of all <type> in here…**, and the restructuring preview dialog | a tree lens whose view allows `move`, in a change set only (D38): the node menu (Shift+F10, context menu key, ⋯), **Move to…** or a drag | B5's drag and glow (the accepted preview adds **Becomes <type>**); `TreeMoveDialog`'s candidate radios (an accepted pill, **Becomes <type>**); the preview is `ui/Modal` (new `wide` size) with `ui/Tabs`, a continuous list (`ScrollWindow`) of plan records styled after the P2 review rows, and the P2 before/after table for the type pairs; the insert dialog's sibling list reuses the move dialog's candidate list with checkboxes | **B** (**Planning…**, then the plan; a new level waits for its name) | **B** populated: one record, a cascade-free move, two records under a record, a created level taking a chosen sibling, and a removed level; **C** a plan with no records (**Nothing changes**) and a filter matching none | **B** (**Updating the plan…** while a choice or input re-plans; the previous plan stays, no row unmounts, so the field being typed in keeps focus); **B** (**Applying…** with a status line) | **B** (**Applied to the change set** with **Review the change set** and **Done**; focus to Done, then back to the record under its new type, or to the removed level's parent); **C** (apply sends the previewed version and digest) | **B** (a record's required values asked in place, **Some answers are needed**); **C** (refusals listed with their reason, per operation and per record; a type question; a request error such as `RESTRUCTURING_TOO_LARGE` in place; Apply disabled until **Ready to apply**) | **C** (`RESTRUCTURING_PLAN_CHANGED`, `CHANGE_SET_VERSION_CONFLICT` and `RESTRUCTURING_NOT_READY` on apply: **The plan changed**, nothing written, the plan read again) | **C** (a failed preview shows the error with Retry, as `InlineError`) | **B** (390px: the preview full width, actions pinned to its foot, no horizontal scroll; no drag on touch, D35: the menu and Move to… are the path) | **B** (menu, Move to…'s radios, the plan's tabs, selects and fields, Apply and Done by keyboard; Escape cancels) | `model/restructuring.test` (6), `RestructuringDialog.test` (8), `views/TreeView.test` (5 C4 cases), `client.test` (`withinObjectTypeKey`), `ChangeSetReview.test` (the type change row), `ObjectDetail.test` (D42 follow); `test:browser:c4` (12 checks, axe on the ready, inputs and 390px previews). C5: `test:browser:c5` (the milestone journey by keyboard on the starter and generated trees: a two-level cascade answered by type and by record, insert and remove a level, the review, publishing, live, publication and history, the way back restoring values and a relationship; axe on the by-type, review and restored states); gates `test:a11y` (`tree-move-type-change`, `restructuring-preview`, `-preview-by-type`, `-insert-level`, `-remove-level`, `-change-type`, light and dark) and `test:visual` (the same without `-change-type`, light and dark) |

The preview is the server's plan (C3) rendered two ways, so its states are the plan's statuses
(`ready`, `needsInput`, `refused`) plus the dialog's own pending and apply states. Live, the lens
offers no restructuring and a place that would change the type stays refused as B5 and B5b say; in a
change set the same place glows green with what the record becomes. Both paths keep to the tree's
types: Move to… asks the server for candidates of those types only (`withinObjectTypeKey`), and where
records may stand is the engine's served rule (`GET /model/placements`, D45). Live, a place refused
only for the record's type says a change set can change it. A record whose type changed is
followed to its current route when the inspector re-reads it (D42, `409 OBJECT_TYPE_CHANGED`); that
follow replaces the route and leaves focus where the user is working. The review screen names a
type change on the record's row (**Master value → Codelist**) and as **Type** in its before/after
table. The preview's dimming while it updates was removed after the runner's axe pass measured the
dimmed text below AA contrast; the status line says it is updating instead. Accessibility and visual
gate scenarios (light and dark) for the preview and the refactoring dialogs are C5's.

### Surfaces added or materially changed in 0.9 U3

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U3-1 | Settings shell and navigation | gear in the top bar, **All settings** in the account popover; `/settings` | Settings layout | — (static) | **B** (five pages listed in two groups, the current one marked) | — | **B** (Back to applications returns to the view and query it left, from two applications) | — | — | — | **B** (390px: the drawer from the **Settings: {page}** bar, Back as an icon in the top bar, no page overflow) | **B** (skip link, top bar, navigation with the resize handle, content; Enter on a link) | `u3-settings`, `Settings.test`, `App.test`; gates `settings-*` |
| U3-2 | About | `/settings/about` | Settings layout, DescriptionList | **C** (Skeleton) | **B** | — | — (read only) | — | — | **C** (InlineError, Retry) | **B** | B | `u3-settings`, `Settings.test`; gates `settings-about` light and dark |
| U3-3 | Appearance: theme and default table density | `/settings/appearance` | Settings layout, FormField (radio groups) | — | **B** | — | **B** (Compact compacts two views of different object types; a view's own choice wins) | — | — | — (storage blocked: the choice applies for the session, C) | **B** | B (radio groups by keyboard) | `u3-settings`, `Settings.test`, `localPreference.test`; gates `settings-appearance` |
| U3-4 | Deployment: capability groups and every setting | `/settings/deployment` | Settings layout, StatusPill, tables | **C** (Skeleton) | **B** (secrets as Set or Not set; the ephemeral cursor key warning) | — | — (read only, U-D2) | — | — | **C** (InlineError, Retry for either read) | **B** (rows stacked) | **B** (focusable table groups) | `u3-settings`, `w4-workspace-admin` (group off), `Settings.test`; gates `settings-deployment` light and dark |
| U3-5 | Workspaces: catalogue beside the selected workspace (moved from W1, W4) | `/settings/workspaces[/<key>]`; old `/workspaces[/<key>]` redirects | Settings layout, catalogue and card | **C** | **B** (retired listed) | C | **B** (create, rename, default, retire, delete; Toast confirms) | **B** (as W1/W4; `subscribed` reason: C) | **B** (as W1) | C (`WorkspaceAdmin.test`) | **B** (390px: the workspace alone, **All workspaces** back to the catalogue, rename dialog) | **B** (as W1) | `w4-workspace-admin`, `WorkspaceAdmin.test`; gates `settings-workspaces` light and dark, `settings-workspace-detail` |
| U3-6 | Model: catalogue of releases and drafts beside the selected one (moved from S12, S13) | `/settings/model`, `/settings/model/releases/<id>`, `/settings/model/drafts/<id>`; old `/models?…` redirects | Settings layout, catalogue and card | **C** | **B** (no drafts: EmptyState in the catalogue, C) | C | **B** (activation keeps the release page; Toast confirms install and activation) | as S12 | as S12 | C | **B** | B | `wp12-release-identity`, `wp9-navigation`, `ModelWorkbench.test`; gates `settings-model` light and dark, `settings-release-detail` |

W1, W3, W4, S12 and S13 above describe these pages before U3. W3's capability status is replaced by
Deployment's capability groups and a notice on a disabled page naming its setting.

## 3. Selected focused browser checks

Selected by risk to the user's job (losing an unsaved choice, silently overwriting a newer mapping,
publishing from the wrong model, being stranded on a failed read), not by earlier defect reports. Two
model configurations are exercised: the outgoing System → Master binding in `rdm-systems` and the
incoming Master ← System binding in `rdm-master`, in Live and a named Change set respectively, plus two
installed releases of the starter model.

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  npm --prefix frontend run test:browser:wp13c
```

`e2e/wp13c-ui-states.mjs` (real backend, 11 checks, 5 scoped axe checks, 12 screenshots; ~8.5 s of
which ~2.4 s harness setup):

1. Coverage read outage keeps the shell and lens, states “Coverage unavailable”, Retry loads the grid.
2. Filtered-empty coverage is explained; clearing the facet restores rows.
3. Keyboard opening of the mapping dialog focuses candidate search; a no-match search is named.
4. Candidate read outage stays inside the dialog; Retry restores candidates.
5. Contextual creation offers every application containing the target type, with the lens's
   application as the default and only its parent types; Cancel keeps the unsaved choice and coverage.
   Creating a master value in RDM Master from the RDM Systems lens selects it and saves it (WP-10F).
6. Explicit save stores the selection and refreshes coverage.
7. A concurrent mapping change shows the current mapping, keeps the attempted choice, blocks Save until
   **Continue with my selection**, then saves the attempted target.
8. Narrow grid and dialog fit 390px, and the candidate search stays ≤ 48px high (WP-10G); Escape
   returns focus to the row action.
9. The inverse binding creates a system value in its only application inside a named change set, maps it,
   and neither the value nor the mapping reaches live.
10. Change-set list outage keeps the page header; Retry loads change sets.
11. A change set created on a non-active release names both releases by key and version (no UUID, WP-10G),
    explains the mismatch and refuses activation.

Outages are simulated with `page.route` 503 responses on one read path until restored; every successful
read and write reaches the real backend. React development mode issues reads twice, so an injected
failure must persist until the Retry click rather than failing once.

## 4. Screenshot review (2026-09-24)

Inspected against the references in section 1: all twelve wp13c screenshots.

| Surface | Result |
| --- | --- |
| S4 coverage failure (wide), S8 drafts-list failure (wide) | Matches the load-failure reference: header, lens tabs and facets stay; error replaces only the content. |
| S5 candidate failure, conflict (wide) | Dialog reference respected; conflict notice states the current mapping and the review action; disabled Save/Remove visibly disabled. |
| S5 conflict and dialog (narrow) | **Defect (WP-10G):** the candidate search box stretches to fill free height (≈170–500px). `responsive.css` gives every `.search-box` `flex: 1 1 100%`, which becomes a height basis inside the dialog's column form. |
| S4 grid (narrow) | Usable; secondary columns hidden, Action column scrolls inside the labelled region; lens tab strip and application tabs scroll horizontally within their own row. Acceptable. |
| S6 creation refusal (wide) | Error is contained and actionable, but the user cannot complete the job (WP-10F). |
| S7 change set inverse (wide) | Change set bar, inverse direction label and target fields render per reference. |
| S8 creation dialog (wide) | Matches the dialog and field references. |
| S9 mismatch (wide, narrow) | Layout correct at both widths. **Defect (WP-10G):** the notice names the active model by raw release UUID instead of key and version, contrary to WP-12's human-readable release identity. |

Dark-theme variants of the new states were not captured. WP-9 ran the dark a11y/visual gate pages.

**Re-review after WP-10F/WP-10G (2026-09-25):** `mapping-create-target-wide` shows the Application
choice with only the RDM Systems parent type. `mapping-change-set-create-target-wide` shows a single owner
as a fixed Application fact aligned with the labelled fields. `mapping-dialog-narrow` keeps a one-line
search box. `change-set-version-mismatch-wide`/`-narrow` read "the active model rdm-starter 0.7.0". All
match the dialog and notice references.

**WP-9 composed review (2026-09-25).** A second binding configuration, the independent **Master
alignment** lens (`qa-master-aligns-to-system`, outgoing from master values), reuses S4/S5 unchanged.
Reviewed screenshots: `sc07-ambiguous-expanded-wide` (25 targets after continuation, count in the
badge), `sc07-independent-binding-wide`/`-narrow` and `sc07-independent-dialog-narrow` (third lens,
dialog fits 390px; actions pinned at the sheet foot), `sc07-activation-conflict-wide` (the error now
reads as two sentences), `sc15-incompatible-create-wide`/`-narrow` and `sc15-incompatible-change-wide`
(records listed under the reason), `sc15-draft2-candidate-view-wide` (candidate view name and Priority
column), `sc15-draft1-mismatch-narrow`. All match the dialog, notice and page references. Diagnostics
still identify a record by UUID, which is recorded as a residual gap. Fixed shell elements appear
mid-page in full-page captures; this is a stitching artifact.

## 5. Follow-ups found (delivered as WP-10F/WP-10G on 2026-09-25)

- **WP-10F — Contextual target creation is scoped to the lens's application.** `MappingActionDialog`
  passes the view's `applicationKey` to `ObjectFormDialog`, and objects belong to one application. In
  the starter model the System → Master lens (`rdm-systems`) offers a Codelist parent that its
  application cannot load, and the Master ← System lens (`rdm-master`) cannot create a system value at
  all. Needs a product decision on which application owns a target created in context (the target
  type's owning application, or one chosen from the applications that contain it) and a real-API
  regression.
- **WP-10G — Visual fixes:** narrow candidate-search height; human-readable active release in the change set
  mismatch notice.

## 6. Limitations

- Contextual creation at 390px was not captured; the dialog uses the shared narrow form layout.
- Pending states rely on component evidence; browser timing of `busy` states was not asserted.
- The new states have no committed visual baselines; screenshots are reviewed evidence. WP-9 ran the
  comprehensive a11y/visual gates (13 baselines; the two Models baselines were refreshed for WP-12).
- One Chrome build, one machine; no operating-system zoom or assistive-technology session.
