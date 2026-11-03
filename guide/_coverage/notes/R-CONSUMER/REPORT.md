# R-CONSUMER completion report

Reconciled 124 source headings: 30 CONSUMER_API, 10 COMPATIBILITY, 37 INTEGRATION_API and 47 selected API concept headings. Exact headings, facts, homes, skips and disagreements are in `_waves/reconcile/R-CONSUMER.md`. All headings of the first three sources have a row; API operation schemas remain in the reference.

Changed 23 pages and the owned sidebar (removed the unbuilt assistants entry). Existing integrate task guides were reviewed and retained. Fact groups: 266 added, 19 corrected, 86 expanded. Counts below describe final reconciliation; they are not line counts.

| Page (under src/content/docs/) | Added | Corrected | Expanded |
| --- | ---: | ---: | ---: |
| integrate/api-reference.md | 3 | 0 | 0 |
| integrate/business-dates.md | 3 | 0 | 0 |
| integrate/changes-approvals-and-publication.md | 6 | 0 | 2 |
| integrate/compatibility.md | 7 | 0 | 0 |
| integrate/consumer-apis.md | 35 | 2 | 12 |
| integrate/consumer-events-and-webhooks.md | 36 | 1 | 9 |
| integrate/discovering-the-model.md | 6 | 0 | 1 |
| integrate/files-imports-and-exports.md | 21 | 0 | 7 |
| integrate/following-changes.md | 8 | 0 | 1 |
| integrate/identifiers-paging-and-errors.md | 14 | 0 | 5 |
| integrate/jobs.md | 12 | 0 | 3 |
| integrate/looking-up-and-resolving.md | 10 | 0 | 1 |
| integrate/model-and-release-operations.md | 29 | 1 | 13 |
| integrate/reading-business-objects.md | 9 | 0 | 3 |
| integrate/reading-records.md | 10 | 0 | 3 |
| integrate/security-model-for-integrators.md | 8 | 1 | 2 |
| integrate/signing-in-and-tokens.md | 10 | 0 | 3 |
| integrate/versions-and-conflicts.md | 4 | 0 | 2 |
| integrate/workspaces-contexts-and-models.md | 7 | 0 | 1 |
| integrate/writing-in-bulk.md | 25 | 0 | 9 |
| model/consumer-apis.md | 3 | 6 | 5 |
| guide/model/define-a-consumer-api.md | 0 | 4 | 2 |
| guide/model/see-a-consumer-apis-documents.md | 0 | 4 | 2 |

## Checks

- `GUIDE_OUT=_build/R-CONSUMER npm run verify`: build PASS (225 pages, 3.10 s); terms and brand PASS; global links FAIL with exactly one issue outside the owned files: use/workspaces/index.html links to /docs/model/, which has no page. Left untouched. No owned-page link failures reported among 58,127 checked links/sources.
- `node --check guide/sidebar/integrate.mjs`: PASS.
- Scoped `git diff --check`: PASS.
- Three model-admin pages contain no fenced payloads, API paths or inline JSON bodies: PASS.
- This was source/code reconciliation and a documentation build. No live data routes, webhook receiver, migration, browser interaction or fresh screenshot capture was exercised. Existing request/response examples retain their provenance and illustrative placeholders.
- Build warnings outside scope: Caddyfile highlighting fallback in run/https; duplicate 404 route warning. They did not fail the build.

## Screenshots

No new screenshot needed. Retained nine existing images, all resolved by the build/link check:

| Image | Screen/state retained |
| --- | --- |
| model-consumer-tab-fields.png | Fields: roles, ordered sources, served types, defaults |
| model-consumer-tab-filters.png | Filters: ancestor and related choices |
| model-consumer-tab-types.png | Exposed types and related blocks |
| model-consumer-add-dialog.png | New API: name, key, exposed types |
| model-consumer-add-field.png | Add field: output, sources, role |
| model-consumer-add-filter.png | Add filter: verb and matching choices |
| model-consumer-tab-schema.png | Draft generated schema |
| model-consumer-tab-example.png | Generated placeholder message |
| model-consumer-active-documents.png | Active release, contract version, addresses and routes |

Images were reused, not freshly inspected or recaptured. Each page names the state it needs.

## Product/source findings

The important unresolved product gap is version overlap: COMPATIBILITY promises simultaneous old/new consumer versions but current code serves only the selected workspace definition's live version. The guide explicitly says so. Other source disagreements (public OpenAPI/client-only access, 0.10-only schema window, draft-base comparison, output-name event detection, database uniqueness, obsolete allowlist/coalescing/export/preview designs) are recorded with code pointers in the ledger. The broken /docs/model/ link is outside this wave. No code was changed, no state-changing git command was run, and nothing was committed.
