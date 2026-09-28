# Instructions for coding agents

## Read first

Use the smallest authoritative context that covers the requested change:

1. `docs/PROJECT_STATUS.md`
2. The active work-package section and its acceptance criteria
3. The relevant ADR, API or model-contract section
4. The source files and tests on the execution path being changed

Read `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/APPLICATION_MODEL.md`,
`docs/SOURCE_MODEL_ANALYSIS.md` and `docs/DECISIONS.md` in full only when the task
changes or reopens product, architecture or model-contract decisions. Prefer targeted
searches and relevant sections over loading complete documents into the session.

Do not infer the product from one screen or object type. This is a generic model-driven engine. RDM
Master, Systems and Translations are starter applications, not hardcoded modules.

## Product invariants

- The versioned JSON model is the declarative source for applications, object types, global attribute
  types, relation types, allowed object-type relationships and views.
- Runtime code must remain unaware of domain-specific keys such as `master-value` or `system-value`.
- Attribute types are globally reusable; object types attach them through explicit bindings.
- Relation types define forward/reverse semantics separately from permitted source/target combinations.
- Parent containment is both an object hierarchy and a typed relation, maintained atomically.
- UI renderers may implement generic view types but must not branch on application or object-type keys.
- Every model reference is validated at startup and should fail with a precise path and reason.
- Public APIs never use an undocumented result cap. Collections page with cursors or positions
  (ADR-030): the UI scrolls with cursors and jumps with positions.
- Bulk and integration APIs are first-class features, not wrappers around UI calls.
- Public IDs and model keys are stable. Never expose database sequence IDs as domain identifiers.
- Attribute values retain their declared types. Do not reduce booleans, numbers or dates to strings.
- Updates use optimistic concurrency. Never silently overwrite a newer version.
- Model releases are immutable snapshots; schema-language and content-release versions are separate.
- Keep vendor-specific source exports and internal numeric identifiers outside this repository.
- Other domains (MDM-lite, small product catalogues) are modelled, never built in. Add no capability
  only one domain can use, and keep the doors in `docs/COMPOSABLE_DOMAINS.md` open: a plan touching
  identity, attribute storage, audit/history, bulk APIs, the consumer API `match` declaration or
  mapping coverage states in one line whether a door is affected (ADR-032).

## Working method

For each feature, apply only the steps relevant to its scope:

1. State the user-visible behavior in a small plan.
2. Extend the application model only when behavior must be configurable.
3. Add model validation before relying on new configuration.
4. Update metadata persistence if the model contract changes.
5. Implement behavior and focused tests in the affected layer.
6. For UI changes, implement a generic component and exercise it with at least two object types.
7. Update documentation when behavior or contracts change; add an architecture decision only
   for a durable architectural choice.
8. Run the validation required for the affected layer as defined below.

Avoid speculative abstractions. Add a generalization after two real RDM cases demonstrate it. Keep API
errors explicit and machine-readable.

### Error handling and regression fixes

- A stack trace is diagnostic data, not an operator-facing error message. Handle expected operational
  failures at the relevant boundary and report what failed, why it failed, the resulting service
  state, the safe recovery action and the information needed when escalating it. Do not require a
  user or operator to interpret a Python, JavaScript, SQL or framework traceback.
- Do not silently discard the underlying cause. Preserve it for controlled debug diagnostics or a
  correlation identifier, while keeping normal logs and API responses concise, safe and actionable.
- Fixing a defect includes a regression test that reproduces the observed failure mode and verifies
  the human-facing error behavior. Also test the adjacent real execution boundary that allowed the
  defect through; unit coverage of the corrected function alone is insufficient.
- When a migration or startup path changes, test clean bootstrap, upgrade from the preceding revision,
  restart, and recovery or actionable refusal after an interrupted migration. Exercise the FastAPI
  lifespan against a real temporary database and perform a final smoke start against the configured
  development database or an isolated copy of it.
- Validation reports must state what was actually exercised and any remaining limitations. Never use
  a broad claim such as “the application works” based only on passing unit or fixture-level tests.

## Code conventions

### Backend

- Python 3.14, FastAPI, Pydantic 2 and SQLAlchemy 2.
- Type public functions.
- Keep Pydantic API models separate from SQLAlchemy persistence models.
- Keep model parsing and validation independent of the database.
- Attribute conversion belongs in `services/attributes.py`, not route handlers.
- Every attribute write goes through `services/attributes.apply_attribute_values` or its
  `validate_attribute_change` half, so no path can persist values while skipping a check.
- Routers translate requests and responses. Orchestration lives in `services/`; a handler that
  reads the model to decide what to write belongs in a service.
- Handlers take the request-scoped `DbSession` dependency. Do not open `SessionLocal()` inside a
  request path; one request reads from one session.
- Collections page through `services/pagination.py`. Declare sort keys, do not hand-write a keyset
  predicate, and make the last key unique within the filtered set. A collection route takes
  `routers/paging.PageQuery` (or `SeekablePageQuery` where it supports seek) and returns the page's
  `links()`, so every list gains cursors both ways, position, `from=end` and totals together.
