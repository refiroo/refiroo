# PostgreSQL read budgets: findings and the post-1.0 fixes

**Status:** written 2026-10-03 at the close of
[0.9.0-alpha.1 PG5](POSTGRESQL_RUNTIME_PLAN.md#pg5-budgets-acceptance-and-release). The remaining
budget exceptions on PostgreSQL are **deferred to the first fixes after 1.0** (user's decision,
2026-10-03). This document is the complete handoff: what the budgets are, how to measure them without
wasting hours, what PG5 found and fixed, every open exception with its cause, the fixes considered and
what was tried and rejected. Start the post-1.0 work here, not from the PG5 session.

## 1. The budgets

Set in Base 0.8 S1 ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md), "_Budgets._" under S1) on the Track S
volume fixture: 110,254 live records (100,000 items, 10,000 groups, a 7-level node hierarchy), a
261,000-row publication history, a change set with 1,592 rows over it, and 30 matrix columns with
150,055 cells.

1. **Statements.** A request's SQL statement count does not change with the dataset size.
2. **Rows.** A request materialises at most 6 ORM rows per row of a full 20-row page (120).
3. **Time.** At full volume, a page or record read in any context (live, change set, history) stays
   within **100 ms median**, and a single-record write within 50 ms.

Budgets 1 and 2 are held by tests at two seeded sizes (`test_volume_baseline`,
`test_change_lists_volume`, `test_restructuring_volume`, `test_relation_matrix_volume`,
`test_batch_statements`, `test_paging_contract`): **54 passed at PG5's close**. Budget 3 is a
measurement, not a test, because wall time depends on the machine.

Batch budgets: D13 (B1, an inline batch costs no more per item than its single write) and PG-D17 (a
100,000-item background batch in under a minute per context), measured once per release with
`pytest -m budget`.

### Is 100 ms reasonable on PostgreSQL?

Yes, for a page read: ~100 ms is the usual threshold for a response that feels immediate, and an
indexed 20-row page answers in single-digit to low tens of milliseconds on PostgreSQL (most of the
table below). The database switch did not move typical reads. The exceptions share one shape: in one
request they count, filter or probe tens of thousands to ~100,000 rows (an exact total over a search
matching nearly everything, a matrix filter whose result is thousands of row IDs, a deep position in a
change set computed as base minus overlay). PostgreSQL checks every row's visibility (MVCC) when it
counts or scans; SQLite, in-process and without that check, counts faster. Some of these reads were
over budget on SQLite too (a match-everything search took ~0.4 s there). Products keep such reads
fast by design, not by database choice: no exact total over large result sets (a cap such as
"10,000+", an estimate, or a count computed separately), keyset paging instead of deep positions or
precomputed ranks, a filter computed once per request and reused, covering indexes on vacuumed
tables, search in a dedicated index, caching or materialising what changes less often than it is read.
Whether the 100 ms promise stays as it is for the reads in §5 is a product decision.

## 2. How to measure (and how not to)

**What went wrong in PG5, so it is not repeated.** PG5 spent hours in rounds of
measure → change → full re-measure: `volume_baseline.py --scale 1` replays every scenario (154 reads,
5 runs each) and takes 3–7 minutes, and several changes were made per round. Rounds disagreed because
of noise, cold caches and statistics, not code, and one data-dependent planner choice was flipped
back and forth on timing evidence. The user's laptop is a working machine; other load moves single
figures by 20–50 %. **Use the full replay once, at the end. Diagnose with plans.**

### The method

1. **Per statement, from its plan.** For a slow read, capture its statements and `EXPLAIN (ANALYZE,
   BUFFERS)` the slow one on the full-volume clone (recipe A). Name the cause from the plan: an
   estimate far from the actual rows, an index chosen that filters thousands of rows, a join order
   driven by a wrong estimate, a walk over a whole index with a filter.
2. **One change, checked on that statement's plan**, at both data sizes the read must serve (the full
   volume and the small seeded sizes the tests use). A change that only moves timing without changing
   the plan is noise.
3. **Statistics are part of the input.** A plan on freshly written rows (a change set base just
   captured, a clone seconds old) can differ from the same plan after autovacuum's `ANALYZE`. Check
   the worst case deterministically with recipe B, never by repeating a run until it is slow.
4. **One closing measurement** of the final code, warm (§2, "cold and warm").

### Commands and their cost (this machine, Apple M1 Pro)

