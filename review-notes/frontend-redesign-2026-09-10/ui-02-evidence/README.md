# UI-02 — Focused collections and table controls

Completed 2026-09-10 on the existing UI-01 working tree. No commit created. Executed UI-02 at the
user's explicit request; the recommended UI-07-first ordering was disclosed and UI-07 remains open.

## Delivered

- Visible search and one Add action; configured typed operations in a React Aria Filter popover.
  Applied chips remove only the corresponding filter. Existing Clear filters also clears search.
- Supported headings toggle the existing single sort; the Sort disclosure offers all configured
  ascending/descending choices, including hidden columns. Only the active heading has an indicator.
- Shared Display controls for top-level and embedded collections: configured column visibility,
  protected record identity, comfortable/compact density and bounded page size.
- Top-level page size remains URL-backed; embedded page size belongs to the mounted panel.
  Display settings are temporary and do not alter query/page/context. UI-05 owns persistence.
- Sticky headings within a bounded scroll region, row hover/focus highlighting, mobile identity plus
  two configured fields, and an explicit Show all columns toggle for horizontally scrolling the rest.
  Record links still open the existing detail page; inspector selection belongs to UI-03.
- Loading counts, empty results and failed reads remain distinct; failed continuation retains rows
  and retries the same request. No backend, API, model or persistence changes.

## Validation

From `frontend/`, after the final source/test changes:

- `npm run format` — passed.
- `npm run lint` — passed, zero errors and 12 existing hook warnings in unchanged modules.
- `npm run test` — 26 files, 123 tests passed.
- `npm run build` — passed; Vite reports the existing >500 kB chunk warning (520.09 kB JS).
- `git diff --check` — passed.

An initial build caught unsupported Testing Library `exact` options in the new tests; those were
removed and final gates rerun. An immediate browser focus assertion was changed to wait for React
Aria's asynchronous focus restoration; the final assertion passes without weakening its target.

From the repository root:

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser
```

Passed on Chrome **152.0.7977.83**, with no page errors. See [report.json](report.json).
The harness used temporary Vite/FastAPI servers, a temporary model and an isolated SQLite database;
it did not access the configured development database. Local-server execution required sandbox
escalation because the initial attempt returned `listen EPERM`.

Browser coverage includes Domain and System collections at **1440×1000** and **390×844**, numeric
zero, boolean false, date comparisons, isUnset/isNull, chip isolation, header/menu sorting, page-size
reset, column hiding, density, URL reload, all mobile columns and Escape/focus restoration. The
embedded Codelist panel covers display/page-size controls on desktop/mobile and exact failed-page
retry while retaining loaded rows. Existing navigation checks cover search/filtered later-page
restoration, Back/reload, two workspaces, Live/named Draft context, detail/panel failures, hierarchy,
cross-application navigation and **720×500** zoom-equivalent reflow.

Component tests exercise typed controls/query ownership for Domain and Codelist, and embedded
collection display changes without extra reads for both types, alongside existing failure/retry tests.

## Representative screenshots

- [Domain filter popover](ui02-domain-filters.png)
- [System filter popover](ui02-system-filters.png)
- [Domain compact desktop](ui02-domain-desktop.png)
- [System compact desktop](ui02-system-desktop.png)
- [Domain mobile, all columns exposed](ui02-domain-mobile.png)
- [System mobile, all columns exposed](ui02-system-mobile.png)
- [Embedded Codelist mobile](ui02-embedded-mobile.png)

Screenshots were visually inspected. Automated keyboard/touch/focus checks are bounded interaction
evidence, not a manual assistive-technology session, full accessibility audit or visual-regression
baseline. UI-07 and WP10 remain open; authoring/draft/history runners were not rerun for this bounded
collection package. Existing history journeys were preserved, not reimplemented.
