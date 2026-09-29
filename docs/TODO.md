# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.8

Base 0.7 is released (2026-09-25). 0.8 Track S (scalable browsing) and Track W (workspace terminology
and capability boundaries) are delivered (2026-09-26), and Milestone A's relation matrix (A1–A5) is
delivered (2026-09-28), closed by A6 (snapshot table index drift, 2026-09-28). The hierarchy editor's
`tree` contract (B1), move targets (B2), tree lens (B3) and acceptance (B4) are delivered (2026-09-28);
B5 (drag and drop in the tree lens) and its amendment B5b (move to the top level) were added in the
Milestone B review and are delivered (2026-09-29), which closes Milestone B. P2 (change lists API, P2a; review screen, P2b)
is delivered (2026-09-28). R1 passed (2026-09-28); B5 and B5b are delivered (2026-09-29); now the build acceptance R1b. Milestone C (structure
refactoring, C0–C5, with R2 as its build acceptance) was added (2026-09-28); C0 is delivered
(2026-09-29) with ADR-034 and D37–D43 accepted, and 0.8.0 waits for R2 (D43). See
[Next — 0.8 and beyond](#next--08-and-beyond).

## Open decisions

Offset/limit pagination is closed by ADR-030 (accepted 2026-09-25): each request pages with a
cursor or a position; the UI scrolls with cursors and jumps with positions. Delivered in 0.8 Track S.

Milestone A decisions D8–D13 and D28 (A6) are accepted. D14 (ineligible move targets listed disabled
with a reason) is accepted (2026-09-28), as are D2–D6 as delivered in Track S. A6's two open
measurements are decided (2026-09-28): the container move, measured in B2, is a known 0.8 budget
exception (D29), and the link candidate page is a known 0.8 budget exception (D30). B5's D34 (drop
targets and confirmation) and D35 (touch drag deferred to 0.11), and B5b's D36 (move to the top
level), are accepted (2026-09-28). No 0.8
decision is open; see the
[0.8 plan](BASE_0_8_IMPLEMENTATION_PLAN.md#decisions-summary).

See `ROADMAP.md` for the delivery scope, exit gates and full milestone sequence.

## Base 0.7 delivery record (released 2026-09-25)

WP-1–WP-9, WP-10A–K, WP-11, WP-12, WP-13A/B/C and WP-14 are complete, with ADR-022 relation-set
versions, ADR-028 change set version selection, ADR-029 contextual collections, UI-07 gates, the frontend
redesign and dark mode. See `CHANGELOG.md` and `BASE_0_7_IMPLEMENTATION_PLAN.md` for details.

## Base 0.6 delivery record (complete 2026-09-11)

WP0–WP8, WP8.1-A–C, ADR-026 slices 0–5, WP9 slices A–D, WP10 and UI-01–UI-06 are all complete.
See `CHANGELOG.md` and `BASE_0_6_IMPLEMENTATION_PLAN.md` for detailed delivery history.

## Next — 0.8 and beyond

- [x] 0.8 Track S — scalable browsing ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md), ADR-030), first:
  - [x] S1 volume fixture and baseline over a generated model.
  - [x] S2 change-set and publication reads in the database (D1 accepted: typed value rows).
  - [x] S2b bounded change set writes: a rename at full volume in 7.5 ms (was 4.9 s).
  - [x] S3 cursor and position paging: backward cursors, anchor, totals, seek by value, `position`.
  - [x] S4 top-level filter; relation search and sort.
  - [x] S5 shared continuous-scroll list with loading and end markers.
  - [x] S6 sidebar tree by parent, replacing **Load more objects**.
  - [x] S7 composed volume acceptance (open: attribute sorts over the 20,000-child parent, deferred
    after 0.9 by D26).
  - [x] S8 indexed search keeping "contains" matching in every context (D25): a trigram index over
    text values; a whole-type name search with its total in 37 / 73 / 40 ms (was 0.7–0.9 s).
- [x] 0.8 Track W — workspace terminology and capability boundaries ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#track-w--workspace-terminology-and-capability-boundaries), ADR-031):
  - [x] W1 glossary, roadmap and milestone names (translation/hierarchy editor); stale gap notes.
  - [x] W2 change sets and publications ("Publication N") carry their ADR-031 names in every layer.
  - [x] W3 narrow `WORKSPACE_ADMIN_MUTATIONS_ENABLED` to catalogue administration.
  - [x] W4 workspace administration screen, read-only single-workspace selector, capability status.
  - [x] W5 test (and fix if confirmed) live writes committing across a model activation.
  - [x] W6 delete an unused workspace (D27): API, detail deletability, Workspaces screen action.
- [x] 0.8 Milestone A — relation matrix ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-a--relation-matrix)):
  - [x] A1 schema 0.7 `relationMatrix` view contract.
  - [x] A2 relation matrix query with cell states and whole-list state filter.
  - [x] A3 writes from a cell: container and link-candidate lookups, create, edit, link and unlink, live or in a change set.
  - [x] A3b stored cell states for the row state filter (ADR-033).
  - [x] A4 relation matrix lens.
  - [x] A5 Milestone A acceptance (SC-09 translation half and the mapping-shape journey).
  - [x] A6 snapshot table index drift (D28): change set objects gain the owner-leading page indexes,
    the other eight declarations are removed, and a schema drift test holds a migrated database equal
    to the ORM. Found by its measurements: moving a container that holds about 2,500 matrix
    cells in a change set takes 5–9 s (A3b state recompute, about 110 statements; measured in B2,
    D29), and a link candidate page over a 5,000-cell column takes 92 ms live and 160 ms in a change
    set (known 0.8 budget exception, D30).
