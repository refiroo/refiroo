# PostgreSQL runtime: interim release 0.9.0-alpha.1

**Status:** Planned 2026-10-01. Decisions [PG-D1–PG-D10](#decisions) accepted 2026-10-01. The same
day the user chose **PostgreSQL only** over a mixed setup with SQLite for development, so PG-D2,
D3, D4, D6, D7 and D8 were revised to that and PG-D10 added; each keeps its accepted intent.
Inserted in the [0.9 delivery queue](BASE_0_9_IMPLEMENTATION_PLAN.md#delivery-queue) after B2,
before F1, together with the [test harness](TEST_HARNESS_PLAN.md): PG1 builds the harness's seeded
databases (H1) on PostgreSQL, and H2–H3 follow PG2. Packages are delivered one per instruction
("deliver PG1"), each by the 0.9 plan's
[delivery steps](BASE_0_9_IMPLEMENTATION_PLAN.md#how-a-package-is-delivered).

**Before PG1:** install the PostgreSQL 17 binaries with `brew install postgresql@17`, and never
start it with `brew services` (PG-D8). Not installed on 2026-10-01.

## Why now

- **F1 cannot be shown on SQLite.** Its feed position relies on commit order under a per-workspace
  row lock (D5). SQLite has one writer for the whole database, so F1's tests would pass without
  proving anything.
- **B2 is waiting on it.** A cancel request committing while a chunk runs (D28), the lease with two
  workers, and live writes beside a background job (refused after `SQLITE_LOCK_WAIT_SECONDS` on
  SQLite) can only be confirmed on PostgreSQL.
- **SQLite debt is growing.** `SQLITE_LOCK_WAIT_SECONDS` (B1), `db.begin_transaction` (B2),
  `BEGIN IMMEDIATE` in three places, a `json_each` row list, an `INDEXED BY` hint, FTS5 search
  tables, nine migrations with SQLite-only DDL, and budgets measured on SQLite only.
- **Nothing runs on PostgreSQL today.** `docker-compose.yml` declares `postgres:17` with `psycopg`,
  and a few code paths have a PostgreSQL branch (relation-set upsert, cascade deletion, release
  compatibility), but no test runs them and the migration history has never been applied to it.
- **It is planned anyway.** PostgreSQL deployment is in
  [0.11](ROADMAP.md#product-release-011--production-hardening-and-staged-model-rollout). This
  release brings forward the runtime only. Multi-node, metrics, backup rehearsal and
  production-scale performance stay in 0.11.

## Why PostgreSQL only

A mixed setup (SQLite for development and most tests, PostgreSQL in CI and for concurrency tests)
was planned first, to spare tests a database server. With seeded databases built once and reused
(H1) and parallel runs (H2), that saving is small: a native server on a local socket adds tens of
microseconds per statement, and a template clone per test tens of milliseconds, against the minutes
H1 and H2 remove. The mixed setup would have cost, for good, a second database to keep in step
(every migration on both, a list of differences, a `postgres` marker decided per test), drift found
only at checkpoints since the repository has no CI remote, and a development app that behaves
unlike production. With one database, every test run proves what the product promises. The
estimates are confirmed by measurement in PG1.

## Product outcome

The engine runs on PostgreSQL only, with real row-level concurrency. Writes in different workspaces
run in parallel, and writes in one workspace serialize without losing an invariant. A background job
leaves other writes free, and a cancel request never waits for a chunk. Tests run on PostgreSQL from
seeded databases built once. Existing development databases carry over. API, model contract and UI
are unchanged.

## Principles

1. **One database.** PostgreSQL is the only runtime and test database. No dialect branch stays in
   `app/` (a `test_boundaries` check), and no test proves behaviour on a database the product does
   not run on.
2. **No server left running.** PostgreSQL runs from the installed binaries only while something
   needs it: the test harness starts and stops its own server, and the development app has a start
   and stop script. Nothing starts at login.
3. **No added waiting.** A test run never seeds what an earlier run seeded from the same schema,
   model and seed code (H1). A package's local checks must not take longer than on SQLite with the
   harness; PG1 measures it.
4. **No contract change.** The OpenAPI lock must not move. A difference PostgreSQL exposes (an
   enforced foreign key, an ordering SQLite happened to give) is fixed to the documented contract,
   never documented as new behaviour.
5. **Concurrency is proven, not assumed.** Every invariant a write checks in code gets a test with
   two real connections racing (PG3).

## Decisions

Accepted 2026-10-01; D2, D3, D4, D6, D7 and D8 revised the same day to PostgreSQL only, and D10
added.

| # | Question | Decision |
| --- | --- | --- |
| PG-D1 | Release version | **0.9.0-alpha.1**, tagged `v0.9.0-alpha.1`. `main` already carries delivered 0.9 packages (Q1–Q4, C1, V1, B1, B2) and the starter is content release 0.9.0 on schema 0.8, so a 0.8.x patch would claim to be 0.8 plus fixes, which it is not. A SemVer pre-release of 0.9 orders before 0.9.0, does not use up 0.9.0, and says what it is. The CHANGELOG gets a `[0.9.0-alpha.1]` section, and the 0.9.0 notes later cover everything since 0.8.0 |
| PG-D2 | The database | **PostgreSQL only**, for the runtime, the tests and the browser runners. SQLite is removed with its settings, dialect branches and migrations (revised from "PostgreSQL for the product, SQLite for development") |
| PG-D3 | The migration history | **One PostgreSQL baseline revision** at today's head schema (`20261001_01`). The 25 SQLite-shaped revisions, their interrupted-run recovery and their tests are removed (allowed before 1.0; no PostgreSQL database exists). Revisions after it are written and tested on PostgreSQL. Existing SQLite data carries over by PG-D10 |
| PG-D4 | Foreign keys | **Enforced, and every `ondelete` rule checked** (accepted as important). PostgreSQL enforces them; PG2 checks each rule against what its service expects, so a delete the services order explicitly (to write their audit entries) still works, and nothing relied on SQLite ignoring them. Closes the TODO item from 0.8 W6 |
| PG-D5 | Invariants that relied on SQLite's single writer | **The per-workspace write lock, taken now.** The live write unit (`LiveWrites`) opens with `SELECT … FROM workspaces WHERE key = … FOR UPDATE`, the lock F1 needs anyway (D5, lock order: workspace, then records). Writes in one workspace serialize, so the per-workspace checks (unique values, parent cycles, cardinality, required relations, sibling rules, relation sets, matrix states) stay sound, while workspaces run in parallel. Change set writes already serialize on their version claim, and publish locks the workspace first. F1 then adds only the feed counter. Per-invariant database constraints wait for evidence (0.11) |
| PG-D6 | Isolation and locks | READ COMMITTED for writes, as D28 assumes; multi-statement reads keep `begin_snapshot_read` (REPEATABLE READ). `BEGIN IMMEDIATE` becomes the row lock each place needs: the runtime-state row for activation, the change set row for lifecycle, the workspace row for the catalogue. `db.begin_transaction` and `SQLITE_LOCK_WAIT_SECONDS` are removed |
| PG-D7 | Search index | **`pg_trgm` GIN indexes** replace the FTS5 tables, with the same contract (S8: the index decides speed, never which records match). The baseline runs `CREATE EXTENSION IF NOT EXISTS pg_trgm`; a role that may not create it is refused at startup with that instruction |
| PG-D8 | Running PostgreSQL | **Homebrew's `postgresql@17` binaries, never `brew services`.** The test harness starts a private server on a data directory under `backend/.test-postgres/` (git-ignored) on a local socket, with durability off since its data is disposable, and stops it when the run ends; the seeded databases (H1) live there as template databases between runs, and each test gets a clone. `scripts/postgres.sh start|stop|backup` runs the development server on its own data directory, for the app and the browser runners. CI (once the repository has a remote) uses a `postgres:17` service. The Docker compose file stays for a containerised deployment |
| PG-D9 | Driver and connections | `psycopg` 3 (already a dependency), synchronous, SQLAlchemy's pool with `pool_pre_ping`. `WEB_CONCURRENCY` stays 1: several processes need 0.11's cross-process release propagation, not a database change |
| PG-D10 | Existing SQLite databases | **A one-off copy command** (`python -m app.tools.copy_from_sqlite <sqlite-url>`) copies a SQLite database at `20261001_01` into an empty PostgreSQL database at the baseline, table by table in dependency order. It keeps public IDs, sequence values, typed values and history, rebuilds the derived indexes (matrix states, search), checks the row counts, and refuses a source at another revision or a target that is not empty, each with an instruction. It is removed again in 0.11. On 2026-10-01 `backend/rdm-engine.db` and `rdm-engine.db` were at `20260928_01` and are upgraded first with the current code; `backend/rdm-operators-timetables.db` is at `20261001_01`. Backups first, and only with the user's go-ahead |

## Inventory

What this release changes, found by a code search on 2026-10-01.

| Area | SQLite form today | PostgreSQL form |
| --- | --- | --- |
| Settings | `DEFAULT_DATABASE_URL` a SQLite file; `SQLITE_LOCK_WAIT_SECONDS` | `DATABASE_URL` required (the development server's URL in `.env.example`); the setting removed |
| `db.py` | a per-URL engine with a SQLite timeout; `begin_snapshot_read` and `begin_transaction` begin explicitly on SQLite | one pooled engine; `begin_transaction` removed |
| Write locks | `BEGIN IMMEDIATE` in `model/releases.py`, `change_sets/lifecycle.py`, `workspaces/catalogue.py`; SQL-level claims written because SQLite ignores `FOR UPDATE` | row locks (PG-D6); the workspace lock in `LiveWrites` (PG-D5); claims kept where they are also the version bump |
| Search | FTS5 trigram tables (`models/search_index.py`, `20260926_03`) | `pg_trgm` GIN (PG-D7) |
| Relation matrix | `json_each` row list and an `INDEXED BY` hint (`indexes/matrix_states.py`); the change set walk with two recursive arms | `= ANY(:ids)` and no hint; the walk as one recursive term (TODO, 0.8 A2/A3b) |
| Partial index | `sqlite_where` on a `models/database.py` index | `postgresql_where` |
| Upsert | `sqlite_insert` / `pg_insert` branch (`relation_set_versions.py`) | `pg_insert` only |
| Foreign keys | not enforced | enforced; every `ondelete` rule checked (PG-D4) |
| Migrations | 25 revisions, 9 with SQLite-only DDL | one baseline (PG-D3) |
| Tests | a migrated template file copied per test; 21 modules open SQLite files directly, mostly migration tests | the harness's private server, seeded template databases cloned per test (PG-D8, H1); SQLite migration tests removed with their revisions |
| Browser runners | `database.sqlite` per run (`e2e/helpers/harness.mjs` and three runners) | a database per run on the development server, cloned from the runner's seed |
| CI | pytest on SQLite (never runs: no remote) | pytest with a `postgres:17` service |

## Packages

Each package keeps the API, the model contract and the OpenAPI lock unchanged.

### PG1: Runtime, baseline and test harness

**Scope:** `DATABASE_URL` required and PostgreSQL only; `db.py` with one pooled engine; the baseline
migration (PG-D3) from the ORM metadata plus `pg_trgm`; the startup checks refusing a non-PostgreSQL
URL, a missing extension and an unknown revision, each with an operator instruction;
`scripts/postgres.sh`; `.env.example` and README. The test harness on PostgreSQL (PG-D8) with the
seed store of [H1](TEST_HARNESS_PLAN.md#h1-seeded-databases-built-once): the private server, seeds
as template databases with their fingerprints, one clone per test. The SQLite revisions and their
migration tests removed. First, a measurement on the seeded harness: `records` and the volume reads
against the SQLite numbers recorded in TEST_HARNESS_PLAN, recorded in the package.

**Tests:** clean bootstrap, restart, an unknown revision refused, a missing `pg_trgm` refused, the
lifespan against a real database, schema drift (ORM against migration), and H1's evidence (a second
run seeds nothing). **Groups:** `startup`, `contract`.

**Exit:** the application starts on PostgreSQL, `startup` and `contract` pass on it, and seeds are
reused across runs. Other groups may fail until PG2.

### PG2: PostgreSQL forms

**Scope:** every row of the [inventory](#inventory) not done in PG1, except the workspace lock:
search on `pg_trgm`, the matrix forms, the partial index, the upsert, row locks for activation,
change set lifecycle and the catalogue, `begin_transaction` and `SQLITE_LOCK_WAIT_SECONDS` removed,
every `ondelete` rule checked (PG-D4). The browser runner harness on the development server. No
dialect name remains in `app/` (`test_boundaries`).

**Tests:** every backend group except `volume` passes. A failure is fixed to the documented contract
(principle 4) and recorded.

**Exit:** `ruff`, and all groups except `volume`, green on PostgreSQL. H2 and H3 of the test harness
can then follow.

### PG3: Concurrency

**Scope:** the per-workspace write lock in `LiveWrites` (PG-D5), with the lock order written into
ARCHITECTURE (workspace, then change set, then records; a job's chunk takes the job row only at its
checkpoint). Every invariant a write checks in code is tested with two connections racing.

**Tests:** two writers racing on one workspace for the same unique value, a parent cycle, a
cardinality limit, a required relation, a relation-set version and the stored matrix state: one
succeeds, one is refused with its single write's code, and `matrix_states.verify` is clean. Two
workspaces written in parallel, measured as not serialized. The W5 activation race on row locks.
For B2: a cancel request answered while a chunk runs, and the atomic job rolled back between items
(D28); two workers sharing one job through the lease; live writes beside a background job not
waiting for it, with the latency bound B2 left open. **Groups:** `records`, `change_sets`,
`mapping`, `matrix`, `jobs`, `model_admin`, `workspaces`.

**Exit:** the concurrency tests pass; the D28 and B2 notes in TODO are closed.

### PG4: Carrying data over

**Scope:** the copy command (PG-D10), its row-count and derived-index checks and its refusals.

**Tests:** a seeded SQLite database (the volume fixture at a small scale, and one with change sets,
publications, jobs and history) is copied. Every API read compared before and after gives the same
answer, matrix states verify, and search finds the same records. **Groups:** `startup`.

**Exit:** the developer's databases are copied and smoke-started, with the user's go-ahead and
backups first.

### PG5: Budgets, acceptance and release

**Scope:** every `volume` budget re-measured on PostgreSQL. Statement-count and time budgets are
restated with each decision record amended (0.8 Track S, A2, D13), and B2's budget gains its latency
bound for writes beside a background job; full-size budgets follow
[H3](TEST_HARNESS_PLAN.md#h3-cheaper-per-test-work-and-budget-sizes). The TODO SQLite debt item is
closed: a search for SQLite and dialect names in `app/`, `tests/` and `frontend/e2e` finds nothing
that is not history. AGENTS.md, ARCHITECTURE, README and EXECUTION_GUIDE describe PostgreSQL only.

**Acceptance (the interim release's build acceptance):** the full backend suite on PostgreSQL;
frontend format, lint, `npm run test` and build; the browser runners against the PostgreSQL backend.
Nothing in the UI changes, so visual and accessibility runs are added only if a runner's journey
shows a difference.

**Release:** version 0.9.0-alpha.1 in `pyproject.toml` and the FastAPI title. The CHANGELOG section
covers everything since 0.8.0. Tag `v0.9.0-alpha.1` on the user's instruction (commit and tag only
when asked).

## Composable domains (ADR-032)

Identity and attribute storage are touched (the baseline, the copy and the indexes) and no door is
affected. Public IDs, typed value columns and the audit cause are copied as they are, and the
workspace lock serializes writes within the uniqueness scope (ADR-010) without changing it.

## What stays in 0.11

Multi-node and multi-process operation (cross-process release propagation, the job worker on
several nodes through its lease, `WEB_CONCURRENCY` above 1). Production-scale performance: the
volume fixture at full scale, connection pool sizing, and model-derived indexes, including unique
checks on non-text values. Precomputed sort keys (D26). Database constraints as a second line
behind the workspace lock (a database lock, so it holds across nodes), for writes that bypass the
write unit, decided on evidence. Metrics, structured logging, readiness, and backup/restore
rehearsal with `pg_dump`. See
[ROADMAP 0.11](ROADMAP.md#product-release-011--production-hardening-and-staged-model-rollout).
