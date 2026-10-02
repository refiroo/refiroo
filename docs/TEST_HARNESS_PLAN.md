# Test harness: seeded databases built once, faster runs, time ceilings (H1–H4)

**Status:** Planned 2026-10-01, revised the same day: seeded databases first, and, once PostgreSQL
became the only database ([PG-D2](POSTGRESQL_RUNTIME_PLAN.md#decisions)), built on PostgreSQL.
**H1 is delivered inside [PG1](POSTGRESQL_RUNTIME_PLAN.md#pg1-runtime-baseline-and-test-harness)**,
so the harness is built once, for the database the product runs on. H2 and H3 follow PG2, when the
suite passes on PostgreSQL. Delivered one package per instruction ("deliver H2"). No product
behaviour, contract or model changes. **H2 is delivered (2026-10-01).** **Revised 2026-10-01 after
H2** (user's direction: development time must go to development, not to waiting for tests): every
run now has a [time ceiling](#time-ceilings), full-size budgets leave every run but the interim
release's acceptance, and H3 is split into H3 (budgets out of everyday runs) and H4 (cheaper
per-test work). **H3 is delivered (2026-10-01).**

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
| A package's checks: its boundary's groups (EXECUTION_GUIDE §2) | end of a package | **2 minutes**, with `-n auto` and the groups' serial part |
| Build acceptance: the full backend suite without `budget` | end of a build | **5 minutes**, parallel part plus serial part |
| Full-size budgets (`-m budget`) | a release's acceptance only, once | announced with its expected time before it starts (about 25 minutes today; PG-D17's target is under a minute per context) |

The rules that hold the ceilings:

- **Announce before running.** A run expected to take more than 2 minutes is named with its expected
  time before it starts, and needs the user's go-ahead in a package. A result already measured is
  not measured again: a run is repeated only after the code it covers changed.
- **Full-size budgets never run by default.** They carry the `budget` marker, which a run selects
  only by naming it (`-m budget`). From PG3b their timed checks are statement counts at two seeded
  sizes (PG-D17), and the 100,000-item batch is a measurement run once at PG5's acceptance.
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

### H4: Cheaper per-test work (next)

Moved from H3 on 2026-10-01. Done when a package's checks stay over the 2-minute ceiling after H3,
which the slow-test report shows.

**Scope:**

- `matrix_states.verify` after every test only in the modules that test matrix maintenance
  (`test_matrix_states`, `test_relation_matrix_writes`, `test_batch_matrix_states`); elsewhere once
  per module on its final data, which catches the same drift.
- The application's start in tests shared per module where a test does not test start-up; every
  start-up path stays exercised in the `startup` group.
- The slowest tests the H3 report names (today `test_model_query`'s every-criterion test, 16 s per
  model under `-n auto`, and `test_matrix_states`' change set test, 12 s): data built once per
  module instead of per case where the case does not write it.

**Evidence:** per-module times before and after for every changed module, and the groups green.

## Targets

Measured before H1 and after each package, on the same machine:

- a second run of any group seeds nothing (H1);
- the full backend suite without full-size budgets at least **4× faster** in wall time (after H2;
  not met at H3: 2.7×, 2 min 41 s against about 436 s, within the 5-minute ceiling);
- no package's local checks wait for a full-size budget, and they stay within 2 minutes (H3, H4);
- no test removed or weakened. A check that moves (the matrix recheck, a shared start) is replaced
  by one that catches the same failure, named in the package record.

## Not changed

The renamed-model copies (25 modules run twice) stay: they prove no code depends on a model key, a
product invariant, and with seeds they cost a copy instead of a reseed. The per-commit cost of
matrix maintenance is a product question, recorded in TODO for its own assessment.
