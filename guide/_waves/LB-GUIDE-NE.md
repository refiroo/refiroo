# LB guide: Hide inactive hides exactly the marked records; the sidebar search is a phrase

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

A product fix after the first LB build (CHANGELOG, Unreleased, "Added (list browsing: ...)", the availability bullet; plan
`docs/BASE_0_13_IMPLEMENTATION_PLAN.md` LB-D9). The code wins: `frontend/src/features/objects/ObjectToolbar.tsx`
(`HideInactive`), `frontend/src/features/objects/filters/FilterBar.tsx` (`pillText`), `backend/app/engine/reads/object_query.py`
(`ne`), `docs/API.md` (booleans and `ne`), `frontend/src/model/collections.ts` (`narrowNavigation`).

## What the product does now (check each point in the code)

- **Hide inactive** hides exactly the records the table marks Inactive: those whose yes/no value is No. A record with no
  value at all is not marked and is not hidden by the switch. The filter the switch adds is shown as a pill that reads
  the field and **not No** (for the Active field: "Active: not No"); it is kept in the page address and removed like any
  filter. The number in the switch's name counts the records whose value is No (with the list's search and other filters),
  so it is the number of rows the switch will hide. It is written even when it is 0.
- The earlier wording that "the Yes filter also excludes records with no value" is about the ordinary **Filter** menu's
  Yes choice for a yes/no field, which still keeps only the records that are Yes. Keep that true where a page says it, but
  say that the switch is different and does not use it.
- In the API, a list's filter on a yes/no attribute takes `ne`: `filter.<attribute>.ne=false` keeps the records whose value
  is not false, a record with no value included. `docs/API.md`, "booleans support `eq` and `isNull`" paragraph. If a guide
  page for integrators lists the filter operators, add it there; otherwise add nothing.
- **Find a list** matches the words as one phrase, not word by word: typing "eye col" finds "Eye colours" but typing
  "colours eye" finds nothing. Say it plainly where the page describes the search, once.

## What to do

- Fix each passage that no longer matches in the page that owns it. Keep each page's voice and structure. Candidates:
  `use/lists-and-filters.md`, `guide/use/find-records.md` (the switch, the pill, the no-value note), `use/applications.md`
  (the phrase), `model/record-pages-and-tables.md` and `guide/model/choose-table-columns-filters-and-sort.md` if they say
  what the switch hides, and an integrator page that lists the filter operators if one exists.
- No new pages. Pictures: list in the report any picture the text calls for that is not taken yet.

## Files you may edit

- `src/content/docs/use/lists-and-filters.md`
- `src/content/docs/guide/use/find-records.md`
- `src/content/docs/use/applications.md`
- `src/content/docs/model/record-pages-and-tables.md`
- `src/content/docs/guide/model/choose-table-columns-filters-and-sort.md`
- `src/content/docs/integrate/identifiers-paging-and-errors.md`
- `_waves/progress/LB-GUIDE-NE.md`

## Report

Per page: what changed and why (one line each), what you checked and left, pictures needed, and any point the guide cannot
describe honestly.
