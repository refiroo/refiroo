# LB guide review

## Evidence and limits

- Read `guide/AGENTS.md` and the wave in full. Top-level AGENTS instructions were excluded as requested. No LB steering or previous progress existed at the start; steering was checked before each page.
- `Explorer.tsx`: threshold is more than 10 entries, `role="status"` count, hint only during a nonempty search, Enter opens the first match, Escape clears, fold buttons replaced during search. Existing Browse records search remains separate.
- `model/collections.ts`, `narrowNavigation`: trimmed, case-insensitive substring of each entry label; it does not split the text into words or search group names. Collections and matrices placed in groups count with ungrouped collections.
- `ObjectTable.tsx`: only an exact No marks a row; neutral pill after its identity. `model/fields.ts`, `unavailableWord`: Active becomes Inactive, other names become Not plus the lower-case attribute name.
- `ObjectToolbar.tsx`, `HideInactive`: the switch replaces conditions on the chosen field with Yes when on, removes them when off, and counts No after removing conditions on that same field. The count can be omitted on loading/failure. Yes excludes unset values too, although they are unmarked and not counted. This is a product wording pitfall, explicitly documented rather than claiming only marked rows disappear.
- `CollectionView.tsx` passes the table setting to its rows; the toolbar includes the switch's field in its filter pills even when not declared in the ordinary filter menu.
- `layout.ts`, `tableAvailabilitySpec`, and `TypePreview.tsx`: exact button/dialog/field labels, None and bound boolean fields. Backend `application_rules.py` validates a boolean attached to the table's type. No arbitrary non-boolean/foreign field can be chosen in the dialog; refusal is a model validation rule.
- Compared relevant Table view / Inactive records contract and CURRENT_FUNCTIONALITY passages. No browser verification: the wave says the needed reference-instance configurations do not exist yet.

## Checked and retained

- `use/applications.md`: ungrouped-first ordering, remembered group folds, direct matrix entries, group-page search and context, collection view tabs. No change to these mechanisms in the inspected navigation path.
- `use/lists-and-filters.md`: ordinary filter pills and Yes/No behavior, one sort, Display, long-list position and context. The switch uses these existing filter controls.
- `guide/use/find-records.md`: workspace/context selection, text search, ordinary and relationship filters, sort and Back to list. New list search supplements choosing the collection.
- `model/record-pages-and-tables.md`: table columns, Filters, related columns, panel settings, sort menu and sizes. The new field is a table-view setting, not a record-page panel setting.
- `guide/model/choose-table-columns-filters-and-sort.md`: layout entry, column selection, Filters, Default sort and Sort menu and page size steps. The new control is alongside these, without changing their purpose.

## Screenshot handoff

Names below identify capture requests, not invented image filenames. Keep existing image references until captures can be supplied.

1. Sidebar list search — `use/applications.md`, reused by `guide/use/find-records.md`: an application with more than ten entries, total count empty; then a phrase matching grouped and ungrouped entries, bold matches, open matching groups, no fold buttons, filtered count and keyboard hint; also No list matches. Existing app-network and app-navigation-matrix-entry pictures still illustrate valid configurations and do not need replacement merely for lacking a conditional search.
2. Inactive table — `use/lists-and-filters.md`, reused by `guide/use/find-records.md`: a table using Active, with Yes and No rows, a grey Inactive pill after the quieter No row's name, and Hide inactive (N) off. A second state should show it on with Active: Yes and excluded rows absent. Include an unset value to demonstrate the count/Yes-filter distinction. Existing list-filter-pills, stops-filter-menu and stops-filtered-sorted pictures remain valid for tables without the setting.
3. Table layout toolbar refresh — `guide/model/choose-table-columns-filters-and-sort.md`: existing `model-layout-table-tab.png` shows the changed surface; recapture with Columns…, Filters…, Inactive records…, Sort menu and page size… and Default sort visible.
4. Inactive records dialog — `model/record-pages-and-tables.md` and `guide/model/choose-table-columns-filters-and-sort.md`: table layout context, dialog title naming the view, A record is inactive when this is No, None and the type's Yes/No choices, Apply. Use only reference data once a suitable model exists.

## Product points needing care

The guide cannot honestly describe search as separate-word matching or the switch as hiding only marked rows. It documents the implemented phrase match and Yes filter. No claim of visual/browser acceptance or new screenshots is made. The other inspected behavior can be described from current code; appearance needs reference-instance captures.

## Validation

Final isolated guide build passed: `GUIDE_OUT=_build/LB-GUIDE npm run build` in `guide/`, 257 pages in 3.36 seconds. Scoped whitespace check passed; 11 built local fragment links resolved. Build warning: /404 route conflict. No browser or screenshot acceptance was performed.
