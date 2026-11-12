# CANVAS-GUIDE report

## Pages written

`guide/src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md` — **Shape a workbook on the canvas**:

- Open the canvas and read the page
- Make object types and map columns
- Connect object types
- Read several columns as rows
- Correct how the sheet is read
- Add filters and arrange navigation
- Check refused rows and correct a value
- Undo, then finish
- On a phone

`guide/src/content/docs/guide/model/edit-a-model-on-the-canvas.md` — **Edit a model on the canvas**:

- Open a draft on the canvas
- Find what you need on the board
- Add and rename definitions
- Use an element's menu
- Connect object types and inspect a line
- Work in the inspector
- Review issues and history
- Finish or return later

## Other pages changed, with before and after

The exact changed passages, including additions and the sidebar entries, are in
[page-changes.md](page-changes.md). All content paths there are relative to `guide/`.

- `src/content/docs/use/workspaces.md`: Adjust opens the canvas; creation is hidden when there is no completed usable result.
- `src/content/docs/guide/model/find-your-way-around-the-editor.md`: select Editor for the described panes; link to Canvas; identify the + Add menu.
- `src/content/docs/guide/model/map-a-column.md`: one sentence linking to canvas column drops.
- `src/content/docs/guide/model/read-lists-in-a-sheet.md`: one sentence linking to canvas sheet drops and reading choices.
- `src/content/docs/model/models.md`: include the canvas among model-building routes and subsequent tasks.
- `src/content/docs/model/the-model-editor.md`: identify the two views, remembered opening view, workbook default and + Add menu.
- `src/content/docs/model/workbook-onboarding.md`: identify canvas shaping, the shared draft and Adjust before workspace creation.
- `sidebar/model.mjs`: general canvas guide follows Find your way around; workbook canvas guide follows Read lists in a sheet.

## Differences from the changelog or plan

The pages follow the code, including the later shared-editor changes which supersede the original workbook-canvas design.

1. The original gesture table includes a sheet dropped onto an attribute to create a relationship. `BoardCard.tsx` accepts columns and attributes; its attribute-row drop handler does not accept a sheet. `CanvasBoard.tsx` handles sheets as sheet-to-board drops. The guides direct readers to Connect between object-type cards instead.
2. The plan promises a menu or keyboard equivalent for every gesture. `WorkbookPane.tsx` has column menus but no sheet-to-board action. The guides give + Object type and column mapping as the general no-drag route, and Editor's Source/list actions for sheets laid out as lists. They do not invent a canvas sheet menu.
3. The plan describes dragging a wrong value onto a correction. `RefusedDialog.tsx` offers See the rows and Correct the values of …; `WorkbookCanvas.correctValues` opens the shared `ValueMapDialog`. The guide uses that dialog. Its suggested unmatched values come from an initial page of refused rows, while the check totals cover the full reading.
4. The earlier PL3b changelog names Open as canvas, Suggest/Apply and Load into an existing workspace. Current `DraftViewSwitch`, `useDraftActions` and `WorkbookCanvas.moreItems` use Editor | Canvas, Propose again…, Apply to this workspace… and Load into a change set…. The later CE1 entries describe these replacements.
5. The earlier canvas footer and “n to fix” strip are superseded by the shared `IssuesDrawer`, as the final CE1 note records. The guides use Issues and history / Issues, history and dry run, and follow issue links to the selected element.
6. The plan calls the remembered opening view a per-person preference. `DraftViewSwitch.tsx` stores it per draft in this browser; the guides say so. Positions, folds and scope are stored on the draft, while zoom is stored in the browser.
7. At phone width `CanvasBoard` uses flow layout: no application frames, relationship lines or zoom. `WorkbookCanvas` hides Tidy and disables dragging. The guides describe the menus and panels rather than implying the desktop board is unchanged.
8. `NewFromWorkbook.tsx` hides Create workspace when no list was found or the check is incomplete. The pre-existing Workspaces page called it unavailable; the correction says hidden.

## Things in refiroo that looked wrong or remain uncertain

These are code observations, not browser reproductions; no application code was changed.

- In `WorkbookCanvas.link`, choosing None of them in `TiePopover` leaves the header undefined, then the same-sheet fallback can still select a column. The guide says this choice *asks* for an unfilled link and directs readers to inspect the result, especially for object types reading the same sheet. Its behaviour should be checked in the browser before promising that it always leaves a link empty.
- Missing canvas sheet-menu parity and the sheet-to-attribute gesture are described above. The documented alternatives are available controls, rather than claims that those planned gestures exist.
- `useCanvasDocument` suppresses failures while saving arrangement changes, leaving the local display as placed. A failed save can therefore lose positions, folding or scope on reopening without an explanation. The guide describes their normal persistence, not a guarantee under failure.
- Preview/layout entry controls depend on an available running model (`activeModel`). The guide describes them conditionally. New-model preview, workbook load, keyboard and phone behaviour were checked in source only, not exercised in a browser in this wave.

