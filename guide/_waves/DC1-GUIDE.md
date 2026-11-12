# DC1-GUIDE: dialogs open in the middle of the window again

On 2026-11-12 the side sheet that 0.17 package UX1 had given every form was withdrawn (decision PP-D69 in
`docs/BASE_0_17_IMPLEMENTATION_PLAN.md`; `CHANGELOG.md` under `[Unreleased]`, the entry headed **0.17 UX1: dialogs
in the middle of the window**). The rules are in `frontend/src/styles/interactions.css` (first section) and
`frontend/src/styles/components.css` (`.dialog-backdrop`, `.dialog`); the component is `frontend/src/ui/Modal.tsx`.
Read them, then bring the guide in line. The code wins over the changelog; if they differ, write what the code
does and list the difference in your report.

## What is true now

- Every dialog (a form to add or edit a record, a relationship's form, a relation matrix cell's dialog, a bulk
  change, import and export, a new change set, a new workspace from a workbook, the forms in Settings and in the
  model editor, a confirmation) opens in the middle of the window on a desktop, over a dimmed page. It no longer
  opens beside the page, at the right edge, or as a "sheet".
- A long form scrolls inside the dialog; its buttons stay at the dialog's foot.
- On a phone a dialog fills the screen, as before.
- Unchanged, and to be left as written: a record opened beside its list on a desktop; a small edit that opens in a
  popover under its control; menus; notices; the filter editor that opens as a sheet from the bottom on a phone.

## What to do

1. Correct every sentence that says a form or dialog opens beside the page, at the side, or as a (side) sheet on
   a desktop. Known places (check for more with the searches below):
   - `src/content/docs/guide/use/add-a-record.md`: "The **New …** form opens beside the page on a desktop."
   - `src/content/docs/guide/use/correct-a-record.md`: "… opens beside the page on a desktop, with the current values."
   - `src/content/docs/guide/use/relate-records.md`: "The connection form opens beside the page on a desktop."
   - `src/content/docs/use/records.md`: the sentence about where the add form opens (near "More fields (n)").
   - `src/content/docs/model/the-model-editor.md`: "Longer forms and forms needing a preview open beside the page
     as sheets."
2. Change only what is wrong. Do not restructure pages, do not rewrite correct text, do not touch screenshots,
   their file names or their captions' file references. If a caption's words say a form is beside the page or a
   sheet, correct those words only.
3. Keep the guide's voice and its words; no time estimates.
4. Then run, in `guide/`: `GUIDE_OUT=_build/DC1-GUIDE npm run build` and `npm run verify`.

## How to find the sentences

Search `src/content/docs` for: `beside the page`, `side sheet`, `as sheets`, `as a sheet`, `sheet` (only where it
means a form or dialog, never a workbook's sheet or the phone's filter sheet), `at the right`, `slides in`,
`beside the list` (only where it is a form, not a record).

## Files you may edit

- `src/content/docs/use/*.md`
- `src/content/docs/use/*.mdx`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/use/*.mdx`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/guide/model/*.mdx`
- `src/content/docs/model/*.md`
- `src/content/docs/model/*.mdx`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/guide/administer/*.mdx`
- `src/content/docs/administer/*.md`
- `src/content/docs/administer/*.mdx`
- `src/content/docs/journeys/*.md`
- `src/content/docs/about/*.md`

## Report

- Each page changed, with the sentences before and after in one line each.
- Differences you found between the changelog and the code.
- Screenshots whose picture shows a form as a side sheet at the right edge, if you can tell from the captions or
  the screens files (file name and what it shows): list only, do not retake.
- The result of the build and of `npm run verify`.
