# MX-COLUMNS: choosing a relation matrix's columns for their own sake

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md`. Reader: people who use a relation matrix in the
browser (stewards, contributors). Nothing in the product changes; two pages describe the column chooser
only as a step in checking coverage. Add what they miss, in the pages' own style. The code wins over this
brief, and a fact that no source supports is not written.

**Pages:**

- `src/content/docs/guide/use/fill-in-a-relation-matrix.md` (task page)
- `src/content/docs/use/relation-matrices.md` (concept page, section "Filters and coverage")

**What is missing** (check each statement in the sources below):

1. **Narrowing the columns is a use in itself.** A matrix shows every record of its column type, for
   example every system, also those that do not concern the list in the rows. **Filter** › "<column
   type plural> to show" lets the reader keep only the columns that concern them (at most 20), without
   choosing a cell state. Add a short task section for this on the task page (choose Filter, select the
   columns in the chooser, Done; **Show all <column type plural>** brings every column back), and one or
   two sentences on the concept page. Keep the existing "Find empty cells across the list" section as it is.
2. **The choice is not saved for the view.** It belongs to the page the reader has open: the chosen
   columns are kept in the page's address (one `matrixColumn` parameter per column, with `matrixState`
   for the state), so a bookmark or a shared link opens the matrix with the same columns, but opening
   the view again from the navigation shows all columns. Other people do not see the choice. Say this
   on both pages in plain words; name the URL parameters at most once, on the concept page, if the page
   already names technical details elsewhere, otherwise not at all.

**What stays as it was:** every other section, the screenshot and its caption, headings and order of
the existing sections. Use only examples already on these pages or in the guide's example data; do not
name any system or list from outside the guide.

**Sources:**

- `frontend/src/features/objects/RelationMatrixFilter.tsx` (the chooser, "to show", "Show all …")
- `frontend/src/features/objects/RelationMatrixView.tsx` (columns chosen or paged)
- `frontend/src/routing/routes.ts` (lines around `matrixColumn`: the choice in the address)
- `docs/API.md` (`columnIds`, at most 20)

## Files you may edit

- `src/content/docs/guide/use/fill-in-a-relation-matrix.md`
- `src/content/docs/use/relation-matrices.md`
- `_coverage/notes/MX-COLUMNS/**` (working notes)

## Report

As `COMPLETE-COMMON.md` says. Also list each statement above you could not confirm in the sources.
