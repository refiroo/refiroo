# MAPVIEWS guide: mapping grids and relation matrices on the shared table

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

A product fix (CHANGELOG, Unreleased, "Fixed (mapping grids and relation matrices on the shared table, 0.13 FX)")
changed two screens. Check the pages below against it. The code wins:
`frontend/src/features/objects/MappingGridView.tsx`, `frontend/src/features/objects/RelationMatrixView.tsx`,
`frontend/src/ui/DataTable.tsx`, `frontend/src/features/model-editor/viewKinds.ts` (`gridSourceOptions`),
`docs/APPLICATION_MODEL.md` ("Mapping grid view", `sourceColumns`), `docs/API.md` (coverage search paragraph).

## What the product does now (check each point in the code)

- A mapping grid is drawn with the table every record list uses. Its columns resize (drag a column's edge, or
  focus its edge and use the arrow keys); the widths are kept per view on this device. A value a column cuts off
  shows whole in a box under it when pointed at or focused. Rows stay one line high, except a row with several
  targets, which lists them.
- In a mapping grid, the source record's name is a link that opens the record, and each target chip opens its
  record. A click elsewhere on the row, and the **Map**/**Change** button, still open **Change mapping**.
- A mapping grid's columns of a row (`sourceColumns`) may also name the type above the row (`ancestor:<type>`),
  as a relation matrix's row columns already can: the column shows the name of the record's nearest ancestor of
  that type, headed by the type's name (for system values: their system). In the model editor, **Columns of a
  row** offers those types under "From the parents". Search does not look at them.
- A relation matrix's columns (the row column and each record column) resize the same way and keep their
  widths per view; a cut-off cell value shows whole when pointed at or focused. The cell dialog and keyboard
  editing are unchanged. On a narrow screen a matrix keeps every column, scrolling sideways.

## What to do

- Fix each passage that no longer matches, in its page. Keep each page's voice and structure; change what is
  wrong or missing, not what is right. Candidates: `use/mapping-grids.md` (reading a mapping; the name and the
  targets open records; resizing and the reveal), `use/relation-matrices.md` (resizing and the reveal),
  `model/applications-and-views.md` (the mapping-grid declarations: `sourceColumns` and ancestors),
  `guide/model/add-a-view.md` (the step that chooses **Columns of a row**), `guide/use/map-codes-between-systems.md`
  (only if a step names something that changed).
- No new pages; no new pictures. A picture that no longer matches: list it in the report (name and page).
- A point the guide cannot describe honestly: list it in the report with the evidence.

## Files you may edit

- `src/content/docs/use/mapping-grids.md`
- `src/content/docs/use/relation-matrices.md`
- `src/content/docs/model/applications-and-views.md`
- `src/content/docs/guide/model/add-a-view.md`
- `src/content/docs/guide/use/map-codes-between-systems.md`
- `_waves/progress/MAPVIEWS.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures
that no longer match, and any product point the guide cannot describe honestly.
