# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the active release
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Product 0.7 core mapping

Base 0.6 is released (2026-09-11). WP-1 delivered (2026-09-12). WP-2 delivered (2026-09-12).
WP-3 delivered (2026-09-12); its pending participation changes committed 2026-09-14.
WP-4 and its WP-10A review fix delivered (2026-09-14). WP-5 delivered (2026-09-14). WP-7 delivered (2026-09-14).

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
- [x] WP-7: browser version selection and complete model-context refresh. Delivered 2026-09-14:
  model-release selector in draft creation, model release display on draft cards and detail,
  informational banner and activation refusal when versions differ, version-change action with
  incompatibility diagnostics, model-context refresh after pin change, and dirty-input protection
  via navigation guards. 169 frontend tests (5 new), zero lint errors, production build passes.
- [x] WP-11 (after WP-7, before WP-9): historical release diff/compile unsupported-schema refusals,
  informative frontend states, actionable internal-error diagnostics and WP-7 draft UI consistency
  using the existing modal/form styles and diagnostics; supported pinned-schema loading, shell-aligned
  workspace loading/error recovery and safe handling of HTML/non-JSON API responses. Delivered
  2026-09-15: 422 unsupported_schema_version with structured details for diff/compile/activation, correlation-ID
  error boundary, API client HTML hardening, Modal version-change dialog, supported-schema pinned-model
  loading, retry-aware shell-aligned error recovery and historical-release informational state. Final
  review passed 155 affected backend and 55 focused frontend tests, static/build gates and a five-check
  desktop/narrow real-browser journey. Comprehensive suites and gates remain WP-9.
- [x] WP-12 (after WP-11, before WP-9): Models release **Technical details** with explained,
  copyable public release UUID and canonical content hash; keep human-readable release information
  prominent. Correct semantic-change baselines to earlier release → selected release, including active
  release inspection, with explicit baseline selection and truthful unsupported/first-release states.
  Preserve separate activation compatibility checks; correlation-ID behavior remains unchanged.
  Delivered 2026-09-24 with an additive read-only `GET /model-releases/{id}/activations` over the
  existing audit trail for the recorded-predecessor default. Focused evidence: backend activation-
  history and OpenAPI tests, 15 model-admin component tests, `npm run test:browser:wp12` (seven
  wide/narrow checks); comprehensive suites and a11y/visual gates remain WP-9.
- [x] WP-8A/WP-8B review: preserved the bounded reads and atomic actions; corrected conflict review,
  duplicated configured identity fields and missing coverage filters through WP-14. Reviewed locally
  with focused component and real-browser evidence on 2026-09-15; not committed.
- [x] WP-14A: record ADR-029 and reconcile product, UI, architecture, model and roadmap documentation.
- [x] WP-14B: add cursor-bound `parentObjectId` and mapping coverage-state filters with live/draft/revision
  integration coverage and public-contract updates.
- [x] WP-14C: replace the Browse hierarchy/Views switch with one generic application browser; group
  table/mapping declarations by source object type as collection lenses; provide visible scope, typed
  and coverage facets; retain Live/Draft/History, detail-origin and narrow/keyboard behavior.
- [x] WP-14D: review the composed WP-8/WP-14 implementation, run focused backend/frontend and
  real-browser evidence for generic collections and two mapping directions, then reconcile status
  documentation. Comprehensive suites and a11y/visual baselines remain WP-9 build acceptance.
- [x] WP-13A: risk-ranked contract inventory in `docs/testing/COVERAGE_MAP.md`; filled mapping-write
  authority, draft relation-set, starter-key, date-value and conflict-retry gaps; removed one duplicate
  with surviving protection recorded; reproduced WP-10C/WP-10D as strict xfail tests. 2026-09-24.
- [x] WP-13B: `docs/testing/EXECUTION_GUIDE.md` with measured costs, pytest contract-group markers
  (unclassified modules refused), `unit`/`dom` Vitest projects, boundary-to-check expansion and the
  WP-9 command set; migrated-template databases halve the sampled backend time. 2026-09-24.
- [x] WP-13C: `docs/testing/UI_ACCEPTANCE.md` with reference patterns and the state inventory of 14
  changed 0.7 surfaces; `test:browser:wp13c` covers outage/retry, empty, conflict, draft-context mapping
  and non-active-release draft states at 1440/390px; screenshots reviewed; found WP-10F/WP-10G. 2026-09-24.
- [ ] WP-9: independent binding fixtures, same-schema differing releases, new-control a11y/visual
  coverage, generic-write races and draft activation/live same-set conflicts.
- [x] WP-10A: live/draft cascade deletion advances affected mapping-set versions atomically; stale
  target continuations require refresh. Delivered with WP-4 review, 2026-09-14.
- [x] WP-10C: typed `date`/`dateTime`/`decimal` values in draft writes, activation, and draft/revision
  list filters and sort. Delivered 2026-09-24.
- [x] WP-10D: based contained records keep one containment edge on draft rename or move, and
  activate. Delivered 2026-09-24.
- [ ] WP-10E: a live `dateTime` write drops its UTC offset (the instant moves), and live decimals
  are padded to the column scale. Strict xfail reproduces it; blocks 0.7.
- [ ] WP-10F: contextual mapping-target creation is scoped to the lens's application, so the starter
  model cannot create a target in either direction; needs an owning-application decision.
- [ ] WP-10G: narrow mapping-dialog search box height; raw release UUID in the draft mismatch notice.
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

- [x] WP1-001: the navigation resize separator now sits inside the navigation landmark (fixed
  2026-09-24); its allowlist entries were removed. Collection and settings popovers render inside a
  landmark so their dismiss controls are not stray page content.
- [ ] WP1-002: give the child/relation table regions distinct accessible labels. The gate permits
  one known duplicate-label target on the System detail page (light and dark) only.
