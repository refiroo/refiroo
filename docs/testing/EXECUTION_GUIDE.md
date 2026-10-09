# Test execution guide

**Package:** Base 0.7 WP-13B, 2026-09-24. **Inputs:** the [coverage map](COVERAGE_MAP.md) (contract
IDs, tiers T0–T5, risk). **Consumers:** every work package choosing focused checks, WP-13C and WP-9.

This guide answers one question: *I changed this production boundary — which checks do I run?* Pick the
direct group for the boundary you changed, apply the listed shared-boundary expansion, and run
nothing broader. The selection is the ceiling for a work package, also for a shared path such as the
matrix state hook: a concrete uncovered risk adds the one module or case that covers it, never a whole
suite. The full suites run once, at build acceptance
([AGENTS.md](../../AGENTS.md#work-package-validation)). A group that passed after the last edit to
its boundary is not rerun.
Selection is transparent and manual. No tool here promises perfect impact detection; `vitest related`
follows imports only, and the backend groups are declared, not inferred.

Commands assume the repository root. Backend commands use `backend/.venv/bin/python` (written `py`
below) from `backend/`; frontend commands run from `frontend/`.

## 1. Selection mechanics

### Backend: the PostgreSQL test harness (0.9.0-alpha.1 PG1, H1)

Backend tests run on PostgreSQL only. `pytest` starts a private server from Homebrew's
`postgresql@17` binaries (`brew install postgresql@17`; never `brew services`) on
`backend/.test-postgres/` (git-ignored), on a Unix socket, with the ICU root collation (PG-D11) and
durability off, and stops it when the run ends (`tests/postgres_server.py`). With
`RDM_TEST_DATABASE_SERVER` set to a superuser URL (CI's `postgres:17` service) it uses that server
instead.

Databases come from **seeds built once and reused** (`tests/seeds.py`): template databases on that
server with a fingerprint of what built them (the migrations; for the volume fixture also the volume
model, the fixture code it calls and the shape). A matching seed is reused; a changed input rebuilds
that seed once, and the next run reuses it. Tests get clones (`CREATE DATABASE … TEMPLATE`, about
90 ms): the session database the modules importing `app.main.app` share, each `migrated_database()`
and each `volume_fixture.volume_app(directory, shape)`. The end of a run names every seed it used as
`reused` or `built`, with the build time.

```sh
cd backend && .venv/bin/python -m tests.seeds list    # each seed, its fingerprint, current/stale/missing
.venv/bin/python -m tests.seeds build                 # build every stale seed now, e.g. after a pull
```

Do not run `pytest` or `tests.seeds build` while another is running: they share the server, and a
starting run drops databases an interrupted run left behind. If the server's directory is damaged,
delete `backend/.test-postgres/`; the next run creates it and rebuilds the seeds.

### Backend: parallel runs (H2)

One invocation parallelizes itself: `-n auto` starts one worker per core (pytest-xdist), and
`--dist loadfile` (in `pyproject.toml`) keeps each module on one worker. The run's own process starts
the server, drops leftover databases and builds the `schema` seed before the workers start; each
worker clones its own session database, and all of them clone from the same seeds.

**Timing-based checks are `serial`** (narrowed in H3): only a test whose outcome depends on wall
time, listed in `TIMED` in `conftest.py` by module or by `module::test` — validating and publishing
the large workspace (`test_graph_validation_scale`), the job worker's wait between retries (a unit
test marked `serial` itself), and the current-live capture whose race is decided by a 0.3 s timer. The `volume` modules that count
statements and rows run in the parallel part. A parallel run leaves `serial` tests out and its
summary names the command for them; run it next, without `-n`:

```sh
cd backend && .venv/bin/python -m pytest -n auto -q        # everything except serial and budget tests
.venv/bin/python -m pytest -m serial -q                    # then the serial tests, one process
.venv/bin/python -m pytest -n auto -m records -q           # a group in parallel …
.venv/bin/python -m pytest -m "serial and (records)" -q    # … and its serial part, if it has one
```

Without `-n` a run is serial and runs everything except `budget`, `serial` tests included. A small
selection (one module, a few cases) is faster without `-n`, which starts a worker per core. Add a
test to `TIMED` only when its outcome depends on wall time; a statement-count budget is not
timing-based.

**Full-size budgets are `budget`** (H3): `test_batch_volume` (the 10,000-item atomic batch) and
`test_background_volume` (the 100,000-item background batch; both modules 2 min 39 s at PG5). A run
leaves them out unless its `-m` expression names `budget`, and they are `serial` when named. They
run only at a release's acceptance, once and announced. PG3b replaced their timed checks with
statement counts at two seeded sizes (PG-D17), in `test_batch_statements`, which runs in the
parallel part.

```sh
.venv/bin/python -m pytest -m budget --collect-only -q     # names exactly the budget tests
.venv/bin/python -m pytest -m budget -q                    # a release's acceptance only
```

**The run reports what grew.** The summary lists every test over 10 s outside `budget` (setup, call
and teardown added up, so a module fixture's cost lands on its first test) and the run's wall time.

### Backend: time ceilings and their commands (H3)

The ceilings are [TEST_HARNESS_PLAN's](../TEST_HARNESS_PLAN.md#time-ceilings); a run expected to
exceed 2 minutes is announced with its expected time first, and in a package it needs the user's
go-ahead.

| Run | Ceiling | Command (from `backend/`) |
| --- | --- | --- |
| Focused tests while iterating | seconds | `.venv/bin/python -m pytest tests/test_x.py::test_case -q` (no `-n`) |
| A package's checks: its boundary's groups (§2) | 2 minutes | `.venv/bin/python -m pytest -n auto -m "<groups>" -q`, then `.venv/bin/python -m pytest -m "serial and (<groups>)" -q` |
| Build acceptance: the full suite without `budget` | 5 minutes | `.venv/bin/python -m pytest -n auto -q`, then `.venv/bin/python -m pytest -m serial -q` |
| Full-size budgets | announced (2 min 39 s at 0.9.0-alpha.1 PG5; about 25 minutes before PG3b's bulk writes) | `.venv/bin/python -m pytest -m budget -q`, a release's acceptance only |

### Backend: journey tests, unit tests and selection by change (H4b)

Delivered 2026-10-02 for the [testing strategy](STRATEGY.md). **From 2026-10-03 it is a package's
selection:** the tests whose code changed (`--testmon`) and the journey tests of the journeys the
package touches (`--journey`). The group selection below is the fallback, for a change coverage
cannot see and for the older modules.

```sh
cd backend && .venv/bin/python -m pytest -n auto --testmon -q    # the tests whose code changed
.venv/bin/python -m pytest -n auto -q --journey J11 --journey J24   # the journeys it touches
```

- **Journey tests** live in `backend/tests/journeys/` and carry `@pytest.mark.journey("J02",
  "J02.2")` with the [journeys and variants](../product-functionality/USER_JOURNEYS.md) they walk.
  An unknown or retired ID, or a journey test without one, fails collection. `--journey J02` runs
  the tests that walk J02 or any of its variants; `-m journey` runs every journey test.
  A journey test names the model structures it uses (`@pytest.mark.structures("R", "Bnn")`) and runs
  once per configuration chosen for them (`configurations.py`): with the `world` fixture on a clone
  of the configuration's seeded data with the application started (`scenario.py`), or with the
  `configuration` fixture alone when it starts the service itself, as the operator's journey J12
  does (`service.py`).
- **Unit tests** live in `backend/tests/unit/` in folders that mirror the code they test:
  `tests/unit/engine/records/test_rules.py` tests `app/engine/records/rules.py`
  (`test_rules__<topic>.py` splits one), and `tests/unit/harness/` tests the harness modules in
  `tests/`. A unit test that mirrors no module fails collection.
- **Selection by change** (`pytest-testmon`): `--testmon` records which code each test executes
  in `backend/.testmondata` and, on the next run, selects the tests whose code changed. Testmon
  turns its selection off under `-m` unless `--testmon-forceselect` is given. Coverage runs on the
  C tracer for this (`COVERAGE_CORE=ctrace`, set in `conftest.py`): Python 3.14's default
  `sys.monitoring` core lost the code that runs in the TestClient's request threads.
- **What a change requires:** `.venv/bin/python -m tests.affected` (or `… tests.affected <commit>`)
  lists each changed file with what it selects and prints the commands. Code goes to testmon; what
  coverage cannot see selects its readers: a migration, the starter model, seed code, the test
  server and the harness (`conftest.py`, `layout.py`) select everything; the journey catalogue and
  the API inventory select the tests that read them; documentation and the frontend select nothing
  here.
- **Trace report:** `.venv/bin/python -m tests.journey_trace` (`--modules` for the full lists)
  reads the testmon data and the journey markers: the modules each journey reaches, the modules no
  journey reaches, the modules no test reaches, and the declaration-only modules no trace can see.

```sh
cd backend && .venv/bin/python -m tests.affected        # what this change requires
.venv/bin/python -m pytest -n auto --testmon -q         # the tests whose code changed
.venv/bin/python -m pytest -m serial --testmon --testmon-forceselect -q
.venv/bin/python -m tests.journey_trace                 # code by journey; code no test reaches
```

### Backend: pytest markers from one manifest

`backend/tests/conftest.py` holds `TEST_GROUPS`, mapping every test module to the contract groups
it is evidence for, and applies them as markers. Select a group with `-m`:

```sh
cd backend && .venv/bin/python -m pytest -m mapping -q
.venv/bin/python -m pytest -m "change_sets and not mapping" -q   # boolean expressions work
```

| Marker | Contracts (coverage map) | Modules | Cases |
| --- | --- | --- | --- |
| `model` | INV-01/02/03/04/06, compatibility classes | `test_model`, `test_model_diagnostics`, `test_model_independence`, `test_model_compatibility`, `test_effective_periods`, the unit tests under `tests/unit/engine/model/` (0.9 C15) | 348 |
| `model_admin` | C-MOD-*, C-DR-PIN, C-MOD-ACT | `test_model_lifecycle`, `test_build07_wp11`, `test_build07_wp6`, `test_build07_wp9_acceptance`, `test_model_compatibility`, `test_model_schema_upgrade`, `test_wp81a_context`, `test_w5_activation_write_race`, `test_pg3_concurrency` | 187 |
| `startup` | C-BOOT, C-MIG, C-SCHEMA-UP, INV-15 (startup) | `test_startup` (clean bootstrap, restart, the database refusals, a failed migration rolled back), `test_model_schema_upgrade`, `test_matrix_states`, `test_schema_drift` (the PostgreSQL baseline against the ORM), `test_foreign_keys` (every `ondelete` rule, PG-D4), `tests/unit/test_config.py` (with the settings catalogue, 0.9 U3) and `test_main.py`, the J12 and J31 journey tests (J31: `test_j31_system`, `GET /system`) | 103 |
| `records` | C-OBJ-*, C-ATTR, C-REL, C-DEL, C-TR, C-HIST-OBJ, INV-05/10/12 (live) | `test_api`, `test_attributes`, `test_relations`, `test_translations`, `test_cascade_delete`, `test_query_foundations`, `test_wp8_review_regressions`, `test_relation_set_versions`, `test_w5_activation_write_race`, `test_matrix_states`, `test_parent_candidates`, `test_type_changes`, `test_restructuring_planner`, `test_restructuring_api`, `test_encoding`, `test_rule_parity`, `test_effective_periods`, `test_pg3_concurrency`, `test_pg3b_batch_writes` | 240 |
| `queries` | C-Q-FILTER, C-Q-SCOPE, INV-07/08/11 | `test_pagination`, `test_typed_table_queries`, `test_query_foundations`, `test_context_read_parity`, `test_paging_contract`, `test_change_set_position_reads`, `test_search_index`, `test_parent_candidates`, `test_change_lists`, `test_cross_type_lookup`, `test_model_query`, `test_effective_periods` | 247 |
| `workspaces` | C-WS-*, C-PUB-RET, INV-14/16 | `test_workspaces`, `test_wp81a_context`, `test_request_scope`, `test_wp8_withdrawal`, `test_build07_wp9_acceptance`, `test_pg3_concurrency` | 40 |
| `change_sets` | C-DR-*, C-REV, C-PUB-RET | `test_change_sets`, `test_wp7_canonical_crud`, `test_wp8_*`, `test_wp81b_current_live_bases`, `test_build07_wp6`, `test_build07_wp9_acceptance`, `test_typed_table_queries`, `test_mapping_replacement`, `test_wp8_withdrawal`, `test_context_read_parity`, `test_change_set_position_reads`, `test_change_set_write_lookups`, `test_search_index`, `test_matrix_states`, `test_parent_candidates`, `test_change_lists`, `test_change_lists_volume`, `test_type_changes`, `test_restructuring_planner`, `test_restructuring_volume`, `test_restructuring_api`, `test_graph_validation_scale`, `test_cross_type_lookup`, `test_rule_parity`, `test_model_query`, `test_effective_periods` | 441 |
| `mapping` | C-MAP-R, C-MAP-W, C-MAP-SET | `test_mapping_coverage`, `test_mapping_replacement`, `test_relation_set_versions`, `test_pg3_concurrency` | 131 |
| `matrix` | Relation matrix reads, cell writes and stored cell states: cells, states, row state filter, columns, containers, candidates, maintenance on every write path (Base 0.8 A2, A3, A3b) | `test_relation_matrix`, `test_relation_matrix_volume`, `test_relation_matrix_writes`, `test_matrix_states`, `test_type_changes`, `test_restructuring_planner`, `test_restructuring_api`, `test_pg3_concurrency`, `test_pg3b_batch_writes` | 75 |
| `consumer` | Consumer API definitions (Base 0.9 C1); the consumer tier's reads from C2 (get by ID), C3 (lists and parameters), C4 (XREF), C5 (parameters on XREF), C14 (batch resolve) and C15 (crosswalk), then publications, parity and business dates (C16), and from C10 the events read | `test_consumer_api_model`, the J23, J25, J28, J29 and J30 journey tests (J29 in the group since C8, J23 since C16, also in `queries`; J30 also in `feed`), `test_j28_j29_parity` (C8), `test_consumer_list_volume` (C3), `test_consumer_xref_volume` (C4, C5, C14), `test_consumer_event_volume` (C10), the unit tests under `tests/unit/engine/reads/` (C14) and `tests/unit/engine/events/` (C10, C11's URL check) | 376 |
| `jobs` | Jobs, outcomes, idempotency and batches (Base 0.9 B1); background runs, the worker, its lease, cancellation and retention (B2); from J2 import profiles, imports and exports | the J11, J24 and J27 journey tests and `tests/unit/engine/jobs/` (H4d-1; `test_xlsx`, 0.9 J1), `tests/unit/common/test_outage.py` (C12), `test_batch_volume`, `test_background_volume`, `test_export_volume` (0.9 J1, also `volume`), `test_pg3_concurrency`, `test_batch_statements`, `test_pg3b_batch_writes` | 145 |
| `feed` | Feed positions, publish entries and the feed read (Base 0.9 F1); from F2 retention and recovery; from C10 consumer events: the deriver, its plan and the pull feed; from C11 subscriptions; from C12 their delivery | the J26 and J30 journey tests (J30.6–J30.7 in `test_j30_subscriptions`, J30.8–J30.9 in `test_j30_delivery`, the events' acceptance in `test_j30_acceptance`, C13), `tests/unit/engine/change_sets/test_publish.py`, `tests/unit/engine/events/`, `tests/unit/common/test_sealing.py` (C11), `tests/unit/common/test_outage.py` (C12) and `test_consumer_event_volume` (C10) | 166 |
| `contract` | OpenAPI lock, route inventories, the backend tiers, upper-case error codes and the API reference page | `test_openapi_contract`, `test_paging_contract`, `test_boundaries`, `test_error_codes`, `test_api_reference`, `test_api_journeys` | 74 |
| `volume` | Track S read and write budgets and the paging contract over the generated volume fixture (Base 0.8 S1, S2b, S3, S4, S4R1, S4R6, S7, S8, A2, B2, P2a, C2, C5; Base 0.9 B1 batch budgets, B2 background budget, T1 dated reads) | `test_volume_baseline`, `test_paging_contract`, `test_change_set_position_reads`, `test_relation_matrix_volume`, `test_change_lists_volume`, `test_restructuring_volume`, `test_graph_validation_scale`, `test_batch_volume`, `test_background_volume` (the last two also `budget`, left out by default, H3), `test_batch_statements` (PG3b: statements per chunk at two seeded sizes; 0.9 K2b: a previewed run of two or eight cascading deletes, live and in the change set; 0.9 K3: `ensureNoRelation` items, half removing a relationship), `test_consumer_list_volume` (0.9 C3: consumer list reads at two seeded sizes), `test_consumer_xref_volume` (0.9 C4, C5, C14: XREF lookups, plain and narrowed, and batch resolve at two seeded sizes), `test_consumer_event_volume` (0.9 C10: deriving a page and a container rename, and the events read; C13: the dispatcher's claim, a delivered batch of each payload and, since C17, one as CloudEvents; at two seeded sizes) | 77 |

From H4d the tests moved into `tests/unit/` and the journey tests carry groups too (`UNIT_GROUPS` by
folder and `JOURNEY_GROUPS` by journey in `conftest.py`), so `-m <group>` still selects what a
module's tests were. The groups stay while the older modules do (H4d is postponed). The `jobs` group has no module of its own left but its
volume and race modules.

Counts are collected cases on 2026-09-24 (532 in total); `test_effective_periods` (Base 0.9 Q4, 21 cases) is listed in `model`, `records`, `queries` and `change_sets` without recollecting their counts; group counts include the WP-9 composed
SC-15 case. The full suite collected 534 cases at WP-9 build acceptance (2026-09-25). The `startup`,
`queries`, `change_sets` and `volume` counts were recollected at Base 0.8 S2 (2026-09-25, 546 in total), and the `startup`, `queries`, `change_sets`, `contract` and `volume` counts at S3/S4 (2026-09-25, 584 in total) at S4R1 (2026-09-26, 588 in total), and the `queries`, `change_sets`, `contract` and `volume` counts at S4R6 (2026-09-26, 622 in total), and the `startup` and `change_sets` counts at S2b (2026-09-26, 625 in total), and the `startup`, `queries` and `change_sets` counts at S8 (2026-09-26, 631 in total). Every count was recollected at W2 (2026-09-26, 637 in total), where the `drafts` marker became `change_sets`. The `records`, `change_sets` and `matrix` counts were recollected at C1 (2026-09-29, 790 in total), and with `volume` at C2 (2026-09-29, 809 in total). The `model_admin` and `records` counts were recollected at W5 (2026-09-26, 643 in total), and the `queries`, `change_sets` and `volume` counts at P2a (2026-09-28, 774 in total). Every count was recollected at E3 of the backend boundaries refactor (2026-09-29, 852 in total). A module carries several markers when it is
evidence for several groups, so groups overlap and their counts do not add up to the total.
The `contract` count was recollected at 0.9 V1 (2026-09-30), with `test_api_reference`. The `jobs`, `startup`, `records`, `change_sets`, `matrix` and `volume` counts were recollected at 0.9 B1 (2026-10-01, 1020 in total). Every count was recollected at 0.9.0-alpha.1 PG1 (2026-10-01, 1032 in total), when the SQLite migration modules were removed with their revisions. The `startup`, `change_sets` and `contract` counts were recollected at PG2 (2026-10-01, 1039 in total). PG3b (2026-10-02) added `test_batch_statements` (6) and `test_pg3b_batch_writes` (6) without recollecting the counts; the four groups it ran hold 581 cases, 1071 in total.

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
| `unit` | `src/**/*.test.ts` | node (per-file `// @vitest-environment jsdom` opt-in) | API clients, routing, model reads, dates, fixtures; the token contrast test (`styles/tokens.test.ts`, reads `tokens.css` raw), selected by any change to `styles/tokens.css` |
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

Each runner starts its own isolated backend, Vite and Chrome. The backend runs on a database of its
own on the **development server** (`scripts/postgres.sh start` first; PG-D8), cloned from a seed in
the seed store there and dropped when the runner ends (`backend/tests/browser_seeds.py`,
0.9.0-alpha.1 PG2): `schema` for the runners that create their records themselves, `starter` (the
harness's records, one seed per model the runner starts with) and `volume` (the Track S fixture at
the runner's scale). A seed is built on a runner's first use after its inputs change and reused after
that; a clone takes about 0.5 s. `RDM_TEST_DATABASE_SERVER` points the runners at another server.
Setup costs ~2.8 s per runner (section 4, measured on SQLite and not measured again on PostgreSQL; a
seed clone adds about 0.5 s). Pick by surface:

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
| `e2e/v1-api-reference.mjs` (`test:browser:v1`) | Base 0.9 V1 API reference at `/docs` against a real backend (no Vite): every request leaving the engine's origin is aborted and fails the runner; the page, the bundled Scalar script and the management source load from the engine; Scalar's hosted services (agent, MCP, toolbar, hosted client) absent; an operation found by its path; the "try it" console's request answered by the engine; 1440px and 390px without horizontal overflow; `/redoc` `404`; axe reported, not gated (Scalar's markup) |
| `e2e/u3-settings.mjs` (`test:browser:settings`) | 0.9 U3 Settings area at 1440px and 390px: the gear from two applications into the same top bar (same tabs and height, tabs 36px after the product name, none current, Settings current) and each application's tab back to its view; every page through the rail and, at 390px, the navigation drawer; a release's and a workspace's page; About and Deployment against `GET /system` (secrets as set or not, the database URL without its password); each replaced address (`/models`, `/workspaces`, `/settings`) landing on its page; Compact on Appearance in two views of different object types, a view's own choice winning; keyboard order; with the Account popover open, one click on an application tab or a settings link closes it and navigates (UA0), axe with it open; axe on Deployment |
| `e2e/u4-integration.mjs` (`test:browser:integration`) | 0.9 U4 Settings › Integration at 1440px and 390px on two consumer API configurations (the starter's `rdm` and a second definition with other keys, types and version the runner adds): each page from the navigation (rail, drawer); each definition's base URL read from the page answering on its list; its reference link opening `/docs` on its source; a job queued behind a large background batch cancelled from Jobs and feed by keyboard and read back cancelled; the API reference's sources and links; axe on the three pages, light and dark |
| `e2e/j1u-export.mjs` (`test:browser:j1u`) | 0.9 J1u exporting in the browser on two object types of two applications (Domains with a filter, Systems), at 1440px and 390px: Export opened and started by keyboard, the dialog prefilled; the started and the completed notifications pushed over the job's stream; Download's file name and size; View job's page with the counts; New export from Jobs and feed; a cancelled batch's page updated by its stream; axe on the dialog, the notification and the job page, light and dark; screenshots of each |
| `e2e/k1-selection.mjs` (`test:browser:k1`) | 0.9 K1 selecting records in a collection on two object types of two applications (Domains, Systems; 80 and 150 records the runner adds through `POST /batches`, its server at `BACKGROUND_JOB_MAX_ITEMS=100`), at 1440px and 390px: three by hand and a Shift range, kept across opening a record and sorting; the loaded rows, Select all 80 matching and an exception; a new search clearing it; Cmd+A in the search field and in the table; Cmd+A over the limit explained; keyboard only at 390px with the status announcements; no selection in a publication; axe on a collection with a selection, light and dark; screenshots of each |
| `e2e/k2b-bulk-delete.mjs` (`test:browser:k2b`) | 0.9 K2b deleting a selection on two object types of two applications (Domains live, Systems in a change set; the domains, codelists, 60 systems and their values the runner adds through `POST /batches`), at 1440px and 390px: a leaf domain and one with two codelists, the preview's totals by type and the destructive Delete 4 records, applied, the rows gone and the selection empty; all 60 matching systems except one by Cmd+A in a change set, a value added under one after the preview refusing Apply whole, Preview again showing it, then applied in the change set only; live, a codelist added under one previewed domain refusing only that one, the rest deleted, Preview again and View job; keyboard only at 390px with a preview left by Escape read back cancelled and the status announcements; axe on the dialog's form, preview and result and a batch's job page with deletes, light and dark; screenshots of each |
| `e2e/k3-bulk-relations.mjs` (`test:browser:k3`) | 0.9 K3 changing the relationships of a selection on the starter's system values (RDM Systems, live and in a change set) and master values and codelists (RDM Master; the runner adds a domain, two codelists, three master values, a system with 60 values and one relationship through `POST /batches`), at 1440px and 390px: two master values added to three values and one removed again (5 added, 1 already related; 3 removed), the selection kept and the record's relationships showing them; all 60 matching values except one by Cmd+A set to a codelist in a change set (Set to and Clear only), live unchanged; live, a set changed through the API after the preview refusing only that record, Preview again and View job; the modes master values and codelists offer, and no translation relationship; keyboard only at 390px through the record picker, with a preview left by Escape read back cancelled and the status announcements; axe on the dialog's form, preview and result and a batch's job page, light and dark; screenshots of each |
| `e2e/k2-bulk-change.mjs` (`test:browser:k2`) | 0.9 K2 changing values of a selection on two object types of two applications (Domains live, Systems in a change set; 5 domains and 80 systems the runner adds through `POST /batches`, its server at `JOB_PREVIEW_MAX_ITEMS=50`), at 1440px and 390px: a description set and Active cleared on three domains, previewed and applied, then changed again without a conflict; all 80 matching systems except one given one unique code: a sample preview, all or nothing writing nothing, the default writing one and refusing 78, a refused system opened; a preview left by Back, ✕, Escape and a click outside read back cancelled, one kept by View job applied on its page, its outcomes linked; keyboard only at 390px with the status announcements; axe on the dialog's fields, preview and result and a batch's job page, light and dark; screenshots of each |
| `e2e/j4-import.mjs` (`test:browser:j4`) | 0.9 J4 SC-10 in the browser on two object types of two applications (Master values at 1440px, Systems at 390px), each through a profile the runner saves through the API: Import opened and previewed by keyboard; the preview's counts and refused rows by row and column with the data unchanged; Load the file, the result and the collection; the corrected file previewing as unchanged and created; all or nothing, then Cancel import; New import from Jobs and feed into a change set with an XLSX file, leaving and returning by Preview ready, reopened from Jobs and feed after a reload; a file over a lowered `IMPORT_MAX_BYTES` at the file field; axe on the dialog, the waiting and the loaded page and the notifications, light and dark; screenshots of each |
| `e2e/u5-webhooks.mjs` (`test:browser:webhooks`) | 0.9 U5 Settings › Integration › Webhooks with subscriptions on, on two consumer API configurations (the starter's `rdm` and a second definition with its own event the runner adds), against a receiver the runner serves: a webhook created from the page on each, at 1440px and 390px, its key read once and the subscription read back; a refused delivery shown as Retrying with the receiver's answer; suspend and resume by keyboard, then the batch arriving signed with the page's key; a workspace refused deletion naming its webhook; delete; axe on the list, the detail and the dialog, light and dark. Since U5a: webhooks named, events chosen in the picker and the filter menu opened, the Deliveries tab after the resume (the dropped 503 batch and the delivered one) and an event opened by keyboard whose request body equals the body the receiver got; the dialog scrolled to its buttons; axe also on the deliveries with an event open. Since C17: the 1440px webhook created batched up to 50 as CloudEvents and the 390px one with the defaults, each read back and shown on its detail; a batched CloudEvents webhook whose array the receiver got, listed per event and opened; the dialog's delivery choices and a CloudEvents webhook's detail at 390px, dark (the coalesced webhook retired). Since the record-link revision: an event's object ID opens its record |
| `e2e/w4-workspace-admin.mjs` (`test:browser:w4`) | Base 0.8 W4 workspace administration (Settings › Workspaces since U3) with the capability on and off: single-workspace label, the list and a workspace's page, create (keyboard, duplicate key), concurrent rename, switching in RDM Systems, dropdown Manage workspaces, set default (landing workspace, stale switch), retire and read-only opening; W6 deletion of a mistyped key by keyboard, stale URL, re-creation and the selector; Deployment naming the group's setting when it is off; 1440px and 390px; axe on seven states |
| `e2e/a4-relation-matrix.mjs` (`test:browser:a4`) | Base 0.8 A4 relation matrix lens on the starter model, by keyboard alone: fill an empty translation cell in its only container, correct one and filter to gaps across the list (codelists, live); fill a master value's translation through the container picker in a change set; link and unlink a system value in the incoming matrix (master values, live) and the outgoing one (codelists, change set); the publication read-only; each write checked against the API in its context; 1440px and 390px; axe on five states |
| `e2e/a5-matrix-acceptance.mjs` (`test:browser:a5`) | Base 0.8 A5 Milestone A acceptance by keyboard alone: SC-09's translation half on the starter model (Delivery Methods by language with a current Czech, an empty English and a history-only German cell; fill English live; a superseded Czech translation's reactivation refused with the input kept and the current one linked; German restored from history in a change set and published from the change set screen, checked in live and the new publication); link and unlink in Master values by system at 390px; a fill through the container picker on the generated volume model (10% by default, `A5_VOLUME_SCALE=1` for full volume); reports the matrix reads' times as the browser saw them |
| `e2e/b3-tree-lens.mjs` (`test:browser:b3`) | Base 0.8 B3 tree lens by keyboard alone on three trees: the starter system hierarchy (live, 1440px), the domain hierarchy (change set, 390px, then its publication read-only) and the generated volume model's seven-level node tree (2% by default, `B3_VOLUME_SCALE`; live 1440px and change set 390px). In each: a lens search reveals a nested record by seeking each branch on its path (only its ancestors' branches read), add a child from the node menu, rename with F2, set availability where the view allows, and move through the dialog with the current parent (and, once, a descendant) listed disabled; each write checked against the API in its context; axe on eight states. Part 3 (B5) drags with the mouse at 1440px: a group onto a collapsed group that opens under the pointer, a value into the gap between another group's values, a group over its own descendant (red with its reason, nothing written) and Escape, live; a master value between another codelist's values in a change set, live unchanged; each drop confirmed in the move dialog with Enter; axe on the refused drag. B5b, on the volume tree at 1440px: a nested group to the top level by Move to… live (axe on the dialog) and by a drag onto the top-level heading in the change set; an item dragged there is refused with its reason live and, in the change set, says it becomes a group (C4) before the drag is cancelled; each checked against the API (no parent, no containment edge) |
| `e2e/b4-hierarchy-acceptance.mjs` (`test:browser:b4`) | Base 0.8 B4 Milestone B acceptance by keyboard alone: SC-09's hierarchy half on the starter model (`seedHierarchy`). The system hierarchy live at 1440px: a nested group found reading only its ancestors' branches; a child and a grandchild added; the move beneath the grandchild listed disabled and refused by the API (`PARENT_CYCLE`); the child moved to another group, with the new path in the tree, the breadcrumb and the API, one containment edge from the new parent and every unrelated drawn branch unchanged. The same on the domain hierarchy's nested master values at 390px. A move in a change set (group to system, so the containment relation type changes) kept out of live until the change set is published from the change set screen, then checked in live and the new publication |
| `e2e/c4-restructuring.mjs` (`test:browser:c4`) | Base 0.8 C4 restructuring in the tree lens, each operation previewed, applied to a change set and checked against the API. Starter domain hierarchy (change set, 1440px): a master value dragged onto a domain (**Becomes Codelist**), the preview by record and by type pair, applied by keyboard; **Review the change set** shows **Master value → Codelist**; the old route answers `OBJECT_TYPE_CHANGED`; dragged back, its values restored; **Insert level above…** taking a sibling chosen by keyboard, with the new record's values asked in place; **Remove this level…** moving both back. Starter system hierarchy (second change set): **Change type of all system values in here…** and **Change type…**, published, live and history checked, and the browser following the old route to the new type (D42). Generated volume tree (2% by default, `C4_VOLUME_SCALE`; change set): **Move to…** by keyboard to a node (**Becomes vol-node**), an item dragged onto the top-level heading (**Becomes vol-group**), the preview at 390px. Axe on three preview states |
| `e2e/c5-restructuring-acceptance.mjs` (`test:browser:c5`) | Base 0.8 C5 Milestone C acceptance (SC-17), by keyboard against a real backend. Starter domain hierarchy (`seedRestructuring`, 1440px): Move to… takes a domain holding a codelist under another domain, so both levels change type; the preview is answered by type pair (a mapping chosen by type-ahead) and in the record's row; Insert level above… with a sibling chosen and the new record's values in place; Remove this level…; the review from the applied preview; publishing from the change set screen; live, the publication and the history, in the API and the browser (breadcrumb, history panel, the old route followed, D42); a second change set moving the record back, its values restored, published, the first publication unchanged. Generated volume tree (2% by default, `C5_VOLUME_SCALE`): a group holding a group, an item and a citing item dragged onto a node (four type changes, the citation kept in history), a level inserted and removed, the review with the removed citation, publishing, both ends' history, and Move to… plus Change type… restoring the citation under its former ID. Axe on three states |
| `e2e/p2-change-review.mjs` (`test:browser:p2`) | Base 0.8 P2b change set review on the starter model by keyboard: a change set that adds, changes, moves and removes master values and system values and adds and removes a mapping (`seedChangeReview`); open the review from the change set bar, every record row checked against `object-changes`, an edit and a move expanded to their before/after tables, kind and type filters to one row and to nothing, Relationships with parent links hidden then shown, a reload keeping tab and filter, a changed record (RDM Master) and an added one (RDM Systems) opened in the change set; 390px, dark theme, an empty change set, live untouched; axe on seven states |
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
| `models/schema.py`, `engine/model/validation/*`, `compiler.py`, `loader.py` | `model` | a model field is consumed at runtime | the consuming group; `contract` if the `/model` shape changes |
| `engine/model/consumer_contract.py`, `engine/model/validation/consumer_api_rules.py`, the `consumerApis` shapes in `models/schema.py` (0.9 C1; schema 0.9 since C18), `engine/model/consumer_{definitions,expansion,legacy,rendering}.py` (0.9 C18) | `consumer` + `model` (`test_consumer_api_model`, `tests/unit/engine/model/test_consumer_expansion.py`) | always | `model_admin` when the check's place in draft compile, diff or activation changes, or the authoring refusal (`compile_authored_model`); `contract` when `consumerContracts` or the expanded read changes; J25.5 (`test_j28_j29_parity`) when the expansion of a default changes |
| `app/consumer/*`, `engine/reads/consumer_objects.py` (0.9 C2), `consumer_parameters.py`, `consumer_lists.py` (0.9 C3), `consumer_xref.py` (0.9 C4), `consumer_resolve.py` (0.9 C14) | `consumer` (the J28 and J29 journey tests) | always | `contract` (`test_boundaries`, the OpenAPI lock, `test_api_journeys`) when a route, code or import changes; J21.8 when `management/query_parameters.py`'s skip changes; `volume` (`test_consumer_list_volume`, `test_consumer_xref_volume`) when a list's, a parameter's or XREF's or batch resolve's statements change; `queries` when the shared object list builder changes |
| `engine/model/placements.py`, `GET /model/placements` in `management/routers/model.py` | `model` (`test_model_placements`) + `contract` | always | `change_sets` + `records` + `matrix` (the planner) and `queries` (parent candidates) |
| `engine/model/{releases,registry,runtime,metadata,drafts,diff,compatibility}.py`, `management/routers/model_*.py`, `management/projections/model_metadata.py` | `model_admin` | activation or registry resolution changes | `workspaces` (pinned contexts), `startup` (registry at lifespan) |
| `db.py`, `migrations/**`, `main.py` lifespan, `engine/model/bootstrap.py`, `management/dependencies.py`, `cli/*`, `tests/postgres_server.py`, `tests/seeds.py`, `tests/browser_seeds.py` | `startup` | always for migrations | AGENTS.md startup rules: bootstrap, upgrade, restart, interrupted migration, lifespan, smoke start |
| `models/database.py` | the owning group | a column, index, constraint or table changes | `startup` (`test_schema_drift` compares a migrated head with the metadata: columns, types, indexes, unique constraints and foreign keys, each difference named) |
| `engine/records/objects.py`, `attributes.py`, `values.py`, `management/routers/objects.py`, `management/routers/attributes.py` | `records` | typed conversion or version claims change | `queries` (typed filters), `change_sets` (change set writes use the same value forms) |
| `engine/records/rules.py`, `refusals.py`, `context.py` | `records` + `change_sets` (`test_rule_parity`) | always | `mapping` (the replacement's scope and binding rules), `matrix` (type changes, restructuring), `volume` when a lookup's statements change |
| `engine/records/writes.py`, `audit.py`, `feed.py` | `records` + `change_sets` + `mapping` + `matrix` + `feed` | always | `volume` (write and publish budgets); `jobs` (batches record through the write unit); `test_pg3_concurrency` when `_begin` or the counter changes |
| `engine/reads/feed.py`, the feed route and schemas, `engine/change_sets/publish.py` (`publish_entries`) | `feed` | always | `change_sets` when the publish changes; `contract` when the route or entry shape changes |
| `engine/events/*` (0.9 C10: the plan, the deriver and its thread), `engine/reads/consumer_events.py`, the events route | `feed` + `consumer` (J30, `tests/unit/engine/events/`) | always | `volume` (`test_consumer_event_volume`) when the deriver's or the read's statements change; `startup` when the thread's start in the lifespan changes; `contract` when the route or a code changes |
| `engine/events/subscriptions.py`, `subscription_rules.py`, `webhook_urls.py`, `common/sealing.py`, `management/routers/consumer_subscriptions.py` and its schemas (0.9 C11) | `feed` (`test_j30_subscriptions`, the URL and sealing unit tests) | always | `model_admin` when `suspend_left_behind` or the activation call changes; `workspaces` when the retirement or deletion hook changes; `contract` when a route, a code or the capabilities change; `startup` when the settings check or the migration changes |
| `engine/events/dispatcher.py`, `delivery.py`, `webhook_client.py`, the delivery columns (0.9 C12) | `feed` + `consumer` (`test_j30_delivery`, `test_j30_acceptance`, `tests/unit/engine/events/`) | always | `volume` (`test_consumer_event_volume`) when the claim's or a batch's statements change (C13); `startup` when the thread's start or the migration changes; `contract` when the subscription answer, a reason or the capabilities change |
| `engine/jobs/*`, `management/routers/jobs.py`, `management/schemas/jobs.py`, the batch items in `models/commands.py` (0.9 B1, B2), `models/exports.py` (0.9 J1), `engine/imports/*`, `engine/reads/context_sets.py`, `management/routers/imports.py`, `management/schemas/imports.py`, `models/imports.py` (0.9 J2) | `jobs` (the J11, J24 and J27 journey tests, `test_export_volume` for an export's statements, `test_import_volume` for an import's binding, `tests/unit/engine/imports/`, `tests/unit/engine/jobs/`, and the unit tests of `config.py`, `main.py`, `models/commands.py` and `records/audit.py`; its serial part holds the worker's retry wait) | always | `records` + `change_sets` when an item's single-write core (`decide_…`) changes; `matrix` (`test_matrix_states`) when `matrix_states.deferred` changes; `volume` for item cost (`test_batch_statements`; `test_batch_volume` and `test_background_volume` are `budget`: a release's acceptance only, H3); `contract` when the request or a job shape changes; `startup` (`test_schema_drift`, J12) when the tables, the settings or the worker's start in the lifespan change |
| `common/outage.py` (0.9 C12: the background threads' outage log) | `jobs` + `feed` (`tests/unit/common/test_outage.py`, J24.6, the worker's unit outage case) | always | `startup` (J12.8's outage case) |
| `engine/records/relations.py`, `relation_set_versions.py`, `relation_writes.py`, `relation_sets.py`, `management/routers/relations.py` | `records` + `mapping` | always | `change_sets` (change set relation writes, publishing merge); `jobs` (relation items decide through the same steps, 0.9 B3); `matrix` when what a relation write lays over the batch lookup changes |
| `engine/records/deletion.py` (since 0.9 K2b the one deletion path: the single `DELETE` and a batch's delete items, live and in a change set) | `records` | cascade or preview token changes | `mapping` (continuation invalidation), `change_sets` (change set deletion), `jobs` (J11.6 delete items, `test_batch_statements`' delete runs), `contract` when an outcome or item field changes |
| `common/pagination.py`, `cursors.py`, `management/paging.py` | `queries` (`test_pagination`, `test_paging_contract`, `test_change_set_position_reads`) | always | every group with a collection endpoint: `-m "queries or mapping or model_admin or workspaces"`; `volume` (read budgets) |
| `engine/workspaces/catalogue.py`, `management/routers/workspaces.py` | `workspaces` | scope resolution changes | `mapping` (C-MAP-W authority), `change_sets` |
| `engine/change_sets/*`, `engine/reads/change_lists.py`, `engine/workspaces/workspace_audit.py`, `engine/records/audit.py` | `change_sets` | overlay, publishing or audit projection changes | `mapping` (change set coverage and replacement), `records` (history); `volume` when a change set read or write path changes |
| `engine/operations/type_changes.py` | `change_sets` + `records` + `matrix` (`test_type_changes`, `test_restructuring_planner`) | always | `queries` (`test_change_lists`, `test_parent_candidates`) when the change lists or the D42 refusal change; `volume` when a change set write path changes |
| `engine/operations/restructuring.py`, the restructuring routes in `management/routers/change_sets.py` | `change_sets` + `records` + `matrix` (`test_restructuring_planner`, `test_restructuring_api`) | always | `volume` (`test_restructuring_volume`) when planning reads or the dry run change; `queries` (`test_parent_candidates`) when `possible_types` changes, which `includeTypeChanges` reads; `contract` when a request or plan shape changes |
| `engine/reads/snapshot_reads.py`, `engine/indexes/snapshot_values.py`, `engine/reads/relation_queries.py` | `change_sets` + `queries` (`test_context_read_parity`, `test_paging_contract`, `test_change_set_position_reads`) | always | `volume` (change-set and publication read budgets); `startup` when the typed value index or its backfill changes |
| `engine/reads/object_lookup.py`, `GET /objects` in `management/routers/objects.py` (0.9 Q1) | `queries` + `change_sets` (`test_cross_type_lookup`) | always | `contract` when the route's parameters change; `volume` (`lookup:` read budgets); the `object_query.py` or `snapshot_reads.py` row when a shared builder changes |
| `engine/reads/model_query.py`, `models/queries.py`, `management/projections/model_query.py`, `management/routers/queries.py`, `expansion_rows` in `engine/reads/relation_queries.py`, `common/sql.py` (0.9 Q3) | `queries` + `change_sets` (`test_model_query`) | always | `contract` when the body or response changes; `volume` (`query:` read budgets); the `object_query.py`, `snapshot_reads.py` or `relation_queries.py` row when a shared builder changes |
| `models/search_index.py`, the search predicate in `engine/reads/object_query.py` | `queries` + `change_sets` (`test_search_index`, `test_context_read_parity`) | always | `startup` when the index DDL changes (a new migration, `test_schema_drift`); `volume` (search budgets) |
| `engine/operations/mapping_replacement.py`, `management/projections/mapping.py`, `engine/reads/mapping_projection.py`, `management/routers/mapping.py` | `mapping` | never by default | `change_sets` only if publishing or change set overlay is touched |
| `management/projections/relation_matrix.py`, `management/routers/relation_matrix.py` | `matrix` | always | `volume` (matrix read budgets, `test_volume_baseline`); `contract` when the route or page shape changes |
| `engine/indexes/matrix_states.py`, `engine/reads/matrix_cells.py`, or a write path that bypasses the ORM | `matrix` (`test_matrix_states`, and `verify` after every matrix test) | always | `change_sets` and `records` (the write paths it maintains); `startup` when the tables, migration or startup build change; `volume` (filter budgets) |
| `engine/indexes/unique_values.py`, the `unique_attribute_values` triggers (0.9 J2a) | `records` + `change_sets` (`tests/unit/engine/indexes/test_unique_values.py`, J03.8, J06.4, J08.10, J11.1) | always | `jobs` (the batch's redo); `model` (activation's trigger); `startup` when the revision changes; `volume` (`test_batch_statements`) |
| `errors.py`, `management/errors.py`, `management/presenters.py`, `common/encoding.py` (`records`: `test_encoding`) | the group of the changed error | error envelope shape changes | `contract`; `model_admin` (`test_build07_wp11` correlation IDs) |
| `management/reference/**` (the `/docs` page and its bundled script), `RDM_API_REFERENCE_SCRIPT` in `config.py` (0.9 V1) | `contract` (`test_api_reference`, `test_openapi_contract`) | always | `test:browser:v1` when the page, the script or its options change; `test_startup` when settings parsing changes |
| An import between modules, or a new module | `contract` (`test_boundaries`) | always | none |
| Any router signature, parameter or response model | the router's group | always | `contract` (re-baseline the OpenAPI lock only for intended changes) |

### Frontend

| Changed boundary | Direct | Expansion |
| --- | --- | --- |
| `src/api/*` | `npx vitest related <file> --run` (a change to `client.ts` selects 24 of 36 files) | the browser runner covering the consuming surface if request shape or error handling changes |
| `src/routing/*`, `src/app/useRouter*` | `src/routing`, `src/app` | `wp9-navigation.mjs` for URL or history behavior |
| `src/lib/hooks/useCursor*`, `src/ui/ScrollWindow.tsx`, `src/ui/ObjectLookup.tsx` | `vitest related` | `test:browser:s5`; scroll, landing or anchor changes also `test:browser` (record return and URL restoration); nested windows or the `group` role also `test:browser:s6` |
| `src/features/objects/Explorer.tsx`, `RecordTree.tsx`, `src/model/collections.ts` | `Explorer.test`, `vitest related` | `test:browser:s6`; `test:browser` (tree steps and `ui03b-hierarchy`) and `test:browser:wp14` (a heading opens a scoped collection) |
| `src/model/*` | `--project unit`, `src/model` | `vitest related` when a read's result shape changes |
| `src/model/placements.ts`, `src/test/placements.ts`, `src/test/starterPlacements.json` | `vitest related` | every tree runner (`test:browser:s6`, `test:browser`, `test:browser:b3`, `b4`, `c4`) and `wp9-authoring.mjs` (parent types in the object form); regenerate the starter fixture from `backend/tests` with `test_model_placements.write()` when the starter model's containment changes |
| `src/ui/*` shared components | `vitest related` | `test:a11y`/`test:visual` scenario for the changed control only when focus, semantics or tokens change; full gates at WP-9 |
| `src/features/objects/MappingGridView.tsx` and its `views/` host | `vitest related` (3 files) | `wp14-contextual-browser.mjs`, `wp13c-ui-states.mjs` |
| `src/features/objects/RelationMatrix*.tsx`, `relationMatrixStates.tsx` | `views/RelationMatrixView.test`, `vitest related` | `test:browser:a4`; `test:browser:a5` for the cell dialog, create, link or publishing paths; the `relation-matrix*` a11y and visual scenarios when the grid or dialog renders differently |
| `src/features/objects/TreeView.tsx`, `TreeMoveDialog.tsx`, `useTreeDrag.ts`, `RestructuringDialog.tsx`; `src/model/treeDrop.ts`, `src/model/restructuring.ts` | `views/TreeView.test`, `RestructuringDialog.test`, `model/treeDrop.test`, `model/restructuring.test`, `vitest related` | `test:browser:b3`, `test:browser:b4`, `test:browser:c4` (restructuring, or a change-set path of Move to… or the drag) and `test:browser:c5` (the milestone journey); the `tree-lens`, `tree-drag-*` and `tree-move-dialog` a11y and visual scenarios when the tree, a drag or the move dialog renders differently, and `tree-move-type-change` and `restructuring-*` (C5) when Move to…'s type-change marks, the preview or a restructuring dialog render differently; with `RecordTree.tsx`, also the `RecordTree` row's runners |
| `src/ui/DataTable.tsx`, `ObjectTable.tsx`, `SelectionCheckbox.tsx`, `src/lib/recordSelection.ts`, `src/lib/hooks/useRecordSelection.ts`, `src/features/objects/CollectionView.tsx`, `SelectionBar.tsx` (0.9 K1) | `recordSelection.test`, `ObjectTable.test`, `views/CollectionView.test`, `SelectionBar.test`, `vitest related` | `test:browser:k1`; `test:browser:j4` when the collection header changes |
| `src/features/objects/BulkChangeDialog.tsx`, `bulkChange.ts`, `src/lib/readMatching.ts`, `src/features/jobs/BatchOutcome.tsx`, `Verdict.tsx`, `JobPage.tsx` (0.9 K2) | `BulkChangeDialog.test`, `bulkChange.test`, `JobPage.test`, `recordSelection.test`, `vitest related` | `test:browser:k2`; `test:browser:j4` when the preview sections or the job page change; `test:browser:k1` when the selection bar changes |
| `src/features/objects/BulkJobDialog.tsx` (the flow every bulk action shares), `BulkDeleteDialog.tsx`, `bulkDelete.ts`, `src/test/jobStream.ts` (0.9 K2b) | `BulkDeleteDialog.test`, `BulkChangeDialog.test`, `bulkDelete.test`, `JobPage.test`, `vitest related` | `test:browser:k2b`; `test:browser:k2` when `BulkJobDialog` or `BatchOutcome` change; `test:browser:k1` when the selection bar changes |
| `src/features/objects/BulkRelationDialog.tsx`, `bulkRelations.ts`, `bulkRelationChoices` in `src/model/lookup.ts`, `src/ui/RecordListField.tsx`, `src/ui/ChipList.tsx` (0.9 K3) | `BulkRelationDialog.test`, `bulkRelations.test`, `RecordListField.test`, `JobPage.test`, `vitest related` | `test:browser:k3`; `test:browser:k2` and `test:browser:k2b` when `BulkJobDialog` or `BatchOutcome` change; `test:browser:webhooks` when `ChipList` changes (`MultiSelect`, `TokenField`); `test:browser:k1` when the selection bar changes |
| `src/features/objects/**` other | the file's test and `vitest related` | the runner for the surface (section 1 table) |
| `src/features/workspaces/**` | `src/features/workspaces` | `wp9-change-sets.mjs` or `wp9-publications.mjs`; `wp11-model-admin.mjs` and `wp13c-ui-states.mjs` for version selection; `w4-workspace-admin.mjs` for `WorkspaceAdmin` and `WorkspaceSelector`; `p2-change-review.mjs` for `ChangeSetReview` and the change set bar's review entry |
| `src/features/settings/**`, `src/app/SettingsShell.tsx`, `SettingsArea.tsx`, `SettingsMenu.tsx`, `TopBar.tsx`, `ShellFrame.tsx`, `src/lib/tableDensity.ts` (`TopBar` and `ShellFrame` also `test:browser`) | `src/features/settings`, `vitest related` | `u3-settings.mjs`; `u4-integration.mjs` for the Integration pages and the navigation; `u5-webhooks.mjs` for Webhooks; `j1u-export.mjs` for Jobs and feed, the job page and exports (also for `src/features/jobs/**`, `ui/Toast.tsx` and a collection's Export); `j4-import.mjs` for imports (also for `src/features/jobs/**`, `ui/FileField.tsx` and a collection's Import); `w4-workspace-admin.mjs` and `wp12-release-identity.mjs` when the Workspaces or Model pages change |
| `config.py` settings catalogue, `engine/reads/system.py`, `management/routers/system.py` (0.9 U3) | `startup` (`test_j31_system`, `tests/unit/test_config.py`) | always | `contract` when the response changes (`test_openapi_contract`, `test_api_journeys`) |
| `src/features/model-admin/**` | `src/features/model-admin` | `wp12-release-identity.mjs`, `wp11-model-admin.mjs` |
| `src/styles*`, theme tokens | none at T1 | focused a11y/visual scenarios for affected pages, plus dark variants |

### Worked traces (representative change per layer)

| Layer | Change | Selected | Cases vs blanket |
| --- | --- | --- | --- |
| Backend service | Mapping replacement validation in `engine/operations/mapping_replacement.py` | `py -m pytest -m mapping` | 115 of 532 (22%) |
| Backend shared | Keyset predicate in `common/pagination.py` | `-m "queries or mapping or model_admin or workspaces"` | 252 of 532 (47%) |
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
pytest invocations at once: they share the harness's PostgreSQL server. The backend suite is one
parallel invocation followed by its serial part, without `budget` (5-minute ceiling); the full-size
budgets run only at a release's acceptance (§1).

```sh
(cd backend && .venv/bin/python -m ruff check app/ tests/)
(cd backend && .venv/bin/python -m pytest -n auto -q && .venv/bin/python -m pytest -m serial -q)
(cd frontend && npm run format:check && npm run lint && npm run build)
(cd frontend && npm run test && npm run test:gate-helpers)
(cd frontend && npm run test:browser && npm run test:browser:authoring && npm run test:browser:change-sets \
  && npm run test:browser:publications && npm run test:browser:wp11 && npm run test:browser:wp12 \
  && npm run test:browser:wp14 && npm run test:browser:wp13c \
  && npm run test:browser:sc07 && npm run test:browser:sc15 \
  && npm run test:browser:s5 && npm run test:browser:s6 && npm run test:browser:s7 \
  && npm run test:browser:w4 && npm run test:browser:a4 && npm run test:browser:a5 \
  && npm run test:browser:b3 && npm run test:browser:b4 && npm run test:browser:p2 \
  && npm run test:browser:c4 && npm run test:browser:c5 && npm run test:browser:v1)
(cd frontend && npm run test:a11y && npm run test:visual)
```

Plus the AGENTS.md startup/migration smoke start against an isolated copy of the development database,
and the composed acceptance journeys WP-9 defines.

## 4. Measured execution cost

*History: measured before 0.9.0-alpha.1, when the backend ran on SQLite. The current costs are the
time ceilings in §1.*

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
- **Backend parallelism** was out of scope here; it is delivered in 0.9.0-alpha.1 H2
  ([parallel runs](#backend-parallel-runs-h2)).

### Not measured

Full frontend Vitest suite, the six other browser runners and the a11y/visual gates after this
change (their code paths only gained harness timing output). These belong to WP-9.
