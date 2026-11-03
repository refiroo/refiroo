# C10 first capture review and recapture handoff

Reviewed the 14 distinct attached images. Repeated user messages carry the same capture log, not evidence of repeated setup runs.

## Image inspection

| Attached image | Finding |
| --- | --- |
| appearance-display-choices | All four choice groups visible; current page caption matches. |
| phone-navigation-drawer | Drawer fills the viewport; collections and record search visible, workspace/context band hidden. Use-page caption correction needed below. |
| run-deployment | Groups, limits, database revision and effective Runtime settings visible; current caption matches. |
| run-operations | Three workspaces served, one live process, threads and pool use visible; no rehearsal recorded. Current monitoring caption matches. |
| list-position-and-seek | Page 3, range 51–64 of 2,443, Go to name and start/end controls visible; requested state achieved. |
| new-record-required-connections | New Name translation, Parent, Translates, Name, Translated name, Active and disabled Create visible; requested empty form achieved. |
| model-workbook-map-column | Existing integer attribute selected, not the new-attribute value-type form; caption corrected. |
| model-workbook-value-map | Unsaved J → true entry and empty placeholder replacements visible; caption corrected. |
| model-workbook-list-range | Proposed fictional-code list and shaded range visible. Proposal uses header row 1 although column headings appear at row 3; guide explicitly instructs reviewing Adjust list… before loading. |
| c10-setup-hierarchy-change-set | Dedicated version-1 change set open and unpublished; UUID not shown. |
| c10-setup-export | Completed export UUID and 1,657 items visible. A waiting 2-item Batch also appears; do not treat its preview counts as applied data. |
| c10-setup-next-workbook | Upload/check succeeded: New/Renamed columns, Accept/Ignore, Needs a fix and disabled loading. Lower missing-record controls are outside this 1400px image. |
| model-migration-review | Missing choices and outcomes present, but huge blank area makes it unsuitable. Retake at 2700px rather than 8500px. |
| model-consumer-active-documents | Active release, Stops API v1, base/document addresses and routes visible; caption matches. |

Also inspected local failed-capture files bulk-delete-impact, job-results-and-file, model-migration-loss-confirm and import-profile-next-version. The latter 2000px image includes When loading / Keep the missing records. Older export-dialog-collection and bulk-change-values-field images were supplementary source-label evidence, not this run’s passing screenshots.

## Failed-entry corrections

| Entry | Correction |
| --- | --- |
| run-backup-rehearsal | Expect the actual No backup has been rehearsed state; no restore manufactured. |
| bulk-selection-preview | Height (m), visible field-menu row; Escape cancels/closes after the preview. |
| bulk-delete-impact | Image shows preview succeeded; failure was nonexistent Cancel cleanup. Footer offers Back and Delete 2 records. Escape closes/cancels without deletion. |
| export-for-people | Click the visible For people label; Choice radios have opacity 0 and pointer-events none. |
| workbook-columns-per-parent | Same label hit-target correction for For people and Columns per parent. |
| replace-related-records | Focus the row via its selection checkbox, wait out scroll suppression and hover it before clicking its mounted edit control. Selection is local browser state. |
| hierarchy-restructure-plan | Hover Road and click its Actions trigger; TreeView opens its menu from that trigger or Shift+F10, not a plain row right-click. |
| job-results-and-file | Pin the created export UUID; check Exported records and relationships as an accessible group name and Type/Count as visible headings. |
| import-profile-next-version | Actual buttons are Accept and Ignore. No profile corrections or load confirmed. |
| model-migration-loss-confirm | Three blockers hide the acceptance checkbox. Capture blocked Removed rows and disabled migration; caption and explanation corrected. |

Source evidence: FieldMenu/BulkChangeDialog/BulkJobDialog, Choice and styles/layout.css, DataTable/tableCell/EditInPlace/useCellEditing, TreeView/AnchoredMenu, JobPage/SettingsTable, ProfileCheckReport and MigrationPage. All three setup entries now reopen existing state; they no longer create/upload again.

## Page edits in permitted folders

- guide/model/map-a-column.md: actual mapping/value-map captions, removed capture-request wording, named Save the value map and Cancel.
- guide/model/read-lists-in-a-sheet.md: removed nonexistent separate Lists control; corrected proposed-list caption and explained the observed header-row discrepancy.
- guide/model/migrate-a-workspace.md and model/migrations.md: blockers hide acceptance and disable migration; loss image caption describes the actual blocked state.

## Needed changes outside permitted folders

1. **use/appearance-and-devices.md:** replace the phone caption with “Phone application navigation drawer with collections and record search”. Its image does not show the workspace/context band. Keep the explanation of the band for the closed-drawer state.
2. **guide/use/load-the-next-version-of-a-workbook.md:** step 3 and image caption must say **Accept** on a Renamed row and **Ignore** on a New row, not Accept rename / Ignore new column. Explain that the pictured Needs a fix keeps Load into a change set… disabled. Use the same labels wherever use/importing-and-exporting.md describes these controls.
3. **guide/use/delete-many-records.md:** the pictured two stops have no dependants. Suggested caption: “Delete preview for two stops, showing ten relationships to surviving records and the Delete 2 records action”. A separate parent-record preview is needed to illustrate dependent child records.

Current run/backup-and-restore.md already captions the no-rehearsal state, use/jobs.md already captions the completed export correctly, and bulk instructions already name Back. These concurrent owner edits were preserved. No additional integrate/ or administer/ discrepancy was found in the supplied captures; those sections were not audited in full.

## Recapture

Retake the ten failed entries plus the oversized successful review:

`run-backup-rehearsal,bulk-selection-preview,bulk-delete-impact,export-for-people,workbook-columns-per-parent,replace-related-records,hierarchy-restructure-plan,job-results-and-file,import-profile-next-version,model-migration-loss-confirm,model-migration-review`

Setup entries need not run again. The seven earlier excluded images remain excluded: historical language recovery/unavailable workspace, stale migration confirmation, Contributor access, configured email digest, simultaneous queued/running job states and a For people import fixture.

## Limits and observations

No live recapture or instance mutation ran in this correction turn. Revised locators remain pending external verification. A proposed workbook header is visibly questionable; no draft step was applied to correct it. No code fix, access/security change, deletion, release activation or migration confirmation was performed. The original bulk-delete preview may still be waiting because its cleanup failed; the corrected cleanup applies to future captures and does not retroactively cancel that job.
