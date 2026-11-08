# C11-FIX2 evidence

## Browser findings 1–10

Checked TreeView.tsx rootAdds (rootCreatable, createChild, write permission); inboxText.ts noticeRoute and NotificationsPage.tsx open (active opens snapshot; otherwise Publications; bell uses noticeRoute); DataContextBand.tsx RETIRED_BAND_TEXT; ImportProfilesPage.tsx read/save workspace; BulkJobDialog.tsx currentVersions retry; model-editor/history.ts and its rename test. Changelog Unreleased records workbook overwrite fix. Findings 2–3 are setup exclusions.

Changes explain first-root creation, all cancel labels, publication notice fallback, retired band, profile comparison workspace, current-version delete retry, rename summary and deliberate workbook overwrite. No browser session or product regression tests run by this writing wave.

## Operator and exceptional-state checks

Checked compose.yml and compose.acme.yml services/mounts/ports; frontend/Dockerfile user and TLS files; backend/app/common/logs.py JsonFormatter; backend/app/cli/create_client.py and create_admin.py; generate_key.py and database_upgrade.py argument parsing; engine/authorization/catalogue.py PREDEFINED_ROLES and role-name migrations 20261029_01 and 20261120_01; engine/jobs/batches.py file-row overwrite version handling; model/compiler.py SCHEMA_VERSIONS; model/raising.py stored-release recovery; frontend model-editor/OperationDialog.tsx refusalText. Detailed dispositions, picture review and validation are in report.md.
