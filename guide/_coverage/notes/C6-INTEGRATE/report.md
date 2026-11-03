# C6-INTEGRATE completion report

Completed the existing wave from its recorded progress: 21 documentation pages and 10 task guides. Added the three missing pages (API reference, compatibility and security for integrators), completed missing recovery behavior, and applied the owner’s steering to the four consumer concept pages and three consumer task guides. Consumer pages now explain declarations, concrete routes, parameters and responses directly, with complete reference-data examples.

## Pages

### Documentation

- [integrate/api-reference.md](../../../src/content/docs/integrate/api-reference.md)
- [integrate/business-dates.md](../../../src/content/docs/integrate/business-dates.md)
- [integrate/changes-approvals-and-publication.md](../../../src/content/docs/integrate/changes-approvals-and-publication.md)
- [integrate/compatibility.md](../../../src/content/docs/integrate/compatibility.md)
- [integrate/consumer-apis.md](../../../src/content/docs/integrate/consumer-apis.md)
- [integrate/consumer-events-and-webhooks.md](../../../src/content/docs/integrate/consumer-events-and-webhooks.md)
- [integrate/discovering-the-model.md](../../../src/content/docs/integrate/discovering-the-model.md)
- [integrate/files-imports-and-exports.md](../../../src/content/docs/integrate/files-imports-and-exports.md)
- [integrate/following-changes.md](../../../src/content/docs/integrate/following-changes.md)
- [integrate/identifiers-paging-and-errors.md](../../../src/content/docs/integrate/identifiers-paging-and-errors.md)
- [integrate/jobs.md](../../../src/content/docs/integrate/jobs.md)
- [integrate/looking-up-and-resolving.md](../../../src/content/docs/integrate/looking-up-and-resolving.md)
- [integrate/model-and-release-operations.md](../../../src/content/docs/integrate/model-and-release-operations.md)
- [integrate/overview.md](../../../src/content/docs/integrate/overview.md)
- [integrate/reading-business-objects.md](../../../src/content/docs/integrate/reading-business-objects.md)
- [integrate/reading-records.md](../../../src/content/docs/integrate/reading-records.md)
- [integrate/security-model-for-integrators.md](../../../src/content/docs/integrate/security-model-for-integrators.md)
- [integrate/signing-in-and-tokens.md](../../../src/content/docs/integrate/signing-in-and-tokens.md)
- [integrate/versions-and-conflicts.md](../../../src/content/docs/integrate/versions-and-conflicts.md)
- [integrate/workspaces-contexts-and-models.md](../../../src/content/docs/integrate/workspaces-contexts-and-models.md)
- [integrate/writing-in-bulk.md](../../../src/content/docs/integrate/writing-in-bulk.md)

### Task guides

- [guide/integrate/exchange-a-supplier-file.md](../../../src/content/docs/guide/integrate/exchange-a-supplier-file.md)
- [guide/integrate/get-a-token.md](../../../src/content/docs/guide/integrate/get-a-token.md)
- [guide/integrate/load-then-follow-changes.md](../../../src/content/docs/guide/integrate/load-then-follow-changes.md)
- [guide/integrate/move-records-between-models.md](../../../src/content/docs/guide/integrate/move-records-between-models.md)
- [guide/integrate/read-a-collection-completely-and-resume.md](../../../src/content/docs/guide/integrate/read-a-collection-completely-and-resume.md)
- [guide/integrate/read-as-of-a-date.md](../../../src/content/docs/guide/integrate/read-as-of-a-date.md)
- [guide/integrate/read-through-a-consumer-api.md](../../../src/content/docs/guide/integrate/read-through-a-consumer-api.md)
- [guide/integrate/resolve-a-file-of-codes.md](../../../src/content/docs/guide/integrate/resolve-a-file-of-codes.md)
- [guide/integrate/submit-a-bulk-change.md](../../../src/content/docs/guide/integrate/submit-a-bulk-change.md)
- [guide/integrate/subscribe-a-webhook-and-verify-it.md](../../../src/content/docs/guide/integrate/subscribe-a-webhook-and-verify-it.md)

## Coverage and navigation

