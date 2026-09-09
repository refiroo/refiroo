# Base 0.6 implementation plan

**Status:** Product resolutions accepted on 2026-09-08 (ADR-027). Prior WP0–WP8 delivery is retained
as history. Remaining delivery order is WP8.1 authority corrections, WP9 complete live/optional-draft UI,
then WP10 composed release validation. This planning update implements no runtime behavior.

**Target:** Product 0.6.0, schema language 0.5. The starter model content is already version 0.6.0;
that number alone does not mean the product release is accepted.

**Depends on:** Base 0.5 operational and model-release foundation; retained Base 0.6 generic services,
workspace persistence, typed tables and UI primitives.

## Product outcome

A steward selects a known workspace, finds and maintains live records, typed fields, containment,
relationships and translations through one familiar generic flow. An ordinary save needs no draft,
validation ceremony or activation. It preserves identity, validates data, checks concurrent changes and
records audit history. The same flow works for two differently configured record types.

For coordinated work, the steward chooses a draft copied from actual current live content or a named
historical snapshot. Draft application changes only authored rows, preserves unrelated live work and
publishes nothing on conflict or invalid merged data. History is newest first and read-only; a
historical source is not a restore operation. Publication retirement removes a designation, not live
consumer access. Data drafts and application-definition drafts remain separate.

Traceability: US-D01–D14, US-W01–W08, US-L01–L02, US-P01–P04, US-P06, US-U01, US-A01–A03;
SC-01–SC-06, SC-08, SC-12–SC-14 in their applicable channels. See
[product stories](product-functionality/USER_STORIES.md) and
[acceptance scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md).

## Release principles and exclusions

1. Live object/field/relation storage is current-data authority. Immutable revisions serve history.
2. A selected immutable model governs current data. Historical reads use their pinned supported model.
3. Record versions, aggregate draft versions, publication IDs and model-release versions are distinct.
4. Preserve generic CRUD, typed values, stable IDs, bounded queries and optimistic concurrency.
5. Reuse model-driven controls and registries; no starter-key branches or duplicate draft CRUD API.
6. Every added mandatory step or removed capability needs an explicit product reason and decision.
7. Compare the completed user task with its earlier flow; implementation-only tests are insufficient.

Excluded: specialist mapping/translation/tree renderers, bulk/import/export/feeds, authentication,
multi-node publication, model-designer redesign, history purge and independent object lifecycle.
Automatic rebasing and confirmed lossy historical model migration are 0.10 work under ADR-027; Base
0.6 preserves an incompatible draft and reports its model conflict. It does not offer an unsupported
force-confirm action. Normal user draft creation copies live or history; the existing empty-root path
is development/bootstrap support, not the required daily starting screen.

## Accepted contracts

### Model and data authority

- Global runtime state selects the current immutable model. Compatibility checks must include all
  live rows served under that model, including live-only and readable catalogue-retired content.
- Historical content resolves the revision's pinned supported model before query validation, value
  conversion and response composition. Unsupported historical schemas fail explicitly and retain data.
- A data draft pins a model and cannot silently change its pin or the global model. Until 0.10,
  activation with a different active model retains `workspace_draft_model_release_conflict`.
- Current-live bases capture a consistent graph and model/record versions without creating a public
  publication. Historical-source bases preserve the selected revision. Keep internal base identity
  separate from `derivedFromRevisionId` and `supersedesRevisionId` lineage.
- Activation merges authored creations/updates/removals over live content, checks touched versions,
  validates the merged graph and atomically writes the merged revision plus live changes and removes
  the draft. Failure changes neither live data nor draft.

### Workspace and content context

- The workspace catalogue owns stable keys, labels, active/retired status and one versioned default.
  Unknown explicit keys fail; retired catalogue workspaces are readable and reject all mutations.
  Capability flags are deployment controls, not user authorization.
- Canonical reads select live `workspaceKey`, an effective `workspaceDraftId`, or immutable
  `workspaceRevisionId`. Draft and history are mutually exclusive. Preserve context across browser
  list, detail, panel, lookup, history and return paths.
- Live object creation requires `workspaceKey`; live mutations of existing records use their owning
  workspace. Do not invent extra workspace fields on payloads that currently do not accept them.
