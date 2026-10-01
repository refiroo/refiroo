# Test harness: seeded databases built once, faster runs (H1–H3)

**Status:** Planned 2026-10-01, revised the same day: seeded databases first, and, once PostgreSQL
became the only database ([PG-D2](POSTGRESQL_RUNTIME_PLAN.md#decisions)), built on PostgreSQL.
**H1 is delivered inside [PG1](POSTGRESQL_RUNTIME_PLAN.md#pg1-runtime-baseline-and-test-harness)**,
so the harness is built once, for the database the product runs on. H2 and H3 follow PG2, when the
suite passes on PostgreSQL. Delivered one package per instruction ("deliver H2"). No product
behaviour, contract or model changes.

The measurements below were taken on SQLite (2026-10-01) and are the baseline PG1's measurement
compares against.

## The rule

**A seeded database is built once and reused until what it was built from changes.** No test run
seeds data that an earlier run already seeded from the same schema, model and seed code. A test that
needs its own copy gets a clone of the seeded database (a template database copy), never a new
seed.

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
[PG1's record](POSTGRESQL_RUNTIME_PLAN.md#pg1-runtime-baseline-and-test-harness). The heavy modules'
records and the browser runners' seed follow in PG2.

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
  rebuilt per session), the heavy `records` and `change_sets` modules' common records, and the
  browser runner harness's seed (`e2e/helpers/harness.mjs`), which today creates its records through
  the API on every run.
- **Split with PG2 (decided 2026-10-01 at the start of PG1).** PG1 builds the seed store, the migrated
  schema seed and the volume fixture seeds. The heavy modules' common records and the browser
  runners' seed move onto seeds in [PG2](POSTGRESQL_RUNTIME_PLAN.md#pg2-postgresql-forms), once
  those modules and runners run on PostgreSQL.

**Evidence:** two runs of the same groups back to back, the second building no seed (its log names
each seed as reused), with times for both; a schema change rebuilding exactly the affected seeds;
the changed modules' groups green.

### H2: Parallel runs

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

### H3: Cheaper per-test work and budget sizes

**Scope:**

- `matrix_states.verify` after every test only in the modules that test matrix maintenance
  (`test_matrix_states`, `test_relation_matrix_writes`, `test_batch_matrix_states`); elsewhere once
  per module on its final data, which catches the same drift.
- The application's start in tests shared per module where a test does not test start-up; every
  start-up path stays exercised in the `startup` group.
- Full-size budgets (B1's 10,000-item atomic batch, B2's 100,000-item background batch,
  `volume_baseline.py --scale 1`) carry a `budget` marker and run at checkpoints (T1, R) and at the
  interim release's acceptance. In a package they run at `RDM_BUDGET_SCALE` (default 0.1), so a
  package that changes a write path still sees its cost per item. The plans' "Budget" lines and
  AGENTS.md state which size runs where.

**Evidence:** per-module times before and after for every changed module, the groups green, and one
full-size run confirming the `budget` marker selects what it should.

## Targets

Measured before H1 and after each package, on the same machine:

- a second run of any group seeds nothing (H1);
- the full backend suite without full-size budgets at least **4× faster** in wall time (after H2);
- no package's local checks wait for a full-size budget (H3);
- no test removed or weakened. A check that moves (the matrix recheck, a shared start) is replaced
  by one that catches the same failure, named in the package record.

## Not changed

The renamed-model copies (25 modules run twice) stay: they prove no code depends on a model key, a
product invariant, and with seeds they cost a copy instead of a reseed. The per-commit cost of
matrix maintenance is a product question, recorded in TODO for its own assessment.
