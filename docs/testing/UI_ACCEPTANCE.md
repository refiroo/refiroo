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
| Confirmation | `ui/ConfirmDialog` (draft activate/discard, deletion) | States the consequence; destructive action uses `danger`/`danger-ghost`. |
| Field | `ui/AttributeField`, `ui/ObjectLookup`, label-wrapped `<input>/<select>` in `ObjectFormDialog` | Visible `<label>` text wraps the control; required state from the model; typed input types. |
| Actions | Collection header action (`.collection-header-actions .primary`), `RecordActionMenu`/`ui/ActionMenu`, `ui/ControlPopover` | One primary action per surface; secondary actions in a menu or `<details>` disclosure; icon buttons carry an accessible name. |
| Page surface | `features/objects/CollectionView.tsx` | `.page-header` with `.page-title` and `h1`; `.surface` with toolbar and a continuous list. |
| Continuous list (0.8 S5) | `ui/ScrollWindow` in `ui/ObjectTable` (collection lens) | Labelled scrolling region with a sticky header; quiet start and end markers, an edge loading marker only while waiting; a proportional window scrollbar when the window holds part of the list; footer with the visible range, page field, start/end buttons and, where the list seeks, a **Go to** field. Rows carry `aria-rowindex` and the table `aria-rowcount`. |
| Tree (0.8 S6) | `features/objects/RecordTree` in the explorer's **Browse records** | `role="tree"` with one tab stop. Each object type's records form a group headed by an item naming the type and its count (opening its collection); the rows scroll in a bounded `ui/ScrollWindow` whose viewport is the named `group` (a tab stop only while it scrolls, presentational edge markers, announcements through the tree's one live region). `aria-level`, `aria-setsize` and `aria-posinset` from totals; Up/Down cross window edges by loading, Right/Left expand, enter, collapse and return, Home/End, Ctrl+Home/End within a group, Enter opens. |
| Table sort (0.8 S4R3) | Record panel header sort: `CollectionPanelTable` over `ui/ObjectTable`, through `ui/TableSort` | Every data column sorts from its header (quiet icon on hover/focus drawn in the header padding, accent arrow when sorted, toggle on activation, `aria-sort`, name stating the order, polite announcement); only Actions, the computed path, JSON and unrecorded timestamps do not. Every list with sort fields carries the same icon-only `ui/ActionMenu` Sort menu in its toolbar (radio fields plus direction, tooltip). No labelled sort select or popover. |
| Load failure | `ui/InlineError` (a `Notice` titled “Could not load this content” with **Retry**) | Replaces only the failed content; shell, header and previously loaded data stay; Retry repeats the exact request. |
| Empty state | Collection empty row, `.empty-panel` in `WorkspaceDrafts` | Says whether nothing exists or nothing matches the current search/filter. |
| Notice | `ui/Notice` tones `info`/`warning`/`error` | Title plus a sentence stating what happened and the safe next action; `focusOnMount` for a failure the user must act on. |
| Disclosure | `<details>` in `WorkspaceDrafts` (More draft actions) and `ModelReleaseDetail` (Technical details); `ui/Tabs`; `ui/NavigationDrawer` | Native keyboard operation; identifiers and technical metadata stay collapsed by default. |
| Narrow layout | `styles/responsive.css` at ≤ 720px; 390×844 is the checked phone width | No page-level horizontal scroll; wide tables scroll inside their labelled region; dialogs fit the viewport. |

## 2. Surfaces added or materially changed in 0.7

Navigation is given from a fresh isolated harness (`e2e/helpers/harness.mjs`). The state columns use:
**B** browser evidence (runner named in the last column), **C** component evidence only,
**—** not applicable (reason in the notes), **gap** applicable without evidence.

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | Shell: application tabs, model/schema version, Live/Drafts/History, settings menu, dark theme (redesign, 315e6f7) | any `/apps/<app>/…` | Page surface | C | B | — | B | — | — | B (context failure) | B | B | `wp9-navigation`, `App.test` “keeps transient context failures in the shell”, `SettingsMenu.test`, a11y dark pages |
| S2 | Unified application browser: collections + record tree (WP-14) | sidebar; narrow: **Browse application** | Disclosure (drawer, tree) | C | B | — | B | — | — | C (`Explorer.test`) | B | B | `wp9-navigation`, `wp14-contextual-browser` |
| S3 | Collection lenses, scope banner, Filter popover (WP-14, redesign) | `/apps/rdm-systems/views/systems` → expand System 00 → System values collection | Page surface, `ControlPopover` | C | B | — | B | C (typed filter 422) | — | C (`CollectionView.test`) | B | B | `wp14-contextual-browser`, `wp9-navigation` UI-02 |
| S4 | Mapping lens grid (WP-8A/WP-14) | lens tab **System → Master mapping**; `/apps/rdm-master/views/master-to-system-mapping` | Page surface | C | B incl. filtered-empty | — | B | — | — | **B** | **B** | B (region focusable, row button) | `wp13c-ui-states`, `wp14-contextual-browser` |
| S5 | Mapping dialog: candidates, save/next, remove, conflict (WP-8B) | row **Map/Change** | Dialog | C | **B** incl. no-match, page two (WP-9) | C (`Saving…`) | **B** | C (server error notice; WP-10H: no removal for a required binding) | **B** (also a racing generic write, WP-9) | **B** | **B** | **B** (search focus, Escape restores focus, keyboard-only save) | `wp13c-ui-states`, `sc07-mapping-acceptance`, `MappingGridView.test` (26) |
| S6 | Contextual target creation (WP-8B) | mapping dialog → **Create new …** | Dialog (nested `ObjectFormDialog`) | — | — | — | **B** (WP-10F: create, select, save in both directions, live and draft) | C (no parent type in the chosen application) | — | B (lookup error + Retry shown) | gap | C | `wp13c-ui-states`, `MappingGridView.test` |
| S7 | Mapping in a named draft, inverse direction (WP-8B/WP-7) | `…/master-to-system-mapping?workspaceDraftId=…` | as S4/S5 | — | **B** | — | **B** (live unchanged) | — | C | — | gap (wide only) | B | `wp13c-ui-states` |
| S8 | Drafts list and creation with model version (WP-7) | Drafts tab | Page surface, Dialog | C | B | C | **B** | **B** (WP-9: incompatible release lists the records, keeps the name, leaves no draft) | — | **B** | **B** (refused creation at 390px) | C | `wp13c-ui-states`, `sc15-model-version-acceptance`, `wp9-drafts` |
| S9 | Draft bar, model mismatch notice, activation refusal (WP-7/WP-11) | open a draft pinned to a non-active release | Notice, Actions | C | **B** | C | B (`wp9-drafts`; WP-9: the prepared draft after model activation) | **B** (Activate disabled with reason; WP-9 also after the active release moves on) | B (`wp9-drafts`; WP-9 mapping-set divergence) | C (refresh warning) | **B** | C | `wp13c-ui-states`, `sc15-model-version-acceptance`, `sc07-mapping-acceptance`, `wp9-drafts` |
| S10 | Change model version dialog (WP-7/WP-11) | draft bar → More draft actions → **Change model version** | Dialog (`compact`) | C | B | C | B | **B** (WP-9: incompatibility diagnostics, pin unchanged) | C | C | B | B (focus trap, dirty Escape) | `wp11-model-admin`, `sc15-model-version-acceptance`, `WorkspaceDrafts.test` |
| S11 | Workspace/page load failures (WP-11) | any context read failing | Load failure | — | — | — | B | B (unsupported historical schema: C) | — | **B** (drafts list), B (`wp9-navigation` panels) | C | C | `wp13c-ui-states`, `App.test` |
| S12 | Release detail: identity, Technical details, comparison baseline (WP-12) | Models → release | Page surface, Disclosure | C | B | — | B (copy) | C (unsupported baseline) | — | C | B | B | `wp12-release-identity`, `ModelReleaseDetail.test` |
| S13 | Models page alignment (315e6f7) | header **Models** | Page surface | C | B | — | B | C | C (version conflict) | C | C | C | visual/a11y gate pages (`model-workbench-*`), `ModelWorkbench.test` |
| S14 | Record header, breadcrumb, readable activity (redesign) | open any record | Page surface | C | B | — | B | — | B (`wp9-authoring`) | B | B | B | `wp9-navigation`, `wp9-authoring`, visual baselines |

Not applicable, with reasons: S4 has no pending/refused state of its own (writes happen in S5);
S6 load/empty belong to the nested form's lookups, shown under dependency failure; S7 load and failure
share S4's renderer and code path, so only the context difference (draft overlay, inverse direction) is
checked; S11 has no conflict state.

### Surfaces materially changed in 0.8 Track S

| # | Surface (package) | Navigation | Reference | Load | Populated / empty | Pending | Success | Invalid / refused | Conflict | Dependency failure → retry | Narrow | Keyboard / focus | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Continuous lists: collection lens, record panels (with a name-default sort), relation panels (with search and sort), mapping lens, mapping candidates (S5) | any collection; a record's panels; mapping lens | Continuous list | C (`useCursorWindow.test`) | **B** (populated at 10,000 and 72 rows; empty from search: C) | B (edge marker while waiting: component only; not captured in a screenshot) | **B** (scroll both ways, scrollbar click and drag, page number, seek, Ctrl+Home/End, URL anchor reopen, in live, draft and history) | B (unknown seek value: InlineError, C) | — (read-only lists; writes keep their own conflict states) | **B** (edge read fails, window kept, Retry in place: `wp9-navigation`); C (`CollectionPanelTable.test`, `RelationsPanel.test`) | **B** (390px, no page overflow) | **B** (arrow keys across page boundaries, focus kept by row identity) | `s5-continuous-lists`, `s7-volume-acceptance`, `wp9-navigation`, `sc07-mapping-acceptance`; gates: `scrolling-list-tree` |
| T3 | Table sort: collection lens, record panels, relation panels (S4R3) | a collection's headers; a record's panels | Table sort | C (`ObjectTable.test`, `RelationsPanel.test`, `CollectionView.test`) | **B** (relation panels on a domain and a codelist; the schema 0.6 volume relation panel, declaring no sort, lists by name and sorts every header including Relationship) | — (a sort is one list read; its loading is T1's) | **B** (header toggles both ways, a never-flagged attribute (value name), record panel attribute sort, the toolbar menu for a field without a column, in live, draft and history; request, `aria-sort` and announcement checked) | C (live-only timestamps dropped in drafts and history; path not sortable) | — (read-only) | as T1 | **B** (390px: relation header sort, the record panel's toolbar menu for its collapsed Sort order column, lens menu; no page overflow) | **B** (headers by Enter, menu opened and chosen by keyboard) | `s5-continuous-lists`, `wp9-navigation`; baselines `collection-table-*`, `record-detail-*`, `draft-detail-light`, `draft-editing-light` |
| T4 | Sidebar tree by parent (S6) | explorer **Browse records**, every application | Tree | C (`Explorer.test`: loading note, a failed group) | **B** (1,000 roots, a 2,000-child branch, two child types with one empty on a system; an empty codelist says **Nothing inside**; no matching search result: C) | C (a group's edge marker while waiting, as T1) | **B** (branches show exactly their own children and counts, the heavy branch scrolls end to end, an eight-level keyboard path opens its record, a heading opens its scoped collection, search shows ancestor paths, in live, draft and history) | — (read-only; nothing to refuse) | — (read-only; a refresh reloads groups in place) | C (`Explorer.test`: a failed group's error outside the tree, Retry in place) | **B** (390px drawer: touch expand, scroll past the first page, keyboard expand; no page overflow) | **B** (one tab stop; Up/Down across a window edge, Right/Left, Home/End, Ctrl+Home/End in a group, Enter) | `s6-sidebar-tree`, `s7-volume-acceptance`, `wp9-navigation` (incl. `ui03b-hierarchy`), `wp14-contextual-browser`; gates: `scrolling-list-tree` |
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
now share the text-input treatment. `test:browser:s7` composes T1 and T4 in live, draft and history.

## 3. Selected focused browser checks

Selected by risk to the user's job (losing an unsaved choice, silently overwriting a newer mapping,
publishing from the wrong model, being stranded on a failed read), not by earlier defect reports. Two
model configurations are exercised: the outgoing System → Master binding in `rdm-systems` and the
incoming Master ← System binding in `rdm-master`, in Live and a named Draft respectively, plus two
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
9. The inverse binding creates a system value in its only application inside a named draft, maps it,
   and neither the value nor the mapping reaches live.
