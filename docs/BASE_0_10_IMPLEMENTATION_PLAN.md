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
**Delivered:** A0, N1, A2, A4a (2026-10-11); A4b, A4c and T1, released as 0.10.0-alpha.1 (2026-10-12);
A3 and A3a (2026-10-12); A5a (2026-10-12); A5b committed (2026-10-12), its open points carried into
A6, which comes before A5c (the user, 2026-10-12); A6a, inference through the API (2026-10-12); A6b,
the editor filled by the inference, delivered (screenshots approved 2026-10-14, after its run on the
user's workbooks and D99–D103); A5c, the next version of a workbook, built (2026-10-14, D104 and
D105 accepted), delivered (screenshots approved 2026-10-14). A7, model-description sheets and
matching across files, built (2026-10-14, D106–D113 accepted), delivered (screenshots approved 2026-10-14).
A8 planned in three slices (D114–D121 accepted 2026-10-14); A8a, lists of a sheet laid out for
reading through the API, delivered (2026-10-14).

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
| 5 | [A4b](#a4b-editor--preview-and-layout-editing) | A4a | **Delivered 2026-10-12.** Preview with existing records; views, panels and fields laid out in place |
| 6 | [A4c](#a4c-editor--consumer-apis) | A4a, A4b | **Delivered 2026-10-12.** The consumer API editor: a Consumer APIs tab beside Model; definitions changed by six kinds; their schema and message example; the contract at activation |
| 7 | [T1](#t1-designer-checkpoint) | A4b, A4c | **Delivered 2026-10-12, released as 0.10.0-alpha.1.** US-P05 composed in the browser on two models; the designer's gates; tagged `v0.10.0-alpha.1` (D14) |
| 8 | [A3](#a3-source-profiling-and-the-dry-run-summary) | A0 | **Delivered 2026-10-12.** Source files, profiles of sheets and columns, the dry run of the whole file; W1–W3 generators |
| 8a | [A3a](#a3a-a-faster-trial-run) | A3 | **Delivered 2026-10-12.** A trial run records no audit entries (D72); sets advance from arrays (D73) |
| 9 | [A5](#a5-editor-with-a-source-file) | A3, T1 | **A5a delivered 2026-10-12; A5b committed 2026-10-12, its open points carried into A6; A5c delivered 2026-10-14; A5's exit gate met.** Source and mapping panes, mapping operations, profiles following the model, load, saved profiles and re-runs |
| 10 | [A6](#a6-inference-over-table-patterns) | A5 | **A6a delivered 2026-10-12; A6b delivered 2026-10-14.** Proposals from the table patterns; new application or extending the active model; pinned decisions |
| — | _cut line (D2)_ | | _If R is out of reach, 0.10.0 releases here and A7, A8 move to 0.10.x_ |
| 11 | [A7](#a7-model-description-sheets-and-matching-across-files) | A6 | **Delivered 2026-10-14** (screenshots approved). Model-description sheets; matching records across files |
| 12 | [A8](#a8-list-blocks-in-sheets-laid-out-for-reading) | A6 | **A8a delivered 2026-10-14; A8b built 2026-10-15, its screenshots awaiting approval; A8c open.** List blocks detected, confirmed and loaded |
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
| D9 | Interactive dry-run budget | As planned: 1 s up to 10,000 rows on this machine, a deterministic sample above that, measured once in A3. *Replaced by D67 (A3): the whole file, always* |
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
| D29 | `setKey` on an element a consumer API definition names | **Refused `INVALID_OPERATION`** (`reason: namedByConsumerApi`, with the pointer of the naming node), **instead of rewriting the definition as A0 designed.** A consumer definition names elements in its own grammar (field sources, `ancestor:<type>.<field>`, `via` by relation key or reverse key, public names), A2 has no kinds for consumer APIs, and a renamed element changes what consumers read. The definition is edited in the JSON workbench (one `replaceModel` step). Amends A0's "setKey rewrites every reference". *Replaced by A4c's D54 (2026-10-12): the definitions are rewritten* |
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
- **Every element panel in the type panel's form** (the user, after approval, 2026-10-11): a relation
  type shows its keys and containment as chips, its two names with their directions, and the pairs
  it is allowed between as a table whose rows carry their own menus, with **Allow between two
  types…** (`relation-type-allow`, `allowRelation`); an attribute type shows its value type and
  features as chips and the types it is attached to as a table with each binding's menu, with
  **Attach to a type…** (`attribute-type-attach`, `attachAttribute`); an application lists its types
  as a table (where each stands, attributes, relations, state, menu). A type in any table is its tile
  and name, opening the type (`TypeLink`). `test:browser:authoring-a4a`: 16 and 17 checks on the two
  models, axe on both panels; 77 editor Vitest tests.
- **The editor's tables are the record lists' table** (the user: "reuse the existing components"):
  every editor table is `ui/DataTable` through `EditorTable`, over a list held whole
  (`fixedWindow`, moved from the test helpers into `lib/hooks/useCursorWindow`, so the helper is one
  copy), with resizable columns remembered per table, its phone layout and no paging chrome
  (`whole`, passing `ScrollWindow`'s existing switches). `ui/SettingsTable` stays the settings
  pages' table. The type panel's "Shared with" and "From → to" are plain text again (the user).
- **Edited in place, as a record's title and fields are** (the user): the editable value and its
  form are now `ui/EditInPlace` (`EditInPlaceValue`, `InlineEditForm`), lifted out of
  `EditableField` and `InlineAttributeEditor`, which use them unchanged. An element's name in its
  heading, a relation type's two names and a group's label (`EditableText`), and a table's cells
  (`EditableCell`): value type, required, unique and read-only of an attribute; cardinality and
  required of a relation; required and read-only of an attribute on each type; a group's label and
  start. Each save is one step. The headers lost their Rename and Move to… buttons; both stay in
  the ⋯ menu.
- **A cut-off cell shows its whole value** (the user): every `ui/DataTable` cell the column cuts
  shows its value below it, wrapped, on hover or focus, and on a touch screen on a long press or a
  tap on its text (`ui/CellReveal`); nothing for a cell that fits or is being edited.
- **Which records a relationship may choose** (0.9 K7, the user's question): the editor sets a
  relation's `candidates` (**Which records may be chosen…** in its menu and its table cell, and in
  **Turn into a list type…**, which then names its list type and relation itself so the criteria
  follow in the same step); the fields and operators are 0.9's (APPLICATION_MODEL D170), the server
  validates each criterion. The outline serves `relations[].candidates`. A relation's menu gained
  **Make required / optional**.
- **A2 defect found here:** `setRelationRule` refused a `candidates` change on a released relation
  as needing a migration, though 0.9 made adding, changing or removing criteria compatible
  (installing checks no data). It now applies when only `candidates` changes; cardinality, required
  and scoped uniqueness stay draft-only. Unit case in `test_kinds.py`; API.md's table amended.
- **A2 layout defect found by the user's draft:** a newly allowed relation joined the `from`
  type's first outgoing relations panel, whatever it was set up for. On a page whose first such
  panel lists translations sorted by `ancestor:language`, the new relation made it list two related
  types and the draft invalid (`… cannot sort by 'ancestor:language': it lists several related
  object types`). A relation now joins only a plain relations panel (its relation types, direction
  and title, as the server generates them) or gets a panel of its own (`layout.place_relation`;
  regression cases in `test_layout.py`). The user's draft keeps the panel its step made; undoing
  that step and allowing the relation again places it in a panel of its own.
- **Editor tables fit their pane** until a column is sized by hand (cells wrap); an open cell
  editor stands above the cells beside it; the cut-off box measures visible text only, so a
  control's margin or a screen-reader label is not taken for a cut (the user's screenshots).
- **Removing relations** (the user: "the delete relation is missing"): a relation between two types
  had a Remove item, labelled only "Remove", and a relation type could be removed only while no type
  pair used it, so a type in use had no delete. The item is now **Remove relation**, and **Remove
  relation type** works on a type in use: its question names the pairs, and it removes them and the
  type in one step (`disallowRelation` for each pair, then `removeRelationType`), undone as one. A
  released relation or type is still refused with its impact. **Then a parent link too** (the user
  could not find the item on one: it was left out of containment relations): its question says where
  the child type is left (under its other parents, at the top level only, or nowhere, which the draft
  shows as an issue until Move to… places it); the server's `disallowRelation` already takes the link
  off the child type's parents. Checks: 96 Vitest tests; the runner removes Rack's link to Room and
  undoes it (`test:browser:authoring-a4a`, 21 and 23 checks on the two models). Built while A4b was in progress, coordinated with its session; committed with A4b
  (`719ad13`). Checks: `src/features/model-editor` 87 Vitest tests; `test:browser:authoring-a4a` 43
  checks on both models, among them a type in use removed and undone.
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

##### A4b plan (2026-10-11)

**Planned 2026-10-11; accepted by the user the same day ("looks cool, above is ok"): D43–D50 as
recommended, the test cases and the mock-up** ([preview and layout mock-up](https://claude.ai/artifact/R7BReAfCDnKMAwqioxA5s6), six
boards, 1440px and 390px, light and dark; private until shared). Checked against the code at
`c6ad770`:

- **The draft's model.** `compile_model` returns `canonical_model`, the same `EngineModel` dump
  `GET /model` serves, so the generic renderers can take a compiled draft as they are. Only
  `POST …/compile` serves it today, and that route is a write-shaped request (`expectedVersion`)
  that refuses an invalid draft and also works out the differences, compatibility and consumer
  contracts, which is too much to run after every step. Placements (`GET /model/placements`, 0.8
  D45) are served for the active model only.
- **The renderers** take the model as a prop (`ObjectDetail`, the panel registry, `ObjectCollectionView`)
  and read data through `useDataApi()` from `WorkspaceDataContext`. A record screen already renders
  a change set under a model other than the active one, so rendering under a model the server is not
  running is an existing pattern. The reads the renderers make are `object`, `objects`,
  `relations`, `relation` and `objectHistory`; their writes (`createAttribute`, `updateAttribute`,
  `createRelation`, …) are reached only when `readOnly` is off.
- **Pickers** limit candidates on the server (`candidateFor`, 0.9 K7) by the **active** model's
  relation binding, so a relation the draft adds or whose choice rule it changes cannot be checked by
  the existing read.
- **The view verbs** (A2, D19) cover every layout change in scope: `moveViewItem` on a page's
  `panels` (keeping `order`) and on a panel's `fields` or a view's `columns`, `filterFields` and
  `sortFields`; `insertViewItem` and `removeViewItem` on the same lists; `setViewProperty` for a
  panel's `region`, `visible` and `title`, a view's `defaultSort` and `pageSize`, a relations panel's
  `defaultSort`. **No kind adds a detail page**: `_detail_path` refuses a type without one, and the
  example model has such types (one in one application, five in two of the starter's), which the
  browser shows through `model/defaults.fallbackDetail`. `layout.detail_page` already generates the
  page `addObjectType` adds.
- **Field editors.** The attribute registry has one editor per value type, and no model hint chooses
  one (`ui` carries `helpText` and `hidden` only), so "a field's editor where the registry declares
  more than one" has nothing to choose from (D49).

**What is built:**

1. **Backend: the draft's model** (D43). `GET /model-drafts/{id}/model` under the model
   administration gate: `version`, `valid`, `diagnostics` (as the outline's), and, when the draft
   compiles, `model` (the dump `GET /model` gives) and `placements` (as `GET /model/placements`
   gives, from the same model). An invalid draft answers `200` with `valid: false` and no model. It
   reads; it writes nothing and takes no lock. Response schema in `management/schemas/model.py`.
2. **Backend: `addDetailPage` and `removeDetailPage`** (D48), additive, each the other's inverse
   (`removeDetailPage`'s inverse carries the page's declaration, as `removeView`'s does). `addDetailPage`
   (`applicationKey`, `objectType`) writes the page `layout.detail_page` generates;
   `alreadyPresent` when the type has one. API.md's kinds table and the history's words gain both.
3. **The preview pane** (D44, D45, D46): a right-hand pane of the editor for the selected type,
   resizable like the model pane, folded away by the reader, a fourth tab **Preview** at 390px. Its
   head chooses the **workspace** (the default first), the **record** (the first by name, or any one
   through a search) or **Empty record**; a new type has only the empty record. Below it, two tabs:
   **Record** (`ObjectDetail` with the draft's model, read-only) and **Table** (the type's table views,
   one at a time, by `ObjectCollectionView` with the draft's model, first page). The renderers get a
   preview data context: reads go to the server, every write is refused in the browser before it is
   sent, and an empty record answers its own reads with nothing. Pickers open from a relations
   panel's **Add…** and list candidates (D45). When the draft does not compile, the pane says so with
   the issue count and a link to Issues, and renders nothing (D47).
4. **Layout editing in place** (D46): **Edit layout** in the preview's head turns each panel into a
   frame with a grip, its title, its region and a **⋯** menu: Move up, Move down, Move to side /
   main, Hide / Show (a hidden panel stays in the frame, struck through), Rename…, Columns…, Sort…,
   Remove from page. In an attributes panel each field has a grip and a menu (Move up, Move down,
   Move to panel…, Remove from panel); **Add field…** lists the type's attributes not on the page;
   **New field group** inserts an attributes panel (D50). In the Table tab each column header has a
   grip and a menu (Move left, Move right, Remove column), with **Columns…**, **Filters…** and
   **Default sort…** in the head. Each choice is one operation request, so one step in the history,
   undone by the bar's Undo. Drags (mouse and pen) reorder panels, fields and columns and move a
   panel between regions; the menus are the keyboard and phone path, as in A4a (D40). A type with no
   declared page shows the page the browser falls back to, and its first layout change sends
   `addDetailPage` with the change in the same request.
5. **Shared, not copied:** the panel and field frames are one `LayoutFrame` component; the list
   dialogs (Columns…, Filters…, Add field…) are one `ListChoiceDialog` over `ui/Modal`; the menus are
   `OperationsMenu`. The operation descriptors gain the view verbs (A4a left them out, D38) with
   their history words.
6. **Documents:** API.md (the draft's model, the two kinds), API_JOURNEYS (the route), USER_JOURNEYS
   (J33.10's status and evidence), UI_ACCEPTANCE (rows A4b-1 to A4b-3), CURRENT_FUNCTIONALITY and
   PRODUCT, ARCHITECTURE (the preview's data context), CHANGELOG, PROJECT_STATUS, TODO. The scope line
   on field editors is amended (D49).

No migration. **Reference patterns:** the record screen (`ObjectDetail`) and the collection's table
as they are; **Actions** (`ActionMenu`) for the frames' menus; **Dialog** for the list choices; the
tree lens's Move to… (B5) and A4a's drags for reordering; **Notice** for an invalid draft.

**Decisions** (D43 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D43 | How the preview gets the draft's model | **A read, `GET /model-drafts/{id}/model`**, with the compiled model and its placements, or `valid: false` and the diagnostics. The compile route is a POST that refuses an invalid draft and computes differences and compatibility the preview does not need, and the browser cannot compile the model itself. Cost: one route in the `authoring` and `contract` groups. An integrator gets the model their client would render before installing |
| D44 | What data the preview shows | **Records of the active model, read live through the existing routes, in a workspace the reader picks; an empty record for a new type; nothing written.** Only the layout comes from the draft. A field the active model does not hold shows empty, which is true: no record has a value for it yet. Reading records through the draft's model on the server would put a model that is not running into every data read; the record screen already renders under a model other than the active one (change sets) |
| D45 | Pickers with the candidates they would offer | **The existing per-type list, limited by the active rule where the draft keeps it; otherwise the far type's records, unlimited, with a line saying the draft's choice rule applies after activation.** A far type that is new has no records ("New type: no records yet"). A draft-aware candidate read on the server is the alternative; it puts a draft into live reads for a hint the reader gets after activation anyway. Recorded for after 1.0 if a client needs it |
| D46 | Where layout is edited | **In the preview, on the rendered page, behind Edit layout**, as MODEL_AUTHORING says: the reader sees the page change after every step. Menus on every frame are the keyboard and phone path; drags are mouse and pen. The alternative, a Layout tab in the centre listing panels and columns as tables, is easier to build but shows a list, not the page; the mock-up shows the in-place version for approval |
| D47 | The preview while the draft does not compile | **Say so and render nothing**, with the issue count and a link to Issues. Keeping the last valid render would show a layout that is no longer the draft's, and layout editing on it would send operations against a model the reader is not looking at |
| D48 | A type without a declared detail page | **Two additive kinds, `addDetailPage` and `removeDetailPage`; the editor sends `addDetailPage` with the first layout change of such a type.** Without them, a type the model declares no page for cannot be laid out, and the browser's fallback page would stay the only one. The server generates the page, as for a new type (principle 2) |
| D49 | A field's editor | **Not built in A4b.** The registry has one editor per value type and no model hint chooses one; a choice comes with a second editor for a value type, after two real cases (AGENTS.md). The scope line is amended to say so |
| D50 | Grouping fields | **A group is an attributes panel**: New field group adds one with a title, Move to panel… moves a field between groups (one request: remove from one list, insert into the other). No new model structure; a page already declares several attributes panels |

**Journey test cases** (backend, J33.10 through the API, on generated-a and the example where they
hold the structures, otherwise generated-b; marker `authoring`):

1. **The draft's model.** Given a draft of the active release with a type added under `R`, when the
   draft's model is read, then it is `valid`, holds the new type with its generated table view and
   detail page, its placements list it under `R`'s type, its `version` equals the draft's, and the
   draft's version and history are unchanged by the read.
2. **Invalid between steps.** After `addApplication` alone, the read answers `200` with `valid:
   false`, no model, and the diagnostics the step answered.
3. **Lay out a type, then activate.** Given a type with a detail page and a table view, when panels
   are reordered, one moved to `side`, one hidden, a field moved to a new attributes panel in one
   request, a table column moved and one removed and the default sort set, then each is one step;
   after one undo the layout is the previous step's; after install and activate, `GET /model`
   answers the same page and view as the draft's model read before installing.
4. **A type without a page.** `addDetailPage` on such a type writes the page a new type would get;
   undo removes it; on a type with a page it is refused `INVALID_OPERATION` (`alreadyPresent`) and
   nothing applies.
5. **Not found and gated:** an unknown draft is `404 MODEL_DRAFT_NOT_FOUND`; with administration
   disabled the route is absent.

**Browser** (`test:browser:authoring-a4b`, on both designer models, D20, naming no key): select a
released type and see an existing record and its table in the preview; Edit layout: move a panel to
the side, hide one, move a field to a new field group, reorder table columns and remove one, set the
default sort, by drag and by menu; undo one; a new type's empty record laid out the same way; an
invalid step shows the notice; install and activate; open the record screen and the collection and
find the same layout. Keyboard alone for one pass; 1440px and 390px (the Preview tab); axe on the
preview, Edit layout and a list dialog; screenshots for approval. No write reaches the server from
the preview (the runner counts requests).

**Unit tests:** backend, `addDetailPage` and `removeDetailPage` and their inverses; frontend, the view
verb descriptors (each builds the request API.md defines) and their history words, the preview data
context (writes refused, an empty record's reads), and the candidate line of D45.

**Groups:** `authoring`, `contract`, `model_admin`; Vitest for the new and changed modules (`vitest
related`); `npm run format`, `lint`, `build`; `test:browser:authoring-a4b` and `-a4a`, and the
record screen's runners the guide selects for `ObjectDetail` and the collection view, since the
renderers are reused (no change to them is planned beyond the data context). **Deferred to T1:**
visual baselines and the accessibility gate's scenarios, as A4a deferred its own.

**Composable domains (ADR-032):** model administration only; no door is affected.


##### A4b record (2026-10-12)

**Delivered 2026-10-12.** The user approved it ("okay cool, can be committed"). The
user reviewed it on the development server while it was built and changed where the preview and the
layout editor stand; what is below is the built state. Built as planned (D43, D44, D47–D50), with
these differences:

- **Where the preview stands (the user, 2026-10-12, amending the mock-up and D46).** No pane at the
  right: a **Preview** button in the selected type's header, between its name and its ⋯ menu, opens
  the preview in the editor's centre, beside the model pane. **Edit layout** opens the layout editor
  over the whole editor (the bar, the panes and the drawer give way), with **Back to the model
  editor**. Each has its own address (`?show=type&key=…&mode=preview|layout`), so the browser's Back
  goes back too. A band in the data-context band's way (ADR-039) says which one shows: the preview is
  marked as a publication is (a read-only view), the layout editor as a change set is (an edit under
  way), so neither is taken for the live record screen. The band holds the type's name, the mark, the
  **workspace** and the **record** as choices that open their lists (as the phone band's choices do),
  a note, and the actions: Edit layout and Back to definition in the preview; Undo, Redo, Preview and
  Back to the model editor in the layout editor. The band stays in place; the page under it scrolls.
- **The first build's right-hand pane** (resizable, folded to a strip and opened again, both
  remembered) was liked by the user and is kept for later in
  [SAVED_UI_PATTERNS.md](SAVED_UI_PATTERNS.md#a-folding-side-pane); it is not in the product.
- **The preview's controls are shown and disabled (the user, 2026-10-12), amending D45.** The record
  page and the table render with their editing controls, inside a disabled fieldset, so every button,
  field and menu is there and none can be pressed, and links are not followed. A relationship's picker
  therefore does not open in the preview; the preview client still leaves out a choice rule the draft
  adds or changes (D45's rule), unused by the editor until a picker opens there.
- **D48 as a step of its own.** A type with no declared page shows, in the layout editor, a notice and
  **Declare its page**, which sends `addDetailPage` alone; the page's frames are then the server's.
  The plan said the first layout change carries it, but the page the browser falls back to
  (`fallbackDetail`) names its panels differently from the page the server writes, so a change made on
  it would name panels the declared page does not have.
- **`addDetailPage`'s undo.** When the page starts the application's list of pages, its inverse is
  `restoreElements`, which takes the list away again; otherwise `removeDetailPage`. Removing an
  application's last page keeps its empty list (two sessions had built both ways; one was kept).
- **Table columns** are frames in a bar above the table, each with its grip and menu, with Columns…,
  Filters… and Default sort… beside them; the mock-up drew the menus in the header cells. Listed for
  the user's review.
- **No field editor choice** (D49), as accepted.
- **A defect found by the user, fixed:** a table column's grip started a drag, but no drop moved it;
  the column's frame took the drop and did nothing. A column dropped on another now takes its place,
  and the runner drags a column on both models (it had dragged only panels).
- **Shared, not copied:** the layout dialogs are descriptors on the editor's one `OperationDialog`
  (`model-editor/layout.ts`); the band reuses the data-context band's classes, `ui/ControlPopover`,
  `features/workspaces/WorkspaceSelector` and `ui/ObjectLookup`; the preview's renderers are the
  record screen's (`ObjectDetail`, the panel registry, `ObjectCollectionView`) under
  `PreviewDataProvider`, a provider beside `WorkspaceDataProvider`.
- **Built across sessions.** The backend was started in this session, carried on for a while in a
  second session that also took up A4b, and finished here once the user chose one session. A4a's
  follow-up from a third session (`operations.ts`, its test and the A4a runner: "Remove relation"
  and a relation type removed with its pairs) is in the same working tree and is A4a's, not this
  package's.

**Checks:**

- Journeys `tests/journeys/test_j33_layout.py`: seen failing first (10 of 12; the two "absent when
  disabled" cases pass either way), then 12 passed (6 cases on two configurations); with the route
  inventory, 17 passed.
- Unit `tests/unit/engine/model/authoring/test_kinds.py` with `addDetailPage` and `removeDetailPage`
  generated for every type of both models: 1,350 passed. Its first run found the empty `details` list
  an undo left behind, fixed as above.
- Groups `authoring`, `model_admin`, `contract` by EXECUTION_GUIDE §2: 1,762 passed in 61 s,
  parallel; the serial part selected none. `ruff check app/ tests/` clean. No migration, so no startup
  checks. The OpenAPI lock is unchanged (the route is gated); the gated inventory lists it.
- Vitest: `previewClient.test` (writes refused before a request, the empty record answered here, a
  type, sort, filter or relation column the active model lacks, D45's rule), `layout.test` (every
  layout change's request), `history.test` (the layout words), `routes.test` (the mode in the
  address); `src/features/model-editor`, `src/routing` and the client 146 passed; `vitest related`
  over every changed source file, 52 files and 602 tests passed. `npm run format`; `npm run lint`, 0
  errors (the 7 earlier warnings; two this package would have added were removed); `npm run build`
  succeeds.
- Browser: `test:browser:authoring-a4b`, 29 checks on both designer models (the preview from the
  header under its band, the record choice, the disabled controls, the layout editor over the whole
  editor and Back, a declared page, a panel moved by menu, by keyboard and by drag, a field group,
  undo and redo, the table's columns moved by menu and by drag and its sort, a new type's empty record, an invalid draft, no write
  from the preview, install and activate and the record screen, 390px; axe on the preview, the layout
  editor and the field group dialog). `test:browser:authoring-a4a` (43) and `test:browser:settings`
  passed for the shared editor and frame.
- **Observed once, not reproduced:** one run on the renamed example ended with the application a
  test step adds (to make the draft invalid) still in the draft, although the preview had come back
  after Undo; the next two runs on that model passed. The runner now prints the history when it
  happens. Listed in TODO.
- **Not run:** the full suites, `test:a11y` and `test:visual` (build acceptance; the editor joins the
  gates at T1). Dark mode is uninspected.
- **Appearance:** inspected at 1440px in the light theme from the runner's screenshots, three
  revisions with the user (the centre's width, the band staying in place, the workspace and record
  choices); 390px and the layout editor's table checked in the screenshots only. Screenshots wait for
  the user's approval, given 2026-10-12.

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

##### A4c plan (2026-10-12)

**Planned 2026-10-12; accepted by the user the same day ("Design looks good … otherwise its
good"): D51–D59, the test cases and the mock-up**
([consumer API editor mock-up](https://claude.ai/artifact/V1V9r8ggEV1D2uDnxWfAZ9), eight boards,
1440px and 390px, light and dark; private until shared), **with one amendment (the user): no
"Served shape"; the schema definition and a message example are two items with buttons of their
own, since an integration uses them as two different documents** (D56 as amended below). Checked against the code at
`d25a8cd`:

- **Definitions in the document.** A draft holds `consumerApis` in the schema 0.9 shape
  (`models/schema.py` `ConsumerApiDocument`: `key`, `name`, `description`, `contractVersion`,
  `exposes`, `publicNames`, `object` with `fields`, `parent`, `path`, `hierarchy`, `related`,
  `operations` with `objects`, `xref` (`matchOn`, `alsoMatchThrough`), `resolve`, `lists`, `events`
  (`perType`, `custom`), and `filters`). `consumer_expansion.expand` turns it into the internal form
  with every default; `consumer_rendering.expanded_definition` writes the defaults out, as
  `GET /model/consumer-apis/{consumerApi}` serves them; `consumer_contract.output_contract` gives each
  output field's type and each related block's shape (one or many); `contract_diagnostics` compares a
  candidate with the active release; `consumer_openapi.consumer_openapi` builds a definition's
  OpenAPI document. Every reference rule is in `validation/consumer_api_rules.py`, at the author's
  pointers. The draft is stored as `JSON` (not `JSONB`), so member order, which is field output
  order, survives.
- **Field sources** may name an attribute that **any** exposed type binds
  (`_check_sources`); output names are unique and `objectType`, `matchScore` and `target` are
  reserved.
- **A2 and A4a** give consumer definitions no kinds: `setKey` on an element a definition names is
  refused `namedByConsumerApi` (D29, `references.consumer_api_pointer`), and the outline leaves
  `consumerApis` out (a diagnostic under `/consumerApis/…` belongs to no element). The view verbs
  (`insertViewItem`, `moveViewItem`, `removeViewItem`, `setViewProperty`) are the precedent for
  generic verbs over named lists.
- **Activation** already refuses a breaking change without a higher version
  (`releases.py`, `409 CONSUMER_CONTRACT_VERSION_REQUIRED`), and `POST …/compile` answers
  `consumerContracts`; the editor's `InstallDialog` shows `compatibility` but not
  `consumerContracts`, and shows a refused activation's diagnostics as one line.
- **Both designer models** carry a definition: the example's `rdm`, and generated-a's and
  generated-b's (`configurations._consumer_api`), so the journeys and the runner run on two.

**What is built:**

1. **Backend: consumer API kinds** (D51–D54) in `engine/model/authoring/consumer.py`, registered in
   `KINDS`: `addConsumerApi`, `removeConsumerApi`, and four part verbs over a JSON pointer below one
   definition: `setConsumerApiPart`, `insertConsumerApiPart`, `moveConsumerApiPart`,
   `removeConsumerApiPart`. Each checks that the definition still has the schema 0.9 shape after the
   change (refused `INVALID_OPERATION` at its pointer otherwise) and returns its inverse;
   references are left to the compiler's diagnostics. `addConsumerApi` writes the starting
   definition (D53). `setKey` rewrites the definitions that name the element (D54), through a walk
   of the consumer grammar added to `references.py`.
2. **Backend: the outline** (`authoring/outline.py`) gains `consumerApis`: per definition its key,
   name, contract version, mark (new, changed or released against the base release, D55), exposed
   types with their public names, counts per part, and `contract` (the check against the active
   release, when the draft compiles). Diagnostics under `/consumerApis/<key>` are tied to the
   definition.
3. **Backend: the definition, its schema and a message example** (D56).
   `GET /model-drafts/{id}/consumer-apis/{consumerApi}`: the draft's `version`, `valid`, the
   definition as written, and when the draft compiles, the definition with every default
   (`expanded_definition`) and its `contract`. Three documents beside it, each a download of its
   own: `…/schema.json`, the JSON Schema (2020-12) of the object message consumers receive, the
   same schema the OpenAPI document's component holds; `…/example.json`, one message valid against
   that schema, written by the server from it; `…/openapi.json`, the whole API's OpenAPI document
   from the draft. All under the model administration gate; reads, nothing written.
4. **Frontend: the Consumer APIs tab** (D57, D59). The left pane gets **Model** and **Consumer APIs**
   tabs (`ui/Tabs`) before the ＋ button, which adds within the open tab. The tab lists the
   definitions as a tree (as `ModelPane`: one tab stop, keys, Shift+F10), each with its mark and
   contract state. A definition selected opens in the centre: its header (name, `/api/consumer/<key>/v<n>`,
   contract version, contract state, **Schema** and **Message example**, ⋯ with Rename…, Describe…, Raise contract
   version, Edit as JSON…, Download OpenAPI (draft), Remove consumer API…) and tabs **Types and
   related**, **Fields**, **Operations**, **Filters**, **Schema**, **Message example**. Schema and Message example each have Copy and
   Download. Tables are `EditorTable`
   with in-place cells (`EditableCell`), rows with ⋯ menus (`OperationsMenu`); dialogs are
   descriptors on the one `OperationDialog`. ＋ in the tab opens **New consumer API** (name, key,
   types to expose).
5. **Frontend: install and activate** (D58). `InstallDialog` gains a Consumer APIs section from the
   compile's `consumerContracts`: each definition's result, with **Raise to v<n+1>** for one that
   needs it (one step), and Activate disabled while one does; a removed definition is a warning.
6. **Address:** `?show=consumerApi&key=<key>&tab=<tab>` (`routing/routes.ts`), so Back works and a
   reload keeps the place; the pane's tab follows the selection.
7. **Documents:** API.md (the six kinds in the kinds table, the two routes, the outline's
   `consumerApis`; D29's refusal replaced by D54), API_JOURNEYS (routes), USER_JOURNEYS (J33.13,
   J33.14), CONSUMER_API (a definition is also edited by operations), UI_ACCEPTANCE (rows A4c-1 to
   A4c-3), CURRENT_FUNCTIONALITY, PRODUCT, CHANGELOG, PROJECT_STATUS, TODO.

No migration. **Reference patterns:** A4a's model pane and element panel (the tree, the header with
facts and ⋯, the tabs, `EditorTable` with in-place cells), **Actions** (`ActionMenu`) for the
menus, **Dialog** (`OperationDialog` over `ui/Modal`) for additions, **Notice** for a contract
change, A4a's `InstallDialog`.

**Decisions** (D51 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D51 | The kind vocabulary for consumer definitions | **Two whole-definition kinds and four part verbs over a JSON pointer below the definition**, as the view verbs are generic over a view's lists: `addConsumerApi` and `removeConsumerApi`; `setConsumerApiPart` (`consumerApi`, `pointer`, `value`; `null` takes an optional member out, as A2's flags), `insertConsumerApiPart` (`pointer` of a list or of a keyed map, `value`, `key` for a map, `position`), `moveConsumerApiPart` (`pointer` of the item, `position`), `removeConsumerApiPart` (`pointer` of the item). Inverses: set ↔ set with the old value; insert ↔ remove; move ↔ move back; remove ↔ insert at its old position. `pointer: ""` with `setConsumerApiPart` replaces the definition (Edit as JSON). The alternative, about twenty named kinds (`exposeType`, `addField`, `addFilter`, `addMatchRule`, …), reads better in the API reference but needs a kind for every part of the definition grammar and a new one whenever the grammar grows. The history's words are written per pointer by the editor, as A4b's layout words are ("Added field packSize to Shop feed") |
| D52 | What a consumer kind refuses, and what it leaves to the issues | **Refused: what makes the document unreadable.** An unknown definition, a pointer that names nothing, a key taken, a position out of range, and a value that does not have the schema 0.9 shape at its place (the definition is re-read as `ConsumerApiDocument` after the change) are `422 INVALID_OPERATION` at the parameter, and nothing applies. **Left to the issues: references.** A source naming no attribute, a `via` naming no relation, a role given twice: the step applies and the answer's diagnostics point at the node, as an invalid model step does (A2). Checking references in the kinds would copy `consumer_api_rules.py`'s rules into a second place. A draft below schema 0.9 is refused `addConsumerApi` (`reason: unsupportedSchemaVersion`); `setRelease` raises it first |
| D53 | What `addConsumerApi` writes | **A starting definition from the exposed types, as the server generates a new type's layout (principle 2):** `contractVersion` 1; fields `id` (role `id`), `name` (role `name`) and one field per attribute an exposed type binds, in binding order, named by the key in camelCase (a clash with a taken or reserved name gets a number); `operations.objects` and a list per exposed type, keyed by its plural key (`of` the type). No XREF, filters, related blocks or events: those need choices only the author can make. Parameters `name`, `key` (generated from the name, A-D6, when left out), `exposes`, `position`; the stored parameters hold the written definition, so redo writes the same one. Inverse `removeConsumerApi`, whose inverse is `addConsumerApi` with the stored definition |
| D54 | `setKey` on an element a definition names (revisits D29) | **Rewrite the draft's definitions, as A0 designed, instead of refusing.** `setKey` already applies only to elements the base release does not declare (a released element is `OPERATION_REQUIRES_MIGRATION`), and a released definition names only released elements, so a rewrite changes only definitions no consumer reads yet. The walk covers the consumer grammar: `exposes`, `publicNames` keys, field sources (`<attribute>`, `ancestor:<type>.<attribute>`), related `via` (key and reverse key) and related fields, list `of`, `within.types`, `sortBy`, filter `under`, `linkedTo`, `matchOn`, XREF `matchOn` and `firstOf` fields, `preferTypes`, event `objectTypes`. The rewrite is logged, so undo puts the old names back. A type whose public name comes from its key gets the new key's: the type is new. Cost: the walk in `references.py`, held by the existing unit test that re-keys every element of both models. The alternative, D29's refusal, leaves "add a type, expose it, rename it" blocked until the definition is edited by hand |
| D55 | Released definitions, marks and the contract | **No migration refusal for consumer definitions.** A definition is marked new, changed or released against the base release, as model elements are, but changing a released one is not refused: what protects consumers is the contract check against the active release at activation (C-D17, F23), which the editor shows as it goes (D56, D58). The outline carries each definition's `contract` (`compatible` or `version_required` with the diagnostics), computed when the draft compiles. A definition's `key` can be changed by `setConsumerApiPart` at `/key`; for a released one the check reports `CONSUMER_API_REMOVED` (consumers of the old key get 404), as removing it does |
| D56 | What the editor shows of a definition's served shape | *Amended by the user at acceptance:* **two documents, each its own tab and button: the Schema (the JSON Schema of the object message, which an integration validates against or generates types from) and a Message example (one message valid against it, which an integration uses as a fixture or to agree the format), both worked out by the server from the draft; no sample read.** `GET /model-drafts/{id}/consumer-apis/{consumerApi}` answers the definition with its defaults written out and the contract result; `…/schema.json` and `…/example.json` answer the two documents, and `…/openapi.json` the whole API's OpenAPI document, so an integrator gets what their client will read before it is installed. The example's values come from each field's type (a related block as one object or a list of one), not from records. A sample from real records would make the consumer tier read a model that is not running, the objection D44 and D45 answered for the preview; consumers read samples after activation. A sample read through a draft is recorded for after 1.0 if a client needs it. An invalid draft answers `valid: false` and the definition as written; the OpenAPI document is then `422 INVALID_MODEL` |
| D57 | What the editor's forms cover | **Every part of the definition, in tables and switches:** the definition's name, description and contract version; exposed types and public names; fields (sources in order, role, default, description, order); parent, path and hierarchy; related blocks (via a relation forward or reverse, their fields); operations offered (switches for Get by ID, XREF, Resolve, events per type); lists (`of`, `within`, `sortBy`); XREF match rules and the rules that match through a related block; custom events (types, changes, watched outputs and blocks); filters, each with its verb chosen when added and its parts edited in place. **Edit as JSON…** edits the one definition (one `setConsumerApiPart` step) for anything a form makes awkward. Cost: the largest part of the package; the forms reuse A4a's table, cell and dialog components, and each choice is one descriptor building one request |
| D58 | Install and activate | **The dialog shows the consumer contract result from the compile, per definition, and offers Raise to v<n+1> for one that needs it (one `setConsumerApiPart` at `/contractVersion`); Activate is disabled while one remains.** A removed definition is a warning naming the consumers' 404. The server still refuses a breaking activation (`409 CONSUMER_CONTRACT_VERSION_REQUIRED`); the dialog's disabled button only saves the round trip, and a refusal is shown with its diagnostics as a list |
| D59 | Where it stands | **As the intent says, and as the mock-up shows:** two tabs in the left pane, Model and Consumer APIs, before ＋, which adds within the open tab; a definition selected opens in the centre with its tabs; Issues and History stay the editor's one drawer, and a consumer step is undone by the bar's Undo. The selection is in the address (`show=consumerApi`), so the pane's tab follows it. At 390px the phone tabs are the pane (named by its open tab), the selected definition and Issues |

**Journey test cases** (backend, J33.13 and J33.14 through the API, on generated-a and the example,
naming no key of either; marker `authoring`):

1. **J33.13 Define a consumer API by operations.** Given a draft of the active release. When
   `addConsumerApi` exposes `R` and `K`, then the answer is `valid`, the outline lists the definition
   as `new` with `contract: compatible`, and the schema lists `id`, `name` and a property for each
   attribute `R` and `K` bind with its type, the example validates against the schema, and there is a
   list per type. When a field is inserted, a related
   block added via a relation allowed from `R`, a list `within` an `under` filter added and an XREF
   rule added, each in its own request, then each is one step, the draft stays valid, and one undo
   takes back only the last. After install and activate, the consumer tier answers
   `GET /api/consumer/<key>/v1/objects/{id}` for an `R` record valid against the schema read before
   installing, and the list for `R` pages its records.
2. **Invalid between steps; a value of the wrong shape.** Inserting a field whose source names no
   attribute applies, answers `valid: false` with the diagnostic at
   `/consumerApis/<key>/object/fields/<field>/source/0`, and the outline ties it to the definition;
   setting an XREF weight to a text, or inserting at a position out of range, or naming an unknown
   definition, is `422 INVALID_OPERATION` at the parameter, and the draft's version is unchanged.
3. **J33.14 A contract change at activation.** Given a draft of the active release with its
   definition. When a field the active release serves is removed, then the outline's `contract` is
   `version_required` with the field's pointer, and activation is
   `409 CONSUMER_CONTRACT_VERSION_REQUIRED`. When `contractVersion` is raised by one step, then the
   contract is `compatible`, the draft installs and activates, `…/v2/objects/{id}` answers without the
   field and `…/v1/…` answers `404`.
4. **A key changed after it is exposed (D54).** Given a draft with a new type, a new attribute it
   binds, and a definition exposing the type with a field from the attribute and a list of it. When
   `setKey` re-keys the type and the attribute, then the definition names the new keys, the draft is
   valid, and the schema is unchanged apart from the type's default public name; one undo
   puts back the old keys in the definition.
5. **Remove and put back.** `removeConsumerApi` on the released definition answers a draft whose
   contract lists `CONSUMER_API_REMOVED` as a warning; undo returns the definition exactly as it
   was; `addConsumerApi` with a key taken is `422 INVALID_OPERATION` (`keyTaken`).
6. **Not found and gated:** the definition of an unknown draft is `404 MODEL_DRAFT_NOT_FOUND`, of
   an unknown definition `404 CONSUMER_API_NOT_FOUND`; the schema, example and OpenAPI document of an
   invalid draft are `422 INVALID_MODEL`; with administration disabled the routes are absent.

**Browser** (`test:browser:authoring-a4c`, on both designer models, naming no key): open the
Consumer APIs tab and the model's definition; add a field and change its sources in place, add a
related block, switch XREF off and on, add a list and a filter, each one step in History; undo one;
open Schema and Message example; remove a released field, see "needs version 2", raise the version
from the Schema tab; New consumer API exposing two types; Install and activate showing the consumer
contract section; read the consumer tier's object after activation. Keyboard alone for one pass
(the tree, the tabs, a table's menus, a dialog); 1440px and 390px; axe on the tab, a definition's
tabs, New consumer API and the install dialog; screenshots for approval.

**Unit tests:** backend, each consumer kind applied and then its inverse returns the document,
generated over every part of both models' definitions (the existing property test's way);
`addConsumerApi`'s definition compiles valid for every type of both models; `setKey` over every
element of both models leaves no old key in a definition (the existing re-key test extended).
Frontend, the consumer descriptors (each builds the request API.md defines) and their history
words, and the address's `show=consumerApi`.

**Groups:** `authoring`, `model`, `model_admin`, `contract`; the consumer tier's journeys are not
selected (the tier is unchanged; case 1 and 3 read it after activation). Vitest for the new and
changed modules (`vitest related`); `npm run format`, `lint`, `build`; `test:browser:authoring-a4c`
and `-a4a` (the shared pane and install dialog). **Deferred to T1:** visual baselines and the
accessibility gate's scenarios, as A4a and A4b deferred theirs.

**Composable domains (ADR-032):** the consumer API's `match` declaration (XREF rules) is edited by
the new kinds but its grammar is unchanged; no door is affected.

##### A4c record (2026-10-12)

**Delivered 2026-10-12.** The user approved it ("you can commit") after the two rounds of changes
below (the sources picklist, then a selector wherever a field name was typed). Built as planned (D51–D59, with D56 as the user amended it at acceptance), with these differences:

- **Schema and Message example (the user, at acceptance).** No "Served shape": the definition's
  **Schema** (the JSON Schema of the object message) and a **Message example** are two tabs, each with
  Copy and Download, and two buttons in the header, since an integration uses them as two documents.
  The routes are `…/schema.json` and `…/example.json` beside `…/openapi.json`; the definition read
  answers the definition, its defaults and its contract, without a shape of its own.
- **XREF switched off asks first, and Resolve stops with Get by ID or XREF** (found by the runner on
  generated-b). Switching XREF off took its match rules with it, and switching it on again started it
  empty, leaving a filter that scores through those rules invalid; and Resolve stayed offered without
  what it answers through. Switching off Get by ID or XREF now stops Resolve in the same step, and
  switching XREF off while it holds rules asks, saying that Undo puts them back.
- **No field name is typed by hand (the user, after the first screenshots: "this shall apply
  everywhere").** Every place a dialog or a cell asked for a field name now offers a selector of
  what is valid there, so a mistake cannot be typed:
  - a field's **sources**, in order (the first non-empty is served): Name, the exposed types'
    attributes with each value type, and the name and attributes of each type above them
    (`ancestor:<type>.<field>`), with Move up, Move down and Remove (Add field…, **Sources…**, the
    cell);
  - a filter's **match fields**, as removable chips, with the defaults said when none is chosen: under
    or linked to types, `id`, `name`, `code` and their searchable or unique attributes (C-D20); on a
    related block, its fields (Add filter…, **Matches on…**, the cell); a linked-to filter's
    **routes** (the record itself, a related block, a shared related record) as chips;
  - an **XREF rule's field** and the **field read through a related block**, as grouped selects, the
    latter following the block chosen;
  - a related block's **fields**, as rows of an output name reading a source picked from the
    records the block reaches (Add related…, **Fields…**, the cell);
  - a list's **sort**, as a select of the scalar attributes of its type (Add list…, the cell);
  - a custom event's **watched outputs**, as chips of the fields and related blocks.

  One component, `ChoiceListField`, draws an ordered list or chips; `PairsField` draws the rows; both
  are field kinds of the one `OperationDialog`, whose selects now show groups and follow an earlier
  choice. What is still typed is a name the author gives (an output, a key, a filter's name) or a
  weight; `operations.test` pins that list. A value written by hand earlier stays listed. The runner
  picks a field's sources and orders them, and adds a filter with its match fields as chips; 20
  checks on both models again.
- **No marks on a definition's rows.** The mock-up marked each field New or Released; the outline marks
  whole definitions only (against the base release's definition of that key), and the contract check
  says what consumers would notice. Listed for the user's review.
- **The operation switches are checkboxes with the switch role**, styled as the editor's checkboxes,
  not the mock-up's sliders.
- **Shared, not copied:** the pane's tree is one `EditorTree` (extracted from `ModelPane`) listing the
  model and the consumer APIs; the definition's header, its add buttons and the "no longer in the
  draft" state are `ElementPanel`'s, now exported; every dialog is a descriptor on the one
  `OperationDialog`, which gained a JSON field for Edit as JSON…; `EditableCell` gained an `optional`
  text cell (a public name back to its default, a default taken out). The UI icon set gained `api`,
  `document` and `download`.
- **The consumer kinds register from the authoring package's `__init__`**: registering them from
  `kinds.py` made an import cycle `test_boundaries` refuses, and registering them from the history
  module left readers of `KINDS` without them (the unit test of every kind found it).
- API_JOURNEYS held `GET /model-drafts/{id}/model` twice (from A4b); one row was removed.
- **Seen, not started by this session:** a `uvicorn` on port 61380, running since 2026-10-07, was left
  as it was.

**Checks:**

- Journeys `tests/journeys/test_j33_consumer_apis.py`: seen failing first (12 of 14; the two "absent
  when disabled" cases pass either way), then 14 passed (7 cases on two configurations).
- Unit `tests/unit/engine/model/authoring/`: 2,554 passed; the outline of a definition written by
  hand without its key or with a version that is not a number (found in the final review: the outline
  route would have failed on it); the consumer kinds over every part of both
  models' definitions (about 600 applied and undone exactly per model; the rest refused for a shape
  the grammar does not allow), `addConsumerApi` for every type of both models compiling, and every key
  of the example re-keyed with its consumer API kept.
- Groups `authoring`, `model`, `model_admin`, `contract` by EXECUTION_GUIDE §2: 3,206 passed in 73 s,
  parallel; the serial part selects none. `ruff check app/ tests/` clean. No migration. The OpenAPI
  lock is unchanged (the routes are gated); the gated inventory and API_JOURNEYS list the four routes.
- Vitest: `src/features/model-editor` and `src/routing`, 181 passed (the consumer descriptors, the
  history's consumer words, the address); `vitest related` over every changed source file, 60 files
  and 703 tests passed. `npm run format`; `npm run lint`, 0 errors (the 7 earlier warnings); `npm run
  build` succeeds.
- Browser: `test:browser:authoring-a4c`, 20 checks on both designer models (listed in
  EXECUTION_GUIDE); `test:browser:authoring-a4a` (44) and `-a4b` (29) for the shared pane, frame and
  dialogs.
- **Not run:** the full suites, `test:a11y` and `test:visual` (build acceptance; the editor joins the
  gates at T1). Dark mode is uninspected.
- **Appearance:** inspected at 1440px in the light theme from the runner's screenshots (the Fields
  tab, the Schema with and without a contract change, the install dialog) and at 390px (the
  definition and the pane). Two fixes came of it: a pane row with a name, a mark and the contract pill
  pushed the name out (the row's note is now the version alone, and the name keeps a few letters), and
  at 390px a role broke letter by letter. The user approved the screenshots, 2026-10-12.

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

##### T1 plan (2026-10-12)

**Planned 2026-10-12; accepted by the user the same day ("otherwise ok"): D60–D64 and the test
cases, with D60 amended at the user's question: the walks also click every button they use, since
earlier packages' runners passed while a button's action was wrong.** Checked
against the code at `5963d96`:

- **What each package proved on its own.** `test:browser:authoring-a4a` (44 checks), `-a4b` (29) and
  `-a4c` (20) each run on both designer models (D20) and walk their own surface; none walks US-P05
  from start to end, and each starts from a draft its own setup prepared. The API side is covered by
  `test_j33_operations`, `test_j33_outline`, `test_j33_layout`, `test_j33_consumer_apis` and
  `test_j33_design`, two configurations each.
- **What was deferred to T1.** Every designer package left its surfaces out of the accessibility
  gate (`e2e/accessibility-gate.mjs`, 109 checks at 0.9 R) and the visual gate
  (`e2e/visual-regression-gate.mjs`, 100 baselines), and dark mode uninspected: N1's sidebar groups,
  group page and phone band; A4a's editor, matrix, Move to…, operation and install dialogs; A4b's
  preview, layout editor and its dialogs; A4c's Consumer APIs tab, a definition's tabs, its dialogs
  and the install dialog's section (TODO). A4a's shared dialog and menu styles and N1's phone band
  changed existing baselines, which are to be re-recorded after review.
- **What the release touches.** One migration since 0.9.0 (`20261011_01_model_draft_operations`),
  whose upgrade from `20261007_08`, interruption and recovery A2 tested in `test_startup`. Version
  strings in `backend/pyproject.toml`, `backend/app/config.py` (`ENGINE_VERSION`) and
  `frontend/package.json`, written as 0.9.0-alpha.1 was (`0.9.0-alpha.1`). The starter model is
  unchanged (D3), so no content release.
- **Open in TODO that touches the line:** A4b's once-seen runner case (the added application still
  in the draft after Undo); the startup check for a migration changed after it was applied (for the
  user to decide; not T1's).

**What is built:**

1. **A composed browser journey**, `e2e/authoring-t1-designer.mjs` (`test:browser:authoring-t1`),
   US-P05 from start to end on both designer models, naming no key (D60, cases below).
2. **The gates:** the designer's surfaces into the accessibility and visual gates, light and dark
   (D61); the changed baselines re-recorded after the user reviews their differences.
3. **The backend groups together** (D62), and the release's migration check (D63).
4. **The interim release** 0.10.0-alpha.1 (D63): CHANGELOG section, version strings, PROJECT_STATUS,
   TODO; the commit and tag `v0.10.0-alpha.1` on the user's instruction.

No behaviour changes are planned. A defect found is fixed in T1 with its regression test when it is
small, or becomes a named amendment (T1a, …) before the release when it changes what A3 or A5 build
on (D64).

**Decisions** (D60 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D60 | What the composed journey walks, and how | *Amended at acceptance:* **One runner, both designer models, each walk done once by keyboard alone and once by clicking, at 1440px, then a shorter walk at 390px.** Walk 1 is keyboard alone on the renamed example and clicked on generated-b; walk 2 the other way round, so every step is taken both ways and the runner's length is unchanged. Clicking means the real button (found by its role and name, clicked as a user does, no API shortcut in between), and each click is checked by what the screen shows and what the server then holds, so a button that calls the wrong action fails. T1 adds the end-to-end order nobody has walked, the keyboard for all of it, which the spec names, and every button in it clicked. Two walks per model: *from an empty draft* (an application, two types under each other, attributes, a relation allowed from the matrix, a navigation group, a column and a panel laid out, a consumer API exposing the new types; install and activate; a record of each new type created on the record screen; the consumer tier serving one) and *extending the active model* (a type under a released one, an attribute on a released type, a relation, a field added to the released consumer API, which then needs a higher contract version, raised; install and activate; a record created and seen in its released parent's panel). At 390px: open the editor, add a type and an attribute through the phone tabs, install and activate, create a record. Cost: one runner of about 3–4 minutes over both models |
| D61 | Which surfaces join the gates, and in which themes | **Every designer surface into the accessibility gate in light and dark; into the visual gate, light for every surface and dark for one per package.** Accessibility (about 20 scenarios): the sidebar groups, the group page, the phone band; the editor's model pane with an element, the matrix, Move to…, an operation dialog, the install dialog, Issues and History; the preview and the layout editor with its group and sort dialogs; the Consumer APIs tab, a definition's Fields and Schema tabs, a consumer dialog and the install dialog's consumer section. Visual (about 16 light, 5 dark): the same surfaces' screens, dark for the sidebar groups, the model pane, the preview, the layout editor and a consumer definition, as 0.9 kept dark to a representative subset. The changed existing baselines (dialogs, menus, the phone shell) are re-recorded only after the user has seen the differences; a difference not explained by N1 or A4a stops the gate as a defect. Both gates run on the example model as they do today: the designer models' second configuration is the runners' job (D60) |
| D62 | Which backend checks | **`authoring` and `model` together, as the spec says, with `model_admin`, `contract` and `startup` for the release (D63); no full suite**, which waits for R by AGENTS.md. Run once, parallel and serial parts, within the 2-minute ceiling or reported with its time |
| D63 | What the alpha's migration check covers | **Clean bootstrap and restart, the upgrade of a database built by 0.9.0 (tag `v0.9.0`, at `20261007_08`, with records and a draft) to the head, and schema 0.9 → 0.10 activation, plus a smoke start on a copy of the development database.** The upgrade and its interruption are A2's `test_startup` case, rerun with the `startup` group; the 0.9 → 0.10 activation is N1's `test_earlier_models_are_unchanged_by_schema_0_10`, rerun; the database built by the 0.9.0 code itself (not by the head's baseline downgraded) is the one new step, done once by hand with the tagged code in a scratch worktree and a scratch database, both removed after. Versions written `0.10.0-alpha.1` in the three files, as 0.9.0-alpha.1 was |
| D64 | When T1 passes, and what a failure does | **T1 passes when the composed runner, the gates and the backend groups pass and the user approves the screenshots and baseline differences; then the release steps run.** A defect found is fixed in T1 with its regression test when it is local to the designer; one that changes the operation API, the outline or a contract A3 or A5 builds on becomes an amendment package before the release, with the user's agreement. A runner flake seen once is rerun once and recorded in TODO, as 0.9 R's D201 did; seen twice it is a defect |

**Journey test cases** (browser, `test:browser:authoring-t1`, on the renamed example and
`generated-b`, naming no key of either; types, applications and parents read from each model):

1. **J33.1 + J33.13, from an empty draft** (keyboard alone on one model, clicked on the other; D60).
   Given an empty draft opened from Settings › Model. When an application, a top type, a child type under it, an
   attribute on each, a relation allowed between them from the matrix, a navigation group holding
   the top type's collection, a column moved and a panel hidden in the layout editor, and a consumer
   API exposing both types are added, each by keys alone or by clicking its buttons, then History lists each as one step and
   Issues is empty. When installed and activated from the install dialog, then the application's
   sidebar shows the group, a record of the top type and a child under it are created on the record
   screen with the layout as laid out, and the consumer tier answers the child record valid against
   the Schema read in the editor before installing.
2. **J33.2 + J33.14, extending the active model** (the other way round from case 1). *Amended in
   the record: the field added is compatible; a released field renamed is the change that needs the
   higher version.* Given a draft of the active
   release with records in it. When a type under a released type, an attribute on a released type,
   a relation from a released type to the new one, and a field from the new attribute in the
   released consumer API are added, then the released elements stay marked released, the definition
   shows that it needs a higher contract version, and the install dialog holds Activate until it is
   raised in one step. When installed and activated, then a record of the new type is created under
   an existing parent and shown in the parent's children, the existing records keep their values,
   and the consumer tier serves the field at the new version and answers `404` at the old one.
3. **J33.4 inside the walk.** In walk 2, one step is undone and redone (by keyboard or the bar's
   buttons, as the walk goes) before installing,
   and a new step after an undo leaves nothing to redo.
4. **J33.11 at 390px.** On each model, a draft opened at 390px: a type and an attribute added
   through the phone tabs, installed and activated, a record of the type created; no horizontal
   scroll on any screen of the walk.
5. **No error and nothing left.** Across the walks, the browser shows no `Error:` text and no
   console error; the runner's drafts are installed or deleted, and its databases are clones removed
   after.

These pass on the first run if the packages are right, since T1 changes no behaviour (as 0.9's T1
found); they cannot be confirmed failing first, which the record will say.

**Groups:** `authoring`, `model`, `model_admin`, `contract`, `startup`; `test:browser:authoring-t1`;
`test:a11y` and `test:visual`, extended (D61); no Vitest beyond the files a fix changes; `npm run
format`, `lint`, `build` if a frontend file changes. **Not run:** the full suites and the other
browser runners (R).

**Composable domains (ADR-032):** no contract changes; no door is affected.

##### T1 record (2026-10-12)

**Delivered 2026-10-12 and released as 0.10.0-alpha.1 (D14):** the user approved the screenshots and
the changed baselines and asked for the commit and the interim release ("you can commit and make the
interim release"). Version strings `0.10.0-alpha.1` in `backend/pyproject.toml`, `ENGINE_VERSION` and
`frontend/package.json` (with its lock); the CHANGELOG section; the tag `v0.10.0-alpha.1`. The visual
gate's update mode rewrites every baseline; only the 8 reviewed and the 23 new ones were kept, the
68 others restored, and the gate then passed (123 checks). Built as planned, with these differences
and findings:

- **Walk 2's contract change is a rename.** Adding a field to a released consumer API is compatible
  (the contract check counts only what consumers lose or see change), so the walk adds the field from
  the new attribute, sees no version needed, then renames a released field, which needs version 2.
  Case 2 is amended to say so.
- **Keyboard mode chooses a select's option by typing its name.** On macOS a closed native select
  opens its list on the arrow keys rather than changing its value, as a keyboard user there knows; the
  runner types the option, as that user does, and fails if another option is chosen.
- **Defect (from A4a): after installation everything the draft added read as changed.** The release
  holds each element with its defaults written out (`model_dump`), the draft what was authored, and
  the outline compared them as raw JSON, so after an installation the new type, its attribute, its
  relation, its parent type and its application, and a consumer API added in the draft, were all marked
  changed against the release just installed from them. Marks now compare one element at a time in the
  release's form (`outline._same`, through the schema class of each element), so they stay right
  while the rest of the draft is invalid. Found in the phone-editor screenshot of the gates'
  surfaces. Regression: `test_after_installation_what_the_draft_added_is_marked_released` (J33.2, two
  configurations), seen failing without the fix; walk 2 now checks that the new type and its parent
  read released after installing.
- **Defect (from A4b): the preview's History panel read the live API.** For a new type's empty record
  it asked `GET /objects/{type}/preview-empty-record/history`, a 404 in the browser's console. The
  History panel used the plain client, not the page's (`useDataApi`), so the preview's client never saw
  the read. It now reads through the page's client; the change-set and publication clients pass history
  through unchanged, so nothing else changes. Found by the runner's console check on generated-b's
  clicked walk (the keyboard walk had hidden that panel). Regression in `HistoryPanel.test` (the panel
  under the preview's client asks the server nothing), seen failing without the fix.
- Both defects passed their packages' runners because those runners watched neither the console nor
  the marks after installing; T1's runner fails on any console error, any 4xx or 5xx response and
  any `Error:` text.
- **The designer surfaces in the gates** are one helper, `e2e/helpers/designer-surfaces.mjs`, visited
  by both gates as 0.9's `release-surfaces` is: 18 surfaces on the starter model raised to 0.10 with a
  type, an attribute and a navigation group set up by one operation request, light and dark (36
  accessibility scenarios), and 23 visual baselines (18 light, 5 dark: the type panel, the preview, the
  layout editor, a consumer API's fields and the sidebar's groups).
- **Dark mode inspected** for every designer surface from the gates' screenshots: the semantic tokens
  hold; no defect seen.

**Checks:**

- Browser: `test:browser:authoring-t1`, 34 checks on both designer models in 42 s (walk 1 by keyboard
  on the renamed example and by clicking on generated-b, walk 2 the other way round, 390px on each),
  then walk 1 (18) and walk 2 (16) again after the last changes. The cases pass, as T1 changes no
  behaviour; they were not seen failing first, except where the two defects made them fail.
- `test:a11y`: 145 checks (109 and the 36 designer scenarios) passed in 2 min 53 s. A first run was
  stopped by a timeout after the machine slept (1 h 48 min of wall time) and was run again.
- `test:visual`: 123 checks in 2 min; the 23 designer baselines are new, and 8 existing ones differ:
  the four phone screens (`narrow-collection-domain-*`, `narrow-record-detail-domain-*`: N1's band and
  no top-bar tabs) and the export and import dialogs, light and dark (A4a's shared dialog spacing).
  Each difference was inspected and is explained by N1 or A4a; none recorded until the user approves.
- Backend groups `authoring`, `model`, `model_admin`, `contract`, `startup`: 3,364 passed in 1 min
  43 s, parallel; the serial part selects none. `ruff check app/ tests/` clean.
- Frontend: `vitest related` over `HistoryPanel.tsx`, 4 files and 52 tests; `npm run format`; `npm
  run lint`, 0 errors (the 7 earlier warnings); `npm run build` succeeds.
- **Migration (D63):** the `startup` group above (A2's upgrade from `20261007_08`, its interruption
  and recovery, clean bootstrap and restart). By hand: the tagged 0.9.0 code in a scratch worktree
  built a scratch database on the development server (`20261007_08`) with a record and a draft; the
  head code upgraded it to `20261011_01`, kept the record and the draft (with an empty history),
  applied operations to that draft raising it to schema 0.10 with a navigation group, installed and
  activated it (the 0.9 → 0.10 activation), and started again; no error in its log. N1's
  `test_earlier_models_are_unchanged_by_schema_0_10` is in the `model` group above. Smoke start: a
  copy of the development database (143 MB, `pg_dump` and `pg_restore`) answered `/system` and
  `/model` with 200. Worktree and both scratch databases removed.
- **Not run:** the full suites and the other browser runners (R). The record screen's runners were not
  run for the History panel change: the panel's request is the same function through the page's
  client, and the gates' record pages passed.
- **Seen, not started by this session:** the user's development server and its PostgreSQL, and the
  `uvicorn` on port 61380 noted in A4c, left running.

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
  row list. Every row, as a job; a newer draft version cancels the running one (D67, replacing D9).
- The W1, W1′, W2 and W3 generators.

**Tests:** W1, W2 and W3 profiled (header and block detection, statistics); the dry run on W1 after a
rename, a move and a value map, with its difference; the whole file checked, a superseded run cancelled; the
budget measured once and recorded.

**Groups:** `authoring`, `jobs`, `contract`, `startup` (if a table is added), `volume` (the budget).

**Exit:** profiles and summaries in API.md; the budget recorded.

##### A3 plan (2026-10-12)

**Planned 2026-10-12; accepted by the user the same day: D65, D66 and D68–D71 and the test cases
as recommended ("otherwise its fine"), D68 after asking what ignoring colour and formatting means;
D67 changed by the user from a sampled interactive run to a check of the whole file ("by definition,
the dry run is a dry run, a check of the whole set"), which withdraws D9's 1-second target.** Checked
against the code at `b0ae3ef`:

- **The import path takes its model as a value.** `check_profile(model, definition)`, the binding
  (`imports/binding.py`) and `run_items` over a `BatchContext` read the `EngineModel` they are given;
  only `open_batch_context` resolves it from the active release or the change set. The unique rule
  (`rules.unique_values`) reads holders from `attribute_values` through the lookup, not from
  `unique_attribute_values`, so a draft that adds a type or makes an attribute unique is checked
  correctly by the same rules. The database's `check` after the write sees only the active release's
  unique attributes; for a draft's newly unique attribute the rule is the only check, which is enough
  in a rolled-back run. **So the dry run is the J3 preview with the draft's compiled model in the
  context, and no second validation path** (principle 4).
- **D9's budget does not hold on that path.** 0.9 measured the preview's own step at about 5–8 s
  live and 18 s in a change set for 10,000 items (D82, POSTGRESQL_BUDGETS), holding the workspace's
  write lock that long; PG3b measured 0.25–0.46 s per 500 items. Reading 10,000 rows of XLSX through
  openpyxl adds seconds of its own. D9's "1 s for 10,000 rows" cannot hold for a check of the whole
  file; D67 withdraws it.
- **Job files cannot hold a source file** (A0, checked again): `JobFiles.reconcile` removes every file
  in `JOB_FILE_DIR` whose name is not a running or completed job's.
- **A draft may be invalid between steps** (A2); installation then refuses it `422 INVALID_MODEL`
  with its diagnostics (`model_management.install_model_draft`).
- **No draft holds a profile before A5** (D12, D13), so A3's dry run needs the profile in its request.
- Migration head `20261011_01_model_draft_operations`; settings in `config.py`
  (`INTEGRATION_JOBS_ENABLED`, `JOB_RETENTION_DAYS`, `JOB_PREVIEW_MAX_ITEMS`, `IMPORT_MAX_BYTES`);
  the J2 workbook helpers are private to `test_j27_import.py`.

**What is built:**

1. **Migration** `20261012_01_source_files`: `source_files` (`id`, `draft_id` → `model_drafts`
   `ON DELETE CASCADE` or `profile_key` → `import_profiles` `ON DELETE CASCADE`, exactly one;
   `name`, `format`, `bytes`, `sha256`, `version`, `uploaded_at`, `superseded_at`, `profile_job_id`);
   `source_file_rows` (`source_file_id` cascade, `sheet_index`, `row_number`, `cells` JSON array,
   primary key on the three) for staged rows (D66); `source_file_sheets` and `source_file_columns`
   for the profile, keyed by file, sheet index and column, paged by them; `model_draft_dry_runs`
   (`draft_id` cascade, `source_file_id`, `draft_version`, `request` JSON, `summary` JSON, `job_id`,
   `ran_at`), the latest and its predecessor read for the difference. A `jobs.kind` of `profile` and
   `dryRun`.
2. **Engine `engine/sources/`** (no FastAPI):
   - `files.py`: store an upload under `{sourceFileId}.file` in `JOB_FILE_DIR`; `reconcile` taught
     its names (a file is kept while its row exists); supersede the owner's older file and remove it
     `JOB_RETENTION_DAYS` later (the sweep the job retention already runs).
   - `staging.py`: the `profile` job reads the file once through the J2 readers and stages its rows
     with `COPY` into `source_file_rows`, per sheet, without a header assumption.
   - `profiling.py`: set statements over the staged rows (D68): the header row and blocks per sheet,
     then per column `filled`, `distinct`, `valueTypes`, `candidateKey`, `delimiters`,
     `placeholders`, `overlaps` with other columns and with existing records (D69).
   - `staged_file.py`: a `TabularFile` over `source_file_rows`, so the J2 binding reads staged rows
     with no change to the binding (D66).
   - `dry_run.py`: open a context of the named workspace with the draft's compiled model; bind the
     request's profile over the staged file; run the J3 preview over every item as a `dryRun` job,
     cancelling the draft's running one (D67);
     record the summary per source with rejections by code, and its difference from the draft's
     previous dry run of the same file.
3. **Routes** (`management/routers/source_files.py` and the dry-run routes in
   `model_management.py`), as API.md designs them, gated by D6: `POST /source-files` (multipart),
   `GET /source-files` (`draftId` or `profileKey`, paged), `GET /source-files/{id}`,
   `DELETE /source-files/{id}?expectedVersion=`, `GET …/profile/sheets`,
   `GET …/profile/sheets/{sheet}/columns` (both paged, `409 SOURCE_FILE_PROFILE_NOT_READY` until the
   job ends); `POST /model-drafts/{id}/dry-run` (D65), `GET …/dry-run` (the latest),
   `GET …/dry-run/rows` (`source`, `status`, `code`, paged, as `/jobs/{id}/rows`);
   `sourceFileId` on `POST /imports` in place of the `file` part. OpenAPI lock re-baselined.
4. **Generators** `tests/workbooks.py`: W1, W1′, W2 and W3 as A0 defines them, from a seed and a
   size, written with openpyxl in an invented neutral domain; one sample of each opened in the
   user's spreadsheet program before the shape is fixed (mock up before building formats).
5. **Documents:** API.md moves source files and the dry run into "delivered" with their field-level
   detail; API_JOURNEYS moves the A3 routes, codes and settings out of "planned"; OPERATIONS gains the
   new setting (D67) and the storage of source files; CHANGELOG, PROJECT_STATUS, TODO.

**Decisions** (recommendations):

| # | Question | Recommendation |
| --- | --- | --- |
| D65 | Where the dry run's import profile comes from before A5 | **In the request: `POST …/dry-run` `{ "sourceFileId", "workspaceKey", "profile" }`, the inline profile `POST /imports` takes, checked against the draft's model.** A draft holds no profile until A5 (D12, D13). In A5 the editor stops sending it: the draft's profile is used and every operation's answer carries the summary. The request form stays for integrators, who keep their profile outside the engine |
| D66 | How the dry run reads its rows | **From the rows the profile job staged, through a `TabularFile` over `source_file_rows`; the binding is unchanged.** The file is read once, at upload. Reading a 10,000-row workbook through openpyxl again after every editor step would cost seconds by itself. The staged rows stay while the file exists, so A5's row lists and A6's evidence read them too |
| D67 | D9's budget on the J3 preview path | **Accepted as changed by the user: every dry run checks the whole file, every item the import would run, through the J3 preview path; a file too large for an import is refused alike. It runs as a `dryRun` job, so an operation answers at once and the summary reads `checking` until the job ends; a newer draft version cancels a running dry run of the draft and starts its own. D9's 1-second target is withdrawn; the time on W1 at 10,000 rows is measured once and recorded.** The recommendation was a sample of the first 1,000 items; the user rejected it because a sample cannot say whether the load will work, which is a dry run's purpose. Each run holds the workspace's write lock for its length (5–8 s at 10,000 items, 0.9's figures); cancelling superseded runs bounds how often. Running it in a change-set context, which does not block live writes, is the known alternative (about 18 s at 10,000 items) if the measurement shows the lock matters |
| D68 | How the header row and blocks are found | **Per sheet, the header is the first row whose filled cells are all text and are followed by rows filled in the same columns; blocks are runs of filled columns separated by fully empty columns, each with its own header row.** It covers W1 and W2 and reports W3's blocks, which A8 confirms (A-D9). Nothing reads colour or formatting. An administrator who disagrees changes the profile's `headerRow` and `block`, as J2 allows |
| D69 | Overlap "with existing records of mapped types" before any mapping exists | **Overlap with the values of the draft model's unique attributes and record names in a workspace the profile request names, the best five per column, each over distinct values and bounded (`PROFILE_OVERLAP_SAMPLE`, 1,000 distinct values per column).** A3 has no mapping (A5) to say which type a column belongs to; unique attributes and names are what A6's extend mode will match on. Without a named workspace the profile has column-to-column overlaps only |
| D70 | Placeholders | **A value is a placeholder when it is one of a fixed list (`N/A`, `n/a`, `NA`, `-`, `--`, `?`, `TBD`, `tbd`, `none`, empty after trimming) or a value of at most two non-alphanumeric characters found in at least 1% of a column's cells; each listed with its count.** Fixed and visible, so a test can name its expectation; A6's pattern decides what to do with them |
| D71 | A dry run on a draft that does not compile | **Refused `422 INVALID_MODEL` with the draft's diagnostics, as installation refuses it; nothing recorded.** A draft may be invalid between steps (A2); a summary from a model that cannot be installed would mislead, and one code for "this draft does not compile" serves both routes |

**Journey test cases** (`tests/journeys/test_j34_onboard.py`, J34.1 and J34.3; each on two
configurations: the workbooks are the same, the draft is the configuration's model with types added
by operations, so no test names a configuration's key):

1. **J34.1 Upload and profile.** Given a draft and W1 at 200 rows, when it is uploaded, then a
   `profile` job is queued, the profile reads `409 SOURCE_FILE_PROFILE_NOT_READY` until it ends,
   and then lists `S1` and `S2` with header row 1 and their row counts; `S1`'s columns, paged two at a
   time, give `K` as the only candidate key, `P` with about `n/15` distinct values, `T`'s `N/A` and `-`
   as placeholders, `Fo`'s `;` as a delimiter, and `Ln` overlapping `S2`'s `N`.
2. **J34.1 Blocks.** Given W3, when profiled, then each block is reported with its range and header
   row, separated by its empty columns, and the section and group header rows are not columns.
3. **J34.1 Limits and refusals.** A file over `IMPORT_MAX_BYTES` is `413 IMPORT_TOO_LARGE`, an `.xls`
   is `422 UNSUPPORTED_FILE_FORMAT`; a second upload to the same draft supersedes the first, which is
   still listed until the retention sweep; deleting the draft deletes its files and their rows.
4. **J34.3 The dry run follows the editing.** Given a draft with a new type and W1 mapped by an inline
   profile, when the dry run runs, then it counts records, values and relationships per source with
   rejections by code; after `setKey` on the mapped attribute (with the profile updated) the next run
   is the same; after a value map for `T`'s placeholders the rejections fall and the difference names
   the figures that changed against the last run; `GET …/dry-run/rows?code=` lists the rows behind a
   rejection figure.
5. **J34.3 The whole file.** Given W1 above 1,000 rows, the dry run's summary covers every row;
   a draft changed while a dry run runs cancels it and the next summary is of the new version; the
   dry run writes nothing (the workspace's records and feed are unchanged).
6. **J34.3 Refusals.** A dry run on a draft that does not compile is `422 INVALID_MODEL`; a
   profile naming an element the draft lacks is J2's `422` with the problem at its pointer; an unknown
   source file is `404 SOURCE_FILE_NOT_FOUND`.
7. **J27 variant, `sourceFileId` on `POST /imports`:** an import naming a stored source file loads as
   the same file sent inline does.

**Unit tests** (`tests/unit/engine/sources/`): header and block detection on edge shapes (a title
row above the header, an empty first column, one-column blocks), placeholders and delimiters,
generated combinations; the staged `TabularFile` gives the same rows as the J2 readers for one
XLSX and one CSV.

**Budget:** measured once (D67), recorded in POSTGRESQL_BUDGETS: profiling W1 at 10,000 rows, and
the interactive dry run on it. Run in `volume` only when the release runs budgets.

**Groups:** `authoring`, `jobs`, `contract`, `startup` (the migration: clean bootstrap, upgrade from
`20261011_01`, restart, an interrupted upgrade), `test_api_journeys.py`; `J34` joins
`JOURNEY_GROUPS` as `authoring`, `jobs`. No frontend change.

**Composable domains (ADR-032):** inbound flow gains a stored source file an import can name and a
dry run of an import against a draft; identity, attribute storage, audit and history, bulk APIs, the
`match` declaration and mapping coverage are unchanged. No door is affected.

##### A3 record (2026-10-12)

**Delivered 2026-10-12** as planned, with D65, D66 and D68–D71 as recommended and D67 as the user
changed it; through the API only (no editor surface, A5's). What is built:

- **Migration `20261012_01_source_files`**: `source_files` (one owner, a draft or a profile, cascade),
  `source_file_cells` (the staged cells, D66), `source_file_sheets`, `source_file_columns`; `jobs.kind`
  gains `profile` and `dryRun`. A downgrade removes them and the jobs of the new kinds.
- **`engine/sources/`**: `store.py` (upload, supersede, read, delete, the retention sweep, an import's
  stored upload), `values.py` (a cell staged with its kind, text and value, and back), `profiling.py`
  (the `profile` job: `COPY` of every filled cell, blocks and header rows by D68, statistics,
  placeholders and overlaps as set statements), `staged.py` (`StagedFile`, a `TabularFile` over the
  staged cells), `dry_run.py` (submit, the context with the draft's model, the summary and its
  difference). The worker runs both kinds; `JobFiles.reconcile` keeps `{id}.upload` while its row
  exists. The binding takes an opener for its rows (`bind_import(…, open_book=)`), nothing else in it
  changed.
- **Routes** as API.md now records them; `sourceFileId` on `POST /imports`; `GET /jobs/{id}/rows`
  serves a dry run. OpenAPI lock re-baselined by diffing the document against HEAD: the four
  source-file paths, their schemas, `ImportRequest.sourceFileId`, the import's optional file part and
  the two job kinds, nothing else; the dry-run routes are model administration's, in the guarded
  list.
- **Browser** (not planned, found in the checks): the Jobs list and notifications would have named a
  profile or dry-run job "Batch"; they read "Profile of <file>" and "Dry run of <file>" (`KIND` in
  `jobText.ts`, `jobTitle`).
- **Generators** `tests/workbooks.py`: W1, W1′, W2, W3 from a seed and a size.

**Where it differs from the plan and the design:**

1. **No `model_draft_dry_runs` table.** The dry run's job holds its summary (`jobs.report.dryRun`) and
   the previous one is the draft's last completed dry run of the same file, so a summary, and the
   difference against it, lasts as long as the job (`JOB_RETENTION_DAYS`).
2. **No `{ "full": true }`** on `POST …/dry-run`: every dry run checks the whole file (D67).
3. **D68's fallback** for a block whose header has an empty cell is the text row with the most cells
   (the first of equals), found while writing the unit tests; the plan's "first text row followed by
   a row within its columns" found none in that case.
4. **Two approved test-case statements do not fit W1 as A0 defined it** (spec gaps, for the user):
   case 1 says "`K` as the only candidate key", but `X`, a GUID on every row, is one too, so the
   test asserts `K` and `X`; it says "`Ln` overlapping `S2`'s `N`", but `Ln` (colour names) shares no
   value with `S2`'s `N` (item names), so the test asserts `K` with `S2`'s `K` and `N` with `S2`'s `N`.
   W1's names repeat across records (a generator choice), so `N` is not a candidate key.
   **Accepted by the user on 2026-10-12** ("the corrections are good"), together with the W1′, W2
   and W3 samples generated from `tests/workbooks.py` and opened in the user's spreadsheet program.
5. **Test order:** the journey cases were written after the code, not seen failing first (step 5).
6. **The smoke start** was done by the user's own development server: running with `--reload`, it
   restarted on the code change and migrated the development database to `20261012_01` (healthy, its
   53 jobs kept, the new routes answering).
7. New codes beyond the design: `404 SOURCE_SHEET_NOT_FOUND`, `404 DRY_RUN_NOT_FOUND`, `410
   SOURCE_FILE_MISSING`.

**Found, not changed:** `tests/unit/engine/imports/` (77 cases) belongs to no group in
`UNIT_GROUPS`, although EXECUTION_GUIDE lists it under `jobs`, so a `-m jobs` run leaves it out;
`engine/sources/` was added to the map.

**Follow-up the same day, at the user's request:** the 19.8 s split into binding 9.3 s (8.1 s of it
one statement looking up relationship links per row, a 0.9 import defect) and preview 11.5 s; the
statement now collects the links once (1.4 s), held by a plan check in `test_binding`; `jobs` group
370 passed, import unit tests and J34 passed; the dry run is 13.2 s. The preview's options are in
TODO for an A3a.

**Measured once** (D67, POSTGRESQL_BUDGETS §11): W1 at 10,000 rows profiled in 6.3 s, dry run 19.8 s
for 19,453 items, about J3's cost per item; the preview holds the workspace's write lock most of that
time. Recorded in TODO with the options, for a decision before A5 runs a dry run after every step.

**Checks:** J34 (`test_j34_onboard.py`, 7 cases × 2 configurations): 14 passed. Unit tests
`tests/unit/engine/sources/` (92) and the upload sweep case in `test_files.py`: passed. The groups
`jobs`, `contract` and `startup` in parallel: 471 passed in 1 min 50 s, and their serial case; the
first run's 31 failures were this package's (the pinned head revision, the reviewed foreign keys, a
boundary rule against `session.delete`, the dialect check's `json_typeof`, a unit test's fake
session) and were fixed and rerun. A new `test_startup` case: upgrade from `20261011_01` keeping a
draft and a job, an interrupted upgrade refused and recovered, two restarts, a file profiled after
the upgrade, and the downgrade. `test_api_journeys`, `test_openapi_contract`, `test_schema_drift`,
`test_boundaries`, `test_j33_operations`: passed. `ruff check app/ tests/`: clean. Frontend: Vitest
`src/features/jobs` (31) passed; `npm run format`, `npm run lint` (0 errors, the 7 listed warnings),
`npm run build`: passed. **Not run:** the `authoring` group's 2,632 A2 cases (no code of theirs
changed), every browser runner (no surface changed beyond the job titles), the full suites (R).

### A3a: A faster trial run

**Needs:** A3. Added by the user on 2026-10-12, after the dry run of W1 at 10,000 rows measured
19.8 s and the binding fix brought it to 13.2 s, 11.8 s of it the trial run (the J3 preview), which
holds the workspace's write lock (POSTGRESQL_BUDGETS §11). The trial run is shared: a dry run, an
import's preview and a batch's preview all run it.

##### A3a plan (2026-10-12)

**Planned 2026-10-12; accepted by the user the same day ("yes"), D72, D73 and the test cases as
recommended.** Checked
against the code at `4d29daa`, with the statement timings of §11:

- **Audit entries in a trial run** cost 1.6 s in PostgreSQL (`audit_events` 1.2 s, their subjects
  0.4 s) plus building them in Python (`to_jsonable` over every change), and take feed positions.
  Both bulk write paths call `record_all` (`engine/records/bulk.py`) and ignore what it returns; no
  rule, lookup or summary reads an audit entry within a run; the run is rolled back.
- **The very large statements are one function's.** `increment_set_versions_by`
  (`engine/records/relation_set_versions.py`) writes up to 1,000 sets per `INSERT … VALUES` with ten
  named parameters per row, about 368,000 characters each: 0.8 s in PostgreSQL for W1 and most of
  the 4.5 s (profiled) psycopg spends turning statements into PostgreSQL's form. The record, value
  and relationship inserts are short statements and are not changed.
- The rest (about 5 s) is PostgreSQL writing the rows the trial run tests, and the ORM's bookkeeping;
  A3a does not change it.

**Decisions:**

| # | Question | Recommendation |
| --- | --- | --- |
| D72 | Audit entries in a trial run | **A trial run records none and takes no feed position: `run_items(previewing=True)` marks the session, and `record_audit_events` writes nothing while it is marked.** No reader exists inside the run and everything is rolled back, so the outcome of every item is unchanged. An execution, and every single write, audits as before |
| D73 | How sets advance in bulk | **One `INSERT … SELECT … FROM unnest(…)` per thousand sets, each column one array parameter, with the same `ON CONFLICT` rules and the same key order.** It writes exactly what it writes today, for every batch, import, preview and live write; the statement stays short whatever the number of sets. `COPY` was considered and set aside: it cannot express the conflict rule that advances an existing set |

**Expected:** the trial run of W1 from 11.8 s to about 8–9 s, and the lock with it; the binding
(1.4 s) is unchanged. Measured once after the change.

**Test cases** (behaviour is unchanged, so no new journey; the existing journeys of previews and
relation sets are the cases):

1. **Unit, `tests/unit/engine/records/test_relation_set_versions.py`:** advancing more than 1,000
   sets at once, some already written and some new, live and in a change set, leaves each at its old
   version plus its count (generated over counts and existing versions).
2. **Unit, `tests/unit/engine/records/test_audit.py`:** while a session is marked as a trial run,
   recorded entries write no event, no subject and take no feed position; unmarked, they do.
3. **Existing journeys rerun as the cases of the shared paths:** J27.11 and J11's previews (outcomes
   and summaries unchanged), J34 (the dry run's summary unchanged), the relation set journeys (J13,
   J24's set versions), and `test_batch_statements` (its statement counts, updated only where a
   preview's audit statements disappear).

**Groups:** `jobs`, `records`, `change_sets` (the write paths), `volume`'s `test_batch_statements`;
`ruff`. No migration, route or frontend change.

**Composable domains (ADR-032):** audit and history are unchanged for every write that commits; a
trial run never committed any. No door is affected.

##### A3a record (2026-10-12)

**Delivered 2026-10-12** as planned (D72, D73). `engine/records/audit.trial_run` marks a session
during a trial run and `record_audit_events` writes nothing while it is marked; `run_items` marks
it when previewing. `increment_set_versions_by` advances up to 1,000 sets per
`INSERT … SELECT … FROM unnest(…) WITH ORDINALITY`, each column one array parameter, with the
same conflict targets (the live partial index, the change-set constraint) and key order.

**Measured once** (W1 at 10,000 rows, 19,453 items, as §11): binding 1.24 s, trial run **5.75 s**
(11.8 s before; the plan expected 8–9 s), the dry run about 7 s in all, with the same summary
(9,453 records, 9,453 relationships, the placeholder rows refused). The workspace's write lock is
held about 5.8 s per dry run.

**Checks:** the two unit tests (`test_audit`'s trial-run case, written first and seen failing on the
missing marker; `test_relation_set_versions`, 6 cases over three seeds, live and in a change set,
passing before and after as the plan's guard). The groups `jobs`, `records` and `change_sets` in
parallel: 1,064 passed, and their 3 serial cases; `test_batch_statements` unchanged and passing
(its counts measure executions, not previews); `tests/unit/engine/imports/` and J34: passed.
`ruff check app/ tests/`: clean. **Over the ceiling:** the three groups took 3 min 40 s, above a
package's 2-minute ceiling (AGENTS.md), and the run was not announced beforehand; the selection was
the guide's for the write paths the package changed.

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

##### A5 plan (2026-10-12)

**Planned 2026-10-12; accepted by the user the same day: D74–D78 and D80–D85 as recommended, the
test cases and the mock-up ("otherwise its ok, the canvas is also ok, test cases too"); D79 asked
about (which steps, and the time), restated below and accepted as restated ("okay, its good").** Mock-up ([editor with a workbook](https://claude.ai/artifact/LJfE8Gu5mBhoX6nba1Hxk9), five boards:
the editor with a workbook, Map to… and the profile following a move, the load dialog, Settings ›
Imports with the next version's differences, 390px; private until shared). Checked against the code at `fcc6c5e`:

- **A draft has no place for a profile.** `model_drafts` holds `model_json` only; consumer API
  definitions (A4c) live inside it because they are part of the model, which an import profile is
  not. `import_profiles` rows are instance-wide and checked against the **active** release (0.9
  D65), so they cannot hold a profile naming a draft's new types (D12).
- **The undo machinery is reusable as it is.** Every kind changes the model through
  `authoring/document.Document`, which logs the reversal of each primitive change by path, not
  position; `restoreElements` replays such a log. A second `Document` over the draft's profile,
  writing into the same log with the document named on each entry, gives the profile side (D13) the
  same exact undo with no second history.
- **A draft owns one current source file** (A3, D5: a newer upload supersedes the older), so one
  profile per draft is enough for A5. A7 (two files) would change D5 anyway, and is below the cut
  line (D2).
- **The 0.9 profile cannot express three of the eight named mapping kinds as they are worded.**
  There is no general unpivot (only `relationFlags` and per-column `relatedRecord`), no way to create
  a list value a cell names (a `relation` or `parent` binding refuses `REFERENCE_NOT_FOUND`), and no
  binding chooses which type a sheet loads: a **source** does, and no named kind adds one.
- **Records have no retired state.** A-D7's "retire" has nothing to stand on: retirement exists for
  workspaces only. Deleting a record in a change set exists (0.8).
- **An import needs an existing change set** (`changeSetId` and `expectedChangeSetVersion`); there
  is no "into a new change set" option. `sourceFileId` on `POST /imports` names any stored file.
- **No import profile screen exists**; the browser client has the routes only. J35 needs one place
  in the UI to upload the next version.
- **The built editor is not A0's four columns.** A4b moved the preview into the centre (the user,
  2026-10-12); the editor is a resizable model pane (with Model and Consumer APIs tabs), the centre
  (the selected element, or the preview) and a bottom drawer (Issues, History). The A5 layout has to
  join that, not the A0 board.

**What is built**, in three slices (D74):

**A5a: the draft's profile, through the API.**

1. **Migration** `20261013_01_draft_profiles`: `model_drafts.profile_json` (JSON, nullable). No
   other table.
2. **Engine `engine/model/authoring/`:** `Document` entries name their document (`model`,
   `profile`); `Context` holds both; `apply_changes` replays each into its own. New
   `mapping.py` with the source and mapping kinds (D76, D77), and the profile side of every model
   kind that renames, moves or removes something a profile names (D78), written once in
   `profile_side.py` and called by those kinds, never by the client. The draft's profile is checked
   by `check_profile` against the draft's compiled model; its problems join the step's
   `diagnostics` as warnings at `/profile/…` pointers (they do not block installation of the model).
3. **The dry run follows every step** (D79): after a step that changes the model or the profile of
   a draft with a profiled source file and a profile, the operation request queues the dry run of
   that draft version and answers it as `checking`; A3's cancellation of a superseded run applies.
4. **Installation saves the profile** (D80): installing a draft with a profile writes or updates
   the instance profile of the same key, checked against the release just installed.
5. **Routes:** `GET /model-drafts/{id}/profile` (the profile, its `valid` and `problems` against the
   draft's model, and its source file), replacing the designed `GET …/profiles` (D75). The kinds go
   through the existing `POST …/operations`, undo and redo. OpenAPI lock re-baselined.
6. **Import binding:** `missing: "create"` on `relation` and `parent` bindings (D77): a cell naming
   no record of the far type creates one by name, once per distinct value per load, before the
   relationships; reported per row as a related record created.

**A5b: the editor with a workbook.**

7. **Start points:** "New from a workbook" on Settings › Model (a new empty draft, then the
   upload) and "Add a workbook" in an open draft's ⋯ menu; both upload through `POST /source-files`
   and show the profiling job's progress.
8. **The source pane** (D84): left of the model pane, the sheets as tabs, each column with its
   status (mapped, unmapped, ignored, with issues) and statistics from A3's profile; selecting a
   column shows **its mapping in the centre** (target, reading, split, value map, sample values,
   rows refused) and highlights its target in the model pane; selecting a model element highlights
   its columns.
9. **Mapping by drag and by keyboard:** a column dragged onto a type, an attribute, or an empty
   place in the model pane; **Map to…** in the column's menu is the same as a dialog (`MoveToDialog`'s
   pattern), the keyboard and phone path. Each is one request of the kinds above.
10. **The dry run** as a third tab of the bottom drawer, **Dry run**, with A3's figures per source
    and the difference from the previous run; each figure opens its rows (`GET …/dry-run/rows`).
11. **Load** (D81): one confirmed dialog: install and activate when the model changed (A4a's
    step), a new change set named after the file, the import naming the profile and the stored file,
    the job's progress, then **Open the change set review**.

**A5c: the next version of a workbook.**

12. **Missing records** (D82): a source's `missing: "report" | "delete"` (default `report`);
    `delete` only into a change set.
13. **Differences before loading** (D83): uploading a file to a stored profile (`POST /source-files`
    with `profileKey`, A3) profiles it and runs the profile's **check job**: new, missing and
    renamed columns, new values in lookup columns, name drift (a key found with another name),
    records missing from the file, the binding check against the active release, and the dry-run
    summary; `GET /import-profiles/{key}/check` reads it.
14. **Import profiles in Settings** (D85): Settings › Imports lists the stored profiles (key, name,
    valid, the last file); a profile's page has **Upload the next version**, the differences report
    with each figure's rows, and **Load into a change set** as in 11.

**Documents:** API.md (the profile route, the kinds, `missing: "create"`, the check, `missing` per
source), API_JOURNEYS, USER_JOURNEYS (J34.2, J34.7, J34.8, J35), UI_ACCEPTANCE rows A5-1 to A5-4,
CURRENT_FUNCTIONALITY and PRODUCT, OPERATIONS (none expected), MODEL_AUTHORING (the amended layout,
unpivot, A-D7's retire), CHANGELOG, PROJECT_STATUS, TODO.

**Decisions** (D74 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D74 | One package or slices | **Three slices, delivered in order, each with its own record and checks: A5a (API: the draft's profile, the kinds, the profile side, the dry run after each step, the profile saved at installation), A5b (the editor with a workbook and the load), A5c (the next version: differences and missing records, API and Settings screen).** A5 as scoped is larger than A4a and A4b together; AGENTS.md asks for slices when a package is too large for one ownership unit. A5a is backend only and can be checked through the API before any screen depends on it, as A3 was. The exit gate stays A5's: W1 and W1′ load without JSON or code after A5c |
| D75 | Where the draft's profile lives | **One profile per draft in `model_drafts.profile_json`, changed only by operations, in the same history step and undo as the model.** A separate table would need a second version and a second history; inside `model_json` it would be released as part of the model. The route becomes `GET …/profile` (singular), since a draft owns one current file (D5). If A7 stays in 0.10, it widens this to one profile per file |
| D76 | The source and mapping kinds | **Eleven kinds, all additive, each changing the profile only:** `addSource` (sheet, block, header row, `objectType`, `applicationKey`, key) · `setSource` (any of those) · `removeSource` · `mapColumn` (column to `field`, attribute, parent, relation, related record; one per column, replacing what was there) · `setColumnReading` (`text`, `lookup`, `relation`, `relationFlag` with its target) · `splitColumn` (`split` delimiter, or none) · `ignoreColumn` · `ignoreSheet` (its sources removed, the sheet marked ignored) · `setValueMap` (a named map's entries; `null` removes the map) · `addValuesToList` (D77) · `setMissing` (A5c, D82). **`unpivotColumns` is not a kind:** the binding's two column-per-member shapes (flags to one relation, a column per related record such as a language) are `setColumnReading` and `mapColumn`; a general unpivot is ETL (principle 9). `addSource` is new: the type a sheet loads is a source's, and a column dropped onto a type with no source on that sheet starts one |
| D77 | "Add values found to a list" | **A binding option, `missing: "create"`, on `relation` and `parent` bindings: a cell naming no record creates a record of the far type with that name.** The values become records of the list type in the same load, reviewed in the change set; nothing is written into the model, which never holds runtime data (MODEL_AUTHORING, lists as object types). It extends the 0.9 import contract for any client, as the API-first rule asks. The alternative, a second source on the same sheet loading the list type, needs a unique key the list type does not have, and would load every row of the sheet once per list |
| D78 | The profile side of model kinds (D13) | **`setKey` rewrites the key everywhere in the profile. A removal (`removeObjectType`, `detachAttribute`, `removeAttributeType`, `removeRelationType`, `disallowRelation`, `removeApplication`) turns each binding naming it into an unmapped column, and a source of a removed type into an unmapped sheet, with a diagnostic `COLUMN_UNMAPPED` naming the step. `moveAttribute` moves the column to a source of the target type on the same sheet and block, else unmaps it with the diagnostic. `splitObjectType` starts a source of the new type on the same sheet with the moved columns, its key the first moved unique attribute, else none and a `SOURCE_WITHOUT_KEY` diagnostic, and joins the two by the split's relation. `mergeObjectTypes` re-points the merged type's sources and merges value maps of the same name. `convertAttributeToListType` turns the column into a lookup of the list by name with `missing: "create"`.** Each change is in the step's inverse, so undo puts the profile back exactly. A profile that no longer fits is never refused: the step answers with the diagnostics, as an invalid model is (A2) |
| D79 | When the dry run runs | **Restated after the user's question:** after a step (a request, an undo, a redo or a `PATCH`) on a draft holding a profiled file and a profile, when the step holds at least one kind that can change what the load writes: every source and mapping kind (D76); the model kinds on applications, types, attributes, attribute types, relation types, relation bindings and their rules, containment and keys (`addApplication` … `setRelationRule`, `setKey`, `replaceModel`, `restoreElements` of these). **Not** after a step of only `setLabel`, `setRelease`, the view, panel and detail page kinds, the navigation kinds or the consumer API kinds: the import binding and the write rules read none of them (checked in `imports/binding.py` and `records/rules.py`; the first wording's "labels can change a match by name" was wrong, a match reads record names, not model labels). Uploading a new file to the draft runs it after profiling. Queued by the request in the source file's workspace (the default workspace when the file names none); the answer carries `dryRun: {"state": "checking", "jobId"}`, or `null` when the step ran none. The worker is woken when a job is queued (no polling delay). **Time:** the step answers at once; the summary follows. W1 at 10,000 rows: about 7 s per dry run (A3a, measured), 5.8 s of it holding the workspace's write lock. W1 at 200 rows: not measured, estimated well under 1 s. A newer step cancels a running dry run, so quick steps do not queue up |
| D80 | When the draft's profile becomes an instance profile (D12) | **At installation, the existing route: the profile is written to `import_profiles` under its key (created, or updated at its version), checked against the release just installed; the draft's source file stays the draft's.** Activation is a release's route and does not know a draft. Until the release is activated, the stored profile reads `valid: false` against the active release with its problems, which is true. The load (D81) names the draft's file by `sourceFileId` |
| D81 | Load from the editor | **Three existing routes in one confirmed dialog, no combined route: install and activate when the model changed, create a change set named after the file, `POST /imports` with the profile, the stored file, `onExisting: "overwrite"`, `policy: "independent"`; on completion, Open the change set review.** An integrator has each step already (as A-D8 decided for install and activate); a combined route would be a second way to do each. Live loads stay possible through the API (principle 6), not in this dialog |
| D82 | Records missing from a new version (A-D7) | **A source option `missing: "report"` (default) or `"delete"`; delete only into a change set (`422 MISSING_DELETE_NEEDS_CHANGE_SET` live); no "retire".** Records have no retired state, and adding one changes every read and the model; it is not 0.10's. A missing record is one of the source's type in the context, with the source's key filled, that no row names; counted by a set statement (principle 6). Reported in the check (D83) and the dry run either way |
| D83 | How the next version's differences are worked out | **A job of kind `profileCheck` on a profile's new file, after its profiling: columns by header (new, missing; renamed when a missing and a new column stand at the same position and share at least half their distinct values), new values per lookup column, name drift per key, missing records (D82), the profile's problems against the active release (J35.3) and the dry run's summary; read by `GET /import-profiles/{key}/check`.** One job so the report is one consistent read; each list paged by its rows, as the dry run's. The renamed-column rule is fixed and visible so a test can name it, as D70's placeholders were |
| D84 | The editor's layout with a workbook | **A source pane left of the model pane, the selected column's mapping in the centre, the dry run as a drawer tab** (the mock-up's board 1). The built editor already puts the selected element in the centre and keeps a drawer under it; a column is one more kind of selected element. A0's separate mapping column (four columns at 1440px, board 3 of the A0 mock-up) is the alternative; with the centre it would leave each column too narrow. At 390px the panes are tabs: Source, Model, the selection, Issues |
| D85 | Where the next version is uploaded | **Settings › Imports, a list of stored profiles and a profile's page.** The 0.9 import dialog loads a file once; a profile is an instance's standing object and needs a home, as Settings › Model is for drafts. The editor is not that home: a recurring load does not open a draft |
| D104 | How `missing: delete` deletes a record with relationships (A5c, asked 2026-10-14) | **Accepted by the user (2026-10-14) as recommended: the record with its own relationships, no token; a record others depend on (a child it contains, a record it owns through a required relation) refused `OBJECT_HAS_DEPENDANTS` with its impact.** The 0.9 deletion rule (K2b, D120) wants `cascade` and a preview's token for any record with a relationship, and an import cannot carry tokens (its confirmation binds the file again), so `delete` deleted almost nothing. Only an import's binding gives a delete item the ref `missing!…`, and only a file's rows (`ROW_KINDS`) are run with that reading. The rejected alternatives: a full cascade without a token, or no cascade at all |
| D105 | A lookup whose value changes in the next version (A5c, asked 2026-10-14) | **Accepted by the user (2026-10-14) as recommended: the mapping kinds write `replace: true` for a relation column onto a relation the row's record holds one of (many-to-one from its side, or one-to-one), without `split`, `idColumn` or `attributes` and not saying `replace`.** A relation column adds; W1′'s changed material gave an item a second one, refused `CARDINALITY_VIOLATION`. Map to… and the inference reach the profile through those kinds, so both follow; the import contract is unchanged and profiles stored before keep refusing until re-mapped or edited. The rejected alternatives: the import replacing on its own, or leaving it |

**Journey test cases** (backend; J34 in `tests/journeys/test_j34_onboard.py`, J35 in a new
`test_j35_next_version.py`; each on two configurations, the draft built by operations on the
configuration's model, so no test names a configuration's key; W1 at 200 rows):

*A5a*

1. **J34.2 Map by hand.** Given a draft with a new type and W1 profiled, when `addSource` on `S1`
   and `mapColumn` for `K` (key), `N` (name), `P` (parent, by name), `T` (lookup, `missing:
   "create"`), `F1`/`F2` (flags) and `Fo` (split on `;`), and `ignoreColumn` for `X`, then each is one
   step, `GET …/profile` reads them, the profile is valid against the draft's model, and the dry run
   of the last step counts `S1`'s rows with no `REFERENCE_NOT_FOUND` for `T`.
2. **J34.2 Values.** After `setValueMap` sending `N/A` and `-` to empty for `T`, the next dry run's
   difference shows the related records created falling; `addValuesToList` on `Lc`'s list makes its
   missing codes created instead of refused.
3. **J34.7 The profile follows the model.** After mapping, `setKey` on the type and on an attribute,
   `moveAttribute` of `Po`'s attribute to the parent type, `splitObjectType` and
   `mergeObjectTypes`: the profile names the new keys, the moved column sits in a source of the
   target type, and after each step the profile is valid or carries exactly the diagnostic D78 names;
   one undo of each puts the profile back as it was (compared whole).
4. **J34.7 Removal.** `detachAttribute` of a mapped attribute leaves its column unmapped with
   `COLUMN_UNMAPPED`; undo maps it again.
5. **J34.3 After each step.** A step on a draft with a profiled file answers `dryRun.state:
   checking`; the next `GET …/dry-run` is of that draft version.
6. **D80 at installation.** Installing the draft writes an instance profile of its key, checked
   against the new release; after activation, `POST /imports` naming it and the draft's
   `sourceFileId` into a change set loads the rows the dry run counted.
7. **Refusals:** a mapping kind naming a column the sheet lacks or a sheet the file lacks is
   `INVALID_OPERATION` (`unknownElement`); `addSource` on a draft without a source file likewise;
   a stale version is `VERSION_CONFLICT`.

*A5b* (backend case for the load; the rest is the browser runner)

8. **J34.8 Load into a change set:** W1 loaded by the editor's three calls, the change set lists its
   records, publishing it makes them live.

*A5c*

9. **J35.1 Differences first.** Given the profile from case 6 and W1′ uploaded to it, the check
   reports the new column `Y`, `Ln` renamed (not one missing and one new), the new `T` value, two
   missing records and the drift of changed names; nothing is written.
10. **J35.2 Missing records.** Loaded with `missing: "report"`, the two records stay; with
    `"delete"` into a change set, the change set deletes them; `"delete"` live is
    `MISSING_DELETE_NEEDS_CHANGE_SET`.
11. **J35.3 A newer release.** After a release that removes an attribute the profile maps, the check
    lists `ATTRIBUTE_NOT_BOUND` at the binding's pointer and the load is refused
    `INVALID_IMPORT_PROFILE`.
12. **J27 variant, `missing: "create"`** through `POST /imports` with an inline profile: a lookup
    naming an absent value creates it once although many rows name it.

**Browser** (`test:browser:authoring-a5`, on both designer models, naming no key): A5b: new from W1,
map it by drag and by Map to…, a value map, the dry-run drawer and a figure's rows, a rename and a
move after mapping with the source pane following, load, the change set review, publish; keyboard
alone for the mapping; 1440px and 390px; axe on the source pane, the column's mapping and the load
dialog. A5c: Settings › Imports, W1′ uploaded, the differences, load, review only the differences.

**Unit tests:** the profile side of each model kind with its inverse (generated over both models'
types and attributes, as `test_kinds` does), the mapping kinds' refusals, the renamed-column rule,
`missing: "create"` in the binding; frontend, the mapping descriptors and their history words.

**Groups:** A5a `authoring`, `jobs`, `contract`, `startup` (the migration: bootstrap, upgrade from
`20261012_01`, restart, interrupted upgrade); A5b `authoring` (case 8), Vitest related,
`test:browser:authoring-a5`, `-a4a` and `-a4b` (the shared editor); A5c `jobs`, `contract`,
`startup` if the check job needs a column, the browser runner's A5c part. Budget: the check job on
W1′ at 10,000 rows measured once.

**Composable domains (ADR-032):** inbound flow gains a draft's profile, `missing: "create"` and a
profile check; mapping coverage, identity and attribute storage are unchanged. **Audit and history:**
a `delete` of missing records goes through the change set and its audit like any delete. The
`match` declaration is untouched. No door is affected.

##### A5a record (2026-10-12)

**Delivered 2026-10-12** as planned (D75–D80), through the API; no frontend change. What is built:

- **Migration `20261013_01_draft_profiles`**: `model_drafts.profile_json`.
- **`engine/model/authoring/`**: `document.py` takes a document name and identities of its own and
  can share another document's log, each entry naming its document; `apply_changes` replays each
  entry into its document. `profile_side.py` (model facts from the draft's JSON, key renames, the
  follow code for moves, splits, list types and containment, and the generic prune into unmapped
  entries), called from `kinds.py` (`setKey`, `moveAttribute`, `splitObjectType`,
  `mergeObjectTypes`, `convertAttributeToListType`, `setContainment`, and `restoring`, which every
  compound kind ends with). `mapping.py`: the source and mapping kinds, registered with the package.
  `history.py` gives every step the draft's profile and its file's sheets and stores the profile
  with the model.
- **`engine/sources/draft_profile.py`**: the draft's file and sheets, the import profile it stands
  for, its warnings against the draft's compiled model, the read, the dry run after a step (D79) and
  the save at installation (D80).
- **Import binding**: `missing` on `parent` and `relation` bindings; `create` resolves a match that
  found nothing to a new ID and adds the record as an item before the records (phase 0), with the
  first row naming it; `CREATE_NEEDS_NAME_MATCH` in the profile check.
- **Routes**: `GET /model-drafts/{id}/profile`; `dryRun` on the answers of operations, undo and
  redo; `importProfile` on the installation's answer (`ModelInstallationResponse`). OpenAPI lock
  re-baselined by diffing the document against HEAD: `missing` on `ParentBinding` and
  `RelationBinding`, nothing else (the draft routes are model administration's).

**Where it differs from the plan and the design:**

1. **`setProfile`** is a kind beside D76's ten of A5a (the key the profile is saved under at
   installation had no other way to change); `setMissing` stays A5c's.
2. **An unmapped entry names the operation's kind, not its step** (D78 said "naming the step"): the
   step's number is written after its operations apply. The history entry says the rest.
3. **Warnings beyond the plan:** `SOURCE_WITHOUT_COLUMNS` and `SOURCE_WITHOUT_KEY` (every row would
   create a record), beside `COLUMN_UNMAPPED` and the import check's codes.
4. **No dry run while the profile would be refused**: a step answers `dryRun: null` when the draft
   does not compile or the profile has a problem an import would refuse, rather than queueing a run
   that fails; the warnings say why.
5. **Installation saves the profile only when it holds against the release**; otherwise the draft
   installs and `importProfile` is absent.
6. **`mergeObjectTypes` merges no value maps**: they are the profile's, not a type's, so there is
   nothing to merge. **`setContainment` follows too** (not in D78's list): a parent column names the
   new parent type when there is exactly one.
7. **A record a column creates follows its type's rules**: a type with required values refuses it
   (found while testing on a configuration type; the case uses a list type of the draft).
8. **Case 12 (the J27.8 variant) is delivered here**, since `missing: "create"` is A5a's code; the
   plan listed it under A5c. Its journey is J27.8 (load through a profile), not J27.9.
9. **Test order:** the journey cases were written after the code, not seen failing first (step 5).

**Smoke start:** the user's development server, running with `--reload`, restarted on the change and
migrated the development database; `GET /model-drafts/{id}/profile` answers on an existing draft
(`profile: null`). **Found, not ours:** a second uvicorn (port 61380) running since 2026-10-07,
orphaned (parent `launchd`); left running for the user to decide.

**Checks:** J34 (`test_j34_onboard.py`): the 7 new cases × 2 configurations, 14 passed (and the
module's A3 cases). Unit `tests/unit/engine/model/authoring/test_profile_side.py`: 606 generated
cases (the profile side of every renaming, moving and removing kind over both models, with its
inverse) passed; `tests/unit/engine/model/authoring` 2,554 passed before it was added;
`tests/unit/engine/imports` and `sources` 170 passed. Groups by EXECUTION_GUIDE §2, in two runs
under the ceiling: `authoring` and `contract`, 3,420 passed in 1 min 23 s (run twice: the second
only to read the slow-test list, which the rules ask not to do); `jobs` and `startup`, 509 passed
in 1 min 50 s; their serial part, 1 passed. A new `test_startup` case: upgrade from `20261012_01`
keeping a draft, an interrupted upgrade refused and recovered, two restarts, a profile written after
the upgrade, and the downgrade. `test_openapi_contract`, `test_api_journeys`, `test_boundaries`,
`test_schema_drift`: passed. `ruff check app/ tests/`: clean. **Not run:** the browser runners and
the frontend (no surface changed), the full suites (R).

##### A5b record (2026-10-12)

**Built 2026-10-12** as planned (D81, D84), in the mock-up's layout. **Not accepted as complete
(the user, 2026-10-12):** "New from a workbook" opens a draft with nothing proposed; every type,
attribute, relation and mapping is made by hand, and the automatic building of the model and its
mappings, A6, is missing entirely. At the user's instruction A5b is committed as it is, A6 comes
next, before A5c, and anything A5b still needs is addressed in A6. No backend code changed; no route, no migration. What is built:

- **Start points:** **New from a workbook** on Settings › Model (the create-draft dialog with a
  workbook field: the draft is created, the workbook uploaded with `POST /source-files`, the editor
  opened) and **Add a workbook… / Upload a newer workbook…** in the editor's ⋯ menu. The source pane
  says the workbook is being profiled and follows the profiling job's event stream.
- **The source pane** (`SourcePane`, D84) left of the model pane, resizable: the sheets as tabs with
  their rows, the types each loads and Ignore this sheet; the columns as one `role="listbox"` (Up,
  Down, Home, End, Enter; Shift+F10 opens Map to…), each with its status, letter and statistics in a
  line; the columns feeding the selected type marked, and the types the selected column feeds marked
  in the model pane. `useDraftSource` reads the draft's profile after every step, the sheets once
  profiled and a sheet's columns when opened.
- **A column in the centre** (`ColumnPanel`): Feeds, Read as, Matched by, Split on (a select, one
  `splitColumn` step), Not found (`addValuesToList`), Value map (`ValueMapDialog`, starting from the
  column's placeholders sent to empty), Key (`setSource`), the dry run's refused rows of its source,
  and Statistics (filled, value types, placeholders, delimiters, shared values). Address
  `…/editor?show=column&sheet=…&key=…`.
- **Map to…** (`MapColumnDialog`, D76): the row's type, proposed from the sheet's sources or a type
  named as the sheet; what the column holds (name, attribute, parent, related record, flag of a
  relation, nothing); the target in Move to…'s combobox over a listbox, extracted as `TargetList`
  and shared; a new attribute (name, value type proposed from the cells, unique), the rows' key,
  split and create. One request: `addAttributeType` and `attachAttribute` for a new attribute,
  `addSource` when the sheet does not load the type, then the mapping kind (`mapping.ts`,
  `mapOperations`). A column dropped on a type opens it with the target chosen (`dropChoice`: that
  type's source, the parent, a related record, or a new source's name), as A4a's drops open Move to….
- **The dry run** as the drawer's third tab (`DryRunPanel`), named with its state on the drawer's
  toggle: per source the figures and what each was, each opening its rows (`DryRunRowsDialog` over
  `JobRowsTable`, extracted from the import job's rows section and shared). A step's `dryRun` is
  followed over the job's event stream.
- **Issues** lists the draft profile's warnings beside the model's, each with **Go to column**.
- **Load into a change set…** (`LoadDialog`, D81): installation, activation when the release is not
  the active one, a change set named "Load {file} ({date})" in a chosen workspace, `POST /imports`
  with the saved profile's key, `sourceFileId`, `independent` and `overwrite`; the job followed,
  then **Open the change set review**. The release identity fields are the install dialog's,
  extracted as `ReleaseIdentityFields`.
- **Backend:** J34.8 case 8 in `test_j34_onboard.py` (the editor's three calls, the review, the
  publication).

**Where it differs from the plan and the design:**

1. **New from a workbook starts from the active release**, with an empty model a choice, not a new
   empty draft: an empty draft installed and activated would take away every other application, and
   activation refuses that when records exist. The browser runner maps onto a new application added
   to that draft.
2. **The load always installs**, also when the model is unchanged: installation finds the same
   release and saves the profile (D80), which the import names. D81's "install and activate when the
   model changed" holds for activation and for asking a new version.
3. **No sample values** in the column's centre: the file's profile serves none (A3). The statistics,
   placeholders, delimiters and shared values stand in; refused rows are per source, not per column.
4. **Map to… does not offer a related record's value** (`relatedRecord`, the mock-up's "a value of
   a related record") **or a match by an attribute**; the mapping kinds take both through the API.
   Dropping beside the tree opens Map to… with no target, not the mock-up's "New attribute… or New
   list type…" choice; a new attribute is in Map to…'s attribute list.
5. **Found and fixed:** after a step changing the selected element's key the editor kept the old key
   in the address and the centre lost the element (A4a); `followKeyChange` keeps it selected. The
   runner first found it by having to select the type again.
6. **Found by T1's runner and fixed:** the editor read the dry run of every draft, and one without
   a workbook answered `404 DRY_RUN_NOT_FOUND`, a failed request in every session; it reads the dry
   run only when the draft has a workbook.
7. **Case 8 passed when first run**: the load composes existing routes, so there was no failing state
   to see (step 5).

**Checks:** `test:browser:authoring-a5` (new), both designer models, 18 checks, about 30 s: New from
a workbook, a column mapped by keyboard alone, two by drag, a lookup and its value map, a second
source on the sheet, the dry run with 0 refused and a figure's rows, a key change and a move after
mapping, the load, the review, publication (200 items live), 390px; axe 0 violations on Map to…, a
column (1440px and 390px) and the load dialog; dialogs measured. `test:browser:authoring-a4a` 44
and `-a4b` 29 checks (the shared editor), and, for the bar's new ⋯ menu and the editor's reads,
`-a4c` 20 and `-t1` 34 (keyboard-alone walks; failed once on the 404 above, passed after the fix). Vitest `model-editor`,
`model-admin`, `jobs`, `routing`, `api`, `app`: 22 files, 330 passed (new: `mapping.test`, 8 cases;
`history.test` +1). J34 module (`test_j34_onboard.py`): 32 passed in 1 min 10 s (case 8 × 2
configurations new). `ruff check app/ tests/`, `npm run format`, `npm run lint` (0 errors; the 7
warnings are in files this package did not touch), `npm run build`: clean. **Screenshots inspected**
(1440px: Map to…, a column, the dry run, the load dialog before and after, the review; 390px: the
source tab and a column): two problems found and fixed (the choice rows' layout, the column's
letter and statistics at 390px opened from the address). **Not run:** the accessibility and visual
gates (the A5 surfaces join them at R), the full suites (R).

##### A5c record (2026-10-14)

**Delivered 2026-10-14**: built as planned (D82, D83, D85, and D104, D105 asked and accepted the
same day), in the approved board's shape (Next version, the mock-up's board 4), revised after the
user's run on the development server (below), and its screenshots approved by the user the same
day. With it A5's exit gate is met: W1 and W1′ load without JSON or code (the browser walk on both
designer models). What is built:

- **Migration `20261015_01_profile_check`**: `jobs.kind` gains `profileCheck`.
- **A source's `missing`** (`report`, `delete`; D82): `models/imports.py` (`delete` needs a keyed
  source loading its records); the binding finds the records of a keyed source's type the context
  holds with the key filled that no row names in one statement into `import_missing`, counts them in
  the binding report (`missingRecords`) and, for `delete`, adds delete items after every other item
  (ref `missing!{id}`). A record goes with its own relationships and no token; one others depend on
  is refused with its impact (D104: `Deletion.own_links`, read by the batch runner for a file's rows
  only). `POST /imports` refuses a live load that deletes `MISSING_DELETE_NEEDS_CHANGE_SET`; an
  import of a stored file keeps its `sourceFileId` in its parameters. The kind `setMissing`.
- **The check** (`engine/sources/profile_check.py`, D83): queued by the worker once a profile's file
  is profiled, and by `POST /import-profiles/{key}/check`; it compares the columns per sheet with the
  profile and the file the profile read before (its own earlier file, else its last import's stored
  file), checks the profile against the active release, binds the staged cells through the profile
  as it reads this file (renames followed, missing columns left out) live in the file's workspace,
  keeps what binding found (new values, drift, missing records; `binding._findings`) and previews
  every item as a dry run does (`dry_run.summary`, now public, counting `deleted` and
  `missingRecords`). Routes: `GET …/check`, `…/check/new-values`, `…/check/drift`,
  `…/check/missing-records` (each paged over the job's report), `…/check/rows`.
- **D105**: `mapping._replacing` writes `replace: true` for a lookup onto a relation the row's record
  holds one of (`profile_side.holds_one`); the inference's comparison reads a binding as holding
  what a proposal sets member by member (`compare._has`), so proposing again stays quiet.
- **Settings › Integration › Imports** (D85): `ImportsPage` (the list, a profile's page, following
  the profiling and the check over the job stream), `ProfileCheckReport` (Columns with Ignore and
  Accept, Values, Records with the missing records' choice, the profile against the active release;
  its lists in `CheckRowsDialog`), `ProfileLoadDialog`, `profileEdits` (the profile changes Accept,
  Ignore and the choice save with `PUT`, then the file is checked again). Shared, not copied: the
  editor's Load dialog's change set fields, steps, call and progress moved into
  `features/jobs/ChangeSetLoad.tsx` (`ChangeSetFields`, `LoadStep`, `stepState`,
  `loadIntoChangeSet`, `LoadProgress`); `AddWorkbookDialog` takes any owner.

**Where it differs from the plan and the design:**

1. **D104 and D105** were not in the plan; both found while building (the J35.2 case and the browser
   walk) and decided by the user.
2. **The check reads the file through the profile as it would read it**, renames followed and
   missing columns left out, so a renamed column still gives the differences and a dry run; the
   load itself stays refused `IMPORT_FILE_MISMATCH` until the profile is updated (Accept). D83 did
   not say how a file that no longer fits would be dry-run.
3. **New columns are reported once per sheet**, against what every source on the sheet names (the
   browser walk found a sheet of two sources listing each new column twice and the other source's
   columns as new).
4. **The lists are kept on the check's job** and paged over its report, not stored in a table; the
   job's retention removes them.
5. **Missing records are found by the source's key only**: a row refused for another reason still
   names its record; a source of the same type keyed differently counts its found records.
6. **The draft editor has no control for `missing`**: the kind is the API's, and Settings › Imports
   sets it on the stored profile.
7. **Found measuring the check of W1′ at 10,000 rows, and fixed:** the check stopped for ever at the
   binding's first lease renewal (every 10,000 rows), which waited for the check's own lock on its
   job row (the report written before binding; now committed first; regression in J35.1 with the
   renewal every 50 rows, seen failing without the fix). The missing-records statement first joined
   on an `OR` (12.7 s at 10,000 × 10,000; three anti-joins, 0.011 s), and the 0.9 binding's lookup of
   a row's record by its key attribute, and a match by attribute, compared every row with every
   record (21.9 s): they now join on `import_context_values` and `import_row_values`, the values a key
   or a match reads (a pre-existing 0.9 defect; CHANGELOG Fixed).
8. **Test order:** the J35 cases were written after the code, not seen failing first (step 5); the
   lease regression was.

**Revised after the user's run on the development server (2026-10-14):** a profile installed from
a draft and loaded from the editor read "None uploaded to the profile" and "no file uploaded yet",
which counted only files uploaded to the profile; the profile's answer now carries `lastLoad`
(`engine/imports/loads.py`: the latest import naming it, and its change set open, published (the
publication's audit entry) or discarded), shown in the list and on the page (J35.1–J35.2 cover
published, in a change set and discarded). The list and the page's bare links were the user's
second point: Imports became a catalogue (`CatalogueLayout`, as Workspaces, Model and Webhooks)
with the profile beside it, buttons for its actions and its rows; the record page's breadcrumbs
became `ui/Breadcrumbs`, used by a job's page too (Jobs and feed › the job), and `SettingsLayout`
takes a `trail`. Then, at the user's request, a settings group **Data operations** (Imports, Jobs) ahead of
Integration, and Imports renamed **Import profiles** (`/settings/import-profiles`, the old address
still opening it), since Jobs › New import is the other, one-off import; Jobs and feed renamed Jobs, its feed retention moved to Consumer APIs (Deployment keeps
both); `test:browser:settings` had not listed Imports in its keyboard order since A5c added it, and
now lists the new order. Checks after the revision: J35 8 passed; J27 with the contract checks 67 passed
(the OpenAPI lock re-baselined for `lastLoad`, diffed against `96b6f4e`); Vitest `settings`,
`jobs`, `objects`, `ui`, `app` 435 passed; `test:browser:authoring-a5` 24 checks (it now opens the
profile from the catalogue and reads its last load, with axe on the profile's page) and
`test:browser:j1u` 12 checks; ruff, tsc, format and lint clean.

**Budget** (measured once, generated-a, this laptop): W1′ at 10,000 rows uploaded to a profile whose
workspace holds W1's 10,000 items: profiling 6.1 s, then the check job 10.1 s (prepare 0.1 s,
binding 2.4 s, the preview of 40,107 items 6.1 s, recording 1.5 s). Two earlier attempts were
stopped at a 4-minute cap (the lock above).

**Checks:** J35 (`test_j35_next_version.py`, new): 4 cases × 2 configurations, 8 passed (J35.1 with
the lease regression, J35.2 with the re-check, `delete` in a change set and the live refusal, the
`setMissing` case, J35.3). J34 with J35: 66 passed in 2 min 37 s (the two dry-run cases updated for
`deleted` and proposing again for D105). `jobs` without J34 and J35: 397 passed in 1 min 18 s, and
its serial part; before the binding's last change the whole `jobs` group, 449 in 2 min 51 s.
`records` (the deletion path): 424 passed in 2 min 6 s. Unit: authoring (with `holds_one` over both
models), `tests/unit/engine/sources` (with `test_profile_check.py`). `test_startup`'s new case
(upgrade from `20261014_01` keeping a profile, an interrupted upgrade refused naming `ck_job_kind`
and recovered, two restarts, a check job after the upgrade, the downgrade) and A6's; `test_schema_
drift`, `test_boundaries`, `test_api_journeys`, `test_openapi_contract` (re-baselined by diffing the
document against HEAD: the check's reads and schemas, `Source.missing`, `missingRecords`, the job
kind; nothing else). `ruff check app/ tests/`: clean. Vitest `settings`, `jobs`, `model-editor`,
`routing`, `app`: 22 files, 322 of 323 passed; the one failure was the Settings navigation's list,
which the new Imports page changes (updated, its file rerun: 12 passed). New: `profileEdits.test`;
`mapping.test` +1 (`setMissing`'s words); the import dialog's fixture made as the server answers. `npm run format`, `npm run lint` (0 errors;
the 7 warnings in files this package did not touch), `npm run build`: clean.
`test:browser:authoring-a5` on both designer models, 24 checks (12 new for A5c), run after the last
change; `-a6` 18 checks (D105 and the proposal comparison); `test:browser:integration` (the
Integration navigation). **Screenshots inspected** (1440px: the profiles list, a profile's check,
the review after loading W1′; 390px: the check): three problems found and fixed (the section's lines
stretched to the row's height, the notice breaking after the file name, the missing records' select
unstyled). **Not run:** `-a4a`, `-a4b`, `-a4c`, `-t1` (the shared editor changed only in the Load
dialog's parts and the workbook dialog's owner, both in the A5 walk), the accessibility and visual
gates (A5-5 joins them at R), the full suites (R).

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

##### A6 plan (2026-10-12)

**Planned 2026-10-12, revised the same day after the user's review; D86–D98, the test cases and
the revised mock-up accepted by the user the same day ("go ahead").** The first version put the proposals in a
list of their own with Accept and Reject; the user found it "terminal and very binary", a
questionnaire beside the editor rather than the editor. **Revised (approach and D92's Propose again
rule accepted by the user, 2026-10-12, "okay"):** the inference writes its first draft into the
draft as ordinary steps, and everything after that is the editing A4a–A5b built, as
MODEL_AUTHORING's principle 2 says ("an editor, not a wizard"). Mock-up ([editor with
proposals](https://claude.ai/artifact/3gB1sWQGg9QLNGLwC2NJV4), four boards: the editor filled by
the inference with a proposed type selected, the start dialog, proposing again after a newer
workbook, 390px; private until shared). Checked against the code at `7ac83de`:

- **The profile has per-column statistics only.** A3 stores filled, distinct, value types,
  candidate key, delimiters, placeholders and the five best overlaps per column
  (`engine/sources/profiling.py`). Four patterns need facts between columns that it does not hold:
  a code and name that vary together, columns constant per value of another (the repeated
  parent's order and ID), a key repeated once per language, and the parts of a split cell found as
  whole values elsewhere. The staged cells (`source_file_cells`) are still there (D66), so these
  are set statements over them, not a second read of the file.
- **History already knows a proposal step.** `history.py` lists `proposal` among undoable origins
  and stores each step's `created`, `rekeyed` and `named` elements, so an applied proposal is an
  ordinary step, and whose an element is (the engine's or the administrator's, D92) can be read
  from history. **One gap:** the mapping kinds name sources and model elements in their effects,
  not columns (`mapping.py`, `_named`), so a column's owner needs a `column:` entry added there.
- **The import contract carries most proposals as they are.** Rows of one source sharing a key with
  the same values load as one record (0.9 D69), so a second source on the same sheet can load a
  list or a parent by its code or ID; rows that disagree are refused `DUPLICATE_KEY_IN_FILE`, which
  is why name drift needs its value map before the load. **One gap:** a related record's `parent`
  (`RelatedParent`) and a flag set (`relationFlags`) have no `missing`, so in a new application a
  translation proposal would refuse every row until its language records exist, and a flag
  proposal every row with a flag set until its records exist (D93).
- **What A5b left open** (its record): nothing is proposed; Map to… cannot choose a related record's
  value or a match by an attribute, which proposals produce (translations, a list matched by its
  code); the column's centre has no sample values.

**What is built**, in two slices (D86):

**A6a: inference through the API.**

1. **Migration** `20261014_01_draft_proposals`: `model_draft_proposals` (draft, inference job,
   position, pattern, signature, the proposal as JSON with its evidence and alternatives). The
   inference is a job of kind `inference` (D88); its proposals are rows so they page, and the
   centre's Proposed because reads an element's proposal from them. Whether a proposal is applied,
   and whether it was rejected (D92), is read from history, not stored.
2. **Profile:** each column's statistics gain `values`, its ten most frequent values with their
   counts (closing A5b's missing samples; the evidence quotes them).
3. **Engine `engine/sources/inference/`:** the cross-column facts as set statements over the staged
   cells (`facts.py`); one rule per pattern over the statistics and facts (`patterns.py`, D90), each
   giving a proposal with its evidence, operations and alternatives; matching against the draft's
   model in extend mode (`matching.py`, D91); attribute types shared across the workbook's sheets
   (D98); requirements between proposals; the comparison with
   what the draft already holds, by owner (D92); the assistant's interface (`assistant.py`, D95).
   History: the `column:` effect, and each element's owner read from the steps naming it.
4. **Routes** (D87): `POST /model-drafts/{id}/inference`, `GET …/inference` (with its
   disagreements), `GET …/inference/proposals` (paged, `sheet`, `column`: evidence, operations,
   alternatives, `applied`), `POST …/inference/application` (D89). The disagreements also join the
   draft's diagnostics as `INFERENCE_DISAGREES` warnings. OpenAPI lock re-baselined.
5. **Import binding:** `missing: "create"` on a related record's `parent` and on a flag set, both
   matched by name (D93).

**A6b: the editor filled by the inference** (D94). No new view: the existing panes and centre.

6. **New from a workbook** asks what to propose: a new application (its name, from the file's),
   additions to the active model, or nothing (A5b's mapping by hand); after profiling it runs the
   inference and applies it, and the editor opens on the model and mapping it wrote, with the dry
   run. ⋯ › **Propose again…** does the same on an open draft (after a newer workbook, say).
7. **Proposed, until edited:** a type, attribute, relation or list type, and a column, that is
   still the engine's (D92) carries a **Proposed** mark in the model pane and the source pane, as
   New does. Its centre (A4a's element panel, A5b's column) gains **Proposed because**: what the
   rule found, in one sentence, with its evidence (statistics and values), and its alternatives as
   actions ("Read as a text attribute instead"), each one step through `POST …/operations`.
   Editing the element by any operation makes it the administrator's and the mark goes.
8. **Disagreements** of Propose again are warnings in Issues, each with **Go to column**; History
   names each applied proposal ("Proposed: Category as the parent of Item").
9. **A5b's open points:** Map to… offers a value of a related record and a match by an attribute;
   the column's centre shows its most frequent values.

**Documents:** API.md (the inference routes replacing the designed ones, `values`, `missing` on a
related parent and a flag set), API_JOURNEYS, USER_JOURNEYS (J34.4–J34.6), MODEL_AUTHORING (the pattern rules as
built, pinned decisions, the assistant), UI_ACCEPTANCE rows A6-1 and A6-2, OPERATIONS
(`INFERENCE_ASSISTANT`), CURRENT_FUNCTIONALITY and PRODUCT, CHANGELOG, PROJECT_STATUS, TODO.

**What W1 gives** (new application, the proposals in the order they are applied; the test
names structures, never headers):

| # | Pattern | Columns | Proposal | Alternatives |
| --- | --- | --- | --- | --- |
| 1 | — | — | A new application named after the file | — |
| 2 | Key column | `S1`: `K`, `N` | Type from the sheet's name (singular), `K` its unique key attribute, `N` its name; the source | — |
| 3 | Repeated parent | `P`, `Po`, `Pi` | Parent type from `P`'s header holding `Po` (integer) and `Pi` (unique text); containment; a second source on `S1` keyed by `Pi`; `P` the item's parent by name | A list related to the type (no containment) |
| 4 | Text lookup | `T` | List type from the header, a relation from the row's type, `T` read by name with values created by the load | A text attribute |
| 5 | Placeholder values | `T` | Value map: `N/A`, `-` to empty, with their counts | — |
| 6 | Code and name pair | `Lc`, `Ln` | List type with a unique code; a third source on `S1` keyed by `Lc`, `Ln` its name; `Lc` related by the code | `Ln` a text attribute, `Lc` a text attribute |
| 7 | Name drift | `Lc`, `Ln` | Value map sending each code's less frequent name to its most frequent one (2 codes) | A warning only |
| 8 | Flag columns, with a multi-valued cell beside them | `F1`, `F2`, `Fo` | One list, one relation: `F1`, `F2` its flags (each a record named by its header), `Fo` split on `;` with values created | A yes/no attribute per flag column, `Fo` its own list |
| 9 | External IDs | `X` | A unique text attribute | Ignore the column |
| 10 | Reference to another sheet; translations, one row per language | `S2`: `K` → `S1`'s `K`, `Lang`, `N` | A language list and a translation type under it, a relation from the row's type; `S2` a source of existing records keyed by `K`, `N` the translation's name under the language its row names | Ignore the sheet |
| 11 | Navigation group | — | The list types the sheet's proposals add, as one collapsed group named after the sheet | — |

Level columns and translations by column are not in W1 or W2; their rules are unit tested on
generated tables (D90).

**Decisions** (D86 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D86 | One package or slices | **Two slices, each with its own record and checks: A6a (inference through the API: the rules, the job, the proposals and their application, extend mode, pinned decisions, the assistant's interface, `missing` on a related parent and a flag set) and A6b (the editor: the start, the Proposed marks and Proposed because, A5b's open points).** As D74 did for A5: the rules have the most uncertainty and are checked on W1 through the API before a screen depends on them. A6's exit stays one: W1 to a published change set from the inference's first draft, changed in the editor, screenshots approved |
| D87 | The routes | **Singular, the latest inference of the draft, as the dry run's routes are: `POST /model-drafts/{id}/inference` (`mode`, `applicationKey` or `applicationName`, `workspaceKey`?) answering `202` with `{state: "checking", jobId}`; `GET …/inference` (state, mode, draft version, counts, disagreements); `GET …/inference/proposals` (paged); `POST …/inference/application` (D89).** A0 designed `POST …/inferences` and `GET …/inferences/{id}/proposals`. A draft has one current file (D5) and only its latest inference matters, as only its latest dry run does; an id in every path would make a client remember which is current. Reading the proposals before applying them stays possible for an integrator who wants to look first; the editor applies at once |
| D88 | Synchronous or a job | **A job of kind `inference`, as profiling and the dry run are; the editor follows it over the job's event stream as A5b does.** Its time is unmeasured: the rules are a few grouped statements per column pair of a sheet, and 40 sheets or 10,000 rows are possible. W1 at 10,000 rows is measured once in A6a. A request held open for a whole-file statement is what the job model exists to avoid |
| D89 | How proposals reach the draft | **`POST …/inference/application` with `expectedVersion` and optionally `proposals` (ids; by default every proposal not yet applied): all or none, each proposal its own step of origin `proposal` (its id and pattern), in the order of their requirements, one dry run after the last. The editor calls it as soon as the inference completes. An alternative is not a second application: it is a batch of ordinary operations (from the proposal as applied to the alternative) the client sends to `POST …/operations`, which makes the element the administrator's.** The first version had an acceptance route and Accept/Reject per proposal; the user rejected that as a questionnaire beside the editor. Choosing "propose" in New from a workbook (or Propose again) is the request, so the J34.4 rule "nothing applied unasked" holds. **Requirements:** a proposal naming an element another creates requires it; applying one without it is refused `422 PROPOSAL_REQUIREMENT_MISSING` with the requirement's id. A proposal step is undone like any step (D8: dependants together) |
| D90 | The rules | **Each pattern a fixed rule over the profile's statistics and the cross-column facts, with fixed thresholds stated in MODEL_AUTHORING so a test names its expectation (as D70 did): key column — a candidate key, text without spaces or integer, not a GUID, the leftmost such; name — the first other text column filled on ≥ 95% of rows with ≥ 50% distinct; code and name pair — a code-like column and a text column with at most 1.5 names per code; repeated parent — a column with distinct ≤ rows / 3 grouping other columns constant within ≥ 98% of its groups; level columns — headers differing only by a number, or a column whose values are ≥ 90% in the key column; text lookup — text, distinct ≤ 50 and ≤ 20% of filled cells; reference to another sheet — ≥ 90% of a column's distinct values in another sheet's key column; multi-valued cell — a delimiter in ≥ 10% of cells whose parts are ≥ 80% values found whole in the column; flag columns — every filled cell in one of `y/n`, `yes/no`, `x`/empty, `true/false`, `1/0`, adjacent columns forming one set, joined by an adjacent multi-valued column; translations by row — a column of ≥ 2 language codes or names repeating a key referenced to another sheet once per value; by column — headers differing only by a language suffix; external IDs — every cell a GUID, or a unique code under a header naming an ID beside a key; placeholders — A3's (D70); name drift — a code with two or more names; navigation group — two or more list types proposed from one sheet.** Deterministic and visible. Scored similarity was considered and left out: it gives an answer nobody can predict or name in a test, and the design says inference is deterministic first. The language codes are ISO 639-1 and the names in English, the only words in the rules beyond the placeholder list |
| D91 | Extend mode | **The draft's model is read for matches before anything new is proposed, in this order: a sheet becomes a source of an existing type when ≥ 50% of its key column's distinct values are that type's unique attribute values or names in the workspace (A3's overlaps, D69), or when the sheet's name equals the type's name or plural; a column maps to an attribute the type binds when its header equals that attribute's name and ≥ 95% of its cells convert to its value type; a global attribute type of that name and fitting type is attached rather than a new one added; a lookup column relates to an existing type when ≥ 50% of its distinct values are that type's record names, through a relation type already allowed between them when there is one. Names compare after folding case, accents and punctuation and dropping a final plural `s`.** New types go into `applicationKey`, by default the application holding most matched types. "Not duplicated" is then checkable: an attribute matched is never added again. Released elements are matched, never changed (a change would be a migration) |
| D92 | Pinned decisions | **An element, binding, ignored column or sheet is the engine's while every step naming it since it was proposed is of origin `proposal`; a step of any other origin naming it (a request, a patch) makes it the administrator's, for good. A proposal step undone, or a proposed element the administrator removed, is a rejection: the same proposal (pattern and columns, its signature) is not applied again. Propose again: for what nothing decides yet, the new proposals are applied as steps; for what is still the engine's and the new rule's result differs (a renamed column in a newer workbook), a step of origin `proposal` takes it from the earlier proposal to the new one, undone like any step; for what is the administrator's and the rule reads otherwise, a disagreement (current binding, what the rule found, the step that decided it) is reported and nothing changes.** Accepted by the user (2026-10-12) with the revised approach: otherwise the engine's earlier guesses would freeze just by sitting in the draft. The first version pinned everything the draft held; with proposals applied directly, that would have left Propose again unable to correct its own guesses. "Mine for good" keeps the design's rule that inference never overrides a decision. The column's owner needs the `column:` effect (above) |
| D93 | Records a new application's proposals name before they exist | **`missing: "create"` on a related record's `parent` and on a flag set, both matched by name: a language a row names, or the record a set flag stands for, is created once per load when it does not exist, as D77 does for a lookup.** Without it a translation or flag proposal for a new application loads nothing (or refuses every flagged row) until someone adds the languages and flag records by hand, which is what A6 removes. A separate source loading them would need a unique key the list does not have, and a flag's record is named by a header, which no row holds. It extends the import contract for any client, as D77 did |
| D94 | The proposals in the editor | **No proposals view: the inference fills the model and source panes; what is still the engine's carries a Proposed mark; the selected element's or column's centre shows Proposed because (the rule's finding, its evidence, its alternatives as actions); disagreements are Issues warnings; History names each proposal.** The user's review (2026-10-12): a card list with Accept and Reject is binary and terminal, and nothing in it could be changed until accepted. In the editor every proposal is changeable by the operations that already exist (rename, Move to…, Map to…, remove, undo), the profile follows (D78), and the dry run shows the effect. The cost is that a first look at "what the engine guessed" is spread over the panes rather than in one list; the Proposed marks and History are that overview |
| D95 | The assistant (A-D5) | **An interface only: `INFERENCE_ASSISTANT`, empty by default (off), names a Python factory returning an object with `suggest(request)`; the request carries each sheet's headers and at most `INFERENCE_ASSISTANT_ROWS` (20) rows; it answers label suggestions for elements other proposals add, served as proposals of pattern `assistant` (`setLabel` operations requiring the proposal they rename), marked as the assistant's. No provider is bundled; a failing assistant is reported in the inference's `warnings` and the deterministic proposals stand.** Pluggable by setting, as the design asks, with nothing sent anywhere unless an operator configures it. Tested with a fake in a unit test |
| D96 | External IDs | **A unique text attribute named by the header, with Ignore as the alternative; in extend mode, a related record of an existing type when ≥ 50% of the values are already that type's unique attribute values.** The design says "system mappings", but a system mapping is a related-record structure (a mapped type under a system's record) that a new application does not have, and building one for each ID column would add two types per column. A plain unique attribute keeps the ID searchable and keyed, and the extend case uses a structure that is there |
| D98 | Attribute types shared within a workbook | **Columns of different sheets or sources with the same header (folded as D91 folds names) and the same proposed value type become one global attribute type, attached to each type that has them, proposed by the first proposal that needs it and required by the others. A unique column shares only with unique columns and only when no value appears in both (A3's column overlaps): uniqueness is per workspace and attribute type, across every type (`unique_attribute_values`), so two lists sharing a unique "Code" could not hold the same code. Otherwise each gets its own attribute type, keyed `-2`, `-3` (A-D6).** Added at the user's request (2026-10-12) after comparing with a model Claude built from a workbook, where a "code" attribute was reused across types. Attribute types are global and reusable by design; one per column would make a workbook with ten lists hold ten "Code" attribute types. W1 has no repeated header outside its key reference, so the rule is unit tested on generated workbooks |
| D99 | Rows the proposed model refuses (found on the user's workbooks, 2026-10-14) | **A row type gets one parent: the first repeated column; a further one is a list it refers to (each set the parent anew, the last winning, and the earlier parent columns were looked up as the last parent's type). A parent is optional (`setContainment`'s `parent.optional`, `rootCreatable` beside the parent) when some rows leave the parent column empty, and always for a parent code column. A source reads no record from a row holding nothing in any column it names. The key falls back to a GUID filled and different on every row; a text key leaving the rows without a name, beside such a GUID, is the name. A reference to another sheet matches its names too.** Accepted by the user (2026-10-14, "Yes" to fixing the defects). Three workbooks' proposed models refused 20 of 30, 1,676 of 2,694 and 153 of 3,727 of their own rows; 10 of a workbook's 12 lists (an ID and a name) were not proposed |
| D100 | Translations found by their values | **Columns about as many values as a base column whose values repeat, one value per base value and back (80% each), mostly different, are its translations, whatever their headers say; the k-th translation of every base is in the k-th language (a header's language word, else "Language k"). A base that is no type's name leaves them attributes.** Accepted by the user (2026-10-14). A workbook repeated its columns per language with headers in each language (one header even repeated in English): no header rule finds that. All-different columns are excluded, since any two of them match one to one; translations of an attribute that is not a name (a unique "Type") stay attributes, which the translation type (a name) cannot hold |
| D101 | Flag sets | **The yes/no columns of a sheet with one vocabulary form one set, adjacent or not.** Accepted by the user (2026-10-14): twelve station columns split by translation columns became four lists |
| D102 | Sentences | **Text averaging more than 60 characters is a description: never a parent, a pair's name or a lookup; long text.** Accepted by the user (2026-10-14): a description repeated over rows was proposed as a parent type |
| D103 | Names | **Headers and sheet names written as words (underscores, joined capitals, capitals); a row type named after its key's header without a final code word, else its sheet; a navigation group after its row type.** Accepted by the user (2026-10-14): types were named "SHEET COPY (01-01-26)" and kept "Platform_Code" |
| D97 | The flag set's name | **When a multi-valued column stands next to the flag columns (W1's shape), the list is named after it, with a leading `Other`, `More` or `Additional` dropped; otherwise "{type} flags". Either is renamed in the editor.** The flag headers name members, not the set, and the set has no header of its own. The three words are English, like D90's language names |

**Journey test cases** (backend, `tests/journeys/test_j34_onboard.py`; each on two configurations,
the draft the configuration's active model, W1 at 200 rows in a new workspace; no test names a
configuration's key or a header text):

*A6a*

1. **J34.4 Proposals with their evidence.** Given W1 profiled on a draft, when the inference runs in
   new-application mode, then it lists the eleven proposals of the table above, each naming its
   pattern, its columns by structure and its evidence (for the repeated parent: `P`'s groups and
   `Po`, `Pi` constant in all of them; for the code and name pair: the two codes with two names);
   no proposal reads `N` as a key or lookup, `X` as a key, or `Po` as a parent; and until it is
   applied the draft's version and history are unchanged.
2. **J34.4 Applied, loaded and published.** When the inference is applied, then each proposal is
   one step of origin `proposal`, the draft compiles, its profile is valid, the dry run counts 200
   items with no row refused; installed and loaded into a change set and published, the workspace
   holds `n/15` parents, 200 items, 8 materials, 6 colours with one name each, the features and
   1,400 translations under 7 languages.
3. **J34.4 Changed after applying.** Sending the text lookup's alternative maps `T` to a text
   attribute and removes the material list; renaming the parent type and moving `Po`'s attribute
   keep the profile valid (D78); undoing the translations' step removes them and leaves `S2`
   unmapped; each of these makes or leaves the element the administrator's (D92).
4. **J34.4 Requirements and refusals.** Applying a proposal without the proposal it requires is
   `PROPOSAL_REQUIREMENT_MISSING`; both together are applied in order; an unknown proposal is `404
   PROPOSAL_NOT_FOUND`; a stale version `VERSION_CONFLICT`; an inference on a draft whose file is
   still profiling `409 SOURCE_FILE_PROFILE_NOT_READY`, without a file `404 SOURCE_FILE_NOT_FOUND`.
5. **J34.5 Extend the active model.** Given a draft holding a type named as `S1`, binding a unique
   attribute named as `K`'s header, an unbound global attribute type named as `X`'s, and a list
   type whose records in the workspace are named as `T`'s values, when the inference runs in extend
   mode and is applied, then the draft has a source of that type, `K` mapped to its attribute,
   `X`'s attribute type attached, and `T` related to the list type; no attribute type name appears
   twice and no new list type is named as `T`'s header.
6. **J34.6 Propose again after edits and a newer workbook.** After case 3's edits, W1′ uploaded to
   the draft and the inference run and applied again: `Y` (new) is mapped by a new proposal step;
   the colour list's name binding, still the engine's, follows `Ln`'s new header in a step of
   origin `proposal`; `T` (the administrator's) is unchanged, with one `INFERENCE_DISAGREES`
   naming the step that remapped it; the renamed parent type keeps its name; the translations
   (undone) are not applied again.
7. **J27.8 variant, `missing: "create"` on a related record's parent and a flag set:** an import
   with an inline profile whose translation column names languages that do not exist, and whose
   flag columns stand for records that do not exist, creates each language and each flag record
   once, the translations under them and the flagged relationships.

*A6b* (the browser runner)

**Browser** (`test:browser:authoring-a6`, new; on both designer models, naming no key): New from a
workbook with W1 and a new application; the editor opens filled, with Proposed marks and the dry
run at 0 refused; a proposed type's Proposed because and an alternative taken from it (keyboard
alone); a rename making it the administrator's (the mark goes); a proposal step undone; the load,
the review, publication; 1440px and 390px; axe on a proposed type's and a proposed column's
centre. `-a5` and `-a4a` (the shared panes, Map to…, the element panel).

**Unit tests:** each rule of D90 on generated tables with a control column that must not match
(property-based where the shape varies: sizes, column order, placeholders); D98 on generated
workbooks (a shared header and type shared; a different type, a unique column with values in
common, and a unique and a non-unique column each kept apart); the matching of D91
(name folding, thresholds); the comparison with the draft (D92); the assistant interface with a
fake (bounded rows, proposals only, a failure reported); the owner of an element read from
history; frontend, the Proposed because descriptors and history words.

**Groups:** A6a `authoring`, `jobs` (the inference job, `missing` on a related parent and a flag set), `contract`,
`startup` (the migration: bootstrap, upgrade from `20261013_01`, restart, interrupted upgrade); W1
at 10,000 rows measured once. A6b Vitest related, `test:browser:authoring-a6`, `-a5`.

**Composable domains (ADR-032):** inbound flow gains `missing: "create"` on a related record's
parent and a flag set; identity, attribute storage, audit and history, the `match` declaration and mapping
coverage are unchanged (proposals are model-draft data, and an applied one is an ordinary step).
No door is affected.

##### A6a record (2026-10-12)

**Delivered 2026-10-12** as planned (D86–D98), through the API; no frontend change. What is built:

- **Migration `20261014_01_draft_proposals`**: `model_draft_proposals` (the latest inference's
  proposals, deleted with the draft) and the job kind `inference`.
- **`engine/sources/inference/`**: `facts.py` (a sheet's columns and the questions the rules ask of
  the staged cells, each one set statement: values constant within another column's groups, distinct
  pairs, names per code, a split cell's parts, values two columns share), `patterns.py` (the rules of
  D90 over that interface), `build.py` (each finding a proposal: operations with keys given per
  role, alternatives, anchor and signature; extend matching, D91; shared attribute types, D98),
  `compare.py` (an element's state, snapshots, whether an operation holds, what operations create and
  name), `run.py` (the job, the reads, ownership from history, the application, the disagreements
  as warnings) and `assistant.py` (D95).
- **History**: `apply_steps` writes several steps in one request, each with an origin made once its
  operations applied; a proposal step's origin carries its anchor, keys, created elements and a
  snapshot of what it touched, which `entry_response` leaves out.
- **Routes** (`management/routers/inference.py`): `POST` and `GET /model-drafts/{id}/inference`,
  `GET …/inference/proposals` (`sheet`, `column`), `POST …/inference/application`; the step answer
  shared by the operation, undo, redo and application routes (`management/steps.py`). `GET
  …/profile` adds `INFERENCE_DISAGREES` warnings. Settings `INFERENCE_ASSISTANT` and
  `INFERENCE_ASSISTANT_ROWS`.
- **Kinds**: `unmapColumn`; `addValuesToList` on a flag set and a related record's column.
- **Import binding** (D93): `missing: "create"` on a flag set and a related record's `parent`.
- **Profiling**: a column's ten most frequent `values`; the staged cells analyzed after `COPY`.
- **OpenAPI lock** re-baselined by diffing the document against HEAD: `missing` on `FlagsBinding`
  and `RelatedParent`, the job kind `inference`, a column's `values` and `valuesListed`, nothing
  else (the inference routes are model administration's).

**Where it differs from the plan and the design:**

1. **No `workspaceKey` on `POST …/inference`**: the overlaps extend mode reads were computed when the
   file was profiled, against the file's workspace, so the inference uses that one.
2. **Status `held`** besides `open`, `applied` and `rejected`: a proposal whose columns the draft
   binds already (by hand), applied by no step. Codes beyond the plan: `INFERENCE_NOT_READY`,
   `INFERENCE_STALE` (the draft changed after the inference other than by its own proposals),
   `NOTHING_TO_APPLY`, `PROPOSAL_ALREADY_APPLIED`, `INVALID_INFERENCE_REQUEST`.
3. **D92, removal:** removing a proposed element is not a rejection; it makes what the proposal
   created the administrator's, so the proposal is not applied again either, and a column it read
   otherwise is a disagreement (case 6's `T`). Only an undone proposal step is a rejection. Taken
   literally, D92's "or a proposed element the administrator removed" would have marked `T`'s text
   lookup rejected, which case 6 (approved) reports as a disagreement.
4. **Whose an element is** is read from snapshots in the proposal steps' origins, not from a
   `column:` effect in the mapping kinds (the plan's gap): a snapshot also tells a renamed type from
   one only referenced, which effects cannot.
5. **D93 needed two more parts of the binding**, found by case 7: a `record: "existing"` row finds the
   record another source of the same file creates by its key (a translation sheet beside the sheet
   loading the records), and a related record's parent created by name gets its creation item.
6. **D96, extend:** an ID column whose values are an existing type's unique values under one parent
   record becomes a relation to that type matched by the attribute, not a related record: a related
   record only finds one the row already relates to and would create a second record holding the
   same unique value. Covered by a case added beside the approved seven (J34.5, 2 configurations).
7. **D90, as built:** the name column prefers a header holding the word "name" and needs no share of
   distinct values (W1's names repeat: 64 over 200 rows); level columns are found before a repeated
   parent (Level 1 is constant within Level 2's groups, found by a unit test); a lone yes/no column is
   a yes/no attribute with a value map, not a lookup of "Y" and "N" (found by a unit test). A
   navigation group raises the schema language to 0.10 when the draft is older (found by case 2: a
   0.9 model refuses `navigation`).
8. **Measured (D88):** the inference of W1 at 10,000 rows took 54.6 s: the staged cells had no
   planner statistics after `COPY`. Profiling now analyzes them; measured once again: 0.35 s
   (profiling 6.0 s, application of the 11 proposals 0.2 s).
9. **Test order:** the seven journey cases were written from the plan and seen failing before the
   code; the D96 case was added after its code.

**Smoke start:** the user's development server (`--reload`) restarted on the change, migrated the
development database to `20261014_01`, and answers `GET /model-drafts/{id}/inference` with `404
INFERENCE_NOT_FOUND` for an existing draft. The orphaned uvicorn on port 61380 noted in A5a is still
running, left for the user.

**Checks:** J34 (`test_j34_onboard.py`): the 8 new cases × 2 configurations passed, and the module's
earlier cases (48 in all); A3's profiling case updated for `values` (the package's own change). Unit
`tests/unit/engine/sources/inference/` (new): 22 passed (each rule on generated tables over 4 seeds,
sizes and column orders with control columns; D98's four cases; extend matching; D96's binding;
ownership and holds; the assistant with a fake). Groups by EXECUTION_GUIDE §2: `authoring or
contract`, 3,455 passed in 2 min 12 s; `jobs or startup`, 547 passed in 2 min 10 s, and its serial
part, 1 passed. **Both over the 2-minute ceiling** (TODO, to fix in the next package). A new
`test_startup` case: upgrade from `20261013_01` keeping a draft, an interrupted upgrade refused and
recovered, two restarts, an inference after the upgrade, the downgrade. `test_openapi_contract`,
`test_api_journeys`, `test_boundaries`, `test_schema_drift`, `test_foreign_keys`, `test_config`:
passed. `ruff check app/ tests/`: clean. **Not run:** the browser runners and the frontend (no
surface changed; A6b), the full suites (R). **Not covered by a test:** the assistant's row limit is
the statement's `LIMIT` in `run._assisted`, read but not exercised.

##### A6b record (2026-10-12)

**Built 2026-10-12** as planned (D94, the revised mock-up's four boards); **delivered 2026-10-14**:
the user approved its screenshots after the run on their workbooks (item 8). What is built:

- **Start points:** New from a workbook asks **Propose** (a new application with its name from the
  file's, additions to the model, nothing) and **Compare with the records of** (the workspace;
  `WorkspaceField`, extracted from Add a workbook and shared); the request waits for the workbook's
  profiling (`proposing.ts`) and the editor proposes, follows the inference's job and applies its
  open proposals as one request of one step each (`useInference`), then shows the sheet's type. ⋯ ›
  **Propose again…** (`ProposeDialog`, the same `ProposeFields`).
- **Proposed, until edited:** a **Proposed** mark (a status tone of its own, `--status-proposed-*`,
  light and dark) in place of New in the model pane and as a column's status in the source pane; a
  **Proposed because** section (`ProposedBecause`) under the header of a type, attribute type,
  relation type and column: the pattern, the summary, **Evidence** and the alternatives, each one
  step through `POST …/operations`. History reads "Proposed: …" (the origin's `summary`);
  disagreements arrive as the profile's `INFERENCE_DISAGREES` warnings at the column's binding, with
  Go to column. A notice says when the editor is proposing, and why nothing was proposed.
- **A5b's open points:** Map to… reads a related record matched by a unique attribute (**Matched by**;
  no "create" then) and **a value of a related record** (what it fills, its parent's type, the record
  named or the column naming it, created when missing); the column's centre lists its most
  frequent values.
- **Backend** (after A6a's record): a proposal step's origin carries the proposal's `summary`; an
  `INFERENCE_DISAGREES` warning points at the column's binding; `proposed` names the proposal that
  created each element; an operation holds when the binding has what it sets.

**Where it differs from the plan and the mock-up:**

1. **An installed element is no longer marked Proposed**: once in a release it reads Released and has
   no Proposed because, since its alternatives would be migrations. The profile's columns keep theirs.
2. **Taking an alternative makes what it changes the administrator's**, as D92 says: the text
   lookup's alternative attaches an attribute to the row's type, so that type reads New afterwards.
3. **The start dialog is wide** with a workbook (three choices, the name, the workspace), and the
   starting document and base release stand side by side (`dialog-pair`): A6's runner measured its
   buttons 60 px below the frame first.
4. **Found by the browser runner and fixed:** proposing again on the unchanged workbook re-applied the
   colour list's name binding, which dropped the name drift's value map, and the dry run refused 102
   rows (`holds` compared the binding whole); regression case `test_proposing_again_on_the_same_
   workbook_applies_nothing` (J34.6, 2 configurations) and a unit case. A list's Proposed because named
   the navigation group, the last proposal listing it, instead of the text lookup that made it. The
   "Nothing" choice's text held "workbook", so its label matched the Workbook field (reworded). A
   type under a parent has its row id ending in `/key` (the runner's own selector).
5. **Reported by the user on a real workbook (2026-10-14), fixed:** every sheet but one was lists side
   by side and the other had a side block, so nothing was proposed but the new application, applied
   alone: an application without types, which a model refuses. Load into a change set then blanked
   the page: an invalid draft's compilation has no `changes` (`exclude_unset`), the Load dialog read
   its length and the app has no error boundary (the Install dialog read it the same way; latent
   since A4a and A5b, the Install dialog's test fixture sent `changes: []`). The application is now
   proposed only with what goes into it and an inference finding nothing says so (regression case
   `test_a_workbook_with_nothing_to_propose_leaves_the_draft_as_it_was`, J34.4, on W3); both dialogs
   read a missing `changes` as none, and the Load dialog says nothing is mapped yet (`LoadDialog.test`,
   the Install fixture as the server answers). Each regression seen failing without its fix.
6. **Accepted by the user after the report (2026-10-14):** a sheet of several blocks is read by its
   main table when one block is clearly the table (`MAIN_COLUMNS` 3, `MAIN_SHARE` 60% of the sheet's
   cells), its source limited to that block's columns (`block`); the other blocks stay A8's and are
   named in the warnings (regression case `test_a_table_with_a_note_beside_it_is_read_by_the_table`, J34.1, and a
   unit case). The app has an error boundary (`ErrorBoundary`) round the page inside the frame and
   round the app: a part failing while rendering says what failed and offers a reload, the top bar
   stays, and a new address clears it (`ErrorBoundary.test`).
7. **Why the tests missed it, and what changed (the user, 2026-10-14):** the compile answer of an
   invalid draft sends `changes` empty instead of leaving it out, so answer, type and test fakes agree
   (regression in `test_navigation_needs_schema_0_10_and_its_own_shape`, J33.9, seen failing without
   it); every browser runner fails on an uncaught page error or a part the error boundary replaced,
   in any page it opens (`watchPageErrors`, `harness.node-test`). A new application on an empty model
   is checked: a model of the workbook alone (`test_a_new_application_on_an_empty_model_is_a_model_of_
   the_workbook_alone`, J34.4). At the user's request, the start offers **A new model**: the same
   new application in a draft that starts empty (the starting document is not asked then), since
   "A new application" adds it to the model the draft starts from, the active one by default
   (`CreateDraftDialog.test`).
8. **Run on the user's four workbooks (2026-10-14) and revised (D99–D103, accepted):** the
   proposed models refused many of their own rows (one parent per type, optional parents, rows empty
   for a source, a GUID key, references by name), and the rules missed lists of an ID and a name,
   translations by value, yes/no columns apart, descriptions and readable names. Run again on the
   files: a data dictionary 153 rows, none refused; a reference data workbook 4,117 rows, one refused
   (a category named without its ID, a gap in the file); a working copy 3,735 rows, 70 refused (two
   categories translated on a few rows as a category the English column does not have, conflicts in
   the file the dry run names); a workbook of lists side by side proposes nothing (A8). A second
   column with an earlier column's header is left out with a warning. Generated W4 holds these
   shapes (`test_a_workbook_of_real_shapes_gives_a_model_its_own_dry_run_takes_whole`, J34.4, seen
   failing without the row rule) and `test_build__shapes` the rules; the samples stay out of the
   repository. **Not covered:** translations of an attribute that is not a name (they stay
   attributes); a code and name pair whose codes hold no digit is two lists.
9. **Found, not A6's (TODO):** History words a rename with the element's current name; a type's
   attribute table wraps "Yes" beside the source pane; Export, Import and Load still list workspaces
   themselves.

**Checks:** `test:browser:authoring-a6` (new), both designer models, 18 checks, about 35 s: New from a
workbook proposing a new application (11 steps), the Proposed marks and History, the dry run with 0
refused, a proposed type's Proposed because and evidence, the text lookup's alternative by keyboard
alone, a proposed column, a rename taking the mark away, a proposal step undone, Propose again with
nothing new, 390px with the section inside the width, Map to… matched by an attribute and a value of
a related record, Load, the review, publication (200 items), installed types Released; axe 0
violations on the start dialog, a proposed type and column, Map to… and 390px; dialogs measured.
`-a5` 18 checks (it now chooses "Nothing: I will map it by hand") and `-a4a` 44 (the shared panes and
element panel). Vitest `model-editor`, `model-admin` and `ui`: 243 passed (new: `proposing.test`, 2;
`mapping.test` +2; `history.test` +1; `ModelEditor.test` mocks the inference read). Backend after
A6b's changes: the inference unit tests and J34's inference cases, 40 passed; `ruff check app/
tests/`: clean. `npm run format`, `npm run lint` (0 errors; the 7 warnings in files this package did
not touch), `npm run build`: clean. **Screenshots inspected** (1440px: the start dialog, the filled
editor, a proposed type with its evidence, a proposed column; 390px: a proposed type): five problems
found and fixed (the name field's style, the editor not showing the proposals, the placeholders'
sentence, the section past the phone's edge, a released type still Proposed). **Not run:** `-a4b`,
`-a4c` and `-t1` (the preview, the consumer APIs and the designer's walks do not reach the changed
parts), the accessibility and visual gates (A6-1 and A6-2 join them at R), the full suites (R).

### A7: Model-description sheets and matching across files

Below the cut line (D2). **Needs:** A6.

**Scope:** recognize a model-description sheet and read it before the lookup sheets it names; propose
types, attributes and relations from it; match records across workbooks by ID or code, report name
drift and missing IDs, and propose value maps.

**Tests:** W2 alone becomes an application; W2 then W1 into the same draft reconcile by ID with drift
reported; placeholders and "to be defined" lists reported, not loaded as values.

##### A7 plan (2026-10-14)

**Planned 2026-10-14; D106–D113 and the test cases accepted by the user the same day ("yes").** Started
on the user's instruction ("deliver A7"), ahead of A8, which the Next list recommended first.
Checked against the code at `1079de4`:

- **A draft holds one profile and one current file** (`draft_profile.py`, `store.py`, D5): a newer
  upload supersedes the older, and a load or dry run refuses a profile naming a sheet the file
  lacks (`binding._plans`, `SHEET_NOT_FOUND`). "W2 then W1 into the same draft", as the package's
  test line says, would leave W2's sources naming sheets W1 does not have. Where the two files meet
  is D106.
- **Nothing reads a description sheet today.** W2's sheet `D` has no candidate key without spaces,
  so the rules skip it; `Materials` and `Colours` become types of their own by the key rule
  (an ID and a name, D99), with nothing relating them to anything; `Finishes` (one row, "To be
  defined", no name) has no key and is skipped silently.
- **Extend mode matches less than cross-file matching needs** (`build.py`, D91): a sheet by its
  key's values or its name, a column by an attribute's name, a text lookup by stored names. A code
  and name pair always adds a new list, even when its codes are an existing list's unique values,
  and a flag set always adds a new list. So W1 onto W2's model would duplicate Colours and the
  flag set's list.
- **Binding already finds drift and unknown values against stored records** (`binding._findings`:
  values of a match column naming no record, a key finding a record by another name), but only the
  profile check (A5c) reads them; a draft's dry run does not.
- **A row whose key is empty is refused** `MISSING_RECORD_KEY` (`binding`), so a placeholder ID
  mapped to empty still refuses its row; nothing skips a row on purpose (D99 skips only rows empty
  in every column a source names). `PLACEHOLDER_VALUES` (profiling, D70) are `n/a`, `na`, `-`,
  `--`, `?`, `tbd`, `none`; MODEL_AUTHORING's catalogue also names `TBC`.

**What is built** (one package, D113):

1. **The description rule** (`patterns.py`, D107), run before every other rule: a sheet with a
   field, a type and a target column is a model description; the sheets its targets name are read
   as its lists, never as row types.
2. **Its proposals** (`build.py`, D108): the described type, an attribute per plain field, a
   relation per lookup field to its target's list, one flag set per flag target, each target sheet
   a source of its list keyed by its ID; alternatives as A6's (a lookup read as a text attribute).
3. **Placeholders and lists to be defined** (D109): the placeholder words gain `tbc`, `to be
   defined`, `to be decided`, `to be confirmed`; a target sheet holding nothing but placeholders
   gives its list type with no source and a warning; a row whose ID is a placeholder is skipped
   (D110).
4. **Import:** a source's `rowsWithoutKey: "refuse" | "skip"` (D110), counted in the dry run and the
   outcomes as skipped.
5. **Extend mode across files** (`build.py`, D111): a sheet matched to a type by its headers, every
   proposed list matched to an existing type of its name, a column matched by codes before names, a
   header matched to a relation the type already holds.
6. **What differs between the files** (D112): codes and names a column holds that the stored list
   lacks (missing IDs) and codes whose stored name differs (drift), found by a set statement over
   the staged cells and the workspace's records, in the proposal's evidence and the inference's
   warnings, each with an alternative.
7. **Editor:** the description sheet's columns read **Describes the model** in the source pane;
   Proposed because words for the description, a list to be defined, missing IDs and drift.
   Nothing else changes on screen.

**Documents:** API.md (`rowsWithoutKey`, the inference's new patterns and warnings), MODEL_AUTHORING
(the description rule and the cross-file rules as built), USER_JOURNEYS J34.9, API_JOURNEYS,
UI_ACCEPTANCE (the A6 rows gain the A7 states), CURRENT_FUNCTIONALITY and PRODUCT, CHANGELOG,
PROJECT_STATUS, TODO. W2's generator is unchanged; its shapes already hold every case below.

**Decisions** (D106 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D106 | Where two workbooks meet | **Through the stored model and records: W2 becomes an application, installed and loaded; W1 then comes as additions to the active model (New from a workbook, extend mode, A6's D91) and is matched against W2's types and records. This changes the package's test line from "into the same draft" to "onto the model and records W2 made".** It reuses what is built: extend mode, one profile per workbook saved at installation, and each workbook's next version through its own profile (A5c). The records are what any later file meets anyway. The other way, one draft holding several workbooks with one profile each, would let both be edited before anything installs, but the source files, the draft's profile, the dry run, installation and the load would all become per workbook, with the source pane: an A5-sized change. It can be a later package if the user wants it |
| D107 | Recognising a description sheet | **A sheet with three columns, found by their values, not their headers: a field column (text, every value different), a type column (every filled value a word of the field-type vocabulary below) and a target column (at least half its filled values name another sheet of the workbook, folded as D91 folds names). Vocabulary: `lookup`, `list`, `reference`, `select` → one record of the target; `multi`, `multiple`, `multi-select`, `multi-lookup` → several; `flag`, `yes/no`, `boolean`, `checkbox` → a member of the target's flag set, a yes/no attribute without a target; `text`, `string` → text; `long text`, `description` → long text; `number`, `integer` → integer; `decimal` → decimal; `date` → date.** Read before the rules A6 built, so the sheets it names become its lists. Headers vary between organisations ("Field code", "Attribute", "Column"), so they are not read. The type words are English, as D90's language names are; a type word outside the list makes the field a text attribute, with a warning naming it |
| D108 | What a description proposes | **The described type, named after the description sheet (written as words, D103), renamed in the editor; per plain field an attribute of its type; per lookup field a relation named after the field to a list named after its target; the flag fields of one target one relation to one list named after the target, its records named by the fields (created by a later load, D93); per target with a sheet a list type keyed by that sheet's ID (D90's key rule) with its name, the sheet its source. One proposal per field and per list, each with A6's alternatives.** The description does not name the type it describes (W2's sheet is called `D`), so any name is a guess; the sheet's is the nearest. W2 alone has no rows of the described type, so the type is declared with no source until a data workbook arrives (D106) |
| D109 | Placeholders and lists to be defined | **The placeholder words gain `tbc`, `to be defined`, `to be decided` and `to be confirmed`. A target sheet whose rows hold nothing but placeholders and empty cells gives its list type, relations included, no source, and a warning "{list} is to be defined: its sheet holds no value yet". A row whose ID is a placeholder is not loaded: its value map sends the placeholder to empty and the source skips rows without a key (D110), with the count in the evidence.** The scope says "reported, not loaded as values". The list still exists so the field can relate to it once someone fills it |
| D110 | Skipping a row without a key | **A source's `rowsWithoutKey`: `refuse` (the default, today's behaviour, `MISSING_RECORD_KEY`) or `skip`: a row whose key is empty after value maps is not loaded, counted as skipped in the dry run, the preview and the outcomes, with its rows behind the figure. Only for a source with a key.** Without it W2's `?` row is refused on every dry run and every load, so the file never loads clean. It extends the import contract for any client, as D77 and D93 did. A general row filter ("skip rows where …") was considered and left out: it is the ETL the plan excludes |
| D111 | Extend mode across files | **Added to D91: (a) a sheet maps to an existing type when at least half of the type's attribute and relation names (two at least) are headers of the sheet; (b) a list any proposal would add (a lookup, a code and name pair, a flag set) under the name of an existing type, folded, is that type; (c) a column matches that type by its unique attribute when at least 50% of its distinct values are that attribute's stored values, otherwise by name when at least 50% are stored names; (d) a header named as a relation the matched type holds is read through that relation.** (a) is how W1's sheet finds W2's described type, which has no records and no name W1 knows. (b) stops the duplicates found above. (c) is the design's "IDs or codes, never names alone" where the file holds codes; a file holding only names (W1's material) is matched by name and says so in the evidence. Released elements are matched, never changed |
| D112 | What differs between the files | **Reported, not scored: missing IDs (a matched column's values that no stored record holds, with their row counts) and name drift (for a code and name pair matched to a stored list, each code whose name in the file differs from the stored name). Both in the proposal's evidence and as warnings of the inference. Missing values stay refused by the load, with "Create them on load" (`missing: "create"`) as the alternative; the pair's name column is not mapped, so the stored names stand, with "Load the names from this file" (the list's source keyed by the code, renaming the stored records in the change set) as the alternative.** The stored list is the earlier file's decision, so the later file does not overwrite it unasked; the administrator chooses which file is right. A value map for drift (A6's name drift) maps names within one file; across files the stored record is the reference, so no value map is proposed there |
| D113 | One package, and the screen | **One package. The editor shows A7 through what A6b built: the description sheet's columns read Describes the model in the source pane (a status, as Ignored is), and Proposed because gains the words for a description, a list to be defined, missing IDs and drift. No mock-up, since no surface is new; the package is complete when the user approves its screenshots (1440px and 390px: W2's draft with the description selected, a list to be defined, W1's draft with drift and missing IDs).** A6 was split because its rules were uncertain and a screen depended on them; A7's screen change is a word and four sentences. If the user wants a mock-up first, it is one board of the A6 mock-up with these states |

**Journey test cases** (backend, `tests/journeys/test_j34_onboard.py`, J34.9; each on two
configurations, W2 and W1 of one seed at 200 rows in a new workspace; no test names a
configuration's key or a header text):

1. **J34.9 A description recognised.** Given W2 profiled on a draft, when the inference runs in
   new-application mode, then one proposal of pattern `modelDescription` names `D`'s three columns
   with its evidence (five fields, four targets naming sheets of the workbook, the type words); the
   described type has two relations to lists (lookups), one to a flag set's list and one to the
   list to be defined; `Materials` and `Colours` are sources of their lists keyed by their ID; no
   proposal reads `D`, `Materials` or `Colours` as a row type; `Finishes` has no source and one
   warning says it is to be defined.
2. **J34.9 W2 loaded.** When the proposals are applied, the dry run counts no refused row and one
   skipped (the `?` row); installed, loaded into a change set and published, the materials list
   holds the IDs W2 lists without `?`, colours six records, the list to be defined none, and no
   record is named by a placeholder.
3. **J34.9 W1 onto W2's records.** Given case 2 published, when W1 is uploaded to a new draft of the
   active model and the inference runs in extend mode, then `S1` maps to the described type;
   `Lc` relates to the colours list by its ID attribute and `Ln` is not mapped, with drift listing
   each code whose name in W1 differs from W2's; `T` relates to the materials list by name, with
   the two materials W2 lacks listed as missing with their row counts; `F1` and `F2` are flags of
   the flag set's list; no list type name appears twice in the draft. Applied, the dry run refuses
   exactly the rows naming a missing material; with "Create them on load" taken, none.
4. **J34.9 Not a description.** W1 alone (new application) proposes no `modelDescription`; a
   workbook whose sheet names other sheets in one column but holds a type word outside the
   vocabulary in another proposes none either, and its sheets are read by A6's rules.
5. **J27.8 variant, `rowsWithoutKey`.** An import with an inline profile whose key column is empty
   on some rows: with `skip`, the rows with a key load and the others are counted skipped; left out,
   they are refused `MISSING_RECORD_KEY`; `skip` on a source without a key is refused
   `INVALID_IMPORT_PROFILE` at its pointer.

**Browser** (`test:browser:authoring-a7`, new; both designer models, naming no key): New from a
workbook with W2 and a new application; the description sheet's columns read Describes the model;
the list to be defined with its warning; load and publish; then W1 as additions to the active
model, a list with drift and one with missing IDs read in Proposed because, one alternative taken
by keyboard alone; 1440px and 390px.

**Unit tests:** D107 on generated sheets (each type word, the half of targets on either side, a
control sheet with a column of sheet names and no type column); D111's matching (folding, the
half of the type's fields, codes before names); the placeholder words in profiling; D110 in the
binding (skipped counted, refused by default).

**Groups:** `authoring`, `jobs` (D110 in binding and the dry run), `contract` (the profile schema
and the inference's patterns); no migration (`rowsWithoutKey` lives in the profile's JSON). Vitest
related; `test:browser:authoring-a7`, and `-a6` for the shared panes.

**Composable domains (ADR-032):** inbound flow gains `rowsWithoutKey: "skip"`; matching across
files is reported, not scored, and by IDs or codes before names, as the design says; identity,
attribute storage, audit and history, the `match` declaration and mapping coverage are unchanged.
No door is affected.

##### A7 record (2026-10-14)

**Built 2026-10-14** as planned (D106–D113); **delivered 2026-10-14**, its screenshots approved by
the user (D113). What is built:

- **The description rule** (`patterns.py`, D107): a sheet's field, type and target columns found by
  their values (`TYPE_WORDS`, `TYPE_SHARE` 80%, `TARGET_SHARE` 50%, at most `DESCRIPTION_ROWS`
  1,000 rows and `DESCRIPTION_VALUES` 200 distinct values per column read), run before every other
  rule; the description and its target sheets are not read by A6's rules. Two bounded questions
  join the facts interface (`distinct_values`, `rows_of`), with their twins in the tests' memory
  tables.
- **Its proposals** (`build.py`, D108, D109): `modelDescription` (the described type, its sheet
  ignored), `describedList` (a list from its sheet keyed by its ID, a placeholder ID through a value
  map and `rowsWithoutKey: "skip"`; a list to be defined with its sheet ignored and a warning; no
  source without a sheet), `describedField` (a relation named after the field, or an attribute of
  the field's type), `describedFlags`. After proposing, the editor selects the described type.
- **Import** (D110): a source's `rowsWithoutKey`, `skippedRows` in the binding report and the dry
  run (and its difference), `SKIP_NEEDS_KEY` in the profile check, `setSource` taking it. The
  placeholder words gain `tbc`, `to be defined`, `to be decided`, `to be confirmed`.
- **Extend mode across files** (D111, D112): `described_by`, `existing_list`, `matched_code` in the
  builder; a pair onto a stored list (`_stored_pair`: no own source, the name column unread, drift
  and missing codes, Load the names as the alternative); a lookup onto a list holding records lists
  its missing values with Create them on load; the flag set and the multi-valued list reuse an
  existing list of their name. `StoredRecords` (`run.py`) answers missing values and drift with one
  statement each over the staged cells and the records.
- **Editor** (D113): Describes the model as a column status and the sheet head's words, the pattern
  labels, the evidence words for drift, missing values and yes/no, the dry run's rows skipped figure;
  `test:browser:authoring-a7`.

**Where it differs from the plan** (each found while building; the approved cases are unchanged in
what they claim):

1. **Case 1's evidence**: the plan's "four targets naming sheets of the workbook" is wrong for W2: it
   has four targets, of which three name sheets (the flag target has none). The test asserts
   `targets` 4 and `sheets` the three.
2. **Case 3's refusals**: besides the rows naming a missing material, the dry run refuses those
   items' translation rows on `S2` (`REFERENCE_NOT_FOUND`, 7 per item), since the items do not load.
   The test asserts both, per sheet; with Create them on load none is refused.
3. **Case 3's "no list type name twice"** is checked over W2's lists and the types W1's proposals
   add: generated-a and generated-b have a type of their own named "D", the name the described type
   takes from W2's sheet (D108).
4. **Case 5's refusal** comes from the profile check (`INVALID_IMPORT_PROFILE`, `SKIP_NEEDS_KEY` at
   `/sources/0/rowsWithoutKey`), not the request schema, which would have answered
   `REQUEST_VALIDATION_ERROR`.
5. **D107's type column**: the plan asked for every value a type word and also a warning for a word
   outside the list, which cannot both hold; built as 80% of the cells, the rest text attributes with
   a warning (unit tested at four and three in five).
6. **D110's skipped rows** make no item, so the dry run counts them with no rows behind the figure.
7. **A matched lookup's missing values** are also on the column's placeholder proposal, which is the
   column's latest proposal and so the one its Proposed because shows (found by the browser runner).
8. **Missing values against a stored list** stay refused (D112) only where the list holds records; a
   flag set's list, whose records a later file's flag columns create (D108), keeps A6's creating.
9. **Defect found and fixed (A6, extend mode):** the editor uploads a workbook without a workspace,
   and its columns were compared with no records, so additions to the model never matched by value
   from the editor. A file without a workspace is compared with the default workspace's records
   (`store.compared_workspace`, used by profiling and the inference). Regression:
   `test_a_workbook_uploaded_without_a_workspace_is_compared_with_the_default_workspaces_records`
   (J34.5, seen failing without the fix).

**Checks:** journey and unit tests written first: the five cases failed before the build (the
control, case 4, passed already, as a control does). `test_j34_onboard.py` (with the A7 cases),
`test_j35_next_version.py` and `tests/unit/engine/sources/`: 198 passed (3 min 25 s, over the
2-minute ceiling: the J34 test-time item in TODO); after the last backend changes the cases on
their paths again: 165 passed (1 min 9 s). `-m contract`: 76 passed, the OpenAPI lock re-baselined
after diffing the document against the previous commit (Source's `rowsWithoutKey`, `skippedRows` on
two schemas, nothing else). `-m jobs`: 475 passed (5 min 59 s, over the ceiling and run without
being announced first). New unit tests: D107 on generated sheets (each type word, the 80% and
half thresholds, a control, a list to be defined), D111's matching; 44 inference unit tests pass.
`ruff check app/ tests/`: clean. Frontend: `vitest related` 75 passed, `proposing.test` 3,
`npm run format`, `npm run lint` (0 errors, the 7 known warnings), `npm run build`: clean.
`test:browser:authoring-a7` (new): 12 checks on both designer models, about 30 s;
`test:browser:authoring-a6`: 18 checks. **Screenshots inspected** (1440px: the description, the list
to be defined with the dry run, drift, missing values; 390px: drift): two problems found and fixed
(the description's columns read Ignored; the drift sentence's wording). **Not run:** `-a5`, `-a4*`
and `-t1` (the shared panes are covered by `-a6`), the accessibility and visual gates (A7-1 joins
them at R), the full suites (R); no migration, so no `startup`. **Not covered:** a description
whose type the model already has (extend mode over a description) is unit tested only; a
description workbook's next version through its saved profile is not exercised.

### A8: List blocks in sheets laid out for reading

Below the cut line (D2). **Needs:** A6.

**Scope:** detect header-and-values blocks, section and group headers, language column pairs, Y/N
flags and cardinality notes; propose one source per block; the administrator confirms, adjusts or
drops each block in the source pane (A-D9). Colour and formatting carry no meaning.

**Tests:** W3's blocks detected with their headers; confirmed blocks become list types in proposed
navigation groups; an adjusted block boundary; a language pair becomes translations.

##### A8 plan (2026-10-14)

**Planned 2026-10-14; D114–D121 and the test cases accepted by the user the same day** (D118 as
written, after the user asked how a translation is known, see D118). Started
on the user's instruction ("deliver build 0.1 a8", read as 0.10 A8). A7's screenshots were waiting
for approval when A8 started; A7 is committed (`c089802`). Checked against the code at `c089802`
read cell by cell; no content of it is copied here):

- **Blocks are column runs only** (`profiling._layouts`, D68): columns holding a cell, split by
  empty columns. The real workbook also **stacks lists in the same columns**, one under another,
  split by empty rows (one sheet holds eight lists in its first two columns), so today each column
  run is one "block" of several lists. W3 has blocks side by side only.
- **What sits around a list in the real workbook:** a section title above several lists (one cell,
  merged across them in Excel; merges are formatting and are not read); the list's header, sometimes
  followed by an empty row; a note row under the header (`(Multiple answer)`, `Multiple choice`,
  `Free field`) with its translation in the paired column; a translation column whose header is the
  header in another language, with no language suffix, filled on some lists and empty on others;
  Y/N columns headed by a country code beside each language column; a second header row naming a
  role; sub-lists headed by an item of the list above; prose paragraphs below a list.
- **Several lists of one shape side by side whose headers are values, not list names**: one sheet
  has twelve blocks of four columns (name, flag, translated name, flag), each headed by a category,
  together one list of items under twelve categories. W3 has nothing like it. See D120.
- **Inference reads one block per sheet** (`facts.main_block`, A6): the main table when one block
  holds at least 60% of the cells and three columns; otherwise the sheet is skipped with a warning
  "left to A8" (`workbook.partial`).
- **A source can already load a rectangle**: `headerRow` and `block` (`firstColumn`, `lastColumn`,
  `lastRow`) in the import contract, and `setSource` changes both, so adjusting a block's boundary
  needs no new operation.
- **A list of names alone cannot be keyed.** A source's key is a unique attribute or a public-ID
  column (`SourceKey`); a column has one binding (`mapColumn`); A6's lists without a sheet are
  created by a lookup's `missing: "create"`, by name. A block of one column of names has neither.
  See D117.
- **D100 does not find a list's translations**: it needs a base column whose values repeat, and a
  list's names are all different.

**What is built**, in three slices (D114):

**A8a, blocks through the API** (no screen):

1. **Blocks split by rows** (`profiling.py`, D115): on a sheet laid out for reading, a column run is
   split at empty rows into blocks, each with its header, its **note** and the **titles** above it.
   Sheets holding a main table keep today's blocks.
2. **One list per block** (`patterns.py`, `build.py`, D116): a `listBlock` proposal per block: a list
   type named after the header, a source limited to the block's rectangle, its first column the
   name, keyed by name (D117); other columns read by A6's rules within the block (a lone Y/N column a
   yes/no attribute, two or more a flag set, a code column a key); translation columns (D118); the
   note row skipped (A7's value map to empty and `rowsWithoutKey: "skip"`) and the note recorded
   (D119); a block holding nothing but a note proposes no list and says why.
3. **Navigation groups from titles** (D116): the lists under one title form a group named after it,
   the innermost title when there are two levels (groups have one level, A-D11).
4. **Import:** a source keyed by name (D117).
5. **W3 grows** (D121) to hold the real workbook's shapes.

**A8b, blocks in the editor's source pane** (a new surface, so a mock-up first, then build): a
sheet laid out for reading lists its blocks (title path, header, range, rows) with each block's
columns under it; a block's list reads Proposed like any proposal; **Adjust block…** changes its
rectangle (`setSource`), shown on a grid of the block's cells; **Don't load this block** undoes its
proposal's step, or ignores the block when it was never proposed; an unproposed block can be
proposed as a list. The A8b plan holds the mock-up and the browser cases.

**A8c, lists of one shape as one list** (D120): the alternative "one list with the headers as its
parents", which needs a source to set the same parent on every row it loads.

**Documents:** API.md (the profile's blocks, `key.field`, the new pattern and warnings),
MODEL_AUTHORING (the block rules as built), USER_JOURNEYS J34.10, API_JOURNEYS, UI_ACCEPTANCE (A8b),
CURRENT_FUNCTIONALITY and PRODUCT, CHANGELOG, PROJECT_STATUS, TODO.

**Decisions** (D114 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D114 | Slices | **A8a through the API (blocks, proposals, the name key), A8b the source pane (mock-up first, the package then complete on approved screenshots), A8c lists of one shape as one list (D120). Each delivered and recorded on its own, as A5 and A6 were.** A8b's screen depends on what A8a finds on the real workbook, as A6b's did on A6a; A8c changes the import contract and is the part most likely to be cut |
| D115 | Where blocks split | **On a sheet with no main table (A6's `main_block` finds none) and more than one column run, or one run of at most two columns: a column run is split at every empty row into parts; a part that is one text row (one cell or a row of text cells) directly above a part in the same columns, with at most one empty row between, is its header; a one-cell part whose column starts no part below it in the next rows is a title (section or group) for the blocks below it, from its column to the next title's column on its row; a part of text averaging more than 60 characters (D102) is prose, not a block. A sheet with a main table keeps today's blocks.** A table with an empty row in it must not be cut in two; the main-table rule already tells a table from a layout, so it decides here too. Real headers are sometimes followed by an empty row, so one empty row between a header and its values joins them. Bounded: the parts are found by one statement over the staged cells, never by reading the sheet in Python |
| D116 | What a block proposes | **A `listBlock` proposal per block: a list type named after the header (written as words, D103), a source on the block's rectangle with the first column as the name, the other columns read by A6's rules inside the block; per title, a navigation group of its lists named after the title, the innermost title where there are two levels. A sub-list headed by a value of the list above it is proposed as a list of its own, with that relation left to the administrator.** Colour, bold and merges are not read (A-D9). Sub-lists are rare in the files seen and their reading is a guess; the editor can relate them |
| D117 | A list of names without codes | **A source's key gains a third form, `{"field": "name"}`: a row's record is the one of the type with that name in the load's context; two rows or two records with one name are refused (`DUPLICATE_KEY_IN_FILE` as today; `AMBIGUOUS_NAME_KEY` for the records). Generic: any client may load a list by name.** The other ways are worse: a generated code attribute would need one column bound twice (a column has one binding), and leaving these lists to be created by a later lookup's `missing: "create"` leaves the block's own file unloadable. Identity door (ADR-032): not affected; public IDs and unique attributes are unchanged, and the name is a match, not an identity |
| D118 | A list's translations | **Inside a block, a text column beside the name column, filled on at least 80% of the name's rows, is a translation of the name, in the language its header names (a suffix or a language word, as today), else "Language k". A translation column holding only its header is reported in the evidence ("holds no values yet") and not bound.** D100 needs repeated values and cannot see a list. The real workbook's translation headers are the header in another language with no suffix, so "Language k" is what the administrator renames there. **How it is known** (the user's question, 2026-10-14): it is not; the rule sees a second text per item on the same rows, and only a header naming a language says which. A plain attribute by default was considered and left out by the user: the proposal stays a translation, which the editor turns into an attribute in one step |
| D119 | Notes under a header | **A row directly under the header (or under its empty row) whose cells are notes is not loaded: its value map sends the note to empty and the source skips rows without a key (A7, D110). Note words, English, folded: `multiple answer(s)`, `multiple choice`, `multi-select`, `several` → many; `single answer`, `single choice`, `one answer` → one; `free field`, `free text` → not a list: the block proposes no list and a warning names it. The note's meaning is the proposal's evidence and the list type's description ("Multiple answers").** The list itself has no cardinality: a relation does, and no type relates to these lists yet. The description keeps it in front of the administrator until a later file or the editor adds the relation |
| D120 | Lists of one shape side by side | **In A8c: three or more adjacent blocks under one title with the same columns by kind propose, as an alternative to a list each, one list with the blocks' headers as records of a parent list. To load it a source gains `parent: {"fixed": "<a value>"}`, setting the same parent on every row it loads. Leaving A8c out leaves such sheets as a list per block, which the administrator merges by hand (A2's merge), losing which block a row came from.** The real workbook's main sheet is this shape; W3's flag blocks are adjacent lists of one shape that are separate lists, so the evidence cannot decide and a list per block stays the default. A fixed value is an import feature any client may use |
| D121 | W3 grows | **W3 gains a second band of blocks under the first, separated by an empty row; a header followed by an empty row; a translation column whose header carries no language suffix, and one holding only its header; a note `Free field`; prose under a block; and (for A8c) a run of three blocks of one shape under one title whose headers are values.** The cases below must hold for what the real workbook does, and W3 is how the tests see it without client data |

**Journey test cases** (backend, `tests/journeys/test_j34_onboard.py`, J34.10; each on two
configurations, W3 of one seed in a new workspace; no test names a configuration's key or a header
text):

1. **J34.10 Blocks found.** Given W3 profiled, the sheet's profile lists every block of both bands
   with its range, header row and titles; a block below another in the same columns is a block of
   its own; title rows, note rows and prose are in no block's columns as values.
2. **J34.10 One list per block.** When the inference runs in new-application mode, there is one
   `listBlock` proposal per W3 block that is a list and none for the `Free field` block, whose
   warning names it; each list's source names its block's rectangle; the language blocks' columns
   are translations of the name, in German and French where the header says so and "Language 2"
   where it does not; the empty translation column is unbound and reported; the flags block's Y/N
   column is a yes/no attribute; the note blocks' lists carry the note in their evidence and
   description; one navigation group per innermost title, holding its lists.
3. **J34.10 Loaded.** When the proposals are applied, the dry run refuses no row and counts each
   note row skipped; installed, loaded into a change set and published, each list holds its values
   by name with their translations, and no record is named by a note, a title or a header.
4. **J34.10 An adjusted block.** When a block's source is narrowed by `setSource` to end two rows
   earlier, the dry run counts two rows fewer for it and the others are unchanged.
5. **J34.10 Not a layout.** W1 (one table) and a table with an empty row in it propose no
   `listBlock`, and their blocks are as before A8.
6. **J27 variant, a source keyed by name.** An import keyed by `{"field": "name"}` creates the
   list's records, a second run of the same file changes none, and a file naming a record by a name
   two records share is refused `AMBIGUOUS_NAME_KEY`.

**Unit tests:** D115 on generated grids (stacked and side-by-side parts, a header with an empty row,
a title over three blocks, prose, a table with an empty row unchanged); D118 and D119's words.

**Groups:** `authoring`, `jobs` (the name key in binding and the dry run), `contract` (the profile's
blocks, `SourceKey`, the pattern); no migration (the key lives in the profile's JSON). A8b: Vitest
related, `test:browser:authoring-a8` (new) and `-a6` for the shared panes.

**Real-file smoke** (before A8a is reported done): the user's reading-layout workbook profiled and
proposed once; what it finds, per sheet, in the record, by structure, not content.

**Composable domains (ADR-032):** inbound flow gains a key by name (D117) and, with A8c, a fixed
parent (D120); identity (public IDs), attribute storage, audit and history, the `match` declaration
and mapping coverage are unchanged. No door is affected.

##### A8a record (2026-10-14)

**Delivered 2026-10-14** (A8a has no screen, D114). A8b (the source pane, a mock-up first) and A8c
(D120) are open. What is built:

- **Lists of a sheet laid out for reading** (`engine/sources/layout.py`, D115, D119): the sheet's
  cells (at most `LAYOUT_ROWS` 2,000 rows) read once, each column run split at empty rows, prose
  left out, headers, titles and notes found; the profile's sheets gain `laidOut`, its blocks
  `titles` and `note`; a note's row is left out of the block's statistics.
- **Column statistics per block** (migration `20261016_01`, `source_file_columns.block_index` in the
  key): a column holds several stacked lists; the column page pages by block, then column; a column
  holding only its header is listed with `filled` 0; a column overlap names its `block` on a sheet
  laid out for reading.
- **`listBlock`** (`patterns.list_block`, `build._listBlock`, D116–D119): a list type per list with
  a source on its block keyed by name, its translations (each with the alternative of a text
  attribute), a yes/no column as an attribute, two or more as a flag set, other columns as
  attributes, a column of only its header reported, the note row skipped and the note the type's
  description; a free field or a header with no values a warning; a navigation group per innermost
  title of two lists or more. The facts read each list as a `BlockTable`.
- **Import** (D117): `key: {"field": "name"}`, `AMBIGUOUS_NAME_KEY`, `KEY_NOT_BOUND` at
  `/key/field`; `addSource` and `setSource` take it.
- **W3** grows (D121) except the run of one shape, which A8c adds. Frontend: the types, a source
  keyed by name in the source pane's words, the pattern's label; the pane itself is A8b's.

**Where it differs from the plan** (each found while building; the approved cases are unchanged in
what they claim):

1. **A migration**, where the plan said none: a column of a stacked layout holds several lists, and
   its statistics were keyed by sheet and column only. `20261016_01` adds `block_index` to the key,
   filled from the statistics' `block`; its case in `test_startup` (upgrade, an interrupted run
   refused and recovered, two starts, a downgrade) was written with it.
2. **D115's rules, refined on the user's reading-layout workbook** before the tests ran: a one-row
   part directly above a list is its header unless it is one cell over lists beside it starting on
   the same row with nothing such above them (then their title); lists side by side share a header
   row only where two parts at least start on it and two hold values under it, and only under
   one-cell rows. **Found by A7's cases:** a sheet of one block of two columns (an ID and a name)
   is laid out only when it stacks several lists; first built without that, it took W2's list
   sheets from A7's rules.
3. **D119's note is found by the profile**, not the inference, so the note row is out of the
   statistics (case 1 asserts no column holds a note among its values); the words are
   `layout.NOTE_WORDS`.
4. **Case 2's "Language 2"** is "Language 1": an unnamed translation is numbered among the list's
   translations, as A6 numbers them (D100).
5. **`AMBIGUOUS_NAME_KEY`** is the code of a source keyed by name; a `record: existing` source's
   name fallback (`nameColumn`) keeps `REFERENCE_AMBIGUOUS`.
6. **Defect found and fixed (A5, A6):** the draft's sheets kept a header's surrounding spaces while
   the import reads it trimmed, so a column whose header ends in a space could not be mapped
   (`unknownElement`); found by the real-file smoke on a list's header. Regression:
   `test_a_header_ending_in_a_space_is_mapped_by_its_trimmed_name` (J34.2, seen failing without
   the fix).
7. **Older tests the package made wrong, replaced:** A3's W3 block test reads the first band (W3 has
   a second); A6's nothing-to-propose regression uses a sheet of headers with nothing under them,
   since W3 now proposes its lists; A3's overlap assertion gains `block: None`.

**Real-file smoke** (the user's reading-layout workbook, once, through the API; by structure):
four sheets, all laid out for reading, with 8, 21, 27 and 39 blocks; 87 lists proposed and 10
navigation groups; 8 warnings, each a header with no values; the proposals applied leave the draft
valid; the dry run reads 720 rows over 87 sources, skips the 4 note rows and refuses none.
Misreadings left to A8b's adjusting and dropping: a title with two sentences under it read as a
list of two values; a second header row (a role under each category) read as a value; on the
densest sheet a few sub-list headers read as titles; the lists of one shape under categories read
as a list each (A8c).

**Checks:** the six cases written first: 12 of 16 failed before the build (case 5, the control,
and A6's replaced regression passed). `test_j34_onboard.py`, `test_j35_next_version.py`,
`tests/unit/engine/sources/`, `tests/unit/engine/imports/`: 323 passed (3 min 49 s, over the
2-minute ceiling, run with the user's go-ahead; a first run found A7's narrow sheets, fixed above).
`-m jobs` without those: 276 passed (3 min 29 s, with the go-ahead). `test_startup`,
`test_schema_drift`, `test_foreign_keys`: 44 passed (1 min 30 s), and the new migration case.
`-m contract`: 76 passed, the OpenAPI lock re-baselined after diffing the document against the
previous commit (the block's `titles` and `note`, `SourceBlockNote`, `laidOut`, the overlap's
`block`, `SourceKey.field`, descriptions; nothing else). `tests/unit/engine/model/authoring/`:
3,190 passed; the J33 journeys (`-m authoring` without units, J34, J35): 66 passed; `-m
model_admin`: 321 passed in 4 min 52 s, **over the ceiling and run without being announced** (it
was estimated from T1's run of five groups). New unit tests: `test_layout.py` (10: side by side,
stacked, a header with an empty row, titles reaching and levels, prose, a header without values,
notes) and four for `list_block`. `ruff check app/ tests/`: clean. Frontend: `vitest related` 75
passed, `npm run format`, `npm run lint` (0 errors, the 7 known warnings), `npm run build`. **Not
run:** browser runners (no screen changed; `test:browser:authoring-a6` and `-a7` read the source
pane, which A8b reworks), the accessibility and visual gates, the full suites (R).

##### A8b plan (2026-10-14)

**Planned 2026-10-14 on the user's instruction ("deliver build 0.10 A8b"); D122–D130, the test
cases and the mock-up accepted by the user on 2026-10-15 ("all good, you can go ahead").** Mock-up
([lists of a sheet](https://claude.ai/artifact/V31U2wkFwnfA4XR4oMrrPv), four boards: the source pane
list by list with a proposed list selected, Adjust list…, a list nothing loads with Load as a
list…, 390px; private until shared). Its workbook is made up, with the shapes A8a found on the
user's reading-layout workbook. Checked against the code at `50384ae`:

- **The source pane is a flat column list per sheet** (`SourcePane.tsx`, one `listbox`). A sheet
  laid out for reading lists the same header once per list holding it, with nothing saying which
  list a column belongs to; on the real workbook's densest sheet that is 39 lists in one list.
- **No route reads cells.** The profile serves sheets (with their blocks, `titles` and `note`) and
  column statistics; the staged cells (`source_file_cells`) are read only by the engine.
- **`setSource` changes `headerRow` and `block`** and leaves the bindings alone; bindings name a
  column by its header (`mapColumn`), so moving the header row leaves every binding naming a
  header the new row does not have.
- **Undoing a proposal's step is refused when a later step names what it created**
  (`OPERATION_HAS_DEPENDANTS`, D8). The navigation group step names every list of its group, so
  undoing one list's step would also undo its group.
- **A removal takes the type's navigation entries with it** (D31); the type's source becomes an
  `unmapped` entry (D78) unless it is removed first.
- **`POST …/inference/application` is refused `INFERENCE_STALE`** after any step that is not a
  proposal's, so a list cannot be proposed again from the latest inference once the administrator
  has edited anything.
- **A list's proposal is built from a `BlockTable`** (`facts.py`), filled by one statement over the
  staged cells for a rectangle; `patterns.list_block` and `build._listBlock` do not depend on how
  the rectangle was found.

**What is built:**

1. **The source pane list by list** (D122): a sheet laid out for reading shows its lists under their
   titles; each list one row (header, range, rows, a note, its status: Proposed, Loaded, Not
   loaded); the selected list opens to its columns, which are A5b's column rows with their
   statuses, Map to… and drags. Sheets holding a table are as before.
2. **A selected list in the centre** (D123): its titles, range, header row, rows, note and what it
   loads; Proposed because while it is the engine's (A6b's card, from its `listBlock` proposal);
   the cells around it; its actions.
3. **The cells of a range** (D124): `GET /source-files/{id}/profile/sheets/{sheet}/cells?range=E11:G19`,
   paged by rows.
4. **Adjust list…** (D125, D126): a dialog over the sheet's cells with header row, last row, first
   and last column; one `setSource` step; bindings follow their column letters.
5. **Don't load this list** (D127): one step removing the list's source and its list type.
6. **Load as a list…** (D128): the same dialog on a list nothing loads; the engine reads the
   rectangle as A8a reads every list; the operations sent as one step.
7. **390px** (D129) and the browser runner `test:browser:authoring-a8`.

**Decisions** (D122 onward):

| # | Question | Recommendation |
| --- | --- | --- |
| D122 | How a sheet laid out for reading shows in the source pane | **Its lists, under their titles (the innermost title as a heading), each one row: the header, the range, the rows and the note in words, and a status: Proposed (a source the engine still owns loads it), Loaded (yours), Not loaded (no source loads it: dropped, a free field, a header with no values). The selected list opens to its columns, which are the column rows A5b built. One `role="tree"` with one tab stop: Up and Down move, Right opens a list, Left closes it or goes to its list, Enter selects, Shift+F10 on a column opens Map to… as today.** A list is what the administrator thinks in on such a sheet, and A8a's misreadings are fixed per list. A column list per list as a second level of tabs was considered; 39 lists do not fit as tabs. A list's status comes from the draft's profile: a source on the sheet whose `headerRow` lies within the list's rows and whose columns overlap the list's is the list's source. That is matching in the browser, over data the client already holds, and it decides only what is shown |
| D123 | What the centre shows for a list | **The list's titles, cells (range, header row, rows), note and what it loads (the list type, keyed by name, its group); Proposed because from its `listBlock` proposal while the source and type are still the engine's; the sheet's cells around the list, a row and a column on each side, the list shaded and its header darker. Actions: Adjust list… and Don't load this list on a loaded list; Load as a list… on one nothing loads.** The cells are how the administrator sees that a role row was read as a value, or that two sentences were read as a list (the A8a smoke's misreadings); the statistics cannot show it. A selected column keeps A5b's centre |
| D124 | How the browser reads cells | **A new read, `GET /source-files/{id}/profile/sheets/{sheet}/cells?range=A1:F30`, paged by rows (`PageQuery`, cursors and positions like every collection): each row's `row` and its `cells`, by column letter, the staged value as text with its value type. A range is required; an empty range or one outside the sheet is refused `INVALID_RANGE` with the reason. Under the source files' gate.** API-first: an integrator checking a list's rectangle before an import needs the same read. Paging keeps it bounded without a cap. The staged cells are already one row per cell, so this is one keyset query |
| D125 | How a list is adjusted | **A dialog (`ui/Modal`) showing the sheet's cells with the list outlined and four fields: header row, last row, first column, last column. The outline follows as they change; under it, the rows the list will load against the rows it loads now. Apply sends one `setSource` (`headerRow`, `block`); the dry run follows. Fields are the keyboard and phone path; the grid is the picture and takes no clicks.** Dragging the outline's edges on the grid was considered; it is the mouse-only part of the dialog and can come later without changing anything here. The dialog shows the whole sheet up to 200 rows around the list, read by D124's pages as the grid scrolls |
| D126 | What happens to a list's columns when its header row moves | **`setSource` with a new `headerRow` rewrites each of the source's bindings to the header the same column letter holds on the new row; a column left outside the new `block`, or whose new header cell is empty, becomes an `unmapped` entry, as a removal leaves one (D78). The dialog says which header each column will have. When the header row moves, it offers "Name the list after the new header", off by default, sent in the same step as `setLabel` of the type.** Without it, moving the header row (the fix for the A8a smoke's role row read as a value) leaves every binding naming a header that row does not have. The rule is generic: a table's header row moved by any client keeps its columns. A `firstRow` for values in the import contract was the other way (header stays, values start later); it adds a field every source, import and dry run would carry for one case, and the note row (D119) already shows a skipped row needs none. Composable domains (ADR-032): inbound flow only, no door affected |
| D127 | What Don't load this list does | **One step of two operations, sent together: `removeSource` of the list's source, then `removeObjectType` of its list type when nothing else in the draft loads or relates to it (otherwise the source alone). Undo restores both. The list then reads Not loaded; its columns not mapped. Propose again leaves it alone: a removal is the administrator's change (D92).** The plan said "undo its proposal's step"; undo is refused when a later step names what it created (D8), and the navigation group's step names every list in it, so undoing one list would take its group with it, and an edit made since would block it. A list nothing loads needs no "ignore": it loads nothing already, so the plan's "ignores the block" is dropped. Whether D92 treats a removal as the administrator's change is not yet checked in code; case 9 asserts it |
| D128 | What Load as a list… does | **The adjust dialog in its loading form, on a list nothing loads (a free field, a header read as a title, a list dropped earlier): the administrator sets the rectangle and the engine reads it as A8a reads every list. A new route, `POST /model-drafts/{id}/inference/list` with `sheet`, `headerRow` and `block`, answers a `listBlock` proposal for that rectangle (summary, evidence, operations), built now against the draft and not stored; the editor sends its operations to `POST …/operations` as one step. The list is the administrator's (New), not Proposed. A free field note is read as any note, and the list is loaded because it was asked for. A rectangle with no values under its header is refused `INVALID_RANGE`.** The browser building the operations itself would copy A8a's reading rules (translations, yes/no columns, the note) into the client. Proposing again from the latest inference is refused once anything was edited (`INFERENCE_STALE`), so the stored proposals cannot serve. A rectangle is read by one statement, so the route answers at once, with no job |
| D129 | 390px | **As A5b's tabs: Source lists the lists under their titles; choosing one opens the selection tab with its card, cells (scrolling sideways in their frame) and actions as full-width buttons; the dialog fills the screen, its fields above the cells.** The same tabs, nothing new to learn |
| D130 | When A8b is done | **On approved screenshots (1440px and 390px, light and dark): W3's sheet list by list with a list selected; Adjust list… with the header row moved; a dropped list; Load as a list… on the free field. Plus one real-file smoke on the user's reading-layout workbook: the three A8a misreadings each fixed in the editor (a list dropped, a header row moved, a list loaded), the dry run refusing no row.** Memory rules: a spreadsheet package is tried on a real file before done, dialogs included |

**Journey test cases** (backend, `tests/journeys/test_j34_onboard.py`, J34.10 continued; each on two
configurations, W3 of one seed in a new workspace; no test names a configuration's key or a
header text):

7. **J34.10 A list's cells.** Given W3 profiled, reading a list's range returns its rows in order,
   the header row first, each cell by its letter with its value type, paged with cursors; an
   empty range and a range outside the sheet are refused `INVALID_RANGE`.
8. **J34.10 A header row moved.** Given the proposals applied, when a list's source moves its
   `headerRow` one row down, each bound column keeps its binding under the header its letter has
   on the new row, and the dry run counts one row fewer for it; a column whose new header cell is
   empty is `unmapped`.
9. **J34.10 A list not loaded.** When a list's source and list type are removed in one step, the
   dry run has no source for it, its navigation group no longer lists it, and proposing again
   proposes nothing for it; undoing the step restores the source, the type and the group entry.
10. **J34.10 A rectangle loaded as a list.** Given the free-field list's rectangle, the list route
    answers a proposal with a list type, a source on that rectangle keyed by name and the note row
    skipped; its operations applied, the dry run loads its values; a rectangle with nothing under
    its header is refused `INVALID_RANGE`.

**Unit tests:** D126's rebinding (moved down, moved up, a column dropped by a narrower block, an
empty new header cell).

**Browser cases** (`test:browser:authoring-a8`, new, real backend, W3 in a new application and in
extend mode over `generated-b`):

1. The sheet shows its lists under their titles with their statuses; by keyboard alone a list is
   opened to its columns and a column mapped with Map to….
2. A selected list shows its cells and Proposed because.
3. Adjust list… by keyboard: the last row two up, Apply; the list's rows and the dry run follow;
   History names the step.
4. Don't load this list: the list reads Not loaded and leaves the model pane; Undo brings it back.
5. Load as a list… on the free field: the list type appears in the model pane marked New; the dry
   run loads it.
6. 390px: Source → a list → its tab; the dialog usable.

`test:browser:authoring-a6` and `-a7` run again for the shared panes.

**Groups:** `authoring`, `jobs` (the dry run after a moved header), `contract` (the cells route,
the list route, `INVALID_RANGE`; the OpenAPI lock re-baselined after a diff); Vitest related.
**UI acceptance:** the reference pattern is A5b's source pane and A6b's Proposed because; the state
inventory gains the list row (Proposed, Loaded, Not loaded, loading, error) and the dialog (its
states, a refused apply).

**Composable domains (ADR-032):** inbound flow gains bindings that follow their column when a
header row moves (D126); identity, attribute storage, audit and history, the `match` declaration
and mapping coverage are unchanged. No door is affected.

##### A8b record (2026-10-15)

**Built 2026-10-15** as planned (D122–D130, the approved mock-up's four boards); **complete when the
user approves its screenshots** (D130). What is built:

- **The source pane list by list** (`SourcePane.tsx` `SheetLists`, `lists.ts`, D122): a sheet laid
  out for reading is one `role="tree"` of its lists in reading order under their innermost titles,
  each with the range its source loads, its rows and note, and a Proposed, Loaded or Not loaded
  pill; the open list's columns are A5b's column rows (the row's markup and status extracted once,
  `ColumnRowBody`, `columnDisplayStatus`, for the list and the tree).
- **A selected list** (`ListPanel.tsx`, `CellGrid.tsx`, `useCells.ts`, D123): `show=list&sheet=&block=`
  in the address; Proposed because while its source or type is the engine's; its cells around it.
- **The cells of a range** (D124): `GET /source-files/{id}/profile/sheets/{sheet}/cells?range=`,
  `staged.cell_range` and `cell_rows`, one keyset-paged statement; `INVALID_RANGE`.
- **Adjust list…** (`AdjustListDialog.tsx`, D125) and **`setSource` following column letters**
  (`mapping._follow_columns`, D126): the kinds' sheets read a row of staged cells on demand
  (`Sheet.row`); a binding or key column whose new header cell is empty, outside the block, or taken
  by another binding becomes an unmapped entry (`profile_side.unmap`, `unmap_key`, now also used by
  `prune`); a source moved to another header row may be mapped by that row's headers.
- **Don't load this list** (D127): `removeSource` and, when no other source loads it and no other
  type relates to or contains it, `removeObjectType`, in one request.
- **Load as a list…** (D128): `POST /model-drafts/{id}/inference/list` (`inference/one_list.py`):
  the rectangle's statistics by profiling's statement (`profiling.rectangle_columns`), its table
  (`facts.block_tables`, made public), `list_block(asked=True)` and `Builder.list_proposal`, which
  reuses the draft's language list and translation type.
- **390px** (D129): the dialog's fields two by two.

**Where it differs from the plan:**

1. **Case 10 on a dropped list** (the user, 2026-10-15): W3's free field holds no values, so the case
   loads a list dropped by case 9's step and the free field's rectangle is the refused case; browser
   case 5 the same way.
2. **The dialog does not send a rectangle with nothing to load**: it says there is nothing to load
   and offers no Load (found on the screenshots); the API's refusal is case 10's.
3. **Defect found and fixed (A6, D92):** an element created again exactly as its proposal made it
   read as still the engine's (ownership was decided by comparing states). Found by case 10. Fixed in
   `run.engine_elements`, which now reads the steps that created an element after its proposal.
4. **D127's check, done:** case 9 passed before any code changed; a removal is the administrator's
   and Propose again leaves the list alone.
5. **Found by the runner:** the profile lists blocks column run by column run, so a title's lists
   were not consecutive; the tree reads them in reading order and gathers each title's lists.

**Real-file smoke** (the user's reading-layout workbook, once, through the API; by structure): 4
sheets, 87 lists proposed, 8 warnings; applied, the dry run reads 720 rows and refuses none. A list
of a sentence (J26:J27) dropped in one valid step, its type removed; a three-column list's header
moved a row down: the column with a header of its own there followed its letter, one whose new
header repeated another's and one whose new header cell is empty became unmapped; the one list
nothing loaded with values under its header read as a list on request, the 8 headers with nothing
under them refused; afterwards the dry run reads 719 rows over 87 sources and refuses none.

**Checks:** the four cases written first: 6 of 8 failed before the build (case 9 passed, see 4).
`test_j34_onboard.py`, `test_j35_next_version.py`, `tests/unit/engine/sources/`,
`tests/unit/engine/model/authoring/`: 3,450 passed in 6 min 47 s (with the user's go-ahead, estimated
at about 4 minutes; the authoring units, 3,190, were included). `-m contract`: 76 passed, the
OpenAPI lock re-baselined after diffing the document against the previous commit (the cells route
and `SourceCell`, `SourceCellRow`, `SourceCellPage`; nothing else). New unit tests:
`tests/unit/engine/model/authoring/test_mapping.py` (7: moved down, up, an empty new header cell,
narrowed, moved and narrowed, a key column, an unchanged header row) and `lists.test.ts` (5). `ruff
check app/ tests/`: clean. Frontend: `npm run format`, `npm run lint` (0 errors, the 7 known
warnings), `npm run build`, `vitest related` on the changed files 556 of 557 (the one,
`WorkspaceAdmin`'s retire test, passes alone with and without A8b: a timing flake under load).
Browser: `test:browser:authoring-a8` 14 checks on both designer models;
`-a6` (18) and `-a7` (12) for the shared panes. Screenshots inspected (1440px light and dark, 390px):
the list tree, a proposed list, the adjust dialog with the header moved, a dropped list, Load as a
list…, the free field's dialog, 390px list, source and dialog. **Not run:** the accessibility and
visual gates (R; axe ran in the runner on a list's centre and the dialog), the full suites (R).

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
| D9 | Interactive dry-run budget | **Accepted 2026-10-11; replaced by D67 (A3, 2026-10-12):** every dry run checks the whole file as a job, superseded runs cancelled; no 1-second target; the time measured once in A3 | A3 |
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

1. **A8b is built (2026-10-15, [record](#a8b-record-2026-10-15))**, complete when the user approves
   its screenshots; then A8c (D120). A8a is delivered (2026-10-14, [record](#a8a-record-2026-10-14)).
   **A7 is delivered (2026-10-14, [record](#a7-record-2026-10-14)), its screenshots approved**; its plan, D106–D113 and test cases were accepted by the user the same day. The user chose A7 before A8. A5c is delivered (2026-10-14,
   [record](#a5c-record-2026-10-14)). After A7: A8 (below the cut line, D2) or R. A6 came before A5c (the user,
   2026-10-12: A5b is tested well only once A6 proposes the model and its mappings). A5b is committed
   ([record](#a5b-record-2026-10-12)); what it still needs is settled in A6. A5a is delivered (2026-10-12); the [A5 plan](#a5-plan-2026-10-12),
   its decisions, test cases and mock-up were accepted the same day. A3 and A3a are delivered (2026-10-12).
