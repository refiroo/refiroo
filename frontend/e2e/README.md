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

WP-11 has a focused model-version-dialog journey:

```bash
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend run test:browser:wp11
```

It installs a second compatible model release in an isolated database, opens the change set
version-change dialog at normal and narrow widths, checks focus containment and dirty-input refusal,
applies the release, and writes screenshots plus `report.json` to its printed temporary directory.
Historical unsupported-release rendering remains covered by the focused component and real HTTP
regressions; comprehensive accessibility and visual-baseline gates remain WP-9 acceptance work.

The runner starts local Vite and FastAPI servers on temporary ports, writes a
starter-model variant to the system temporary folder, clones a database of its own on the
development PostgreSQL server (`scripts/postgres.sh start` first) and seeds all records
through real APIs. It does not use the development database `rdm`, and drops its own
database when it ends.
It stops its servers on completion and prints the evidence directory containing
screenshots, server logs and `report.json`.

SC-01 covers Domain and System collections with numeric/date filters, two
workspaces, later-page restoration, browser Back and reload, detail and panel
retries, genuine empty translations, cross-application navigation, both containment
paths, audit reads, and a narrow-screen keyboard navigation check. Simulated 503s
exercise retry behavior; successful reads always reach the real backend.

This is bounded WP9-A evidence. It does not establish complete CRUD, change-set/publication
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
live authoring creates no change sets or publications.

This does not close slices C/D or WP10. Full accessibility/visual audits and composed
release, migration, installed-wheel and draft/history acceptance remain separate.


## Slice C: optional change sets and publication

```sh
npm --prefix frontend run test:browser:change-sets
```

The same installed-Chrome override works here. This runner creates an isolated PostgreSQL
backend and temporary starter model, enables workspace lifecycle mutations, and exercises
SC-05/SC-06 and change set SC-04 through the browser. It covers current-live capture without
publication and after later live edits, two-type editing with zero/false, translation creation
with required ownership, individual fields, ordinary relationships, route/reload context,
aggregate/record conflict reconciliation, successful publication preserving unrelated live work,
touched-record refusal, invalid final merged graph, discard/cancellation, and signed deletion
with stale-preview recovery across Master and System containment. Narrow-screen Escape and
focus restoration are exercised at 390×844. All successful reads and writes reach the real API.

The runner asserts canonical change set write paths and both concurrency contexts and records
screenshots, server logs and `report.json` in its printed temporary evidence directory.
History/historical-source acceptance remains slice D; WP10 composed release, full accessibility,
visual, migration and packaging gates remain separate. Backend code and public contracts are
unchanged by slice C, so its final unit/build gates are frontend-only.


## Slice D: immutable history and historical sources

```sh
npm --prefix frontend run test:browser:publications
```

The isolated real-backend runner exercises SC-08: newest-first history, an unchanged typed older
snapshot under its pinned model, publication context through shared list/detail reads, immutable controls,
an explicitly labelled change set started from a publication source, pinned/current model mismatch guidance, truthful
publication withdrawal, and catalogue retirement as a separate read-only state. It records screenshots,
server logs and `report.json` in its printed temporary evidence directory.

Exact failed-page retry is additionally locked by the focused history-feed component regression; the
real-backend runner uses the API's normal bounded page. WP10 still owns composed release, full
accessibility/visual, migration and packaging acceptance.

## UI-01 navigation foundation

`test:browser` also checks the compact shell, all configured Master/System views, hierarchy
continuation across mode changes, touch/keyboard drawer dismissal and focus restoration, retained
search and collection position, named change sets in two workspaces, and desktop/mobile model navigation.
It captures 1440px and 390px screens plus a 720px CSS viewport for 200%-zoom-equivalent reflow.
This is not an operating-system browser-zoom or manual assistive-technology test.

## UI-02 collection controls

`test:browser` additionally exercises Filter chips, zero/false and date operations, null/unset
distinctions, cursor reset, heading and menu sorting, column visibility, density, URL-backed page
size/reload, mobile column access and popover focus for Domain and System collections. The embedded
Codelist collection exercises display/page-size controls at desktop and 390px, alongside its existing
failed-page preservation/retry checks. Successful requests use the isolated real backend. Screenshots
and `report.json` are recorded with the navigation evidence. Display preference persistence is
exercised; this does not supply UI-07 automated accessibility/visual baselines.

## UI-03A navigation preservation

`test:browser` includes `ui03a-navigation.mjs` in the same isolated backend harness. Domain and System
records in Live and a named Change set retain filtered later-page origins through record reload and
Back/Forward. At 1440px and 390px it verifies cancelled navigation preserves editable input, explicit
discard permits navigation, native reload cancellation retains the form, and a delayed real save
blocks Back until completion. Cross-application related-record reload returns to the original list.
The existing authoring and change set runners exercise successful writes, conflicts and signed deletion
through the guarded record editors. Evidence is written to the runner's temporary output directory.
This section records the UI-03A navigation coverage. UI-03B extends it below; UI-07 gate delivery is recorded below.

## UI-03B inspector and record actions

