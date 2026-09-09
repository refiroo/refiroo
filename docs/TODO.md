# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the Base 0.6
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Base 0.6 completion under ADR-027

User GAP-01–GAP-08 answers are accepted. That resolves product direction, not runtime delivery.
The next sequence is **WP8.1-B/C → WP9 → WP10**. Completed checkboxes below record prior work;
they do not close the newly identified authority or browser gaps.

- [x] Consolidate accepted live/draft/history and historical-migration direction in ADR-027 and the
  technical planning baseline; retain user comments in the product planning handoff.
- [x] WP8.1-A: make model compatibility inspect all authoritative live data and resolve historical
  reads using their pinned supported model. Prove live-only incompatibility and historical typing after
  model activation, including readable retired workspace content.
- [ ] WP8.1-B: capture an immutable current-live draft base including post-publication edits, model and
  record versions; support live data without a prior publication. Keep historical source separate and
  empty-root creation as development/bootstrap support. Preserve existing drafts through migrations.
- [ ] WP8.1-C: newest-first revision history and cursor tests; prove designation retirement preserves
  live access, catalogue retirement rejects writes, and history is not a direct restore operation.
- [ ] WP9: restore complete live CRUD and optional draft UI, non-default context throughout the task,
  pinned read-only history, truthful retirement, coherent editing and preserved-input recovery.
- [ ] WP10: execute product scenarios against a real browser/backend, plus accessibility, visual,
  concurrency, live-only compatibility, history, migration/lifespan and packaging gates. Record evidence
  by story and channel; no component-only acceptance or relevant skipped CRUD suite.

See `BASE_0_6_IMPLEMENTATION_PLAN.md` for slice ownership, contracts, exclusions and exit evidence.

## Prior Base 0.6 delivery record

- [x] WP0: independently review and accept the produced seven-journey interaction specification and
  frontend acceptance fixtures.
- [x] D1: ADR-019 defines database workspace authority, administrator provisioning, atomic default
  selection, explicit unknown-key failure and read-only retirement. Mutation routes are
  capability-gated but enabled by default until authentication exists; this is not an authorization
  boundary, so exposed deployments must disable them or provide external access control.
- [x] D2 correction: ADR-024 supersedes ADR-020. Workspaces own mutable content drafts and immutable
  revisions; objects and relations inside them have stable identities and audit versions but no
  independent publication lifecycle.
- [x] D3: ADR-021 defines a strict schema 0.5 table contract, explicit schema-version dispatch and
  pre-production schema 0.4 rejection with reset and offline one-shot transition paths. Frontend phase
  6 must reject semantic view types that do not yet have honest contracts and renderers.
- [x] D4: ADR-022 defines exact-binding relation-set versions and atomic replacement. The decision is
  retained, while implementation moves with `mappingGrid` to schema 0.6/product release 0.7.
- [x] D5: ADR-023 adopts React Aria behavior behind RDM-owned semantic wrappers and plain CSS, with
  Lucide behind one accessible icon wrapper and direct feature imports prohibited.
- [x] WP1: implement the RDM-owned accessible UI foundation, exact dependency locks, import boundary,
  semantic wrappers and clarified desktop/narrow application shell.
- [x] WP2: add the workspace catalogue, default runtime state, administration API and selector.
- [x] WP3: implement schema 0.5 typed tables, the fixed daily-use filter/sort grammar and the
  atomic offline schema transition command.
- [x] WP4: delivered per-object revisions; rejected before release and retained only as corrective
  migration input.
- [x] WP5: refroze ADR-024 workspace lifecycle journeys, fixtures, API design, concurrency, cursor and migration contracts; no persistence or APIs implemented.
- [x] WP6: replace object-lifecycle persistence with workspace drafts/revisions and corrective migration.
- [x] WP7: restore established generic object, attribute, containment, relation and translation CRUD over
  WP6 workspace storage; no nested draft CRUD resources or object lifecycle remain.
- [x] WP8: complete workspace draft/revision discovery, graph validation, atomic activation and
  publication retirement as workspace-level operations.
- [x] WP8 amendment (ADR-026, implemented 2026-09-07): `workspaceDraftId` is optional on record writes
  so the **active workspace is live-writable for data** (absent draft → write directly to the live
  object store with a record `expectedVersion` claim and audit; no workspace revision). Active reads
  resolve the live projection; model stays immutable on active; drafts remain the design playground.
  - [x] Slice 0: decision note + doc/roadmap/plan/TODO updates (this entry, plus ADR-026, the
    discrepancy highlight, and the API/architecture/status/README/CHANGELOG notes).
  - [x] Slice 1: live read path — active reads resolve the live projection (drop the active-revision
    membership join for the active context); cursors bind workspace+filters only; history reads stay on
    `workspaceRevisionId` snapshots.
  - [x] Slice 2: live write service path — modernize restored `create_object_record`/
    `update_object_record`, relation helpers and `deletion.py` as the live create/update/delete/cascade
    path (delete is physical over live rows; provenance = record version + `object`/`relation` audit).
  - [x] Slice 3: optional draft context in the object/relation/attribute routers (draft present → draft
    path; absent → live path, resolving `workspaceKey`, requiring an active workspace).
  - [x] Slice 4: activation **delta-merge over live** — apply only the draft's created/updated/tombstoned
    rows onto live with per-record version conflict detection; preserve live-only objects; validate the
    merged graph; write a merged immutable revision snapshot; publish nothing and preserve draft + live
    on any conflict/validation failure.
  - [x] Slice 5: audit additions, OpenAPI digest, full-suite + new live/delta-merge tests; adjusted
    `test_wp8_history.py` active-without-draft expectations; historical-context write rejection stays.
The prior ADR-026 slice record establishes live CRUD and delta merge. Its blanket completion wording
must not imply that fresh live draft bases, full model/history authority or browser journeys are done;
those are tracked above. Previous test totals are historical, not newly executed evidence.

## Next

- [ ] Product 0.7/schema 0.6: typed `mappingGrid`, cursor-paged coverage and candidate lookup.
- [ ] Implement ADR-022 exact-binding relation-set versions and atomic mapping replacement in live
  and optional-draft contexts; generic relation writes participate in the same protection (0.7).
- [ ] Translation coverage matrix and in-cell live editing, with explicit optional staging (0.8).
- [ ] Lazy hierarchy workspace with contextual live creation and atomic reparenting, optional draft (0.8).
- [ ] Integration-grade query expressions beyond Base 0.6 daily-use filters.
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
  parser support; no Base 0.6 force flag. Covers the accepted GAP-02 addition and separate GAP-08 concepts.
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
- Physical purge of published workspace revisions or audit history.
- Graph-canvas-first model authoring.
- Arbitrary server-filesystem model load/save.
- Client-side loops over single-item APIs presented as bulk operations.
- Starter-key branches in backend or frontend behavior.
- Object drafts, object revisions, object activation/retirement, or per-object publication state.
- A second public CRUD dialect under `/workspace-drafts/{draftId}/objects` or `/relations`.
