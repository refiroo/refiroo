# READINGS-IN-EDITOR: the model editor sets the three readings too

On 2026-11-12 the model editor gained the three import-profile readings that until then only the canvas set
(0.17 CE1): read a wide sheet as rows, fill blanks from the cell above, and read heading rows as the parent of the
rows beneath them. Read the CE1 entry in `CHANGELOG.md` `[Unreleased]` that names them, and the code:
`frontend/src/features/model-editor/ReadingEntries.tsx`, `ReadingAsks.tsx`, `ColumnPanel.tsx`, `ListPanel.tsx`,
`SourcePane.tsx`. The code wins.

## What to write

Where the guide says these readings are set on the canvas (search for "fill blanks", "as rows", "heading" in the
pages listed below), say they are set on the canvas and in the model editor. In the editor:

- a column's panel has a **Readings** row: **Fill blanks from the cell above**, **Rows holding only this column are
  headings…** and **Read these columns as rows…**, and a **Stop…** entry for a reading that is on;
- a list's panel has **Read these columns as rows…**;
- the source pane marks the column a reading is on.

Use the interface's labels exactly. Change only the sentences that are now wrong or incomplete; do not restructure.
No time estimates; add no image references.

Then run, in `guide/`: `GUIDE_OUT=_build/READINGS-IN-EDITOR npm run build` and `npm run verify`.

## Files you may edit

- `src/content/docs/use/importing-and-exporting.md`
- `src/content/docs/guide/use/load-the-next-version-of-a-workbook.md`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/integrate/files-imports-and-exports.md`

## Report

Each page changed with the sentences before and after; build and verify results.
