# Base 0.7 implementation plan

**Status:** In progress. WP-1–WP-7 and WP-11 delivered; WP-4 implementation review and the bounded
WP-10A cascade-deletion version fix are complete. WP-5 acceptance follow-up and WP-10B activation
hardening are delivered. The earlier WP-1–WP-3 review boundary remains separate;
WP-1–WP-3 scopes are frozen. WP-6 backend, WP-7 frontend and WP-11 follow-up are delivered.
WP-8A/WP-8B were reviewed and composed through WP-14 (ADR-029), committed 2026-09-15. WP-12 and
WP-13A/B/C are delivered; WP-13A triggered WP-10C/WP-10D/WP-10E and WP-13C found WP-10F/WP-10G, all
delivered (WP-10E/F/G on 2026-09-25). **WP-9 composed 0.7 acceptance passed on 2026-09-25**; it found and
closed WP-10H/I/J; the draft-timestamp decision it surfaced was taken and delivered as WP-10K. All work
packages are complete; cutting the 0.7.0 release is a separate step.

**Target:** Product 0.7.0, schema language 0.6. The starter model content advances to a version on
schema 0.6; that number alone does not mean the product release is accepted.

**Depends on:** Base 0.6 released (2026-09-11); retained generic CRUD, typed tables, workspace
lifecycle, optional drafts, immutable history, delta-merge activation and the frontend redesign.

## Validation ownership