- Existing-record updates/deletes claim `expectedVersion`. Draft writes additionally claim
  `expectedWorkspaceDraftVersion`; creation has no existing record version. Draft lifecycle operations
  use their documented draft/active-revision claims. See `API.md` for route-specific shapes.
- Publication retirement clears the current-publication designation while live data and immutable
  history remain. It must not disable live access or act as catalogue retirement.
- Revision discovery is newest first with deterministic cursor paging. Current oldest-first behavior
  must change with tests and API documentation before the history UI is accepted.

### Table queries and cursors

Schema 0.5 keeps the existing strict table contract: non-empty unique columns, configured filter/sort
fields, one default sort and bounded page size. API capability comes from model attributes; a view
chooses the UI-visible subset. No unrelated renderer substitutes for an unsupported view type.

The existing grammar remains: text equality/contains/starts-with, numeric/date/datetime comparisons,
boolean equality, null and missing-field tests. Different filters combine with AND and repeated equal
values on one field with OR. Values retain declared types, date lexical forms and null/unset distinction;
JSON is excluded from this grammar. Sorting has a unique non-public tie-breaker and null/unset last.

Live cursors currently bind query/workspace/order, not publication or model identity; they survive a
publication switch and do not promise a frozen dataset. Draft/history cursors bind their selected
identity and query. UI context/filter/sort changes discard the corresponding continuation. Do not add a
new guarantee by prose alone; strengthen cursor contracts only with explicit scope and regression tests.

## Required journeys

1. SC-01: non-default workspace search, detail, relationships, history and return without scope loss.
2. SC-02–SC-04: live create/edit/field removal/availability/parent/relation/translation/deletion,
   typed values, required initial relationships, impact confirmation and conflict recovery.
3. SC-05: copy current live after post-publication edits and with no prior publication; immutable base.
4. SC-06: staged invisibility, unrelated live edits preserved, touched-record conflicts and merged-graph
   validation; no partial application and no automatic overwrite.
5. SC-08: historical source and supersession differ, newest-first history, no direct restore, truthful
   publication retirement, catalogue-retired read-only behavior and preserved snapshots.
6. SC-12–SC-13 (current foundation): model validation/install/activation, live-only incompatible data
   blocking model activation, correctly typed pinned history after a model change, actionable failures.
7. SC-14: workspace provisioning/default conflicts/retirement through the API and stable paged reads.

Exercise two record types and two containment/ownership configurations; keyboard, narrow-screen,
empty/error/retry and dirty-input behavior apply to every relevant browser journey.

## Historical work-package record

WP0–WP8 below record prior implementation and rejected approaches; they are not instructions to
reintroduce draft-only writes or active-revision read authority. Their original exit claims do not
prove the ADR-027 acceptance above. Execute only the remaining packages after this record.

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

### WP4 — Make object revisions authoritative (historical, rejected and removed by WP6)

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

### WP6 — Replace object-lifecycle persistence with workspace revisions (historical delivery)

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

### WP8 — Complete workspace lifecycle orchestration (complete)

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

## Remaining implementation packages

### WP8.1 — Correct the authority boundaries before dependent UI acceptance

**Status:** Planned; accepted product semantics, runtime corrections and evidence outstanding.
**Stories:** US-W01–W08, US-P02/P04, US-D12 and the live-data invariants used by every CRUD story.

Deliver the following bounded slices sequentially. One implementation owner per slice; no overlapping
module writers. Each slice produces an independently reviewed diff and direct boundary evidence.

#### WP8.1-A — Live compatibility and pinned historical interpretation (implemented)

Primary areas: `backend/app/services/model/compatibility.py`, snapshot dependencies/resolution,
object/attribute/relation query and response services, routers and focused integration tests.

- Replace active-revision membership as the model-compatibility population with authoritative live
  objects and related fields/edges, including readable catalogue-retired scopes.
- Resolve history through its pinned model before filters, metadata, typed responses and relationships.
  Keep current model selection for live operations; resolve drafts through their own pin.
- Return explicit model/context errors for unsupported history without guessing or silently upgrading.
- Preserve context through route/service validation: an explicitly supplied workspace must not conflict
  with a selected draft or historical revision. Document current omissions as gaps and lock the
  corrected behavior with request-boundary tests; do not silently accept mismatched context.
- Preserve current model activation concurrency and post-commit readiness handling.