- Change-set and publication reads go through `services/snapshot_reads.py`, never `effective_change_set_membership`,
  which is for whole-graph validation, publishing and writes. Publication, change-set base and change-set object
  rows keep a typed value index (`snapshot_attribute_values`) that an ORM flush hook maintains; a bulk
  insert or delete of those rows outside the ORM must update it through `services/snapshot_values.py`.
- Relation matrix cell states (`matrix_cell_states`, ADR-033) follow objects, relations, attribute
  values and change set rows through an ORM flush hook. A Core insert, update or delete of those rows
  must note what it changed with `services/matrix_states.note_rows`, `note_cells` or
  `note_relations_removed`, or the matrix state filter drifts until the next rebuild; the write path's
  test runs `matrix_states.verify`.
- Model shape lives in `models/schema.py`; cross-reference rules live in
  `services/model/validation/`. A rule raises `ModelReferenceError` with the JSON pointer of the
  failing node — never reconstruct a path from a message.
- Obtain an `EngineModel` through `services/model/compiler.parse_model` or `compile_model`.
  `EngineModel.model_validate` checks shape only and does not guarantee references resolve.
- Database migrations will use Alembic before the first deployed schema change.
- Prefer focused service modules over adding more logic to `main.py`.

### Frontend

- React, TypeScript and Vite. See `docs/FRONTEND_STRUCTURE_REFACTOR.md` for the module layout and
  the reasoning behind it.
- Import within `src/` through the `@/` alias, never with relative paths that climb directories.
- Keep model contracts in `src/types/`, which `src/types/index.ts` re-exports as one barrel. Split
  by area: `model.ts` for the declarative model, `runtime.ts` for stored objects and relations,
  `modelAdmin.ts` for model drafts and releases, and `ui.ts` for state the browser owns such as
  `RouteState` — that is not a model contract and does not belong beside one.
- Generic renderers receive model definitions as input.
- Do not embed object-specific columns, labels or forms in components.
- Resolve a declared view or panel type through its registry in `features/objects/views/` or
  `features/objects/panels/`, and render the result as an element. Calling it as a function puts
  its hooks in the caller's hook list.
- `model/` holds reads over the model and stays free of JSX; presentation belongs in `ui/`.
- Page a collection a user scrolls or jumps through with `lib/hooks/useCursorWindow` rendered in
  `ui/ScrollWindow` (ADR-030): a bounded window of pages, cursors to scroll, positions to jump, one
  `anchor` in the URL. `useCursorFeed` remains for short append-only feeds (record history, change-set and
  publication lists). Do not hand-write a cursor stack or page buttons.
- Recognise an API failure with `isApiError` from `api/errors`, never by reading `code` off a cast,
  and render one with `errorMessage` so users never see an `Error:` prefix.
- Build a dialog with `ui/Modal`, which owns the backdrop, the generated `aria-labelledby`,
  Escape, focus restore, the focus trap and the scroll lock. Do not hand-roll a `.dialog-backdrop`.
- Preserve keyboard operation and semantic HTML.
- Run `npm run lint` and `npm run format` before finishing. `react-hooks/set-state-in-effect` is
  configured as a warning for the reason recorded in `eslint.config.js`; do not add sites to it.

## Definition of done

A change is complete when the checks relevant to its changed layers pass, new configuration is
validated, documentation matches changed behavior, and no branch was added for a starter
application or object-type key.

For startup or migration changes, completion additionally requires the startup and interrupted-
migration checks in the error-handling section above; a green unit suite alone is not sufficient.

### Work-package validation

Keep validation proportional to the changed behavior. Choose the smallest existing tests that
exercise the acceptance criteria and affected execution paths; add meaningful regression coverage
for defects. Finish implementation and review the final diff before running final package checks.
Select them from the changed boundary with [the execution guide](docs/testing/EXECUTION_GUIDE.md)
(pytest group markers, Vitest projects, browser runners); register a new backend test module in
`TEST_GROUPS` in `backend/tests/conftest.py` and a new browser runner in that guide.

- Backend code: run focused tests while iterating, then the affected test files or cases and
  `ruff check app/ tests/` after the final backend change. Do not run the full `pytest` suite
  for each work package.
- Frontend code: run focused tests for changed behavior, then `npm run format`, `npm run lint`
  and `npm run build` after the final frontend change. Do not run the full `npm run test` suite
  for each work package. Lint must report zero errors; justified warnings are listed in
  `eslint.config.js`.
- Cross-stack behavior or a public contract: exercise the changed API boundary, relevant contract
  checks and affected consumer behavior. A contract change alone does not require both full suites.
- UI changes: follow [UI acceptance](docs/testing/UI_ACCEPTANCE.md). Name the reference pattern the
  surface reuses, add or complete its state-inventory row (applicable states or a reason each is
  inapplicable), and exercise its user-critical states in a real-backend browser runner with at least
  two object types or model configurations, keyboard operation and 390px width. Inspect the changed
  screenshots against the reference; add or update scenarios and baselines only for changed surfaces.
  Reserve the comprehensive accessibility and visual runners for build acceptance.
