# MC1 guide: second-wave handoff

Continued the saved first-wave work. Read guide/AGENTS.md first and the wave brief second. Top-level instructions excluded. No steering file appeared. Only the ten assigned pages, assigned progress and this notes directory were edited; no git state changes or commits.

## Sources

Checked RelationMatrixCellDialog.tsx (holdsOne, actions, CreateCellRecord); model-editor/matrixView.ts (actionOptions); jobs/ExportDialog.tsx and exportRequest.ts (view scope, fields); jobs/ImportOutcome.tsx (reading, counts, reread and profile save); engine/model/candidate_places.py; imports/places.py and binding.py; jobs/matrix_sheets.py; reads/matrix_read.py; docs/API.md (view export, cellField, value sheets, reading, reread and containers). Also checked CURRENT_FUNCTIONALITY.md current EX1/MC1 sections, USER_JOURNEYS.md J27.24/25/27/28 and product-functionality/GLOSSARY.md.

## Precision

Main matrix sheets ignore row-label edits; value sheets load records separately. Several-record field cells are skipped; link cells accept non-empty lists. Cleared matrix cells do nothing. Link/Unlink-only value sheets do not load; Edit or Create allows updates and Create allows new rows. JSON fields are omitted. Unselected rows still load. Record identities survive renames; ambiguous matching values refuse import. Required fields still apply to typed new values.

Placement uses candidate rules, then busiest used group (no default on ties or zero usage), then a compatible group proposal. Rule-fixed places are the exception to zero-usage selection. Proposed names are editable without model changes. Export container maps and suggestedContainerId are superseded; the first-wave container-suggestion discrepancy no longer describes current code.

## Pictures needed

Capture only the reference instance and guide data. No visual appearance was verified in this run.

1. NEW matrix-proposed-group.png: creation form, proposed group's editable name, row/column, record fields, submit, and Use an existing group instead. Used by fill-in-a-relation-matrix.
2. NEW matrix-import-reading.png: How the file is read, matching-field selector, matches, value-sheet update/new counts, will create ... under ..., and Load the file. Used by edit-in-excel-and-import-back and import-a-file. Another state should show Guessed, an uncertainty note and Save these fields in the profile.
3. REFRESH export-for-people.png: This view, matrix count/context, spreadsheet kind, What each cell lists and selector. No container section. Used by export-records.
4. Filled several-record cell with Create and Link existing together; candidate chooser with eligible reuse and disabled candidate reason. For fill-in-a-relation-matrix and relation-matrices.
5. Filled one-per-cell dialog without Create; change-set Conflict with count and two counting records. Same pages.
6. REFRESH model-view-matrix-dialog.png / model-matrix-view-dialog.png: Change... with What people can do in a cell; required-relationship configuration with Unlink absent. For both model pages.
7. Workbook main sheet, Values sheet with record fields/group and hidden IDs retained, and About this export second; record-field layout without value sheets. For spreadsheet guide and importing-and-exporting.
8. Import refusal naming the column and why no place is available. For spreadsheet/import guides. Replaces obsolete export-container omission screenshot request.

## Checks and limitations

Second-wave logs are in this directory. Isolated GUIDE_OUT build passed, 257 pages. Terms, brand and sidebar checks passed. Link check found only two new missing screenshot files, at three references. Scoped diff whitespace check passed before final prose precision changes; final check recorded in progress.

No browser, spreadsheet application, workbook round trip, application tests or consumer runtime test. Dropdown appearance in Excel and Numbers is deliberately unclaimed. Screenshot refreshes remain outstanding.

No runtime product defect established. Source-only concern: CreateCellRecord's no-default message says no group holds cells even when a tied busiest count can leave no default. Not reproduced; no application code changed.
