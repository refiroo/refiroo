# C11 final report

Recorded 2026-11-03T16:50:13+01:00.

## Counts before and after

Counts are ledger classifications, not independently executed application journeys. All 3,106 rows were processed; every currently covered target page and anchor was checked. The content pass used page-text comparisons and focused review of flagged destinations, low-support claims, glossary use and reconciliation handoffs. Keyword similarity is a finding aid, not evidence of product behavior.

| Section | Covered before → after | Not for readers | After 0.16 before → after | Open before → after |
| --- | ---: | ---: | ---: | ---: |
| about | 43 → 43 | 1 | 1 → 1 | 0 → 0 |
| administer | 238 → 238 | 9 | 31 → 42 | 11 → 0 |
| examples | 6 → 6 | 0 | 0 → 0 | 0 → 0 |
| integrate | 632 → 632 | 30 | 57 → 57 | 0 → 0 |
| journeys | 47 → 47 | 1 | 9 → 9 | 0 → 0 |
| model | 762 → 763 | 19 | 27 → 37 | 11 → 0 |
| run | 150 → 150 | 36 | 68 → 68 | 0 → 0 |
| use | 659 → 659 | 73 | 185 → 185 | 0 → 0 |
| **Total** | **2,537 → 2,538** | **169** | **378 → 399** | **22 → 0** |

One current gap, C1698, was filled. Twenty-one apparent gaps were AI/assistant/agent features explicitly deferred by the assignment. Existing deferred rows were preserved. C1698 also retains a deferred AI-only empty-state clause. C0040 is an existing mixed row: its ordinary security content is already in about/security-and-trust; AI disclosure remains deferred.

## What was written

- `src/content/docs/administer/mail.md` — Earlier C11 unit: removed the unavailable Messages screenshot and described its empty state.
- `src/content/docs/administer/deployment-pages.md` — Named the real About-screen headings.
- `src/content/docs/administer/sign-in.md` — Named WebAuthn passkeys and TOTP authenticator codes.
- `src/content/docs/about/how-it-is-built.md` — Named deployment components, protocols, formats, documentation tools and third-party licences from repository sources.
- `src/content/docs/about/how-it-works.md` — Clarified that object type is the editor term for record type.
- `src/content/docs/about/people-and-access.md` — Named OpenID Connect and WebAuthn at the access overview.
- `src/content/docs/about/security-and-trust.md` — Named OpenID Connect, TOTP and WebAuthn.
- `src/content/docs/guide/model/add-a-relationship.md` — Linked the actual relationship documentation page for a reciprocal pair.
- `src/content/docs/guide/model/check-a-workbook-with-a-dry-run.md` — Linked workbook onboarding for a reciprocal pair.
- `src/content/docs/model/models.md` — Linked the delete-draft guide back from its documentation page.
- `src/content/docs/model/managing-workspaces.md` — Explained permanent key rules, retirement waiting for writes and competing default switches.
- `src/content/docs/model/types-attributes-relations.md` — Explained the scope of released-element impact counts.
- `src/content/docs/integrate/workspaces-contexts-and-models.md` — Explained subscription blockers and deletion/recreation feed and idempotency consequences.
- `src/content/docs/integrate/jobs.md` — Named Server-Sent Events (SSE).
- `src/content/docs/use/account.md` — Named WebAuthn and TOTP at their controls.
- `src/content/docs/use/applications.md` — Explained wide-screen tabs, phone selection, Home and Settings.
- `src/content/docs/use/appearance-and-devices.md` — Explained heading focus, inline edit keys and Escape search clearing.
- `src/content/docs/use/history.md` — Explained the Live-only record History panel and Show all activity.
- `src/content/docs/use/mapping-grids.md` — Explained empty search/filter/workspace results and a missing-type view, with recovery.
- `src/content/docs/use/workspaces.md` — Explained pending and failed context reads, Retry and Return to Live.

Twenty page paths are listed, including the mail page finished by the earlier C11 run. No new page or sidebar change was needed. All eight coverage-file count headers were updated.

## Rows corrected

284 rows changed in coverage or wording. Full before/after values are in `corrected-rows.json`. The list below identifies every corrected row; bracketed links are the ledger destinations, not new guide navigation.