| What | Command (from `backend/`) | Time |
| --- | --- | --- |
| Full-volume read table | `.venv/bin/python tests/volume_baseline.py --scale 1 --repeat 5 --json out.json` | ~3.5 min, plus ~3 min when the seed rebuilds |
| Restructuring planner near its limit | `… volume_baseline.py --only-restructuring --scale 0.024` | ~30 s |
| Dated reads only (0.9 T1) | `… volume_baseline.py --only-dated --scale 1 --repeat 3` | ~10 s |
| Exports of the whole live workspace, once per format (0.9 J1) | `… volume_baseline.py --only-exports --scale 1` | ~1.5 min, plus ~5.5 min when the seed rebuilds |
| Publish of a tenth of the items renamed (0.9 T1; the full table runs it last) | `… volume_baseline.py --only-publish --scale 0.1` | ~1 min (11 s publish after T1); at `--scale 1` about 2 min plus |
| Budgets 1–2 | `.venv/bin/python -m pytest -n auto -q tests/test_volume_baseline.py tests/test_change_lists_volume.py tests/test_restructuring_volume.py tests/test_relation_matrix_volume.py tests/test_batch_statements.py tests/test_paging_contract.py` | ~20 s |
| Validate and publish at 2 % volume (serial, timed) | `.venv/bin/python -m pytest -q tests/test_graph_validation_scale.py::test_validating_and_publishing_a_large_workspace_stay_within_budget` | ~20 s |
| Batch budgets (a release's acceptance only) | `.venv/bin/python -m pytest -m budget -q -s` | 2 min 39 s at PG5 |

The full-volume seed is rebuilt when any of its inputs changes: the migrations, `tests/volume_fixture.py`,
`app/engine/indexes/matrix_states.py`, `app/engine/indexes/snapshot_values.py`,
`app/engine/model/bootstrap.py` or the volume model (`tests/seeds.py`, `volume_seed`). Batch these
edits before a measurement.

**Cold and warm.** The first round after a seed rebuild reads the history-only matrix filter at
157–176 ms and later rounds at 95–108 ms (every PG5 round showed this). Record a warm round.

### Recipe A: one scenario's statements and the slow one's plan

A script, not a test: start the test server, clone the full-volume seed, run the chosen scenarios
twice (the first warms), time each statement and `EXPLAIN` the slowest. Scenario names are those of
`tests/volume_baseline.py` (`_read_scenarios`, `_matrix_scenarios`, `_query_scenarios`).

```python
"""Usage: .venv/bin/python probe.py "change_set:objects: seek by name" [...]   (from backend/)"""
import sys, tempfile, time
from pathlib import Path
sys.path[:0] = ["tests", "."]
import postgres_server, volume_baseline as vb
from sqlalchemy import event
from volume_fixture import WORKSPACE, scaled_shape, volume_app

wanted = sys.argv[1:]
started = postgres_server.start()
try:
    with tempfile.TemporaryDirectory() as d, volume_app(Path(d), scaled_shape(1.0)) as (client, dataset):
        from app.db import get_engine
        engine, log = get_engine(), []
        event.listen(engine, "before_cursor_execute", lambda c, *a: c.info.__setitem__("t", time.perf_counter()))
        event.listen(engine, "after_cursor_execute",
                     lambda c, cur, st, p, *a: log.append((time.perf_counter() - c.info.get("t", time.perf_counter()), st, p)))
        for context in ("live", "change_set", "history"):
            calls = [(s, lambda b=b: client.post(f"/api/v1/workspaces/{WORKSPACE}/queries/objects", json=b))
                     for s, b in vb._query_scenarios(context, dataset)]
            calls += [(s, lambda p=p, q=q: client.get(p, params=q))
                      for s, p, q in vb._read_scenarios(engine, context, dataset) + vb._matrix_scenarios(client, context, dataset)]
            for scenario, call in calls:
                if not any(w in f"{context}:{scenario}" for w in wanted):
                    continue
                call(); log.clear(); call()
                took, statement, params = max(log, key=lambda x: x[0])
                print(f"== {context}: {scenario}: {[round(x[0] * 1000, 1) for x in log]} ms")
                with engine.connect() as c, c.connection.dbapi_connection.cursor() as cur:
                    cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + statement, params)
                    print(statement, params, *(row[0] for row in cur.fetchall()), sep="\n")
finally:
    if started:
        postgres_server.stop()
```

### Recipe B: a test's slow statements, with statistics off (deterministic worst case)

A pytest plugin loaded with `PYTHONPATH=<dir> .venv/bin/python -m pytest -s -p stmt_profile <test>`.
It sums time per statement shape, `EXPLAIN`s the first instance over 0.3 s, and with `STALE=1` turns
autovacuum off on the test's databases, so rows written during the test are planned without
statistics every time (the harness refuses an unclassified test module, so it must be a plugin).

```python
import os, re, time
from collections import defaultdict
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

TOTAL, COUNT, WORST, PLANS = defaultdict(float), defaultdict(int), {}, {}

@pytest.fixture(autouse=True, scope="session")
def _profile():
    done = set()
    def connect(dbapi, record):
        with dbapi.cursor() as cur:
            cur.execute("SELECT current_database(), to_regclass('snapshot_attribute_values') IS NOT NULL")
            name, ready = cur.fetchone()
            if ready and name not in done:
                done.add(name)
                for table in ("snapshot_attribute_values", "change_set_base_objects", "change_set_objects"):
                    cur.execute(f"ALTER TABLE {table} SET (autovacuum_enabled = false)")
        dbapi.commit()
    def before(conn, cursor, statement, params, context, many):
        conn.info["t0"] = time.perf_counter()
    def after(conn, cursor, statement, params, context, many):
        took = time.perf_counter() - conn.info.pop("t0", time.perf_counter())
        shape = re.sub(r"%\([a-z_0-9]+\)s", "?", statement)[:4000]
        TOTAL[shape] += took; COUNT[shape] += 1
        if took > WORST.get(shape, (0,))[0]:
            WORST[shape] = (took, statement)
        if took > 0.3 and shape not in PLANS:
            with conn.connection.dbapi_connection.cursor() as cur:
                cur.execute("EXPLAIN (ANALYZE) " + statement, params)
                PLANS[shape] = [row[0] for row in cur.fetchall()]
    if os.environ.get("STALE"):
        event.listen(Engine, "connect", connect)
    event.listen(Engine, "before_cursor_execute", before)
    event.listen(Engine, "after_cursor_execute", after)
    yield

def pytest_sessionfinish(session):
    for shape in sorted(TOTAL, key=TOTAL.get, reverse=True)[:2]:
        took, statement = WORST[shape]
        print(f"\n=== {TOTAL[shape]:.1f} s total, {COUNT[shape]} runs, worst {took * 1000:.0f} ms\n{statement[:2500]}")
        print("PLAN", *PLANS.get(shape, ["(none)"]), sep="\n")
```

## 3. Results at PG5's close

Final code, warm round, 2026-10-03, PostgreSQL 17.11, Python 3.14.8, macOS 15.7, Apple M1 Pro (the
user's working laptop). Median of 5 runs · statements · ORM rows. Full volume as in §1.

| Request | Live | Change set | History |
| --- | --- | --- | --- |
| objects: first page | 3.9 ms · 5 · 64 | 30.3 ms · 6 · 4 | 4.0 ms · 5 · 3 |
| objects: middle page | 4.5 ms · 6 · 65 | 55.8 ms · 7 · 4 | 4.6 ms · 6 · 3 |
| objects: last page | 4.9 ms · 6 · 64 | 35.7 ms · 7 · 4 | 4.6 ms · 6 · 3 |
| children: heavy parent, first page | 3.9 ms · 5 · 64 | 16.5 ms · 6 · 4 | 3.9 ms · 5 · 3 |
| children: heavy parent, middle page | 4.8 ms · 6 · 65 | 22.7 ms · 7 · 4 | 5.1 ms · 6 · 3 |
| children: small parent | 3.8 ms · 5 · 18 | 7.0 ms · 6 · 4 | 4.2 ms · 5 · 3 |
| relations: 1,500-relation record | 10.7 ms · 7 · 85 | 17.1 ms · 8 · 4 | 12.8 ms · 7 · 3 |
| relations: heavy parent | 38.7 ms · 7 · 85 | 60.7 ms · 8 · 4 | 55.4 ms · 7 · 3 |
| record: single read | 3.4 ms · 5 · 6 | 3.7 ms · 6 · 4 | 2.9 ms · 5 · 3 |
| objects: last page by from=end, total | 10.9 ms · 6 · 64 | 66.6 ms · 7 · 4 | 20.5 ms · 6 · 3 |
| objects: backward page from the middle | 5.4 ms · 6 · 65 | 54.5 ms · 7 · 4 | 4.7 ms · 6 · 3 |
| objects: seek by name, total | 11.8 ms · 8 · 65 | 91.3 ms · 9 · 4 | 23.4 ms · 8 · 3 |
| objects: position ¾ deep, total | 29.5 ms · 6 · 64 | 98.7 ms · 10 · 4 | 51.5 ms · 6 · 3 |
| children: heavy parent, position ¾ deep, total | 34.2 ms · 6 · 64 | 56.0 ms · 10 · 4 | 37.4 ms · 6 · 3 |
| roots: top-level page, total | 5.8 ms · 5 · 64 | 16.2 ms · 6 · 4 | 4.5 ms · 5 · 3 |
| relations: 1,500-relation record by name, total | 18.4 ms · 8 · 85 | 22.6 ms · 9 · 4 | 20.2 ms · 8 · 3 |
| relations: 1,500-relation record, search | 12.9 ms · 7 · 85 | 93.3 ms · 8 · 4 | 86.8 ms · 7 · 3 |
| relations: 1,500-relation record by rank | 15.2 ms · 7 · 85 | 22.9 ms · 8 · 4 | 17.9 ms · 7 · 3 |
| relations: 1,500-relation record by group, total | 62.6 ms · 8 · 85 | 86.8 ms · 9 · 4 | 66.3 ms · 8 · 3 |
| relations: heavy parent by rank | 58.1 ms · 7 · 85 | 96.7 ms · 8 · 4 | 61.8 ms · 7 · 3 |
| children: heavy parent by rank | **103.6 ms** · 9 · 64 | **150.4 ms** · 10 · 4 | **141.9 ms** · 9 · 3 |
| relations: heavy parent by group | 61.2 ms · 7 · 85 | 74.7 ms · 8 · 4 | 65.3 ms · 7 · 3 |
| relations: deep node by top node | 8.2 ms · 12 · 8 | 12.2 ms · 13 · 4 | 7.4 ms · 12 · 3 |
| objects: search by name, total | 12.2 ms · 6 · 33 | 15.8 ms · 7 · 4 | 12.0 ms · 6 · 3 |
| objects: search by code, total | 19.7 ms · 7 · 64 | 22.6 ms · 8 · 4 | 17.5 ms · 7 · 3 |
| objects: common search, total | 76.1 ms · 7 · 64 | **210.5 ms** · 8 · 4 | **103.6 ms** · 7 · 3 |
| objects: two-character search, total | 53.8 ms · 6 · 64 | **154.4 ms** · 7 · 4 | 51.5 ms · 6 · 3 |
| record: deep node | 3.9 ms · 11 · 6 | 7.6 ms · 12 · 4 | 5.2 ms · 11 · 3 |
| lookup: first page, every type | 5.3 ms · 8 · 84 | 49.2 ms · 9 · 4 | 40.1 ms · 8 · 3 |
| lookup: search by name, total | 12.1 ms · 5 · 33 | 10.9 ms · 6 · 4 | 8.4 ms · 5 · 3 |
| lookup: two types, first page | 23.6 ms · 4 · 64 | 32.2 ms · 5 · 4 | 28.3 ms · 4 · 3 |
| matrix: first page, 20 columns, total | 47.8 ms · 12 · 45 | 54.4 ms · 13 · 5 | 30.2 ms · 12 · 4 |
| matrix: position ¾ deep, total | 55.4 ms · 12 · 45 | 57.9 ms · 16 · 5 | 35.5 ms · 12 · 4 |
| matrix: inactive in 10 columns, jump, total | 96.2 ms · 14 · 34 | **136.0 ms** · 18 · 5 | 74.3 ms · 14 · 4 |
| matrix: none in 3 columns, jump, total | 46.6 ms · 14 · 27 | 66.6 ms · 18 · 5 | 35.9 ms · 14 · 4 |
| matrix: history only in 20 columns | **108.0 ms** · 13 · 44 | 96.6 ms · 11 · 5 | 41.6 ms · 11 · 4 |
| matrix incoming: first page, total | 48.4 ms · 12 · 45 | 56.6 ms · 13 · 5 | 31.1 ms · 12 · 4 |
| matrix incoming: one in 1 column, jump, total | 73.1 ms · 14 · 25 | **154.2 ms** · 18 · 5 | 52.9 ms · 14 · 4 |
| parent candidates: 20,000-descendant record, total | 17.7 ms · 6 · 25 | 13.8 ms · 8 · 4 | — |
| parent candidates: search, total | 17.4 ms · 5 · 14 | 25.2 ms · 7 · 4 | — |
| parent candidates: deep node, two types, total | 34.4 ms · 6 · 25 | 15.1 ms · 8 · 4 | — |
| parent candidates: deep node, position ¾ deep | 37.1 ms · 6 · 25 | 29.3 ms · 11 · 4 | — |
| query: one-hop criterion, total | 12.3 ms · 6 · 64 | 43.9 ms · 8 · 5 | 14.1 ms · 7 · 4 |
| query: inverted hop, first page | 6.9 ms · 5 · 64 | 35.9 ms · 7 · 5 | 6.1 ms · 6 · 4 |
| query: ancestor criterion, total | 8.8 ms · 6 · 64 | 68.6 ms · 8 · 5 | 9.5 ms · 7 · 4 |
| query: 20-row expansion of 1,500 citations | 13.2 ms · 8 · 66 | 16.1 ms · 9 · 5 | 11.7 ms · 8 · 4 |
| query: 20-row expansion of 20,000 children | 70.5 ms · 8 · 66 | 45.8 ms · 9 · 5 | 40.9 ms · 8 · 4 |
| write: rename one record | 4.6 ms · 14 · 8 | 11.8 ms · 32 · 10 | — |
| write: move a 20,000-descendant record | 9.9 ms · 24 · 10 | 20.2 ms · 39 · 11 | — |
| object changes: first page | — | 33.2 ms · 5 · 3 | — |
| object changes: last page by from=end, total | — | 70.9 ms · 7 · 3 | — |
| object changes: backward page from the middle | — | 44.3 ms · 7 · 3 | — |
| object changes: position ¾ deep, total | — | 90.3 ms · 7 · 3 | — |
| object changes: kind filter (removed), total | — | 63.4 ms · 7 · 3 | — |
| relation changes: first page | — | 28.9 ms · 6 · 3 | — |
| relation changes: last page by from=end, total | — | 54.0 ms · 7 · 3 | — |
| relation changes: backward page from the middle | — | 31.5 ms · 7 · 3 | — |
| relation changes: position ¾ deep, total | — | 59.9 ms · 7 · 3 | — |
| relation changes: kind filter (removed), total | — | 51.8 ms · 7 · 3 | — |
| relation changes: containment edges left out, total | — | 12.2 ms · 7 · 3 | — |
| write: move a container of ~2,500 cells (D29, known) | 15,402.9 ms · 37721 · 170,707 | 8,235.6 ms · 110 · 11 | — |

**11 of the 154 reads are over 100 ms** (18 before PG5 on PostgreSQL), plus the D29 container move.
Restructuring near its 500-record limit (scale 0.024, measured mid-PG5, before the name indexes
and the final read-path edits, and not measured again): plan 62.5 ms · 10 statements, preview with
dry run 4.1 s · 13,425 statements for 479 records. Its statement budget (`test_restructuring_volume`)
passed on the final code. Validate and publish at 2 % volume: within their 10 s and 20 s limits with the name indexes.

**Batch budgets** (`pytest -m budget`, 2 min 39 s): 1,000 upserts in 0.8 s live and in a change set
(0.06 statements per item; B1 on SQLite 3.3 s and 6.8 s, 20.5 and 34.0 per item); 10,000 atomic
creates 5.4 s live and 17.8 s in a change set (0.01–0.02 per item; SQLite 29 s and 55 s); 100,000
background creates 52 s live (1,918 items/s) and 64 s in a change set (1,572 items/s; SQLite 231 s and
663 s), with live writes beside the job served in at most 0.35 s (median 0.12 s live, 0.01 s beside the
change-set job). PG-D17's "under a minute" holds live and is missed by 4 s in a change set.

## 4. What PG5 changed, and why

Each change was decided from a plan except where noted. "Before" is PostgreSQL before PG5 (warm).

1. **Relation expansion reads the anchor's relations first** (`expansion_rows`,
   `engine/reads/relation_queries.py`). The 20-row expansion of a group's 20,000 children took
   415 ms: PostgreSQL estimated ~3,700 relations for `(relation_type_key, from_object_id)` (it assumes
   the two columns independent) and, to produce 20 rows in name order, walked `ix_objects_name` over
   157,191 records probing each, because the group's items sort late. The anchor's relations are now a
   `MATERIALIZED` CTE joined to their records by ID and sorted top-20: **70 ms** (20,000 record lookups
   by ID at ~2.5 µs each; SQLite 44 ms).
2. **SQLite-era planner constructs removed** (`common/sql.py` `CrossJoin`; `unindexed`, `found`, the
   `CASE` wrappers and `MATERIALIZED` in `matrix_cells.py`, `relation_matrix.py`, `change_lists.py`,
   `snapshot_reads.py`, `matrix_states.py`; `_rows_of`; `id_rows` as a `VALUES` list; the model query's
   `narrow` flag). They steered SQLite's planner; on PostgreSQL removing them was faster or equal in
   two full rounds compared against two rounds with them (the ancestor query 47 → 7 ms live and 141 →
   69 ms in a change set, change-set object pages 112–154 → 55–99 ms, the history heavy parent by
   group 254 → 65 ms). This was decided by timing rounds, not plans. One construct, the change set's
   "replaced" rows, is discussed in §5 E6.
3. **The matrix state filter sends its row list once per statement** (`matrix_states.row_list` and
   `listed`). The stored filter's matching row IDs (5,685 in the one-in-one-column scenario) were bound
   once per arm, three times in a change set's total; the client side of shipping and parsing them was
   25 ms of a 49 ms statement. One shared `matrix_row_ids` parameter: change-set filters 210 → 136–154 ms.
4. **Name search through trigram indexes, candidates read first** (revision `20261003_01`;
   `models/search_index.py`; `object_query.search_candidates`, `live_search_candidates`,
   `snapshot_reads.snapshot_search_candidates`, `bounded_match`). S8 had decided names need no index
   because walking the (type, name) index cost ~20 ms per 100,000 records on SQLite; on PostgreSQL it
   costs ~90 ms, twice in a change set's page and total. Now: GIN trigram indexes on `name` of
   `objects`, `publication_objects`, `change_set_base_objects` and `change_set_objects`; the per-type
   list (`build_object_query`, `build_snapshot_object_query`, given the session) first reads up to 1,001
   candidate record IDs from the name and value indexes (`UNION ALL … LIMIT`, so a common phrase stops
   early); with at most 1,000 the statements take `id = ANY(:search_ids) AND (exact match)`, which
   PostgreSQL pushes into every arm of a change set's projection; with more, or a phrase under three
   characters, the statement matches every row as before, the value side still bounded inside it.
   The `ILIKE` decides in every path, so results are unchanged (`test_search_index` compares the three
   paths). Specific phrases 50–226 ms → **11–23 ms** in every context; lookups 52–55 → 8–12 ms. One
   statement more per search, at every size.
5. **`ix_snapshot_attribute_values_owner_key` dropped** (same revision). Its columns are the prefix
   of `ix_snapshot_attribute_values_owner_key_text`. On rows without statistics (a base just captured)
   the planner chose it to find one record's value (estimating 1 row) and filtered ~3,230 rows per
   lookup: `test_change_set_position_reads[type-vol-rank-currentLive]` took 99 s in the worst case
   (recipe B). Without it: 51 s worst case; 9–66 s in normal runs depending on when autovacuum
   analyzes (see E6).
6. **Batch budgets restated** (`test_batch_volume`, `test_background_volume`): at most 0.1 statements
   per item, a re-sent batch under its write's statement count; the SQLite writer-lock refusals the
   background test counted cannot happen on PostgreSQL and were removed.

## 5. Open exceptions: the post-1.0 fixes

Ordered by suggested priority. Figures are §3's (warm) unless noted; SQLite figures are the 0.8
plan's (S7, S8, A2 tables) for the same fixture.

### E1. Change-set matrix state filters: 136 ms and 154 ms

`matrix: inactive in 10 columns` (live 96, change set 136, history 74; SQLite change set 73) and
`matrix incoming: one in 1 column` (live 73, change set 154, history 53; SQLite 54).
**Cause (plan):** `stored_row_filter` (`engine/indexes/matrix_states.py`) returns the matching row IDs
to Python; `_state_filter` (`management/projections/relation_matrix.py`) then filters every paging
statement by them: the page, its total and the position, each over the change set's projection arms.
18 statements; the 5–8 that carry the list cost 6–27 ms each. In one total statement the server spent
14.7 ms (each arm an index-only scan probing 5,685 IDs, ~7 ms) and the client ~10 ms more to send and
parse the array, once per statement since PG5.
**Fix options:** (a) compute the filter once per request on the server and reuse it: the stored-state
compound as a CTE shared by the page and total in fewer statements; (b) a temporary table of the IDs
for the request (check first whether the read's REPEATABLE READ snapshot transaction is read-only,
which forbids `CREATE TEMP TABLE`); (c) pass the stored-state compound as a subquery when its result
is large (recomputes it per statement, ~3 ms per selected column). **Effort:** 0.5–1 day with tests.
**Verify:** recipe A on both scenarios; `test_relation_matrix_volume`.

### E2. Change-set searches that match nearly every record: 154 ms and 211 ms

`objects: common search, total` ("Item", every item's name and code: live 76, change set 211, history
104; SQLite ~0.4 s, S8 decision D25) and `objects: two-character search, total` (live 54, change set
154, history 52).
**Cause:** the result is ~100,000 records and the request asks for an exact total. No index can make
"every record matches" cheap: both statements (page and total) walk the base's type index and evaluate
the match on each of 100,000 rows minus the overlay (~0.6 µs per row). A two-character phrase has no
trigram, so no index applies at all. The candidate read (§4.4) adds ~15–27 ms to a common phrase: it
reads 1,001 candidates before falling back to the walk.
**Fix options:** a product decision first: cap the total for search ("10,000+") or make it optional,
then (a) stop counting past the cap, (b) skip the candidate read when the trigram index's own
estimate (`EXPLAIN` row estimate, or `pg_trgm`'s similarity statistics) says the phrase is common.
**Effort:** the decision; then about half a day. **Verify:** recipe A, `test_search_index`.

### E3. Sort by an attribute under the 20,000-child parent: 104, 150 and 142 ms (live closed by 0.9 C3a)

`children: heavy parent by rank`. Known since 0.8 S4R1 and decided as **D26: precomputed sort keys,
after 0.9** (an indexed sort value per record). Unchanged by PG5. **Live: closed by 0.9 C3a
(2026-10-04), 9.9 ms**, through value-order indexes and a list read in two parts (0.9 D46). The change
set (150 ms) and history (142 ms) contexts remained; 0.9 D47 made them a task of C6. **History: 0.9
C6a (2026-10-05)** reads a publication's attribute sort in two parts through partial value-order
indexes (`20261005_03`, C-D67); a consumer list pinned to the publication reads the first page by rank
in 14.5 ms and the heavy parent's items in 15.0 ms. The management `children: heavy parent by rank`
history row was not re-measured (the full table was not run). **The change-set context stays** (its
base-and-overlay union cannot be walked in one index's order; TODO). What 0.8 D26's
stored key would still add: attributes with few distinct values (a whole group of equal values sorted
by name) and deep positions (113–123 ms at row 50,000 of a consumer list sorted by rank).

### E4. Live history-only matrix filter: 108 ms warm, 157–176 ms cold

`matrix: history only in 20 columns` (change set 97, history 42; SQLite 72 live).
**Cause (plan):** A3b's stored-state filter reads ~10,000 state rows per selected column and combines
held and holding rows with `EXCEPT` per column (`HashSetOp Except`, ~3 ms per column), so 20 columns
cost ~60 ms in one statement before paging. SQLite merged the same compounds in index order.
**Fix options:** (a) a state index or materialised "history only" flag per (row, column) so the filter
reads matches, not every state; (b) one anti-join over all selected columns instead of 20 compounds.
**Effort:** about half a day for (b); (a) touches the state build and its flush hooks (ADR-033).

### E5. Change-set seek and position reads near the limit: 91 ms and 99 ms

`objects: seek by name, total` and `objects: position ¾ deep, total` (SQLite 46 and 56 ms). Within
budget at PG5's close but with no margin; a noisy run crosses 100 ms.
**Cause (plan):** four statements of 17–31 ms, most of it counting ~100,000 base rows minus the
overlay for the total and the position (`Parallel Seq Scan` on `publication_objects` for the type).
**Fix options:** the position's count through an index-only scan (needs a vacuumed visibility map in
production, see E6), or the overlay correction computed from the change set's rows only (S4R6 does
this for some reads; extend it). **Effort:** half a day to a day.

### E6. Plans on freshly written rows (statistics not yet gathered)

Not a budget row but the cause of the slowest test and a production risk: right after a change set is
started from current live data (the base captured as thousands of new `change_set_base_objects` and
`snapshot_attribute_values` rows), PostgreSQL has no statistics for the new owner until autovacuum's
`ANALYZE` runs (seconds to a minute later). It then estimates the base's rows as one, and:
- puts the base's rows on the outside of the "replaced" part's semi-join (`snapshot_reads`,
  `object_projection`, `part == "replaced"`), evaluating a position read's sort terms on every base
  row before joining to the few rows the change set replaces;
- looks up a record's value through `ix_snapshot_attribute_values_owner_key_text` (owner, attribute,
  …, record) instead of the unique (owner, record, attribute) key: ~0.12 ms per lookup instead of a
  direct hit (it used the dropped `owner_key` index before, 0.25 ms).