Each implementation package uses focused changed-behavior and regression checks under
[AGENTS.md](../AGENTS.md#work-package-validation). Full backend/frontend suites, composed journeys
and comprehensive accessibility/visual gates belong to WP-9 after implementation is complete.
WP-7/WP-8A/WP-8B still add scenarios for their new controls and check the changed surfaces locally.
Focused migration/startup, concurrency and other high-risk boundary checks remain package requirements.
Record deferred build checks explicitly; package delivery does not establish release acceptance.
WP-13 audits priority coverage, implements efficient affected-area commands and establishes explicit
UI acceptance. Its slices use focused checks; WP-9 owns the comprehensive execution.
Historical validation evidence below remains a record of what was actually run.

## Product outcome

A mapping steward can review mapping coverage for a configured relationship, see mapped, unmapped and
ambiguous rows, and safely create, remove or replace one mapping without navigating low-level relation
screens. Concurrent mapping work is protected at the relation-set level. A steward can prepare data in
a draft that works under the next model version while live data and other drafts keep the current one.

Traceability: US-M01–M04, US-W09; SC-07, SC-15. See
[product stories](product-functionality/USER_STORIES.md) and
[acceptance scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md).

## Release principles and exclusions

1. Mapping is a business view over the generic relation graph, not a separate data model.
2. Relation-set versions protect all relation writes, not only mapping operations.
3. Draft version selection changes one draft and nothing else; it is not model activation.
4. Schema 0.6 is an additive extension of 0.5; existing 0.5 models remain activatable.
5. Preserve generic CRUD, typed values, stable IDs, bounded queries and optimistic concurrency.
6. Every added mandatory step or removed capability needs an explicit product reason.

Excluded: moving a draft onto a version its content does not fit (0.10 conversion machinery),
workspace-scoped model-release assignment (0.10), translation/hierarchy specialist views (0.8),
bulk/integration APIs (0.9), authentication (0.10), physical history purge, model-designer redesign.

## Frozen-scope boundary and 2026-09-12 design follow-up

WP-1–WP-3 retain their existing scope and delivery evidence. The plan review does not establish
implementation defects in them or replace the pending WP-1/WP-2 review. Later packages consume their
contracts and add integration acceptance evidence:

| Frozen foundation | Follow-up owner | Required evidence |
| --- | --- | --- |
| WP-1 gates | WP-7, WP-8A, WP-8B, WP-9 | New version-selection and mapping controls included in accessibility and visual scenarios |
| WP-2 configuration | WP-4, WP-9 | View-specific API configuration and independent relation-binding fixtures |
| WP-3 set versions | WP-4, WP-5, WP-9 | Consistent coverage/version reads, both directional sets, generic-write races and activation conflicts |

If that evidence reveals a missing foundation capability, activate WP-10 below; do not amend a frozen
package implicitly. Dark-theme baselines remain deferred until dark mode exists.

## Work packages

Each work package is scoped for one LLM coding session. Dependencies between packages are stated
explicitly; independent packages may be implemented in any order within their tier.

### Tier 0 — Foundation (no 0.7 dependencies)

#### WP-1: UI-07 — Automated accessibility and visual-regression gates ✓

**Status:** Delivered.

**Carried from 0.6.** Add tooling gates using the existing Playwright harness; no application logic
changes.

**Scope:**

1. Add `@axe-core/playwright` as a dev dependency.
2. Create an accessibility test helper that runs axe on a loaded page and reports violations with
   element, rule and impact. Configure permitted known violations (if any) as an explicit allowlist
   with tracked issue references, not a blanket suppression.
3. Write accessibility gate tests for the core page types: collection table, record detail with
   panels, draft editing, history view and the model workbench. Exercise two object types.
4. Add visual-regression infrastructure: screenshot capture against named baselines, pixel-diff
   threshold configuration, and a clear workflow for updating baselines when intentional visual
   changes land.
5. Capture initial baselines for the same core page types in both light and dark themes.
6. Document the gate in the definition of done and validation matrix in `AGENTS.md`.

**Primary areas:** `frontend/package.json`, `frontend/e2e/`, test infrastructure.

**Prerequisites:** None — uses the existing Playwright installation and e2e test patterns.

**Decisions needed:** None.

**Exit:** `npm run test:e2e` (or equivalent) runs accessibility checks and visual-regression
comparisons; violations and unexpected visual changes fail the gate. Baselines are committed and
the update workflow is documented.

**Delivery notes:**

- `npm run test:a11y` runs axe-core WCAG 2.1 AA checks on 9 page types (collection table ×2 object
  types, record detail ×2, draft collection, draft detail, history, model workbench, drafts list).
  All pages pass with zero unexpected violations.
- `npm run test:visual` compares viewport screenshots against 9 committed baselines using pixelmatch.
  `npm run test:visual:update` accepts new baselines after intentional visual changes. Missing
  baselines fail the normal gate; only explicit update mode creates or replaces them.
- Two allowlisted violations with tracked references in `TODO.md`, exact node targets and bounded
  counts (the duplicate-label exception applies only to System detail): `region` (WP1-001: resize-handle
  separator
  between landmarks) and `landmark-unique` (WP1-002: duplicate "Objects" aria-label on child/relation
  panels).
- ~16 color-contrast violations fixed by darkening muted text colors to `var(--color-text-muted)`
  (`#66736e`, 4.68:1 on white). One `definition-list` violation fixed (row-actions moved inside
  `<dd>`). Sidebar changed from `<div>` to `<aside>` with `aria-label`.
- **Deviation from scope item 5:** baselines captured for light theme only. Dark theme does not exist
  yet; dark-theme baselines will be added when a dark theme is implemented.
- Gate documented in `AGENTS.md` validation matrix and `frontend/e2e/README.md`.

---

### Tier 1 — Schema and persistence (no cross-tier dependencies)

#### WP-2: Schema 0.6 model language — `mappingGrid` view contract ✓

**Status:** Delivered.

**Scope:**

1. Extend `models/schema.py` to accept `schemaVersion: "0.6"` alongside `"0.5"`. The top-level
   model discriminates on schema version; schema 0.5 models continue to parse and activate.
2. Add a `MappingGridViewConfig` Pydantic model with the typed contract: `relationTypeKey`,
   `fromObjectTypeKey`, `toObjectTypeKey`, `direction` (`outgoing` | `incoming`), bounded `pageSize`,
   source columns, target display columns and candidate search fields.
3. Add `MappingGridViewDefinition` to the `ViewDefinition` discriminated union (type `"mappingGrid"`).
4. Add model validation rules: the relation type must exist; the from/to object type keys must match
   an allowed `objectTypeRelations` triple for that relation type; the binding must not be a
   containment (`parentOf`) or required-ownership binding; columns reference attached attributes;
   candidate search fields reference target-type attributes.
5. Update the compiler to dispatch schema 0.6 explicitly. A schema 0.6 model that declares only
   `table` views is valid; `mappingGrid` is an addition, not a replacement.
6. Extend the starter model to schema 0.6 with at least one `mappingGrid` view exercising
   `system-value-maps-to-master` and retain the existing table views.
7. Preserve the schema 0.4 → 0.5 transition tooling; add a 0.5 → 0.6 path if the only change is the
   version number (the schema 0.6 language is a strict superset).
8. Update `APPLICATION_MODEL.md` with the `mappingGrid` contract.

**Primary areas:** `backend/app/models/schema.py`, `backend/app/services/model/compiler.py`,
`backend/app/services/model/validation/`, `model/rdm-starter.json`, `docs/APPLICATION_MODEL.md`,
tests.

**Prerequisites:** None.

**Decisions needed:**

- **D1: Mapping-grid configuration shape.** The fields listed above (relationTypeKey, from/to object
  type keys, direction, columns, candidate search, pageSize) are derived from ADR-022 and the
  product stories. Review whether `candidateSearchFields` should be part of the view config or
  derived from the target object type's searchable/filterable attributes. _Recommendation:_ declare
  them explicitly in the view config, consistent with table view's explicit `filterFields`.
- **D2: Schema 0.5 → 0.6 transition path.** Since schema 0.6 is a strict superset (only adds
  `mappingGrid`), an existing 0.5 model can be promoted by changing only the version number.
  _Decision:_ should the existing `model_schema_upgrade` CLI accept 0.5 → 0.6 transitions, or is a
  new model file sufficient? _Recommendation:_ a new model file is sufficient pre-production; defer
  CLI upgrade tooling unless a database already has 0.5-only releases that must coexist.

**Exit:** A schema 0.6 model with `mappingGrid` views parses, validates, installs and activates. A
schema 0.5 model still works. Invalid mapping-grid configuration (wrong relation type, containment
binding, missing columns) is rejected with precise JSON-path errors. Tests cover both schema versions.

**Delivery notes:**

- `MappingGridViewConfig` and `MappingGridViewDefinition` added to `models/schema.py` with a
  Pydantic discriminated union on `ViewDefinition.type`. `schemaVersion` accepts `"0.5"` and `"0.6"`;
  schema 0.5 rejects `mappingGrid` at the view type path, while schema 0.6 also accepts table-only models.
- Validation in `application_rules.py` checks: relation type exists, from/to object types exist,
  matching `objectTypeRelations` triple exists, relation is not containment (`parentOf`), binding is
  not required-ownership, source/target columns reference attached attributes, candidate search fields
  are searchable target-type attributes, all field lists are unique.
- Compiler, registry, releases, router and startup updated to support both schema versions.
- Starter model advanced to schema 0.6 / content release 0.7.0 with two `mappingGrid` views:
  `system-to-master-mapping` (outgoing, system-value → master-value in RDM Systems) and
  `master-to-system-mapping` (incoming, master-value ← system-value in RDM Master).
- Frontend `ViewDefinition` is a TypeScript discriminated union. Type-safe narrowing in App.tsx,
  routes.ts, CollectionView.tsx and ObjectToolbar.tsx. At this package boundary the view registry
  dispatched `mappingGrid` to a styled placeholder; WP-8/WP-14 subsequently replaced it with the
  contextual mapping lens.
- 11 new backend tests covering parse, activation, backward compatibility and all validation rejection
  paths. Schema upgrade tests generate a schema 0.5 fixture at test time to isolate from the 0.6
  starter model. Initial validation recorded 370 backend passes and 161/162 frontend passes.
  The stale draft-context test assertion is corrected in the WP-1/WP-2 review fixes; final
  regression evidence is recorded below.
- `APPLICATION_MODEL.md` updated with the `mappingGrid` contract table and validation rules.
- **D1 resolved:** `candidateSearchFields` declared explicitly in view config (consistent with table
  view's `filterFields`).
- Offline schema 0.4 recovery accepts compatible schema 0.5 or 0.6 candidates, preserving the
  documented startup command with the current starter. Tests run the actual logged command,
  verify interrupted-transaction rollback, restart and safe repeat refusal.
- **D2 resolved:** new model file sufficient pre-production; no CLI upgrade tooling for 0.5 → 0.6.

**WP-1/WP-2 review validation:** Backend Ruff and all 384 tests pass; frontend formatting,
lint (zero errors, 12 existing warnings), all 162 tests and production build pass. Four gate-helper
regressions pass. Chrome accessibility checks pass on nine core pages and reject two injected
violations; all nine visual comparisons pass with the reviewed loaded-workbench baseline.
Real temporary-database lifespan checks cover clean bootstrap, restart, supported recovery candidates,
interrupted-transition rollback and safe repeat refusal; the full suite also exercises database upgrade
and interrupted-migration refusal/recovery. A consistent copy of the configured development database
starts and restarts with health/model reads returning 200 under its selected schema 0.5 release.
These are WP-1/WP-2 regression checks, not composed 0.7 product acceptance or dark-theme coverage.

---

#### WP-3: Relation-set version persistence and generic participation ✓

**Status:** Delivered.

**Scope:**

1. Add a `relation_set_versions` database table through Alembic: composite unique key on
   (`workspace_key`, `workspace_draft_id` nullable, `relation_type_key`, `from_object_type_key`,
   `to_object_type_key`, `anchor_object_id`, `direction`), with an integer `version` (starting at 0
   for untouched sets) and timestamps. `workspace_draft_id` null represents the live context.
2. Add a service function to atomically read-and-increment the set version for an exact binding,
   creating the row on first touch.
3. Integrate into existing generic relation create, update and delete paths: every relation mutation
   increments both the outgoing set (anchored on `fromObjectId`) and the incoming set (anchored on
   `toObjectId`) for the exact binding. This is transparent to callers — no API change.
4. Ensure draft-scoped relation writes use the draft-scoped set version (draft id in the key) and
   live-scoped writes use the live set version (null draft id).
5. Draft deletion cascades set-version rows for that draft. Draft activation merges draft set versions
   into live set versions.
6. Add focused tests: relation create/update/delete increments versions; concurrent claims on the same
   set conflict; different bindings of the same relation type have independent versions; draft and
   live versions are independent.

**Primary areas:** `backend/app/models/database.py`, `backend/app/migrations/`, `backend/app/services/relations.py`,
`backend/app/services/workspaces.py`, tests.

**Prerequisites:** None.

**Decisions needed:**

- **D3: Set-version row lifecycle.** Should set-version rows be created eagerly (at relation creation)
  or lazily (on first mapping-aware operation)? _Recommendation:_ lazily, with version 0 for a
  previously untouched set, as specified in ADR-022. This avoids backfilling existing data.
- **D4: Activation merge strategy.** When a draft activates, its set-version rows must be reconciled
  with live versions. _Recommendation:_ the activation delta already tracks which relations the draft
  touched; apply the same touched-record conflict check to set versions. A set version in the draft
  that was also changed live since the draft's base conflicts.

**Exit:** Every generic relation write atomically maintains set versions. Concurrent relation writes
to the same binding conflict correctly. Draft and live contexts have independent version tracks.
Existing relation tests still pass (set versions are transparent).

**Delivery notes:**

- `relation_set_versions` table added through Alembic migration `20260912_01`. Composite unique key
  on (workspace_key, workspace_draft_id, relation_type_key, from_object_type_key, to_object_type_key,
  anchor_object_id, direction) with a partial unique index `uq_relation_set_version_live` for the
  live context (where `workspace_draft_id IS NULL`), because NULL != NULL in SQL unique constraints.
  Integer `version` starts at 0 (implicit) for untouched sets; first mutation inserts with version 1.
  `CHECK` constraint limits direction to `outgoing` or `incoming`. Foreign keys cascade on workspace
  and draft deletion.
- `RelationSetVersion` SQLAlchemy model in `models/database.py` mirrors the migration schema
  including the partial unique index.
- `services/relation_set_versions.py` provides three functions: `increment_set_versions` (atomically
  advances both outgoing and incoming sets for a mutation, creating rows lazily on first touch),
  `delete_draft_set_versions` (removes all set-version rows for a discarded draft) and
  `merge_draft_set_versions_to_live` (carries draft mutation counts into live set versions during
  activation, then deletes draft rows).
- Integrated into all six generic relation mutation paths: `create_live_relation`,
  `update_live_relation` and `delete_live_relation` in `services/relations.py`; `put_draft_relation`,
  `patch_draft_relation` and `delete_draft_relation` in `services/workspace_revisions.py`.
  Set-version maintenance is transparent to callers — no API response change.
- Draft deletion path (`_delete_draft_and_base`) calls `delete_draft_set_versions` before deleting
  the draft. Draft activation path calls `merge_draft_set_versions_to_live` before cleanup.
- 9 focused tests in `tests/test_relation_set_versions.py`: create/update/delete increment both
  outgoing and incoming versions; different bindings have independent version tracks; draft-scoped
  relation create increments draft-scoped set version; draft and live versions are independent;
  draft discard cascades set-version rows; draft activation merges set versions into live;
  existing relation API responses are unchanged (transparent).
- **D3 resolved:** lazy row creation with implicit version 0 for untouched sets, as specified in
  ADR-022.
- **D4 resolved:** activation merges draft set versions by adding the draft's mutation count to the
  live set version, then deletes draft rows.
- All 379 backend tests pass. Migration tests confirm the new table is included in the complete
  current schema and that upgrade/interrupted-migration paths work correctly.

---

### Tier 2 — Mapping API (depends on WP-2 and WP-3)

#### WP-4: Mapping coverage API

**Delivered 2026-09-14.** Dedicated mapping router; live and draft SQL projections, batched exact
counts and 20-target previews, version-bound `/mapping-targets` continuation, configured typed
fields and candidate search. The response and detail-query contracts are frozen in `docs/API.md`.
Integration coverage includes both directions, all states, shared-binding views, candidate and
coverage pagination, large ambiguous live/draft sets, overlays/tombstones, cursor mismatches,
draft-pinned differing releases, concurrent reads and query counts independent of page row count.

**Scope:**

1. Add a mapping coverage query endpoint:
   `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage?relationTypeKey=...&fromObjectTypeKey=...&toObjectTypeKey=...&direction=...`
   with cursor pagination (`pageSize`, `cursor`), optional search on source name/attributes.
   Require `applicationKey` and `viewKey` to resolve the existing `mappingGrid` configuration under
   the effective live or draft-pinned model. Explicit binding parameters must match that view.
   Multiple views over one binding may select different columns and candidate search fields.
2. The response returns batched rows: each row contains the source object identity and display fields,
   the current mapping state (`mapped` | `unmapped` | `ambiguous`), the current target(s) with
   display fields, and the current `mappingVersion` (relation-set version) for that source.
   Return exact `targetCount`, at most 20 target summaries, and an explicit cursor-paged target-detail
   query for remaining targets; never truncate without reporting the count and continuation.
   State derives from the complete count. Fields, state, targets and version describe one consistent
   read; target continuation binds the observed mapping version and requires refresh if it changed.
3. The query resolves against the view's configured relation binding and counts outgoing (or incoming,
   per direction) edges per source object. Zero edges = unmapped, one = mapped, more than one =
   ambiguous.
4. Support `workspaceDraftId` query parameter for draft-context coverage.
5. Add server-side candidate search:
   `GET /api/v1/workspaces/{workspaceKey}/mapping-candidates?objectTypeKey=...&search=...`
   with the same required application/view identity and optional `workspaceDraftId`, returning
   candidate target objects for mapping, with cursor pagination. `objectTypeKey` must match the
   configured target side for the selected direction. Candidates are objects of
   the target type in the same workspace, searched by name and configured searchable attributes.
6. Both endpoints validate the relation binding against the active model (or draft-pinned model) and
   return `404` for unknown bindings or views, and an explicit validation error for view/binding
   mismatches. Cursors bind workspace, live/draft context, effective release, view, direction and
   query configuration. Typed projections use the selected view; candidate eligibility respects
   direction-aware constraints, with final validation on save.

**Primary areas:** `backend/app/routers/` (new mapping router or extension of relations router),
`backend/app/services/` (new mapping service), `backend/app/models/api.py`, tests.

**Prerequisites:** WP-2 (schema 0.6 with mapping-grid config to validate against), WP-3 (relation-set
versions to return as `mappingVersion`).

**Decision resolved:** D5 uses the dedicated `backend/app/routers/mapping.py` router. Coverage,
`mapping-candidates` and `mapping-targets` share view/context resolution; response fields and target
continuation parameters are frozen in [API.md](API.md#product-07-mapping-api-wp-4-and-wp-5-delivered).

**Exit:** Coverage returns correct mapped/unmapped/ambiguous states with set versions. Candidate
search returns bounded, searchable results. Both endpoints page correctly and validate against the
model. Draft context returns draft-scoped coverage and versions. Tests cover all three mapping states,
pagination and invalid-binding rejection. Include multiple views over one binding, candidates beyond
page one, large ambiguous sets, mismatched cursors and concurrent coverage reads. These are WP-4
integration checks, not amendments to WP-2/WP-3.

---

#### WP-5: Atomic mapping replacement API

**Delivered 2026-09-14.** `PUT /api/v1/workspaces/{workspaceKey}/mappings` with live and draft
paths, direction-aware cross-cardinality enforcement, retained relation identity, typed attribute
semantics (omitted/explicit/empty), single-direction set version increments without double counting,
idempotent no-ops, bounded conflict responses and mapping-transition audit events. Decisions D6
(PUT method), D7 (one target per operation) and D13 (retained identity + attribute omission) are
resolved. The response and attribute contracts are documented in `docs/API.md`. After follow-up
review and acceptance follow-up, 73 replacement/activation integration tests pass; the full backend
suite passes 486 tests on SQLite.

**Review fixes (2026-09-14):** Conflict target summaries were direction-unaware — incoming conflicts
could return the source object instead of the target. Fixed to use the same direction-aware extraction
as the rest of the replacement path. Draft no-op paths (clear-when-already-unmapped and
same-target-with-same-attributes) incorrectly incremented the draft aggregate version; claim is now
deferred until after no-op detection. Three regression tests added. Unused test imports cleaned up.

**Final documentation/review follow-up (2026-09-14):** Twelve new HTTP regression cases reproduced
ancestor-scope bypasses, an orientation-dependent required-ownership rejection and empty supplied
view identities selecting unconfigured reads. Replacement now reuses canonical live/draft relation
validation against the final graph; obsolete and retained edges are excluded while checking the
proposed edge. Generic draft writes also refuse a missing required ancestor, matching live writes.
Required-ownership rejection is independent of orientation. Supplied view keys are checked by
presence rather than truthiness. Valid outgoing replacement within one ancestor scope still succeeds;
refusals preserve graph and aggregate/set versions. Documentation across build, product, roadmap,
catalogue and acceptance records separates this backend delivery from pending WP-8A/WP-8B/WP-9.

**Earlier implementation review snapshot (2026-09-14, before WP-10B):** Replacement now conditionally claims the exact
set version before graph writes, including the initially absent row, and holds the workspace active
status through the transaction. Draft no-ops reject stale aggregate tokens without increments.
Draft deletions/attribute updates preserve underlying relation audit events and mapping transitions
identify their draft context. Large conflict previews provide version-bound continuation, with a
binding-only target projection when no mapping view exists. Regression evidence includes concurrent
HTTP replacements, conditional-claim refusal, both draft no-op states, relation audits and live/draft
continuation with and without mapping views. Final validation: Ruff and 446 backend tests passed;
frontend format, lint (zero errors, 12 existing warnings), 162 tests and build passed. PostgreSQL
concurrency and the future mapping browser workflow were not exercised.

**Mapping list API (initial delivery snapshot, 2026-09-14):** `GET /api/v1/workspaces/{workspaceKey}/mappings` delivered with
all-optional parameters. No filters returns every edge twice (outgoing + incoming); `direction` filter
yields single-orientation rows. Optional `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`
narrow the result. Optional `applicationKey` + `viewKey` control column projection only (enriched
`fields` dict); without a view, default projection returns id/name/objectTypeKey with empty fields.
Each row includes `direction` in the response. Six new integration tests added (28 total mapping
tests); the earlier delivery gate passed 437 tests on SQLite. The later WP-5/WP-10B final gate
and current totals are recorded below.

**Scope:**

1. Add the mapping replacement endpoint:
   `PUT /api/v1/workspaces/{workspaceKey}/mappings`
   accepting `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey`, `direction`,
   `sourceObjectId`, `expectedMappingVersion`, nullable `targetObjectId` and optional relation
   `attributes`. Endpoint type keys are always required (even when target is null) so removal cannot
   broaden scope.
2. Validate: workspace status, draft status if `workspaceDraftId` is supplied, source and target
   object existence and types, exact allowed binding match, binding is not containment or required
   ownership, cardinality, and typed relation attributes.
3. Transaction: conditionally claim the relation-set version; delete obsolete edges for the exact
   binding and anchor except an already-existing selected edge; preserve its public identity and
   update its attributes if requested, or create it when absent. Maintain all affected outgoing and
   incoming sets through the WP-3 service without double increments, then commit atomically.
4. A null target with empty attributes removes the mapping (all edges for that binding and source).
5. A non-null target replaces the complete set with exactly that target.
6. Stale version claim returns `409 mapping_version_conflict` with current version and bounded
   current-target summaries; nothing changes. Use WP-4's exact count, bounded preview and target
   continuation convention. Check stale tokens before treating an identical request as a no-op.
7. Requesting the already-current target with identical attributes is an idempotent no-op: no version
   increment, no audit event.
8. Record one mapping-transition audit event with old/new target and relation identities.
9. Live and draft contexts are both supported. Draft writes claim `expectedWorkspaceDraftVersion` in
   addition to `expectedMappingVersion`. Both conflict paths preserve attempted input in the client.
10. Omitted `attributes` preserves values on a retained edge; for a new edge it supplies no explicit
    values and normal typed validation/defaults apply. An explicit object replaces the complete
    attribute set; `{}` clears it only where valid. Clearing a mapping permits omitted or empty
    attributes only. No typed attribute write bypasses the canonical validation boundary.
11. Preserve underlying relation audit events as well as the single mapping-transition event.
    Attribute-only changes count as a transition; semantic no-ops produce neither event.
12. One selected target is the mapping-operation rule, separate from relation cardinality.
    Check cardinality in the actual direction and across the applicable relation scope; never infer
    outgoing single-target cardinality from `one-to-many`. Clear is permitted only if empty is valid.

**Primary areas:** `backend/app/routers/mapping.py`, `backend/app/services/mapping.py`,
`backend/app/models/api.py`, `backend/app/services/audit.py`, tests.

**Prerequisites:** WP-3 (relation-set versions), WP-2 (model validation of mapping bindings),
and WP-4 response-contract freeze for bounded conflict target summaries.

**Decisions (resolved):** D6 uses PUT for complete-set replacement; D7 selects zero or one target
per operation while validating the declared cardinality separately; D13 preserves selected relation
identity and uses omission/explicit-object attribute semantics. Multi-target operations remain later
bulk work.

**Exit:** Mapping replacement creates, replaces and removes mappings atomically. Concurrent
replacement conflicts with the current version. Idempotent re-save does not increment the version.
Audit records the transition. Draft and live contexts both work. Two different relation bindings are
exercised. Invalid bindings, containment and required-ownership are rejected. Test retained relation
identity during ambiguous resolution, omitted/empty/typed attributes, both directions, constrained
candidate targets, rejected clearing, generic-write versus replacement races and both draft tokens.

---

### Tier 3 — Draft version selection (depends on Tier 1)

#### WP-6: ADR-028 draft version selection — backend

**Status:** Delivered 2026-09-14. Selected-release creation, complete effective-graph compatibility,
atomic audited pin changes and context-aware model/metadata reads are implemented. Backend and
HTTP regression coverage is in `backend/tests/test_build07_wp6.py`; browser selectors and context
refresh remain WP-7. No activation bypass or conversion is included.

**Validation:** Backend Ruff and all 507 tests passed on SQLite, including 20 WP-6 regressions.
Frontend formatting, lint (zero errors, 12 existing warnings), all 164 tests and production build
passed. Frontend tests used `--maxWorkers=1 --testTimeout=30000` after the default parallel run
hit timing failures on the busy machine. Independent backend review found no remaining defects.
This is backend/API evidence; WP-7 browser delivery and WP-9 composed acceptance remain pending.

**Scope:**

1. The `WorkspaceDraft` table already has `model_release_id`. Extend draft creation to accept an
   optional `modelReleaseId` parameter: when supplied, the draft pins that installed release instead
   of the currently active one. The release must be installed, parseable and supported by this
   deployment; an unavailable, corrupt or unsupported target is refused with the existing pinned-model
   error codes.
2. Extend draft reads, writes and validation to resolve the draft's pinned model instead of the global
   active model. This means: when a `workspaceDraftId` is supplied on a record read/write, the
   service resolves the draft's `model_release_id` and uses that model for validation, type checking
   and response composition.
3. Add a draft version-change endpoint:
   `PATCH /api/v1/workspaces/{workspaceKey}/drafts/{draftId}/model-release`
   accepting `modelReleaseId` and `expectedDraftVersion`. The target release must be installed and
   supported. The draft's existing content must already satisfy the target model (fields, relations,
   types). If the content does not fit, return `409 draft_content_incompatible` with diagnostics; the
   0.10 conversion machinery is required for that case.
4. Draft activation: the existing `workspace_draft_model_release_conflict` refusal is retained. A
   draft activates only when its pinned release matches the currently active release. No change to
   the activation path.
5. Discarding a draft is always available regardless of version match.
6. Draft detail responses include the pinned model release identity (public ID, key, version) so the
   UI can display which version each draft works under.
7. Current-live base creation: when a draft is created against a non-active release, the base still
   captures current live content and record versions, but the draft's model context uses the selected
   release. The base is a data snapshot, not a model snapshot. Validate the complete copied candidate
   against the selected target before committing creation; incompatible inherited content returns
   `409 draft_content_incompatible` without leaving a draft/base behind. Keep the captured active
   release/runtime version separate from the chosen draft pin, preserving snapshot retry checks.
8. Compatibility check: when moving a draft to a new release, run the existing model compatibility
   rules through a draft-scoped whole-graph validation boundary. The current live-table compatibility
   analyzer cannot be called unchanged for this purpose. Validate effective membership: immutable
   base plus authored replacements/new rows minus tombstones, including attributes, ownership,
   containment, uniqueness and cardinality. If incompatible, refuse with bounded structured
   diagnostics; do not attempt conversion.
9. Version change claims `expectedDraftVersion` and validates the same candidate graph atomically
   with updating the pin. Success increments the draft version and audits old/new public release
   identities; stale claims or failures leave pin, content and version unchanged. Selecting the
   current pin with a valid token is a no-op. Historical-source creation retains its source pin;
   selecting a different release is an explicit subsequent compatible version change.

**Primary areas:** `backend/app/services/workspaces.py`, `backend/app/services/model/runtime.py`,
`backend/app/routers/workspaces.py`, `backend/app/models/api.py`, tests.

**Prerequisites:** None for the backend logic (the database column exists). However, if schema 0.6 is
the motivating use case, WP-2 should be complete so a schema 0.6 release can be installed for
testing.

**Decisions needed:**

- **D8: Content compatibility when changing a draft's version.** When a draft moves from release A to
  release B, what content is checked? _Recommendation:_ check the draft's authored candidate content
  (complete effective objects, attributes and relations, including inherited base content) against the target model. If the target model removes an
  object type, attribute type or relation type that the draft uses, refuse. If the target adds new
  required fields, refuse (the draft has not provided them). This is a strict "content must already
  fit" check, not a conversion.

**Exit:** A draft can be created against any installed, supported release. Draft reads, writes and
validation use the draft's pinned model. A draft on a non-active release cannot activate. Moving a
draft to a release its content satisfies succeeds; moving to an incompatible release is refused with
diagnostics. Discarding is always available. Tests cover: draft on active release (existing behavior),
draft on non-active release, activation refusal, version change, incompatible version change refusal,
discard, and two drafts on different releases in the same workspace. Include incompatible creation,
inherited invalid content, tombstoned content, concurrent edits during version change, snapshot retries,
and unchanged live/history/other-workspace state. Two same-schema releases must differ in fields,
rules and views so model-context selection is observable.

---

#### WP-7: ADR-028 draft version selection — frontend ✓

**Status:** Delivered 2026-09-14.

**Delivery notes:** Model-release selector in draft creation (default active release, optional
non-active selection from installed releases); model release key and version displayed on draft list
cards and draft detail header; informational banner and disabled activation with tooltip when the
draft's model version differs from the active release; "Change model version" action in secondary
draft actions with available releases, incompatibility diagnostics from the server, and dirty-input
protection via `allowNavigation()`; model-context refresh after successful pin change reloads the
draft, pinned model and active release state and triggers a view refresh with existing `views[0]`
fallback. The review follow-up below replaces the initial external-pin refresh implementation. Frontend
type `WorkspaceDraft` extended with `modelReleaseKey` and `modelReleaseVersion`. API client extended
with optional `modelReleaseId` on `createWorkspaceDraft` and new `changeWorkspaceDraftModelRelease`
method. 169 frontend tests (5 new covering creation selector, non-active draft creation, single-release
omission, draft card display and incompatibility error), zero lint errors, 12 existing warnings,
production build passes, `git diff --check` clean.

**Implementation review follow-up (2026-09-14):** Release selectors now use cursor feeds with
continuation and retry rather than silently stopping at page one. Refresh validates and loads a changed
pin before publishing its aggregate token, blocks writes after failed/refused refresh, and protects dirty
input. Model changes reset the route to a model-declared default, clear obsolete cursors and remount
model-dependent record/collection components. A committed pin change followed by refresh failure is
reported visibly and truthfully. Focused component/API-adapter/application regressions cover these paths;
comprehensive suites remain WP-9, and visual integration was delivered in WP-11.

**Scope:**

1. Draft creation dialog: add an optional model-release selector. The default is the currently active
   release. Available releases come from the installed-releases list endpoint. Historical-source
   creation retains the source revision's pinned release.
2. Draft list and detail: display which model release each draft works under. Distinguish "active
   version" from a different pinned version visually, including replaced older releases.
3. Draft detail banner: when a draft's version differs from the active release, show an informational
   banner explaining the state ("This draft uses [version]; live uses [active version]. Activation
   requires these versions to match.").
4. Activation refusal: when a draft's version does not match the active release, the activate button
   is disabled with a tooltip/explanation. The existing `workspace_draft_model_release_conflict`
   error handling is retained as a server-side safety net.
5. Version change: add a "Change model version" action on draft detail. It shows available installed
   releases and attempts the change. Success updates the draft's model context; failure shows the
   incompatibility diagnostics. The 0.10 conversion option is not offered.
6. Discard: always available, never requires model agreement. No change to existing discard flow.
7. The mapping grid and table views resolve their column/filter/sort configuration from the draft's
   pinned model, not the global active model.
8. Successful pin changes reload the pinned model and refresh applications, navigation, views,
   detail panels, forms, lookups, permissions/capabilities and model-dependent caches. Reset obsolete
   cursors. If the route/view no longer exists, offer a valid model-declared destination.
   Protect dirty input before changing context. A refresh detecting an external pin change must
   reload the model before enabling writes; never pair a new draft token with stale model forms.
9. Exercise the creation/version selectors, incompatibility diagnostics and activation explanation
   in accessibility and visual scenarios, including an older retained pin.

**Primary areas:** `frontend/src/features/workspaces/`, `frontend/src/features/objects/`,
`frontend/src/api/`, `frontend/src/types/`, tests.

**Prerequisites:** WP-6 (backend version selection).

**Decisions needed:** None — the UX follows directly from the acceptance criteria in US-W09 and SC-15.

**Exit:** A steward can create a draft against a non-active release, see which version it uses,
attempt activation (refused with explanation), change its version (where content fits), and discard
it freely. Two drafts on different releases coexist without interference. Tests cover the creation
selector, version display, activation refusal and discard paths, different same-schema model content,
removed views, dirty-input protection and an external version change.

---

### Tier 4 — Mapping frontend (depends on WP-2, WP-4, WP-5)

#### WP-8A: Read-only mapping grid — frontend

**Scope:** Replace the placeholder with generic cursor-paged coverage and bounded target previews,
state/count display, target continuation, empty/error/retry states, keyboard operation and responsive
layout. Resolve the effective model and view, use the WP-4 API, and preserve workspace/draft context.

**Prerequisites:** WP-2 and WP-4. Live-only development may precede WP-7; acceptance of the
non-active-draft context requires WP-7.

**Exit:** Coverage works for two independent relation bindings and both directions, including large
ambiguous sets. Extend accessibility/visual scenarios to the new view and run affected-layer gates.
No mapping mutations are required to accept this slice.

#### WP-8B: Mapping actions — frontend

**Scope:**

1. Extend the accepted WP-8A renderer with generic mapping actions driven by its configuration.
2. Add a change-mapping action to each eligible source row and refresh coverage after a saved change.
3. Mapping action opens an inline or modal target selector with server-side candidate search. The
   selector shows cursor-paged target candidates and supports search, selection and clearing only
   where empty is valid. Keep mapping and draft aggregate tokens current without discarding the
   attempted choice; separately handle `mapping_version_conflict` and draft-version conflicts.
   Respect typed relation-attribute semantics from WP-5; a target-only edit must not clear attributes.
4. On save, call the mapping replacement endpoint with the current `mappingVersion`. Handle conflict
   (`409 mapping_version_conflict`) by showing the current mapping state and preserving the user's
   attempted choice for retry.
5. Support both live and draft contexts: the workspace context header controls which context is
   active, consistent with existing collection views.
6. Keyboard accessibility: the grid is navigable by keyboard; the candidate selector supports
   keyboard search and selection.
7. Exercise with two relation bindings that differ in type, direction and labels (per the product
   requirement in roadmap item 7).
8. Narrow-screen responsive behavior: the grid stacks or scrolls horizontally as appropriate.

**WP-5/WP-10B consumer handoff:**

- Preserve the attempted target and typed attributes on both conflict codes. A mapping conflict's
  returned state/version is for review; retry requires an explicit save with refreshed tokens.
- Conflict target continuation includes its own `applicationKey`/`viewKey`. Use those identities
  with the cursor, binding, anchor, returned mapping version and the same workspace/draft context,
  or start a fresh detail query under the user's selected view. Never reuse a cursor under a
  different view. If both returned view keys are null, omit them for binding-only name projection.
- Target-only saves omit relation attributes to retain existing values. Explicit `{}` requests
  replacement with an empty attribute set. Refresh the draft aggregate token after successful target
  creation/mapping writes and on aggregate conflict, without discarding unsaved choices.
- Draft activation can return mapping-set diagnostics under `version_conflict`; show the server's
  actionable message and anchor identity. A validation retry alone does not reconcile a divergent
  source/live set. Preserve the existing draft for review and guide explicit reapplication under
  a fresh current-live draft. No automatic overwrite, repinning or discard is permitted.
- US-M01 is completed by WP-8A coverage, US-M02/M03 by WP-8B save/conflict controls, and US-M04 by
  WP-8B contextual creation. WP-9 records composed browser/API acceptance for all four stories.

**Primary areas:** `frontend/src/features/objects/views/`, `frontend/src/features/objects/panels/`
(if mapping is also a panel type), `frontend/src/api/`, `frontend/src/types/model.ts`, tests.

**Prerequisites:** WP-8A and WP-5. Non-active-draft acceptance also depends on WP-7.
Extend accessibility/visual scenarios to candidate search, conflict recovery, clearing and target
creation. Target creation reuses generic fields, parent/ownership selection and validation under the
selected draft model, with refreshed draft tokens and no mapping change until explicit save.

**Decisions (resolved for this handoff):**

- **D9:** Mapping remains a full-page renderer for 0.7, but ADR-029 composes it as a lens of its
  source collection instead of a separate primary navigation destination. A detail-panel variant
  remains later work and is not needed for US-M01–M04 acceptance.
- **D10:** Contextual target creation uses `ui/Modal` and the generic create-object form. This keeps
  the mapping workspace/draft/view and unsaved choice available. On success, refresh candidates
  and the draft token; creating the object leaves the mapping unchanged until explicit save.


**Exit:** The mapping grid renders for two differently configured relation bindings. Mapped, unmapped
and ambiguous states are visually distinct. Replacement, clearing and conflict recovery work.
Candidate search returns results. Target creation in context is available where the model permits.
Keyboard navigation works. Two object types are exercised.

---

### Model-administration follow-up — after WP-7, before composed acceptance

#### WP-11: Historical release refusals, actionable API errors and draft UI consistency

**Status:** Delivered 2026-09-15. All eight scope items implemented and verified:
unsupported-schema diff/compile/activation refusals (422 with structured details), correlation-ID error boundary,
API client HTML/non-JSON hardening, Modal version-change dialog, supported-schema pinned-model loading,
shell-aligned workspace loading/error recovery, and historical-release informational state in the
model workbench. Final review exercised 155 affected backend tests and 55 focused frontend tests,
Ruff, format, lint and production build. A focused real-browser journey passed five interaction/layout
checks at 1440x900 and 390x844 with two compatible releases; comprehensive suites and gates remain WP-9.

**Implementation review (2026-09-15):** Consolidated the hardcoded supported-schema-version list
(`["0.5", "0.6"]`) from five independent locations (two routers, activation service, registry and
compiler) into a single canonical `SUPPORTED_SCHEMA_VERSIONS` frozenset in `compiler.py`, imported
by all backend consumers. Unsupported-schema responses now use the version actually found in stored
JSON and activation includes release/operation details even when persisted metadata disagrees. Removed
the false "previous state is unchanged" claim from the unexpected-error handler and separated concise
error logging from debug cause diagnostics. Non-retryable pinned-schema limitations no longer offer a
futile Retry. Visual inspection found the version dialog was not using form styles; the final dialog
uses the compact Modal form layout and passed the focused wide/narrow browser journey.

**Observed defect (2026-09-14):** Opening inactive release
`3a61b675-5674-4192-b9fb-7719b273c7aa` (content 0.5.0, schema 0.4) automatically requests a diff
against `d93e0114-6189-4b74-99c9-312b8f6671d5`. The compiler diagnoses an unsupported schema,
but the release-diff router converts all compilation failures into `500 invalid_installed_model`.
The browser displays only “An installed model release failed validation”. An unsupported installed
draft baseline has the same classification gap during model-draft compilation. These findings are
source-traced; the reported request has not been independently replayed against the development DB.

**Additional observed workspace error (2026-09-14):** Opening a data draft pinned to schema 0.5
shows “This draft's pinned model schema 0.5 is unsupported” outside the application layout, with
Retry and a plain Return to Live link. Source inspection confirms the loader checks equality with
the active model schema, rather than runtime support (the backend compiler supports 0.5 and 0.6).
The provider replaces `AppContent`, including its shell, with a bare wrapper on loading/refusal.
The reported Vite HTML has not been traced to a specific request; the shared API client does preserve
non-JSON error bodies as display messages, so HTML disclosure is a confirmed boundary weakness.

**Scope:**

1. Distinguish expected unsupported-schema refusals from corrupt installed JSON in release diff
   (both candidate and baseline), model-draft compilation baselines and activation. Use the existing
   structured error envelope and `422 unsupported_schema_version` for unsupported installed release
   operations. Include the affected release ID, schema version, supported versions, operation and
   actionable explanation. Preserve established pinned-workspace `409` contracts.
2. Keep historical release metadata and raw JSON inspection/export available. Show an informational
   unsupported-release state in the model workbench, explain why semantic comparison/activation is
   unavailable, and keep activation unavailable. Handle the structured API refusal even when browser
   metadata checks avoid an unnecessary diff request. Do not interpret old releases using the active
   model or introduce legacy schema parsers, migration or automatic repair.
3. Preserve truthful 5xx statuses for actual internal failures. Improve the shared unexpected-error
   boundary and model-administration internal-error messages with a safe operation-specific explanation,
   resulting service state when known, recovery guidance and a correlation identifier. Retain the
   underlying cause in controlled diagnostics linked by that identifier; normal logs and responses
   must remain concise and must not expose tracebacks or sensitive data. Never invent a cause or claim
   that a failed mutation left state unchanged unless the execution boundary establishes it.
4. Update API response documentation, examples and relevant generated contract inventory, frontend
   scenarios and delivery records to match the changed behavior. No domain-specific branches.
5. Correct the WP-7 workspace draft version-change UI using the existing `ui/Modal`, dialog form
   layout, typography, spacing, control styles and action hierarchy. Replace the unstyled inline
   `draft-version-change` block with the established dialog pattern; reuse the existing diagnostics
   component for compatibility refusals. Keep release labels consistent across creation and change
   dialogs, clearly distinguishing active and installed inactive releases. Preserve dirty-input
   protection, pending/error states and all existing version-selection behavior. This is UI integration
   work only: selection remains limited to installed immutable releases; direct mutable model-draft
   selection and model-preview workflows are outside this package.
6. Correct pinned-model loading and refresh support checks for workspace drafts and historical reads:
   differing from the active schema is not itself unsupported. Establish actual parser/renderer
   support, load the exact pinned model for supported releases, and keep genuinely unsupported or
   corrupt pins refused without substituting the active model. Cover both initial loading and the
   changed-pin refresh path introduced in WP-7; preserve draft/history data and active selection.
7. Keep workspace loading and failure states within the established application shell and styled
   content surface, preserving workspace/application context and usable navigation. Replace the bare
   wrapper and standalone Return to Live anchor with the existing notice/action patterns and guarded
   router navigation to the appropriate live destination. Show operation-specific explanations and
   distinguish transient retryable failures from limitations that Retry cannot resolve.
8. Harden the shared API response boundary against HTML/non-JSON error bodies and unexpected
   successful HTML responses. Never render document markup or framework pages as user-facing errors.
   Report the failed operation, safe recovery and available status/correlation information concisely;
   retain underlying response evidence only in controlled diagnostics. Trace the reported Vite page
   to its request before attributing a routing/proxy cause or changing deployment configuration.

**Primary areas:** `backend/app/routers/model_releases.py`,
`backend/app/routers/model_management.py`, `backend/app/errors.py`, the compiler's diagnostic
contract, `frontend/src/features/model-admin/ModelReleaseDetail.tsx`, API error consumers and
focused backend/frontend regression tests; `frontend/src/features/workspaces/WorkspaceDrafts.tsx`,
`frontend/src/ui/Modal.tsx`, `frontend/src/features/workspaces/WorkspaceDataContext.tsx`,
`frontend/src/app/App.tsx`, `frontend/src/api/client.ts`, shared notice/action components and existing
dialog/form styles (reuse before extending).

**Prerequisites:** WP-7 completed; existing immutable-release/compiler contracts. Deliver before WP-9.

**Acceptance criteria:**

- Open a workspace data draft, expand **More draft actions** and select **Change model version**:
  the action opens the established modal with **Target release**, **Cancel** and **Apply version
  change** controls. The dialog matches existing forms in font sizes, alignment, spacing and control
  sizing, without unstyled inline controls or a separate visual system.
- Inspect creation and version-change dialogs at normal and narrow widths, including pending and
  compatibility-error states. Verify keyboard operation, focus trap/restore and dirty-input protection;
  keep diagnostics readable and actions usable with two model configurations. Record focused visual
  and interaction evidence; comprehensive accessibility/visual runners remain WP-9 requirements.
- Open a schema 0.5 data draft while live uses supported schema 0.6: the exact pinned model loads,
  its fields/views remain authoritative, and the draft can be read/edited. Repeat supported-schema
  transitions on refresh and a pinned historical read. Unsupported/corrupt pins remain refused,
  preserving data and blocking writes; never fall back to the active model.
- Exercise initial loading, failed loading and retry from workspace draft navigation: application
  framing, workspace context, typography and action alignment match existing pages at normal/narrow
  widths. Return to Live uses guarded navigation and retains the correct workspace/application;
  transient retry recovers, while unsupported-version recovery is explained without a futile Retry loop.
- Focused shared-client and rendered-consumer regressions cover HTML 4xx/5xx responses, other non-JSON
  failures and unexpected HTTP 200 HTML. No raw markup, Vite document or JSON parsing traceback reaches
  the UI. Record the affected request if the development-page response is reproduced; do not claim
  a confirmed proxy diagnosis without evidence. Extend affected accessibility/visual scenarios for WP-9.
- Real HTTP regressions reproduce schema 0.4 on either diff participant and on an installed
  model-draft compilation baseline. Each expected refusal returns the documented structured 422,
  identifies the affected release and creates no internal-error log or traceback. Missing releases
  retain 404; supported comparisons remain successful; activation retains its unsupported-schema refusal.
- Corrupt supported-schema JSON remains distinct from unsupported schema, preserves diagnostics and
  produces an informative response with a traceable identifier for an actual internal failure.
- Exercise the shared unexpected-exception boundary through a real request: a safe response and concise
  log explain the failed operation and safe next step, with the same identifier in controlled cause
  diagnostics. Do not replace actual server failures with success responses or expected-refusal codes.
- Browser coverage shows the historical-release information state, successful JSON export and blocked
  activation, plus successful supported comparison. Exercise keyboard operation and semantics with two
  model configurations/object types; update affected accessibility scenarios and inspect changed surfaces.
- Refused read/compile/activation operations preserve immutable releases and active runtime selection.
  Focused API/consumer regressions, applicable contract checks, Ruff and frontend format/lint/build pass.
  Comprehensive suites and accessibility/visual gates remain owned by WP-9.

**Exit:** The reported expected limitation no longer generates HTTP 500, useful diagnostics reach the
user and operator, the workspace version-change controls match the existing UI patterns, and focused
evidence is recorded. This package does not claim production-wide
observability or release acceptance.

---

#### WP-12: Model release identity, technical details and comparison baseline

**Status:** Delivered 2026-09-24. Scope item 6's missing activation-history access was scoped as an
additive read-only `GET /api/v1/model-releases/{releaseId}/activations` over the existing
`activated`/`schema_upgraded` audit events; no existing hashing, identity, installation, activation
or API contract changed. WP-11's scope and correlation-ID behavior remain unchanged.

**Observed comparison defect (2026-09-14):** Release inspection compares every inactive selected
release against the globally active release, treating active as Before and selected as After. Thus
selected content 0.6.0/schema 0.5 shows removals relative to active content 0.7.0/schema 0.6. Active
release inspection skips the comparison entirely. This is a current-to-selected activation comparison,
not a view of what changed when the selected release was introduced; the UI does not explain that
purpose. Both behaviors are confirmed in `ModelReleaseDetail.tsx`.

**Scope:**

1. Keep model release name, version, schema and status prominent in the Models release details.
2. Move the canonical hash into an expandable **Technical details** area and display the release's
   public UUID there as **Release ID**. Provide copy actions for both values with accessible feedback.
3. Explain briefly: Release ID identifies an installed release for API/support use; the content hash
   verifies identical normalized model content across installations. These are inspection aids,
   not fields the user edits. Use existing styles and controls; do not change hashing, release
   identity, installation, activation or API contracts.
4. Make release inspection compare an earlier baseline (**Before**) to the selected release
   (**After**), including inspection of the currently active/latest release. Default to the recorded
   preceding active release for the selected release when that history is available. Where no such
   history exists, use a clearly labelled preceding installed release of the same model key, or an
   explicit baseline choice; do not imply installation order establishes activation history or infer
   ancestry from version strings. Read all required release pages rather than stopping at page one.
5. Show both compared releases and direction, and provide an explicit **Compare with** baseline
   selector using existing form styles. No predecessor means an explained first-release state;
   identical models mean a truthful no-semantic-changes state. If a schema 0.4 baseline is unsupported,
   use WP-11's actionable comparison refusal, retaining metadata/export; do not silently switch to a
   newer baseline, add legacy parsing or present a blank section.
6. Keep release-history comparison separate from activation compatibility: activation must still
   check the selected candidate against the current active model and live data. Label compatibility
   results by their comparison context, so a historical diff is never represented as activation
   readiness. Reuse the existing diff API's explicit baseline parameter; any missing activation-history
   access needed for the default must be identified and scoped before implementation.

**Primary areas:** `frontend/src/features/model-admin/ModelReleaseDetail.tsx`, existing disclosure,
clipboard and feedback patterns, release catalogue/activation-history reads, existing semantic-diff
API consumers, focused component tests and model-workbench documentation.

**Prerequisites:** WP-11 completed.

**Acceptance criteria:**

- Open **Models**, select an installed release and expand **Technical details**: the exact public
  release UUID and canonical hash are visible, explained and individually copyable.
- The default view prioritizes human-readable release information. Keyboard operation, copy success
  and clipboard failure feedback are usable; formatting, lint, build and focused tests pass.
- Inspect installed content 0.6.0 with 0.5.0 as predecessor, then latest/active 0.7.0 with 0.6.0
  as predecessor: Before/After run earlier to selected, and active inspection is not skipped.
  Unsupported predecessor schemas show the WP-11 refusal, rather than a backwards comparison or
  empty section. Cover first release, explicit baseline choice, later release pages and identical content.
- Activation checks remain current-active to candidate regardless of the inspection baseline;
  displayed compatibility clearly identifies its context. Correlation-ID handling remains unchanged.
- Inspect the changed surface at normal
  and narrow widths; comprehensive accessibility/visual gates remain WP-9 requirements.

**Exit:** Administrators can locate and copy both identifiers and understand their purpose without
technical metadata dominating the release page.

---

#### WP-13: Coverage, efficient test execution and UI acceptance

**Status:** Scheduled for Base 0.7; all three slices close before WP-9. This package changes the
validation system, not the product scope. Deliver sequentially with one implementation owner.

**Outcome:** A package runs a small, justified set of checks that protects its actual user behavior,
including refusals and recovery. Build acceptance retains comprehensive coverage. New UI is reviewed
in the existing application layout before delivery; test count is not a quality measure.

**Method:** Derive coverage from product invariants, public contracts, state transitions and user jobs,
then connect existing tests to that inventory. Do not derive the inventory from recent defects or the
current test-file structure. Reported defects are useful regression evidence, but they are not the
organising principle and do not receive special status once their contract is represented. Use
risk-based combinations rather than an exhaustive Cartesian product. Record unaudited areas and
residual risk explicitly. Newly found product defects need a bounded follow-up (WP-10 where applicable);
they do not silently expand this package. No target test count, arbitrary coverage percentage, new
testing platform or speculative abstraction.

**External basis:** Apply the established guidance that tests should exercise user-visible behavior
and avoid implementation details ([Playwright best practices](https://playwright.dev/docs/best-practices),
[Testing Library principles](https://testing-library.com/docs/)). Use pytest node IDs and explicit
markers for transparent selection ([pytest markers](https://docs.pytest.org/en/stable/example/markers.html)).
These sources guide mechanics; RDM's product contracts and risk assessment determine what must be tested.

##### WP-13A — Contract coverage and confirmed gaps

**Prerequisites:** WP-11 complete. Prefer delivery before further mapping UI implementation.

**Delivered 2026-09-24:** [coverage map](testing/COVERAGE_MAP.md) with 16 cross-cutting invariants
and 38 capability contracts, risk ranking and audit record. Filled gaps: mapping-write authority across
workspace contexts, draft relation update/delete set versions, a static starter-key guard, live date
values, and the mapping conflict retry's attempted target. One duplicated test was removed with its
surviving protection recorded. Two product defects were reproduced as strict `xfail` tests and scoped
as WP-10C and WP-10D. Focused evidence only; see the map's residual-risk section.

**Scope:**

1. Build a product contract inventory from `AGENTS.md`, acceptance scenarios, ADRs, the API and model
   contracts. For every capability record: user/consumer job, operation, authority/context, relevant
   state transition, input/state partitions, promised success/refusal/failure behavior, data effects
   and the lowest real boundary that can prove it. Include reads as well as mutations and include
   lifecycle, pagination, concurrency, startup/migration and generic model-driven behavior.
2. Inventory test files, fixtures and browser scenarios through collection/source inspection, without
   running full suites. Create `docs/testing/COVERAGE_MAP.md` linking each product contract to evidence,
   execution boundary, meaningful input/state partitions, missing evidence, audit status and cost tier.
   A line or branch coverage percentage is supporting diagnostic data, never proof of behavior.
3. Rank gaps using documented impact, likelihood, change frequency, boundary complexity and existing
   evidence. Audit the highest-risk contracts across normal, boundary, invalid, unavailable,
   conflicting and unexpected-dependency outcomes where applicable. Use equivalence partitions,
   boundary values and pairwise/risk-selected combinations; explain omissions instead of mechanically
   crossing every state with every endpoint. Distinguish expected refusals from internal errors and
   claim state preservation only where the transaction boundary proves it.
4. Fill confirmed gaps through real API requests or rendered consumers as appropriate. Reuse
   contract fixtures/helpers only where actual duplication supports them; assert status, machine code,
   actionable user response and relevant data effects. Keep pure validation tests database-independent.
5. Identify redundant coverage with explicit references. Consolidate only when distinct assertions
   remain protected; similarity or parameterization alone does not justify removing a case.
6. Remove a test only when it protects no product contract, duplicates evidence at equal or stronger
   boundary, or asserts an implementation detail with no user/contract value. Record the surviving
   protection and retain the deletion in normal code review.

**Acceptance:** Every documented 0.7 capability and cross-cutting product invariant is present in the
inventory. Highest-risk contracts have linked, meaningful evidence or named gaps; recent incidents map
to the same taxonomy as any other defect. Missing coverage is not labelled “covered”. Each consolidation
states where its distinct protection survives. Remaining audit work and its risk are explicit.

##### WP-13B — Affected-area commands and measured execution cost

**Prerequisites:** WP-13A.

**Delivered 2026-09-24:** [execution guide](testing/EXECUTION_GUIDE.md) with a fixed profiled selection,
nine pytest contract-group markers from one manifest (unclassified modules fail collection), `unit`
(node) and `dom` (jsdom) Vitest projects, a browser-runner classification check, boundary-to-check
expansion with worked traces and the WP-9 command set. A migrated template database replaces per-test
Alembic runs (sampled backend selection 46.75 s → 22.71 s, same 262 cases); pure frontend unit files
leave jsdom (1.48 s → 0.82 s). The order-dependent pagination test owns its database. Focused evidence
plus one full backend run justified by the shared `conftest.py` change.

**Scope:**

1. Profile a fixed representative selection of backend, frontend and browser checks once, recording
   commands, environment, case counts and elapsed time. Separate test cost from database/bootstrap,
   server/browser startup and fixture setup where measurable. Use existing timings for broader suites;
   record unavailable measurements rather than launching full suites just to populate a report.
2. Create `docs/testing/EXECUTION_GUIDE.md` and small runnable scripts/configuration only as needed.
   Give stable contract/risk groups explicit pytest markers, Vitest projects or maintained manifests;
   document exact node/file selections where grouping adds no value. Map changed production boundaries
   to their direct group and shared-boundary expansion rules, plus targeted failure reruns and the WP-9
   comprehensive command set. Keep selection transparent and detect unclassified new tests in CI or a
   cheap metadata check; do not promise perfect automatic impact detection.
3. Remove demonstrated repeated setup/duplicate execution in the sampled paths while preserving
   isolation, real request/transaction coverage and bootstrap/recovery tests. Backend pytest remains
   serial with the shared test database; parallelisation requires separate isolation work.
4. Measure changed commands against the same selection/environment. Record before/after timing and
   case counts, optimisations made and remaining bottlenecks in `docs/testing/EXECUTION_GUIDE.md`.

**Acceptance:** Each high-risk contract group has a working focused command and justified shared-layer
expansion. A representative change in each affected layer can be traced from changed boundary to selected
checks. Show the reduction in executed scope versus a blanket suite, and measured runtime/setup
improvements where achieved; do not invent a percentage target or claim unmeasured gains. No meaningful
cases are skipped to manufacture speed. Full suites run at WP-9, not per slice.

##### WP-13C — UI patterns, changed-state browser checks and visual review

**Prerequisites:** WP-13B; complete final scenario coverage after WP-8A/WP-8B and WP-12.
Establish the pattern/checklist first so those packages can use it during implementation.

**Delivered 2026-09-24:** [UI acceptance](testing/UI_ACCEPTANCE.md) names the reference pattern for
dialogs, fields, actions, page/load-failure/empty surfaces, notices, disclosures and narrow layout, and
holds the state inventory of 14 surfaces added or materially changed in 0.7 with the evidence for
each state (browser, component only, gap, or inapplicable with a reason). A new real-backend runner,
`e2e/wp13c-ui-states.mjs` (`test:browser:wp13c`), covers the user-critical states without browser
evidence: coverage/candidate/drafts-list outages with Retry, filtered-empty and no-match states,
conflict review keeping the attempted choice, the inverse binding in a named draft with live unchanged,
a draft pinned to a non-active release, keyboard focus, 390px layout and five scoped axe checks. All
12 screenshots were inspected against the references. Three product defects were found and scoped,
not fixed: WP-10F (contextual target creation) and WP-10G (two visual fixes). `AGENTS.md`, the
execution guide and the e2e README now require a named reference, a state-inventory row, focused
browser selection and separate functional/accessibility/visual reports for UI changes.

**Scope:**

1. Create `docs/testing/UI_ACCEPTANCE.md` with named existing 0.6 reference screens/components for
   dialogs, fields, actions, page/error surfaces and disclosures. Require reuse of their structure,
   styles and tokens. Introduce shared field/layout components only for demonstrated repeated gaps;
   do not redesign the application or create a second design system.
2. Inventory every user-visible surface added or materially changed in 0.7. For each, record exact
   navigation, reference pattern and applicable states: initial/loading, populated/empty, pending,
   success, invalid/refused, conflict, dependency failure, retry/recovery and narrow layout. Mark states
   inapplicable with a reason. Select focused browser checks for the user-critical states, using a real
   temporary backend where integration matters and two applicable model configurations/object types.
   Component tests cover isolated rules; they do not substitute for browser evidence of page context.
3. Verify shell/context retention, navigation, preserved input, error actions, keyboard/focus behavior
   and overflow. Inspect screenshots of changed surfaces at normal and narrow widths against the
   named reference. Accessibility checks and screenshot equality supplement design review; neither
   establishes that a layout is good. Review intentional baselines before acceptance.
4. Update `AGENTS.md`, the validation guide and package-completion guidance: exact user flow,
   affected failure boundaries, named UI reference, focused command selection and separate reports
   for functional, accessibility and visual evidence. An uninspected appearance remains unverified.

**Acceptance:** Every materially changed 0.7 surface has a completed state inventory. User-critical
workflows have runnable focused browser scenarios and reviewed changed-state screenshots selected by
risk, rather than by previously reported defects. New UI fits the established patterns and remains
usable at narrow widths/by keyboard. Missing browser prerequisites or incomplete inspection are reported
as limitations, not passes. Remaining visual product fixes are separately scoped.

**Package validation:** Run only affected checks for each slice, plus applicable Ruff or frontend
format/lint/build and documentation/link checks. Do not repeat passing gates without relevant changes.
Validate modified runners with their selected scenarios; comprehensive backend/frontend, accessibility
and visual gates remain WP-9. Do not run concurrent backend pytest processes.

**Exit:** Coverage map, runnable execution guide, runtime evidence and UI acceptance references are
implemented and used for the named areas. Residual risks have explicit follow-ups. WP-9 executes the
comprehensive command set once against the finished build; no slice claims release acceptance.

---

#### WP-14: Contextual collections and model-driven application browser

**Status:** Implemented and reviewed 2026-09-15; committed in `f8e39a8`. This package started from the
uncommitted WP-8A/WP-8B frontend implementation, preserved its mapping API and atomic-action work, and
replaced the original standalone-grid presentation with contextual collection composition.

**Outcome:** A steward navigates one arbitrary model-defined application browser, selects an unscoped
or direct-parent-scoped collection, and chooses among the configured semantic lenses for that source
type. Mapping coverage is a collection lens rather than an additional primary global table. The three
starter applications remain examples only.

**WP-14A — Decision and design documentation**

1. Record ADR-029's context/collection/lens/query/detail terminology and schema 0.5/0.6 compatibility.
2. Reconcile `PRODUCT.md`, `UI_MODEL.md`, `ARCHITECTURE.md`, `APPLICATION_MODEL.md`, roadmap, stories
   and acceptance documentation. Do not claim runtime delivery from this slice.
3. Preserve 0.8 ownership of lazy arbitrary-depth hierarchy traversal and mutation. Do not add a new
   schema version without a demonstrated composition ambiguity.

**WP-14B — Bounded contextual mapping queries**

1. Extend mapping coverage with optional `parentObjectId` and `state=mapped|unmapped|ambiguous`.
   Parent scope selects direct children of the configured source type. Both values participate in
   cursor fingerprints and work identically in live and draft projections.
2. Filter before pagination so every returned page and continuation satisfies the selected state;
   never client-filter a page or calculate state after an incompatible page boundary.
3. Return explicit validation for an unknown, cross-workspace, wrong-context or incompatible parent;
   an empty valid scope is a successful empty page.
4. Update API/OpenAPI contracts and focused integration coverage for all states, scope/state changes,
   stale cursor rejection and both directions.

**WP-14C — Unified application browser and collection lenses**

1. Remove the mutually exclusive Browse hierarchy/Views switch. Present virtual collection groups and
   bounded runtime containment records in one application browser. A flat application still exposes
   its collections.
2. Derive a view's source type generically. Group all views for that source type and render their
   configured names as lenses inside one collection workspace. Do not add starter-key branches.
3. Selecting a compatible child collection from a runtime parent opens it with visible
   `parentObjectId` scope. Scope, search and compatible query state are URL-backed and retained through
   detail/return and lens navigation; scoped collection reads work correctly in Live, Draft and
   History contexts.
4. Replace the single hidden table-filter entry point with visible model-labelled facet triggers and
   applied values. Mapping adds a visible coverage-state facet. Use existing semantic controls and
   responsive wrapping; no second design system.
5. Correct the WP-8 baseline: configured `name` is rendered once, conflict recovery presents the
   returned current mapping for review before explicit retry, candidate/target context remains bounded,
   target-only replacement preserves relation attributes and historical contexts expose no mutations.

**WP-14D — Review, focused acceptance and documentation reconciliation**

1. Review the complete WP-8/WP-14 diff against ADR-029, mapping concurrency, model-context and generic
   renderer invariants. Resolve confirmed defects before final gates.
2. Exercise one contained and one flat/mixed model configuration, two mapping bindings/directions,
   unscoped and parent-scoped collections, all coverage states, detail return, Live/Draft/History,
   keyboard operation and narrow layout. Component evidence does not replace the real API/browser path.
3. Run affected backend tests and Ruff; frontend focused tests, format, lint and build; public contract
   checks and `git diff --check`. WP-9 still owns comprehensive suites, accessibility/visual gates and
   release acceptance.
4. Update current status, roadmap, TODO, API/model/UI documentation and changelog only to the behavior
   actually exercised. Record remaining 0.8 hierarchy and later explicit model-composition work.

**Primary areas:** `backend/app/routers/mapping.py`, `backend/app/services/mapping.py`, mapping/OpenAPI
tests, `frontend/src/app/AppShell.tsx`, `features/objects/Explorer.tsx`, collection view host/renderers,
routing/query state, styles, focused component/browser tests and product/architecture documentation.

**Prerequisites:** WP-4/WP-5/WP-7/WP-10A/WP-10B/WP-11 delivered; the existing WP-8A/WP-8B dirty-tree
implementation is the preserved starting point.

**Exit:** The application browser no longer separates hierarchy from views; mapping does not add a
duplicate primary destination; visible scope and semantic facets issue bounded server-side queries;
existing schema 0.5/0.6 models remain usable; and focused evidence covers generic contained, flat and
mapping configurations. WP-9 remains pending until its comprehensive gate runs.

**Delivery evidence (2026-09-15):** 39 focused backend mapping/OpenAPI tests and 95 focused frontend
tests pass. Ruff, frontend format, lint (zero errors, 12 configured warnings) and production build
pass. A six-check real-backend/browser journey includes both configured directions, wide/narrow
screenshots and an axe check of the composed mapping lens. This evidence does not replace WP-9
comprehensive suites or visual-baseline acceptance.

---

### Tier 5 — Composed validation (depends on all above)

#### WP-9: Composed product validation — SC-07 and SC-15

**Scope:**

1. Extend the starter dataset with the mapping and version-selection test data specified in the
   acceptance scenarios.
2. Execute SC-07 (mapping coverage, replacement, conflict, ambiguous resolution, target creation in
   context, two relation bindings) as composed browser + API evidence.
3. Execute SC-15 (draft version selection, two drafts on different releases, activation of the
   prepared draft after the new release becomes active, discard of the remaining draft, refusal of
   unavailable, corrupt and unsupported releases) as composed browser + API evidence. Use two
   content releases on the same schema with visibly different fields, rules and views, and verify
   incompatible creation/version change leaves all other contexts untouched.
4. Verify cross-cutting concerns: keyboard navigation, narrow-screen layout, empty/error/retry
   states, dirty-input preservation and workspace context retention across all mapping and version-
   selection flows.
5. Own comprehensive build acceptance: run the full backend pytest and frontend test suites once
   after implementation packages are complete, plus backend Ruff, frontend lint + format + build,
   extended accessibility and visual-regression scenarios, and `git diff --check`. Reuse unchanged
   passing static checks and focused migration/bootstrap evidence. Execute composed scenarios here;
   rerun failures and affected boundaries after fixes, expanding to full-suite reruns only for broad
   impact or unexplained failures. Focused package evidence does not replace the full build suites.
6. Update `PROJECT_STATUS.md`, `ROADMAP.md`, `TODO.md`, `CHANGELOG.md` and this plan with delivery
   evidence and any remaining gaps.

7. Add an independent allowed binding fixture beyond the two opposite-direction starter views of
   one binding. Demonstrate independent versions and unchanged unrelated bindings, candidates beyond
   page one, large ambiguous target sets and typed relation attributes. Include generic-write versus
   mapping races, draft aggregate conflicts and live mapping changes before draft activation,
   including changes to a different edge in the same touched set. Untouched live work must survive.
8. Include WP-11 composed browser/API evidence for unsupported historical release inspection/export,
   truthful diff/compile refusals and actionable internal-error diagnostics.
9. Use WP-13’s coverage map and execution guide, exercise its final workflow scenarios and record
   residual gaps. Do not substitute a passing case count for contract or visual acceptance.
10. Missing foundation behavior activates WP-10; do not treat a failing integration check as evidence
   that frozen implementation has already been reviewed or silently waive the release criterion.

**Primary areas:** test data, e2e tests, documentation.

**Prerequisites:** WP-1–WP-7, WP-8A, WP-8B, WP-11, WP-12, WP-13A/B/C and WP-14; any triggered WP-10 slices must close before
release acceptance.

**Decisions needed:** None.

**Exit:** SC-07 and SC-15 pass with recorded evidence. The full validation matrix is green. All
documentation reflects the delivered state. Any gaps or simplifications are explicitly stated.

**Delivered 2026-09-25.** Evidence, then gaps.

*Acceptance data.* No starter dataset exists outside the browser harness, so the SC-07/SC-15 data is
`e2e/helpers/acceptance-data.mjs`, seeded through the real API: `Collection`, `Home delivery`, `Parcel
locker` and 24 fillers (so candidates exist beyond page one); `PICKUP` unmapped, `HOME` mapped to a
different target, `MULTI` ambiguous across 25 targets (beyond the 20-item preview). It also defines an
independent binding, `qa-master-aligns-to-system` (master value → system value, own labels, an integer
`qa-confidence` relation attribute, **Master alignment** lens). The SC-15 releases are the active one,
a same-schema candidate with a new `Priority` field (rule 1–5) in a renamed **Prioritised values** view, and
an incompatible one that makes `External ID` required. `bootHarness({ transformModel })` starts from a variant.

*SC-07 — `test:browser:sc07` (9 checks, 4 axe scans with 0 violations, 1440/390px).* Keyboard-only search
for “Collection” maps `PICKUP`; a candidate first listed on page two replaces `HOME`'s different target;
`MULTI`'s exact count (25), bounded preview and continuation show every target, and resolving it to an
existing target keeps that edge's relation ID. A generic `POST /relations` racing the dialog's save yields
the conflict review with the current targets and the attempted choice kept; nothing changes until the
reviewed retry. The independent binding appears as a third lens; resolving it keeps the retained edge's
ID and integer attribute (`7`), and neither binding's writes change the other. The inverse starter lens
reads the same edges from the master side. In a draft, a live edge added to the draft's touched set
refuses activation (409 with anchor diagnostics) while the draft, the live set and unrelated live work
survive; after that edge is withdrawn, activation publishes the draft and keeps the unrelated live
change. WP-13C's evidence is reused, not repeated: outages and Retry, cancelled contextual creation,
contextual creation in both directions and the draft-context inverse lens.

*SC-15 — `test:browser:sc15` (8 checks, 4 axe scans with 0 violations, 1440/390px) and
`test_build07_wp9_acceptance.py`.* In the browser, draft1 is created on the active release and draft2 on the
installed candidate. Creation on the incompatible release is refused with the records that do not fit;
the typed name stays, and no draft is left. draft2 shows the candidate's view name and `Priority` column;
draft1 and live do not. The draft2 form applies the 1–5 rule (9 is not sent and stays in the field) and
stores the integer 3 in draft2 only. An incompatible version change of draft1 (browser) and an
unavailable release (API) are refused, and a JSON snapshot of the runtime selection, the live record,
history and the Warehouse workspace's records and drafts is unchanged. draft2 cannot activate until the
administrator activates the candidate; live then follows the new view without data changes, and draft2
publishes through validate/activate. draft1 is refused with the mismatch explanation and discarded with no
data change. The backend test repeats the journey through HTTP, adding **corrupt** and **unsupported**
installed releases (`pinned_model_invalid`, `unsupported_pinned_model_schema`) for creation and version
change against the same untouched-state snapshot. It uses a private database because it activates a release.

*Cross-cutting.* Keyboard: the full SC-07 unmapped flow, conflict and version dialogs (WP-11/WP-13C focus
trap and restore). Narrow: SC-07 lens/dialog, SC-15 refused creation and mismatch notice at 390px with no
horizontal scroll. Empty/error/retry: WP-13C. Dirty input: attempted mapping choice after conflict, draft
name after refused creation, out-of-range field value, version-change discard prompt (WP-11). Context
retention: workspace/draft context in every URL above; scope and lens retention by `test:browser:wp14`.

*Build acceptance (one run after implementation).* Backend: Ruff clean; `pytest` **534 passed**, no
xfails. Frontend: format check, lint (0 errors, 11 existing warnings), `tsc -b && vite build`, Vitest
**36 files / 231 tests**, gate helpers 5/5. Browser: `test:browser`, `:authoring`, `:drafts`, `:history`,
`:wp11`, `:wp12`, `:wp14`, `:wp13c`, `:sc07`, `:sc15` all pass. `test:a11y` passes (no unexpected
violations, light and dark). `test:visual` passes 13 baselines after the reviewed update below. The
startup smoke against a copy of the development database served health, runtime state, the 0.7.0/0.6
model and records. `git diff --check` is clean. Migration code did not change; the focused WP-10E
migration/bootstrap evidence is reused.

*Failures found and fixed during the gate.*

- `test:browser:wp12` and `test:browser:wp13c` failed on the committed source too. Both were test races:
  copy feedback was read before the clipboard promise settled, and focus was read in the same frame the
  dialog unmounted. Both now wait for the outcome (focus restore is still required within 2s).
- `test_wp81b_current_live_bases::test_current_live_source_captures_unpublished_graph_and_stays_frozen`
  failed once in a group run: it read the first draft base in the shared test database, not its own.
  It is now scoped to its workspace and object.
- `test:visual` flagged `model-workbench-dark` (0.72%): both Models baselines predated WP-12's Technical
  details and Release history. The new screenshots were reviewed against the delivered WP-12 layout, and
  only those two baselines were replaced.
- The SC-07 runner's own early failures were debounce races. It now waits for the exact search
  response before choosing, and passed four consecutive runs.

*Decision taken after WP-9 (user, 2026-09-25).* The coverage map asked for a decision on built-in
timestamps in drafts before 0.7 acceptance. Investigation showed it was wider than filters. Draft and
history responses filled `createdAt`/`updatedAt` with the request time, timestamp filters silently
matched nothing, and timestamp sorts fell back to ID order. The user chose to report timestamps as not
recorded (WP-10K). Recording real timestamps in drafts and history is on the roadmap, unscheduled.

*Re-verification after WP-10K (2026-09-25).* WP-10K landed after the gate and changed the shared
collection renderer in draft and history contexts, so the gate was repeated on `138c268`: Ruff clean,
`pytest` **535 passed**, lint 0 errors (11 existing warnings), `format:check`, build, Vitest **36 files /
235 tests**, gate helpers, all ten browser runners, `test:a11y` (16 checks, no unexpected violations)
and `test:visual` (13 baselines match). No defects found; an unreachable `eq` branch in the draft/history
object filter was removed.

*Residual gaps (not release blockers, recorded for later work).*

- Activation and compatibility diagnostics identify records by UUID (for example the mapping-set
  anchor and the record missing `External ID`). WP-10G fixed release identities only. Naming records
  needs a diagnostic contract addition.
- PostgreSQL concurrency is not exercised; all race evidence is on SQLite.
- The candidate's server-side rule in a draft is proven by `test_build07_wp6`; the browser run shows
  the form-level constraint, which prevents the request.
- Moving draft1 onto the new release was not repeated here. `test:browser:wp11` and
  `test_build07_wp6` cover compatible version change.
- `history-view-light` drifts 0.20% (under the 0.5% threshold). Inspected on 2026-09-25: the
  difference is only the generated revision UUID, publication time and release UUID; layout matches.

---

#### WP-10: Conditional 0.7 foundation hardening

**Status:** WP-10A and WP-10B delivered after WP-4/WP-5 review (2026-09-14). WP-10C and WP-10D,
triggered by the WP-13A audit, were delivered on 2026-09-24. WP-10E (found while validating WP-10C)
and WP-10F/WP-10G (found by WP-13C) were delivered on 2026-09-25, as were WP-10H/I/J (found by WP-9)
and WP-10K (the decision WP-9 surfaced). No further slice is open.

**WP-10A — Cascade-deletion relation-set participation:** HTTP reproduction in both live and
current-live draft contexts: deleting a mapped system value reduced incoming coverage from 21
edges to 20 while `mappingVersion` stayed at 21 (live) or 0 (draft). The previous target continuation
returned 200. This violates ADR-022 set-version maintenance and WP-4's required refresh after set
changes. Ownership is bounded to `services/deletion.py`, the incident-relation tombstone loop in
`services/workspace_revisions.py`, and mapping HTTP regression tests. No schema extension is needed.
Acceptance: confirmed cascades increment both exact directional sets for each removed edge atomically;
preview/refused/stale deletes leave tokens unchanged; old target continuations return
`409 mapping_version_conflict` with refresh guidance; unrelated bindings and the other live/draft
context remain unchanged.

Validation: all 20 focused mapping/cascade tests and the final 401-test backend suite passed on SQLite;
Ruff and diff whitespace checks passed. Independent patch review found no further issues. The API
contract and frontend are unchanged by this fix; composed WP-9 acceptance remains separate.

**WP-10B — Mapping-set conflicts during draft activation (delivered 2026-09-14):**
HTTP regression in both directions confirms that a draft clears an existing mapping, a generic live
write adds a different edge in that same set, and activation incorrectly returns 200. Per-relation
comparison misses the new identity. This slice owns the activation merge in
`services/workspace_revisions.py` and HTTP regressions in `tests/test_mapping_replacement.py`.
No schema extension is required: use the draft's immutable source graph and the exact directional
sets already marked by WP-3. Before applying the draft, compare complete relation identities and
versions in each touched mutable, non-ownership binding set with current live data. Containment
continues to use its existing object/graph merge rules. A divergence returns `409 version_conflict`
with bounded binding/anchor/direction diagnostics and recovery instructions, preserving the draft,
all live rows and the active revision. Check newly mapped sets, both directions, new/deleted/updated
live edges, independent bindings and unrelated live work. A changed live set whose complete current
state and relation versions match the source again is not a divergent graph under this check.

**WP-10C — Typed values in draft writes (triggered by WP-13A; delivered 2026-09-24):** HTTP reproduction:
creating a record with a `date` field inside a draft returns `500 internal_error`. The draft write
path stores the typed output of `validate_attributes` (a Python `date`) in the JSON
`workspace_draft_objects.attributes` column, which cannot serialize it. Live writes and current-live
capture of dated records are correct. Affected contract: typed attribute values (AGENTS.md invariant)
and operator-facing errors. Ownership: attribute normalization for draft rows in
`services/workspace_revisions.py` (`_normalize_object_attributes` and its create, update and
attribute-endpoint callers). No schema change. Acceptance: draft create, update and field writes of
`date` values succeed and read back in ISO form; invalid dates remain `422 invalid_attribute_value`;
the same holds for `dateTime` and `decimal` bindings (use a test model, since the starter has neither);
activation publishes the values to live typed columns. Regression: remove the strict `xfail` from
`test_typed_table_queries.py::test_date_values_keep_their_type_through_write_filter_and_sort[draft]`.

*Delivered:* draft rows store the JSON form that current-live capture already copies from live rows
(`attributes.stored_json_value`); `save_attribute_values` converts each value to its declared type
before writing typed columns, so activation of new and captured values works. Validation found two
more parts of the same contract, which are included: in-memory draft and revision list filters
compared typed filter values with stored strings (500 for dates), and their sort key ordered numbers
as text (`10` before `5`) and date-times by local wall clock. Filters now compare declared types, a
zone-less `dateTime` filter is read as UTC, and `pagination.sequence_sort_text` gives numbers and
instants an order-preserving cursor text. A draft or revision cursor issued before this change may
continue in the old order once; restarting the list fixes it.

**WP-10D — Containment edge on based draft edits (triggered by WP-13A; delivered 2026-09-24):** HTTP
reproduction: in a current-live (or revision-derived) draft, renaming a contained record (a codelist
under a domain) adds a second containment edge with a new relation ID; activation then refuses with
`409 version_conflict` / `duplicate_edge`. Moving it to another parent keeps the old base edge as
well, and activation refuses with `422 relation_cardinality_violation`. Root records, the field
sub-resource and deletion are unaffected. Cause: `_sync_draft_parent_relation` tombstones only
draft-local containment rows, never the edge inherited from the draft base, and recreates the edge
even when the parent is unchanged. Affected contracts: atomic containment (ADR-006), stable public
IDs, SC-06 publication. Ownership: `_sync_draft_parent_relation` in `services/workspace_revisions.py`.
Acceptance: an unchanged parent keeps the effective edge and its identity; a parent change tombstones
the effective (base or draft) edge and creates exactly one new edge; activation succeeds for rename
and move; set versions for affected containment sets follow ADR-022. Regression: remove the strict
`xfail` from `test_wp81b_current_live_bases.py::test_editing_a_based_child_keeps_its_one_containment_edge_and_activates`
and add a move case.

*Delivered:* `_sync_draft_parent_relation` compares the requested parent with the *effective* (base or
draft) containment edge. An unchanged parent keeps the edge and its identity. A changed parent
tombstones the effective edge — a base edge through a draft tombstone row, as deletion does — and adds
exactly one new edge. As in live updates, containment edits do not advance relation-set versions;
mapping views cannot address containment bindings.

**WP-10E — Live `dateTime` values lose their offset (found validating WP-10C, 2026-09-24; delivered 2026-09-25):**
HTTP reproduction: a live write of `2026-12-24T18:00:00+01:00` reads back as `2026-12-24T18:00:00`.
SQLite does not keep the zone despite `DateTime(timezone=True)`, and clients read a zone-less value
as UTC, so the stored instant moves by the offset. Draft rows keep the offset until activation, which
then loses it. Live `decimal` reads are also padded to the column scale (`12.5000000000`) while draft
writes return the submitted form, so draft uniqueness compares unequal strings for equal decimals.
Affected contract: typed attribute values. Ownership: `services/attributes.py` value storage and
reads. Acceptance: store instants in UTC and return them with an explicit offset in every context;
decide whether existing live `dateTime` values need a migration (the starter model has no `dateTime`
field; check deployed models first); give decimals one canonical form across contexts. Regression:
remove the strict `xfail` from `test_typed_table_queries.py::test_live_datetime_keeps_its_instant`.

*Delivered:* every timestamp column uses `UTCDateTime` (`models/database.py`), which converts to UTC
on write and attaches UTC on read. SQLite then keeps the instant, and every response carries an
explicit offset: attribute `dateTime` values and all server timestamps, which removes the frontend's
zone-less workaround. `normalize_value` stores a `dateTime` as its UTC instant (zone-less means UTC,
as in filters) and a `decimal` in `canonical_decimal` form. `stored_json_value` returns the same forms
for live reads, so live, draft and revision values are equal strings for equal values. The column type
does not change the DDL; the head-versus-metadata migration test passes. **Migration decision:** none.
No local development database holds a live `dateTime` value; the starter model has none; and an offset
already dropped cannot be recovered. Existing server timestamps were written as UTC and read back
unchanged. Regression: the strict `xfail` is removed. The live test also asserts the canonical forms
and offset-aware filtering, and a new test asserts that object, draft and history timestamps carry an
offset. WP-10C's draft test now expects `12.5` for `12.50` and exact equality after activation.

**WP-10F — Contextual target creation uses the lens's application (found by WP-13C, 2026-09-24;
delivered 2026-09-25):** Browser reproduction (`wp13c-ui-states.mjs`, starter model): in the System → Master lens of
`rdm-systems`, **Create new master value** offers a Codelist parent, and its lookup fails with
“Object type 'codelist' is not available in application 'rdm-systems'”; no master value exists in
that application to serve as the other permitted parent, so the target cannot be created. In the
Master ← System lens of `rdm-master`, a system value cannot be created because `rdm-master` does not
contain that type. Cause: `MappingActionDialog` passes the view's `applicationKey` to the generic
`ObjectFormDialog`, while objects belong to exactly one application and candidates are read across
applications. The refusal is contained (message shown, unsaved choice kept). Affected contract: US-M04
contextual creation “where the model permits”. Needs a decision on the owning application of a target
created in context (for example the target type's application that contains the permitted parents,
or a choice among the applications containing the type), then a real-API and browser regression that
creates, selects and saves the target in both configured directions.

*Decision (user, 2026-09-25):* always ask. *Delivered:* `MappingActionDialog` passes every
application that contains the target type to `ObjectFormDialog` as `applicationChoices`, defaulting
to the lens's application when it contains the type. The form shows an **Application** choice, or a
fixed fact when only one application qualifies. Because a parent must share the record's application
(`parent_wrong_scope`), the form offers only parent types the chosen application contains. When a
required parent has no type there, it explains that and disables **Create**. No model change. Evidence:
two component tests, and `test:browser:wp13c` creating a master value in RDM Master from the RDM Systems
lens (live) and a system value in RDM Systems from the RDM Master lens (named draft). Each run checks
that the new target is selected, saved as the mapping and placed in the chosen application under the
chosen parent, and that a draft-created value does not reach live.

**WP-10G — Visual fixes from WP-13C screenshot review (2026-09-24; delivered 2026-09-25):** (1) At ≤ 720px the mapping
dialog's candidate search stretches to ~170–500px high: `styles/responsive.css` gives every
`.search-box` `flex: 1 1 100%`, which becomes a height basis in the dialog's column form. (2) The draft
model-mismatch notice names the active model by raw release UUID instead of key and version, contrary
to WP-12's human-readable release identity. Acceptance: reviewed narrow and wide screenshots of both
surfaces; rerun `test:browser:wp13c`.

*Delivered:* `.dialog form .candidate-search` sets `flex: none`. The workspace data context resolves
the active release's key and version when it differs from the pinned one, so the draft mismatch
notice reads "the active model rdm-starter 0.7.0". The historical-revision banner had the same raw-ID
defect and now names both releases by key and version. `test:browser:wp13c` asserts the narrow search
height (≤ 48px) and the mismatch text without a UUID. Wide and narrow screenshots were inspected.

**WP-10H — Removal offered for a required mapping (found by WP-9; delivered 2026-09-25):** SC-07 says
clearing is offered only where an empty mapping is allowed. The server refuses to clear a `required`
binding (`422 required_relation`), but the mapping dialog offered **Remove mapping** whenever a row had a
target. Ownership: `MappingActionDialog`. *Delivered:* the dialog offers removal only when the binding is
not required and otherwise says a replacement is needed. Two component cases (outgoing and incoming
views of a required binding); the unchanged optional case keeps its removal test.

**WP-10I — Draft refusal messages (found by WP-9; delivered 2026-09-25):** Creating a draft on an
incompatible release showed only the summary, while a version change listed the records that do not
fit; and a server message without a full stop ran into the guidance (“…live active data The draft is
preserved”). Ownership: `CreateDraft` and `DraftActions`. *Delivered:* creation shows the same
diagnostics list; joined messages end the server sentence first. Component regressions and
`test:browser:sc15` cover both.

**WP-10J — Field names in attribute errors (found by WP-9; delivered 2026-09-25):**
`missing_required_attributes` and `read_only_attributes` messages were Python list literals of keys
(“Required attributes missing: ['external-id']”), shown to users in forms and draft diagnostics. Ownership:
`services/attributes.validate_attributes`. *Delivered:* messages name the model fields (“Required fields
are missing: External ID”); keys move to `details.attributeTypeKeys`. Codes are unchanged. Live and
draft-graph regressions assert both.

**WP-10K — Timestamps not recorded in drafts and history (decision after WP-9; delivered 2026-09-25):**
Draft, draft-base and revision rows have no timestamp columns. Object and relation responses in those
contexts invented `createdAt`/`updatedAt` as the request time. Timestamp filters excluded every record
without an error, and timestamp sorts had no effect. Only models whose views declare these fields
expose them in the browser; the starter has none. *Decision (user):* say “not recorded” now and put
recorded timestamps on the roadmap without a release. *Delivered:* `ObjectResponse` and
`RelationResponse` timestamps are nullable (the OpenAPI lock was re-baselined, and the diff showed only
those four fields). Draft and revision responses return `null`. Filters and sorts on them are refused
with `422 invalid_filter`/`invalid_sort` naming the field, while live responses and queries are
unchanged. The collection view neither offers nor sends these fields in a draft or history, and a view
whose default sort is a timestamp sorts by name there; an unrecorded column shows “—”. No migration.
Evidence: `test_wp8_history` snapshot parity (live has timestamps; revision and draft objects and
relations return null and refuse both queries), `test_query_foundations` live/draft sort traversal,
`test_typed_table_queries` draft refusals, `CollectionView.test.tsx` (live, draft ×2 object types,
history), and `test:browser:drafts`, `:history` and `:sc15`.

**WP-5 acceptance follow-up (delivered 2026-09-14):** Add independent-binding isolation in live/draft
contexts, required-ownership rejection, forbidden clearing, and overlapping real HTTP generic
create/update/delete versus replacement. Verify error codes, graph preservation, directional tokens
and relation identity. Do not equate sequential stale-token checks with concurrent-write evidence.

**Delivery and handoff:** Implement WP-5 tests, then WP-10B merge refusal, reconcile ADR-022 request
names and document binding-only continuation in WP-8B. Run focused regression tests and one final
backend Ruff/full-pytest and frontend format/lint/test/build gate for the changed public error
contract. Existing unrelated worktree edits and review notes remain intact. WP-8A/WP-8B continue
as independently deliverable UI packages; WP-9 owns their composed US-M01–M04/SC-07 acceptance.

**WP-5/WP-10B final validation (2026-09-14):** 486 backend tests passed, including 73
replacement/activation cases; Ruff passed. Frontend format, lint (zero errors, 12 existing warnings),
164 tests and production build passed. Two frontend diagnostics cases verify the recovery message and
anchor identity. The preceding independent WP-10B review identified a missing
restored-source-graph case; that HTTP regression now passes in both directions and is included in
the final backend gate. Diff whitespace checks passed. PostgreSQL concurrency and composed mapping
browser journeys were not exercised. No migration or production UI structure changed, so additional
migration smoke, accessibility and visual-baseline gates were not required for this follow-up.

**Trigger:** WP-4/WP-5/WP-9 integration evidence identifies a missing WP-1/WP-2/WP-3 capability
needed for SC-07/SC-15. Before editing, record the reproduced failure, affected contract, bounded
ownership and acceptance criteria as a WP-10 slice. Do not reopen frozen scopes or duplicate their
pending reviews. A required schema extension is a separately named model-contract slice; otherwise
prefer the existing contract and later-package API configuration.

**Scope:** Correct only established gaps, for example relation-set read consistency, directional
maintenance or draft activation conflict protection. Preserve unrelated bindings, live work,
stable identities and explicit refusals. Add regression coverage at the real integration boundary;
startup/migration corrections also require the applicable recovery and smoke gates.

**Exit:** The reproduced failure is fixed and its relevant gates pass. Required slices block 0.7
acceptance and WP-9 is rerun for affected scenarios. If no trigger occurs, record “not required”; this
package is not speculative implementation work.

## Dependency graph

```
WP-1 (UI-07)                          — independent
WP-2 (Schema 0.6)                    — independent
WP-3 (Relation-set versions)         — independent

WP-4 (Mapping coverage API)          — depends on WP-2, WP-3
WP-5 (Mapping replacement API)       — depends on WP-2, WP-3, WP-4 response-contract freeze

WP-6 (Draft version selection BE)    — independent (WP-2 recommended)
WP-7 (Draft version selection FE)    — depends on WP-6

WP-8A (Read-only mapping grid)        — depends on WP-2, WP-4
WP-8B (Mapping actions)              — depends on WP-8A, WP-5
                                     — non-active-draft acceptance of both requires WP-7
WP-10 (Conditional hardening)        — triggered by integration evidence; blocks acceptance if needed

WP-11 (Release refusals/errors)      — delivered 2026-09-15; required before WP-9
WP-12 (Release identity UI)          — scheduled after WP-11; required before WP-9

WP-13A/B (Coverage/execution)        — after WP-11 (delivered); prefer before mapping UI delivery
WP-13C (UI acceptance)              — establish patterns early; close after WP-8A/WP-8B, WP-12

WP-9 (Composed validation)           — depends on all
```

Parallelizable tracks:

- **Track 1 (mapping):** WP-2 → WP-3 → WP-4 + WP-5 → WP-8A → WP-8B
- **Track 2 (draft version and release follow-up):** WP-6 → WP-7 → WP-11 → WP-12
- **Track 3 (accessibility):** WP-1 (any time)
- **Validation improvement:** WP-11 → WP-13A → WP-13B → WP-13C (final coverage after mapping/WP-12)
- **Final:** WP-9

WP-1, WP-2, WP-3 and WP-6 have no cross-dependencies and can proceed in any order.

## Open decisions summary

| ID | Question | Recommendation | Blocking |
| --- | --- | --- | --- |
| D1 | Candidate search fields: view-declared or derived from target type? | Explicit in view config | WP-2 ✓ |
| D2 | Schema 0.5 → 0.6 CLI transition path? | New model file sufficient pre-production | WP-2 ✓ |
| D3 | Set-version row lifecycle: eager or lazy? | Lazy, implicit version 0 for untouched sets | WP-3 ✓ |
| D4 | Activation merge strategy for set versions? | Add draft mutation count to live version, then delete draft rows | WP-3 ✓ |
| D5 | Coverage endpoint: new router or extend relations? | New dedicated mapping router | WP-4 |
| D6 | HTTP method for mapping replacement? | PUT (idempotent set replacement) | WP-5 |
| D7 | Replacement target count? | One target; separate direction-aware cardinality checks | WP-5 |
| D8 | Creation/version-change compatibility? | Complete effective graph must already fit; atomic refusal | WP-6 |
| D9 | Mapping as view only, or also as panel? | Full-page collection lens only for 0.7 | WP-8B/WP-14 |
| D10 | Target creation: modal or navigation? | Modal (preserves context) | WP-8B |
| D11 | View configuration for mapping reads? | Required application/view identity; binding must match | WP-4 |
| D12 | Ambiguous target response bounds? | Exact count, 20-item preview, version-bound continuation | WP-4/WP-5 |
| D13 | Relation identity and attribute omission? | Retain selected edge; omission preserves retained values | WP-5 |

## Starter model changes

The starter model advances from schema 0.5 / content 0.6.0 to schema 0.6 / content 0.7.0:

- Schema version changes from `"0.5"` to `"0.6"`.
- At least one `mappingGrid` view is added for the `system-value-maps-to-master` relation binding in
  the Systems application (outgoing from System Value to Master Value).
- The delivered second mapping view uses the reverse direction of the same binding. WP-9 adds a
  separate test-model binding with different labels to prove binding independence; WP-2 is frozen.
- Existing table views are retained unchanged.

## Schema transition

Schema 0.6 is a strict superset of 0.5. A schema 0.5 model is valid schema 0.6 (no `mappingGrid`
views, which are optional). The compiler supports both `"0.5"` and `"0.6"` as active runtime schemas.
Immutable schema 0.4 releases remain stored and listable but cannot be activated (existing behavior).

Pre-production, the transition from a 0.5 database to 0.6 is: install the new schema 0.6 model and
activate it. No data migration is needed because `mappingGrid` is a view type, not a data contract.
The `relation_set_versions` table is added by Alembic migration and starts empty; untouched sets
have implicit version 0.

## Risk and scope notes

- **WP-8 is split into WP-8A and WP-8B** so coverage and actions have separate acceptance gates.
- **WP-6 is invariant-heavy despite the existing pin column.** Whole-candidate compatibility,
  snapshot consistency, atomic version changes and isolation are its main risks.
- **WP-3 activation behavior is frozen.** Later integration evidence must verify same-set conflicts
  and preservation of unrelated live work; confirmed missing behavior belongs to conditional WP-10.