- All 719 IDs retained: **632 covered, 57 deferred AI, 30 internal-only exclusions**. No current row remains uncovered.
- Every documentation page and task guide is already present in `sidebar/integrate.mjs`; no sidebar change was necessary. The absent assistant page stays deferred.
- Misassigned error and UI rows now link to the actual recovery or reader page. The 314 current message/error rows have code-presence and recovery-page evidence in `error-source-audit.md`.
- Screenshots requested: **none**. API examples supply the evidence for this section; browser setup links to Administer and Model. `screens-wanted/C6-INTEGRATE.md` records this.

## Checks actually performed

- `GUIDE_OUT=_build/C6-INTEGRATE npm run verify` in `guide/`: **build passed** (200 built pages), **terms and brand passed**. Link checking reports **12 missing references**, all missing screenshots on pages outside this wave’s permitted edits, listed below.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python guide/_coverage/notes/C6-INTEGRATE/consumer_examples.py`: compiled the reference model and composed sample objects with the production renderer over reference sample records, without a database.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python guide/_coverage/notes/C6-INTEGRATE/verify_examples.py`: eight published request/response examples validate against generated stops OpenAPI; the subscription request validates against its command model. The published verification function accepts the production-generated signature and overlap signatures, rejects body tampering, stale timestamps and malformed non-ASCII input. Published raw delivery bytes match the signed bytes.
- Read and cross-checked relevant J25, J28, J29 and J30 source assertions. These journey suites were **not executed**. No application code or tests changed.
- Checked all 31 pages’ front matter, all sidebar entries and coverage counts. No server, database or receiver was started. No git state-changing command or commit was run.

## What remains unconfirmed or inconsistent

- The environment refused HTTP access to `localhost:8480` with Operation not permitted. No live response, cursor, ETag, subscription or receiver was captured or exercised. Object values use production composition over reference data. Envelopes are code-derived and schema-checked. Instance-specific cursors and ETags are explicit placeholders; event occurrences and delivery IDs are illustrative. The demonstration key is public example text, not an instance secret.
- The compatibility commitment requires parallel old contract versions. Current consumer routing checks the workspace’s active definition and version before reading even a publication, and serves only that declared live version. Raising the contract version does not retain the old live endpoint; this policy/implementation discrepancy needs owner review. The pages explain current behavior and distinguish it from the commitment.
- Older records say `/docs` is the API reference; current code serves documentation there and the API reference at `/docs/api`. Export checkpoints are job metadata, not file contents. Consumer totals are null without totals requested. The pages follow code for these differences.

## Missing cross-wave references in the final link check

- `guide/model/migrate-a-workspace/index.html: src "/docs/screens/model-migration-stale.png" points to nothing`
- `guide/model/raise-a-model-language-version/index.html: src "/docs/screens/model-language-raise-review.png" points to nothing`
- `guide/use/add-a-language-with-a-workbook/index.html: src "/docs/screens/workbook-columns-per-parent.png" points to nothing`
- `guide/use/export-records/index.html: src "/docs/screens/export-for-people.png" points to nothing`
- `guide/use/open-a-retired-or-unavailable-workspace/index.html: src "/docs/screens/workspace-cannot-open.png" points to nothing`
- `guide/use/propose-a-change/index.html: src "/docs/screens/contributor-propose-change.png" points to nothing`
- `guide/use/replace-a-records-related-records/index.html: src "/docs/screens/replace-related-records.png" points to nothing`
- `guide/use/reshape-a-hierarchy/index.html: src "/docs/screens/hierarchy-restructure-plan.png" points to nothing`
- `run/background-jobs/index.html: src "/docs/screens/run-jobs.png" points to nothing`
- `use/changing-many-records/index.html: src "/docs/screens/bulk-selection-preview.png" points to nothing`
- `use/importing-and-exporting/index.html: src "/docs/screens/import-preview-columns.png" points to nothing`
- `use/notifications-settings/index.html: src "/docs/screens/notification-email-digest.png" points to nothing`

## Resumed final validation

The continuation removed repeated version guidance and repaired both Integrate links to the absent Administer Webhooks page. They now give explicit Settings navigation and link to the existing client-access documentation. No other section was edited. The wave-specific build passes (200 pages), terms and brand pass, and all 31 section pages have front matter and sidebar entries. The offline example/signature check passes again. The final `verify` remains unsuccessful only because of the 12 missing screenshots listed above; none is on an Integrate page. Current coverage remains 632 covered, 57 deferred AI and 30 internal-only exclusions, with no current row open. No new live HTTP verification was attempted.
