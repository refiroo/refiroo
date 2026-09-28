# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.8

Base 0.7 is released (2026-09-25). 0.8 Track S (scalable browsing) and Track W (workspace terminology
and capability boundaries) are delivered (2026-09-26), and Milestone A's relation matrix (A1–A5) is
delivered (2026-09-28), closed by A6 (snapshot table index drift, 2026-09-28). The hierarchy editor's
`tree` contract (B1), move targets (B2), tree lens (B3) and acceptance (B4) are delivered (2026-09-28),
closing Milestone B. Next: P2a (change lists API), then P2b (review screen), then R1. See
[Next — 0.8 and beyond](#next--08-and-beyond).

## Open decisions

Offset/limit pagination is closed by ADR-030 (accepted 2026-09-25): each request pages with a
cursor or a position; the UI scrolls with cursors and jumps with positions. Delivered in 0.8 Track S.

Milestone A decisions D8–D13 and D28 (A6) are accepted. D14 (ineligible move targets listed disabled
with a reason) is accepted (2026-09-28), as are D2–D6 as delivered in Track S. A6's two open
measurements are decided (2026-09-28): the container move, measured in B2, is a known 0.8 budget
exception (D29), and the link candidate page is a known 0.8 budget exception (D30). No 0.8 decision is open; see the
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
- [x] 0.8 Milestone B — hierarchy editor ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-b--hierarchy-editor)):
  - [x] B1 schema 0.7 `tree` view contract.
  - [x] B2 move targets with eligibility (D14) and path context in every context; a deep move meets
    the write budget live and in a change set; the matrix container move is a known 0.8 budget
    exception (D29).
  - [x] B3 tree lens with add child, rename, availability and move, beside the record's detail;
    `test:browser:b3` on both starter trees and the generated tree, live and in a change set.
  - [x] B4 Milestone B acceptance (SC-09 hierarchy half); `test:browser:b4`, tree lens and move dialog
    in the a11y and visual gates.
- [ ] 0.8 P2 change set changes list, after W2 (D20); planned 2026-09-28 with D31–D33 accepted.
  - [ ] P2a change lists API: `object-changes` and `relation-changes`, kinds, before/after, volume budgets.
  - [ ] P2b change set review screen.
- [ ] 0.8 R1 build acceptance and release.
- [ ] Enforce foreign keys on SQLite (`PRAGMA foreign_keys=ON` per connection) or document that every
  `ondelete` rule is advisory there. 0.8 W6 found none of them, not only the `workspaces.key` ones, are
  enforced at runtime; services delete dependants explicitly and W6 rechecks the workspace at commit.
  Enabling it needs a data check for existing violations and must keep the table-rebuild migrations,
  which require it off, working.
- [ ] Integration-grade query expressions beyond daily-use filters.
- [ ] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a change set merely because several records change (0.9).
- [ ] Asynchronous CSV/Excel import and export with validation previews.
- [ ] Ordered change feed and retryable webhooks.
- [ ] Cross-type object lookup `GET /objects` (P1) and a general relation edge list with publication
  context (P3), moved from 0.8 (D20).
- [ ] Built-in Scalar API reference at `/docs` replacing Swagger UI and ReDoc (0.9): management API plus
  each consumer API contract version as sources; pinned script bundled by default, CDN loading by
  setting; route excluded from the OpenAPI document; tests for page, bundled script and unchanged
  OpenAPI digest.

## Later — production and self-service authoring

- [ ] Complete the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md), including
  ownership, contribution, dependency, security, trademark and commercial-service documentation.
- [ ] PostgreSQL performance and multi-writer uniqueness hardening, including the trigram form of
  the S8 search index and the relation matrix's SQLite-only statements: the change set walk down
  (two recursive arms, which PostgreSQL needs in one recursive term) and the stored state filter's
  row list, read through `json_each` on SQLite and as a plain `IN` list elsewhere (0.8 A2, A3b).
- [ ] Precomputed sort keys for attribute and ancestor sorts over very large parents (D26, after 0.9).
- [ ] OIDC, application/object/operation authorization and audit identity.
- [ ] Replace the pre-authentication, default-enabled workspace mutation posture with authenticated,
  authorized workspace administration; retain the capability gate as deployment defence in depth.
- [ ] Multi-node active-model propagation and protected publication; verify split deployment
  (administration and public instances on one database) against the caveats in ARCHITECTURE.
- [ ] Structured model designer with reference-aware forms, matrices and live preview.
- [ ] Read-only dependency graph visualization where it improves comprehension.
- [ ] Product 0.10: executable runtime-data migration plans for currently blocked model changes.
- [ ] Product 0.10: model replacement for a change set started from a publication, with a side-effect-free impact/loss preview,
  explicit confirmation tied to the reviewed versions or cancel, atomic workspace model/data switch,
  immutable history and unaffected-workspace isolation. Confirmation cannot waive target validity or
  parser support; nothing in Base 0.6 overrides them.
- [ ] Product 0.10: add workspace-scoped model-release assignment for staged tenant or
  governance-domain rollout.
  Resolve the workspace before its immutable model snapshot, scope compatibility and migration to that
  workspace, bind cursors to the release identity and switch assignments atomically. Supporting mixed
  schema-language versions additionally requires a bounded current/previous parser window and explicit
  conversion; workspace pinning alone is not schema compatibility.
- [ ] Product 0.10 (ADR-028): move a change set onto a release its content does not already satisfy, by
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