## Screenshots needed

No image references were added. Every requested screenshot is **1440 pixels wide**, taken later from the reference instance with Graubünden public-transport data. The example belongs in the caption; the task text remains generic.

### Shape a workbook on the canvas

| Picture | Screen and state | Must be visible |
| --- | --- | --- |
| Opening and three parts | Canvas after Adjust, with a proposed workbook draft | Editor/Canvas switch, Workbook sheets and columns, First rows, object-type cards, Inspector, Proposed marks and latest check strip. |
| Mapping and connection | Canvas with an attribute mapped and two object types connected | Source column, destination row and column label, Connect, solid containment and dashed relationship, line rule controls. |
| Tied join | Which column names the … records? open | Both candidate headers, column letters, matched-row counts and None of them, with starting card for context. |
| Columns read as rows | Selected language columns and Read … columns as rows question | Multi-column selection and both new-column name inputs; capture the resulting added columns separately if they cannot be shown together. |
| Reading the sheet | First rows beside a column's Readings menu | Header row and row numbers, Fill blanks from the cell above and Rows holding only this column are headings…; an additional open heading question should show its new column and parent choices. |
| Filters and navigation | Navigation tab open after placement | Card's Filters, Connect, application groups and entries, New group and Not in a group. |
| Refused rows | An object type's rows refused dialog | Refusal count and reason, unmatched values, See the rows and Correct the values of …; an additional value-map picture should show Text in the file, Becomes and Save the value map. |
| Finish | Create workspace dialog after a completed check | Name, load/refusal figures, Cancel and Create workspace, with the draft canvas behind it. |

### Edit a model on the canvas

| Picture | Screen and state | Must be visible |
| --- | --- | --- |
| Whole model | A released model with a small draft change | Whole model / Changed in this draft / From the workbook, application frames, New/Changed/Released marks, folded card, quieter unchanged card and zoom/Fit. |
| Add and edit | Header + menu open on a draft without a workbook | Application…, Object type…, Attribute type…, Relation type…, Navigation group…, a card's New attribute and the no-workbook panel. |
| Attribute inspection | An attribute selected with Inspector open | Name, Value type, Required, Unique, Read-only, Filled by and its operations menu, including Move to… where offered. |
| Relationship rule | A relationship line's rule popover | How many, Required, Attributes of the relationship, Which records may be chosen and All operations. |
| Navigation and views | Navigation tab with group/entry operations, then Views for an object type | Application/group/entry menus; in the second picture, view names, Preview tables and record page and Edit layout. |
| Layout | Preview/layout opened inside the canvas | The editor's existing layout surface and Back to the board. |
| Consumer contract | Consumer APIs tab with an existing contract selected | Add control, contract list and its shared detail panel. |
| Review | Issues drawer with a useful issue, then History | Issue counts and destination; saved steps and undo action; with a workbook, the Dry run tab. |

Phone instructions were source-checked; no phone image reference was introduced. A later 390px capture would be useful for the stacked layout, but it is outside the wave's requested 1440px screenshot list.

## Validation

Results are recorded after the commands finish in the progress file and appended here.

- `GUIDE_OUT=_build/CANVAS-GUIDE npm run build` — **passed**, 259 pages, 6.87 seconds.
- `GUIDE_OUT=_build/CANVAS-GUIDE npm run verify` — **failed at inventory freshness**. Its build passed (259 pages, 9.07 seconds), and terms, brand and sidebar passed. The stored `management-api.json` and `screen.json` do not match current source. Regenerating those files is outside the wave's permitted edits; no inventory regeneration was performed.
- `GUIDE_OUT=_build/CANVAS-GUIDE npm run check:coverage` — **failed**, six unmatched entries in the stored inventory. They include the superseded Open as canvas, Remove list and Make a list of its values labels, two label-less menu entries, and the heading-clear entry. The guide documents the current controls rather than adding obsolete UI labels to force this check green.
- `GUIDE_OUT=_build/CANVAS-GUIDE npm run check:links` — **passed**, 77,178 local links and sources across 259 built pages.
- `node --check guide/sidebar/model.mjs` — **passed**.

The coverage command writes its generated `_coverage/inventory/uncovered.md` report as a side effect; the six-entry result is also captured in this wave's `coverage.log`. Authored edits stayed within the assigned pages, sidebar, progress and notes. No git state-changing command or commit was run. No application server or database was started. This wave did not exercise browser flows or inspect rendered appearance; requested screenshots remain to be taken. Logs are bounded, completed command outputs under `_coverage/notes/CANVAS-GUIDE/`.