10. Drafts-list outage keeps the page header; Retry loads drafts.
11. A draft created on a non-active release names both releases by key and version (no UUID, WP-10G),
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
| S7 draft inverse (wide) | Draft bar, inverse direction label and target fields render per reference. |
| S8 creation dialog (wide) | Matches the dialog and field references. |
| S9 mismatch (wide, narrow) | Layout correct at both widths. **Defect (WP-10G):** the notice names the active model by raw release UUID instead of key and version, contrary to WP-12's human-readable release identity. |

Dark-theme variants of the new states were not captured. WP-9 ran the dark a11y/visual gate pages.

**Re-review after WP-10F/WP-10G (2026-09-25):** `mapping-create-target-wide` shows the Application
choice with only the RDM Systems parent type. `mapping-draft-create-target-wide` shows a single owner
as a fixed Application fact aligned with the labelled fields. `mapping-dialog-narrow` keeps a one-line
search box. `draft-version-mismatch-wide`/`-narrow` read "the active model rdm-starter 0.7.0". All
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
- **WP-10G — Visual fixes:** narrow candidate-search height; human-readable active release in the draft
  mismatch notice.

## 6. Limitations

- Contextual creation at 390px was not captured; the dialog uses the shared narrow form layout.
- Pending states rely on component evidence; browser timing of `busy` states was not asserted.
- The new states have no committed visual baselines; screenshots are reviewed evidence. WP-9 ran the
  comprehensive a11y/visual gates (13 baselines; the two Models baselines were refreshed for WP-12).
- One Chrome build, one machine; no operating-system zoom or assistive-technology session.
