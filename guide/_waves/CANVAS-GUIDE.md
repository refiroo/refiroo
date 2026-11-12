# CANVAS-GUIDE: the model draft canvas

On 2026-11-12 the model editor gained a second view of the same model draft: the **canvas** (0.17 packages
**PL3b**, the workbook canvas, and **CE1**, the canvas edits the whole model). What it does is written in
`CHANGELOG.md` under `[Unreleased]` (the entries headed **0.17 PL3b** and **0.17 CE1**, and the Fixed entries for
them) and in `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, sections **PL3b: The workbook canvas** (with its table
"Gestures and what each one uses") and **CE1: The canvas edits the whole model** (with its state notes). Read
both, then the code: `frontend/src/features/workbook-canvas/` (`WorkbookCanvas.tsx`, `CanvasBoard.tsx`,
`BoardCard.tsx`, `CanvasInspector.tsx`, `LinePopover.tsx`, `WorkbookPane.tsx`, `canvasModel.ts`, `canvasView.ts`),
the shared pieces it mounts from `frontend/src/features/model-editor/` (`AddMenu.tsx`, `DraftViewSwitch.tsx`,
`IssuesDrawer.tsx`, `operations.ts`), and `frontend/src/features/workspaces/NewFromWorkbook.tsx` (Adjust). The code
wins over the changelog and the plan; where they differ, write what the code does and list the difference in your
report.

## Words

The canvas uses the model editor's words: **object type**, **attribute**, **relationship**, **application**,
**navigation group**. A workbook has **sheets** and **columns**. Use the labels exactly as the interface writes
them (for example the **+** Add menu with **Object type…** and **Application…**, **Connect**, **Tidy**, **Move to…**,
**Move up**, **Move down**, **New attribute**, **Propose again…**, **Create workspace…**, **Install and activate…**,
**Editor** and **Canvas**). Do not call an object type a "list" or an attribute a "field".

## What to write

1. **A new how-to page** `src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md`: for a person who has
   never seen it. Opening it (New workspace from a workbook → **Adjust**, or the **Editor | Canvas** switch on a
   draft with a workbook). The three parts of the page. Every gesture of the plan's table, each with its result
   and its menu or keyboard way: a sheet onto the board, a column onto an object type or an attribute, a column
   onto the empty board, **Connect** onto an object type (under it) or onto an attribute (a relationship) and what
   happens when two columns could join, several columns read as rows, a column onto a filter, an object type onto
   a navigation group, an attribute back onto the workbook, an attribute onto another object type, an attribute
   up or down within its object type. The sheet preview: the header row, blanks filled from the cell above,
   heading rows. The row count: what loads and what is refused, opening the refused rows and correcting a value.
   Undo and redo. Finishing: **Create workspace…**, and the other finishes the code offers. Phone width.
2. **A new how-to page** `src/content/docs/guide/model/edit-a-model-on-the-canvas.md`: any draft, with or without
   a workbook. The **Editor | Canvas** switch and which view a draft opens in. What the board shows (the scope
   switch, the frame per application, marks such as New and Changed, folding, Find, zoom and Fit, **Tidy**).
   Adding with the **+** Add menu. Renaming where the name stands. Every element's menu (the same as the model
   editor's), right-click and Shift+F10. The inspector's tabs (Inspector, Navigation, Views, Consumer APIs) and
   that they are the model editor's own panels. A relationship line and its rule. Issues, history and dry run at
   the foot. The draft's actions. What the canvas does not do and where that is (say it in one or two sentences,
   from the code; for example card positions are not part of the model).
3. **Sidebar**: add both pages to `sidebar/model.mjs` next to the related pages
   (`guide/model/find-your-way-around-the-editor`, `guide/model/read-lists-in-a-sheet`), in the file's own style.
4. **Correct what the canvas made wrong elsewhere**, briefly, where a reader would look: the page that describes
   New workspace from a workbook (its **Adjust** now opens the canvas), `find-your-way-around-the-editor.md` (the
   **Editor | Canvas** switch; the **+** Add menu), the pages about mapping columns and reading sheets (one
   sentence each pointing to the canvas where it does the same by dragging), and `src/content/docs/model/*.md`
   overview pages that list the ways to build a model. Change only what is wrong or incomplete; do not
   restructure pages or rewrite correct text.
5. **Screenshots**: add no image references (the reference instance does not hold the states yet). List, in your
   report, the screenshots each new page needs (what the picture shows, at 1440 wide).

Check each fact against the code before you write it. Keep the guide's voice; no time estimates.

Then run, in `guide/`: `GUIDE_OUT=_build/CANVAS-GUIDE npm run build` and `npm run verify`.

## Files you may edit

- `src/content/docs/guide/model/*.md`
- `src/content/docs/guide/model/*.mdx`
- `src/content/docs/model/*.md`
- `src/content/docs/model/*.mdx`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/use/*.md`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/journeys/*.md`
- `sidebar/model.mjs`

## Report

- The two new pages (their headings), and each other page changed with the sentences before and after.
- Differences between the code and the changelog or the plan.
- The screenshots each new page needs.
- The result of the build and of `npm run verify`.
