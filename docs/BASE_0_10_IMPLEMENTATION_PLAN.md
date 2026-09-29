# Base 0.10 implementation plan

**Status:** Provisional, drafted 2026-09-29 while 0.8 finishes Milestone C and 0.9 planning is under
way. It records the sequence, packages and acceptance that follow from
[MODEL_AUTHORING.md](MODEL_AUTHORING.md) and [ADR-035](DECISIONS.md#adr-035--model-authoring-is-an-editor-of-operations-on-a-model-draft-a-spreadsheet-is-one-way-to-start-it).
Review it when 0.9 Track J's import contract is written ([INTEGRATION_API.md](INTEGRATION_API.md)
section J) and again when 0.9.0 is released; package scopes may change then. A-D1–A-D3 are decided;
A-D11 and A-D12 are open but non-blocking; A-D4–A-D10 and this plan's D1–D10 are settled in A0.

**Target:** Product 0.10.0, [model authoring and spreadsheet onboarding](ROADMAP.md#product-release-010--model-authoring-and-spreadsheet-onboarding).
The `navigation` declaration (A-D2) extends the model, so 0.10 introduces the next schema language
version (D1).

**Depends on:** Product 0.9.0 released, in particular:

- Track B bulk upsert with upsert keys (0.9 D2) and item outcomes;
- Track J import jobs with preview, executing import profiles with XLSX and several sheets (revised
  0.9 D3). **Package A1 of this design is delivered inside 0.9 Track J**, not in 0.10;
- job file storage and limits (0.9 D12, D13) and retention (D14).

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

## Principles and exclusions

The principles of [MODEL_AUTHORING.md](MODEL_AUTHORING.md#principles) apply. For delivery:

1. **Generic.** No branch on an application, object-type, attribute or relation key in the editor,
   inference or services. Every journey runs on at least two differently shaped workbooks and on the
   starter model with its keys renamed.
2. **Operations are the only write path of the editor.** The whole-model `PATCH` stays for the JSON
   workbench; the editor never uses it.
3. **Same validation.** Operations, previews and install use the existing model validators; the dry
   run uses the 0.9 import preview. No second validation path.
4. **Lifecycles unchanged.** Model draft → immutable release → activation; data through a 0.9 import
   job into a change set by default; review on the P2 change set review screen.
5. **Bounded and paged.** Source profiles, operation history, dry-run rows and inference proposals page
   under ADR-030; every limit is documented and returned in errors.
6. **Keyboard parity and narrow layouts.** Every drag has a menu and keyboard path. Below the desktop
   breakpoint the panes become tabs; the editor remains usable at 390px, not identical.

Excluded: migration-class operations (1.0, on the 0.11 migration boundary), canvas-first authoring,
pixel layouts, general ETL (formulas, joins beyond key lookup, scripting), live links to online
spreadsheets, legacy `.xls`, authentication and authorization (0.12), PostgreSQL and multi-node
operation (0.11). The designs must not depend on SQLite's single writer.

## What already exists

- **Model drafts** (`/model-drafts`): create, whole-model patch with `expectedVersion`, delete,
  validation with JSON Pointer diagnostics, compile, installation; releases, diff and activation with
  the compatibility check; the JSON workbench. Gated by the model administration capability (ADR-031).
- **Change sets and review:** imports can target a change set; P2 lists added, changed, moved and removed
  records and relationships with before and after.
- **Restructuring (ADR-034):** type changes of existing records in change sets, the operation 1.0's
  migration-class operations will reuse.
- **Generic renderers:** table, mapping grid, relation matrix and tree lenses; detail panel registry
  (attributes, children, relations, table, hierarchy); object pickers limited by relation bindings;
  the tree lens's drag with Move to… as its keyboard path (B5).
- **From 0.9 (planned):** jobs, item outcomes, idempotency, upsert keys, import preview and execution,
  import profiles (A1), job file storage.

## Design documents

| Document | Holds | State |
| --- | --- | --- |
| This plan | Sequence, packages, decisions D1–D10, delivery records, acceptance | Provisional |
| [MODEL_AUTHORING.md](MODEL_AUTHORING.md) | Editor, operation catalogue, import profile outline, pattern catalogue, navigation groups, API outline, decisions A-D1–A-D12 | Direction accepted |
| [INTEGRATION_API.md](INTEGRATION_API.md) J | The import profile contract and its execution (A1) | 0.9, to write |
| [APPLICATION_MODEL.md](APPLICATION_MODEL.md) | The `navigation` declaration and schema language version | Written in A4 |
| [API.md](API.md) | Operation, source file, inference and profile endpoints as delivered | Written in A0, moved per package |
| [DECISIONS.md](DECISIONS.md) | ADR-035; further ADRs only for durable choices found in A0 | ADR-035 accepted |

## Scope inventory

| # | Roadmap 0.10 item | Stories | Package |
| --- | --- | --- | --- |
| 1 | Import profiles, XLSX, several sheets | US-P09, US-P10 | A1 (in 0.9 Track J) |
| 2 | Operation API on model drafts, history, undo | US-P05, US-P09 | A2 |
| 3 | Source profiling and dry-run summary per operation | US-P09 | A3 |
| 4 | Editor: model pane, relationship matrix, preview, layout editing, navigation groups | US-P05 | A4 |
| 5 | Editor with a source file; saved and re-run profiles | US-P09, US-P10 | A5 |
| 6 | Inference over table patterns; extending an existing model | US-P09 | A6 |
| 7 | Model-description sheets, matching across files | US-P09 | A7 (may move to 0.10.x) |
| 8 | List blocks in sheets laid out for reading | US-P09 | A8 (may move to 0.10.x) |

## Acceptance workbooks

reference only. The repository gets **synthetic workbooks generated by test code** with the same shapes,
so fixtures are deterministic and contain no client data:

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

Each journey runs on W1 and W2, and A8's on W3. The starter model (and the same model with every key
renamed) is the "extend an existing model" case.

## Work packages

Browser modules of this build are named `e2e/authoring-<package>-*.mjs` with scripts
`test:browser:authoring-<package>`, because the 0.8 relation matrix packages already use `a1`–`a6`.
Backend tests join new contract groups declared in `TEST_GROUPS` (named in A0) and are run per
[the execution guide](testing/EXECUTION_GUIDE.md), targeted to the changed boundary.

### A0: Design pass

**Scope:** settle A-D4–A-D10 and D1–D10; write the API design for operations, source files and
profiles, inference proposals and dry-run summaries in API.md's design style; fix the operation
vocabulary (one kind per catalogue row, with its parameters, its inverse and its class); name the
backend contract groups; confirm A2–A8 scopes against the delivered 0.9 contracts; define the
synthetic workbook generators' shapes in test terms.

**Exit:** decisions recorded; API design written; package scopes confirmed or adjusted.

Checks: documentation only.

### A1: Import profile contract and execution (delivered in 0.9 Track J)

Listed for completeness. The 0.10 packages rely on: stored profiles naming a model release and
re-checked on use (A-D3); bindings as in [MODEL_AUTHORING](MODEL_AUTHORING.md#import-profile); sources
ordered by references; per-row outcomes with sheet and row; an import preview that writes nothing;
W1 loaded by a hand-written profile with no code.

### A2: Operation API on model drafts

**Scope:**

- `POST /model-drafts/{id}/operations`: a batch of operations at `expectedVersion`, applied atomically
  to the draft's model and attached profiles, validated, returning the new version and diagnostics.
- The operation vocabulary's additive and draft-only kinds. A draft-only kind on an element present in
  the base release is refused with `operation_requires_migration`, its impact reported and nothing
  applied.
- Operation history (`GET …/operations`, paged), stored per draft with author (the local session until
  0.12), time and the inverse.
- Undo and redo as inverse operations. Undoing an operation that later operations depend on is refused
  with the dependants listed; the client may undo them together (D8).
- Profiles follow model changes: renamed keys are rewritten, removed targets turn their bindings into
  unmapped columns with a diagnostic.
- A whole-model `PATCH` on a draft is recorded in its history as one `replaceModel` operation, so the
  history stays complete.
- Keys generated from labels and editable until installed (A-D6).

**Tests:** each operation kind applied and inverted on the starter model and on the renamed-key model;
batch atomicity (a failing operation applies none); stale version refused with the newer operations;
dependent undo refused; profile rewrite on rename, move, split and merge; `operation_requires_migration`
on a released element; diagnostics identical to whole-model validation of the same result.

### A3: Source profiling and the dry-run summary

**Scope:**

- `POST /source-files` (0.9 job file storage and limits) and `GET /source-files/{id}/profile`: sheets,
  header row, data ranges and blocks, and per column: fill, distinct count, value types, candidate key,
  delimiters, placeholders and value overlap with other columns and with existing records of mapped
  types. Profiling runs as a job; the profile pages by sheet and column.
- The dry-run summary: after each operation batch (A2), the import preview runs on every attached source
  file and returns counts per source (records, values, relations, translations, mappings), rejections by
  code and the difference from the previous summary, each figure linking to a paged row list.
- Interactive budget (D9): the summary returns within the budget up to a row limit; larger files are
  summarized on a deterministic sample with the full run on request, and the response says which.

**Tests:** W1, W2 and W3 profiles (header detection, block detection on W3, statistics); the dry run
after rename, remap, move and value map on W1; difference reporting; the sample-versus-full switch at
the limit; budgets measured and recorded as in 0.8 Track S.

### A4: Editor — model pane, preview and layout editing

**Scope:**

- The editor frame in the Models area (D7): open a draft of the active release or an empty draft;
  model pane (applications, types in their containment tree, attributes, relation types) and the
  relationship matrix of allowed relations between types; the issues list; the operation history with
  undo and redo.
- Every catalogue operation available from menus and keyboard; drag an attribute to another type and a
  type under another parent, with the same keyboard path.
- Preview: a record rendered by the generic renderers from the draft, using existing records (no source
  file yet); edit panels (order within `main`/`side`, visibility, columns, default sort), table views
  (columns, filters, default sort) and field order in place.
- Default views and panels generated for a new type from its bindings.
- Navigation groups (A-D2): the `navigation` declaration in the new schema language version (D1) with
  its validation, APPLICATION_MODEL documentation, sidebar sections and the group page; group operations
  in the editor.
- Install and activate as one confirmed step (A-D8).

**Tests:** backend: the `navigation` contract (valid, unknown collection, duplicate entry, duplicate
group key, absent field unchanged). Browser (`test:browser:authoring-a4`): add a type with attributes
and a relation, reorganize, undo, lay out its detail page, group collections, install and activate, then
create a record in the browser; on the starter model and the renamed-key model; keyboard alone; 1440px
and 390px; axe on the editor's main states; visual baselines.

### A5: Editor with a source file

**Scope:**

- Source pane (sheets, blocks, columns with status and statistics) and mapping pane (column to target
  with its transformation), synchronized with the model pane.
- Mapping operations: map, re-read as text/lookup/relation/flags, split, unpivot, value maps, ignore;
  drag a column onto a target with the keyboard path.
- The dry-run summary after every operation (A3), with links to the rows.
- Load: install and activate if the model changed, then run the import job into a new change set by
  default, and open the change set review.
- Saved profiles: upload the next version to a profile, report new, missing and renamed columns, new
  values and drift before loading (US-P10); missing records reported, never deleted unless the profile
  says so (A-D7).

**Tests:** browser (`test:browser:authoring-a5`): W1 mapped by hand onto a new application (no
inference yet), loaded into a change set, reviewed and published; W1′ through the saved profile with
only its differences in the review; a rename and a move after mapping keep the profile valid; keyboard
alone; 1440px and 390px; axe. Backend: profile save, re-check against a newer release, missing-record
handling.

### A6: Inference over table patterns

**Scope:**

- The table patterns of the [catalogue](MODEL_AUTHORING.md#pattern-catalogue): key column, code and
  name pair, repeated parent, level columns, text lookup, reference to another sheet, multi-valued
  cell, flag columns, translations by row and by column, external IDs, placeholder values, name drift.
- `POST /model-drafts/{id}/inferences`: proposals as operation batches with evidence and alternatives,
  applying nothing; accepting a proposal applies its batch through A2.
- Two starting modes: a new application, or extending the active model by matching columns to existing
  types and attributes (label similarity and value overlap with existing records, bounded).
- Pinned decisions: elements changed or confirmed by the administrator are pinned; re-inference reports
  disagreements and never overrides them.
- Navigation group proposals from sheet names and section headers.
- The optional assistant (A-D5) is an interface only in 0.10 unless A0 decides otherwise; no provider is
  bundled.

**Tests:** each pattern detected on W1 or W2 with its evidence, and not detected on a control column;
proposals applied and edited; re-inference after edits keeps pinned decisions; W1 onto the starter
model extends it rather than duplicating its attributes. Browser (`test:browser:authoring-a6`): W1 from
upload to published change set, accepting, changing and rejecting proposals; keyboard alone; 1440px and
390px.

### A7: Model-description sheets and matching across files (may move to 0.10.x)

**Scope:** recognize a model-description sheet and read it before the lookup sheets it names; propose
types, attributes and relations from it; match records across workbooks by ID or code, report name
drift and missing IDs, and propose value maps.

**Tests:** W2 alone becomes an application; W2 then W1 into the same draft reconcile by ID with drift
reported; placeholders and "to be defined" lists reported, not loaded as values.

### A8: List blocks in sheets laid out for reading (may move to 0.10.x)

**Scope:** detect header-and-values blocks, section and group headers, language column pairs, Y/N
flags and cardinality notes; propose one source per block; the administrator confirms, adjusts or drops
each block in the source pane (A-D9). Colour and formatting carry no meaning.

**Tests:** W3's blocks detected with their headers; confirmed blocks become list types in proposed
navigation groups; adjusted block boundaries; a language pair becomes translations.

### R: Build acceptance and release

- US-P09 on W1 and W2 and US-P10 on W1′, composed in the browser over the real backend, keyboard alone,
  1440px and 390px, with the accessibility and visual gates.
- The editor as designer on the starter model and the renamed-key model (US-P05, additive and
  draft-only).
- The [MODEL_AUTHORING exit gate](MODEL_AUTHORING.md#exit-gate) and the roadmap 0.10 exit gate.
- Budgets from A3 met on the recorded fixture sizes.
- Migration check for the new tables (operation history, pinned decisions) and the new schema language
  version: clean bootstrap, upgrade from 0.9.0, and a 0.9 model still valid.
- Full suites per AGENTS.md at release.

## Provisional sequence

```text
0.9:   Track J ── A1 (import profile contract and execution)
0.10:  A0 ─┬─ A2 ─── A4 ─┬─ A5 ─── A6 ─┬─ A7
           └─ A3 ────────┘              └─ A8
                                         R
```

A2 and A3 can proceed in parallel after A0. A4 needs only A2. A7 and A8 are the cut line (D2): if R is
not in reach they move to 0.10.x and R accepts US-P09 on W1 and W1′ plus the designer journeys.

## Composable domains check (ADR-032)

As recorded in [MODEL_AUTHORING](MODEL_AUTHORING.md#composable-domains-check-adr-032): identity and
inbound flow use 0.9 upsert keys; provenance gains the profile key as a natural source name on import
jobs; audit and data history are unchanged (operation history is model-draft history); value types
convert through the attribute registry; the `match` declaration and mapping coverage are not touched.

## Invariant notes

- **Model references runtime data.** Rejected (A-D1): list scoping is structural, one type per list.
- **Install and activate in one step.** Both lifecycle steps still run, in order, with the compatibility
  check shown; the step is refused on any diagnostic (A-D8). It is a convenience, not a bypass.
- **Stable keys.** Keys change only while unreleased; afterwards a key change is a migration-class
  operation, refused in 0.10.
- **Live by default.** An onboarding load goes to a change set by default because it creates many
  records at once and the administrator asked to review it; a recurring profile load may target live
  data like any 0.9 import. This is the import's choice, not a new mandatory step.

## Open decisions

To settle in A0. The recommendation is the planning default. Design-level decisions are
[A-D1–A-D12](MODEL_AUTHORING.md#open-decisions).

| # | Question | Recommendation | Blocks |
| --- | --- | --- | --- |
| D1 | Schema language version | The version after 0.9's (0.9 D7), adding the optional `navigation` declaration; earlier schemas stay valid; the starter model moves to it only if it declares groups (D3) | A4 |
| D2 | Cut line | A7 and A8 may move to 0.10.x; R then accepts W1/W1′ and the designer journeys | R |
| D3 | Starter model | Unchanged unless a group improves it; acceptance uses generated models from W1 and W2 | A4, R |
| D4 | Where operation history lives | A new table per draft operation (kind, parameters, inverse, author, time, draft version); deleted with its draft; installed releases keep no operation history | A2 |
| D5 | Source files attached to drafts and profiles | Stored as 0.9 job files; the latest file per profile is kept while the profile exists (outside D14 retention) so it can be edited again; older ones follow D14 | A3, A5 |
| D6 | Capability gates | Operations, inference and install under the model administration gate; source upload and import under `INTEGRATION_JOBS_ENABLED` (0.9 D10) | A2, A3 |
| D7 | Where the editor lives | In the Models area, opened from a draft or from "New from a workbook"; no new top-level destination | A4 |
| D8 | Undo with dependent operations | Refused with the dependants listed; the client offers to undo them together | A2 |
| D9 | Interactive dry-run budget | Summary within 1 s for up to 10,000 rows on the reference machine; a deterministic sample above that with the full run on request; figures confirmed in A3 | A3 |
| D10 | Concurrent editors | Optimistic versions only; no locks or live co-editing in 0.10 | A2, A4 |

## Risks

- **Scope.** This is an editor plus inference plus import on top of 0.9's largest build. The cut line
  (D2) and A1 in 0.9 keep 0.10 bounded.
- **Inference quality on real files.** Mitigated by proposals with evidence, pinned decisions and the
  editor as the real product: a weak proposal costs edits, not a wrong load.
- **Dry-run speed.** Measured in A3 with the Track S method; sampling above the budget.
- **Editor accessibility.** A multi-pane editor with drag and drop is the hardest UI in the product so
  far; keyboard paths are designed with each interaction, not added at the end.

## Next

1. Keep this plan in step with 0.9 Track J while INTEGRATION_API section J is written, so A1 carries
   what A3–A6 need (profile shape, preview summary, per-row outcomes).
2. After 0.9.0: run A0.
