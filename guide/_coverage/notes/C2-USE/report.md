# C2-USE completion report

Resumed the existing wave pages, finished remaining steward explanations, corrected source-checked
labels and permissions, reconciled the coverage register and verified the isolated site build.
Only allowed source pages, the coverage/capture/progress files and C2-USE working notes were edited.
No commits or state-changing Git commands were run.

## Pages delivered

The wave contains 19 documentation pages and 38 task guides, all represented exactly once in
`sidebar/use.mjs`. This list includes pages completed by the earlier run; the progress file
identifies continuation edits separately.

### use

- `use/account.md` — Your account
- `use/appearance-and-devices.md` — Appearance and devices
- `use/applications.md` — Applications
- `use/change-sets.md` — Change sets
- `use/changing-many-records.md` — Changing many records
- `use/hierarchies.md` — Hierarchies
- `use/history.md` — History
- `use/home.md` — Home
- `use/importing-and-exporting.md` — Importing and exporting
- `use/inbox-and-approvals.md` — Inbox and approvals
- `use/jobs.md` — Jobs
- `use/lists-and-filters.md` — Lists, search and filters
- `use/mapping-grids.md` — Mapping grids
- `use/notifications-settings.md` — Notification settings
- `use/publications.md` — Publications
- `use/records.md` — Records
- `use/relation-matrices.md` — Relation matrices
- `use/relationships.md` — Relationships
- `use/workspaces.md` — Workspaces

### guide/use

- `guide/use/add-a-language-with-a-workbook.md` — Add a language with a workbook
- `guide/use/add-a-record.md` — Add a record
- `guide/use/approve-a-change-set.md` — Approve a change set
- `guide/use/arrange-records-in-a-tree.md` — Arrange records in a tree
- `guide/use/browse-a-publication.md` — Browse a publication
- `guide/use/change-how-refiroo-looks.md` — Change how refiroo looks
- `guide/use/change-relationships-of-many-records.md` — Change relationships of many records
- `guide/use/change-values-of-many-records.md` — Change values of many records
- `guide/use/continue-a-long-list.md` — Continue a long list
- `guide/use/continue-live-work-while-a-change-set-is-open.md` — Continue live work while a change set is open
- `guide/use/correct-a-record.md` — Correct a record
- `guide/use/delete-a-record.md` — Delete a record
- `guide/use/delete-many-records.md` — Delete many records
- `guide/use/edit-in-excel-and-import-back.md` — Edit in Excel and import back
- `guide/use/export-records.md` — Export records
- `guide/use/fill-in-a-relation-matrix.md` — Fill in a relation matrix
- `guide/use/find-records.md` — Find records
- `guide/use/follow-a-workspace.md` — Follow a workspace
- `guide/use/follow-and-cancel-a-job.md` — Follow and cancel a job
- `guide/use/import-a-file.md` — Import a file
- `guide/use/load-the-next-version-of-a-workbook.md` — Load the next version of a workbook
- `guide/use/map-codes-between-systems.md` — Map codes between systems
- `guide/use/move-several-records-together.md` — Move several records together
- `guide/use/open-a-retired-or-unavailable-workspace.md` — Open a retired or unavailable workspace
- `guide/use/open-an-application.md` — Open an application
- `guide/use/prepare-and-publish-a-change-set.md` — Prepare and publish a change set
- `guide/use/prepare-under-the-next-model-version.md` — Prepare under the next model version
- `guide/use/propose-a-change.md` — Propose a change
- `guide/use/relate-records.md` — Relate records
- `guide/use/replace-a-records-related-records.md` — Replace a record’s related records
- `guide/use/reshape-a-hierarchy.md` — Reshape a hierarchy
- `guide/use/review-what-a-change-set-changes.md` — Review what a change set changes
- `guide/use/see-who-changed-what.md` — See who changed what
- `guide/use/set-up-email-notices.md` — Set up email notices
- `guide/use/start-from-an-earlier-publication.md` — Start from an earlier publication
- `guide/use/stop-offering-a-value.md` — Stop offering a value
- `guide/use/switch-workspace.md` — Switch workspace
- `guide/use/withdraw-a-publication.md` — Withdraw a publication

## Coverage and handoffs

All 917 rows have a destination, an explicit deferral or an internal-only explanation. No ordinary
steward row remains labelled uncovered or partly. 185 AI rows remain deferred under the wave rules
(139 existing deferrals retained, 46 additional assistant/AI evidence rows recognised).
Seven other-reader-only rows are handoffs, not claims of completed work in those sections:
C0093 (people import/invitations), C0927 (workbook model inference), C0994 (client notification
limits), C1046 (business-period contract), C1059 (workspace/release deletion), C1067 (cross-workspace
stored-data repair) and C1199 (declared relationship fields). Full destinations and per-row
resolutions are in `coverage-resolution.md`; other-reader parts of shared rows remain assigned
to their section waves. Model authoring, workspace administration and approval-policy setup are
short links from Use, rather than instructions for a steward to administer them.

## Screenshots

Sixteen pending captures are listed below with their page and required state. The existing
`record-delete-impact.png` is reused; its capture request is already satisfied. These placeholders
are intentionally retained as the writing instructions require. No replacement images were invented.

