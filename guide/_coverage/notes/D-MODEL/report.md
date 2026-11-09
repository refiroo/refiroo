# D-MODEL completion report

Reviewed all 63 existing pages and added 2 guides; 65 pages total. Expanded 20 existing pages and added `guide/model/add-a-view.md` and `guide/model/delete-a-model-mapping.md`, both in the sidebar. Three further pages have inventory trace annotations only. The scope’s whitespace word count is 44,667 before and 48,524 after (invisible trace/capture comments excluded after; source files retained in before.json).

## Pages written or expanded

| Page | Before | After |
| --- | ---: | ---: |
| [src/content/docs/guide/model/add-a-record-type-and-fields.md](../../../src/content/docs/guide/model/add-a-record-type-and-fields.md) | 745 | 849 |
| [src/content/docs/guide/model/add-a-relationship.md](../../../src/content/docs/guide/model/add-a-relationship.md) | 768 | 929 |
| [src/content/docs/guide/model/add-a-view.md](../../../src/content/docs/guide/model/add-a-view.md) | 0 | 666 |
| [src/content/docs/guide/model/arrange-applications-and-views.md](../../../src/content/docs/guide/model/arrange-applications-and-views.md) | 346 | 412 |
| [src/content/docs/guide/model/choose-table-columns-filters-and-sort.md](../../../src/content/docs/guide/model/choose-table-columns-filters-and-sort.md) | 762 | 904 |
| [src/content/docs/guide/model/define-a-consumer-api.md](../../../src/content/docs/guide/model/define-a-consumer-api.md) | 1,493 | 1,577 |
| [src/content/docs/guide/model/delete-a-model-mapping.md](../../../src/content/docs/guide/model/delete-a-model-mapping.md) | 0 | 206 |
| [src/content/docs/guide/model/edit-a-record-page.md](../../../src/content/docs/guide/model/edit-a-record-page.md) | 889 | 1,173 |
| [src/content/docs/guide/model/map-a-column.md](../../../src/content/docs/guide/model/map-a-column.md) | 492 | 539 |
| [src/content/docs/guide/model/raise-a-contract-version.md](../../../src/content/docs/guide/model/raise-a-contract-version.md) | 246 | 266 |
| [src/content/docs/guide/model/retire-or-delete-a-workspace.md](../../../src/content/docs/guide/model/retire-or-delete-a-workspace.md) | 229 | 245 |
| [src/content/docs/guide/model/reuse-and-change-attributes.md](../../../src/content/docs/guide/model/reuse-and-change-attributes.md) | 311 | 542 |
| [src/content/docs/guide/model/review-an-assistants-workbook-design.md](../../../src/content/docs/guide/model/review-an-assistants-workbook-design.md) | 1,285 | 1,302 |
| [src/content/docs/model/applications-and-views.md](../../../src/content/docs/model/applications-and-views.md) | 1,572 | 1,675 |
| [src/content/docs/model/consumer-apis.md](../../../src/content/docs/model/consumer-apis.md) | 2,309 | 2,519 |
| [src/content/docs/model/json-view.md](../../../src/content/docs/model/json-view.md) | 374 | 801 |
| [src/content/docs/model/managing-workspaces.md](../../../src/content/docs/model/managing-workspaces.md) | 836 | 880 |
| [src/content/docs/model/model-mappings.md](../../../src/content/docs/model/model-mappings.md) | 1,173 | 1,299 |
| [src/content/docs/model/models.md](../../../src/content/docs/model/models.md) | 1,144 | 1,218 |
| [src/content/docs/model/record-pages-and-tables.md](../../../src/content/docs/model/record-pages-and-tables.md) | 1,648 | 2,015 |
| [src/content/docs/model/types-attributes-relations.md](../../../src/content/docs/model/types-attributes-relations.md) | 2,073 | 2,436 |
| [src/content/docs/model/workbook-onboarding.md](../../../src/content/docs/model/workbook-onboarding.md) | 3,003 | 3,102 |

## Coverage

- Legacy section ledger: all 819 rows have a disposition, none open. Corrected the superseded no-table-creation claim.
- Code inventory: 381 model entries, 378 covered and 3 excluded; zero model gaps. These comprise 205 covered model features plus 3 excluded, 140 covered screen entries and 33 management operations supplied by the generated API reference.
- Excluded: application settings free map, application state and application colour, unused by runtime presentation. The schema language version is now covered by the recovery page instead of excluded.
- All code keys have a trace to the owning page and editor control in `_waves/coverage/model.md`; invisible comments provide exact inventory identity without putting model paths in reader instructions.
- The stock coverage checker’s only write (uncovered.md) was redirected to `_coverage/notes/D-MODEL/uncovered.md`, because the shared inventory is outside the edit allowlist. Its global failure is other sections’ entries; inspect coverage.log for the exact run. No shared inventory output was changed.

## Specialist-only choices

The JSON-view page lists model title/description, icons, existing element descriptions, typed attribute defaults, ancestor-scoped conditional relationship uniqueness, detailed tree actions/per-type and descending sort/reading size, mapping-grid reading size, matrix search/reading size, full panel declarations and consumer combinations without a form. The new ordinary Settings controls are documented on their capability pages, not described as specialist-only.

## Screenshots and depth limits

Nine new captures are requested in `_waves/screens-wanted/D-MODEL.md`, each with page, state and required controls. Exact image Markdown remains as pending HTML comments until capture; all pre-existing image references remain rendered. No screen was invented, substituted, captured or visually inspected in this wave. Restore the pending references after capture.

All applicable depth questions were reviewed; details by capability and page are in depth.md. No known factual question was filled in by guessing. Browser tasks, real provider calls, actual activation/migration/copy/deletion and live access grants were not exercised: this is source-checked writing, not product acceptance. Operator recovery, backup and provider retention remain owned by linked operator documentation.

## Product issues found

1. `frontend/src/features/model-editor/viewKinds.ts:104–115,259–290`: changing an existing tree regenerates its action list from availability only and rebuilds one common child sort. It can remove specialist-declared Create/Rename/Move actions and replace per-type or descending orders. Documented in the view page and new guide; product code unchanged.
2. `frontend/src/features/model-editor/elementSettings.tsx:113–114` describes Oriented as removing outgoing relationships. The deletion rule at `backend/app/engine/records/deletion.py:775–785` uses orientation to cascade into required owned target records. The help understates that consequence; the guide explains it. Product code unchanged.

## Checks

See verify.log for the final isolated `GUIDE_OUT=_build/D-MODEL npm run verify` (build, terms, brand, local links). See coverage.log for the code-inventory check. No application tests or product writes were performed. No commit or state-changing git command was run.
