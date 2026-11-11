# LB guide: Hide empty columns on a relation matrix

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

An addition to the product (CHANGELOG, Unreleased, "Added (list browsing: ...)", the bullet "A relation matrix can hide its
empty columns"). The code wins: `frontend/src/features/objects/RelationMatrixView.tsx` (`Hide empty columns`,
`chooseHideEmpty`, the line "N empty columns hidden · Show all"), `frontend/src/ui/TableDisplay.tsx`
(`readHideEmptyColumns`), `backend/app/management/projections/relation_matrix.py` (`_non_empty_columns`),
`docs/product-functionality/CURRENT_FUNCTIONALITY.md`, `docs/API.md` (the `hideEmptyColumns` row of the relation matrix read).

## What the product does now (check each point in the code)

- In a relation matrix's toolbar, beside **Filter**, a switch **Hide empty columns**, off by default. It is kept for
  this view in this browser (with the column widths), so it is still on after a reload, and on another device it starts off.
- On, the matrix shows only the columns that have at least one related record in some row. "Some row" means every row the
  current search and the scope (rows under one record) leave, not only the rows on the screen. The columns the matrix
  pages through sideways skip the empty ones, so each page of columns is full.
- When columns were left out, a line under the toolbar reads "N empty columns hidden · Show all" ("1 empty column hidden"
  for one). **Show all** turns the switch off.
- If columns were chosen in **Filter**, the chosen columns are shown and the switch has no effect; the switch says "No
  effect while columns are chosen in Filter". The setting stays as it was and works again when the choice is removed.
- It works in a change set and in a publication on their own values.

## What to do

- Add what is missing, in the page that already owns the topic; keep its voice and structure. Candidates:
  `use/relation-matrices.md` (the toolbar and the columns' paging, Filter), `guide/use/fill-in-a-relation-matrix.md` (a
  step or a note where columns are chosen or the empty ones are in the way).
- No new pages and no new pictures; do not touch `matrix-operator-names.png`, `matrix-municipalities-by-system.png` or
  `matrix-filter-panel.png` (they are being retaken). List in the report any picture the toggle calls for.
- A point the guide cannot describe honestly: list it in the report with the evidence.

## Files you may edit

- `src/content/docs/use/relation-matrices.md`
- `src/content/docs/guide/use/fill-in-a-relation-matrix.md`
- `_waves/progress/LB-GUIDE-MATRIX.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures needed, and
any product point the guide cannot describe honestly.
