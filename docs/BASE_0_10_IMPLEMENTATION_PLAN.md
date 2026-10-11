# Base 0.10 implementation plan

**Status:** Planned 2026-10-11, after 0.9.0, replacing the provisional plan of 2026-09-29. **The
designer line comes first** (D11, requested by the user 2026-10-11): the editor opened on a model,
without a workbook, is built and checked before the spreadsheet profiling, mapping and inference it
later hosts. A-D1–A-D3 are decided; A-D4 and A-D10 were taken by 0.9 J2 (D64–D74); **D11–D16 are
accepted by the user (2026-10-11)**, D14 changed to tag an interim release after T1; **D1–D10,
D17–D21 and A-D5–A-D9 were accepted with the [A0 plan](#a0-plan-2026-10-11) the same day.** Work packages A0, N1, A2, A4a, A4b,
T1, A3, A5–A8 and R are specified below at package level; each package's detailed plan, test cases
and decisions are written and accepted when it starts, and it is delivered in the order of the
[delivery queue](#delivery-queue), each by the [delivery steps](#how-a-package-is-delivered).
**Delivered:** A0, N1, A2 (2026-10-11).

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

**The designer line — N1, A2, A4a, A4b, A4c, T1.** The editor opened on a model. N1 opens schema 0.10 with
navigation groups. A2 is the operation API: typed, validated operations on a draft with history,
undo and version checks, covering the catalogue's model-side operations. A4a is the editor's model
pane over that API: types in their containment tree, attributes, relation types, the relationship
matrix, issues, history, install and activate. A4b adds the preview, rendered by the generic renderers
from the draft with existing records, where views and panels are laid out. T1 accepts US-P05 on its
own. A4c, added by the user after A4a, puts a consumer API editor beside the
model editor, as a second tab of the editor's left pane.

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
3. **Mock up first for a new surface.** A package that adds or reshapes a screen (A4a, A4b, A4c, A5, A6)
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
| 1 | [A0](#a0-design-pass) | — | **Delivered 2026-10-11.** Decisions D1–D10 and A-D5–A-D9; API design; operation vocabulary; journeys; mock-ups of the editor; workbook shapes |
| 2 | [N1](#n1-navigation-groups-and-schema-010) | A0 | **Delivered 2026-10-11.** Schema 0.10 with `navigation`; sidebar groups and the group page; the phone band |
| 3 | [A2](#a2-operation-api-on-model-drafts) | A0, N1 | **Delivered 2026-10-11.** `POST …/operations`, history, undo and redo; the model-side catalogue; generated defaults for new types |
| 4 | [A4a](#a4a-editor--model-pane) | A2 | **Delivered 2026-10-11.** The editor frame and model pane, relationship matrix, issues, history, install and activate |
| 5 | [A4b](#a4b-editor--preview-and-layout-editing) | A4a | Preview with existing records; views, panels and fields laid out in place |
| 6 | [A4c](#a4c-editor--consumer-apis) | A4a, A4b | **Added by the user 2026-10-11.** The consumer API editor: a Consumer APIs tab beside Model in the editor; consumer API definitions changed by operations. Planned in detail when it comes |
| 7 | [T1](#t1-designer-checkpoint) | A4b, A4c | US-P05 composed in the browser on two models; the designer's gates; tagged `v0.10.0-alpha.1` (D14) |
| 8 | [A3](#a3-source-profiling-and-the-dry-run-summary) | A0 | Source files, profiles of sheets and columns, the dry-run summary; W1–W3 generators. May be taken earlier as a filler |
| 9 | [A5](#a5-editor-with-a-source-file) | A3, T1 | Source and mapping panes, mapping operations, profiles following the model, load, saved profiles and re-runs |
| 10 | [A6](#a6-inference-over-table-patterns) | A5 | Proposals from the table patterns; new application or extending the active model; pinned decisions |
| — | _cut line (D2)_ | | _If R is out of reach, 0.10.0 releases here and A7, A8 move to 0.10.x_ |
| 11 | [A7](#a7-model-description-sheets-and-matching-across-files) | A6 | Model-description sheets; matching records across files |
| 12 | [A8](#a8-list-blocks-in-sheets-laid-out-for-reading) | A6 | List blocks detected, confirmed and loaded |
| 13 | [R](#r-build-acceptance-and-release) | all | Build acceptance and release |

## Sequence and dependencies

```text
Design:       A0
Designer:     A0 ─ N1 ─ A2 ─ A4a ─ A4b ─ A4c ─ T1
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

**In test terms** (A0, 2026-10-11). A generator takes a seed and a size and writes the workbook;
tests name these structures, never a header text, as the journey configurations do. Headers are
plain business words in an invented neutral domain.

- **W1**, sheet `S1` (one row per record, `n` rows, default 200): `K` the key (unique, fully filled,
  code-like); `N` the name; `P` a parent name repeated per row (about `n/15` distinct) with `Po` (its
  sort order) and `Pi` (its external ID), both constant per `P`; `T` a text lookup (about 8 distinct)
  with `N/A` and `-` on about 5% of rows; `Lc` and `Ln` a code and name pair (about 6 codes) where
  two codes each carry two different names; `F1`, `F2` two Y/N columns and `Fo` a text column, `;`
  separated on some rows, together naming members of one set; `X` a GUID per row (an external
  system's ID). Sheet `S2`: `K`, `Lang` (7 language codes) and `N` translated, one row per record and
  language, one `N` differing from `S1`'s for its language.
- **W1′** = W1 with 5 records changed, 3 added, 2 missing, one new `T` value, one new column `Y`, and
  `Ln` renamed.
- **W2**: sheet `D` (columns field code, field type, lookup target) describing W1's `T`, `Lc` and
  flag set; one sheet per lookup with ID and name; `?` IDs, one list marked "to be defined", names
  drifting from W1 for the same IDs, and only part of W1's IDs present.
- **W3**: one sheet with 20–40 blocks (`B`), each a header and values, side by side, separated by
  empty columns, under section and group header rows; some blocks with a column per language, some
  with Y/N columns per item, some with a "multiple answers" note under the header.

The designer packages need no workbook: they run on the starter model with its keys renamed and on
the journey configuration `generated-b` (D20). The spreadsheet journeys run on W1 and W2, A8's on W3.

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

##### A0 plan (2026-10-11)

**Planned 2026-10-11; accepted by the user the same day ("you can go ahead"), every decision as
recommended.** Checked
against the code at `29aac8e`:

- **Drafts** (`engine/model/drafts.py`, `model_drafts`): a draft has `version`, `model_json` and an
  optional `base_model_release_id`. Its lifecycle is written to `audit_events` (`model_draft`
  created, updated, deleted, with a summary of the changed fields), but nothing reads that as the
  draft's history: J08.9, "read a model draft's history", is planned and unbuilt (API_JOURNEYS D-5).
- **Installation** (`POST /model-drafts/{id}/installation`) leaves the draft as it was: open,
  editable, its base release unchanged. Installing the same `release.key` and `release.version` with
  different content is `409 RELEASE_IDENTITY_CONFLICT`; the release identity (`key`, `name`,
  `version`) sits in the model document.
- **Compile** diffs the draft against its base release, or the active release when it has none
  (`semantic_diff`), and runs the compatibility check against the active release. This is what the
  editor's new, changed and released marks and the draft-only check can stand on.
- **Gate:** `MODEL_ADMIN_MUTATIONS_ENABLED`, which requires `WEB_CONCURRENCY=1`; installation runs
  under an in-process lock and takes the draft row `FOR UPDATE`.
- **Schema:** `schemaVersion` accepts 0.5–0.9. `ApplicationDefinition` allows extra members, so a
  0.9 document holding `navigation` is accepted today and the member is ignored.
- **Job files** (`engine/jobs/files.py`) are named after their job and live only as long as it:
  an import's upload goes when its job finishes, and `reconcile` deletes any file without a job.
  Nothing there can hold a file a draft keeps for weeks.
- **Test models:** journey tests run on `generated-a`, `generated-b` and the example
  (`tests/journeys/configurations.py`), named by structure (`R`, `H`, `P`/`C`, `Bnn`, …).
- **Frontend:** the JSON workbench (`features/model-admin/ModelWorkbench.tsx`,
  `ModelDraftEditor.tsx`) in Settings › Model; `RelationMatrixView` is a records grid that pages
  records and cell states from the server, not a grid of types.
- **Inventory check** (`tests/test_api_journeys.py`) requires every served route, parameter, code and
  setting to be listed, and every journey the inventory cites to exist. Planned routes may be listed
  before they exist.

**What A0 produces**, in this order, each with its approval point:

1. **Decisions.** The user accepts or changes D1–D10, the new D17–D21 and A-D5–A-D9 below. They are
   then recorded here and in MODEL_AUTHORING, and the package scopes are amended where a decision
   changes them (listed with each decision).
2. **The operation vocabulary** in API.md, under a "Designed for 0.10" heading that each package
   moves into "delivered". It has one row per kind, with its parameters, inverse, class and profile
   side (A5). The first cut is below. The final list is written against `models/schema.py`, so every
   kind names a real model element.
3. **The API design** in API.md's style: operations and history, source files and their profiles,
   the dry-run summary and inference proposals. It is written at contract level (routes, bodies,
   codes, paging, limits); the field-level detail of A3's and A6's parts is finished in those
   packages' plans.
4. **Journeys.** USER_JOURNEYS gains J33, J34 and J35 (below), and J08.9 is pointed at the operation
   history. API_JOURNEYS gains the planned routes, codes and settings with their journeys.
5. **The editor mock-up**, published as a claude.ai artifact as U1's mock-ups were: clickable, built
   on the Atlas tokens, light and dark, 1440px and 390px. It uses an invented neutral domain, not the
   example model. The user approves it, possibly after revisions, and the approved link is recorded
   here.
6. **The workbook shapes** W1–W3 written out in test terms (structures, as `configurations.py` names
   them), plus a one-sheet sample of W1's main sheet (about 20 rows) for the user to open in their
   own spreadsheet program before the shape is fixed.
7. **ADR-041** if D4 is accepted as recommended.
8. **The A0 record**: the decisions as taken, the mock-up link, the scope amendments, and the checks.

**Mock-up screens** (one artifact, switchable):

- The editor opened on a draft of the active release: model pane (applications, the containment
  tree, a type's attributes, relation types), preview, issues and history; new, changed and released
  marks; the source and mapping panes shown as the places A5 fills.
- The relationship matrix of allowed relations between types: a cell's menu to allow or remove a
  relation and set its cardinality.
- The editor with a workbook (A5's layout): source, mapping, model and preview together, with the
  dry-run summary and its difference after an operation.
- Keyboard paths: Move to… for an attribute and for a type, the context menu with the operations for
  the selected element, undo and redo.
- Install and activate as one confirmed step: the release version (D18), the differences and the
  compatibility result.
- 390px: the panes as tabs, the same editor reachable.

**Operation vocabulary, first cut** (model side; mapping and value kinds are A5's and written in A0
only by name):

| Group | Kinds | Class |
| --- | --- | --- |
| Names | `setLabel` (any element) · `setKey` (any element) | additive · draft-only |
| Release | `setRelease` (key, name, version; D18) | additive |
| Applications | `addApplication` · `removeApplication` | additive · draft-only |
| Types | `addObjectType` (with generated views and panels) · `removeObjectType` · `splitObjectType` · `mergeObjectTypes` · `convertAttributeToListType` | additive · draft-only ×4 |
| Attributes | `addAttributeType` · `attachAttribute` · `detachAttribute` · `moveAttribute` · `setValueType` · `setAttributeRule` (required, unique) | additive ×2 · draft-only ×4 |
| Structure | `setContainment` · `addRelationType` · `allowRelation` · `disallowRelation` · `setRelationRule` (cardinality, required) | draft-only · additive ×2 · draft-only ×2 |
| Views and panels | `addView` · `removeView` · `insertViewItem` · `moveViewItem` · `removeViewItem` · `setViewProperty` (D19) | additive |
| Navigation | `addNavigationGroup` · `removeNavigationGroup` · `setNavigationGroup` · `placeCollection` | additive |
| Whole model | `replaceModel` (written by `PATCH`, never sent by the editor) | — |

Every kind's inverse is a kind of this table, or the stored prior state of the element it replaced
(`replaceModel`, `removeObjectType`, `mergeObjectTypes`).

**Journeys** (wording final in USER_JOURNEYS; the variants are the ones the packages' test cases
will walk):

- **J33 Design a model in the editor** (US-P05; A2, A4a, A4b, N1). Variants: build an application
  from an empty draft; extend the active model; undo and redo; an undo with dependants; a stale
  version answered with the newer operations; a draft-only operation on a released element refused
  with its impact; group collections; lay out a type's table and detail page; install and activate,
  then work with records of the new type.
- **J34 Onboard a workbook** (US-P09; A3, A5, A6). Variants: upload and profile; accept, change and
  reject proposals; map by hand; the dry run after an operation; load into a change set and review
  it; extend the active model rather than duplicate it.
- **J35 Load the next version of a workbook** (US-P10; A5). Variants: differences reported before
  loading (new, missing and renamed columns, new values, drift); missing records reported and kept;
  only the differences in the change set review.
- **J08.9** (planned) becomes the operation history read, delivered by A2.

**Decisions** (accepted 2026-10-11). D1–D10 are the plan's, restated where the code changed the
recommendation; D17–D21 are new from the check above.

| # | Question | Recommendation |
| --- | --- | --- |
| D1 | Schema language version | **As planned, with one addition.** 0.10 adds only the optional `navigation` member, and earlier versions stay valid. The addition: below 0.10 a `navigation` member is refused at its pointer, as 0.9 K5 refused `related:` below 0.9. Today an application allows extra members, so without this a 0.9 document carrying `navigation` would be accepted and the groups would silently do nothing. Amends N1's tests |
| D2 | Cut line | As planned: A7 and A8 first, then A6 |
| D3 | Starter model | As planned: unchanged unless a group improves it |
| D4 | Where operation history lives | **As planned, with its relation to the audit stated.** A `model_draft_operations` table (kind, parameters, inverse, author, time, draft version), paged, deleted with its draft. It is the answer to J08.9. The audit events stay as they are (API_JOURNEYS D-5 decided to keep capturing them); the history adds what they lack, the parameters and inverse of each change. Recorded as ADR-041 ("model drafts change only through recorded operations"), since every later authoring package builds on it |
| D5 | Source files | **Changed: a resource of its own, not job files.** Job files live and die with their job (checked above), and a source file belongs to a draft or a profile for as long as they exist. Proposed: a `source_files` row (owner, name, format, size, SHA-256) with the file in `JOB_FILE_DIR` under its own name, `IMPORT_MAX_BYTES` as the limit, `reconcile` taught its names, the latest file per owner kept and older ones removed after the job retention period. An import may then name a stored source file instead of sending it again. Amends A3's scope (the table, the reconcile rule) and A5's (the load names the file) |
| D6 | Capability gates | **As planned.** Operations, inference, install and activate under `MODEL_ADMIN_MUTATIONS_ENABLED`; uploading source files, profiling and dry runs (jobs) also under `INTEGRATION_JOBS_ENABLED`. The editor with a workbook needs both settings; without the second, its workbook actions are absent, as other routes are |
| D7 | Where the editor lives | **As planned, inside the one frame.** Opened from Settings › Model ("Open in editor") and later "New from a workbook", as its own route rendered in `ShellFrame` under `TopBar` with the settings navigation out of the way. It is not a second frame (U-D14) and not a new top-level destination |
| D8 | Undo with dependants | **As planned, with "depends" defined.** A later operation depends on an earlier one when it names an element the earlier one created or re-keyed. The undo is refused with `OPERATION_HAS_DEPENDANTS` listing them; the client may undo them together. A new operation clears the redo list |
| D9 | Interactive dry-run budget | As planned: 1 s up to 10,000 rows on this machine, a deterministic sample above that, measured once in A3 |
| D10 | Concurrent editors | As planned: optimistic versions only |
| D17 | What counts as released, for the draft-only class | **The draft's base release, or the active release when it has none; installing a draft makes the release it created its new base.** Today a draft stays open with its old base after it is installed, so without the rebase a key installed a minute ago could still be renamed as if it were new. With it, carrying on in the same draft after installing means preparing the next version. Amends A2 (the rebase at installation, the class check against the base) |
| D18 | The release identity in the editor | **A `setRelease` operation; the install-and-activate step proposes the next version and the user can edit it.** Installing the same key and version with different content is refused today, so the designer must change the version before every install. The step suggests the base release's version with its last number raised by one, and the change is recorded as an operation like any other. Amends A2 and A4a |
| D19 | How views and panels are edited | **A few generic verbs over a view's or panel's named lists** (`insertViewItem`, `moveViewItem`, `removeViewItem` on `columns`, `filterFields`, `sortFields`, panels, fields) **and `setViewProperty` for single values,** addressed by the view's key and the list's name. One kind per view type and setting would multiply kinds every time a view type gains a setting. Replacing a whole view declaration would leave the layout to the editor, against principle 2 (the server produces layout changes). The existing validators check the result. Amends A2 and A4b |
| D20 | The two designer models | **The example model with every key renamed, and `generated-b`.** The journey configurations already keep `generated-b` different in shape and keys, so a second generator would add test machinery and no coverage. The renamed example shows that no code depends on its keys. Amends the "designer packages" paragraph under Acceptance workbooks |
| D21 | Where the mock-up lives | **A claude.ai artifact, as U1's mock-ups were.** It can be opened from any device and leaves nothing in the repository. The approved link is recorded in the A0 record |
| A-D5 | Optional assistant | As MODEL_AUTHORING recommends: off by default, pluggable, receives headers and a bounded sample only when configured, and returns proposals. Only its interface is in 0.10 (A6) |
| A-D6 | Keys of new elements | As recommended, with the rule fixed: lower-case, hyphen-separated ASCII from the label (accents dropped), `-2`, `-3` on a clash, editable until released (D17) |
| A-D7 | Records missing from a new version | As recommended: reported; retired or deleted only when the profile says so, in a change set |
| A-D8 | Install and activate from the editor | As recommended, with D18's version in the confirmation |
| A-D9 | Sheets laid out for reading | As recommended: blocks proposed, each confirmed; colour and formatting carry no meaning |

**Checks.** Documentation only: `pytest tests/test_api_journeys.py` (the inventory and the journey
IDs it cites), the links in every changed document, and the mock-up opened at 1440px and 390px in
light and dark before it is shown. No product code and no other suite.

**Composable domains (ADR-032):** A0 changes only documents. D5 touches inbound flow (a stored
source file an import can name), which leaves the door open: the import itself is unchanged. No
door is affected.

##### A0 record (2026-10-11)

**Delivered 2026-10-11.** The user approved the mock-up and the W1 sample the same day ("all is
good"), without changes; the editor's layout is the one A4a builds on, and W1's shape is the one A3's
generator writes.

- **Decisions:** D1–D10, D17–D21 and A-D5–A-D9 accepted as recommended, recorded in the decisions
  table and in MODEL_AUTHORING. Package scopes amended: N1 (D1's refusal below 0.10), A2 (D17's
  rebase, D18's `setRelease`, D19's view verbs, the generated layout), A3 (D5's `source_files`),
  the designer models (D20).
- **API design:** [API.md § Model authoring](API.md#model-authoring-product-010-designed): draft
  operations with the kinds table (34 model-side kinds plus `replaceModel` and `restoreElements`, each with its class and inverse; the eight
  mapping kinds named for A5), history, undo and redo, source files and their profiles, the dry-run
  summary, inferences. **Where it goes beyond the plan:** steps (one request is one history step and
  one undo); a draft may be invalid between steps, with diagnostics returned and installation still
  refusing; `restoreElements` as the inverse of removals; a limit of 500 operations per request
  (`MODEL_OPERATION_MAX_ITEMS`, `413 OPERATION_BATCH_TOO_LARGE`); the migration impact counted
  exactly up to 10,000; install and activate kept as the two existing routes, with no combined
  route. `author` is `null` until 0.12: nothing in the engine records who made a change today.
- **ADR-041**, model drafts change through recorded operations.
- **Journeys:** J33 (design a model, 12 variants), J34 (onboard a workbook, 10), J35 (the next
  version, 3) in USER_JOURNEYS; J08.9 pointed at the operation history; the planned routes, codes
  and setting in API_JOURNEYS. MODEL_AUTHORING's outline now points to the design.
- **Workbooks:** W1–W3 defined in test terms under [Acceptance workbooks](#acceptance-workbooks); a
  20-row sample of W1's main sheet (an invented office-supplies catalogue) sent to the user to open
  in their spreadsheet program. The generators remain A3's.
- **Mock-up:** [model editor canvas](https://claude.ai/artifact/XDpdfTB1zy93AERaaLVbU7), six
  boards: the editor on a model draft (clickable: type selection, issues and history, undo, a dark
  tweak), the relationship matrix (clickable cells), the editor with a workbook (A5's four panes and
  the dry-run figures), the context menu and Move to… (with the released-attribute refusal), install
  and activate, and 390px with the panes as tabs. Built on the Atlas tokens from
  `frontend/src/styles/tokens.css`, without the account's design system, which belongs to another
  product. Private until shared.

**Checks:** `pytest tests/test_api_journeys.py`: 5 passed (the inventory with the planned routes, and
every journey it cites). **Not done:** the mock-up was not opened at 1440px and 390px in light and
dark before it was shown, because no browser tool was available in this session; the user then
looked at it and approved it. Links were checked by hand for the anchors added (the API.md
heading was named "Draft operations" so the existing restructuring "Operations" anchor stays as it
was). No product code; no other suite.

## Track: the designer

### N1: Navigation groups and schema 0.10

**Design:** [MODEL_AUTHORING navigation groups](MODEL_AUTHORING.md#navigation-groups), A-D2, A-D11,
A-D12, ADR-029. **Needs:** A0.

**Scope:**

- Schema language 0.10 (D1): the optional `navigation.groups` on an application, with its
  validation (each entry a collection of the application, a collection in at most one group, unique
  group keys) and APPLICATION_MODEL's section. Earlier schema versions stay valid; a `navigation`
  member below 0.10 is refused at its pointer (D1, amended in A0).
- The sidebar shows declared groups as labelled, collapsible sections; ungrouped collections stay at
  the top level in their current order.
- The group page: its collections with a search over their names, reachable from the group's header.
- Read through the existing model and application routes; no new data, no migration.

**Tests:** the `navigation` contract (valid, unknown collection, a collection in two groups,
duplicate group key, absent field unchanged, present below schema 0.10); a model of schema 0.9 activating unchanged. Browser
(`test:browser:authoring-n1`): a grouped and an ungrouped application in the sidebar, collapse and
expand, the group page and its search, keyboard alone, 1440px and 390px.

**Groups:** `model`, `contract`, `startup` (schema activation).

**Exit:** schema 0.10 accepted by the compiler; the sidebar and group page approved from screenshots.

##### N1 plan (2026-10-11)

**Planned 2026-10-11; accepted by the user the same day ("yes"), D22–D27 and the test cases as
recommended.** Checked against the code at `4afb570`:

- **Schema versions** are listed in two places, `EngineModel.schemaVersion` (`models/schema.py`) and
  `SUPPORTED_SCHEMA_VERSIONS` (`engine/model/compiler.py`); `require_schema`
  (`validation/fields.py`) compares versions as numbers, so `0.10` sorts after `0.9` there. The one
  string sort is the `UNSUPPORTED_SCHEMA_VERSION` message (`sorted(...)` would list `0.10` first);
  N1 sorts it by number. Nothing in the frontend names a schema version.
- **Applications** allow extra members (`ApplicationDefinition`, `extra="allow"`), so today a
  `navigation` member at any version is kept and ignored (D1's reason to refuse it below 0.10).
- **A collection** is the sidebar's entry per view source type: `collectionGroups` in
  `frontend/src/model/collections.ts` groups an application's views by `table.objectTypeKey`,
  `relationMatrix.rowObjectTypeKey`, `tree.rootObjectTypeKeys[0]` and a mapping grid's side by its
  direction (ADR-029). The backend has no such rule today; N1 adds the same one to the application
  rules, so "a collection of the application" means the same on both sides.
- **The sidebar** is `features/objects/Explorer.tsx`: a flat `nav.collection-tree` under the label
  **Collections**, then **Browse records**. `RecordTree` already remembers folded type groups in the
  browser's storage, and `lib/localPreference` is the helper for it.
- **Routes** (`routing/routes.ts`) are `/apps/{app}/views/{view}`, `/objects/…`, `/change-sets…` and
  `/publications`; there is no group route. The served model (`GET /model`) is the compiled model,
  so a typed `navigation` field reaches the browser without a new route.
- **Test models:** `generated-a`, `generated-b` and the example are schema 0.9
  (`tests/journeys/configurations.py`); a journey raises its configuration to 0.10 and adds groups
  from the configuration's own collections, naming no keys.

**What is built:**

1. **Backend.** `NavigationDefinition` (`groups`) and `NavigationGroupDefinition` (`key`, `label`,
   `collections`, `collapsed`, default `false`), both `extra="forbid"`, as the optional
   `ApplicationDefinition.navigation`, left out of the canonical document when absent so every
   earlier model's hash holds. Schema `0.10` in both lists. Rules in `application_rules.py`, each at
   its pointer `/applications/{app}/navigation/…`: below 0.10 refused (`require_schema`); a group key
   twice; an entry that is not a collection of the application; a collection in a second group.
2. **Frontend.** The type `navigation?` on `ApplicationDefinition`; `model/collections.ts` gains
   `navigationSections(application)`: the ungrouped collections in their order, then each declared
   group with its collections in declared order. The explorer draws each group as a collapsible
   section in the collections navigation; the group page is a new route kind `group` at
   `/apps/{app}/groups/{group}` carrying the workspace, change set and publication as the list route
   does. The page is a `ui/PageHeader` (the group's label, its application as the eyebrow) over a
   `ui/Card` listing the collections (tile, plural name, the type's description, its lenses), a
   `ui/SearchField` that narrows them by name in the browser (model data, bounded by the model), and
   `ui/EmptyState` for no collections or no match.
3. **Documents.** APPLICATION_MODEL (schema 0.10, `navigation`), API.md (the served model's
   `navigation`), CURRENT_FUNCTIONALITY and PRODUCT (groups in plain words), UI_ACCEPTANCE (the
   state-inventory rows), USER_JOURNEYS J33.9's status, CHANGELOG, PROJECT_STATUS, TODO.

No migration, no new route, no new error code. The starter and example models stay on schema 0.9
(D3): their applications have three to six collections, which no group improves.

**Reference patterns** (UI_ACCEPTANCE §1): the sidebar groups reuse the **Tree** pattern's quiet
type group heading and its remembered fold, inside the **Shell** rail; the group page is a **Page
surface** (`PageHeader`, `Card`) with the **Empty state** pattern and `ui/SearchField`.

**Decisions** (D22 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D22 | Where groups stand in the sidebar | **The ungrouped collections first, in their current order, then the groups in declared order**, each listing its collections in declared order. A model without groups looks exactly as today, and the main work areas stay on top, which is what groups are for (A-D2). Placing a group where its first collection was would move sections whenever a group is edited |
| D23 | Folded or open | **`collapsed` is the starting state; a reader's fold or unfold is remembered in their browser per application and group,** as `RecordTree` remembers its folded type groups. A folded group holding the open collection shows its header marked as current, so the reader sees where they are without the group springing open |
| D24 | The group header's controls | **Two controls: the label is a link to the group page, and a toggle beside it folds and unfolds the section** (`aria-expanded`, `aria-controls`). One control doing both would make the page unreachable by keyboard without folding, or the fold unreachable without leaving the page |
| D25 | The group page | **`/apps/{app}/groups/{group}`, listing the group's collections with a name search done in the browser;** each entry opens the collection's default lens in the current data context (Live, a change set, a publication). No record counts (A-D12). An unknown group key in a URL falls back to the application's default route, as an unknown view does |
| D26 | Error codes | **No new codes.** A group key twice is `DUPLICATE_KEY`; an entry that is not a collection of the application is `INVALID_REFERENCE`; a collection in a second group and `navigation` below 0.10 are `INVALID_MODEL`, each a diagnostic at its pointer. All four are diagnostic codes the model rules already use, and an install still answers `422 INVALID_MODEL` with them in its details |
| D27 | An empty group | **Valid.** A2's `addNavigationGroup` creates a group before `placeCollection` fills it, and a draft step that leaves an empty group must not be an error. The sidebar shows its header; its page says it has no collections |

**Journey test cases** (J33.9; through the API, on two configurations each: generated-a and the
example where it holds the structures, otherwise generated-b):

1. **Groups are served.** Given A1 at schema 0.10 with a group holding two of its collections
   (`collapsed: true`) and its other collections ungrouped. When validated, installed and activated.
   Then it is valid, `GET /model` serves the application's `navigation` exactly as written, and the
   other application has no `navigation` member.
2. **A collection of another application** named in A1's group is refused `INVALID_REFERENCE` at
   `/applications/{A1}/navigation/groups/{g}/collections/{i}`; a key that is no type at all likewise.
3. **A collection in two groups** is refused `INVALID_MODEL` at the second group's entry.
4. **A group key twice** is refused `DUPLICATE_KEY` at the second group.
5. **`navigation` below 0.10:** the same document at schema 0.9 is refused `INVALID_MODEL` at
   `/applications/{A1}/navigation`; an unknown member inside a group is refused at its pointer.
6. **Earlier models unchanged:** the configuration's 0.9 model compiles to the same hash as before
   N1 and activates; raised to 0.10 without `navigation`, it is valid and compatible with it.

**Unit tests:** `navigationSections` (ungrouped order, declared group order, an empty group, a model
without groups); the schema version order in the unsupported-version message. Explorer component
tests for fold, the remembered fold and the current marker.

**Browser** (`test:browser:authoring-n1`, a starter variant with its keys renamed and groups added
to one application, the other left ungrouped): the grouped and ungrouped applications in the
sidebar; fold and unfold by pointer and keyboard, kept after reload; the group page from its header,
its search narrowing and its no-match state, an entry opening its collection; keyboard alone; 1440px
and 390px (the drawer); axe on the sidebar and the group page; screenshots for approval.

**Groups:** `model`, `contract` (no route changes, but the served model's shape), `startup` (schema
activation); Vitest for the changed modules; `npm run format`, `lint`, `build`.

**Composable domains (ADR-032):** presentation only; no door is affected.

##### N1 record (2026-10-11)

**Delivered 2026-10-11.** The user approved the screenshots and D28 the same day ("they are
approved"); the group heading stays as shown in them. Built as planned, with these differences:

- **The version order was wider than the plan found.** Seven places sorted the supported versions
  as text, two of them in API answers (`GET /system`'s `schemaLanguages`, a refusal's
  `supportedSchemaVersions`) and the startup and upgrade messages. `SCHEMA_VERSIONS` in
  `engine/model/compiler.py` now lists them oldest first and every place reads it.
- **The rule for a collection** is `collection_keys` in `validation/application_rules.py`, the same
  rule as the frontend's `viewSourceObjectTypeKey`.
- **One route read, not three copies:** which publication a route shows is `routePublicationId` in
  `routing/routes.ts`, used by `App`, `AppShell` and `DataContextBand` (U-D14); the group route
  joins it and `routeChangeSetId`.
- **Tests the change made wrong:** J31's `schemaLanguages` assertion compared with a text sort and
  now asserts the order; three older modules (`test_build07_wp11`, `test_wp81a_context`,
  `test_model_lifecycle`) pin the version list and gained `0.10`. `J33` maps to `model` and
  `model_admin` in `JOURNEY_GROUPS` until A2 adds `authoring`.
- **The browser runner** starts the renamed starter on the `schema` seed, since the starter seed's
  records carry the original keys; the sidebar and the group page need no records.
- **Two layout defects found in the screenshots and fixed:** the group page's descriptions did not
  wrap at 390px, and its empty states had no padding.

**Amended the same day at the user's request, after the first screenshots** (scope added to N1 by
the user, "n1"):

- **The group page's rows** show a chevron and a pressed state, so they read as something to tap.
- **The phone band.** Below 760px the band is one line: the workspace, the application in its tile,
  and the data context's pill, each opening its choice in a `ControlPopover` (the workspace
  selector; the applications through `ApplicationButtons`, extracted from the top bar; the band's
  own switch with the line saying what an edit does). The rail's workspace selector is left out on
  a phone. `lib/hooks/useMediaQuery` replaces the two copies of the width check (the drawer's and
  the filter bar's).
- **D28, the top bar on a phone: no application tabs in any area,** so the top bar stays one and the
  same across areas (U-D14) and one row high; Settings returns through its existing **Back to
  {application}** link. The alternative, tabs kept on Settings only, made the bar change height
  between areas. **Accepted by the user 2026-10-11** with the screenshots.
- **Desktop is unchanged.** A design proposal for the desktop band comes before any change there
  (the user, 2026-10-11): [proposal](https://claude.ai/artifact/BQf1M8edotaquqTXcknrjz); the topic was
  dropped by the user for now the same day, and desktop stays as it is.
- **Older runners the change made wrong:** `wp9-navigation` switched application at 390px through
  the tabs and now does so through the band; `u3-settings` returned from Settings at 390px through a
  tab and now through Back.
- At 390px a long workspace and application name together are cut with an ellipsis (a change set's
  "Wareho…" / "RDM Mast…"); the full names are in the popovers' titles.

**Checks of the amendment:** `DataContextBand.test` (phone case added), `vitest related` over the
changed files (148 and 42 tests passed); `test:browser:authoring-n1`, 8 checks with the band's three
choices and axe on the band; `test:browser`, `change-sets`, `w4`, `wp13c`, `s6`, `ua9`, `j1u`, `j4`,
`settings`, `webhooks`, `integration` and `wp14`, all passed after the two runner updates; format,
lint (0 errors), build.

**Checks:**

- Journey J33.9, `tests/journeys/test_j33_design.py`: seen failing first (10 of 10, schema 0.10
  unsupported), then 10 passed on generated-a and the example.
- Backend groups `model`, `contract`, `model_admin` (the model routers' version lists) and
  `startup`, by EXECUTION_GUIDE §2: 744 passed in 1 min 21 s, parallel. The serial part selects
  none of these groups. `ruff check app/ tests/` clean. `test_api_journeys`: 5 passed.
- Unit: `tests/unit/engine/model/test_compiler.py`, 4 passed (the version order).
- Vitest: `Explorer.test`, `model.test` and `routes.test`, 65 passed; `vitest related` over every
  changed file, 23 files and 332 tests passed. `npm run format`; `npm run lint`, 0 errors (the 7
  warnings are in unchanged files); `npm run build` succeeds.
- Browser: `test:browser:authoring-n1`, 7 checks passed, with axe on the open sidebar and the group
  page at 1440px and 390px. The guide's expansion for `Explorer.tsx`, `collections.ts` and
  `src/routing`: `test:browser` (53 s), `test:browser:wp14`, `test:browser:s6` (10 checks) and
  `test:browser:ua9`, all passed.
- **Not run:** the full suites, `test:a11y` and `test:visual` (build acceptance; N1's surfaces join
  the gates at T1, TODO). Dark mode is uninspected. No migration, so no startup migration checks.
- **Appearance:** inspected at 1440px and 390px in the light theme; approved by the user.

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
- `setRelease` (D18), and installation making the new release the draft's base (D17), the class
  check standing on it (amended in A0).
- View and panel edits as D19's generic verbs; the generated layout of a new type and of an attached
  attribute or allowed relation ([API.md § Operations](API.md#draft-operations)).

**Tests:** journeys through the API: build a small application from an empty draft (types,
attributes, a relation, a group), undo part of it, install and activate it, create a record; the
same on the starter model with renamed keys; a batch that fails applies nothing; a stale version
answered with the newer operations; a dependent undo refused; `OPERATION_REQUIRES_MIGRATION` on a
released element; diagnostics equal to whole-model validation of the same result. Unit tests per
operation kind and its inverse.

**Groups:** `authoring` (new), `model`, `contract`, `startup` (the history table).

**Exit:** every model-side kind in API.md with its inverse; a draft built only through operations
installs.

##### A2 plan (2026-10-11)

**Planned 2026-10-11; accepted by the user the same day ("yes"), D29–D35 and the test cases as
recommended.** The request for acceptance listed the decisions by subject only; the user accepted
while saying they could not judge them from that, and each was then explained in plain words; any
may still be changed before the code that uses it is built. Checked
against the code at `4afb570` (with N1's uncommitted changes in the working tree):

- **Drafts** (`engine/model/drafts.py`): `update_draft` writes `model_json` at `expectedVersion`
  with a conditional `UPDATE` and an audit event; the routes (`management/routers/model_management.py`)
  are under `MODEL_ADMIN_MUTATIONS_ENABLED`. Installation (`install_model_draft`) takes the draft
  `FOR UPDATE` under `model_installation_lock` and leaves `base_model_release_id` unchanged.
- **The compile route** already finds "the base release, or the active one" and diffs against it;
  A2 moves that lookup into the engine (`drafts.base_release`) so the class check and the compile
  read one rule.
- **The model document** (`models/schema.py`) orders attribute bindings and panels by an `order`
  integer as well as by list position; containment is a type's `behavior.parentRelationTypeKeys`
  naming relation types with `features.parentOf`, bound from each parent type; a top-level type
  needs `features.rootCreatable`. A table view's `filterFields` and `sortFields` need one field
  each, and `name` serves both.
- **Keys of different kinds can be equal** (a panel and a view, an attribute and a column), so
  `tests/model_support.renamed_model`'s string replacement, which renames every key at once with
  one prefix, cannot rename one element. A2 needs a **reference index**: for each element kind,
  every pointer in the document that names it, by the document's structure.
- **Impact counts:** `engine/model/compatibility.py` already counts records of a type, values of
  an attribute and relationships of a binding in live data (`_count_objects`,
  `_count_attribute_values`, `_count_relation_pair`); A2 reuses them with a limit, plus the open
  change sets' rows.
- **Journey worlds** are clones of a seed holding the configuration's records (`scenario.world_for`).
  A model built from an empty draft installs, but activating it there would be refused
  `MODEL_MIGRATION_REQUIRED` (the configuration's records lose their types); so J33.1 installs, and
  activation with records is walked by J33.2 on a draft of the active release.
- Migration head `20261007_08_import_preview`; the OpenAPI lock is `tests/test_openapi_contract.py`;
  `J33` maps to `model`, `model_admin` in `JOURNEY_GROUPS`.

**What is built:**

1. **Migration** `20261011_01_model_draft_operations`: table `model_draft_operations` (`id`,
   `draft_id` → `model_drafts` `ON DELETE CASCADE`, `sequence`, `step`, `kind`, `parameters`
   JSON, `inverse` JSON, `draft_version`, `author` nullable, `origin` JSON, `effects` JSON (added in
   the build: the elements an entry created, re-keyed and named, for D8), `undone_by_step`
   nullable, `created_at`; unique `(draft_id, sequence)`, index `(draft_id, step)`). No backfill:
   an existing draft starts with an empty history.
2. **Engine package `engine/model/authoring/`** (no FastAPI, no API schemas):
   - `references.py`, the reference index: element kinds (application, object type, attribute type,
     relation type, attribute binding, relation binding, view, detail, panel, navigation group) and,
     for each, the pointers naming it, including `ancestor:<type>`, `related:<key>`, `childSort`'s
     keys and `atLeastOneOf`. Used by `setKey` (rewrite), removals (what goes with an element) and
     D8 (which elements a step names).
   - `keys.py`, A-D6's key from a label.
   - `layout.py`, the generated table view, detail page and placements (A0's "Generated layout").
   - `kinds.py`, one function per kind: it validates its parameters against the document, applies
     the change to a working copy, and returns the inverse and the elements it created, re-keyed and
     named. `INVALID_OPERATION` carries `index`, `pointer` (into the request) and `reason`.
   - `released.py`, the class check against the base release and the impact counts (D17, D33).
   - `history.py`, applying a request as one step at `expectedVersion`, writing the draft through
     `update_draft` and the entries in the same transaction; undo, redo and dependants (D8, D32);
     the history page.
3. **Routes** in `model_management.py`, under the existing gate: `POST` and `GET
   /model-drafts/{id}/operations`, `POST …/undo`, `POST …/redo`. `PATCH /model-drafts/{id}` with a
   `model` records one `replaceModel` entry (origin `patch`); a name-only `PATCH` records nothing.
   Installation sets the draft's base to the release it created or found (D17, D34). The answer to
   an operation request: `version`, `entries`, `valid`, `diagnostics` (the compiler's, as
   `/compile` gives them). Setting `MODEL_OPERATION_MAX_ITEMS` (500).
4. **All model-side kinds of [API.md's table](API.md#kinds)**, 34 plus `replaceModel` and
   `restoreElements`, with D29–D31's parameter shapes.
5. **Documents:** API.md (the operations part moves from "designed" to delivered, field-level detail
   added), API_JOURNEYS (routes, codes and the setting as delivered), USER_JOURNEYS J33's and
   J08.9's status, ARCHITECTURE (the authoring package and the history table), OPERATIONS (the
   setting), CURRENT_FUNCTIONALITY and PRODUCT (drafts change by operations, with history and undo),
   EXECUTION_GUIDE (the `authoring` marker and its boundary), CHANGELOG, PROJECT_STATUS, TODO.

No frontend change: the editor is A4a, and the JSON workbench's `PATCH` is recorded by the server.

**Decisions** (D29 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D29 | `setKey` on an element a consumer API definition names | **Refused `INVALID_OPERATION`** (`reason: namedByConsumerApi`, with the pointer of the naming node), **instead of rewriting the definition as A0 designed.** A consumer definition names elements in its own grammar (field sources, `ancestor:<type>.<field>`, `via` by relation key or reverse key, public names), A2 has no kinds for consumer APIs, and a renamed element changes what consumers read. The definition is edited in the JSON workbench (one `replaceModel` step). Amends A0's "setKey rewrites every reference" |
| D30 | Containment in `addObjectType` and `setContainment` | **`parent: null`** puts the type at the top (`rootCreatable: true`); **`parent: { "objectTypes": [...], "relationType": "<key>" or { "name", "reverseName", "key"? } }`** binds one containment relation type (existing, or created with `parentOf` and `creatableOnChildAdd`) `one-to-many` from each parent type, and sets `rootCreatable: false`. A type containing itself names its own key in `setContainment`. One relation type for several parents is what `possible_types` already reads as one placement per parent |
| D31 | What a removal takes with it | **`removeObjectType`** removes its attribute bindings, the relation bindings at either end, its views and detail page, navigation entries, and the items naming it in other views and panels (a panel or view left with an empty required list goes too); **relation types and attribute types left unbound go when they are absent from the base release.** Everything removed is stored in the entry, and `restoreElements` puts it back at its old places. `removeApplication` removes the application and the types only it lists, the same way |
| D32 | Undo and redo order | **A stack:** undo takes back the latest step not yet undone (or the `steps` named); redo applies again the steps the latest undos took back, most recently undone first. Any new request or `PATCH` clears redo; an installation does not |
| D33 | Where the impact of a refused draft-only operation is counted | **Across all workspaces: live records, values and relationships plus the rows of open change sets,** each counted exactly up to 10,000 and reported as `"10000+"` beyond. The model is one for every workspace, so a migration touches them all |
| D34 | The draft's version at installation | **Unchanged.** The rebase (D17) changes what counts as released, not the model, so an editor at that version carries on without a `VERSION_CONFLICT`; the next operation's class check reads the new base. The history records nothing for it. An undo that would remove an element the installation released is then refused `OPERATION_REQUIRES_MIGRATION`, by the class check alone |
| D35 | Positions | **`position` is the index in the declared list (0-based; omitted: the end).** Where a list also carries `order` (attribute bindings, panels), the server rewrites `order` as 10, 20, 30… in list order after an insert or move, so the two never disagree. A position out of range is `INVALID_OPERATION`. *Amended in the build:* the moved or inserted item takes an `order` between its neighbours' (a panel's within its region), and the list is renumbered only when no whole number fits; renumbering every time would change other items, which an undo could then not put back |

**Journey test cases** (J33 and J08.9, through the API, on generated-a and the example where it
holds the structures, otherwise generated-b; marker `authoring`):

1. **J33.1 From an empty draft.** Given a draft of an empty schema 0.10 document. When one request
   adds an application, a top-level type and a type under it (a new containment relation type), a
   new attribute type attached to each (one required), a relation type allowed between them and a
   navigation group holding both collections. Then the answer is `valid` with no diagnostics, the
   history holds the request as one step with each entry's inverse, both types have a generated table
   view and detail page, and installation answers `201`.
2. **J33.2 and J33.3 Extend the active model.** Given a draft of the active release. When a type is
   added under `R`, with a new attribute, and a relation from it to `K` is allowed, and `setRelease`
   raises the version. Then the new type's table view and detail page are generated, `R`'s detail
   page gains a children panel, the draft installs and activates, and a record of the new type is
   created under an `R` record. The draft's `baseReleaseId` is now the installed release, and
   `setKey` on the new type is refused `OPERATION_REQUIRES_MIGRATION`.
3. **J33.4 Undo and redo.** Two steps; undo answers the model as it was after the first, redo as
   after the second; after an undo, a new step makes redo `409 NOTHING_TO_REDO`; a fresh draft's
   undo is `409 NOTHING_TO_UNDO`.
4. **J33.5 An undo with dependants.** Step 1 adds a type, step 2 attaches an attribute to it. Undoing
   step 1 is `409 OPERATION_HAS_DEPENDANTS` naming step 2; undoing steps 1 and 2 together returns the
   draft's starting model.
5. **J33.6 A stale editor.** Two clients at version v; one applies a step; the other's request at v
   is `409 VERSION_CONFLICT` with `details.operations` equal to the first client's entries; resent at
   the new version it applies.
6. **J33.7 A released element.** On a draft of the active release, a request holding an additive
   operation and then `removeObjectType` on `R` is `409 OPERATION_REQUIRES_MIGRATION` with
   `details.index` 1, the element and `records` equal to the `R` records the API lists; the draft's
   version and model are unchanged. Likewise `setKey` on `R.u` with its `values` count.
7. **J33.8 A request that cannot apply.** An operation naming an unknown type, or `addObjectType`
   with a key already taken, after valid operations in the same request: `422 INVALID_OPERATION` at
   its `index` and `pointer`, nothing applied. More operations than `MODEL_OPERATION_MAX_ITEMS` (set
   to 3 for the test) is `413 OPERATION_BATCH_TOO_LARGE`.
8. **Invalid between steps.** `addApplication` alone leaves the draft invalid: the answer's
   `diagnostics` equal `POST /model-validations` of the draft's model, and installation is
   `422 INVALID_MODEL`.
9. **J33.12 and J08.9 A whole-model edit.** A `PATCH` with a model is one `replaceModel` step with
   origin `patch`; an operation then applies on the edited model; undoing both returns the model before
   the `PATCH`; the history pages with `from=end` and lists every step with its origin.

**Unit tests** (`tests/unit/engine/model/authoring/`): each kind applied and then its inverse returns
the document, generated over the example model and generated-b (property-based over the kinds and
their elements, not one case per kind); `setKey` for every element of the example model compiles
valid and agrees with `renamed_model` on that element's pointers; A-D6's keys (accents, clashes);
D8's dependants; D35's positions.

**Groups:** `authoring` (new, J33's journeys and the unit tests), `model`, `model_admin` (the draft
routes), `contract` (the routes and the OpenAPI lock, re-baselined by diffing the document),
`startup` (the migration: clean bootstrap, upgrade from `20261007_08`, restart, interrupted upgrade,
lifespan, final smoke start). `ruff check app/ tests/`; `test_api_journeys`. No frontend checks: no
frontend change.

**Composable domains (ADR-032):** the history is model administration data; no door is affected
(identity, attribute storage, audit/history of records, bulk APIs, `match` and mapping coverage are
untouched).

##### A2 record (2026-10-11)

**Delivered 2026-10-11.** Built as planned (D29–D35), with these differences, each amended in
[API.md § Model authoring](API.md#model-authoring-product-010-designed):

- **Exact inverses for compound kinds.** Every change goes through `authoring/document.py`, which logs
  how to reverse it by key-based paths. `splitObjectType`, `detachAttribute`, `moveAttribute`,
  `setContainment` and `disallowRelation` store that log as their inverse (`restoreElements`), as the
  removals do, instead of the kinds A0 named (`mergeObjectTypes`, `attachAttribute`, …): only the
  stored state puts back the layout places they took. `setAttributeBinding` and `moveViewItem` do so
  when the move changed an `order`. `restoreElements` carries `removes`, the elements the undone
  operation created, so an undo that would take away an element released since is refused
  `OPERATION_REQUIRES_MIGRATION`, as D34 relies on.
- **`effects` column** on the history table, for D8: what each entry created, re-keyed and named. Not
  served.
- **D35 amended** (above): an `order` between the neighbours', panels counted within their region.
- **A detail page is generated where the application declares `details`.** An application without
  them shows every type on the default page; starting a list for one type would leave an empty list
  behind on undo. Likewise a released parent without a detail page is not given one (found by the
  J33.2 case, which assumed `R` had a page; the case now checks the page where it exists, and J33.1
  checks the children panel on a generated page).
- **`setRelease` takes `schemaVersion`** (any supported version), so a draft below 0.10 can be raised
  to use navigation groups by an operation, and the inverse can set it back.
- **A flag or `valueType` may be `null`**: the default, left unwritten, so an inverse restores a
  member that was absent rather than writing its default.
- **The test cases' new elements use `j33-` keys.** The first run's J33.1 used "Shelf" and "Item",
  keys generated-a's active release already holds; the class check rightly treated them as released
  (D17). The cases are unchanged.

**Not changed:** no frontend (A4a), the JSON workbench's `PATCH` recorded by the server. Consumer API
definitions have no kinds (D29).

**Checks:**

- Journeys `tests/journeys/test_j33_operations.py`: seen failing first (18 of 18: no route), then 18
  passed (9 cases on two configurations each).
- Unit `tests/unit/engine/model/authoring/`: 1,286 passed (every kind and then its inverse, generated
  over every element of the example model and generated-b, 1,275; the release refusal before any
  change; every key of the example re-keyed keeps it valid with no old reference; A-D6's keys; D35).
- Groups `authoring`, `model`, `model_admin`, `contract`, `startup` by EXECUTION_GUIDE §2: 2,054
  passed in 1 min 31 s, parallel, then the three it found (the setting's OPERATIONS row, the new
  foreign key's reviewed rule) passed after their fixes (48). The serial part selects none of them.
  `ruff check app/ tests/` clean; `test_api_journeys` 5 passed; the OpenAPI lock unchanged (the
  routes are under the administration gate) and the gated inventory updated.
- Startup for the migration: `test_startup`'s new case (an upgrade from `20261007_08` with a draft,
  an interrupted run rolled back and refused naming the table, recovery, two starts, the draft kept
  with an empty history and an operation recorded, a downgrade), clean bootstrap and restart, the
  lifespan, `test_schema_drift` and `test_foreign_keys`. **Smoke start:** the user's development
  server (`uvicorn --reload`, port 8000) reloaded on the new files and upgraded the development
  database itself to `20261011_01` (its 11 drafts kept); `/system` answers 200. It was not a copy, as
  the rule asks: the reload did it before a copy was made.
- **Not run:** the full suites (build acceptance). No frontend, so no Vitest or browser runner.

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

##### A4a plan (2026-10-11)

**Planned 2026-10-11; accepted by the user the same day ("ok"), D36–D42 and the test cases as
recommended.** Checked
against the code at `5a5684a`:

- **Settings › Model** (`features/model-admin/ModelWorkbench.tsx`) is the catalogue of releases and
  drafts beside the selection; a draft opens `ModelDraftEditor`, the JSON workbench (save by
  `PATCH`, validate, compile and compare, install). The routes are `/settings/model`,
  `…/releases/{id}` and `…/drafts/{id}` (`routing/routes.ts`); `CreateDraftDialog` creates a draft
  from a release, an empty document (`{}`) or a file.
- **The frame:** `SettingsShell` puts every settings page in `ShellFrame` with the settings rail;
  `ShellFrame` always has a rail, which goes into the drawer below 760px.
- **The operation API** (A2) answers a step with `version`, `entries`, `valid` and `diagnostics`;
  diagnostics carry a JSON pointer into the draft's document. Which elements are released is
  `authoring/released.released_atoms` over the base release (D17); containment is read from parent
  relations by `engine/model/placements` for an `EngineModel`, which a draft that does not validate
  does not have. **No route serves a draft's structure or its released marks**, so the editor would
  have to re-derive both from the JSON, against 0.8's D45 rule that the browser does not derive
  containment.
- **Compile** (`POST …/compile`) gives the differences against the base release and the
  compatibility with the active one, but only for a valid draft; installation and activation are two
  routes, as A-D8 and API.md keep them.
- **Reusable pieces:** the relation matrix lens (`RelationMatrixView`) is a record grid with paged
  rows and columns; its table styles and its cell keyboard handling (`onGridKeyDown`) fit a grid of
  types, its paging does not (the types are bounded by the model). `TreeMoveDialog` and
  `useTreeDrag` are the tree lens's Move to… and drag (B5): the pattern to follow, not components to
  reuse, since they move records. `ui/ActionMenu`, `ui/Modal`, `ui/ConfirmDialog`, `ui/Tabs`,
  `ui/HueTile`, `ui/StatusPill`, `lib/hooks/useCursorFeed` (the history) are reused as they are.
- **Browser models:** N1's runner builds the renamed starter at schema 0.10 on the `schema` seed;
  `generated-b` is printed from `tests/journeys/configurations.py` the same way.

**What is built:**

1. **Backend: the draft's outline** (D36). Engine `authoring/outline.py` and
   `GET /model-drafts/{id}/outline` under the model administration gate: the draft's `version`;
   per application its types as a containment tree (the parents each type's parent relations bind,
   by the placements' rule read over the document), its navigation groups with their collections and
   the collections in no group; per type its attribute bindings (value type, required, unique,
   read-only, the other types sharing the attribute type); the relation types; the allowed relations
   (relation type, from, to, cardinality, required, containment); every element marked `new`,
   `changed` or `released` against the base release, by `released_atoms`; and the compiler's
   diagnostics, each with the element its pointer falls in. It reads the raw document, so a draft
   that does not validate is outlined with what can be read and its diagnostics. Response schema in
   `management/schemas/model.py`; OpenAPI inventory updated (the route is gated, as A2's are).
2. **Frontend: the editor route** (D7, D37). `/settings/model/drafts/{id}/editor`, with the selected
   element in the query (`?type=`, `?matrix`), rendered in `ShellFrame` under `TopBar` with no rail:
   `ShellFrame`'s `rail` becomes optional. The editor bar: Settings › Model, the draft's name, its
   base release and version, the issue count, Undo, Redo, **Open as JSON** (the draft's workbench
   page) and **Install and activate…**. **Open in editor** on the draft page; **New draft** opens the
   editor after creating an empty or release-based draft.
3. **The model pane** (left): each application, its ungrouped types in their containment tree, then
   its navigation groups with their types; the relation types; **Relationship matrix**. Each row
   shows its type's `HueTile` and its `new` / `changed` / `released` mark, has a `⋯` menu (also
   Shift+F10 and the context-menu key) and an **Add** menu at the top (application, type, attribute
   type, relation type, group). The pane is a `role="tree"` with one tab stop, as the Tree pattern.
4. **The selected type** (centre): name, key and where it stands; tabs **Attributes** and
   **Relations** (Layout is A4b's); attribute rows with value type, rules, shared with, mark and
   their menu; **New attribute** and **Attach an existing one…**.
5. **Operations** (D38): one descriptor per model-side kind A4a offers (every kind in API.md's table
   except the view and panel verbs, which are A4b's, and `replaceModel` and `restoreElements`,
   which no client sends): its menu label, the element it applies to, its form fields and its
   history text. One `OperationDialog` renders any descriptor in `ui/Modal`, sends the step and
   shows a refusal in place (D39).
6. **Move to… and drag** (D40): Move to… on an attribute (`moveAttribute`) and on a type
   (`setContainment`, including the top level), a dialog with a searchable list of targets; drag in
   the model pane, with mouse or pen only, opens the same dialog with the target chosen, as B5 does.
7. **The relationship matrix** (centre, when chosen): types × types, each cell listing the allowed
   relations from the row's type to the column's, containment marked "contains"; arrow keys move
   between cells, Enter selects; the side panel shows the selected pair's relations (rule, remove)
   or the form to allow one. `onGridKeyDown` moves into one shared helper used by both matrices.
8. **Issues and history** (bottom): Issues lists the diagnostics, each linking to its element;
   History pages the draft's operations newest first (`useCursorFeed`, `from=end`), each step one
   line in plain words with its time and whether it is undone; any step can be undone from its line
   (`step`), with `OPERATION_HAS_DEPENDANTS` answered by offering to undo them together.
9. **A stale version** (D41): a `VERSION_CONFLICT` reloads the outline and asks: the steps applied
   since, in plain words, and **Apply mine again** (the same operations at the new version) or
   **Discard mine**.
10. **Install and activate** (D42, A-D8, D18): one dialog with the release key, version (suggested
    from the base release, last number raised) and name, the differences (compile's changes grouped
    by element), validity and compatibility; confirming sends `setRelease` when the identity changed,
    then installation, then activation. A refused activation leaves the release installed and the
    dialog says so; success reloads the active model and offers to open the application.
11. **Narrow** (below 760px): the panes become tabs **Model**, the selected type, **Issues** (with
    History); the editor bar keeps Undo, Redo and a menu with Open as JSON and Install. No drag on a
    phone; Move to… is the path.
12. **Documents:** API.md (the outline), API_JOURNEYS (the route), USER_JOURNEYS (J33's status,
    J33.11 in part), UI_ACCEPTANCE (state rows A4a-1 to A4a-5), CURRENT_FUNCTIONALITY and PRODUCT
    (the editor in plain words), ARCHITECTURE (the outline, the editor's module), CHANGELOG,
    PROJECT_STATUS, TODO.

No migration. **Reference patterns:** the **Settings layout**'s frame and top bar without its rail;
the **Tree** pattern for the model pane; **Dialog** and **Confirmation** for the operations and
install; **Actions** (`ActionMenu`) for the menus; the tree lens's Move to… (B3, B5) for moving;
the relation matrix lens for the grid; **Notice** for refusals and the stale version.

**Decisions** (D36 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D36 | How the editor reads a draft's structure and what is released | **A server read, `GET /model-drafts/{id}/outline`,** giving the containment tree, bindings, allowed relations, groups, each element's mark against the base release, and diagnostics tied to elements. The alternative, the browser reading the draft's JSON and the base release's, would write the containment rule and the class rule a second time in TypeScript (0.8 D45, D17); an API client gets the same picture the editor shows. Cost: one route and its schema, in the `authoring` and `contract` groups |
| D37 | Where the editor stands in the frame | **A route under Settings › Model, in `ShellFrame` with no rail,** `rail` made optional. The mock-up's phone board has the panes as tabs; a rail would go into the drawer instead. The alternative, the model pane as the rail, gives the drawer on a phone against the approved board |
| D38 | Which operations A4a offers, and how | **Every model-side kind except the view and panel verbs (A4b),** through one descriptor table and one dialog. A dialog per kind would be some 28 components; the descriptor keeps one component (U-D14) and one place for the history's plain words |
| D39 | A draft-only operation on a released element | **Listed in the menu with "needs a migration", sent when chosen, and the server's refusal shown in the dialog with its impact; nothing applies.** The mock-up shows the verdict before Move, but only the server knows the counts and the class rule, and a refused request applies nothing, so sending it is the check. Pre-disabling from the marks would copy the class rule into the browser |
| D40 | Drags in A4a | **An attribute onto another type, and a type onto another parent or the top level,** both opening Move to… with the target chosen; Move to… is the keyboard and phone path. Dropping a type into a navigation group is a menu action (**Move to group…**, `placeCollection`), since groups are presentation, not structure |
| D41 | A stale version | **Ask, never replay silently:** reload, list the steps applied since in plain words, then **Apply mine again** or **Discard mine**. Another editor's step may make mine wrong (a type renamed or removed), which an automatic replay would hide or turn into an error the user did not see coming |
| D42 | After install and activate | **The editor stays open on the draft,** now based on the new release (D17), with a notice offering to open the application. A refused activation keeps the installed release and says so in the dialog, with its diagnostics, as the mock-up's note |

**Journey test cases** (backend, J33 through the API, on generated-a and the example where they hold
the structures, otherwise generated-b; marker `authoring`):

1. **J33.2 The outline of a draft of the active release.** Given a draft of the active release, when
   a type is added under `R` with a new attribute and a relation from it to `K` is allowed, then
   the outline shows the new type under `R`'s place with mark `new`, `R` as `changed`, `K` and the
   released attributes as `released`, the new relation among the allowed relations, and the
   outline's `version` equal to the step's.
2. **J33.1 The outline of a draft built from empty.** Given J33.1's empty draft and its one request,
   the outline's tree, groups and allowed relations equal what the request built, every element
   `new`.
3. **Invalid between steps.** After `addApplication` alone, the outline answers `200` with the
   application and the diagnostics equal to the step's, each carrying the element its pointer falls
   in.
4. **Not found and gated:** an unknown draft is `404 MODEL_DRAFT_NOT_FOUND`; with administration
   disabled the route is absent.

**Browser** (`test:browser:authoring-a4a`, on both designer models, D20; the renamed example and
generated-b, each at schema 0.10 on the `schema` seed, naming no key): open the active model's
draft in the editor; add a type under a top-level type with a new attribute; allow a relation from
it in the matrix; add a group and move the new type's collection into it; undo and redo; move the
attribute to another new type by keyboard (Move to…) and a type under another parent by drag; a
released element's draft-only operation refused with its impact; a stale version from a second
client answered by **Apply mine again**; install and activate; open the new collection and create a
record. From an empty draft (generated-b only): an application with two types, installed. Keyboard
alone for one full pass; 1440px and 390px (the tabs); axe on the editor, the matrix, an operation
dialog and the install dialog; screenshots for approval.

**Unit tests:** backend, the outline's element for a diagnostic pointer and the marks (`changed`
when a released element's declaration differs); frontend, the descriptors (each produces the
request API.md defines), the history's plain words, the suggested version, and the editor's
component states (refusal with impact, the stale version question, dependants).

**Groups:** `authoring`, `contract`, `model_admin` (the new route); Vitest for the new and changed
modules (`vitest related`); `npm run format`, `lint`, `build`; the browser runners the guide selects
for `ShellFrame` and `routing/` (the expansion N1 ran). **Deferred to T1:** visual baselines and the
accessibility gate's scenarios for the editor, as N1 deferred its own; the package's **Tests** line
named baselines, and recording them before the surface is approved would record a layout still
changing.

**Composable domains (ADR-032):** model administration only; no door is affected.

##### A4a record (2026-10-11)

**Delivered 2026-10-11.** The user approved the editor after the revisions below ("otherwise the
model editor looks good", 2026-10-11). Built as
planned (D36–D42), with these differences:

- **The editor's address** names any selected element, `?show=type|application|relationType|attributeType&key=…`
  or `?show=matrix`, instead of the plan's `?type=` and `?matrix`: the centre also shows applications,
  relation types and attribute types.
- **No ⋯ button on the model pane's rows.** A button inside a tree item is a nested control, which the
  Tree pattern avoids. A row's operations are the selected element's menu in the centre; Shift+F10, the
  context-menu key or a right click on a row selects it and opens that menu.
- **The mock-up's preview pane and workbook rail are not drawn**: the preview is A4b's, the source and
  mapping panes A5's; each adds its pane to this layout.
- **Keys named by the editor** where one request creates an element and refers to it (a new attribute
  attached at once, a new relation type allowed at once): the editor makes the key from the label by
  A-D6's rule (`keyFromLabel`, the server's: accents and characters without an ASCII form dropped) and
  the server still checks it. Elsewhere the server generates keys.
- **An empty draft** from **New draft** is now a document of the newest schema language with a release
  identity (key from the draft's name, version `1.0.0`) and empty lists, instead of `{}`, on which no
  operation could build. Its bar says "A new model", not the active release its class check falls back
  to (D17).
- **`changed` for a type** includes a relation allowed from it (its outgoing relations, as its panel
  and the matrix's rows show); a relation allowed to it leaves it `released`. In API.md.
- **Shared, not copied:** `ShellFrame`'s rail became optional and `SettingsShell` takes `fullWidth`;
  the relation matrix lens's cell keys moved into `lib/gridNavigation.nextGridCell`, used by both
  matrices; the name lookup for the history is one function (`nameOf`); the attribute and group tables
  are `ui/SettingsTable`. Icons `undo`, `redo` and `grip` were added to `ui/Icon`.
- **Observed, not changed:** a type renamed after it was added keeps its generated view's name, so its
  collection's title shows the plural it was added with while the sidebar shows the new plural (A2's
  `setLabel` renames the type, not the views). Listed for the user; no change made.

**Checks:**

- Journeys `tests/journeys/test_j33_outline.py`: seen failing first without the route (8 of 10; the
  two "absent when disabled" cases pass either way), then 10 passed (5 cases on two configurations).
- Unit `tests/unit/engine/model/authoring/test_outline.py`: 19 passed (a pointer's element, by key and
  by index; the marks; no base; a containment cycle; an unreadable document).
- Groups `authoring`, `model_admin`, `contract` by EXECUTION_GUIDE §2: 1,673 passed and 1 failed in
  60 s, parallel; the failure was the API inventory missing the new route, added, then
  `test_api_journeys` 5 passed. The serial part selected none. `ruff check app/ tests/` clean. The
  OpenAPI lock is unchanged (the route is gated); the gated inventory gained it. No migration, so no
  startup checks.
- Vitest: `src/features/model-editor` 75 passed (`operations.test`: every descriptor builds requests
  of known kinds, the composed steps, the migration marks; `history.test`; `InstallDialog.test`;
  `ModelEditor.test`: the refusal with its impact, the stale version, dependants, Shift+F10, an
  issue's link); `routes.test`; `vitest related` over every changed file, 56 files and 627 tests
  passed before the last two test files were added. `npm run format`; `npm run lint`, 0 errors (the 7
  warnings are in unchanged lines; one this package added was removed); `npm run build` succeeds.
- Browser: `test:browser:authoring-a4a`, 23 checks passed on both designer models (11 on the renamed
  example, 12 on generated-b with the empty draft), axe clean on the opened editor, the matrix, Move
  to…, the refusal, the install dialog and 390px. The guide's expansion: `test:browser:settings`,
  `test:browser:wp11` (5 checks) and `test:browser:wp12` (7) passed; `test:browser:a4` (10) and
  `test:browser` each timed out once and passed on the rerun, unchanged (TODO's flakes).
- **Not run:** the full suites, `test:a11y` and `test:visual` (build acceptance; the editor joins the
  gates at T1). Dark mode is uninspected. Shift+F10 and the refused activation are checked in
  components only; the history's retry after a failed load has no test.
- **Appearance:** inspected at 1440px and 390px in the light theme from the runner's screenshots;
  three defects found and fixed (the row menus drawn as a dot by a class shared with another
  rule, a group's name cut by its note, the install dialog's fields out of line); approved by the
  user after the revision below.

**Revised 2026-10-11 after the user's review of the first screenshots**, then approved:

- **Dialogs, every one in the application.** A labelled field's label stood 14px above its own
  control and right under the field before it, because the general `.dialog form label` rule also
  spaced `ui/FormField`'s label; the webhook dialog had worked around it with its own class. One rule
  now spaces every dialog's fields (the label 6px above its control, 16px between fields) and the
  webhook class's copy is gone. A dialog whose actions sit inside its body keeps a bottom margin (Move
  to…'s buttons touched the frame). Move to… and Install and activate are forms, so their fields take
  the dialog style.
- **Menus, every `ui/ActionMenu`.** Items may carry a glyph, a second line and a section heading;
  every menu gained hover, a wider popover and clearer sections. The editor's menus are one
  `OperationsMenu` (the matrix had a copy), sectioned Change, Move, Add, Reshape and Remove, and a
  released element's draft-only operation says "Needs a migration" on its second line instead of in
  its label.
- **The editor's frame.** Full width (the frame's 1440px page width no longer applies to it) and the
  viewport's height, each pane scrolling on its own, so a large matrix no longer moves the page. The
  model pane and the matrix's side panel resize by dragging or the keyboard, remembered in the
  browser (`ui/ResizeHandle`, as the rail). Issues and history is a drawer at the bottom, closed
  until the reader opens it and closed only by the reader; undo, redo and an issue's link never open
  or close it (the user, 2026-10-11).
- **Headers.** The editor's title is `ui/PageHeader`, its base release, version, save and validity as
  chips; an element's key and whether it can change are chips too (`Facts`). The empty centre is
  `ui/EmptyState` with Object type, Application and Relationship matrix as buttons.
- **A type under itself** appears twice in the pane; the row chosen is the one shown selected (the
  inner one could not be chosen before).
- **The matrix scrolls inside a frame** (the user, after the second screenshots): a bordered, rounded
  box instead of open white sides, with the type column and the header row staying in place while it
  scrolls; checked by `test:browser:authoring-a4a` (14 checks on the renamed example).
- **Measured layout checks** (`e2e/helpers/layout-checks.mjs`): every dialog the runner opens
  (thirteen per model, the record and draft dialogs among them) is measured, buttons clear of the
  frame, each label nearer its control than the field before; the editor is as wide as the window at
  1440px and 1920px, the page does not scroll and the panes end on one line.
- **A2 defect found by the user, fixed in their database:** every history read and operation on the
  development database answered 500, `column model_draft_operations.effects does not exist`. The
  development server's reload had upgraded that database to `20261011_01` while A2 was still building
  it, and `effects` was added to the migration afterwards, so the database stayed at the head revision
  without the column. Fresh databases (every test) had it. The table held no rows; it was dropped and
  recreated by a downgrade to `20261007_08` and an upgrade, with the user's 12 drafts kept, and the
  history route answers 200 on the development server. No release carries the migration, so the file
  is unchanged. TODO holds the question of a startup check for this.

**Checks of the revision:** `test:browser:authoring-a4a` 29 checks on both models (the dialog
measurements, the full surface at 1440px and 1920px, the type under itself, the drawer opened and
closed by hand only); `src/features/model-editor` and `routes` 115 Vitest tests; `vitest related` over
`ui/ActionMenu`, `ShellFrame` and the editor, 28 files and 367 tests; `test:browser:webhooks` (19),
`test:browser:authoring`, `test:browser:ua8` (7) and `test:browser:settings` (10) for the shared dialog
and menu change; format, lint (0 errors, the 7 earlier warnings), build. The webhook dialog's
appearance was not inspected (its runner keeps no screenshot); the visual gate's dialog and menu
baselines will change with this at T1.

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

### A4c: Editor — consumer APIs

**Added by the user 2026-10-11** (after A4a), before T1; planned in detail when it comes. **Design:**
[CONSUMER_API.md](CONSUMER_API.md), 0.9's consumer API decisions (C1, C18), MODEL_AUTHORING's
principles. **Needs:** A4a (the editor frame), A4b (placed after it: A4b is designed and can start
at once, while this package needs its design pass first; the order can be swapped).

**Intent (the user's words, 2026-10-11):** beside the model editor, a consumer API editor that puts
the consumer APIs together in the same form. The editor's left pane gets a second tab: **Model**
(the pane A4a built) and **Consumer APIs**, placed before the pane's ＋ button; ＋ adds within the
open tab. The Model tab brings the model editor; the Consumer APIs tab brings the API editor.

**Outline of the scope, to be settled in its plan:**

- The Consumer APIs pane: the draft's consumer API definitions, and per definition what it exposes
  (types, fields with their public names and sources, relations followed, the operations offered,
  the contract version), each marked new, changed or released, as the model pane marks elements.
- Every change an operation on the draft, recorded in its history with undo and redo (MODEL_AUTHORING
  principle 3, ADR-041). A2 has no consumer API kinds (D29), so the package adds them to the
  operation API and the draft's outline: a backend part, like A2, before the pane.
- Install and activate shows the consumer contract result (an incompatible change without a new
  contract version is refused at activation, F23), as it shows compatibility today.
- Questions for its plan: the kind vocabulary for consumer definitions; whether `setKey` on a model
  element then rewrites the definitions that name it instead of refusing (revisits D29); what the
  editor shows of a definition's served shape (a sample read, or the shape only); the journeys
  (J33 or a journey of its own) and the browser runner; a mock-up approved before building (a new
  surface).

### T1: Designer checkpoint

**Needs:** A4b, A4c.

US-P05 composed in the browser over the real backend on both designer models: an application
designed from an empty draft and the starter model extended, through to records created in the new
types, and a consumer API defined for them in the editor (A4c). Keyboard alone, 1440px and 390px, the accessibility and visual gates for the editor's
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

- `POST /source-files`: a resource of its own owned by a draft or a profile, the file in
  `JOB_FILE_DIR` under `IMPORT_MAX_BYTES`, the cleanup taught its names, `sourceFileId` on
  `POST /imports` (D5, amended in A0).
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

D11–D16 accepted by the user on 2026-10-11 (D14 changed from its recommendation). D1–D10 and
D17–D21 accepted with the A0 plan the same day; where A0 restated one, the
[A0 plan](#a0-plan-2026-10-11) holds the full wording.
Design-level decisions are [A-D1–A-D12](MODEL_AUTHORING.md#open-decisions).

| # | Question | Recommendation | Blocks |
| --- | --- | --- | --- |
| D1 | Schema language version | **Accepted 2026-10-11:** 0.10, adding only the optional `navigation` declaration; earlier versions stay valid, and below 0.10 a `navigation` member is refused at its pointer; the starter moves to 0.10 only if it declares groups (D3) | N1 |
| D2 | Cut line | **Accepted 2026-10-11:** A7 and A8 may move to 0.10.x; R then accepts W1/W1′ and the designer. If more must go, A6 next, with the designer and manual mapping (A5) released | R |
| D3 | Starter model | **Accepted 2026-10-11:** unchanged unless a group improves it; acceptance uses the generated models | N1, R |
| D4 | Where operation history lives | **Accepted 2026-10-11:** a table of the draft's operations (kind, parameters, inverse, author, time, draft version, step); deleted with its draft; an installed release keeps none; it answers J08.9; [ADR-041](DECISIONS.md#adr-041--model-drafts-change-through-recorded-operations) | A2 |
| D5 | Source files attached to drafts and profiles | **Accepted 2026-10-11, changed in A0:** a resource of its own (`source_files`), the file in `JOB_FILE_DIR` under its own name, owned by a draft or a profile and deleted with it; the latest per owner kept, older ones removed after the job retention period; `POST /imports` may name one. Job files live and die with their job, so they cannot hold it | A3, A5 |
| D6 | Capability gates | **Accepted 2026-10-11:** operations, inference and install under the model administration gate; source upload and import under `INTEGRATION_JOBS_ENABLED` | A2, A3 |
| D7 | Where the editor lives | **Accepted 2026-10-11:** opened from Settings › Model on a draft ("Open in editor") and by "New from a workbook" (A5), as its own full-width route inside `ShellFrame` under `TopBar` (no second frame, U-D14); no new top-level destination; the JSON workbench stays | A4a |
| D8 | Undo with dependent operations | **Accepted 2026-10-11:** refused `OPERATION_HAS_DEPENDANTS` with the dependants listed (a later step depends on an earlier one when it names an element the earlier created or re-keyed); the client may undo them together; a new step clears redo | A2 |
| D9 | Interactive dry-run budget | **Accepted 2026-10-11:** a summary within 1 s for up to 10,000 rows on the reference machine; a deterministic sample above that with the full run on request; measured once in A3 | A3 |
| D10 | Concurrent editors | **Accepted 2026-10-11:** optimistic versions only; no locks or live co-editing | A2, A4a |
| D11 | Order of the lines | **Accepted 2026-10-11:** the designer line before the spreadsheet line, as the user requested (see [why](#why-the-designer-comes-first)); A3 may fill a gap | All |
| D12 | Which model a draft's profile is checked against | **Accepted 2026-10-11:** the draft's own model while editing; saved as an instance profile on install and activate, so instance profiles keep resolving against the active release as J2 defined (D65) | A5 |
| D13 | Profile effects of model operations | **Accepted 2026-10-11:** in A5, not A2: before A5 no draft holds a profile, and an instance profile cannot name an unreleased element, which is all a draft-only operation may touch | A2, A5 |
| D14 | An interim release after T1 | **Accepted 2026-10-11, changed by the user:** the designer is released as 0.10.0-alpha.1 when T1 passes, tagged `v0.10.0-alpha.1` ([T1](#t1-designer-checkpoint)). The recommendation was a checkpoint without a release | T1 |
| D15 | Split and merge of types in A2 | **Accepted 2026-10-11:** in A2 as model operations on unreleased types (their profile side in A5); they are in the roadmap's exit gate and their inverses shape the history format | A2 |
| D17 | What counts as released (draft-only class) | **Accepted 2026-10-11 (A0):** the draft's base release, or the active release when it has none; an installation makes the release it created the draft's new base | A2 |
| D18 | Release identity in the editor | **Accepted 2026-10-11 (A0):** a `setRelease` operation; install and activate proposes the base version with its last number raised, editable | A2, A4a |
| D19 | How views and panels are edited | **Accepted 2026-10-11 (A0):** generic verbs over a view's or panel's named lists (`insertViewItem`, `moveViewItem`, `removeViewItem`) and `setViewProperty`, addressed by keys; the server produces layout changes | A2, A4b |
| D20 | The two designer models | **Accepted 2026-10-11 (A0):** the example model with every key renamed, and `generated-b` | A2, A4a, A4b, T1 |
| D21 | Where the mock-up lives | **Accepted 2026-10-11 (A0):** a claude.ai artifact | A0 |
| D22–D27 | Navigation groups: sidebar order, folding, the header's controls, the group page, error codes, an empty group | **Accepted 2026-10-11 (N1):** as in the [N1 plan](#n1-plan-2026-10-11) | N1 |
| D28 | The top bar on a phone | **Accepted 2026-10-11 (N1):** no application tabs in any area below 760px; the band chooses the application, Settings returns through Back | N1 |
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

1. A4b, the preview and layout editing (A4a delivered 2026-10-11), starting with its plan; then
   A4c, the consumer API editor (added by the user 2026-10-11), with its design pass. A3 may fill a
   wait for approval.
