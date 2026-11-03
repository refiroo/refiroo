# C3-MODEL screenshots wanted

Existing `/docs/screens/model-*.png`, workbook and workspace captures are reused where their screens match the task. These additional captures need the reference instance and are not fabricated by this wave. Use only the public Graubünden reference data. A requested image remains a placeholder until captured.

| Filename | Pages | Screen and state | Must be visible |
| --- | --- | --- | --- |
| model-workbook-map-column.png | guide/model/map-a-column | Workbook draft, Map to… open on a reference-data column | Source column, row type, What the column holds, destination and applicable matching/value-type choices; no unrelated organisation data. |
| model-workbook-value-map.png | guide/model/map-a-column | Workbook column, value map dialog open | Text in the file, Becomes, at least one meaningful replacement, remove control and confirmation. |
| model-workbook-list-range.png | guide/model/read-lists-in-a-sheet | Source Lists, selected detected list | Under, Cells, Note, Loads, shaded header and data range, Adjust list…, Don't load this list; use a list from the reference workbook. |
| model-migration-review.png | model/migrations; guide/model/migrate-a-workspace | Finished migration preview before confirmation | Workspace and target release, Nothing has changed yet, missing type/field Became / Not kept choices, Converted / Type changed / Removed / Must be fixed counts and item rows. |
| model-migration-loss-confirm.png | guide/model/migrate-a-workspace | Preview with a deliberate, reviewed removal | Removed items and count, acceptance checkbox, exact migration action, destination; no execution needed to capture. |
| model-migration-stale.png | guide/model/migrate-a-workspace | Preview invalidated by a controlled intervening edit | Notice saying nothing migrated, Close and Preview again; capture on an isolated reference-data workspace. |
| model-language-raise-review.png | guide/model/raise-a-model-language-version | Older-language workspace, Review the change preview | Schema language, Consumer APIs rewritten, Workspaces that return, unchanged records/change sets/publications, Cancel and Raise and reopen. Requires an isolated historical-release fixture; do not alter the reference's running release to obtain it. |

## Capture limits

The wave verifies labels from source, not a new live browser run. Some existing workbook images describe a fictional transport workbook; prose is retained as a clearly marked example. Their captions and correspondence need visual confirmation during the screenshot pass. Missing requested images cause the global link checker to report missing sources, while Markdown compilation can pass.