Exit evidence: live-only incompatible data blocks activation; compatible activation succeeds; an old
snapshot's fields and relationships remain correctly interpreted after a model switch; retired live
content cannot evade compatibility; failing activation leaves selection/data unchanged. A stored model
ID or a unit test of its getter is not enough. No data migration or new schema override belongs here.

#### WP8.1-B — Capture the actual current-live draft base

Primary areas: workspace persistence, additive Alembic revision if required, draft service/API models,
workspace routes, effective membership/merge and lifecycle tests.

**Status: complete (2026-09-09).** SQLite current-live bases are private immutable snapshots with an
explicit source discriminator and retry/refusal isolation boundary. PostgreSQL capture remains explicitly
unsupported pending an equivalent protocol; WP8.1-C, WP9 and WP10 remain open.

- Provide an explicit current-live source and a separate historical source while retaining existing
  historical derivation. Do not reinterpret an existing client request ambiguously; define the request
  discriminator and compatibility treatment in `API.md` and OpenAPI before changing behavior.
- Capture objects, fields, parent/typed edges, independent relations, selected model and record versions
  in one consistent base. No existing publication is required; no new public revision or activation is
  created merely to start a draft.
- Persist immutable internal base identity separately from publication lineage. Existing drafts retain
  their original source and versions through migration; never silently rebase them onto today's data.
- Keep empty-root behavior only as explicitly documented development/bootstrap compatibility. Normal
  UI creation chooses current live or history; current live may naturally be empty.
- Bind snapshot capture to concurrent live/model changes transactionally or fail/retry explicitly;
  document the chosen isolation/version mechanism before implementation.

Exit evidence: SC-05 including post-publication field/relation edits and no publication; concurrent
capture cannot mix incompatible graph/model states; subsequent live edits do not rewrite the base;
SC-06 merges untouched work and rejects conflicts; old drafts/revisions and IDs survive upgrade.
Run clean bootstrap, preceding revision upgrade, restart and interrupted-migration recovery/refusal
against real temporary databases, plus final startup against the configured database or isolated copy.

#### WP8.1-C — History order and retirement contract proof

Primary areas: revision pagination service/router, cursor tests, retirement integration tests and API docs.

- Implement newest-first revision history with a unique tie-breaker, bounded pages and exact retry.
- Preserve old snapshot content; historical derivation is not full-dataset replacement.
- Prove publication retirement clears only the designation while live records remain readable and
  mutable in an active catalogue workspace. Catalogue retirement remains read-only and separately tested.
- Keep public naming truthful in the UI; no endpoint rename or data-withdrawal authority is implied.

Exit evidence: multiple history pages in correct order without repeat/omission under the supported
query contract, stale retirement conflict with no side effects, retained live reads/writes after
publication retirement and rejected mutations after catalogue retirement. Update affected API and
cursor expectations without claiming broader snapshot guarantees.

**WP8.1 gate:** all three slices pass their direct boundary tests and applicable repository checks;
model/source/retirement semantics match ADR-027. Unaffected live UI work may be designed independently,
but the complete WP9 design/history acceptance depends on this gate.

### WP9 — Complete generic browser tasks in live, draft and history contexts

**Status:** Planned. **Stories:** US-D01–D14, US-L01–L02, US-W01–W08, US-U01.
Primary areas: `frontend/src/features/workspaces/`, `features/objects/`, API client/types, routing,
model resolution, shell and RDM-owned UI wrappers.

1. Fix workspace handoff through every read, write context, lookup, detail panel and return URL. Keep
   the chosen label visible and preserve query/page position. Repair non-default detail before claiming
   a usable workspace selector journey.
2. Restore Add/Edit/Delete for live records, fields, ordinary relationships and translations using
   existing generic components. One record-create can include permitted initial relationships; it is
   not a new arbitrary multi-record transaction API. Required/typed/read-only rules remain model-driven.
3. Use coherent edit forms for mutable core fields, typed fields, parent and required connections.
   Keep individual field controls useful; do not force users through multiple saves for one normal edit.
4. Add workspace Live, Drafts and History contexts. A draft is an explicit alternative, never a
   prerequisite for live writes. Copy from current live or selected history; empty draft creation is
   not the main user journey. No per-record activation/retirement or nested draft CRUD resources.
