# Test harness: seeded databases built once, faster runs, time ceilings, consolidation (H1–H4)

**Status:** Planned 2026-10-01, revised the same day: seeded databases first, and, once PostgreSQL
became the only database ([PG-D2](POSTGRESQL_RUNTIME_PLAN.md#decisions)), built on PostgreSQL.
**H1 is delivered inside [PG1](POSTGRESQL_RUNTIME_PLAN.md#pg1-runtime-baseline-and-test-harness)**,
so the harness is built once, for the database the product runs on. H2 and H3 follow PG2, when the
suite passes on PostgreSQL. Delivered one package per instruction ("deliver H2"). No product
behaviour, contract or model changes. **H2 is delivered (2026-10-01).** **Revised 2026-10-01 after
H2** (user's direction: development time must go to development, not to waiting for tests): every
run now has a [time ceiling](#time-ceilings), full-size budgets leave every run but the interim
release's acceptance, and H3 is split into H3 (budgets out of everyday runs) and H4 (cheaper
per-test work). **H3 is delivered (2026-10-01).** **Revised 2026-10-02 after an audit of the
suite** (user's decision): H4 becomes the [testing consolidation](#h4-testing-consolidation) onto
the [testing strategy](testing/STRATEGY.md), delivered in slices H4a–H4e before PG4. **Revised
2026-10-03 (user's decision): H4 stops after H4d-1.** H4a–H4c and H4d-1 are delivered and part of
the suite; H4d-2 onwards and H4e are postponed, to be continued later, and are no dependency of any
release up to 1.0. Development continues with PG4.

The measurements below were taken on SQLite (2026-10-01) and are the baseline PG1's measurement
compares against.

## The rule

**A seeded database is built once and reused until what it was built from changes.** No test run
seeds data that an earlier run already seeded from the same schema, model and seed code. A test that
needs its own copy gets a clone of the seeded database (a template database copy), never a new
seed.

## Time ceilings

Added 2026-10-01 after H2. H2's evidence run took 28 min 39 s; 21 minutes of that were two tests (the
100,000-item background batch, 1,145 s, and the 10,000-item atomic batch, 138 s). Those tests came
with B1 and B2 on SQLite, where the 100,000-item batch took about 15 minutes (B2's 433 items/s live
and 151 in a change set) against 19 on PostgreSQL. Each item costs a whole single write, dozens of
statements, and on PostgreSQL each statement is a round trip to the server; PG3b
([PG-D12–PG-D17](POSTGRESQL_RUNTIME_PLAN.md#decisions)) writes batch items in bulk and replaces the
timed checks with counted ones. PostgreSQL made an ordinary test about 1.5×
slower (`records` 21.7 s → 33.9 s, PG1), which parallel runs more than repay (`not volume`: 6 min
32 s serial on PG2, 1 min 49 s with `-n auto`). The cost is the size of a few tests, and the absence
of any limit on it.

| Run | When | Ceiling (wall time, this machine) |
| --- | --- | --- |
| Focused tests while iterating | any time | seconds: one module or case, without `-n` |
| A package's checks: testmon's selection and the journeys it touches, or its boundary's groups (EXECUTION_GUIDE §2) | end of a package | **2 minutes**, with `-n auto` and the groups' serial part |
| Build acceptance: the full backend suite without `budget` | end of a build | **5 minutes**, parallel part plus serial part |
| Full-size budgets (`-m budget`) | a release's acceptance only, once | announced with its expected time before it starts (about 25 minutes today; PG-D17's target is under a minute per context) |

The rules that hold the ceilings:

- **Announce before running.** A run expected to take more than 2 minutes is named with its expected
  time before it starts, and needs the user's go-ahead in a package. A result already measured is
  not measured again: a run is repeated only after the code it covers changed.
- **Full-size budgets never run by default.** They carry the `budget` marker, which a run selects
  only by naming it (`-m budget`). From PG3b their timed checks are statement counts at two seeded
  sizes (PG-D17; `test_batch_statements`, delivered 2026-10-02), and the 100,000-item batch is a
  measurement run once at PG5's acceptance.
- **The run reports what grew.** The summary lists every test over 10 s outside `budget`, so a
  package that makes a test slow sees it in its own run, not at the next acceptance. A package that
  adds a test over 10 s says why in its record, or makes it smaller.
- **`serial` means wall time.** Only a test whose outcome depends on wall time is serial. A test that
  counts statements or rows runs in parallel, however large its data.
- **A ceiling exceeded is a defect** of the harness or of the tests, reported and fixed in the next
  package, not a reason to stop testing.

## Why

- **Waiting for seeding.** Packages spend minutes rebuilding the same data before a test can run. In
  B2 the user waited 15–20 minutes at a time. Volume modules seed the volume fixture from scratch,
  each at its own scale (0.005, 0.01, 0.02, 0.04), in every run, although the fixture changes only
  when its code or the schema does.
- **Per-test setup through the API.** In the two heaviest `records` modules (`test_type_changes`,
  `test_rule_parity`), 1,231 HTTP requests took about 15 ms each, mostly creating the records a test
  needs before it tests anything; all their SQL together took 1.2 s of 34 s. The same records are
  created again for every test and for the renamed-model copy.
- **Building an application per test.** In `records`, 137 tests each start a fresh application
  (about 135 ms).
- **One core.** The suite runs on 1 of this machine's 10 cores, because one shared session database
  in `conftest.py` (22 modules use it) forbids two processes at once.
- **The matrix recheck after every test.** Eight modules recheck all matrix states when each test
  ends: 8.4 s of the 34 s above.
- **Full-size budgets inside packages.** B2's 100,000-item background batch ran three times. That
  data is the job under test, not a seed, so it cannot be cached; it can run at a smaller size in a
  package (H3).

## Packages

### H1: Seeded databases built once

**Delivered 2026-10-01 inside PG1 (its PG1 part):** the private server, the seed store with
fingerprints, `schema` and the volume seeds, clones per test, `python -m tests.seeds list|build`, and
the run summary. Evidence and timings are in
[PG1's record](POSTGRESQL_RUNTIME_PLAN.md#pg1-runtime-baseline-and-test-harness). **The browser
runners' seeds are delivered in PG2 (2026-10-01)**: `tests/browser_seeds.py` clones `schema`, a
`starter` seed per model and the volume seeds on the development server for each runner
([PG2's record](POSTGRESQL_RUNTIME_PLAN.md#pg2-postgresql-forms)). **The heavy modules' common
records were dropped (user's decision, 2026-10-01):** `test_type_changes` and `test_rule_parity`
share no records; each case creates its own through the API as part of the write it checks. H1 is
complete.

**Scope:** a seed store for the backend tests and the browser runners.

- **What a seed is.** A named database file built by a seed function: the migrated empty schema, the
  volume fixture at each scale the tests use, each heavy module's common records (on the generated
  model and on its renamed copy), and the browser runners' starter seed and prepared databases.
- **Where it lives.** Template databases on the test harness's private PostgreSQL server, whose
  data directory `backend/.test-postgres/` (git-ignored) is kept between runs (PG-D8).
- **When it is rebuilt.** Each seed carries a fingerprint: the Alembic head, the model it was built
  from, and the source of its seed function and of the fixture code it calls. On use, a matching
  fingerprint is used as it is; a different one rebuilds that seed once, and later runs reuse it. A
  schema, model or seed code change therefore rebuilds only the seeds it affects.
- **How a test gets it.** A test that writes gets a clone of the seed (`CREATE DATABASE … TEMPLATE`);
  tests that only read share one clone per module. The module's own writes still go through the API,
  as today.
- **Prebuilding.** `python -m tests.seeds build` builds every stale seed up front, for example after
  pulling a schema change, so no test run waits for it. `python -m tests.seeds list` shows each seed,
  its fingerprint and whether it is current.
- **Moved onto seeds:** the volume fixture (`volume_fixture.volume_app`), the migrated template (today
  rebuilt per session), and the browser runner harness's seed (`e2e/helpers/harness.mjs`), which
  today creates its records through the API on every run. (The heavy `records` and `change_sets`
  modules' common records were planned here too and dropped in PG2: they have none.)
- **Split with PG2 (decided 2026-10-01 at the start of PG1).** PG1 builds the seed store, the migrated
  schema seed and the volume fixture seeds. The heavy modules' common records and the browser
  runners' seed move onto seeds in [PG2](POSTGRESQL_RUNTIME_PLAN.md#pg2-postgresql-forms), once
  those modules and runners run on PostgreSQL.

**Evidence:** two runs of the same groups back to back, the second building no seed (its log names
each seed as reused), with times for both; a schema change rebuilding exactly the affected seeds;
the changed modules' groups green.

### H2: Parallel runs

**Delivered 2026-10-01.** `pytest-xdist` (3.8) is a dev dependency and `--dist loadfile` is in
`addopts`, so `pytest -n auto` parallelizes and a run without `-n` stays serial. The run's own
process starts the server, drops leftover databases and builds the `schema` seed in
`pytest_sessionstart`, before any worker starts, and stops the server in `pytest_unconfigure`, after
the last worker ends. Each worker clones its own session database (`t_session_gw<N>_…`) and sets its
own `DATABASE_URL`: a worker inherits the run's environment, and the first parallel run failed 244
tests because every worker pointed at the run process's session database, which is never created.
Workers send the seeds they used back, so the summary still names each seed as reused or built.
`serial` is the whole `volume` group plus two tests (the background worker thread's deadline in
`test_background_jobs`, and the current-live capture race decided by a 0.3 s timer in
`test_wp81b_current_live_bases`; `test_jobs_migration` no longer exists). A parallel run leaves them
out and its summary names the count and the command, `pytest -m "serial and (<expression>)"`.

Measured on the M1 Pro (10 workers with `-n auto`):

| Run | Tests | Wall time |
| --- | --- | --- |
| Before, serial, the whole suite | 1039 passed | 28 min 39 s, of which 1,283 s are the setups of the two full-size budgets (the 100,000-item background batch 1,145 s, the 10,000-item batch 138 s) |
| After, `-n auto`, everything except `serial` | 968 passed | 1 min 49 s |
| After, without `-n`, one module (`test_wp81b_current_live_bases`) | 14 passed | 5 s; the server started and stopped by the run |

The 71 `serial` tests were not rerun after the change: they run as before, one at a time in one
process, and their code is unchanged except for the marker, so their cost is the baseline's. A rerun
would have spent 19 minutes on the 100,000-item batch to repeat a known number; H3 moves the
full-size budgets out of package runs. **The 4× target is not shown.** Without the two full-size
budgets the baseline is about 436 s; after, the parallel part is 109 s plus the serial part without
budgets, which was not measured separately (the baseline's slowest list puts at least 75 s of it in
`volume` modules). That number is H3's: H3 changes what the serial part holds (only wall-time
tests; `budget` out of default runs), so it is measured once there, against the 5-minute ceiling,
rather than here and again there. Worker counts other than `-n auto` were not compared.

**Scope:** `pytest-xdist` as a dev dependency. The shared session database becomes one per worker,
so no two processes share a database; all workers clone from the same seeds on the one test
server. Tests run with `--dist loadfile`, so a module stays on one worker.
Timing-based checks (`volume`, the lock-wait tests in `test_jobs_migration`, the worker thread test
in `test_background_jobs`) carry a `serial` marker and run in a second, non-parallel invocation.
AGENTS.md's rule "never run multiple backend pytest processes concurrently" becomes "run one pytest
invocation at a time; it parallelizes itself". EXECUTION_GUIDE gives the commands.

**Evidence:** the full backend suite before and after, serial and parallel. Measuring the gain is
this package's purpose, so running the full suite here is the instruction, not a breach of the
no-full-suite rule.

### H3: Budgets out of everyday runs, the time ceilings enforced

**Delivered 2026-10-01.** `conftest.py` marks `test_batch_volume` and `test_background_volume`
`budget` (and `serial`), and leaves them out of every run whose `-m` expression does not name
`budget`; `pytest -m budget --collect-only` names exactly their 7 tests. `serial` comes from `TIMED`,
a list of modules and `module::test` entries with their reasons: the large workspace's validate and
publish (`test_graph_validation_scale`, one test) and H2's two timer tests, whose decorators moved
into the list. The six counting `volume` modules run in the parallel part. A default run collects
1032 of 1039 tests. The summary lists every test over 10 s outside `budget` (setup, call and teardown
added up, so a module fixture lands on its first test) and the run's wall time. AGENTS.md (Execution
discipline) and EXECUTION_GUIDE §1 carry the ceilings, "announce before running" and the commands.

Measured on the M1 Pro, the full suite without `budget`:

| Part | Tests | Wall time |
| --- | --- | --- |
| `pytest -n auto` | 1028 passed, 1 failed | 2 min 19 s |
| `pytest -m serial` | 3 passed | 22 s (the large workspace 19.8 s) |
| Total | 1032 | **2 min 41 s**, within the 5-minute ceiling |

The failure is a product deadlock, not the harness: a generic relation create and a mapping save on
one edge take their rows in opposite order, which the extra load of the volume modules in the
parallel part made reachable. It is recorded in
[PG3](POSTGRESQL_RUNTIME_PLAN.md#pg3-concurrency), whose workspace lock orders the two writes (fixed
there 2026-10-02, with a race test that holds the create while the mapping save waits); the test was
not rerun in H3. **The 4× target is not met:** about 436 s before H2 (without the budgets) against
161 s, 2.7×. The slowest tests outside `budget` were the first `test_change_set_position_reads` case
(48 s, carrying the module's volume fixture), `test_model_query`'s every-criterion test (18–19 s per
model), `test_matrix_states`' change set test (19 s), `test_restructuring_volume` (17 s),
`test_volume_baseline`'s live test (17 s) and a `test_rule_parity` case (17 s); H4 takes them, since a
package whose groups include `volume` or `queries` waits for them. The run was started without the
user's go-ahead, against the rule this package wrote.

Revised 2026-10-01 (was "Cheaper per-test work and budget sizes"; the per-test work moved to H4).
Small: markers, a scale, the summary, and the rules in AGENTS.md and EXECUTION_GUIDE.

**Scope:**

- **`budget` marker, out of default runs.** B2's 100,000-item background batch
  (`test_background_volume`) and B1's 10,000-item atomic batch (`test_batch_volume`) carry `budget`,
  and a run leaves `budget` tests out unless its `-m` expression names `budget`. No scale setting:
  PG3b replaces their timed checks with statement counts at two seeded sizes (PG-D17), and the
  100,000-item batch is measured once at PG5. The plans' "Budget" lines say so.
- **`serial` narrowed to wall time.** `serial` comes from a `timed` list of modules and single tests
  instead of the whole `volume` group: `test_graph_validation_scale` and H2's two timer tests
  (`test_batch_volume` and `test_background_volume` are `budget`, and serial when named). The six
  volume modules that count statements and rows (`test_volume_baseline`, `test_paging_contract`,
  `test_change_set_position_reads`, `test_relation_matrix_volume`, `test_change_lists_volume`,
  `test_restructuring_volume`) run in the parallel part.
- **The slow-test report.** The run's summary lists tests over 10 s outside `budget`, with their
  times, and the run's wall time.
- **The rules.** AGENTS.md (Execution discipline) gains the ceilings and "announce before running";
  EXECUTION_GUIDE gives the commands for each row of the ceilings table.

**Evidence:** the full suite without `budget`, parallel part and serial part, each with its wall
time against the 5-minute ceiling (this run is H3's purpose and is announced with its expected
time); `pytest -m budget --collect-only` naming exactly the budget tests. No `budget` run in H3: the
28 min 39 s baseline already holds it.

### H4: Testing consolidation

**Planned 2026-10-02** (replaces "Cheaper per-test work", whose items are in H4d). The user accepted
the audit's conclusions the same day: the suite moves onto the [testing strategy](testing/STRATEGY.md)
(unit tests for each piece of code's purpose, journey tests for every user journey, every piece of
code traced to a journey, selection by what a change can affect), the target "no test removed" is
replaced, and renamed-model copies stay only where model keys drive the code. **H4 comes before PG4**,
so PG4 is the first package delivered the new way. Slices are delivered one per instruction ("deliver
H4a"), in order; each depends on the one before it. The scope is the backend suite; the frontend's
Vitest projects and browser runners are mapped to journeys in H4a and consolidated in a later package.

**Why:** the [audit](testing/STRATEGY.md#findings-that-led-here-audit-2026-10-02): 1,063 cases
written per work package after the code, from the code; no test refers to a journey; four of 17
scenarios walked; duplicated refusals and model rules; fabricated database states; spies on private
functions; and every package over its 2-minute ceiling.

#### H4a: The journey catalogue

Documentation only, for the user's review.

**Delivered 2026-10-02; the user approved the catalogue the same day ("for now it's fine"), which
closes H4a.** The catalogue is revised as journeys are tested in H4c.

- [USER_JOURNEYS.md](product-functionality/USER_JOURNEYS.md) is the catalogue: 26 journeys (J01–J27,
  J09 retired) in six groups, each with its actor, channel, stories, example scenario, status, steps,
  named variants (`J02.2`, 138 in all), refusals by error code and today's evidence. **Revised the
  same day at the user's direction:** journeys are the engine's, never the example model's. Records,
  containment hierarchies and relationships within and across applications, with the rules the model
  declares (cardinality, required ownership, scoped uniqueness, typed relationship attributes, attribute
  rules), are the subject; translation (J09) is retired into generic variants of J02, J03 and J13, the
  mapping journey is "replace a record's related records" (J10) and the matrix "relationship coverage
  across ancestors" (J16). Every journey test runs on at least two model configurations and names no
  configuration's keys (STRATEGY, H4c's seeds). J01–J12 keep their IDs; J11 is
  narrowed to bulk changes, with background jobs (J24), the change feed (J26, planned) and supplier
  files (J27, planned) split out. New: relating records (J13), building and changing hierarchies (J14), reshaping across types (J15),
  relationship coverage (J16), change review (J17), the next model version (J18), workspace
  administration (J19), consumer API definitions (J25), and the integrator's journeys: discover
  (J20), read completely (J21), a precise dataset (J22), a business date (J23). Concurrency is a
  variant of the journey it threatens (J02.2, J03.8, J13.8, J14.8, J19.2, J24.1, …); J12 gained the
  operator's variants, among them the worker's database outage (J24.6, J12.8).
- [API_JOURNEYS.md](testing/API_JOURNEYS.md) maps every one of the 81 operations, every query
  parameter and header, all 139 error codes the backend raises, every setting and command, and every
  browser runner and frontend test area to journeys. Every route, code and setting has a journey.
- **Seven decisions** raised for the user (D-1–D-7 in API_JOURNEYS): two routes for one list (keep
  both), two ways to change one value (keep both), unknown query parameters silently ignored
  (recommend refusing them), 32 undocumented error codes (document them in H4c), lifecycle audit
  recorded but readable by no route (a hidden capability; decide F1 or a read), batch delete without
  cascade (PG-D18), and a stale command help text.
- The strategy's audit finding was corrected: the browser runners walk more scenarios than the
  backend (SC-01 to SC-09 in parts, SC-15, SC-17), but only through the UI.
- **The user's decisions (2026-10-02):** D-2 keep both ways to change a value; D-3 refuse unknown
  query parameters and D-4 document the 32 codes, both in H4c; D-5 keep recording lifecycle audit
  and add reads (J19.5, J08.9; TODO); D-6 batch delete items cascade (J11.6; PG-D18); D-7 the
  command's help fixed (built from the supported schema list). D-1 was answered (the two routes are
  identical), and the user decided to remove `GET /mappings` (in H4c).

**Checks:** a one-off script compared API_JOURNEYS with the OpenAPI document of `create_app()` and
the codes in `app/` (no route, code or setting missing), every code a journey cites exists in the
backend, every variant the inventory cites is defined, and every relative link resolves. No test
was run (documentation only). H4b turns the comparison into a check.

**Scope:**

- [USER_JOURNEYS.md](product-functionality/USER_JOURNEYS.md) extended from J01–J12 to every client:
  stewards (UI and API), **integrators** (the user stories US-I01–I09 and the 0.9 APIs: paged and
  resumable reads with cursor, position, seek, `from=end`, anchor and totals; the cross-type lookup;
  the model-aware query; the edge list; batches and background jobs; consumer API definitions),
  **operators** (start, upgrade, refusal and recovery, a database outage under the job worker) and
  **model authors** (drafts, releases, activation, schema upgrade). Concurrency is a variant of the
  journey it threatens: two stewards correcting one record, an import running while stewards work,
  an activation or a retirement beside writes.
- Each journey: an ID, its actor and channel (API, UI, operator command), its steps, its named
  variants, its refusals with their codes, and the scenario data it runs on.
- **The API inventory.** Every route and every parameter of the OpenAPI document mapped to the
  journeys and variants that use it. The API is the product (strategy, first section): an option
  serving an integrator journey stays even when the UI never uses it. An option that serves no
  journey of any client is listed for the user to decide: a journey to add, or the option closed.
- Every browser runner and frontend Vitest project mapped to its UI journeys (for the later package).

**Exit:** the user approves the catalogue, and no inventory entry is left without a journey or a
decision.

#### H4b: Traceability and selection

**Scope:**

- A `journey` marker taking catalogue IDs; a test naming an ID the catalogue does not hold fails
  collection.
- The layout `tests/journeys/` and `tests/unit/<tier>/<module>`; `TEST_GROUPS` keeps only what the
  layout and markers cannot say.
- `pytest-testmon` (dev dependency): a change selects the unit tests that execute the changed code
  and the journeys linked to it. Changes coverage cannot see (the model schema, migrations, the
  starter model, seed code, configuration) select everything that reads them, by rules in the
  execution guide.
- The trace report (`python -m tests.journey_trace`): from the journey tests' coverage, the modules
  each journey executes, and the modules no journey reaches.
- ~~The mutation score of `app/engine` (`mutmut`) as H4d's baseline.~~ **Dropped 2026-10-02 (user's
  decision).** Probes showed about 40 s per file to generate mutants (1.5 hours for `app/` before any
  test runs), several thousand mutants each re-running database tests, and a dozen test files that
  break when copied. H4d checks each area by breaking the code on purpose instead.

**Exit:** two shown selections, a change to a module many others use and a change to one route,
each running what the strategy's table says; the trace report recorded.

**Delivered 2026-10-02.**

- **Journey marker and layout** (`tests/layout.py`, `conftest.py`): `@pytest.mark.journey(...)` with
  IDs read from USER_JOURNEYS.md (a retired journey is not one); an unknown ID, or a journey test
  without one, fails collection; `--journey J02` selects a journey with its variants. `tests/journeys/`
  and `tests/unit/` are packages, so unit tests may share file names; a unit test must mirror the
  module it tests (`tests/unit/engine/records/test_rules.py` → `app/engine/records/rules.py`,
  `tests/unit/harness/` → `tests/`). The flat modules keep `TEST_GROUPS` until H4d moves them.
  Shown on throwaway files: an unknown ID, a retired one, a missing marker and an unmirrored unit
  test each refused (exit 4); `--journey J02` selected the J02 test and not the J13.5 one.
- **The inventory check** `test_api_journeys.py` (`contract`): every operation, query parameter,
  header, raised error code and setting must be in API_JOURNEYS.md, and every journey it cites must
  exist. The routes table now names every operation in full. Shown by deleting one route and one
  code from the inventory: both named, then restored.
- **Selection by change:** `pytest-testmon` (2.2) as a dev dependency. **Coverage runs on the C
  tracer** (`COVERAGE_CORE=ctrace`, set in `conftest.py`): on Python 3.14 the default
  `sys.monitoring` core lost the code run in the TestClient's request threads when testmon switched
  tests (an API test recorded 5–13 app modules of the 38–66 it ran). `python -m tests.affected`
  prints what a change requires, with the rules for what coverage cannot see.
- **The trace report** `python -m tests.journey_trace` (named so as not to shadow the standard
  library's `trace`): on the full data, 2 modules with functions are reached by no test
  (`management/schemas/jobs.py`, `management/schemas/queries.py`), 5 declaration-only modules cannot
  be traced, and no module is reached by a journey test yet (H4c writes them).
- **Mutation testing dropped** (user's decision): see the struck item above.
- **Fixed on the way:** the volume measurement (`volume_fixture.measure`) counted the background
  job worker's statements when its startup sweep fell inside a measured request, which the slower
  tracer made happen (`test_restructuring_volume::test_planning_reads_level_by_level` failed once);
  it now leaves out the worker's thread (`worker.THREAD_NAME`).
- **Found, for H4d:** seven modules route "live" tests through a change set
  (`ChangeSetTestClient`, see H4d's scope). `test_model_lifecycle::test_draft_crud_compile_and_installation_lifecycle`
  failed once in the full parallel run under the C tracer and passed in five reruns (alone, in its
  groups in parallel, and reselected); its failing assertion was not captured (the run's output was
  filtered, not kept). Candidate, unconfirmed: its whole-table row counts before and after compiling
  run while the app's job worker sweeps.

**Exit evidence** (selection on the full testmon data; edits behaviour-preserving and reverted):
a change in `as_utc` (`app/common/time.py`, under every timestamp read) selected 732 of 1,087 tests,
exactly those whose recorded code includes it; a change in the job-cancel route selected 6 (the
cancel tests on both models and two concurrency tests).

**Checks:** the full suite once under testmon (parallel part 1,077 passed and 1 failed, the
restructuring volume test above, in 2 min 51 s; serial part 3 passed), then the tests testmon
selected after the fix: 676 passed and the lifecycle test failed, then passed when reselected
(1 passed); the testmon data holds 1,087 tests and no failure. The harness unit tests (10) and the
inventory check (5) pass; `ruff check app/ tests/`. A first full testmon run on the
`sys.monitoring` core (1,078 passed, 2 min 18 s) gave incomplete data and was discarded. Not run:
frontend and browser runners (nothing there changed). Every server the package started was stopped,
and `mutants/` and the probe logs were deleted.

#### H4c: Journey tests

**Delivered 2026-10-03.** Every catalogue entry with an API or operator side has its journey test,
and every deviation found has the user's decision (records below).

**Scope:**

- A `scenario` seed per model configuration in the seed store: at least two configurations that
  differ in keys and shape (the example model and a generated model), each with the structures the
  journeys need (two workspaces, a deep self-hierarchy and a mixed-type one, relationships of every
  cardinality within and across applications, required ownership, scoped uniqueness, a large related
  set), built through the API once and cloned per test. No journey test asserts a configuration's
  keys; the example model is tested only as one configuration.
- One test per catalogue journey and variant with an API side, given/when/then, asserting the data,
  status and error code the actor sees. The cases are written from the catalogue in a separate
  context (one subagent) and shown to the user as a list per journey group before they are coded.
- They run against today's code. A failing case is a product defect or a specification gap,
  recorded with a decision; a case is never changed to fit the code.
- The four existing composed tests (SC-05, SC-07, SC-11, SC-15) become journey tests.
- **Decided in H4a (2026-10-02):** unknown query parameters are refused, `422 unknown_parameter`
  naming the parameter (D-3, journey variant J21.8): its journey test is written first and fails,
  then the change follows, with the OpenAPI lock re-baselined. `GET /workspaces/{key}/mappings` is
  removed (D-1; `GET /workspaces/{key}/relations` is the same list). The 32 undocumented error codes are
  documented in API.md beside the journey tests that meet them (D-4).

**Exit:** every catalogue entry has its test, or is UI-only with its browser runner named; every
failure found has a decision; the [deviations list](#deviations-between-apimd-and-the-code) is complete
and every line has the user's decision.

**A case corrected to API.md:** J04's case counted one kept association; API.md counts every
relationship with an end outside the deletion set, so the dependant's link to its container counts
too (two).

**Test data adjusted, expectation kept:** J03.2's and J14.2's wrong-type parent stands in the same application
as the child; the case put it in the other application, where API.md's scope rule refuses it first. J14.1 moves the subtree under
the other branch's top record, where the case's "one shorter" holds (it named the level-2 record).

**Cases written 2026-10-02.** 154 cases, given/when/then, written from the catalogue, API.md and the
scenarios in a separate context that read no code; the user accepted them "for now" (each test keeps
its case as its description). No variant is UI-only; three steps inside cases are (J01 step 5, J10.4's
kept choice, J10.8's cancel), with their runners named. Planned, no case: J08.9, J19.5, J11.6, J26,
J27, J12.9. The model configurations: two generated models that hold every structure the cases need
and differ in keys and shape; each test runs on generated A and on the example model where it has the
test's structures, otherwise on generated B (the starter lacks a read-only attribute, a maximum, a
one-to-one binding, relationship attributes, a non-owning required binding and a consumer API).

**Decisions taken while writing the cases (user, 2026-10-02):**

- **The catalogue follows API.md where they disagreed** (the code agrees with API.md in each):
  J02.5's bounds (`attribute_below_minimum`, `attribute_above_maximum`), J05's and J06.2's publish
  divergence (`409 version_conflict` with `details.conflicts`, not `activation_conflict`), J10.6's
  (`mapping_set_changed` within it), J08.5's stale activation (`409 activation_conflict`), J17's
  filters (`unknown_object_type`, `unknown_relation_type`), J18.3's and J18.4's codes (the
  `pinned_model_*` codes, `change_set_version_conflict`), J15's type-change codes against the
  restructuring preview's plan problems, J20's release header (the model read only), J24.5's
  expired outcomes. Corrected in USER_JOURNEYS.md.
- **To confirm:** a refused stale record write (`409 version_conflict`) carries no current version
  (J02.2). The user decided to fix it on my statement that API.md promised it; API.md promises it only
  for workspace updates (deviation 1). J02.2's journey test fails until this is settled.
- **The relation-set version on the anchored relationship read**: a set claim works for every
  binding. Its version is readable from a matrix or mapping view and, with no view, from the workspace
  edge list, but only for a record that has an edge of the binding (corrected the same day: I first
  told the user no read without a view existed). Planned into 0.9
  [B3](BASE_0_9_IMPLEMENTATION_PLAN.md#b3-relation-and-relation-set-items). J13.5's test reads the
  version from the edge list.
- **J10 replaces a record's related records with one record, or none**, as WP-5 built it; the
  catalogue said "a new set". Several records in one save is B3's extension.
- **Two behaviours API.md did not state**, written into it as they are: validating an invalid change
  set answers `200` with `valid: false` and diagnostics; an expired job's items read as an empty page.
- **Keeping the catalogue current** is now a rule (STRATEGY "How a package uses this", AGENTS working
  method step 5): a package that adds or changes a journey extends USER_JOURNEYS.md and API_JOURNEYS.md
  before its cases are written.

**Progress.** Group 1 (records and structure: J01–J04, J13–J15) coded 2026-10-02: 53 cases, 106 runs
on two configurations, 20 s with `-n auto`; the failures are deviations 1, 7 and 8. The race helper
(`World.race`) holds the workspace row from the test's own connection and watches from a second one;
its first version watched inside its own transaction, saw a stale `pg_stat_activity` and waited on
itself (two runs hung until stopped). J15.1 changes the record back by moving it to the top level as
L1, where L1 stands (the case named `changeType`, which keeps the parent).

Group 2 (J10, J16) coded the same day: 28 cases; the failures are deviation 9. Generated A gained an
optional container between a scope record and its dependants (B requires one), so J16.2 runs on both.
Group 3 (J05–J07, J17, J18) coded the same day: 24 cases, all passing. J05.4 stages its scope breach by
moving a container (API.md's example), since a staged create is refused (deviation 9). Three races are
checked as guarantees rather than forced orders, because forcing the order needs engine hooks: J05.7 (a
capture beside a live write: the capture holds the write or asks for a retry), J06.3 (publishing beside
a live write and another change set's write: no refusal or deadlock), J17.3 (a change-list page and
its paths are one snapshot while renames commit). J18.3's corrupt and unsupported releases are written
into the store, as only an older engine or a damaged store produces them.

Group 4 (J08, J19, J25) coded the same day: 17 cases, all passing. J19.2 checks retirement beside a
live and a change-set write as a guarantee over both lock orders. J19.4 expects `405` for a disabled
workspace route whose path keeps its read, `404` otherwise (the framework's answer; API.md states
`404` only for model administration). J25.1 lowers the contract version from 2 to 1 (the case said
to 0, which the schema does not allow). J25.2 projects from the relationship's many side, where
one-to-many to many-to-many changes the shape (one record to a list); from the one side both are
lists. J25's removed field is named by its diagnostic, which points at the field's parent: a removed
field has no place in the new document.

**D-1 and D-3 delivered 2026-10-02.** `GET /workspaces/{key}/mappings` is removed (its path keeps the
replacement's `PUT` and answers a `GET` with `405`); the four old modules that read it use
`GET /workspaces/{key}/relations`, and the OpenAPI lock was re-baselined (one paged collection fewer).
Unknown query parameters are refused as `422 unknown_parameter` naming each (`details.parameters`),
by one application-wide dependency (`app/management/query_parameters.py`); the object list and the
cross-type lookup also take the `filter.<field>.<operator>` family. J21.8's test failed first. A
static comparison found no parameter the browser client sends that its route does not declare.

Group 5's rest (J22, J23, J11, J24) coded 2026-10-03: 24 tests, 48 runs, all passing. Two races are
forced with the database's own locks, not engine hooks: J11.4 holds the workspace so the inline batch
waits after resolving its model while another release activates (refused `model_release_changed`, no
job, no record), and J24.3 holds it so worker A's chunk waits past its lease while worker B takes the
job over (A commits nothing). J24.2 cancels an atomic job while its chunk waits the same way. J24
drives the engine's own `JobWorker` chunk by chunk, a "restart" being a worker with another owner
after the lease expires; J24.6 takes the database away for real (`ALLOW_CONNECTIONS false` and its
sessions ended) while the worker runs on its thread. J24.1 (a steward beside an import) and J24.6 are
guarantees over whatever order occurs. J24.5 expires by the sweep's own clock argument. The race
tests passed in two repeated runs.

Group 6 (J12) coded the same day: 11 tests, 42 runs, on two configurations each. The operator
harness (`tests/journeys/service.py`) starts the application on a database with the configuration's
model and settings, reads its log as the operator output and runs `database_upgrade` and
`model_schema_upgrade` as processes. J12.6 stores the selected release as an engine before schema 0.5
did (the configuration's model at schema 0.4 with its own content hash), the state no API can write.
Two findings: the unsupported-schema refusal named schemas "0.5, 0.6 and 0.7", omitting 0.8, the stale
text D-7 decided to build from the supported list, so it is built from it now (`app/main.py`); and
J12.8's `/health` (deviation 10).

**D-4 delivered 2026-10-03:** the 32 codes are in [API.md, further error
codes](API.md#further-error-codes) with status, route and meaning, each beside its journey.

**The four composed tests.** SC-05 is J05.1, extended to relationships added and removed after the
last publication (the old test's point); SC-07 is J10 with its variants; SC-11 is J23; SC-15 is J18
with J18.2, which now also checks that discarding changes no live data. Their old modules
(`test_wp81b_current_live_bases`, `test_build07_wp9_acceptance`, `test_effective_periods`' SC-11
case) go in H4d with the rest of the flat suite.

**Old tests D-3 refused.** Each sent a parameter its route never declared, which the API used to
ignore; the calls were corrected, not the routes: two journey tests (J01's history read with
`workspaceKey`, J10's candidate search with the binding's fields, which only coverage takes),
`test_typed_table_queries` (history with `workspaceKey`), `test_batches` (a live `DELETE` with
`workspaceKey`) and `test_wp8_history`, whose live `PATCH` and `POST` named a `publicationId` and
asserted the write went live anyway: they now assert the refusal, then write without it.

**Checks (2026-10-03).** The journey suite and the inventory check: 345 runs, 335 passed, 10 failed,
exactly deviations 1, 7, 8, 9 and 10 (1 min 7 s, `-n auto`). The guide's selection for the change
(testmon, since the D-3 dependency in `app/main.py` runs under nearly every API test): 1,030 passed
and 15 failed, the deviations above plus the three old modules corrected afterwards (41 passed in
their modules) and `test_model_lifecycle::test_draft_crud_compile_and_installation_lifecycle`, the
intermittent failure H4b recorded, failing again in the full parallel run and passing alone (6 min
22 s under the coverage tracer). The serial part: 3 passed. `ruff check app/ tests/`. Not run: the
frontend build and browser runners (nothing under `frontend/` changed).

**Deviations decided 2026-10-03 (user):** 1, 2, 6, 7, 8, 9 and 10, each applied to its case (the
table below). 6, 7 and 8 settle four rows of E-D4 ([BACKEND_BOUNDARIES_PLAN](BACKEND_BOUNDARIES_PLAN.md#wording-that-still-differs-e-d4)),
and 9 adds one there as a stated difference (`Refusals.holds_scope_breaches`). Fixing 8 let J13.3 run
on and find 11, decided the same day. Checks, the touched cases only: the journey tests of J02, J03,
J10, J11, J12, J13 and J16 and `test_startup` pass; `test_rule_parity` passes with the settled rows
re-pinned. Every line of the deviations list has the user's decision, which closes H4c. Not tested by a case: empty text shared by two records in a change set, and the
current version on a stale write in a change set (one line each, like their live paths).

##### Deviations between API.md and the code

Every place where the code and API.md disagree, or API.md is silent on what the code does, found by
the journey tests (a case written from the documents that fails on the code) or while writing them.
Each line: what API.md says, what the code does, the decision.

| # | Journey | API.md | The code | Decision |
| --- | --- | --- | --- | --- |
| 1 | J02.2 | A stale record write is `409 version_conflict`; no details described (a stale *workspace* update carries `details.currentVersion`). The catalogue says the second writer gets the current content | No `details` | Decided 2026-10-03 (user): keep the fix; API.md updated. Done: every stale record or relation write carries `details.currentVersion` |
| 2 | J16 | An unknown view is `404 relation_matrix_view_not_found`; an unknown application is not described | An unknown `applicationKey` answers `relation_matrix_view_not_found`; other routes say `unknown_application` | Decided 2026-10-03 (user): `404 unknown_application`, as other routes. Done |
| 3 | all | 32 codes the backend raises are not documented (D-4) | Raised | Document them in API.md (user, D-4). Done 2026-10-03 |
| 4 | J05.4 | The validation response is not described | `200` with `valid` and `diagnostics` | Documented as it is (user, 2026-10-02) |
| 5 | J24.5 | What an expired job's items read answers is not described | `200`, an empty page | Documented as it is (user, 2026-10-02) |
| 6 | J02.5 | A uniqueness breach is `409 duplicate_attribute_value`; details not described | Live: message names the attribute's display name, no `details`. In a change set: `details` with `attributeTypeKey` and `conflictingObjectId` | Decided 2026-10-03 (user): alike. Done: the name in the message, `attributeTypeKey` and `conflictingObjectId` in `details` in both; empty text is no value in both, validation included (two E-D4 rows settled) |
| 7 | J03.4 | Not described; the inventory lists `422 duplicate_initial_relation` | Live: `409 duplicate_relation`. In a change set: `422 duplicate_initial_relation` | Decided 2026-10-03 (user): alike. Done: `422 duplicate_initial_relation` live too (an E-D4 row settled) |
| 8 | J13.3 | Not described for a write; the catalogue lists `422 unknown_relation_type` | Live: `404 unknown_relation_type`. In a change set: `422` | Decided 2026-10-03 (user): alike. Done: `422` live too (an E-D4 row settled) |
| 9 | J16.3 | A scope breach staged in a change set shows as a `several` cell with `conflict`, is reported by validation and refused at publishing ("a change set can hold until validation") | A staged create that breaches the scope is refused at once, `409 duplicate_relation_scope` | Decided 2026-10-03 (user): follow API.md. Done: a change set holds a direct breach too (relation create, initial relations, edit, move, set replacement); validation reports it, publishing refuses it; API.md's relation section corrected |
| 10 | J12.8 | Not described. The catalogue says requests and the job worker "report it concisely and recover"; the case also expects `/health` to report not ready while the database is unreachable | Requests answer `500 internal_error` with a correlation ID and no traceback, and recover without a restart; `/health` answers `200` throughout (it reports the model registry, not the database) | Decided 2026-10-03 (user): `/health` reports it. Done: `/health` asks the database and answers `503` while it is unreachable |
| 11 | J13.3 | Not described for a write; the inventory lists `422 relation_endpoint_missing` under the write rules. Found once deviation 8 was fixed (the test stopped before it) | Live: `404 object_not_found`. In a change set: `422 relation_endpoint_missing` (an E-D4 row) | Decided 2026-10-03 (user): the more descriptive answer. Done: `422 relation_endpoint_missing` naming the record, live and in a change set (an E-D4 row settled) |

#### H4d: The unit layer and the move

**Postponed after H4d-1 (user's decision, 2026-10-03).** H4d-1 took about a third of a five-hour
working window for 4 of about 80 modules; the 13 slices left and H4e were estimated at about a week of
the available capacity with no feature delivered, against a suite that passes. The older modules stay
in place, the groups keep selecting them, and an older test is replaced only when a feature package's
change makes it wrong or in the way ([AGENTS.md, Testing](../AGENTS.md#testing)). The slice plan
below is kept for when H4d continues.

**Scope:** every existing test is classified once, with its traced specification statement or
purpose, and:

- **kept as a journey test** when it walks a journey step (merged into that journey's test);
- **moved down** when it checks a piece of code's edge cases: a unit test on the engine module, with
  no application start; a grid of options becomes a property-based or pairwise test;
- **removed** when it traces to no specification statement or purpose, or a journey or unit test
  already covers it. The record names, for each removed check, the test that covers it.

Known from the audit: renamed-model copies kept only where keys drive the code (rule parity, type
changes, restructuring, query, lookup, placements; `test_model_independence` stays as the static
guard); refusals already pinned by rule parity; model rules already pinned by the diagnostics
table; mapping's one-step tests, `test_list_mappings_*` and option grids; the modules named after
work packages dissolved; fabricated states rebuilt through the API, or removed, unless the state
arrives from outside the API (an import, an older release), which the test says; spies on private
functions removed; status-only assertions given their error codes. The slow tests made smaller:
change-set position reads sampled at the edges and around the moved rows, the model query's
criteria checked in full in live data and by a representative set per other context, the matrix
recheck once per module except in the modules that test matrix maintenance, and one application
start per module where startup is not under test. Found in H4b: seven modules (`test_api`,
`test_attributes`, `test_relations`, `test_translations`, `test_cascade_delete`,
`test_query_foundations`, `test_typed_table_queries`) replace the test client with
`ChangeSetTestClient`, which sends every record and relationship call through a change set, so at
least 75 tests named as live operations never reach live code; their live checks are rebuilt or
traced to the tests that do reach it.

**Delivered in very small slices (user's decision, 2026-10-02):** one area at a time, each slice
small enough to review on its own. **Checked by breaking the code:** before an area's old tests are
removed, a handful of faults are planted on purpose in the area's critical rules (a uniqueness
check, a cascade, a version claim, a cardinality limit, …); the tests that remain must fail on each,
and the slice's record lists every planted fault and the test that caught it.

**Exit:** no test outside `tests/journeys/` and `tests/unit/`; the removal list complete; every
area's planted faults caught by the tests that remain, which shows that nothing the old tests
detected was lost.

**How a test is classified** (2026-10-03, from the scope above):

- A check a journey test already makes is **removed**, naming that journey test. A journey step or
  refusal the journey test does not make yet is **merged** into it, marked "merged in H4d".
- A check of one module's purpose or edge case is **moved** to `tests/unit/` as a test of that
  module. A module that writes or queries runs on a clone of a journey configuration's `scenario`
  seed with no application started (`tests/unit/conftest.py`, fixture `seeded`; generated A only,
  since no key drives the code a unit test reaches); the rest need no database.
- A state no client can produce is rebuilt through the API or removed; a fault injected at a module
  boundary (a concurrent writer the lock does not cover, a defect) stays where the behaviour under it
  is the module's purpose, and the test says so.
- Until H4e removes the groups, a moved unit test and a journey test carry the groups of what they
  test (`UNIT_GROUPS` by folder, `JOURNEY_GROUPS` by journey in `conftest.py`), so `-m <group>` still
  selects them.

**Slices (2026-10-03).** One area each, in this order; a module whose tests span two areas is split
between them. Budgets, forced races and the static guards each form their own slice, so one
decision is applied to all of their kind at once.

| Slice | Area | Modules |
| --- | --- | --- |
| H4d-1 | Jobs and batches | `test_batches`, `test_background_jobs`, `test_job_settings`, `test_batch_matrix_states`, `test_pg3b_batch_writes` (its bulk-write fallback) |
| H4d-2 | The model | `test_model`, `test_model_diagnostics`, `test_model_placements`, `test_consumer_api_model`, `test_model_compatibility` |
| H4d-3 | Model administration | `test_model_lifecycle`, `test_build07_wp6`, `test_build07_wp11`, `test_build07_wp9_acceptance`, `test_model_schema_upgrade` |
| H4d-4 | Startup and the database | `test_startup`, `test_schema_drift`, `test_foreign_keys`, `test_encoding`, `test_request_scope` |
| H4d-5 | Live records | `test_api`, `test_attributes`, `test_relations`, `test_translations`, `test_cascade_delete`, `test_wp7_canonical_crud`, `test_rule_parity`, `test_relation_set_versions` |
| H4d-6 | Reads and queries | `test_pagination`, `test_typed_table_queries`, `test_query_foundations`, `test_search_index`, `test_cross_type_lookup`, `test_model_query`, `test_effective_periods`, `test_context_read_parity`, `test_workspace_edge_list` |
| H4d-7 | Workspaces | `test_workspaces`, `test_w6_workspace_deletion`, `test_wp81a_context`, `test_wp8_withdrawal` |
| H4d-8 | Change sets | `test_change_sets`, `test_wp8_change_set_lifecycle`, `test_wp8_graph_validation`, `test_wp8_publish`, `test_wp8_publish_merge`, `test_wp81b_current_live_bases`, `test_wp8_history`, `test_wp8_review_regressions`, `test_change_set_write_lookups`, `test_change_lists` |
| H4d-9 | Replacing related records | `test_mapping_coverage`, `test_mapping_replacement` |
| H4d-10 | The relation matrix | `test_relation_matrix`, `test_relation_matrix_writes`, `test_matrix_states` |
| H4d-11 | Restructuring | `test_parent_candidates`, `test_type_changes`, `test_restructuring_planner`, `test_restructuring_api` |
| H4d-12 | Forced races | `test_pg3_concurrency`, `test_w5_activation_write_race`, `test_pg3b_batch_writes` (the rest) |
| H4d-13 | Budgets | `test_volume_baseline`, `test_paging_contract`, `test_change_set_position_reads`, `test_change_lists_volume`, `test_relation_matrix_volume`, `test_restructuring_volume`, `test_graph_validation_scale`, `test_batch_statements`, `test_batch_volume`, `test_background_volume` |
| H4d-14 | Static guards | `test_openapi_contract`, `test_boundaries`, `test_api_journeys`, `test_api_reference`, `test_model_independence` |

##### H4d-1: Jobs and batches

**Delivered 2026-10-03.** 73 old cases (40 test functions, most on two models) became 31 unit
test functions in ten modules (62 cases, most of them rows of a grid; about 10 s in parallel) plus
four checks merged into J11 and J12.

**New unit tests:** `tests/unit/engine/jobs/test_batches.py` (`batches.py`), `test_inline.py`,
`test_store.py`, `test_worker.py`, `test_background.py`; `tests/unit/engine/records/test_audit.py`;
`tests/unit/models/test_commands.py`, `tests/unit/models/test_database.py`;
`tests/unit/test_config.py`, `tests/unit/test_main.py`. The generated configurations gained one
binding: `R2` may hold `R.u`, a unique value two types share, the only shape in which a reference by
a unique value finds a record of another type (`reference_type_mismatch` on a key). No journey test
changed its expectation.

**Merged into journeys:** J11.5 refuses an empty or a 201-character `Idempotency-Key`
(`request_validation_error`; its helper now sends an empty key instead of none); J12.7's
small-limits case sets and reads all seven job limits; J12.7's jobs-off case finds no cancel route
and still reads jobs.

**Classification** (old test → what covers each of its checks now):

| Old test | Outcome | Covered by |
| --- | --- | --- |
| `test_batches::test_each_item_op_is_refused_with_its_single_writes_code` | removed; one check moved | `test_rule_parity::test_batch_items_refuse_as_their_single_writes` (every create and update refusal as a one-item batch, both contexts; keep it in H4d-5); the delete with dependants and its absent preview token: unit `test_batches::test_a_delete_item_with_dependants_is_refused_without_a_preview_token` |
| `test_batches::test_items_apply_like_their_single_writes` | removed; checks moved | J11 (create, child by key, update, delete, the job as the history entry's cause), J11.3 (one claim, live untouched); unit `test_batches` (an update whose target is named by key; an atomic batch in a change set), `test_worker` (counts, parameters), `test_audit` (a single write records no cause) |
| `test_batches::test_independent_items_stand_alone_and_see_earlier_applied_items` | moved | unit `test_batches::test_items_see_the_items_before_them_and_a_refused_item_writes_nothing` |
| `test_batches::test_an_atomic_batch_applies_everything_or_nothing` | removed (live), moved (change set) | J11.1; unit `test_batches::test_an_atomic_batch_in_a_change_set_applies_everything_or_nothing` (no audit entry, no staged row, version kept) |
| `test_batches::test_upserts_need_a_version_claim_or_a_declared_overwrite` | removed; checks moved | J11.2 (created, `version_required`, updated, overwrite with `previousVersion`, unchanged writes nothing); unit `test_batches::test_a_claim_beside_equal_values_and_an_overwrite_on_record` (stale claim at `expectedVersion`, equal values with a stale claim, an equal update item, the overwrite in the audit entry) |
| `test_batches::test_an_upsert_by_id_creates_with_that_id_and_never_changes_a_type` | removed | J11.2 (created under the ID, another type's ID refused) |
| `test_batches::test_upsert_initial_relations_apply_only_when_it_creates` | moved | unit `test_batches::test_an_upserts_initial_relations_apply_only_when_it_creates` |
| `test_batches::test_references_resolve_by_unique_key_and_are_refused_at_their_pointer` | moved | unit `test_batches::test_references_name_a_record_by_a_unique_value_and_refusals_point_at_them`, `…::test_a_reference_finding_a_record_of_another_type_is_refused` |
| `test_batches::test_request_level_refusals_create_no_job` | removed; checks moved or merged | J11 (item limit, no job), J11.3 (context refusals, no job); unit `test_inline` (every limit of each run), `test_batches::test_a_request_names_live_data_or_one_change_set_with_its_claim` (all eight combinations), `…::test_a_batch_writes_only_in_an_active_workspace`, `test_commands` (malformed requests); J12.7 small limits (merged: all seven limits) |
| `test_batches::test_with_jobs_disabled_no_route_creates_one_and_reads_remain` | removed | J12.7 jobs-off (merged: reads remain) |
| `test_batches::test_an_idempotency_key_replays_the_finished_job` | removed; checks moved or merged | J11 (replay with the header), J11.5 (reused, in progress with `Retry-After`; merged: malformed keys), J24.5 (expired key counts as new); unit `test_store` (`jobId` in details, every state of the job, another workspace), `test_inline` (a change set's key belongs to its workspace) |
| `test_batches::test_jobs_and_their_outcomes_page_in_order` | removed; checks moved | J24 (outcomes by status with a cursor, the job among completed batches); unit `test_store::test_jobs_list_newest_first_and_outcomes_in_item_order`, `test_batches` (an outcome's fields by status). Not kept: the job's `modelReleaseId` equals the model's release header, a presenter's copy of a stored ID |
| `test_batches::test_refs_are_echoed` | moved | unit `test_batches` (a ref on the outcome), `test_commands` (an empty ref) |
| `test_batches::test_a_model_release_change_before_commit_saves_nothing` | removed (it set a private session key) | J11.4 (a real activation while the batch waits for the workspace) |
| `test_background_jobs::test_a_background_batch_is_queued_and_applied_in_chunks` | removed; checks moved | J24 (queued, progress by chunk, outcomes as they commit, completed); unit `test_worker` (no inputs and no lease once finished), `test_store` (inputs with their refs) |
| `test_background_jobs::test_items_in_a_later_chunk_see_earlier_chunks_and_keep_their_semantics` | moved | unit `test_store::test_inputs_are_read_back_as_they_were_sent`, `test_batches::test_an_item_that_leaves_out_its_parent_keeps_the_record_where_it_stands` |
| `test_background_jobs::test_a_background_batch_in_a_change_set_holds_its_claim_between_chunks` | moved | unit `test_worker::test_a_job_in_a_change_set_follows_the_version_each_chunk_leaves`, `test_background::test_a_job_queued_with_a_stale_change_set_version_is_refused` |
| `test_background_jobs::test_an_atomic_background_job_is_one_chunk` | moved | unit `test_worker::test_an_atomic_job_runs_as_one_chunk_and_a_rejection_rolls_it_back` |
| `test_background_jobs::test_a_job_resumes_after_a_crash_without_repeating_or_skipping_an_item` (2 cases) | removed (it raised inside a private method) | J24 (a process gone after two chunks), J24.3 (a chunk that never commits) |
| `test_background_jobs::test_a_worker_that_lost_its_lease_commits_nothing` | removed (it wrote another owner into the row) | J24.3 (a real takeover after the lease expired) |
| `test_background_jobs::test_a_stopping_worker_releases_its_leases` | moved | unit `test_worker::test_a_stopping_worker_releases_its_leases_and_a_finished_job_leaves_no_inputs` |
| `test_background_jobs::test_cancelling_a_queued_job_runs_none_of_its_items`, `…_between_chunks_keeps_the_applied_chunks`, `…_an_atomic_job_rolls_it_back_completely` | removed | J24.2 (queued, between chunks, atomic, twice, finished with `details.state`, unknown); unit `test_worker` (an unprocessed item keeps its ref) |
| `test_background_jobs::test_a_release_activated_mid_job_fails_it_at_the_next_chunk` | removed | J24.4 |
| `test_background_jobs::test_a_release_activated_during_a_chunk_refuses_that_chunk` | removed (it set a private session key) | `test_pg3b_batch_writes::test_an_activation_dropping_a_matrix_shape_beside_a_chunk_does_not_deadlock` (a real activation during a chunk; H4d-12) |
| `test_background_jobs::test_a_change_set_moved_to_another_release_fails_the_job` | removed (a state no client produces) | Changing a change set's release claims its version, so a client meets J24.4's `change_set_version_conflict` |
| `test_background_jobs::test_a_lost_change_set_claim_fails_the_job`, `…_a_workspace_retired_mid_job_fails_it` | removed | J24.4 |
| `test_background_jobs::test_an_unexpected_error_fails_the_job_with_a_correlation_id` | moved | unit `test_worker::test_an_unexpected_error_fails_the_job_with_a_correlation_id` (the batch's code made to raise at the worker's call) |
| `test_background_jobs::test_an_idempotency_key_answers_with_the_background_job` | removed; checks moved | J11.5 (in progress, reused); unit `test_store` (a finished job answers, the key lives as long as the job) |
| `test_background_jobs::test_retention_expires_finished_jobs_and_keeps_their_summary` | removed; checks moved | J24.5; unit `test_store::test_retention_expires_finished_jobs_only` |
| `test_background_jobs::test_with_jobs_disabled_there_is_no_worker_and_no_cancel_route` | removed; checks moved or merged | J12.7 jobs-off (merged: no cancel route); unit `test_main` (no worker) |
| `test_background_jobs::test_the_application_runs_background_jobs_on_its_worker_thread` (serial) | removed | J12.8 (the service's own worker runs a job after the outage) |
| `test_background_jobs::test_background_attributes_keep_their_declared_types` | moved | unit `test_store::test_inputs_are_read_back_as_they_were_sent` |
| `test_background_jobs::test_a_worker_without_its_database_waits_between_retries_and_logs_one_traceback` | moved (serial) | unit `test_worker::test_without_its_database_the_worker_waits_between_retries_and_logs_one_traceback`; J24.6 has the real outage but cannot see a retry loop that does not wait |
| `test_job_settings::test_batch_settings_have_defaults_and_refuse_invalid_values` | moved | unit `test_config` |
| `test_job_settings::test_a_live_unique_value_check_seeks_to_the_value` | moved | unit `models/test_database` |
| `test_batch_matrix_states::test_batches_keep_stored_matrix_states_derived` | moved | unit `test_batches::test_batches_keep_the_stored_matrix_states_derived` (on the generated model's relationship coverage instead of the starter's translations) |
| `test_pg3b_batch_writes::test_a_bulk_write_that_fails_is_redone_item_by_item` | moved | unit `test_batches::test_a_bulk_write_that_fails_is_redone_item_by_item` |

**Planted faults** (each planted alone, then the area's remaining tests run: `tests/unit/engine/jobs`,
`tests/unit/engine/records/test_audit.py`, the J11 and J24 journey tests; every one caught, and the
code restored):

| Fault | Caught by |
| --- | --- |
| F1 an atomic batch keeps its items after a rejection | J11.1; unit `test_batches` (change set), `test_worker` (atomic job) |
| F2 a key's request fingerprint is ignored | J11.5; unit `test_store`, `test_inline` |
| F3 a worker that lost its lease commits | J24.3 |
| F4 equal values are never `unchanged` | J11.2, J11.3; unit `test_batches` (two) |
| F5 a key reference's type is not checked | unit `test_batches::test_a_reference_finding_a_record_of_another_type_is_refused` |
| F6 retention expires a queued job | unit `test_store::test_retention_expires_finished_jobs_only` |
| F7 the byte limit is not enforced | unit `test_inline` |
| F8 a failed bulk write is not redone item by item | unit `test_batches::test_a_bulk_write_that_fails_is_redone_item_by_item` |
| F9 a cancel requested before the first chunk is ignored | J24.2 |
| F10 a resumed job repeats its last item | J24, J24.1, J24.3, J24.6; unit `test_store`, `test_worker` (two) |
| F11 a job keeps the change set version it started with | unit `test_worker::test_a_job_in_a_change_set_follows_the_version_each_chunk_leaves` |
| F12 a delete item's refusal keeps its preview token | unit `test_batches::test_a_delete_item_with_dependants_is_refused_without_a_preview_token` |
| F13 the job is not recorded as its entries' cause | J11; unit `test_audit` |
| F14 an atomic background job runs in chunks | unit `test_worker::test_an_atomic_job_runs_as_one_chunk_and_a_rejection_rolls_it_back` |

**Checks (2026-10-03):** the journey suite, the unit layer, `test_pg3b_batch_writes` and the
inventory check, since the generated configurations changed (every journey test reads them):
421 passed in 1 min 4 s (`-n auto`), and the serial part (the worker's retry wait) 1 passed;
`-m jobs` collects the moved unit tests and J11/J24 (116 cases); `ruff check app/ tests/`. Each
planted-fault run took about 18 s (F10, whose jobs time out, 95 s). Not run: the other old modules
(unchanged), the frontend and browser runners (nothing there changed). The fault script and its
output were scratch files, deleted.

#### H4e: Rules and acceptance

**Postponed with H4d (2026-10-03).** The rules part was done then instead, in proportion: AGENTS.md
and STRATEGY now say how much testing a package does, a package selects its checks with testmon and
its journeys, and the groups remain the fallback.

**Scope:** AGENTS.md's testing sections, EXECUTION_GUIDE and COVERAGE_MAP rewritten to the strategy
(the coverage map becomes the catalogue plus the trace report); the old group selection removed
where testmon and the journey markers replace it. The full backend suite run once, announced with
its expected time.

**Exit (H4's targets):**

- at most 550 backend cases, the full suite at most 1 min 30 s wall time, and a typical package's
  selected run under 1 minute;
- every test is a journey test with its marker or a unit test under `tests/unit/`;
- every engine module is reached by a journey, or listed with a decision;
- every area's planted faults caught (H4d's records).

**Evidence (each slice):** counts and times before and after, the selected run's command and
result, what was not run and why, and every server, clone and log the slice started stopped or
deleted.

## Targets

Measured before H1 and after each package, on the same machine:

- a second run of any group seeds nothing (H1);
- the full backend suite without full-size budgets at least **4× faster** in wall time (after H2;
  not met at H3: 2.7×, 2 min 41 s against about 436 s, within the 5-minute ceiling);
- no package's local checks wait for a full-size budget, and they stay within 2 minutes (H3, H4);
- H4's targets: at most 550 backend cases, the full suite within 1 min 30 s, a typical package's
  selected run under 1 minute;
- every removed check names the test that still covers it, and every area's planted faults are
  caught by the tests that remain (H4). Until 2026-10-02 this read "no test removed or weakened"; the audit showed that many tests
  were written from the code and covered nothing a journey or unit test does not.

## Not changed

The renamed-model copies stay where model keys drive the code (rule parity, type changes,
restructuring, query, lookup, placements): they prove no code depends on a model key, a product
invariant. Revised 2026-10-02: in modules where keys never drive the code (consumer model compile,
job mechanics, batches; 75 cases), the copies go in H4d, and `test_model_independence` remains the
static guard. The per-commit cost of
matrix maintenance is a product question, recorded in TODO for its own assessment.
