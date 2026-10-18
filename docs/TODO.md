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
UA, the Atlas redesign (ADR-040), is implemented and approved (2026-10-07). **U4 is implemented
(2026-10-07)**: Settings › Integration (Consumer APIs, Jobs and feed, API reference) and the
starter's consumer API ([record](SETTINGS_AND_UI_PLAN.md#u4-record-2026-10-07)); screenshots
approved by the user 2026-10-10. **U5 is implemented (2026-10-07)**: Settings › Integration › Webhooks
([record](SETTINGS_AND_UI_PLAN.md#u5-record-2026-10-07)), and **U5a** (webhook names, the delivery
log, the page revised, [record](SETTINGS_AND_UI_PLAN.md#u5a-record-2026-10-07)); screenshots approved
2026-10-07. **J1 is delivered (2026-10-07)**: export jobs in JSON Lines, CSV and XLSX
([record](BASE_0_9_IMPLEMENTATION_PLAN.md#j1-record-2026-10-07)). See
[Next — 0.9](#next--09).

- **Document the starter's consumer API lookups and the reworked Consumer APIs page (the user,
  2026-10-07, "later").** The starter (content 0.9.2) now declares `match` (own fields and, through
  the `systemVariants` and `translations` projections, a mapped system code or a translated name),
  so XREF and batch resolve find records; 0.9.1 had none and its XREF found nothing. The Consumer
  APIs page now lists each API's routes from its OpenAPI document and shows its fields, related
  records, lookup rules (or a warning when there are none) and parameters. Still to update:
  EXAMPLE_MODEL (the starter's `rdm`), CURRENT_FUNCTIONALITY F23, CHANGELOG, the U4 record and
  UI_ACCEPTANCE U4-1. A 0.9.1 installed on a database stays beside 0.9.2 and is never activated.
- **Rework the type palettes so A and B differ visibly (the user, 2026-10-07). Moved on 2026-10-10 to
  [Base 0.14 UP1](BASE_0_14_IMPLEMENTATION_PLAN.md#up1-type-palettes-a-and-b-reworked).** A and B differ
  only in slots 3 and 4 (magenta and olive against plum and gold), and side by side the user could
  not tell them apart: in the example model only five types' tiles change, and pink against purple, olive against gold, read as near shades.
  Rework them into two palettes a person tells apart at a glance, keeping what both must hold: eight
  hues distinguishable from each other and from the Live, change-set and publication colours (green,
  amber, violet; ADR-040), ink at 4.5:1 on its fill and the page, markers at 3:1, in light and dark
  (`tokens.test.ts`). Show both on the real app for the user to judge (Settings › Appearance › Type
  colours switches them). Where: `styles/tokens.css`, palette section of
  [SETTINGS_AND_UI_PLAN](SETTINGS_AND_UI_PLAN.md#type-palettes-a-and-b).
- **For UA0 (2026-10-06): the user's check on the dev server.** The popover click and the
  workspace switcher are fixed ([record](SETTINGS_AND_UI_PLAN.md#ua0-record-2026-10-06)); UA0 is
  done when the user has seen the settings navigation and the application tabs respond to the
  first click with a popover open, and that the applications now stand 36px after the product
  name (also done in UA0), on the Settings page as well, which now has the same top bar (U-D14).
- **From UA0 (2026-10-06): three failures seen once, not reproduced.** `RelationMatrixView.test`
  "lets a reload replace cells re-read after earlier saves" (once in U3's parallel `vitest related`;
  30 repeats under load passed in UA0). `test:browser:a4` timed out once waiting for the cell dialog
  to reopen after an unlink (`a4-relation-matrix.mjs` line 383) and passed on the rerun.
  `test:browser` failed once with a timeout whose step was not captured, then passed twice. _UA4 revision (2026-10-07):_ `RelationMatrixView.test` failed once more in a full run ("creates a record from an empty cell…": the row named Connections not found) and passed alone.
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
- **`test:browser:c4`: the volume drag's preview never appeared (seen once, UA6, 2026-10-07).**
  `dragFrom` (`helpers/tree.mjs:193`, from `c4-restructuring.mjs:437`) waited 10 s for
  `.tree-drag-preview`. The next run passed that journey. UA6 changed no tree or drag code (the lens's
  surface became `ui/Card` with the same classes and padding); one run does not rule it out. Next
  time: capture the pointer's target at the failure.

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
  _Taken by 0.9 K2b (D116, accepted 2026-10-09), on K2's batch preview; delivered 2026-10-09
  (D120–D126): cascading delete items and one set-based deletion path. Left: the timing on the
  full-size fixture (D124), deferred by the user to R._
- **Lifecycle audit reads (decided 2026-10-02, H4a D-5).** The engine records workspace, change set
  and publication lifecycle events and model draft events, but no route reads them. Keep recording
  them and add reads (journeys J19.5, J08.9); consider showing a workspace's activity in the UI.
  To plan as its own package. F1's feed now gives publications (`published`, `withdrawn`) positions.

- **Consumer API definitions after C18 (2026-10-08)**, from the
  [C18 record](BASE_0_9_IMPLEMENTATION_PLAN.md#c18-record-2026-10-08):
  - **A `code` role on object types.** An object type naming its code attribute in the model, after
    which a consumer API's `code` field may leave out `from` and `parent.code` is unchanged: an
    application-model change of its own.

## Open decisions
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
  - **Which records a relationship may choose (0.9 K7, 2026-10-10).** A binding's `candidates`, with
    examples of each kind of criterion (a name, a yes/no attribute, an ancestor's name), what the
    pickers then offer and say, why a record is not offered a relationship, that relationships made
    before are kept when the data changes, and that free-text criteria are the model administrator's
    responsibility ([APPLICATION_MODEL](APPLICATION_MODEL.md#which-records-a-relationship-may-choose-schema-09-base-09-k7)).
  - **How many relation columns a table view may show (D142 revised, 0.9 K6a, 2026-10-10).** No fixed
    number: as many as the type has relationships (and fields of them), each column read only for the
    rows on the page and dropped when hidden in Display. Explain it with examples, a view of a type
    with several relationships and one with a field of the related records, as in
    [APPLICATION_MODEL](APPLICATION_MODEL.md#table-view-type-table), and say what the integrator's
    `expand` costs (page size × columns × `expandLimit`).
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
- [x] 0.9 planning ([plan](BASE_0_9_IMPLEMENTATION_PLAN.md), [integration design](INTEGRATION_API.md)): document
  set accepted 2026-09-28; decisions D1–D16 and CONSUMER_API C-D1–C-D16 accepted 2026-09-29;
  INTEGRATION_API sections P, B, F, Q and J, the schema 0.8 section and ADR-036–038 drafted
  2026-09-29; work packages and the delivery queue specified 2026-09-29. Open: review of the F and J
  drafts. Implementation started 2026-09-29 with Q1 and Q2 (delivered); Q3 delivered 2026-09-30 with
  D17–D19, C1 with C-D17–C-D20 and Q4 with D20–D22; B1 2026-10-01 with D23–D26, B2 with D27–D30.
  Closed at R (2026-10-11): 0.9 is complete; F and J were delivered on their sections, which their
  packages amended (INTEGRATION_API's state table).
- [x] Integration-grade query expressions beyond daily-use filters: delivered as 0.9 Q3 (2026-09-30),
  the model-aware query; `asOf` with effective periods in Q4 (2026-09-30).
- [x] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a change set merely because several records change (0.9).
  Object items run inline delivered as 0.9 B1 (2026-10-01) and in the background as B2
  (2026-10-01); relation and relation-set items as B3 (2026-10-03).
- [x] Asynchronous CSV/XLSX import and export with validation previews; import runs an import profile
  (revised D3, [MODEL_AUTHORING A1](MODEL_AUTHORING.md#delivery)). Export delivered as 0.9 J1 and
  J1u (2026-10-07); import profiles and imports run directly as J2 (2026-10-07); the preview,
  confirmation, outcomes by row and the binding report as J3 (2026-10-07); the screen as J4
  (2026-10-08).
- [x] 0.9 J5 (delivered 2026-10-08, D96–D101): load an export of one workspace into
  another workspace of the same instance as that workspace's own records (counterpart IDs derived
  from the file's IDs and the workspace); amends D49 and touches the identity door (ADR-032). J4a
  made the import say why such a file cannot load today.
- [ ] If wanted (0.9 J4, D94's alternative): a file of an import's refused rows to download, with
  their cells and reasons. It needs the refused rows' cells kept after binding and a download route,
  an API capability; today the refused rows are listed on the import's page.
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
- [x] J1's export budget names "110,000 records"; the volume fixture holds 258,000 since 0.8 A2 (found
  in Q1). Restated in D56 and measured at 258,000 in J1 (2026-10-07, POSTGRESQL_BUDGETS §8).
- [x] J1u: the export dialog, the job page and notifications pushed over a per-job event stream
  (delivered 2026-10-07; screenshots approved).
- [x] **Flake (0.9 R step 0, 2026-10-10):** `test_mapping_coverage::test_coverage_query_count_does_not_grow_per_source[False]`
  failed once in a parallel run of nine groups and passed alone; `[True]` failed once in R step 2.
  Cause: the count took every statement on the engine, the background threads' polls included.
  Fixed in R step 2: it counts the request's statements only, as `volume_fixture.measure` does.
- [ ] **Flakes (0.9 R step 3, 2026-10-10)**, each failed once and passed on its rerun (D201):
  `test:browser:c4` (focus left the tree after the lens search's Tab, looking for Pickup point, on the
  second search after `goBack`); `test:browser:k6` (Select all 42 matching not offered: the list may
  have loaded every row before the check); `test:browser` (`checkRecordReturn` after a reload: Back to
  list did not reach the systems list's address with its anchor). Look at each when it recurs.
  Seen again in 0.10 A4a (2026-10-11): `test:browser` and `test:browser:a4` each timed out once in a
  run of the guide's runners after the package's changes and passed on their rerun, unchanged; the
  first runs' logs were not kept.
- [ ] **`NOT IN` subqueries that may outgrow `work_mem` (0.9 R, after R-F23 and R-F25):**
  `jobs/people.py` `_walk_ids` (`wanted NOT IN the workbook's records`, which can reach a whole
  type at full volume) and `management/projections/mapping.py` exclusive targets (`id NOT IN` the
  mapping's edges). PostgreSQL hashes such a subplan only while it fits; past that it scans it per
  row. Not measured at that size; the mapping read's budgets passed. Rewrite as `NOT EXISTS` or a
  join when either is measured large.
- [ ] **Budget (0.9 R step 2, 2026-10-10):** the full backend suite without `budget` took 6 min 19 s
  in parallel (2,201 cases), over the 5-minute ceiling (TEST_HARNESS_PLAN). Not a regression per case:
  H3 measured 2 min 41 s for 1,032 cases (0.16 s each), R 0.17 s each. The suite doubled in 0.9. The
  slowest are volume statement counts and journey parametrisations (the run's list of tests over 10 s).
  Revisit the ceiling or the slowest modules before 1.0.
- [x] **Found in 0.10 A6b (2026-10-12), not A6's; fixed in 0.10 R (2026-10-15):** History words a `setLabel` step with the element's
  current name ("Renamed Product group to Product group", A4a's `describeOperation`): it should name
  the old name, from the step's inverse. A type's attribute table is narrow beside the source pane at
  1440px, so its Unique column wraps "Yes" letter by letter (A4a's `EditorTable`). Export, Import and
  Load still load and list workspaces themselves; A6b moved Add a workbook and New from a workbook
  onto `WorkspaceField` (U-D14): move the other three onto it.
- [ ] **Budget (0.10 A6a, 2026-10-12):** a package's group runs went over the 2-minute ceiling:
  `authoring or contract` 3,455 cases in 2 min 12 s (1 min 23 s for 3,420 in A5a) and `jobs or
  startup` 547 in 2 min 10 s (1 min 50 s for 509 in A5a), with no test over 10 s. The J34 module
  alone takes about 2 min 15 s in parallel (48 cases, the slowest the loads of W1 at 11 s); its
  cases each build a draft, profile W1 and run its jobs. Measured once on a shared laptop. To fix in
  the next package: a session fixture profiling W1 once per configuration for the cases that only
  read it, or the J34 module split so its cases spread over the workers. **Still open after A5c
  (2026-10-14):** the `jobs` group took 2 min 51 s (449 cases); split, the group without J34 and
  J35 took 1 min 18 s (397) and J34 with J35 2 min 37 s (66). A5c did not take this fix on (its own
  cases add 8). **Worse after A7 (2026-10-14):** `jobs` 5 min 59 s (475 cases), and J34 with J35
  and the source unit tests 3 min 25 s (198); A7's cases add 12 (W2 is profiled, applied, installed
  and loaded before W1 onto it). A7 did not take the fix on either. **After A8a (2026-10-14):** J34
  with J35 and the source and import unit tests 3 min 49 s (323), the rest of `jobs` 3 min 29 s
  (276), and `model_admin` alone 4 min 52 s (321), the last over the ceiling unannounced. A8a did
  not take the fix on.
- [x] R: add J1u's export dialog, notification and job page, and J4's import dialog, the import's
  job page (waiting and loaded) and its notifications, to `test:a11y` and `test:visual` (scenarios
  and baselines), light and dark; J1u and J4 checked them with axe in their runners (D95). Done in
  R step 4 (2026-10-11) with the other D202 surfaces.
- [x] J2 reads an export's CSV and XLSX table layout without a profile, decoding XLSX's `_xHHHH_`
  escapes (INTEGRATION_API §J2); the round trip of CSV and XLSX is tested there. Delivered in J2
  (2026-10-07), with `applicationKey` added to the records table (D71).
- [x] J2a (D74): database-backed uniqueness for `unique` attributes (the item below), delivered
  2026-10-07 (D75–D78).
- [x] J4: Settings › Integration's limits list shows `IMPORT_MAX_BYTES` and
  `IMPORT_PREVIEW_MAX_ITEMS` (`integrationJobs.limits.importMaxBytes`, `importPreviewMaxItems`,
  added in J2 and J3), and the job page an import's file and profile, its preview, binding report
  and rows (delivered 2026-10-08).
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

- [x] 0.10 design ([MODEL_AUTHORING.md](MODEL_AUTHORING.md), ADR-035) and
  [plan](BASE_0_10_IMPLEMENTATION_PLAN.md) (2026-10-11, replacing the provisional one): the designer
  line first, then the spreadsheet line (D11, the user's request). A-D1–A-D3 decided; A-D4 and A-D10
  taken by 0.9 J2; plan D11–D16 accepted 2026-10-11 (D14: interim release after T1); D1–D10, D17–D21 and
  A-D5–A-D9 accepted with the A0 plan the same day.
  - [x] A1 import profile contract and execution: delivered by 0.9 J2 and J3 (2026-10-07).
  - [x] A0 design pass: decisions, API design, operation vocabulary, journeys, ADR-041, the editor
    mock-up and the W1 sample, approved by the user (2026-10-11).
  - [x] N1 navigation groups and schema 0.10, with the phone band: delivered and approved by the
    user (2026-10-11).
  - [x] N1's surfaces (the sidebar groups, the group page, the phone band) into the accessibility
    and visual gates, light and dark, at T1 (2026-10-12); the phone shell baselines re-recorded after
    review; dark mode inspected.
  - [x] Desktop data-context band: proposal made ([proposal](https://claude.ai/artifact/BQf1M8edotaquqTXcknrjz));
    the topic dropped by the user for now (2026-10-11), desktop unchanged.
  - [x] A2 operation API on model drafts: model-side operations, history, undo and redo, generated
    layout (2026-10-11).
  - [x] A4a editor: model pane, relationship matrix, install and activate; delivered and approved by
    the user after a revision (2026-10-11).
  - [ ] **Startup check for a migration changed after it was applied (found in A4a, 2026-10-11).**
    A database at the head revision whose tables differ from the models (the development database
    lacked `model_draft_operations.effects` after A2's migration was edited post-apply) starts and then
    answers 500 on every read of the table. A startup comparison of the live columns with the models,
    refusing with the table and column, would catch it; it costs a catalogue read per start and a
    startup test. Not done; for the user to decide.
  - [x] The visual gate's baselines for dialogs and menus change with A4a's shared dialog and menu
    styles: the export and import dialogs (light and dark) re-recorded at T1 after review (2026-10-12).
  - [x] A4a's surfaces (the editor, the matrix, Move to…, the operation and install dialogs) into the
    accessibility and visual gates, light and dark, at T1 (2026-10-12); dark mode inspected.
  - [x] A4b editor: preview and layout editing (delivered 2026-10-12).
  - [ ] A4b: one runner run on the renamed example ended with the application a test step adds still
    in the draft although the preview had come back after Undo; not seen again in two runs. The runner
    prints the draft's history when it happens; look at it then.
  - [x] A4b's surfaces (the preview, the layout editor, the field group and sort dialogs) into the
    accessibility and visual gates, light and dark, at T1 (2026-10-12); dark mode inspected.
  - [x] A4c editor: consumer APIs (delivered 2026-10-12).
  - [x] A4c's surfaces (the Consumer APIs tab, a definition's tabs, its dialogs and the install
    dialog's section) into the accessibility and visual gates, light and dark, at T1 (2026-10-12); dark mode inspected.
  - [x] T1 designer checkpoint (US-P05), released as 0.10.0-alpha.1 (D14), 2026-10-12.
  - [x] A3 source profiling and the dry-run summary; the synthetic workbooks W1–W3 (delivered
    2026-10-12).
  - [x] A3: the dry run's binding of W1 at 10,000 rows took 9.3 s, 8.1 s of it the record items'
    per-row lookup of relationship links (also every import with a relationship column); fixed with
    a grouped join, 1.4 s (2026-10-12, POSTGRESQL_BUDGETS §11).
  - [x] A3a: the dry run's trial run of W1 at 10,000 rows took 11.8 s holding the workspace's write
    lock; with no audit entries in a trial run (D72) and sets advanced from arrays (D73) it takes
    5.75 s (2026-10-12). The rest is PostgreSQL writing the rows it tests and the ORM's bookkeeping;
    a change-set context that does not block live writes remains an option if A5 needs it.
  - [x] A5a a draft's import profile, edited by operations; the dry run after each step; the
    profile saved at installation; `missing: "create"` (delivered 2026-10-12).
  - [x] A5b the editor with a workbook: source pane, a column's mapping, Map to…, the dry-run
    drawer, Load (committed 2026-10-12; its open points settled in A6).
  - [x] A6 inference over the table patterns (A6a 2026-10-12, A6b 2026-10-14).
  - [x] A5c the next version of a workbook: the profile check, missing records, Settings › Import profiles
    (delivered 2026-10-14, screenshots approved).
  - [x] A5c: the check of W1′ at 10,000 rows stopped at binding's first lease renewal (the check's
    own lock on its job row) and the binding's key lookup took 21.9 s against 10,000 records; both
    fixed, the check takes 10.1 s after 6.1 s of profiling (2026-10-14, A5c record).
  - [x] A7 model-description sheets and matching across files (below the cut line): delivered
    2026-10-14, screenshots approved.
  - [ ] A7, not covered: a description whose type the model already has (extend mode over a
    description) is unit tested only; a description workbook's next version through its saved
    profile is not exercised.
  - [x] A8a lists of a sheet laid out for reading through the API (delivered 2026-10-14, A8a record).
  - [x] A8b the source pane list by list: **delivered 2026-10-15 (A8b record), its screenshots
    approved by the user**. A sheet laid out for reading shown as its lists, a list adjusted
    (`setSource`'s block) or dropped; a mock-up first, complete on approved screenshots.
    The real-file smoke's misreadings (a title with sentences under it read as a list, a second
    header row read as a value, sub-list headers read as titles) are what it lets the administrator
    correct.
  - [x] A8c lists of one shape as one list under their headers (delivered 2026-10-15, A8c record;
    D140–D146).
  - [ ] A8c, not covered: a category's name in another language (a translation column's header) and
    a second header row's role are not loaded with the parent list; a row keyed by name under a
    parent is not matched by name from another row of the same file.
  - [x] Fixed in 0.10 R (2026-10-15): editor history: the steps count reads the steps of the last 100 operations, so a large step
    (A8c's alternative is about 70) makes it read fewer steps than the draft has (found by A8c's
    browser runner).
  - [x] R build acceptance and release: done 2026-10-15 (D147–D153; R-F1–R-F19 fixed but R-F14;
    record in the plan); the commit and the tag `v0.10.0` on the user's instruction.
  - [x] **Flakes (0.10 R, 2026-10-15):** `test:browser:c4`'s (focus left the tree looking for Pickup
    point, seen at 0.9's R too) had its cause in the shared lens helper: `findBySearch` pressed Tab
    once while the search's results still redrew. It now waits for the requests to settle and tabs
    until a tree row has focus; `c4`, `b3`, `b4` and `c5`, which share it, passed. `authoring-a5`
    failed only while the laptop's load stood at 190.
  - [ ] **Flake (0.10 R, 2026-10-15), cause not found:** one `test:visual` run failed in 0.9's release
    surfaces (MULTI, a seeded record, not shown within 10 s of opening System values); four other
    runs passed. Nothing in the code explains it; look again if it recurs.
  - [x] **R-F14 (0.10 R review), fixed in R (2026-10-15):** the supersede and latest-job reads of
    the dry run, the check and the inference bound the parameter's key (`Job.parameters[...]`), so no
    index could serve them; they go through `jobs.store.job_parameter` (the key written literally)
    and three partial expression indexes (migration `20261017_01`).
  - [ ] A-D1 revision, deferred by the user (2026-10-11) until the designer works: reuse one object
    type for similar reference data in a similar hierarchy while it fits, with attributes switched
    on or off per type so flat types are easier to share; a separate type only where relations
    clearly differ. Not decided; to be written up for acceptance before A6.
  - [ ] Non-blocking open items: A-D11 nested navigation groups (one level in 0.10); A-D12 record
    counts on the group page (none in 0.10, later only as a bounded read).

## Next — 0.11 production hardening and staged model rollout

- [x] 0.11 P0 design pass, per the [Base 0.11 plan](BASE_0_11_IMPLEMENTATION_PLAN.md), delivered
  2026-10-15: decisions D4–D29 and the move inventory accepted, ADR-042, API design, J36–J38, the M5
  and X4 mock-ups approved. M1 (with M2 folded in, plan D32) delivered 2026-10-15; M3 and M4
  delivered 2026-10-16; M5, M6 and M6a delivered 2026-10-16, released as 0.11.0-alpha.1
  (2026-10-17); V1 delivered 2026-10-18; V2 delivered 2026-10-18; V3 delivered 2026-10-18; next:
  V4.
  - [ ] The user's requirement: each workspace runs a model of its own (Track M, then Track V).
    M1 delivered the API: a workspace on a release of its own, activation into one workspace, the
    commit guard per workspace. M3: import profiles, drafts and the consumer index and OpenAPI
    following a workspace's model. M4: the cross-type lookup over several workspaces, counterparts
    refused across models. M5: the browser follows each workspace's model, Settings › Model and
    Settings › Workspaces per workspace, the editor's choice of workspace. M6: the checkpoint
    composed in the browser; M6a: a request naming the release it was built on. V1: a workspace's
    migration to another release, API and screen. V2: a change set on an older release published
    by migrating its workspace to that release, API and the change set bar. V3: a change set moved
    onto the release its workspace runs when its content does not fit, API and the change set bar.
    Still to come: V4.
  - [ ] **From V3 (D87), not scheduled:** moving a change set onto a release its workspace does not
    run (a candidate prepared before activation) when its content does not fit. It needs a converted
    private base and a content comparison in V2's merge, since V2's migration raises the version of
    every record it converts. Refused today with `MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`.
  - [x] **Found in M5 (2026-10-16), small (fixed in M6, D58):** on the "not in this workspace's model" page the rail
    still marks the workspace's first collection as current (the shown route is the start); and a
    switch to another workspace reads the rail's collections twice (the shell remounts once the
    model arrives). Neither is wrong data; worth a look with M6.
  - [ ] **Seen once in M6 (2026-10-16):** the accessibility gate stopped in 0.10's spreadsheet
    surfaces (`editor-dry-run-rows-dialog`: the dry run's figure never shown) while the machine's load
    averaged about 17; the rerun passed. Seen again, it is a defect (D62).
  - [ ] **For 0.14: Settings › Model redesigned (the user, 2026-10-16, in M6).** M6 leaves the page
    laid out as Settings › Workspaces is (models in the list, the default workspace's first; the
    selected model's card with where it runs, its releases and its drafts), and the user judged it
    still not good, to be redesigned in 0.14. Tried in M6 and rejected: columns of releases per model
    (M5), a catalogue listing every release and draft, a page per model with tabs, cards for
    workspaces and models with a release timeline. What the user asked for on the way: no window
    nested in the page; a row or card opens on a click anywhere on it; "Change model…" (not
    "Activate a release…") and its dialog grouped by model; the default or current item first, not
    alphabetical; one design for every kind of entry (no separate "New models"); the header's
    navigation consistent with the other Settings pages. Open question raised: whether "which release
    a workspace runs" belongs on Settings › Workspaces and the model page should only be the library
    of models, versions and drafts.
  - [x] **At R (from M5), done in M6:** the visual baselines of Settings › Model change (the overview replaces
    the catalogue with the active release); review them as intended changes.
  - [x] **Found in M1 (2026-10-15), not caused by it (fixed in M6, D59):** `test_boundaries::test_tiers_hold` fails at
    `71b15ea` already (the import cycle `sources.draft_profile` ↔ `sources.dry_run`, the deferred
    import in `dry_run`). Untouched by M1, M3 and M4.
  - [x] **Found in M3 (2026-10-16), not caused by it (fixed in M6, D59):**
    `test_model_lifecycle::test_installed_release_diff_is_key_based_and_assesses_active_runtime_data`
    passes only after the module's earlier tests: alone, on a fresh database, its own
    `ensure_bootstrap_release` gives the candidate to the default workspace, so the diff compares the
    release with itself.
  - [ ] **Found in M1, unchanged code path:** after an offline schema upgrade (J12.6) the event
    deriver logs an error for feed entries written under the release whose schema the upgrade
    replaced (`UNSUPPORTED_PINNED_MODEL_SCHEMA` in `worker._plans_for`); it retries every 2 s.
  - [ ] **Found in M1:** `test_j34_onboard.py` alone took 5 min 3 s with `-n auto` (112 cases), over
    the package ceiling; one more input for S1 (D152).
  - [ ] **Found in V1 (2026-10-17), not caused by it (fails at `0b08e9c` too):**
    `tests/journeys/test_j35_next_version.py` fails 8 of its cases: a profile loads
    `INVALID_IMPORT_PROFILE` "Object type … is not in the model", the profile checked against the
    default workspace's model rather than its own (M3 bound profiles to a model).
  - [ ] **Found in V1 (2026-10-17), not caused by it (fails at `0b08e9c` too):**
    `test_startup::test_upgrade_to_the_profile_check_kind_keeps_jobs_and_an_interrupted_run_recovers`:
    the profile job runs twice (`pk_source_file_cells`, then `uq_job_input` duplicated), so the check
    fails. Seen again in V4 (2026-10-18) in a parallel group run, where a profile-check job failed in
    a chunk; it passed run alone.
  - [x] **Found in V1 (2026-10-18), fixed in V1:** a migration's long steps did not renew the
    job's lease, so a second worker could take the job over; they now renew it between their
    statements from a session of their own, and stop if another worker holds the job. N2 still
    checks every job kind's leases under real concurrency.
  - [ ] **Found in V1 (2026-10-18):** the visual gate's `integration-jobs-dark`, `import-notification-dark`
    and `webhook-deliveries` (light, dark) differ by 0.50–0.54%, over the 0.5% threshold, on screens
    V1 does not change; the webhook ones passed and failed between two runs. Their baselines predate
    0.11 (the jobs one still shows "Jobs and feed"); look at them with the flake below at R.
  - [x] **Found in V1 (2026-10-18), fixed in V1:** the compatibility analysis's scoped-uniqueness
    count walked every record's ancestors to the root (over 9 minutes at 100,000 records); it now
    climbs from the rule's targets only and stops at the scope: a check of every rule over 100,000
    records takes 5.8 s. Activation shares it.
  - [ ] **Found in V1:** the `change_sets` group took 2 min 32 s with `-n auto` (474 cases), over the
    package ceiling; one more input for S1 (D152).
  - [ ] **Found in V4 (2026-10-18):** the groups `model`, `model_admin`, `startup`, `contract`,
    `workspace_models` and `migration` together took 2 min 36 s with `-n auto` (4,148 cases, `model`
    selecting most of them), over the package ceiling; one more input for S1 (D152).
  - [ ] **Found in X1 (2026-10-18):** the groups `move`, `startup` and `jobs` together took 4 min
    55 s with `-n auto` (734 cases), and D105's draft-side check (J33, J34 and the `authoring` and
    `sources` unit tests, 3,536 cases) 4 min 57 s, both over the package ceiling; more input for S1
    (D152).
  - [ ] **Found in X1 (2026-10-18):** a development server started with `uvicorn --reload` on the
    shared checkout applies a migration file as soon as it is written, before the package finishes
    it: the development database `rdm` reached `20261020_01` without the index `ix_jobs_mapping` the
    final migration adds, and its downgrade then fails on the missing index. Recovery for `rdm`
    (no mapping stored): create the index by hand, or take `rdm` back to `20261019_01` after adding
    it and start again.
  - [ ] The user's requirement: data moved between workspaces whose models differ (Track X), in
    0.11 (plan D3, accepted 2026-10-15). X1, the mapping between two models, delivered 2026-10-18;
    X2–X5 remain.
  - [ ] The backend suite's time (D152, package S1): a filler during Part 1, before X2 at the latest
    (plan D2, accepted 2026-10-15).
  - [x] 0.11.0-alpha.1 when the M6 checkpoint passes (plan D12, accepted 2026-10-15): released
    2026-10-17, tag `v0.11.0-alpha.1`.

## Later — production and self-service authoring

- [ ] Complete the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md), including
  ownership, contribution, dependency, security, trademark and commercial-service documentation.
- [ ] **Before 1.0: revise publication withdrawal (raised by the user, 2026-10-07).** Publishing
  merges the change set into live and copies all of live into the publication, so live is the data
  and a publication is a frozen copy. Withdrawing changes only the copy's status: live keeps what the
  publication put there, nothing is rolled back, the previous publication does not become current
  again (`latest` is the newest publication or none, C-D61), and the only effect is that
  `?publication=latest` returns `404` until the next publish. It survives from ADR-024 as first
  written, when a draft replaced the current data and the published revision was the data; ADR-026
  made live the authority and left withdrawal acting on a copy. Recommendation: remove it. Removal
  reaches the `POST /publications/{id}/withdrawal` route and `withdrawn` status, the feed's
  `withdrawn` event and webhook handling, C-D61's `latest`, the UI action, J07, US-W06 and their
  tests, and existing `withdrawn` rows (a migration choice). Related findings, each its own decision:
  - The need behind "the release was bad" is a restore: a change set holding the whole of an earlier
    publication (deleting records added since), validated and published as usual, as set work in
    PostgreSQL. Today a change set from a publication applies only what is edited in it.
  - Every publish copies the whole data set, so storage grows with data size × publishes. Row
    versions valid between feed positions would make Publication N a position (as SNOMED CT's
    effective-time rows or SQL temporal tables do), but need permanent record and relationship
    history, since feed events expire. Size it by expected publish frequency and data volume.
  - The Publications page opens each snapshot read-only but shows no difference between two
    publications, or between the latest and live.
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
- [ ] **After 1.0: relationship values in a bulk relationship change (0.9 D132, deferred by the user,
  2026-10-09).** K3's dialog adds, removes and replaces relationships without their values: new
  relationships carry none, kept ones keep theirs, and values are edited one relationship at a time in
  the record's Relationships panel. Taking it up means the binding's `attributeTypeKeys` as fields in
  the dialog (Keep, Set to, Clear, as D117) and, because an `ensureRelation` that changes an existing
  relationship's values is an update needing its `expectedVersion`, the preview carrying each
  relationship's version into confirm as D130 carries a set's. Needs a shipped model that declares
  relationship values to show it.
- [ ] **When a model needs it: a required many-to-one relationship (0.9 D137).** K3a refuses
  `required` on a `many-to-one` binding, because `required` means the `to` record is created with its
  relationship. "Every `from` record holds one" is a rule at the other end: the record is created with
  it (initial relations), cannot clear it, imports and batches supply it, a `to` record still serving
  records that require it cannot be deleted, and a release making a binding required counts `from`
  records without one. Its own package, planned when a model asks for it.
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
- [x] **Delivered in 0.9 J2a (2026-10-07):** `unique_attribute_values`, kept by PostgreSQL triggers
  under a deferred unique constraint, live values only (D75–D78).
  **Database-backed uniqueness for `unique` attributes (decided 2026-10-04, 0.9 C2 C-D24; build
  to be chosen, at the latest with the import and migration work; scheduled as 0.9 J2a, D74).** A `unique` attribute (for
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
- [ ] Product 0.11: each workspace runs a model of its own (ADR-042; 0.11 Track M), with staged
  per-workspace rollout.
  Resolve the workspace before its immutable model snapshot, scope compatibility and migration to that
  workspace, bind cursors to the release identity and switch assignments atomically. Supporting mixed
  schema-language versions additionally requires a bounded parser window and explicit conversion;
  workspace pinning alone is not schema compatibility (the window, 0.5–0.10, and its conversion rules
  are V4's, delivered 2026-10-18, in APPLICATION_MODEL "Schema versions and the window").
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
  query's `related` criterion would also let a row filter through a relation (records
  whose related reference value is a given one), which fits Track K's "select all filtered". _Open:_ whether today's
  filter already covers what users need.

## Known accessibility exceptions

- [x] WP1-001: the navigation resize separator now sits inside the navigation landmark (fixed
  2026-09-24); its allowlist entries were removed. Collection and settings popovers render inside a
  landmark so their dismiss controls are not stray page content.
- [x] WP1-002: the child/relation table regions have distinct accessible labels since Base 0.8 S5
  (each panel names its scrolling region); the gate's exception matched nothing and was removed in S7.
