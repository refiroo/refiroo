# First capture review

The supplied capture log is one run, repeated in the conversation. It is not evidence of repeated setup execution. Reviewed all 14 distinct attached images. Further local images are inspected separately below; files merely present on disk are not assumed to have passed.

## First correction unit

- Backup: actual no-rehearsal state; change recipe to that state. Run-page caption correction is outside this turn’s permitted page folders.
- Phone: drawer fills screen; workspace/context band is not in the image. Caption correction belongs to the use-page owner.
- Bulk field: exact model label is Height (m), not Height. Select its visible field-menu row. Preview footer has Back, not Cancel; Escape closes/cancels without applying.
- Bulk delete: local image shows the completed preview, so its failure was in the Cancel cleanup. Escape replaces that invalid cleanup. The image has no dependants: two stops, ten relationships to surviving records. Flag requested dependant coverage separately.
- Export results: viewed local image; the table has visible Type and Count headings, while Exported records and relationships is its accessible name. Pin the job shown by the setup image, avoiding a different newest Export.
- Next workbook: visible labels are Accept and Ignore. The check recognised the intended rename and new column; profile still Needs a fix, so loading is disabled.

## Interaction corrections

- Export choices: `ui/Choice.tsx` labels wrap radios; `styles/layout.css` sets their inputs to opacity 0 and pointer-events none. Click visible label text, including Columns per parent. This was an input hit-target error, not evidence that For people is absent.
- Relationship set: focus a selection checkbox before hovering the row. `ui/DataTable.tsx` and `ui/tableCell.ts` draw edit controls only for the active/focused row, and suppress hover shortly after scrolling. The exact label comes from `model/lookup.ts` and remains Served by mode.
- Hierarchy: `TreeView.tsx` opens its menu from `.tree-menu-trigger` or Shift+F10. Replace the row right-click with the node’s actual action trigger. Do not change the existing change set.
- Migration: `needsLoss = counts.loss && !blocked` in `MigrationPage.tsx`. The real preview is blocked (3 items), so there is no loss checkbox to locate. Keep this as a blocked-preview image and correct the page. Reduce the oversized review capture from 8500 to 2700 pixels.

## Page edits (only permitted sections)

- `guide/model/map-a-column.md`: removed capture-request wording, made mapping/value-map captions match the actual existing-attribute and unsaved replacement screens, and named Save the value map / Cancel.
- `guide/model/read-lists-in-a-sheet.md`: removed the nonexistent separate Lists control; the sheet itself shows detected list entries. Caption now says Proposed and marks the local-code demonstration fictional.
- `guide/model/migrate-a-workspace.md` and `model/migrations.md`: explain that blocking items hide loss acceptance and disable migration; changed the loss image caption to the actual blocked Removed view.
- The consumer-documents image matches its existing caption; no page change needed. Other attached successful screens are covered in the inspection table below.

All three setup entries now only reopen the state the first run created. They no longer create duplicates or replace the source file if someone runs the whole file again. Their original creation steps remain described in C10.data-changes.md.
