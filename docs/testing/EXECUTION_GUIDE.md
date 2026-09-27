# Test execution guide

**Package:** Base 0.7 WP-13B, 2026-09-24. **Inputs:** the [coverage map](COVERAGE_MAP.md) (contract
IDs, tiers T0–T5, risk). **Consumers:** every work package choosing focused checks, WP-13C and WP-9.

This guide answers one question: *I changed this production boundary — which checks do I run?* Pick the
direct group for the boundary you changed, apply the listed shared-boundary expansion, and run
nothing broader unless a concrete uncovered risk says so ([AGENTS.md](../../AGENTS.md#work-package-validation)).
Selection is transparent and manual. No tool here promises perfect impact detection; `vitest related`
follows imports only, and the backend groups are declared, not inferred.

Commands assume the repository root. Backend commands use `backend/.venv/bin/python` (written `py`
below) from `backend/`; frontend commands run from `frontend/`.

## 1. Selection mechanics

### Backend: pytest markers from one manifest

`backend/tests/conftest.py` holds `TEST_GROUPS`, mapping every test module to the contract groups
it is evidence for, and applies them as markers. Select a group with `-m`:

```sh
cd backend && .venv/bin/python -m pytest -m mapping -q
.venv/bin/python -m pytest -m "change_sets and not mapping" -q   # boolean expressions work
```

| Marker | Contracts (coverage map) | Modules | Cases |
| --- | --- | --- | --- |
| `model` | INV-01/02/03/04/06, compatibility classes | `test_model`, `test_model_diagnostics`, `test_model_independence`, `test_model_compatibility` | 125 |
| `model_admin` | C-MOD-*, C-DR-PIN, C-MOD-ACT | `test_model_lifecycle`, `test_build07_wp11`, `test_build07_wp6`, `test_build07_wp9_acceptance`, `test_model_compatibility`, `test_model_schema_upgrade`, `test_wp81a_context`, `test_w5_activation_write_race` | 99 |
| `startup` | C-BOOT, C-MIG, C-SCHEMA-UP, INV-15 (startup) | `test_startup`, `test_migrations`, `test_wp8_audit_migration`, `test_model_schema_upgrade`, `test_snapshot_value_migration`, `test_page_index_migrations`, `test_snapshot_lookup_index_migration`, `test_search_index`, `test_change_set_rename_migration`, `test_matrix_states` | 54 |
| `records` | C-OBJ-*, C-ATTR, C-REL, C-DEL, C-TR, C-HIST-OBJ, INV-05/10/12 (live) | `test_api`, `test_attributes`, `test_relations`, `test_translations`, `test_cascade_delete`, `test_query_foundations`, `test_wp8_review_regressions`, `test_relation_set_versions`, `test_w5_activation_write_race`, `test_matrix_states` | 137 |
| `queries` | C-Q-FILTER, C-Q-SCOPE, INV-07/08/11 | `test_pagination`, `test_typed_table_queries`, `test_query_foundations`, `test_context_read_parity`, `test_paging_contract`, `test_change_set_position_reads`, `test_search_index` | 92 |
| `workspaces` | C-WS-*, C-PUB-RET, INV-14/16 | `test_workspaces`, `test_wp81a_context`, `test_request_scope`, `test_wp8_withdrawal`, `test_build07_wp9_acceptance` | 31 |
| `change_sets` | C-DR-*, C-REV, C-PUB-RET | `test_change_sets`, `test_wp7_canonical_crud`, `test_wp8_*` (except audit migration), `test_wp81b_current_live_bases`, `test_build07_wp6`, `test_build07_wp9_acceptance`, `test_typed_table_queries`, `test_mapping_replacement`, `test_wp8_withdrawal`, `test_context_read_parity`, `test_snapshot_value_migration`, `test_page_index_migrations`, `test_change_set_position_reads`, `test_change_set_write_lookups`, `test_snapshot_lookup_index_migration`, `test_search_index`, `test_change_set_rename_migration`, `test_matrix_states` | 200 |
| `mapping` | C-MAP-R, C-MAP-W, C-MAP-SET | `test_mapping_coverage`, `test_mapping_replacement`, `test_relation_set_versions` | 116 |
| `matrix` | Relation matrix reads, cell writes and stored cell states: cells, states, row state filter, columns, containers, candidates, maintenance on every write path (Base 0.8 A2, A3, A3b) | `test_relation_matrix`, `test_relation_matrix_volume`, `test_relation_matrix_writes`, `test_matrix_states` | 32 |
| `contract` | OpenAPI lock and route inventories | `test_openapi_contract`, `test_paging_contract` | 40 |
| `volume` | Track S read and write budgets and the paging contract over the generated volume fixture (Base 0.8 S1, S2b, S3, S4, S4R1, S4R6, S7, S8, A2) | `test_volume_baseline`, `test_paging_contract`, `test_change_set_position_reads`, `test_relation_matrix_volume` | 55 |

Counts are collected cases on 2026-09-24 (532 in total); group counts include the WP-9 composed
SC-15 case. The full suite collected 534 cases at WP-9 build acceptance (2026-09-25). The `startup`,
`queries`, `change_sets` and `volume` counts were recollected at Base 0.8 S2 (2026-09-25, 546 in total), and the `startup`, `queries`, `change_sets`, `contract` and `volume` counts at S3/S4 (2026-09-25, 584 in total) at S4R1 (2026-09-26, 588 in total), and the `queries`, `change_sets`, `contract` and `volume` counts at S4R6 (2026-09-26, 622 in total), and the `startup` and `change_sets` counts at S2b (2026-09-26, 625 in total), and the `startup`, `queries` and `change_sets` counts at S8 (2026-09-26, 631 in total). Every count was recollected at W2 (2026-09-26, 637 in total), where the `drafts` marker became `change_sets`. The `model_admin` and `records` counts were recollected at W5 (2026-09-26, 643 in total). A module carries several markers when it is
evidence for several groups, so groups overlap and their counts do not add up to the total.

**Unclassified tests are refused.** A module missing from `TEST_GROUPS` fails collection with exit
code 4 and names the module, in every run including CI. Markers are registered from the manifest and
`--strict-markers` is on, so a mistyped marker also fails. Add a new module to the manifest and to
the table above in the same change.

**Node selection** is still the sharpest tool when a group is broader than the risk. Use it for
single contracts, e.g. INV-02 alone: `py -m pytest tests/test_model_independence.py`; activation
failure atomicity: `py -m pytest "tests/test_wp8_publish.py::test_no_partial_publication_after_every_failure_class"`.

### Frontend: Vitest projects plus `vitest related`

`frontend/vite.config.ts` declares two projects:

| Project | Files | Environment | Purpose |
| --- | --- | --- | --- |
| `unit` | `src/**/*.test.ts` | node (per-file `// @vitest-environment jsdom` opt-in) | API clients, routing, model reads, dates, fixtures |
| `dom` | `src/**/*.test.tsx` | jsdom with `src/test/setup.ts` | rendered components and hooks |

Every test file matches exactly one project by extension, so none is unclassified. Selection:

```sh
npx vitest run --project unit                         # all pure tests, < 1 s
npx vitest run src/features/objects/views             # a directory
npx vitest related src/lib/hooks/useCursorWindow.ts --run   # tests importing a changed file
```

`vitest related` follows the static import graph. It is the right tool for a changed shared module;
it cannot see behavior reached through props, context or the API contract, so pair it with the
consumer rules in section 2.

### Browser: named runners

Each runner starts its own isolated backend (fresh SQLite, real Alembic migration), Vite and
Chrome. Setup costs ~2.8 s per runner (section 4). Pick by surface:

| Runner | Surfaces / contracts |
| --- | --- |
| `e2e/wp9-navigation.mjs` (`test:browser`) | C-UI-NAV, C-Q-FILTER UI, UI-01/02/03 shell, collection controls, inspector; imports `e2e/ui03a-navigation.mjs`, `e2e/ui03b-deletion.mjs`, `e2e/ui03b-hierarchy.mjs`, `e2e/record-actions.mjs` |
| `e2e/wp9-authoring.mjs` (`test:browser:authoring`) | C-OBJ-C/U, C-REL, C-TR, C-DEL live, conflict reconciliation |
| `e2e/wp9-change-sets.mjs` (`test:browser:change-sets`) | C-DR-SRC/EDIT/ACT, change set C-DEL |
| `e2e/wp9-publications.mjs` (`test:browser:publications`) | C-REV, historical sources, C-PUB-RET, C-WS-RET |
| `e2e/wp11-model-admin.mjs` (`test:browser:wp11`) | C-DR-PIN version-change dialog |
| `e2e/wp12-release-identity.mjs` (`test:browser:wp12`) | C-MOD-DIFF release identity and history comparison |
| `e2e/wp14-contextual-browser.mjs` (`test:browser:wp14`) | C-Q-SCOPE, C-MAP-UI, contextual collections |
| `e2e/wp13c-ui-states.mjs` (`test:browser:wp13c`) | C-MAP-UI and C-DR-PIN changed states: outage/retry, empty, conflict review, change-set-context mapping, non-active-release change set, narrow layout ([UI acceptance](UI_ACCEPTANCE.md)) |
| `e2e/sc07-mapping-acceptance.mjs` (`test:browser:sc07`) | WP-9 composed SC-07: C-MAP-UI/W/SET across the starter binding in both directions and an independent binding with a typed relation attribute; candidates beyond page one, large ambiguous sets, generic-write race, publishing against a divergent live set |
| `e2e/s5-continuous-lists.mjs` (`test:browser:s5`) | Base 0.8 S5 continuous lists: collection lens, record and relation panels, mapping lens and object picker over the Track S volume fixture (seeded by `backend/tests/volume_seed.py`, 10% by default, `S5_VOLUME_SCALE=1` for full volume) and the starter model; live, change-set and publication; scrollbar, page number, seek, URL anchor, keyboard, 1440px and 390px |
| `e2e/s6-sidebar-tree.mjs` (`test:browser:s6`) | Base 0.8 S6 sidebar tree by parent over the Track S volume fixture (10% by default, `S6_VOLUME_SCALE=1` for full volume) and the starter model: top-level roots, each branch's own children and counts per child type, a 2,000-child branch scrolled end to end, an eight-level keyboard path, collapse releasing the branch, search with ancestor paths; live, change-set and publication; 1440px and 390px; axe on three tree states |
| `e2e/s7-volume-acceptance.mjs` (`test:browser:s7`) | Base 0.8 S7 composed Track S acceptance over the volume fixture (10% by default, `S7_VOLUME_SCALE=1` for full volume) and the starter model: one lens journey per context (scroll, seek, scrollbar click, end, page number, copied URL), each landing checked against the context's API read, then a record deep in the tree (volume: search with its ancestor path; starter: keyboard across a tree window's edge); live, change-set and publication; 1440px and 390px; reports API read times as the browser saw them |
| `e2e/w4-workspace-admin.mjs` (`test:browser:w4`) | Base 0.8 W4 workspace administration with the capability on and off: single-workspace label, Workspaces screen, create (keyboard, duplicate key), concurrent rename, switching in RDM Systems, dropdown Manage workspaces, set default (landing workspace, stale switch), retire and read-only opening; W6 deletion of a mistyped key by keyboard, stale URL, re-creation and the selector; capability status on both screens; 1440px and 390px; axe on seven states |
| `e2e/sc15-model-version-acceptance.mjs` (`test:browser:sc15`) | WP-9 composed SC-15: C-DR-PIN and C-MOD-ACT with two same-schema releases and an incompatible one; refusals leave live, history and another workspace untouched |
| `e2e/accessibility-gate.mjs` (`test:a11y`) | C-UI-A11Y, T5 build gate |
| `e2e/visual-regression-gate.mjs` (`test:visual`) | C-UI-A11Y visual stability, T5 build gate |

Set `PLAYWRIGHT_EXECUTABLE_PATH` to use an installed Chrome ([e2e README](../../frontend/e2e/README.md)).
`npm run test:gate-helpers` fails when an `e2e/*.mjs` module is not named in this table.

## 2. Changed boundary → selected checks

"Direct" is the group that owns the boundary. "Expand" lists groups that call the boundary through a
shared path and would break silently if it changed meaning. Run direct plus expansion, then Ruff or
frontend format/lint/build as [AGENTS.md](../../AGENTS.md) requires.

### Backend

| Changed boundary | Direct | Expand when | Expansion |
| --- | --- | --- | --- |
| `models/schema.py`, `services/model/validation/*`, `compiler.py`, `loader.py` | `model` | a model field is consumed at runtime | the consuming group; `contract` if the `/model` shape changes |
| `services/model/{releases,registry,runtime,metadata,drafts,diff,compatibility}.py`, `routers/model_*.py` | `model_admin` | activation or registry resolution changes | `workspaces` (pinned contexts), `startup` (registry at lifespan) |
| `db.py`, `migrations/**`, `main.py` lifespan, `services/model/bootstrap.py`, `cli/*` | `startup` | always for migrations | AGENTS.md startup rules: bootstrap, upgrade, restart, interrupted migration, lifespan, smoke start |
| `models/database.py` | the owning service group | a column or table changes | `startup` (`test_migrations::test_fresh_migration_provisions_the_complete_current_schema` compares head with metadata) |
| `services/objects.py`, `attributes.py`, `routers/objects.py`, `routers/attributes.py` | `records` | typed conversion or version claims change | `queries` (typed filters), `change_sets` (change set writes use the same apply path) |
| `services/relations.py`, `relation_set_versions.py`, `routers/relations.py` | `records` + `mapping` | always | `change_sets` (change set relation writes, publishing merge) |
| `services/deletion.py` | `records` | cascade or preview token changes | `mapping` (continuation invalidation), `change_sets` (change set deletion) |
| `services/pagination.py`, `cursors.py`, `routers/paging.py` | `queries` (`test_pagination`, `test_paging_contract`, `test_change_set_position_reads`) | always | every group with a collection endpoint: `-m "queries or mapping or model_admin or workspaces"`; `volume` (read budgets) |
| `services/workspaces.py`, `routers/workspaces.py` | `workspaces` | scope resolution changes | `mapping` (C-MAP-W authority), `change_sets` |
| `services/change_sets.py`, `change_set_lookups.py`, `workspace_audit.py`, `audit.py` | `change_sets` | overlay, publishing or audit projection changes | `mapping` (change set coverage and replacement), `records` (history); `volume` when a change set read or write path changes |
| `services/snapshot_reads.py`, `snapshot_values.py`, `relation_queries.py` | `change_sets` + `queries` (`test_context_read_parity`, `test_paging_contract`, `test_change_set_position_reads`) | always | `volume` (change-set and publication read budgets); `startup` when the typed value index or its backfill changes |
| `models/search_index.py`, the search predicate in `services/objects.py` | `queries` + `change_sets` (`test_search_index`, `test_context_read_parity`) | always | `startup` when the index DDL changes (a new migration, `test_search_index` upgrade and interrupted run); `volume` (search budgets) |
| `services/mapping.py`, `mapping_projection.py`, `routers/mapping.py` | `mapping` | never by default | `change_sets` only if publishing or change set overlay is touched |
| `services/relation_matrix.py`, `routers/relation_matrix.py` | `matrix` | always | `volume` (matrix read budgets, `test_volume_baseline`); `contract` when the route or page shape changes |
| `services/matrix_states.py`, `matrix_cells.py`, or a write path that bypasses the ORM | `matrix` (`test_matrix_states`, and `verify` after every matrix test) | always | `change_sets` and `records` (the write paths it maintains); `startup` when the tables, migration or startup build change; `volume` (filter budgets) |
| `errors.py`, `routers/presenters.py` | the group of the changed error | error envelope shape changes | `contract`; `model_admin` (`test_build07_wp11` correlation IDs) |
| Any router signature, parameter or response model | the router's group | always | `contract` (re-baseline the OpenAPI lock only for intended changes) |

### Frontend

| Changed boundary | Direct | Expansion |
| --- | --- | --- |
| `src/api/*` | `npx vitest related <file> --run` (a change to `client.ts` selects 24 of 36 files) | the browser runner covering the consuming surface if request shape or error handling changes |
| `src/routing/*`, `src/app/useRouter*` | `src/routing`, `src/app` | `wp9-navigation.mjs` for URL or history behavior |
| `src/lib/hooks/useCursor*`, `src/ui/ScrollWindow.tsx`, `src/ui/ObjectLookup.tsx` | `vitest related` | `test:browser:s5`; scroll, landing or anchor changes also `test:browser` (record return and URL restoration); nested windows or the `group` role also `test:browser:s6` |
| `src/features/objects/Explorer.tsx`, `RecordTree.tsx`, `src/model/collections.ts` | `Explorer.test`, `vitest related` | `test:browser:s6`; `test:browser` (tree steps and `ui03b-hierarchy`) and `test:browser:wp14` (a heading opens a scoped collection) |
| `src/model/*` | `--project unit`, `src/model` | `vitest related` when a read's result shape changes |
| `src/ui/*` shared components | `vitest related` | `test:a11y`/`test:visual` scenario for the changed control only when focus, semantics or tokens change; full gates at WP-9 |
| `src/features/objects/MappingGridView.tsx` and its `views/` host | `vitest related` (3 files) | `wp14-contextual-browser.mjs`, `wp13c-ui-states.mjs` |
| `src/features/objects/**` other | the file's test and `vitest related` | the runner for the surface (section 1 table) |
| `src/features/workspaces/**` | `src/features/workspaces` | `wp9-change-sets.mjs` or `wp9-publications.mjs`; `wp11-model-admin.mjs` and `wp13c-ui-states.mjs` for version selection; `w4-workspace-admin.mjs` for `WorkspaceAdmin` and `WorkspaceSelector` |
| `src/features/administration/**` | `vitest related` | `w4-workspace-admin.mjs` |
| `src/features/model-admin/**` | `src/features/model-admin` | `wp12-release-identity.mjs`, `wp11-model-admin.mjs` |
| `src/styles*`, theme tokens | none at T1 | focused a11y/visual scenarios for affected pages, plus dark variants |

### Worked traces (representative change per layer)

| Layer | Change | Selected | Cases vs blanket |
| --- | --- | --- | --- |
| Backend service | Mapping replacement validation in `services/mapping.py` | `py -m pytest -m mapping` | 115 of 532 (22%) |
| Backend shared | Keyset predicate in `services/pagination.py` | `-m "queries or mapping or model_admin or workspaces"` | 252 of 532 (47%) |
| Backend model | A new validation rule in `validation/relation_rules.py` | `-m model` (T0, no database) | 109 of 532 (20%) |
| Startup | New Alembic revision | `-m startup` plus the AGENTS.md smoke start | 24 of 532 (5%) |
| Frontend leaf | `MappingGridView.tsx` | `npx vitest related … --run` and `test:browser:wp14` | 3 of 36 files, 50 tests; one runner of 8 |
| Frontend shared | `src/api/client.ts` | `vitest related` | 24 of 36 files |
| Browser surface | Publishing dialog | `ChangeSets.test.tsx` and `test:browser:change-sets` | one runner of 8 |

### Targeted failure reruns

- Backend: rerun the failing node IDs, then the direct group of the boundary you fixed.
  `py -m pytest --lf` needs the cache provider, so do not pass `-p no:cacheprovider` if you want it.
- Frontend: `npx vitest run <file> -t "<test name>"`, then `vitest related` for the fixed file.
- Browser: rerun only the failed runner; its evidence directory is printed on exit.
- A second failure at the same boundary after a fix, or an unexplained failure, justifies the
  broader group or suite. State the reason before running it.

### UI changes

A changed user-visible surface additionally follows [UI acceptance](UI_ACCEPTANCE.md): name its
reference pattern, complete its state inventory row, run the runner that covers its user-critical
states and inspect the changed screenshots at 1440px and 390px. Report functional, accessibility and
visual evidence separately.

## 3. WP-9 comprehensive command set

Run once, against the finished build, after all implementation packages close. Never run two
pytest processes at once: they share `backend/tests/test-rdm-engine.db`.

```sh
(cd backend && .venv/bin/python -m ruff check app/ tests/)
(cd backend && .venv/bin/python -m pytest -q)
(cd frontend && npm run format:check && npm run lint && npm run build)
(cd frontend && npm run test && npm run test:gate-helpers)
(cd frontend && npm run test:browser && npm run test:browser:authoring && npm run test:browser:change-sets \
  && npm run test:browser:publications && npm run test:browser:wp11 && npm run test:browser:wp12 \
  && npm run test:browser:wp14 && npm run test:browser:wp13c \
  && npm run test:browser:sc07 && npm run test:browser:sc15 \
  && npm run test:browser:s5 && npm run test:browser:s6 && npm run test:browser:s7 \
  && npm run test:browser:w4)
(cd frontend && npm run test:a11y && npm run test:visual)
```

Plus the AGENTS.md startup/migration smoke start against an isolated copy of the development database,
and the composed acceptance journeys WP-9 defines.

## 4. Measured execution cost

**Environment:** Apple M1 Pro (10 cores), macOS 15 (Darwin 24.6.0), Python 3.14.7, pytest 8.4.2,
SQLite, Node 22, Vitest 4, installed Google Chrome via `PLAYWRIGHT_EXECUTABLE_PATH`. Single runs on a
developer machine; expect ±10% noise. Measured 2026-09-24.

### Fixed representative selection

| Layer | Selection |
| --- | --- |
| Backend T0 | `test_model.py test_model_diagnostics.py test_pagination.py test_model_independence.py` |
| Backend T2 | `test_api.py test_mapping_replacement.py test_mapping_coverage.py test_wp8_publish.py test_typed_table_queries.py` |
| Backend T3 | `test_startup.py test_migrations.py` |
| Frontend T1 | `MappingGridView.test.tsx CollectionView.test.tsx App.test.tsx client.test.ts Modal.test.tsx`; separately all seven `*.test.ts` files |
| Browser T4 | `wp14-contextual-browser.mjs` |

Backend setup was attributed with a throwaway profiling plugin wrapping the lifespan steps
(`load_bootstrap_model`, `create_database`, `bootstrap_model`, `model_registry.resolve_active`);
it is not committed.

### Before and after

| Measurement | Before | After | Change |
| --- | --- | --- | --- |
| Backend selection, cases | 262 passed, 1 xfailed | 262 passed, 1 xfailed | identical |
| Backend selection, pytest time | 46.75 s | 22.71 s | −51% |
| … of which Alembic in lifespan (153 calls) | 22.70 s | 1.14 s | template copy replaces per-test migration |
| … bootstrap release install (152 calls) | 2.28 s | 2.13 s | unchanged (kept) |
| … model load (153 calls) | 0.72 s | 0.44 s | unchanged (kept) |
| Frontend `*.test.ts` (7 files, 48 tests), wall | 1.48 s | 0.82 s | node environment |
| … cumulative jsdom environment setup | 7.06 s | 0.62 s | only `routes.test.ts` keeps jsdom |
| Frontend mixed selection (5 files, 80 tests), wall | 4.92 s | 4.38 s | `client.test.ts` moved to node |
| Browser `wp14`, total | 4.96 s | not changed | setup 2.78 s: backend ready 1.06 s, Vite 0.33 s, seed 0.18 s, Chrome 1.22 s; checks 2.17 s |

Full backend suite **after** the change (run once because `conftest.py` and `--strict-markers` touch
every module): 531 passed, 1 xfailed (WP-10E strict reproduction) in 58.94 s; part of the run
overlapped Vitest runs, so treat the time as an upper bound. Lifespan attribution over 404 lifespans:
Alembic 3.50 s, bootstrap release 4.15 s, model load 1.48 s. No full-suite *before* measurement was
taken; the selection above is the like-for-like comparison.

Earlier recorded full-suite timings (historical, fewer tests): 359 backend tests in 25–26 s and 103
frontend tests in 6.1 s on 2026-09-10 ([WP-10 composed validation](../../review-notes/wp10-composed-release-validation-2026-09-10.md)).
The full frontend suite and the other browser runners were not rerun for this package.

### What was optimised, and why isolation is preserved

1. **Migrated template database (backend).** The mapping, typed-query and review-regression
   fixtures created an empty SQLite file per test and ran the whole Alembic chain (~0.2 s per
   test). The session fixture `_migrated_template` now migrates one empty database once;
   `migrated_database()` copies it into the test's own `tmp_path`. Every test still owns its file,
   and the real lifespan still runs its Alembic head check, model bootstrap and registry
   resolution, so request and transaction coverage is unchanged. **Not used** by `startup` tests or
   any test proving migration from an empty, older or partial database; those keep real migrations.
2. **Node environment for pure unit files (frontend).** jsdom cost ~1 s per file against ~10 ms of
   test time. Six files pass unchanged under node; `routes.test.ts` reads `window` and opts back in.
3. **Order-independent pagination test.** `test_pagination::test_statement_paginator_accepts_the_historical_draft_cursor_identity`
   failed when run alone (no schema) — the coverage map's residual-risk item. It now owns a migrated
   database, so the `queries` group and node selection work in any order.
4. **Harness phase timings (browser).** `bootHarness` records backend, Vite, seed and Chrome phases and
   prints them on cleanup, separating setup from checks for every harness-based runner.

### Remaining bottlenecks (measured, not optimised)

- **Lifespan per `TestClient`**: ~9 s of the full suite across 404 lifespans (bootstrap release
  ~10 ms, Alembic head check ~5 ms at median, model load ~4 ms per lifespan).
  Kept: it is the real startup path, and caching it would reduce what every test proves.
- **`resolve_active`** is called ~2,000 times in the selection (lifespan and requests), 1.5 s total;
  a production-path cost, not a test artefact.
- **Heaviest individual cases** are the mapping conflict and activation tests (0.3–0.4 s each), which
  do real multi-request work. No duplicate execution was found in them.
- **Browser setup** is ~2.8 s per runner, dominated by Chrome launch and uvicorn import. Runners are
  separate processes by design; sharing a server would couple their databases.
- **Frontend `dom` project**: import (3.7 s cumulative) and jsdom (2.1 s) dominate the mixed selection;
  replacing jsdom would be a new testing platform, which WP-13 excludes.
- **Unexplained transient failure:** one `dom` test failed once in `npx vitest related src/ui/Modal.tsx --run`
  while the backend suite ran concurrently (CPU contention); its name was not captured and three idle
  reruns passed (14 files). Likely a timing-sensitive component test; if it recurs, capture the name
  and treat it as a defect rather than rerunning until green.
- **Backend parallelism** is out of scope: the shared test database requires serial pytest.

### Not measured

Full frontend Vitest suite, the six other browser runners and the a11y/visual gates after this
change (their code paths only gained harness timing output). These belong to WP-9.
