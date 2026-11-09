# D-INTEGRATE completion report

Reviewed 34 pages; changed 16. Section words: **36,227 → 40,548** (whitespace count including front matter and examples). No pages were added or moved; sidebar order is unchanged. No commit or state-changing git command was run.

## Pages and word counts

| Page under src/content/docs | Before | After | Result |
| --- | ---: | ---: | --- |
| [guide/integrate/connect-an-assistant.md](../../../src/content/docs/guide/integrate/connect-an-assistant.md) | 677 | 677 | Reviewed; retained |
| [guide/integrate/exchange-a-supplier-file.md](../../../src/content/docs/guide/integrate/exchange-a-supplier-file.md) | 351 | 641 | Changed |
| [guide/integrate/get-a-token.md](../../../src/content/docs/guide/integrate/get-a-token.md) | 251 | 540 | Changed |
| [guide/integrate/load-then-follow-changes.md](../../../src/content/docs/guide/integrate/load-then-follow-changes.md) | 317 | 692 | Changed |
| [guide/integrate/move-records-between-models.md](../../../src/content/docs/guide/integrate/move-records-between-models.md) | 352 | 606 | Changed |
| [guide/integrate/read-a-collection-completely-and-resume.md](../../../src/content/docs/guide/integrate/read-a-collection-completely-and-resume.md) | 234 | 497 | Changed |
| [guide/integrate/read-as-of-a-date.md](../../../src/content/docs/guide/integrate/read-as-of-a-date.md) | 229 | 391 | Changed |
| [guide/integrate/read-through-a-consumer-api.md](../../../src/content/docs/guide/integrate/read-through-a-consumer-api.md) | 576 | 576 | Reviewed; retained |
| [guide/integrate/resolve-a-file-of-codes.md](../../../src/content/docs/guide/integrate/resolve-a-file-of-codes.md) | 525 | 525 | Reviewed; retained |
| [guide/integrate/submit-a-bulk-change.md](../../../src/content/docs/guide/integrate/submit-a-bulk-change.md) | 284 | 463 | Changed |
| [guide/integrate/subscribe-a-webhook-and-verify-it.md](../../../src/content/docs/guide/integrate/subscribe-a-webhook-and-verify-it.md) | 743 | 1,078 | Changed |
| [integrate/api-reference.md](../../../src/content/docs/integrate/api-reference.md) | 475 | 475 | Reviewed; retained |
| [integrate/assistant-tasks.md](../../../src/content/docs/integrate/assistant-tasks.md) | 1,727 | 1,727 | Reviewed; retained |
| [integrate/assistants-and-agents.md](../../../src/content/docs/integrate/assistants-and-agents.md) | 1,428 | 1,842 | Changed |
| [integrate/business-dates.md](../../../src/content/docs/integrate/business-dates.md) | 459 | 459 | Reviewed; retained |
| [integrate/changes-approvals-and-publication.md](../../../src/content/docs/integrate/changes-approvals-and-publication.md) | 1,255 | 1,491 | Changed |
| [integrate/compatibility.md](../../../src/content/docs/integrate/compatibility.md) | 766 | 766 | Reviewed; retained |
| [integrate/consumer-apis.md](../../../src/content/docs/integrate/consumer-apis.md) | 3,687 | 4,086 | Changed |
| [integrate/consumer-events-and-webhooks.md](../../../src/content/docs/integrate/consumer-events-and-webhooks.md) | 3,240 | 3,486 | Changed |
| [integrate/discovering-the-model.md](../../../src/content/docs/integrate/discovering-the-model.md) | 572 | 572 | Reviewed; retained |
| [integrate/files-imports-and-exports.md](../../../src/content/docs/integrate/files-imports-and-exports.md) | 1,798 | 2,027 | Changed |
| [integrate/following-changes.md](../../../src/content/docs/integrate/following-changes.md) | 1,053 | 1,053 | Reviewed; retained |
| [integrate/identifiers-paging-and-errors.md](../../../src/content/docs/integrate/identifiers-paging-and-errors.md) | 918 | 918 | Reviewed; retained |
| [integrate/jobs.md](../../../src/content/docs/integrate/jobs.md) | 1,025 | 1,210 | Changed |
| [integrate/looking-up-and-resolving.md](../../../src/content/docs/integrate/looking-up-and-resolving.md) | 1,753 | 1,753 | Reviewed; retained |
| [integrate/model-and-release-operations.md](../../../src/content/docs/integrate/model-and-release-operations.md) | 1,979 | 2,225 | Changed |
| [integrate/overview.md](../../../src/content/docs/integrate/overview.md) | 355 | 355 | Reviewed; retained |
| [integrate/reading-business-objects.md](../../../src/content/docs/integrate/reading-business-objects.md) | 1,741 | 1,960 | Changed |
| [integrate/reading-records.md](../../../src/content/docs/integrate/reading-records.md) | 1,493 | 1,493 | Reviewed; retained |
| [integrate/security-model-for-integrators.md](../../../src/content/docs/integrate/security-model-for-integrators.md) | 1,893 | 1,893 | Reviewed; retained |
| [integrate/signing-in-and-tokens.md](../../../src/content/docs/integrate/signing-in-and-tokens.md) | 932 | 932 | Reviewed; retained |
| [integrate/versions-and-conflicts.md](../../../src/content/docs/integrate/versions-and-conflicts.md) | 544 | 544 | Reviewed; retained |
| [integrate/workspaces-contexts-and-models.md](../../../src/content/docs/integrate/workspaces-contexts-and-models.md) | 677 | 677 | Reviewed; retained |
| [integrate/writing-in-bulk.md](../../../src/content/docs/integrate/writing-in-bulk.md) | 1,918 | 1,918 | Reviewed; retained |

