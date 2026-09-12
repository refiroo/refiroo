# Base 0.7 implementation plan

**Status:** Planning. Not started.

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

## Work packages

Each work package is scoped for one LLM coding session. Dependencies between packages are stated
explicitly; independent packages may be implemented in any order within their tier.

### Tier 0 — Foundation (no 0.7 dependencies)

#### WP-1: UI-07 — Automated accessibility and visual-regression gates

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

---

### Tier 1 — Schema and persistence (no cross-tier dependencies)

#### WP-2: Schema 0.6 model language — `mappingGrid` view contract

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

---

#### WP-3: Relation-set version persistence and generic participation

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

---

### Tier 2 — Mapping API (depends on WP-2 and WP-3)

#### WP-4: Mapping coverage API

**Scope:**

1. Add a mapping coverage query endpoint:
   `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage?relationTypeKey=...&fromObjectTypeKey=...&toObjectTypeKey=...&direction=...`
   with cursor pagination (`pageSize`, `cursor`), optional search on source name/attributes.
2. The response returns batched rows: each row contains the source object identity and display fields,
   the current mapping state (`mapped` | `unmapped` | `ambiguous`), the current target(s) with
   display fields, and the current `mappingVersion` (relation-set version) for that source.
3. The query resolves against the view's configured relation binding and counts outgoing (or incoming,
   per direction) edges per source object. Zero edges = unmapped, one = mapped, more than one =
   ambiguous.
4. Support `workspaceDraftId` query parameter for draft-context coverage.
5. Add server-side candidate search:
   `GET /api/v1/workspaces/{workspaceKey}/mapping-candidates?objectTypeKey=...&search=...`
   returning candidate target objects for mapping, with cursor pagination. Candidates are objects of
   the target type in the same workspace, searched by name and configured searchable attributes.
6. Both endpoints validate the relation binding against the active model (or draft-pinned model) and
   return `404` for unknown bindings.

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
pagination and invalid-binding rejection.

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
3. Transaction: conditionally claim the relation-set version; delete all existing edges for the exact
   binding and anchor; if target is non-null, create the new edge; increment the set version; commit.
4. A null target with empty attributes removes the mapping (all edges for that binding and source).
5. A non-null target replaces the complete set with exactly that target.
6. Stale version claim returns `409 mapping_version_conflict` with current version and bounded
   current-target summaries; nothing changes.
7. Requesting the already-current target with identical attributes is an idempotent no-op: no version
   increment, no audit event.
8. Record one mapping-transition audit event with old/new target and relation identities.
9. Live and draft contexts are both supported. Draft writes claim `expectedWorkspaceDraftVersion` in
   addition to `expectedMappingVersion`.

**Primary areas:** `backend/app/routers/mapping.py`, `backend/app/services/mapping.py`,
`backend/app/models/api.py`, `backend/app/services/audit.py`, tests.

**Prerequisites:** WP-3 (relation-set versions), WP-2 (model validation of mapping bindings).

**Decisions needed:**

- **D6: HTTP method for mapping replacement.** ADR-022 describes a replacement operation on a
  complete set. `PUT` is semantically correct (idempotent replacement of the complete mapping set for
  one source). _Recommendation:_ `PUT` on a resource identified by the binding + source.
- **D7: Cardinality enforcement.** For `many-to-many` bindings, replacement sets exactly one target.
  For `one-to-one` and `one-to-many` bindings, the single-target constraint is already enforced.
  Should `many-to-many` mapping replacement be limited to one target per operation, or should it
  accept a list? _Recommendation:_ one target per operation for 0.7; a multi-target variant can be
  added in 0.9 bulk operations if needed. This keeps the conflict model simple.

**Exit:** Mapping replacement creates, replaces and removes mappings atomically. Concurrent
replacement conflicts with the current version. Idempotent re-save does not increment the version.
Audit records the transition. Draft and live contexts both work. Two different relation bindings are
exercised. Invalid bindings, containment and required-ownership are rejected.

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
   release. The base is a data snapshot, not a model snapshot.
