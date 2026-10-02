# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.9

Base 0.8 is released (2026-09-29). 0.9 adds integration-grade APIs in the order of the
[0.9 delivery queue](BASE_0_9_IMPLEMENTATION_PLAN.md#delivery-queue): Q1 and Q2 are delivered (2026-09-29),
and Q3 on 2026-09-30. The queue was reordered after Q3 (C1 and Q4 first, F1 before B2, V1 as a
filler, checkpoint T1 after F2). C1, Q4 and V1 are delivered (2026-09-30), and B1 and B2 on
2026-10-01 (B2 before F1, by instruction). Next is the interim release
[0.9.0-alpha.1, PostgreSQL runtime](POSTGRESQL_RUNTIME_PLAN.md) (PG1–PG5, PostgreSQL only, decisions
accepted 2026-10-01) with the [test harness](TEST_HARNESS_PLAN.md) (H1 inside PG1, H2–H3 after PG2),
then F1. PG1, PG2, H2 and H3 are delivered (2026-10-01) and PG3 (2026-10-02); the order from here is
[PG3b](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk) (batch writes
decided in memory and written in bulk, PG-D12–PG-D17), PG4, PG5. See [Next — 0.9](#next--09).

- **Revisit: large batch deletes (PG-D18, noted 2026-10-01).** Batch delete items stay on the
  per-item path in PG3b, and neither that nor a set-based copy of it is the right answer. Large
  delete batches are not rare, and one must not occupy the job worker for minutes or stall the
  engine. Decide a deletion design (cascades, subtree impact, signed confirmation) after PG3b.

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

- [x] Foreign keys enforced and every `ondelete` rule checked against its service: delivered by
  0.9.0-alpha.1 PG2 (2026-10-01, PG-D4; `test_foreign_keys`), superseding the SQLite item from 0.8 W6.
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
- [ ] PostgreSQL follow-ups, delivered by [0.9.0-alpha.1](POSTGRESQL_RUNTIME_PLAN.md) (PG3 for (1),
  PG2 and PG5 for (2)). (1) **Done in PG3 (2026-10-02):** D28 cancellation on PostgreSQL (a cancel
  request answered while a chunk runs, the `atomic` job rolled back between items, the lease shared
  by two workers) and live writes beside a background job, which wait for one chunk at most in the
  job's workspace and not at all elsewhere (`test_pg3_concurrency`); PG3b records the time of one
  chunk, and PG5's full-size run confirms it. (2) After the migration, review the code for SQLite
  technical debt and remove it: dialect branches, `json_each` row lists, the recursive arms, the
  `SQLITE_LOCK_WAIT_SECONDS` setting, explicit dependant deletes standing in for unenforced foreign
  keys, SQL-level claims written because SQLite ignores `FOR UPDATE`, the explicit `BEGIN` of
  `db.begin_snapshot_read` and `db.begin_transaction` (SQLite's driver begins no transaction before a
  `SAVEPOINT`; a job chunk uses the latter), and budgets measured only on SQLite (D13 included).
  PG1 (2026-10-01) removed the SQLite migrations, settings default and engine branch, and made
  `begin_snapshot_read` PostgreSQL's. PG2 (2026-10-01) removed every dialect branch, the `json_each`
  row list, the recursive arms, `SQLITE_LOCK_WAIT_SECONDS`, `db.begin_transaction` and the FTS5 search
  (`test_boundaries` holds it); the explicit dependant deletes stay, since the services order them for
  audit and matrix states. Left for PG5: budgets measured on SQLite and the planner comments.
- [ ] Unique-value checks over non-text values (integer, decimal, date, dateTime, boolean) still read
  every value of the attribute, live and in a change set: the value indexes cover `text_value` only
  (0.9 B2 added the live one). Add them with 0.11's model-derived indexes.
- [ ] PostgreSQL at production scale and across nodes (0.11): the volume fixture at full scale, pool
  sizing, several processes and nodes. The trigram search index and the relation matrix's PostgreSQL
  forms (0.8 A2, A3b) were delivered by 0.9.0-alpha.1 PG2 (2026-10-01); single-node multi-writer
  uniqueness moves to [PG3](POSTGRESQL_RUNTIME_PLAN.md) (delivered 2026-10-02: the workspace lock).
- [ ] Found in PG3 (2026-10-02), moved to
  [PG3b](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk): an activation
  that drops a matrix shape could deadlock with a live batch whose matrix notes it locks before its
  commit check (not reproduced). The other finding, change-set writes beside a retirement, was fixed
  in PG3's amendment the same day.
- [ ] H4: the package checks for PG3's seven groups took 2 min 7 s on `-n 10`, over the 2-minute
  ceiling; the longest tests are `test_change_set_position_reads` (43 s) and `test_model_query`'s
  every-criterion cases (17 s each).
- [ ] Assess the cost of matrix state maintenance per commit (found by the test harness assessment,
  2026-10-01): a commit recomputes the touched matrix cells, about 7 ms in the parity and
  type-change test models, and a single create cost 19 ms through the API. Measure it on the volume
  fixture against the 0.8 A2 write budget before changing anything.
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