## What was completed

- Added the consumer operation directory: every shared route and every reference list, with context and links to complete examples. Added publication selection and its distinct collection envelope.
- Explained each of the 21 exposed MCP tools individually and distinguished the internal resource-read handler. Clarified that history facts is nonpaged.
- Expanded token exchange, collection checkpoints, business-date reads, bulk reconciliation, file preview/fingerprints, profile lifecycle, job SSE reconnection, model rollout and transfer/publication recovery.
- Added the consumer-only load/list/events sequence and corrected webhook reset recovery. Covered receiver moves, retirement and separate receiver/instance backups.

## Coverage and depth

**53/53 code-inventory entries covered, 0 excluded, 0 uncovered.** Breakdown: consumer API 18, MCP entries 22, OAuth operations 7, screens 5, setting 1. The initial 13 unmatched entries are now matched. Updated `_waves/coverage/integrate.md`; preserved the older 719-row capability record. No exclusion or sidebar edit was needed.

The standard checker ran unchanged, with only its generated shared `uncovered.md` write redirected to `_coverage/notes/D-INTEGRATE/uncovered.md` using `redirect-coverage.mjs`. This avoids editing shared inventory outside the allowed files. The full captured coverage table is in `coverage-check.txt`; it currently reports no uncovered entries in any section.

Every page has an entry in [depth.md](depth.md), identifying applicable questions, evidence and questions owned by linked pages. No unsupported feature was invented to fill a depth question. Read-only operations do not create an independent backup, expiry or deletion lifecycle; model/data recovery and deployment configuration link to their operator or administrator owners. The original product concerns and their later D-DF status are recorded below.

## Validation

- `GUIDE_OUT=_build/D-INTEGRATE npm run verify`: **build passed**, 252 pages; **terms and brand passed**; **global links failed on 10 screenshot references in Use pages outside this assignment**. No Integrate page or guide appears in the failures. Exact output is in `verify.log`.
- `node --import ./_coverage/notes/D-INTEGRATE/redirect-coverage.mjs tools/check.mjs coverage`: passed, all 53 Integrate entries covered. Output redirection only; no inventory regeneration was needed.
- Parsed all 14 JSON fenced examples in the Integrate pages/guides: passed.
- `git diff --check` restricted to allowed wave paths: passed.

The first verification attempt caught an uppercase product-name occurrence in the newly added URL variable; corrected it to `INSTANCE_URL` and reran verification. Existing build warnings concern the unsupported Caddyfile highlighter and duplicate 404 route, outside this scope. No app/server/browser process was started; no HTTP workflows, database restore, assistant session or webhook delivery was executed. Existing captured reference payloads were retained, not recaptured. New publication empty-state output is explicitly illustrative.

### External link-check blockers

- `guide/use/change-how-refiroo-looks/index.html: src "/docs/screens/use-appearance-themes.png" points to nothing`
- `guide/use/copy-or-move-records/index.html: src "/docs/screens/use-move-review-change-sets.png" points to nothing`
- `guide/use/load-the-next-version-of-a-workbook/index.html: src "/docs/screens/use-import-file-delete-confirm.png" points to nothing`
- `guide/use/set-up-email-notices/index.html: src "/docs/screens/use-notification-email-digest-settings.png" points to nothing`
- `use/account/index.html: src "/docs/screens/use-sign-in-second-step.png" points to nothing`
- `use/appearance-and-devices/index.html: src "/docs/screens/use-appearance-themes.png" points to nothing`
- `use/copying-and-moving/index.html: src "/docs/screens/use-copy-dry-run.png" points to nothing`
- `use/importing-and-exporting/index.html: src "/docs/screens/use-import-profile-delete-actions.png" points to nothing`
- `use/importing-and-exporting/index.html: src "/docs/screens/use-import-profile-delete-confirm.png" points to nothing`
- `use/notifications-settings/index.html: src "/docs/screens/use-notification-email-digest-settings.png" points to nothing`

These pages/assets are outside the permitted edit paths. They were left untouched; the full verification command is not claimed to pass.

## Screenshots

No new screenshot requested. The existing `integrate-agent-access-connect.png` is present and retained in the connection guide. No screenshot was recaptured or visually reapproved. See [`_waves/screens-wanted/D-INTEGRATE.md`](../../../_waves/screens-wanted/D-INTEGRATE.md).

## Product concerns and uncertainty

1. **Expired webhook recovery can skip changes if the error text is followed literally.** `backend/app/engine/events/subscriptions.py:442-452` resets acknowledgment to the current feed head but tells the caller to re-sync from the named publication, which may be older. The guide now requires a baseline at/after reset, or a replacement subscription using a retained publication sequence. Code unchanged.
2. **Resolved: earlier consumer contracts are served beside the current version.** D-DF
   rechecked `engine/model/consumer_definitions.py`, `reads/consumer_objects.py`, `consumer/router.py`
   and `engine/events/`: the active model retains definitions in earlierVersions; reads,
   documents, pull feeds and subscriptions use the selected served version. Deprecation and
   optional Sunset headers announce retained contracts. A sunset day is not enforced; the
   model administrator chooses notice and removes the version explicitly. Guide pages now
   describe that lifecycle and the servedContractVersions recovery details. See
   `../D-DF/report.md` for source-review limits and current verification.

No additional unanswered source question was found for the added text. Operational success in a live deployment remains unverified: this wave checked documentation against source and built-site checks, not application acceptance.
