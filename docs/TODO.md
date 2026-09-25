# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.8

Base 0.7 is released (2026-09-25). Next: 0.8 Track S (scalable browsing), then arbitrary-depth tree
browsing and translation screens. See [Next — 0.8 and beyond](#next--08-and-beyond).

## Open decisions

None. Offset/limit pagination is closed by ADR-030 (accepted 2026-09-25): each request pages with a
cursor or a position; the UI scrolls with cursors and jumps with positions. Delivered in 0.8 Track S.

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
  - [ ] S1 volume fixture and baseline over a generated model.
  - [ ] S2 draft and history reads in the database (D1 accepted: typed value rows).
  - [ ] S3 cursor and position paging: backward cursors, anchor, totals, seek by value, `position`.
  - [ ] S4 top-level filter; relation search and sort.
  - [ ] S5 shared continuous-scroll list with loading and end markers.
  - [ ] S6 sidebar tree by parent, replacing **Load more objects**.
  - [ ] S7 composed volume acceptance.
- [ ] Translation coverage matrix and in-cell live editing, with explicit optional staging (0.8).
- [ ] Lazy hierarchy workspace with contextual live creation and atomic reparenting, optional draft (0.8).
- [ ] Integration-grade query expressions beyond daily-use filters.
- [ ] Bounded live bulk object/relation/mapping operations with explicit optional staging, per-item
  outcomes and safe retry; do not require a draft merely because several records change (0.9).
- [ ] Asynchronous CSV/Excel import and export with validation previews.
- [ ] Ordered change feed and retryable webhooks.

## Later — production and self-service authoring

- [ ] Complete the release licensing checklist in [LICENSING_TODO.md](LICENSING_TODO.md), including
  ownership, contribution, dependency, security, trademark and commercial-service documentation.
- [ ] PostgreSQL performance and multi-writer uniqueness hardening.
- [ ] OIDC, application/object/operation authorization and audit identity.
- [ ] Replace the pre-authentication, default-enabled workspace mutation posture with authenticated,
  authorized workspace administration; retain the capability gate as deployment defence in depth.
- [ ] Multi-node active-model propagation and protected publication.
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
- [ ] WP1-002: give the child/relation table regions distinct accessible labels. The gate permits
  one known duplicate-label target on the System detail page (light and dark) only.
