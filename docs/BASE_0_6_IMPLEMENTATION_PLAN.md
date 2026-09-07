# Base 0.6 implementation plan

**Status:** Replanned; WP0-WP3 complete, WP5 workspace publication and WP6 persistence retained;
WP7 is stopped and must restore generic CRUD over that storage before WP8-WP10

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
2. Keep workspace content revisions, application-model releases and record-level optimistic concurrency distinct.
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
- The established generic object, attribute and relation CRUD contract is unchanged. A workspace
  content context selects its backing snapshot: `workspaceKey` selects the active revision for
  published reads, `workspaceDraftId` selects the effective mutable draft for draft reads and writes,
  and `workspaceRevisionId` selects an immutable historical revision. A request must not combine
  draft and historical contexts. Record routes remain canonical and must not create a second CRUD
  vocabulary.
- Historical reads require `workspaceRevisionId`; no mutation route may silently target an active or
  historical projection. There are no object drafts, object revisions or independent record lifecycle
  states.
- `GET/POST /api/v1/workspaces/{workspaceKey}/drafts` lists or creates workspace drafts.
  `GET/PATCH/DELETE /api/v1/workspace-drafts/{draftId}` reads, names or discards a draft with
  optimistic concurrency.
- The canonical object, attribute and relation resources retain their existing paths, request and
  response shapes, pagination and validation semantics. A selected workspace draft is execution
  context, not a new public resource dialect. Record writes must carry the workspace-draft and record
  concurrency claims so unrelated editors receive explicit conflicts without inventing record lifecycle.
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
authoritative for WP6-WP10.

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

### WP7 — Restore generic CRUD over workspace revisions (completed corrective implementation)

Primary areas: existing generic object/attribute/relation services and routers, workspace revision
resolution, query/pagination, audit and OpenAPI locks. Use Git history as a recovery source; do not
replace the established CRUD surface with nested draft resources.

1. Review the stopped WP7 diff and retain only valid workspace lifecycle infrastructure.
2. Recover established object, attribute, containment, relation and translation behavior selectively
   from the pre-WP6 history. Use `a3ead41^` to locate deleted backend CRUD. Use `41aa7e7^` only as a
   source for individual generic frontend controls: that tree is `60c8967` and also contains the
   rejected lifecycle UI, so never restore a file wholesale without removing object drafts, object
   revisions, activation and retirement behavior.
3. Restore one canonical generic CRUD contract. Do not make
   `/api/v1/workspace-drafts/{draftId}/objects` or `/relations` public CRUD resources; workspace
   draft/revision discovery and lifecycle actions remain under workspace resources.
4. Resolve the same CRUD operations against the active workspace revision when `workspaceKey` is the
   read context, the effective workspace draft when `workspaceDraftId` is supplied, and an immutable
   historical revision when `workspaceRevisionId` is supplied. Writes require `workspaceDraftId`;
   create payloads retain `workspaceKey` and must match the draft's workspace. Preserve typed values,
   model validation, containment atomicity,
   relation cardinality, translation atomicity, pagination and optimistic concurrency.
5. Ensure empty relationship and translation collections return successful empty pages, not retryable
   errors. Restore and unskip the object, attribute, relation, cascade and translation test suites.
6. Keep workspace draft/revision discovery, validation, activation and publication retirement separate
   from record CRUD; activation still validates and publishes the complete graph atomically.
7. Update OpenAPI inventory and digest locks only for the corrected public contract.

Exit: all established CRUD operations work against workspace-backed storage with no semantic or public
API regression; active reads remain unchanged until workspace activation; conflicts publish nothing and
preserve the workspace draft; no object-level lifecycle authority or duplicate CRUD dialect remains.

### WP8 — Complete workspace lifecycle orchestration

Primary areas: workspace lifecycle API models/router/services, draft/revision discovery, graph
validation, activation, retirement, audit and OpenAPI locks.

1. Implement workspace draft/revision discovery, root and history-derived draft creation, discard,
   complete graph validation, activation and publication retirement.
2. Require explicit workspace-draft context for writes while preserving the canonical CRUD operations;
   active and historical reads remain immutable.
3. Claim draft, record and expected active-revision concurrency independently and publish the complete
   graph atomically, preserving the draft after failure.
4. Bind cursors to workspace, model release and exact active revision or draft identity.
5. Keep lifecycle endpoints under workspace resources and never expose object/relation lifecycle
   endpoints or nested draft CRUD aliases.

Exit: workspace lifecycle is complete and independently testable; no object is independently activated
or retired and generic CRUD semantics remain unchanged.

### WP9 — Restore and reuse generic CRUD UI in workspace context

Primary areas: workspace pages, `frontend/src/features/objects/`, runtime types/API client, routing,
shared UI wrappers and focused component tests.

1. Restore Add/Edit object and attribute operations, Add/Edit/Delete relation operations, and Add/Edit
   translation operations using the existing generic forms and panels.
2. Add workspace-level Published, Drafts and History destinations and require a selected draft before
   enabling record writes; do not duplicate lifecycle actions on object rows or details.
3. Render empty relationships and translations as empty collections, not error/retry panels.
4. Preserve dirty input, keyboard/focus behavior and conflict recovery inside the selected draft.
5. Keep published and historical content read-only and remove every object retirement control.

Exit: the established CRUD UI operates inside a workspace draft without changing its semantics, and
workspace lifecycle controls remain visibly workspace-level.

### WP10 — Integration recovery and release validation

Primary areas: real-browser/accessibility/visual scenarios, backend contract and migration suites,
packaging checks, `README.md`, `CHANGELOG.md` and current documentation.

1. Add real frontend-to-backend coverage for object, attribute, relation and translation CRUD, including
   empty relationship/translation states and at least two object types.
2. Verify draft changes are invisible to published reads, activation publishes all changes together,
   and failed activation publishes nothing while preserving the draft.
3. Add browser, keyboard, accessibility and visual regression coverage for shell, selector, tables,
   generic forms, workspace draft, history and retirement states.
4. Run backend contract/concurrency/migration/fresh-boot and packaged-wheel checks, frontend lint,
   tests and production build, and verify no relevant CRUD suite is skipped.
5. Update release documentation and record manual acceptance results.

Exit: all corrected journeys and the repository definition of done pass on Python 3.14 and the
supported frontend toolchain; the public contract contains no rejected object-lifecycle endpoint.

## Release acceptance criteria

- Workspace selection is catalogue-backed, URL-stable and correctly read-only when retired.
- Schema 0.5 table declarations are typed, validated and honestly rendered.
- Daily-use filters and sorts are typed, server-side, bounded and cursor-stable.
- Workspace revision storage is authoritative and active object/relation projections are transactional derivatives.
- Generic object, attribute, containment, relation and translation CRUD retains one canonical contract;
  workspace context changes the backing snapshot, not the operation semantics.
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

Implement work packages in order and keep each independently reviewable. WP0 through WP3, WP5 and WP6
remain complete. Do not build UI or APIs on the rejected WP4 object-lifecycle contract. WP7 is the
current stopped recovery package: restore generic CRUD over WP6 storage and re-enable its tests before
starting WP8 lifecycle orchestration, WP9 CRUD UI integration or WP10 release validation. Inspect the
worktree before each package, preserve unrelated changes, update OpenAPI locks with public contracts
and create a checkpoint only after that package's definition of done passes.