`test_change_set_position_reads[type-vol-rank-currentLive]` shows it: 9–66 s in normal runs depending
on autovacuum's timing, **51 s with statistics off** (recipe B; 99 s before the index drop).
**Tried in PG5 and not kept:**
- *The base's terms kept off their indexes* (`CASE` wrappers, the SQLite-era `_off_index`): 11 s in
  that test, but at full volume change-set seek 93 → 139 ms, position 96 → 139 ms, from=end 64 →
  118 ms, the ancestor query 70 → 130 ms, because the IDs were then looked up in every owner's rows.
- *The change set's IDs as an array* (`object_id = ANY(ARRAY(SELECT …))`): 22 s worst case in that
  test, since the base's (owner, record) key is probed with the IDs whatever the statistics; but the
  planner cannot estimate an array's size (it assumes 4 rows) and joined 1,492 replaced rows to a
  1,500-row hop by nested loop: the change-set one-hop query 44 → 138 ms.
**Fix options:** (a) `ANALYZE` the captured tables at the end of a capture (measure its cost at full
volume first; the capture already writes every row); (b) extended statistics or a planner hint
equivalent for the replaced part, e.g. the array form plus an explicit join order only for the
replaced part; (c) an index exactly matching the value lookup, so no statistics are needed to choose
it. **Effort:** half a day to a day. **Verify:** recipe B on the test above and recipe A on the
change-set seek, position, from=end and one-hop scenarios: both must hold together.

