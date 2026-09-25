# Base 0.8 implementation plan

**Status:** Draft plan, 2026-09-25. Track S (scalable browsing) is planned below and starts first.
Milestone A (translation workspace) and Milestone B (hierarchy workspace) from the
[roadmap](ROADMAP.md#product-release-08--translation-and-hierarchy-workspaces) are not yet broken into
work packages.

**Target:** Product 0.8.0. Track S does not change the schema language.

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
bounded for any model. [ADR-030](DECISIONS.md#adr-030--continuous-scrolling-over-bidirectional-cursors)
records the chosen approach.

## Product outcome

A steward scrolls any collection continuously in both directions: collection lenses, record panels,
relation panels, the mapping lens, pickers and every sidebar tree branch. Rows ahead are fetched
before they are needed. A small marker appears only when the user actually waits, and quiet markers
show the start and end of the list. Memory and DOM size stay flat however far the user scrolls. A
list shows its total, can jump to its start, its end or a value (for example "go to M"), and a copied
URL reopens at the same place. This holds in live, draft and history contexts for any model.

## Principles and exclusions

1. Collections keep cursor pagination (AGENTS.md invariant). No offset-based paging is added.
2. Every addition is generic: no branch on application, object-type or relation-type keys.
3. Draft and history reads return the same results as today; only where the work happens changes.
4. Additive API changes only. Existing clients that pass `cursor` and read `nextCursor` keep working.
5. A read's cost depends on the page size and the hierarchy depth, not on the size of the dataset.

Excluded: dragging the scrollbar to an arbitrary position in a list larger than the loaded window
(ADR-030); the typed `tree` view contract, reparenting and child creation of Milestone B; translation
coverage of Milestone A; bulk and export APIs (0.9).

## Work packages — Track S

Order: S1 → S2 → S3, with S4 alongside S3 → S5 → S6 → S7. Each package states its own focused
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

**Decision needed — D1, typed values for draft/history queries.** Live values sit in a typed
`attribute_values` table; draft and revision rows store them as JSON. Two options:

- Extract typed values from JSON per dialect. No migration, but decimal comparison through floats is
  inexact, JSON extraction is not indexable, and SQLite and PostgreSQL behave differently.
- Store typed value rows for revision and draft objects, mirroring live. This needs a migration and
  more storage, but gives exact typed comparison and indexes, and lets one query builder serve all
  three contexts.

_Recommendation:_ typed value rows. Attribute values must keep their declared types, and one builder
for every context removes a class of parity defects. The migration follows the AGENTS.md startup
rules: clean bootstrap, upgrade from the preceding revision, restart, interrupted migration,
lifespan and a smoke start.

**Exit:** S1 draft and history reads meet the live budget, the parity test passes, and existing
`drafts`, `workspaces`, `mapping` and `records` groups pass unchanged.

#### S3: Bidirectional cursor contract

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
6. Cursors stay signed and bound to endpoint, ordering and filters; a changed filter still returns
   `422 invalid_cursor`.
7. Update API.md and the OpenAPI lock, and state the concurrency behavior: rows inserted or deleted
   elsewhere never cause a repeated or skipped row at a page boundary.

**Exit:** forward, backward, end, anchor, total and seek reads are exercised over the S1 fixture in
live, draft and history contexts, including a concurrent insert between page reads.

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
6. Accessibility: `aria-rowcount` from `totalCount` and `aria-rowindex` from `startIndex`.
7. Adopt it in the collection lenses, record panels (which gain a sort control, defaulting to name),
   relation panels, the mapping lens and object pickers (a searchable listbox instead of a native
   select plus **Load more**).
8. Update AGENTS.md: the rule naming `useCursorPages` and `useCursorFeed` changes to the new hook.

**Exit:** each adopted surface scrolls the S1 fixture both ways with flat memory, in two model
configurations (the starter model and the generated model) at 1440px and 390px, using the keyboard
alone.

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

#### S7: Composed volume acceptance

**Scope:** a real-backend browser runner over the S1 fixture and the starter model that scrolls,
seeks, jumps to the end, reopens from a copied URL and opens a record deep in the tree, in live,
draft and history contexts. It adds accessibility scenarios for the scrolling list and the tree,
updates visual baselines for tables that lose their page buttons (reviewed, not blind), and records
the S1 measurements again against the budgets.

**Exit:** budgets met in all three contexts; accessibility and visual gates pass; the runner is
registered in the [execution guide](testing/EXECUTION_GUIDE.md).

## Decisions summary

| ID | Question | Recommendation | Blocking |
| --- | --- | --- | --- |
| D1 | Typed values for draft/history queries: JSON extraction or typed value rows? | Typed value rows, mirroring live | S2 |
| D2 | Window size and prefetch distance | 5 pages kept; prefetch one page from either edge; a code constant, not model configuration | S5 |
| D3 | Branch with several child types: mixed endpoint or one list per type? | One list per child-type group, matching the existing collection groups | S4, S6 |
| D4 | Does a view's `pageSize` keep its meaning? | Yes: it becomes the fetch size; no schema change | S5 |
| D5 | Totals on every page or on request? | On request (`includeTotal`); the UI asks on first load and after a query change | S3 |
| D6 | Relation sort keys | Related record's name and relation creation order; related-type fields later if needed | S4 |
| D7 | Draft writes still load the whole membership | Measure in S1; scope a follow-up only if over budget | S1, S2 |
