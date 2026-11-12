# PL4-GUIDE: a workspace from a workbook

On 2026-11-12 the application gained one step that turns a workbook into a workspace (0.17 PL4). What it does is
written in `CHANGELOG.md` under `[Unreleased]`, entry **Added (0.17 PL4: a workspace from a workbook)**, and
decided in `docs/BASE_0_17_IMPLEMENTATION_PLAN.md` (PP-D44 to PP-D47). Read those, then the code:
`frontend/src/features/workspaces/NewFromWorkbook.tsx`, `NewFromWorkbookAction.tsx`, `fromWorkbook.ts`,
`WorkspaceLoad.tsx`, and the route in `backend/app/management/routers/workspaces.py` with its reference text in
`backend/app/management/reference/content/workspaces.md`. The code wins over this page and the changelog.

## What to write

1. On the page where a reader looks for making a workspace (the workspaces page of the use or administer
   section, whichever describes New workspace today), add a short section **A workspace from a workbook**:
   where the action is (Home beside "Your workspaces", Settings › Workspaces, a workspace's page), who sees it,
   the two steps (the file and a name; then "What refiroo found" with every row checked), what **Create
   workspace**, **Adjust**, **Cancel** and **More ways to start** do, and what the new workspace's page shows
   while and after the workbook loads (the counts, the rows that did not load, See the rows, Dismiss).
2. On the page where importing a workbook into an existing workspace is described, one sentence that points to
   the new section for a workbook that should become a workspace of its own.
3. On the integration page that lists workspace operations, if one exists, one or two sentences on
   `POST /api/v1/workspaces/from-workbook`: what it takes, what it answers, that a clash of version or profile
   key never refuses, and where the errors are listed. Do not copy the reference.

Do not touch screenshots or their file names; add no image reference. Change nothing else.
Then run `GUIDE_OUT=_build/PL4-GUIDE npm run build` and `npm run check:coverage` in `guide/`.

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/use/*.mdx`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/administer/*.md`
- `src/content/docs/guide/integrate/*.md`
- `src/content/docs/integrate/*.md`
- `src/content/docs/journeys/*.md`

## Report

The pages changed with the text added; anything where the code differs from the changelog.