8. Compatibility check: when moving a draft to a new release, run the existing model compatibility
   analysis against the draft's candidate content. If incompatible, refuse with structured
   diagnostics; do not attempt conversion.

**Primary areas:** `backend/app/services/workspaces.py`, `backend/app/services/model/runtime.py`,
`backend/app/routers/workspaces.py`, `backend/app/models/api.py`, tests.

**Prerequisites:** None for the backend logic (the database column exists). However, if schema 0.6 is
the motivating use case, WP-2 should be complete so a schema 0.6 release can be installed for
testing.

**Decisions needed:**

- **D8: Content compatibility when changing a draft's version.** When a draft moves from release A to
  release B, what content is checked? _Recommendation:_ check the draft's authored candidate content
  (draft objects, attributes, relations) against the target model. If the target model removes an
  object type, attribute type or relation type that the draft uses, refuse. If the target adds new
  required fields, refuse (the draft has not provided them). This is a strict "content must already
  fit" check, not a conversion.

**Exit:** A draft can be created against any installed, supported release. Draft reads, writes and
validation use the draft's pinned model. A draft on a non-active release cannot activate. Moving a
draft to a release its content satisfies succeeds; moving to an incompatible release is refused with
diagnostics. Discarding is always available. Tests cover: draft on active release (existing behavior),
draft on non-active release, activation refusal, version change, incompatible version change refusal,
discard, and two drafts on different releases in the same workspace.

---

#### WP-7: ADR-028 draft version selection — frontend

**Scope:**

1. Draft creation dialog: add an optional model-release selector. The default is the currently active
   release. Available releases come from the installed-releases list endpoint. Historical-source
   creation retains the source revision's pinned release.
2. Draft list and detail: display which model release each draft works under. Distinguish "active
   version" from "preparing for version X" visually.
3. Draft detail banner: when a draft's version differs from the active release, show an informational
   banner explaining the state ("This draft is preparing for [version]. It can be activated once that
   version is active.").
4. Activation refusal: when a draft's version does not match the active release, the activate button
   is disabled with a tooltip/explanation. The existing `workspace_draft_model_release_conflict`
   error handling is retained as a server-side safety net.
5. Version change: add a "Change model version" action on draft detail. It shows available installed
   releases and attempts the change. Success updates the draft's model context; failure shows the
   incompatibility diagnostics. The 0.10 conversion option is not offered.
6. Discard: always available, never requires model agreement. No change to existing discard flow.
7. The mapping grid and table views resolve their column/filter/sort configuration from the draft's
   pinned model, not the global active model.

**Primary areas:** `frontend/src/features/workspaces/`, `frontend/src/features/objects/`,
`frontend/src/api/`, `frontend/src/types/`, tests.

**Prerequisites:** WP-6 (backend version selection).

**Decisions needed:** None — the UX follows directly from the acceptance criteria in US-W09 and SC-15.

**Exit:** A steward can create a draft against a non-active release, see which version it uses,
attempt activation (refused with explanation), change its version (where content fits), and discard
it freely. Two drafts on different releases coexist without interference. Tests cover the creation
selector, version display, activation refusal and discard paths.

---

### Tier 4 — Mapping frontend (depends on WP-2, WP-4, WP-5)

#### WP-8: Mapping grid view — frontend

**Scope:**

1. Add a `mappingGrid` view renderer in the view registry. The renderer receives its configuration
   from the schema 0.6 model and renders a cursor-paged grid of source objects with their mapping
   state.
2. Each row shows: source object display fields (configured columns), mapping state indicator
   (mapped/unmapped/ambiguous), current target display fields, and an action to change the mapping.
3. Mapping action opens an inline or modal target selector with server-side candidate search. The
   selector shows target candidates and supports search, selection and clearing.
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

**Prerequisites:** WP-2 (schema 0.6 model with mapping-grid config), WP-4 (coverage API), WP-5
(replacement API).

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
   unsupported releases) as composed browser + API evidence.
4. Verify cross-cutting concerns: keyboard navigation, narrow-screen layout, empty/error/retry
   states, dirty-input preservation and workspace context retention across all mapping and version-
   selection flows.
