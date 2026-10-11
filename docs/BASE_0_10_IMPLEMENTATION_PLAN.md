# Base 0.10 implementation plan

**Status:** Planned 2026-10-11, after 0.9.0, replacing the provisional plan of 2026-09-29. **The
designer line comes first** (D11, requested by the user 2026-10-11): the editor opened on a model,
without a workbook, is built and checked before the spreadsheet profiling, mapping and inference it
later hosts. A-D1–A-D3 are decided; A-D4 and A-D10 were taken by 0.9 J2 (D64–D74); **D11–D16 are
accepted by the user (2026-10-11)**, D14 changed to tag an interim release after T1; D1–D10 and
A-D5–A-D9 are open with a recommendation and are settled in A0. Work packages A0, N1, A2, A4a, A4b,
T1, A3, A5–A8 and R are specified below at package level; each package's detailed plan, test cases
and decisions are written and accepted when it starts, and it is delivered in the order of the
[delivery queue](#delivery-queue), each by the [delivery steps](#how-a-package-is-delivered).
**Delivered:** none yet.

**Target:** Product 0.10.0, [model authoring and spreadsheet onboarding](ROADMAP.md#product-release-010--model-authoring-and-spreadsheet-onboarding).
The `navigation` declaration (A-D2) extends the model, so 0.10 opens the next schema language version
(D1) in its first code package (N1).

**Depends on:** Product 0.9.0, released 2026-10-11 (tag `v0.9.0`), in particular:

- bulk upsert with upsert keys (0.9 D2) and item outcomes (B1–B3);
- import profiles, the XLSX, CSV and JSON Lines readers and `POST /imports` (J2, D64–D74);
- the import preview, confirm and outcomes by row with the binding report (J3, D80–D88);
- job file storage, limits and retention (D12–D14);
- the change set review (0.8 P2) and the Atlas UI foundation and components (UA, ADR-040).

**Package A1 of [MODEL_AUTHORING](MODEL_AUTHORING.md#delivery) is delivered** by 0.9 J2 and J3; it
has no package here. What stays open from 0.9 R (the backend suite over its time ceiling, three
browser runner flakes, two `NOT IN` subqueries to measure) remains in TODO and is not a 0.10 package.

## Product outcome

An administrator turns reference data that arrives in spreadsheets into a working application without
writing a model file or an import script. One editor proposes a model and an import mapping from the
uploaded workbook; the administrator renames, remaps and reorganizes both, seeing the effect on the real
rows after every change; the model is installed and activated through the normal checks; the data
arrives in a change set reviewed before publishing. The next version of the workbook loads through the
saved profile and shows only its differences. Opened without a workbook, the same editor is the
structured model designer for additive and unreleased changes.

Stories: US-P05 (additive and draft-only operations), US-P09, US-P10. Scenario: SC-12 through the
editor, plus the exit gate below.

## What changed from the provisional plan

| Change | Why |
| --- | --- |
| The designer line (N1, A2, A4a, A4b, T1) comes before the spreadsheet line (A3, A5–A8) | The user's request (D11). No dependency is broken: A4 needed only A2, and A3 is needed only by A5 |
| A1 is gone from the queue | Delivered by 0.9 J2 and J3 |
| Navigation groups are a package of their own (N1), first after A0 | A schema language version opens once, before the packages that build on it, as 0.9's C1 did; it was part of A4 |
| A4 is split into A4a (model pane) and A4b (preview and layout editing) | 0.9 kept UI packages to one surface each, approved from screenshots |
| Profile effects of operations move from A2 to A5 | No draft has a profile before A5, and no model operation can break an instance profile (D13) |
| A profile is edited against the draft's model (D12) | Delivered profiles are checked against the active release (D65), which does not hold an uninstalled draft's types |
| T1, a designer checkpoint, is added | The designer is accepted on its own before the spreadsheet line builds on it |
| PostgreSQL only; no SQLite caveats | 0.9.0-alpha.1 |
| Roadmap item U6 removed | U6 was folded into UA in 0.9 |

## Principles and exclusions

The principles of [MODEL_AUTHORING.md](MODEL_AUTHORING.md#principles) apply. For delivery:

1. **Generic.** No branch on an application, object-type, attribute or relation key in the editor,
   inference or services. Every journey runs on two differently shaped models: the starter model
   with its keys renamed, and a generated one (the W1 model once A3 exists).
2. **API first.** Every editor action is an API operation an integrator can send; the editor is one
   client. Default views for a new type, groups and layout changes are produced by the server, not
   by the editor.
3. **Operations are the only write path of the editor.** The whole-model `PATCH` stays for the JSON
   workbench and is recorded in the history (A2); the editor never uses it.
4. **Same validation.** Operations, previews and install use the existing model validators; the dry
   run uses the 0.9 import preview. No second validation path.
5. **Lifecycles unchanged.** Model draft → immutable release → activation; data through a 0.9 import
   job into a change set by default; review on the change set review screen.
6. **Set work in the database.** Profiling statistics and dry runs work on rows staged in PostgreSQL,
   as J2's binding does; nothing iterates a file's rows in Python beyond reading them.
7. **Bounded and paged.** Source profiles, operation history, dry-run rows and inference proposals page
   under ADR-030; every limit is documented and returned in errors.
8. **Keyboard parity and narrow layouts.** Every drag has a menu and keyboard path. Below the desktop
   breakpoint the panes become tabs; the editor remains usable at 390px, not identical.

Excluded: migration-class operations (1.0, on the 0.11 migration boundary), canvas-first authoring,
pixel layouts, general ETL (formulas, joins beyond key lookup, scripting), live links to online
spreadsheets, legacy `.xls`, authentication and authorization (0.12), multi-node operation (0.11),
live co-editing (D10).

## What already exists

- **Model drafts** (`/model-drafts`, `engine/model/drafts.py`): create, whole-model patch with
  `expectedVersion`, delete, validation with JSON Pointer diagnostics, compile, installation;
  releases, diff and activation with the compatibility check. The UI is the JSON workbench
  (`features/model-admin/ModelDraftEditor.tsx`) in Settings › Model. Gated by the model
  administration capability (ADR-031).
- **Import (0.9 J2–J6a):** stored, instance-wide import profiles checked against the active release
  with every problem at its JSON pointer; readers for XLSX (openpyxl, read-only, values), CSV and
  JSON Lines; bindings for fields, attributes, parents, relations (split, `replace`), relation flags,
  related records (translations, system mappings) and value maps; source order by references; a
  preview of up to `IMPORT_PREVIEW_MAX_ITEMS` that writes nothing, confirm, outcomes by row and the
  binding report; the import screen (J4); workbooks for people carrying their profile (J6, J6a).
- **Change sets and review:** P2 lists added, changed, moved and removed records and relationships
  with before and after.
- **Restructuring (ADR-034):** type changes of existing records in change sets, the operation 1.0's
  migration-class operations will reuse.
- **Generic renderers:** table, mapping grid, relation matrix and tree lenses; the detail panel
  registry; object pickers limited by relation bindings and by K7's choice rules; the tree lens's drag
  with Move to… as its keyboard path; the Atlas shell and `ui/` components.

## Design documents

| Document | Holds | State |
| --- | --- | --- |
| This plan | Outcome, tracks, packages, sequence, decisions D1–D16, delivery records, acceptance | Planned 2026-10-11 |
| [MODEL_AUTHORING.md](MODEL_AUTHORING.md) | Editor, operation catalogue, pattern catalogue, navigation groups, API outline, decisions A-D1–A-D12 | Direction accepted 2026-09-29 |
| [API.md](API.md) | Delivered contracts; A0 writes the operation, source file, inference and dry-run designs, each moved to "delivered" by its package | Written in A0 |
| [APPLICATION_MODEL.md](APPLICATION_MODEL.md) | Schema 0.10: the `navigation` declaration | Written in N1 |
| [DECISIONS.md](DECISIONS.md) | ADR-035; a further ADR only for a durable choice found in A0 (the operation history is the candidate) | ADR-035 accepted |
| [USER_JOURNEYS.md](product-functionality/USER_JOURNEYS.md), [API_JOURNEYS.md](testing/API_JOURNEYS.md) | The authoring journeys and their API inventory | Extended in A0 |

## Scope inventory

| # | Roadmap 0.10 item | Stories | Package |
| --- | --- | --- | --- |
| 1 | Import profiles, XLSX, several sheets | US-P09, US-P10 | Delivered in 0.9 J2, J3 |
| 2 | Operation API on model drafts, history, undo | US-P05, US-P09 | A2 (model side), A5 (profile side) |
| 3 | Editor: model pane, relationship matrix, preview, layout editing, navigation groups | US-P05 | N1, A4a, A4b |
| 4 | Source profiling and dry-run summary per operation | US-P09 | A3 |
| 5 | Editor with a source file; saved and re-run profiles | US-P09, US-P10 | A5 |
| 6 | Inference over table patterns; extending an existing model | US-P09 | A6 |
| 7 | Model-description sheets, matching across files | US-P09 | A7 (below the cut line) |
| 8 | List blocks in sheets laid out for reading | US-P09 | A8 (below the cut line) |

## Tracks overview

**The designer line — N1, A2, A4a, A4b, T1.** The editor opened on a model. N1 opens schema 0.10 with
navigation groups. A2 is the operation API: typed, validated operations on a draft with history,
undo and version checks, covering the catalogue's model-side operations. A4a is the editor's model
pane over that API: types in their containment tree, attributes, relation types, the relationship
matrix, issues, history, install and activate. A4b adds the preview, rendered by the generic renderers
from the draft with existing records, where views and panels are laid out. T1 accepts US-P05 on its
own.

**The spreadsheet line — A3, A5, A6, then A7 and A8.** The editor with a workbook. A3 profiles an
uploaded file and runs the dry-run summary after each operation. A5 adds the source and mapping panes,
the mapping operations and the profile side of every model operation, saved profiles and re-runs.
A6 proposes operations from the table patterns. A7 and A8 are the reading of model-description sheets
and of sheets laid out for reading.

**R — build acceptance.** The exit gate of the roadmap and of MODEL_AUTHORING on the acceptance
workbooks, the full review and every suite.

### Why the designer comes first

The user asked for the editor before the spreadsheet functionality (2026-10-11). It fits the design
for four reasons:

- **The editor is where every spreadsheet result is used.** Inference (A6) only proposes operation
  batches; accepting, changing or rejecting a proposal is editing. With the editor built first,
  inference is a producer of operations for a surface that already works, rather than the editor
  being shaped around inference output.
- **The file reading is already there.** 0.9 J2/J3 delivered the readers, profiles and preview. What
  remains on the spreadsheet side is the part with the most uncertainty (profiling and pattern
  rules on real shapes), which is better built against a settled operation vocabulary.
- **It stands on its own.** The designer replaces the JSON workbench for normal changes and answers
  US-P05 even if the spreadsheet line runs late.
- **No dependency is broken.** A4 needed only A2; A3 is needed only by A5.

What it costs, and how the plan covers it:

- **The editor's layout must leave room for the source and mapping panes.** A0's mock-ups cover all
  four panes and the narrow-width tabs, so A5 adds panes to an approved layout instead of redesigning
  A4a's.
- **The dry run on real rows arrives later.** Until A5, the preview shows existing records (as
  MODEL_AUTHORING's "from a model" starting point already says), not workbook rows.
- **The cut line moves.** If time runs out, what is cut is now spreadsheet work at the end (A7, A8,
  then A6), never the designer (D2).
- **A3 is backend only and does not depend on the editor.** It may be taken as a filler while a
  designer package waits for screenshot approval, as V1 was in 0.9.

## How a package is delivered

As in 0.9: each package is one vertical slice, delivered on the instruction **"deliver
`<package>`"** (for example "deliver A2"), in the order of the [delivery queue](#delivery-queue).

1. **Read** the package entry, the design sections it cites, the ADRs it names and `AGENTS.md`.
2. **Plan** under the package (`##### <package> plan (date)`): what is built, checked against the code
   at the current commit; the decisions it raises (D17 onward) with a recommendation; the journey test
   cases. The user accepts the decisions and the test cases before coding.
3. **Mock up first for a new surface.** A package that adds or reshapes a screen (A4a, A4b, A5, A6)
   shows a sample in the browser first and builds on the shape the user approves; it is complete when
   the user approves its screenshots, as 0.9's UI packages were.
4. **Build** the slice: migration when the package names one, service, route, OpenAPI lock
   re-baseline (checked by diffing the document), frontend where the scope says so. Nothing branches
   on application, type, attribute or relation keys (principle 1).
5. **Test** the journeys the plan lists, written first and seen failing, plus unit tests for the new
   code's purpose. Run the package's groups and the changed boundary per
   [EXECUTION_GUIDE §2](testing/EXECUTION_GUIDE.md#2-changed-boundary--selected-checks) only. A new
   module joins `TEST_GROUPS` and the guide's table in the same change. Test work stays a quarter of
   the package or less; no full suite before R.
6. **Record** under the package: **Delivered YYYY-MM-DD.**, what was built, where it differs from the
   design (and amend the design section), and **Checks:** the groups run with their counts, and what
   was not run and why. Move a delivered contract into [API.md](API.md).
7. **Update** CHANGELOG (Unreleased), PROJECT_STATUS and TODO. Commit only when asked.

A package starts when every package it **needs** is delivered. A defect, a revised decision or a new
need found during a package is sorted as 0.9 did: if it changes something the next package builds on,
it is a named amendment package (A2a, …) before the queue continues; otherwise it goes into TODO.

**Names.** Package IDs follow MODEL_AUTHORING's A0–A8, with A4 split into A4a and A4b and navigation
groups as N1. Decisions are D1 onward here and A-D1 onward in MODEL_AUTHORING. Browser runners are
named `test:browser:authoring-<package>` (`e2e/authoring-<package>-*.mjs`), because the 0.8 relation
matrix runners already use `a1`–`a6`.

### Test groups and runners added in 0.10

| Group or runner | Introduced by | Covers |
| --- | --- | --- |
| `authoring` marker | A2 | Operations, history, undo, generated defaults, source profiles, dry runs, inference |
| `test:browser:authoring-n1` | N1 | Sidebar groups and the group page |
| `test:browser:authoring-a4a`, `-a4b` | A4a, A4b | The designer journeys |
| `test:browser:authoring-a5`, `-a6` | A5, A6 | The spreadsheet journeys |

Existing groups carry on: `model` (every model contract change), `jobs` (imports), `startup` (every
migration), `contract` (every route change) and `volume` (every budget).

## Delivery queue

| # | Package | Needs | Scope in one line |
| --- | --- | --- | --- |
| 0 | — | 0.9.0 released | **Met 2026-10-11**, tag `v0.9.0` |
| 1 | [A0](#a0-design-pass) | — | Decisions D1–D10 and A-D5–A-D9; API design; operation vocabulary; journeys; mock-ups of the editor; workbook shapes |
| 2 | [N1](#n1-navigation-groups-and-schema-010) | A0 | Schema 0.10 with `navigation`; sidebar groups and the group page |
| 3 | [A2](#a2-operation-api-on-model-drafts) | A0, N1 | `POST …/operations`, history, undo and redo; the model-side catalogue; generated defaults for new types |
| 4 | [A4a](#a4a-editor--model-pane) | A2 | The editor frame and model pane, relationship matrix, issues, history, install and activate |
| 5 | [A4b](#a4b-editor--preview-and-layout-editing) | A4a | Preview with existing records; views, panels and fields laid out in place |
| 6 | [T1](#t1-designer-checkpoint) | A4b | US-P05 composed in the browser on two models; the designer's gates; tagged `v0.10.0-alpha.1` (D14) |
| 7 | [A3](#a3-source-profiling-and-the-dry-run-summary) | A0 | Source files, profiles of sheets and columns, the dry-run summary; W1–W3 generators. May be taken earlier as a filler |
| 8 | [A5](#a5-editor-with-a-source-file) | A3, T1 | Source and mapping panes, mapping operations, profiles following the model, load, saved profiles and re-runs |
| 9 | [A6](#a6-inference-over-table-patterns) | A5 | Proposals from the table patterns; new application or extending the active model; pinned decisions |
| — | _cut line (D2)_ | | _If R is out of reach, 0.10.0 releases here and A7, A8 move to 0.10.x_ |
| 10 | [A7](#a7-model-description-sheets-and-matching-across-files) | A6 | Model-description sheets; matching records across files |
| 11 | [A8](#a8-list-blocks-in-sheets-laid-out-for-reading) | A6 | List blocks detected, confirmed and loaded |
| 12 | [R](#r-build-acceptance-and-release) | all | Build acceptance and release |

## Sequence and dependencies

```text
Design:       A0
Designer:     A0 ─ N1 ─ A2 ─ A4a ─ A4b ─ T1
Spreadsheet:  A0 ─ A3 ─────────────────────┐          A3 may fill a gap in the designer line
                              T1 ──────────┴─ A5 ─ A6 ─┬─ A7
                                                       └─ A8
              ── cut line (D2) between A6 and A7 ──
Release:      T1, A6 (A7, A8 above the cut) → R
```

## Acceptance workbooks

only. The repository gets **synthetic workbooks generated by test code** with the same shapes, so
fixtures are deterministic and contain no client data. A3 writes the generators, building on J2's
workbook helpers in the import tests.

- **W1 — flat table.** ~200 rows, one per record: a unique code column; a parent repeated per row with
  its sort order and an external ID; a lookup stored as text including placeholder values (`N/A`); a
  code and name pair forming a second list, with two codes carrying two different names; two
  true/false columns and a text column that together express one relationship (the text column
  semicolon-separated on some rows); an external-system ID column; a second sheet with one row per
  record and language (7 languages), one of whose names differs from the main sheet.
- **W1′ — the next version of W1.** Five records changed, three added, two missing, one new list
  value, one new column, one renamed column.
- **W2 — model description.** A sheet with field code, field type and lookup target; one sheet per
  lookup with IDs and names; placeholder IDs (`?`), a "to be defined" list, names that drift from W1 for
  the same IDs, and only part of W1's IDs present.
- **W3 — layout sheet.** Twenty to forty lists placed side by side under section and group headers,
  separated by empty columns; some with a column per language, some with Y/N flags per item, some with
  a "multiple answers" note under the header.

The designer packages need no workbook: they run on the starter model with its keys renamed and on a
second, differently shaped generated model. The spreadsheet journeys run on W1 and W2, A8's on W3.

## A0: Design pass

**Scope:**

- Settle D1–D10 and A-D5–A-D9; record A-D4 and A-D10 as taken by 0.9 J2.
- Write the API design in API.md's style for operations and history, source files and their
  profiles, the dry-run summary and inference proposals.
- Fix the operation vocabulary: one kind per catalogue row, with its parameters, its inverse, its
  class and whether it has a profile side (A5).
- Add the authoring journeys to USER_JOURNEYS and API_JOURNEYS.
- **Mock up the editor** in the browser: all four panes, the issues list and history, the
  relationship matrix, the narrow-width tabs and the keyboard paths of the drags. The user approves
  the layout before A4a builds on it.
- Define the shapes of the synthetic workbooks and of the second designer model in test terms.

**Exit:** decisions recorded; API design written; journeys added; the editor's layout approved;
package scopes confirmed or adjusted here.

**Checks:** documentation and a throwaway mock-up, removed afterwards; no product code.

## Track: the designer

### N1: Navigation groups and schema 0.10

**Design:** [MODEL_AUTHORING navigation groups](MODEL_AUTHORING.md#navigation-groups), A-D2, A-D11,
A-D12, ADR-029. **Needs:** A0.

**Scope:**

- Schema language 0.10 (D1): the optional `navigation.groups` on an application, with its
  validation (each entry a collection of the application, a collection in at most one group, unique
  group keys) and APPLICATION_MODEL's section. Earlier schema versions stay valid.
- The sidebar shows declared groups as labelled, collapsible sections; ungrouped collections stay at
  the top level in their current order.
- The group page: its collections with a search over their names, reachable from the group's header.
- Read through the existing model and application routes; no new data, no migration.

**Tests:** the `navigation` contract (valid, unknown collection, a collection in two groups,
duplicate group key, absent field unchanged); a model of schema 0.9 activating unchanged. Browser
(`test:browser:authoring-n1`): a grouped and an ungrouped application in the sidebar, collapse and
expand, the group page and its search, keyboard alone, 1440px and 390px.

**Groups:** `model`, `contract`, `startup` (schema activation).

**Exit:** schema 0.10 accepted by the compiler; the sidebar and group page approved from screenshots.

### A2: Operation API on model drafts

**Design:** [MODEL_AUTHORING operation catalogue](MODEL_AUTHORING.md#operation-catalogue), A0's API
design, D4, D6, D8, D10, D13. **Needs:** A0, N1.

**Scope:**

- `POST /model-drafts/{id}/operations`: a batch of operations at `expectedVersion`, applied
  atomically to the draft's model, validated by the existing validators, returning the new version
  and diagnostics.
- The catalogue's **model-side** kinds: names and keys, types (add, remove, split, merge), attributes
  (add, attach an existing global attribute type, move, value type, required, unique), structure
  (containment, allowed relations, cardinality), views and panels, navigation groups. A draft-only
  kind on an element present in the base release is refused with `OPERATION_REQUIRES_MIGRATION`
  (0.9's upper-case codes), its impact reported and nothing applied. Mapping and value kinds are A5's.
- **Generated defaults:** adding an object type gives it a table view and detail panels from its
  bindings, produced by the server, so an API client gets the same result as the editor.
- Keys generated from labels and editable until installed (A-D6).
- Operation history (`GET …/operations`, paged), stored per draft with author (the local session until
  0.12), time, draft version and the inverse (D4).
- Undo and redo as inverse operations; undoing an operation that later operations depend on is
  refused with the dependants listed (D8).
- A whole-model `PATCH` on a draft is recorded as one `replaceModel` operation, so the history stays
  complete.
- A stale `expectedVersion` is `409` with the operations applied since (D10).

**Tests:** journeys through the API: build a small application from an empty draft (types,
attributes, a relation, a group), undo part of it, install and activate it, create a record; the
same on the starter model with renamed keys; a batch that fails applies nothing; a stale version
answered with the newer operations; a dependent undo refused; `OPERATION_REQUIRES_MIGRATION` on a
released element; diagnostics equal to whole-model validation of the same result. Unit tests per
operation kind and its inverse.

**Groups:** `authoring` (new), `model`, `contract`, `startup` (the history table).

**Exit:** every model-side kind in API.md with its inverse; a draft built only through operations
installs.

### A4a: Editor — model pane

**Design:** [MODEL_AUTHORING the editor](MODEL_AUTHORING.md#the-editor), A0's approved mock-up, D7.
**Needs:** A2.

**Scope:**

- The editor frame where D7 places it: opened on a draft of the active release or on an empty draft;
  "Open as JSON" keeps the workbench one step away.
- The model pane: applications, types in their containment tree, each type's attributes, relation
  types; elements marked new, changed or released. The relationship matrix of allowed relations
  between types, reusing the relation matrix's grid component where it fits.
- Every model-side operation from menus and the keyboard; drag an attribute to another type and a
  type under another parent, with Move to… as the keyboard path (as the tree lens's B5).
- The issues list (each issue linked to its element), the history with undo and redo, and a stale
  version handled by replaying or asking.
- Navigation group operations on the application.
- Install and activate as one confirmed step with the compatibility check shown (A-D8).

**Tests:** browser (`test:browser:authoring-a4a`): add a type with attributes and a relation,
reorganize by drag and by keyboard, group collections, undo and redo, install and activate, then open
the new collection and create a record; on both designer models; keyboard alone; 1440px and 390px;
axe on the editor's main states; visual baselines.

**Groups:** frontend unit tests for the new components; `authoring` only if a route changes.

**Exit:** screenshots approved; the JSON workbench is no longer needed for a normal additive change.

### A4b: Editor — preview and layout editing

**Design:** [MODEL_AUTHORING views and layouts](MODEL_AUTHORING.md#views-and-layouts), UI_MODEL.md.
**Needs:** A4a.

**Scope:**

- The preview: a record of the selected type rendered by the generic renderers from the draft
  (compiled, not installed), using an existing record of the active workspace, or an empty one for a
  new type; its detail panels, its pickers with the candidates they would offer, its table row.
- Layout editing in place, each change a view operation (A2): panels ordered within `main` and
  `side`, shown or hidden, their columns and default sort; a table view's columns, filters and default
  sort; field order and grouping; a field's editor where the registry declares more than one.

**Tests:** browser (`test:browser:authoring-a4b`): lay out a new type's detail page and table view,
undo a layout change, install, and find the same layout on the record screen; on both designer
models; keyboard alone; 1440px and 390px; axe; visual baselines. Backend: the preview reads the
draft's compiled model and writes nothing.

**Groups:** `authoring`, `model` if the compile path changes; frontend unit tests.

**Exit:** screenshots approved.

### T1: Designer checkpoint

**Needs:** A4b.

US-P05 composed in the browser over the real backend on both designer models: an application
designed from an empty draft and the starter model extended, through to records created in the new
types. Keyboard alone, 1440px and 390px, the accessibility and visual gates for the editor's
surfaces, and the `authoring` and `model` groups together. As 0.9's T1 did for Q, B and F, it confirms
the line before the next one builds on it, so R confirms rather than discovers.

**Interim release 0.10.0-alpha.1 (D14).** When T1 passes, the designer is released as
0.10.0-alpha.1, as 0.9.0-alpha.1 released the PostgreSQL runtime: CHANGELOG section, version strings,
a migration check (clean bootstrap and upgrade from 0.9.0, schema 0.9 → 0.10 activation), and the
tag `v0.10.0-alpha.1` with the commit on the user's instruction. It is not a full R: the full suites
and the full review of every change wait for 0.10.0's R, which still reviews everything since 0.9.0.

## Track: the spreadsheet

### A3: Source profiling and the dry-run summary

**Design:** [MODEL_AUTHORING concepts and recurring loads](MODEL_AUTHORING.md#concepts), J2's
binding, J3's preview, D5, D6, D9. **Needs:** A0.

**Scope:**

- `POST /source-files` on 0.9 job file storage and limits, attachable to a draft (D5).
- `GET /source-files/{id}/profile`, built by a job: sheets, header row, data ranges and blocks, and
  per column fill, distinct count, value types, candidate key, delimiters, placeholders and value
  overlap with other columns and with existing records of mapped types. Computed in PostgreSQL over
  staged rows (principle 6); paged by sheet and column.
- The dry-run summary: for a draft with source files and a profile, the J3 preview run against the
  draft's model, returning counts per source (records, values, relations, related records),
  rejections by code and the difference from the previous summary, each figure linking to a paged
  row list. Within the interactive budget up to a row limit, on a deterministic sample above it with
  the full run on request, and the response says which (D9).
- The W1, W1′, W2 and W3 generators.

**Tests:** W1, W2 and W3 profiled (header and block detection, statistics); the dry run on W1 after a
rename, a move and a value map, with its difference; the sample-versus-full switch at the limit; the
budget measured once and recorded.

**Groups:** `authoring`, `jobs`, `contract`, `startup` (if a table is added), `volume` (the budget).

**Exit:** profiles and summaries in API.md; the budget recorded.

### A5: Editor with a source file

**Design:** [MODEL_AUTHORING layout and recurring loads](MODEL_AUTHORING.md#recurring-loads-and-reconciliation),
D12, D13, A-D7. **Needs:** A3, T1.

**Scope:**

- "New from a workbook" and "Add a workbook" to an open draft; the source pane (sheets, blocks,
  columns with status and statistics) and the mapping pane (column to target with its
  transformation), synchronized with the model pane, in the layout approved in A0.
- The mapping and value operations: map, re-read as text/lookup/relation/flags, split, unpivot, value
  maps, ignore, add values found to a list, turn an attribute's values into a list type; drag a column
  onto a target with its keyboard path.
- The profile side of every model operation (D13): a renamed key rewritten in the draft's profile, a
  moved attribute's column following it, a removed target's binding becoming an unmapped column with
  a diagnostic, split and merge carrying their columns and value maps.
- The draft's profile checked against the draft's model while editing and saved as an instance
  profile when the draft is installed and activated (D12).
- The dry-run summary after every operation, linking to the rows.
- Load: install and activate if the model changed, run the import job into a new change set by
  default, and open the change set review.
- Saved profiles: upload the next version to a profile; new, missing and renamed columns, new values
  and drift reported before loading (US-P10); missing records reported, never deleted unless the
  profile says so (A-D7).

**Tests:** browser (`test:browser:authoring-a5`): W1 mapped by hand onto a new application, loaded into
a change set, reviewed and published; W1′ through the saved profile with only its differences in the
review; a rename and a move after mapping keep the profile valid; keyboard alone; 1440px and 390px;
axe. Backend journeys: the profile following rename, move, split and merge; the saved profile
re-checked against a newer release; missing-record handling.

**Groups:** `authoring`, `jobs`, `contract`; frontend unit tests.

**Exit:** screenshots approved; W1 and W1′ load without JSON or code.

### A6: Inference over table patterns

**Design:** [MODEL_AUTHORING pattern catalogue](MODEL_AUTHORING.md#pattern-catalogue), A-D5.
**Needs:** A5.

**Scope:**

- The table patterns: key column, code and name pair, repeated parent, level columns, text lookup,
  reference to another sheet, multi-valued cell, flag columns, translations by row and by column,
  external IDs, placeholder values, name drift, and navigation group proposals from sheet names.
- `POST /model-drafts/{id}/inferences`: proposals as operation batches with evidence and
  alternatives, applying nothing; accepting one applies its batch through A2.
- Two starting modes: a new application, or extending the active model by matching columns to existing
  types and attributes (label similarity and bounded value overlap with existing records).
- Pinned decisions: elements changed or confirmed by the administrator are pinned; re-inference
  reports disagreements and never overrides them.
- The optional assistant (A-D5) is an interface only; no provider is bundled.

**Tests:** each pattern found on W1 or W2 with its evidence and not on a control column; W1 from upload
to published change set, accepting, changing and rejecting proposals; re-inference after edits keeps
pinned decisions; W1 onto the starter model extends it rather than duplicating its attributes. Browser
(`test:browser:authoring-a6`): the W1 journey; keyboard alone; 1440px and 390px.

**Groups:** `authoring`, `contract`; frontend unit tests.

**Exit:** screenshots approved; the roadmap's first exit gate line holds on W1.

### A7: Model-description sheets and matching across files

Below the cut line (D2). **Needs:** A6.

**Scope:** recognize a model-description sheet and read it before the lookup sheets it names; propose
types, attributes and relations from it; match records across workbooks by ID or code, report name
drift and missing IDs, and propose value maps.

**Tests:** W2 alone becomes an application; W2 then W1 into the same draft reconcile by ID with drift
reported; placeholders and "to be defined" lists reported, not loaded as values.

### A8: List blocks in sheets laid out for reading

Below the cut line (D2). **Needs:** A6.

**Scope:** detect header-and-values blocks, section and group headers, language column pairs, Y/N
flags and cardinality notes; propose one source per block; the administrator confirms, adjusts or
drops each block in the source pane (A-D9). Colour and formatting carry no meaning.

**Tests:** W3's blocks detected with their headers; confirmed blocks become list types in proposed
navigation groups; an adjusted block boundary; a language pair becomes translations.

## R: Build acceptance and release

- A full review of every change since 0.9.0 first, as every R.
- US-P09 on W1 and W2 and US-P10 on W1′ (W1 and W1′ only if A7 and A8 moved), composed in the
  browser over the real backend, keyboard alone, 1440px and 390px, with the accessibility and visual
  gates.
- The designer on both designer models (US-P05, additive and draft-only), repeated from T1.
- The [MODEL_AUTHORING exit gate](MODEL_AUTHORING.md#exit-gate) and the roadmap 0.10 exit gate.
- A3's budget met on the recorded fixture sizes.
- Migrations: clean bootstrap, upgrade from 0.9.0, schema 0.9 → 0.10 activation, a 0.9 model still
  valid.
- Full suites per AGENTS.md; documents and versions; tag on the user's instruction.

## Composable domains check (ADR-032)

As recorded in [MODEL_AUTHORING](MODEL_AUTHORING.md#composable-domains-check-adr-032): identity and
inbound flow use 0.9 upsert keys; provenance gains the profile key as a natural source name on import
jobs; audit and data history are unchanged (the operation history is model-draft history); value
types convert through the attribute registry; the `match` declaration and mapping coverage are not
touched. No door is affected.

## Invariant notes

- **Model references runtime data.** Rejected (A-D1): list scoping is structural, one type per list.
- **Install and activate in one step.** Both lifecycle steps still run, in order, with the
  compatibility check shown; the step is refused on any diagnostic (A-D8). A convenience, not a bypass.
- **Stable keys.** Keys change only while unreleased; afterwards a key change is a migration-class
  operation, refused in 0.10.
- **Live by default.** An onboarding load goes to a change set by default because it creates many
  records at once and the administrator asked to review it; a recurring profile load may target live
  data like any 0.9 import. This is the import's choice, not a new mandatory step.
- **Preview of an uninstalled model.** A4b renders the draft's compiled model in the editor only;
  runtime routes keep serving the active release.

## Decisions

D11–D16 accepted by the user on 2026-10-11 (D14 changed from its recommendation). D1–D10 are open
and settled in A0 unless a package is named; the recommendation is the planning default.
Design-level decisions are [A-D1–A-D12](MODEL_AUTHORING.md#open-decisions).

| # | Question | Recommendation | Blocks |
| --- | --- | --- | --- |
| D1 | Schema language version | 0.10, adding only the optional `navigation` declaration; earlier versions stay valid; the starter moves to it only if it declares groups (D3) | N1 |
| D2 | Cut line | A7 and A8 may move to 0.10.x; R then accepts W1/W1′ and the designer. If more must go, A6 next, with the designer and manual mapping (A5) released | R |
| D3 | Starter model | Unchanged unless a group improves it; acceptance uses the generated models | N1, R |
| D4 | Where operation history lives | A table per draft operation (kind, parameters, inverse, author, time, draft version); deleted with its draft; an installed release keeps no operation history | A2 |
| D5 | Source files attached to drafts and profiles | Stored as 0.9 job files; the latest file per draft and per profile kept while they exist (outside D14 retention) so it can be edited again; older ones follow D14 | A3, A5 |
| D6 | Capability gates | Operations, inference and install under the model administration gate; source upload and import under `INTEGRATION_JOBS_ENABLED` | A2, A3 |
| D7 | Where the editor lives | Opened from Settings › Model on a draft ("Open in editor") and by "New from a workbook" (A5), as a full-width workspace rather than inside the settings layout; no new top-level destination; the JSON workbench stays | A4a |
| D8 | Undo with dependent operations | Refused with the dependants listed; the client offers to undo them together | A2 |
| D9 | Interactive dry-run budget | A summary within 1 s for up to 10,000 rows on the reference machine; a deterministic sample above that with the full run on request; measured once in A3 | A3 |
| D10 | Concurrent editors | Optimistic versions only; no locks or live co-editing | A2, A4a |
| D11 | Order of the lines | **Accepted 2026-10-11:** the designer line before the spreadsheet line, as the user requested (see [why](#why-the-designer-comes-first)); A3 may fill a gap | All |
| D12 | Which model a draft's profile is checked against | **Accepted 2026-10-11:** the draft's own model while editing; saved as an instance profile on install and activate, so instance profiles keep resolving against the active release as J2 defined (D65) | A5 |
| D13 | Profile effects of model operations | **Accepted 2026-10-11:** in A5, not A2: before A5 no draft holds a profile, and an instance profile cannot name an unreleased element, which is all a draft-only operation may touch | A2, A5 |
| D14 | An interim release after T1 | **Accepted 2026-10-11, changed by the user:** the designer is released as 0.10.0-alpha.1 when T1 passes, tagged `v0.10.0-alpha.1` ([T1](#t1-designer-checkpoint)). The recommendation was a checkpoint without a release | T1 |
| D15 | Split and merge of types in A2 | **Accepted 2026-10-11:** in A2 as model operations on unreleased types (their profile side in A5); they are in the roadmap's exit gate and their inverses shape the history format | A2 |
| D16 | The preview's data before A5 | **Accepted 2026-10-11:** an existing record of the active workspace for a released type, an empty record for a new type; never a write | A4b |

## Risks

- **Scope.** This is an editor plus inference on top of 0.9's import. The designer first and the cut
  line (D2) keep a usable release in reach.
- **The editor is the hardest UI so far.** A multi-pane editor with drag and drop; the layout is
  approved as a mock-up in A0 and keyboard paths are designed with each interaction, not added at the
  end.
- **Inference quality on real files.** Mitigated by proposals with evidence, pinned decisions and the
  editor as the real product: a weak proposal costs edits, not a wrong load.
- **Dry-run speed.** Measured once in A3; sampling above the budget.
- **The designer built before real workbook rows.** The A0 mock-up includes the source and mapping
  panes so A5 extends the layout rather than reworking it.

## Next

1. A0: settle D1–D10 and A-D5–A-D9, and the editor mock-up.
