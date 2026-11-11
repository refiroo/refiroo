# MC1 guide: reuse or create in a matrix cell, and exporting what a view shows

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names (people filling in views, model authors,
integrators).

## Why

Two 0.17 packages, built (plan `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, sections "EX1: Export says what it exports" and
"MC1: Reuse or create in any matrix cell", decisions PP-D18 to PP-D23; CHANGELOG, Unreleased, the EX1 and MC1 entries).
The code wins over the plan wherever they differ:
- cell dialog: `frontend/src/features/objects/RelationMatrixCellDialog.tsx` (`holdsOne`, `createButton`, `linkButton`);
- cell actions in the editor: `frontend/src/features/model-editor/matrixView.ts` (`actionOptions`) and
  `frontend/src/features/model-editor/operations.ts` (the view's Change…, "What people can do in a cell");
- matrix reads and containers: `backend/app/engine/reads/matrix_read.py`, `backend/app/management/projections/relation_matrix.py`;
- export: `frontend/src/features/jobs/ExportDialog.tsx`, `frontend/src/features/jobs/exportRequest.ts`,
  `backend/app/engine/jobs/export_views.py`, `matrix_sheets.py`, `grid_sheets.py`, `about.py`, `people.py`;
- API: `docs/API.md` (`POST /exports` with `view`, `newCellContainers`, the matrix containers read with
  `suggestedContainerId`).

## What the product does now (check each point in the code)

**A matrix cell (MC1).**
- What people can do in a cell is set per view in the model editor: the view's Change…, field "What people can do in a
  cell", any combination of create, edit, link and unlink. Say where it is, step by step, and why the editor may not offer
  an action (check `actionOptions` for the conditions).
- A cell that already holds records offers **Create** next to **Link existing**, unless the cell may hold only one record.
  It may hold one when the relationship's uniqueness is scoped to the column type, or when its cardinality lets the row's
  end hold one (one-to-one; many-to-one read outgoing; one-to-many read incoming). Then a filled cell offers what it did
  before. An empty, inactive or history-only cell offers Create as before.
- Link existing lists the candidates, and says why a candidate cannot be linked.
- A record created in a cell goes into a container the person picks, as for an empty cell. There is no model default.
- What each action does: a link is a relationship; unlink removes the relationship, never the record. A created record sits
  in its container and is listed there too. The same record can be linked under several rows (reuse).
- In a one-per-cell matrix, a change set can still hold two records for one cell (a conflict); say what the cell shows then
  (cell states in the projection) and how it is resolved.

**Exporting a view (EX1).**
- The Export dialog's "What" choice: this view, the type, the application or the whole workspace. "This view" is first on
  every view, and it shows a count line (for example "200 rows × 8 columns, from change set …"; records for a tree or a
  mapping grid). The file kind is "For editing in a spreadsheet" or "Technical". Technical is offered for a table, a type,
  an application or a workspace only.
- Each view kind has its own file shape: a matrix as rows × columns with hidden IDs; a link matrix with a dropdown per
  cell; a relationships table as rows or a grid; a mapping grid; a tree with its parents. "For editing" a type,
  application or workspace gives one sheet per type, parents first. Every file has the same About sheet, second in the
  file: which view, which relationships, counts, and what loads back.
- A matrix that creates records: the dialog asks, per column, where new records go. The container holding most of the
  column's exported cells is preselected, none otherwise. A new cell with no container is refused on import, by name.
- What loads back: a matrix file loads only its cells. A cleared or empty cell changes nothing. A cell holding several
  records is not loaded. A relationship that owns its records is read-only in a cell. A name with ";" is written and read
  with a comma in a link cell. Filters on a relationship's own values are not carried (the dialog says so).
- Still in the app only: removing every value of a cell; editing a cell that holds several records.

**What an integrator sees.** After the change set is published, the consumer API shows the new record and the new
relationship. A reused record has the same record ID under every row that links it. An unlink shows as a removed
relationship in the feed. An export of a view is `POST /exports` with `view` (and `newCellContainers` for a creating
matrix). Check every claim against `docs/API.md` and the integrator pages' existing wording.

## What to do

- Explain the cell by example, in neutral examples (never the example model or its types):
  a translation matrix (create, one per language), a mapping matrix (reuse a record already linked elsewhere, or create
  one), and a one-per-cell matrix (what the dialog shows, the conflict). For each say the implication for relationships and
  for consumers.
- Extend the pages that own each topic, rather than duplicate: the cell in `fill-in-a-relation-matrix.md` and
  `use/relation-matrices.md`; the actions in `guide/model/add-a-relation-matrix.md` and `model/applications-and-views.md`;
  exporting a view in `guide/use/export-records.md`, `guide/use/edit-in-excel-and-import-back.md` and
  `use/importing-and-exporting.md`; the consumer side in `integrate/relationships-and-their-values.md`; the export API in
  `integrate/files-imports-and-exports.md`. Link the pages to each other where a reader needs the next step.
- No new pages. Pictures: list in the report each picture the text calls for that is not taken yet.

## Changed since the first wave (second wave: the code wins over the pages written in the first)

Plan decisions PP-D24 to PP-D28 and the EX1/MC1 delivery records. Code: `backend/app/engine/model/candidate_places.py`,
`backend/app/engine/imports/places.py`, `backend/app/engine/jobs/matrix_sheets.py`, `backend/app/engine/imports/binding.py`,
`frontend/src/features/objects/RelationMatrixCellDialog.tsx`, `frontend/src/features/jobs/ExportDialog.tsx`,
`frontend/src/features/jobs/ImportOutcome.tsx`, `docs/API.md`.

- **Where a new cell record goes.** First the relationship's candidate rules in the model: only groups a record could
  meet them in are offered; where the rules name one group exactly and it is missing, it is created with the record.
  Without such rules, the data decides: the group already holding this view's records in that column (the busiest; none on
  a tie). A group holding none is never picked automatically, even as the only one. Where nothing decides, refiroo proposes
  a new group named like the groups this view uses in other columns: the dialog asks, the name editable, one OK creates the
  group and the record; an import preview says "will create … under …" and confirming the import creates it. Other groups
  stay choosable. Say plainly that no model change is needed for this.
- **The export dialog has no container section any more.** It asks "What each cell lists": any text field of the cell's
  records (default Name). The file records the choice. Remove the first wave's text about choosing containers in the export.
- **Value sheets** (matrices that link): one sheet per column listing that column's records with every field, the group
  and a hidden ID. The main sheet's dropdowns read it. Edit a value there (updates by ID); add a row (a new record, where
  the view creates); a name typed in a main cell that is in neither place becomes a new record with only that field; the same
  name in both is one record; a row picked nowhere is still created. A spreadsheet cannot sync the sheets itself; the import
  does. A matrix that only creates (cells hold the record's own fields) has no value sheet. Do not claim how Numbers or Excel
  show the dropdowns: that is not checked yet.
- **The import preview "How the file is read"**: per column the field used (guessed for a file refiroo did not write,
  with a note when unsure), values matched, where new records go, value-sheet counts; the field can be changed (the preview
  runs again) and saved into the profile. Nothing is written before confirming.
- **Integrators**: `POST /exports` view `cellField` (no `newCellContainers`); the matrix containers read's `derivedPlace`
  (with `proposed`, `willBeCreated`) and per-container `cellCount`; `POST /jobs/{jobId}/reread`; the reading in the import
  report. Check against `docs/API.md`.

Extra page allowed for the preview: `src/content/docs/guide/use/import-a-file.md`.

## Files you may edit

- `src/content/docs/guide/use/fill-in-a-relation-matrix.md`
- `src/content/docs/use/relation-matrices.md`
- `src/content/docs/guide/model/add-a-relation-matrix.md`
- `src/content/docs/model/applications-and-views.md`
- `src/content/docs/guide/use/export-records.md`
- `src/content/docs/guide/use/edit-in-excel-and-import-back.md`
- `src/content/docs/use/importing-and-exporting.md`
- `src/content/docs/integrate/relationships-and-their-values.md`
- `src/content/docs/integrate/files-imports-and-exports.md`
- `src/content/docs/guide/use/import-a-file.md`
- `_waves/progress/MC1-GUIDE.md`

## Report

Per page: what changed and why (one line each), what you checked and left, pictures needed, and any point the guide cannot
describe honestly.
