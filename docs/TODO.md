# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.7 core mapping

Base 0.6 is released (2026-09-11). WP-1 delivered (2026-09-12). WP-2 delivered (2026-09-12).
WP-3 delivered (2026-09-12); its pending participation changes committed 2026-09-14.
WP-4 and its WP-10A review fix delivered (2026-09-14). WP-5 delivered (2026-09-14).

- [x] UI-07 (carried from 0.6): automated accessibility and visual-regression gates using the existing
  Playwright harness with `@axe-core/playwright` and visual comparison baselines. Delivered 2026-09-12;
  light-theme baselines only (dark theme does not exist yet).
- [x] Schema 0.6 `mappingGrid` view contract (WP-2). `MappingGridViewConfig` and discriminated
  `ViewDefinition` union, full validation rules (relation binding, containment/required-ownership
  rejection, column/search-field checks), starter model 0.7.0 with two mapping grid views, frontend
  type-safe narrowing and placeholder renderer. Delivered 2026-09-12.
- [x] ADR-022 relation-set versions (WP-3). `relation_set_versions` table with lazy row creation,
  integrated into all six generic relation mutation paths (live and draft), draft deletion cascade
  and activation merge. Delivered 2026-09-12.
- [x] Product 0.7: cursor-paged mapping coverage, version-bound target details and candidate lookup
  (WP-4). View-specific typed projections and batched live/draft SQL reads. Delivered 2026-09-14.
- [x] ADR-022: atomic mapping replacement in live and optional-draft contexts (WP-5). Delivered
  2026-09-14: retained relation identities, typed relation-attribute semantics and direction-aware
  replacement/clear validation with single-direction set version increments.
- [x] WP-5 acceptance follow-up and WP-10B activation hardening: independent bindings, forbidden
  ownership/clearing, overlapping generic writes, and complete touched-set source/live comparison
  with actionable activation refusal. See the 0.7 implementation plan for validation boundaries.
- [ ] ADR-028: let a workspace draft work under a version the user chooses, so one draft prepares the
  schema 0.6 release while another stays on the version serving live data.
- [x] WP-6: backend selected-release creation, complete-candidate compatibility, atomic audited pin
  changes, snapshot isolation and pinned model/metadata reads (2026-09-14).
- [ ] WP-7: browser version selection and complete model-context refresh.
- [ ] WP-8A: read-only mapping coverage; WP-8B: selection, conflicts, clearing and contextual creation.
- [ ] WP-9: independent binding fixtures, same-schema differing releases, new-control a11y/visual
  coverage, generic-write races and draft activation/live same-set conflicts.
- [x] WP-10A: live/draft cascade deletion advances affected mapping-set versions atomically; stale
  target continuations require refresh. Delivered with WP-4 review, 2026-09-14.
- [ ] Further conditional WP-10 slices: only confirmed missing foundation capabilities; required slices block 0.7
  acceptance. WP-1–WP-3 are delivered and frozen; their implementation reviews stay separate.

## Open decisions

- **Offset/limit pagination alongside cursors.** All collection endpoints currently use cursor-based
  pagination (sequential-only). Frontend table UIs need random-access page jumps (e.g. "go to page 8
  of 10") which cursors cannot provide. Proposed change: accept `offset`+`limit` as an alternative to
  `cursor` on list endpoints — when `offset` is supplied the endpoint uses `OFFSET/LIMIT` instead of
  keyset pagination. Cursor mode remains the default and the recommended path for M2M consumers and
  data streaming. The tradeoff is that offset pagination can skip or duplicate rows when data changes
  between page fetches and degrades on very large result sets (`OFFSET N` scans and discards N rows).
  Decision needed: apply to all list endpoints or only `GET /mappings`; whether to add `totalCount` to
  every page response or only when offset mode is used.

See `ROADMAP.md` for the 0.7 delivery scope, exit gate and full milestone sequence.

## Base 0.6 delivery record (complete 2026-09-11)

WP0–WP8, WP8.1-A–C, ADR-026 slices 0–5, WP9 slices A–D, WP10 and UI-01–UI-06 are all complete.
See `CHANGELOG.md` and `BASE_0_6_IMPLEMENTATION_PLAN.md` for detailed delivery history.

## Next — 0.8 and beyond

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

- [ ] WP1-001: place the navigation resize separator inside a landmark. The gate permits only
  the known separator target, with one matching node per page.
- [ ] WP1-002: give the child/relation table regions distinct accessible labels. The gate permits
  one known duplicate-label target on the System detail page only.
