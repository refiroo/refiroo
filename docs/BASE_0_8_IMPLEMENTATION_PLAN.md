# Base 0.8 implementation plan

**Status:** In progress; plan drafted 2026-09-25. Track S (scalable browsing, S1–S8) and Track W
(W1–W6, ADR-031 terminology and capability boundaries) are delivered (2026-09-26). Milestone A
(relation matrix) and Milestone B (hierarchy editor) from the
[roadmap](ROADMAP.md#product-release-08--relation-matrix-and-hierarchy-editor) are broken into work
packages A1–A5 and B1–B4; P2 is scheduled after W2 (D20); R1 owns build acceptance. A1 is delivered
(2026-09-27) with D8 and D9 accepted. A2, A3 and A3b are delivered (2026-09-27) with D10–D13
accepted; A3b's stored cell states closed A2's budget exception for the row state filter. A4 and A5
are delivered (2026-09-28), and A6 (snapshot table index drift, found in A2) with D28 accepted
(2026-09-28), which completes Milestone A. B1 and B2 are delivered (2026-09-28); D14 is accepted (2026-09-28),
D30 decides one of A6's two open measurements and B2 decides the other (D29, a known budget exception);
see the [summary](#decisions-summary).

**Target:** Product 0.8.0. Track S does not change the schema language. Milestones A and B add
schema language 0.7 (`relationMatrix` and `tree` views); the starter model becomes content release
0.8.0 on schema 0.7.

**Depends on:** Product 0.7.0 released.

## Why Track S comes first

A volume probe on 2026-09-25 put 1000 master values under one codelist and 3 under another, in an
isolated database through the real API and browser. The findings, confirmed in code:

- **Live API paging is fast and bounded.** 51 pages of 20 at 2–4 ms each on SQLite.
- **Tables work but do not scale as a reading experience.** Previous/Next only, `Page N` without a
  total, and every visited page appends a ~250-character cursor to the URL (about 12 KB by page 51).
  Record panels have no sort control and list in creation order.
- **The sidebar tree is wrong at volume, not only slow.** It loads the first 30 records of every
  object type in the application, across all parents, and derives the tree from whatever is loaded.
  The first codelist showed 30 of its 1000 values with no hint of more; the second showed none of its
  3. A record whose parent is not loaded yet is drawn as a top-level item. Seeing everything takes
  about 33 clicks of **Load more objects**.
- **Draft and history reads load whole sets into memory.** `effective_draft_membership` loads every
  object and relation of the draft's workspace; 32 call sites use it, including a single-record read,
  every object page and every relation page. Revision object lists load all revision objects of the
  type, and revision relation pages load every relation and object of the revision, before filtering
  and paging in Python.
- **Relations can be paged but not searched or sorted.** Live relation pages come in creation order
  only, which does not help with 1500 relations on one record.

Object types, hierarchy depth and relation volume come from the model and its data, not from code.
Nothing guarantees a first level of 7 records rather than 7000, so every collection surface must stay
bounded for any model. [ADR-030](DECISIONS.md#adr-030--cursor-and-position-paging-with-continuous-scrolling)
records the chosen approach.

## Product outcome

A steward scrolls any collection continuously in both directions: collection lenses, record panels,
relation panels, the mapping lens, pickers and every sidebar tree branch. Rows ahead are fetched
before they are needed. A small marker appears only when the user actually waits, and quiet markers
show the start and end of the list. Memory and DOM size stay flat however far the user scrolls. A
list shows its total and a proportional scrollbar; clicking or dragging it, or entering a page number,
jumps there. The user can also jump to the start, the end or a value (for example "go to M"), and a
copied URL reopens at the same place. This holds in live, draft and history contexts for any model.

## Principles and exclusions

1. Each request pages with a cursor or a position, never both. The UI scrolls with cursors and
   jumps with positions (ADR-030).
2. Every addition is generic: no branch on application, object-type or relation-type keys.
3. Draft and history reads return the same results as today; only where the work happens changes.
4. Additive API changes only. Existing clients that pass `cursor` and read `nextCursor` keep working.
5. A read's cost depends on the page size and the hierarchy depth, not on the size of the dataset.

Excluded: the typed `tree` view contract, reparenting and child creation of Milestone B; translation
coverage of Milestone A; bulk and export APIs (0.9).

## Work packages — Track S

Order: S1 → S2 → S3, with S4 alongside S3 → S5 → S6 → S7. S2b (bounded draft writes) follows S2 and
blocks nothing in the read path. Each package states its own focused
checks under [AGENTS.md](../AGENTS.md#work-package-validation); S7 owns composed acceptance for the
track.

#### S1: Volume fixture and baseline

**Scope:**

1. Build a generated test model with its own application, object-type and relation keys, so no
   check relies on the starter model. It includes a root type with 10,000 records, a contained type
   with 100,000 records spread unevenly across parents (one parent holds 20,000), a self-hierarchy
   at least six levels deep, a record with 1,500 relations of one type and a parent with children of
   two types.
2. Seed it through a bulk database fixture (not the HTTP API, which takes about 13 s per 1000 records)
   and create a revision and a draft on top, with draft edits scattered through the data.
3. Measure per-request time and SQL query count in live, draft and history contexts for: first,
   middle and last object pages; scoped child pages; relation pages; a single-record read; one draft
   write. Record the results in this plan.
4. Set explicit budgets from the live figures, for example that a page read's query count is constant
   and its time does not grow with dataset size beyond index cost.

**Exit:** a reproducible fixture and a recorded baseline that shows today's draft and history
reads growing with the dataset while live reads do not.

**Delivered 2026-09-25.** `backend/tests/volume_fixture.py` holds the generated model (keys
`vol-catalogue`, `vol-group`, `vol-item`, `vol-node`, `vol-*` relation types; no starter key) and
the seeded bulk writer; `backend/tests/volume_baseline.py` measures; `test_volume_baseline.py`
(marker `volume`) holds the budgets. The draft derives from revision 1, whose membership equals
live; a current-live draft reads through the same whole-membership code, so it is not measured
separately. The seeded draft passes the app's own graph validation.

_Baseline_ (full shape: 110,254 objects, 220,508 typed values, 101,754 relations, 7-level
hierarchy of 254 nodes; draft with 1,031 edits, 461 tombstones and 50 new records; seeded in 17.7 s).
Page size 20, median of 3 runs after a warm-up, in-process ASGI, SQLite 3.53.4, Python 3.14.7,
Apple silicon laptop. Each cell is time · SQL statements · ORM rows materialised. Reproduce with
`cd backend && .venv/bin/python tests/volume_baseline.py --scale 1 --repeat 3`.

| Request | Live | Draft | History |
| --- | --- | --- | --- |
| objects: first page | 20.2 ms · 5 · 79 | 3,171 ms · 8 · 214,065 | 1,312 ms · 4 · 100,003 |
| objects: middle page | 20.9 ms · 5 · 80 | 3,188 ms · 8 · 214,065 | 1,404 ms · 4 · 100,003 |
| objects: last page | 20.2 ms · 5 · 80 | 3,540 ms · 8 · 214,065 | 1,424 ms · 4 · 100,003 |
| children: 20,000-child parent, first page | 13.7 ms · 5 · 65 | 3,081 ms · 8 · 214,065 | 1,199 ms · 4 · 100,003 |
| children: 20,000-child parent, middle page | 12.5 ms · 5 · 65 | 3,121 ms · 8 · 214,065 | 1,279 ms · 4 · 100,003 |
| children: 5-child parent | 2.1 ms · 5 · 19 | 3,032 ms · 8 · 214,065 | 1,111 ms · 4 · 100,003 |
| relations: 1,500-relation record | 10.6 ms · 45 · 105 | 3,079 ms · 8 · 214,065 | 2,405 ms · 5 · 212,011 |
| relations: 20,000-child parent | 52.1 ms · 45 · 85 | 3,156 ms · 8 · 214,065 | 2,609 ms · 5 · 212,011 |
| record: single read | 2.5 ms · 5 · 7 | 2,944 ms · 8 · 214,065 | 1.8 ms · 4 · 4 |
| write: rename one record | 3.6 ms · 13 · 9 | 7,638 ms · 29 · 431,004 | — |

Findings:

- Live reads are bounded: rows track the page, not the dataset, and the statement count is fixed.
- Every draft read, including a single-record read, materialises the whole draft membership
  (objects and relations). History object pages materialise every revision object of the type;
  history relation pages every revision relation and object. A history single-record read is
  already a direct lookup.
- A draft write loads the membership twice (the write, then the response) and takes 7.6 s.
- Live relation pages issue two statements per listed row (building each related object's
  response). This is constant in dataset size but proportional to page size; S4 should batch it.

_Budgets._ Held by `test_volume_baseline.py` at two scales four times apart:

1. A request's SQL statement count does not change with dataset size.
2. A request materialises at most 6 ORM rows per row of a full 20-row page (120).
3. At full volume, a page or record read in any context stays within 100 ms median on the
   reference machine (live worst case: 52 ms), and a single-record draft write within 50 ms. Time
   is checked by rerunning `volume_baseline.py`, not in the test suite, because wall time is
   machine-dependent.

Live reads and writes meet 1 and 2 today. The draft/history read test and the draft write test are
strict expected failures; S2 removes the markers as each is met.

_D7 outcome:_ draft writes are over budget (7.6 s and 431,004 rows for one rename at full volume),
so S2 scopes a bounded follow-up slice for draft writes after the read paths move to SQL.

#### S2: Draft and history reads in the database

**Scope:**

1. Answer draft reads with a base-plus-overlay query in SQL: base rows hidden by any draft row
   (including tombstones), plus non-deleted draft rows. `services/mapping_projection.py` already
   uses this pattern for mapping reads.
2. Answer revision reads with SQL over the revision tables, keyed by revision and object type.
3. Apply search, typed filters, sort and keyset pagination in SQL through `services/pagination.py`,
   replacing `_sequence_object_rows` and `paginate_sequence` on read paths.
4. Replace whole-membership loading for single-record, attribute and relation reads with direct
   lookups.
5. Leave validation and activation on whole-graph loading; they need the whole graph by definition.
   Draft writes stay on it too unless S1 shows them over budget, in which case a bounded follow-up
   slice is scoped.
6. Add a parity test: the same query in live, draft and history returns the same rows in the same
   order when the three contexts hold the same data.

**Decision D1 — typed values for draft/history queries (accepted 2026-09-25: typed value rows).** Live values sit in a typed
`attribute_values` table; draft and revision rows store them as JSON. Two options:

- Extract typed values from JSON per dialect. No migration, but decimal comparison through floats is
  inexact, JSON extraction is not indexable, and SQLite and PostgreSQL behave differently.
- Store typed value rows for revision and draft objects, mirroring live. This needs a migration and
  more storage, but gives exact typed comparison and indexes, and lets one query builder serve all
  three contexts.

_Accepted:_ typed value rows. Attribute values must keep their declared types, and one builder
for every context removes a class of parity defects. The migration follows the AGENTS.md startup
rules: clean bootstrap, upgrade from the preceding revision, restart, interrupted migration,
lifespan and a smoke start.

**Exit:** S1 draft and history reads meet the live budget, the parity test passes, and existing
`drafts`, `workspaces`, `mapping` and `records` groups pass unchanged.

**Delivered 2026-09-25.** Migration `20260925_01` adds `snapshot_attribute_values`, a typed index of
the JSON values of revision, draft-base and draft objects keyed by owner, object and field, and
backfills it from every existing row with the value types of the owner's pinned release. A
`before_flush` hook (`services/snapshot_values.py`) rewrites an object row's index whenever the ORM
writes it, so no draft, activation or capture path can leave it behind; bulk writers call the same
helpers. The migration also adds (owner, type, name, id) and (owner, parent, type, name, id) indexes on
revision and draft-base objects, so pages read in index order. `services/snapshot_reads.py` answers
object, record, attribute, relation and draft-write-response reads with one base-plus-overlay
statement narrowed inside each arm, and `services/objects.py` builds search, typed filters and sort
for live and snapshot sources from one builder (`refine_object_query`). `_sequence_object_rows` is
gone; `paginate_sequence` remains only for model definitions and mapping previews. Validation,
activation and the draft write services still load the whole membership (item 5).

The shared keyset predicate now binds positions as typed literals, which fixes a live defect found by
the parity test (paging a boolean sort past its first page returned 500), and adds the implied
leading bound `k0 >= v0` so an index on the first key seeks to the cursor rather than scanning from
the start.

_Results_ (same machine, fixture and method as S1; `volume_baseline.py --scale 1 --repeat 3`):

| Request | Live | Draft | History |
| --- | --- | --- | --- |
| objects: first page | 20.6 ms · 5 · 79 | 3.8 ms · 5 · 4 | 2.4 ms · 4 · 3 |
| objects: middle page | 20.8 ms · 5 · 80 | 3.5 ms · 5 · 4 | 2.6 ms · 4 · 3 |
| objects: last page | 18.7 ms · 5 · 80 | 3.5 ms · 5 · 4 | 2.5 ms · 4 · 3 |
| children: 20,000-child parent, first page | 11.8 ms · 5 · 65 | 3.3 ms · 5 · 4 | 2.4 ms · 4 · 3 |
| children: 20,000-child parent, middle page | 12.9 ms · 5 · 65 | 3.5 ms · 5 · 4 | 2.6 ms · 4 · 3 |
| children: 5-child parent | 2.1 ms · 5 · 19 | 3.0 ms · 5 · 4 | 2.6 ms · 4 · 3 |
| relations: 1,500-relation record | 10.6 ms · 45 · 105 | 6.0 ms · 6 · 4 | 4.8 ms · 5 · 3 |
| relations: 20,000-child parent | 50.0 ms · 45 · 85 | 4.0 ms · 6 · 4 | 2.9 ms · 5 · 3 |
| record: single read | 2.3 ms · 5 · 7 | 2.3 ms · 5 · 4 | 1.7 ms · 4 · 3 |
| write: rename one record | 4.5 ms · 13 · 9 | 4,664 ms · 30 · 216,944 | — |

Draft and history reads meet budgets 1–3; `test_draft_and_history_reads_hold_the_live_budget` is no
longer an expected failure, and the S1 test that asserted their growth is retired. The draft write
halves because its response no longer loads the membership, but the write itself still does (D7).

_Evidence._ `test_context_read_parity.py` runs 37 queries (every field type sorted both ways, search
including `%` and `_`, every filter operator, null and unset) over live data, a current-live draft that
reaches the same data through identical overlay rows and tombstones, a draft derived from a revision
and the revision itself, paged three at a time: same rows, same order up to ties, same values; plus
parent scope, relation pages, single-record and attribute reads, cursor binding to context and query,
and the index equal to the JSON after every draft write kind. `test_snapshot_value_migration.py`
downgrades an API-written database to `20260912_01` and upgrades it through the FastAPI lifespan: the
backfill equals the hook's rows and reads answer as before across two restarts; a table left by an
interrupted run is rebuilt; an unexpected table refuses startup with the operator message and is
preserved. A copy of the development database was downgraded and smoke-started: health ok, the
backfilled index equals the one written at head, and draft and history reads answer for every starter
type. The full backend suite passes except `test_base_0_7_wp12_openapi_document_is_locked`, which
fails identically on the unchanged S1 commit (the OpenAPI document is byte-identical before and after
S2); it is left for its owner to re-baseline.

_Behaviour changes._ Draft and history `search` now matches the name and `searchable` fields, as live
does; before, it matched any attribute's text form. Draft and history cursors issued before the
upgrade are refused with `422 invalid_cursor` (they encoded in-memory sort identities); clients restart
from the first page.

_D7 follow-up slice (S2b, scoped): bounded draft writes._ The draft write services
(`put_draft_object`, `update_draft_object`, `delete_draft_object`, attribute and relation writes,
`_sync_draft_parent_relation` and draft mapping replacement) load the whole membership to check parent
existence, draft-wide attribute uniqueness, the relations touching the record and, for deletion, its
dependants. Replace each with `snapshot_reads` lookups: parent and endpoint existence by ID;
uniqueness as one query over the typed index in the draft projection; relation and cardinality checks
over `relation_projection` for the touched record; deletion planning as a walk down `parent_object_id`
and required-ownership edges whose cost is the deleted subtree, not the draft. Exit: the draft write
budget test passes without its expected-failure marker and a rename stays within 50 ms at full volume;
the `drafts` and `mapping` groups pass unchanged. Whole-graph validation and activation stay as they
are.

**S2b delivered 2026-09-26.** `services/draft_lookups.DraftLookup` answers a draft write's checks
over the draft's effective rows (`snapshot_reads`): records by ID, children of a set of parents,
relations leaving, entering or touching a set of records (optionally by type), the nearest ancestor
of a type, resolved level by level for a batch, and the draft-wide holder of a unique value.
`object_projection` gains `parent_object_ids` and `relation_projection` gains `endpoint_ids` for the
batched reads. Every draft write service uses it: object create, update and delete, attribute patch
and delete, relation create, update and delete, the containment edge sync and draft mapping
replacement (including its conflict and cross-cardinality checks). `validate_draft_relation` reads
the relations at the candidate's own ends: cardinality from the source's outgoing and the target's
incoming relations of the type, and the ancestor scope from the source's relations of the type.
Deletion walks the subtree level by level, children and required-ownership targets, and reads the
relations touching it, so its cost is the deleted subtree; previews list records and relations in ID
order as before, so preview tokens are unchanged. `effective_draft_membership` remains for
validation, activation and the validation audit's counts.

A lookup statement flushes the write's pending rows first, so each check sees the edited record and
any relation already added in the same request, as the candidate membership did. The unique check
asks `snapshot_attribute_values` which base or draft rows hold the value and keeps those that are
the effective row of their record: a base value replaced by a draft row, or a deleted record, holds
nothing. Migration `20260926_02` adds (owner, attribute, text value, object) to that table so the
check seeks to a text value; without it the check read all 100,000 codes of the draft (37.7 ms per
rename). Other value types read the attribute's values; JSON values are compared after decoding.

_Result_ (full volume, `volume_baseline.py --scale 1 --repeat 5`): **write: rename one record in the
draft 7.5 ms · 29 statements · 8 rows** (S2: 4,855 ms · 30 · 216,944; live: 3.6 ms · 13 · 9).
`test_draft_writes_hold_the_live_budget` passes without its expected-failure marker.

_Evidence._ `test_draft_write_lookups` (unique values over a derived draft: a base holder, a base
value freed by a draft row, a record's own value, a draft-only record before and after deletion, a
deleted base record). `test_snapshot_lookup_index_migration`: a clean bootstrap creates the index; a
database written at head, downgraded to `20260926_01`, upgrades through the lifespan across two
restarts with draft and history reads unchanged; an index of another shape left by an interrupted
run is rebuilt. The `drafts`, `mapping`, `records`, `startup` and `volume` groups and the full backend
suite pass.

_Behaviour change._ A unique attribute written without a value no longer conflicts with every draft
record that lacks it; the membership comparison matched a missing value as equal to `null`.

_Open:_ a unique check over a non-text value type reads every value of the attribute in the draft
(no such unique attribute in the starter model). On PostgreSQL, a B-tree entry over about 2.7 KB
fails, so a `longText` value that long in the index would need an expression or hash index when
PostgreSQL hardening starts.

#### S3: Cursor and position paging contract

**Scope:** in the shared pagination helpers, so every collection endpoint gains it:

1. Each page returns `prevCursor` beside `nextCursor`. A cursor encodes its direction; the server
   reverses the keyset predicate and order for backward reads and returns rows in list order.
2. Omitting the cursor with `from=end` returns the last page; the default remains the first page.
3. Each page returns an `anchor` cursor that reopens the same page, for the URL.
4. `includeTotal=true` adds `totalCount` and `startIndex` (the number of matching rows before the
   page's first row), counted under the same filters. Totals are opt-in so export-style clients pay
   nothing.
5. `seek=<value>` on object, relation and mapping-coverage lists starts at the first row whose
   current sort value is at or after the value (at or before for descending order).
6. `position=N` returns the page starting at row N of the filtered, sorted list, with the same
   `prevCursor`, `nextCursor` and `anchor` as any page. A request with both `position` and `cursor` is
   refused with a machine-readable error. API.md documents that position reads can repeat or miss a
   row at a page boundary when data changes between requests, and that whole-list reads should use
   cursors.
7. Cursors stay signed and bound to endpoint, ordering and filters; a changed filter still returns
   `422 invalid_cursor`.
8. Update API.md and the OpenAPI lock, and state the concurrency behavior of each mode: cursor reads
   never repeat or skip a row when data changes; position reads can.
9. Update the AGENTS.md invariant and the S5 hook rule once delivered.

**Exit:** forward, backward, end, anchor, total, seek and position reads are exercised over the S1
fixture in live, draft and history contexts, including a concurrent insert between cursor reads, a
position read deep in the 20,000-child parent within budget, and refusal of `position` with `cursor`.

**Delivered 2026-09-25 (with S4).** `services/pagination.py` takes a `PageRequest` (at most one of
cursor, position, seek, `from=end`; otherwise `422 conflicting_page_parameters`) and returns a `Page`
with `nextCursor`, `prevCursor`, `anchor` and, on request, `totalCount` and `startIndex`. A cursor
records its direction (after, from, before, up to its row); cursors without one, issued before S3,
continue forward. Backward reads reverse the keyset predicate and order and return rows in list order.
A page costs its own read, at most one probe for the opposite edge and, with totals, two counts.
`routers/paging.PageQuery` and `SeekablePageQuery` give all 17 cursor-paged collections the same
parameters; seek is offered on objects (typed by the sorted field, including attribute sorts),
relations and mapping coverage. Every page response inherits `PageNavigation`; API.md documents the
contract and each mode's concurrency behaviour, and the OpenAPI lock is re-baselined with an explicit
paging inventory beside it.

_Evidence._ `test_paging_contract.py` (fixture at 1%, all three contexts) walks the 20,000-child
parent's name-sorted list forward and backward against a reference walk, with totals and start
indexes on every page; lands position reads mid-list and past the end and continues from their
cursors and anchor; seeks by name and by an integer attribute in both directions; refuses combined
selectors, a negative position, a cursor reused with another filter and an unparseable or
unsupported seek; and inserts records before and after the reader between cursor reads, live and in
the draft, without a repeat or a skip. `test_pagination.py` covers the in-memory paginator the same
way, and a pre-S3 cursor still continuing forward. The S1 budget scenarios gained last page, backward
page, seek, deep position, top-level page and relation name sort and search, and hold budgets 1–2 in
every context.

_Result:_ see the S4 table. The previous-page probe first doubled live middle and last object pages
(20 → 40–47 ms), and a live position read three quarters into 100,000 records took about 500 ms,
because live objects had only single-column indexes and every name-ordered read scanned the type.
Migration `20260925_03` adds (workspace, type, name, sequence) and (workspace, parent, type, name,
sequence) indexes on live objects, mirroring the S2 page indexes on revision and draft-base objects:
live pages now take 2–13 ms. The default creation order already reads through the primary key and
needs no index. `test_page_index_migrations.py` holds both S3/S4 index migrations.

#### S4: Top-level and relation query additions

**Scope:**

1. `topLevel=true` on object lists returns only records without a parent, so a tree can page a root
   type without loading its descendants.
2. `search` and `sort` on relation lists, in live, draft and history. Search covers the related
   record's name and its searchable fields; sort covers the related record's name and relation
   creation order.
3. A branch with children of several types pages each child type separately through the existing
   `parentObjectId` filter. No mixed-type endpoint is added (D3).

**Exit:** the S1 record with 1,500 relations can be searched and sorted in each context within
budget, and a root type pages without descendants.

**Delivered 2026-09-25.** `topLevel=true` on object lists, in every context, and refused beside
`parentObjectId`. `services/relation_queries.py` builds relation pages for live and for draft and
history with one contract: `search` over the related record's name and `searchable` values, `sort`
by the related record's name or, live, `createdAt`, and seek on either. Draft and history read the
related record through correlated lookups on its (owner, object) keys (`snapshot_reads.
effective_object_value`) rather than a join to the object projection. Live relation pages build their
related records in one batch (the S1 finding): 7 statements instead of 45.

The first full-volume run showed draft and history relation pages scanning every relation of the
revision: the revision and draft relation tables had only owner indexes, so `owner = ? AND (from = ?
OR to = ?)` read the whole owner. Migration `20260925_02` adds (owner, from, relation ID) and (owner,
to, relation ID) indexes on revision, draft-base and draft relations, and `relation_projection` reads
each end in its own arm. `test_page_index_migrations.py` checks clean bootstrap, upgrade
from `20260925_01` through the FastAPI lifespan across two restarts with relation pages answering as
before, and an interrupted run that left one index behind and an earlier shape of another. The
development database was upgraded by the running dev server and smoke-checked (health, relation and
object pages with totals in live and history).

_Results_ (same machine, fixture and method as S1; `volume_baseline.py --scale 1 --repeat 3`):

| Request | Live | Draft | History |
| --- | --- | --- | --- |
| objects: first page | 3.1 ms · 5 · 79 | 4.3 ms · 5 · 4 | 4.0 ms · 4 · 3 |
| objects: middle page | 3.7 ms · 6 · 81 | 5.4 ms · 6 · 4 | 4.0 ms · 5 · 3 |
| objects: last page | 3.7 ms · 6 · 81 | 4.3 ms · 6 · 4 | 3.3 ms · 5 · 3 |
| children: heavy parent, first page | 2.9 ms · 5 · 65 | 3.6 ms · 5 · 4 | 3.0 ms · 4 · 3 |
| children: heavy parent, middle page | 3.5 ms · 6 · 66 | 4.8 ms · 6 · 4 | 3.7 ms · 5 · 3 |
| children: small parent | 2.3 ms · 5 · 19 | 3.6 ms · 5 · 4 | 2.4 ms · 4 · 3 |
| relations: 1,500-relation record | 8.3 ms · 7 · 103 | 4.6 ms · 6 · 4 | 3.5 ms · 5 · 3 |
| relations: heavy parent | 47.1 ms · 7 · 85 | 4.7 ms · 6 · 4 | 3.5 ms · 5 · 3 |
| record: single read | 2.0 ms · 5 · 7 | 3.2 ms · 5 · 4 | 2.2 ms · 4 · 3 |
| objects: last page by from=end, total | 7.6 ms · 6 · 81 | 47.6 ms · 6 · 4 | 9.0 ms · 5 · 3 |
| objects: backward page from the middle | 4.6 ms · 6 · 83 | 6.5 ms · 6 · 4 | 3.3 ms · 5 · 3 |
| objects: seek by name, total | 8.2 ms · 8 · 83 | 48.3 ms · 8 · 4 | 10.7 ms · 7 · 3 |
| objects: position ¾ deep, total | 12.6 ms · 6 · 81 | **175.1 ms** · 6 · 4 | 15.6 ms · 5 · 3 |
| children: heavy parent, position ¾ deep, total | 6.1 ms · 6 · 65 | 43.0 ms · 6 · 4 | 9.1 ms · 5 · 3 |
| roots: top-level page, total | 3.3 ms · 5 · 64 | 9.2 ms · 6 · 4 | 6.2 ms · 5 · 3 |
| relations: 1,500-relation record by name, total | 9.8 ms · 8 · 103 | 21.7 ms · 7 · 4 | 16.4 ms · 6 · 3 |
| relations: 1,500-relation record, search | 18.5 ms · 7 · 102 | 18.3 ms · 6 · 4 | 13.9 ms · 5 · 3 |
| write: rename one record | 3.6 ms · 13 · 9 | 4,793.7 ms · 30 · 216,944 | — |

Every read meets budgets 1–3 in every context except one: a draft position read three quarters into
a whole 100,000-record type takes 175 ms (budget 100 ms; history 16 ms). SQLite skips 75,000 rows
through the draft's base-plus-overlay union, then counts it. Position reads inside a branch, the S3
exit case, stay within budget (43 ms in the 20,000-child parent). **Resolved by S4R6** (60 ms): a
deep position resolves against the base's index and corrects for the overlay's rows before it. Totals
cost most in drafts (the count runs over the base-plus-overlay union, about 40 ms over 100,000 items);
the UI asks for them on first load, after a query change and with jumps (D5), not on every scroll.
The draft write is unchanged (S2b).

#### S4R: Revision of the S3/S4 query design (decided 2026-09-26)

**Why.** Reviewing the relation panels on systems and translations showed that S4 gave relation lists
a fixed sort vocabulary: the related record's `name` and `createdAt`. It ignores the model. Tables sort by
their declared `sortFields`, object lists by any `sortable` attribute, and the starter's relation panels
show `ancestor:system`, `value-code`, `ancestor:language` and `translated-name`, none of which could be
sorted. It also behaves differently per context: `createdAt` works live only, so "Newest first"
disappears in drafts, and without a sort, live lists came back in creation order while drafts and
history came back in UUID order. S5 then hardcoded that vocabulary in `RelationsPanel`. The same review
found mapping coverage seeking by source ID, the draft deep-position read over budget, and pages
always carrying null totals.

**Decisions (user, 2026-09-26).**

- **D21** Relations panels declare their sort options in the model: optional `sortFields` and
  `defaultSort`, as table views do, in **schema 0.7**. This is the first schema 0.7 addition; A1 and B1
  add their view types to the same version. Schema 0.5 and 0.6 panels keep working and sort by name.
- **D22** Every list's default order is the same in live, draft and history: name order, with the
  context's unique tiebreak. Recorded timestamps in drafts and history (reopening WP-10K) become a
  separate later package (T1); until then a relation list sorts by the related record's
  `createdAt`/`updatedAt` live only, as an object list does, and refuses them in drafts and history
  as not recorded. Relation creation order is not offered.
- **D23** Ancestor columns (`ancestor:<type>`) are sortable on relation lists now, measured at volume.

**Slices**, each independently deliverable and verified on its own:

1. **S4R1 — Relation queries through the object query builder (API).** A relation list sorts and
   searches its related records with `refine_object_query`, in live, draft and history. `sort` accepts
   `name`, any `sortable` attribute of the related type, and `ancestor:<type>` for a type the related
   type can sit under; typed values, nulls last, descending with `-`. Attribute and ancestor sorts need
   one related type, derived from the relation types, direction and anchor type; otherwise
   `422 invalid_sort`. `relationTypeKey` repeats, so a panel over several relation types derives its
   related types exactly. Search uses the related types' searchable bindings. `createdAt` and
   `updatedAt` are the related record's, live only (D22). The default is `name`. An ancestor is
   resolved by one walk up the containment chain for the anchor's related records, not per row. Exit:
   parity across contexts, the S1 budgets, and the 1,500-relation record and the 20,000-child parent
   sorted by ancestor within budget.
2. **S4R2 — Schema 0.7 and panel sort configuration.** Accept `schemaVersion: "0.7"` (schema, compiler,
   registry, releases, `model_schema_upgrade`, startup message) as A1 item 1 describes. Relations panels
   gain optional `sortFields` and `defaultSort`, refused below 0.7 at the field's path. Validation: each
   field sorts on every related type the panel can list (name, sortable attribute, or reachable
   ancestor), `defaultSort` (with optional `-`) names one of them, lists are unique. The starter moves to
   schema 0.7, content release 0.8.0, with sort options on its relation panels (systems: system, value
   code, name; translations: language, translated name, name). Exit: `model` group, starter and
   generated model validate, a 0.6 model still installs.
3. **S4R3 — One sort element (UI).** Every table-shaped list sorts through one generic element, fed
   by the model (`sortFields`, `defaultSort`), never by component-defined options:
   - **Sortable column headers** in `ui/ObjectTable` are the primary control. A sortable header shows
     a quiet sort icon on hover and focus; the active one an accent up or down icon (Lucide, replacing
     the text arrows); activating it toggles ascending and descending. `aria-sort`, an accessible name
     stating the current order, and a polite announcement of the change.
   - **A compact icon-only sort menu** (sort icon with tooltip, `ui/ActionMenu`, one radio item per
     field plus direction) appears only when a sortable field has no visible header: at 390px, with
     columns collapsed, or on a list without headers.
   - Adopted by the collection lens, record panels and relation panels. Removed: the collection lens's
     toolbar **Sort** popover (a duplicate of its headers) and the relation panel's inline **Sort**
     select, whose layout was broken: it used `.toolbar-field`, the stacked label-over-select field
     meant for popovers, so inline its label sat above the select and the control stood taller than
     the search box and **Add relationship** beside it. `RelationsPanel` renders through the shared
     header; without configured sort fields it lists by name and offers no sort.
   Reference pattern: the record panel's header sort (`CollectionPanelTable` over `ObjectTable`). Exit:
   focused component tests (header states, toggling, keyboard, the menu appearing only when needed);
   the UI acceptance state-inventory row; the S5 browser runner's lens, record panel and relation panel
   in live, draft and history for two object types at 1440px and 390px by keyboard; screenshots of the
   three surfaces inspected and their visual baselines updated after review (search and actions aligned,
   no labelled sort control left).
4. **S4R4 — One default order in every context.** Object lists default to name order in every context
   (live used the internal creation sequence), and mapping coverage and candidates sort by source name,
   so `seek` jumps to a name. Pre-change cursors for the changed defaults are refused with
   `422 invalid_cursor`. Exit: parity test with the default order, mapping group.
5. **S4R5 — Page response shape.** Pages list `items` first and omit `totalCount` and `startIndex`
   unless `includeTotal=true`. Exit: contract group and the OpenAPI lock.
6. **S4R6 — Draft deep-position read.** Bring a draft position read three quarters into a whole
   100,000-record type within 100 ms (175 ms now), for example by resolving the position against the
   base's index and correcting for the overlay rows before it. Exit: the S1 scenario within budget.

**S4R1 delivered 2026-09-26.** `relation_queries` builds both relation lists over
`objects.refine_object_query`, with `ObjectColumns` describing the related record: live, an aliased
`objects` row joined on the other end; in drafts and history, `snapshot_reads.effective_record`, outer
joins to the one draft row and the one base row on their unique keys (replacing S4's correlated
lookups, which ran up to three times per row). `relation_projection` arms name the other end as a
plain `related_id` column to join on. The builder gained what relation lists need and object lists can
reuse: several object types (search over all their searchable bindings, attribute and ancestor sorts
refused unless there is one), `select_sort_values` (sort values selected as labelled columns and read
back for cursors, and attribute values joined rather than looked up per row), and an `ancestor` hook.
The ancestor walk starts once from each distinct parent of the listed records, reads records with
keyed lookups (the walk is small), and joins the name back by parent. Draft and history object and
relation pages now return each record's `path`, resolved level by level for the page
(`snapshot_reads.object_paths`); they returned an empty `path`, so an `ancestor:` column was blank
outside live. A relation page for a record the context does not hold answers `404`, as live did.
Migration `20260926_01` rebuilds the revision, draft-base and draft relation endpoint indexes as
(owner, end, relation type, relation ID, other end), so the listing reads the index alone.

Two planner findings are recorded in the code. A `WHERE name IS NOT NULL` on the outer-joined record
let SQLite reduce the join to an inner one and scan all 110,000 records of the revision to probe the
list (history totals took 38 ms instead of 2 ms); `EffectiveRecord.present` is a `CASE`, which keeps
the outer join. Joins in the ancestor walk were reordered into a scan of every group; keyed lookups
keep the walk on its own rows.

Full volume, `ms · statements · rows` (repeat 5); the heavy parent lists its 20,000 contained items:

| Request | Live | Draft | History |
| --- | --- | --- | --- |
| relations: heavy parent (default: name) | 43.0 · 7 · 85 | 72.5 · 8 · 4 | 59.6 · 7 · 3 |
| relations: 1,500-relation record by name, total | 9.0 · 8 · 103 | 14.8 · 9 · 4 | 10.0 · 8 · 3 |
| relations: 1,500-relation record by rank | 9.2 · 7 · 101 | 18.5 · 8 · 4 | 13.1 · 7 · 3 |
| relations: 1,500-relation record by group, total | 28.1 · 8 · 102 | 50.4 · 9 · 4 | 34.0 · 8 · 3 |
| relations: deep node by top node (7 levels) | 5.0 · 12 · 14 | 10.4 · 13 · 4 | 6.1 · 12 · 3 |
| relations: heavy parent by rank | 85.9 · 7 · 85 | 170.2 · 8 · 4 | 205.5 · 7 · 3 |
| relations: heavy parent by group | 98.1 · 7 · 85 | 208.2 · 8 · 4 | 198.3 · 7 · 3 |
| children: heavy parent by rank (object list, for comparison) | 101.2 · 9 · 65 | 132.3 · 10 · 4 | 108.0 · 9 · 3 |

Statement counts stay constant and every other S1 scenario is unchanged or faster (the heavy parent's
default relation page was 155 ms in drafts by name before the joins and indexes).
**Open: the exit's 20,000-child parent sorted by ancestor is not within budget** in drafts and history
(about 200 ms; live 98 ms), and neither is an attribute sort there. An order no index holds costs a
keyed lookup per listed row for each field it reads: about 50 ms per pass over 20,000 relations
here, and an ancestor sort needs two passes (parents, then the list). Object lists share the
limit: sorting the same 20,000 children by an attribute takes 101–132 ms, which S1 never measured.
The 1,500-relation record, the size of the starter's relation panels, sorts by any field within
budget. Closing the gap needs precomputed sort keys (an indexed sort value per record and sortable
field, or a stored ancestor per record and containment type), which is storage work for a later
package rather than S4R1.

**S4R2 delivered 2026-09-26.** Schema 0.7 is accepted everywhere a supported version is checked
(`SUPPORTED_SCHEMA_VERSIONS`, the `EngineModel` literal, `model_schema_upgrade`, the startup
message); A1 item 1 is therefore done and A1 only adds its view type. The mapping grid's gate became
"0.6 or later" through a shared `require_schema` rule. `RelationsPanelConfig` gains optional
`sortFields` and `defaultSort`, declared together. Validation reads the panel's related types with
the function the relation query uses (`related_object_types`, moved with `ancestor_type_keys` into
the database-free `services/model/traversal.py`), so a declared field is exactly one the API accepts:
`name`, or with one related type a sortable non-JSON attribute or a reachable ancestor. Failures
point at `config/sortFields/<n>` or `config/defaultSort`. Absent fields are excluded from the
canonical document, so 0.5 and 0.6 model hashes are unchanged and re-installing an existing release
does not conflict. The starter is schema 0.7, content 0.8.0: the three system-value panels declare
`ancestor:system`, `value-code`, `name` and the three translation panels `ancestor:language`,
`translated-name`, `name`, each defaulting to its ancestor; `translated-name` became `sortable` to
allow it. Panels over several related types (represented structures, translation targets) and the
systems application's mappings panel declare nothing and list by name. The generated volume model
stays on schema 0.6 as the installed 0.6 case; S4R3 may give it sort options when its browser runner
needs a second configuration. The frontend type carries the two fields; S4R3 consumes them.

**S4R3 delivered 2026-09-26.** `ui/TableSort` is the one sort element. `useTableSort` holds a list's
sort, its model-fed fields and the polite announcement; `SortHeader` renders a sortable header
(Lucide `ArrowUpDown` shown quietly on hover and focus, accent `ArrowUp`/`ArrowDown` when sorted, the
sorted button named "Name, sorted ascending"); `SortMenu` is an icon-only `ui/ActionMenu`, which gained
radio sections, a trigger icon and a tooltip: a **Sort by** section with one radio item per field and
an **Order** section. The menu appears only for a sortable field without a visible header. A declared
field with no column, or a column hidden through Display, puts it in the surface's toolbar beside
Filter and Display (`hasHeaderlessField`). `ObjectTable` shows it beside **Show all columns**, narrow
widths only, while one of its collapsed columns is sortable. No starter list has headerless relation
sort fields, so relation panels show headers only. The collection lens (`view.config.sortFields`),
record panels (the listed type's sortable columns) and relation panels (`sortFields`, `defaultSort`,
live-only timestamps dropped in drafts and history) use it. The lens's toolbar **Sort** popover and
the relation panel's inline **Sort** select, with its fixed name and creation-time options, are gone.
A relation panel without sort fields lists by name and its headers are plain. The volume model stays
on schema 0.6 as that case; the starter's declared panels are the configured case.

Evidence: `ObjectTable.test` (header states, toggling, announcement, menu only when needed, keyboard
menu, narrow-only class), `RelationsPanel.test` (declared default, header toggle, menu for a headerless
field, no sort without configuration, draft timestamps), `CollectionView.test`. The S5 runner's
starter part sorts the relation panel (declared default, value code both ways), the record panel and
the master-values lens (header, then the toolbar menu for Sort order) on a domain and a codelist in
live, draft and history by keyboard. It checks the request, `aria-sort`, the announcement and the
aligned relation toolbar. At 390px it sorts relation headers, uses the record panel's narrow menu until
all columns show and uses the lens menu. The volume part checks the unconfigured relation panel in
all three contexts. `wp9-navigation` toggles the lens header by keyboard. The `collection-table-*`,
`record-detail-*` and `draft-detail-light` baselines were inspected and updated: no Sort popover, the
relation toolbar's search and **Add relationship** at one height, accent arrows. They also absorb
drift that predates S4R3: S4R2's "Model 0.8.0 · Schema 0.7" label, and S5's scroll-window footer
replacing the page buttons.

**S4R3 revised 2026-09-26 (D24).** In review, lists looked like a zebra: a few headers sorted, most
did not, and the Sort button appeared on some lists only. Three causes compounded: each surface took
its sort fields from a different source (view `sortFields`, panel `sortFields`, or the `sortable`
attributes among a record panel's columns), the menu rule depended on layout, and the starter flagged
only ten attribute types `sortable`. The revision applies one rule. The server sorts by any non-JSON
attribute (`objects._sort_attribute`), across several related types with records lacking it last,
and by `objectType` and `relationship` labels from the model, then by name (`_label_sort`). The UI
derives every list's fields with `model/fields.listSortFields`: sortable columns in column order, then
declared `sortFields`. `SortMenu` is always in the toolbar when a list has fields; the narrow-only
menu is gone. The hidden header icon sits in the header padding (absolutely positioned) because as an
inline element it widened columns and pushed the relation table's Actions column to the panel edge.
Model validation relaxes to match, and a relations panel may declare `defaultSort` alone; no model
content changed, so the installed 0.8.0 release keeps its hash. Evidence: `test_paging_contract`
(label sorts walked, reversed and sought in live, draft and history; an attribute across two types),
`test_model` (any-field panel sorts, the ancestor-over-several-types refusal), `test_typed_table_queries`,
the OpenAPI lock, the unit suites above, and the S5 runner. The runner now checks that the volume
relation panel sorts every header but Actions, that the never-flagged value name sorts, and that the
record panel's toolbar menu reaches a collapsed column at 390px. Baselines were re-inspected and
updated for the lens, record, draft-detail and draft-editing surfaces.

**S4R4 delivered 2026-09-26.** An object list without `sort` orders by name in every context: live
used the internal creation sequence and drafts and history the record ID. `ObjectColumns` no longer
carries a per-context default; `objects.DEFAULT_SORT` (`name`) serves object and relation lists alike,
closed by each context's unique tiebreak (live sequence, record ID, relation). An unsorted list
therefore seeks by name, and the "default order has no value to seek by" refusal is gone. Mapping
coverage and candidates key by (name, ID) instead of ID, so coverage `seek` jumps to a source name.
Pre-change cursors carry the former sort tokens (`sequenceId`, `id`) and are refused with
`422 invalid_cursor` by the existing sort binding; no cursor code changed. No migration: the
`*_type_name` and `*_parent_name` indexes from migration `20260925_03` and S2 already serve name order,
and every S1 object scenario already requested `sort=name`, so the new default runs the measured
path. The browser already requested `sort=name` on the lens and record panels; the object picker
and Explorer search results, which sent no sort, now list by name. Evidence:
`test_context_read_parity` (the parity walk compares default-order names in all four contexts; the default equals `sort=name` by ID, seek
without a sort, and forged former-default cursors refused in live, draft and history, with a re-signed
control accepted), `test_mapping_coverage` (coverage by name in live and draft, candidates by name,
seek by source name, a former ID-order cursor refused), `test_paging_contract` (an unsorted volume list
seeks by name in live, draft and history), the OpenAPI lock (the object `sort` description names the
default). Both new tests fail against the previous services. Not measured: mapping coverage at volume,
which no S1 scenario covers.

**S4R5 delivered 2026-09-26.** Every page model derives from one generic `CollectionPage[Item]` in
`models/api.py` (replacing `PageNavigation`, whose fields came before each subclass's `items`), so
all 17 cursor-paged responses list `items` first, then `nextCursor`, `prevCursor`, `anchor` and, with
`includeTotal=true`, `totalCount` and `startIndex`; the mapping target page adds `mappingVersion` and
`targetCount` after them. The counts are excluded when unset (`exclude_if`) rather than serialized as
`null`, and OpenAPI documents them as optional integers instead of nullable ones. No service changed:
`Page.links()` still names every field and the response model drops the unset counts. The frontend
types drop `null` from the counts; its readers already treated them as optional. Evidence:
`test_paging_contract` (the exact key order of an object page with and without totals in live, draft
and history), `test_openapi_contract` (every page schema starts with `items`, the counts are optional
integers, and the re-baselined lock, whose diff is only those 17 schemas), and `test_model_lifecycle`
(an empty activation page without totals).

**S4R6 delivered 2026-09-26.** A draft position read no longer offsets through the base-plus-overlay
union, which SQLite can only skip row by row. `paginate_statement` takes an optional `Overlay`
naming the union's parts, each filtered and sorted as the list is: every base row, the base rows the
draft replaces or deletes, and the draft's own rows. `pagination._locate` counts the draft's own
rows (`added`), reads the base row at `position - added` through the base's page index (it precedes
the target row or is it, since at most `added` draft rows can come before), then counts the replaced
and the draft rows before it in one statement. Its rank in the draft is its base rank, less the
replaced rows before it, plus the draft rows before it; the page is read from that row forward,
skipping the remainder, which is at most the draft's size. A position shallower than `added`, or
past the base's end, still reads by offset. `snapshot_reads.object_projection` gains `part`
(`effective`, `base`, `replaced`, `added`) and `build_snapshot_object_query` returns the overlay for a
draft with a base; revisions and base-less drafts are unchanged. The replaced part keeps only its
`object_id IN (draft IDs)` term indexable: SQLite otherwise walked the base's name index to count
the replaced rows before the position (24 ms), and on a current-live base would have taken the
single-column type or parent index. A position read costs three more statements (a constant: 10 in
the draft, 6 live), and no migration is needed.

_Results_ (full volume, `volume_baseline.py --scale 1 --repeat 5`, same machine as S1):

| Request | Draft before | Draft after |
| --- | --- | --- |
| objects: position ¾ deep, total | 175.1 ms · 6 · 4 | 60.3 ms · 10 · 4 |
| children: heavy parent, position ¾ deep, total | 43.0 ms · 6 · 4 | 21.4 ms · 10 · 4 |

The whole-type read now costs the same at every depth (56–62 ms from a quarter to 99% deep, against
81–190 ms before); about 40 ms of it is the total count over the union, which the S4 note above
covers and which the UI asks for only on first load, after a query change and with jumps (D5).
Evidence: `test_draft_position_reads` lands position reads across two drafts whose rows move (renames
to the front, back and middle, new records at the front, the fixture's tombstones), on a revision base
and a current-live base, over a whole type and inside a parent, by name, descending and by an
attribute; each landing, its start index, total and both cursors match a cursor walk, and every read
past the draft's own rows resolved in the base. Two mutations of the correction (dropping the
replaced or the preceding draft rows) each fail it. `test_volume_baseline` holds the constant
statement count across scales.

**Later package T1 — recorded timestamps in drafts and history.** Timestamp columns on draft,
draft-base and revision object and relation rows (captured rows keep live values, draft writes set
them), plus an internal creation ordinal so creation order is identical in every context. Backfill from
live where the record still exists; others stay not recorded. Restores `createdAt`/`updatedAt` queries
in drafts and history and makes creation order available as a relation sort. Scheduled separately.

#### S5: Shared continuous-scroll list

**Scope:**

1. One hook (working name `useCursorWindow`) keeps a bounded window of pages (D2), prefetches when
   the viewport is within one page of either edge, and evicts the page furthest from the viewport.
   Evicting keeps no cursor stack: the window's edge pages hold the cursors needed to go further.
2. Scroll position stays stable when rows are added above or removed.
3. A loading marker appears at an edge only when the user reaches it before data arrives. Start and
   end markers are quiet ("Start of list", "End · 1,000 records"). Markers are announced politely to
   screen readers and respect reduced motion.
4. The URL holds one `anchor` cursor instead of the cursor trail.
5. Keyboard: arrow keys move through rows across page boundaries; Ctrl+Home and Ctrl+End go to the
   start and end; the focused or selected row keeps its identity when pages are evicted.
6. A proportional scrollbar sized from `totalCount`. Clicking or dragging it, or entering a page
   number, sends one position request and replaces the window with the landed page; scrolling on
   uses that page's cursors. Rapid dragging sends only the final position.
7. Accessibility: `aria-rowcount` from `totalCount` and `aria-rowindex` from `startIndex`.
8. Adopt it in the collection lenses, record panels (which gain a sort control, defaulting to name),
   relation panels, the mapping lens and object pickers (a searchable listbox instead of a native
   select plus **Load more**).
9. Update AGENTS.md: the rule naming `useCursorPages` and `useCursorFeed` changes to the new hook.

**Exit:** each adopted surface scrolls the S1 fixture both ways with flat memory and jumps by
scrollbar and page number, in two model
configurations (the starter model and the generated model) at 1440px and 390px, using the keyboard
alone.

**Delivered 2026-09-25.** `lib/hooks/useCursorWindow` holds at most five pages (D2), each with its
own cursors, so evicting the page furthest from the viewport keeps no trail; jumps (`position`,
`from=end`, `seek`) replace the window with one request and ask for totals (D5), and edge reads
extend it with cursors alone. Reaching either end corrects the counted indexes and total. `ui/
ScrollWindow` renders the scrolling region: it prefetches when the viewport is within one page of an
edge, keeps the rows on screen still when rows arrive above or are evicted, lands jumps below the
sticky header, shows quiet start and end markers and a loading marker only at the edge being waited
for (announced politely, spinner still under reduced motion), and, while the window holds part of the
list, a proportional scrollbar sized from `totalCount`: a track click or the release of a drag sends
one position request, and a target already held scrolls without one. Its footer shows the visible
range, a page field, start and end buttons and, on the collection lens, **Go to** the sorted value.
Arrow keys move focus through rows across page boundaries, Ctrl+Home and Ctrl+End jump and focus,
and a focused row evicted from the window leaves focus on the list. Tables carry `aria-rowcount` and
`aria-rowindex`. The URL holds one `anchor`, written without a history entry or the navigation
guard, and only when the user scrolls or jumps; the list's own compensating scrolls never rewrite
it. A view's `pageSize` is the fetch size (D4). Adopted by the collection lens, record panels (sorted
by name by default, by any sortable column from its header), relation panels (search and sort), the
mapping lens and its candidate list, and the object picker, now a combobox over a listbox with
`aria-setsize` and `aria-posinset`. `useCursorPages` and `ui/Pagination` are removed; `useCursorFeed`
remains for record history and draft and revision lists. AGENTS.md names the new hook.

_Evidence._ `useCursorWindow.test.tsx` covers the bounded window both ways, jumps held and not
held, anchor reopening with a stale-anchor fallback, index correction after deletions before the
window, edge failure and retry, and refresh in place. `e2e/s5-continuous-lists.mjs`
(`test:browser:s5`) runs against a real backend: over the volume fixture it scrolls the items lens
both ways with the window bounded at 100 rows and the JS heap flat, jumps by scrollbar click and
drag with exactly one position request each and by page number, reopens a copied URL at the same row,
and walks it by keyboard (arrow keys across pages, Ctrl+End, Ctrl+Home, seek), in live, draft and
history; it also scrolls, sorts and walks the heavy record panel and searches and walks the cited
relation panel in all three contexts, and repeats the lens and panel at 390px. Over the starter
model it scrolls the codelist lens, the mapping lens (keyboard across pages, Ctrl+End, page number),
a relation panel and the picker (keyboard choice across a page boundary), at 1440px and 390px, with
axe clean on five surfaces. It passes at the default 10% scale and at full volume
(`S5_VOLUME_SCALE=1`: 100,000 items, the 20,000-child parent, the 1,500-relation record; about 100 s).
`wp9-navigation`, `wp9-authoring`, `wp9-drafts`, `wp9-history`, `wp13c`, `wp14`, `sc07` and `sc15`
were updated for the removed page buttons, **Load more** and native picker select, and pass.

_Found on the way and fixed:_ a landing measured against the header's unstuck position and the
visible range counted a row under the stuck header (both one to two rows off); an edge page read
from the previous window could be appended to a replaced one (the page is now applied only to the
window whose edge it continues); a landed page too short to fill the viewport never prefetched; a
list mounted hidden (a record reopened by reload) refreshed from its first page.

_Open:_ the S4 draft position read three quarters into a whole 100,000-record type (175 ms, budget
100 ms) is unchanged; the scrollbar works there at that cost (resolved by S4R6: 60 ms). Visual baselines for the tables that
lost their page buttons and dedicated accessibility-gate scenarios for the list remain S7 scope; the
edge loading marker is covered by component state only, not a captured screenshot.

#### S6: Sidebar tree by parent

**Scope:**

1. Top level: each root type of the application loads through `topLevel=true` in its own bounded,
   scrolling group.
2. Branches: expanding a record loads each child-type group separately with `parentObjectId`, in a
   window from S5. Collapsing a branch releases its pages.
3. Remove **Load more objects** and the global per-type load, which also removes the defect where a
   record with an unloaded parent appears at the top level.
4. Tree semantics: `role="tree"`, `aria-setsize` and `aria-posinset` from totals, and arrow-key
   navigation that loads into a branch as it goes.
5. Search keeps using the server and shows matching records with their ancestor path.

This delivers Milestone B's traversal item for the generic browser. The typed `tree` view contract,
reparenting and child creation remain Milestone B.

**Exit:** in the S1 fixture, every branch shows exactly its own children and their count, the
20,000-child parent scrolls end to end, and a six-level path opens by keyboard.

**Delivered 2026-09-26.** `features/objects/RecordTree` replaces the explorer's global load. Root
types are the application's `rootCreatable` types (`model/collections.rootObjectTypeKeys`); a parent
is always in its child's application, so top-level roots and parent branches reach every record once.
Each root type pages `topLevel=true`, and an expanded record mounts one group per child type
(`childObjectTypeKeys`, the model's `parentOf` bindings) paged with `parentObjectId`, both sorted by
name, 50 rows a page. A group is a `useCursorWindow` in a `ScrollWindow` with a bounded height (a
branch's is shorter), headed by an item naming the type and its total that opens the type's
collection, scoped to the parent: the former **All …** row. A group without records draws nothing; a
record whose groups are all empty says **Nothing inside**. Collapsing a record, or a row leaving its
window, unmounts its groups and releases their pages; branch choices persist per browser as before,
and the active record's ancestors (read once from its `path`) open by default. **Load more objects**
and the per-type load of every type are gone, and so is the defect of a record with an unloaded
parent drawn at the top level. A search pages each type of the application with `search` and shows
each match's ancestor path; a match's own branch lists plain children.

The tree follows the WAI-ARIA tree pattern: one tab stop (the last focused item, else the active
record, else the first heading), `aria-level`, and `aria-setsize` and `aria-posinset` from each
group's total, the heading counting as the set's first item. Up and Down move in document order;
leaving a window that holds more rows beyond its edge loads them and moves on when they arrive, and
entering a window that does not hold its first (or last) row jumps there. Right and Left expand,
enter, collapse and return to the parent; Home and End; Ctrl+Home and Ctrl+End jump within a group;
Enter opens a record or a heading's collection. axe allows a tree to own only items, groups and plain
containers, so `ScrollWindow` gained `role="group"`: the viewport is the named group (a tab stop only
while it scrolls, which `scrollable-region-focusable` needs), its edge markers are presentational
and its announcements go to the tree's one live region. `ScrollWindow` also reads only its own rows,
so windows nest, ignores keys a nested window handled, and can show start and end markers only for a
list longer than a page.

_Evidence._ `Explorer.test` (roots by `topLevel` with totals, each child type by parent, exactly a
branch's own children with level, position and set size, release and re-read on collapse, **Nothing
inside**, persisted choices, the active record's path, keyboard across a page edge with one tab stop,
search over every type with paths, a failed group retried in place). `e2e/s6-sidebar-tree.mjs`
(`test:browser:s6`) against a real backend: over the volume fixture, in live, draft and history, the
root pages its 1,000 top-level groups; the 5-item group and the heavy group (2,000 items live and in
history, 1,993 in the draft) show exactly their own first page and counts for both child types, as
the API lists them in that context; the heavy branch scrolls end to end with the wheel, never holding
more than 250 rows, and returns by Ctrl+Home; an eight-level path (the group and seven node levels)
opens by keyboard alone (Ctrl+End, Down into the next window, Down and Right per level, level,
position and set size checked), Enter opens the deep node and marks it current; collapsing releases
the branch (122 items); every tree read is top-level, by parent or by search. At 390px the drawer's
tree opens the heavy branch by touch, scrolls past its first page and expands by keyboard. Over the
starter model it walks a domain and its codelists by keyboard, opens a record and a heading's scoped
collection, searches with a path, and shows a system's one non-empty child group of two. axe is
clean on the volume tree eight levels deep and on the master and systems trees. `wp9-navigation`
(with `ui03b-hierarchy`), `wp14-contextual-browser` and `s5-continuous-lists` were updated for the
tree items and pass; `test:visual` passes with the sidebar's added heading under threshold (history
view 0.26%), baselines not refreshed.

_Found on the way and fixed:_ in search mode, a match's expanded children also showed an ancestor
path (the runner caught it; `Explorer.test` now covers it). `App.test`'s discard test looked for a
**Name** header that S4R3 renamed "Name, sorted ascending", and failed before this package.

It passes at the default 10% scale and at full volume (`S6_VOLUME_SCALE=1`: 10,000 roots, the
20,000-child branch, 19,901 in the draft, scrolled end to end in every context; about 110 s).

_Open:_ a record opened
elsewhere reveals its ancestors' branches but does not scroll a long group to it. At eight levels the
default 248px rail truncates names (the rail widens to 380px). Visual baselines and dedicated
accessibility-gate scenarios for the tree remain S7 scope.

#### S7: Composed volume acceptance

**Scope:** a real-backend browser runner over the S1 fixture and the starter model that scrolls,
seeks, jumps by scrollbar and page number, jumps to the end, reopens from a copied URL and opens a record deep in the tree, in live,
draft and history contexts. It adds accessibility scenarios for the scrolling list and the tree,
updates visual baselines for tables that lose their page buttons (reviewed, not blind), and records
the S1 measurements again against the budgets.

**Exit:** budgets met in all three contexts; accessibility and visual gates pass; the runner is
registered in the [execution guide](testing/EXECUTION_GUIDE.md).

**Delivered 2026-09-26, with the exit's budget clause open for three request kinds (below).**
`e2e/s7-volume-acceptance.mjs` (`test:browser:s7`) composes the track in one journey per context. On
the volume fixture's items lens and the starter's codelist lens (72 records, ten a page), in live,
draft and history: scroll both ways with the wheel, a scrollbar click from the start, seek by name,
**Go to end**, a page number, and the copied URL reopened at the same row. Each landing is checked
against the same context's API read at that position, so draft renames, tombstones and new records
are compared with what the draft holds. Then a record deep in the tree: the volume model's deep node
(seven node levels under its group) found by the tree's search with every ancestor in its path and
opened from the match; the starter's master value reached by keyboard alone, Ctrl+End crossing the
codelists' first 50-row window to the 72nd codelist. The record opens in the same context and is
marked current. The lens journey repeats at 390px for both models. The runner reports each context's
API read times as the browser saw them. It passes at the default 10% scale and at full volume
(`S7_VOLUME_SCALE=1`, about 115 s).

The accessibility and visual gates gain `scrolling-list-tree`, light and dark: the codelist lens at
page 3 of 7 (window scrollbar, footer fields) beside a 60-codelist tree branch scrolling in its
group, focus on a row inside it (`helpers/acceptance-data.mjs`, seeded after the other gate pages
so they are unchanged). The accessibility gate also rejects a control appended to the tree. All
visual baselines were refreshed after inspection; the changes are S6's root-type heading in every
sidebar and, in dark, the footer fields below.

_Found and fixed._ A draft or history single-record read returned an empty `path` (pages and write
responses had it since S4R1), so draft and history record pages showed no ancestor breadcrumb and
the tree could not reveal the active record's branch. `get_object` now uses `snapshot_reads.object_path`,
one lookup per level; `test_context_read_parity` compares the single-record path in every context
with live, and fails without the fix. In the dark theme, the list footer's page and **Go to** fields
kept the browser's light field colours with the footer's muted text (below AA contrast); they now
share the text-input treatment in `base.css`. The accessibility gate's duplicate-landmark self-check
injected the label `Objects`, which no panel has used since S5, so it no longer produced a duplicate
and the gate failed before reaching its pages; it now repeats a label on the page. The `WP1-002`
exception it guarded matched nothing and was removed.

_Results_ (full volume, `volume_baseline.py --scale 1 --repeat 5`, same machine as S1; two rows are
new in S7):

| Request | Live | Draft | History |
| --- | --- | --- | --- |
| objects: first page | 3.0 ms · 5 · 79 | 5.1 ms · 6 · 4 | 3.9 ms · 5 · 3 |
| objects: middle page | 3.6 ms · 6 · 81 | 5.8 ms · 7 · 4 | 4.8 ms · 6 · 3 |
| objects: last page | 4.0 ms · 6 · 81 | 6.2 ms · 7 · 4 | 5.1 ms · 6 · 3 |
| children: heavy parent, first page | 3.3 ms · 5 · 65 | 4.9 ms · 6 · 4 | 4.1 ms · 5 · 3 |
| children: heavy parent, middle page | 3.4 ms · 6 · 66 | 5.9 ms · 7 · 4 | 4.8 ms · 6 · 3 |
| children: small parent | 2.3 ms · 5 · 19 | 5.0 ms · 6 · 4 | 3.1 ms · 5 · 3 |
| relations: 1,500-relation record | 7.5 ms · 7 · 103 | 11.2 ms · 8 · 4 | 9.2 ms · 7 · 3 |
| relations: heavy parent | 41.4 ms · 7 · 85 | 74.2 ms · 8 · 4 | 63.9 ms · 7 · 3 |
| record: single read | 1.9 ms · 5 · 7 | 2.9 ms · 6 · 4 | 2.2 ms · 5 · 3 |
| objects: last page by from=end, total | 7.2 ms · 6 · 81 | 44.9 ms · 7 · 4 | 10.7 ms · 6 · 3 |
| objects: backward page from the middle | 3.7 ms · 6 · 83 | 6.9 ms · 7 · 4 | 4.5 ms · 6 · 3 |
| objects: seek by name, total | 8.1 ms · 8 · 83 | 45.8 ms · 9 · 4 | 10.8 ms · 8 · 3 |
| objects: position ¾ deep, total | 12.5 ms · 6 · 81 | 55.8 ms · 10 · 4 | 15.7 ms · 6 · 3 |
| children: heavy parent, position ¾ deep, total | 5.2 ms · 6 · 65 | 22.4 ms · 10 · 4 | 7.3 ms · 6 · 3 |
| roots: top-level page, total | 3.4 ms · 5 · 64 | 8.5 ms · 6 · 4 | 4.6 ms · 5 · 3 |
| relations: 1,500-relation record by name, total | 8.5 ms · 8 · 103 | 14.8 ms · 9 · 4 | 12.6 ms · 8 · 3 |
| relations: 1,500-relation record, search | 6.8 ms · 7 · 102 | 11.2 ms · 8 · 4 | 9.9 ms · 7 · 3 |
| relations: 1,500-relation record by rank | 9.5 ms · 7 · 101 | 16.7 ms · 8 · 4 | 16.5 ms · 7 · 3 |
| relations: 1,500-relation record by group, total | 26.3 ms · 8 · 102 | 48.5 ms · 9 · 4 | 41.8 ms · 8 · 3 |
| relations: heavy parent by rank | **85.0 ms** · 7 · 85 | **159.0 ms** · 8 · 4 | **161.6 ms** · 7 · 3 |
| children: heavy parent by rank | 96.4 ms · 9 · 65 | **130.2 ms** · 10 · 4 | 88.9 ms · 9 · 3 |
| relations: heavy parent by group | **101.6 ms** · 7 · 85 | **204.1 ms** · 8 · 4 | **186.6 ms** · 7 · 3 |
| relations: deep node by top node | 6.8 ms · 12 · 14 | 10.6 ms · 13 · 4 | 6.3 ms · 12 · 3 |
| objects: search by name, total (S7) | **884.4 ms** · 6 · 42 | **885.2 ms** · 7 · 4 | **702.5 ms** · 6 · 3 |
| record: deep node (S7) | 2.6 ms · 11 · 13 | 7.5 ms · 12 · 4 | 3.3 ms · 11 · 3 |
| write: rename one record | 3.7 ms · 13 · 9 | **4,855.2 ms** · 30 · 216,944 | — |

_Against the budgets._ Budgets 1 and 2 hold for every read in every context (`pytest -m volume`,
the new rows included); the single-record read in drafts and history gains one statement per
hierarchy level for its path (a constant for a given record). Budget 3 holds for every S1 scenario
and every S3/S4 read, and fails for three request kinds, all outside S7's scope to fix:

1. **Draft write** (4.9 s): S2b, scoped and not yet delivered. _Resolved by S2b: 7.5 ms._
2. **Attribute and ancestor sorts over the 20,000-child parent** (85–204 ms): the S4R1 open item;
   precomputed sort keys are later storage work. _Deferred until after 0.9 (D26)._
3. **Whole-type name search** (0.7–0.9 s, every context, live included), new in S7. A contains-match
   cannot use the name index, and with fewer matches than a page the read scans the type; the total
   adds a second scan. The tree's search (S6) sends one per type of the application, and the lens
   and pickers search the same way. The browser runner saw it as the slowest tree read. It needs a
   decision: an indexed search (SQLite FTS5 or PostgreSQL trigram), a prefix match for the tree, or
   search without a total. _Decided: an indexed search (D25), scoped as S8. Resolved by S8: 37 / 73 / 40 ms._

The browser runner's medians were 9–17 ms per read at full volume. A context's first lens load with
its total took 0.6–1.3 s in the browser against about 45 ms warm in the baseline, which points to a
cold SQLite page cache after server start; it is observed, not measured separately.

_Open:_ budget item 2 above (item 1 closed by S2b, item 3 by S8); the S6 open item (a record opened elsewhere does not scroll a
long group to it) is unchanged, so the volume runner opens the deep node through search rather than
from a cleared tree. The edge loading marker is still covered by component state only.

#### S8: Indexed name search

**Scope (D25):**

1. A search index over each record's name and its `searchable` fields, in live, revision,
   draft-base and draft rows, kept by the same write paths as the typed value index (the flush hook
   for snapshot rows, the live write services for live rows) and built by the migration.
2. `search` keeps its meaning, a case-insensitive "contains" match over the same fields, and answers
   from the index in every context, with and without a total. SQLite's FTS5 trigram tokenizer
   matches substrings of three or more characters; how a one- or two-character search answers is
   decided in the package (measured scan with a bound, or prefix match on the name index), and the
   choice is stated in API.md.
3. The draft arm applies the overlay rule as other draft reads do: a base match hidden by a draft
   row does not count, a draft match counts unless deleted.
4. Draft writes stay bounded (S2b): an index update costs the rows written.

**Exit:** `objects: search by name, total` within 100 ms at full volume in all three contexts; the
parity test covers search in every context; `%`, `_` and non-ASCII text match as before; the
migration meets the AGENTS.md startup rules; the S6 tree search and the S7 runner pass.

**Delivered 2026-09-26, with the index over text values only (scope item 1 narrowed, below).**
Migration `20260926_03` adds two SQLite FTS5 tables with the `trigram` tokenizer, over
`attribute_values.text_value` (live) and `snapshot_attribute_values.text_value` (revision,
draft-base and draft rows). Each is external content keyed by the value row's `sequence_id`, so it
stores no text of its own, and three triggers per value table keep it equal to the column on every
insert, update and delete. Every write path, ORM or bulk, therefore maintains it at the cost of the
rows it writes (item 4); FTS5's `integrity-check` holds after live, draft, publication and discard
writes. `Base.metadata.create_all` builds the same objects (`models/search_index.py`).

_Why names are not indexed._ Measured at full volume, the S7 cost was not the name: a `LIKE` over
the (type, name) index a search already walks takes about 20 ms per 100,000 records. The cost was
the correlated look-up of each non-matching record's values (0.7–0.9 s). A search driven entirely
from a trigram index over names and values answered a rare phrase in 5 ms but a common one
("Item", every record) in 0.4–0.6 s, because it sorts every match; SQLite has no statistics to pick
between the two plans. So a search keeps walking the name index and matches the name on the row,
and looks a value up only for the records the value index names.

_How a search reads the index_ (`objects._search_predicate`, `indexed_value_match`). For a search of
three or more characters, a record's value look-up is guarded by "the record is among the
candidates": the value rows whose text the index matches, mapped to the listed rows by sequence ID,
which the type and parent indexes already hold. A bounded, uncorrelated count of the index's
matches (at most 10,001) is evaluated once per statement; past 10,000 matches the guard is skipped
and each record is looked up as before, which is then the cheaper plan. The `LIKE` decides in every
case, so the index changes which records are read, never which match (item 2); a test forces the
per-record path and compares every search in every context. One- and two-character searches have no
trigram and read each record (item 2's short-search decision: a measured scan, stated in API.md).
Relation lists, bounded by their anchor, keep the per-record look-up.

_Draft overlay_ (item 3). A draft's candidates come from its base's values and its own. A base
value the draft replaced, a tombstoned record, or a base and a draft row sharing a sequence number
may name a row that does not match; the `LIKE` on the effective row's values drops it. The draft's
replaced and added parts, as small as the draft, skip the index: two fixed trigram look-ups cost
more than their few rows.

_Two paging changes the budget needed._ A draft total counted the base-plus-overlay union, which
checks every base row against the overlay (45–56 ms at full volume in S7, before any search). It is now the
base part's count, less the replaced part's, plus the added part's, in one statement: the same parts
S4R6 position reads use. And a first or position page that reaches the end of the list knows its
total, so it runs no count. Both apply to every list, not only searches.

_Results_ (full volume, `volume_baseline.py --scale 1 --repeat 5`; unchanged rows omitted, three
rows new in S8):

| Request | Live | Draft | History |
| --- | --- | --- | --- |
| objects: last page by from=end, total | 8.5 ms · 6 · 81 | 18.5 ms · 7 · 4 | 10.2 ms · 6 · 3 |
| objects: seek by name, total | 9.5 ms · 8 · 83 | 20.5 ms · 9 · 4 | 10.8 ms · 8 · 3 |
| objects: position ¾ deep, total | 13.2 ms · 6 · 81 | 31.1 ms · 10 · 4 | 16.0 ms · 6 · 3 |
| objects: search by name, total | **36.7 ms** · 5 · 42 | **72.7 ms** · 6 · 4 | **39.5 ms** · 5 · 3 |
| objects: search by code, total (S8) | 53.7 ms · 6 · 82 | 89.9 ms · 7 · 4 | 56.1 ms · 6 · 3 |
| objects: common search, total (S8) | 32.0 ms · 6 · 79 | 42.9 ms · 7 · 4 | 36.0 ms · 6 · 3 |
| objects: two-character search, total (S8) | 31.8 ms · 6 · 79 | 39.8 ms · 7 · 4 | 32.3 ms · 6 · 3 |

The name search was 884 / 885 / 703 ms (S7). The other rows are within noise of S7, with the
attribute and ancestor sorts over the heavy parent still the D26 exception. Outside the table, with
`includeTotal` over 100,000 items: a two-character search that few names contain reads every
record's values (0.4–0.7 s), as does a phrase in every code and no name (`ITEM-0`, 0.4–0.5 s, as
before S8). The migration fills both indexes in about 2 s at full volume and adds about 12 MB; the
volume fixture now seeds in about 45 s (was 25 s) because the triggers index its bulk inserts.

_Open:_ names are matched by walking the type's name index, about 20 ms per 100,000 records, so a
type of millions would need the name trigram index and a planner choice between the two plans; the
PostgreSQL form (trigram GIN, with statistics) arrives with 0.10. The 10,000-match bound counts a
phrase's matches in every revision, draft base and draft (the count stays bounded by not filtering
them), so a workspace with many publications falls back to the per-record look-up at a lower share
of its own records; the result is the same, only slower. A draft page that scans its whole
base, such as a search matching few records, still checks every base row against the overlay before
the search (about 30 ms of the draft's 73 ms): SQLite evaluates the arm's own terms before a term
pushed into it.

_Review fix (2026-09-26)._ The migration and the search query assumed SQLite, while
`docker-compose.yml` runs PostgreSQL: the upgrade would stop at `CREATE VIRTUAL TABLE … USING fts5`
and every search of three or more characters would name a table that does not exist. The migration
now changes nothing on another dialect, and the index guard is a `search_index.SqliteOnly` element
that compiles to `true` there, so a PostgreSQL search reads each record's values as before S8, with
the same results. `test_search_index` compiles a live and a draft search for both dialects and runs
the migration against a PostgreSQL-named bind. Not exercised: a real PostgreSQL server.

## Track W — Workspace terminology and capability boundaries

Delivers [ADR-031](DECISIONS.md#adr-031--workspace-terminology-and-deployment-capability-boundaries).
"Workspace" currently names the catalogue scope, the prefix of its drafts and revisions, and the 0.8
steward screens. `WORKSPACE_ADMIN_MUTATIONS_ENABLED` gates both catalogue administration and the data
draft workflow. Track W gives each concept one name and each operation group its own gate.

Unlike Track S (principle 4), Track W renames API routes and fields deliberately. Nothing is in
production before 1.0, so there are no aliases; the change is still planned as one migration with
full verification.

Order: W1 → W2 → W3 → W4 → W6. W1 may run at any time. W2 follows S7 and precedes A2 and B2 (D15). W5 is
independent and may run at any time. W6 adds deletion to the W4 screen (D27).

#### W1: Terms in documentation

**Scope:** update the [glossary](product-functionality/GLOSSARY.md) to the ADR-031 terms and add the
Live / change set / publication relationship to one workspace. Rename Milestones A and B to
**Translation editor** and **Hierarchy editor** in ROADMAP, TODO, this plan and the functionality
catalogue. Correct the stale "non-default workspace detail gap" notes in PRODUCT and USER_JOURNEYS
after checking the current behavior.

**Exit:** no document uses "workspace" for the 0.8 screens; the glossary defines every ADR-031 term.

**Delivered 2026-09-26.** The glossary defines every ADR-031 term and verb, shows one workspace's
live data, change sets and publications, and lists the old names the code keeps until W2. Milestones
A and B are the Translation editor and Hierarchy editor in ROADMAP, TODO, this plan and the
functionality catalogue; ARCHITECTURE and two earlier plans no longer call a steward screen a
workspace. The non-default workspace detail gap was repaired by 0.6 WP9 (`ObjectDetail` passes the
workspace; `e2e/wp9-navigation.mjs` opens detail, children, relationships and history in a
non-default workspace), so the notes in PRODUCT, the product guide, user journeys, user stories and
the functionality catalogue now say so. Left open: other pre-WP9 status markers in the catalogue
(F03, F05, F06, J02) and PROJECT_STATUS's 0.8 progress.

#### W2: Rename change sets and publications

**Scope:**

1. Migration: `workspace_draft*` tables become `change_set*`, `workspace_revision*` become
   `publication*` (`revision_number` → `publication_number`), with their columns, indexes and constraints. Stored audit event and aggregate
   names are rewritten in the same migration.
2. API: `/workspace-drafts` → `/change-sets`, `/workspace-revisions` → `/publications`,
   `/workspaces/{key}/drafts` and `/revisions` accordingly; `/activation` on a change set →
   `/publication`; `POST /workspaces/{key}/retirement` → `POST /publications/{id}/withdrawal` (status `withdrawn`,
   `withdrawnAt`). Today that route withdraws the current publication, not the workspace; workspace
   retirement is `PATCH /workspaces/{key}` with `status: "retired"` and keeps that name; `workspaceDraftId`, `workspaceRevisionId`, `revisionNumber`,
   `expectedWorkspaceDraftVersion` and error codes such as `workspace_draft_model_release_conflict`
   take the new names. The OpenAPI lock is re-baselined.
3. Backend services, schemas and tests; frontend types, API client, route state, URLs, components
   (`WorkspaceDrafts`, `WorkspaceHistory`) and labels ("Draft · name" → "Change set · name", "Activate draft" → "Publish change set",
   "Historical snapshot" and "Revision N" → "Publication N", with date and model release as secondary
   text); e2e runners and fixtures.
4. Route shape: lists stay nested under their workspace (`/workspaces/{key}/change-sets`,
   `/workspaces/{key}/publications`), single items are flat by global id (`/change-sets/{id}`,
   `/publications/{id}`). The one exception, `PATCH /workspaces/{key}/drafts/{id}/model-release`,
   becomes `PATCH /change-sets/{id}/model-release`. API.md records the rule for future endpoints.
5. API.md, ARCHITECTURE, README and the functionality catalogue.

**Exit:** the ADR-031 acceptance search finds no old name; migration checks pass (clean bootstrap,
upgrade from the previous head, restart, interrupted migration); full backend and frontend suites and
every browser runner pass.

**Delivered 2026-09-26.** Migration `20260926_04_change_sets_and_publications` rebuilds each table
into a `_w2_` copy from DDL frozen in the revision and swaps it in, so it renames constraints, changes
the publication status CHECK (`retired` → `withdrawn`) and the snapshot owner kinds, and resumes a run
stopped after any statement; `test_change_set_rename_migration` covers upgrade with data in every
context across two lifespan starts, the schema equal to a clean bootstrap, three interrupted states,
a refused source of another shape, the downgrade to `20260926_03` and the non-SQLite refusal. The
publication response gained `modelReleaseKey` and `modelReleaseVersion` so the browser can show
"Publication N · model X · date" (item 3). Withdrawal takes the publication ID in the path as its
claim and no body. The rename also covers the audit payload keys, the `drafts` test marker and the WP9
runner names. Earlier plans, ADRs and review notes keep the names they were written with, as ADR-031's
consequences allow; the ADR-031 terms table names the old terms on purpose.

#### W3: Narrow the workspace administration capability

**Scope:** move change-set create, update, delete, model-release change, validation and publish, and
publication withdrawal, from the workspace administration router to an always-registered router,
keeping the retired-workspace refusal. `WORKSPACE_ADMIN_MUTATIONS_ENABLED` then gates only workspace
create, rename, retire and set default. Update README, ARCHITECTURE's capability table and the CHANGELOG.

**Exit:** with the flag off, catalogue mutations return 404/405 and the change-set workflow passes end
to end; with it on, both work; `MODEL_ADMIN_MUTATIONS_ENABLED` tests are unchanged.

**Delivered 2026-09-26.** The change-set and publication routes moved from `routers/workspaces.py`
to an always-registered `routers/change_sets.py` (OpenAPI tag `change-sets`); `workspaces.admin_router`
keeps workspace create, update (rename, retire) and the default switch. The retired-workspace refusal
lives in the change-set services and is unchanged. `test_change_set_workflow_runs_end_to_end_without_workspace_administration`
runs with the flag off: catalogue mutations return 405, then a change set is created, renamed,
repinned, edited, validated, published, its publication withdrawn and a second change set discarded;
after retirement through a flag-on app, creation returns `workspace_retired`. The OpenAPI lock is
re-baselined for the tag alone. The browser never gated the workflow on `manageWorkspaces`, so it is
unchanged.

#### W4: Workspace administration screen

**Scope:**

1. A global **Workspaces** screen in the header next to **Models**, in the same list-and-detail
   layout: all workspaces including retired, create, rename, retire and set default, with the
   existing concurrency claims. Shown only when `workspaceAdmin.manageWorkspaces` is true.
2. A **Manage workspaces** link in the selector dropdown when the capability is on.
3. The selector renders as a read-only label while exactly one workspace exists.
4. Read-only capability status on the Models and Workspaces screens: a disabled group names the
   environment setting that controls it.
5. Change sets and publications stay per workspace, as renamed in W2.

**Exit:** component tests for each state; a browser runner creates a second workspace, switches to
it, sets it as default and retires it; accessibility and visual gates pass.

**Delivered 2026-09-26.** `features/workspaces/WorkspaceAdmin.tsx` is the `/workspaces/<key>` route
in the Models layout: the catalogue (every status, Default and Retired marks) in the sidebar, the
selected workspace (the default when none is named) as the page. Create suggests a key from the
name; rename, retire and reactivate claim the workspace version and set default the runtime-state
version. A conflict reloads and names the current state, keeps the user's input and waits for them to
act again; the default's Retire is disabled with its reason. Reactivation was added because the
screen lists retired workspaces and the API already allows it. The selector gains a trailing
**Manage workspaces** option (a `ComboBoxField` action that never becomes the selection) and becomes
a labelled group with that link when an unfiltered read finds exactly one workspace. Item 4 needed the
setting names in the contract rather than in the browser, so each capability group gains a required
`setting` field (OpenAPI lock re-baselined; additive). `features/administration/CapabilityStatus`
shows both groups on both screens. A direct `/workspaces` link with the flag off stays read only, and
the header then marks Workspaces as the current page rather than hiding it. Setting the default also
moves the router's fallback, so a URL without `workspaceKey` lands in the new default.

Evidence: `WorkspaceAdmin.test` (15: load and retry, flag off, create and duplicate, rename and
conflict, set default and conflict, retire, refused retirement, reactivate, unknown workspace),
`WorkspaceSelector.test` (+5), `App.test` (+2), `ModelWorkbench.test`, `routes.test`; backend
capability, OpenAPI and workspace tests. `test:browser:w4` (19 checks, two harnesses, flag on then
off) does the exit journey plus the conflicts, keyboard creation and 390px; axe is clean on its six
states. `test:a11y` (20 pages, including `workspaces-admin` light and dark) passes. `test:visual`
passes after reviewing the diffs: the 15 earlier baselines changed only in the header entry, the
single-workspace label and the Models capability block; `workspaces-admin-light`/`-dark` are new.
`test:browser` and `test:browser:wp12` were rerun for the shared selector and Models screen and pass.
Limits: an axe scan with the selector popover open covers the popover only (React Aria hides the rest
of the page while it is open); reactivation and the in-dialog retirement refusal have component
evidence only; the full suites are left to build acceptance.

#### W5: Model activation versus concurrent live writes

**Background:** the registry's publication guard only covers the moment a request resolves the active
release, not the whole request. Only draft-base capture takes `BEGIN IMMEDIATE`; ordinary live writes
neither lock nor recheck the active release inside their transaction. A write resolved under release
A may therefore commit after an incompatible release B activates, inside one process as well as across
instances sharing a database. Unverified; found while documenting split deployment (D17).

**Scope:**

1. A focused backend test: hold a live write resolved under release A, activate a release B that
   makes that write invalid (for example a newly required attribute), then let the write commit.
   Cover object, attribute and relation writes, and draft-base capture as the protected reference.
2. If the write commits under the wrong release: make live writes and activation mutually exclusive
   in the database, or recheck the active release identity inside the write transaction and return a
   recoverable conflict. Choose the smaller change that also holds across processes.
3. If the write is already refused: record the mechanism in ARCHITECTURE and keep the test.
4. Update ARCHITECTURE's split-deployment caveats with the result.

**Exit:** the test passes on SQLite; the caveat is either removed or restated precisely.

**Delivered 2026-09-26.** Confirmed: with release A resolved and an incompatible B activated before
the write continued, a live object create (B makes an omitted attribute required), an attribute
delete (same) and a relation create (B tightens the pair to one-to-one) all committed; draft-base
capture was already refused. Fix, recheck plus exclusion: `resolve_model_snapshot` binds the session
to the release it resolved, and a `before_commit` hook flushes and rereads the active release in the
write transaction, refusing with `409 model_release_changed` (nothing saved). Activation now starts
with `BEGIN IMMEDIATE` (row lock elsewhere), so its compatibility check cannot miss a write that
flushed first; `409 model_activation_retry` if the busy timeout expires. The hook covers every
request that resolved the active release, including mapping writes, deletions and publishing,
without changing service signatures; both locks are database-level, so the result holds across
processes. ARCHITECTURE's caveat is replaced by the guarantee, and the publication-guard caveat is
restated for reads only. Evidence: `test_w5_activation_write_race` (5 cases: three live writes, the
reverse order where activation waits for a flushed write and then refuses, and capture as the
reference); each half of the fix was removed once to confirm its test fails. Focused suites for
activation, live records, relations, deletion, publish, mapping replacement, capture and the OpenAPI
lock pass (238 cases); Ruff clean. Not exercised: two OS processes, and a non-SQLite database.

#### W6: Delete an unused workspace

**Background:** a workspace key cannot be renamed (ADR-019), so a typo in a new key stays forever;
retirement only hides it from the active list. Deleting is safe only when nothing refers to the
workspace: objects, change sets (with their bases) and publications reference the key with
`RESTRICT`, while `relation_set_versions` cascade. Live objects are hard-deleted and discarding a
change set removes it and its base, so a steward can empty a workspace by hand. A publication is
only ever withdrawn, never removed, so a published workspace can never be deleted (D27).

**Scope:**

1. ADR-019 amendment: a workspace may be deleted when it is not the default, has no objects and no
   change sets, and has never been published. Everything else is retired. A deleted key may be
   created again.
2. API: `DELETE /workspaces/{key}?expectedVersion=N` on `workspaces.admin_router`, gated by
   `WORKSPACE_ADMIN_MUTATIONS_ENABLED`; `204` on success. Refusals, checked in this order inside one
   transaction that locks the workspace row: `404 workspace_not_found`,
   `409 workspace_is_default`, `409 workspace_has_publications` (retire instead),
   `409 workspace_not_empty` with `objectCount` and `changeSetCount` in the details, and the existing
   version conflict. Retired workspaces may be deleted under the same rule. A refusal changes nothing.
3. Workspace detail gains `deletable` and, when false, a `deleteBlockedBy` reason (`default`,
   `published`, `notEmpty`), so the screen does not guess. It is computed on detail reads only, not
   in the paged list.
4. W4 screen: a **Delete** action in the workspace detail when `deletable`, with a confirmation that
   names the key; otherwise the reason, suggesting **Retire** for a published workspace. After
   deletion the screen returns to the list, and the selector drops the workspace; a stale URL for the
   deleted key shows the existing not-found state.
5. API.md, CURRENT_FUNCTIONALITY (F-workspace administration), PRODUCT_GUIDE, ARCHITECTURE's
   capability table, COVERAGE_MAP (new C-WS-DEL row) and the CHANGELOG.

**Exit:** backend tests cover deletion of an empty workspace, re-creation of the same key, each
refusal with no data change (default, published then withdrawn, objects, change set, stale version),
deletion after the objects are deleted and the change set discarded, and 404/405 with the flag off;
the OpenAPI lock is re-baselined; component tests cover the deletable and each blocked state; the W4
browser runner creates a workspace with a mistyped key, deletes it and creates the corrected one.

**Delivered 2026-09-26.** `DELETE /workspaces/{key}` on `workspaces.admin_router` runs its checks and
the delete under `BEGIN IMMEDIATE` (row locks elsewhere), in the specified order, and rolls back on
any refusal; `workspace_delete_retry` covers a busy writer lock. Single-workspace responses (`GET`,
`POST`, `PATCH`) share `WorkspaceDetailResponse` with `deletable` and `deleteBlockedBy`, so the
screen keeps the reason current after rename, retire or set default; the paged list is unchanged.
Discovery found that SQLite does not enforce the `workspaces.key` foreign keys at runtime, so neither
`RESTRICT` nor the `relation_set_versions` cascade exists in practice: deletion removes relation-set
versions itself, and `resolve_workspace(require_active=True)` now records the key for a
`before_commit` recheck beside W5's. A live write resolved before its workspace was deleted then
returns `404 workspace_not_found` instead of committing an orphan row (confirmed by removing the
hook); a write resolved before retirement likewise returns `409 workspace_retired`, which closes the
same window for retirement. The ADR-019 amendment, API.md, ARCHITECTURE, README, the functionality
catalogue, the product guide, COVERAGE_MAP (C-WS-DEL), UI_ACCEPTANCE (W4 row) and the CHANGELOG
are updated.

Evidence: `test_w6_workspace_deletion` (8: empty, retired, re-create, default, published then
withdrawn and emptied, objects and a change set then removed with relation-set versions cleaned up,
stale version, flag off 405, held live write); adjacent workspace, OpenAPI, W5, relation, cascade,
mapping, record CRUD, request-scope, context and withdrawal suites (179) and Ruff pass.
`WorkspaceAdmin.test` (+7: delete, three blocked reasons, retired published, flag off, refusal,
conflict), `App.test` (+1: leaving the screen after deleting the remembered workspace lands in the
default), `WorkspaceSelector.test`; format, lint (0 errors) and build pass. `test:browser:w4` (21
checks, step 11 new) deletes `nordcis` by keyboard, checks the stale URL, creates `nordics` and the
selector; axe is clean on the delete confirmation. `test:visual` passes; `workspaces-admin` and
`model-workbench` light and dark baselines were refreshed after review for the new capability and
default-reason wording. Not exercised: `test:a11y` (left to R1), a published or non-empty workspace in
the browser (component evidence only), two OS processes and a non-SQLite database.

## Pending items — revisit before R1

Gaps in the read API found on 2026-09-25. They are not scheduled work packages. Each is decided at the
latest before R1: scheduled into 0.8 as a package, moved to a later build in ROADMAP/TODO, or dropped
with a reason (D20). A package taken into 0.8 is written after W2, so it uses the ADR-031 names.

A parameterless "list everything" endpoint for object, relation or attribute value reads was
considered and rejected. Paging through live data across many requests is not a consistent snapshot
(API.md, object cursors), so full extraction stays with 0.9 export and the change feed (ADR-008).
Until then a publication (revision) read is the consistent full traversal. A flat list of attribute
values was also rejected: values only mean something with their object, which already returns
them, and "objects where attribute X = Y" belongs to the 0.9 advanced queries.

#### P1: Cross-type object lookup

_Moved to 0.9 (D20)._

**Gap:** objects are listed only per type (`GET /objects/{objectTypeKey}`). A record whose type is not
known, for example one found by name or external ID, cannot be looked up in one call.

**Shape to evaluate:** `GET /objects`, paged under the S3 contract, in live, change-set and
publication contexts. Search, filter and sort on built-in fields only (`name`, `id`,
`objectTypeKey`, parent, created and updated). A repeatable `objectTypeKey` narrows the list. Each
item carries its `objectTypeKey`. Model-declared typed filters stay on the per-type route. No branch
on type keys (principle 2); additive (principle 4).

**Uses:** global search, a lookup field that accepts several types, admin and debugging.

#### P2: Change set changes list

_Scheduled into 0.8 as a package after W2 (D20); written with the ADR-031 names._

**Gap:** a change-set read returns the complete graph as the change set sees it (base plus overlay
and tombstones). No endpoint lists only what the change set changed, so reviewing it means scanning
every record.

**Shape to evaluate:** a paged list of the change set's own object and relation entries, each with
its kind (`added`, `changed`, `removed`), the record's identity and type, and its before and after
versions. Field-level differences only if cheap. Validation and publication remain the only checks
against current live content.

**Uses:** reviewing before publish, the change-set screen, and integrations that stage changes.

#### P3: Relation edge list across the workspace

_Moved to 0.9 (D20)._

**Gap:** `GET /relations` needs `objectId`, because its items are expansions from that object
(direction plus the other object). The flat edge list that exists, `GET /workspaces/{key}/mappings`,
already returns edges of any relation type in live and change-set contexts. It has no publication
context, and its name suggests it covers mapping relations only.

**Shape to evaluate:** add publication context to the existing edge list and decide whether to rename
or document it as the general relation list, instead of a second endpoint. `GET /relations` keeps its
anchored shape; one endpoint does not return two response shapes.

## Sequence and dependencies

```text
Track S:      S1 → S2 → S3 ─┬─ S5 → S6 → S7 → S8
                            └─ S4 ─┘
Milestone A:  A1 ──────────────┐
              S2, S3 ─────────→ A2 → A3 → A3b → A4 → A5 → A6
              S5 ──────────────────────────────↗
Milestone B:  B1 ──────────────┐
              S3, S4 ─────────→ B2 → B3 → B4
              S6 ────────────────────↗
Track W:      W1, W5 (any time)
              S7 → W2 → W3 → W4 → W6
              W2 ─→ A2, B2
Pending:      W2 → P2 (D20; P1, P3 in 0.9)
Release:      S8, W6, W5, A6, B4, P2 → R1
```

A1 and B1 depend only on 0.7 and may be delivered while Track S is in progress. Everything else in
A and B follows the Track S packages named above, because both milestones browse large collections
through the S3 contract and the S5 list. Milestones A and B are independent of each other and may be
delivered in either order. If one of them is cut from 0.8, its view type is removed from schema 0.7
before release so the language never declares a view without a renderer (D9).

W2 lands before A2 and B2 so the new translation and hierarchy endpoints are written with the ADR-031
names rather than renamed afterwards. A2 and B2 already wait for S5 and S6, so the extra wait is W2
alone (D15).

## Milestone A — Relation matrix

### Outcome

A steward opens a collection as a matrix: its records as rows, the records of an ancestor type as
columns, and in each cell the row's related records that sit under that column's record. Each cell
says whether it holds one related record, several, only ones that fail the binding's condition, one
only in history, or none. The steward filters to rows with a given cell state in any selected column
across the whole list, not only the loaded page, and acts in the cell as the view allows: create a
related record, edit it, link an existing one or unlink it. Routine edits are live; a selected change
set stages them.

The engine builds the capability, not a domain. The starter model configures it three ways, each a
real task, so no one shape defines the contract:

| Starter view | Rows | Columns | Cells (relation, direction, binding) | Actions |
| --- | --- | --- | --- | --- |
| Codelist / Master value translations | codelists, master values | language | translation via `object-has-translation`, outgoing, required one-to-many, one per language | create, edit |
| Codelists by system | codelists | system | system value via `reference-has-system-representation`, outgoing, optional one-to-many | create, edit, link, unlink |
| Master values by system | master values | system | system value via `system-value-maps-to-master`, incoming, many-to-many | edit, link, unlink |

A catalogue model (price per market, listing per channel) is the same shape. The translation views
serve stories US-L03 and US-L04 and scenario SC-09 (translation half).

### Model facts the matrix relies on

- A cell record reaches its column record through containment: the column type can contain the cell
  type at some depth, possibly through recursive container types (translation groups, system groups).
  The column is an ancestor, not a field.
- The row and the cell record are joined by one declared binding, read from either end
  (`direction`). The binding may be required or optional and of any cardinality.
- When the binding declares `uniqueToAncestorTypeKey` (and optionally `uniqueWhenToAttributeEquals`),
  live writes, change-set validation and publishing already enforce at most one matching record per
  scope (ADR-014); the matrix reports a breach rather than enforcing it again.
- No ancestor path is stored. Ancestry is walked through `parent_object_id`, so a read that needs a
  cell record's column costs the hierarchy depth per record.

All of these come from the model. The matrix reads the binding, its features and the containment
chain; runtime code never names a starter type or relation.

#### A1: Schema 0.7 — `relationMatrix` view contract

**Scope:**

1. Accept `schemaVersion: "0.7"` (done by S4R2). Schema 0.5 and 0.6 models reject the new view type
   at the view's `type` path.
2. Add `RelationMatrixViewDefinition` (type `relationMatrix`) to the `ViewDefinition` union with
   config: `relationTypeKey`, `direction` (`outgoing`: the row is the binding's `from` end;
   `incoming`: its `to` end), `rowObjectTypeKey`, `columnObjectTypeKey`, `cellObjectTypeKey`,
   `rowColumns`, `columnLabelField`, `cellFields` (cell-record fields shown and edited in a cell),
   `searchFields`, `cellActions` (a subset of `create`, `edit`, `link`, `unlink`; empty or absent is
   read-only) and `pageSize` (1–100).
3. Validation rules in `services/model/validation/application_rules.py`, each raising
   `ModelReferenceError` at the failing node:
   - the three object types exist and belong to the application;
   - the relation type exists, is not containment, and has a declared binding in the configured
     direction;
   - the column type can contain the cell type at some depth through `parentRelationTypeKeys`;
   - `rowColumns` are fields of the row type; `columnLabelField` is `name` or a scalar attribute of
     the column type; `cellFields` are attached to the cell type; `searchFields` are `name` or
     searchable row attributes; lists are unique;
   - each cell action can succeed for this model: `edit` needs a writable cell field; `unlink` is
     refused on a required binding, which the engine never lets go on its own; `create` needs every
     required cell attribute without a default among `cellFields`, and no required relation into the
     cell type besides the view's own relation.
4. Lens grouping (ADR-029): a `relationMatrix` groups under its `rowObjectTypeKey`, beside that type's
   table when the application has one.
5. Starter model: the four views above, in the applications that hold their column and cell types.
6. Frontend: extend the `ViewDefinition` union in `src/types/model.ts` and register a generic
   placeholder whose labels come from the model; A4 replaces it.
7. Document the contract and its validation rules in `APPLICATION_MODEL.md`.

View definitions persist as JSON with a `view_type` string, so no database migration is needed.

**Exit:** a schema 0.7 model with the view parses, installs and activates; 0.5 and 0.6 models still
do; each rule rejects an invalid configuration with a precise JSON pointer; all three binding shapes
validate, and so does the starter with every type and relation key renamed; the generated S1 model
(extended in A2) validates. Focused `model` group tests and the frontend build pass.

**A1 delivered 2026-09-27, corrected the same day.** The first delivery added a `translationMatrix`
type whose keys and rules (a required one-to-many binding scoped to the column type, translation and
language vocabulary) fitted translations only; it was replaced before commit by the contract above.
`_check_relation_matrix_view` applies the rules in the order listed and `_cell_action_refusal` the
action rules; a required relation counts as satisfied by the view's own relation key, as the engine
checks it on create. The starter's translations application holds the two translation views (and now
includes `codelist`); the systems application holds the two system views (and now includes
`codelist`). Neither application has a table for those row types, so each row type appears there as
a sidebar collection whose only lens is its matrix. The placeholder names the row, column and cell
types from the model. The content release stays 0.8.0, so a database that installed the S4R2 0.8.0
content refuses to start with a release identity conflict until it is re-bootstrapped. Found on the
way: `mappingGrid` duplicate-field errors pointed at `…/config/config/<field>`; fixed with a
regression test.

Checks: `pytest tests/test_model.py` (every rule with its exact pointer over the three shapes, a
column several containment levels above the cell, strict shape, read-only views, a renamed-keys model,
the 0.5/0.6 starters and the 0.6 generated model), `-m "model or contract"`,
`test_model_schema_upgrade.py`, `test_translations.py` and `ruff check app/ tests/`; Vitest
`model.test.ts` (grouping in both directions) and `CollectionView.test.tsx` (the placeholder lens for
two row types); frontend format, lint (0 errors, the 8 recorded warnings) and build. `test:visual` passes; the
`collection-table-system` and `record-detail-system` baselines were updated after inspection for the
systems sidebar's two new collections. A one-off harness check opened both starter matrix
placeholders by keyboard at 1440px and 390px (no overflow, axe clean) and its screenshots were
inspected; the placeholder's UI acceptance row records it. Not run: `test:a11y` and a registered
runner for the placeholder, which A4 replaces with the real lens and its own runner.

#### A2: Relation matrix query

**Scope:**

1. `GET /api/v1/workspaces/{workspaceKey}/relation-matrix` with `applicationKey`, `viewKey`, optional
   `parentObjectId` scope for rows, `search`, `sort`, one of `changeSetId` or `publicationId`, and the
   S3 paging parameters (`cursor`, `from`, `includeTotal`, `seek`, `position`) for rows.
2. Columns: `columnIds` (explicit, at most 20) or, when omitted, the first page of column records in
   name order; the response carries a `columnsNextCursor` so the UI can page columns (D10). Columns
   are records of the column type in the same context.
3. Each cell reports one state (D11), from the binding alone:
   - `one` — exactly one related record under the column that meets the binding's
     `uniqueWhenToAttributeEquals` condition (every record meets it when none is declared);
   - `several` — more than one such record, with `conflict: true` when the binding's
     `uniqueToAncestorTypeKey` is the column type in the outgoing direction (a change set can hold
     one before validation); otherwise several is an ordinary state;
   - `inactive` — related records exist, none meets the condition (only with a condition);
   - `historyOnly` — nothing in the current context, but a publication of this workspace held a
     related record under the same row and column;
   - `none` — none of the above.
   A cell returns each record's id, version, `cellFields` values and the relation's id and set
   version for writes, up to a bounded number of records with the count beyond it.
4. `state=<state>` together with `columnIds` filters rows before pagination: a row matches when any
   selected column's cell has that state. Totals count the filtered rows.
5. Implementation: page rows first; fetch their related records through the binding in one query;
   resolve each record's column with one recursive query up the containment chain (depth-bounded);
   fetch the `historyOnly` evidence in one query over publication relations for the page's rows. No
   per-row or per-cell requests. Change-set and publication contexts use the S2 base-plus-overlay
   and snapshot SQL. Both directions share one query, choosing the binding's end.
6. The row state filter decides across all rows, not a page. Resolve it with one recursive query
   from the selected column records down through container types to cell records (D12), and
   measure it against an S1 fixture extension with its own keys: 10,000 rows, 30 column records, a
   three-level container hierarchy under each column record and 150,000 cell records, a tenth failing
   the condition; plus a many-to-many incoming matrix over the same records.
7. Cursors bind view, context, scope, selected columns, state filter and sort.
8. Update API.md and the OpenAPI lock.

**Exit:** each state is produced in live, change-set and publication contexts for the three starter
shapes and the generated model; a filtered page deep in the list is correct and within its recorded
budget; the query count per page is constant; `historyOnly` never counts as `one`.

**A2 delivered 2026-09-27, closed with a temporary budget exception.** The route, its service
(`services/relation_matrix.py`) and D10–D11 behave as scoped. D12 is implemented as recommended and
measured over budget; the filter's results are correct and stay the oracle, and its time budget is
met by [A3b](#a3b-stored-cell-state-for-the-row-state-filter) before A4 (decided 2026-09-27). Found
on the way:

- Rows are every record of the row type in the workspace context, not only the view application's
  own: the starter's translation and system matrices list codelists and master values that
  `rdm-master` owns. Search covers the view's `searchFields` only; the object query builders gained
  that option and an ID predicate that also narrows a change set's overlay parts, so position reads
  stay exact under the state filter.
- A binding's `uniqueWhenToAttributeEquals` and `uniqueToAncestorTypeKey` describe its `to` end, so
  they apply only when the matrix reads it `outgoing`; read `incoming`, no cell is `inactive` or a
  conflict. `historyOnly` looks in every publication of the workspace for live and change set reads,
  and in earlier ones for a publication read; the cell lists the latest such publication's records.
- Creating a record with `initialRelations` does not advance the relation-set versions (only generic
  relation writes and cascades do). A3's create-from-cell relies on it: fix it there.
- `change_set_objects` lacks the parent and type indexes its ORM model declares (migration drift);
  the walk down uses an automatic index instead. A follow-up migration, not part of A2; scheduled as
  [A6](#a6-snapshot-table-index-drift), which found the drift on all four snapshot tables.
- SQLite plans recursive steps and page edges badly unless steered: each step outer-joins its
  children (a `CASE` keeps the join outer) with type and owner terms off the index, the page's cell
  CTE is `MATERIALIZED`, and page edges and cell records are found from the page rows, not by type.
- Two tests broken by A1 and already failing at HEAD were fixed: `test_mapping_replacement`
  (a required binding cannot keep a matrix's `unlink`) and `test_wp81a_context` (the attribute scrub
  now also clears `columnLabelField`).

_Volume fixture extension._ A `vol-matrix` application in the generated model (now schema 0.7): 30
columns, each over a three-level shelf hierarchy (8 leaf shelves), and 15 cells per group in the columns
of the group's parity (150,100 cells at full scale, a tenth inactive, 3,002 deleted live after
publication 1), a required conditioned binding scoped to the column read outgoing
(`cells-by-column`) and a many-to-many binding read incoming (`marks-by-column`) over the same cells.
The heavy, cited and small groups carry no matrix data, so every S1–S8 check reads what it did.
Matrix data comes from its own random stream, so the catalogue's IDs are unchanged. The full-scale
seed now takes about 17 minutes (was 18 s).

_Measurements_ (full shape, median of 3, same machine as S1). The first full run, before the plan
fixes above, gave unfiltered pages of 40–52 ms live and in change sets but 0.25–1.5 s in a
publication, and state filters of 0.27–76 s. After the fixes, a page's slowest statement is 6–15 ms
in every context and view (the page's cell statement; a publication count 32 ms), measured per
statement on the same database; a full baseline rerun is still to be recorded. State filters remain
over budget: over 10 columns (about 50,000 cells) the walk takes about 0.2 s and the pairs with their
condition 0.4–0.6 s warm, several seconds cold on the 1.3 GB database, and a page evaluates the filter
once per paging statement (page, count, position), so a filtered jump takes seconds.

_Budgets._ Held by `test_volume_baseline.py` with the other reads: each matrix scenario's statement
count is the same at both scales (11–16 by context) and it loads at most 45 ORM rows. The time budget
of 100 ms holds for unfiltered pages and fails for state filters.

_D12 outcome:_ over budget. The recommended fallback, a stored ancestor table, removes the walk but not
the per-request pass over every cell under the selected columns; meeting the budget likely needs a
stored per-cell state (row, column, counts) maintained by writes, a scoped follow-up with a migration.
**Decided 2026-09-27:** A2 closes with the filter as a temporary exception; the stored per-cell state
is scheduled as A3b, after A3 and before A4.

Checks: `pytest tests/test_relation_matrix.py` (8: the three starter shapes in live, change set and
publication; every state; filters with totals; cursor, position and `from=end` paging; cursors bound
to state and columns; column paging; row scope, search, sort, seek; set versions; refusals),
`tests/test_relation_matrix_volume.py` (6: the filter equals the rows whose cells show each state,
and a deep filtered page is the matching slice, in three contexts and both directions), and
`-m "model or queries or change_sets or mapping or contract or matrix or volume or records or
workspaces or model_admin"`, and `ruff check app/ tests/`. OpenAPI lock re-baselined; the paging
inventory counts 18 collections, the matrix seekable. Not run: the full suite (R1), frontend (no
frontend change).

#### A3: Writes from a cell

The existing object and relation APIs already create a record with its containment and initial
relations, edit it, and create or remove a relation, live or in a change set, in one transaction each
(ADR-014, ADR-022). This package adds what a cell needs to call them without asking the user for
context they already chose, for whichever `cellActions` the view declares.

**Scope:**

1. `GET /api/v1/workspaces/{workspaceKey}/relation-matrix/containers` with `applicationKey`,
   `viewKey`, `columnId`, context, `search` and cursor: the column record and the records under it
   whose type can directly contain the cell type, with their path below the column record. A column
   with exactly one container is marked as the default (D13).
2. `GET /api/v1/workspaces/{workspaceKey}/relation-matrix/link-candidates` with `applicationKey`,
   `viewKey`, `rowId`, `columnId`, context, `search` and cursor: cell-type records under the column
   record, each with `eligible` and, when false, a machine-readable reason (`alreadyLinked`, or the
   binding's cardinality would be exceeded), listed rather than hidden so totals stay truthful.
3. `create` from a `none`, `inactive` or `historyOnly` cell: `POST /objects` with the chosen container
   as parent, the row through `initialRelations` in the view's direction and `cellFields` as
   attributes. The name defaults from the row and column names; the user may change it.
4. `edit`: `PATCH` with `expectedVersion`, changing `cellFields`. A uniqueness breach returns the
   existing duplicate error with the conflicting record's id, so the cell can point to it.
5. `link` and `unlink`: create or remove the relation with the relation-set version from A2, so a
   concurrent change is refused rather than overwritten.
6. Tests at the real boundaries, over the translation and mapping shapes: live create, edit, link and
   unlink; change-set create, validation and publishing; a uniqueness breach staged in a change set
   and the same cell filled live, refused at publishing with the change set kept; a change set that
   moves a container to another column record, rechecked at publishing (ADR-014); a stale
   `expectedVersion` or relation-set version. Each refusal leaves nothing partial.

**Exit:** every write a cell performs succeeds or fails whole in live and change-set contexts, with
machine-readable errors that carry enough context for the cell to keep the user's input.

**A3 delivered 2026-09-27.** Both reads are in `services/relation_matrix.py` (`matrix_containers`,
`matrix_link_candidates`) over one walk down from the column record in the read's context, and
require the view to offer `create` or `link` (`422 relation_matrix_action_not_allowed`); they take
`changeSetId` but no publication, since nothing is written there. Decisions made on the way:

- The link and unlink claim is a generic addition to the relation API rather than a matrix endpoint:
  `POST /relations` and `DELETE /relations/{id}` take an optional `expectedRelationSetVersion` with
  `relationSetDirection`, claimed through `relation_set_versions.advance_set_versions` (the claimed end
  from the version read, the other end advanced once), live and in a change set. The mapping
  replacement remains the atomic set replacement; this is a conditional single write.
- Unlink needs the relation's own version, which A2's cell records did not carry: they now carry
  `relationVersion`.
- Candidate reasons mirror the writes: cardinality counts relations of the relation type at an end
  whatever the other end's type (as `validate_cardinality` and the change-set check do); `scopeTaken`
  is checked only when the uniqueness scope is the column type, other scopes are left to the write.
- The initial-relations gap found in A2 is fixed in both contexts, so A2's set versions changed.
- `duplicate_relation_scope` names the record already in the scope on every write path and in the
  publish diagnostic (`conflictingObjectId`, plus `conflictingRelationId` on writes).
- Found on the way: a change set's scope conflicts surface at publishing as `422
  workspace_graph_invalid` with the diagnostic in `details`, which the matrix cell can show; nothing
  new was needed there.

Checks: `pytest tests/test_relation_matrix_writes.py` (9: containers over nested, single and empty
columns, a column that holds cells directly, search, cursors, a change set's added and moved
containers; candidate reasons for one-to-many outgoing and many-to-many incoming bindings, and
`scopeTaken` on a model with a column-scoped binding; live create, duplicate, edit, stale version and
activation breach on the translation shape; live link and unlink with fresh, stale and half claims in
both directions; change-set create, a staged duplicate, claimed link, unlink and relink, validation
and publish; a staged translation filled live, refused at publishing with the change set kept; a
container moved to another column, refused live and staged then refused at publishing), `-m "matrix
or mapping or change_sets or records or contract or queries"` (after updating the A2 set-version
expectation and the OpenAPI lock and inventory), `test_volume_baseline.py` and
`test_relation_matrix_volume.py` (statement and row budgets hold with `relationVersion` read on the
page edges), and `ruff check app/ tests/`. Not run: the full suite (R1), frontend (no frontend
change; A4 consumes these reads), and a full-scale timing rerun of the page with the added relation
version column.

#### A3b: Stored cell state for the row state filter

_Scheduled 2026-09-27 (D12): after A3, before A4. Closes A2's temporary budget exception._

**Gap:** A2's row state filter walks down from the selected column records to every cell record and
pairs each with its row on every request, and once per paging statement (page, count, position). At
full volume it takes seconds against a 100 ms budget, so filtering to gaps across a whole list, the
matrix's main task, is slow exactly where it is used. A stored ancestor table would remove the walk
but not the pass over every cell, so it is not pursued.

**Outcome:** the filter reads a stored state per (row, column) instead of deriving it, so a filtered
page, its total and a position jump cost an indexed lookup whatever the number of cells, in live,
change-set and publication contexts, with results identical to A2's.

**Scope:**

1. A derived table of cell states, keyed by workspace, context owner (live, a publication or a change
   set), matrix shape, row record and column record, holding the cell's record count and the count
   meeting the binding's condition. A matrix shape is what a view declares and the model derives:
   relation type, direction, row, column and cell types, and the binding's condition. Views with the
   same shape share rows; nothing names a starter type, relation or application.
2. `historyOnly` from stored state too: a publication's states are computed once when it is published
   and never change, so "an earlier publication held one" is a lookup over publication states.
3. Maintenance in the same transaction as every write that can change a state: object create and
   delete (cascades included), an edit of the condition attribute, relation create and delete, a
   parent move (which can move many cells between columns), and publishing. Each write recomputes the
   (row, column) pairs it touches from the records rather than adjusting counts, so a missed update
   cannot accumulate drift. One service owns the recomputation, in the manner of
   `services/snapshot_values.py`; bulk inserts outside the ORM call it explicitly.
4. Change sets, decided at the start of the package: a change set's own state rows for the pairs its
   changes touch, read over the base's states as objects are (recommended), or a full copy per change
   set. Discarding or publishing a change set removes or merges its rows.
5. Model changes: activating a model release, or changing a change set's release, builds the states
   of shapes it adds or changes and drops those it removes.
6. The filter's SQL reads the table; the page's own cells keep A2's walk up, which is within budget.
   The filter is decided once per request rather than once per paging statement.
7. Migration with a backfill of every existing workspace, publication and change set. The startup and
   migration checks in `AGENTS.md` apply: clean bootstrap, upgrade from the preceding revision,
   restart, interrupted-migration recovery or refusal, the lifespan against a real temporary
   database and a smoke start against a copy of the development database.
8. An ADR for the derived-state choice (what is stored, who maintains it, how it is rebuilt), and
   API.md and ARCHITECTURE notes. The API contract does not change.

Composable-domains doors (ADR-032): none affected; the table is a derived index over existing records,
like `snapshot_attribute_values`, not a new identity or attribute storage.

**Exit:** `test_relation_matrix_volume.py` holds unchanged with A2's walk as the oracle, and a
rebuild-and-compare check finds stored states equal to derived ones after each write path's test, in
all three contexts and both directions; a filtered page, count and position jump are within 100 ms at
full volume in every context (recorded in `test_volume_baseline.py`); the migration and startup checks
pass.

**A3b delivered 2026-09-27.** `services/matrix_states.py` owns the stored states (ADR-033);
`services/matrix_cells.py` now holds the cell SQL that the page and the states share (the shape, the
context's arms, the walk up), so both derive cells identically. Decisions made on the way:

- Item 4 (change sets): the recommended overlay, at row granularity. A change set stores rows only for
  the row records its changes touch, and those replace all of the base's rows for that record (a
  sentinel row with an empty column marks it), so a removed cell needs no per-cell tombstone.
- Item 2 (`historyOnly`): a per-workspace `history` owner keeps, per cell, the first publication that
  held a record, extended at each publish; a publication read compares with its own number. Reading
  every publication's states instead would grow with the number of publications.
- Item 7 (backfill): the migration `20260927_01` creates the two tables empty, and the startup sync
  builds every missing (owner, shape), committing each build. Deriving the states in migration SQL
  would duplicate the cell semantics; a stopped build resumes on the next start. Until an owner is
  built, reads derive its cells from records (A2's walk), which is correct but slower.
- Which owners keep which shapes follows from the models in use; one idempotent sync builds and drops
  them at startup, on activation, change set creation and release change, publishing and workspace
  creation or deletion. `matrix_state_builds` stores each shape's definition, so maintenance needs no
  model.
- The filter reads each selected column's rows from the column index and combines columns by
  `UNION`, `EXCEPT` and `INTERSECT`, which SQLite merges in index order; it is pinned to that index
  (`INDEXED BY`) because without statistics SQLite scanned the owner's whole shape. The matching IDs
  are read once per request and passed to the paging statements as one JSON value.
- Found on the way: `_named_columns` looked columns up through the workspace index, reading every
  record of the workspace (20 ms at full volume on every `columnIds` request); it now seeks by ID.
  `session.get(ChangeSet, …)` takes the sequence key, not the public ID, a trap worth knowing.

_Measurements_ (full shape, median of 5, same machine as S1; live · change set · publication):

| Request | After |
| --- | --- |
| matrix: inactive in 10 columns, jump, total | 52.9 · 74.4 · 44.1 ms |
| matrix: none in 3 columns, jump, total | 41.7 · 62.7 · 32.5 ms |
| matrix: history only in 20 columns | 71.7 · 86.8 · 22.4 ms |
| matrix incoming: one in 1 column, jump, total | 38.1 · 55.0 · 28.5 ms |
| matrix: first page, 20 columns, total (unfiltered) | 36.2 · 46.9 · 24.9 ms |

A2 measured the state filters at 0.27–76 s on its first full run and several seconds warm after its
plan fixes, per request.

Statement counts are unchanged at both scales (11–18 by context). Building every owner and shape from
scratch at full volume (12 builds over two workspaces, a publication and a change set) takes 74 s;
`verify` over them takes 77 s and finds none differing.

Checks: `pytest tests/test_matrix_states.py` (9: live create, condition edits, a container move, cell
and row deletion; links and unlinks in both directions and a group moved to another column; change
set create, edit, move and delete, then publish, with the history; a publication-derived change set
and discard; activation and a change set's release change dropping a removed shape; workspace create
and delete; startup build, a failed build that logs and falls back, restart; upgrade from
`20260926_04` and restart; an interrupted upgrade recreating the derived tables and refusing an
unknown one; a long ID list), each step checked by `verify` and by every state filter against the
unfiltered cells with the derived filter disabled; `test_relation_matrix.py` and
`test_relation_matrix_writes.py` now run `verify` after every test; `test_relation_matrix_volume.py`
unchanged in its oracle and now refusing the derived filter; the full backend suite (714) before the
final filter and column-lookup changes, then `-m "matrix or volume"` (81) after them, and
`ruff check app/ tests/`. A smoke start on a copy of the development database (already at the new
head, so a restart) and on a copy downgraded to `20260926_04` (an upgrade): healthy, states built and
verified. Not run: frontend (no frontend change); the comprehensive suites belong to R1.

Limits: activation builds the states of a new shape inside its transaction, which at full volume
holds the writer reservation for several seconds per shape; startup does the same outside requests.
A write path added later that bypasses the ORM must note its changes (`note_rows`, `note_cells`),
or the filter drifts until the next rebuild; `verify` finds it.

#### A4: Relation matrix lens

**Scope:**

1. Replace the A1 placeholder with a generic `RelationMatrixView` that receives the view definition
   and takes every label from the model. Rows scroll through the S5 hook; the row columns and the
   column header stay pinned; columns page horizontally with the column cursor.
2. Grid semantics: `role="grid"` with row and column counts from totals, arrow keys across cells and
   row pages, Enter to act, Escape to cancel. Each state has a text label and an icon, not colour
   alone, and a legend.
3. Filters in the Filter popover: columns to show (searchable, from the column type's records) and
   the cell state. Both live in the URL with the S5 anchor.
4. Cell popover, offering only the view's `cellActions`: a `none` cell offers create (row and column
   fixed, container preselected when there is one, a searchable container picker otherwise) and link
   (searchable candidates with reasons); a `one` or `inactive` cell edits `cellFields` and offers
   unlink; a `historyOnly` cell shows the last published record, read-only, with **Create from this**
   that prefills it; a `several` cell lists its records, marks a conflict, and opens or unlinks them.
5. After a save, only the affected cell refreshes. A failure keeps the entered values and shows the
   error through `errorMessage`; a uniqueness conflict links to the conflicting record.
6. Context: in a change set the lens shows its badge and writes to it; in a publication it is
   read-only, as is a view without `cellActions`.
7. Add the lens to the UI acceptance state inventory (loading, empty, filtered-empty, error, read-only
   publication, change set, 390px).

**Reference pattern:** the mapping lens (`MappingGridView`) for the pinned-column grid and inline
action, and `ui/Modal` rules for the popover focus trap.

**Exit:** a steward fills an empty translation cell, corrects one and filters to gaps across the whole
list, and links and unlinks a system value in the mapping matrix, by keyboard alone, for two row types
at 1440px and 390px in live and change-set contexts.

**A4 delivered 2026-09-28.** `features/objects/RelationMatrixView` replaces the A1 placeholder in the
view registry; `RelationMatrixCellDialog`, `RelationMatrixFilter` and `relationMatrixStates` hold the
cell dialog, the Filter popover and the state vocabulary. Every label comes from the view, its binding
and the column records; nothing names a starter type. Decisions made on the way:

- Pinned row columns (item 1): the row header cell is the one sticky column and carries the view's
  `rowColumns` under the name (hidden at 390px as other secondary columns are), so there is no
  stack of sticky offsets to keep aligned. Columns named by the user come from `columnIds`;
  otherwise the column type pages sideways with **Previous** and **Next** and the column cursor,
  which is component state, not URL state.
- Grid (item 2): `role="grid"` with `aria-rowcount` from the total, `aria-colcount`, one roving tab
  stop, Left/Right/Home/End within a row and Enter or Space to open. Up and Down stay with
  `ui/ScrollWindow`, which gained one generic rule: a focused `data-grid-col` cell keeps its column in
  the next row, across page edges too. Ctrl+Home/End jump as on every list. Each state has an icon
  and a text label in the cell and a legend that lists only the states the binding can produce
  (`inactive` and conflict only when the condition and scope apply, read outgoing).
- Filters (item 3): `matrixColumn` (repeated) and `matrixState` in the URL beside the anchor. The
  API decides a state over named columns, so choosing a state while the matrix pages its columns
  names the columns on screen; a state without columns is dropped when a URL is parsed.
- The cell dialog is a `ui/Modal` (item 4). A single `one` or `inactive` record opens straight into
  its fields; `create` is offered in `none`, `inactive` and `historyOnly` cells, `link` in every
  state (candidates carry their reasons, so an unusable one says why), `unlink` with a confirmation.
  **Create from this** prefills from the last published record. Link and unlink claim the row's
  `relationSetVersion`; the client gained that claim on `createRelation` and `deleteRelation`,
  including through the change-set client.
- Refreshing one cell (item 5): the API has no row-ID filter, so the cell is re-read with
  `columnIds=[column]` and `seek=<row name>` without the search or state filter, and the row is found
  in that short page; if it is not there, the page reloads. The re-read cell overrides the loaded
  page until the list reloads. The rest of the page, the search and a state filter the row no longer
  meets are left alone until the next reload.
- Found on the way: after a save the dialog's submit button is disabled, which drops focus to the
  page before React Aria can restore it, so the lens returns focus to the cell itself; the runner
  caught it.

Checks: `views/RelationMatrixView.test.tsx` (12: two row types and both binding shapes, every state
label and the legend, keyboard across cells and rows and Enter/Escape, the state filter naming the
shown columns and the filtered-empty state, choosing columns from a search, column paging, create in the only container with a
one-cell refresh, a uniqueness breach keeping input and opening the conflicting record, link with
the row's claim and an ineligible candidate's reason, unlink with a stale claim, the load failure
retrying the same request, read-only), `CollectionView.test` (the lens beside the row type's table),
`routes.test` (matrix URL round-trip), `client.test`, `changeSetClient.test`,
`publicationClient.test`; `vitest related` over every changed module (273) plus `src/routing` and
`src/app` (49); format, lint (0 errors, the 8 recorded warnings) and build. `test:browser:a4`
(10 checks, registered in the execution guide) runs the exit journey by keyboard alone against a
real backend: fill, correct and filter to gaps on codelist translations live at 1440px; a master
value translation in a change set through the container picker at 390px; link and unlink on master
values by system live at 1440px and on codelists by system in a change set at 390px; the published
change set read-only. Each write is checked against the API in its context and the gap filter
against the API's filtered page and total; axe is clean on the grid, the cell dialog, the Filter
popover, the narrow grid and the link candidates. Screenshots were inspected at both widths.
`test:browser:s5` passes for the `ScrollWindow` change. Not run: `test:a11y` and `test:visual`
(matrix scenarios and baselines are A5 scope; no existing page's styles changed), the full suites
(R1). Pending labels (**Saving…**, **Linking…**) are not asserted in the browser.

#### A5: Milestone A acceptance

**Scope:** a real-backend browser runner on the starter model: for SC-09's translation half, Delivery
Methods by language with a present Czech cell, an empty English cell and a history-only cell; fill
English live; reject a duplicate; stage a change in a change set and publish it. For the mapping
shape, link and unlink a system value in **Master values by system**. Repeat a fill on the generated
model. Add accessibility scenarios for the matrix and its popover (light and dark) and reviewed
visual baselines. Record A2 measurements against budgets.

**Exit:** SC-09 translation half and the mapping-shape journey pass; budgets hold; the runner is
registered in the [execution guide](testing/EXECUTION_GUIDE.md); US-L03 and US-L04 move to delivered
in the functionality catalogue.

**A5 delivered 2026-09-28.** `e2e/a5-matrix-acceptance.mjs` (`test:browser:a5`) runs the milestone by
keyboard alone against a real backend in two model configurations. The SC-09 data is a shared helper
(`seedTranslationMatrix` in `e2e/helpers/acceptance-data.mjs`) so the runner and both gates show the
same records: Delivery Methods with a current Czech translation beside a superseded inactive one, no
English one, and a German one that publication 1 holds and live no longer does. Decisions made on the
way:

- "Reject a duplicate" is the steward's real mistake in this view: reactivating the superseded Czech
  translation while the current one counts. The translation views offer create only in `none`,
  `inactive` and `historyOnly` cells, so a second active record cannot be created from a `one` cell;
  the edit path is where the uniqueness rule meets the user.
- The change set is staged from the matrix (German restored with **Create from this**) and published
  from the change set screen (**Open change set**, **Validate change set**, **Publish change set**),
  so the journey crosses the one place publishing lives rather than calling the API.
- The generated model's fill takes the first row with an empty cell on the first page of columns, as
  the API reads it, so the runner does not depend on the fixture's arithmetic; its column offers 14
  places (every shelf can hold a cell), so the container picker is exercised by arrow keys.
- Found on the way: the refusal read "A related object already exists for this ancestor scope", the
  API's generic wording. The cell dialog now says it in the view's terms when the binding is read
  outgoing and the error names its scope: "Delivery Methods already has a translation in cs where
  Active is Yes, and only one may count there." (or "under the same …" when the scope is not the
  column); otherwise the API message stays. The API is unchanged.
- The gates' matrix scenarios run after the pages whose baselines already exist, since seeding the
  history publishes a second time (the publications baseline shows one).

_A2 measurements against budgets_ (`volume_baseline.py --scale 1 --repeat 5`, same machine as S1,
median ms · statements · ORM rows; live · change set · history). The full rerun A2 left open, with
A3's `relationVersion` and A3b's stored states in place. The seed now takes 189 s at full volume.

| Request | Live | Change set | History |
| --- | --- | --- | --- |
| matrix: first page, 20 columns, total | 37.7 · 12 · 45 | 47.0 · 13 · 5 | 26.4 · 12 · 4 |
| matrix: position ¾ deep, total | 36.4 · 12 · 45 | 52.6 · 16 · 5 | 26.4 · 12 · 4 |
| matrix: inactive in 10 columns, jump, total | 54.2 · 14 · 34 | 72.7 · 18 · 5 | 44.3 · 14 · 4 |
| matrix: none in 3 columns, jump, total | 41.9 · 14 · 27 | 64.1 · 18 · 5 | 32.3 · 14 · 4 |
| matrix: history only in 20 columns | 72.3 · 13 · 44 | 81.9 · 11 · 5 | 23.2 · 11 · 4 |
| matrix incoming: first page, total | 37.8 · 12 · 45 | 44.9 · 13 · 5 | 26.0 · 12 · 4 |
| matrix incoming: one in 1 column, jump, total | 36.8 · 14 · 25 | 53.7 · 18 · 5 | 30.1 · 14 · 4 |

Every matrix request is within the 100 ms budget in every context, at most 45 ORM rows, and with the
statement counts `test_volume_baseline.py` holds at both scales; the filters are within noise of A3b.
The rest of the table is within noise of S8, with the heavy parent's attribute and ancestor sorts
still the D26 exception (94–226 ms). Through the browser, the runner's 23 matrix reads (starter model
and the generated one at 10%) took at most 91 ms, a containers read.

Checks: `test:browser:a5` (7: SC-09's three starting states against the API's, including that the
history-only German cell does not count as `one`; fill English live; the refused reactivation with
its message, the checkbox still set, the stored record unchanged and **Open the translation already
here** landing on the current Czech one; German restored in the change set and absent from live;
validate and publish by keyboard, then all three languages `one` in live and in the new publication;
link and unlink in Master values by system at 390px; the generated model's fill through the picker,
checked in live and in the chosen place), `test:browser:a4` (10, for the dialog change),
`views/RelationMatrixView.test.tsx` (12; the breach case now checks both messages), `test:a11y`
(26 scenarios, 0 violations; new: the matrix, a history-only cell's dialog and the Filter popover,
light and dark), `test:visual` (21; four new reviewed baselines, `relation-matrix-{light,dark}` and
`relation-matrix-cell-{light,dark}`, every existing one matching), `test:gate-helpers`, format, lint
(0 errors, the 8 recorded warnings) and build. Screenshots were inspected: the grid at both themes,
the refusal, the published grid, the mapping cell at 390px and the generated model's picker; a hover
highlight caught in the first dark baseline was removed by moving the mouse away before capture.
Not run: the backend suites (no backend change) and the comprehensive suites (R1).

_Review fixes (2026-09-28)._ A review of A1–A5 found two defects in the lens:

- When an edit or unlink was refused as stale and the re-read cell no longer held that record, the
  cell dialog rendered nothing but the notice. It now shows the cell's records and actions again,
  says the record is gone, and starting another action clears the earlier notice.
- A cell re-read after a save stayed over the page when the lens later reloaded it (a refresh that
  could not find its row falls back to a reload), so a cell changed elsewhere since could show stale
  data. The reloaded rows now replace every such cell.

Each has a regression test in `views/RelationMatrixView.test.tsx` that fails without its fix. Found
on the way and fixed in the docs: `AGENTS.md` now states the matrix state rule for Core writes
(`note_rows`, `note_cells`, `note_relations_removed`, with `verify` in the write path's test), and the
0.10 PostgreSQL hardening in `TODO.md` and `ROADMAP.md` now names the matrix's SQLite-only statements.
Checks: `-m "matrix or mapping or change_sets or records or contract or queries or model"` (618),
Vitest (304), format, lint (0 errors, the 8 recorded warnings) and build. The plan header and
`TODO.md` now record A1–A5 as delivered; the index drift A2 left open is scheduled as
[A6](#a6-snapshot-table-index-drift). Not re-run: `test:browser:a4`/`a5` and the gates
(the dialog's rendering on the paths they cover is unchanged).

#### A6: Snapshot table index drift

_Scheduled 2026-09-28 from the A review: after A5, before R1. Found in A2, which left it as a
follow-up migration without scheduling one._

**Gap:** the ORM declares ten single-column indexes on the snapshot tables that no migration creates,
so a migrated database, which is every real one and the one the tests and `volume_baseline.py`
build, has none of them. Measured on 2026-09-28 by migrating an empty database to `20260927_01`
and comparing it with `Base.metadata`:

| Table | Declared, never created |
| --- | --- |
| `publication_objects` | `parent_object_id`, `object_type_key` |
| `publication_relations` | `from_object_id`, `to_object_id`, `relation_type_key` |
| `change_set_objects` | `parent_object_id`, `object_type_key` |
| `change_set_relations` | `from_object_id`, `to_object_id`, `relation_type_key` |

The drift dates from 0.6, when the revision and draft tables (now publication and change set tables,
ADR-031) were created by migrations that never had these indexes; the W2 rename carried the gap over.
Nothing checks that a migrated schema matches the ORM, so it went unnoticed until A2 read the plan of
a change set's walk down, which finds children by parent through an automatic index SQLite builds
per statement. The tests that build their schema with `metadata.create_all` get the indexes, so they
run on a different schema from production.

**Why it is not a plain "add the indexes":** every S and A budget was measured and every query plan
was steered (`unindexed`, `found`, `MATERIALIZED`, `INDEXED BY`) on the schema without them. The
relation tables already have covering (owner, endpoint, type, ID, other end) indexes (S4, S4R1), which
make the single-column endpoint and type indexes redundant at best. A new index SQLite prefers could
undo a plan those packages chose deliberately.

**Scope:**

1. For each of the ten indexes, decide (D28): create it in a migration, replace it with an
   owner-leading composite the reads actually need (for example (`change_set_id`,
   `parent_object_id`) for walks down a change set), or remove the declaration from the ORM because
   an existing index already serves it. Decide from the query plans and the measurements in item 3,
   not from the declaration.
2. One Alembic migration after `20260927_01` for what item 1 adds, idempotent over a database that
   already has an index of the same name (one built with `create_all`); the ORM declarations changed
   to match exactly.
3. Measure `volume_baseline.py --scale 1` before and after for the S, S8 and A2 rows, with the change
   set and publication contexts in particular: every row within its budget and no statement-count
   change, or the index reconsidered. Check the plans of the walks in `matrix_cells.py` and
   `relation_matrix.py`: they should seek their children by an index, not build an automatic one.
4. A schema drift test: migrate an empty database to head and compare its tables, columns, indexes
   and unique constraints with `Base.metadata`, failing with each difference named. The search index
   tables that `models/search_index.py` registers separately are compared too. Once it passes, a
   future ORM declaration without a migration fails the suite.
5. The migration checks in `AGENTS.md`: clean bootstrap, upgrade from `20260927_01`, restart,
   interrupted migration recovery or refusal, the lifespan against a real temporary database, and a
   smoke start on a copy of the development database.

Composable-domains doors (ADR-032): none affected; indexes over existing tables, no new identity,
attribute storage or API.

**Exit:** a migrated database matches the ORM, and the drift test holds that; every volume budget
holds with statement counts unchanged; the matrix walks no longer depend on an automatic index; the
migration checks pass. API contract unchanged.

**A6 delivered 2026-09-28.** D28 was decided from the query plans of every volume scenario, captured
with `EXPLAIN QUERY PLAN` on the full-volume fixture before and after:

| Index declared, never created | Decision | Why |
| --- | --- | --- |
| `publication_objects` parent, type | declaration removed | every read names the publication; (publication, parent, type, name, object) and (publication, type, name, object) serve it |
| `publication_relations` from, to, type | declaration removed | every read names the publication; the S4R1 (publication, end, type, relation, other end) indexes serve it |
| `change_set_relations` from, to, type | declaration removed | the same, per change set |
| `change_set_objects` parent, type | replaced by (change set, type, name, object) and (change set, parent, type, name, object) | the table had only an owner index; the walks down found a change set's children by parent through an automatic index built per statement |

The change set object table now has the two page indexes the publication and base object tables
have, so the three owner tables of `object_projection` arms are indexed alike. The matrix walks
(`matrix_cells.descendants`, `relation_matrix._current_pairs` and `_walk_below`) no longer keep the
change set term off the index (`by_change_set=False` is gone): each step seeks
`ix_change_set_objects_parent_name (change_set_id=? AND parent_object_id=?)`. Migration
`20260928_01` creates the two indexes, keeps one of the expected shape and rebuilds one of another
(an interrupted run), and drops the ten removed indexes where a pre-A6 `create_all` database has
them, so every starting point ends with the ORM's schema. The change set base tables keep their
single-column indexes: they are declared and created, so they are not drift, and no plan measured
here depends on them either way.

`tests/test_schema_drift.py` migrates an empty database to head and compares it with
`Base.metadata` through Alembic's `compare_metadata` (tables, columns with types and nullability,
indexes, unique constraints, foreign keys; not CHECK constraints, which Alembic does not compare),
naming each difference by table, index and columns; the trigram search index tables and triggers are
compared with those `create_all` builds. Before this package it reported exactly the ten indexes.

_Measurements_ (full volume, median of 5, same machine as S1; a copy of one seeded database per
run, upgraded through the lifespan for "after"). Statement counts and ORM rows are identical in
every scenario and context; times are within noise of the before run and of A5's table. The only
plan changes are change set overlay reads: walks down seek the new parent index instead of an
automatic one, and type- and parent-narrowed page arms seek the new indexes instead of the owner
index. No automatic index is built on a table in any scenario; the remaining automatic indexes are
on recursive CTE queues (`matrix_walk`, `matrix_history_walk`, `ancestors`), which no table index can
serve. Scenarios added to the measurement for the walks down (live · change set):

| Request | Before | After |
| --- | --- | --- |
| matrix: containers of a column | 4.9 · 11.8 ms | 4.9 · 9.8 ms |
| matrix: link candidates in a column | 90.6 · 156.5 ms | 92.0 · 160.8 ms |
| write: move a container to another column (change set) | 7,307 ms · 114 | 7,410 ms · 114 |

_Found on the way, not index drift, left open:_ moving a first-level container (about 2,500 cells of
the outgoing matrix under it) in a change set takes 5–9 s; the time is A3b's recompute of the cell
states of every affected row, about 110 statements of which the slowest take 0.5–0.8 s each. A link
candidate page over a column of about 5,000 cells takes 92 ms live and 160 ms in a change set,
because its name order and total read every cell under the column. Neither was in a budget before.
**Decided 2026-09-28:** the move is measured in B2 (D29); the candidate page is a known 0.8 budget
exception (D30).

Checks: `tests/test_schema_drift.py` (3: the migrated database equals the ORM, the search indexes
equal `create_all`'s, and the comparison names a dropped and an undeclared index) and
`tests/test_change_set_object_index_migration.py` (4: clean bootstrap; data written at head,
downgraded to `20260927_01` and upgraded through the lifespan across two restarts with object and
relation pages in every context unchanged; an interrupted run with one index kept and one rebuilt;
a pre-A6 `create_all` database losing its ten indexes; downgrade), each ending with no drift;
`-m "startup or matrix or change_sets or volume or queries or mapping or model_admin"` (480, with the
Alembic head updated in eight migration tests), and `ruff check app/ tests/`. A smoke start on a copy
of the development database (the running dev server had already upgraded it: a restart) and on a
copy downgraded to `20260927_01` (an upgrade): healthy across two starts, no drift. Not run: the full
suite and frontend (no frontend change); R1 owns them.

## Milestone B — Hierarchy editor

### Outcome

A steward opens a hierarchy as a tree beside the selected record's detail, finds a nested record
without loading every branch, adds a child in the branch it belongs to, renames it or changes its
availability in place, and moves it to another valid parent. The path and the typed containment
relation change together; a move beneath the record's own descendant is refused. Routine edits are
live; a selected design draft stages them. Stories US-H01, US-H02 and US-D09, scenario SC-09
(hierarchy half).

### What already exists

- `PATCH /objects/{type}/{id}` with `parentObjectId` changes the parent and its typed edge together,
  live or in a draft, and rejects cycles (`_would_create_parent_cycle`, `_validate_candidate_parent`).
  Activation revalidates the merged graph (ADR-006).
- `POST /objects` with `parentObjectId` creates a child and its containment edge together.
- Object reads return `path`.
- S6 delivers generic tree loading by parent, per child type, with totals and keyboard traversal. S3
  `seek` lets a branch open at a given child.

Milestone B adds a declared tree view, a query for valid move targets, and the maintenance actions in
the tree.

#### B1: Schema 0.7 — `tree` view contract

**Scope:**

1. Add `TreeViewDefinition` (type `tree`) to the schema 0.7 union. Config: `rootObjectTypeKeys`,
   `objectTypeKeys` (the node types shown), `labelField`, optional `secondaryField`, `childSort` per
   type (a sort field of that type), `pageSize` (1–100), and `actions` (subset of `createChild`,
   `rename`, `move`, `setAvailability`) with `availabilityField` required when `setAvailability` is
   listed.
2. Validation: every node type belongs to the application and is reachable from a root type through
   `parentRelationTypeKeys`; root types can exist without a parent; fields are attached to their types;
   `childSort` fields are declared sortable; `availabilityField` is a boolean attached to every node
   type that the action applies to.
3. Lens grouping: a `tree` groups under its first root type.
4. Starter model: a tree over systems and system groups (recursive self-hierarchy with values beneath
   it, mixed types) and one over domains, codelists and master values. The generated S1 model gains
   a tree over its six-level self-hierarchy.
5. Frontend union and placeholder registration, as in A1. Document in `APPLICATION_MODEL.md`.

**Exit:** as A1, for the tree contract; a view whose node type is unreachable from its roots is
rejected at that type's pointer.

**B1 delivered 2026-09-28.** `_check_tree_view` applies the rules; reachability is a walk down from
the root types over containers the tree itself shows, so a type the application holds but no shown
type contains is refused at its `objectTypeKeys` entry. Decided on the way, within the scope above,
and confirmed 2026-09-28:
root types must be listed among `objectTypeKeys` and be `rootCreatable`; `labelField`,
`secondaryField` and `availabilityField` must be available on every node type; `availabilityField`
without `setAvailability` is refused rather than ignored. "Declared sortable" for `childSort` means
what the list query sorts by (built-ins and non-JSON attributes of that type), because D24 retired the
`sortable` flag. Actions follow A1's "could it ever succeed" rule: `createChild` and `move` need a node
type that contains another, and `rename` and `setAvailability` a field writable on every node type.
The starter trees are `rdm-master.domain-hierarchy` and `rdm-systems.system-hierarchy`; the volume
model's is `vol-catalogue.hierarchy` (no availability action: its types have no boolean). The content
release stays 0.8.0, so a database that installed the earlier 0.8.0 content refuses to start with a
release identity conflict until it is re-bootstrapped, as after A1. Three existing tests whose
mutations now trip a tree first were narrowed to keep testing their own rule.

Checks: `pytest tests/test_model.py` (each rule with its exact pointer over both starter trees, a node
type reachable only through a recursive container, writable-field refusals, a tree of roots alone,
strict shape, a renamed-keys model, 0.6 refusing each 0.7 view type, the 0.5/0.6 starters, the served
starter and the generated model), `-m "model or contract"` (229 passed, OpenAPI lock unchanged),
`test_model_schema_upgrade.py`, `test_translations.py` and `ruff check app/ tests/`; Vitest
`model.test.ts` (grouping under the first root type) and `CollectionView.test.tsx` (the placeholder
lens for two root types); frontend format, lint (0 errors, the 8 recorded warnings) and build.
`test:visual` passes after the `collection-table-domain-light`/`-dark`,
`collection-table-system-light` and `change-set-editing-light` baselines were updated for the new lens
switch after inspection. A one-off harness check opened both starter tree placeholders by keyboard at
1440px and 390px (no overflow, axe clean) and its screenshots were inspected. Not run: `test:a11y` and
a registered runner for the placeholder, which B3 replaces with the real lens and B4 covers.

#### B2: Move targets and path context

**Scope:**

1. `GET /api/v1/objects/{objectTypeKey}/{objectId}/parent-candidates` with context, `search`,
   optional `objectTypeKey` of the candidate, and S3 paging. It returns records of every type that the
   model allows as this record's parent, in the same workspace and context.
2. Each candidate carries `eligible` and, when false, a machine-readable `reason`: `self`,
   `descendant` or `currentParent`. Ineligible candidates stay in the list so pages and totals remain
   truthful (D14). `descendant` is decided by walking each candidate's ancestors, which costs page
   size × depth and does not grow with the size of the moved subtree.
3. Candidates include their `path` so a steward can tell same-named groups apart.
4. Confirm that `path` on object reads is correct in draft and history contexts after S2, including a
   record whose parent changed in the draft; fix it if not.
5. Moving a record with 20,000 descendants (S1 fixture) stays within the single-record write budget,
   live and in a draft, because only the moved record's parent and edge change. Measure also a move
   of a container that holds about 2,500 relation matrix cells, live and in a change set, and fix it
   or record it as a known budget exception (D29).
6. Tests: every refusal reason; a draft move that the draft makes valid but live makes cyclic,
   refused at activation with the draft kept; moving across types in a mixed hierarchy. Update API.md
   and the OpenAPI lock.

**Exit:** the candidate query and a deep move meet budget in each context; cycles are refused at the
query, the write and activation.

**B2 delivered 2026-09-28.** `GET /objects/{type}/{id}/parent-candidates`
(`services/parent_candidates.py`) lists the records of every type the model allows as the record's
parent, in its application and workspace, live (`workspaceKey`) or in a change set (`changeSetId`),
through the object query builder: name order, `search` with the object list's meaning (name or a
searchable field, trigram-indexed), cursors, positions and totals. Decided on the way, within the
scope above: the candidate type filter is `parentObjectTypeKey`, because `objectTypeKey` beside the
path's `{objectTypeKey}` would name two types with one word; a type that cannot contain the record
is `422 invalid_parent_type` with the `permitted` types; a publication has no move targets and the
route does not take `publicationId`, as the matrix's container and candidate reads do not. Each
candidate carries its root-first `path`, and `descendant` is read from that path, so it costs one
lookup per hierarchy level for the page, and a change set's own moves count. `object_projection`
gains `object_type_keys` for the mixed-type change set list.

Path context (item 4): single reads and pages already resolve `path` in the request's context; a
record whose parent changed in a change set, its untouched child, the child's page and the new
publication after publishing were each checked, and needed no fix.

The deep move (item 5) needed three fixes, each found by measuring:

- A live update re-checked ancestor-scoped uniqueness (`uniqueToAncestorTypeKey`) for every relation
  into the record's whole subtree, on every write, a rename included: 773 ms and 40,517 ORM rows to
  move the 20,000-descendant group. `relations.validate_scoped_relations` now checks nothing for a
  rename, the record's own relations for a value change (a condition reads only the related record's
  values), and after a move only relations of scoped bindings into the records below whose scope
  record is above the moved one, walking only types that can hold such a record. A move under which
  no scoped binding can apply reads nothing below the record.
- Stored matrix cell states (A3b) walked down from any moved record. Only a container or a cell can
  change the column of a cell under it, so `_resolve` now walks from those types only (and from a
  record it cannot find, such as a tombstone).
- The flush hook noted the ends of every relation written, of any type, as rows to recompute in every
  shape, so the move's new containment edge recomputed its two groups' cells. The ORM hook now notes
  a relation's ends under its type, and a shape recomputes only those of its binding type; rows noted
  by Core statements (`note_rows`) and relations whose ends or type changed still apply to every
  shape. Also, a live cell's rows were found through the (type, from, to) key, which read every
  relation of the binding when the cell is the `to` end; `related_rows` now reads that end's own index.

The generated volume model gains `vol-group-has-child`, so groups nest and the heavy group can move.

_Measurements_ (`volume_baseline.py --scale 1 --repeat 5`, same machine as S1; ms · statements ·
ORM rows). The new rows join the scenarios `test_volume_baseline.py` holds at two scales, except the
container move, which the script alone measures (`known_exceptions`):

| Request | Live | Change set |
| --- | --- | --- |
| parent candidates: 20,000-descendant record, total | 5.3 · 6 · 25 | 13.0 · 8 · 4 |
| parent candidates: search, total | 8.6 · 5 · 14 | 18.8 · 7 · 4 |
| parent candidates: deep node, two types, total | 17.9 · 6 · 25 | 13.8 · 8 · 4 |
| parent candidates: deep node, position ¾ deep | 22.8 · 6 · 25 | 25.5 · 11 · 4 |
| write: move a 20,000-descendant record (before: 773 · 38 · 40,517 and 53 · 51 · 11) | 5.8 · 22 · 8 | 13.0 · 43 · 11 |
| write: rename one record (before: 4.2 · 12 · 7 and 16.5 · 35 · 10) | 3.4 · 12 · 7 | 8.3 · 35 · 10 |
| write: move a container of ~2,500 cells | 19,650 · 155,848 · 251,134 | 4,552 · 114 · 11 |

Every other row is within noise of A5 and A6, the D26 sorts included.

_The container move (D29), a known 0.8 budget exception._ Moving a first-level container of the
outgoing matrix (about 2,500 cells) to the next column takes 4.6–7.9 s in a change set and 20–24 s
live. In a change set the time is A3b's recompute of every affected row's states in each shape. Live,
about 84% is the scoped uniqueness check, which B2 no longer runs for the unaffected records but
still runs one relation at a time for the 2,500 whose scope moves (about 60 lookups each); the rest
is the recompute. Bringing either within the write budget means a set-based scope check for a moved
subtree and a recompute limited to the old and new column, neither small. Recorded as a known
exception; a steward moving a container of thousands of matrix cells waits seconds, and B3's move
dialog must show progress rather than assume an instant answer.

Also fixed on the way: `test_build07_wp6.py`'s `parent` case made `domain` not root-creatable, which
B1's tree rule now refuses first; its mutation now also drops the tree rooted at domains, as B1 did
for three other tests.

Composable-domains doors (ADR-032): none affected; a read over existing identity and hierarchy, no
new attribute storage, audit or bulk API.

Checks: `tests/test_parent_candidates.py` (9: every reason with paths, one type, search by name and
code, cursors and a position with ineligible candidates in place; the write agreeing with each
reason and moving the edge; a move across types in the mixed system hierarchy; the master value
hierarchy and a type with no parent types; refusals; a change set move with the moved record's and
its untouched child's paths, candidates, a refused cycle and the publication's paths; a move live
made cyclic refused at publication with `containment_cycle`, live and the change set kept; a
translation group taking a translation into a language that holds one, refused, and a move within
the language accepted; the OpenAPI route; `matrix_states.verify` after each), the OpenAPI lock
re-baselined after checking that only the new path and its three schemas changed, and the paging
inventory at 21 routes; the guide's groups for the changed boundaries (`records`, `matrix`,
`change_sets`, `volume`, `contract`) and `ruff check app/ tests/`. The full backend suite was also run
(763 passed), which the execution guide does not select for a package; `AGENTS.md` now rules that out. Not run: frontend (no frontend change); B3 builds the lens.

#### B3: Tree lens with maintenance actions

**Scope:**

1. A generic `TreeView` lens: the tree on the left, the selected record's configured detail on the
   right (panels as today), resizable as the existing split. Tree loading reuses S6 by parent and per
   child type; `childSort` sets each branch's order.
2. Opening a URL or a search result reveals the record: load its `path`, then open each ancestor's
   branch at the child with `seek`. Unrelated branches stay closed.
3. Actions from a node's menu and keyboard shortcuts, as the view allows:
   - **Add child** — choose the child type when several are allowed; the form carries the parent; the
     new node appears in its branch and gets focus.
   - **Rename** — inline on the node.
   - **Set availability** — a toggle on the node.
   - **Move to…** — a dialog with a searchable B2 candidate list; ineligible candidates are shown
     disabled with their reason; confirming moves the node, updates both branches' counts and keeps
     focus on the moved node.
4. Failure keeps the user's place and input: loaded branches stay loaded, a failed branch shows
   **Retry** without collapsing its siblings, and a refused move leaves the dialog open with the error.
5. Draft and history: in a draft the actions write to it; in history the tree is read-only.
6. WAI-ARIA tree pattern: `aria-level`, `aria-setsize`, `aria-posinset`, `aria-expanded`,
   Home/End and type-ahead. Every action is reachable without a pointer.
7. Add the lens to the UI acceptance state inventory.

**Reference pattern:** the S6 sidebar tree for loading and keyboard behaviour; `ObjectFormDialog` for
child creation; `ui/Modal` for the move dialog.

**Exit:** on both starter trees and the generated six-level tree, a steward finds a nested record,
adds a child, renames it and moves it, by keyboard alone, at 1440px and 390px, live and in a draft.

**B3 delivered 2026-09-28.** `features/objects/TreeView.tsx` replaces the placeholder. Decided on the
way, within the scope above:

- _One tree, configured._ The lens is S6's `RecordTree`, which gains a `TreeConfiguration` (root,
  search and child types, a sort and page size per type, label, extras, item keys) rather than a
  second tree. Both trees gain the reveal by `seek` (item 2), type-ahead, and a tab stop that
  returns to the open record once it is drawn unless the user has since focused another item. A
  `childSort` field recorded only live (`createdAt`, `updatedAt`) sorts by name in a change set or
  publication, where the list query refuses it.
- _Beside the detail._ Records open with `fullPage: false`, the inspector split kept in code since
  UI-03; history now records `false` as well as `true`, so reload, Back and Forward keep the split.
  Below 1080px the existing responsive rule gives the record the whole view, and Back returns to the
  tree as it was. The inspector re-reads its record when the collection beside it writes, and a
  narrow inspector wraps the record's actions below its title (found in the screenshots: titles broke
  mid-word). Item 2's "opening a URL" is the record open beside the tree, including after a reload or
  history move; a bare record link has no collection origin by design (UI-03) and opens full width.
- _Actions._ A node's menu (`ui/AnchoredMenu`, a new wrapper: React Aria's `Popover` and `Menu`
  anchored to the row) opens with Shift+F10, the context menu key or the row's ⋯, so the tree keeps
  one tab stop. It lists Open, **Add <type>** for each type the node can contain among the tree's
  node types (the choice of child type), Rename (also F2), **Mark (not) <field>** and **Move to…**,
  each only where the view's `actions` include it. The availability switch and ⋯ on the row are
  pointer shortcuts hidden from assistive technology; the item's name says when a record is not
  available. A search result reveals the record with its branches opened explicitly, and focus goes
  to the record it opens.
- _Move dialog._ `TreeMoveDialog` lists the B2 candidates with the matrix link dialog's list
  (search, `ScrollWindow`, radios), each with its path and, when several types are listed, its type;
  ineligible ones are disabled with the reason (`Current location`, `Inside the record`, `The record
  itself`). While the write runs it says **Moving…** with a status line that a large branch can take
  seconds (D29). A refused move keeps the dialog, the choice and the reason; a version conflict reads
  the record again so a retry claims its new version.
- _Type-ahead and Space._ Space opens a record, so a space typed while a type-ahead is in progress
  continues it instead, as the ARIA tree pattern allows; names with spaces are reachable by typing.

Composable-domains doors (ADR-032): none affected; a lens over existing reads and writes.

Checks: Vitest `views/TreeView.test` (11: two configurations' types, order, labels and read-only
rows; the reveal seeking a branch past its first page; F2 rename refused then saved with focus
back; the node menu's entries and availability; add child; move with ineligible candidates, a refused
move keeping the dialog, then the move; type-ahead with a space; empty workspace; a refused
availability change; read-only), `CollectionView.test`, `Explorer.test` (the sidebar unchanged),
`ObjectDetail.test`, `useRouter.test` (the split kept across reload and history), `client.test` (the
candidates request live and in a change set), `src/routing`, `src/app`, `src/features/objects`;
format, lint (0 errors, the 8 recorded warnings) and build. `test:browser:b3` (21 checks, below),
`test:browser:s6`, `test:browser` and `test:browser:wp14` for the shared tree and history.

`test:browser:b3` drives three trees by keyboard alone: the starter system hierarchy live at 1440px
(Sodium found three levels down and revealed with Boat left closed; a group added under Chemistry,
renamed, marked not active and moved to Boat; Lab group's descendant Chemistry listed disabled),
the domain hierarchy in a change set at 390px (a codelist added, renamed, marked not active and moved
to another domain, none of it in live data; the publication then read-only), and the generated
volume tree at 2% scale, live at 1440px and in its change set at 390px (the node seven levels down
revealed reading only its ancestors' branches, one by seek; a node added, renamed and moved to its
grandparent). Every write is checked against the API in its context. Axe found no violations on the
eight states scanned. Screenshots inspected: the system tree with the record beside it, the move
dialog, the domain tree at 390px, the volume tree at both widths. Not run: `test:a11y` and
`test:visual` scenarios for the lens (B4), and the full suites (R1).

#### B4: Milestone B acceptance

**Scope:** a real-backend browser runner for the SC-09 hierarchy half: find a nested system group
without loading every branch, add a child, move it to another permitted group, see the new path and
unchanged unrelated branches, and be refused a move beneath the child's own descendant. Repeat on the
domain/codelist/value tree (different record types). Repeat the move in a draft and activate it;
check that parent and containment edge both changed in live. Add accessibility scenarios for the tree
lens and move dialog (light and dark) and reviewed visual baselines.

**Exit:** SC-09 hierarchy half passes; the runner is registered in the execution guide; US-H01,
US-H02 and US-D09 move to delivered in the functionality catalogue.

## R1: Build acceptance and release

**Scope:** after S8, W6, W5, A6, B4 and P2 (D20, D25, D27, D28): the full backend `pytest` suite, frontend `npm run test`, Ruff,
format, lint and build, every browser runner, `test:a11y` and `test:visual`. Migration checks for the
S2 typed value rows (clean bootstrap, upgrade from the 0.7 head, restart, interrupted migration,
lifespan, smoke start on a copy of the development database). Confirm a schema 0.7 release installs
and activates on a Base 0.7 database that holds schema 0.6 releases. Update PROJECT_STATUS, ROADMAP,
TODO, CHANGELOG, API.md and the functionality catalogue; record residual gaps.

**Exit:** all gates pass, or each failure is explained and tracked; Base 0.8.0 is ready to release.

## Decisions summary

| ID | Question | Recommendation | Blocking |
| --- | --- | --- | --- |
| D1 | Typed values for draft/history queries: JSON extraction or typed value rows? | **Accepted 2026-09-25:** typed value rows, mirroring live | S2 |
| D2 | Window size and prefetch distance | **Accepted 2026-09-28 as delivered in S5:** 5 pages kept; prefetch one page from either edge; a code constant, not model configuration | S5 |
| D3 | Branch with several child types: mixed endpoint or one list per type? | **Accepted 2026-09-28 as delivered in S4 and S6:** one list per child-type group, matching the existing collection groups | S4, S6 |
| D4 | Does a view's `pageSize` keep its meaning? | **Accepted 2026-09-28 as delivered in S5:** yes, it becomes the fetch size; no schema change | S5 |
| D5 | Totals on every page or on request? | **Accepted 2026-09-28 as delivered in S3:** on request (`includeTotal`); the UI asks on first load, after a query change and with position jumps | S3 |
| D6 | Relation sort keys | **Accepted 2026-09-28 as delivered in S4:** related record's name and relation creation order; related-type fields later if needed | S4 |
| D7 | Draft writes still load the whole membership | **Measured in S1:** over budget (7.6 s per rename at full volume). **S2:** 4.7 s after reads moved to SQL; follow-up slice S2b scoped. **S2b:** 7.5 ms | S2b |
| D8 | A view type for the translation task, or a generic one? | **Accepted 2026-09-27 (A1, corrected):** a generic `relationMatrix` — rows, columns of an ancestor type, cells of related records through one binding in either direction — with a closed `cellActions` set. Translations are one starter configuration; system representations and cross-system mapping are two more (COMPOSABLE_DOMAINS admission tests) | A1 |
| D9 | Schema 0.7 if only one milestone ships | **Accepted 2026-09-27 (A1):** each view type is added by its own package; a cut milestone's type is removed before release | A1, B1 |
| D10 | Matrix columns | Explicit `columnIds` (at most 20) or the first page of column records; columns page with their own cursor. **Accepted 2026-09-27 as delivered in A2** | A2 |
| D11 | Cell states | `one`, `several` (a conflict only when the binding's uniqueness scope is the column type), `inactive` (only with a binding condition), `historyOnly`, `none`, all derived from the binding. `historyOnly` means a publication of this workspace held one. **Accepted 2026-09-27 as delivered in A2.** Condition and conflict apply only read `outgoing` | A2 |
| D12 | Resolving a cell record's column for the row state filter | A recursive query down from the selected column records, measured in A2. A stored ancestor table only if the measurement is over budget, as a scoped follow-up. **Measured in A2: over budget** (seconds over 50,000 cells); a stored ancestor table alone would not meet it, a stored per-cell state likely would. **Decided 2026-09-27:** A2 closes with the recursive filter as a temporary budget exception; a stored per-cell state maintained by writes replaces it in A3b, before A4 | A2, A3b |
| D13 | Which container a new cell record goes into | The user picks the column record or a container under it; preselected when there is exactly one. No model default. **Accepted 2026-09-27 as delivered in A3** (`defaultContainerId` on the containers read); the preselection is A4's | A3, A4 |
| D14 | Ineligible move targets | **Accepted 2026-09-28:** listed but disabled, with a machine-readable reason (`self`, `descendant`, `currentParent`), so totals stay truthful and the user sees why | B2, B3 |
| D15 | When does the W2 rename land? | **Accepted 2026-09-25:** after S7 (draft and revision tables stable after S2) and before A2 and B2, so new endpoints use the new names | W2, A2, B2 |
| D16 | Name of the snapshot a change set publishes | **Accepted 2026-09-25:** **Publication**, referred to as "Publication N" by its per-workspace counter, which continues across model releases; date and model release are secondary. "Version" is avoided because record, change-set and model-release versions already use it | W1, W2 |
| D17 | Is split deployment (admin and public instance on one database) verified in 0.8? | **Accepted 2026-09-25:** no, it stays a documented, unsupported topology until 0.10 multi-node work; the suspected write-versus-activation race it exposed is investigated in 0.8 as W5 because it may affect one process too | W5 |
| D18 | Verb for making a change set live | **Accepted 2026-09-25:** **publish**; **activate** is reserved for model releases, **install** for model drafts | W1, W2 |
| D19 | Removing a publication's current designation | **Accepted 2026-09-25:** **withdraw** (status `withdrawn`); **retire** is reserved for workspaces | W1, W2 |
| D20 | Are P1 (cross-type lookup), P2 (change set changes list) and P3 (workspace edge list) in 0.8? | **Accepted 2026-09-26:** P2 is in 0.8, as a package after W2; P1 and P3 move to 0.9 (integration APIs). A parameterless "list everything" and a flat attribute value list are rejected (export and change feed, 0.9) | P2, R1 |
| D21 | Where relation panel sort options come from | **Accepted 2026-09-26:** declared on the relations panel (`sortFields`, `defaultSort`) in schema 0.7; no hardcoded options; 0.5/0.6 panels sort by name | S4R1–S4R3 |
| D22 | Default list order across contexts | **Accepted 2026-09-26:** name order in live, draft and history; recorded draft and history timestamps are a later package (T1) | S4R4, T1 |
| D23 | Ancestor sort on relation lists | **Accepted 2026-09-26:** included now, one walk per list rather than per row, measured at volume | S4R1 |
| D25 | Whole-type name search is over budget (0.7–0.9 s, S7): indexed search, prefix match, or no total? | **Accepted 2026-09-26:** an indexed search that keeps "contains" matching, in every context (S8). SQLite first; the PostgreSQL equivalent (trigram) arrives with 0.10 hardening. **Delivered 2026-09-26** as a trigram index over text values; names stay on the (type, name) index, which measured cheaper than indexing them (S8) | S8 |
| D26 | Attribute and ancestor sorts over the 20,000-child parent are over budget (85–204 ms, S4R1, S7) | **Accepted 2026-09-26:** deferred until after 0.9 (precomputed sort keys, 0.10 or later); recorded as a known budget exception for 0.8 | — |
| D27 | Can a workspace be deleted? (ADR-019 said never) | **Accepted 2026-09-26:** yes, to correct a mistyped key, when it is not the default, has no objects and no change sets, and was never published; a published workspace is retired instead because publications are never removed. No audit event, matching the unaudited create, rename and retire; the key may be reused | W6 |
| D28 | Index declarations that no migration creates on the snapshot tables (A6) | Per index: create it, replace it with an owner-leading composite the reads need, or drop the declaration where an existing index serves it, decided from query plans and the volume baseline; a drift test keeps a migrated schema equal to the ORM. **Accepted 2026-09-28 as delivered in A6:** change set objects gain (owner, type, name, object) and (owner, parent, type, name, object); the other eight declarations are removed because owner-leading indexes already serve every read | A6 |
| D24 | Which columns sort | **Accepted 2026-09-26 (S4R3 review):** every data column sorts from its header, whatever the attribute's `sortable` flag, including Type and Relationship by their labels; every list shows the same toolbar Sort menu; D21's `sortFields` only add menu fields and `defaultSort` chooses the order. Exceptions: Actions, the computed path, JSON attributes and unrecorded timestamps | S4R3 |
| D29 | Moving a container of about 2,500 matrix cells in a change set takes 5–9 s (A3b cell state recompute, found in A6) | **Accepted 2026-09-28:** measured in B2 beside its deep-move budget, because a tree move of a container (a system group to another system) takes the same path; B2 either brings it within the single-record write budget or records it as a known 0.8 budget exception. **Decided in B2 (2026-09-28):** a known 0.8 budget exception, 4.6–7.9 s in a change set and 20–24 s live; the deep move meets the budget (6 ms live, 13 ms in a change set) | — |
| D30 | A link candidate page over a column of about 5,000 cells takes 92 ms live and 160 ms in a change set (found in A6) | **Accepted 2026-09-28:** a known 0.8 budget exception, as D26; the name order and total read every cell under the column only at an unusual column size. Revisit with precomputed sort keys (0.10 or later) | — |