### E7. PG-D17 in a change set: 64 s for 100,000 items (target under 60 s)

Live meets it (52 s). The change set also takes 3.3× live for 10,000 atomic creates (17.8 s against
5.4 s). **Cause:** not investigated in PG5. Start with recipe A's statement timing on one chunk of
`submit_inline_batch` in a change set (`test_batch_statements` builds one at two sizes).

### E8. Dated totals and change-set dated pages (0.9 T1)

Measured at T1 (2026-10-03, `--only-dated --scale 1`), with three quarters of 100,000 items applying
on the date:
- `objects: dated, total` takes 161 ms in a change set.
- `query: dated ancestor criterion, total` takes 111 ms live, 148 ms in a change set and 140 ms in
  history.

Dated first pages are 5 ms live and 82–89 ms in a change set. **Cause:** not investigated. The
totals count about 75,000 rows through the period check, the shape of E2. Fixes as for E2: no exact
total over large result sets, or a count computed separately.

### Known and unchanged: D29 and the restructuring dry run

Moving a container of ~2,500 matrix cells takes 15.4 s live and 8.2 s in a change set (0.8 B2, D29,
a known exception). The restructuring preview's dry run for 479 records takes 4.1 s on PostgreSQL
(2.8 s on SQLite, 0.8 C2; D44 accepted it as a preview cost that grows with the records). Neither was
touched by PG5.