The navigation runner now checks the full-width collection-record default, reload/Back/Forward,
canonical Copy link, all configured panel headings, mobile single-screen layout, real save refresh,
right-click and keyboard row menus, and last-row deletion with filter-preserving page recovery.
Domain and System are covered in Live and Change set at 1440px and 390px. The hierarchy regression starts
in a codelist record and selects a master value from the application browser: the unrelated collection
must disappear, Value details must be available in the full record view, and reload must preserve it.

The live-authoring, change-set and publication runners use the visible Record actions menu and retain their
mutation, conflict, signed-deletion and read-only assertions. UI-07 gates are documented below; these screenshots
and interaction checks do not establish an accessibility audit or automated visual baselines.

### Unified application browser correction

The navigation runner verifies that model-defined collections and runtime records coexist in one
application browser without a navigation-mode switch. Separate branch toggles retain the selected
record, collapsed and expanded state is restored across real reloads, and keyboard expansion works at
desktop/mobile widths. Branch preferences remain browser-local per workspace/application. The linked
Base 0.6 evidence is historical and predates ADR-029's Base 0.7 composition.
See [historical correction evidence](../../review-notes/frontend-redesign-2026-09-10/hierarchy-preferences-evidence/README.md).

## WP-14 contextual collection browser

```sh
npm --prefix frontend run test:browser:wp14
```

Runs a focused real-backend/browser journey for the unified application browser. It opens a
direct-parent-scoped collection, switches between table and mapping lenses without losing scope,
applies the server-backed mapping-status facet, performs a real live mapping replacement, and checks
the inverse configured direction on a second source type. It also checks a narrow drawer without the
former mode switch, runs axe against the composed mapping page and records wide/narrow screenshots.
This is package evidence; the comprehensive accessibility and visual-baseline gates remain WP-9 build
acceptance.

## WP-13C changed-state checks

```sh
npm --prefix frontend run test:browser:wp13c
```

Runs the user-critical states selected in [UI acceptance](../../docs/testing/UI_ACCEPTANCE.md) for 0.7
surfaces: mapping coverage and candidate outages with Retry, filtered-empty and no-match states,
contained contextual-creation refusal, conflict review preserving the attempted choice, the inverse
binding in a named change set with live unchanged, a change-set list outage, and a change set pinned to a non-active
release. Both widths (1440px, 390px), keyboard focus and scoped axe checks are included. Outages are
503 responses held until the Retry click; everything else reaches the isolated real backend.
Screenshots must be inspected against the named reference patterns; the runner does not compare them.

## UI-07 accessibility gate

```sh
npm --prefix frontend run test:a11y
```

