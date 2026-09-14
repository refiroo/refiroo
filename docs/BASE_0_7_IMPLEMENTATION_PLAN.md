# Base 0.7 implementation plan

**Status:** In progress. WP-1, WP-2 and WP-3 delivered; their implementation review is pending and
separate from this plan review. WP-1–WP-3 scopes are frozen.

**Target:** Product 0.7.0, schema language 0.6. The starter model content advances to a version on
schema 0.6; that number alone does not mean the product release is accepted.

**Depends on:** Base 0.6 released (2026-09-11); retained generic CRUD, typed tables, workspace
lifecycle, optional drafts, immutable history, delta-merge activation and the frontend redesign.

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
  routes.ts, CollectionView.tsx and ObjectToolbar.tsx. The view registry dispatches `mappingGrid` to a
  styled placeholder renderer; the full mapping grid UI ships in WP-8.
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

**Decisions needed:**

- **D5: Coverage endpoint location.** Should this be a new `/mapping-coverage` router or an extension
  of the existing workspace/relations API? _Recommendation:_ new dedicated router
  (`backend/app/routers/mapping.py`) — the mapping coverage query is a distinct business view, not a
  generic relation list.

**Exit:** Coverage returns correct mapped/unmapped/ambiguous states with set versions. Candidate
search returns bounded, searchable results. Both endpoints page correctly and validate against the
model. Draft context returns draft-scoped coverage and versions. Tests cover all three mapping states,
pagination and invalid-binding rejection. Include multiple views over one binding, candidates beyond
page one, large ambiguous sets, mismatched cursors and concurrent coverage reads. These are WP-4
integration checks, not amendments to WP-2/WP-3.

---

#### WP-5: Atomic mapping replacement API

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

**Decisions needed:**

- **D6: HTTP method for mapping replacement.** ADR-022 describes a replacement operation on a
  complete set. `PUT` is semantically correct (idempotent replacement of the complete mapping set for
  one source). _Recommendation:_ `PUT` on a resource identified by the binding + source.
- **D7: Cardinality enforcement.** For `many-to-many` bindings, replacement sets exactly one target.
  Underlying cardinality constraints are checked separately and depend on direction.
  Should `many-to-many` mapping replacement be limited to one target per operation, or should it
  accept a list? _Recommendation:_ one target per operation for 0.7; a multi-target variant can be
  added in 0.9 bulk operations if needed. This keeps the conflict model simple.

**Exit:** Mapping replacement creates, replaces and removes mappings atomically. Concurrent
replacement conflicts with the current version. Idempotent re-save does not increment the version.
Audit records the transition. Draft and live contexts both work. Two different relation bindings are
exercised. Invalid bindings, containment and required-ownership are rejected. Test retained relation
identity during ambiguous resolution, omitted/empty/typed attributes, both directions, constrained
candidate targets, rejected clearing, generic-write versus replacement races and both draft tokens.

---

### Tier 3 — Draft version selection (depends on Tier 1)

#### WP-6: ADR-028 draft version selection — backend

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

#### WP-7: ADR-028 draft version selection — frontend

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

**Primary areas:** `frontend/src/features/objects/views/`, `frontend/src/features/objects/panels/`
(if mapping is also a panel type), `frontend/src/api/`, `frontend/src/types/model.ts`, tests.

**Prerequisites:** WP-8A and WP-5. Non-active-draft acceptance also depends on WP-7.
Extend accessibility/visual scenarios to candidate search, conflict recovery, clearing and target
creation. Target creation reuses generic fields, parent/ownership selection and validation under the
selected draft model, with refreshed draft tokens and no mapping change until explicit save.

**Decisions needed:**

- **D9: Mapping as view only, or also as panel?** The roadmap specifies a mapping _view_ (full-page
  grid). Should mapping also be available as a _panel_ on an object's detail page (showing "this
  object's mappings for binding X")? _Recommendation:_ view only for 0.7. A panel variant can be
  added later without API changes, as the coverage and replacement endpoints accept any valid
  binding. Adding both in one session risks scope creep.
- **D10: Target creation in context (US-M04).** The story requires creating a missing target while
  mapping. The existing record-creation flow can be reused. _Decision:_ should target creation open
  in a modal (preserving the mapping grid context) or navigate to the standard creation page (losing
  grid context)? _Recommendation:_ modal, to satisfy the "do not abandon the task" acceptance
  criterion. The modal reuses the generic create-object form. On success, the new target appears in
  candidates but is not automatically selected as the mapping target (per the requirement: "creating
  a target does not silently change the mapping").

**Exit:** The mapping grid renders for two differently configured relation bindings. Mapped, unmapped
and ambiguous states are visually distinct. Replacement, clearing and conflict recovery work.
Candidate search returns results. Target creation in context is available where the model permits.
Keyboard navigation works. Two object types are exercised.

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
5. Run the full validation matrix: backend Ruff + pytest, frontend lint + format + test + build,
   migration/bootstrap checks, extended accessibility and visual-regression scenarios, and
   `git diff --check`. Reuse passing final package gates when relevant code has not changed; run
   composed scenarios here and rerun other gates only for relevant changes or unexplained failures.
6. Update `PROJECT_STATUS.md`, `ROADMAP.md`, `TODO.md`, `CHANGELOG.md` and this plan with delivery
   evidence and any remaining gaps.

7. Add an independent allowed binding fixture beyond the two opposite-direction starter views of
   one binding. Demonstrate independent versions and unchanged unrelated bindings, candidates beyond
   page one, large ambiguous target sets and typed relation attributes. Include generic-write versus
   mapping races, draft aggregate conflicts and live mapping changes before draft activation,
   including changes to a different edge in the same touched set. Untouched live work must survive.
8. Missing foundation behavior activates WP-10; do not treat a failing integration check as evidence
   that frozen implementation has already been reviewed or silently waive the release criterion.

**Primary areas:** test data, e2e tests, documentation.

**Prerequisites:** WP-1–WP-7, WP-8A and WP-8B; any triggered WP-10 slices must close before
release acceptance.

**Decisions needed:** None.

**Exit:** SC-07 and SC-15 pass with recorded evidence. The full validation matrix is green. All
documentation reflects the delivered state. Any gaps or simplifications are explicitly stated.

---

#### WP-10: Conditional 0.7 foundation hardening

**Status:** WP-10A delivered after WP-4 implementation review (2026-09-14). Other slices remain conditional.

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

WP-9 (Composed validation)           — depends on all
```

Parallelizable tracks:

- **Track 1 (mapping):** WP-2 → WP-3 → WP-4 + WP-5 → WP-8A → WP-8B
- **Track 2 (draft version):** WP-6 → WP-7
- **Track 3 (accessibility):** WP-1 (any time)
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
| D9 | Mapping as view only, or also as panel? | View only for 0.7 | WP-8B |
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
