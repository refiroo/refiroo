# Base 0.8 implementation plan

**Status:** Draft plan, 2026-09-25. Track S (scalable browsing) starts first. Milestone A
(translation editor) and Milestone B (hierarchy editor) from the
[roadmap](ROADMAP.md#product-release-08--translation-and-hierarchy-editors) are broken into work
packages A1–A5 and B1–B4; Track W (W1–W5) delivers ADR-031 terminology and capability boundaries; R1
owns build acceptance. Decisions D8–D19 are proposed, not yet accepted.

**Target:** Product 0.8.0. Track S does not change the schema language. Milestones A and B add
schema language 0.7 (`translationMatrix` and `tree` views); the starter model becomes content release
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

Order: W1 → W2 → W3 → W4. W1 may run at any time. W2 follows S7 and precedes A2 and B2 (D15). W5 is
independent and may run at any time.

#### W1: Terms in documentation

**Scope:** update the [glossary](product-functionality/GLOSSARY.md) to the ADR-031 terms and add the
Live / change set / publication relationship to one workspace. Rename Milestones A and B to
**Translation editor** and **Hierarchy editor** in ROADMAP, TODO, this plan and the functionality
catalogue. Correct the stale "non-default workspace detail gap" notes in PRODUCT and USER_JOURNEYS
after checking the current behavior.

**Exit:** no document uses "workspace" for the 0.8 screens; the glossary defines every ADR-031 term.

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

#### W3: Narrow the workspace administration capability

**Scope:** move change-set create, update, delete, model-release change, validation and publish, and
publication withdrawal, from the workspace administration router to an always-registered router,
keeping the retired-workspace refusal. `WORKSPACE_ADMIN_MUTATIONS_ENABLED` then gates only workspace
create, rename, retire and set default. Update README, ARCHITECTURE's capability table and the CHANGELOG.

**Exit:** with the flag off, catalogue mutations return 404/405 and the change-set workflow passes end
to end; with it on, both work; `MODEL_ADMIN_MUTATIONS_ENABLED` tests are unchanged.

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
              S2, S3 ─────────→ A2 → A3 → A4 → A5
              S5 ─────────────────────────↗
Milestone B:  B1 ──────────────┐
              S3, S4 ─────────→ B2 → B3 → B4
              S6 ────────────────────↗
Track W:      W1, W5 (any time)
              S7 → W2 → W3 → W4
              W2 ─→ A2, B2
Pending:      W2 → P2 (D20; P1, P3 in 0.9)
Release:      S8, W4, W5, A5, B4, P2 → R1
```

A1 and B1 depend only on 0.7 and may be delivered while Track S is in progress. Everything else in
A and B follows the Track S packages named above, because both milestones browse large collections
through the S3 contract and the S5 list. Milestones A and B are independent of each other and may be
delivered in either order. If one of them is cut from 0.8, its view type is removed from schema 0.7
before release so the language never declares a view without a renderer (D9).

W2 lands before A2 and B2 so the new translation and hierarchy endpoints are written with the ADR-031
names rather than renamed afterwards. A2 and B2 already wait for S5 and S6, so the extra wait is W2
alone (D15).

## Milestone A — Translation editor

### Outcome

A localization steward opens a target collection (for example the values of one codelist) as a
translation matrix: targets as rows, languages as columns. Each cell says whether a usable current
translation exists, whether one exists but is unavailable, whether one exists only in history, or
whether none exists. The steward filters to targets missing any selected language across the whole
list, not only the loaded page, and fills or corrects a translation in the cell. Routine edits are
live; a selected design draft stages them. Stories US-L03 and US-L04, scenario SC-09 (translation half).

### Model facts this milestone relies on

- A translation record is contained by a group type, which is contained, possibly recursively, by
  the language type. The language is an ancestor, not a field.
- The target owns the translation through a required one-to-many binding whose
  `uniqueToAncestorTypeKey` names the language type and whose `uniqueWhenToAttributeEquals` names
  the availability predicate (ADR-014). Live writes, draft validation and activation already enforce
  it.
- No ancestor path is stored. Ancestry is walked through `parent_object_id`, so a read that needs a
  translation's language costs the hierarchy depth per translation.

All of these come from the model. The matrix reads the binding, its uniqueness feature and the
containment chain; it never names `translation`, `language` or `object-has-translation`.

#### A1: Schema 0.7 — `translationMatrix` view contract

**Scope:**

1. Accept `schemaVersion: "0.7"` beside 0.5 and 0.6 in `models/schema.py`, `compiler.py`
   (`SUPPORTED_SCHEMA_VERSIONS`), registry, releases and `cli/model_schema_upgrade.py`. Schema 0.7 is a
   strict superset; 0.5 and 0.6 models keep parsing and activating, and reject the new view type at
   the view's `type` path.
2. Add `TranslationMatrixViewDefinition` (type `translationMatrix`) to the `ViewDefinition` union
   with config:
   `relationTypeKey`, `targetObjectTypeKey`, `translationObjectTypeKey`, `languageObjectTypeKey`,
   `targetColumns`, `languageLabelField`, `cellFields` (translated fields shown and edited in a cell),
   `searchFields` and `pageSize` (1–100).
3. Validation rules in `services/model/validation/application_rules.py`, each raising
   `ModelReferenceError` at the failing node:
   - a binding `relationTypeKey` from `targetObjectTypeKey` to `translationObjectTypeKey` exists, is
     required and one-to-many, and is not containment;
   - its `uniqueToAncestorTypeKey` equals `languageObjectTypeKey`;
   - the language type is reachable from the translation type through `parentRelationTypeKeys`;
   - `cellFields` are attached to the translation type and at least one is required or meaningful;
     `targetColumns` and `searchFields` are attached to the target type; lists are unique;
   - all three object types belong to the application.
4. Lens grouping (ADR-029): a `translationMatrix` groups under its `targetObjectTypeKey`, so it
   appears as a lens beside the target's table rather than as a new sidebar destination.
5. Starter model: schema 0.7, content release 0.8.0, with `translationMatrix` views for two target
   types (master values and codelists) in the translations application. Existing views are unchanged.
6. Frontend: extend the `ViewDefinition` union in `src/types/model.ts` and register a placeholder in
   `features/objects/views/registry.ts`; A4 replaces it.
7. Document the contract and its validation rules in `APPLICATION_MODEL.md`.

View definitions persist as JSON with a `view_type` string, so no database migration is needed.

**Exit:** a schema 0.7 model with the view parses, installs and activates; 0.5 and 0.6 models still
do; each rule above rejects an invalid configuration with a precise JSON pointer; the starter model
and the generated S1 model (extended in A2) both validate. Focused `model` group tests and the
frontend build pass.

#### A2: Translation coverage query

**Scope:**

1. `GET /api/v1/workspaces/{workspaceKey}/translation-coverage` with `applicationKey`, `viewKey`,
   optional `parentObjectId` scope, `search`, `sort`, one of `workspaceDraftId` or
   `workspaceRevisionId`, and the S3 paging parameters (`cursor`, `from`, `includeTotal`, `seek`,
   `position`) for rows.
2. Columns: `languageIds` (explicit, at most 20) or, when omitted, the first language page in the
   language's sort order; the response carries a `languagesNextCursor` so the UI can page columns
   (D10). Languages are records of the configured type in the same context.
3. Each cell reports one state (D11):
   - `current` — exactly one translation whose availability predicate holds;
   - `unavailable` — translations exist but none satisfies the predicate;
   - `historyOnly` — nothing in the current context, but a published revision of this workspace held
     one for the same target and language;
   - `missing` — none of the above;
   - `duplicate` — more than one available translation, which a draft can hold before validation.
   A cell also returns its translation's id, version, `cellFields` values and a relation-set version
   for writes, and a count when several exist.
4. `state=missing|unavailable|historyOnly|duplicate` together with `languageIds` filters rows before
   pagination: a row matches when any selected language's cell has that state. Totals count the
   filtered rows.
5. Implementation: page targets first; then fetch their translations through the binding in one
   query; resolve each translation's language with one recursive query up the containment chain
   (depth-bounded); fetch the `historyOnly` evidence in one query over revision relations for the
   page's targets. No per-row or per-cell requests. Draft and history contexts use the S2
   base-plus-overlay and revision SQL.
6. The row state filter must decide across all targets, not a page. Resolve it with one recursive
   query from the selected languages down through container types to translations (D12), and
   measure it against an S1 fixture extension: 10,000 targets, 30 languages, a three-level group
   hierarchy under each language and 150,000 translations, a tenth of them unavailable.
7. Cursors bind view, context, scope, selected languages, state filter and sort.
8. Update API.md and the OpenAPI lock.

**Exit:** each state is produced in live, draft and history contexts over both starter target types
and the generated model; a missing-filter page deep in the list is correct and within its recorded
budget; the query count per page is constant; `historyOnly` never counts as covered.

#### A3: Writes from a cell

The existing create and update APIs already save a translation, its containment and its target
relation in one transaction, live or in a draft (ADR-014). This package adds what a cell needs to
call them without asking the user for context they already chose.

**Scope:**

1. `GET /api/v1/workspaces/{workspaceKey}/translation-containers` with `applicationKey`, `viewKey`,
   `languageId`, context, `search` and cursor: the records under that language whose type can
   directly contain the translation type, with their path below the language. A language with
   exactly one container is marked as the default (D13).
2. Create from a `missing`, `unavailable` or `historyOnly` cell: `POST /objects` with the chosen
   container as parent, the target through `initialRelations` and `cellFields` as attributes. The
   name defaults from the target and language names; the user may change it.
3. Edit from a `current` or `unavailable` cell: `PATCH` with `expectedVersion`, changing `cellFields`
   or the availability field. Making a second translation available returns the existing duplicate
   error with the conflicting translation's id, so the cell can point to it.
4. Tests for the matrix path at the real boundaries: live create and edit; draft create, validation
   and activation; a duplicate created in a draft and the same language filled live, refused at
   activation with the draft kept; a draft that moves a translation's group to another language,
   rechecked at activation (ADR-014); a stale `expectedVersion`. Each refusal leaves nothing partial.

**Exit:** every write a cell performs succeeds or fails whole in live and draft contexts, with
machine-readable errors that carry enough context for the cell to keep the user's input.

#### A4: Translation matrix lens

**Scope:**

1. Replace the A1 placeholder with a generic `TranslationMatrixView` that receives the view definition.
   Rows scroll through the S5 hook; the target column and the language header stay pinned; language
   columns page horizontally with the column cursor.
2. Grid semantics: `role="grid"` with row and column counts from totals, arrow keys across cells and
   row pages, Enter to edit, Escape to cancel. Each state has a text label and an icon, not colour
   alone, and a legend.
3. Filters in the Filter popover: languages to show (searchable, from the language list) and the
   coverage state. Both live in the URL with the S5 anchor.
4. Cell editor in a popover: a `missing` cell offers a create form with the target and language fixed,
   the container preselected when there is one and a searchable container picker otherwise; a
   `current` or `unavailable` cell edits `cellFields` and availability; a `historyOnly` cell shows the
   last published content, read-only, with **Create from this** that prefills it; a `duplicate` cell
   lists the translations and opens their records.
5. After a save, only the affected cell refreshes. A failure keeps the entered text and shows the
   error through `errorMessage`; a duplicate conflict links to the conflicting translation.
6. Context: in a draft the lens shows the draft badge and writes to it; in history it is read-only.
7. Add the lens to the UI acceptance state inventory (loading, empty, filtered-empty, error, read-only
   history, draft, 390px).

**Reference pattern:** the mapping lens (`MappingGridView`) for the pinned-column grid and inline
action, and `ui/Modal` rules for the popover focus trap.

**Exit:** a steward fills a missing cell, corrects a current one and filters to gaps across the whole
list, by keyboard alone, for two target types at 1440px and 390px in live and draft contexts.

#### A5: Milestone A acceptance

**Scope:** a real-backend browser runner for the SC-09 translation half on the starter model:
Delivery Methods by language with a current Czech cell, a missing English cell and a history-only
cell; fill English live; reject a duplicate; stage a change in a draft and activate it. Repeat the
fill on the generated model. Add accessibility scenarios for the matrix and its editor (light and
dark) and reviewed visual baselines. Record A2 measurements against budgets.

**Exit:** SC-09 translation half passes; budgets hold; the runner is registered in the
[execution guide](testing/EXECUTION_GUIDE.md); US-L03 and US-L04 move to delivered in the
functionality catalogue.

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
   live and in a draft, because only the moved record's parent and edge change.
6. Tests: every refusal reason; a draft move that the draft makes valid but live makes cyclic,
   refused at activation with the draft kept; moving across types in a mixed hierarchy. Update API.md
   and the OpenAPI lock.

**Exit:** the candidate query and a deep move meet budget in each context; cycles are refused at the
query, the write and activation.

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

**Scope:** after S8, W4, W5, A5, B4 and P2 (D20, D25): the full backend `pytest` suite, frontend `npm run test`, Ruff,
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
| D2 | Window size and prefetch distance | 5 pages kept; prefetch one page from either edge; a code constant, not model configuration | S5 |
| D3 | Branch with several child types: mixed endpoint or one list per type? | One list per child-type group, matching the existing collection groups | S4, S6 |
| D4 | Does a view's `pageSize` keep its meaning? | Yes: it becomes the fetch size; no schema change | S5 |
| D5 | Totals on every page or on request? | On request (`includeTotal`); the UI asks on first load, after a query change and with position jumps | S3 |
| D6 | Relation sort keys | Related record's name and relation creation order; related-type fields later if needed | S4 |
| D7 | Draft writes still load the whole membership | **Measured in S1:** over budget (7.6 s per rename at full volume). **S2:** 4.7 s after reads moved to SQL; follow-up slice S2b scoped. **S2b:** 7.5 ms | S2b |
| D8 | A dedicated `translationMatrix` view type, or a generic coverage-matrix type? | `translationMatrix` with generic config keys. One real case exists; generalise after a second (AGENTS.md) | A1 |
| D9 | Schema 0.7 if only one milestone ships | Each view type is added by its own package; a cut milestone's type is removed before release | A1, B1 |
| D10 | Language columns | Explicit `languageIds` (at most 20) or the first page of languages; columns page with their own cursor | A2 |
| D11 | Cell states | `current`, `unavailable`, `historyOnly`, `missing`, `duplicate`; only `current` counts as covered. `historyOnly` means a published revision of this workspace held one | A2 |
| D12 | Resolving language ancestry for the gap filter | A recursive query down from the selected languages, measured in A2. A stored ancestor table only if the measurement is over budget, as a scoped follow-up | A2 |
| D13 | Which group a new translation goes into | The user picks a container under the language; preselected when there is exactly one. No model default | A3, A4 |
| D14 | Ineligible move targets | Listed but disabled, with a reason, so totals stay truthful and the user sees why | B2, B3 |
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
| D24 | Which columns sort | **Accepted 2026-09-26 (S4R3 review):** every data column sorts from its header, whatever the attribute's `sortable` flag, including Type and Relationship by their labels; every list shows the same toolbar Sort menu; D21's `sortFields` only add menu fields and `defaultSort` chooses the order. Exceptions: Actions, the computed path, JSON attributes and unrecorded timestamps | S4R3 |