5. Run the full validation matrix: backend Ruff + pytest, frontend lint + format + test + build,
   migration/bootstrap checks, accessibility and visual-regression gates (WP-1), and
   `git diff --check`.
6. Update `PROJECT_STATUS.md`, `ROADMAP.md`, `TODO.md`, `CHANGELOG.md` and this plan with delivery
   evidence and any remaining gaps.

**Primary areas:** test data, e2e tests, documentation.

**Prerequisites:** All other work packages.

**Decisions needed:** None.

**Exit:** SC-07 and SC-15 pass with recorded evidence. The full validation matrix is green. All
documentation reflects the delivered state. Any gaps or simplifications are explicitly stated.

---

## Dependency graph

```
WP-1 (UI-07)                          — independent
WP-2 (Schema 0.6)                    — independent
WP-3 (Relation-set versions)         — independent

WP-4 (Mapping coverage API)          — depends on WP-2, WP-3
WP-5 (Mapping replacement API)       — depends on WP-2, WP-3

WP-6 (Draft version selection BE)    — independent (WP-2 recommended)
WP-7 (Draft version selection FE)    — depends on WP-6

WP-8 (Mapping grid frontend)         — depends on WP-2, WP-4, WP-5

WP-9 (Composed validation)           — depends on all
```

Parallelizable tracks:

- **Track 1 (mapping):** WP-2 → WP-3 → WP-4 + WP-5 → WP-8
- **Track 2 (draft version):** WP-6 → WP-7
- **Track 3 (accessibility):** WP-1 (any time)
- **Final:** WP-9

WP-1, WP-2, WP-3 and WP-6 have no cross-dependencies and can proceed in any order.

## Open decisions summary

| ID | Question | Recommendation | Blocking |
| --- | --- | --- | --- |
| D1 | Candidate search fields: view-declared or derived from target type? | Explicit in view config | WP-2 |
| D2 | Schema 0.5 → 0.6 CLI transition path? | New model file sufficient pre-production | WP-2 |
| D3 | Set-version row lifecycle: eager or lazy? | Lazy with version 0 (ADR-022) | WP-3 |
| D4 | Activation merge strategy for set versions? | Same touched-record conflict as records | WP-3 |
| D5 | Coverage endpoint: new router or extend relations? | New dedicated mapping router | WP-4 |
| D6 | HTTP method for mapping replacement? | PUT (idempotent set replacement) | WP-5 |
| D7 | Many-to-many: one target per operation or a list? | One target for 0.7 | WP-5 |
| D8 | Content compatibility check when changing draft version? | Strict "must already fit" | WP-6 |
| D9 | Mapping as view only, or also as panel? | View only for 0.7 | WP-8 |
| D10 | Target creation: modal or navigation? | Modal (preserves context) | WP-8 |

## Starter model changes

The starter model advances from schema 0.5 / content 0.6.0 to schema 0.6 / content 0.7.0:

- Schema version changes from `"0.5"` to `"0.6"`.
- At least one `mappingGrid` view is added for the `system-value-maps-to-master` relation binding in
  the Systems application (outgoing from System Value to Master Value).
- A second mapping view exercises a different relation binding with different direction and labels to
  prove the contract is generic.
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

- **WP-8 (mapping frontend) is the largest single package.** It introduces a new view type, a target
  selector with search, conflict UI and target creation in context. If it proves too large for one
  session, it can be split into: (a) read-only mapping grid with coverage display, and (b) mapping
  actions (replacement, conflict, target creation). The split boundary is clean because the coverage
  API (WP-4) and replacement API (WP-5) are independent endpoints.
- **WP-6 (draft version selection backend)** is lower risk because the `model_release_id` column
  already exists on `WorkspaceDraft`. The main work is changing how draft-scoped operations resolve
  their model context and adding the version-change endpoint with compatibility checks.
- **Set-version integration into activation** (part of WP-3) requires careful design to ensure
  draft set versions merge correctly with live versions during delta-merge activation. This is the
  most novel concurrency concern in 0.7.
