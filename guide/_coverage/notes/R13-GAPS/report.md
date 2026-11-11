# R13-GAPS report

## Entry mapping

Paths below are relative to guide/src/content/docs/. System operations have the system tag link and literal method/path; source-file operations have the source%20files tag link and literal method/path. The dynamic source-file ID is written as `{source_file_id}`.

| Inventory entry | Page and heading | Coverage mechanism |
| --- | --- | --- |
| GET /api/v1/system/processes | run/monitoring.md — Read the same figures as JSON / Engine processes | system tag and method/path |
| GET /api/v1/system/readiness | run/monitoring.md — Read the same figures as JSON / Workspace readiness | system tag and method/path |
| GET /api/v1/system/summary | run/monitoring.md — Read the same figures as JSON / Instance totals | system tag and method/path |
| GET /api/v1/system/backup-rehearsals | run/monitoring.md — Read the same figures as JSON / Backup rehearsals; run/backup-and-restore.md — Rehearse in a separate database | system tag and method/path, cross-link |
| POST /api/v1/source-files | integrate/files-imports-and-exports.md — Source files and their profile, step 1 | source files tag and method/path |
| GET /api/v1/source-files | same heading, step 2 | source files tag and method/path |
| GET /api/v1/source-files/{source_file_id} | same heading, step 2 | source files tag and method/path |
| GET /api/v1/source-files/{source_file_id}/profile/sheets | same heading, step 3 | source files tag and method/path |
| GET /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/columns | same heading, step 4 | source files tag and method/path |
| GET /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/cells | same heading, step 4 | source files tag and method/path |
| DELETE /api/v1/source-files/{source_file_id} | same heading, step 5 | source files tag and method/path |
| applications[].views[].config.fromColumns | model/applications-and-views.md — Relationships tables: columns and grouping; model/json-view.md — Relationships table configuration | full key in trace comment; visible specialist key and rules |
| applications[].views[].config.toColumns | same headings | full key in trace comment; visible specialist key and rules |
| applications[].views[].config.attributeColumns | same headings | full key in trace comment; visible specialist key and rules |
| applications[].views[].config.groupBy | same headings | full key in trace comment; visible specialist key and rules |
| operation:consumer-version-sunset | model/consumer-apis.md — Keep an earlier version available; guide/model/stop-serving-an-earlier-contract-version.md — Announce the end date | UNRESOLVED: registry defines dialog, rendered table retains inline editing and supplies no row menu. Pages document actual behavior; see sunset-discrepancy.md. |
| route:aiTask | use/jobs.md — Jobs grouped under a task or a draft | route trace comment, visible group behavior |
| route:modelDraft | same heading | route trace comment, visible group behavior |

Browser source-file coverage is in model/workbook-onboarding.md — Source file and draft; use/importing-and-exporting.md — Read a file through a profile and Remove an uploaded file or an import profile. The assistant page links to the jobs subsection. model/issues-and-dry-run.md contains no existing job-location statement and was left unchanged.

## Existing statements corrected or clarified

- Added Relationships table to the four-kind Views table and Add a view choices. Distinguished its Layout action from a collection table's Preview.
- Corrected the relationships-table guide's sort description to exclude JSON relationship attributes. Added its conceptual-page link.
- Clarified that source-file profiling is background work and is distinct from the saved import profile's mapping. The import-profile page reports the next-file comparison; it does not display the editor source pane.
- Added source retention, sharing and readiness refusals without implying replacement in one workspace replaces another workspace's file.
- Sunset pages retain the code-supported inline flow; clarified field/pencil, Not saved, unchanged saved value, dash on clearing and non-enforcement of the date. The requested change to dialog instructions was not made because that action is not connected to the rendered table.
- Jobs opening paragraph now scopes individual-job columns to All jobs. Assistant return path includes Data operations.

## Screenshots wanted

New placeholders:

1. /docs/screens/use-jobs-grouped.png — Settings > Data operations > Jobs, Grouped selected. Show an assistant-task row named after a reference workbook and a model-draft row, workspace, job counts, state counts, latest time, and Grouped / All jobs buttons.
2. /docs/screens/use-jobs-task-group.png — An assistant-task group, loaded with visible jobs. Show workbook heading, Assistant task and workspace eyebrow, Jobs trail, summary count/latest time, All and non-zero state buttons with counts, job table, Refresh and Open the task for an authorised reader.

Existing references retained: run-operations.png (process/workspace/rehearsal evidence); use-wb-editor.png and use-wb-evidence.png (source pane/statistics); model-add-relationships-table-layout.png (pair, columns, layout/grouping); model-consumer-earlier-versions.png (actual inline field and Stop serving). These images were not visually re-inspected in this wave. No screenshot of the unreachable sunset dialog is requested as a current task step.

## Validation

- GUIDE_OUT=_build/R13-GAPS npm run build: passes, 257 pages; final run recorded in build.log. Non-blocking warning: duplicate /404 route.
- node tools/check.mjs terms: passes after choosing A100:C120 as the example range; the checker misidentifies A3 and C12 as package IDs.
- node tools/check.mjs brand: passes.
- node tools/check.mjs sidebar: passes.
- git diff --check scoped to edited pages: passes.
- Coverage checker executed with its uncovered.md write redirected in memory to _coverage/notes/R13-GAPS/uncovered.md, leaving inventory and tooling unchanged: 1 uncovered of 1047, the sunset action. 17 of the wave's 18 entries now covered.
- GUIDE_OUT=_build/R13-GAPS node tools/check.mjs links: only the two requested screenshot placeholders are missing; no broken page/anchor links reported.

Code-backed documentation review only: no API calls, browser interactions or screenshot captures were performed. No application code changed. No commits or state-changing git commands.

## Product issue / uncertainty

The Set sunset day… operation exists but its Earlier versions table has no menu prop and no button for that action. Inline editing remains reachable. The wave's claimed dialog route cannot be verified in the current execution path. Backend behavior for empty dates, refused dates and continued service was verified in code. Do not claim the dialog inventory entry is covered until its real screen entry point is resolved.
