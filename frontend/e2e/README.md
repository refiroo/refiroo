# WP9 browser regressions

Run from the repository root after installing frontend dependencies and the Python
3.14 backend environment:

```sh
frontend/node_modules/.bin/playwright install chromium
npm --prefix frontend run test:browser
```

To use an existing browser instead of downloading Chromium, set
`PLAYWRIGHT_EXECUTABLE_PATH` to its executable. On macOS, for example:

```sh
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser
```

The runner starts local Vite and FastAPI servers on temporary ports, creates a
fresh SQLite database and a starter-model variant in the system temporary folder,
and seeds all records through real APIs. It does not use the development database.
It stops its servers on completion and prints the evidence directory containing
screenshots, server logs and `report.json`.

SC-01 covers Domain and System collections with numeric/date filters, two
workspaces, later-page restoration, browser Back and reload, detail and panel
retries, genuine empty translations, cross-application navigation, both containment
paths, audit reads, and a narrow-screen keyboard navigation check. Simulated 503s
exercise retry behavior; successful reads always reach the real backend.

This is bounded WP9-A evidence. It does not establish complete CRUD, draft/history
publication journeys, a full accessibility audit, visual regression baselines or
WP10 release acceptance.


## Slice B: direct live authoring

```sh
npm --prefix frontend run test:browser:authoring
```

The same `PLAYWRIGHT_EXECUTABLE_PATH` override works for this runner. It starts its
own isolated backend/database and Vite servers, uses the starter model with numeric
fields and a typed ordinary relationship attribute, and writes screenshots and a
JSON report to a temporary evidence directory.

SC-02/SC-03 and live SC-04 cover root and child creation, coherent typed edits,
zero/false, availability filtering, parent moves, ordinary relationship CRUD,
translations from a target and a group, required-content and duplicate rejection
without partial records, individual fields, explicit conflict reconciliation,
cancellation, signed deletion impact and stale-preview refusal. Master containment,
required translation ownership and independent System/Translation hierarchies are
exercised. It also checks keyboard/focus at 390×844, catalogue retirement, and that
live authoring creates no drafts or revisions.

This does not close slices C/D or WP10. Full accessibility/visual audits and composed
release, migration, installed-wheel and draft/history acceptance remain separate.


## Slice C: optional drafts and publication

```sh
npm --prefix frontend run test:browser:drafts
```

The same installed-Chrome override works here. This runner creates an isolated SQLite
backend and temporary starter model, enables workspace lifecycle mutations, and exercises
SC-05/SC-06 and draft SC-04 through the browser. It covers current-live capture without
publication and after later live edits, two-type editing with zero/false, translation creation
with required ownership, individual fields, ordinary relationships, route/reload context,
aggregate/record conflict reconciliation, successful publication preserving unrelated live work,
touched-record refusal, invalid final merged graph, discard/cancellation, and signed deletion
with stale-preview recovery across Master and System containment. Narrow-screen Escape and
focus restoration are exercised at 390×844. All successful reads and writes reach the real API.

The runner asserts canonical draft write paths and both concurrency contexts and records
screenshots, server logs and `report.json` in its printed temporary evidence directory.
History/historical-source acceptance remains slice D; WP10 composed release, full accessibility,
visual, migration and packaging gates remain separate. Backend code and public contracts are
unchanged by slice C, so its final unit/build gates are frontend-only.
