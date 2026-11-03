# Capture coverage and remaining prerequisites

No browser captures or image inspections were performed. Routes and labels were checked against the frontend. Existing screenshots were excluded.

## Missing page images with recipes

| Image | Pages |
| --- | --- |
| model-workbook-map-column.png | `src/content/docs/guide/model/map-a-column.md` |
| model-workbook-value-map.png | `src/content/docs/guide/model/map-a-column.md` |
| model-migration-review.png | `src/content/docs/guide/model/migrate-a-workspace.md`, `src/content/docs/model/migrations.md` |
| model-migration-loss-confirm.png | `src/content/docs/guide/model/migrate-a-workspace.md` |
| model-workbook-list-range.png | `src/content/docs/guide/model/read-lists-in-a-sheet.md` |
| workbook-columns-per-parent.png | `src/content/docs/guide/use/add-a-language-with-a-workbook.md` |
| new-record-required-connections.png | `src/content/docs/guide/use/add-a-record.md` |
| list-position-and-seek.png | `src/content/docs/guide/use/continue-a-long-list.md` |
| bulk-delete-impact.png | `src/content/docs/guide/use/delete-many-records.md` |
| export-for-people.png | `src/content/docs/guide/use/export-records.md` |
| import-profile-next-version.png | `src/content/docs/guide/use/load-the-next-version-of-a-workbook.md` |
| replace-related-records.png | `src/content/docs/guide/use/replace-a-records-related-records.md` |
| hierarchy-restructure-plan.png | `src/content/docs/guide/use/reshape-a-hierarchy.md` |
| run-backup-rehearsal.png | `src/content/docs/run/backup-and-restore.md` |
| run-deployment.png | `src/content/docs/run/configure.md` |
| run-operations.png | `src/content/docs/run/monitoring.md` |
| appearance-display-choices.png | `src/content/docs/use/appearance-and-devices.md` |
| phone-navigation-drawer.png | `src/content/docs/use/appearance-and-devices.md` |
| bulk-selection-preview.png | `src/content/docs/use/changing-many-records.md` |
| job-results-and-file.png | `src/content/docs/use/jobs.md` |

## Left out

| Image | Reason |
| --- | --- |
| model-migration-stale.png | The stale notice is raised when a migration confirmation is refused. Triggering it requires pressing Migrate after an intervening edit; this wave forbids migration/activation confirmations. No stale-state fixture or screenshot is fabricated. |
| model-language-raise-review.png | Requires a workspace on a historical schema-language release outside the supported read window. The documented reference workspaces use readable releases; no isolated historical-release fixture is supplied. Do not corrupt or replace the running release to manufacture it. |
| workspace-cannot-open.png | The requested administrator repair card requires schemaLeftWindow on a real workspace. An unknown workspace or retired workspace does not show that state. Shares the missing historical-release fixture prerequisite with model-language-raise-review. |
| contributor-propose-change.png | The runner supports only the reference admin and Rita Approver. Earlier capture notes give Rita Data owner, not Contributor. Producing the Contributor-only Live band would require creating/changing an account or grant, which this wave forbids. |
| notification-email-digest.png | Earlier reference captures document mail unavailable. The requested enabled email/digest state needs configured mail and an account destination. Neither is verified available, and no deployment/account setting is changed to invent this state. Reassess if the external capture confirms mail has since been configured. |
| run-jobs.png | The requested single image contains queued, running and finished work together. Existing finished/cancelled jobs and the prepared export are not that state. The runner cannot hold a worker or deterministically pause jobs; the small reference jobs can finish before capture. No large artificial workload or worker disruption is introduced for a picture. |
| import-preview-columns.png | Requires an exported For people workbook with saved import metadata and a deliberate invalid cell. No such local fixture is supplied; the runner has no download/save-download action to recover the prepared export. The ordinary supplier workbook or a JSON Lines refusal would not show Read as exported plus the required column report. Supply the actual exported workbook for a subsequent preparation pass; do not substitute an unrelated preview. |

## Capture review required