| Row | Current disposition |
| --- | --- |
| C2236 | [model/managing-workspaces](../../src/content/docs/model/managing-workspaces.md); [administer/roles-and-grants](../../src/content/docs/administer/roles-and-grants.md) |
| C2246 | [integrate/security-model-for-integrators](../../src/content/docs/integrate/security-model-for-integrators.md); [use/history](../../src/content/docs/use/history.md) |
| C2318 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2321 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2335 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2342 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2345 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2359 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2374 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2385 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2386 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2473 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2476 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2519 | [administer/signing-keys#normal-replacement](../../src/content/docs/administer/signing-keys.md#normal-replacement); [run/sign-in-and-mail-setup](../../src/content/docs/run/sign-in-and-mail-setup.md) |
| C3962 | [integrate/workspaces-contexts-and-models#deletion-and-reusing-a-workspace-key](../../src/content/docs/integrate/workspaces-contexts-and-models.md#deletion-and-reusing-a-workspace-key) |
| C3128 | [integrate/discovering-the-model](../../src/content/docs/integrate/discovering-the-model.md); [integrate/identifiers-paging-and-errors](../../src/content/docs/integrate/identifiers-paging-and-errors.md) |
| C3303 | [integrate/jobs](../../src/content/docs/integrate/jobs.md); [use/jobs](../../src/content/docs/use/jobs.md) |
| C3518 | [integrate/changes-approvals-and-publication](../../src/content/docs/integrate/changes-approvals-and-publication.md); [integrate/security-model-for-integrators](../../src/content/docs/integrate/security-model-for-integrators.md) |
| C3674 | [use/relation-matrices](../../src/content/docs/use/relation-matrices.md); [integrate/writing-in-bulk](../../src/content/docs/integrate/writing-in-bulk.md) |
| C1316 | [guide/model/add-a-record-type-and-fields](../../src/content/docs/guide/model/add-a-record-type-and-fields.md); [guide/model/add-a-relationship](../../src/content/docs/guide/model/add-a-relationship.md) |
| C1324 | [guide/model/choose-table-columns-filters-and-sort](../../src/content/docs/guide/model/choose-table-columns-filters-and-sort.md) |
| C1416 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1417 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1418 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1419 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1420 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1421 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1422 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1423 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1424 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1425 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1426 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1427 | [model/applications-and-views#mapping-grid-declarations](../../src/content/docs/model/applications-and-views.md#mapping-grid-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1438 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1439 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1440 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1441 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1442 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1443 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1444 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1445 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1446 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1447 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1448 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1449 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1450 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1451 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1452 | [model/applications-and-views#relation-matrix-rules](../../src/content/docs/model/applications-and-views.md#relation-matrix-rules); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1487 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1488 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1489 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1490 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1491 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1492 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1493 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1494 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1495 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1496 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1497 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1498 | [model/applications-and-views#tree-declarations](../../src/content/docs/model/applications-and-views.md#tree-declarations); [model/json-view](../../src/content/docs/model/json-view.md) |
| C1500 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis#declaration-rules-and-defaults](../../src/content/docs/integrate/consumer-apis.md#declaration-rules-and-defaults) |
| C1506 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis#review-a-contract-change](../../src/content/docs/integrate/consumer-apis.md#review-a-contract-change) |
| C1512 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1513 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1514 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1515 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1516 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1517 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1518 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1519 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1520 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1521 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1522 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1523 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1524 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1525 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1526 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1527 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1528 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1529 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1530 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1531 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1532 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1533 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1534 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1535 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1536 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1537 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1538 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1539 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1540 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1541 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1542 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1543 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1544 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1545 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1546 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1547 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1548 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1549 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1550 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1551 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1552 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1553 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1554 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1555 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1556 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1557 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1558 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1559 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1560 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1561 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1562 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1563 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1564 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1565 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1566 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1567 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1568 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1569 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1570 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1571 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1572 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1573 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1574 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1575 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1576 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1577 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1578 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1579 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1580 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1581 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1582 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1583 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1584 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1585 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1586 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1587 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1588 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md); [integrate/consumer-events-and-webhooks](../../src/content/docs/integrate/consumer-events-and-webhooks.md) |
| C1589 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1590 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1591 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1592 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1593 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1594 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1595 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1596 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1597 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1598 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1599 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1600 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1601 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1602 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C1607 | [model/the-model-editor#compare-before-releasing](../../src/content/docs/model/the-model-editor.md#compare-before-releasing); [guide/model/compare-releases](../../src/content/docs/guide/model/compare-releases.md) |
| C1619 | [model/managing-workspaces](../../src/content/docs/model/managing-workspaces.md) |
| C1623 | [guide/model/create-a-workspace](../../src/content/docs/guide/model/create-a-workspace.md) |
| C1624 | [guide/model/retire-or-delete-a-release](../../src/content/docs/guide/model/retire-or-delete-a-release.md); [run/model-releases-and-rollback](../../src/content/docs/run/model-releases-and-rollback.md) |
| C1625 | [use/workspaces#each-workspace-runs-its-own-model](../../src/content/docs/use/workspaces.md#each-workspace-runs-its-own-model) |
| C1630 | [guide/model/install-and-activate-a-release#apply-from-a-workspace](../../src/content/docs/guide/model/install-and-activate-a-release.md#apply-from-a-workspace) |
| C1646 | [guide/model/change-a-workspaces-model](../../src/content/docs/guide/model/change-a-workspaces-model.md) |
| C1647 | [guide/model/install-and-activate-a-release#apply-from-a-workspace](../../src/content/docs/guide/model/install-and-activate-a-release.md#apply-from-a-workspace) |
| C1649 | [model/managing-workspaces#tabs-and-model-changes](../../src/content/docs/model/managing-workspaces.md#tabs-and-model-changes) |
| C1650 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1681 | [administer/deployment-pages#about](../../src/content/docs/administer/deployment-pages.md#about) |
| C1682 | [model/migrations](../../src/content/docs/model/migrations.md); [guide/model/migrate-a-workspace](../../src/content/docs/guide/model/migrate-a-workspace.md) |
| C1698 | [use/mapping-grids#empty-results-and-an-unavailable-view](../../src/content/docs/use/mapping-grids.md#empty-results-and-an-unavailable-view); AI-only proposed-target empty state after 0.16 |
| C1699 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1740 | [use/workspaces#when-a-destination-cannot-open](../../src/content/docs/use/workspaces.md#when-a-destination-cannot-open); [guide/model/change-a-workspaces-model](../../src/content/docs/guide/model/change-a-workspaces-model.md) |
| C1742 | [model/the-model-editor](../../src/content/docs/model/the-model-editor.md) |
| C1749 | [model/managing-workspaces](../../src/content/docs/model/managing-workspaces.md); [model/migrations](../../src/content/docs/model/migrations.md); [guide/model/install-and-activate-a-release](../../src/content/docs/guide/model/install-and-activate-a-release.md) |
| C1750 | [model/json-view](../../src/content/docs/model/json-view.md); [model/releases](../../src/content/docs/model/releases.md); [guide/model/work-on-a-draft-with-others](../../src/content/docs/guide/model/work-on-a-draft-with-others.md) |
| C1751 | [model/workbook-onboarding](../../src/content/docs/model/workbook-onboarding.md) |
| C1752 | [model/workbook-onboarding](../../src/content/docs/model/workbook-onboarding.md); [model/workbook-proposals](../../src/content/docs/model/workbook-proposals.md) |
| C1753 | [model/workbook-onboarding](../../src/content/docs/model/workbook-onboarding.md); [guide/model/install-and-activate-a-release](../../src/content/docs/guide/model/install-and-activate-a-release.md) |
| C1757 | [model/workbook-onboarding#applying-and-keeping-the-work](../../src/content/docs/model/workbook-onboarding.md#applying-and-keeping-the-work) |
| C1766 | [guide/model/create-a-model-draft](../../src/content/docs/guide/model/create-a-model-draft.md); [guide/model/start-a-draft-from-a-workbook](../../src/content/docs/guide/model/start-a-draft-from-a-workbook.md) |
| C1781 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1782 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1789 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1798 | [guide/model/retire-or-delete-a-release](../../src/content/docs/guide/model/retire-or-delete-a-release.md); [run/model-releases-and-rollback](../../src/content/docs/run/model-releases-and-rollback.md); [model/releases](../../src/content/docs/model/releases.md) |
| C1801 | [model/model-mappings](../../src/content/docs/model/model-mappings.md); [guide/model/move-records-to-another-model](../../src/content/docs/guide/model/move-records-to-another-model.md) |
| C1803 | [model/models](../../src/content/docs/model/models.md); [model/releases](../../src/content/docs/model/releases.md); [guide/model/export-a-release](../../src/content/docs/guide/model/export-a-release.md); [guide/model/compare-releases](../../src/content/docs/guide/model/compare-releases.md) |
| C1811 | [model/the-model-editor](../../src/content/docs/model/the-model-editor.md); [model/types-attributes-relations](../../src/content/docs/model/types-attributes-relations.md) |
| C1813 | [model/json-view](../../src/content/docs/model/json-view.md) |
| C1841 | [guide/use/prepare-and-publish-a-change-set](../../src/content/docs/guide/use/prepare-and-publish-a-change-set.md); [use/change-sets](../../src/content/docs/use/change-sets.md) |
| C1852 | [model/types-attributes-relations](../../src/content/docs/model/types-attributes-relations.md); [model/applications-and-views](../../src/content/docs/model/applications-and-views.md); [model/record-pages-and-tables](../../src/content/docs/model/record-pages-and-tables.md); [model/issues-and-dry-run](../../src/content/docs/model/issues-and-dry-run.md) |
| C1871 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1872 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1874 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C1893 | [model/the-model-editor#history-undo-and-other-editors](../../src/content/docs/model/the-model-editor.md#history-undo-and-other-editors); [integrate/model-and-release-operations#draft-steps-and-generated-documents](../../src/content/docs/integrate/model-and-release-operations.md#draft-steps-and-generated-documents) |
| C1950 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C2052 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2064 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2065 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2066 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2067 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2068 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2069 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2070 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2071 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2072 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2073 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2074 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2075 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2076 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis#operations-and-matching](../../src/content/docs/integrate/consumer-apis.md#operations-and-matching) |
| C2077 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis#operations-and-matching](../../src/content/docs/integrate/consumer-apis.md#operations-and-matching) |
| C2078 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis#operations-and-matching](../../src/content/docs/integrate/consumer-apis.md#operations-and-matching) |
| C2079 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis#operations-and-matching](../../src/content/docs/integrate/consumer-apis.md#operations-and-matching) |
| C2083 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2084 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2085 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2086 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2087 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2112 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2113 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2114 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2115 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2116 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2117 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2118 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2119 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2122 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2123 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2124 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2131 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2132 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2133 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2134 | [model/consumer-apis](../../src/content/docs/model/consumer-apis.md); [integrate/consumer-apis](../../src/content/docs/integrate/consumer-apis.md) |
| C2168 | after 0.16: AI proposal, assistant, explanation or agent-access behavior; deferred by COMPLETE-COMMON |
| C3973 | [integrate/model-and-release-operations#draft-steps-and-generated-documents](../../src/content/docs/integrate/model-and-release-operations.md#draft-steps-and-generated-documents); [model/the-model-editor](../../src/content/docs/model/the-model-editor.md); [model/types-attributes-relations](../../src/content/docs/model/types-attributes-relations.md) |
| C2574 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2575 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2576 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2577 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2578 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2579 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2581 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2583 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2584 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2613 | [run/webhook-delivery](../../src/content/docs/run/webhook-delivery.md); [model/managing-workspaces](../../src/content/docs/model/managing-workspaces.md) |
| C2722 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2723 | [run/configure#batch-and-job-limits-catalogue](../../src/content/docs/run/configure.md#batch-and-job-limits-catalogue) |
| C2727 | [run/configure#runtime-catalogue](../../src/content/docs/run/configure.md#runtime-catalogue) |
| C2728 | [run/configure#runtime-catalogue](../../src/content/docs/run/configure.md#runtime-catalogue) |
| C2729 | [run/configure#capability-groups](../../src/content/docs/run/configure.md#capability-groups-catalogue) |
| C2767 | [run/database](../../src/content/docs/run/database.md); [run/health-and-startup-checks](../../src/content/docs/run/health-and-startup-checks.md) |
| C2921 | [run/upgrades](../../src/content/docs/run/upgrades.md#prepare-and-verify-a-cutover) |
| C4002 | [run/health-and-startup-checks](../../src/content/docs/run/health-and-startup-checks.md#distinguish-the-service-states) |
| C4034 | [run/install-with-compose](../../src/content/docs/run/install-with-compose.md); [run/https](../../src/content/docs/run/https.md)  [service, network and storage inventory](../../src/content/docs/run/overview.md#network-and-storage) |
| C4037 | [run/secrets-and-keys](../../src/content/docs/run/secrets-and-keys.md#supply-the-temporary-new-key-without-a-literal-secret-in-history) |
| C0197 | [integrate/api-reference](../../src/content/docs/integrate/api-reference.md) |
| C0218 | [model/models](../../src/content/docs/model/models.md); [guide/model/create-a-model-draft](../../src/content/docs/guide/model/create-a-model-draft.md) |
| C0232 | [use/records#deleting-a-record](../../src/content/docs/use/records.md#deleting-a-record) |
| C0234 | [use/change-sets](../../src/content/docs/use/change-sets.md) |
| C0235 | [use/change-sets#publishing-and-intervening-live-work](../../src/content/docs/use/change-sets.md#publishing-and-intervening-live-work) |
| C0294 | [use/appearance-and-devices](../../src/content/docs/use/appearance-and-devices.md); [administer/deployment-pages](../../src/content/docs/administer/deployment-pages.md) |
| C0296 | [use/history#a-persons-changes](../../src/content/docs/use/history.md#a-persons-changes) |
| C0297 | [use/appearance-and-devices](../../src/content/docs/use/appearance-and-devices.md); [use/jobs](../../src/content/docs/use/jobs.md); [model/model-mappings](../../src/content/docs/model/model-mappings.md) |
| C0298 | [use/appearance-and-devices](../../src/content/docs/use/appearance-and-devices.md); [use/account](../../src/content/docs/use/account.md) |
| C0299 | [use/appearance-and-devices](../../src/content/docs/use/appearance-and-devices.md); [administer/api-reference-and-consumer-api-pages](../../src/content/docs/administer/api-reference-and-consumer-api-pages.md); [administer/webhooks](../../src/content/docs/administer/webhooks.md) |
| C0300 | [use/appearance-and-devices](../../src/content/docs/use/appearance-and-devices.md); [administer/people-and-groups](../../src/content/docs/administer/people-and-groups.md); [administer/roles-and-grants](../../src/content/docs/administer/roles-and-grants.md) |
| C0421 | [use/workspaces#a-context-that-could-not-load](../../src/content/docs/use/workspaces.md#a-context-that-could-not-load) |
| C0423 | [guide/use/switch-workspace](../../src/content/docs/guide/use/switch-workspace.md); [use/workspaces](../../src/content/docs/use/workspaces.md) |
| C0432 | [use/publications](../../src/content/docs/use/publications.md) |
| C0439 | [guide/use/change-relationships-of-many-records](../../src/content/docs/guide/use/change-relationships-of-many-records.md); [integrate/reading-records](../../src/content/docs/integrate/reading-records.md) |
| C0443 | [use/relationships](../../src/content/docs/use/relationships.md); [guide/use/change-relationships-of-many-records](../../src/content/docs/guide/use/change-relationships-of-many-records.md) |
| C0448 | [use/records](../../src/content/docs/use/records.md); [guide/use/correct-a-record](../../src/content/docs/guide/use/correct-a-record.md) |
| C0455 | [use/workspaces#refresh-after-the-model-changes](../../src/content/docs/use/workspaces.md#refresh-after-the-model-changes); [integrate/versions-and-conflicts](../../src/content/docs/integrate/versions-and-conflicts.md) |
| C0456 | [use/hierarchies](../../src/content/docs/use/hierarchies.md); [use/relation-matrices](../../src/content/docs/use/relation-matrices.md) |
| C0625 | [use/change-sets](../../src/content/docs/use/change-sets.md); [use/importing-and-exporting](../../src/content/docs/use/importing-and-exporting.md); [use/history](../../src/content/docs/use/history.md) |
| C0653 | [use/publications](../../src/content/docs/use/publications.md); [use/history](../../src/content/docs/use/history.md) |
| C0725 | [use/changing-many-records](../../src/content/docs/use/changing-many-records.md); [use/inbox-and-approvals](../../src/content/docs/use/inbox-and-approvals.md); [use/importing-and-exporting](../../src/content/docs/use/importing-and-exporting.md) |
| C0733 | [use/appearance-and-devices#keyboard-operation](../../src/content/docs/use/appearance-and-devices.md#keyboard-operation); [use/records](../../src/content/docs/use/records.md) |
| C0781 | [use/applications](../../src/content/docs/use/applications.md); [use/appearance-and-devices#help-beside-your-work](../../src/content/docs/use/appearance-and-devices.md#help-beside-your-work) |
| C1059 | [model/managing-workspaces](../../src/content/docs/model/managing-workspaces.md); [model/releases](../../src/content/docs/model/releases.md) |
| C1060 | [use/lists-and-filters](../../src/content/docs/use/lists-and-filters.md); [guide/use/find-records](../../src/content/docs/guide/use/find-records.md) |
| C1061 | [guide/use/add-a-record](../../src/content/docs/guide/use/add-a-record.md); [guide/use/fill-in-a-relation-matrix](../../src/content/docs/guide/use/fill-in-a-relation-matrix.md) |
| C1135 | [use/applications#collections-and-views](../../src/content/docs/use/applications.md#collections-and-views) |
| C1189 | [use/relationships#longer-sets-and-actions-on-several-records](../../src/content/docs/use/relationships.md#longer-sets-and-actions-on-several-records); [integrate/reading-records](../../src/content/docs/integrate/reading-records.md) |
| C1265 | [integrate/workspaces-contexts-and-models#read-across-workspaces](../../src/content/docs/integrate/workspaces-contexts-and-models.md#read-across-workspaces); [integrate/model-and-release-operations](../../src/content/docs/integrate/model-and-release-operations.md) |
| C1295 | [use/applications](../../src/content/docs/use/applications.md) |
| C1297 | [use/appearance-and-devices#keyboard-operation](../../src/content/docs/use/appearance-and-devices.md#keyboard-operation) |
| C1299 | [use/home](../../src/content/docs/use/home.md) |
| C1301 | [use/applications](../../src/content/docs/use/applications.md) |

## Rows still open and screenshots

No row is classified uncovered or partly. All 399 deferred rows and their individual reasons are listed in `deferred-rows.md`; they remain unwritten because COMPLETE-COMMON defers AI/assistant/agent content. The 169 not-for-readers rows retain their reasons in their source ledgers.

The only outstanding screenshot request is `admin-mail-messages.png`: Messages filtered to Waiting, state counts, Refresh and “No message is in this state.” No credentials, password links or message bodies should be visible. Its reference was removed from administer/mail. The request is in `_waves/screens-wanted/C11-FINAL.md` because the requested C10-LATER ledger is outside the permitted edits.

## Handoffs and scope limits

All 26 R-FUNCTIONALITY handoff groups have a current home recorded in `handoffs.md`, including already-present explanations. Reconciliation ledgers themselves were not edited: `_waves/reconcile/*.md` is outside the explicit allowlist. The same scope restriction applies to C10-LATER and shared build configuration.

## Verification and remaining uncertainty

- `GUIDE_OUT=_build/C11-FINAL npm run verify` in guide: passed, 225 pages, terms/brand and 58,158 local links and sources. Full bounded output: `verify-final.log`.
- `python3 guide/_coverage/notes/C11-FINAL/final_structure.py`: passed. All 223 ordinary content pages are listed in the sidebar; all 111 task guides have a reciprocal documentation link; every covered ledger destination and fragment exists in the built HTML. Front matter is present on all 225 pages. The deferred Agent access sidebar placeholder is intentionally filtered out by existing configuration.
- The actual GuideFiles class mounted over the isolated output returned HTTP 404, the custom page introduction and search guidance, and security headers for an unknown address. No listening server or database was started.
- The duplicate /404 generation warning remains. Starlight’s explicit route uses the custom content correctly; eliminating the warning cleanly requires an out-of-scope configuration/route change. See `404.md` for evidence and why draft/slug workarounds were rejected.
- The source glossary is docs/product-functionality/GLOSSARY.md; the assignment’s shorter docs/GLOSSARY.md path does not exist. Current per-workspace activation and structured editing follow code rather than superseded glossary wording.
- No reference instance, external provider, SMTP server, migration, full application journey, screenshot appearance or assistive-technology session was revalidated. No new product defect was confirmed by this documentation pass.
- No commit or Git state-changing command was run. Notes and reports were kept only in the permitted C11 notes folder.
