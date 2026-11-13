
## 2026-11-11T12:23:26+01:00 — guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md
Added create-or-reuse steps for filled cells, shared-record effects, container choice and change-set conflict resolution. Checked dialog and projection code; no steering file was present. Existing screenshots do not show the new filled-cell Create action.

## 2026-11-11T12:24:05+01:00 — guide/src/content/docs/use/relation-matrices.md
Explained filled-cell actions, shared identity, cardinality versus counting conflicts, and workbook limits. Checked holdsOne and projection state rules; browser appearance remains unverified. No steering file was present.

## 2026-11-11T12:24:05+01:00 — guide/src/content/docs/guide/model/add-a-relation-matrix.md
Added the Change… route, each action and the exact conditions that remove editor choices. Checked actionOptions and followMatrix; release link will be checked by the build. No steering file was present.

## 2026-11-11T12:24:05+01:00 — guide/src/content/docs/model/applications-and-views.md
Documented per-view action rules and their effects without duplicating the task steps. Checked editor action conditions and runtime create gating; existing model screenshot may need recapture for the action choices. No steering file was present.

## 2026-11-11T12:24:52+01:00 — guide/src/content/docs/guide/use/export-records.md
Rewrote export steps around What, counts and context, per-view file kinds, matrix containers and the About sheet. Checked ExportDialog, exportRequest and export writers; no steering file was present. The existing export picture needs a current capture with This view and matrix containers.

## 2026-11-11T12:25:44+01:00 — guide/src/content/docs/guide/use/edit-in-excel-and-import-back.md
Added per-layout editing steps and matrix blank, container, shared-record and link-list rules. Checked matrix_sheets and grid_sheets; several-record field cells are skipped, but link-list cells do load lists, so the text distinguishes them. No steering file was present.

## 2026-11-11T12:26:18+01:00 — guide/src/content/docs/use/importing-and-exporting.md
Added a layout comparison, view scope/counts, About sheet, container suggestions and precise matrix versus table round-trip rules. Checked API contract and writers, including owned relationship summaries; no steering file was present. No runtime workbook import was exercised.

## 2026-11-11T12:26:38+01:00 — guide/src/content/docs/integrate/relationships-and-their-values.md
Explained shared IDs, separate connection values, unlink/feed effects and consumer publication visibility. Checked API feed contract and existing consumer wording; consumer exposure remains conditional on declarations and grants. No steering file was present.

## 2026-11-11T12:27:03+01:00 — guide/src/content/docs/integrate/files-imports-and-exports.md
Added the view export sequence, newCellContainers and suggestedContainerId, file metadata and matrix round-trip distinctions, linking operation details to the reference. Checked API.md and writers; no steering file was present. All nine assigned pages are now saved; build and link review remain.

## 2026-11-11T12:27:54+01:00 — final source and link review
Corrected the release-page link and matrix API tag, checked the nine-page diff and saved evidence plus screenshot requirements under _coverage/notes/MC1-GUIDE/evidence.md. No steering file was present. Next is the isolated GUIDE_OUT build.

## 2026-11-11T12:29:09+01:00 — export container precision review
Build passed (257 pages), static checks passed and local-link checks passed. A final source check found dialog container suggestions ignore row search/filters, whereas omitted API choices fall back from exported cells; corrected export-records, importing-and-exporting and files-imports-and-exports and recorded the discrepancy. No steering file was present. Rebuilding after these wording changes.

## 2026-11-11T12:29:37+01:00 — completed validation and handoff
Final `GUIDE_OUT=_build/MC1-GUIDE npm run build` passed, 257 pages in 2.89 seconds; log: `_coverage/notes/MC1-GUIDE/build.log`. `npm run check` passed terms, brand and sidebar; `GUIDE_OUT=_build/MC1-GUIDE npm run check:links` passed 75,914 local links/sources; final scoped `git diff --check` passed. The final wording changes introduced no new links or terminology requiring another run of those checks. Build emitted a /404 route-conflict warning but completed successfully.
All nine assigned pages are complete. Source-based checks only: browser states, new screenshots, sample-file spreadsheet round trips and runtime reproduction of the container-suggestion discrepancy remain unverified. Evidence, screenshot specifications and the discrepancy are recorded in `_coverage/notes/MC1-GUIDE/evidence.md`. No steering file appeared, no commits or git state changes were made, and no application code was edited.