| File | Page | Screen, state and required visible details |
|---|---|---|
| list-position-and-seek.png | guide/use/continue-a-long-list | A collection footer with range, total, Page, Go to and start/end controls; a noninitial position is loaded. |
| bulk-selection-preview.png | use/changing-many-records | Selected rows and selection bar, followed by a Change values preview with changed, unchanged and refused counts and Apply. |
| bulk-delete-impact.png | guide/use/delete-many-records | Delete preview showing selected records, dependants by type, relationships to surviving records and the total on the confirmation button. |
| import-preview-columns.png | use/importing-and-exporting | Import job awaiting confirmation, Read as exported summary, counts, column report, a refused row with failing cells, Load the file and Cancel import. |
| job-results-and-file.png | use/jobs | Completed export job showing state, requester, Kept until, counts, file size, checksum and Download; no sensitive content. |
| export-for-people.png | guide/use/export-records | Export opened from a filtered collection; Kind of file For people, scope summary, Advanced columns and sheets and Start export. |
| workbook-columns-per-parent.png | guide/use/add-a-language-with-a-workbook | For people Advanced layout with Columns per parent, owned fields and an additional selected parent; capture workbook headings separately if useful. |
| import-profile-next-version.png | guide/use/load-the-next-version-of-a-workbook | Import profile after a next-version check, column differences with Accept rename and Ignore new column, missing-record choice and Load into a change set. |
| notification-email-digest.png | use/notifications-settings | Notification email with the master switch on, mixed At once/Digest/Off choices, saved time zone, next digest and followed workspace with Stop following. |
| appearance-display-choices.png | use/appearance-and-devices | Appearance Display section with Theme, Table density, Type colours and Edit pencil; capture phone navigation band and drawer as a separate view. |
| new-record-required-connections.png | guide/use/add-a-record | New record form with name, typed fields, required parent and relationship, Create and a visible context. |
| record-delete-impact.png | guide/use/delete-a-record | Single-record deletion impact showing dependent names/types, relationships removed, independent connections retained and Confirm deletion. |
| contributor-propose-change.png | guide/use/propose-a-change | Contributor Live band and Propose a change dialog with Change set name, explanatory text and Start and edit; no Live edit controls. |
| replace-related-records.png | guide/use/replace-a-records-related-records | Multi-valued relationship dialog with pinned checked records, count, searched unchecked candidate and Save. |
| hierarchy-restructure-plan.png | guide/use/reshape-a-hierarchy | Restructure dialog with new type, plan counts, records needing input, values without a place and Apply to the change set. |
| workspace-cannot-open.png | guide/use/open-a-retired-or-unavailable-workspace | Unavailable workspace page with its precise reason, unaffected-workspace explanation and administrator recovery card; no invented record data. |
| phone-navigation-drawer.png | use/appearance-and-devices | 390px phone layout with the application navigation drawer open, workspace/application/context band visible, close control and collection labels readable. |

`record-delete-impact.png` already exists in `public/screens/` and is reused by the single-record deletion guide. The other 16 names above are pending captures. No screenshots were fabricated or generated for this wave.

## Checks actually run

- `GUIDE_OUT=_build/C2-USE npm run build` in `guide/`: PASS; 200 built pages in 2.55 seconds.
- `npm run check`: PASS; terminology and brand checks over 199 source pages.
- Sidebar/file comparison: PASS; 57 section pages, 57 entries, none missing or duplicated.
- Coverage resolution/link-existence check: PASS; 917 rows, no uncovered/partly marker and all
  referenced content files present.
- `GUIDE_OUT=_build/C2-USE npm run verify` was attempted before the final edits: build and
  static checks passed; the local-link stage failed. Final build, static and link checks were
  then run individually after the final page changes.
- Final `GUIDE_OUT=_build/C2-USE npm run check:links`: FAIL; 34 missing-target reports. Sixteen
  are this wave's requested, not-yet-captured screenshots; eighteen are outside this wave.
  No missing page or anchor is reported from a Use page. The complete bounded output is in
  `links-check.log`.

The link checker is site-wide. The remaining other-wave targets are missing model/run screenshots,
Administer mail/webhook pages, and `integrate/jobs` linking to the old `use/import-export` slug
(the delivered home is `use/importing-and-exporting`). They were not edited outside this scope.
A passing build is established; a passing verify is not claimed. Full verify requires the requested
captures and the other waves' target repairs.

## Uncertainties and observations

No live-browser walkthrough, screen-reader test, mail delivery or runtime error reproduction was
performed. Screenshots still need capture and visual inspection. Source-checked keyboard and phone
instructions are not a claim of device acceptance. The existing AI explanation text in History was
retained; deferred AI features were not expanded. No refiroo runtime defect was confirmed.

Source discrepancies corrected or recorded: export requires Browse rather than Bulk and import;
Clear all removes filters, and Clear search and filters removes both; missing-element buttons now
read Go back / Open in; the old three-related-record inventory is stale against the current
collection expansion bound; an empty workbook replacement-relationship cell clears its set although
ordinary blank field cells leave values unchanged. Application code was not changed.