- [ ] 0.8 Milestone B — hierarchy editor ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-b--hierarchy-editor)):
  - [x] B1 schema 0.7 `tree` view contract.
  - [x] B2 move targets with eligibility (D14) and path context in every context; a deep move meets
    the write budget live and in a change set; the matrix container move is a known 0.8 budget
    exception (D29).
  - [x] B3 tree lens with add child, rename, availability and move, beside the record's detail;
    `test:browser:b3` on both starter trees and the generated tree, live and in a change set.
  - [x] B4 Milestone B acceptance (SC-09 hierarchy half); `test:browser:b4`, tree lens and move dialog
    in the a11y and visual gates.
  - [x] B5 drag and drop in the tree lens (added in review, D34, D35; delivered 2026-09-29): onto a node, into a gap or onto
    a type heading, checked by the model's containment rule, glowing green or red with the reason,
    confirmed in the existing move dialog; mouse and pen (touch drag in 0.11). One record at a time.
  - [x] B5b move to the top level (amendment to B5, D36; delivered 2026-09-29): a **Top level** option in
    Move to… and top-level drop targets, for the tree's root types; others refused with `notRoot`.
- [x] 0.8 P2 change set changes list, after W2 (D20); planned 2026-09-28 with D31–D33 accepted.
  - [x] P2a change lists API: `object-changes` and `relation-changes`, kinds, before/after, volume budgets.
  - [x] P2b change set review screen: Records and Relationships, kind and type filters, parent links on
    request, before/after rows, `beforePath` for moves; `test:browser:p2`, review in the a11y and visual gates.
- [x] 0.8 R1 build acceptance of the build without B5 (2026-09-28): every gate green; the change lists
  read one snapshot; `sc15` and `wp13c` runner data follows the 0.8.0 starter. Release waits for R1b.
- [ ] 0.8 R1b B5 and B5b build acceptance (amendment to R1, after both); 0.8.0 releases when R1, R1b and R2 pass (D43).
- [ ] 0.8 Milestone C — structure refactoring ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-c--structure-refactoring)):
  a record's type changes when it moves where only another type is allowed, derived from the model
  with a preview. Nothing is lost (history offers values back), and named refactorings run in a
  change set. D37–D43 accepted in C0.
  - [x] C0 design (2026-09-29): ADR-034 and the restructuring API design in API.md; D37–D42 as
    recommended, D43 holds 0.8.0 until R2; no migration needed.
  - [x] C1 type change in the engine (values, containment edge, relationships, derived state, audit,
    publishing) (2026-09-29).
  - [x] C2 planner: possible types, mapping suggestions, cascade, the way back, size limit
    (2026-09-29; D44 lowers the limit to 500).
  - [x] C3 restructuring API: preview and apply for move, change type, insert and remove a level,
    change type under a record (2026-09-29).
  - [x] C4 refactoring in the tree lens, reusing B5's dialog, list and drag (2026-09-29; D45).
  - [x] C5 Milestone C acceptance (2026-09-29): `test:browser:c5` on the starter and generated
    models, the preview and dialogs in both gates, US-H03 and SC-17; fixed on the way: linear change
    set validation, a reclassified-then-removed record in the change lists and review, and the lens's
    late refocus after a restructuring.
- [ ] 0.8 R2 Milestone C build acceptance; 0.8.0 releases after it (D43).
- [ ] Enforce foreign keys on SQLite (`PRAGMA foreign_keys=ON` per connection) or document that every
  `ondelete` rule is advisory there. 0.8 W6 found none of them, not only the `workspaces.key` ones, are
  enforced at runtime; services delete dependants explicitly and W6 rechecks the workspace at commit.
  Enabling it needs a data check for existing violations and must keep the table-rebuild migrations,
  which require it off, working.
- [ ] 0.9 planning ([plan](BASE_0_9_IMPLEMENTATION_PLAN.md), [integration design](INTEGRATION_API.md)): document
  set accepted 2026-09-28; decisions D1–D16 and CONSUMER_API C-D1–C-D16 accepted 2026-09-29;
  INTEGRATION_API sections P, B, F, Q and J, the schema 0.8 section and ADR-036–038 drafted
  2026-09-29; work packages and the delivery queue specified 2026-09-29. Open: review of the drafts;
  implementation after 0.8.0, starting with Q1.
- [ ] Integration-grade query expressions beyond daily-use filters.
- [ ] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a change set merely because several records change (0.9).
- [ ] Asynchronous CSV/XLSX import and export with validation previews; import runs an import profile
  (revised D3, [MODEL_AUTHORING A1](MODEL_AUTHORING.md#delivery)).
- [ ] Ordered change feed and retryable webhooks.
- [ ] Cross-type object lookup `GET /objects` (P1) and a general relation edge list with publication
  context (P3), moved from 0.8 (D20).
- [ ] Built-in Scalar API reference at `/docs` replacing Swagger UI and ReDoc (0.9): management API plus
  each consumer API contract version as sources; pinned script bundled by default, CDN loading by
  setting; route excluded from the OpenAPI document; tests for page, bundled script and unchanged
  OpenAPI digest.

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
