# PostgreSQL runtime: interim release 0.9.0-alpha.1

**Status:** Planned 2026-10-01. Decisions [PG-D1–PG-D11](#decisions) accepted 2026-10-01. The same
day the user chose **PostgreSQL only** over a mixed setup with SQLite for development, so PG-D2,
D3, D4, D6, D7 and D8 were revised to that and PG-D10 added; each keeps its accepted intent. PG-D11
(ICU root collation) was decided at the start of PG1. **PG-D12–PG-D17 and the package
[PG3b](#pg3b-batch-writes-decided-in-memory-written-in-bulk) accepted 2026-10-01 after H2**, when the
100,000-item budget test (19 minutes) showed a batch item costing a whole single write: dozens of
statements, each a round trip to the server.
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
added. D11 accepted 2026-10-01 at the start of PG1. D12–D17 accepted 2026-10-01 after H2.

| # | Question | Decision |
| --- | --- | --- |
| PG-D1 | Release version | **0.9.0-alpha.1**, tagged `v0.9.0-alpha.1`. `main` already carries delivered 0.9 packages (Q1–Q4, C1, V1, B1, B2) and the starter is content release 0.9.0 on schema 0.8, so a 0.8.x patch would claim to be 0.8 plus fixes, which it is not. A SemVer pre-release of 0.9 orders before 0.9.0, does not use up 0.9.0, and says what it is. The CHANGELOG gets a `[0.9.0-alpha.1]` section, and the 0.9.0 notes later cover everything since 0.8.0 |
| PG-D2 | The database | **PostgreSQL only**, for the runtime, the tests and the browser runners. SQLite is removed with its settings, dialect branches and migrations (revised from "PostgreSQL for the product, SQLite for development") |
| PG-D3 | The migration history | **One PostgreSQL baseline revision** at today's head schema (`20261001_01`). The 25 SQLite-shaped revisions, their interrupted-run recovery and their tests are removed (allowed before 1.0; no PostgreSQL database exists). Revisions after it are written and tested on PostgreSQL. Existing SQLite data carries over by PG-D10 |
| PG-D4 | Foreign keys | **Enforced, and every `ondelete` rule checked** (accepted as important). PostgreSQL enforces them; PG2 checks each rule against what its service expects, so a delete the services order explicitly (to write their audit entries) still works, and nothing relied on SQLite ignoring them. Closes the TODO item from 0.8 W6 |
| PG-D5 | Invariants that relied on SQLite's single writer | **The per-workspace write lock, taken now.** The live write unit (`LiveWrites`) opens with `SELECT … FROM workspaces WHERE key = … FOR UPDATE`, the lock F1 needs anyway (D5, lock order: workspace, then records). Writes in one workspace serialize, so the per-workspace checks (unique values, parent cycles, cardinality, required relations, sibling rules, relation sets, matrix states) stay sound, while workspaces run in parallel. Change set writes already serialize on their version claim, and publish locks the workspace first. F1 then adds only the feed counter. Per-invariant database constraints wait for evidence (0.11) |
| PG-D6 | Isolation and locks | READ COMMITTED for writes, as D28 assumes; multi-statement reads keep `begin_snapshot_read` (REPEATABLE READ). `BEGIN IMMEDIATE` becomes the row lock each place needs: the runtime-state row for activation, the change set row for lifecycle, the workspace row for the catalogue. `db.begin_transaction` and `SQLITE_LOCK_WAIT_SECONDS` are removed |
| PG-D7 | Search index | **`pg_trgm` GIN indexes** replace the FTS5 tables, with the same contract (S8: the index decides speed, never which records match). The baseline runs `CREATE EXTENSION IF NOT EXISTS pg_trgm`; a role that may not create it is refused at startup with that instruction |
| PG-D8 | Running PostgreSQL | **Homebrew's `postgresql@17` binaries, never `brew services`.** The test harness starts a private server on a data directory under `backend/.test-postgres/` (git-ignored) on a local socket, created with ICU `und` (PG-D11), with durability off since its data is disposable, and stops it when the run ends; the seeded databases (H1) live there as template databases between runs, and each test gets a clone. `scripts/postgres.sh start|stop|backup` runs the development server on its own data directory, for the app and the browser runners. CI (once the repository has a remote) uses a `postgres:17` service. The Docker compose file stays for a containerised deployment |
| PG-D9 | Driver and connections | `psycopg` 3 (already a dependency), synchronous, SQLAlchemy's pool with `pool_pre_ping`. `WEB_CONCURRENCY` stays 1: several processes need 0.11's cross-process release propagation, not a database change |
| PG-D10 | Existing SQLite databases | **A one-off copy command** (`python -m app.tools.copy_from_sqlite <sqlite-url>`) copies a SQLite database at `20261001_01` into an empty PostgreSQL database at the baseline, table by table in dependency order. It keeps public IDs, sequence values, typed values and history, rebuilds the derived indexes (matrix states, search), checks the row counts, and refuses a source at another revision or a target that is not empty, each with an instruction. It is removed again in 0.11. On 2026-10-01 `backend/rdm-engine.db` and `rdm-engine.db` were at `20260928_01` and are upgraded first with the current code; `backend/rdm-operators-timetables.db` is at `20261001_01`. Backups first, and only with the user's go-ahead |
| PG-D11 | Collation | **ICU root collation (`und`), on every database the engine runs on.** Reference data holds many languages side by side, so the order must be language-independent without choosing a language: the Unicode Collation Algorithm's root order sorts every script sensibly at once (case and accents rank below the base letter, so `Elan, élan, Élan, Emil`), and ICU makes `lower`, `upper` and case-insensitive matching Unicode-aware. Rejected: `C` (code-point order, right for no language, and case mapping for A–Z only; it only kept SQLite's order) and a libc locale such as `en_US.UTF-8` (the operating system's collation: almost code-point order on macOS, linguistic on Linux and changed by glibc upgrades, so tests would not prove production). The test and development servers are created with `initdb --locale-provider=icu --icu-locale=und`, and startup refuses a database whose default collation is not ICU `und`, with the `CREATE DATABASE` instruction. Equality and uniqueness are unchanged (the collation is deterministic). The visible sort order of names changes (CHANGELOG). Code that sorts names in Python beside the database's order (for example `reads/relation_queries.py`, `operations/restructuring.py`) and tests that build an expected order with `sorted()` follow the database's order in PG2. A language-specific order (Hungarian `cs`, Swedish `å ä ö`) would be an optional per-request refinement later, never a requirement |

| PG-D12 | How batch items are written | **Decided in memory, written in bulk, per chunk.** A chunk reads what its items name once per kind (`IN` lists), decides every item in order through the write rules, and writes the accepted items as multi-row inserts. A single API write is a batch of one through the same code, so there is still one write path. Create, update and upsert only; delete stays per item (PG-D18 note) |
| PG-D13 | Where the rules read | **A batch lookup, not new rules.** A third lookup beside `LiveLookup` and `ChangeSetLookup`, preloaded per chunk, with the items accepted earlier in the chunk laid over it, so each item sees the earlier ones (D23). `rules.py` is unchanged; the services around it (`apply_object_create` and the update and upsert paths) are split into a decide step and a write step. `test_rule_parity` gains the batch context: the same refusals with the same codes |
| PG-D14 | Concurrency between the reads and the writes | **PG3's workspace lock (PG-D5), held for the chunk**; in a change set its version claim, as today. So PG3b follows PG3. Uniqueness stays enforced by the engine (PG-D5; database constraints wait for 0.11) |
| PG-D15 | A failure inside a chunk | **No savepoint per item.** A refused item is never written. A bulk write that fails on something the rules did not predict redoes that chunk item by item, as batches of one, so the item fails with its single write's code |
| PG-D16 | History | **Per record, as today:** one audit event per item with the job as its cause, inserted together; the events' sequence numbers come back from the insert (`RETURNING`) for their subjects. Typed value index rows go through `snapshot_values` and matrix notes through `note_rows`/`note_cells`, applied once per chunk as now (ADR-033) |
| PG-D17 | How the cost is held | **Counted, not timed.** Statements per chunk at two seeded dataset sizes, which must not grow with the data or with the chunk's item count beyond a constant; seconds to run, in the parallel part. The 100,000-item run becomes a measurement at PG5's acceptance, announced and run once. Target: 100,000 items in under a minute in each context, confirmed or restated by that first measurement |

**Note (PG-D18, open, to revisit):** batch deletion stays per item in PG3b, and neither today's
per-item path nor a set-based copy of it is the right answer. A large delete batch is not rare, and
it must not occupy the job worker for minutes or stall the engine. Revisit after PG3b with the
deletion path's cascades, subtree impact and signed confirmation in view
([TODO](TODO.md#now--product-09)).

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
| Collation | SQLite's binary order; names sorted in Python beside it | ICU `und` (PG-D11); Python-side name sorts follow the database's order |
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
URL, a missing extension, a collation other than ICU `und` (PG-D11) and an unknown revision, each
with an operator instruction;
`scripts/postgres.sh`; `.env.example` and README. The test harness on PostgreSQL (PG-D8) with the
seed store of [H1](TEST_HARNESS_PLAN.md#h1-seeded-databases-built-once): the private server, seeds
as template databases with their fingerprints, one clone per test. The SQLite revisions and their
migration tests removed. First, a measurement on the seeded harness: `records` and the volume reads
against the SQLite numbers recorded in TEST_HARNESS_PLAN, recorded in the package.

**Tests:** clean bootstrap, restart, an unknown revision refused, a missing `pg_trgm` refused, a
database with another collation refused, the
lifespan against a real database, schema drift (ORM against migration), and H1's evidence (a second
run seeds nothing). **Groups:** `startup`, `contract`.

**Exit:** the application starts on PostgreSQL, `startup` and `contract` pass on it, and seeds are
reused across runs. Other groups may fail until PG2. **Amended 2026-10-01 (user's decision during
PG1):** five tests in those groups (six cases) need two PG2 rows, current-live change set capture (refused on
any database but SQLite) and the matrix row list (`json_each`), and pass in PG2:
`test_matrix_states` `test_startup_builds_what_is_missing_and_a_failed_build_falls_back`,
`test_activation_and_release_change_follow_the_model`,
`test_change_set_writes_and_publishing_keep_states_derived` and
`test_a_long_row_list_filters_as_one_value` (`startup`), and `test_model_placements` `test_served_in_the_context_of_the_model` (`contract`, both
models).

**Delivered 2026-10-01.**

- **Runtime.** `DATABASE_URL` is required (`config.py` no longer defaults to a SQLite file).
  `db.py` has one pooled psycopg engine (`pool_pre_ping`), and `create_database` checks before it
  migrates, refusing each case with what failed, the maintenance state and the next step: no URL, a
  non-PostgreSQL URL (naming PG-D10 for SQLite data), another driver, an unreachable server, a
  collation other than ICU `und` (PG-D11), a revision the code does not know, and a `pg_trgm` it
  cannot create (contrib missing or no privilege). `DatabaseStartupError` is the lifespan's and
  `cli/database_upgrade`'s one refusal type; a migration failure says the database is still at its
  revision, since PostgreSQL rolls the migration's DDL back. `migrations/env.py` reads
  `DATABASE_URL`, so the `alembic` command needs no URL in `alembic.ini`. `begin_snapshot_read`
  ends a request's read-only transaction (its model resolution) before setting REPEATABLE READ,
  which PostgreSQL accepts only first; each earlier read stood alone on SQLite as well.
- **Baseline `20261001_01`** (PG-D3), autogenerated from the ORM on PostgreSQL 17, plus `pg_trgm`.
  Two things the ORM does not say and PostgreSQL showed: every foreign key is added after all tables
  and indexes (several reference a column a unique *index* makes unique, `objects` references
  itself, and `workspaces` and `publications` reference each other), and the default workspace
  with the runtime state naming it is inserted, as the SQLite history did (checked against a clean
  SQLite database built by the removed revisions). The 23 SQLite revisions and seven migration test
  modules are removed; `test_jobs_migration` became `test_job_settings` (the settings, and the value
  index seek shown with `EXPLAIN`); `test_search_index` and `test_matrix_states` lost their
  migration tests, and `test_search_index` left `startup`.
- **A contract fix PostgreSQL exposed** (principle 4): the relation list's `ancestor:<type>` sort
  took the ancestor's name as a bare column beside `max(depth)`, which SQLite allows and PostgreSQL
  refuses. It is now `DISTINCT ON (start) … ORDER BY start, depth DESC`, the same ancestor nearest
  the root (`test_paging_contract`, three contexts).
- **Development server.** `scripts/postgres.sh start|stop|status|backup` (PG-D8) on
  `backend/.postgres/`, localhost port 54320 and a socket, ICU `und`, the database `rdm`; it prints
  the `DATABASE_URL`. `.env.example`, README, `docker-compose.yml` (`POSTGRES_INITDB_ARGS` for ICU
  `und`) and CI (a `postgres:17` service the harness uses through `RDM_TEST_DATABASE_SERVER`) follow.
- **Test harness** ([H1](TEST_HARNESS_PLAN.md#h1-seeded-databases-built-once), its PG1 part):
  `tests/postgres_server.py` starts a private server on `backend/.test-postgres/` (ICU `und`, socket
  only, durability off; stopped when the run ends) and `tests/seeds.py` keeps template databases
  with fingerprints in an `rdm_harness` catalogue: `schema` (the migrations) and one
  `volume-<groups>x<items>-<hash>` per shape (the volume model, `volume_fixture.py`, the matrix,
  snapshot value and bootstrap modules it calls, the shape). The session database,
  `migrated_database()` and `volume_app(directory, shape)` are clones (about 90 ms each, `FILE_COPY`);
  `python -m tests.seeds list|build`; the run's summary names each seed reused or built.
  `volume_fixture.seed_volume` now runs `ANALYZE` after its bulk load, as autovacuum would, and the
  fixture's reproducibility check seeds a second database afresh (`seed_fresh`) and compares it with
  the seed.

**Measurement** (2026-10-01, this machine, against a checkout of `a6e636d` on SQLite):

| What | SQLite | PostgreSQL | Note |
| --- | --- | --- | --- |
| Volume reads, `run_scenarios` at 0.01, 5 timed runs | median 5.0 ms, total 1.15 s | median 7.9 ms, total 2.95 s | 141 scenarios: same statuses and statement counts. Non-matrix reads 1.0–2.5×; relation matrix reads 3.6–6× (PG2's matrix forms) |
| `records` group, the 137 tests passing on both | 21.7 s | 33.9 s (1.56×) | per-statement round trips; app start 21 → 33 ms; clone 92 ms |
| `records` group, the rest | 242 pass | 103 fail | 79 current-live capture, 22 SQLite `PRAGMA` in `test_wp8_review_regressions`, 1 `json_each`, 1 expecting the SQLite-era refusal code (PG2) |
| Volume fixture seeded, 0.01 | 1.9 s every run | 60 s once, then a 0.8 s clone and start | the build is the matrix state build (correlated subqueries, about ×4 per doubling: 15 s at 0.005, 62 s at 0.01); PG2's matrix forms |

Principle 3 does not hold yet: per test PostgreSQL costs about 1.5× SQLite, and only seeds that
SQLite also seeded slowly gain from the store. H2's parallel runs are the planned compensation; PG2
re-measures after the matrix forms.

**Checks:** `-m "startup or contract"` twice back to back from a stopped server: 76 passed, 5
failed and 1 error each time, exactly the six cases named in the amended exit (current-live capture
and `json_each`); each run 37 s wall, both naming `schema` and `volume-100x1000` as reused, and
the server stopped after each. `test_startup` 9 passed, `test_schema_drift` 3 passed,
`test_paging_contract` 32 passed. `test_request_scope` 6 passed (the URL has no default now). Fingerprints (`tests.seeds list`): a line added to the baseline
made `schema` and every volume seed stale, a line added to `volume_fixture.py` only the volume
seeds, and reverting made them current again; a changed migration rebuilt `schema` in 0.3 s on the
next run. `tests.seeds build` built 0.005 in 15 s, 0.01 in 62 s and 0.02 in 262 s; 0.04 (about
15 minutes at that rate) was stopped and is built on first use, after PG2's matrix forms change
its fingerprint anyway. Smoke start against the development server: `scripts/postgres.sh start`,
`python -m app.cli.database_upgrade`, uvicorn with `/health` ok and `/api/v1/model` 200, `backup`,
`stop`. `ruff check app/ tests/`. Not run: the other groups (PG2's exit), the browser runners (on
SQLite until PG2), the frontend (unchanged). The developer's SQLite databases are untouched (PG4).

### PG2: PostgreSQL forms

**Scope:** every row of the [inventory](#inventory) not done in PG1, except the workspace lock:
search on `pg_trgm`, the matrix forms, the partial index, the upsert, Python-side name sorts and
order assertions following the ICU order (PG-D11), row locks for activation,
change set lifecycle and the catalogue, `begin_transaction` and `SQLITE_LOCK_WAIT_SECONDS` removed,
every `ondelete` rule checked (PG-D4). The browser runner harness on the development server, with its seed in the seed store, and the heavy
`records` and `change_sets` modules' common records as seeds (H1's split). No
dialect name remains in `app/` (`test_boundaries`).

**Found in PG1, for PG2:** the tests named in PG1's amended exit; `test_wp8_review_regressions`
issues SQLite `PRAGMA`s (22 tests); the matrix state build's correlated subqueries (a volume seed at
0.01 builds in 60 s, about ×4 per doubling); `volume_seed.py` and `volume_baseline.py` still write
SQLite files (the browser runners' seed and the full-size measurement move to the seed store).

**Tests:** every backend group except `volume` passes. A failure is fixed to the documented contract
(principle 4) and recorded.

**Exit:** `ruff`, and all groups except `volume`, green on PostgreSQL. H2 and H3 of the test harness
can then follow.

**Delivered 2026-10-01.**

- **Current-live capture** (the 79 `records` failures of PG1). The capture reads at REPEATABLE READ
  through `begin_snapshot_read` and takes share locks on the workspace and runtime-state rows, so a
  retirement or an activation cannot commit while it runs; a row changed after the snapshot began
  (SQLSTATE 40001) answers the documented `409 change_set_snapshot_retry` and saves nothing.
  `change_set_snapshot_unsupported` is gone.
- **Row locks (PG-D6).** Activation keeps its `FOR UPDATE` on the runtime-state row and loses the
  SQLite `BEGIN IMMEDIATE` branch; workspace deletion already locked its rows. Both now wait for a
  lock instead of failing on a busy database, so `model_activation_retry`, `ActivationBusy` and
  `workspace_delete_retry` are removed (API.md). `db.begin_transaction` and
  `SQLITE_LOCK_WAIT_SECONDS` are removed; a job chunk's savepoint needs no explicit `BEGIN`. The
  cascade deletion's table lock is now unconditional (it was the PostgreSQL branch).
- **Search (PG-D7).** `pg_trgm` GIN indexes on `attribute_values.text_value` and
  `snapshot_attribute_values.text_value`, declared in the ORM and created by revision `20261001_02`
  (the first revision after the baseline). The guard keeps its shape: the index's `ILIKE` matches,
  counted up to 10,001, narrow which records' values are read; the `LIKE` still decides. Case
  folding is now Unicode's (ICU), so `ünal` finds `Ünal`, which SQLite's ASCII folding did not.
- **Matrix forms.** The long row list is one array parameter (`= ANY`) and the `INDEXED BY` hint is
  gone. The three downward walks over a change set (`descendants`, `matrix_down`, `matrix_below`)
  join one selectable of the context's rows in one recursive term (`CellScope.object_rows`).
  **The build's cost** was not the correlated look-ups: the cell records were joined back to the walk
  of their distinct records, a join of two CTEs PostgreSQL estimated at one row each and planned as a
  nested loop, re-running a look-up per pair (2.3 million at 0.005). `cell_columns` now carries each
  record's columns up the walk, so the states (`cell_states`), the page's cells and the history cells
  group the walk's ends with nothing joined back.
- **Upsert, partial index, JSON key.** `claim_set_version` uses PostgreSQL's insert only;
  `sqlite_where` is gone; the compatibility check's "relation holds this attribute" is `->` (the
  PostgreSQL branch used `?`, which `json` does not have, and no test had run it).
- **Collation (PG-D11).** `expansion_rows` orders its union in SQL; the restructuring planner ranks
  names through the database (`db.name_ranks`). Tests compare name orders with
  `postgres_server.collated`, which sorts as the server does.
- **Foreign keys (PG-D4).** Every rule was checked against the service that deletes the referenced
  row; none needed a change, since the services already delete dependants and detach parents
  themselves. `test_foreign_keys` pins the 40 rules in the ORM and in a migrated database. One
  behaviour followed from enforcement: a create that resolved a workspace deleted before its insert
  now fails the foreign key, which `LiveWrites.add_object` answers as the documented
  `404 workspace_not_found` (`test_w6_workspace_deletion`); PG3's workspace lock will make the two
  serialize instead.
- **No dialect in `app/`.** `test_boundaries` refuses an identifier, keyword or import naming SQLite,
  a `.dialect` read, and `BEGIN IMMEDIATE`, `PRAGMA`, `INDEXED BY`, `json_each`, `json_type` or
  `fts5` in a string. SQLite remains in prose only: the planner rationale in comments, which PG5
  reviews with the budgets.
- **Tests on PostgreSQL only.** The three modules that ran on in-memory SQLite (`test_model_lifecycle`,
  `test_model_compatibility`, `test_change_sets`) use `seeds.schema_session()`, a clone of the
  `schema` seed, with real release rows where they had invented `model_release_id=1`. Two that
  started on a SQLite file use `migrated_database`. The `PRAGMA` modules lost their pragmas. The
  SQLite writer-lock tests became PostgreSQL ones: a capture reads one snapshot while another
  connection commits, holds off an activation and a retirement (lock timeout), and a capture that
  waits for a committing activation answers the retry; a change list page keeps its snapshot while a
  rename commits. A test that fabricates a pin to a missing release turns foreign keys off for its
  own transaction (`postgres_server.without_foreign_keys`). A pre-existing failure from B1 is fixed:
  `test_model_admin_capabilities_and_routes_are_disabled_by_default` compared the whole capabilities
  document, which gained `integrationJobs`.
- **Browser runners** (H1's PG2 part). `tests/browser_seeds.py` clones a seed on the development
  server and prints its URL and payload; `e2e/helpers/database.mjs` calls it and drops the clone at
  the end. Seeds: `schema`, `starter-<model hash>` (the harness's records, created through the API
  when the seed is built) and the volume seeds; `volume_seed.py` prints the clone's URL with the
  dataset. All 19 runners on the harness and the five that start their own backend use it. A clone
  an interrupted runner left is dropped by a later clone after six hours. `volume_baseline.py`
  measures on a clone of the volume seed on the test server.
- **Dropped (user's decision, 2026-10-01):** the heavy modules' common records as seeds.
  `test_type_changes` and `test_rule_parity` share no records: each case creates its own through the
  API as part of the write it checks (30 s for their 21 tests on PostgreSQL).

**Found in PG2, for later packages:** the cascade deletion locks three whole tables, which PG3's
workspace lock should replace (done in PG3); publishing locks the workspace row, but plain live writes take no
workspace lock until PG3, so a live write can still commit beside a publish (PG-D5, as planned);
time budgets and comments still describe SQLite plans (PG5).

**Measurement** (2026-10-01, this machine, the 0.01 volume seed): the 141 `run_scenarios` reads,
five timed runs, median 7.7 ms and total 1.72 s (PG1 7.9 ms and 2.95 s; SQLite 5.0 ms and 1.15 s);
the 21 relation matrix reads' median 113 → 37 ms. Matrix state build in seeding: 0.005 14.3 → 0.3 s,
0.02 1.0 s (the seed took 262 s in PG1), 0.1 7.2 s. Browser seeds on the development server:
`starter` built in 2.2 s and cloned in 0.5 s; volume 0.02 in 5 s and 0.1 in 22 s, once.

**Checks:** `-m "not volume"` 970 passed in 6 min 32 s (all groups but `volume`, before the matrix
walk changes); after them, `-m "matrix and not volume"` 69 passed and
`-m "(records or change_sets) and not volume and not matrix"` 452 passed in 4 min; `-m contract` 53 passed
(with `test_paging_contract`, its volume seed rebuilt in 2.2 s). `test_startup` includes a database at
the baseline upgraded to `20261001_02` and started twice, and that revision interrupted, refused with
the database left at the baseline, and recovered. Smoke start on a copy of the development database
`rdm` (at `20261001_01`): `python -m app.cli.database_upgrade` to `20261001_02`, uvicorn with
`/health` ok, `/api/v1/model` 200, a current-live change set 201 and a search 200; the copy dropped.
Browser runners against the development server: `test:browser:v1`, `test:browser` (wp9-navigation),
`test:browser:wp11` and `test:browser:s6` (volume 10 %) passed, leaving only seeds behind;
`npm run test:gate-helpers` 5 passed. `ruff check app/ tests/`. Not run: the `volume` group (PG5
restates its budgets), the other browser runners (PG5's acceptance), the frontend suites (no `src/`
change).

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

**Found in H3 (2026-10-01), PG3's to fix:** a generic relation create and a mapping save on the
same edge deadlock under load. The create inserts the edge and then advances the set versions; the
mapping save claims the set version and then inserts the edge, so each waits for the other's
row and PostgreSQL ends one with `deadlock detected`, answered as a 500 instead of
`409 mapping_version_conflict` (`test_mapping_replacement::test_overlapping_generic_write_forces_mapping_save_to_refresh[create]`,
once in H3's parallel run; it passed in H2's). The per-workspace lock taken in `LiveWrites._begin`,
before either reads, orders the two writes. The race test above covers it.

**Exit:** the concurrency tests pass; the D28 and B2 notes in TODO are closed.

**Delivered 2026-10-02.**

- **The workspace lock (PG-D5).** `LiveWrites._begin` opens every live write with
  `SELECT status FROM workspaces WHERE key = … FOR NO KEY UPDATE` before it reads, and refuses a
  workspace deleted (`404 workspace_not_found`) or retired (`409 workspace_retired`) while the write
  waited, both "nothing was saved". *Differs from the design's `FOR UPDATE`:* `NO KEY UPDATE`
  conflicts with itself, publishing, a capture's share lock, retirement and deletion, but not with
  the key share lock a row naming the workspace takes through its foreign key, so starting a change
  set or queuing a job does not wait for live writes.
- **Lock order, written into ARCHITECTURE:** workspace, change set, runtime-state row, records, and
  the job row at a chunk's checkpoint. *Differs from the design's "workspace, then change set, then
  records":* the runtime-state row is placed, because a live write takes it shared as it commits
  (W5) while retirement, default switching and deletion took it before the workspace, which would
  now deadlock with a live write; those three lock the workspace first. Publishing locked its change
  set before the workspace and now locks the workspace first. Change-set writes take no workspace
  lock, as before.
- **What the lock replaces.** The cascade deletion's `LOCK TABLE` on three tables and its
  `claim_active_workspace` update; a live mapping save's own `UPDATE workspaces` claim (a change-set
  mapping save keeps it, in lock order); the foreign-key answer in `LiveWrites.add_object`, which
  PG2 added for a workspace deleted mid-create and which can no longer happen.
- **Batches (PG-D14 in part).** A live batch, inline or one background chunk, takes the lock once
  before its first item resolves a record, outside the items' savepoints, so a refused item never
  releases it and the chunk holds it to its commit. A live write in the job's workspace waits for
  one chunk at most; one in another workspace does not wait.
- **Doors (ADR-032):** bulk APIs are touched (a batch takes the lock once per chunk); none is
  closed: the lock is per workspace, generic, and changes no identity, storage or history.
- **H3's deadlock** (a relation create and a mapping save on one edge) is gone: both take the
  workspace lock before they touch the edge or a set version, so the mapping save reads the
  committed create and answers `409 mapping_version_conflict`.

**Tests:** `test_pg3_concurrency` (15, groups `records`, `mapping`, `matrix`, `jobs`, `model_admin`,
`workspaces`). Each race holds one write (just after it takes the lock, or with its checks done and
rows flushed just before commit), starts a second on another connection, sees it wait on the lock in
`pg_stat_activity`, and releases the first: a unique value, a parent cycle, a one-to-many limit, a
required relation against the deletion of its source, a relation-set version, H3's create and
mapping save, and two relations in one stored matrix cell (`matrix_states.verify` clean after every
test). Not serialized: a write in another workspace completes while the first is held. W5 on row
locks: an activation completes while a write holds the workspace lock and the write is refused
`model_release_changed`; an activation waits for a write already committing, and a retirement for a
live write, neither deadlocking. D28 and B2: a cancel request answered (`202`) while a chunk runs,
the chunk committing and the job then cancelled; an atomic job cancelled between items rolled back
completely; a worker whose lease expired mid-chunk losing the chunk to a second worker that waited
for its lock, every item applied once; a live write beside a chunk written between two chunks.
Without the lock (the `FOR NO KEY UPDATE` removed for one run) the ten races that depend on it fail
and the other five pass. *The latency bound B2 left open* is stated structurally (one chunk, held
by the test) rather than timed; the timed figure belongs to PG5's measurement.

**Checks:** `pytest -n 10 -m "records or change_sets or mapping or matrix or jobs or model_admin or
workspaces"` 780 passed in 2 min 7 s, **7 s over the 2-minute package ceiling** (the union of seven
groups is most of the suite; the tests over 10 s are existing ones, the longest
`test_change_set_position_reads` at 43 s, for H4); `-m "serial and (…)"` 3 passed in 21 s;
`test_boundaries` 3 passed; `ruff check app/ tests/`. Two earlier `-n auto` runs hung at worker
startup before reaching the database; `-n 2`, `-n 10` and a later `-n auto` ran normally, so this
was the background shell, not the change. Not run: `startup` and `queries` (no code on their
paths changed), the `budget` tests, browser runners and frontend suites (no UI or contract change;
the OpenAPI document is unchanged).

**Found in PG3, for later packages:** an activation that drops a matrix shape locks that shape's
state rows after taking the runtime-state row, while a batch applies its matrix notes before its
commit check takes that row shared; the two could deadlock (PostgreSQL ends one, answered as a
500 or a failed job). It needs a release that removes a `relationMatrix` view while a live batch
in a workspace with that view runs. Not reproduced; for PG5 to decide (a retry, or the commit
check before the matrix notes). Change-set writes still check the workspace's active status without
a lock, so a retirement can commit beside one (as before PG3).

### PG3b: Batch writes decided in memory, written in bulk

**Scope (PG-D12–PG-D17):** create, update and upsert items of `POST /batches` and background jobs,
live and in a change set.

- The batch lookup (PG-D13): preloads per chunk the records, parents, ancestors and unique-value
  holders its items name, and lays accepted items over them.
- The decide/write split of the object create, update and upsert services; a single write runs both
  for one item. Initial relations resolve their other ends through the lookup.
- The bulk write: records, attribute values, containment and initial relations, typed value index
  rows and audit events with their subjects, as multi-row inserts per chunk; matrix notes once per
  chunk.
- The fallback (PG-D15) and the workspace lock held for the chunk (PG-D14).
- Delete items keep today's per-item path (PG-D18).

**Tests:** `test_rule_parity` with the batch context; the batch tests (`test_batches`,
`test_background_jobs`, `test_batch_matrix_states`) unchanged and green; statements per chunk counted
at two seeded sizes (PG-D17), replacing the timed checks in `test_batch_volume` and
`test_background_volume`; a chunk whose bulk write fails falling back with the single write's code;
two writers racing for a unique value across a chunk. **Groups:** `records`, `change_sets`, `jobs`,
`matrix`. **Doors (ADR-032):** bulk APIs, attribute storage and audit/history are touched; none is
closed: the batch lookup and the bulk write are generic, and history stays per record.

**Exit:** the groups green within the [time ceilings](TEST_HARNESS_PLAN.md#time-ceilings); no
full-size run in the package.

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
bound for writes beside a background job. The 100,000-item batch is measured once here, live and in
a change set, against PG-D17's target, announced with its expected time before it runs
([time ceilings](TEST_HARNESS_PLAN.md#time-ceilings)). The TODO SQLite debt item is
closed: a search for SQLite and dialect names in `app/`, `tests/` and `frontend/e2e` finds nothing
that is not history. AGENTS.md, ARCHITECTURE, README and EXECUTION_GUIDE describe PostgreSQL only.

**Acceptance (the interim release's build acceptance):** the full backend suite on PostgreSQL,
its parallel and serial parts and, once, `-m budget` (H3);
frontend format, lint, `npm run test` and build; the browser runners against the PostgreSQL backend.
Nothing in the UI changes, so visual and accessibility runs are added only if a runner's journey
shows a difference.

**Release:** version 0.9.0-alpha.1 in `pyproject.toml` and the FastAPI title. The CHANGELOG section
covers everything since 0.8.0. Tag `v0.9.0-alpha.1` on the user's instruction (commit and tag only
when asked).

## Composable domains (ADR-032)

Identity and attribute storage are touched (the baseline, the copy and the indexes) and no door is
affected. Public IDs, typed value columns and the audit cause are copied as they are, and the
workspace lock serializes writes within the uniqueness scope (ADR-010) without changing it. PG3b
touches bulk APIs, attribute storage and audit/history and closes no door (see its scope).

## What stays in 0.11

Multi-node and multi-process operation (cross-process release propagation, the job worker on
several nodes through its lease, `WEB_CONCURRENCY` above 1). Production-scale performance: the
volume fixture at full scale, connection pool sizing, and model-derived indexes, including unique
checks on non-text values. Precomputed sort keys (D26). Database constraints as a second line
behind the workspace lock (a database lock, so it holds across nodes), for writes that bypass the
write unit, decided on evidence. Metrics, structured logging, readiness, and backup/restore
rehearsal with `pg_dump`. See
[ROADMAP 0.11](ROADMAP.md#product-release-011--production-hardening-and-staged-model-rollout).
