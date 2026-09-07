# Base 0.6 implementation plan

**Status:** Replanned; WP0-WP3 complete, the delivered WP4 object-lifecycle design is rejected and
must be replaced by WP5-WP8 before WP9 release validation

**Target:** Product release 0.6.0

**Scope:** Versioned daily operations

**Depends on:** Completed Base 0.5 operational and model-lifecycle foundation

**Unlocks:** Schema 0.6 mapping, then translation, hierarchy and integration workflows

## Product outcome

A data steward can select a known workspace, create or open a complete workspace draft, edit its
objects and relations coherently, validate it as one dataset and atomically activate it as an
immutable workspace revision. A later workspace draft may derive from the active or any historical
workspace revision. Published workspace revisions are read-only, and retiring publication affects
the workspace revision as a whole rather than assigning independent lifecycle states to every object.

Base 0.6 establishes the lifecycle and interaction foundation on which specialist workspaces depend.
Mapping-grid configuration, mapping APIs and model-workbench redesign are outside this release so the
workspace-revision migration and daily-operation journeys can be completed as one bounded change.

## Release principles

1. Design and test complete tasks, not isolated components.
2. Keep workspace content revisions, application-model releases and record-level draft concurrency distinct.
3. Keep the engine generic: runtime and UI code never branch on starter keys.
4. The workspace revision is the publication authority; active object and relation projections are
   transactionally derived from it.
5. Every collection is bounded, every write is concurrency-aware and every error is machine-readable.
6. A declared view type has a typed contract and an honest renderer.
7. Product and schema-language versions are independent.

## Scope

### Included

- Task-based interaction specification and acceptance fixtures
- RDM-owned accessible UI foundation and application-shell improvements
- Authoritative workspace catalogue, discovery and selection
- Strict schema 0.5 `table` views
- Typed, model-aware daily-use table filtering and sorting
- Stable object identities inside mutable workspace drafts and immutable workspace revisions
- Root workspace drafts, history-derived workspace drafts, activation and explicit retirement
- Visible derivation and supersession lineage
- Migration from Base 0.5 data and the rejected WP4 object-revision schema to authoritative
  workspace-revision storage
- Browser journey, accessibility, visual, migration and package validation

### Deferred

- `mappingGrid` schema and renderer, mapping query/mutation APIs and ADR-022 implementation
- Model-workbench information-architecture redesign
- Bulk object or relation mutation
- Translation matrix and hierarchy tree
- Import/export jobs, change feeds and webhooks
- Authentication, authorization and multi-node publication
- Automatic workspace-draft rebasing across model releases and executable runtime-data migrations
- Physical purge of published workspace history
- Structured model designer and extension packaging

## Accepted decisions

