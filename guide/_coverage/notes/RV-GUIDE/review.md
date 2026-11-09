# RV-GUIDE review and evidence

Only the wave's allowed source pages, three sidebars, screenshot request, progress and notes were edited.
Generated build output uses the specifically requested `GUIDE_OUT=_build/RV-GUIDE`.
No reference instance, database, sample model, application code or shared coverage report was changed.
No servers or background services were started. No commits or state-changing Git commands were used.

## Assignment qualifications

- The reference sample paths are `guide/samples/README.md` and `guide/samples/SOURCES.md`.
- The sample model has no carried relationship attributes. New examples are explicitly illustrative
  extensions, with fictional values and named prerequisites, not captured reference responses.
- `consumer-example.py` validates the alternative stops v2 declaration against the real compiler,
  after adding two global attributes and assigning them to the existing stop/operator binding in memory.
- `check-examples.py` parses the JSON fences and validates both grid selections using the real input model.
  No HTTP/read/write integration test was run or claimed.
- The relationships-table creation dialog derives filters, sorts and page size 20. There are no separate
  creation fields for those; detailed changes require the specialist view. Both Layout labels are verified.
- Grid filters and bulk change exclude JSON. Carried fields themselves can have all eight value types.
- Click-outside behavior is not identical for all matrix fields: record editors have an explicit
  unchanged-only outside-close handler; relationship editors submit on blur. Pages describe that distinction.
- Existing matrix screenshot/caption `matrix-cell-editor.png` depicts the old form. The wave specifically
  requires retaining it. A separate current table/editor screenshot is requested; appearance is unverified.
- No wave-specific coverage rows were found. The global inventory checker reports all 911 entries covered
  (902 on pages, 9 excluded), zero uncovered. The existing checker normally overwrites
  `_coverage/inventory/uncovered.md`; `coverage-output.mjs` redirects only that output to these notes.

## Product issue found

`frontend/src/features/model-editor/relationTableView.ts` offers every carried attribute in
`attributeOptions`, then `configOf` adds each selected attribute to sortFields without excluding JSON.
The validator rejects JSON sorts. A compiler reproduction of that generated shape fails with
`INVALID_MODEL` at `/applications/network/views/relationship-json-example/config/sortFields/2`.
JSON may be a displayed relationship column, but its generated sort must be omitted. The guide gives
scalar selection or specialist configuration as a workaround. The application remains unchanged.

## Checks

- Isolated build: passes, 257 pages. See build.log (and final-build.log after last prose corrections).
- Terms and brand: passes, 257 pages.
- Coverage: passes, 911 entries, zero uncovered; output redirected to wave notes.
- Internal link/anchor check: nine failures, all image references for the seven requested screenshots.
  No missing page links or anchors. It cannot pass before the requested captures exist.
- Full `npm run verify` is not a green gate: its components were exercised separately so the coverage
  output remains inside the allowed files. Missing screenshot references remain explicit.

## Source map

- Carried definitions: targeted sections of APPLICATION_MODEL.md and the model-editor relation operation.
- Model creation: operations.ts tableFields/Layout operation; relationTableView.ts generation and schema validation.
- Record panels: panels/RelationsPanel.tsx and relations/relationAttributeColumns.ts.
- Matrix cells: RelationMatrixCellDialog.tsx, RelationMatrixCellTable.tsx, EditableField.tsx,
  relations/RelationValueCell.tsx, ui/FloatingCellEditor.tsx.
- Tables/grid: RelationTableView.tsx, RelationTableLayout.tsx, RelationGridView.tsx,
  RelationGridRow.tsx, RelationGridLocations.tsx, RelationGridChangeDialog.tsx, model/relationGrid.ts,
  SelectionBar.tsx; API.md relationships table and grid sections and actual routers/schemas.
- Consumer values/matches: CONSUMER_API.md relationship source rules; consumer editor pickers;
  consumer_api_rules.py, consumer_objects.py, consumer_parameters.py, consumer_xref.py and events/plan.py.
- Management atomic writes: routers/relations.py, routers/mapping.py, commands.py,
  relation_grid_change.py and relation_batch.py. CURRENT_FUNCTIONALITY.md and UI_MODEL.md were cross-checked
  in the relevant sections. No need to read broad architecture/product decisions for this writing wave.
