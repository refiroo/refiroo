# CANVAS-GUIDE-2 progress


- 2026-11-12T14:14:55+01:00 — Finished `guide/src/content/docs/guide/model/edit-a-model-on-the-canvas.md`: added when **Remove object type** appears, which workbook readings it removes, and when it also removes the draft type, checked against `menuFor` and `dropOperations`. No steering file exists; no uncertainty.

- 2026-11-12T14:15:11+01:00 — Finished checking `guide/src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md`: **Stop reading rows holding only this column as headings** already appears beside the heading-row instructions and matches the column menu, which restores those rows to ordinary reading. Kept the existing sentence unchanged; no steering file exists and no uncertainty.

- 2026-11-12T14:15:11+01:00 — Finished `guide/src/content/docs/guide/model/read-lists-in-a-sheet.md`: added the list panel’s default reporting choice, deletion confirmation, deletions in the load’s change set and how to stop future deletions. Checked `ListPanel`, `MissingRecords` and the eligibility helper; no steering file exists and no uncertainty.

- 2026-11-12T14:16:03+01:00 — Updated `guide/src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md`: the first verification found the existing heading-reversal label was missed by inventory coverage because it wrapped across lines. Kept its wording and placed the label on one line; no steering file exists. The initial build passed; verification is being rerun.

- 2026-11-12T14:16:26+01:00 — Validation finished: `GUIDE_OUT=_build/CANVAS-GUIDE-2 npm run build` passed; after the label reflow, `GUIDE_OUT=_build/CANVAS-GUIDE-2 npm run verify` passed, including its build, static checks, inventory, coverage and links (259 pages, zero uncovered entries). Logs are under `guide/_coverage/notes/CANVAS-GUIDE-2/`. No new screenshots are needed, no unresolved uncertainty remains, and no application defect was found.
