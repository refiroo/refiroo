# MX-COLUMNS source checks

- `RelationMatrixFilter.tsx`: column chooser works independently of state; labels are the column type plural plus "to show", "Any state", and "Show all" plus lower-case column type plural. Limit disables additional unselected choices at 20. Clearing columns also clears state.
- `ui/ControlPopover.tsx`: the Filter header has Done, which closes the popover.
- `RelationMatrixView.tsx`: explicit columns are requested without a column cursor; otherwise column records are paged. State is optional.
- `docs/API.md`, relation-matrix parameters: columnIds accepts at most 20; omitted columnIds yields a name-ordered page of column-type records.
- `routing/routes.ts`: matrixQuery reads repeated matrixColumn parameters and optional matrixState; route serialization writes them. viewRoute uses viewDefaults without matrix filters.
- `app/AppShell.tsx` onOpenCollection and `app/App.tsx` NavigationGroupPage onOpenCollection create fresh viewRoute routes, confirming navigation resets the selection. The filter only calls onChange with query choices; it does not save view configuration or other people's preferences.

Both wave statements confirmed. Existing screenshots suffice; no screenshots added or requested. Existing sections, screenshots and captions retained. Steering file absent before each page unit.

## Validation

`GUIDE_OUT=_build/MX-COLUMNS npm run verify` executed in guide/:

- Build passed: 247 pages.
- Terms and brand checks passed.
- Link check failed on six missing screenshot assets outside this wave:
  - guide/administer/check-the-ai-provider/: admin-ai-test-failed.png
  - guide/model/change-a-model-with-the-assistant/: model-assistant-whole-type-move.png
  - guide/model/change-a-model-with-the-assistant/: model-assistant-partial-move.png
  - guide/model/explain-a-model-change/: model-account-provider-failure.png
  - guide/model/migrate-a-workspace/: model-migration-stale.png
  - guide/use/change-records-with-the-assistant/: use-assistant-words.png
- Neither assigned page had a reported link failure. No unrelated fixes made.
- Build warnings: unsupported caddyfile highlighting falls back to txt on run/https; conflicting /404 route. Build still passed.
- No application defect found during the bounded source review. Browser execution and visual inspection were not part of this documentation-only wave.