- Startup or migration code: retain the focused bootstrap, upgrade, restart, interrupted-migration,
  lifespan and final smoke checks required above. Concurrency and security changes likewise require
  focused checks at the real affected boundary; do not defer these checks to the end of the build.
- Documentation or agent configuration only: validate syntax, links or configuration as relevant;
  application test suites are not required.

Package completion requires its focused checks to pass. Record the checks actually exercised and
identify comprehensive checks deferred to build acceptance; do not claim release acceptance from
package evidence. A package report states the exact user flow exercised, the failure boundaries
affected, the named UI reference and the focused commands, and reports functional, accessibility
and visual evidence separately. An uninspected appearance is reported as unverified. These rules govern package delivery even when an older plan or workflow refers
loosely to the “full validation matrix”.

### Build acceptance

After the build's implementation packages are complete, run the full backend `pytest` suite and
frontend `npm run test`, plus Ruff, frontend format/lint/build and composed acceptance journeys
for the affected layers. Run `npm run test:a11y` and `npm run test:visual` for builds with UI changes.
For Base 0.7, WP-9 owns this comprehensive acceptance. Reuse unchanged passing static checks and
focused startup/migration evidence; focused package tests do not replace the full build suites.

Accessibility scenarios must include the changed controls and two object types. Unexpected
violations fail the gate; known violations require tracked references in
`e2e/accessibility-gate.mjs`. Visual checks compare against committed `e2e/baselines/`; review
intentional baseline updates before including them in the change. Dark baselines cover a
representative subset (`*-dark`); extend them and the dark accessibility scenarios when a change
affects theme tokens or a new surface. Do not update baselines merely to hide an unexplained failure.

### Execution discipline

- Run comprehensive suites once at build acceptance, rather than after every package or edit.
  Broaden a package check only for a concrete uncovered risk or an explicit user request; state
  the reason before running the broader check.
- After a failure and fix, rerun the failing cases and affected adjacent boundary. Rerun a full
  acceptance suite only when the fix has broad impact or the failure remains unexplained.
- Reuse passing checks while their relevant code remains unchanged. A change elsewhere does not
  invalidate all previous evidence. Do not repeat equivalent checks for the same behavior.
- Keep test output bounded and report concise results. While a test runs, wait for completion
  rather than repeatedly polling, reanalysing unchanged code or launching overlapping checks.
- Never run multiple backend `pytest` processes concurrently because they share a test database.

## Agent orchestration

The primary agent implements, validates, reviews and reports directly by default. Do not delegate
routine discovery, implementation, testing or review merely to follow a workflow.

Use one subagent only when it materially improves the result:

- an unfamiliar area needs bounded, read-only discovery;
- a genuine architecture question remains after consulting existing decisions;
- a migration, concurrency, security or broad public-contract change merits independent review; or
- the user explicitly requests delegation or parallel agents.

Use at most one subagent during a normal work package. Multiple subagents require an explicit user
request or clearly independent work whose time saving outweighs their token and coordination cost.
The primary agent remains responsible for the completed implementation and final validation.

### Model allocation

- Use Luna only for narrow, repeatable searches or mechanical checks.
- Use Terra for a bounded implementation or focused review.
- Use Sol for difficult architecture decisions, invariant-heavy implementation or complex failures.
- Start with low or medium reasoning and increase it only when concrete complexity requires it.

### Proportional use

- Small and normal changes: the primary agent works directly.
- Unfamiliar code path: one explorer returns a short map, then the primary agent continues.
- Genuine architectural ambiguity: one architect returns a decision, then the primary agent continues.
- High-risk completed change: one reviewer examines the final diff.
- Test execution stays with the primary agent unless the user explicitly requests a test runner.

Do not spawn multiple agents to analyse the same code or repeat work the primary agent has completed.

### Editing and concurrency

Only one agent may write during a work package. Prefer the primary agent as the implementation
owner; if implementation is delegated, give one agent the complete bounded ownership unit.

Do not run implementation and review concurrently. Review the completed diff.

Subagents must preserve unrelated working-tree changes and must not commit,
revert or rewrite another agent's work.

### Context discipline

Give each subagent only:

- a reference to the active work-package specification rather than a copy of it;
- relevant acceptance criteria;
- relevant architecture constraints;
- the files or modules it is expected to inspect.

Subagents should use targeted search rather than reading the whole repository.
They must return concise findings with file and symbol references, without raw
logs or a complete narration of their work.

Keep prompts short and ask one concrete question. The primary agent should reuse subagent findings
and must not repeat the same exploration unless the evidence is incomplete.

### Work-package completion

The objective is a completed, verified work package, not merely an implementation
plan.

When a work package is too large to implement safely as one ownership unit, stop
after discovery and propose explicit independently deliverable slices. Do not
silently divide one work package into overlapping implementation tasks.