Runs axe-core (WCAG 2.1 AA + best practices) on core page types: collection tables (Domain,
System), record detail with panels, change-set editing, publications view, model workbench, the change sets
list and, since Base 0.8 S7, the continuous list and record tree together: the codelist lens at page
3 of 7 (footer fields; since 0.11 X6 the browser's own scrollbar) beside a 60-codelist tree branch scrolling in its group,
with focus on a row inside it, in light and dark. A self-check appends a control the tree may not
own and requires the gate to reject it. Violations not covered by the explicit allowlist in `e2e/accessibility-gate.mjs` fail the
gate. Exceptions require a tracked issue, an exact axe node target and a maximum node count;
page-specific exceptions apply only to their named pages. Additional nodes and changed related-node
sets still fail the gate. The runner also injects new
violations to verify that the exceptions do not hide them. Screenshots and a JSON report are
written to a temporary evidence directory.


## UI-07 visual regression gate

```sh
npm --prefix frontend run test:visual
```

Compares viewport screenshots of the same core page types against committed baselines in
`e2e/baselines/`. A pixel-diff threshold of 0.5% of total pixels is allowed; exceeding it fails
the gate. Missing baselines also fail; only `test:visual:update` creates or replaces them.
Diff and actual images are written to a temporary evidence directory. Capture waits for API requests
and busy panels to settle so a visible heading cannot produce a loading-state comparison.

To accept intentional visual changes:

```sh
npm --prefix frontend run test:visual:update
```

This captures new baselines. Review the updated PNGs in `e2e/baselines/`, then commit them.

`scrolling-list-tree-*` (Base 0.8 S7) captures the codelist lens mid-list with its window
scrollbar and footer beside the expanded tree branch; its data (`helpers/acceptance-data.mjs`
`seedLongList`) is seeded after the other light pages so they are unchanged. Dark variants (`*-dark`)
cover the domain collection, domain detail, change sets list, model workbench and the list and tree. The gate switches with `page.emulateMedia({ colorScheme: "dark" })` and reloads before a
capture so no colour transition is recorded. The accessibility gate repeats core pages and the
settings menu in the dark theme.

## Runners and gates in lanes (TS3)

```sh
npm --prefix frontend run test:lanes -- lb k1 a11y visual   # a list of runners and gates
npm --prefix frontend run test:lanes -- all                 # every runner and both full gates
npm --prefix frontend run test:lanes -- --list              # the names
npm --prefix frontend run test:lanes -- visual --update-baselines
```

`e2e/lanes.mjs` runs the named runners (a file name without `.mjs`, its npm suffix such as `lb`, or
`a11y`, `a11y:security`, `a11y:guide`, `visual`, `visual:security`) in 3-4 lanes, sized to the memory
available when it starts (one lane per 2 GiB, at most four; `--lanes N` or `RDM_LANES` overrides), and
prints and writes one summary: per runner its lane, result, duration and log path. `all` leaves out the
Docker runners (`i3-real-provider`, `dp3-deployment`) and the gates' `--only` parts; name them to run them.
A runner keeps what it already does alone: its own backend, Vite server, Chromium and database clone, now
with ports taken from `helpers/ports.mjs` (reserved by an exclusively created file, so runners starting
together never get the same port) and its own export folder. Only the visual gate writes baselines, and
`--update-baselines` makes the visual runners take turns, so two lanes never write the same file. A runner
needing a fixed port is listed in `FIXED_PORTS` in `helpers/lanes.mjs`: it runs alone on that port and is
refused, with the port named, when another process holds it (none needs one today). Logs are bounded. Each
runner's temporary files (its evidence folders) go to a folder of its own that is removed when it passes and
kept, named in the summary, when it fails or with `--keep`; the output folder (`--out DIR`) holds the logs.

## What a diff touches (TS1)

```sh
npm --prefix frontend run test:changed -- <commit> --list   # the runners and scenario groups the diff selects
npm --prefix frontend run test:changed -- <commit>          # the same, run in lanes
```

`e2e/manifest.mjs` names the source paths each browser runner and each group of accessibility and visual
scenarios covers; a change in `src/ui`, `src/state`, `src/lib` or `src/model` (and `api`, `routing`, `types`,
`app`) selects the entries of every file that imports it, read from the imports; a feature file also selects
the other features that import it, and the shell's frame files select every scenario. A changed `src/` file
no entry covers fails the command. `test:changed` lists
what the diff since `<commit>` (the working tree included) selects and runs it with `test:lanes`; the two
gates run only the selected groups (`--scenario`). A package that changes a screen is finished only when
that screen's runners and accessibility scenarios pass and its changed screenshots are looked at and
re-recorded. `npm run test:gate-helpers` fails when the manifest names a missing path or lacks an entry for
a runner or scenario. The complete gates still run at build acceptance. Details:
[execution guide](../../docs/testing/EXECUTION_GUIDE.md), "what a diff touches". Follow
[AGENTS.md](../../AGENTS.md#work-package-validation) for validation scope and reruns.

## Planned 0.7 scenario extensions

WP-1–WP-3 scopes are frozen. WP-7/WP-8A/WP-8B extend the existing accessibility and visual gates to
version selection/change diagnostics, mapping coverage/target continuation, candidate selection,
conflict recovery, clearing and contextual target creation. WP-9 supplies composed SC-07/SC-15
browser/API evidence with independent bindings and differing same-schema releases, including concurrency
and isolation checks. Existing baseline pages alone do not establish coverage of those new controls.
No new scenario pass is claimed here. See [the 0.7 plan](../../docs/BASE_0_7_IMPLEMENTATION_PLAN.md).
Reuse passing light and dark gates unless relevant code or theme tokens change.

Harness-based runners print `harness timings (ms)` on exit, separating backend, Vite, seed and
Chrome setup from the runner's own checks. Choose runners per changed surface with
[the execution guide](../../docs/testing/EXECUTION_GUIDE.md); every `e2e/*.mjs` module must be listed there.

Run gate-helper regressions (including missing baseline refusal, scoped accessibility exceptions and
browser-runner classification):

```sh
npm --prefix frontend run test:gate-helpers
```


## Base 0.7 WP-9: composed SC-07 and SC-15 acceptance

```sh
npm --prefix frontend run test:browser:sc07
npm --prefix frontend run test:browser:sc15
```

Both use the shared harness and the same installed-Chrome override. `helpers/acceptance-data.mjs` holds
the model variants and records they seed through the real API: an independent mapping binding with an
integer relation attribute, enough master values for a second candidate page, a 25-target ambiguous
row, and SC-15's candidate and incompatible releases. `bootHarness({ transformModel })` starts the
backend on a model variant. Each runner checks browser results against API state, runs scoped axe checks,
captures 1440px and 390px screenshots, and writes `report.json` to its printed evidence directory.

## Base 0.8 S7: composed Track S acceptance

```sh
npm --prefix frontend run test:browser:s7
S7_VOLUME_SCALE=1 npm --prefix frontend run test:browser:s7   # full volume
```

Over the generated volume fixture (seeded by `backend/tests/volume_seed.py`) and the starter model,
in live, change-set and publication: one collection-lens journey per context (wheel scroll both ways, a
scrollbar click from the start, seek by name, **Go to end**, a page number and a copied URL reopened
at the same row), each landing checked against the same context's API read at that position; then a
record deep in the tree (the volume model's deep node through the tree search and its ancestor path;
the starter's master value by keyboard across the codelist window's edge). The lens journey repeats
at 390px. `report.json` records the checks and each context's API read times as the browser saw
them. The S5 and S6 runners keep the per-surface depth (panels, picker, mapping lens, heavy branch).
