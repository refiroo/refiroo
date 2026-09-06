# Base 0.6 implementation plan

**Status:** In progress; D1-D5 accepted, WP0-WP3 complete, WP4 is next

**Target:** Product release 0.6.0

**Scope:** Versioned daily operations

**Depends on:** Completed Base 0.5 operational and model-lifecycle foundation

**Unlocks:** Schema 0.6 mapping, then translation, hierarchy and integration workflows

## Product outcome

A data steward can select a known workspace, find records through typed server-side table filters and
sorts, create a complete root draft, revise any active or retired revision, explicitly retire the
current revision and understand the complete derivation and supersession history. Active and retired
content is read-only. The UI provides one coherent, accessible editing flow without starter-key
branches.

Base 0.6 establishes the lifecycle and interaction foundation on which specialist workspaces depend.
Mapping-grid configuration, mapping APIs and model-workbench redesign are outside this release so the
object-revision migration and daily-operation journeys can be completed as one bounded change.

## Release principles

1. Design and test complete tasks, not isolated components.
2. Keep runtime-object revisions, model releases and relation-instance concurrency distinct.
3. Keep the engine generic: runtime and UI code never branch on starter keys.
4. Revision storage is authoritative; an active projection is transactionally derived.
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
- Stable logical objects with mutable drafts and immutable active/retired revisions
- Root drafts, history-derived drafts, activation and explicit retirement
- Visible derivation and supersession lineage
- Migration from Base 0.5 object state to authoritative revision storage
- Browser journey, accessibility, visual, migration and package validation

### Deferred

- `mappingGrid` schema and renderer, mapping query/mutation APIs and ADR-022 implementation
- Model-workbench information-architecture redesign
- Bulk object or relation mutation
- Translation matrix and hierarchy tree
- Import/export jobs, change feeds and webhooks
- Authentication, authorization and multi-node publication
- Draft rebasing across model releases and executable runtime-data migrations
- Physical purge of published object history
- Structured model designer and extension packaging

## Accepted decisions

