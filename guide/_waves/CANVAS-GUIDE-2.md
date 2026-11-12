# CANVAS-GUIDE-2: three entries the guide does not name yet

The inventory lists three things no page names (`_coverage/inventory/uncovered.md`). Add one sentence each where a
reader would look, checked against the code; change nothing else:

1. **Remove object type** in an object type's menu on the canvas (`frontend/src/features/workbook-canvas/WorkbookCanvas.tsx`
   around line 1008: what it removes, and when it is offered): on `src/content/docs/guide/model/edit-a-model-on-the-canvas.md`.
2. **Stop reading rows holding only this column as headings** in a column's menu on the canvas (the counterpart of
   "Rows holding only this column are headings"): on `src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md`,
   beside the heading-rows sentence.
3. The model editor's choice of what a load does with records no row names, and its confirmation
   **Delete the records no row names?** with **Delete them on load** (`frontend/src/features/model-editor/MissingRecords.tsx`,
   on a source's list panel): on the guide page that describes a sheet's list panel or loading a workbook into a
   change set (`src/content/docs/guide/model/read-lists-in-a-sheet.md` or `load-a-workbook-into-a-change-set.md`,
   whichever describes the list panel), as a short paragraph: Report them (the default) or Delete them, and what
   Delete does in the change set.

Then run, in `guide/`: `GUIDE_OUT=_build/CANVAS-GUIDE-2 npm run build` and `npm run verify`.

## Files you may edit

- `src/content/docs/guide/model/*.md`
- `src/content/docs/model/*.md`

## Report

The sentences added, with their page; the result of `npm run verify`.
