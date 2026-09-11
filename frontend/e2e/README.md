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


## Slice D: immutable history and historical sources

```sh
npm --prefix frontend run test:browser:history
```

The isolated real-backend runner exercises SC-08: newest-first history, an unchanged typed older
snapshot under its pinned model, revision context through shared list/detail reads, immutable controls,
an explicitly labelled historical draft source, pinned/current model mismatch guidance, truthful
publication retirement, and catalogue retirement as a separate read-only state. It records screenshots,
server logs and `report.json` in its printed temporary evidence directory.

Exact failed-page retry is additionally locked by the focused history-feed component regression; the
real-backend runner uses the API's normal bounded page. WP10 still owns composed release, full
accessibility/visual, migration and packaging acceptance.

## UI-01 navigation foundation

`test:browser` also checks the compact shell, all configured Master/System views, hierarchy
continuation across mode changes, touch/keyboard drawer dismissal and focus restoration, retained
search and collection position, named drafts in two workspaces, and desktop/mobile model navigation.
It captures 1440px and 390px screens plus a 720px CSS viewport for 200%-zoom-equivalent reflow.
This is not an operating-system browser-zoom or manual assistive-technology test.

## UI-02 collection controls

`test:browser` additionally exercises Filter chips, zero/false and date operations, null/unset
distinctions, cursor reset, heading and menu sorting, column visibility, density, URL-backed page
size/reload, mobile column access and popover focus for Domain and System collections. The embedded
Codelist collection exercises display/page-size controls at desktop and 390px, alongside its existing
failed-page preservation/retry checks. Successful requests use the isolated real backend. Screenshots
and `report.json` are recorded with the navigation evidence. This does not supply UI-07 automated
accessibility/visual baselines or UI-05 preference persistence.

## UI-03A navigation preservation

`test:browser` includes `ui03a-navigation.mjs` in the same isolated backend harness. Domain and System
records in Live and a named Draft retain filtered later-page origins through record reload and
Back/Forward. At 1440px and 390px it verifies cancelled navigation preserves editable input, explicit
discard permits navigation, native reload cancellation retains the form, and a delayed real save
blocks Back until completion. Cross-application related-record reload returns to the original list.
The existing authoring and draft runners exercise successful writes, conflicts and signed deletion
through the guarded record editors. Evidence is written to the runner's temporary output directory.
This section records the UI-03A navigation coverage. UI-03B extends it below; UI-07 remains deferred.

## UI-03B inspector and record actions

The navigation runner now checks the full-width collection-record default, reload/Back/Forward,
canonical Copy link, all configured panel headings, mobile single-screen layout, real save refresh,
right-click and keyboard row menus, and last-row deletion with filter-preserving page recovery.
Domain and System are covered in Live and Draft at 1440px and 390px. The hierarchy regression starts
in a codelist record and selects a master value from Browse hierarchy: the unrelated collection
must disappear, Value details must be available in the full record view, and reload must preserve it.

The live-authoring, draft and history runners use the visible Record actions menu and retain their
mutation, conflict, signed-deletion and read-only assertions. UI-07 remains deferred; these screenshots
and interaction checks do not establish an accessibility audit or automated visual baselines.

### Hierarchy preferences correction

The navigation runner also verifies Browse hierarchy first and selected on the first visit, saved
Views/hierarchy selection across reloads without changing the selected record URL, separate branch toggles that
retain the selected record, collapsed and expanded state restored across real reloads, and keyboard
expansion at desktop/mobile widths. Preferences are browser-local per workspace/application.
See [correction evidence](../../review-notes/frontend-redesign-2026-09-10/hierarchy-preferences-evidence/README.md).