- Run setup entries once and record actual identifiers before retakes; later `--only` runs need their prepared state. Every ordinary dialog has cancellation or Escape. Migration preview jobs are cancelled on the page.
- Recipes using earlier APPROVALS state depend on its retained draft, profile and Guide workbook test workspace still existing. No instance read verified this snapshot.
- Migration preview may be blocked by consumer-contract checks. If so, leave both images missing and record the precise refusal; do not activate, install a replacement, or alter contracts.
- For the migration review, missing-type choices can be long. Check whether outcomes and context fit; framing may need adjustment after the first capture. The loss image focuses the bottom bar with the acceptance box unticked.
- Phone navigation may cover the workspace band. Inspect the actual image before accepting its existing caption; do not claim the band and drawer are both visible until checked.
- Source-inferred column rename and detected-list block are prerequisites to verify. A failed expectation is not evidence of a product defect.
- Capture runner `waitFor` has a 15-second timeout. Job creation/profiling may exceed it on the instance; adjust only after capture evidence, without confirming data writes.
- This turn makes no page-text or caption edits. Screens with ambiguous correspondence are reserved for the image-review turn.

## Source map

| Recipes | Frontend / retained-state evidence |
| --- | --- |
| Appearance / phone | `features/settings/AppearancePage.tsx`, `app/AppShell.tsx`, `app/DataContextBand.tsx`, `ui/NavigationDrawer.tsx` |
| Deployment / Operations / backup | `features/settings/DeploymentPage.tsx`, `features/settings/OperationsPage.tsx` |
| List / bulk | `ui/ScrollWindow.tsx`, `features/objects/CollectionView.tsx`, `SelectionBar.tsx`, `BulkChangeDialog.tsx`, `BulkDeleteDialog.tsx`, `BulkJobDialog.tsx`, `features/jobs/BatchOutcome.tsx` |
| Export / file results | `features/jobs/ExportDialog.tsx`, `exportRequest.ts`, `JobPage.tsx`, `jobText.ts`, `app/AppShell.tsx` |
| Creation / relationship set | `features/objects/ObjectFormDialog.tsx`, `RelatedRecordsDialog.tsx`, `useCellEditing.tsx`, `ui/EditInPlace.tsx`, `ui/RecordChecklist.tsx` |
| Workbook source | `features/model-editor/ColumnPanel.tsx`, `MapColumnDialog.tsx`, `ValueMapDialog.tsx`, `ListPanel.tsx`, `SourcePane.tsx`, `routing/routes.ts`; `_waves/APPROVALS.data-changes.md`; sample XLSX headers inspected directly |
| Hierarchy | `features/workspaces/ChangeSets.tsx`, `features/objects/Explorer.tsx`, `TreeView.tsx`, `RestructuringDialog.tsx`, `model/restructuring.ts` |
| Next workbook | `features/settings/ImportProfilesPage.tsx`, `ProfileCheckReport.tsx`, `features/model-editor/AddWorkbookDialog.tsx` |
| Migration | `features/model-admin/ModelPage.tsx`, `ModelReleaseDetail.tsx`, `ActivateDialog.tsx`, `MigrationPage.tsx`, `MigrationRows.tsx`, `ui/Selection.tsx`, `ui/OutcomeCards.tsx` |

## Added during final inventory check

`model-consumer-active-documents.png` was newly referenced by `guide/model/see-a-consumer-apis-documents.md` during this turn. Added a read-only Settings › Consumer APIs recipe. Evidence: `features/settings/ConsumerApisPage.tsx`, `consumerAddresses.ts`, `api/client.ts`. That page calls the consumer index without a workspace parameter and names `system.activeModelRelease`; it may show no Stops API if the default model lacks it. Report the actual empty state rather than changing the default, access or releases. This raises coverage to 21 page-image recipes plus 3 setup entries, with 7 omissions (28 missing images total).

## First capture supersedes preparation-only status

The first external capture has run. See `capture-review.md` and `recapture-report.md` for the actual image findings and revised eleven-image recapture list; see C10.data-changes.md for observed creations. Earlier statements about no images having been inspected describe the preparation turn only.