5. Render history with the pinned definition and immutable controls; a catalogue-retired workspace is
   also read-only. Show draft source and superseded publication separately, newest-first history, and
   explain publication retirement as designation removal while live data remains available.
6. Restore empty relationship/translation states, bounded candidate searches, independently retryable
   panels and preservation of loaded content. Failed data must not look like a genuinely empty result.
7. Preserve entered fields on validation and version conflicts; show current content for explicit
   reconciliation. Keep busy/dirty guards, modal focus, keyboard operation, narrow layouts and semantic
   HTML through RDM wrappers. A normal live save has no draft or activation ceremony.
8. For model-mismatched historical drafts, show pinned/current models and preserve input. Base 0.6
   explains that migration is required; the 0.10 schema-confirmation feature is not enabled prematurely.

Exit: SC-01–SC-06 and SC-08 work through the browser and real backend for two configured types and two
ownership/containment cases. Record exact remaining E1/E2/E3 evidence separately. Specialist views,
workspace administration redesign, schema migration and model-workbench redesign remain excluded.

### WP10 — Validate the composed product and publish the evidence

**Status:** Planned. Primary areas: browser harness, accessibility/visual checks, backend integration,
migration/lifespan/package suites and release documentation. No new feature scope hides in this gate.

1. Execute the required journeys above against a real backend and isolated database. Test live CRUD
   without a draft/revision, optional staging, current-live bases, concurrency/delta merge, whole-graph
   atomic failure, live-only compatibility and pinned historical typing.
2. Exercise two record types, configured ownership differences, non-default workspaces, empty/error/
   retry states, explicit deletion impact, availability versus deletion, and complete model-workbench
   save/check/install/activate. Installation alone must not select the model.
3. Run real-browser keyboard/focus/narrow-layout journeys, automated accessibility and visual checks.
   Record the screen sizes, browser version and manual assistive-technology coverage actually used.
4. Exercise clean bootstrap, preceding-revision and corrective legacy upgrades, restart, interrupted
   recovery or actionable refusal, then final smoke startup on the configured database or isolated copy.
5. Build/install a wheel with migration files using Python 3.14; check OpenAPI inventory/digest and
   runtime/error contracts. Run the standard commands below and report relevant skips as gaps.
6. Record commit/worktree, data/configuration variants, commands/results, screenshots/evidence links,
   failure outcomes, limitations and the before/after flow comparison. Update story delivery channels
   only when the matching evidence exists. A green fixture suite is not release acceptance.

Exit: all named invariants have direct integration evidence, browser journeys are proven and no
relevant skipped suite is counted as complete. Any remaining gap has explicit release ownership and
prevents acceptance of the affected story.

## Historical ADR-026 slice record

The 2026-09-07 Slices 0–5 restored live reads/writes and delta-merge activation. Their recorded test
results are historical evidence only; this documentation pass did not rerun them. The fresh live-base
claim was incomplete, and WP8.1 now owns that correction plus dependent model/history authority checks.
See `TODO.md` and ADR-026/027. Do not resurrect the superseded amendment's draft-only prerequisites.

## Required validation for implementation

```bash
backend/.venv/bin/python -m ruff check backend/app backend/tests
backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run lint
npm --prefix frontend run format
npm --prefix frontend run test
npm --prefix frontend run build
git diff --check
```

Browser/accessibility/visual suites, migration/startup and wheel checks are additional gates described
above; passing these six tooling areas alone does not prove them. Build wheels from `backend/` with
`.venv/bin/python -m pip wheel .`. A documentation-only pass checks links, traceability, contracts and
whitespace; it does not claim these runtime tests were executed.

## Coding-agent handoff

Read this plan, ADR-027, the product stories/scenarios, `PROJECT_STATUS.md`, `API.md` and the interaction
specification. Inspect the dirty worktree and preserve unrelated changes. Start with WP8.1-A; give each
slice one implementation owner, followed by focused verification and review appropriate to scope.
Complete WP8.1-C before accepting dependent WP9 history flows, then execute WP9 and WP10.
State story IDs, user-visible behavior, exclusions, public-contract changes and direct evidence before
coding. Preserve all generic controls and invariants. Commit only when explicitly requested.

Report each completed change batch to the user while work continues, including its behavior, validation
and remaining limitations; do not wait until the end of a large package to surface scope changes.
