# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.8

Base 0.7 is released (2026-09-25). Next: 0.8 Track S (scalable browsing), then arbitrary-depth tree
browsing and translation screens. See [Next — 0.8 and beyond](#next--08-and-beyond).

## Open decisions

Offset/limit pagination is closed by ADR-030 (accepted 2026-09-25): each request pages with a
cursor or a position; the UI scrolls with cursors and jumps with positions. Delivered in 0.8 Track S.

Milestone A and B decisions D8–D14 are proposed in the
[0.8 plan](BASE_0_8_IMPLEMENTATION_PLAN.md#decisions-summary) and need acceptance before A1/B1.

See `ROADMAP.md` for the delivery scope, exit gates and full milestone sequence.

## Base 0.7 delivery record (released 2026-09-25)

WP-1–WP-9, WP-10A–K, WP-11, WP-12, WP-13A/B/C and WP-14 are complete, with ADR-022 relation-set
versions, ADR-028 draft version selection, ADR-029 contextual collections, UI-07 gates, the frontend
redesign and dark mode. See `CHANGELOG.md` and `BASE_0_7_IMPLEMENTATION_PLAN.md` for details.

## Base 0.6 delivery record (complete 2026-09-11)

WP0–WP8, WP8.1-A–C, ADR-026 slices 0–5, WP9 slices A–D, WP10 and UI-01–UI-06 are all complete.
See `CHANGELOG.md` and `BASE_0_6_IMPLEMENTATION_PLAN.md` for detailed delivery history.

## Next — 0.8 and beyond

- [ ] 0.8 Track S — scalable browsing ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md), ADR-030), first:
  - [x] S1 volume fixture and baseline over a generated model.
  - [x] S2 draft and history reads in the database (D1 accepted: typed value rows).
  - [x] S2b bounded draft writes: a rename at full volume in 7.5 ms (was 4.9 s).
  - [x] S3 cursor and position paging: backward cursors, anchor, totals, seek by value, `position`.
  - [x] S4 top-level filter; relation search and sort.
  - [x] S5 shared continuous-scroll list with loading and end markers.
  - [x] S6 sidebar tree by parent, replacing **Load more objects**.
  - [x] S7 composed volume acceptance (open: attribute sorts over the 20,000-child parent, deferred
    after 0.9 by D26).
  - [ ] S8 indexed name search keeping "contains" matching in every context (D25).
- [ ] 0.8 Track W — workspace terminology and capability boundaries ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#track-w--workspace-terminology-and-capability-boundaries), ADR-031):
  - [ ] W1 glossary, roadmap and milestone names (translation/hierarchy editor); stale gap notes.
  - [ ] W2 rename workspace drafts/revisions to change sets/publications ("Publication N") in every layer.
  - [ ] W3 narrow `WORKSPACE_ADMIN_MUTATIONS_ENABLED` to catalogue administration.
  - [ ] W4 workspace administration screen, read-only single-workspace selector, capability status.
  - [ ] W5 test (and fix if confirmed) live writes committing across a model activation.
- [ ] 0.8 Milestone A — translation workspace ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-a--translation-workspace)):
  - [ ] A1 schema 0.7 `translationMatrix` view contract (may run alongside Track S).
  - [ ] A2 translation coverage query with cell states and whole-list gap filter.
  - [ ] A3 writes from a cell: container lookup, create and edit, live or in a draft.
  - [ ] A4 translation matrix lens.
  - [ ] A5 Milestone A acceptance (SC-09 translation half).
- [ ] 0.8 Milestone B — hierarchy workspace ([plan](BASE_0_8_IMPLEMENTATION_PLAN.md#milestone-b--hierarchy-workspace)):
  - [ ] B1 schema 0.7 `tree` view contract (may run alongside Track S).
  - [ ] B2 move targets with eligibility, and path context in every context.
  - [ ] B3 tree lens with add child, rename, availability and move.
  - [ ] B4 Milestone B acceptance (SC-09 hierarchy half).
- [ ] 0.8 P2 change set changes list, after W2 (D20).
- [ ] 0.8 R1 build acceptance and release.
- [ ] Integration-grade query expressions beyond daily-use filters.
- [ ] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a draft merely because several records change (0.9).
- [ ] Asynchronous CSV/Excel import and export with validation previews.
- [ ] Ordered change feed and retryable webhooks.
- [ ] Cross-type object lookup `GET /objects` (P1) and a general relation edge list with publication
  context (P3), moved from 0.8 (D20).

## Later — production and self-service authoring

- [ ] Complete the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md), including
  ownership, contribution, dependency, security, trademark and commercial-service documentation.
- [ ] PostgreSQL performance and multi-writer uniqueness hardening, including the trigram form of
  the S8 search index.
- [ ] Precomputed sort keys for attribute and ancestor sorts over very large parents (D26, after 0.9).
- [ ] OIDC, application/object/operation authorization and audit identity.
- [ ] Replace the pre-authentication, default-enabled workspace mutation posture with authenticated,
  authorized workspace administration; retain the capability gate as deployment defence in depth.
- [ ] Multi-node active-model propagation and protected publication; verify split deployment
  (administration and public instances on one database) against the caveats in ARCHITECTURE.
- [ ] Structured model designer with reference-aware forms, matrices and live preview.
- [ ] Read-only dependency graph visualization where it improves comprehension.
- [ ] Product 0.10: executable runtime-data migration plans for currently blocked model changes.
- [ ] Product 0.10: historical-draft model replacement with a side-effect-free impact/loss preview,
  explicit confirmation tied to the reviewed versions or cancel, atomic workspace model/data switch,
  immutable history and unaffected-workspace isolation. Confirmation cannot waive target validity or
  parser support; nothing in Base 0.6 overrides them.
- [ ] Product 0.10: add workspace-scoped model-release assignment for staged tenant or
  governance-domain rollout.
  Resolve the workspace before its immutable model snapshot, scope compatibility and migration to that
  workspace, bind cursors to the release identity and switch assignments atomically. Supporting mixed
  schema-language versions additionally requires a bounded current/previous parser window and explicit
  conversion; workspace pinning alone is not schema compatibility.
- [ ] Product 0.10 (ADR-028): move a draft onto a release its content does not already satisfy, by
  reusing the migration preview/confirm machinery against that draft's own candidate graph and
  current-live base. The review reports conversions and potential draft loss and applies only on
  confirmation of the exact reviewed draft and release versions; nothing forces the move through or
  happens without being asked, and a move never deletes draft content to make a target fit.
- [ ] Extension packaging after two concrete reuse cases exist.

## Explicitly not planned for Base 0.7

- Model-workbench information-architecture redesign.
- Physical purge of published workspace revisions or audit history.
- Graph-canvas-first model authoring.
- Arbitrary server-filesystem model load/save.
- Client-side loops over single-item APIs presented as bulk operations.
- Starter-key branches in backend or frontend behavior.
- Object drafts, object revisions, object activation/retirement, or per-object publication state.
- A second public CRUD dialect under `/workspace-drafts/{draftId}/objects` or `/relations`.

## Known accessibility exceptions

- [x] WP1-001: the navigation resize separator now sits inside the navigation landmark (fixed
  2026-09-24); its allowlist entries were removed. Collection and settings popovers render inside a
  landmark so their dismiss controls are not stray page content.
- [x] WP1-002: the child/relation table regions have distinct accessible labels since Base 0.8 S5
  (each panel names its scrolling region); the gate's exception matched nothing and was removed in S7.