## 6. Other findings for the next person

- **Eight older tests were stale since H4c** and failed on HEAD before PG5 (H4c's decisions: empty
  text is no value; a change set holds an ancestor-scope breach for validation to report and publishing
  to refuse, instead of refusing the write). PG5 moved them to the decided behaviour:
  `test_translations` (2), `test_type_changes` (2 cases, 3 runs), `test_mapping_replacement`,
  `test_relation_matrix_writes`, `test_graph_validation_scale`. Their writes go through
  `ChangeSetTestClient`, which adds a change set to every write without saying so in the test.
- **`VACUUM ANALYZE` before measuring changed nothing** that matters (seek 93 → 76 ms in one probe,
  the rest equal): the visibility map is not the cause of the counts' cost on the fixture.
- **The full backend suite at PG5** (before the last read-path edits): 1,399 passed, the 8 stale
  tests failed, 4 min 1 s. After the edits: the read, search, migration and budget modules (§2) passed;
  the full suite was not rerun (user's decision).

## 7. Consumer API reads (0.9, collected in C8)

Every consumer read was measured at full volume by the package that built it, with
`volume_baseline.py --only-consumer --scale 1 --repeat 3` (warm median · statements · ORM rows).
Base 0.9 C8 (2026-10-05) collects the latest figure of each here and does not re-measure (C-D74):
nothing on a consumer read's path changed after C6a's run. The `volume` group holds the statement
counts at two sizes (`test_consumer_list_volume`, `test_consumer_xref_volume`).

| Read | Live | Pinned to a publication | Measured in |
| --- | --- | --- | --- |
| List: first page by rank | 10.5 ms · 11 · 24 | 14.5 ms · 13 · 5 | C6a |
| List: next cursor page | 12.2 ms · 13 · 25 | 18.3 ms · 15 · 5 | C6a |
| List: position jump to the middle | **113.8 ms** · 11 · 24 | **117.4 ms** · 13 · 5 | C6a |
| List: 20,000 items under a parent | 9.9 ms · 9 · 24 | 15.0 ms · 11 · 5 | C6a |
| List: ancestor filter with `includeTotal` | 95.9 ms · 13 · 24 | **120.2 ms** · 15 · 5 | C6a |
| XREF: an item's code, another case | 28.7 ms · 8 · 3 | 41.5 ms · 10 · 5 | C6a |
| XREF: a group's code promoted to its 1,500 citing items | 48.5 ms · 9 · 3 | 66.9 ms · 11 · 5 | C6a |
| XREF: 4-character contains | 49.4 ms · 7 · 3 | 57.5 ms · 9 · 5 | C6a |
| XREF: `expect=one` | 12.8 ms · 7 · 3 | 18.8 ms · 9 · 5 | C6a |
| XREF: within the heavy group | 63.3 ms · 10 · 3 | 79.6 ms · 12 · 5 | C6a |
| XREF: `scoresFrom` on the group | 52.2 ms · 9 · 3 | 73.5 ms · 11 · 5 | C6a |
| XREF: a term in every item, `QUERY_TOO_BROAD` (a refusal) | **132.5 ms** · 3 · 3 | **161.9 ms** · 5 · 5 | C6a |
| Batch resolve: 1,000 identifiers (budget 1 s) | 816.5 ms · 7 · 3 | — | C14 |
| Batch resolve: 1,000 items over three parameter sets (budget 1 s) | 451.2 ms · 18 · 3 | — | C14 |
| List: dated (`asOf`), first page with `includeTotal` | **192.3 ms** · 12 · 24 | **201.4 ms** · 14 · 5 | C16 |
| List: dated, position jump to the middle | **204.1 ms** · 11 · 24 | **231.9 ms** · 13 · 5 | C16 |
| XREF: a group's code, dated (10 a page) | 72.3 ms · 9 · 3 | 85.8 ms · 11 · 5 | C16 |
| Batch resolve: 1,000 identifiers, dated | **2,224.9 ms** · 10 · 3 | — | C16 |

Batch resolve shapes outside the budget, recorded in C14: a tenth of the identifiers a group code
1,500 items cite (1.7 s), three sets regardless of fit (4.0 s), 1,000 contains-only terms (15.4 s)
and 1,000 items each with its own parameter value (38.4 s, 4,002 statements: one group per value).
C6a's run also measured batch resolve, live only, and did not record it separately.

**Over 100 ms, live or pinned:**
- **The position jump to the middle** (113.8 and 117.4 ms): D46's deep-position cost, the shape of
  [E3](#e3-sort-by-an-attribute-under-the-20000-child-parent-104-150-and-142-ms-live-closed-by-09-c3a);
  0.8 D26's stored sort key is the fix after 1.0.
- **The ancestor filter with a total, pinned** (120.2 ms; 95.9 ms live): it counts 20,000 matches
  over the publication's rows. Not investigated; the shape of E2 and E8 (an exact total over a large
  result).
- **The dated lists** (192–232 ms, C16): they count or skip 75,000 dated records, twice the undated
  read; the shape of [E8](#e8-dated-totals-and-change-set-dated-pages-0-9-t1). The C16 predicate is
  an AND of `NOT EXISTS` so it plans as anti-joins; an OR over the types took 1.3–1.8 s.
- **The dated batch** (2.2 s, C16): identifiers not effective on the date lose their exact match, so
  exact-first (C-D52) reads their contains matches; C14's "parameters filtering items out" shape.
- **A term in every item** (132.5 and 161.9 ms): the cost of refusing it, which joins all 100,000
  items before the 10,000-match limit refuses (C-D37). It answers `400`, not a page.

### Consumer events (0.9 C10)

Measured once at full volume (110,254 objects; 2026-10-06) with
`volume_baseline.py --only-events --scale 1 --repeat 3` (the seed built once, 328 s; warm median ·
statements · ORM rows). A release gives the volume consumer API one event over groups and items,
every change, no watch. Derivation runs once per step, since it consumes its entries; the reads are
timed three times. `test_consumer_event_volume` holds the statement counts at two sizes.

| Step | Live |
| --- | --- |
| Derive a page of 500 live creations | 42.2 ms · 6 · 502 |
| Derive the rename of the heavy group: 20,001 objects told (C-D82's fan-out) | 724.0 ms · 5 · 2 |
| Events read: first page of 100, full payload | 25.5 ms · 13 · 103 |
| Events read: first page of 100, identity | 11.5 ms · 9 · 103 |
| Events read: narrowed by the `within` ancestor parameter, full payload | 54.5 ms · 16 · 103 |

Derivation is not a request: it runs on the deriver's thread a moment after the write commits, and the
write never waits for it. Its 502 rows are the page's 500 entries read to plan it (C10's "decide"
step); the fan-out itself stays in PostgreSQL, so the rename costs the same 5 statements at every
size. The reads are within the 100 ms budget.

### Webhook delivery (0.9 C13)

Measured once at full volume (110,254 objects; 2026-10-06) with the same run as the events above
(`volume_baseline.py --only-events --scale 1 --repeat 3`; the seed rebuilt after C12's migration,
332 s). The heavy group's rename (20,001 events at one position) is delivered to a receiver on
`localhost` that answers `200` at once, so the times are the engine's, with one local HTTP exchange
per batch. A batch is the dispatcher's claim, its step and the acknowledgement (warm median of three
batches · statements · ORM rows). `test_consumer_event_volume` holds the statements of the claim, a
batch of each payload and the coalesced round at two sizes (C-D113). Since 0.9 C17 the batches
are subscriptions batching up to 100 (a subscription sends one event per request by default), and
the coalesced round, retired with its mode, is replaced by a batch of 100 `full` events as
CloudEvents, held for its statements at two sizes; it was not measured at full volume.

| Step | Live | Budget (C-D113) |
| --- | --- | --- |
| The claim, 100 subscriptions caught up (every process, once a second) | 4.9 ms · 1 · 0 | 10 ms |
| A batch of 100 events, `full` | 61.1 ms · 24 · 105 | 100 ms |
| A batch of 100 events, `identity` | 22.4 ms · 20 · 105 | — |
| The whole rename to one subscription, `full` (201 batches) | 5,755 ms · 4,825 · 20,586 | 30 s |
| The whole rename to one subscription, `identity` (201 batches) | 4,033 ms · 4,021 · 20,586 | — |
| A coalesced round over the 20,001 events (retired in C17) | 34.6 ms · 15 · 5 | — |

Every step is within its budget: one subscription takes about 3,500 `full` events a second (about
5,000 with `identity`). A batch's statements do not grow with the data (24 and 20 at every size); the
whole delivery's are its batches'. A `full` batch is the pull feed's `full` page (19.9 ms in the same
run) plus the claim, the pending batch's commit, the POST and the acknowledgement. A slow receiver
adds its own time to each batch: subscriptions are delivered four at a time per process (C-D106), so
one slow receiver delays only its own.

