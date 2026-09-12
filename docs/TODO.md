# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.7 core mapping

Base 0.6 is released (2026-09-11). WP-1 delivered (2026-09-12). WP-2 delivered (2026-09-12).

- [x] UI-07 (carried from 0.6): automated accessibility and visual-regression gates using the existing
  Playwright harness with `@axe-core/playwright` and visual comparison baselines. Delivered 2026-09-12;
  light-theme baselines only (dark theme does not exist yet).
- [x] Schema 0.6 `mappingGrid` view contract (WP-2). `MappingGridViewConfig` and discriminated
  `ViewDefinition` union, full validation rules (relation binding, containment/required-ownership
  rejection, column/search-field checks), starter model 0.7.0 with two mapping grid views, frontend
  type-safe narrowing and placeholder renderer. Delivered 2026-09-12.
- [ ] Product 0.7: cursor-paged mapping coverage API and candidate lookup (WP-4).
- [ ] ADR-022: exact-binding relation-set versions and atomic mapping replacement in live and
  optional-draft contexts; generic relation writes participate in the same protection.
- [ ] ADR-028: let a workspace draft work under a version the user chooses, so one draft prepares the
  schema 0.6 release while another stays on the version serving live data.

- [ ] WP-4/WP-5: view-specific reads, bounded ambiguous targets, retained relation identities,
  typed attribute semantics and direction-aware replacement/clear validation.
- [ ] WP-6/WP-7: complete-candidate compatibility on creation/version change, atomic pin changes,
  snapshot isolation and complete browser model-context refresh.
- [ ] WP-8A: read-only mapping coverage; WP-8B: selection, conflicts, clearing and contextual creation.
- [ ] WP-9: independent binding fixtures, same-schema differing releases, new-control a11y/visual
  coverage, generic-write races and draft activation/live same-set conflicts.
- [ ] Conditional WP-10: only confirmed missing foundation capabilities; required slices block 0.7
  acceptance. WP-1–WP-3 remain frozen and their implementation reviews stay separate.

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
