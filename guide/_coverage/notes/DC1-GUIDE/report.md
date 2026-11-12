# DC1-GUIDE completion

Six sentence corrections only; existing unrelated page edits were preserved. No screenshots, captions or image references were changed. No commits or state-changing git commands were run.

## Sentences

- `guide/src/content/docs/guide/use/add-a-record.md`
  - Before: The **New …** form opens beside the page on a desktop.
  - After: The **New …** form opens in the middle of the window on a desktop.
- `guide/src/content/docs/guide/use/correct-a-record.md`
  - Before: The form is titled with the record's name and opens beside the page on a desktop, with the current values.
  - After: The form is titled with the record's name and opens in the middle of the window on a desktop, with the current values.
- `guide/src/content/docs/guide/use/relate-records.md`
  - Before: The connection form opens beside the page on a desktop.
  - After: The connection form opens in the middle of the window on a desktop.
- `guide/src/content/docs/use/records.md`
  - Before: On a desktop, forms open as sheets beside the page; confirmations stay centred.
  - After: On a desktop, forms and confirmations open as dialogs in the middle of the window.
- `guide/src/content/docs/model/the-model-editor.md`
  - Before: Longer forms and forms needing a preview open beside the page as sheets.
  - After: Longer forms and forms needing a preview open as dialogs in the middle of the window on a desktop.
- `guide/src/content/docs/use/workspaces.md`
  - Before: **Cancel** closes the sheet and removes the draft made for the review.
  - After: **Cancel** closes the dialog and removes the draft made for the review.

## Evidence and limits

No differences found between the changelog's current dialog entry and the code. Screenshot findings are in `screenshots.md`: seven visually inspected pictures show right-edge forms; none were retaken. No live browser verification; remaining screenshots were not audited. No uncertainty about the six corrections or application defect found in the inspected code.

## Checks

- `GUIDE_OUT=_build/DC1-GUIDE npm run build`: passed, 257 pages.
- `GUIDE_OUT=_build/DC1-GUIDE npm run verify`: failed at coverage after its build, terms, brand, sidebar and inventory checks passed. Coverage reports 11 uncovered menu entries: one ModelEditor Open as canvas entry and ten WorkbookCanvas entries. These are outside the dialog-placement correction.
- `GUIDE_OUT=_build/DC1-GUIDE npm run check:links`: passed separately, 76,039 local links and sources across 257 pages.

Logs: `build.log`, `verify.log`, `links.log` in this folder. No DC1-GUIDE steering file was present before any unit or the final checks record.
