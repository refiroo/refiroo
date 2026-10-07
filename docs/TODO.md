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
then F1. PG1, PG2, H2 and H3 are delivered (2026-10-01), and PG3 and
[PG3b](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk) (batch writes
decided in memory and written in bulk, PG-D12–PG-D17) on 2026-10-02; the order from here is
[H4](TEST_HARNESS_PLAN.md#h4-testing-consolidation) (the testing consolidation, H4a–H4e, planned
2026-10-02 on the [testing strategy](testing/STRATEGY.md); H4a delivered and approved the same day,
decisions D-1–D-7 taken, H4b delivered the same day, [API_JOURNEYS](testing/API_JOURNEYS.md#decisions)), then PG5 (H4 stopped after H4d-1 and PG4 dropped,
2026-10-03). **PG5 is delivered and 0.9.0-alpha.1 released (2026-10-03):** budgets re-measured on
PostgreSQL, the 100,000-item batch measured once, the remaining budget exceptions deferred to the
first fixes after 1.0 ([handoff](POSTGRESQL_BUDGETS.md)). **F1 is delivered (2026-10-03)**: feed
positions, publish entries and the feed read (D31–D34). **B3 is delivered (2026-10-03)**:
relationship and relationship-set items in batches (D35–D39). **F2 is delivered (2026-10-03)**:
feed retention and recovery from the active publication (D40–D41). **T1 is delivered
(2026-10-03)**: the Q, B and F checkpoint, with three capture and publish defects fixed. T1a
(copies inside PostgreSQL) and T1b (upper-case error codes) are delivered (2026-10-04). **C2 is
delivered (2026-10-04)**: the consumer tier with get by ID (C-D21–C-D26). **C3 is delivered
(2026-10-04)**: consumer lists and every parameter kind (C-D27–C-D33). **C3a is delivered
(2026-10-04)**: attribute sorts read in value order (D46–D48). **C3b is delivered (2026-10-04)**:
several values the OpenAPI way, `%2C` for a comma in a value (C-D32 amended). **C4 is delivered
(2026-10-05)**: XREF lookup and scoring (C-D34–C-D41). **C5 is delivered (2026-10-05)**: the
definition's parameters on XREF, `scoresFrom` (C-D42–C-D46). **C14 is delivered (2026-10-05)**: batch
resolve, one scoring path with XREF, exact rules first (C-D47–C-D53). **C15 is delivered
(2026-10-05)**: crosswalk, `to.{parameter}` on every consumer read (C-D54–C-D58). **CN1 is delivered (2026-10-05)**:
the consumer API's name is `consumerApi` in public contracts (U-D1, C-D59). **C6a is delivered (2026-10-05)**:
reads pinned to a publication (`publication`, `latest`), the publications list with `eventSequence`
and ETag (C-D60–C-D68). **C6b is delivered (2026-10-05)**: the API index `GET /api/consumer` and an
OpenAPI 3.1 document per consumer API (C-D69, C-D70). **V2 is delivered (2026-10-05)**: every consumer API
as a source on `/docs`. **C8 is delivered (2026-10-05)**: parity acceptance; `objectType` in
projections, the parent keyed by output names (C-D72–C-D75). **C16 is delivered (2026-10-05)**: `asOf`
on every consumer read (C-D76–C-D80). **C9 is delivered (2026-10-05)**: event definitions
(C-D81–C-D86). **C10 is delivered (2026-10-06)**: the event deriver, the event store and the pull feed
(C-D87–C-D92, C-D95). **U2 is delivered (2026-10-06)**, alongside C10: the token layers, the
bundled fonts, the top bar, rail and data-context band, `PageHeader`, `StatusPill` and `Card`
(U-D7–U-D9, [record](SETTINGS_AND_UI_PLAN.md#u2-delivery-record)). **C11 is delivered
(2026-10-06)**: webhook subscriptions, their sealed signing keys, the host allowlist and the
suspensions on activation and retirement (C-D96–C-D102). **C12 is delivered (2026-10-06)**: webhook
delivery, signed, in order, retried for 24 hours, with the dispatcher's suspensions, `reset` on
resume and the background threads' outage logging (C-D103–C-D111). **C13 is delivered
(2026-10-06)**: the events' acceptance end to end, the delivery budget, and C-D114's rule for
records leaving a filter's scope documented (C-D112–C-D114). **U3 is delivered (2026-10-06)**: the
Settings area and `GET /api/v1/system` ([record](SETTINGS_AND_UI_PLAN.md#u3-delivery-record)), revised the same day.
Next: UA, the Atlas redesign (ADR-040), before U4 and U5. See [Next — 0.9](#next--09).

- **For UA0 (2026-10-06): the user's check on the dev server.** The popover click and the
  workspace switcher are fixed ([record](SETTINGS_AND_UI_PLAN.md#ua0-record-2026-10-06)); UA0 is
  done when the user has seen the settings navigation and the application tabs respond to the
  first click with a popover open, and that the applications now stand 36px after the product
  name (also done in UA0), on the Settings page as well, which now has the same top bar (U-D14).
- **From UA0 (2026-10-06): three failures seen once, not reproduced.** `RelationMatrixView.test`
  "lets a reload replace cells re-read after earlier saves" (once in U3's parallel `vitest related`;
  30 repeats under load passed in UA0). `test:browser:a4` timed out once waiting for the cell dialog
  to reopen after an unlink (`a4-relation-matrix.mjs` line 383) and passed on the rerun.
  `test:browser` failed once with a timeout whose step was not captured, then passed twice.
- **For the user to place, from C12 (2026-10-06): an outbound proxy for webhooks.** The dispatcher
  connects to receivers directly (C-D107); a deployment that reaches the internet only through an
  HTTPS proxy cannot deliver. Adding one means connecting through the proxy while keeping the
  address check (C-D107) meaningful, since the proxy, not the engine, then resolves the host.
- **For the user to place, from C13 (2026-10-06): telling a filtered subscription that a record left
  its scope (C-D114).** Filters read a record's state when its events are sent, so a record moved
  out of an `ancestor` filter, or edited so a `related` or `projection` filter stops matching, is
  not sent; the receiver keeps a copy it should drop. Documented in 0.9, with the workarounds. A fix
  needs the record's state before the change for each filter kind, which events do not keep
  (C-D89); how much of it the audit entries already hold was not checked.

- **For U6, from U2 (2026-10-06).** (Booleans are plain text since UA3.) Move each `.surface` panel onto `ui/Card` or a ruled section, whichever reads better in
  the product (U-D8). Remove the older token names in `styles/base.css` once no screen reads them.
- **Intermittent: wp9-navigation's record return (seen once in U2; 4 of 10 runs in UA0,
  2026-10-06).** `ui03a-navigation.mjs:144` waits 10 s for the list URL with its anchor after
  **Back to list** following a reload of the record page; seen at both call sites (live,
  `wp9-navigation.mjs:263`, and change set, `:383`). Without UA0's changes it passed 2 of 2 runs,
  so a link to them is not ruled out; three runs with diagnostics at the wait passed, so the URL it
  lands on is still unknown. Next: capture that URL at the failure and see whether the anchor
  restored after a reload depends on the page's height. _UA3 (2026-10-06):_ 2 of 3 runs failed
  there, both at the change-set call site (`:383`); the UA2 revision's one run failed there too.
  _UA4 (2026-10-07):_ the one run failed there again (`:383`). _UA4 revision, record ID
  (2026-10-07):_ failed once at the live call site (`:263`), passed on the next run.
- **For the UA4 revision (2026-10-07): the user's pick of the pencil variant.** `AttributesPanel`
  reads `localStorage["rdm:edit-hint"]` (`always`: the pencil faint at rest; otherwise only on hover
  and focus). Once the user picks, keep that one and remove the switch and the other variant's CSS.
- **From the UA4 revision (2026-10-07): a column header's accessible name includes its resize
  handle** ("Path Resize Path column"), in every `ui/DataTable` table and in the collection tables
  before it. Naming the header with `aria-label` fixes the name but makes every header match a
  label lookup for the same field name (`getByLabelText`, Playwright `getByLabel`), which the form
  tests and runners rely on. Next: draw the handles outside the header cells (one layer over the
  header row), for UA7's accessibility gate.
- **Since UA3 (2026-10-06), seen in the UA4 revision: `test:browser:authoring` fails on two
  "Add Domain" buttons.** An empty collection's `EmptyState` carries **Add {type}** (UA3) beside the
  page header's button of the same name, and `wp9-authoring` clicks it by exact name (strict mode).
  Whether an empty list should repeat the header's action under the same name is the user's call;
  then the runner follows.
- **From UA4 (2026-10-07): `test:browser:b4` fails at its cycle refusal check.**
  `b4-hierarchy-acceptance.mjs:136` matches the API's refusal against `/422.*parent_cycle/`, but the
  error code is `PARENT_CYCLE`, so the check fails while the API refuses correctly (422
  `PARENT_CYCLE`, for both the system and the domain case). The runner's pattern needs the `i` flag
  or the upper-case code. Every check before it passed, including the published breadcrumb.
- **From UA0 (2026-10-06): `test:browser:b3` fails at its drag of Sodium.** `helpers/tree.mjs:189`
  waits for the drag preview after pressing on Sodium in the opened Electrolytes branch
  (`b3-tree-lens.mjs:579`); none appears. It fails the same without UA0's changes, so it came
  earlier; U3's checks did not run b3. _Since UA2 (2026-10-06):_ the drag of Sodium passes and the
  run stops later, in B5b, differently in each of two runs: after the keyboard **Move to…** the
  focus is on the `vol-groups` window instead of the moved group (`b3-tree-lens.mjs:467`); and,
  in the change set, the page has scrolled the lens's top-level heading under the sticky band, so
  the drop names no target and no dialog opens (`:459`). Neither step was reached since UA0, so it
  is not known whether they failed before UA2. _UA2 revision (2026-10-06):_ the Sodium failure's
  cause is found: Sodium sat just below the bottom edge of its branch's scrolling window, and
  `dragFrom` pressed where it was without scrolling it into view, so the press hit the window's
  edge; whether it fitted depended on the layout. The helper now scrolls the row into view first,
  as a user would. The whole run then passed once (30 checks, B5b included); the two B5b steps
  stay here until they pass again, since they failed differently each time. _Folding headings
  (2026-10-07):_ both B5b failures had the same kind of cause. The change set's band is taller (it
  carries the change set's actions), and scrolling a row only "into view" left the top-level
  heading under it, so the pointer rested on the band. `dragFrom` and `dragOver` now bring the
  row to the middle of the view; b3 then passed in full (30 checks). Kept here until a second run
  confirms it.
- **`test:browser:b3`: "Shift+Tab never reached the tree" (seen once, 2026-10-07).** In the volume
  maintenance journey (`b3-tree-lens.mjs:349`, `maintain` → `keyIntoTree`), sixty Shift+Tab presses
  never focused a tree item. Seen in one of two runs with the tree's wheel handler (the other passed
  all 30 checks), and not in one run of the committed UA4 code without it; the handler touches no
  focus, but one run does not rule it out. Next time: capture the focused element at the failure.
- **`test:browser:c4` fails at its own API call (seen 2026-10-07).** `c4-restructuring.mjs:336`
  reads `/objects/system-group/{id}/history?workspaceKey=default` and the API refuses the
  parameter (`422 UNKNOWN_PARAMETER`). The runner, not the UI, sends it; when the history route
  stopped taking `workspaceKey` was not checked.

- **Publish and change-set creation move the workspace through Python (found 2026-10-03, F1;
  measured and decided in T1).** Publishing 1,000 renamed records in a 26,000-record workspace takes
  11.3 s after T1's fixes (25.0 s before). Decided: the copies move into PostgreSQL as plain
  `INSERT … SELECT` in [T1a](BASE_0_9_IMPLEMENTATION_PLAN.md#t1a-copies-inside-the-database), sized
  for the volume fixture at 0.1 scale. Larger workspaces are deferred until after 1.0 (below).
- **Containment relations in the audit log (found 2026-10-03, F1).** A live create or move audits no
  containment relation, while the live delete cascade audits one. The feed leaves them out
  everywhere (the record's `parentObjectId` names its parent); the audit log keeps the cascade's
  entries without a position. Align the audit log when a history change next touches it.

- **Revisit: large batch deletes (PG-D18, noted 2026-10-01).** Batch delete items stay on the
  per-item path in PG3b, and neither that nor a set-based copy of it is the right answer. Large
  delete batches are not rare, and one must not occupy the job worker for minutes or stall the
  engine. Decide a deletion design (cascades, subtree impact, signed confirmation); PG3b is
  delivered (2026-10-02). The user decided on 2026-10-02 (H4a, D-6) that batch delete items must be
  able to cascade (journey J11.6); the design decides how a batch confirms the impact it deletes.
- **Lifecycle audit reads (decided 2026-10-02, H4a D-5).** The engine records workspace, change set
  and publication lifecycle events and model draft events, but no route reads them. Keep recording
  them and add reads (journeys J19.5, J08.9); consider showing a workspace's activity in the UI.
  To plan as its own package. F1's feed now gives publications (`published`, `withdrawn`) positions.

## Open decisions

No 0.8 decision is open ([0.8 decisions](BASE_0_8_IMPLEMENTATION_PLAN.md#decisions-summary)). The
0.9 decisions are in the [0.9 plan](BASE_0_9_IMPLEMENTATION_PLAN.md#decisions); the 0.10 ones in
[MODEL_AUTHORING.md](MODEL_AUTHORING.md).

- **Settings, integration administration and UI foundation (approved 2026-10-05).** U-D1–U-D6 taken
  in [SETTINGS_AND_UI_PLAN.md](SETTINGS_AND_UI_PLAN.md#decisions); U1 delivered, Direction B "Open"
  chosen (ADR-039). CN1 delivered (2026-10-05).
- **User documentation is not scheduled in any release yet.** API.md, CONSUMER_API and
  CURRENT_FUNCTIONALITY describe contracts and capabilities, but no guide for integrators or users
  exists. When it is planned, it must state these points very clearly, as the user asked:
  - **Reading an older publication after a model release (C-D60, 2026-10-05).** A publication is
    read with the definition of the model release it was published under, and only when that
    release declares the same consumer API at the requested contract version. After a release that
    raises the contract version, publications made before it cannot be read through the new
    version (`409 PUBLICATION_CONTRACT_MISMATCH`) until a new publication is made. Integrators
    pinning extracts to publications must plan contract version changes with this in mind.
  - The consumer search limits: contains from 3 characters and at most 10,000 matches (C-D37).
  - **Which workspace a consumer read addresses (C-D16, C-D23).** Every consumer read (get by ID,
    lists, XREF, batch resolve, publications) reads one workspace: the one named by `workspace`, or
    the deployment's default. Changing the default workspace moves every consumer that does not
    name one, so production integrations should always name it. The response names the workspace
    read in `RDM-Workspace`.
  - **Publications and `latest` (C-D61, C-D62).** `latest` is the workspace's current publication;
    after a withdrawal with no new publication there is none (`404`). A publication read by its ID
    stays readable after it is superseded or withdrawn. A publication is found only in its own
    workspace (C-D62).
  - **ETag (C-D65).** Any live write in the workspace changes a live read's ETag, also one the
    consumer API does not show; a pinned read's ETag never changes.

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
- [x] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a change set merely because several records change (0.9).
  Object items run inline delivered as 0.9 B1 (2026-10-01) and in the background as B2
  (2026-10-01); relation and relation-set items as B3 (2026-10-03).
- [ ] Asynchronous CSV/XLSX import and export with validation previews; import runs an import profile
  (revised D3, [MODEL_AUTHORING A1](MODEL_AUTHORING.md#delivery)).
- [x] Ordered change feed and retryable webhooks. The feed read with positions in commit order is
  delivered as 0.9 F1 (2026-10-03), retention and recovery as F2 (2026-10-03), event definitions
  as C9 (2026-10-05), the events and their pull feed as C10 (2026-10-06), subscriptions with their
  signing keys, suspensions and C-D93's resume as C11 (2026-10-06), webhook delivery with
  full-object batches, a byte limit, signing, retries and the delivery suspensions as C12
  (2026-10-06), and the events' acceptance as C13 (2026-10-06).
- [x] Cross-type object lookup `GET /objects` (P1), moved from 0.8 (D20): delivered as 0.9 Q1
  (2026-09-29).
- [x] A general relation edge list with publication context (P3), moved from 0.8 (D20): delivered as
  0.9 Q2 (2026-09-29).
- [x] T1: record a budget for dated reads (`asOf` on the per-type list and the model query, live, in a
  change set and a publication): delivered in T1 (2026-10-03); four over 100 ms, recorded as
  POSTGRESQL_BUDGETS E8.
- [ ] C16: dated consumer reads over budget, recorded (C-D80): a dated list's first page with a total
  and its position jump 192–232 ms live and pinned at full volume (twice the undated read, the E8
  shape), and a dated 1,000-identifier batch 2.2 s, where identifiers not effective on the date lose
  their exact match and exact-first (C-D52) reads their contains matches. Revisit with E8's fixes, or
  with a rule settling a lookup whose exact matches are all filtered out.
- [ ] J1's export budget names "110,000 records"; the volume fixture holds 258,000 since 0.8 A2 (found
  in Q1). Restate it when J1 is delivered.
- [x] Built-in Scalar API reference at `/docs` replacing Swagger UI and ReDoc: delivered as 0.9 V1
  (2026-09-30) with the management API as its source; pinned script bundled, CDN by setting, outside
  the OpenAPI document.
- [x] V2: each consumer API of the active release as a further source on `/docs`: delivered 2026-10-05
  ([record](BASE_0_9_IMPLEMENTATION_PLAN.md#v2-delivery-record)).
- [x] Consumer lists ordered by `sortBy` over the 100 ms budget (found in C3, 0.5–2.6 s): delivered
  as C3a (2026-10-04), 10–12 ms through value-order indexes. Left at the budget line and recorded,
  not tuned: a position jump to row 50,000 (123 ms) and an ancestor filter over 20,000 items with
  `includeTotal` (101 ms); 0.8 D26's stored sort key, after 0.9, would serve deep positions and
  attributes with few distinct values.
- [ ] XREF's refusal of a term in every record over the 100 ms budget (found in C4; recorded with the
  user's agreement, 2026-10-05): `400 QUERY_TOO_BROAD` for "item" takes 116 ms at full volume. Its
  contains checks read every value the trigram index matches before the record type filters them: a
  promoted rule on groups' codes reads all 100,000 item codes containing the term (~60 ms). Closing
  it needs the record type in the value index, a design change; lookups themselves take 34–58 ms.
  C14 (2026-10-05): 147 ms (C5's run 108 ms); both code-contains reads, own and promoted, now join
  all 100,000 matching values before their limit stops them. A trigram index holding the attribute
  key made it 181 ms and was left out.
- [ ] Batch resolve items with different parameters resolve in one group each (C-D51, C14): a batch
  whose every item has its own parameter values runs close to one lookup per item. One statement
  for all of them would need C3's parameter predicates to read their values from a relation of
  `(item, parameter, value)` instead of literals. For a measured need only.
- [ ] Publish cost of C6a's publication indexes (C-D68): 10.8 s at 0.1 scale on a reused seed, within
  the 11 s budget but 1.7 s above T1a's 9.1 s, leaving 0.2 s margin. Which index costs what is not
  measured (the `btree_gin` trigram on `publication_objects` is the likeliest). Revisit if a later
  package moves publish over its budget.
- [ ] Value-order attribute sort in the change-set context (C-D67): base and overlay in one union,
  partial indexes do not cover it, and change-set base copies would maintain the indexes. Unmeasured;
  a package of about C3a's size if a management list needs it.
- [ ] Consumer ETag: compare `If-None-Match` before the read to save the read itself (C-D65), for a
  measured need only.
- [ ] Comma-separated values on the management API's repeated filters (`filter.<field>.eq=A,B`), as the
  consumer API reads them since C3b (OpenAPI `form` style: a literal comma separates, `%2C` is a comma
  inside a value). Today they repeat the parameter only.

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
- [ ] **First fixes after 1.0: the PostgreSQL read budgets (deferred by the user, 2026-10-03).** PG5
  restated every volume budget on PostgreSQL: statements and rows hold everywhere; 11 of 154
  full-volume reads exceed 100 ms. [POSTGRESQL_BUDGETS.md](POSTGRESQL_BUDGETS.md) is the complete
  handoff: the measuring method (plans per statement, not repeated full replays), the closing table,
  what PG5 changed and why, and each exception's cause, fix options, effort and what was tried:
  E1 change-set matrix filters (136–154 ms), E2 change-set searches matching nearly everything
  (154–211 ms, needs a decision on exact totals first), E3 D26's sort keys (104–150 ms), E4 the live
  history-only matrix filter (108 ms), E5 change-set seek and position near the limit (91–99 ms), E6
  plans on a just-captured base before statistics exist, E7 a 100,000-item background batch in a
  change set (64 s, target 60 s).
- [ ] **After 1.0: creating change sets and publishing for 250,000 records and more (deferred by the
  user, 2026-10-03; revisit when MDM is taken up).** T1a sizes both for the volume fixture at 0.1
  scale. At the full fixture, a copy by `INSERT … SELECT` took about 33 s, most of it maintaining 17
  indexes row by row. Loading first and building the indexes once took about 14.5 s (T1 probes).
  Three steps, each its own decision:
  - Partitioned snapshot tables: each publication or base loaded without indexes, then indexed and
    attached, and dropped as a whole.
  - Creating a change set and publishing as background jobs (B2's worker), with a notification
    stream for the UI.
  - The publish's whole-graph validation as set queries in SQL, held to `rules.py` by
    `test_rule_parity`. Today it loads the workspace into Python. Two rules checked in SQL over the
    full fixture took 0.41 s and 0.05 s.

  Other paths that move bulk data through Python, to list in the same audit: history reads of
  whole publications, the D29 container move and restructuring previews.
- [x] PostgreSQL follow-ups, delivered by [0.9.0-alpha.1](POSTGRESQL_RUNTIME_PLAN.md) (PG3 for (1),
  PG2 and PG5 for (2); closed by PG5, 2026-10-03). (1) **Done in PG3 (2026-10-02):** D28 cancellation on PostgreSQL (a cancel
  request answered while a chunk runs, the `atomic` job rolled back between items, the lease shared
  by two workers) and live writes beside a background job, which wait for one chunk at most in the
  job's workspace and not at all elsewhere (`test_pg3_concurrency`); PG3b (2026-10-02) recorded the
  time of one chunk, 0.25–0.46 s for 500 items at both seeded sizes, and PG5's full-size run
  confirms it. (2) After the migration, review the code for SQLite
  technical debt and remove it: dialect branches, `json_each` row lists, the recursive arms, the
  `SQLITE_LOCK_WAIT_SECONDS` setting, explicit dependant deletes standing in for unenforced foreign
  keys, SQL-level claims written because SQLite ignores `FOR UPDATE`, the explicit `BEGIN` of
  `db.begin_snapshot_read` and `db.begin_transaction` (SQLite's driver begins no transaction before a
  `SAVEPOINT`; a job chunk uses the latter), and budgets measured only on SQLite (D13 included).
  PG1 (2026-10-01) removed the SQLite migrations, settings default and engine branch, and made
  `begin_snapshot_read` PostgreSQL's. PG2 (2026-10-01) removed every dialect branch, the `json_each`
  row list, the recursive arms, `SQLITE_LOCK_WAIT_SECONDS`, `db.begin_transaction` and the FTS5 search
  (`test_boundaries` holds it); the explicit dependant deletes stay, since the services order them for
  audit and matrix states. PG5 (2026-10-03) re-measured every budget on PostgreSQL and removed the
  SQLite planner constructs and comments; a search for SQLite in `app/`, `tests/` and `frontend/e2e`
  finds only the refusal of a SQLite URL, its tests, the boundary check and testmon's data file.
- [ ] **Database-backed uniqueness for `unique` attributes (decided 2026-10-04, 0.9 C2 C-D24; build
  to be chosen, at the latest with the import and migration work).** A `unique` attribute (for
  example a former system's ID kept beside the object ID) must be unique in every case, including a
  migration. Today the write rules compare values within a workspace (ADR-010), serialised by the
  workspace lock. That comparison must keep refusing a duplicate on every write path, and the
  database must back it: a partial unique index where possible; otherwise a dedicated table of
  (workspace, attribute, normalized value) under a unique index, written in the same transaction as
  the value. A write, import or migration that cannot insert its row fails, and nothing is
  committed. This is ADR-010's planned hardening for PostgreSQL. Object IDs need nothing: their
  unique index already covers every workspace.
- [ ] Unique-value checks over non-text values (integer, decimal, date, dateTime, boolean) still read
  every value of the attribute, live and in a change set: the value indexes cover `text_value` only
  (0.9 B2 added the live one). Add them with 0.11's model-derived indexes.
- [ ] PostgreSQL at production scale and across nodes (0.11): the volume fixture at full scale, pool
  sizing, several processes and nodes. The trigram search index and the relation matrix's PostgreSQL
  forms (0.8 A2, A3b) were delivered by 0.9.0-alpha.1 PG2 (2026-10-01); single-node multi-writer
  uniqueness moves to [PG3](POSTGRESQL_RUNTIME_PLAN.md) (delivered 2026-10-02: the workspace lock).
- [x] Found in PG3 (2026-10-02), done in
  [PG3b](POSTGRESQL_RUNTIME_PLAN.md#pg3b-batch-writes-decided-in-memory-written-in-bulk)
  (2026-10-02): a chunk checks its release before it writes a matrix state, so an activation that
  drops a matrix shape no longer can deadlock with a live batch (`test_pg3b_batch_writes`). The
  other finding, change-set writes beside a retirement, was fixed in PG3's amendment the same day.
- [ ] H4: the package checks for PG3's seven groups took 2 min 7 s on `-n 10`, over the 2-minute
  ceiling; the longest tests are `test_change_set_position_reads` (43 s) and `test_model_query`'s
  every-criterion cases (17 s each). PG3b's four groups (`records`, `change_sets`, `jobs`,
  `matrix`, 578 parallel cases) took 2 min 31 s on `-n auto`, 28 s of it rebuilding two volume
  seeds whose fingerprint covers the write code; `test_change_set_position_reads` took 52 s.
- [ ] Assess the cost of matrix state maintenance per commit (found by the test harness assessment,
  2026-10-01): a commit recomputes the touched matrix cells, about 7 ms in the parity and
  type-change test models, and a single create cost 19 ms through the API. Measure it on the volume
  fixture against the 0.8 A2 write budget before changing anything.
- [ ] Precomputed sort keys for attribute and ancestor sorts over very large parents (D26, after 0.9).
- [ ] 0.12 security: engine-provided OAuth 2.0 with JWT for backend, frontend and consumer APIs (no API
  keys, no credential in a URL), application/object/operation authorization, audit identity,
  webhook signing-key rotation (signing itself is 0.9, C-D12 revised), and UI administration of OAuth
  clients.
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

## Ideas to investigate

Not feature requests: ideas the user raised to look into later, kept here so they are not lost.
Each becomes work only if the user decides it is needed.

- **A filter builder in collections (raised 2026-10-07).** _How it works today:_ a table view
  declares its filter fields (`filterFields`); the Filter popover shows exactly those, one row per
  field with an operator set by its value type (text: is, contains, starts with, is null, is
  unset; numbers and dates: comparisons; booleans: Yes, No, Any). A field holds one condition, and
  all conditions combine with AND (repeated "is" on one field is OR). Only attributes whose type
  is marked `filterable` can be declared, so Durations offers value code and active, and value name
  is never offered. _The idea:_ the user builds the filter: rows of attribute, operator and value,
  each with remove and add, choosing any filterable attribute of the type (the view's fields as
  the first rows), several rows on one field, and AND or OR between rows. _What is known:_ the rows
  and the attribute choice are frontend work over the existing list API; OR needs the model query
  (`POST …/queries/objects`) to take groups (deferred by D4 until a second real case), the
  collection to read through it, and the URL to keep the filter tree. Per-row AND/OR is ambiguous
  once mixed ("A and B or C"); groups that match all or any, nested when needed, avoid that. The
  query's `related` criterion would also let a row filter through a relation (timetable types
  whose duration is 45 min), which fits Track K's "select all filtered". _Open:_ whether today's
  filter already covers what users need.

## Known accessibility exceptions

- [x] WP1-001: the navigation resize separator now sits inside the navigation landmark (fixed
  2026-09-24); its allowlist entries were removed. Collection and settings popovers render inside a
  landmark so their dismiss controls are not stray page content.
- [x] WP1-002: the child/relation table regions have distinct accessible labels since Base 0.8 S5
  (each panel names its scrolling region); the gate's exception matched nothing and was removed in S7.