- **D1 / ADR-019:** Workspaces are global database records with immutable keys, mutable labels,
  active/retired state and one atomically selected active default. Mutation routes use
  `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, enabled by default until authentication exists; it is not
  authorization.
- **D2 / ADR-024 (supersedes ADR-020):** A stable workspace owns mutable content drafts and immutable
  active/retired workspace revisions. Objects and relations are records within that aggregate and do
  not have independent publication lifecycles. Derivation and activation supersession are separate
  workspace-history edges.
- **D3 / ADR-021:** Schema 0.5 provides a strict `table` contract and explicit version dispatch. Schema
  0.4 remains stored/listable/exportable but cannot run. This pre-production transition uses
  reset/rebootstrap or an offline one-shot transition rather than a runtime compatibility adapter.
- **D4 / ADR-022:** Atomic mapping replacement and exact-binding relation-set versions remain accepted,
  amended to operate inside an explicit workspace draft; implementation moves with `mappingGrid` to
  schema 0.6 and the next product release.
- **D5 / ADR-023:** React Aria Components supplies difficult interaction behavior behind RDM-owned
  wrappers and plain CSS. Lucide is available only through the RDM icon wrapper.

## Fixed API and persistence contracts

### Workspace administration

- `GET /api/v1/workspaces?search=...&status=active|retired|all&pageSize=...&cursor=...` is
  cursor-paged and searchable; status defaults to `active`.
- `GET /api/v1/workspaces/{workspaceKey}` returns active or retired detail.
- `POST /api/v1/workspaces` creates a record; `PATCH /api/v1/workspaces/{workspaceKey}` changes label
  or status with `expectedVersion`; there is no delete or rename.
- `GET` and `PATCH /api/v1/workspace-runtime-state` read and atomically change
  `defaultWorkspaceKey`; PATCH uses the singleton state's expected version.
- Runtime capabilities expose `workspaceAdmin.manageWorkspaces`. This reflects the deployment flag,
  not the caller's identity.
- Unknown explicit keys return `404 workspace_not_found`; retired scopes reject runtime mutations with
  `409 workspace_retired`. Retired detail and history remain readable.

### Table query semantics

- A schema 0.5 table declaration contains `objectTypeKey` plus a configuration with unique non-empty
  `columns`, `filterFields`, `sortFields`, `defaultSort` and bounded `pageSize`.
- Queries use `filter.<field>.<operator>=<typed lexical value>`. Different filters combine with AND;
  repeated equality values for one field combine with OR.
- Text supports `eq`, `contains`, `startsWith`, `isNull` and attribute `isUnset`. Number/date/datetime
  supports `eq`, range operators, `isNull` and attribute `isUnset`. Boolean supports `eq`, `isNull`
  and attribute `isUnset`. JSON is excluded.
- Equality is case-sensitive; `contains` and `startsWith` are case-insensitive. Dates and datetimes use
  ISO 8601; `isNull` and `isUnset` take booleans. Null and unset remain distinct.
- `sort=<field>` or `sort=-<field>` selects one declared sort. Sorts place null/unset last in both
  directions and append a hidden unique tie-breaker. Cursors bind
  normalized filters and sort. Attribute features determine API capability; the view declares the
  UI-visible subset.

### Workspace content revisions

- A workspace owns zero or one active content revision and any number of mutable workspace drafts and
  immutable historical revisions. This content lifecycle is distinct from the catalogue's
  administrative active/retired status and from application-model releases.
- Each workspace draft/revision pins `modelReleaseId`. Activation against a different currently
  resolved model release returns `409 workspace_draft_model_release_conflict`; rebasing is explicit
  future work.
- A root workspace draft starts empty. A derived workspace draft uses copy-on-write storage over one
  selected immutable workspace revision. `derivedFromRevisionId` records the source;
  `supersedesRevisionId` records the revision active at activation.
- Object IDs remain stable public identifiers across workspace revisions. Object core fields,
  parents, typed attributes, required ownership relations and independent relations belong to the
  workspace-draft/revision snapshot. They have no independent `draft`, `active` or `retired` state.
- Active object and relation APIs resolve only the workspace's active revision. Draft editing APIs
  require `workspaceDraftId`; historical reads require `workspaceRevisionId`. No mutation route may
  silently target the active projection.
- `GET/POST /api/v1/workspaces/{workspaceKey}/drafts` lists or creates workspace drafts.
  `GET/PATCH/DELETE /api/v1/workspace-drafts/{draftId}` reads, names or discards a draft with
  optimistic concurrency.
- Draft-scoped object and relation collections remain cursor-paged under
  `/api/v1/workspace-drafts/{draftId}/...`; record writes carry both the workspace-draft version and a
  record version so unrelated editors receive explicit conflicts without inventing record lifecycle.
- `POST /api/v1/workspace-drafts/{draftId}/validation` validates the complete effective object graph
  without publication. `POST /api/v1/workspace-drafts/{draftId}/activation` requires
  `expectedDraftVersion` and `expectedActiveRevisionId` and publishes every changed object, attribute,
  containment edge and relation atomically.
- `GET /api/v1/workspaces/{workspaceKey}/revisions` and
  `GET /api/v1/workspace-revisions/{revisionId}` expose immutable history and bounded snapshot reads.
- `POST /api/v1/workspaces/{workspaceKey}/retirement` retires the active workspace content revision
  under `expectedActiveRevisionId`. It does not retire or delete individual objects. Catalogue
  retirement remains a separate administrative operation and cannot conceal an unreviewed content
  mutation.
- Discard removes only a mutable workspace draft. Published workspace identity, revisions, stable
  object IDs and audit history are retained; purge is outside Base 0.6.

## Acceptance journeys

Use representative data from at least two object types and two ownership/containment configurations.

1. Select a non-default workspace, move between applications and return without losing URL context.
2. Find an object with configured attribute filters and sort, open it and return to the same list state.
3. Create a root workspace draft, add objects with typed attributes and required relationships, then
   validate and activate the workspace once.
4. Derive a workspace draft from the active revision, edit several related records, and verify active
   reads remain unchanged until one atomic activation.
5. Derive a workspace draft from an earlier retired workspace revision and distinguish its source from
   the revision it supersedes on activation.
6. Retire workspace publication without deleting object identity or history, derive a new draft from
   history and reactivate the workspace through one activation.
7. Recover from workspace-draft, record, active-revision, uniqueness and pinned-model conflicts without
   losing local input or partially publishing the dataset.

## Work packages

### WP0 — Freeze interaction behavior

Completed for the original object-lifecycle proposal, but its lifecycle portions are superseded by
the workspace-level correction in WP5. Workspace selection, typed-table, responsive, keyboard and
action-hierarchy findings remain useful; object-draft/revision journeys and fixtures are not
authoritative for WP6-WP9.

Primary areas: `docs/UI_MODEL.md`, focused interaction notes/fixtures under `docs/`, and frontend test
fixtures.

1. Walk the seven journeys against Base 0.5 and record task failures and unnecessary context switches.
2. Specify information architecture for product, application, view, workspace, logical object, draft
   and revision context.
3. Produce low-fidelity states for collection, complete draft editing, history, retirement, conflicts
   and empty/error/loading cases.
4. Define responsive behavior, keyboard order, focus return, readable density and action hierarchy.
5. Create representative fixtures for two object types and active- and retired-derived histories.

Historical exit: the original specification was independently reviewed. Its lifecycle acceptance was
replaced by completed WP5 under ADR-024; D1 and D3-D5 remain resolved, and D2 is the correction.

### WP1 — Build the UI foundation and shell (complete)

Primary areas: `frontend/package.json`, `frontend/eslint.config.js`, `frontend/src/ui/`,
`frontend/src/styles/`, `frontend/src/app/AppShell.tsx` and their tests.

1. Add reviewed, locked React Aria Components and Lucide dependencies.
2. Enforce that feature modules import only RDM wrappers; direct primitive/icon imports are lint errors.
3. Establish CSS tokens and semantic wrappers for composite selections, menus, notices, dialogs and
   tabs while retaining native HTML for simple controls.
4. Preserve busy and dirty-form dismissal guards, accessible names, focus behavior and semantic HTML.
5. Clarify application, view, workspace and object context in desktop and narrow layouts.

Exit: the shell, workspace selector, one table and one draft workflow use the boundary; keyboard and
narrow-layout tests pass; no starter key determines presentation.

### WP2 — Implement workspace authority and selection (complete)

Primary areas: database models and Alembic, a focused workspace service/router and API models,
capability/configuration handling, frontend API/types, shell selector and tests.

1. Add workspace catalogue and singleton runtime-state persistence through Alembic.
2. Backfill `default` plus every distinct existing object workspace before adding references.
3. Implement the fixed workspace endpoints, paging/search/status semantics, optimistic updates and
   capability response.
4. Default `WORKSPACE_ADMIN_MUTATIONS_ENABLED` to true and document the pre-authentication risk.
5. Replace free text with a searchable selector, retain keys in URLs and label retired records.
6. Test unknown, retired, default-switch and concurrent-update behavior.

Exit: workspace resolution is catalogue-backed and deterministic; the default cannot be retired;
retired scopes are readable but not mutable; no route implicitly provisions or deletes a workspace.

### WP3 — Deliver schema 0.5 typed tables (complete)

Primary areas: model schema/compiler/validation, object query and pagination services, frontend model
types and table view, starter/synthetic models, OpenAPI locks and tests.

1. Implement explicit schema-version dispatch and the strict table contract; reject extra properties
   and unimplemented view types with precise JSON paths.
2. Implement the fixed typed filter and sort grammar in shared query/pagination services.
3. Preserve URL state and filter-bound opaque cursors in the generic table renderer.
4. Migrate the starter to content release 0.6.0/schema 0.5: represent its current tree as a table and
   omit its mapping view until schema 0.6 rather than labelling a generic table as a mapping task.
5. Keep schema 0.4 releases listable/exportable while rejecting activation and selected runtime use;
   test reset/rebootstrap and the offline transition development paths.
6. Add `python -m app.cli.model_schema_upgrade --model <path>` as the no-traffic transition path. It
   validates, installs, compatibility-checks and concurrency-switches to schema 0.5 without first
   resolving the selected schema 0.4 model; failure leaves runtime state unchanged.

Exit: two object types use configured typed fields; null/unset, case, range, invalid-value and cursor
semantics are covered; schema-version failures are explicit; no `mappingGrid` contract is implied.

### WP4 — Make object revisions authoritative (delivered, rejected and to be removed)

Primary areas: database models and Alembic, object/revision API models, focused draft/snapshot/
activation/retirement services and routers, attribute/containment/relation/audit integration and tests.

1. Add stable object, draft, immutable revision, active-pointer and projection persistence.
2. Migrate each Base 0.5 active/draft/retired object without changing its public object ID; stop on
   unknown states with values and counts.
3. Centralize snapshot validation for attributes, containment, ownership, cycles and uniqueness.
4. Implement draft, revision, activation, retirement and retired-discovery service/API contracts.
5. Make activation and retirement transactional with their expected identities, projections, typed
   edges and audit events.
6. Change containment and required-relation writes to draft/activation semantics.
7. Replace published-object deletion/cascade with impact-previewed retirement; retain optimistic
   draft discard, clean up never-published root identity shells and defer physical purge.

This package passed its former tests, but its publication boundary is wrong for RDM. Its object drafts,
object revisions, per-object activation/retirement endpoints and lifecycle-shaped UI contracts are
implementation debt, not a compatibility commitment. WP6 and WP7 replace them without carrying a
dual-authority adapter.

### WP5 — Refreeze workspace lifecycle behavior and contracts (complete)

Primary areas: `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/UI_MODEL.md`,
`docs/BASE_0_6_INTERACTION_SPEC.md`, acceptance fixtures, OpenAPI design notes and this plan.

1. Finalize ADR-024 as the replacement for ADR-020 and define workspace revision, draft, activation,
   retirement, lineage and model-pinning terminology.
2. Rewrite journeys 3-7 around one workspace publication boundary and retain only the still-valid WP0
   workspace navigation, typed-table and accessibility behavior.
3. Freeze the draft-scoped and revision-scoped API shapes, concurrency tokens, cursor bindings and
   error codes before persistence changes.
4. Define whether the active workspace projection contains independent relations as well as
   object-owned data; Base 0.6 requires one coherent graph and therefore includes both.
5. Replace object-lifecycle acceptance fixtures with two workspace revisions containing multiple
   object types, containment and a cross-object relation.

Exit: complete. No accepted contract assigns publication lifecycle to an individual object; corrected
journeys, fixtures and API inventory are independently reviewable before migration code changes.

### WP6 — Replace object-lifecycle persistence with workspace revisions

Primary areas: SQLAlchemy models, Alembic, workspace lifecycle services, migration/startup recovery,
audit projections and backend contract tests.

1. Add workspace drafts, immutable workspace revisions, active-revision authority and copy-on-write
   record/relation membership keyed by stable object and relation IDs.
2. Add a corrective migration from both Base 0.5 and the rejected WP4 schema. Preserve workspace and
   public object/relation IDs; collapse the current effective graph into one initial workspace
   revision per populated workspace and stop with actionable diagnostics on ambiguity.
3. Remove object draft/revision tables and object active-revision pointers after successful conversion;
   do not retain a second runtime authority or hidden compatibility writes.
4. Make active object/relation projection rebuilding transactional with the workspace revision pointer.
5. Exercise clean bootstrap, preceding-revision upgrade, rejected-WP4 upgrade, restart, interrupted
   migration recovery and actionable refusal against real temporary databases.

Exit: each workspace resolves exactly one active content revision or none; no object-level lifecycle
authority remains; migration and startup recovery preserve stable public identities.

### WP7 — Implement workspace-draft editing and atomic publication

Primary areas: workspace lifecycle API models/router/services, draft-scoped object/attribute/relation
services, query/pagination, audit and OpenAPI locks.

1. Implement workspace draft/revision discovery, root and history-derived draft creation, discard,
   complete validation, activation and publication retirement.
2. Route every object, attribute, containment and relation mutation through an explicit workspace
   draft; active and historical reads are immutable.
3. Keep record-level optimistic concurrency inside a workspace draft and separately claim the complete
   draft plus expected active workspace revision during activation.
4. Validate the complete effective graph at activation: types, required attributes/relations,
   containment cycles, cardinality, uniqueness and pinned application-model release.
5. Bind draft and revision collection cursors to workspace, model release and content revision/draft
   identity; never page across a publication switch silently.
6. Remove the rejected object lifecycle endpoints from the public OpenAPI inventory and update its
   digest and error-schema locks.

Exit: related edits remain invisible to active reads until one atomic workspace activation; conflicts
publish nothing and preserve the workspace draft.

### WP8 — Deliver coherent workspace lifecycle UI

Primary areas: workspace pages, `frontend/src/features/objects/`, frontend runtime types/API client,
shared UI wrappers, routing/state handling and focused component tests.

1. Add workspace-level `Published`, `Drafts` and `History` destinations; lifecycle is not repeated on
   every object row or detail page.
2. Create/open a workspace draft before enabling record mutations. Tables, details, object forms,
   attribute fields and relationship editors retain their generic model-driven behavior inside that
   explicit draft context.
3. Show draft change summaries and validation results across all affected object types and relations
   before activation.
4. Show workspace `Created from` separately from `Superseded on activation`, and allow a new workspace
   draft to derive from an active or retired workspace revision.
5. Provide explicit workspace activation and publication-retirement dialogs with impact,
   confirmation and conflict recovery.
6. Preserve dirty input on field, record-version, workspace-draft-version, active-revision,
   uniqueness and pinned-model errors.
7. Keep published and historical workspace content read-only and keep essential table/actions visible
   without hover-only behavior.

Exit: journeys 2-7 operate in one visible workspace draft and publish or retire the dataset as a
whole; no object is independently activated or retired.

### WP9 — Validate and release

Primary areas: browser/accessibility/visual configuration and scenarios, backend migration and
contract suites, packaging checks, `README.md`, `CHANGELOG.md` and current documentation.

1. Add real-browser tests for all seven corrected journeys and automated accessibility plus keyboard coverage.
2. Add visual regression for shell, selector, table, workspace draft editor, history and retirement states.
3. Run backend contract/concurrency suites, migration/fresh-boot tests and packaged-wheel checks.
4. Re-run the usability walkthrough and resolve or explicitly defer serious findings.
5. Update README, changelog, API examples and status documentation to match shipped behavior.

Exit: all corrected journeys and the repository definition of done pass on Python 3.14 and the
supported frontend toolchain; the public contract contains no rejected object-lifecycle endpoint.

## Release acceptance criteria

- Workspace selection is catalogue-backed, URL-stable and correctly read-only when retired.
- Schema 0.5 table declarations are typed, validated and honestly rendered.
- Daily-use filters and sorts are typed, server-side, bounded and cursor-stable.
- Workspace revision storage is authoritative and active object/relation projections are transactional derivatives.
- A steward can create a root workspace draft, derive from any historical workspace revision, retire
  publication without deleting record history and later reactivate through a new workspace draft.
- Workspace history distinguishes derivation from supersession and published snapshots remain immutable.
- Conflicts preserve input and never partially publish a candidate.
- Core workflows pass browser, keyboard, accessibility and visual-regression coverage.
- Backend tests, Ruff, frontend lint/tests/build, migrations, packaging and `git diff --check` pass.

## Required validation

```bash
backend/.venv/bin/python -m ruff check backend/app backend/tests
backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
git diff --check
```

Also run the new browser/accessibility/visual suites; exercise migration and fresh boot; verify both
documented schema 0.4-to-0.5 development paths; verify unsupported schema versions and unknown legacy
object states fail with actionable diagnostics; and verify the wheel contains every Alembic revision.

## Coding-agent handoff

Implement corrective work packages in order and keep each independently reviewable. WP0 through WP3
remain complete. Do not build UI on the rejected WP4 object-lifecycle contract. WP5 is complete; WP6-WP8
replace the persistence, API and UI boundary before WP9 release validation. Inspect the
worktree before each package, preserve unrelated changes, update OpenAPI locks with public contracts
and create a checkpoint only after that package's definition of done passes.