## 2026-11-11T15:24:28+01:00 — guide/src/content/docs/guide/use/fill-in-a-relation-matrix.md
Updated creation steps for rule-based placement, busiest used group and editable group proposals; checked CreateCellRecord and candidate_places. New proposal screenshot needs capture. No steering file was present.

## 2026-11-11T15:24:28+01:00 — guide/src/content/docs/use/relation-matrices.md
Updated placement rules and proposals, and distinguished several-record field cells from link workbooks. Source checked; browser appearance unverified. No steering file was present.

## 2026-11-11T15:24:28+01:00 — guide/src/content/docs/guide/model/add-a-relation-matrix.md
Updated Create guidance for placement without a model default setting; retained verified actionOptions restrictions and Change… steps. No steering file was present.

## 2026-11-11T15:24:28+01:00 — guide/src/content/docs/model/applications-and-views.md
Updated matrix creation concepts for derived and proposed places; action configuration is unchanged. Checked editor actionOptions and creation form. No steering file was present.

## 2026-11-11T15:25:20+01:00 — guide/src/content/docs/guide/use/export-records.md
Removed obsolete export container choices and added What each cell lists, text-field selection, recorded reading and value sheets. Checked ExportDialog and matrix_sheets; export screenshot needs refresh. No steering file was present.

## 2026-11-11T15:25:20+01:00 — guide/src/content/docs/guide/use/edit-in-excel-and-import-back.md
Updated round-trip steps for value sheets, shared identity, free-typed values and automatic placement; added reading-preview review. Checked writer and binding/API contracts; no real spreadsheet round trip performed. No steering file was present.

## 2026-11-11T15:25:20+01:00 — guide/src/content/docs/use/importing-and-exporting.md
Replaced obsolete export placement with current rule/data/proposal behavior; added value-sheet and matching-field rules and preview concepts. Checked candidate_places, matrix_sheets, ImportOutcome and API; runtime spreadsheet behavior remains unverified. No steering file was present.

## 2026-11-11T15:26:03+01:00 — guide/src/content/docs/guide/use/import-a-file.md
Added step-by-step How the file is read checks, re-preview, profile saving, value-sheet counts and proposed group confirmation. Labels checked in ImportOutcome; new screenshot needed. No steering file was present.

## 2026-11-11T15:26:03+01:00 — guide/src/content/docs/integrate/relationships-and-their-values.md
Updated matrix placement and atomic group creation while retaining shared IDs, per-connection values, unlink feed and consumer publication semantics. Checked candidate_places and API; no consumer runtime test. No steering file was present.

## 2026-11-11T15:26:03+01:00 — guide/src/content/docs/integrate/files-imports-and-exports.md
Updated API narrative for cellField, derivedPlace/cellCount, atomic placement, value sheets and reread. Removed superseded container fields; checked API and binding implementation. Runtime imports remain unexercised. No steering file was present.

## 2026-11-11T15:27:02+01:00 — precision review: guide/src/content/docs/guide/use/edit-in-excel-and-import-back.md
Clarified that only the main matrix sheet ignores row-label changes; value sheets load separately. Tightened placement or editing wording where applicable. No steering file was present.

## 2026-11-11T15:27:02+01:00 — precision review: guide/src/content/docs/use/importing-and-exporting.md
Clarified that only the main matrix sheet ignores row-label changes; value sheets load separately. Tightened placement or editing wording where applicable. No steering file was present.

## 2026-11-11T15:27:02+01:00 — precision review: guide/src/content/docs/use/relation-matrices.md
Clarified that only the main matrix sheet ignores row-label changes; value sheets load separately. Tightened placement or editing wording where applicable. No steering file was present.

## 2026-11-11T15:27:02+01:00 — precision review: guide/src/content/docs/integrate/files-imports-and-exports.md
Clarified that only the main matrix sheet ignores row-label changes; value sheets load separately. Tightened placement or editing wording where applicable. No steering file was present.

## 2026-11-11T15:28:12+01:00 — second-wave validation and handoff
All ten pages are complete. Final isolated build passed (257 pages); terms/brand/sidebar passed. Link checks found only two requested screenshot placeholders (three references), outside the allowed asset files. Replaced evidence.md with current source checks, screenshot requests, limits and a source-only tie-message concern; old export-container discrepancy is superseded. No steering file appeared; no commits or git state changes.