## 8. Exports (0.9 J1)

The whole live workspace of the volume fixture at full size (257,758 records of six types and
316,616 relationships, `withinScope`), exported once per format on 2026-10-07 with
`volume_baseline.py --only-exports --scale 1` (the seed rebuilt after J1's migration, 326 s). Each is
one job run by the export worker in the measuring thread, from the claim to the completed job
(time · statements · ORM rows). `test_export_volume` holds the statements at two sizes: the same at
both, except the progress checks, two statements per 10,000 rows written.

| Format | File | Time | Budget (D56) |
| --- | --- | --- | --- |
| JSON Lines | 209.6 MB | 23.1 s · 145 · 4 | 60 s |
| CSV | 103.1 MB | 24.4 s · 36 · 4 | 60 s |
| XLSX | 71.6 MB | 31.5 s · 144 · 4 | 60 s |

Every format is within its budget. The first XLSX writer (openpyxl's write-only workbook, one cell
object each) took 72.8 s; the user chose to make it faster within J1, and the workbook is now written
as sheet XML directly (`engine/jobs/xlsx.py`), its values extracted as text by PostgreSQL as for CSV.
The ORM loads the job only, never a record; the records pass through Python only as the lines and
rows streamed to the file. The snapshot transaction is held for the export's whole time. Memory was
not measured with an instrument; nothing holds the set (server-side cursors, `COPY`, a streamed ZIP
entry).


## 9. Imports (0.9 J3)

Two XLSX files of items (one upsert per row, keyed by a unique code, its group matched by name),
imported live into the volume fixture at the 0.005 shape the batch budgets use, measured once on
2026-10-07 with `pytest -m budget tests/test_import_budget.py` (2 min 8 s with writing the files).
A test worker runs each job from its first claim to its end, binding included.

| Run | Rows (= items) | Binding | In all | Budget (D88) |
| --- | --- | --- | --- | --- |
| Preview | 10,000 | 2.5 s | 10.6 s | 30 s |
| Execution | 100,000 | 26.3 s | 110.7 s | 2 min |

Both are within their budgets; the execution's margin is 8 %. Binding 100,000 rows takes 26 s
(openpyxl's read-only reader and the conversions in Python, the matching in PostgreSQL); the rest,
84 s, is the batch path's chunks with J2a's unique triggers (the 100,000-item batch took 52 s at
PG5). The preview's own step, about 8 s for 10,000 items, holds the workspace's write lock that long.
`test_import_volume` holds the statements at two sizes: binding the same at both, and the preview's
step growing only by the batch path's statements paged by about 1,000 rows (about ten per 1,000
items) and its cancel checks, with no record loaded into the ORM.

Found while measuring (not changed): an `ensureRelation` item whose target already holds many
relationships of the type loads those relationships into the ORM (1,000 rows for a group cited by
1,000 items, seen in `test_import_volume` when a preview followed an execution citing the same
groups). It is the batch path's relation lookup, shared by batches and imports; a candidate for the
post-1.0 fixes if a budget needs it.
