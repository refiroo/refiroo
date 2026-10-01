# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.9

Base 0.8 is released (2026-09-29). 0.9 adds integration-grade APIs in the order of the
[0.9 delivery queue](BASE_0_9_IMPLEMENTATION_PLAN.md#delivery-queue): Q1 and Q2 are delivered (2026-09-29),
and Q3 on 2026-09-30. The queue was reordered after Q3 (C1 and Q4 first, F1 before B2, V1 as a
filler, checkpoint T1 after F2). C1, Q4 and V1 are delivered (2026-09-30), and B1 and B2 on
2026-10-01 (B2 before F1, by instruction); F1 is next. See [Next — 0.9](#next--09).

## Open decisions

No 0.8 decision is open ([0.8 decisions](BASE_0_8_IMPLEMENTATION_PLAN.md#decisions-summary)). The
0.9 decisions are in the [0.9 plan](BASE_0_9_IMPLEMENTATION_PLAN.md#decisions); the 0.10 ones in
[MODEL_AUTHORING.md](MODEL_AUTHORING.md).

See `ROADMAP.md` for the delivery scope, exit gates and full milestone sequence.

## Base 0.8 delivery record (released 2026-09-29)

Track S (S1–S8, ADR-030), Track W (W1–W6, ADR-031), Milestone A (A1–A6, ADR-033), Milestone B (B1–B5b),
P2 (P2a, P2b) and Milestone C (C0–C5, ADR-034) are complete, accepted by R1, R1b and R2, with D1–D46
decided. Known budget exceptions D26, D29 and D30 and the 500-record restructuring limit (D44) remain
as recorded. See `CHANGELOG.md` and `BASE_0_8_IMPLEMENTATION_PLAN.md` for details.

## Base 0.7 delivery record (released 2026-09-25)

WP-1–WP-9, WP-10A–K, WP-11, WP-12, WP-13A/B/C and WP-14 are complete, with ADR-022 relation-set
versions, ADR-028 change set version selection, ADR-029 contextual collections, UI-07 gates, the frontend
redesign and dark mode. See `CHANGELOG.md` and `BASE_0_7_IMPLEMENTATION_PLAN.md` for details.

## Base 0.6 delivery record (complete 2026-09-11)

WP0–WP8, WP8.1-A–C, ADR-026 slices 0–5, WP9 slices A–D, WP10 and UI-01–UI-06 are all complete.
See `CHANGELOG.md` and `BASE_0_6_IMPLEMENTATION_PLAN.md` for detailed delivery history.

## Next — 0.9

- [ ] Enforce foreign keys on SQLite (`PRAGMA foreign_keys=ON` per connection) or document that every
  `ondelete` rule is advisory there. 0.8 W6 found none of them, not only the `workspaces.key` ones, are
  enforced at runtime; services delete dependants explicitly and W6 rechecks the workspace at commit.
  Enabling it needs a data check for existing violations and must keep the table-rebuild migrations,
  which require it off, working.
- [ ] 0.9 planning ([plan](BASE_0_9_IMPLEMENTATION_PLAN.md), [integration design](INTEGRATION_API.md)): document
  set accepted 2026-09-28; decisions D1–D16 and CONSUMER_API C-D1–C-D16 accepted 2026-09-29;
  INTEGRATION_API sections P, B, F, Q and J, the schema 0.8 section and ADR-036–038 drafted
  2026-09-29; work packages and the delivery queue specified 2026-09-29. Open: review of the F and J
  drafts. Implementation started 2026-09-29 with Q1 and Q2 (delivered); Q3 delivered 2026-09-30 with
  D17–D19, C1 with C-D17–C-D20 and Q4 with D20–D22; B1 2026-10-01 with D23–D26, B2 with D27–D30.
- [x] Integration-grade query expressions beyond daily-use filters: delivered as 0.9 Q3 (2026-09-30),
  the model-aware query; `asOf` with effective periods in Q4 (2026-09-30).
- [ ] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a change set merely because several records change (0.9).
  Object items run inline delivered as 0.9 B1 (2026-10-01) and in the background as B2
  (2026-10-01); relation and relation-set items (B3) remain.
- [ ] Asynchronous CSV/XLSX import and export with validation previews; import runs an import profile
  (revised D3, [MODEL_AUTHORING A1](MODEL_AUTHORING.md#delivery)).
- [ ] Ordered change feed and retryable webhooks.
- [x] Cross-type object lookup `GET /objects` (P1), moved from 0.8 (D20): delivered as 0.9 Q1
  (2026-09-29).
- [x] A general relation edge list with publication context (P3), moved from 0.8 (D20): delivered as
  0.9 Q2 (2026-09-29).
- [ ] T1: record a budget for dated reads (`asOf` on the per-type list and the model query, live, in a
  change set and a publication) in the `volume_baseline.py --scale 1` run; Q4 recorded none (found in
  Q4, which ran no `volume`). The volume fixture declares no period yet, so T1 adds one to it.
- [ ] J1's export budget names "110,000 records"; the volume fixture holds 258,000 since 0.8 A2 (found
  in Q1). Restate it when J1 is delivered.
- [x] Built-in Scalar API reference at `/docs` replacing Swagger UI and ReDoc: delivered as 0.9 V1
  (2026-09-30) with the management API as its source; pinned script bundled, CDN by setting, outside
  the OpenAPI document.
- [ ] V2: each installed consumer API contract version as a further source on `/docs` (needs C6).

## Next after 0.9 — 0.10 model authoring and spreadsheet onboarding

- [ ] 0.10 design ([MODEL_AUTHORING.md](MODEL_AUTHORING.md), ADR-035) and provisional
  [plan](BASE_0_10_IMPLEMENTATION_PLAN.md) (2026-09-29, A0–A8 and R; review after 0.9 Track J): direction accepted 2026-09-29;
  A-D1–A-D3 decided 2026-09-29 (A-D2: declared navigation groups); others open; packages A1–A8 to specify after 0.9 Track J's import contract.
  - [ ] A0 design pass: A-D4–A-D10, plan D1–D10, API design, operation vocabulary.
  - [ ] A1 import profile contract and execution (delivered inside 0.9 Track J).
  - [ ] A2 operation API on model drafts: additive and draft-only operations, history, undo.
  - [ ] A3 source profiling and the dry-run summary after each operation.
  - [ ] A4 editor: model pane, relationship matrix, preview, layout editing.
  - [ ] A5 editor with a source file: source and mapping panes, saved and re-run profiles.
  - [ ] A6 inference over the table patterns.
  - [ ] A7 model-description sheets and matching across files (may move to 0.10.x).
  - [ ] A8 list blocks in sheets laid out for reading (may move to 0.10.x).
  - [ ] Synthetic acceptance workbooks with the shapes of the private samples.
  - [ ] Non-blocking open items: A-D11 nested navigation groups (one level in 0.10); A-D12 record
    counts on the group page (none in 0.10, later only as a bounded read).

## Later — production and self-service authoring

- [ ] Complete the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md), including
  ownership, contribution, dependency, security, trademark and commercial-service documentation.
- [ ] PostgreSQL migration follow-ups. (1) Test 0.9 D28 job cancellation on PostgreSQL: a cancel
  request answered without waiting for a running chunk, the `atomic` job's chunk rolled back between
  items, and the lease guard with two workers. Bound the latency of live writes beside a background
  job in `test_background_volume` (B2 recorded it only: on SQLite the worker retakes the writer lock
  after each chunk, so such a write waits for the whole job and fails after
  `SQLITE_LOCK_WAIT_SECONDS`). (2) After the migration, review the code for SQLite
  technical debt and remove it: dialect branches, `json_each` row lists, the recursive arms, the
  `SQLITE_LOCK_WAIT_SECONDS` setting, explicit dependant deletes standing in for unenforced foreign
  keys, SQL-level claims written because SQLite ignores `FOR UPDATE`, the explicit `BEGIN` of
  `db.begin_snapshot_read` and `db.begin_transaction` (SQLite's driver begins no transaction before a
  `SAVEPOINT`; a job chunk uses the latter), and budgets measured only on SQLite (D13 included).
- [ ] Unique-value checks over non-text values (integer, decimal, date, dateTime, boolean) still read
  every value of the attribute, live and in a change set: the value indexes cover `text_value` only
  (0.9 B2 added the live one). Add them with 0.11's model-derived indexes.
- [ ] PostgreSQL performance and multi-writer uniqueness hardening, including the trigram form of
  the S8 search index and the relation matrix's SQLite-only statements: the change set walk down
  (two recursive arms, which PostgreSQL needs in one recursive term) and the stored state filter's
  row list, read through `json_each` on SQLite and as a plain `IN` list elsewhere (0.8 A2, A3b).
- [ ] Precomputed sort keys for attribute and ancestor sorts over very large parents (D26, after 0.9).
- [ ] 0.12 security: engine-provided OAuth 2.0 with JWT for backend, frontend and consumer APIs (no API
  keys, no credential in a URL), application/object/operation authorization, audit identity,
  HMAC-signed webhooks, and UI administration of OAuth clients and webhook subscriptions.
- [ ] 0.12: replace the pre-authentication, default-enabled workspace mutation posture with authenticated,
  authorized workspace administration; retain the capability gate as deployment defence in depth.
- [ ] Multi-node active-model propagation and protected publication; verify split deployment
  (administration and public instances on one database) against the caveats in ARCHITECTURE.
- [ ] 1.0: migration-class operations in the 0.10 editor (key renames, splits, merges, cardinality) on
  the 0.11 migration boundary.
- [ ] Read-only dependency graph visualization where it improves comprehension.
- [ ] Product 0.11: executable runtime-data migration plans for currently blocked model changes.
- [ ] Product 0.11: model replacement for a change set started from a publication, with a side-effect-free impact/loss preview,
  explicit confirmation tied to the reviewed versions or cancel, atomic workspace model/data switch,
  immutable history and unaffected-workspace isolation. Confirmation cannot waive target validity or
  parser support; nothing in Base 0.6 overrides them.
- [ ] Product 0.11: add workspace-scoped model-release assignment for staged tenant or
  governance-domain rollout.
  Resolve the workspace before its immutable model snapshot, scope compatibility and migration to that
  workspace, bind cursors to the release identity and switch assignments atomically. Supporting mixed
  schema-language versions additionally requires a bounded current/previous parser window and explicit
  conversion; workspace pinning alone is not schema compatibility.
- [ ] Product 0.11 (ADR-028): move a change set onto a release its content does not already satisfy, by
  reusing the migration preview/confirm machinery against that change set's own candidate graph and
  current-live base. The review reports conversions and potential loss of change-set content and applies only on
  confirmation of the exact reviewed change set and release versions; nothing forces the move through or
  happens without being asked, and a move never deletes change-set content to make a target fit.
- [ ] Extension packaging after two concrete reuse cases exist.

## Explicitly not planned for Base 0.7

- Model-workbench information-architecture redesign.
- Physical purge of publications or audit history.
- Graph-canvas-first model authoring.
- Arbitrary server-filesystem model load/save.
- Client-side loops over single-item APIs presented as bulk operations.
- Starter-key branches in backend or frontend behavior.
- Object drafts, object revisions, object activation/retirement, or per-object publication state.
- A second public CRUD dialect under `/change-sets/{draftId}/objects` or `/relations`.

## Known accessibility exceptions

- [x] WP1-001: the navigation resize separator now sits inside the navigation landmark (fixed
  2026-09-24); its allowlist entries were removed. Collection and settings popovers render inside a
  landmark so their dismiss controls are not stray page content.
- [x] WP1-002: the child/relation table regions have distinct accessible labels since Base 0.8 S5
  (each panel names its scrolling region); the gate's exception matched nothing and was removed in S7.