- **D1 / ADR-019:** Workspaces are global database records with immutable keys, mutable labels,
  active/retired state and one atomically selected active default. Mutation routes use
  `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, enabled by default until authentication exists; it is not
  authorization.
- **D2 / ADR-020:** A stable logical object owns mutable drafts and immutable active/retired revisions.
  An existing-object draft clones a selected revision; a new object begins with a populated root
  draft. Derivation and activation supersession are separate history edges. The current active
  revision can be explicitly retired without replacement.
- **D3 / ADR-021:** Schema 0.5 provides a strict `table` contract and explicit version dispatch. Schema
  0.4 remains stored/listable/exportable but cannot run. This pre-production transition uses
  reset/rebootstrap or an offline one-shot transition rather than a runtime compatibility adapter.
- **D4 / ADR-022:** Atomic mapping replacement and exact-binding relation-set versions remain accepted,
  but implementation moves with `mappingGrid` to schema 0.6 and the next product release.
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

### Runtime-object revisions

- `objects` owns stable public identity, workspace, application and object type. Revision/draft storage
  owns core fields, parent, typed attributes and required ownership relations.
- Each draft/revision pins `modelReleaseId`. Activation against another currently resolved release
  returns `409 draft_model_release_conflict`; rebasing is not implicit.
- Cloning history validates the copied snapshot against the currently resolved release and pins that
  release on the draft; the immutable source revision retains its original release identity.
- Active collection/detail endpoints expose current active projections by default. Explicit retired
  discovery finds objects without an active revision.
- `GET /api/v1/objects/{objectTypeKey}` accepts `lifecycle=active|retired` and defaults to `active`;
  retired means a logical object currently has no active revision. The existing detail route returns
  only a current active projection; historical content is read through the revision route.
- `POST /api/v1/object-drafts` creates a populated root draft and stable identity.
  `POST /api/v1/objects/{objectTypeKey}/{objectId}/drafts` clones its required
  `derivedFromRevisionId`. `GET` on that collection is cursor-paged.
- `GET`, `PATCH` and `DELETE /api/v1/object-drafts/{draftId}` provide draft detail, optimistic editing
  and deletion. Only drafts are mutable, each PATCH/DELETE uses `expectedVersion`, and multiple drafts
  per logical object are valid.
- `GET /api/v1/objects/{objectTypeKey}/{objectId}/revisions` is cursor-paged;
  `GET /api/v1/object-revisions/{revisionId}` returns an immutable snapshot.
- `POST /api/v1/object-drafts/{draftId}/activation` requires `expectedDraftVersion` and
  `expectedActiveRevisionId`, validates the complete snapshot and atomically publishes it.
  `derivedFromRevisionId` remains the copied source; `supersedesRevisionId` records the revision active
  at publication. For root activation, both expected and superseded active revision IDs are null.
- `POST /api/v1/objects/{objectTypeKey}/{objectId}/retirement` requires
  `expectedActiveRevisionId`, atomically retires the current revision and clears the active pointer.
  The logical object and history remain available and draftable.
- Any draft may be discarded. Discarding the last never-activated root draft also removes its empty
  logical-identity shell; published identity and history are retained.

## Acceptance journeys

Use representative data from at least two object types and two ownership/containment configurations.

1. Select a non-default workspace, move between applications and return without losing URL context.
2. Find an object with configured attribute filters and sort, open it and return to the same list state.
3. Create and activate a populated root draft with typed attributes and required relationships.
4. Derive a draft from the active revision, edit core fields, parent and attributes, then activate it.
5. Derive a draft from an earlier retired revision and see separately what it was created from and
   what active revision it superseded.
6. Retire an active revision without replacement, find it through retired discovery, derive a draft
   from it and activate the new revision.
7. Recover from draft-version, active-revision, uniqueness and pinned-model conflicts without losing
   local input.

## Work packages

### WP0 — Freeze interaction behavior

Completed and independently reviewed in `BASE_0_6_INTERACTION_SPEC.md`, with canonical downstream
test data and invariant coverage in `frontend/src/test/base06AcceptanceFixtures.ts` and its focused
test. The accepted baseline is the interaction contract for WP1-WP6.

Primary areas: `docs/UI_MODEL.md`, focused interaction notes/fixtures under `docs/`, and frontend test
fixtures.

1. Walk the seven journeys against Base 0.5 and record task failures and unnecessary context switches.
2. Specify information architecture for product, application, view, workspace, logical object, draft
   and revision context.
3. Produce low-fidelity states for collection, complete draft editing, history, retirement, conflicts
   and empty/error/loading cases.
4. Define responsive behavior, keyboard order, focus return, readable density and action hierarchy.
5. Create representative fixtures for two object types and active- and retired-derived histories.

Exit: the interaction specification is independently reviewable and every journey has observable
acceptance criteria. D1-D5 are already resolved and require no further decision.

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

### WP4 — Make object revisions authoritative

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

Exit: revision storage is the sole write authority; active projections cannot drift; competing draft,
activation and retirement operations fail atomically; migration and fresh boot both pass.

### WP5 — Deliver coherent lifecycle UI

Primary areas: `frontend/src/features/objects/`, frontend runtime types and API client, shared UI
wrappers, routing/state handling and focused component/browser tests.

1. Provide one root/create and revise-existing editor for core fields, parent, typed attributes and
   required relationships.
2. List drafts separately from active objects and provide explicit retired-object discovery.
3. Show current active revision with cursor-paged history and label `Created from` separately from
   `Superseded on activation`.
4. Offer `Create draft from this revision` on active and retired history entries.
5. Provide explicit activation and retirement actions with impact, confirmation and conflict recovery.
6. Preserve dirty input on field, draft-version, active-revision and pinned-model errors.
7. Improve table scanning and row actions without hover-only essential behavior.

Exit: journeys 2-7 complete without separate core/attribute edit modes; immutable content has no edit
controls; a retired object is straightforward to find, branch from and reactivate.

### WP6 — Validate and release

Primary areas: browser/accessibility/visual configuration and scenarios, backend migration and
contract suites, packaging checks, `README.md`, `CHANGELOG.md` and current documentation.

1. Add real-browser tests for all seven journeys and automated accessibility plus keyboard coverage.
2. Add visual regression for shell, selector, table, draft editor, history and retirement states.
3. Run backend contract/concurrency suites, migration/fresh-boot tests and packaged-wheel checks.
4. Re-run the usability walkthrough and resolve or explicitly defer serious findings.
5. Update README, changelog, API examples and status documentation to match shipped behavior.

Exit: all journeys and the repository definition of done pass on Python 3.14 and the supported frontend
toolchain.

## Release acceptance criteria

- Workspace selection is catalogue-backed, URL-stable and correctly read-only when retired.
- Schema 0.5 table declarations are typed, validated and honestly rendered.
- Daily-use filters and sorts are typed, server-side, bounded and cursor-stable.
- Draft/revision storage is authoritative and active projections are transactional derivatives.
- A steward can create a root draft, revise any historical revision, retire without replacement and
  later reactivate through a new draft.
- History distinguishes derivation from supersession and active/retired snapshots remain immutable.
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

Implement work packages in order and keep each independently reviewable. WP0 through WP3 are complete;
WP4 is the next package. Inspect the worktree before each package, preserve unrelated changes, update
OpenAPI locks with public contracts and create a checkpoint only after that package's definition of
done passes.
