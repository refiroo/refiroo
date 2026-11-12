# IMPORT-READINGS-GUIDE: what changed today for imports and for integrators

On 2026-11-12 the import profile and the model draft routes gained new capabilities (0.17 PL3b and CE1). The
canvas how-to pages already describe them for a person on the canvas; the import pages and the integrator pages
do not mention them yet. Read `CHANGELOG.md` `[Unreleased]` (entries for 0.17 PL3b, CE1, PL4 and their Fixed
entries), `docs/BASE_0_17_IMPLEMENTATION_PLAN.md` section **PL3b** with its "Contract for the canvas (engine and
API)", and `docs/API.md` (search for `setUnpivot`, `join-candidates`, `canvas`, `setMissing`,
`workspaces/from-workbook`). Check each fact against the code (`backend/app/models/imports.py`,
`backend/app/engine/imports/readings.py`, `backend/app/engine/model/authoring/mapping.py`,
`backend/app/management/routers/model_management.py`, `backend/app/management/routers/inference.py`,
`backend/app/engine/model/canvas.py`) and the reference text under `backend/app/management/reference/content/`.
The code wins; list differences in your report.

## What to write (briefly, on the page where a reader looks; no restructuring)

1. **Importing, for a person** (`src/content/docs/use/importing-and-exporting.md` and the page about loading the
   next version of a workbook): a saved import profile can now also read a wide sheet as rows (one row per filled
   cell of the chosen columns), fill blanks from the cell above, and read heading rows as the parent of the rows
   beneath them; the next file is read the same way. Where these are set (the canvas; say whether the model
   editor offers them, from the code). A column header is matched without its surrounding spaces. What a load
   does with records no row names (Report or Delete), where it is chosen.
2. **For integrators** (`src/content/docs/integrate/files-imports-and-exports.md`,
   `src/content/docs/integrate/model-and-release-operations.md`, and `src/content/docs/integrate/workspaces-contexts-and-models.md`
   for the workspace route): the profile members `unpivot`, `fillDown`, `headings` and the order they apply in;
   the six operation kinds that set and clear them; `POST /api/v1/model-drafts/{id}/join-candidates` (what it
   compares, over every row, and the tie rule); `GET`/`PATCH /api/v1/model-drafts/{id}/canvas` (positions,
   folded, scope; not part of the draft's version or a release); `setMissing`; `POST /api/v1/workspaces/from-workbook`
   if not described yet. Point to the API reference for the exact shapes instead of copying them.
3. Correct any sentence these changes made wrong on the pages listed. Keep the guide's words: object type,
   attribute, record, sheet, column. No time estimates; add no image references.

Then run, in `guide/`: `GUIDE_OUT=_build/IMPORT-READINGS-GUIDE npm run build` and `npm run verify`.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/model/*.md`
- `src/content/docs/integrate/*.md`
- `src/content/docs/guide/integrate/*.md`

## Report

Each page changed with the sentences added or changed; differences between code and changelog; build and verify
results.
