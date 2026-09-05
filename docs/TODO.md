# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the Base 0.6
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Base 0.6

- [x] WP0: independently review and accept the produced seven-journey interaction specification and
  frontend acceptance fixtures.
- [x] D1: ADR-019 defines database workspace authority, administrator provisioning, atomic default
  selection, explicit unknown-key failure and read-only retirement. Mutation routes are
  capability-gated but enabled by default until authentication exists; this is not an authorization
  boundary, so exposed deployments must disable them or provide external access control.
- [x] D2: ADR-020 defines immutable runtime-object revisions, editable drafts, atomic activation and
  separate derivation/supersession lineage. Existing-object drafts clone an active or retired revision;
  only a new logical object may have a root draft, and it must contain valid initial data. The current
  active revision can be retired without replacement and later used to derive a new draft.
- [x] D3: ADR-021 defines a strict schema 0.5 table contract, explicit schema-version dispatch and
  pre-production schema 0.4 rejection with reset and offline one-shot transition paths. Frontend phase
  6 must reject semantic view types that do not yet have honest contracts and renderers.
- [x] D4: ADR-022 defines exact-binding relation-set versions and atomic replacement. The decision is
  retained, while implementation moves with `mappingGrid` to schema 0.6/product release 0.7.
- [x] D5: ADR-023 adopts React Aria behavior behind RDM-owned semantic wrappers and plain CSS, with
  Lucide behind one accessible icon wrapper and direct feature imports prohibited.
- [ ] WP1: implement the UI foundation and simplified application shell.
- [ ] WP2: add the workspace catalogue, default runtime state, administration API and selector.
- [ ] WP3: implement schema 0.5 typed tables and the fixed daily-use filter/sort grammar.
- [ ] WP4: make runtime-object revisions authoritative; migrate data and add draft, activation,
  retirement, history and retired-discovery contracts.
- [ ] WP5: deliver coherent root-draft, revise-from-history, activation, retirement and lineage UI.
- [ ] WP6: add browser, accessibility and visual-regression gates and complete release validation.

See `BASE_0_6_IMPLEMENTATION_PLAN.md` for scope, file boundaries and exit criteria.

## Next

- [ ] Product 0.7/schema 0.6: typed `mappingGrid`, cursor-paged coverage and candidate lookup.
- [ ] Implement ADR-022 exact-binding relation-set versions and atomic mapping replacement.
- [ ] Translation coverage matrix and in-cell lifecycle workflow.
- [ ] Lazy hierarchy workspace with contextual creation and atomic reparenting.
- [ ] Integration-grade query expressions beyond Base 0.6 daily-use filters.
- [ ] Bounded bulk object and relation operations, including bulk mapping.
- [ ] Asynchronous CSV/Excel import and export with validation previews.
- [ ] Ordered change feed and retryable webhooks.

## Later — production and self-service authoring

- [ ] PostgreSQL performance and multi-writer uniqueness hardening.
- [ ] OIDC, application/object/operation authorization and audit identity.
- [ ] Replace the pre-authentication, default-enabled workspace mutation posture with authenticated,
  authorized workspace administration; retain the capability gate as deployment defence in depth.
- [ ] Multi-node active-model propagation and protected publication.
- [ ] Structured model designer with reference-aware forms, matrices and live preview.
- [ ] Read-only dependency graph visualization where it improves comprehension.
- [ ] Product 0.10: executable runtime-data migration plans for currently blocked model changes.
- [ ] Product 0.10: add workspace-scoped model-release assignment for staged tenant or
  governance-domain rollout.
  Resolve the workspace before its immutable model snapshot, scope compatibility and migration to that
  workspace, bind cursors to the release identity and switch assignments atomically. Supporting mixed
  schema-language versions additionally requires a bounded current/previous parser window and explicit
  conversion; workspace pinning alone is not schema compatibility.
- [ ] Extension packaging after two concrete reuse cases exist.

## Explicitly not planned for Base 0.6

- `mappingGrid`, mapping APIs or relation-set-version implementation.
- Model-workbench information-architecture redesign.
- Physical purge of a published logical object's revisions or audit history.
- Graph-canvas-first model authoring.
- Arbitrary server-filesystem model load/save.
- Client-side loops over single-item APIs presented as bulk operations.
- Starter-key branches in backend or frontend behavior.
